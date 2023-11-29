import discord
from discord import app_commands
from discord.ext import commands

import utils.XboxFuncs as Xbox
from xbox.webapi.api.client import XboxLiveClient
import sqlite3
import utils.Nitrado as Nitrado
import json
class Commands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.gettingXUIDS = False
        #self.synced = False

    @commands.Cog.listener()
    async def on_ready(self):
        print("Commands Ready")
        #if not self.synced:
        #    await self.tree.sync()

    @app_commands.checks.has_permissions(administrator=True)
    @commands.command()
    async def sync(self, ctx) -> None:
        fmt = await ctx.bot.tree.sync()
        await ctx.send(f"Synced {len(fmt)}")

    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(name="checkgamertag", description="Check an Xbox gamer tag")
    async def checkgamertag(self, interaction:discord.Interaction, gamertag:str):
        profile, friends = await Xbox.Xbox.Client('CheckUser', gamertag)
        friends = friends.dict()
        profile = profile.dict()
        print(profile)
        profile_gamerscore = profile['profile_users'][0]['settings'][7]['value']
        tier = profile['profile_users'][0]['settings'][10]['value']
        print(profile_gamerscore, tier)

        embed = discord.Embed(title=f"{profile['profile_users'][0]['settings'][0]['value']}",
                              description=f"Profile Data | {profile['profile_users'][0]['id']}")
        embed.add_field(name="Gamerscore:",value=profile_gamerscore)
        embed.add_field(name="Friends:", value=friends['target_following_count'])
        embed.add_field(name="Followers", value=friends['target_follower_count'])
        embed.add_field(name="Tier", value=tier)

        embed.set_image(url=profile['profile_users'][0]['settings'][8]['value'])
        await interaction.response.send_message(embed=embed)
        #embed.

    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(name="getbannedxuids", description="Get the XUID of all banned users")
    async def getbannedxuids(self, interaction:discord.Interaction):
        data = await Nitrado.NitradoFunctions.getSettings()
        if self.gettingXUIDS == False:
            if data:
                banData = json.loads(data)['data']['gameserver']['settings']['general']['bans']
                if banData != '':
                    self.gettingXUIDS = True
                    banData = str(banData).replace("\\n",'\n').replace("\\r",'\r')
                    banData = banData.split('\r\n')
                    message = await interaction.channel.send(f"Collecting XUID for {len(banData)} users in banned list. This may take some time...")
                    await interaction.response.send_message("Processing.")
                    XuidList, total, FailedList, rate_limits, duplicates, added = await Xbox.Xbox.Client('BulkCheck', gamertaglist=banData, message=message)
                    if XuidList:
                        embed = discord.Embed(title=f"XUIDs Gathered!",description=f"XUID Gathering Stats:")
                        embed.add_field(name="Processing Stats",value=f"Processed a total of {total} gamertags")
                        embed.add_field(name="XUID Stats", value=f"{len(XuidList)} XUIDs found")
                        embed.add_field(name="Entries Stats", value=f"{added} Unique XUIDs Added to database")
                        embed.add_field(name="Not Found Stats", value=f"{FailedList} Invalid, or changed gamertags (Unobtainable XUID)")
                        embed.add_field(name="Rate Limit Stats", value=f"{rate_limits} Times rate limited by Xbox API")
                        embed.add_field(name="Duplicates Stats", value=f"{duplicates} duplicates found in your ban list. (Same person added more than once either XUID or gamertag)")
                        embed.color = discord.Color.random()
                        await interaction.channel.send(content=f'{interaction.user.mention}', embed=embed)
                        self.gettingXUIDS = False
                    else:
                        await interaction.channel.send(content="No banned users returned from Xbox API (Likely already changed gamertag).")
                        self.gettingXUIDS = False
                else:
                    await interaction.response.send_message("No banned users.")
                    self.gettingXUIDS = False
            else:
                await interaction.response.send_message("No data passed. Ensure Nitrado token, and Server ID is properly passed in Config")
                self.gettingXUIDS = False
        else:
            await interaction.response.send_message("Already gathering XUIDs from server's ban list")
        #await interaction.response.defer()

    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(name="cleardb", description="Clear the XUID of all users")
    async def cleardb(self, interaction:discord.Interaction):
        accounts = sqlite3.connect("db/accounts.db")
        ac = accounts.cursor()   
        ac.execute("DELETE FROM gamers")
        accounts.commit()
        await interaction.response.send_message(f"Deleted {ac.rowcount} from user Database")

    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.choices(choice=[
        app_commands.Choice(name="Add", value="Add XUID to ban list"),
        app_commands.Choice(name="Remove", value="Remove XUID from ban list"),
        ])
    @app_commands.command(name="bannedxuids", description="add/remove XUID from banned xuids")
    async def bannedxuid(self, interaction:discord.Interaction, choice:app_commands.Choice[str], xuid:int):
        bannedxuid = sqlite3.connect("db/bannedxuids.db")
        xu = bannedxuid.cursor()
        if choice.name == 'Remove':
            xu.execute(f"DELETE FROM bannedxuids WHERE xuid = ?", (int(xuid),))
            bannedxuid.commit()
            bannedxuid.close()
            if xu.rowcount > 0:
                await interaction.response.send_message(f'Removed {xuid} from banned database')
            else:
                await interaction.response.send_message(f'{xuid} not in database.')
        if choice.name == 'Add':
            gamertag = await Xbox.Xbox.Client('GetXUID', str(xuid))
            if gamertag:
                print(xu.execute("SELECT * FROM bannedxuids WHERE xuid = ?", (int(xuid),)).fetchall())
                if xu.execute("SELECT * FROM bannedxuids WHERE xuid = ?", (int(xuid),)).fetchall() == []:
                    xu.execute("INSERT INTO bannedxuids (user, xuid) VALUES (?, ?)", ('test', xuid))#(gamertag['profile_users'][0]['settings'][0]['value'], xuid))
                    bannedxuid.commit()
                    bannedxuid.close()
                    embed = discord.Embed(title=f"{gamertag['profile_users'][0]['settings'][0]['value']}",
                                  description=f"Added to banned XUID | {gamertag['profile_users'][0]['id']}")
                    embed.set_image(url=gamertag['profile_users'][0]['settings'][8]['value'])
                    embed.color = discord.Color.random()
                    await interaction.response.send_message(embed=embed)
                else:
                    await interaction.response.send_message(f"XUID {xuid} already in the banned database")
            else:
                await interaction.response.send_message("Invalid XUID. If you think this is a mistake try again in a few seconds.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.choices(action=[
        app_commands.Choice(name="Minimum Gamerscore", value="Set Minimum Gamerscore"),
        app_commands.Choice(name="Minimum Followers", value="Set Minimum Friends"),
        ])
    @app_commands.command(name="settings", description="Update flagging settings")
    async def settings(self, interaction:discord.Interaction, action:app_commands.Choice[str], amount:int):
        accounts = sqlite3.connect("db/accounts.db")
        ac = accounts.cursor()
        if action.name == 'Minimum Gamerscore':
            ac.execute("UPDATE settings SET mingamerscore = ?", (amount,))
            accounts.commit()
            accounts.close()
        if action.name == 'Minimum Followers':
            ac.execute("UPDATE settings SET minfollowers = ?", (amount,))
            accounts.commit()
            accounts.close()
        await interaction.response.send_message(f"Updated {action} to {amount}")

    #@app_commands.checks.has_permissions(administrator=True)
    #@app_commands.choices(action=[
    #    app_commands.Choice(name="Add", value="Set Minimum Gamerscore"),
    #    app_commands.Choice(name="Remove", value="Set Minimum Friends"),
    #    ])
    #@app_commands.command(name="banlist", description="Add user to banned XUID database")
    #async def settings(self, interaction:discord.Interaction, action:app_commands.Choice[str], amount:int):
    #    accounts = sqlite3.connect("db/accounts.db")
    #    ac = accounts.cursor()
    #    if action.name == 'Add':
    #        ac.execute("UPDATE settings SET mingamerscore = ?", (amount,))
    #        accounts.commit()
    #        accounts.close()
    #    if action.name == 'Remove':
    #        ac.execute("UPDATE settings SET minfriends = ?", (amount,))
    #        accounts.commit()
    #        accounts.close()
    #    await interaction.response.send_message(f"Updated {action} to {amount}")

    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.choices(action=[
        app_commands.Choice(name="Minimum Gamerscore", value="Set Minimum Gamerscore"),
        app_commands.Choice(name="Minimum Followers", value="Set Minimum Friends"),
        ])
    @app_commands.command(name="settings", description="Update flagging settings")
    async def settings(self, interaction:discord.Interaction, action:app_commands.Choice[str], amount:int):
        accounts = sqlite3.connect("db/accounts.db")
        ac = accounts.cursor()
        if action.name == 'Minimum Gamerscore':
            ac.execute("UPDATE settings SET mingamerscore = ?", (amount,))
            accounts.commit()
            accounts.close()
        elif action.name == 'Minimum Followers':
            ac.execute("UPDATE settings SET minfollowers = ?", (amount,))
            accounts.commit()
            accounts.close()
        await interaction.response.send_message(f"Updated {action.name} to {amount}")


    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(name="channel", description="Set warning channel")
    @app_commands.choices(choice=[
        app_commands.Choice(name="Warn", value="Warn Channel"),
        app_commands.Choice(name="Ban", value="Ban alert channel"),
        ])
    async def channel(self, interaction:discord.Interaction, choice:app_commands.Choice[str],  channel:discord.TextChannel):
        if choice.name == 'Warn':
            accounts = sqlite3.connect("db/accounts.db")
            ac = accounts.cursor()
            ac.execute("UPDATE settings SET channel = ?", (channel.id,))
            accounts.commit()
            accounts.close()
            await interaction.response.send_message(f"Sending warning to {channel.mention}.")
        if choice.name == 'Ban':
            accounts = sqlite3.connect("db/accounts.db")
            ac = accounts.cursor()
            ac.execute("UPDATE settings SET banchannel = ?", (channel.id,))
            accounts.commit()
            accounts.close()
            await interaction.response.send_message(f"Sending Banning to {channel.mention}.")
        #embed.
        
        #await interaction.response.send_message(friends.dict())
        

async def setup(bot):
    await bot.add_cog(Commands(bot))