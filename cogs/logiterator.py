from discord.ext import commands, tasks
from os import kill, path
import numpy as np
import cv2
from datetime import datetime
from dateutil import tz
from datetime import timedelta
import utils.XboxFuncs as Xbox
import utils.Nitrado as Nitrado
print(Xbox.TOKENS_FILE)
#from utils.locations import Locations

import aiohttp
import aiofiles
import asyncio
import logging
import random
import discord
import re
import sqlite3
import json as json2
import math
import time
import os
from config import Config

accounts = sqlite3.connect("db/accounts.db")
ac = accounts.cursor()
bannedxuid = sqlite3.connect("db/bannedxuids.db")
xuid = bannedxuid.cursor()
ac.execute("CREATE TABLE IF NOT EXISTS gamers (user, status, timechecked)")
ac.execute("CREATE TABLE IF NOT EXISTS whitelisted (user)")
xuid.execute("CREATE TABLE IF NOT EXISTS bannedxuids (user, xuid)")
ac.execute("CREATE TABLE IF NOT EXISTS settings (channel integer, mingamerscore integer, minfriends integer, minfollowers integer, allowprivated integer, autoban integer, banchannel integer)")
if ac.execute("SELECT * FROM settings").fetchall() == []:
    ac.execute("INSERT INTO settings (channel, mingamerscore, minfriends, minfollowers, allowprivated, autoban) VALUES (?, ?, ?, ?, ?, ?)", (0,0,0,0,0,0))
accounts.commit()
bannedxuid.commit()

