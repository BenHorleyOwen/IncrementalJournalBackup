import subprocess
import json
import os
import argparse
import shutil

EXPORTER = "/app/ChatExporter/DiscordChatExporter.Cli"

# --------------------
# Arguments
# --------------------
parser = argparse.ArgumentParser(description="Incremental Discord backup (HTML Dark)")

parser.add_argument("--token", required=True)
parser.add_argument("--server-id", required=True)
parser.add_argument("--output-path", required=True)
parser.add_argument("--media-path", required=True)
parser.add_argument("--data-file", default="/data.json")
parser.add_argument("--temp-dir", default="/tmp/discord_export_temp")

args = parser.parse_args()

TOKEN = args.token
GUILD_ID = str(args.server_id)
OUTPUT_PATH = args.output_path
MEDIA_PATH = args.media_path
DATA_FILE = args.data_file
TEMP_DIR = args.temp_dir

os.makedirs(OUTPUT_PATH, exist_ok=True)
os.makedirs(MEDIA_PATH, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

# --------------------
# Load state
# --------------------
if os.path.exists(DATA_FILE) and os.path.getsize(DATA_FILE) > 0:
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        state = json.load(f)
else:
    state = {}

# --------------------
# Discover channels
# --------------------
print("🔍 Discovering channels...")

raw = subprocess.check_output(
    [EXPORTER, "channels", "-g", GUILD_ID, "-t", TOKEN],
    text=True
)

channels = []
for line in raw.splitlines():
    line = line.strip()
    if not line or line.startswith("DiscordChatExporter"):
        continue
    parts = line.split()
    cid = parts[0] if parts[0].isdigit() else parts[1]
    name = " ".join(parts[2:]) if len(parts) > 2 else cid
    channels.append((cid, name))

if not channels:
    raise RuntimeError("No channels discovered")

# --------------------
# Process channels
# --------------------
for channel_id, channel_name in channels:
    print(f"▶ #{channel_name}")

    channel_dir = os.path.join(OUTPUT_PATH, channel_id)
    os.makedirs(channel_dir, exist_ok=True)

    final_html = os.path.join(channel_dir, "channel.html")
    last_id = state.get(channel_id)

    # --------------------
    # JSON probe (detect new messages)
    # --------------------
    temp_json = os.path.join(TEMP_DIR, f"{channel_id}.json")
    if os.path.exists(temp_json):
        os.remove(temp_json)

    json_cmd = [
        EXPORTER, "export",
        "-c", channel_id,
        "-t", TOKEN,
        "-f", "Json",
        "-o", temp_json,
    ]

    if last_id:
        json_cmd.extend(["--after", last_id])

    subprocess.run(json_cmd, check=False)

    if not os.path.exists(temp_json):
        print("  ⏭ no new messages")
        continue

    with open(temp_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    messages = data.get("messages", [])
    if not messages:
        print("  ⏭ no new messages")
        continue

    newest_id = messages[-1]["id"]

    # --------------------
    # HTML export (authoritative)
    # --------------------
    temp_html_dir = os.path.join(TEMP_DIR, channel_id)
    shutil.rmtree(temp_html_dir, ignore_errors=True)
    os.makedirs(temp_html_dir, exist_ok=True)

    html_cmd = [
        EXPORTER, "export",
        "-c", channel_id,
        "-t", TOKEN,
        "-f", "HtmlDark",
        "-o", temp_html_dir + "/",
        "--media",
        "--media-dir", MEDIA_PATH,
        "--reuse-media",
    ]

    if last_id:
        html_cmd.extend(["--after", last_id])

    subprocess.run(html_cmd, check=False)

    html_files = [
        f for f in os.listdir(temp_html_dir)
        if f.lower().endswith(".html")
    ]

    if not html_files:
        print("  ⏭ HTML export failed")
        continue

    shutil.move(
        os.path.join(temp_html_dir, html_files[0]),
        final_html
    )

    state[channel_id] = newest_id
    print(f"  ✅ up to {newest_id}")

# --------------------
# Save state
# --------------------
with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(state, f, indent=2)

print("✔ Backup complete")
