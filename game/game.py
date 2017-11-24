import json
import os
import random
from collections import defaultdict

import discord
import requests
from discord.ext import commands
from redbot.core import Config, checks
from redbot.core.json_io import JsonIO
from redbot.core.utils.chat_formatting import box, pagify, question, warning


class Game:
    def __init__(self, bot):
        self.config = Config.get_conf(self, identifier=28784542245, force_registration=True)

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

        group = self.config.member(ctx.author)
        await ctx.send(group.all)

        # Check if a subcommand has been passed or not
        if ctx.invoked_subcommand is None:
            suggestions = get_suggestions(get_users(ctx))

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
    async def add(self, ctx, game):
        """
        Add a game to your game list

        game: Name of the game
        """

        user = ctx.author

        if add(game, user.id):
            await ctx.send("{}, {} was added to your library.".format(user.mention, game))
        else:
            await ctx.send("{}, you already have this game in your library.".format(user.mention))

    @game.command()
    @checks.admin_or_permissions(manage_messages=True)
    async def addto(self, ctx, game, user):
        """
        (Admin) Add a game to any user's game list

        game: Name of the game
        user: The user's library into which the game should be added
        """

        if add(game, user.id):
            await ctx.send("{} was added to {}'s' library.".format(game, user.nick))
        else:
            await ctx.send("{} already has this game in their library.".format(user.nick))

    @game.command()
    async def remove(self, ctx, game):
        """
        Remove a game from your game list

        game: Name of the game
        """

        user = ctx.author

        if remove(game, user.id):
            await ctx.send("{}, {} was removed from your library.".format(user.mention, game))
        else:
            await ctx.send("{}, you do not have this game in your library.".format(user.mention))

    @game.command()
    @checks.admin_or_permissions(manage_messages=True)
    async def removefrom(self, ctx, game, user):
        """
        (Admin) Remove a game from the given user's game list

        game: Name of the game
        user: The user's library from which to remove the game
        """

        if remove(game, user.id):
            await ctx.send("{} was removed from {}'s' library.".format(game, user.nick))
        else:
            await ctx.send("{} does not have this game in their library.".format(user.nick))

    @game.command()
    async def removelib(self, ctx):
        "Delete your library"

        user = ctx.author

        await ctx.send(warning("Are you sure you want to delete your library? (yes/no)"))
        response = await self.bot.wait_for_message(author=user, timeout=15, check=check_response)

        if response:
            response = response.content.strip().lower()

            if response in "yes":
                delete_key(user.id)
                await ctx.send("{}, you are way out of this league.".format(user.mention))
            elif response in "no":
                await ctx.send("Well, that was close!")
        else:
            await ctx.send("Yeah, that's what I thought.")

    @game.command()
    @checks.admin_or_permissions(manage_messages=True)
    async def removeuser(self, ctx, user: discord.Member):
        """
        (Admin) Delete another user's library

        user: The user whose library should be deleted
        """

        if check_key(user.id):
            delete_key(user.id)
            await ctx.send("{}, you are way out of this league.".format(user.mention))
        else:
            await ctx.send("That user does not exist in this league.")

    @game.command()
    async def check(self, ctx, game, user: discord.Member=None):
        """
        Check if a game exists in a user's library (or all users' libraries)

        game: Name of the game
        user: (Optional) If given, check the user's library, otherwise check all user libraries
        """

        game_list = get_library()

        # Check if a user has the game
        if user:
            if not check_key(user.id):
                await ctx.send("{} does not have a game library yet. Use {}help game to start adding games!".format(user.nick, ctx.prefix))
                return

            user_game_list = get_library(user.id)

            if game in user_game_list:
                await ctx.send("Aye {}, you have {} in your library.".format(user.mention, game))
            else:
                await ctx.send("Nay {}, you do not have that game in your library.".format(user.mention))
            return

        users_with_games = []

        # Check which users have the game
        for discord_id, user_details in game_list.items():
            if game in user_details["games"]:
                user = ctx.message.guild.get_member(discord_id)
                if user:
                    users_with_games.append(user.nick or user.name)

        if not users_with_games:
            await ctx.send("None of you have {}!".format(game))
        else:
            await ctx.send("The following of you have {}: {}".format(game, box("\n".join(users_with_games))))

    @game.command()
    async def list(self, ctx, user: discord.Member=None):
        """
        Print out a user's game list (sends as a DM)

        user: (Optional) If given, list a user's game library, otherwise list the message user's library
        """

        author = ctx.author

        if not user:
            user = author

        game_list = get_library()

        if check_key(user.id) and game_list.get(user.id).get("games", False):
            user_game_list = get_library(user.id)

            message = pagify(", ".join(sorted(user_game_list)), [', '])

            await ctx.send("Please check your DM for the full list of games, {}.".format(author.mention))
            await self.bot.send_message(author, "{}'s games:".format(user.mention))

            for page in message:
                await self.bot.send_message(author, (box(page)))
        else:
            await ctx.send("{}, you do not have any games. Add one using `{p}game add <game_name>` and/or link your Steam profile with `{p}game steamlink <steam_id>`.".format(user.mention, p=ctx.prefix))

    @game.command()
    async def suggest(self, ctx, choice=None):
        """
        List out games common to all online users (or users in voice channels)

        choice: (Optional) Either 'online' (for all online users; excluding users with 'dnd' status) or 'voice' (for all users in a voice channel))
        """

        if choice is None or choice.lower() in ("online", "voice"):
            suggestions = get_suggestions(get_users(ctx, choice))

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
            suggestions = get_suggestions(get_users(ctx, choice))

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
        await ctx.send("Steam key: {}".format("True" if self.config.steamkey() else "False"))
        await ctx.send("The Steam API key has been successfully added! Delete the previous message for your own safety!")

    @game.command()
    async def steamlink(self, ctx, steam_id, user: discord.Member=None):
        """
        Link a Steam profile with a Discord ID

        steam_id: Steam Name (found in your Custom URL -> steamcommunity.com/id/<name>) or Steam ID (64-bit ID -> steamcommunity.com/profiles/<id>)
        user: (Optional) If given, link library to user, otherwise default to user of the message
        """

        if not user:
            user = ctx.author

        game_list = get_library()

        # Either use given 64-bit Steam ID, or convert given name to a 64-bit Steam ID
        try:
            int(steam_id)
        except ValueError:
            key = get_steam_key()

            if key:
                url = "https://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001/?key={key}&vanityurl={id}&format=json".format(
                    key=key, id=steam_id)
                r = requests.get(url)
                response = json.loads(r.text).get('response')

                if response.get('success') == 1:
                    game_list[user.id]["steam_name"] = steam_id
                    game_list[user.id]["steam_id"] = response.get('steamid')
                else:
                    await ctx.send("{}, there was a problem linking your Steam name. Please try again with your 64-bit Steam ID instead.".format(user.mention))
                    return
            else:
                await ctx.send("Sorry, you need a Steam API key to make requests to Steam. Use `{}game steamkey` for more information.".format(ctx.prefix))
                return
        else:
            game_list[user.id]["steam_id"] = steam_id
        finally:
            JsonIO._save_json("data/game/games.json", game_list)

        await ctx.send("{}'s account has been linked with Steam.".format(user.mention))

        # Update the user's Steam games with their permission
        await ctx.send(question("Do you want to update your library with your Steam games? (yes/no)"))
        response = await self.bot.wait_for_message(author=user, timeout=15, check=check_response)

        if response:
            response = response.content.strip().lower()

            if response in "yes":
                set_steam_games(game_list[user.id]["steam_id"], user.id)
                await ctx.send("{}, your Steam games have been updated!".format(user.mention))
            elif response in "no":
                await ctx.send("Fair enough. If you would like to update your games later, please run `{}game update`.".format(ctx.prefix))
        else:
            await ctx.send("Too late, but you can still use `{}game update` to update your games.".format(ctx.prefix))

    @game.command()
    async def update(self, ctx, user: discord.Member=None):
        """
        Update a user's Steam game library

        user: If given, update the user's Steam games, otherwise default to user of the message
        """

        if not user:
            user = ctx.author

        steam_id = get_user_steam_id(user.id)
        key = get_steam_key()

        if not steam_id:
            await ctx.send("{}, your Discord ID is not yet connected to a Steam profile. Use `{}game steamlink` to link them.".format(user.mention, ctx.prefix))
            return

        if key:
            set_steam_games(steam_id, user.id)
            await ctx.send("{}, your Steam games have been updated!".format(user.mention))
        else:
            await ctx.send("Sorry, you need a Steam API key to make requests to Steam. Use `{}game steamkey` for more information.".format(ctx.prefix))


