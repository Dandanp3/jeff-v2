from datetime import datetime
from zoneinfo import ZoneInfo

class MemoryModel:
    def __init__(self, db):
        self.collection = db["user_memories"]
        self.entities = db["global_entities"]
        self.server_lore = db["server_lore"]  

    async def update_user_identity(self, user_id: int, username: str, display_name: str, guild_nick: str = None):
        apelidos = list(set(filter(None, [username.lower(), display_name.lower(), guild_nick.lower() if guild_nick else None])))
        
        await self.entities.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "username": username,
                    "display_name": display_name,
                    "last_seen": datetime.now(ZoneInfo("America/Recife"))
                },
                "$addToSet": {
                    "aliases": {"$each": apelidos}
                }
            },
            upsert=True
        )

    async def find_mentioned_entities(self, text: str):
        # Procura se alguma palavra da mensagem bate com apelidos salvos no banco.
        
        palavras = [p.lower().strip(".,!?") for p in text.split()]
        
        # Busca no banco qualquer entidade que tenha um dos termos na lista de aliases
        cursor = self.entities.find({"aliases": {"$in": palavras}})
        entidades = await cursor.to_list(length=5)
        return entidades

    async def add_fact_to_entity(self, user_id: int, fact: str):
        # Salva um fato genérico sobre um usuário.
    
        if not fact:
            return
        await self.entities.update_one(
            {"user_id": user_id},
            {
                "$addToSet": {
                    "facts": fact
                }
            }
        )

    async def get_user_profile(self, user_id: int):
        user_data = await self.collection.find_one({"user_id": user_id})
        
        if not user_data:
            return {
                "user_id": user_id,
                "affinity_score": 0,
                "interaction_count": 0,
                "last_mood": "neutro",
                "custom_notes": "",
                "history": []
            }
            
        return user_data

    async def get_history_for_ia(self, user_data: dict):

        if "history" not in user_data or not user_data["history"]:
            return []
        
        groq_history = []
        for msg in user_data["history"]:
            groq_history.append({
                "role": msg["role"],
                "content": msg["content"]
            })
            
        return groq_history

    async def save_interaction(self, user_id: int, user_message: str, bot_response: str, score_change: int = 0, mood: str = "neutro", custom_notes: str = ""):
        # Salva a conversa E atualiza o perfil de amizade do usuário tudo de uma vez.

        agora = datetime.now(ZoneInfo("America/Recife"))

        novas_mensagens = [
            {"role": "user", "content": user_message, "timestamp": agora},
            {"role": "assistant", "content": bot_response, "timestamp": agora}
        ]

        # att o banco
        await self.collection.update_one(
            {"user_id": user_id},
            {
                "$push": {
                    "history": {
                        "$each": novas_mensagens,
                        "$slice": -40  # Mantém as últimas 40 msg
                    }
                },
                "$inc": {
                    "affinity_score": score_change, # Soma ou subtrai os pontos (ex: +5, -10)
                    "interaction_count": 1          # Adiciona +1 no contador de interações
                },
                "$set": {
                    "last_mood": mood,
                    "custom_notes": custom_notes
                }
            },
            upsert=True
        )

    async def clear_memory(self, user_id: int):
        await self.collection.update_one(
            {"user_id": user_id},
            {"$set": {"history": [], "affinity_score": 0, "custom_notes": ""}}
        )

    # =========================================================================
    # NOVAS FUNÇÕES PARA A LORE DO SERVIDOR
    # =========================================================================

    async def add_server_topic(self, topic: str):
        """Salva um assunto geral que a galera tá conversando no servidor"""
        if not topic:
            return
        
        agora = datetime.now(ZoneInfo("America/Recife"))
        await self.server_lore.insert_one({
            "topic": topic,
            "timestamp": agora
        })

    async def get_recent_server_lore(self, limit=5):
        """Pega as últimas fofocas do servidor para o Jeff saber o que tá rolando"""
        # Puxa os últimos limit tópicos ordenados pela data (do mais recente pro mais antigo)
        cursor = self.server_lore.find().sort("timestamp", -1).limit(limit)
        lores = await cursor.to_list(length=limit)
        
        if not lores:
            return "Nenhuma fofoca recente, o mar tá tranquilo."
        
        # Junta tudo numa string com marcadores
        textos = [f"- {l['topic']}" for l in lores]
        return "\n".join(textos)
