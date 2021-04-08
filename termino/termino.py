import asyncio
import contextlib
import datetime
import logging

import discord
from redbot.core import commands, Config
from redbot.core.utils.chat_formatting import box, pagify
from redbot.core.utils.predicates import MessagePredicate

default_wave = "\N{WAVING HAND SIGN}\N{EMOJI MODIFIER FITZPATRICK TYPE-3}"
log = logging.getLogger("red.kreusada.termino")
now = datetime.datetime.now().strftime("%d/%m/%Y (%H:%M:%S)")


class Termino(commands.Cog):
    """Customize bot shutdown and restart messages, with predicates, too."""

    __author__ = ["Kreusada"]
    __version__ = "1.0.0"

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, 89434930598345, force_registration=True)
        self.config.register_global(
            shutdown_message=f"Shutting down... {default_wave}",
            restart_message="Restarting...",
            confirm_shutdown=True,
            confirm_restart=True,
            restart_channel_for_redboot=None,
        )
        self.var_formatter = lambda x, y: y.replace("{author}", x.author.display_name)
        self.task = self.bot.loop.create_task(self.initialize())

    def cog_unload(self):
        global shutdown
        global restart
        if self.task:
            self.task.cancel()
        if shutdown:
            try:
                self.bot.remove_command("shutdown")
            except Exception as e:
                log.info(e)
            self.bot.add_command(shutdown)
        if restart:
            try:
                self.bot.remove_command("restart")
            except Exception as e:
                log.info(e)
            self.bot.add_command(restart)

    def format_help_for_context(self, ctx: commands.Context) -> str:
        context = super().format_help_for_context(ctx)
        authors = ", ".join(self.__author__)
        return f"{context}\n\nAuthor: {authors}\nVersion: {self.__version__}"

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete"""
        return

    async def confirmation(self, ctx: commands.Context, _type: str):
        await ctx.send(f"Are you sure you want to {_type} {ctx.me.name}? (yes/no)")
        with contextlib.suppress(asyncio.TimeoutError):
            pred = MessagePredicate.yes_or_no(ctx, user=ctx.author)
            await ctx.bot.wait_for("message", check=pred, timeout=60)
            if pred.result:
                return True
            return False
        return False

    async def initialize(self):
        await self.bot.wait_until_red_ready()
        restart_channel = await self.config.restart_channel_for_redboot()
        restart_channel = self.bot.get_channel(restart_channel)
        with contextlib.suppress(discord.Forbidden):
            await restart_channel.send(f"{self.bot.user.name} is back online.")
        await self.config.restart_channel_for_redboot.clear()

    @commands.is_owner()
    @commands.command()
    async def restart(self, ctx: commands.Context):
        """Attempts to restart [botname]."""
        restart_message = await self.config.restart_message()
        restart_conf = await self.config.confirm_restart()
        message = self.var_formatter(ctx, restart_message)
        if restart_conf:
            conf = await self.confirmation(ctx, "restart")
        if not restart_conf or conf:
            await ctx.send(message)
            log.info(f"{ctx.me.name} was restarted by {ctx.author} ({now})")
            await self.config.restart_channel_for_redboot.set(ctx.channel.id)
            return await self.bot.shutdown(restart=True)
        else:
            await ctx.send("I will not be restarting.")

    @commands.is_owner()
    @commands.command()
    async def shutdown(self, ctx: commands.Context):
        """Shuts down [botname]."""
        shutdown_message = await self.config.shutdown_message()
        shutdown_conf = await self.config.confirm_shutdown()
        message = self.var_formatter(ctx, shutdown_message)
        if shutdown_conf:
            conf = await self.confirmation(ctx, "shutdown")
        if not shutdown_conf or conf:
            await ctx.send(message)
            log.info(f"{ctx.me.name} was shutdown by {ctx.author} ({now})")
            return await self.bot.shutdown(restart=False)
        else:
            await ctx.send("I will not be shutting down.")

    @commands.group()
    @commands.is_owner()
    async def terminoset(self, ctx: commands.Context):
        """Settings for the shutdown and restart commands."""

    @terminoset.group(name="shut", aliases=["shutdown"], invoke_without_command=True)
    async def terminoset_shutdown(self, ctx: commands.Context, *, shutdown_message: str):
        """
        Set and adjust the shutdown message.

        You can use `{author}` in your message to send the invokers display name."""
        await ctx.invoke(self.terminoset_shutdown_message, shutdown_message=shutdown_message)

    @terminoset_shutdown.command(name="conf")
    async def terminoset_shutdown_conf(self, ctx: commands.Context, true_or_false: bool):
        """Toggle whether shutdowns confirm before shutting down."""
        await self.config.confirm_shutdown.set(true_or_false)
        grammar = "not" if not true_or_false else "now"
        await ctx.send(f"Shutdowns will {grammar} confirm before shutting down.")

    @terminoset_shutdown.command(name="message", hidden=True)
    async def terminoset_shutdown_message(self, ctx: commands.Context, *, shutdown_message: str):
        """Set the shutdown message."""
        await self.config.shutdown_message.set(shutdown_message)
        await ctx.send("Shutdown message set.")

    @terminoset.group(name="res", aliases=["restart"], invoke_without_command=True)
    async def terminoset_restart(self, ctx: commands.Context, *, restart_message: str):
        """
        Set and adjust the restart message.

        You can use `{author}` in your message to send the invokers display name."""
        await ctx.invoke(self.terminoset_restart_message, restart_message=restart_message)

    @terminoset_restart.command(name="conf")
    async def terminoset_restart_conf(self, ctx: commands.Context, true_or_false: bool):
        """Toggle whether restarts confirm before restarting."""
        await self.config.confirm_restart.set(true_or_false)
        grammar = "not" if not true_or_false else "now"
        await ctx.send(f"Restarts will {grammar} confirm before shutting down.")

    @terminoset_restart.command(name="message", hidden=True)
    async def terminoset_restart_message(self, ctx: commands.Context, *, restart_message: str):
        """Set the restart message."""
        await self.config.restart_message.set(restart_message)
        await ctx.send("Restart message set.")

    @terminoset.command()
    async def settings(self, ctx: commands.Context):
        """See the current settings for termino."""
        config = await self.config.all()
        footer = False
        for x in [config["restart_message"], config["shutdown_message"]]:
            if "{author}" in x:
                footer = True
        message = (
            f"Shutdown message: {config['shutdown_message']}\n"
            f"Shutdown confirmation: {config['confirm_shutdown']}\n\n"
            f"Restart message: {config['restart_message']}\n"
            f"Restart confirmation: {config['confirm_restart']}\n\n"
        )
        if footer:
            message += "{author} will be replaced with the display name of the invoker."
        for page in pagify(message, delims=["\n"]):
            await ctx.send(box(page, lang="yaml"))


def setup(bot):
    cog = Termino(bot)
    global shutdown
    global restart
    shutdown = bot.get_command("shutdown")
    restart = bot.get_command("restart")
    if shutdown:
        bot.remove_command(shutdown.name)
    if restart:
        bot.remove_command(restart.name)
    bot.add_cog(cog)
