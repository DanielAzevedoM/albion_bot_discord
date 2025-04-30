import discord
from discord import app_commands
from discord.ext import commands, tasks
import aiohttp
import os
import logging
from flask import Flask
from threading import Thread

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configurações
TOKEN = os.environ['TOKEN']
GUILD_ID_API = 'YNRMcsuVSRWTBs0y4mZ-SQ'
API_URL = f'https://gameinfo.albiononline.com/api/gameinfo/guilds/{GUILD_ID_API}/members'
IM_PREFIX = '[IM]'
CARGO_ID = 1326098802146414624  # Substitua pelo ID real do cargo que será atribuído

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
bot = commands.Bot(command_prefix='/', intents=intents)


async def get_guild_members():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_URL) as response:
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

    try:
        synced = await bot.tree.sync()
        logger.info(f"Comandos sincronizados: {len(synced)}")
    except Exception as e:
        logger.error(f"Erro ao sincronizar comandos: {e}")

    if not verificar_membros.is_running():
        verificar_membros.start()
        logger.info("Tarefa de verificação iniciada")


@bot.tree.command(name="register",
                  description="Registra seu nickname da guild")
@app_commands.describe(nickname="Seu nome de jogador no Albion")
async def register(interaction: discord.Interaction, nickname: str):
    try:
        await interaction.response.defer(ephemeral=True)

        # Verifica se o usuário já está registrado
        guild = interaction.guild
        for member in guild.members:
            if member.id == interaction.user.id and member.nick and member.nick.startswith(
                    IM_PREFIX):
                return await interaction.followup.send(
                    f"⚠️ Você já está registrado como: {member.nick}",
                    ephemeral=True)

        # Verifica membros da guild
        membros = await get_guild_members()
        if not membros:
            return await interaction.followup.send(
                "🔴 Erro ao verificar a guild. Tente novamente mais tarde.",
                ephemeral=True)

        # Verifica se o nickname já está sendo usado por outro membro
        for member in guild.members:
            if member.nick and member.nick.lower(
            ) == f"{IM_PREFIX} {nickname}".lower():
                return await interaction.followup.send(
                    f"⚠️ O nickname [IM] {nickname} já está sendo usado por outro membro",
                    ephemeral=True)

        # Verifica se está na guild do Albion
        if nickname.lower() not in [m['Name'].lower() for m in membros]:
            return await interaction.followup.send(
                "🔴 Você não está na guild do Albion ou digitou seu nickname errado",
                ephemeral=True)

        # Atualiza nickname e atribui cargo
        cargo = guild.get_role(CARGO_ID)
        if not cargo:
            return await interaction.followup.send(
                "🔴 Cargo não configurado no servidor", ephemeral=True)

        try:
            await interaction.user.edit(nick=f"{IM_PREFIX} {nickname}")
            await interaction.user.add_roles(cargo)

            logger.info(
                f"Novo registro: {interaction.user.name} como {nickname}")
            await interaction.followup.send(
                f"✅ Registro completo!\n"
                f"Seu nickname foi atualizado para: {IM_PREFIX} {nickname}\n"
                f"Cargo {cargo.name} atribuído com sucesso!",
                ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send(
                "🔴 Não tenho permissões para atualizar seu nickname/cargo",
                ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"🔴 Erro inesperado: {str(e)}",
                                            ephemeral=True)

    except Exception as e:
        logger.error(f"Erro no comando register: {str(e)}")
        await interaction.followup.send(
            "🔴 Ocorreu um erro ao processar seu registro", ephemeral=True)


@tasks.loop(minutes=30)
async def verificar_membros():
    try:
        logger.info("Iniciando verificação periódica...")

        if not bot.guilds:
            logger.warning("Bot não está em nenhum servidor")
            return

        guild = bot.guilds[0]
        cargo = guild.get_role(CARGO_ID)
        if not cargo:
            logger.error("Cargo de verificação não encontrado!")
            return

        membros_albion = await get_guild_members()
        if not membros_albion:
            logger.error("Não foi possível obter membros da guild Albion")
            return

        nomes_albion = [m['Name'].lower() for m in membros_albion]
        atualizados = 0

        for member in guild.members:
            if member.nick and member.nick.startswith(IM_PREFIX):
                nickname = member.nick[len(IM_PREFIX) + 1:].strip()

                if nickname.lower() not in nomes_albion:
                    try:
                        await member.edit(nick=None)
                        await member.remove_roles(cargo)
                        logger.info(
                            f"Removido registro de: {member.display_name}")
                        atualizados += 1
                    except Exception as e:
                        logger.error(
                            f"Erro ao atualizar {member.display_name}: {str(e)}"
                        )

        logger.info(
            f"Verificação completa. {atualizados} registros atualizados")

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
