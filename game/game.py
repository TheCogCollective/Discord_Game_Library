import json
import os
import random

import discord
import requests
from cogs.utils import checks
from cogs.utils.chat_formatting import box, pagify, question, warning
from cogs.utils.dataIO import dataIO
from discord.ext import commands


class Game:
    def __init__(self, bot):
        self.bot = bot

    @commands.group(name="game", pass_context=True)
    async def game(self, ctx):
        "Get a random game common to all online users"

        # Check if a subcommand has been passed or not
        if ctx.invoked_subcommand is None:
            suggestions = get_suggestions(get_users(ctx))

            if suggestions:
                await self.bot.say("Let's play some {}!".format(random.choice(suggestions)))
            else:
                await self.bot.say("""
                You do not have any games, go get some!

                Once you do, you can either add them directly (`add`) or link your Steam profile (`steamlink`) by:

                1. `{p}game add <game>`
                2. `{p}game steamlink <steam_id>` (or your steam name if you have a custom URL at steamcommunity.com/id/<name>)

                Use `{p}help game` to get a full list of commands that are available to you.
                """.format(p=ctx.prefix))

    @game.command(pass_context=True)
    async def add(self, ctx, game):
        """
        Add a game to your game list

        game: Name of the game
        """

        user = ctx.message.author

        if add(game, user.id):
            await self.bot.say("{}, {} was added to your library.".format(user.mention, game))
        else:
            await self.bot.say("{}, you already have this game in your library.".format(user.mention))

    @game.command(pass_context=True)
    @checks.admin_or_permissions(manage_messages=True)
    async def addto(self, ctx, game, user):
        """
        (Admin) Add a game to any user's game list

        game: Name of the game
        user: The user's library into which the game should be added
        """

        if add(game, user.id):
            await self.bot.say("{} was added to {}'s' library.".format(game, user.nick))
        else:
            await self.bot.say("{} already has this game in their library.".format(user.nick))

    @game.command(pass_context=True)
    async def remove(self, ctx, game):
        """
        Remove a game from your game list

        game: Name of the game
        """

        user = ctx.message.author

        if remove(game, user.id):
            await self.bot.say("{}, {} was removed from your library.".format(user.mention, game))
        else:
            await self.bot.say("{}, you do not have this game in your library.".format(user.mention))

    @game.command(pass_context=True)
    @checks.admin_or_permissions(manage_messages=True)
    async def removefrom(self, ctx, game, user):
        """
        (Admin) Remove a game from the given user's game list

        game: Name of the game
        user: The user's library from which to remove the game
        """

        if remove(game, user.id):
            await self.bot.say("{} was removed from {}'s' library.".format(game, user.nick))
        else:
            await self.bot.say("{} does not have this game in their library.".format(user.nick))

    @game.command(pass_context=True)
    async def removelib(self, ctx):
        "Delete your library"

        user = ctx.message.author

        await self.bot.say(warning("Are you sure you want to delete your library? (yes/no)"))
        response = await self.bot.wait_for_message(author=user, timeout=15, check=check_response)

        if response:
            response = response.content.strip().lower()

            if response in "yes":
                delete_key(user.id)
                await self.bot.say("{}, you are way out of this league.".format(user.mention))
            elif response in "no":
                await self.bot.say("Well, that was close!")
        else:
            await self.bot.say("Yeah, that's what I thought.")

    @game.command(pass_context=True)
    @checks.admin_or_permissions(manage_messages=True)
    async def removeuser(self, ctx, user: discord.Member):
        """
        (Admin) Delete another user's library

        user: The user whose library should be deleted
        """

        if check_key(user.id):
            delete_key(user.id)
            await self.bot.say("{}, you are way out of this league.".format(user.mention))
        else:
            await self.bot.say("That user does not exist in this league.")

    @game.command(pass_context=True)
    async def check(self, ctx, game, user: discord.Member=None):
        """
        Check if a game exists in a user's library (or all users' libraries)

        game: Name of the game
        user: (Optional) If given, check the user's library, otherwise check all user libraries
        """

        game_list = get_games()

        # Check if a user has the game
        if user:
            if game in game_list[user.id]:
                await self.bot.say("Aye {}, you have {} in your library.".format(user.mention, game))
            else:
                await self.bot.say("Nay {}, you do not have that game in your library.".format(user.mention))
            return

        users_with_games = []

        # Check which users have the game
        for userid, games in game_list.items():
            if game in games:
                player = ctx.message.server.get_member(userid)
                if player:
                    users_with_games.append(player.nick or player.name)

        if not users_with_games:
            await self.bot.say("None of you have {}!".format(game))
        else:
            await self.bot.say("The following of you have {}: {}".format(game, box("\n".join(users_with_games))))

    @game.command(pass_context=True)
    async def list(self, ctx, user: discord.Member=None):
        """
        Print out a user's game list (sends as a DM)

        user: (Optional) If given, list a user's game library, otherwise list the message user's library
        """

        author = ctx.message.author

        if not user:
            user = author

        game_list = get_games()

        if check_key(user.id) and game_list.get(user.id, False):
            message = pagify(", ".join(sorted(game_list[user.id])), [', '])

            await self.bot.say("Please check your DM for the full list of games, {}.".format(author.mention))
            await self.bot.send_message(author, "{}'s games:".format(user.mention))

            for page in message:
                await self.bot.send_message(author, (box(page)))
        else:
            await self.bot.say("{}, you do not have any games. Add one using `{p}game add <game_name>` and/or link your Steam profile with `{p}game steamlink <steam_id>`.".format(user.mention, p=ctx.prefix))

    @game.command(pass_context=True)
    async def suggest(self, ctx, choice=None):
        """
        List out games common to all online users (or users in voice channels)

        choice: (Optional) Either 'online' (for all online users; excluding users with 'dnd' status) or 'voice' (for all users in a voice channel))
        """

        if choice is None or choice.lower() in ("online", "voice"):
            suggestions = get_suggestions(get_users(ctx, choice))

            if suggestions:
                await self.bot.say("You can play these games: \n")
                message = pagify("\n".join(suggestions), ['\n'])

                for page in message:
                    await self.bot.say(box(page))
            else:
                await self.bot.say("You have exactly **zero** games in common, go buy a 4-pack!")
        else:
            await self.bot.say("Please enter a valid filter -> either use `online` (default) for all online users or `voice` for all users in a voice channel")

    @game.command(pass_context=True)
    async def poll(self, ctx, choice=None):
        """
        Poll from the common games of all online users (or users in voice channels)

        choice: (Optional) Either 'online' (for all online users; excluding users with 'dnd' status) or 'voice' (for all users in a voice channel))
        """

        if choice is None or choice.lower() in ("online", "voice"):
            suggestions = get_suggestions(get_users(ctx, choice))

            if suggestions:
                id = create_strawpoll("What to play?", suggestions)
                if id:
                    await self.bot.say("Here's your strawpoll link: https://www.strawpoll.me/{}".format(id))
                else:
                    await self.bot.say("Phew! You have way too many games to create a poll. You should try `{}game suggest` instead.".format(ctx.prefix))
            else:
                await self.bot.say("You have exactly **zero** games in common, go buy a 4-pack!")
        else:
            await self.bot.say("Please enter a valid filter -> either use `online` (default) for all online users or `voice` for all users in a voice channel")

    @game.command(pass_context=True)
    async def steamlink(self, ctx, id, user: discord.Member=None):
        """
        Link a Steam profile with a Discord ID

        id: Steam Name (found in your Custom URL -> steamcommunity.com/id/<name>) or Steam ID (64-bit ID -> steamcommunity.com/profiles/<id>)
        user: (Optional) If given, link library to user, otherwise default to user of the message
        """

        if not user:
            user = ctx.message.author

        ids = get_steam_ids()

        try:
            id = int(id)
            ids[user.id] = id
        except:
            url = "https://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001/?key=key&vanityurl={id}&format=json".format(
                id=id)
            r = requests.get(url)
            response = json.loads(r.text).get('response')

            if response.get('success') == 1:
                ids[user.id] = response.get('steamid')
            else:
                await self.bot.say("{}, there was a problem linking your Steam name. Please try again with your 64-bit Steam ID instead.".format(user.mention))

        dataIO.save_json("data/game/steamids.json", ids)

        if not check_key(user.id):
            game_list = get_games()
            game_list[user.id] = None
            dataIO.save_json("data/game/games.json", game_list)

        await self.bot.say("{}'s account has been linked with Steam.".format(user.mention))

        # Update the user's Steam games with their permission
        await self.bot.say(question("Do you want to update your library with your Steam games? (yes/no)"))
        response = await self.bot.wait_for_message(author=user, timeout=15, check=check_response)

        if response:
            response = response.content.strip().lower()

            if response in "yes":
                set_steam_games(ids[user.id], user.id)
                await self.bot.say("{}, your Steam games have been updated!".format(user.mention))
            elif response in "no":
                await self.bot.say("Fair enough. If you would like to update your games later, please run `{}game update`.".format(ctx.prefix))
        else:
            await self.bot.say("Too late, but you can still use `{}game update` to update your games.".format(ctx.prefix))

    @game.command(pass_context=True)
    async def update(self, ctx, user: discord.Member=None):
        """
        Update a user's Steam game library

        user: If given, update the user's Steam games, otherwise default to user of the message
        """

        if not user:
            user = ctx.message.author

        id = get_user_steam_id(user.id)

        if not id:
            await self.bot.say("{}, your Discord ID is not yet linked with a Steam ID.".format(user.mention))
            return

        set_steam_games(id, user.id)

        await self.bot.say("{}, your Steam games have been updated!".format(user.mention))


