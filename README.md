# Game Library Cog for [RedBot](https://github.com/Cog-Creators/Red-DiscordBot)
[![FOSSA Status](https://app.fossa.io/api/projects/git%2Bgithub.com%2FAlchez%2FDiscord_Game_Library.svg?type=shield)](https://app.fossa.io/projects/git%2Bgithub.com%2FAlchez%2FDiscord_Game_Library?ref=badge_shield)

A Discord cog for creating user game lists, finding game list intersections, and some more stuff.

## Commands:
All the following commands need to be prefixed with '[p]game'. For example, if you want to manually add a game to your library with a '!' prefix, use:

    !game add (game_name)

### Steam:
* `steamkey` - Sets the Steam API key for the server (one-time setup; required to use the `steamlink` and `update` commands).
  * Visit the [Steam Web API Key](https://steamcommunity.com/dev/apikey) page, login with your Steam profile and fill out the short form to generate one - you can use any domain to do so.
* `steamlink` - Links a Steam library to a Discord ID
* `update` - Updates a user's game library with their linked Steam games (for new games and accidental deletions!).

### Non-Steam:
* `add` - Adds a game to the author user's library - mostly useful for manually adding non-Steam games.
* `addto` - (Admin only) Adds a game to the specified user's library.

### Suggestions:
* `suggest` - Looks at the libraries of online users and displays all the common games (priority order: voice > online users)
* `poll` - Same as suggest, but instead creates a Strawpoll for users to vote on a game to play.

### Deletions:
* `remove` - Removes a game from the author user's library (the `update` command will re-add all Steam games).
* `removefrom` - (Admin only) Removes a game from the specified user's library.
* `removelib` - Deletes the author user's library.
* `removeuser` - (Admin only) Removes a user and their entire library.

### Library:
* `list` - Prints out a user's entire game library (Steam + non-Steam).
* `check` - Checks for a game in a user's library, or for all valid users in the server.

---

Made with ♥ by [Alchez](https://github.com/Alchez) and [vjFaLk](https://github.com/vjFaLk)


## License
[![FOSSA Status](https://app.fossa.io/api/projects/git%2Bgithub.com%2FAlchez%2FDiscord_Game_Library.svg?type=large)](https://app.fossa.io/projects/git%2Bgithub.com%2FAlchez%2FDiscord_Game_Library?ref=badge_large)