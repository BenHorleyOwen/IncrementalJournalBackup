FROM python:3.11-slim

# Install system deps
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    ca-certificates \
    libicu-dev \
    && rm -rf /var/lib/apt/lists/*

# Set workdir
WORKDIR /app

# Install DiscordChatExporter (Linux)
RUN wget https://github.com/Tyrrrz/DiscordChatExporter/releases/latest/download/DiscordChatExporter.Cli.linux-x64.zip \
    && unzip DiscordChatExporter.Cli.linux-x64.zip -d /app/ChatExporter \
    && chmod +x /app/ChatExporter/DiscordChatExporter.Cli

# Copy Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy script
COPY export.py .

# Copy entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Set entrypoint
ENTRYPOINT ["/entrypoint.sh"]

