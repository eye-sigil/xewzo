"""Funpack Util"""

from discord.ext import commands
import addict
import rethinkdb as r


class FeatureNotOwned(commands.CommandError):
    """Thrown when user can't use feature."""
    pass


def feature() -> bool:
    """Automatically registers features."""
    async def predicate(ctx) -> bool:
        player = r \
            .table('profiles') \
            .get_all(str(ctx.author.id), index='user') \
            .run(ctx.bot.conn) \
            .next()
        if ctx.command.name in player['features']:
            return True
        raise FeatureNotOwned(ctx.command.name)

    return commands.check(predicate)