def check_response(message):
    if message.content.strip().lower() in ("y", "n", "yes", "no"):
        return True


def add(game, userid):
    game_list = get_games()

    if check_key(userid):
        if game_list[userid]:
            if game in game_list[userid]:
                return False
            else:
                game_list[userid].append(game)
        else:
            game_list[userid] = [game]
    else:
        create_key(userid)
        game_list[userid] = [game]

    dataIO.save_json("data/game/games.json", game_list)
    return True


def remove(game, userid):
    game_list = get_games()

    if check_key(userid):
        if game not in game_list[userid]:
            return False
        else:
            game_list[userid].remove(game)
            dataIO.save_json("data/game/games.json", game_list)
            return True
    else:
        create_key(userid)
        return False


def get_steam_ids():
    return dataIO.load_json("data/game/steamids.json")


def get_user_steam_id(userid):
    ids = get_steam_ids()
    return ids.get(userid, None)


def get_games(userid=None):
    games = dataIO.load_json("data/game/games.json")
    if not userid:
        return games
    else:
        return games[userid]


def get_steam_games(id):
    url = "https://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key=key&steamid={id}&include_appinfo=1&format=json".format(
        id=id)
    r = requests.get(url)
    games = [game.get('name') for game in json.loads(r.text).get(
        'response').get('games') if check_category(game.get('appid'))]
    return games