def get_library(discord_id=None):
    games_list = JsonIO._load_json("data/game/games.json")

    if discord_id:
        return games_list.get(discord_id).get("games")
    else:
        return defaultdict(dict, games_list)


def add(game, discord_id):
    game_list = get_library()

    if check_key(discord_id):
        user_game_list = get_library(discord_id)

        if user_game_list:
            if game in user_game_list:
                return False
            else:
                game_list[discord_id]["games"].append(game)
        else:
            game_list[discord_id]["games"] = [game]
    else:
        create_key(discord_id)

        # Refresh game_list object with the new discord_id
        game_list = get_library()
        game_list[discord_id]["games"].append(game)

    JsonIO._save_json("data/game/games.json", game_list)
    return True


def remove(game, discord_id):
    game_list = get_library()

    if check_key(discord_id):
        user_game_list = get_library(discord_id)

        if game not in user_game_list:
            return False
        else:
            game_list[discord_id]["games"].remove(game)
            JsonIO._save_json("data/game/games.json", game_list)
            return True
    else:
        create_key(discord_id)
        return False


def set_steam_key(key):
    settings = JsonIO._load_json("data/game/settings.json")
    settings["steam_key"] = key
    JsonIO._save_json("data/game/settings.json", settings)


def get_steam_key():
    settings = JsonIO._load_json("data/game/settings.json")
    return settings.get("steam_key", False)


