from app import bot, config
from lazbot import db
from lazbot import utils
from lazbot import logger
from collections import Counter
from lazbot.schedule import tz
from lazbot.events import Message
import parsedatetime


EMOJI = utils.merge({
    "yes": "+1",
    "no": "-1",
    "neutral": "thumbsright"
}, config.get("emoji", {}))
polls = []


@bot.setup
def load():
    global polls
    polls = [Poll.from_json(json) for json in db.get("polls", [])]


@bot.teardown(priority=True)
def save():
    db["polls"] = [poll.__json__() for poll in polls]


@bot.listen("@me: ask <channel:target> <*:question>", regex=True)
@bot.listen("@me: ask <*:question>", regex=True)
def start(channel, question, user, target=None):
    if not target:
        target = channel

    poll = Poll(question, user, target)

    logger.info(str(poll))
    poll.ask()
    polls.append(poll)


@bot.listen("@me: close poll")
@bot.listen("@me: close poll <*:time>", regex=True)
def close(channel, user, time=None):
    target_poll = None
    for poll in polls:
        if poll.state == Poll.OPEN and poll.is_target(user, channel):
            target_poll = poll
            break

    if not target_poll:
        return  # spit out error

    if time:
        target_time, _ = parsedatetime.Calendar().parseDT(time, tzinfo=tz())
        target_poll.schedule(target_time)
    else:
        target_poll.close()


class Poll(object):
    INIT = "initialized"
    OPEN = "open"
    CLOSED = "closed"

    def __init__(self, question, asker, target):
        self.question = question
        self.requester = asker
        self.channel = target
        self.boolean = True
        self.msg = None
        self.state = Poll.INIT
        self.close_at = None
        self.results = {}

    @classmethod
    def from_json(cls, json):
        poll = Poll(json["question"], json["requester"], json["channel"])
        poll.state = json["state"]
        poll.msg = Message.from_json(json["msg"])
        if json.get("close_at"):
            poll.schedule(json["close_at"])

    def __json__(self):
        return {
            "question": self.question,
            "requester": self.requester,
            "channel": self.channel,
            "state": self.state,
            "msg": self.msg.__json__(),
            "close_at": self.close_at
        }

    def ask(self):
        self.msg = bot.post(
            channel=self.channel,
            text="Poll: {!s} (asked by {!s})".format(self.question,
                                                     self.requester),
        )

        if self.boolean:
            print self.msg.timestamp
            for vote, emoji in EMOJI.items():
                bot.client.reactions.add(
                    name=emoji,
                    channel=self.msg.channel.id,
                    timestamp=self.msg.timestamp
                )
                self.results[vote] = []

        self.state = Poll.OPEN

    def close(self):
        self.state = Poll.CLOSED
        reactions_raw = bot.client.reactions.get(
            channel=self.channel.id,
            timestamp=self.msg.timestamp,
            full=True
        ).body["message"]["reactions"]

        reactions = {}
        for reaction in reactions_raw:
            reactions[reaction["name"]] = reaction["users"]

        for (result, emoji) in EMOJI.items():
            self.results[result] = set(reactions[emoji])

        votes = Counter([vote for votes in self.results.values() for vote
                         in votes])
        multi_voters = set([v for (v, cnt) in votes.items() if cnt > 1])
        for result in self.results:
            self.results[result] = map(
                bot.get_user, set(self.results[result]) - multi_voters)

        logger.info("Poll closed")
        logger.info(str(self))

        if not any([len(r) for r in self.results.values()]):
            self.results_msg = bot.post(
                channel=self.channel,
                text="Poll Closed: {}, no one voted".format(self.question)
            )
        else:
            self.results_msg = bot.post(
                channel=self.channel,
                text="Poll Closed: {}".format(self.question)
            )

            for (vote, voters) in self.results.items():
                if len(voters):
                    bot.post(
                        channel=self.channel,
                        text="{} said {}: {}".format(
                            len(voters), vote, ", ".join(map(str, voters)))
                    )

        self.msg.update(self.results_msg.__url__())

    def is_target(self, user, channel):
        return self.requester == user and self.channel == channel

    def schedule(self, target_time):
        self.close_at = target_time
        bot.schedule(function=self.close, when=target_time)

    def __str__(self):
        if self.state == Poll.CLOSED:
            result_str = ', '.join(["{}:{}".format(r, len(v)) for (r, v)
                                    in self.results.items()])
            return "Results for {!s} ({!s}): {}".format(
                self.question, self.channel, result_str)
        else:
            return "{!s} asked {!s}: {}".format(self.requester, self.channel,
                                                self.question)
