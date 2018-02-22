"""Store Cog"""

from discord.ext import commands
import discord
import rethinkdb as r
from util import permissions


class Store:

    def __init__(self, bot):
        self.bot = bot
        self.conn = bot.conn

    @commands.group()
    async def store(self, ctx):
        """Starts up the interactive store."""
        ...
