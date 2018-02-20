from discord.ext import commands
import discord
import addict
import rethinkdb as r
import random


class Profile:

    def __init__(self, bot):
        self.bot = bot
        self.conn = bot.conn

    @commands.group(invoke_without_command=True)
    async def profile(self, ctx, user: discord.Member=None):
        """Group for profile"""
        if not user:
            user = ctx.author
        async with ctx.channel.typing():
            # Profile
            profile = r \
                .table('profiles') \
                .get_all(str(user.id), index='user') \
                .run(self.conn) \
                .next()
            profile = addict.Dict(profile)

            # Message
            content = (
                f"**{user.display_name}** _Level {profile.level} "
                f"(XP {profile.xp})_"
            )
            embed = discord.Embed(
                title=str(user),
                description=f"_{profile.bio}_" if profile.bio
                            else "_No bio set._",
                color=user.color)
            embed.set_thumbnail(url=user.avatar_url)
            embed.add_field(
                name="Badges",
                value=profile.badges if profile.badges
                else "Nothin' but a dusty shelf...",
                inline=False)
            embed.add_field(
                name="Money",
                value=profile.money,
                inline=True)
            embed.add_field(
                name="Inventory",
                value=profile.inventory if profile.inventory
                else "They've got nothin'!",
                inline=True)
            embed.add_field(
                name="Features",
                value=profile.features if profile.features
                else "They're a powerless peasant.",
                inline=True)

            await ctx.send(content, embed=embed)

    @profile.command(aliases=['new', 'init', 'start', 'initialize'])
    async def create(self, ctx, bio=None):
        """Creates a profile for a user"""
        exists = r \
            .table('profiles') \
            .get_all(str(ctx.author.id), index='user') \
            .run(self.conn)
        if list(exists):
            await ctx.send(
                f"You already have a profile! If you want to reset it, "
                f"use `{self.bot.prefix[0]}profile reset`.",
                delete_after=7)
        else:
            async with ctx.channel.typing():
                profile = {
                    "user": str(ctx.author.id),
                    "bio": bio,
                    "level": 1,
                    "xp": 0,
                    "money": 50,
                    "badges": [],
                    "inventory": [],
                    "features": []
                }
                r.table("profiles") \
                 .insert(profile) \
                 .run(self.conn)

                await ctx.send(
                    f"{ctx.author.mention} Profile created! "
                    f"View it with `{self.bot.prefix[0]}profile`.")

    @profile.command()
    async def reset(self, ctx):
        """Resets a user profile."""
        passcode = ''.join(random.sample("0123456789", 4))
        await ctx.send(
            f"Are you sure you want to reset your profile?\n\n"
            f"As well as your level, you'll lose all your "
            f"items and badges. Only your features will stay.\n\n"
            f"_Please input `{passcode}` to confirm. "
            f"Say anything else to cancel._")

        try:
            confirm = await self.bot.wait_for(
                'message', check=lambda m: m.author == ctx.author)
        except TimeoutError:
            await ctx.send("Timed out. Reset cancelled.")

        if confirm.content == passcode:
            async with ctx.channel.typing():
                new_values = {
                    'level': 1,
                    'xp': 0,
                    'money': 50,
                    'items': [],
                    'badges': []
                }
                r.table('profile') \
                 .get_all(str(ctx.author.id), index='user') \
                 .update(new_values) \
                 .run(self.conn)
                await ctx.send("Profile reset.")
        else:
            await ctx.send("Reset cancelled.")

def setup(bot):
    """Adds to d.py bot. Necessary for all cogs."""
    bot.add_cog(Profile(bot))
