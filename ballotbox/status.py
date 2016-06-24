from app import bot
from .poll import Poll
from lazbot.models import Channel


@bot.listen("show <(open|closed):status> polls", channel=Channel.IM,
            regex=True)
@bot.listen("show polls", channel=Channel.IM)
@bot.listen("@me: show <(open|closed):status> polls", regex=True)
@bot.listen("@me: show polls")
def show(channel, user, status="open"):
    ''' lists the polls in this context
    Will list the polls in the channel based on their status.  If no status is
    provided, it will assume `open`.  The list will give the question and a
    URL to the original question post.

    usage: `@me show [<status>] polls`
        <status> can be either 'open' or 'closed'
    '''
    filter = {}
    filter["state"] = Poll.OPEN if status == "open" else Poll.CLOSED
    if channel.type == Channel.IM:
        filter["user"] = user
    else:
        filter["channel"] = channel

    open_polls = Poll.find(**filter)

    if not len(open_polls):
        bot.post(
            channel=channel,
            text="No open polls"
        )

    for poll in open_polls:
        bot.post(
            channel=channel,
            text="{}".format(poll.msg.__url__(poll.question))
        )
