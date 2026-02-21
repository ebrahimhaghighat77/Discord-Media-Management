import os
# Disable Python's HTTPS verification flag (affects some stdlib paths)
os.environ['PYTHONHTTPSVERIFY'] = '0'

import ssl
# WARNING: The following disables SSL certificate verification globally.
# This allows the bot to connect even when the system CA bundle is missing,
# but it is insecure and should only be used in controlled environments.
ssl._create_default_https_context = ssl._create_unverified_context

import aiohttp
# Monkey-patch aiohttp's TCPConnector to force `ssl=False` (disable verification)
_original_tcp_init = aiohttp.TCPConnector.__init__
def _patched_tcp_init(self, *args, **kwargs):
    kwargs['ssl'] = False
    return _original_tcp_init(self, *args, **kwargs)
aiohttp.TCPConnector.__init__ = _patched_tcp_init

import discord
from discord.ext import commands, tasks
from typing import Optional
import json
import re

with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.members = True
intents.presences = True

bot = commands.Bot(command_prefix='/', intents=intents)

@bot.event
async def on_ready():
    try:
        await bot.tree.sync()
    except Exception:
        pass
    print(f'Bot is ready: {bot.user}')
    update_activity.start()

@tasks.loop(minutes=5)
async def update_activity():
    guild = bot.get_guild(int(config['server_id']))
    if guild:
        role_id = int(config['role_id'])
        role = guild.get_role(role_id)
        if role:
            total_members = len(role.members)
            online_members = sum(1 for member in role.members if member.status != discord.Status.offline)
            activity_text = f"Media Manager : {online_members}/{total_members}"
            await bot.change_presence(activity=discord.Game(name=activity_text))

@update_activity.before_loop
async def before_update_activity():
    await bot.wait_until_ready()
@bot.tree.command(name="media", description="Post media links with credited users or repost from message link")
async def media(interaction: discord.Interaction, message_link: Optional[str] = None, message_id: Optional[str] = None):
    # Only allow usage in DM
    if interaction.guild is not None:
        await interaction.response.send_message("This command can only be used in DMs.", ephemeral=True)
        return

    # Get guild and check member role
    guild = bot.get_guild(int(config['server_id']))
    if guild is None:
        await interaction.response.send_message("Server not found.", delete_after=60)
        return

    member = guild.get_member(interaction.user.id)
    if member is None:
        await interaction.response.send_message("You are not a member of the server.", delete_after=60)
        return

    role_id = int(config['role_id'])
    if not any(role.id == role_id for role in member.roles):
        await interaction.response.send_message("You do not have the required permissions.", delete_after=60)
        return

    # Determine message_id and channel_id from options
    channel_id = None
    msg_id = None
    if message_link:
        first = message_link.splitlines()[0].strip()
        m = re.search(r'https://discord\.com/channels/(\d+)/(\d+)/(\d+)', first)
        if not m:
            await interaction.response.send_message("Invalid link format.", delete_after=60)
            return
        server_id = int(m.group(1))
        channel_id = int(m.group(2))
        msg_id = int(m.group(3))
        if server_id != int(config['server_id']):
            await interaction.response.send_message("The link is not from the specified server.", delete_after=60)
            return
    elif message_id:
        try:
            msg_id = int(message_id)
            channel_id = int(config['source_channel_id'])
        except ValueError:
            await interaction.response.send_message("Invalid message_id.", delete_after=60)
            return
    else:
        await interaction.response.send_message("Invalid format. Use `message_link` or `message_id` options.", delete_after=60)
        return

    await interaction.response.defer()

    # Fetch the message
    try:
        source_channel = bot.get_channel(int(channel_id))
        message = await source_channel.fetch_message(int(msg_id))
    except discord.NotFound:
        msg = await interaction.followup.send("Message not found.")
        await msg.delete(delay=60)
        return
    except Exception as e:
        msg = await interaction.followup.send(f"Error fetching message: {str(e)}")
        await msg.delete(delay=60)
        return

    if not message.attachments:
        msg = await interaction.followup.send("Selected message has no media attachments.")
        await msg.delete(delay=60)
        return

    target_channel = bot.get_channel(int(config['target_channel_id']))
    if target_channel is None:
        msg = await interaction.followup.send("Target channel not found.")
        await msg.delete(delay=60)
        return

    for attachment in message.attachments:
        file = await attachment.to_file()
        # send attachment and a blockquote 'Posted by'
        quote = f"> Posted by: {message.author.mention}"
        sent_message = await target_channel.send(file=file, content=quote)
        
        for reaction_str in config['reactions']:
            try:
                # Check if it's a custom emoji name like :emoji_name:
                if reaction_str.startswith(':') and reaction_str.endswith(':'):
                    emoji_name = reaction_str.strip(':')
                    # Search for the emoji in the guild
                    custom_emoji = discord.utils.get(guild.emojis, name=emoji_name)
                    if custom_emoji:
                        await sent_message.add_reaction(custom_emoji)
                    else:
                        # If not found in guild, try to add as is (maybe it's a standard emoji or full ID)
                        await sent_message.add_reaction(reaction_str)
                else:
                    # Standard emoji or already formatted
                    await sent_message.add_reaction(reaction_str)
            except Exception as e:
                print(f"Error adding reaction {reaction_str}: {e}")

    msg = await interaction.followup.send("Media posted successfully.")
    await msg.delete(delay=60)

bot.run(config['token'])
