from discord.ext import commands
import discord
import addict
import rethinkdb as r
import random
from utils import permissions


class Profile:

    def __init__(self, bot):
        self.bot = bot
        self.conn = bot.conn

    @commands.group(invoke_without_command=True,
                    aliases=['p', 'account'])
    async def profile(self, ctx, user: discord.Member=None):
        """Group for profile"""
        if not user:
            user = ctx.author
        # Profile
        try:
            contents = r \
                .table('profiles') \
                .get_all(str(user.id), index='user') \
                .run(self.conn) \
                .next()
        except r.ReqlCursorEmpty:
            await ctx.send(
                f"<:rpgxmark:415322326930817027> **{user.display_name}** "
                f"doesn't have a profile!")
            return
        contents = addict.Dict(contents)

        async with ctx.channel.typing():
            # Message
            message = (
                f"**{user.display_name}** _Level {contents.level} "
                f"(XP {contents.xp})_"
            )
            embed = discord.Embed(
                title=str(user),
                description=f"_{contents.bio}_" if contents.bio
                            else "_No bio set._",
                color=user.color)
            embed.set_thumbnail(url=user.avatar_url)

            badges = r \
                .table('badges') \
                .get_all(*contents.badges, index='name')\
                .run(self.conn)

            embed.add_field(
                name="Badges",
                value="".join(item['emoji'] for item in badges)
                if contents.badges else "Nothin' but a dusty shelf...",
                inline=False)
            embed.add_field(
                name="Money",
                value=contents.money,
                inline=True)

            inventory = r \
                .table('items') \
                .get_all(*contents.inventory, index='name')\
                .run(self.conn)
            embed.add_field(
                name="Inventory",
                value="".join(f"<:{item['name']}:{item['emoji_id']}>"
                              for item in inventory)
                      if contents.inventory
                      else "They've got nothin'!",
                inline=True)
            embed.add_field(
                name="Features",
                value=contents.features if contents.features
                else "They're a powerless peasant.",
                inline=True)
            embed.set_footer(
                text="React with section emoji to expand.",
                icon_url="https://cdn.discordapp.com/emojis/415322326939467777.png")

            await ctx.send(message, embed=embed)

    @profile.command(name='create',
                     aliases=['new', 'init', 'start', 'initialize', 'c'])
    async def _create(self, ctx, bio=None):
        """Creates a user profile."""
        exists = r \
            .table('profiles') \
            .get_all(str(ctx.author.id), index='user') \
            .run(self.conn)
        if list(exists):
            await ctx.send(
                f"<:rpgxmark:415322326930817027> **{ctx.author.mention}** "
                f"You already have a profile! If you want to reset it, "
                f"use `{self.bot.prefix[0]}profile reset`.",
                delete_after=7)
        else:
            async with ctx.channel.typing():
                contents = {
                    "user": str(ctx.author.id),
                    "bio": bio,
                    "level": 1,
                    "xp": 0,
                    "money": 50,
                    "badges": [],
                    "inventory": [],
                    "funpacks": [],
                    "features": []
                }
                r.table("profiles") \
                 .insert(contents) \
                 .run(self.conn)

                await ctx.send(
                    f"<:rpgcheckmark:415322326738010134>"
                    f" **{ctx.author.mention}** "
                    f"Profile created! View it with "
                    f"`{self.bot.prefix[0]}profile`.")

    @profile.command(name='reset')
    async def _reset(self, ctx):
        """Resets a user profile."""
        passcode = ''.join(random.sample("0123456789", 4))
        await ctx.send(
            f"<:rpgquestion:415322326842736671> "
            f"**{ctx.author.display_name}**, "
            f"Are you sure you want to reset your profile?\n\n"
            f"As well as your level, you'll lose all your "
            f"items and badges. Only your features will stay.\n\n"
            f"_Please input `{passcode}` to confirm. "
            f"Say anything else to cancel._")

        try:
            confirm = await self.bot.wait_for(
                'message', check=lambda m: m.author == ctx.author)
        except TimeoutError:
            await ctx.send(
                "<:rpgxmark:415322326930817027> Timed out. Reset cancelled.")

        if confirm.content == str(passcode):
            new_values = {
                'level': 1,
                'xp': 0,
                'money': 50,
                'items': [],
                'badges': []
            }
            r.table('profiles') \
                .get_all(str(ctx.author.id), index='user') \
                .update(new_values) \
                .run(self.conn)
            await ctx.send(
                f"<:rpgcheckmark:415322326738010134>"
                f"**{ctx.author.display_name}'s** profile reset (´；д；`)")
        else:
            await ctx.send("<:rpgxmark:415322326930817027> Reset cancelled.")

    @profile.command(name='bio', aliases=['b', 'tag', 'description'])
    async def _bio(self, ctx, *content: str):
        """Lets users set their bio"""
        content = " ".join(content)

        if not content:
            await ctx.send(
                f"<:rpgxmark:415322326930817027>"
                f"**{ctx.author.display_name}**, I need a bio to set one "
                f"for you **>:(**",
                delete_after=7)
            return
        elif len(content) > 254:
            await ctx.send(
                f"<:rpgxmark:415322326930817027>"
                f"**{ctx.author.display_name}**, bio too long  **;()**",
                delete_after=7)
        elif content == 'reset':
            pass
        else:
            async with ctx.channel.typing():
                r.table('profiles') \
                 .get_all(str(ctx.author.id), index='user') \
                 .update({'bio': content}) \
                 .run(self.conn)
                await ctx.send(
                    f"<:rpgcheckmark:415322326738010134>"
                    f"**{ctx.author.display_name}**, bio changed to "
                    f"`{content}`.")

    @commands.command(name="create", aliases=["start"])
    async def create_alias(self, ctx, bio=None):
        """Creates a user profile."""
        await ctx.invoke(self.profile.get_command("create"), bio)

    @commands.command(name="reset", aliases=["wipe"])
    async def reset_alias(self, ctx):
        """Resets a user profile."""
        await ctx.invoke(self.profile.get_command("reset"))


def setup(bot):
    """Adds to d.py bot. Necessary for all cogs."""
    bot.add_cog(Profile(bot))
