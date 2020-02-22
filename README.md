[![FOSSA Status](https://app.fossa.io/api/projects/git%2Bgithub.com%2FAlchez%2FDiscord_Game_Library.svg?type=shield)](https://app.fossa.io/projects/git%2Bgithub.com%2FAlchez%2FDiscord_Game_Library?ref=badge_shield)

---

# Game Library Cog for [RedBot](https://github.com/Cog-Creators/Red-DiscordBot)

A Discord cog for creating user game lists, finding game list intersections, and some more stuff.

## Installation:

* Add this repo to your bot with `[p]repo add collective https://github.com/TheCogCollective/Discord_Game_Library`
* Install the library cog with `[p]cog install collective game-library`
* Finally, load the cog with `[p]load game-library`

## Commands:
All the following commands need to be prefixed with '[p]game'. For example, if you want to manually add a game to your library with a '!' prefix, use:

    !game add (game_name)

### Steam:
* `steamkey` - Sets the Steam API key for the bot (one-time setup; required to use the `steamsync` and `update` commands).
  * Visit the [Steam Web API Key](https://steamcommunity.com/dev/apikey) page, login with your Steam profile and fill out the short form to generate one - you can use any domain to do so.
* `steamsync` - Syncs games between the given Steam ID and the user's library.
* `update` - Updates a user's game library from their synced Steam profile (for new games and accidental deletions!).

### Non-Steam:
* `add` - Adds a game to a user's library.

### Suggestions:
* `suggest` - Looks at the libraries of online users and displays all the common games (priority order: voice > online users)
* `poll` - Same as suggest, but instead creates a [Strawpoll](https://www.strawpoll.me/) for users to vote on a game to play.

### Deletions:
* `remove` - Removes a game from a user's library (the `update` command will re-add all Steam games).
* `destroy` - Deletes the author user's library.

### Library:
* `list` - Prints out a user's entire game library.
* `check` - Checks for a game in a user's library, or for all online users in the server.

## License
[![FOSSA Status](https://app.fossa.io/api/projects/git%2Bgithub.com%2FAlchez%2FDiscord_Game_Library.svg?type=large)](https://app.fossa.io/projects/git%2Bgithub.com%2FAlchez%2FDiscord_Game_Library?ref=badge_large)

---

Made with ♥ by [Alchez](https://github.com/Alchez) and [vjFaLk](https://github.com/vjFaLk)