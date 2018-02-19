from discord.ext import commands
import discord
import addict
import rethinkdb as r


class Profile:

    def __init__(self, bot):
        self.bot = bot
        self.conn = bot.conn

    @commands.group(invoke_without_command=True)
    async def profile(self, ctx, user: discord.User=None):
        """Group for profile"""
        if not user:
            user = ctx.author
        async with ctx.channel.typing():
            # Profile
            profile = r \
                .table("profile") \
                .filter({"user": str(user.id)}) \
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
            embed.set_thumbnail(url=user.avatar)
            embed.add_field(
                name="Badges",
                value=profile.badges,
                inline=False)
            embed.add_field(
                name="Money",
                value="")
            embed.add_field(
                name="Items",
                value="")
            embed.add_field(
                name="Features",
                value="")

            await ctx.send(content, embed=embed)

    @profile.command()
    async def create(self, ctx, bio=None):
        """Creates a profile for a user"""
        exists = r \
            .table("profile") \
            .filter({"user": str(ctx.author.id)}) \
            .run(self.conn)

        if exists:
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
                    "items": [],
                    "features": []
                }
                r.table("profle") \
                 .insert(profile) \
                 .run(self.conn)

                await ctx.send(
                    f"{ctx.author.mention} Profile created! "
                    f"View it with {self.bot.prefix[0]}profile`.")
