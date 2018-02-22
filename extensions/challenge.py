from discord.ext import commands
import discord
import addict
import rethinkdb as r
import random


class Challenge:

    def __init__(self, bot):
        self.bot = bot
        self.conn = bot.conn
