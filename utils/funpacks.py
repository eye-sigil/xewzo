"""Funpack Util"""

from discord.ext import commands
import addict
import rethinkdb as r


class FeatureNotOwned(commands.CommandError):
    """Thrown when user can't use feature."""
    pass


def feature(funpack: str, value: int=50) -> bool:
    """Automatically registers and confirms features."""

    async def predicate(ctx) -> bool:
        try:
            cursor = r.table('funpacks') \
                .filter({'name': funpack}) \
                .run(ctx.bot.conn) \
                .next()
        except r.ReqlCursorEmpty:
            contents = {
                'name': funpack,
                'value': value,
                'features': [ctx.command.name]
            }
            r.table('funpacks') \
             .insert(contents) \
             .run(ctx.bot.conn)
        else:
            if ctx.command.name not in cursor['features']:
                r.table('funpacks') \
                 .filter({'name': funpack}) \
                 .update({'features': r.row['features'].append(
                     ctx.command.name)}) \
                 .run(ctx.bot.conn)

        player = r \
            .table('profiles') \
            .get_all(str(ctx.author.id), index='user') \
            .run(ctx.bot.conn) \
            .next()
        if ctx.command.name in player['features']:
            return True
        raise FeatureNotOwned(ctx.command.name)

    return commands.check(predicate)
