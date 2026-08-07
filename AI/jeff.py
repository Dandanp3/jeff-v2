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
        
        # Instancia o modelo de memória apontando ESPECIFICAMENTE para o db_memory do main.py
        self.db = self.bot.db_memory
        self.memory = MemoryModel(self.db)

    @commands.command(name="jeff", aliases=["j", "Jeff", "J"])
    async def jeff_command(self, ctx: commands.Context, *, message: str = None):
        if not message:
            await ctx.reply("ue oq foi")
            return

        async with ctx.typing():
            try:
                user_id = ctx.author.id
                
                # puxa o perfil e o histórico do user
                user_profile = await self.memory.get_user_profile(user_id)
                history = await self.memory.get_history_for_ia(user_profile)
                
                historico_texto = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history[-6:]])

                # atualiza a identidade do autor da mensagem (nomes, apelidos do servidor)
                guild_nick = ctx.author.nick if hasattr(ctx.author, 'nick') else None
                await self.memory.update_user_identity(
                    user_id=user_id,
                    username=ctx.author.name,
                    display_name=ctx.author.display_name,
                    guild_nick=guild_nick
                )

                # busca no banco se a mensagem menciona algm conhecido (ex: "poke")
                mencionados = await self.memory.find_mentioned_entities(message)
                contexto_mencionados = ""
                if mencionados:
                    linhas = []
                    for ent in mencionados:
                        nome = ent.get("display_name", ent.get("username"))
                        fatos = ", ".join(ent.get("facts", [])) or "nenhum fato registrado"
                        linhas.append(f"- {nome} (também chamado de {ent.get('aliases')}): Fatos conhecidos: {fatos}")
                    contexto_mencionados = "\nPESSOAS QUE FORAM CITADAS NA MENSAGEM:\n" + "\n".join(linhas)

                # PROMPT JUÍZ
                judge_prompt = f"""Você é um sistema de análise de sentimentos e extração de fatos.
Analise a nova mensagem do usuário direcionada ao bot "Jeff".
Histórico recente:
{historico_texto}

Mensagem atual: "{message}"

Regras de Pontuação:
- Elogio normal: +1 ou +2
- Neutro: 0
- Ofensa: -5
- GRUDENTO: -10

Regra de Extração:
Se a mensagem mencionar fatos sobre ALGUÉM (ex: "o poke gosta de café", "a maria joga de suporte"), extraia essa informação de forma resumida. Se não houver fatos novos, retorne null.

Responda APENAS com um JSON válido:
{{
  "score_change": numero_inteiro,
  "mood": "feliz|neutro|irritado|desconfiado|saturado",
  "extracted_fact": "fato curto extraído ou null"
}}"""

                judge_completion = self.client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "user", "content": judge_prompt}],
                    temperature=0.1
                )
                
                judge_response = judge_completion.choices[0].message.content.replace("```json", "").replace("```", "").strip()
                
                try:
                    avaliacao = json.loads(judge_response)
                    score_change = avaliacao.get("score_change", 0)
                    mood = avaliacao.get("mood", "neutro")
                    extracted_fact = avaliacao.get("extracted_fact")
                except json.JSONDecodeError:
                    score_change = 0
                    mood = "neutro"
                    extracted_fact = None

                # Se o Juiz extraiu um fato e a mensagem citou algm, salva o fato no banco
                if extracted_fact and mencionados:
                    # Salva o fato no primeiro usuário identificado na frase
                    await self.memory.add_fact_to_entity(mencionados[0]["user_id"], extracted_fact)

                # Calcula a nova pontuação temp para passar pro Jeff
                pontuacao_atual = user_profile['affinity_score'] + score_change

                # Define como o Jeff deve agir baseado no total de pontos
                diretriz = ""
                
                # REGRAS ESPECIAIS PARA O PAI (eu)
                if user_id == 505806599034765323: 
                    diretriz = "você ta falando com o Dan (seu pai). você ama ele de um jeito bem inocente e bobão. pode chamar de 'dan' ou 'papai' de forma bem natural e carinhosa."
                
                # REGRAS PARA OS MEROS MORTAIS
                elif pontuacao_atual > 50:
                    diretriz = "você gosta dessa pessoa, seja amigável, fofo e bobão com ela."
                elif pontuacao_atual < -20:
                    diretriz = "você nao gosta dessa pessoa. responde de má vontade, emburrado e meio ignorante."
                else:
                    diretriz = "você é neutro e meio desligado com essa pessoa."

                # Se o juiz detectou que a pessoa tá grudenta nessa mensagem específica
                if user_id != 505806599034765323 and (mood in ["desconfiado", "saturado"] or score_change == -10):
                    diretriz += " ATENÇÃO: a pessoa ta sendo grudenta demais. fica desconfiado e manda ela parar."

                # PROMPT JEFF (INOCENTE + CONHECIMENTO COMPARTILHADO) 
                system_prompt = f"""Você é o Jeff, o tubarão land-shark do Marvel Rivals. 

HISTÓRIA DE FUNDO (LORE OFICIAL):
- Passado Glorioso: Você já foi uma lenda nos campos de batalha do multiverso Marvel. Lutou lado a lado com o Thor contra exércitos inteiros, via o Deadpool fazer as piadas mais sem noção no meio do caos, e tentava (sem muito sucesso) aprender truques mentais com a Emma Frost. Você era destemido e ágil.
- O Acidente Multiversal: Durante um colapso do multiverso, você foi jogado para fora de Marvel Rivals e despencou direto aqui dentro deste servidor, o "Arcadia".
- O Trauma: Na aterrissagem, você bateu a cabeça com muita força em uma pedra mística do servidor. Isso travou seus miolos e te deixou com amnésia parcial, lesado e avoado.
- Saudades: Você sente uma saudade desgraçada da Emma Frost (ela era elegante e cheirava a gelo) e do Deadpool (que te dava lanches estranhos). De vez em quando seu coração aperta de nostalgia.
- Lar Doce Lar: Apesar de tudo e de ser meio tonto, você ama o Arcadia. Considera todo mundo daqui como sua nova "equipe" e se sente completamente em casa.

Regras de ESCRITA e ESTILO (MUITO IMPORTANTES):
- Escreva como uma criança digitando no Discord: frases curtas, texto solto e bagunçado.
- PROIBIDO usar português certinho. Sem pontuação perfeita, sem vírgulas formais, sem letras maiúsculas forçadas no começo das frases, sem ponto final.
- Use abreviações normais de internet: "ta", "pra", "q", "nao", "tb", "num sei", "c".
- NUNCA use rosnados ("Grrr") ou barulhos chatos ("Blub"). Fale apenas com palavras normais de forma solta.

COMPORTAMENTO E LÓGICA:
- Lampejos de Herói: Às vezes cê lembra do passado e solta uma frase aleatória sobre o Thor ou homem aranha ou homem de ferro ou o Deadpool ou os X-men, mas logo esquece o raciocínio e muda de assunto para comida ou água.
- Burrice Inocente: Se te perguntarem algo técnico, científico ou complexo, você não entende absolutamente nada. Você distorce o assunto para o seu mundinho de tubarão (acha que código é comida, bugs são peixes estranhos).
- Zero Maldade: Você é extremamente puro e inocente, não entende segundas intenções.

ESTADO ATUAL COM ESSE USUÁRIO:
Afinidade atual: {pontuacao_atual} pontos.
Humor atual com ele: {mood}.
Instrução estrita: {diretriz}
{contexto_mencionados}"""

                messages_for_jeff = [{"role": "system", "content": system_prompt}]
                messages_for_jeff.extend(history) 
                messages_for_jeff.append({"role": "user", "content": message})

                chat_completion = self.client.chat.completions.create(
                    model="llama-3.1-8b-instant",
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
