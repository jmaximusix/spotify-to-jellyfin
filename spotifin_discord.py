import os
import sys
import discord
from discord import app_commands
from spotify_to_jellyfin.notcli import request_music

TOKEN = os.getenv("DISCORD_TOKEN")
MUSIC_LIBRARY_PATH = os.getenv("MUSIC_LIBRARY_PATH")
intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
channel_id = int(os.getenv("SPOTIFIN_CHANNEL_ID"))
assert channel_id, "SPOTIFIN_CHANNEL_ID not set"
spotifin_channel = client.get_channel(channel_id)


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
    await interaction.response.send_message(
        f"Request for {link} received!", ephemeral=True
    )
    try:
        request_music(link, interaction.user.id, MUSIC_LIBRARY_PATH, public)
        await spotifin_channel.send(f"{link} is now available on jellyfin!")
    except Exception as e:
        await spotifin_channel.send(
            f":bangbang: An error occurred during the processing of the request for {link}: ```{e}```"
        )


client.run(token=TOKEN)
