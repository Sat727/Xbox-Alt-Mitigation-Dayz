import argparse
import asyncio
import http.server
import os
import queue
import socketserver
import threading
from urllib.parse import parse_qs, urlparse
import webbrowser
from config import Config
import os
from xbox.webapi.authentication.manager import AuthenticationManager
from xbox.webapi.authentication.models import OAuth2TokenResponse
from xbox.webapi.common.signed_session import SignedSession
from xbox.webapi.scripts import REDIRECT_URI
from xbox.webapi.api.client import XboxLiveClient
import sys
from httpx import HTTPStatusError
import aiohttp
import datetime, pytz
import discord
import sqlite3
CLIENT_ID = Config.XBOX_ID
CLIENT_SECRET = Config.XBOX_SECRET
TOKENS_FILE = './token/tokens.json'
QUEUE = queue.Queue(1)
print(TOKENS_FILE)

class Xbox:
    rate_limits = 0
    @classmethod
    async def Client(self, action, gamertag:str=None, gamertaglist:list=None, message:discord.Message=None):
        # Create a HTTP client session
        async with SignedSession() as session:
            """
            Initialize with global OAUTH parameters from above
            """
            auth_mgr = AuthenticationManager(session, CLIENT_ID, CLIENT_SECRET, REDIRECT_URI)

            """
            Read in tokens that you received from the `xbox-authenticate`-script previously
            See `xbox/webapi/scripts/authenticate.py`
            """
            try:
                with open(TOKENS_FILE) as f:
                    tokens = f.read()
                # Assign gathered tokens
                auth_mgr.oauth = OAuth2TokenResponse.parse_raw(tokens)

            except FileNotFoundError as e:
                print(
                    f"File {TOKENS_FILE} isn`t found or it doesn`t contain tokens! err={e}"
                )
                #sys.exit(-1)

            """
            Refresh tokens, check the token lifetimes and just refresh them
            if they are close to expiry
            """
            print(auth_mgr.oauth.issued)
            async def CheckAuthToken():
                if auth_mgr.oauth.issued + datetime.timedelta(seconds=auth_mgr.oauth.expires_in) >= datetime.datetime.now().astimezone(pytz.timezone("UTC")):
                    try:
                        await auth_mgr.refresh_tokens()
                        # Save the refreshed/updated tokens
                        with open(TOKENS_FILE, mode="w") as f:
                            f.write(auth_mgr.oauth.json())
                            print(f"Refreshed tokens in {TOKENS_FILE}!")
                    except HTTPStatusError as e:
                        print(
                            f"""
                            Could not refresh tokens from {TOKENS_FILE}, err={e}\n
                            You might have to delete the tokens file and re-authenticate 
                            if refresh token is expired
                        """
                        )
                else:
                    print("Auth Token within 'expires_in'")
            #    #sys.exit(-1)
            await CheckAuthToken()



            """
            Construct the Xbox API client from AuthenticationManager instance
            """
            client = XboxLiveClient(auth_mgr)






            if action == 'GameCheck':
                print("Loading profile")
                async def getData(gamertag, p = None, friends = None):
                    try:
                        if p == None:
                            p = await client.profile.get_profile_by_gamertag(gamertag)
                    except Exception as e:
                        print(e)
                        if str(e).startswith('429'):
                            print("Being Rate Limited")
                            await asyncio.sleep(10)
                            return await getData(gamertag, p, friends)
                        if str(e).startswith('404'):
                            print(f"Not found for {gamertag}")
                            return None, None
                    try:
                        if friends == None:
                            friends = await client.people.get_friends_summary_by_xuid(p.dict()['profile_users'][0]['id'])
                        return p, friends
                    except Exception as e:
                        print(e)
                        if str(e).startswith('429'):
                            print("Being Rate Limited")
                            await asyncio.sleep(10)
                            return await getData(gamertag, p, friends)
                        if str(e).startswith('404'):
                            print(f"Not found for {gamertag}")
                            return None, None
                    
                return await getData(gamertag)
            






            if action == 'CheckUser':
                print("Loading profile")
                try:
                    profile = await client.profile.get_profile_by_gamertag(gamertag)
                except Exception as e:
                    print(e)
                    return None, None
                #try:
                friends = await client.people.get_friends_summary_by_xuid(profile.dict()['profile_users'][0]['id'])
                #except aiohttp.ClientResponseError:
                #    friends = False
                return profile, friends
            if action == 'BulkCheck':
                XuidList = []
                FailedList = []
                Duplicates = []
                accounts = sqlite3.connect("db/bannedxuids.db")
                ac = accounts.cursor()
                total = len(gamertaglist)
                count = 0
                added = 0
                print("Bulk XUID from Banned list")
                async def XUID(i, retry=False):
                    try:
                        profile = await client.profile.get_profile_by_gamertag(i)
                        profile = profile.dict()
                        print([list(i.values())[0] for i in XuidList])
                        if retry == False:
                            if profile['profile_users'][0]['id'] in [list(i.values())[0] for i in XuidList]:
                                Duplicates.append(profile['profile_users'][0]['settings'][0]['value'])
                            XuidList.append({profile['profile_users'][0]['settings'][0]['value']: profile['profile_users'][0]['id']})
                        
                        if ac.execute("SELECT * FROM bannedxuids WHERE xuid = ?", (profile['profile_users'][0]['id'],)).fetchall() == []:
                            ac.execute("INSERT INTO bannedxuids (user, xuid) VALUES (?, ?)", (profile['profile_users'][0]['settings'][0]['value'], int(profile['profile_users'][0]['id'])))
                            accounts.commit()
                            return True
                        else:
                            print(f"{profile['profile_users'][0]['settings'][0]['value']} already in database.")
                            return False
                    except Exception as e:
                        print(e)
                        if type(e) == aiohttp.ClientResponseError:
                            e = str(e)
                            print(e)
                            if e.startswith('404'):
                                FailedList.append(i)
                                print(f"Failed to get XUID for {i}. User possibly changed gamertag already.")
                                return False
                            if e.startswith('429'):
                                self.rate_limits += 1
                                embed = discord.Embed(title=f'Gathering XUIDs', description=f"Gathering a total of {len(gamertaglist)} potential XUIDs")
                                embed.add_field(name='Rate Limits',value=f'Limited {self.rate_limits} time(s)', inline=False)
                                embed.add_field(name='Progress',value=f'{count} out of {total} gamertags checked', inline=False)
                                embed.add_field(name='Not Found',value=f'{len(FailedList)} invalid or changed gamertags (XUID unobtainable)', inline=False)
                                embed.add_field(name='Current',value=f'Current Gamertag check: {i}', inline=False)
                                embed.add_field(name='Duplicates',value=f'Duplicate entries/same users: {len(Duplicates)}', inline=False)
                                embed.color = discord.Color.random()
                                print("Rate Limited. Waiting 15 seconds...")
                                await message.edit(embed=embed, content=None)
                                await asyncio.sleep(15)
                                await XUID(i, retry=True)
                for i in gamertaglist:
                    count += 1
                    await CheckAuthToken()
                    if await XUID(i) == True:
                        added += 1
                return XuidList, total, len(FailedList), self.rate_limits, len(Duplicates), added
            if action == 'GetXUID':
                try:
                    profile = await client.profile.get_profile_by_xuid(gamertag)
                    return profile.dict()
                except Exception as e:
                    print(e)
                    return None
                return profile






