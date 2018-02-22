from discord.ext import commands
import rethinkdb as r


class WrongRole(commands.CommandError):
    """Thrown when user has wrong role for command."""
    pass


async def is_owner_check(ctx) -> bool:
    if str(ctx.author.id) in ctx.bot.config.get('OWNERS'):
        return True
    raise WrongRole(message="bot owner")


async def is_moderator_check(ctx) -> bool:
    for role in ctx.author.roles:
        if str(role.id) in ctx.bot.config.get('MOD_ROLES'):
            return True
    raise WrongRole(message="moderator")


def owner_id_check(bot, _id) -> bool:
    return str(_id) in bot.config.get('OWNERS')


def owner() -> bool:
    return commands.check(is_owner_check)


def moderator() -> bool:
    return commands.check(is_moderator_check)