class AltMitigation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.reported = {}
        self.last_log = {}
        self.people = []
        self.headers = {"Authorization": f"Bearer {Config.NITRADO_TOKEN}"}
        logging.basicConfig(level=logging.INFO)
        self.FirstTime = True
        #self.fetch_logs.start()

    @commands.Cog.listener()
    async def on_ready(self):
        logging.info("Started bot")
        self.fetch_logs.start()

    @staticmethod
    async def new_logfile(fp) -> bool:
        async with aiofiles.open(fp, "r") as f:
            text = await f.read()
            logs = len(re.findall("AdminLog", text))

        return logs == 1

    async def run_loop(self):
        coros = []
        #servers = list(Config.SERVERS.keys())
        log = await self.download_logfile(Config.DAYZ_SERVER) 
        #log = True
        #if log:
        r = ac.execute("SELECT * FROM settings").fetchall()
        #log = True
        if r[0][0] == 0:
            log = False
            print("No channel set up for warnings. Please configure bot first.")
        if r[0][1] == 0:
            log = False
            print("No channel set up for minimum Gamerscore. Please configure bot first.")
        if r[0][3] == 0:
            log = False
            print("No channel set up for minimum followers. Please configure bot first.")
        if r[0][6] == 0:
            log = False
            print("No channel set up for Ban Notification. Please configure bot first.")
        if log == True:
            coros.append(self.check_log(Config.DAYZ_SERVER, r)) 
        #else:
        #    print(f"DB File for server id: {Config.DAYZ_SERVER} not found, Please check config.py")
    
        await asyncio.gather(*coros)

    @tasks.loop(minutes=5)
    async def fetch_logs(self):
        await self.run_loop()

    async def check_log(self, nitrado_id: int, config):
            xuids = xuid.execute("SELECT * FROM bannedxuids").fetchall()
            #if xuids != []:
            #    xuids = xuids[0]
            warnchannel = self.bot.get_channel(config[0][0])
            minscore = config[0][1]
            minfriends = config[0][2]
            minfollowers = config[0][3]
            allowprivated = config[0][4]
            banchannel = self.bot.get_channel(config[0][6])
            # Wipe log files when it detects new


            async def checkUserExists(player):
                ac.execute(f"SELECT * FROM gamers WHERE user = ?", (player,))
                r = ac.fetchall()
                if player == None:
                    return False
                if r == []:
                    print(f"Verifying {player}")
                    profile, friends = await Xbox.Xbox.Client('GameCheck', player)
                    if profile == None or friends == None:
                        print(f"Internal Error when getting Xbox data for {player}, read logs")
                        return
                    print(profile, friends)
                    print(xuids[0][1])
                    profile, friends = profile.dict(), friends.dict()
                    if profile != None or friends != None:
                        print([i for i in xuids])
                        print(profile['profile_users'][0]['id'])
                        if xuids != []:
                            for i in xuids:
                                print(i)
                                if int(profile['profile_users'][0]['id']) == int(i[1]):
                                    await Nitrado.NitradoFunctions.banPlayer(player)
                                    embed = discord.Embed(title=f"User {player} Bypass Ban", description=f"❌ Detected ban bypass")
                                    embed.add_field(name=f'{player} AKA {i[0]} banned for attempting to bypass ban.',value='Player automatically banned')
                                    embed.color = discord.Color.red()
                                    await banchannel.send(embed=embed)
                        embed = discord.Embed(title=f"User {player} flags", description=f"List of flags for {player}")
                        status = ['0','0']
                        if int(profile['profile_users'][0]['settings'][7]['value']) <= minscore:
                            embed.add_field(name="Gamerscore", value=f"\n ⚠️ {player} is below {minscore} Gamerscore ({profile['profile_users'][0]['settings'][7]['value']}/{minscore})", inline=False)
                            status[0] = '1'
                        #else:
                        #    embed.add_field(name="Gamerscore", value=f"\n ✔️ {player} is above {minscore} Gamerscore ({profile['profile_users'][0]['settings'][7]['value']}/{minscore})")
                        #    status[0] = 0
                        print(int(friends['target_follower_count']))
                        if int(friends['target_follower_count']) <= minfollowers:
                            embed.add_field(name="Followers", value=f"\n ⚠️ {player} is below {minfollowers} Follower Count ({friends['target_follower_count']}/{minfollowers})",inline=False)
                            status[1] = '1'
                        #else:
                        #    embed.add_field(name="Followers", value=f"\n ✔️ {player} is above {minfollowers} Follower Count ({friends['target_follower_count']}/{minfollowers})")
                        #    status[1] = 0
                        print(player)
                        print(';'.join(status))

                        ac.execute(f"INSERT INTO gamers (user, status, timechecked) VALUES (?, ?, ?)", (player, ';'.join(status), int(time.mktime(datetime.now().timetuple()))))
                        accounts.commit()
                        print(f"Initialized for {player}")
                        if embed.fields:
                            embed.set_image(url=profile['profile_users'][0]['settings'][8]['value'])
                            embed.color=discord.Color.red()
                            await warnchannel.send(embed=embed)
                        return False
                    else:
                        print("User Not Found. Internal error")
                else:
                    return True
            logging.info(f"Checking logfile for {nitrado_id}")
            fp = path.abspath(
                path.join(path.dirname(__file__), "..", "files", f"{nitrado_id}.ADM")
            )
            if nitrado_id not in self.reported:
                self.reported[nitrado_id] = []

            if nitrado_id not in self.last_log:
                self.last_log[nitrado_id] = ""

            async with aiofiles.open(fp, mode="r") as f:
                async for line in f:
                    try:

                        if str(line) in self.reported[nitrado_id]:
                            continue
                        if "AdminLog" in line:
                            if self.last_log[nitrado_id] != str(line):
                                if await self.new_logfile(fp):
                                    self.last_log[nitrado_id] = str(line)
                                    self.reported[nitrado_id] = []
                        self.reported[nitrado_id].append(str(line))
    
                        player = (re.search(r'[\'"](.*?)[\'"]', line))
                        if player:
                            if str(player.group(1)) not in self.people:
                                await checkUserExists(str(player.group(1)))
                                self.people.append(str(player.group(1)))
    
                        #if self.FirstTime == True:
                        #    self.reported[nitrado_id].append(str(line)) 
                        #if re.search(r"##### PlayerList log:", line):
                        #    playercoords = []
                        #if str(line) in self.reported[nitrado_id]:
                        #    continue
                        #if "AdminLog" in line:
                        #    if self.last_log[nitrado_id] != str(line):
                        #        if await self.new_logfile(fp):
                        #            self.last_log[nitrado_id] = str(line)
                        #            self.reported[nitrado_id] = []
                        #    self.reported[nitrado_id].append(str(line))
                    except Exception as e:
                        print(e.with_traceback())
                        continue

    async def download_logfile(self, nitrado_id):
        logging.info(f"Downloading logfile for {nitrado_id}")
        async with aiohttp.ClientSession() as ses:
            async with ses.get(f"https://api.nitrado.net/services", headers=self.headers) as e:
                parsed = json2.loads(await e.read()) 
                #print(json.dumps(parsed, indent=4))  # Show Nitrado Data
            async with ses.get(
                f"https://api.nitrado.net/services/{nitrado_id}/gameservers",
                headers=self.headers,
            ) as r:
                #await print(r.read())
                if r.status != 200:
                    logging.error(
                        f"Failed to get gameserver information ({nitrado_id}) ({r.status})"
                    )
                    return False
                else:
                    json = await r.json()
                    username = json["data"]["gameserver"]["username"]
                    game = json["data"]["gameserver"]["game"].lower()
                    if game == "dayzxb":
                        logpath = "dayzxb/config/DayZServer_X1_x64.ADM"
                    else:
                        log_path = ""
                        logging.error("This bot only supports: DayZ Xbox")
                        return False
                    async with ses.get(
                        f"https://api.nitrado.net/services/{nitrado_id}/gameservers/file_server/download?file=/games/{username}/noftp/{logpath}",
                        headers=self.headers,
                    ) as resp:
                        if resp.status != 200:
                            logging.error(
                                f"Failed to get nitrado download URL! ({nitrado_id}) ({resp.status})"
                            )
                            print(resp.content)
                            return False
                        else:
                            json = await resp.json()
                            url = json["data"]["token"]["url"]
                            async with ses.get(url, headers=self.headers) as res:
                                if res.status != 200:
                                    logging.error(
                                        f"Failed to download nitrado log file! ({nitrado_id}) ({res.status})"
                                    )
                                    return False
                                else:
                                    fp = path.abspath(
                                        path.join(
                                            path.dirname(__file__),
                                            "..",
                                            "files",
                                            f"{nitrado_id}.ADM",
                                        )
                                    )
                                    async with aiofiles.open(fp, mode="wb+") as f:
                                        await f.write(await res.read())
                                        await f.close()
                                    logging.info(
                                        f"Successfully downloaded logfile for ({nitrado_id})"
                                    )
                                    return True
                

async def setup(bot):
    await bot.add_cog(AltMitigation(bot))
