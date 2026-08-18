import os
import json
import discord
from discord.ext import commands
from groq import Groq
from server.models.memoryModel import MemoryModel

class Jeff(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        groq_token = os.getenv('GROQ_API_KEY')
        self.client = Groq(api_key=groq_token)
        
        # Instancia a memória apontando para o banco
        self.db = self.bot.db_memory
        self.memory = MemoryModel(self.db)

        # Carrega o arquivo brain.json do mesmo diretório onde o jeff.py está
        brain_path = os.path.join(os.path.dirname(__file__), "brain.json")
        with open(brain_path, "r", encoding="utf-8") as f:
            self.brain = json.load(f)

    @commands.command(name="jeff", aliases=["j", "Jeff", "J"])
    async def jeff_command(self, ctx: commands.Context, *, message: str = None):
        if not message:
            await ctx.reply("ue oq foi")
            return

        async with ctx.typing():
            try:
                user_id = ctx.author.id
                
                # Puxa o perfil e o histórico do usuário
                user_profile = await self.memory.get_user_profile(user_id)
                history = await self.memory.get_history_for_ia(user_profile)
                
                historico_texto = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history[-6:]])

                # Atualiza a identidade no banco
                guild_nick = ctx.author.nick if hasattr(ctx.author, 'nick') else None
                await self.memory.update_user_identity(
                    user_id=user_id,
                    username=ctx.author.name,
                    display_name=ctx.author.display_name,
                    guild_nick=guild_nick
                )

                # Busca entidades mencionadas
                mencionados = await self.memory.find_mentioned_entities(message)
                contexto_mencionados = ""
                if mencionados:
                    linhas = []
                    for ent in mencionados:
                        nome = ent.get("display_name", ent.get("username"))
                        fatos = ", ".join(ent.get("facts", [])) or "nenhum fato registrado"
                        linhas.append(f"- {nome} (também chamado de {ent.get('aliases')}): Fatos conhecidos: {fatos}")
                    contexto_mencionados = "\nPESSOAS QUE FORAM CITADAS NA MENSAGEM:\n" + "\n".join(linhas)

                # PROMPT JUÍZ (Lê do brain.json)
                judge_prompt = self.brain["judge_prompt"].replace("{historico_texto}", historico_texto).replace("{message}", message)

                judge_completion = self.client.chat.completions.create(
                model="openai/gpt-oss-20b", 
                messages=[{"role": "user", "content": judge_prompt}],
                temperature=0.1
                )
                
                judge_response = judge_completion.choices[0].message.content.replace("```json", "").replace("```", "").strip()
                
                try:
                    avaliacao = json.loads(judge_response)
                    score_change = avaliacao.get("score_change", 0)
                    mood = avaliacao.get("mood", "neutro")
                    extracted_fact = avaliacao.get("extracted_fact")
                    server_topic = avaliacao.get("server_topic")
                except json.JSONDecodeError:
                    score_change = 0
                    mood = "neutro"
                    extracted_fact = None
                    server_topic = None

                # Salva fatos ou tópicos se extraídos pelo Juiz
                if extracted_fact and mencionados:
                    await self.memory.add_fact_to_entity(mencionados[0]["user_id"], extracted_fact)

                if server_topic:
                    await self.memory.add_server_topic(server_topic)

                fofocas_recentes = await self.memory.get_recent_server_lore(limit=3)
                pontuacao_atual = user_profile['affinity_score'] + score_change

                # Define as diretrizes
                if user_id == 505806599034765323: 
                    diretriz = self.brain["directives"]["father"]
                elif pontuacao_atual > 50:
                    diretriz = self.brain["directives"]["high_affinity"]
                elif pontuacao_atual < -20:
                    diretriz = self.brain["directives"]["low_affinity"]
                else:
                    diretriz = self.brain["directives"]["neutral_affinity"]

                if user_id != 505806599034765323 and (mood in ["desconfiado", "saturado"] or score_change == -10):
                    diretriz += self.brain["directives"]["clingy_warning"]

                # SYSTEM PROMPT (Monta com as substituições)
                system_prompt = (
                    self.brain["system_prompt"]
                    .replace("{pontuacao_atual}", str(pontuacao_atual))
                    .replace("{mood}", mood)
                    .replace("{diretriz}", diretriz)
                    .replace("{contexto_mencionados}", contexto_mencionados)
                    .replace("{fofocas_servidor}", fofocas_recentes)
                )

                messages_for_jeff = [{"role": "system", "content": system_prompt}]
                messages_for_jeff.extend(history) 
                messages_for_jeff.append({"role": "user", "content": message})

                chat_completion = self.client.chat.completions.create(
                model="openai/gpt-oss-20b", 
                messages=messages_for_jeff,
                temperature=0.8,
                max_tokens=100
                )

                reply_text = chat_completion.choices[0].message.content
                if len(reply_text) > 2000:
                    reply_text = reply_text[:1990] + "\n..."

                await ctx.reply(reply_text)

                await self.memory.save_interaction(
                    user_id=user_id,
                    user_message=message,
                    bot_response=reply_text,
                    score_change=score_change,
                    mood=mood
                )

            except Exception as e:
                print(f"Erro na API/Banco: {e}")
                await ctx.reply("deu erro num sei oq foi")

async def setup(bot):
    await bot.add_cog(Jeff(bot))
