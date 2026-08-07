import discord
from discord.ext import commands

class Say(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="say", aliases=["falar"])
    async def say_command(self, ctx: commands.Context, channel: discord.TextChannel, *, message: str):
        # Tenta apagar a mensagem que o usuário digitou
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            print("Permissão negada para apagar mensagens.")
        except discord.HTTPException:
            pass
        
        # Envia a mensagem limpa no canal selecionado
        await channel.send(message)

async def setup(bot):
    await bot.add_cog(Say(bot))