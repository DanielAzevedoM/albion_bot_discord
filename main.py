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
GUILD_ID_MAIN = 'YNRMcsuVSRWTBs0y4mZ-SQ'
GUILD_ID_ACADEMY = 'tIvhXYTrSby2f_WPUQj2nQ'
API_URL_MAIN = f'https://gameinfo.albiononline.com/api/gameinfo/guilds/{GUILD_ID_MAIN}/members'
API_URL_ACADEMY = f'https://gameinfo.albiononline.com/api/gameinfo/guilds/{GUILD_ID_ACADEMY}/members'
IM_PREFIX = '[IM]'
AC_PREFIX = '[AC]'
CARGO_ID_IM = 1028036606680117248
CARGO_ID_AC = 1087437619874513028

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
    try:
        synced = await bot.tree.sync()
        logger.info(f"Comandos sincronizados: {len(synced)}")
    except Exception as e:
        logger.error(f"Erro ao sincronizar comandos: {e}")

    if not verificar_membros.is_running():
        verificar_membros.start()
        logger.info("Tarefa de verificação iniciada")

bot.tree.command(name="register", description="Registra seu nickname da guild")
@app_commands.describe(nickname="Seu nome de jogador no Albion", guild="Escolha entre IM ou AC")
@app_commands.choices(guild=[
    app_commands.Choice(name="IMORTAIS", value="IM"),
    app_commands.Choice(name="IMORTAIS ACADEMY", value="AC")
])
async def register(interaction: discord.Interaction, nickname: str, guild: app_commands.Choice[str]):
    try:
        await interaction.response.defer(ephemeral=True)

        guild_choice = guild.value
        guild = interaction.guild

        for member in guild.members:
            if member.id == interaction.user.id and member.nick and (member.nick.startswith(IM_PREFIX) or member.nick.startswith(AC_PREFIX)):
                return await interaction.followup.send(
                    f"⚠️ Você já está registrado como: {member.nick}",
                    ephemeral=True)

        membros = await get_guild_members(API_URL_MAIN if guild_choice == "IM" else API_URL_ACADEMY)

        if not membros:
            return await interaction.followup.send(
                "🔴 Erro ao verificar a guild. Tente novamente mais tarde.",
                ephemeral=True)

        for member in guild.members:
            if member.nick and (member.nick.lower() == f"{IM_PREFIX} {nickname}".lower() or member.nick.lower() == f"{AC_PREFIX} {nickname}".lower()):
                return await interaction.followup.send(
                    f"⚠️ O nickname já está sendo usado por outro membro",
                    ephemeral=True)

        if nickname.lower() not in [m['Name'].lower() for m in membros]:
            return await interaction.followup.send(
                "🔴 Você não está na guild selecionada ou digitou seu nickname errado",
                ephemeral=True)

        prefix = IM_PREFIX if guild_choice == "IM" else AC_PREFIX
        cargo_id = CARGO_ID_IM if guild_choice == "IM" else CARGO_ID_AC
        cargo = guild.get_role(cargo_id)

        if not cargo:
            return await interaction.followup.send(
                "🔴 Cargo não configurado no servidor", ephemeral=True)

        try:
            await interaction.user.edit(nick=f"{prefix} {nickname}")
            await interaction.user.add_roles(cargo)

            logger.info(f"Novo registro: {interaction.user.name} como {nickname} ({prefix})")

            embed = discord.Embed(
                title="✅ Novo Registro Efetuado",
                color=discord.Color.green()
            )
            embed.add_field(name="Nickname", value=f"{prefix} {nickname}", inline=False)
            embed.add_field(name="Guild ID", value=GUILD_ID_MAIN if guild_choice == "IM" else GUILD_ID_ACADEMY, inline=False)
            embed.add_field(name="Cargo Atribuído", value=cargo.name, inline=False)
            embed.set_footer(text=f"Usuário: {interaction.user.display_name}")
            await interaction.channel.send(embed=embed)

            await interaction.followup.send(
                f"✅ Registro completo!\n"
                f"Seu nickname foi atualizado para: {prefix} {nickname}\n"
                f"Cargo {cargo.name} atribuído com sucesso!\n"
                f"DEMOCREST É AMIGO DO RAGNALDO!!!",
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

@tasks.loop(seconds=30)
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
            if member.nick:
                nome_limpo = re.sub(r'\[.*?\]', '', member.nick).strip()  # Remove todas as tags como [IM], [ENG], etc.
                nome_limpo = re.sub(r'[^\w\s-]', '', nome_limpo).strip()  # Remove emojis e símbolos

                if IM_PREFIX in member.nick:
                    if nome_limpo.lower() not in nomes_main:
                        try:
                            await member.edit(nick=None)
                            if cargo_im:
                                await member.remove_roles(cargo_im)
                            logger.info(f"Removido registro de: {member.display_name} (IM)")
                            atualizados += 1
                        except Exception as e:
                            logger.error(f"Erro ao atualizar {member.display_name}: {str(e)}")

                elif AC_PREFIX in member.nick:
                    if nome_limpo.lower() not in nomes_academy:
                        try:
                            await member.edit(nick=None)
                            if cargo_ac:
                                await member.remove_roles(cargo_ac)
                            logger.info(f"Removido registro de: {member.display_name} (AC)")
                            atualizados += 1
                        except Exception as e:
                            logger.error(f"Erro ao atualizar {member.display_name}: {str(e)}")

            else:
                if cargo_im and cargo_im in member.roles:
                    try:
                        await member.remove_roles(cargo_im)
                        logger.info(f"Removido cargo [IM] de {member.display_name} sem nick válido")
                        atualizados += 1
                    except Exception as e:
                        logger.error(f"Erro ao remover cargo [IM]: {str(e)}")

                if cargo_ac and cargo_ac in member.roles:
                    try:
                        await member.remove_roles(cargo_ac)
                        logger.info(f"Removido cargo [AC] de {member.display_name} sem nick válido")
                        atualizados += 1
                    except Exception as e:
                        logger.error(f"Erro ao remover cargo [AC]: {str(e)}")

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