''' Performs randomized requests

Will flip coins or roll dice as requested and configured.
'''
from app import bot, config
from random import choice

COIN_OPTIONS = config.get("coin_sides", ["heads", "tails"])
DIE = {type: map(str, range(1, sides+1)) for (type, sides)
       in config.get("die", {"dice": 6}).items()}


@bot.listen("@me: flip coin")
def flip_coin(channel, user):
    ''' flips a coin for the user
    Will flip a coin for the user

    usage: `@me flip coin`
    '''
    result = choice(COIN_OPTIONS)
    channel.post("{!s}: flipped a {!s}".format(user, result))
    return result


@bot.listen("@me: roll <({}):die_type>"
            .format("|".join(DIE.keys())), regex=True)
@bot.listen("@me: roll <int:number> <({}):die_type>"
            .format("|".join(DIE.keys())), regex=True)
def roll_dice(channel, user, die_type, number=1):
    ''' rolls a variable number of various die types for the user
    Will roll one or many die of the requested type.

    available die: {!s}

    usage: `@me roll [<number>] <die>`
    '''

    die = DIE[die_type]
    results = [choice(die) for i in range(number)]
    channel.post("{!s}: rolled {!s}".format(user, ", ".join(results)))
    return results

# Hacky way of inserting variables into the docstring
roll_dice.__doc__ = roll_dice.__doc__.format(", ".join(DIE.keys()))
