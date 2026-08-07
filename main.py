import discord
from discord.ext import commands
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os
import traceback

import certifi
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
        self.mongo_client = AsyncIOMotorClient(MONGO_URI, tlsCAFile=ca)
        #self.db = self.mongo_client["kalif_bot"]
        #self.server_controller = ServerController(self.db["servers"])

    async def setup_hook(self):
        extensions = [
            "AI.jeff"
        ] 
        
        for ext in extensions:
            try:
                await self.load_extension(ext)
                print(f"Extensão carregada: {ext}")
            except Exception as e:
                print(f"Falha ao carregar {ext}")
                traceback.print_exc()

    async def on_ready(self):
        print(f"\nBot conectado como {self.user}")
        print("Comandos carregados:")
        for cmd in self.walk_commands():
            print(f" - .{cmd.name}")
    
    async def on_guild_join(self, guild):
        await self.server_controller.get_or_create_server(guild.id)
        

if __name__ == "__main__":
    bot = Kalif()
    bot.run(TOKEN)
