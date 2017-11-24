from .game import Game


def setup(bot):
    cog = Game()
    bot.add_cog(cog)
