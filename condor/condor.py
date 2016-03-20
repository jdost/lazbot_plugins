from app import bot, config
from lazbot.schedule import tz
from lazbot import logger
from datetime import datetime, time, timedelta

OPEN_DEV_EPOCH = datetime(tzinfo=tz(), **config["opendev"]["epoch"])
open_dev = False


@bot.schedule(when=time(hour=0, minute=0, tzinfo=tz()),
              after=timedelta(hours=24), recurring=True)
def check_day():
    logger.debug("Checking date...")
    now = datetime.now(tz())

    global open_dev
    open_dev_offset = now - OPEN_DEV_EPOCH
    open_dev = open_dev_offset.days % config["opendev"]["offset"] == 0
    if open_dev:
        logger.info("Open Dev has started")

check_day(quiet=True)  # runs without changing schedule


def is_opendev():
    global open_dev
    return open_dev


@bot.translate
def emojify(text):
    return text.lower().replace(" vs ", " :vs: ")


@bot.translate
def jimify(text):
    return text.replace("@jim", "@gym")


@bot.translate
def fast_and_loose(text):
    if not open_dev:
        return text
    return ' '.join([word.upper() if not word.startswith(("@", ":"))
                     else word for word in text.split()])


@bot.listen("*")
def remind_jim(channel, text, **kwargs):
    if text.find("@gym") != -1:
        bot.post(
            channel=channel,
            text='did you mean @jim?',
            translate=False,
        )
