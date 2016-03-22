from app import bot
from .poll import Poll


@bot.listen("@me: show open polls")
def show(channel):
    open_polls = Poll.find(channel=channel, state=Poll.OPEN)

    if not len(open_polls):
        bot.post(
            channel=channel,
            text="No open polls"
        )

    for poll in open_polls:
        bot.post(
            channel=channel,
            text="{} - {}".format(poll.question, poll.msg.__url__())
        )
