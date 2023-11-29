import aiohttp
import json
from config import Config
class NitradoFunctions():
    @classmethod
    async def getSettings(self): # Category would be the type of setting IE. 'general' key would be the specific setting IE. "bans"
        headers = {"Authorization": f"Bearer {Config.NITRADO_TOKEN}"}
        async with aiohttp.ClientSession() as ses:
            async with ses.get(f"https://api.nitrado.net/services/{Config.DAYZ_SERVER}/gameservers", headers=headers) as e:
                return await e.content.read()
            

    async def banPlayer(self, username, ban):
        id = Config.DAYZ_SERVER
        data = await self.getSettings()
        if data:
            banData = json.loads(data)['data']['gameserver']['settings']['general']['bans']
            if ban.name == 'Add':
                if username in [i for i in banData.split('\r\n')]:
                    return "User already banned"
                else:
                    banData += '\r\n' + username
                    resp = await self.postSetting(category='general', key='bans', value=banData.replace("\\n",'\n').replace("\\r",'\r'), id=id)
                    if resp == 200:
                         print(f"Successfully added {username} to the ban list")
                         return f"Successfully added {username} to the ban list"
                    else:
                         print(f"Something went wrong when trying to ban {username}. Try again in a few moments.")
                         return f"Something went wrong when trying to ban {username}. Try again in a few moments."
            if ban.name == 'Remove':
                if username not in [i for i in banData.split('\r\n')]:
                    print("User not banned")
                    return "User not banned"
                else:
                    banData = banData.replace(f'\r\n{username}', '')
                    resp = await self.postSetting(category='general', key='bans', value=banData.replace("\\n",'\n').replace("\\r",'\r'), id=id)
                    if resp == 200:
                         print(f"Successfully removed {username} from the ban list")
                         return f"Successfully removed {username} from the ban list"
                    else:
                         print(f"Something went wrong when trying to unban {username}. Try again in a few moments.")
                         return f"Something went wrong when trying to unban {username}. Try again in a few moments."
        else:
            return "Something went wrong"