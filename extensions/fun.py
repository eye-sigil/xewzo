import discord
from discord.ext import commands
import asyncio
import aiohttp
from datetime import datetime
import json
import ast
import math
import random
import re
from utils import randomness, permissions


def date(argument):
    formats = (
        '%Y/%m/%d',
        '%Y-%m-%d',
    )

    for fmt in formats:
        try:
            return datetime.strptime(argument, fmt)
        except ValueError:
            continue

    raise commands.BadArgument(':x: Date must be YYYY/MM/DD or YYYY-MM-DD.')


class Fun:

    def __init__(self, bot):
        self.bot = bot

    def dndint(self, no):
        if no == '':
            return 1
        return int(no)

    def gensuffix(self, number):
        if number == 1:
            return "st"
        elif number == 2:
            return "nd"
        elif number == 3:
            return "rd"
        else:
            return "th"

    @commands.command()
    async def cat(self, ctx):
        async with ctx.channel.typing():
            async with aiohttp.ClientSession() as session:
                async with session.get("http://random.cat/meow") as r:
                    r = await r.json()
                    url = r["file"]
                    await ctx.send(
                        embed=discord.Embed(title="Random Cat")
                                     .set_image(url=url)
                                     .set_footer(text="Powered by random.cat"))

    @commands.command()
    @commands.cooldown(10, 1, commands.BucketType.user)
    async def animalfact(self, ctx, _type: str):
        async with ctx.channel.typing():
            sesh = aiohttp.ClientSession()
            types = []
            async with sesh.get("http://fact.birb.pw/api/v1/endpoints") as r:
                if r.status == 200:
                    data = await r.text()
                    types = ast.literal_eval(data)  # safe eval, woot
                    joinedtypes = ", ".join(types)
            if _type not in types:
                sesh.close()
                return await ctx.send(
                    f":x: Invalid type. Available types are: {joinedtypes}")
            async with sesh.get(
                    "http://fact.birb.pw/api/v1/{}".format(_type)) as r:
                if r.status == 200:
                    data = await r.text()
                    json_resp = json.loads(data)
                    fact = json_resp["string"]

                    await ctx.send(
                        embed=discord.Embed(
                            title="{} fact".format(_type.title()),
                            color=randomness.random_colour(),
                            description=fact)
                        .set_footer(text="Powered by fact.birb.pw"))
                else:
                    await ctx.send(
                        ":x: An HTTP error has occurred.", delete_after=3)
            sesh.close()

    @commands.command(description="Number suffixes are fun.")
    async def numbermix(self, ctx):
        """ Number suffixes are fun. """
        numbers = ["fir", "seco", "thi",
                   "four", "fif", "six",
                   "seven", "eig", "nin", "ten"]
        suffix = ["st", "nd", "rd", "th"]
        correctlist = [v + self.gensuffix(i + 1)
                       for i, v in enumerate(numbers)]  # whee
        finished = []
        correctsuffixes = [self.gensuffix(i + 1) for i in range(len(numbers))]
        for i, v in enumerate(numbers):
            finished.append(v + random.choice(suffix))
        correct = [i for i, v in enumerate(finished)
                   if correctlist[i] == v]
        for ind, val in enumerate(finished):
            if correctlist[ind] == val:
                correct.append(val)

        correctstr = "none"
        joinedcorrect = ", ".join(str(correct))
        if correct != []:
            correctstr = (
                f"{joinedcorrect} ({len(correct)}, "
                f"{math.floor(len(correct) / len(correctlist) * 100)}%)")

        finishedstr = ", ".join(finished)
        if finished == correctlist:
            correctstr = "All of them! ^.^"
        await ctx.send(f"```\nOutput: {finishedstr}\nCorrect: {correctstr}```")

    @commands.command(description='Set the bot\'s nick to something.')
    async def bnick(self, ctx, *, nick: str=None):
        'Set the bot\'s nick to something.'
        if nick is None:
            await ctx.me.edit(nick=None)
            return await ctx.send(':ok_hand:')
        if len(nick) > 32:
            return await ctx.send(
                ':x: Give me a shorter nickname. (Limit: 32 characters)',
                delete_after=3)
        await ctx.me.edit(nick=nick)
        await ctx.send(':ok_hand:')
        await asyncio.sleep(30)
        await ctx.me.edit(nick=None)

    @commands.command(
        description='Roll a dice in DnD notation. (<sides>d<number of dice>)',
        aliases=['dice'])
    async def roll(self, ctx, dice: str):
        'Roll a dice in DnD notation. (<sides>d<number of dice>)'
        pat = re.match(r'(\d*)d(\d+)', dice)
        if pat is None:
            return await ctx.send(
                ':x: Invalid notation! Format must be in `<rolls>d<limit>`!')
        rl = self.dndint(pat[1])
        lm = int(pat[2])
        if rl > 200:
            return await ctx.send(':x: A maximum of 200 dice is allowed.')
        if rl < 1:
            return await ctx.send(':x: A minimum of 1 die is allowed.')
        if lm > 200:
            return await ctx.send(':x: A maximum of 200 faces is allowed.')
        if lm < 3:
            return await ctx.send(':x: A minimum of 3 face is allowed.')
        roll = [random.randint(1, lm) for _ in range(rl)]
        res = ', '.join([str(i) for i in roll])
        total = 0
        for i in roll:
            total = total + i
        await ctx.send(f'`{res} (Total: {total})`')

    @commands.command()
    async def ship(self, ctx,
                   member1: discord.Member,
                   member2: discord.Member):
        name1 = member1.display_name[0:round(len(member1.display_name) / 2)]
        name2 = member2.display_name[
            round(len(member2.display_name) / 2):0:-1][::-1]
        return await ctx.send(
            f'Your ship name is {f"{name1}{name2}" if random.random() >= 0.5 else f"{name2}{name1}"}')

    @commands.command(aliases=['eggtimer', 'えぐ'])  # egu
    async def egg(self, ctx, time: int=180, emote: str='🥚⏲'):
        if time > 300 or time < 5:
            return await ctx.send(
                'Maximum time allowed is 5 minutes (300 seconds). '
                'Minimum time allowed is 5 seconds.')
        await ctx.send(emote)
        await asyncio.sleep(time)
        m = await ctx.send(ctx.author.mention)
        await m.edit(content=emote)

    @commands.command(pass_context=True)
    async def nostalgia(self, ctx, date: date, *,
                        channel: discord.TextChannel=None):
        """Pins an old message from a specific date.
        If a channel is not given, then pins from the channel the
        command was ran on.
        The format of the date must be either YYYY-MM-DD or YYYY/MM/DD.
        """
        channel = channel or ctx.channel

        message = await channel.history(after=date, limit=1).flatten()

        if len(message) == 0:
            return await ctx.send('Could not find message.')

        message = message[0]

        try:
            await message.pin()
        except discord.HTTPException:
            await ctx.send('Could not pin message.')
        else:
            await ctx.send('Pinned message for 5 minutes.')
            await asyncio.sleep(300)
            await message.unpin()

    @nostalgia.error
    async def nostalgia_error(self, ctx, error):
        if isinstance(error, commands.BadArgument):
            await ctx.send(error, delete_after=3)


def setup(bot):
    bot.add_cog(Fun(bot))
