import os
import traceback
import certifi
import discord
from discord.ext import commands
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

ca = certifi.where()

load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')
MONGO_URI = os.getenv('MONGO_URI')

intents = discord.Intents.default()
intents.message_content = True 
intents.members = True 

class Kalif(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=">", intents=intents)
        self.remove_command('help')
        
        # Conecta no MongoDB e define exatamente o atributo 'db_memory' que o jeff.py consome
        self.mongo_client = AsyncIOMotorClient(MONGO_URI, tlsCAFile=ca)
        self.db_memory = self.mongo_client["kalif_bot"]

    async def setup_hook(self):
        extensions = [
            "AI.jeff"
        ] 
        
        for ext in extensions:
            try:
                await self.load_extension(ext)
                print(f"Extensão carregada com sucesso: {ext}")
            except Exception as e:
                print(f"Falha ao carregar {ext}:")
                traceback.print_exc()

    async def on_ready(self):
        print(f"\nBot conectado como {self.user}")
        print("Comandos carregados:")
        for cmd in self.walk_commands():
            print(f" - >{cmd.name}")

if __name__ == "__main__":
    bot = Kalif()
    bot.run(TOKEN)