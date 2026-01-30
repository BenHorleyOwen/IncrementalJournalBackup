import subprocess
import discord
import json
import os
import argparse
import shutil

EXPORTER = "/app/ChatExporter/DiscordChatExporter.Cli"

# --------------------
# Argument parsing
# --------------------
parser = argparse.ArgumentParser(description="Incremental Discord guild backup with MD merge")

parser.add_argument("--token", required=True)
parser.add_argument("--server-id", required=True)
parser.add_argument("--output-path", required=True)
parser.add_argument("--media-path", required=True)
parser.add_argument("--data-file", default="data.json")
parser.add_argument("--temp-dir", default="/tmp/discord_export_temp")

args = parser.parse_args()

TOKEN = args.token
GUILD_ID = int(args.server_id)
OUTPUT_PATH = args.output_path
MEDIA_PATH = args.media_path
DATA_FILE = args.data_file
TEMP_DIR = args.temp_dir

# --------------------
# Load last message IDs
# --------------------
last_ids = {}

if os.path.exists(DATA_FILE):
    try:
        with open(DATA_FILE, "r") as f:
            last_ids = json.load(f)
    except (json.JSONDecodeError, OSError):
        print("Warning: data file invalid or empty, starting fresh")
        last_ids = {}


# Ensure temp directory exists
os.makedirs(TEMP_DIR, exist_ok=True)

# --------------------
# Discord client
# --------------------
intents = discord.Intents.default()
intents.guilds = True
intents.messages = True

class BackupClient(discord.Client):
    async def on_ready(self):
        print(f"Starting incremental backup for guild {GUILD_ID} ({self.user})")

        guild = self.get_guild(GUILD_ID)
        if not guild:
            raise RuntimeError("Bot is not in target guild")

        for channel in guild.text_channels:
            print(f"Processing channel #{channel.name}")

            last_id = last_ids.get(str(channel.id))
            temp_file = os.path.join(TEMP_DIR, f"{channel.id}.md")
            final_file = os.path.join(OUTPUT_PATH, f"{channel.name}.md")

            # Build export command
            cmd = [
                EXPORTER,
                "export",
                "-c", str(channel.id),
                "-t", TOKEN,
                "-f", "Markdown",
                "-o", temp_file,
                "--media",
                "--media-dir", MEDIA_PATH,
                "--reuse-media"
            ]
            if last_id:
                cmd.extend(["--after", str(last_id)])

            subprocess.run(cmd, check=False)
            if not os.path.exists(temp_file):
                print(f"No new messages for #{channel.name}")
                continue

            # Merge temp file into existing MD
            if os.path.exists(final_file):
                with open(temp_file, "r", encoding="utf-8") as tf, \
                     open(final_file, "a", encoding="utf-8") as ff:
                    ff.write("\n")  # ensure separation
                    ff.write(tf.read())
            else:
                shutil.move(temp_file, final_file)

            # Fetch newest message for this channel
            try:
                last_msg = await channel.fetch_message(channel.last_message_id)
                last_ids[str(channel.id)] = last_msg.id
            except Exception:
                pass

        # Persist last message IDs
        with open(DATA_FILE, "w") as f:
            json.dump(last_ids, f, indent=2)

        print("Incremental backup completed!")
        await self.close()


client = BackupClient(intents=intents)
client.run(TOKEN)
