import discord
from discord import app_commands
from discord.ext import commands, tasks
import aiohttp
import os
import logging
import re
from flask import Flask
from threading import Thread


# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configurações
TOKEN = os.environ['TOKEN']
GUILD_ID_MAIN = 'YNRMcsuVSRWTBs0y4mZ-SQ'  # ID do servidor IMORTAIS
GUILD_ID_ACADEMY = 'tIvhXYTrSby2f_WPUQj2nQ'  # ID do servidor IMORTAIS ACADEMY
API_URL_MAIN = f'https://gameinfo.albiononline.com/api/gameinfo/guilds/{GUILD_ID_MAIN}/members'
API_URL_ACADEMY = f'https://gameinfo.albiononline.com/api/gameinfo/guilds/{GUILD_ID_ACADEMY}/members'
IM_PREFIX = '[IM]'
AC_PREFIX = '[AC]'
CARGO_ID_IM = 1326098802146414624  # ID do cargo IMORTAIS
CARGO_ID_AC = 1367097116169867314  # ID do cargo IMORTAIS ACADEMY

# Web Server para manter online
app = Flask('')

@app.route('/')
def home():
    return "Bot Albion ativo!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# Bot
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

async def get_guild_members(api_url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as response:
                if response.status == 200:
                    return await response.json()
                logger.error(f"Erro na API: Status {response.status}")
                return None
    except Exception as e:
        logger.error(f"Erro ao buscar membros: {str(e)}")
        return None

@bot.event
async def on_ready():
    logger.info(f'Bot conectado como {bot.user} (ID: {bot.user.id})')
    logger.info(f'Conectado em {len(bot.guilds)} servidor(es)')
    
    # Sincroniza os comandos para um servidor específico (mais rápido)
    try:
        # Sincroniza para um servidor específico
        for guild in bot.guilds:
            logger.info(f"Tentando sincronizar comandos para o servidor: {guild.name} (ID: {guild.id})")
            try:
                guild_obj = discord.Object(id=guild.id)
                synced = await bot.tree.sync(guild=guild_obj)
                logger.info(f"Comandos sincronizados para {guild.name}: {len(synced)}")
            except Exception as e:
                logger.error(f"Erro ao sincronizar comandos para {guild.name}: {e}")
        
        # Sincroniza globalmente também
        synced_global = await bot.tree.sync()
        logger.info(f"Comandos sincronizados globalmente: {len(synced_global)}")
    except Exception as e:
        logger.error(f"Erro ao sincronizar comandos: {e}")

    if not verificar_membros.is_running():
        verificar_membros.start()
        logger.info("Tarefa de verificação iniciada")



@tasks.loop(seconds=15)
async def verificar_membros():
    try:
        logger.info("Iniciando verificação periódica...")

        if not bot.guilds:
            logger.warning("Bot não está em nenhum servidor")
            return

        guild = bot.guilds[0]
        cargo_im = guild.get_role(CARGO_ID_IM)
        cargo_ac = guild.get_role(CARGO_ID_AC)

        membros_main = await get_guild_members(API_URL_MAIN)
        membros_academy = await get_guild_members(API_URL_ACADEMY)
        if not membros_main and not membros_academy:
            logger.error("Não foi possível obter membros das guilds")
            return

        nomes_main = [m['Name'].lower() for m in membros_main] if membros_main else []
        nomes_academy = [m['Name'].lower() for m in membros_academy] if membros_academy else []
        atualizados = 0

        for member in guild.members:
            tem_cargo_im = cargo_im and cargo_im in member.roles
            tem_cargo_ac = cargo_ac and cargo_ac in member.roles
            prefix_im = member.nick and IM_PREFIX in member.nick
            prefix_ac = member.nick and AC_PREFIX in member.nick

            if tem_cargo_im:
                if not prefix_im or not member.nick:
                    try:
                        await member.remove_roles(cargo_im)
                        logger.info(f"Removido cargo [IM] de {member.display_name} sem prefixo ou nick")
                        atualizados += 1
                    except Exception as e:
                        logger.error(f"Erro ao remover cargo [IM]: {str(e)}")
                    continue
                
                nome_limpo = re.sub(r'\[.*?\]', '', member.nick).strip()
                nome_limpo = re.sub(r'[^\w\s-]', '', nome_limpo).strip()
                if nome_limpo.lower() not in nomes_main:
                    try:
                        await member.edit(nick=None)
                        await member.remove_roles(cargo_im)
                        logger.info(f"Removido registro de: {member.display_name} (IM)")
                        atualizados += 1
                    except Exception as e:
                        logger.error(f"Erro ao atualizar {member.display_name}: {str(e)}")

            if tem_cargo_ac:
                if not prefix_ac or not member.nick:
                    try:
                        await member.remove_roles(cargo_ac)
                        logger.info(f"Removido cargo [AC] de {member.display_name} sem prefixo ou nick")
                        atualizados += 1
                    except Exception as e:
                        logger.error(f"Erro ao remover cargo [AC]: {str(e)}")
                    continue
                
                nome_limpo = re.sub(r'\[.*?\]', '', member.nick).strip()
                nome_limpo = re.sub(r'[^\w\s-]', '', nome_limpo).strip()
                if nome_limpo.lower() not in nomes_academy:
                    try:
                        await member.edit(nick=None)
                        await member.remove_roles(cargo_ac)
                        logger.info(f"Removido registro de: {member.display_name} (AC)")
                        atualizados += 1
                    except Exception as e:
                        logger.error(f"Erro ao atualizar {member.display_name}: {str(e)}")

        logger.info(f"Verificação completa. {atualizados} registros atualizados")

    except Exception as e:
        logger.error(f"Erro na verificação periódica: {str(e)}")

@verificar_membros.before_loop
async def antes_da_verificacao():
    await bot.wait_until_ready()
    logger.info("Aguardando bot estar pronto para verificação...")

# Mantém o bot online
keep_alive()

try:
    logger.info("Iniciando bot...")
    bot.run(TOKEN)
except Exception as e:
    logger.critical(f"Falha ao iniciar bot: {str(e)}")
    os._exit(1)