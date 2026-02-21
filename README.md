# Discord-Media-Management

This Discord bot is designed to manage and repost media from one channel to another.

## Installation & Setup

1. Make sure you have Python 3.8 or higher installed.  
2. Install the dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Edit the `config.json` file and fill in the required values:
   - `token`: Your Discord bot token  
   - `server_id`: Discord server ID  
   - `source_channel_id`: Source channel ID (where media is posted)  
   - `target_channel_id`: Target channel ID (where media will be reposted)  
   - `role_id`: Required role ID required to use the command  
   - `reactions`: List of emojis that will be added under the media  

4. Run the bot:
   ```
   python bot.py
   ```

## Usage

Send one of the following commands to the bot via DM:

- Using the full message link:
   ```
   /media message_link: https://discord.com/channels/SERVER_ID/CHANNEL_ID/MESSAGE_ID
   ```

- Or using only the message_id (from the source channel):
   ```
   /media message_id: MESSAGE_ID
   ```

The bot will fetch the media from the specified message and repost it in the target channel, along with the original poster’s name and the configured reactions.

## Notes

- Only users with the specified role can use this command.  
- The link must be from the source channel.  
- The bot must have the required permissions in the server (read messages, send messages, add reactions).
