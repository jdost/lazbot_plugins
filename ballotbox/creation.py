from app import bot
from lazbot import logger
from lazbot.schedule import tz
import parsedatetime
from .poll import Poll


@bot.listen("@me: ask <channel:target> <*:question>", regex=True)
@bot.listen("@me: ask <*:question>", regex=True)
def start(channel, question, user, target=None):
    if not target:
        target = channel

    poll = Poll(question, user, target)

    logger.info(str(poll))
    poll.ask()


@bot.listen("@me: close poll")
@bot.listen("@me: close poll <*:time>", regex=True)
def close(channel, user, time=None):
    target_poll = Poll.find(user=user, channel=channel)

    if not target_poll:
        return  # spit out error

    target_poll = target_poll[0]

    if time:
        target_time, _ = parsedatetime.Calendar().parseDT(time, tzinfo=tz(
            offset=user.timezone))
        target_poll.schedule(target_time)
    else:
        target_poll.close()