def set_steam_games(steamid, userid):
    steam_games = get_steam_games(steamid)
    game_list = get_games()
    user_game_list = game_list.get(userid)

    if user_game_list:
        user_game_list.extend(steam_games)
    else:
        user_game_list = steam_games

    game_list[userid] = list(set(user_game_list))
    dataIO.save_json("data/game/games.json", game_list)


def create_key(userid):
    game_list = get_games()
    game_list[userid] = []
    dataIO.save_json("data/game/games.json", game_list)


def check_key(userid):
    game_list = get_games()
    key_list = game_list.keys()

    if userid in key_list:
        return True
    else:
        return False


def delete_key(userid):
    game_list = get_games()
    del game_list[userid]
    dataIO.save_json("data/game/games.json", game_list)


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

    game_list = get_games()

    # Get only games for the provided list of users
    user_game_list = [game_list.get(user, []) for user in users]
    user_game_list = list(filter(None.__ne__, user_game_list))

    if user_game_list:
        suggestions = set(user_game_list[0]).intersection(*user_game_list[1:])
        return sorted(list(suggestions))


def get_users(ctx, choice=None):
    users = []

    if choice is None or choice.lower == "online":
        for user in ctx.message.server.members:
            if user.status.name == "online" and not user.bot:
                users.append(user.id)
    elif choice.lower() == "voice":
        for channel in ctx.message.server.channels:
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


def check_folders():
    if not os.path.exists("data/game"):
        print("Creating data/game folder...")
        os.makedirs("data/game")


def check_files():
    f = "data/game/games.json"
    if not dataIO.is_valid_json(f):
        print("Creating an empty games.json file...")
        dataIO.save_json(f, {})

    f = "data/game/steamids.json"
    if not dataIO.is_valid_json(f):
        print("Creating an empty steamids.json file...")
        dataIO.save_json(f, {})


def setup(bot):
    check_folders()
    check_files()
    bot.add_cog(Game(bot))
