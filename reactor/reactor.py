from app import bot, config
from lazbot import logger
from condor import is_opendev

reactions = config.get("reactions", {})


@bot.listen("*", channel="#smash-chicago")
def react(user, channel, ts, *args, **kwargs):
    if not is_opendev():
        return

    if not user:
        return

    if user.name in reactions.keys():
        logger.info("Reacting with %s for %s.",
                    ", ".join(reactions[user.name]), user)

        for emoji in reactions[user.name]:
            try:
                bot.client.reactions.add(
                    name=emoji,
                    channel=channel.id,
                    timestamp=ts
                )
            except Exception as e:
                logger.error("Reaction %s for %s failed: %s",
                             emoji, user.name, e)
