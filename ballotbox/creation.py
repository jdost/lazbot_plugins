from app import bot, config
from lazbot import logger
from lazbot.schedule import tz
from lazbot.models import Channel
import parsedatetime
from .poll import Poll, polls
from datetime import datetime, timedelta

EXPIRATION = timedelta(**config.get("expires_after", {"days": 1}))
CLEANUP_FREQUENCY = timedelta(
        **config.get("cleanup_frequency", {"minutes": 15}))


@bot.listen("@me: ask <channel:target> <*:question>", regex=True)
@bot.listen("@me: ask <channel:target> <*:question>", channel=Channel.IM,
            regex=True)
@bot.listen("@me: ask <*:question>", regex=True)
def start(channel, question, user, target=None):
    ''' asks a channel a question as a poll
    Will post a poll to a channel, which entails the question asked and
    reaction based options to "vote" on your responses to the question.  If
    a channel is specified, the question will target that channel, if none is
    provided, it will be in the current channel.

    usage: `@me ask [<channel>] <question>`
    '''
    if Poll.find(user=user, channel=channel):
        user.im("You already have a poll open in {!s}".format(channel))
        return

    if not target:
        target = channel

    poll = Poll(question, user, target)

    logger.info(str(poll))
    poll.ask()


@bot.listen("@me: close poll")
@bot.listen("@me: close poll <*:time>", regex=True)
def close(channel, user, time=None):
    ''' closes your active poll
    If you have an active poll in the channel, this will either close it
    immediately or if a time is given will close it at that point in time.

    usage: `@me close poll [<time>]`
    '''
    target_poll = Poll.find(user=user, channel=channel)

    if not target_poll:
        logger.warn("No poll found for %s in %s", user, channel)
        user.im("You do not have a poll open in {!s}".format(channel))
        return

    target_poll = target_poll[0]

    if time:
        tz_info = tz(offset=user.timezone)
        target_time, _ = parsedatetime.Calendar().parseDT(time, tzinfo=tz_info)
        if target_time > datetime.now(tz_info):
            target_poll.schedule(target_time)
        else:
            user.im("Sorry, that time is in the past")
    else:
        target_poll.close()


@bot.schedule(after=CLEANUP_FREQUENCY, recurring=True)
def cleanup():
    deleted_polls = []
    now = datetime.now()

    for poll in polls:
        if poll.state == Poll.OPEN and now - poll.created_at > EXPIRATION:
            deleted_polls.append(poll)

    for poll in deleted_polls:
        logger.info("Deleting poll %s", poll)
        poll.delete()
