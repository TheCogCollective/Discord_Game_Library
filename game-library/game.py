import asyncio
import json
import os
import random
import requests
from collections import defaultdict

import discord
from redbot.core.config import Config
from redbot.core import commands, checks
from redbot.core.utils.chat_formatting import box, pagify, question, warning
from redbot.core.utils.mod import check_permissions
from redbot.core.utils.predicates import MessagePredicate


class MemberNotInVoiceChannelError(Exception):
    pass


class Game(commands.Cog):
    def __init__(self, bot):
        self.config = Config.get_conf(
            self, identifier=28784542245, force_registration=True)

        default_global = {
            "steamkey": ""
        }
        default_user = {
            "games": [],
            "steam_id": "",
            "steam_name": ""
        }

        self.config.register_global(**default_global)
        self.config.register_user(**default_user)
        self.bot = bot

    @commands.group(name="game")
    async def game(self, ctx):
        "Get a random game common to all online users (excluding 'dnd' users)"

        # Check if a subcommand has been passed or not
        if ctx.invoked_subcommand is None:
            users = await self.get_users(ctx)
            suggestions = await self.get_suggestions(users)

            if suggestions:
                await ctx.send("Let's play some {}!".format(random.choice(suggestions)))
            else:
                await ctx.send("""
                You do not have any games, go get some!

                Once you do, you can either add them directly (`add`) or link your Steam profile (`steamlink`) by:

                1. `{p}game add <game>`
                2. `{p}game steamlink <steam_id>` (or your steam name if you have a custom URL at steamcommunity.com/id/<name>)

                Use `{p}help game` to get a full list of commands that are available to you.
                """.format(p=ctx.prefix))

    @game.command()
    async def add(self, ctx, game, user: discord.Member = None):
        """
        Add a game to your game list

        game: Name of the game
        """

        if user and not await check_permissions(ctx, {"manage_messages": True}):
            await ctx.send("You don't have the permissions to do this action")
            return

        if not user:
            user = ctx.author

        games = await self.config.user(user).games()
        if not game in games:
            games.append(game)
            await self.config.user(user).games.set(games)
            await ctx.send("{}, {} was added to your library.".format(user.mention, game))
        else:
            await ctx.send("{}, you already have this game in your library.".format(user.mention))

    @game.command()
    async def remove(self, ctx, game, user: discord.Member = None):
        """
        Remove a game from your game list

        game: Name of the game
        """
        if user and not await check_permissions(ctx, {"manage_messages": True}):
            await ctx.send("You don't have the permissions to do this action")
            return

        if not user:
            user = ctx.author

        games = await self.config.user(user).games()
        if game in games:
            games.remove(game)
            await self.config.user(user).games.set(games)
            await ctx.send("{}, {} was removed from your library.".format(user.mention, game))
        else:
            await ctx.send("{}, you don't have this game in your library.".format(user.mention))

    @game.command()
    async def destroy(self, ctx, user: discord.Member = None):
        """
        Delete your entire game library from this server

        Args:
            user (Optional) If given, destroy a user's game library, otherwise destroy the message user's library
        """

        if user and not await check_permissions(ctx, {"manage_messages": True}):
            await ctx.send("You don't have the permissions to do this action")
            return

        if not user:
            user = ctx.author

        await ctx.send(warning("Are you sure? (yes/no)"))

        try:
            response = await self.bot.wait_for('message', timeout=15, check=MessagePredicate.yes_or_no(ctx))
        except asyncio.exceptions.TimeoutError:
            await ctx.send("Yeah, that's what I thought.")
        else:
            response = response.content.strip().lower()

            if response in "yes":
                await self.config.user(user).games.set([])
                await ctx.send("{}, your game library has been nuked".format(user.mention))
            elif response in "no":
                await ctx.send("Well, that was close!")

    @game.command()
    async def check(self, ctx, game, user: discord.Member = None):
        """
        Check if a game exists in a user's library (or all users' libraries)

        game: Name of the game
        user: (Optional) If given, check the user's library, otherwise check all user libraries
        """

        # Check if a user has the game
        if user:
            games = await self.config.user(user).games()
            if not games:
                await ctx.send("{} does not have a game library yet. Use {}help game to start adding games!".format(user.mention, ctx.prefix))
                return

            if game in games:
                await ctx.send("Aye {}, you have {} in your library.".format(user.mention, game))
            else:
                await ctx.send("Nay {}, you do not have that game in your library.".format(user.mention))
            return

        users_with_games = []

        # Check which users have the game
        all_users = await self.config.all_users()
        for discord_id, user_data in all_users.items():
            if game in user_data.get("games"):
                user = ctx.message.guild.get_member(discord_id)
                if user:
                    users_with_games.append(user.nick or user.name)

        if not users_with_games:
            await ctx.send("None of you have {}!".format(game))
        else:
            await ctx.send("The following of you have {}: {}".format(game, box("\n".join(users_with_games))))

    @game.command()
    async def list(self, ctx, user: discord.Member = None):
        """
        Print out a user's game list (sends as a DM)

        user: (Optional) If given, list a user's game library, otherwise list the message user's library
        """

        author = ctx.author

        if not user:
            user = author

        game_list = await self.config.user(user).games()

        if game_list:
            message = pagify(", ".join(sorted(game_list)), [', '])
            await ctx.send("Please check your DM for the full list of games, {}.".format(author.mention))
            await author.send("{}'s games:".format(user.mention))

            for page in message:
                await author.send((box(page)))
        else:
            await ctx.send("{}, you do not have any games. Add one using `{p}game add <game_name>` and/or link your Steam profile with `{p}game steamlink <steam_id>`.".format(user.mention, p=ctx.prefix))

    @game.command()
    async def suggest(self, ctx, choice=None):
        """
        List out games common to all online users (or users in voice channels)

        choice: (Optional) Either 'online' (for all online users; excluding users with 'dnd' status) or 'voice' (for all users in a voice channel))
        """

        if choice is None or choice.lower() in ("online", "voice"):
            try:
                users = await self.get_users(ctx, choice)
            except MemberNotInVoiceChannelError:
                await ctx.send("You need to be in a voice channel for this to work")
                return
            if len(users) <= 1:
                await ctx.send("Yeah, you need more than one person online for this to work")
                return
            suggestions = await self.get_suggestions(users)

            if suggestions:
                await ctx.send("You can play these games: \n")
                message = pagify("\n".join(suggestions), ['\n'])

                for page in message:
                    await ctx.send(box(page))
            else:
                await ctx.send("You have exactly **zero** games in common, go buy a 4-pack!")
        else:
            await ctx.send("Please enter a valid filter -> either use `online` (default) for all online users or `voice` for all users in a voice channel")

    @game.command()
    async def poll(self, ctx, choice=None):
        """
        Poll from the common games of all online users (or users in voice channels)

        choice: (Optional) Either 'online' (for all online users; excluding users with 'dnd' status) or 'voice' (for all users in a voice channel))
        """

        if choice is None or choice.lower() in ("online", "voice"):
            users = await self.get_users(ctx, choice)
            suggestions = await self.get_suggestions(users)

            if suggestions:
                poll_id = create_strawpoll("What to play?", suggestions)

                if poll_id:
                    await ctx.send("Here's your strawpoll link: https://www.strawpoll.me/{}".format(poll_id))
                else:
                    await ctx.send("Phew! You have way too many games to create a poll. You should try `{}game suggest` instead.".format(ctx.prefix))
            else:
                await ctx.send("You have exactly **zero** games in common, go buy a 4-pack!")
        else:
            await ctx.send("Please enter a valid filter -> either use `online` (default) for all online users or `voice` for all users in a voice channel")

    @game.command()
    async def steamkey(self, ctx, key):
        """
        (One-time setup) Set the Steam API key to use `steamlink` and `update` commands

        key: An API key generated at https://steamcommunity.com/dev/apikey (login with your Steam profile and enter any domain to create one)
        """

        await self.config.steamkey.set(key)
        await ctx.send("Steam key: {}".format("True" if await self.config.steamkey() else "False"))
        await ctx.send("The Steam API key has been successfully added! Delete the previous message for your own safety!")

    @game.command()
    async def steamlink(self, ctx, steam_id, user: discord.Member = None):
        """
        Link a Steam profile with a Discord ID

        steam_id: Steam Name (found in your Custom URL -> steamcommunity.com/id/<name>) or Steam ID (64-bit ID -> steamcommunity.com/profiles/<id>)
        user: (Optional) If given, link library to user, otherwise default to user of the message
        """

        if not user:
            user = ctx.author

        game_list = []

        # Either use given 64-bit Steam ID, or convert given name to a 64-bit Steam ID
        try:
            int(steam_id)
        except ValueError:
            key = await self.config.steamkey()

            if key:
                url = "https://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001/?key={key}&vanityurl={id}&format=json".format(
                    key=key, id=steam_id)
                r = requests.get(url)
                response = json.loads(r.text).get('response')

                if not response.get('success') == 1:
                    await ctx.send("{}, there was a problem linking your Steam name. Please try again with your 64-bit Steam ID instead.".format(user.mention))
                    return
                else:
                    steam_id = await self.config.user(user).steam_id.set(response.get("steamid"))
            else:
                await ctx.send("Sorry, you need a Steam API key to make requests to Steam. Use `{}game steamkey` for more information.".format(ctx.prefix))
                return

        game_list = await self.get_steam_games(user)
        await self.config.user(user).games.set(game_list)
        await ctx.send("{}'s account has been linked with Steam.".format(user.mention))

    @game.command()
    async def update(self, ctx, user: discord.Member = None):
        """
        Update a user's Steam game library

        user: If given, update the user's Steam games, otherwise default to user of the message
        """

        if user and not await check_permissions(ctx, {"manage_messages": True}):
            await ctx.send("You don't have the permissions to do this action")
            return

        if not user:
            user = ctx.author

        steam_id = await self.config.user(user).steam_id()

        if not steam_id:
            await ctx.send("{}, your Discord ID is not yet connected to a Steam profile. Use `{}game steamlink` to link them.".format(user.mention, ctx.prefix))
            return

        updated_games = await self.get_steam_games(user)
        if not updated_games:
            await ctx.send("Sorry, you need a Steam API key to make requests to Steam. Use `{}game steamkey` for more information.".format(ctx.prefix))
            return

        current_games = await self.config.user(user).games()
        current_games.extend(updated_games)
        await self.config.user(user).games.set(list(set(current_games)))
        await ctx.send("{}, your Steam games have been updated!".format(user.mention))

    async def get_steam_games(self, user):
        key = await self.config.steamkey()
        steam_id = await self.config.user(user).steam_id()

        if key:
            url = "https://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key={key}&steamid={id}&include_appinfo=1&format=json".format(
                key=key, id=steam_id)
            r = requests.get(url)
            games = [game.get('name') for game in json.loads(
                r.text).get('response').get('games')]
            return games
        else:
            return False

    async def get_suggestions(self, users):
        if not users:
            return

        all_user_data = await self.config.all_users()
        users_game_list = [all_user_data.get(user).get("games") for user in users]

        # Sometimes there are some None...
        users_game_list = list(filter(None.__ne__, users_game_list))

        if users_game_list:
            suggestions = set(users_game_list[0]).intersection(
                *users_game_list[1:])
            return sorted(list(suggestions))

    async def get_users(self, ctx, choice=None):
        users = []
        if choice is None or choice.lower == "online":
            for user in ctx.message.guild.members:
                if user.status.name in ("idle", "online") and not user.bot:
                    users.append(user.id)
        elif choice.lower() == "voice":
            current_channel = ctx.author.voice
            if not current_channel:
                raise MemberNotInVoiceChannelError()
            for user in current_channel.channel.members:
                if not user.bot:
                    users.append(user.id)
        return users


def create_strawpoll(title, options):
    data = {
        "captcha": "false",
        "dupcheck": "normal",
        "multi": "true",
        "title": title,
        "options": options
    }
    resp = requests.post('https://www.strawpoll.me/api/v2/polls',
                         headers={'content-type': 'application/json'}, json=data)
    try:
        return json.loads(resp.text)['id']
    except:
        return False
