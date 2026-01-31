import subprocess
import json
import os
import argparse
import re

EXPORTER = "/app/ChatExporter/DiscordChatExporter.Cli"

# --------------------
# Arguments
# --------------------
parser = argparse.ArgumentParser(description="Incremental Discord backup (HTML Dark only)")

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
        last_ids = json.load(f)
else:
    last_ids = {}

# --------------------
# HTML helpers
# --------------------
HTML_SHELL = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Discord Channel Export</title>
</head>
<body>
</body>
</html>
"""

def ensure_html(path):
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(HTML_SHELL)

def extract_body(html):
    m = re.search(r"<body[^>]*>(.*?)</body>", html, re.S | re.I)
    return m.group(1).strip() if m else ""

def append_body(target, fragment):
    if not fragment.strip():
        return
    with open(target, "r+", encoding="utf-8") as f:
        content = f.read()
        insert = content.lower().rfind("</body>")
        new = content[:insert] + "\n" + fragment + "\n" + content[insert:]
        f.seek(0)
        f.write(new)
        f.truncate()

def newest_message_id(html):
    ids = re.findall(r'data-message-id="(\d+)"', html)
    return ids[-1] if ids else None

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
    if len(parts) < 2:
        continue
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
    temp_html = os.path.join(TEMP_DIR, f"{channel_id}.html")

    last_id = last_ids.get(channel_id)

    cmd = [
        EXPORTER, "export",
        "-c", channel_id,
        "-t", TOKEN,
        "-f", "HtmlDark",
        "-o", temp_html,
        "--media",
        "--media-dir", MEDIA_PATH,
        "--reuse-media",
    ]

    if last_id:
        cmd.extend(["--after", last_id])

    subprocess.run(cmd, check=False)

    if not os.path.exists(temp_html):
        print("  ⏭ export failed")
        continue

    with open(temp_html, "r", encoding="utf-8") as f:
        html = f.read()

    body = extract_body(html)
    newest_id = newest_message_id(html)

    if not body or not newest_id:
        print("  ⏭ no new messages")
        os.remove(temp_html)
        continue

    ensure_html(final_html)
    append_body(final_html, body)
    os.remove(temp_html)

    last_ids[channel_id] = newest_id
    print(f"  ✅ up to {newest_id}")

# --------------------
# Save state
# --------------------
with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(last_ids, f, indent=2)

print("✔ Backup complete")
