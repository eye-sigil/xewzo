import discord
from discord.ext import commands
from utils import permissions, randomness
import aiohttp
import asyncio
import subprocess
import inspect
import collections
import traceback
import io
import datetime
import time
from contextlib import redirect_stdout
from lxml import etree
import textwrap
import rethinkdb as r
from urllib.parse import quote as uriquote
from typing import Union


class Utility:

    def __init__(self, bot):
        self.bot = bot
        self.repl_sessions = {}
        self.repl_embeds = {}
        self.aioclient = aiohttp.ClientSession()
        self.conn = bot.conn
        self._eval = {}

    def cleanup_code(self, content):
        '''Automatically removes code blocks from the code.'''
        # remove ```py\n```
        if content.startswith('```') and content.endswith('```'):
            return '\n'.join(content.split('\n')[1:-1])

        # remove `foo`
        return content.strip('` \n')

    def get_syntax_error(self, err):
        '''Returns SyntaxError formatted for repl reply.'''
        return '```py\n{0.text}{1:>{0.offset}}\n{2}: {0}```'.format(
            err,
            '^',
            type(err).__name__)

    async def post_to_hastebin(self, string):
        '''Posts a string to hastebin.'''
        url = "https://hastebin.com/documents"
        data = string.encode('utf-8')
        async with self.aioclient.post(url=url, data=data) as haste_response:
            haste_key = (await haste_response.json())['key']
            haste_url = f"http://hastebin.com/{haste_key}"
        # data = {'sprunge': ''}
        # data['sprunge'] = string
        # haste_url = await self.aioclient.post(url='http://sprunge.us',
        # data=data)
        return haste_url

    @commands.group(name='shell',
                    aliases=['ipython', 'repl',
                             'longexec', 'core', 'overkill'],
                    pass_context=True,
                    invoke_without_command=True)
    @permissions.owner()
    async def repl(self, ctx, *, name: str=None):
        '''Head on impact with an interactive python shell.'''
        # TODO Minimize local variables
        # TODO Minimize branches

        session = ctx.message.channel.id

        embed = discord.Embed(
            description="_Enter code to execute or evaluate. "
            "`exit()` or `quit` to exit._",
            timestamp=datetime.datetime.now())

        embed.set_footer(
            text="Interactive Python Shell",
            icon_url="https://upload.wikimedia.org/wikipedia/commons/thumb"
            "/c/c3/Python-logo-notext.svg/1024px-Python-logo-notext.svg.png")

        if name is not None:
            embed.title = name.strip(" ")

        history = collections.OrderedDict()

        variables = {
            'ctx': ctx,
            'bot': self.bot,
            'message': ctx.message,
            'server': ctx.message.guild,
            'channel': ctx.message.channel,
            'author': ctx.message.author,
            'discord': discord,
            'r': r,
            'conn': self.conn,
            '_': None
        }

        if session in self.repl_sessions:
            error_embed = discord.Embed(
                color=15746887,
                description="**Error**: "
                "_Shell is already running in channel._")
            await ctx.send(embed=error_embed)
            return

        shell = await ctx.send(embed=embed)

        self.repl_sessions[session] = shell
        self.repl_embeds[shell] = embed

        while True:
            response = await self.bot.wait_for(
                'message',
                check=lambda m: m.content.startswith('`') and m.author == ctx.author and m.channel == ctx.channel)

            cleaned = self.cleanup_code(response.content)
            shell = self.repl_sessions[session]

            # Regular Bot Method
            try:
                await ctx.message.channel.get_message(
                    self.repl_sessions[session].id)
            except discord.NotFound:
                new_shell = await ctx.send(embed=self.repl_embeds[shell])
                self.repl_sessions[session] = new_shell

                embed = self.repl_embeds[shell]
                del self.repl_embeds[shell]
                self.repl_embeds[new_shell] = embed

                shell = self.repl_sessions[session]

            try:
                await response.delete()
            except discord.Forbidden:
                pass

            if len(self.repl_embeds[shell].fields) >= 7:
                self.repl_embeds[shell].remove_field(0)

            if cleaned in ('quit', 'exit', 'exit()'):
                self.repl_embeds[shell].color = 16426522

                if self.repl_embeds[shell].title is not discord.Embed.Empty:
                    history_string = "History for {}\n\n\n".format(
                        self.repl_embeds[shell].title)
                else:
                    history_string = "History for latest session\n\n\n"

                for item in history.keys():
                    history_string += ">>> {}\n{}\n\n".format(
                        item,
                        history[item])

                haste_url = await self.post_to_hastebin(history_string)
                return_msg = "[`Leaving shell session. "\
                    "History hosted on hastebin.`]({})".format(
                        haste_url)

                self.repl_embeds[shell].add_field(
                    name="`>>> {}`".format(cleaned),
                    value=return_msg,
                    inline=False)

                await self.repl_sessions[session].edit(
                    embed=self.repl_embeds[shell])

                del self.repl_embeds[shell]
                del self.repl_sessions[session]
                return

            executor = exec
            if cleaned.count('\n') == 0:
                # single statement, potentially 'eval'
                try:
                    code = compile(cleaned, '<repl session>', 'eval')
                except SyntaxError:
                    pass
                else:
                    executor = eval

            if executor is exec:
                try:
                    code = compile(cleaned, '<repl session>', 'exec')
                except SyntaxError as err:
                    self.repl_embeds[shell].color = 15746887

                    return_msg = self.get_syntax_error(err)

                    history[cleaned] = return_msg

                    if len(cleaned) > 800:
                        cleaned = "<Too big to be printed>"
                    if len(return_msg) > 800:
                        haste_url = await self.post_to_hastebin(return_msg)
                        return_msg = "[`SyntaxError too big to be printed. "\
                            "Hosted on hastebin.`]({})".format(
                                haste_url)

                    self.repl_embeds[shell].add_field(
                        name="`>>> {}`".format(cleaned),
                        value=return_msg,
                        inline=False)

                    await self.repl_sessions[session].edit(
                        embed=self.repl_embeds[shell])
                    continue

            variables['message'] = response

            fmt = None
            stdout = io.StringIO()

            try:
                with redirect_stdout(stdout):
                    result = executor(code, variables)
                    if inspect.isawaitable(result):
                        result = await result
            except Exception as err:
                self.repl_embeds[shell].color = 15746887
                value = stdout.getvalue()
                fmt = '```py\n{}{}\n```'.format(
                    value,
                    traceback.format_exc())
            else:
                self.repl_embeds[shell].color = 4437377

                value = stdout.getvalue()

                if result is not None:
                    fmt = '```py\n{}{}\n```'.format(
                        value,
                        result)

                    variables['_'] = result
                elif value:
                    fmt = '```py\n{}\n```'.format(value)

            history[cleaned] = fmt

            if len(cleaned) > 800:
                cleaned = "<Too big to be printed>"

            try:
                if fmt is not None:
                    if len(fmt) >= 800:
                        haste_url = await self.post_to_hastebin(fmt)
                        self.repl_embeds[shell].add_field(
                            name="`>>> {}`".format(cleaned),
                            value="[`Content too big to be printed. "
                            "Hosted on hastebin.`]({})".format(
                                haste_url),
                            inline=False)

                        await self.repl_sessions[session].edit(
                            embed=self.repl_embeds[shell])
                    else:
                        self.repl_embeds[shell].add_field(
                            name="`>>> {}`".format(cleaned),
                            value=fmt,
                            inline=False)

                        await self.repl_sessions[session].edit(
                            embed=self.repl_embeds[shell])
                else:
                    self.repl_embeds[shell].add_field(
                        name="`>>> {}`".format(cleaned),
                        value="`Empty response, assumed successful.`",
                        inline=False)

                    await self.repl_sessions[session].edit(
                        embed=self.repl_embeds[shell])

            except discord.Forbidden:
                pass

            except discord.HTTPException as err:
                error_embed = discord.Embed(
                    color=15746887,
                    description='**Error**: _{}_'.format(err))
                await ctx.send(embed=error_embed)

    @repl.command(name='jump',
                  aliases=['hop', 'pull', 'recenter', 'whereditgo'],
                  pass_context=True)
    @permissions.owner()
    async def _repljump(self, ctx):
        '''Brings the shell back down so you can see it again.'''

        session = ctx.message.channel.id

        if session not in self.repl_sessions:
            error_embed = discord.Embed(
                color=15746887,
                description="**Error**: _No shell running in channel._")
            await ctx.send(embed=error_embed)
            return

        shell = self.repl_sessions[session]
        embed = self.repl_embeds[shell]

        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass

        try:
            await shell.delete()
        except discord.errors.NotFound:
            pass
        new_shell = await ctx.send(embed=embed)

        self.repl_sessions[session] = new_shell

        del self.repl_embeds[shell]
        self.repl_embeds[new_shell] = embed

    @repl.command(name='clear',
                  aliases=['clean', 'purge', 'cleanup',
                           'ohfuckme', 'deletthis'],
                  pass_context=True)
    @permissions.owner()
    async def _replclear(self, ctx):
        '''Clears the fields of the shell and resets the color.'''

        session = ctx.message.channel.id

        if session not in self.repl_sessions:
            error_embed = discord.Embed(
                color=15746887,
                description="**Error**: _No shell running in channel._")
            await ctx.send(embed=error_embed)
            return

        shell = self.repl_sessions[session]

        self.repl_embeds[shell].color = discord.Color.default()
        self.repl_embeds[shell].clear_fields()

        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass
        await shell.edit(embed=self.repl_embeds[shell])

    @commands.command(name="setavy")
    @permissions.owner()
    async def set_avy(self, ctx, *, avy: str):
        async with aiohttp.ClientSession() as sesh:
            async with sesh.get(avy) as r:
                await self.bot.user.edit(avatar=await r.read())
                await ctx.send(":ok_hand:")

    @commands.command(name='eval',
                      aliases=["ev", "e"])
    @permissions.owner()
    async def eval_cmd(self, ctx, *, code: str):
        """Evaluates Python code"""
        if self._eval.get('env') is None:
            self._eval['env'] = {}
        if self._eval.get('count') is None:
            self._eval['count'] = 0

        codebyspace = code.split(" ")
        print(codebyspace)
        silent = False
        if codebyspace[0] == "--silent" or codebyspace[0] == "-s":
            silent = True
            codebyspace = codebyspace[1:]
            code = " ".join(codebyspace)

        self._eval['env'].update({
            'self': self.bot,
            'ctx': ctx,
            'message': ctx.message,
            'channel': ctx.message.channel,
            'guild': ctx.message.guild,
            'author': ctx.message.author,
        })

        # let's make this safe to work with
        code = code.replace('```py\n', '').replace('```', '').replace('`', '')

        _code = (
            'async def func(self):\n  try:\n{}\n  '
            'finally:\n    self._eval[\'env\'].update(locals())').format(
                textwrap.indent(code, '    '))

        before = time.monotonic()
        # noinspection PyBroadException
        try:
            exec(_code, self._eval['env'])
            func = self._eval['env']['func']
            output = await func(self)

            if output is not None:
                output = repr(output)
        except Exception as e:
            output = '{}: {}'.format(type(e).__name__, e)
        after = time.monotonic()
        self._eval['count'] += 1
        count = self._eval['count']

        code = code.split('\n')
        if len(code) == 1:
            _in = 'In [{}]: {}'.format(count, code[0])
        else:
            _first_line = code[0]
            _rest = code[1:]
            _rest = '\n'.join(_rest)
            _countlen = len(str(count)) + 2
            _rest = textwrap.indent(_rest, '...: ')
            _rest = textwrap.indent(_rest, ' ' * _countlen)
            _in = 'In [{}]: {}\n{}'.format(count, _first_line, _rest)

        message = '```py\n{}'.format(_in)
        if output is not None:
            message += '\nOut[{}]: {}'.format(count, output)
        ms = int(round((after - before) * 1000))
        if ms > 100:  # noticeable delay
            message += '\n# {} ms\n```'.format(ms)
        else:
            message += '\n```'

        try:
            if ctx.author.id == self.bot.user.id:
                await ctx.message.edit(content=message)
            else:
                if not silent:
                    await ctx.send(message)
        except discord.HTTPException:
            if not silent:
                with aiohttp.ClientSession() as sesh:
                    async with sesh.post(
                            "https://hastebin.com/documents/",
                            data=output,
                            headers={"Content-Type": "text/plain"}) as r:
                        r = await r.json()
                        embed = discord.Embed(
                            description=(
                                "[View output - click]"
                                "(https://hastebin.com/raw/{})").format(
                                    r["key"]),
                            color=randomness.random_colour())
                        await ctx.send(embed=embed)

    @commands.command(aliases=['sys', 's', 'run', 'sh'],
                      description="Run system commands.")
    @permissions.owner()
    async def system(self, ctx, *, command: str):
        'Run system commands.'
        message = await ctx.send('<a:typing:401162479041773568> Processing...')
        result = []
        try:
            process = subprocess.Popen(command.split(
                ' '), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            result = process.communicate()
        except FileNotFoundError:
            stderr = f'Command not found: {command}'
        embed = discord.Embed(
            title="Command output",
            color=randomness.random_colour()
        )
        if len(result) >= 1 and result[0] in [None, b'']:
            stdout = 'No output.'
        if len(result) >= 2 and result[0] in [None, b'']:
            stderr = 'No output.'
        if len(result) >= 1 and result[0] not in [None, b'']:
            stdout = result[0].decode('utf-8')
        if len(result) >= 2 and result[1] not in [None, b'']:
            stderr = result[1].decode('utf-8')
        string = ""
        if len(result) >= 1:
            if (len(result[0]) >= 1024):
                stdout = result[0].decode('utf-8')
                string = string + f'[[STDOUT]]\n{stdout}'
                link = await self.post_to_hastebin(string)
                await message.edit(
                    content=f":x: Content too long. {link}",
                    embed=None)
                return
        if len(result) >= 2:
            if (len(result[1]) >= 1024):
                stdout = result[0].decode('utf-8')
                string = string + f'[[STDERR]]\n{stdout}'
                link = await self.post_to_hastebin(string)
                await message.edit(
                    content=f":x: Content too long. {link}",
                    embed=None)
                return
        embed.add_field(
            name="stdout",
            value=f'```{stdout}```' if 'stdout' in locals() else 'No output.',
            inline=False)
        embed.add_field(
            name="stderr",
            value=f'```{stderr}```' if 'stderr' in locals() else 'No output.',
            inline=False)
        await message.edit(content='', embed=embed)

    @commands.command(aliases=['game', 'status'])
    @permissions.owner()
    async def setgame(self, ctx, *, status: str):
        await ctx.bot.change_presence(game=discord.Game(name=status, type=0))
        await ctx.send(':ok_hand:')

    @commands.command()
    @permissions.owner()
    async def maintenance(self, ctx, state: str=None):
        bools = False
        if state is not None:
            if state in ['true', 'false', 'on', 'off']:
                bools = state in ['on', 'true']

        if bools:
            prompt = await ctx.send('```Are you sure you want to do this? This will make the bot stop responding to anyone but you!\n\n[y]: Enter Maintenance mode\n[n]: Exit prompt```')
            poll = await self.bot.wait_for('message', check=lambda m: m.author == ctx.author and m.channel == ctx.channel)
            if poll.content == 'y':
                await prompt.delete()
                await self.bot.change_presence(status=discord.Status.dnd, game=None)
                self.bot.maintenance = True
                await ctx.send(':white_check_mark: Bot in maintenance mode.')
                return
            else:
                await prompt.delete()
                await ctx.send('Prompt exited.')
        elif bools == False:
            self.bot.maintenance = False
            await self.bot.change_presence(game=discord.Game(
                name=f'{self.bot.prefix[0]}help',
                type=2))
            await ctx.send(':white_check_mark: Bot in regular mode.')

    @commands.command()
    @permissions.owner()
    async def git(self, ctx, sub, flags=""):
        """Runs some git commands in Discord."""

        if sub == "gud":
            if not flags:
                return await ctx.send("```You are now so gud!```")
            else:
                return await ctx.send(
                    "```{} is now so gud!```".format(flags))
        elif sub == "rekt":
            if not flags:
                return await ctx.send("```You got #rekt!```")
            else:
                return await ctx.send(
                    "```{} got #rekt!```".format(flags))
        else:
            process_msg = await ctx.send(
                "<a:typing:401162479041773568> Processing...")
            process = subprocess.Popen(
                f"git {sub + flags}",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
            res = process.communicate()
            if res[0] == b'':
                content = "Successful!"
            else:
                content = res[0].decode("utf8")
            return await process_msg.edit(content=f"```{content}```")

    # @commands.command(aliases=['contest', 'vote'])
    # async def poll(self, ctx, question: str, time: int=120,
    #                *emojis: Union[discord.Emoji, str]):
    #     """Creates a poll with reaction options."""
    #     emojis = set(emojis)  # Remove duplicates
    #     if len(emojis) <= 1:
    #         return await ctx.send(
    #             "\u274C Cannot start poll with one option or less.",
    #             delete_after=3)

    #     # Initial poll message
    #     poll = (
    #         f"**{ctx.author.mention}** asks: {question}\n\n"
    #         f"_Poll active for {time} seconds. React below to vote._")
    #     async with ctx.channel.typing():
    #         poll_msg = await ctx.send(poll)
    #         for emoji in emojis:
    #             try:
    #                 await poll_msg.add_reaction(emoji)
    #             except discord.NotFound:
    #                 pass

    #     asyncio.sleep(time)  # Users are reacting

    #     # End of poll
    #     results_emojis = [reaction.emoji for reaction in poll_msg.reactions
    #                       if reaction.emoji in emojis]
    #     results_count = collections.Counter(results_emojis)
    #     results = f"**Poll by {ctx.author} ended!**\n\n"
    #     for emoji, count in results_count.most_common():
    #         results += f"{emoji}: _{count}_ \n"
    #     await ctx.send(results)


def setup(bot):
    bot.add_cog(Utility(bot))
