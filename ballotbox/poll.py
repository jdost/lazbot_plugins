from app import bot, config
from lazbot import db
from lazbot import utils
from lazbot import logger
from collections import Counter
from lazbot.models import Message
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
    logger.info("Loaded %s active polls",
                len([True for p in polls if p.state != Poll.CLOSED]))


@bot.teardown(priority=True)
def save():
    db["polls"] = [poll.__json__() for poll in polls]


class Poll(object):
    INIT = "initialized"
    OPEN = "open"
    CLOSED = "closed"

    BOOLEAN = "boolean"

    def __init__(self, question, asker, target):
        self.question = question
        self.requester = asker
        self.channel = target
        self.type = Poll.BOOLEAN
        self.msg = None
        self.state = Poll.INIT
        self.close_at = None
        self.results = {}

        polls.append(self)

    def __json__(self):
        return {
            "question": self.question,
            "requester": self.requester.id,
            "channel": self.channel.id,
            "state": self.state,
            "msg": self.msg.__json__(),
            "close_at": self.close_at.isoformat(' ') if self.close_at else None
        }

    @classmethod
    def from_json(cls, json):
        poll = Poll(json["question"], bot.get_user(json["requester"]),
                    bot.get_channel(json["channel"]))
        poll.state = json["state"]
        poll.msg = Message.from_json(json["msg"])
        if json.get("close_at") and poll.state != Poll.CLOSED:
            close_at, _ = parsedatetime.Calendar().parseDT(
                json.get("close_at"))
            poll.schedule(json["close_at"])

        return poll

    def ask(self):
        self.msg = bot.post(
            channel=self.channel,
            text="Poll: {!s} (asked by {!s})".format(self.question,
                                                     self.requester),
        )

        if self.type is Poll.BOOLEAN:
            for vote, emoji in EMOJI.items():
                self.msg.react(emoji)
                self.results[vote] = []

        self.state = Poll.OPEN

    def close(self):
        self.state = Poll.CLOSED
        self.tally()

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

        # self.msg.update(self.results_msg.__url__())

    def tally(self):
        self.results = self.gather()
        votes = Counter([vote for votes in self.results.values() for vote
                         in votes])

        multi_voters = set([v for (v, cnt) in votes.items() if cnt > 1])
        for result in self.results:
            self.results[result] = map(
                bot.get_user, set(self.results[result]) - multi_voters)

    def gather(self):
        return self._gather_boolean() if self.type is Poll.BOOLEAN \
                else self._gather()

    def _gather_boolean(self):
        reactions_raw = self.msg.get_reactions()

        reactions = {}
        results = {}
        for reaction in reactions_raw:
            reactions[reaction["name"]] = reaction["users"]

        for (result, emoji) in EMOJI.items():
            results[result] = set(reactions[emoji])

        return results

    def _gather(self):
        return {}

    def matches(self, user=None, channel=None, state=None):
        return (self.requester == user if user else True) and \
            (self.channel == channel if channel else True) and \
            (self.state == state if state else True)

    @classmethod
    def find(cls, user=None, channel=None, state="open"):
        query = {"user": user, "channel": channel, "state": state}
        return [p for p in polls if p.matches(**query)]

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
