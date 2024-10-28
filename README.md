# Console Alt Mitigation

I initially started this project for a client who ended up cancelling the commission after completion.

This bot will detect alt accounts by utilizing Xbox API to disallow users below a certain gamerscore, follower count, or to flag potential alt accounts to prevent unfavorable people joining your server. This project took about 2 weeks and was cancelled after it was completed without payment.

Here's a guide on how to setup, and use the bot

 ## Dependencies

- Python >= 3.7
- Discord.py
- Aiohttp
- xbox-webapi-python
  
Authentication

This project uses Nitrado, Discord, and Xbox API. 

## Xbox API


Authentication is supported via OAuth2.

- Register a new application in [Azure AD](https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps/ApplicationsListBlade)
  - Name your app
  - Select "Personal Microsoft accounts only" under supported account types
  - Add <http://localhost/auth/callback> as a Redirect URI of type "Web"
- Copy your Application (client) ID for later use
- On the App Page, navigate to "Certificates & secrets"
  - Generate a new client secret and save for later use

## Setup.py

This uses discord.py wrapper, and built-in Nitrado endpoint requests.
Use config.py to configure bot settings. You will need to generate a [Nitrado Token](https://server.nitrado.net/eng/developer/tokens) and a [Discord Bot Token](https://discord.com/developers/docs/intro)

```py
    DISCORD_TOKEN = '' # Fill out your Discord Token
    NITRADO_TOKEN = ''
    XBOX_ID = ''
    XBOX_SECRET = ''
    EMBED_COLOR = 0xFF3333 # Fill after 0x Hex
    DAYZ_SERVER = 0 # Server ID
    BOT_PREFIX = '!'
```
After you have done these steps, you will need to generate a tokens.json file.

## Tokens.json

```
xbox-authenticate --client-id <client-id> --client-secret <client-secret>
```
After you have ran this command the tokens.json file will appear at:

Windows: `C:\\Users\\<username>\\AppData\\Local\\OpenXbox\\xbox`

Create a folder called 'token' inside the project directory and copy-paste the file into the folder.


## Commands:

Check the gamertag of a supplied user, and display stats regarding the user.
```
/checkgamertag <gamertag> 
```
Assign the warn or ban notifications to a given channel. (Bot will not iterate log files without both supplied)
```
/channel <choice> <channel>
```
Add or remove an XUID to the banned user database
```
/bannedxuids <choice> <xuid>
```
Get the XUID of all banned users in your server's banned list. (This will take some time, and refrain from fully activitating bot before doing this, as this command will delay other commands as per Xbox rate limits)
```
/getbannedxuids
```
Clears the banned database completely
```
/cleardb
```


## Finalization

After you have followed all of the above steps, you can now run the bot. When the bot is initialized, be sure you have public bot disabled as the commands that users are allowed to execute are limited to adminstrative users, and if your bot is public, may be added by an unwanted 3rd party.

When you add the bot to a server, you can use the !sync command to sync the bot's command into the guild you added it to. After this, all of the bot's commands will be available to you. Get started by using the ```/getbannedxuids``` command as this is the most resource intesive command, and may take some time depending on how big your Nitrado ban list is. After the bot has successfully gathered all of the XUIDs in your ban list (if any) you are free to utilize all other commands. The bot will automatically ban any user who is detected to have joined with the same XUID that was documented before, and notify you in the channel you configured it to. Feel free to use this bot in any applications, but if you modify the bot, please give credit.



## Contribute

- Feel free to make suggestions
- Feel free to report bugs


