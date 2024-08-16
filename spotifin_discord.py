import os
import sys
import asyncio
import discord
from discord import app_commands
from spotify_to_jellyfin.notcli import request_music

TOKEN = os.getenv("DISCORD_TOKEN")
MUSIC_LIBRARY_PATH = os.getenv("MUSIC_LIBRARY_PATH")
intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
spotifin_channel_id = int(os.getenv("SPOTIFIN_CHANNEL_ID"))
assert spotifin_channel_id, "SPOTIFIN_CHANNEL_ID not set"

request_music_lock = asyncio.Lock()

@client.event
async def on_ready():
    print(f"{client.user} has connected to Discord!")
    if sys.argv[1:] and sys.argv[1] == "sync":
        print("Syncing commands...")
        try:
            await tree.sync()
        except Exception as e:
            print(f"Failed to sync commands: {e}")
    else:
        print("Not syncing commands.")


@tree.command(name="request")
@app_commands.describe(
    link="Link to a spotify Song, Album or Playlist",
    public="[For playlists] Whether the playlist should be visible to everyone",
)
async def request(interaction: discord.Interaction, link: str, public: bool = False):
    if request_music_lock.locked():
        await interaction.response.send_message(
            "Another request is currently being processed. Please try again later.",
            ephemeral=True,
        )
        return
    async with request_music_lock:
        link = link.split("?si=")[0]
        if not public and link.split("/")[-2] == "playlist":
            channel = interaction.user.dm_channel
            if not channel:
                channel = await interaction.user.create_dm()
        else:
            channel = client.get_channel(spotifin_channel_id)
        await interaction.response.send_message(
            f"Request for {link} received!", ephemeral=True
        )
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, request_music, link, interaction.user.id, MUSIC_LIBRARY_PATH, public
            )
            await channel.send(f"{link} is now available on jellyfin!")
        except Exception as e:
            await channel.send(
                f":bangbang: An error occurred during the processing of the request for {link}: ```{e}```"
            )


client.run(token=TOKEN)
