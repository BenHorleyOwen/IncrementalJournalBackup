import subprocess
import discord
import json
import os
import argparse
import shutil
from typing import Optional

EXPORTER = "/app/ChatExporter/DiscordChatExporter.Cli"

# --------------------
# Argument parsing
# --------------------
parser = argparse.ArgumentParser(
    description="Incremental Discord guild backup with Markdown merge"
)

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
# Load last exported IDs
# --------------------
last_ids = {}

if os.path.exists(DATA_FILE):
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            last_ids = json.load(f)
    except (json.JSONDecodeError, OSError):
        print("Warning: data file invalid or empty, starting fresh")
        last_ids = {}

# Ensure directories exist
os.makedirs(OUTPUT_PATH, exist_ok=True)
os.makedirs(MEDIA_PATH, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

# --------------------
# Helpers
# --------------------
def extract_last_message_id_from_json(json_path: str) -> Optional[int]:
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None

    messages = data.get("messages")
    if not messages:
        return None

    return int(messages[-1]["id"])


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

        active_channel_ids = set()

        for channel in guild.text_channels:
            print(f"Processing channel #{channel.name} ({channel.id})")
            active_channel_ids.add(str(channel.id))

            channel_dir = os.path.join(OUTPUT_PATH, str(channel.id))
            os.makedirs(channel_dir, exist_ok=True)

            final_md = os.path.join(channel_dir, "channel.md")
            meta_file = os.path.join(channel_dir, "meta.json")

            temp_md = os.path.join(TEMP_DIR, f"{channel.id}.md")
            temp_json = os.path.join(TEMP_DIR, f"{channel.id}.json")

            last_id = last_ids.get(str(channel.id))

            # Build exporter command
            cmd = [
                EXPORTER,
                "export",
                "-c", str(channel.id),
                "-t", TOKEN,
                "-f", "Markdown",
                "-o", temp_md,
                "--json", temp_json,
                "--media",
                "--media-dir", MEDIA_PATH,
                "--reuse-media",
            ]

            if last_id:
                cmd.extend(["--after", str(last_id)])

            subprocess.run(cmd, check=False)

            if not os.path.exists(temp_md):
                print(f"No new messages for #{channel.name}")
                continue

            # Merge markdown
            if os.path.exists(final_md):
                with open(temp_md, "r", encoding="utf-8") as tf, \
                     open(final_md, "a", encoding="utf-8") as ff:
                    ff.write("\n")
                    ff.write(tf.read())
            else:
                shutil.move(temp_md, final_md)

            # Update last exported message ID from JSON
            exported_last_id = extract_last_message_id_from_json(temp_json)
            if exported_last_id:
                last_ids[str(channel.id)] = exported_last_id

            # Cleanup temp JSON
            if os.path.exists(temp_json):
                os.remove(temp_json)

            # Write / update metadata (handles renames)
            meta = {
                "id": channel.id,
                "name": channel.name,
                "category": channel.category.name if channel.category else None,
                "deleted": False,
            }

            with open(meta_file, "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=2)

        # --------------------
        # Mark deleted channels
        # --------------------
        existing_dirs = {
            d for d in os.listdir(OUTPUT_PATH)
            if d.isdigit() and os.path.isdir(os.path.join(OUTPUT_PATH, d))
        }

        deleted_channels = existing_dirs - active_channel_ids

        for cid in deleted_channels:
            meta_file = os.path.join(OUTPUT_PATH, cid, "meta.json")
            if os.path.exists(meta_file):
                try:
                    with open(meta_file, "r+", encoding="utf-8") as f:
                        meta = json.load(f)
                        meta["deleted"] = True
                        f.seek(0)
                        json.dump(meta, f, indent=2)
                        f.truncate()
                except Exception:
                    pass

        # Persist state
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(last_ids, f, indent=2)

        print("Incremental backup completed!")
        await self.close()


client = BackupClient(intents=intents)
client.run(TOKEN)
