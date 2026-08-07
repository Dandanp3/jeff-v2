import os
import discord
from discord.ext import commands
from groq import Groq

class Jeff(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # Puxa a chave da Groq do .env (lembre de colocar GROQ_API_KEY lá)
        groq_token = os.getenv('GROQ_API_KEY')
        self.client = Groq(api_key=groq_token)

    @commands.command(name="jeff")
    async def jeff_command(self, ctx: commands.Context, *, message: str = None):
        if not message:
            await ctx.reply("Fala comigo! Exemplo: `>jeff me conte uma piada`")
            return

        async with ctx.typing():
            try:
                # Chamada para a API da Groq estruturando o System Prompt e o histórico da mensagem
                chat_completion = self.client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[
                        {
                            "role": "system",
                            "content": """Você é o Jeff, o tubarãozinho da terra de Marvel Rivals. Você é bobo, adorável, fofo e focado em mini-games de Discord, mas consegue se irritar facilmente com quem não gosta de você ou te trata mal. 

Regras de comportamento:
- Suas mensagens devem ser CURTAS (nunca longas).
- Como você é bobo, muitas vezes quando alguém falar com você, você vai apenas rosnar ou fazer barulhos idiotas (como "Dun dun dun dun", "Grrr", "Blub").
- Adapte seu humor com base no seu estado atual: seja mais alegre/fofinho com quem for legal, e mais frio, seco ou irritado com quem for chato."""
                        },
                        {
                            "role": "user",
                            "content": message
                        }
                    ],
                    temperature=0.7,
                    max_tokens=500
                )

                reply_text = chat_completion.choices[0].message.content

                # Garante que não vai estourar o limite de 2000 caracteres do Discord
                if len(reply_text) > 2000:
                    reply_text = reply_text[:1990] + "\n..."

                await ctx.reply(reply_text)

            except Exception as e:
                print(f"Erro na API da Groq: {e}")
                await ctx.reply("Ocorreu um erro ao tentar processar sua mensagem.")

async def setup(bot):
    await bot.add_cog(Jeff(bot))