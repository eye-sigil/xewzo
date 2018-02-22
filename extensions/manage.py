from discord.ext import commands
import discord
import addict
import rethinkdb as r
from utils import permissions, database
from typing import Optional, Union, List


class Manage:

    def __init__(self, bot):
        self.bot = bot
        self.conn = bot.conn

    # Utility Methods
    def add(self, contents: dict, name: str, table: str) -> str:
        """Adds item to a table."""
        cursor = list(r.table(table)
                       .get_all(name, index='name')
                       .run(self.conn))
        if not cursor:
            r.table(table) \
                .insert(contents) \
                .run(self.conn)
            return (
                f"<:rpgcheckmark:415322326738010134> "
                f"`{name}` added~")
        else:
            return (
                f"<:rpgxmark:415322326930817027> "
                f"`{name}` already exists...")

    def get(self, name: str, table: str) -> Optional[addict.Dict]:
        """Gets items from a table."""
        try:
            badge = r \
                .table(table) \
                .get_all(name, index='name') \
                .run(self.conn) \
                .next()
            return addict.Dict(badge)
        except r.ReqlCursorEmpty:
            return None

    def verify_features(self, *features) -> List[str]:
        """Verifies that what was given is a valid feature."""
        denied = []
        approved = []
        return denied, approved

    # Badge Commands
    @commands.group(invoke_without_subcommand=True)
    async def badge(self, ctx):
        """Provides info on and manages badge."""
        ctx.invoke(self._badgeinfo)  # No arguments

    @badge.command(name='info')
    async def _badgeinfo(self, ctx, badge: Union[discord.Emoji, str]):
        """Gives info for badge."""
        if type(badge) == discord.Emoji:
            badge = badge.name

        entry = self.get(badge, 'badges')
        if not entry:
            await ctx.send(
                f"<:rpgxmark:415322326930817027> "
                f"`{badge}` not found...",
                delete_after=7)
            return

        else:
            message = f"{entry.emoji} **`{entry.name}`**"
            embed = discord.Embed(
                description=f"_{entry.description}_"
            )
            await ctx.send(message, embed=embed)

    @badge.command(name='add')
    @permissions.moderator()
    async def _badgeadd(self, ctx, badge: discord.Emoji, description: str=None,
                        tradeable: bool=False, value: Optional[int]=None):
        """Adds a badge to the game."""

        contents = {
            'name': badge.name,
            'emoji_id': badge.id,
            'description': description,
            'emoji': str(badge),
            'icon': badge.url,
            'tradeable': tradeable,
            'value': value
        }

        async with ctx.channel.typing():
            await ctx.send(self.add(contents, badge.name, 'badges'))

    # Item Commands
    @commands.group(invoke_without_subcommand=True)
    async def item(self, ctx):
        """Provides info on and manages item."""
        ctx.invoke(self._iteminfo)  # No arguments

    @item.command(name='info')
    async def _iteminfo(self, ctx, item: Union[discord.Emoji, str]):
        """Gives info for item."""
        if type(item) == discord.Emoji:
            item = item.name

        entry = self.get(item, 'item')
        if not entry:
            await ctx.send(
                f"<:rpgxmark:415322326930817027> "
                f"`{item}` not found...",
                delete_after=7)
            return

        else:
            message = f"{entry.emoji} **`{entry.name}`**"
            embed = discord.Embed(
                description=f"_{entry.description}_"
            )
            await ctx.send(message, embed=embed)

    @item.command(name='add')
    @permissions.moderator()
    async def _itemadd(self, ctx, item: discord.Emoji, description: str=None,
                       tradeable: bool=False, exclusive: bool=False,
                       value: Optional[int]=None):
        """Adds an item to the game."""

        contents = {
            'name': item.name,
            'emoji_id': item.id,
            'description': description,
            'emoji': str(item),
            'icon': item.url,
            'tradeable': tradeable,
            'exclusive': exclusive,
            'value': value
        }

        async with ctx.channel.typing():
            await ctx.send(self.add(contents, item.name, 'items'))

            # Funpack Commands
    @commands.group(name='funpack', invoke_without_subcommand=True)
    async def funpack_cmd(self, ctx):
        """Provides info on and manages funpack."""
        ctx.invoke(self._funpackinfo)  # No arguments

    @funpack.command(name='info')
    async def _funpackinfo(self, ctx, funpack: Union[discord.Emoji, str]):
        """Gives info for funpack."""
        if type(funpack) == discord.Emoji:
            funpack = funpack.name

        entry = self.get(funpack, 'funpack')
        if not entry:
            await ctx.send(
                f"<:rpgxmark:415322326930817027> "
                f"`{funpack}` not found...",
                delete_after=7)
            return

        message = f"{entry.emoji} **`{entry.name}`**"
        embed = discord.Embed(
            description=f"_{entry.description}_"
        )
        await ctx.send(message, embed=embed)

    @funpack.command(name='add')
    @permissions.moderator()
    async def _funpackadd(self, ctx, funpack: str, description: str=None,
                          giftable: bool=False, exclusive: bool=False,
                          *features):
        """Adds an funpack to the game."""
        async with ctx.channel.typing():
            message = f""
            denied, approved = self.verify_features(*features)
            if denied:
                message += (
                    f"<:rpgxmark:415322326930817027>"
                    f"The following features weren't found:\n\n"
                    f"`{', '.join(denied)}`")

            contents = {
                'name': funpack.name,
                'description': description,
                'giftable': giftable,
                'exclusive': exclusive,
                'features': approved
            }

            await ctx.send(message + self.add(contents, funpack, 'funpacks'))

    @commands.group()
    @permissions.moderator()
    async def bank(self, ctx):
        """Gives or removes money from user."""

    @bank.command(name='add', aliases=['give'])
    @permissions.moderator()
    async def _bankadd(self, ctx, user: discord.Member, amount: int):
        """Gives money to a user."""
        amount = abs(amount)

        # database.verify_profile(user)

        database.edit_money(self.conn, user, amount)

        await ctx.send(
            f"<:rpgcheckmark:415322326738010134> "
            f"`{amount}` added to **{user.name}**~")

    @bank.command(name='subtract', aliases=['remove', 'take'])
    @permissions.moderator()
    async def _bankremove(self, ctx, user: discord.Member, amount: int):
        """Gives money to a user."""
        amount = -abs(amount)
        # database.verify_profile(user)

        database.edit_money(self.conn, user, amount)

        await ctx.send(
            f"<:rpgcheckmark:415322326738010134> "
            f"`{amount}` removed from **{user.name}** **>:)**")

    @commands.command()
    @permissions.moderator()
    async def givefeature(self, ctx, user: discord.Member, feature: str):
        """Raw add feature to a user."""
        profile = r \
            .table('profiles') \
            .get_all(str(user.id), index='user') \
            .run(self.conn) \
            .next()

        if feature in profile['features']:  # Avoid Duplicates
            await ctx.send(
                f"<:rpgxmark:415322326930817027> "
                f"**{user.display_name}** already has `{feature}` **:0**")

        profile['features'].append(feature)
        r.table('profiles') \
         .get_all(str(user.id), index='user') \
         .update({'features': profile['features']}) \
         .run(self.conn)
        await ctx.send(
            f"<:rpgcheckmark:415322326738010134> "
            f"`{feature}` given to **{user.display_name}**~")


def setup(bot):
    """Adds to d.py bot. Necessary for all cogs."""
    bot.add_cog(Manage(bot))
