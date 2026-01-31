# IncrementalJournalBackup
container compose image which updates the contents of a mounted directory 

to run this for yourself clone the repo and add a .env containing your discord API token and the server ID you want to export as well as the aboslute path of the backup dir
example:
BOT_TOKEN
SERVER_ID
BACKUP_DIR

then run docker compose up in the directory. (docker compose up --build)
	
follow the instructions outlined by [Tyrrrz/DiscordChatExporter](https://github.com/Tyrrrz/DiscordChatExporter) to set up your API key, (Also read their blog post)[https://tyrrrz.me/ukraine]

```
currently
the files out outputted without channel names or symlinks
the images within the files are not embedded correctly
e.g. Firefox can’t find the file at /backup/media/Screenshot_20191213_165804-B3C1C.jpg.
```