def get_user_steam_id(discord_id):
    ids = JsonIO._load_json("data/game/games.json")
    return ids.get(discord_id).get("steam_id", False)


def get_steam_games(steam_id):
    key = get_steam_key()

    if key:
        url = "https://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key={key}&steamid={id}&include_appinfo=1&format=json".format(
            key=key, id=steam_id)
        r = requests.get(url)
        games = [game.get('name') for game in json.loads(
            r.text).get('response').get('games')]
        return games
    else:
        return False


def set_steam_games(steam_id, discord_id):
    steam_games = get_steam_games(steam_id)

    if steam_games:
        game_list = get_library()
        user_game_list = game_list.get(discord_id).get("games")

        if user_game_list:
            user_game_list.extend(steam_games)
        else:
            user_game_list = steam_games

        game_list[discord_id]["games"] = list(set(user_game_list))
        JsonIO._save_json("data/game/games.json", game_list)
    else:
        return False


def create_key(discord_id):
    game_list = get_library()
    game_list[discord_id]["games"] = []
    JsonIO._save_json("data/game/games.json", game_list)


def check_key(discord_id):
    game_list = get_library()

    if discord_id in game_list:
        return True
    else:
        return False


def delete_key(discord_id):
    game_list = get_library()

    if discord_id in game_list:
        del game_list[discord_id]
        JsonIO._save_json("data/game/games.json", game_list)


def check_category(id):
    return True
    # url = "http://store.steampowered.com/api/appdetails?appids={id}".format(id=id)
    # r = requests.get(url)
    # data = json.loads(r.text)
    # if data.get('success'):
    #   categories = [game.get('id') for game in data.get(str(id)).get('data').get('categories')]
    #   mp_categories = [1, 9]
    #   return any(category in categories for category in mp_categories)
    # else:
    #   return False


def get_suggestions(users):
    if not users:
        return

    users_game_list = [get_library(user) for user in users]

    # Sometimes there are some None...
    users_game_list = list(filter(None.__ne__, users_game_list))

    if users_game_list:
        suggestions = set(users_game_list[0]).intersection(
            *users_game_list[1:])
        return sorted(list(suggestions))


def get_users(ctx, choice=None):

    users = []

    if choice is None or choice.lower == "online":
        for user in ctx.message.guild.members:
            if user.status.name in ("idle", "online") and not user.bot:
                users.append(user.id)
    elif choice.lower() == "voice":
        for channel in ctx.message.guild.channels:
            for user in channel.voice_members:
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


def check_response(message):
    if message.content.strip().lower() in ("y", "n", "yes", "no"):
        return True


def check_folders():
    if not os.path.exists("data/game"):
        print("Creating data/game folder...")
        os.makedirs("data/game")


# def check_files():
#     f = "data/game/games.json"
#     if not JsonIO.is_valid_json(f):
#         print("Creating an empty games.json file...")
#         JsonIO._save_json(f, defaultdict(dict))

#     f = "data/game/settings.json"
#     if not JsonIO.is_valid_json(f):
#         print("Creating the default settings.json file...")
#         JsonIO._save_json(f, {})


def setup(bot):
    # check_folders()
    # check_files()
    bot.add_cog(Game(bot))
