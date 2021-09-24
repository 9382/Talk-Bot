from discord.ext import commands
from discord.ext import tasks
from datetime import datetime
from PIL import Image,ImageDraw,ImageFont,ImageChops
import re as regex
import traceback
import requests
import asyncio
import discord
import pyttsx3
import random
import math
import json
import time
import sys
import os
import io
prefix = "##"
def exists(table,value): #Wanna reduce the try except spam checking for possible values
    # "Why not use hasattr?" hasattr doesnt support numbers in dictionaries
    try:
        table[value]
        return True
    except:
        return False
def tempFile(extension="txt"):
    name = "storage/temp/"+str(time.time())+"."+extension
    open(name,"x")
    return name
def safeWriteToFile(filename,content,encoding="UTF-8"):
    backup = None
    if os.path.isfile(filename):
        try:
            backup = open(filename,"rb").read()
        except:
            print("[Safe Write] Failed to open",filename,"- Probably access issues")
            return
    try:
        file = open(filename,"w",encoding=encoding)
    except:
        print("[Safe Write] Failed to open",filename,"- Probably access issues")
        return
    try:
        file.write(content)
    except Exception as exc:
        file.close()
        if backup:
            open(filename,"wb").write(backup)
            print("[Safe Write] Failed to write to",filename,":",exc)
        else:
            print("[Safe Write] Failed to write to",filename,"with no backup available:",exc)
        return
    return True
def currentDate():
    return str(datetime.fromtimestamp(math.floor(time.time()))) #Long function list be like
fromdict = discord.Embed.from_dict
numRegex = regex.compile('\d+')
findMediaRegex = regex.compile("https?://((cdn|media)\.discordapp\.(com|net)/attachments/|tenor\.com/view/)")
colours = {'info':0x5555DD,'error':0xFF0000,'success':0x00FF00,'warning':0xFFAA00,'plain':0xAAAAAA}
guildMegaTable = {} # All in one
class FilteredMessage:
    def __init__(self,expirey,msgid=None,channelid=None,messageObj=None):
        if messageObj:
            msgid = messageObj.id
            channelid = messageObj.channel.id
        self.Deletion = expirey
        self.Message = messageObj # Do not get directly, use GetMessageObj
        self.MessageId = msgid
        self.Channel = channelid
    def GetMessageObj(self):
        if self.Message:
            return self.Message
        channel = client.get_channel(self.Channel)
        if channel:
            messageObj = discord.PartialMessage(channel=channel,id=self.MessageId)
            self.Message = messageObj
            return messageObj
    def Expired(self):
        return time.time() > self.Deletion
class Confirmation: # For commands like panic (when it exists)
    def __init__(self,msg,args,function):
        self.msg = msg
        self.args = args
        self.Function = function
        self.Expirey = time.time()+20
    async def Alert(self):
        if not self.Expired():
            await self.msg.channel.send("Woah, are you sure? Reply (y/yes) or (n/no) - Expires in 20 seconds",delete_after=self.Expirey-time.time())
    def Expired(self):
        return time.time() > self.Expirey
    async def Check(self,msg):
        content = msg.content.lower()
        if content == "yes" or content == "y":
            await msg.channel.send("Alright, continuing...")
            await self.Function(self.msg,self.args)
        else:
            await msg.channel.send("Alright, aborting...",delete_after=5)
class GuildObject: #Why didnt i do this before? Python is class orientated anyways
    def __init__(self,gid):
        self.Guild = gid
        self.WordBlockList = {}
        self.NSFWBlockList = []
        self.InviteTrack = None
        self.LogChannel = None
        self.MediaFilters = {}
        self.ChannelClearList = {}
        self.QueuedChannels = {}
        self.LoggedMessages = []
        self.Confirmations = {}
        guildMegaTable[gid] = self
    async def Log(self,content=None,embed=None):
        if self.LogChannel:
            channel = client.get_channel(self.LogChannel)
            if channel:
                try:
                    await channel.send(content=content,embed=embed)
                except:
                    pass
    def GetMediaFilter(self,channel):
        if exists(self.MediaFilters,channel):
            return self.MediaFilters[channel]
    def AddChannelClear(self,channel,cycle): # Why in a function? Cause its easier to handle QueuedChannels this way
        self.ChannelClearList[channel] = cycle
        self.QueuedChannels[channel] = time.time()+cycle
    def RemoveChannelClear(self,channel): # Read above
        if exists(self.ChannelClearList,channel):
            self.ChannelClearList.pop(channel)
        if exists(self.QueuedChannels,channel):
            self.QueuedChannels.pop(channel)
    async def AddToFilter(self,msg,buffer):
        if not buffer: # Failsafe, just in case
            return
        print("[Filter] Msg Filtered ->",msg.content)
        if buffer <= 0:
            try:
                asyncio.run(msg.delete())
                return buffer
            except:
                pass
        self.LoggedMessages.append(FilteredMessage(time.time()+buffer,messageObj=msg))
        return buffer
    async def FilterMessage(self,msg,forced=False): # Now guild specific, how nice :)
        if exists(self.LoggedMessages,msg):
            return time.time()-self.LoggedMessages[msg]
        if type(forced) == type(0):
            return await self.AddToFilter(msg,forced)
        for word in self.WordBlockList:
            buffer = self.WordBlockList[word] # Should never be None now, hopefully
            if msg.content.lower().find(word) != -1:
                return await self.AddToFilter(msg,buffer)
            for embed in msg.embeds:
                if embed.title and embed.title.lower().find(word) != -1:
                    return await self.AddToFilter(msg,buffer)
                if embed.description and embed.description.lower().find(word) != -1:
                    return await self.AddToFilter(msg,buffer)
        buffer = self.GetMediaFilter(msg.channel.id)
        if buffer != None:
            if findMediaRegex.search(msg.content.lower()):
                return await self.AddToFilter(msg,buffer)
            for i in msg.attachments:
                if findMediaRegex.search(i.url.lower()):
                    return await self.AddToFilter(msg,buffer)
            for embed in msg.embeds:
                if embed.image:
                    return await self.AddToFilter(msg,buffer)
    def CachedLoggedMessages(self):
        return self.LoggedMessages
    def FormatLoggedMessages(self):
        LoggedMessagesSave = {}
        for message in self.CachedLoggedMessages():
            if not exists(LoggedMessagesSave,message.Channel):
                LoggedMessagesSave[message.Channel] = {}
            LoggedMessagesSave[message.Channel][message.MessageId] = message.Deletion
        return LoggedMessagesSave
    def CreateSave(self):
        return {"Guild":self.Guild,
                "WordBlockList":self.WordBlockList,
                "ChannelClearList":self.ChannelClearList,
                "NSFWBlockList":self.NSFWBlockList,
                "LogChannel":self.LogChannel,
                "MediaFilters":self.MediaFilters,
                "QueuedChannels":self.QueuedChannels,
                "LoggedMessages":self.FormatLoggedMessages()
        } #How lovely
    def LoadSave(self,data):
        try:
            self.WordBlockList = data["WordBlockList"]
            self.ChannelClearList = data["ChannelClearList"]
            self.NSFWBlockList = data["NSFWBlockList"]
            self.LogChannel = data["LogChannel"]
            self.MediaFilters = data["MediaFilters"]
            self.QueuedChannels = data["QueuedChannels"]
            self.LoggedMessages = []
            for channel in data["LoggedMessages"]:
                for message in data["LoggedMessages"][channel]:
                    expirey = data["LoggedMessages"][channel][message]
                    self.LoggedMessages.append(FilteredMessage(expirey,int(message),int(channel)))
        except:
            print("[GuildObject] Invalid data:",data)
    async def CreateConfirmation(self,msg,args,function):
        confirmationObj = Confirmation(msg,args,function)
        self.Confirmations[msg.author.id] = confirmationObj
        await confirmationObj.Alert()
        return confirmationObj
    async def CheckConfirmation(self,msg):
        user = msg.author
        confirmationObj = exists(self.Confirmations,user.id) and self.Confirmations[user.id]
        if not confirmationObj:
            return
        if confirmationObj.Expired():
            self.Confirmations.pop(user.id)
            return
        await confirmationObj.Check(msg)
        self.Confirmations.pop(user.id)
        return True
def checkMegaTable(gid):
    if not exists(guildMegaTable,gid):
        guildMegaTable[gid] = GuildObject(gid)
def getMegaTable(obj):
    gid = None
    if type(obj) == discord.Message or type(obj) == discord.PartialMessage:
        gid = obj.guild.id
    if type(obj) == discord.Guild:
        gid = obj.id
    if type(obj) == type(0):
        gid = obj
    if gid:
        checkMegaTable(gid)
        return guildMegaTable[gid]
async def getGuildInviteStats(guild):
    toReturn = {}
    try:
        invites = await guild.invites()
    except:
        return
    for invite in invites:
        toReturn[invite.id] = {"m":invite.inviter,"u":invite.uses}
    return toReturn
multList = {"s":1,"m":60,"h":3600,"d":86400}
def strToTimeAdd(duration):
    timeMult = duration[-1].lower()
    timeAmount = duration[:-1]
    try:
        timeAmount = int(timeAmount)
    except:
        return False,"timeAmount must be an integer"
    if timeMult in multList:
        return True,timeAmount*multList[timeMult]
    else:
        return False,"Time period must be s, m, h or d"
def simplifySeconds(seconds): #Feels like it could be cleaner, but eh
    if seconds <= 0:
        return "0 seconds"
    days = seconds//86400
    seconds = seconds - 86400*days
    hours = seconds//3600
    seconds = seconds - 3600*hours
    minutes = seconds//60
    seconds = seconds - 60*minutes
    returnString = ""
    parts = 0
    if seconds > 0:
        returnString = str(seconds)+" second(s)"
        parts += 1
    if minutes > 0:
        if parts == 0:
            returnString = str(minutes)+" minute(s)"+returnString
        else:
            returnString = str(minutes)+" minute(s) and "+returnString
        parts += 1
    if hours > 0:
        if parts == 0:
            returnString = str(hours)+" hour(s)"+returnString
        elif parts == 1:
            returnString = str(hours)+" hour(s) and "+returnString
        else:
            returnString = str(hours)+" hour(s), "+returnString
        parts += 1
    if days > 0:
        if parts == 0:
            returnString = str(days)+" day(s)"+returnString
        elif parts == 1:
            returnString = str(days)+" day(s) and "+returnString
        else:
            returnString = str(days)+" day(s), "+returnString
    return returnString
client = commands.Bot(command_prefix=prefix,help_command=None,intents=discord.Intents(guilds=True,messages=True,members=True))
#Note that due to the on_message handler, i cant use the regular @bot.event shit, so custom handler it is
logChannels = {'errors':872153712347467776,'boot-ups':872208035093839932} # These are different from the guild-defined LogChannel channels, these are for the bot to tell me whats wrong or ok
@client.event
async def on_error(error,*args,**kwargs):
    if exists(args,0):
        causingCommand = args[0].content
    else:
        causingCommand = "<none>"
    print("[Fatal Error] Causing command:",causingCommand,"error:")
    traceback.print_exc(file=sys.stderr)
    try: #Logging
        errorFile = tempFile()
        file = open(errorFile,"w",encoding="ANSI")
        try:
            traceback.print_exc(file=file)
        except Exception as exc:
            print("[Fatal Error] Error Log file failed to write:",exc)
            pass
        file.close()
        await client.get_channel(logChannels['errors']).send("Error in client\nTime: "+currentDate()+"\nCausing command: "+causingCommand,file=discord.File(errorFile))
        os.remove(errorFile)
    except Exception as exc:
        print("[Fatal Error] Failed to log:",exc)
@client.event
async def on_ready():
    await client.change_presence(activity=discord.Game(name='##cmds'))
    print('connected v'+discord.__version__)
    try: #Notifying of start-up
        await client.get_channel(logChannels['boot-ups']).send("Ive connected at "+currentDate())
    except:
        print("Failed to alert of bootup at",currentDate())
@client.event
async def on_guild_join(guild):
    guildMegaTable[guild.id] = GuildObject(guild.id) # Force default settings
    getMegaTable(guild).InviteTrack = await getGuildInviteStats(guild)
@client.event
async def on_member_join(member):
    guild = member.guild
    gmt = getMegaTable(guild)
    if not gmt.InviteTrack:
        gmt.InviteTrack = await getGuildInviteStats(guild)
        return
    invitesBefore = gmt.InviteTrack
    invitesAfter = await getGuildInviteStats(guild)
    if not invitesAfter:
        return
    for inviteId in invitesAfter:
        inviteInfo = invitesAfter[inviteId]
        if not exists(invitesBefore,inviteId):
            invitesBefore[inviteId] = {"m":inviteInfo["m"],"u":0}
        if invitesBefore[inviteId]["u"] < inviteInfo["u"]:
            await gmt.Log(embed=fromdict({"title":"Invite Log","description":f"User <@{member.id}> ({member}) has joined through <@{inviteInfo['m'].id}> ({inviteInfo['m']})'s invite (discord.gg/{inviteId})\nInvite is at {inviteInfo['u']} uses","color":colours["info"]}))
            break
    gmt.InviteTrack = invitesAfter
def findVoiceClient(guildId): #Find the relevant voice client object for the specified guild. Returns None if none are found
    for voiceObj in client.voice_clients:
        if voiceObj.guild.id == guildId:
            return voiceObj
VCList = {}
async def connectToVC(channel,idleTimeout=60,ignorePlaying=False):
    vc = findVoiceClient(channel.guild.id)
    if vc:
        if vc.is_playing():
            if not ignorePlaying:
                return
            else:
                vc.stop()
        await vc.move_to(channel)
    else:
        vc = await channel.connect()
    if not exists(VCList,vc):
        VCList[vc] = {}
    VCList[vc]["idleTimeout"] = idleTimeout
    VCList[vc]["lastActiveTime"] = time.time()
    return vc
devCommands = {} #basically testing and back-end commands
adminCommands = {} #This will take priority over user commands should a naming conflict exist
userCommands = {}
class Command:
    def __init__(self,cmd,function,ratelimit,description,descriptionArgs,extraArg,group,descriptionReference=None):
        if type(cmd) == type([]): #Probably a table, probably declaring multiple aliases
            for cmdalias in cmd:
                Command(cmdalias,function,ratelimit,description,descriptionArgs,extraArg,group,descriptionReference) #Encourages self calling but oh well who cares, shouldnt self-call more than once
                descriptionReference = descriptionReference or cmdalias
            return
        self.Name = cmd
        self.Function = function
        self.RateLimit = ratelimit
        self.Description = description
        self.DescArgs = descriptionArgs
        self.ExtraArg = extraArg
        self.Group = group
        self.RateLimitList = {}
        wantedTable = None
        if group == "dev":
            wantedTable = devCommands
        elif group == "admin":
            wantedTable = adminCommands
        else:
            wantedTable = userCommands
        if exists(wantedTable,cmd):
            print(f"[AddCmd] Command {cmd} was declared twice")
        wantedTable[cmd] = self
    async def Run(self,msg,args):
        user = msg.author
        if exists(self.RateLimitList,user.id):
            rlInfo = self.RateLimitList[user.id]
            if rlInfo["t"] > time.time():
                if not rlInfo["r"]:
                    self.RateLimitList[user.id]["r"] = True
                    return False,rlInfo["t"]-time.time()
                else:
                    return False,-1
        self.RateLimitList[user.id] = {"t":time.time()+self.RateLimit,"r":False}
        if self.ExtraArg:
            await self.Function(msg,args,self.ExtraArg)
        else:
            await self.Function(msg,args)
        return True,0
async def doTheCheck(msg,args,commandTable): #Dont wanna type this 3 times
    arg0 = args[0]
    if '\n' in arg0:
        args[0] = arg0.split('\n')[0]
        args.insert(1,arg0.split('\n')[1])
    for command in commandTable:
        if prefix+command == args[0]:
            success,result = await commandTable[command].Run(msg,args)
            if not success:
                if result != -1: # If first repeat:
                    await msg.channel.send(embed=fromdict({'title':'Slow Down','description':'That command is limited for '+simplifySeconds(math.floor(result))+' more seconds','color':colours['warning']}),delete_after=result)
            return True
@client.event
async def on_message(msg):
    if not msg.guild or msg.author.id == client.user.id: #Only do stuff in guild, ignore messages by the bot
        if msg.guild:
            await getMegaTable(msg).FilterMessage(msg)
        elif msg.author.id != client.user.id:
            await msg.channel.send(embed=fromdict({'title':'Not here','description':'This bot can only be used in a server, and not dms','color':colours['error']}))
        return
    await getMegaTable(msg).FilterMessage(msg)
    gmt = getMegaTable(msg)
    await gmt.FilterMessage(msg)
    if type(msg.author) == discord.User: #Webhook
        return
    if await gmt.CheckConfirmation(msg):
        return
    args = msg.content.split(' ') #Please keep in mind the first argument is the calling command
    if msg.author.id == 260016427900076033:
        if await doTheCheck(msg,args,devCommands):
            return
    if msg.author.guild_permissions.administrator:
        if await doTheCheck(msg,args,adminCommands):
            return
    await doTheCheck(msg,args,userCommands)
@client.event
async def on_raw_message_edit(msg): #On message edit to avoid bypassing
    try:
        messageObj = await discord.PartialMessage(channel=client.get_channel(int(msg.data['channel_id'])),id=int(msg.data['id'])).fetch()
    except:
        pass #Dont care if this errors since it bloody will and its not an issue
    else:
        await getMegaTable(messageObj).FilterMessage(messageObj)
async def cloneChannel(channelid):
    try:
        channel = client.get_channel(channelid)
        newchannel = await channel.clone(reason="Recreating text channel")
        await channel.delete()
        newchannel.position = channel.position #Because clone doesnt include position
        await newchannel.send(embed=fromdict({'title':'Success','description':channel.name+' has been re-made and cleared','color':colours['success']}),delete_after=60)
        print("[CloneChannel] Successfully cloned channel",channel.name)
        return newchannel
    except Exception as exc:
        print("[CloneChannel] Exception:",str(exc))
stopCycling = False
finishedLastCycle = False
@tasks.loop(seconds=1)
async def constantMessageCheck(): #For message filter. Possibly in need of a re-work
    global finishedLastCycle
    if stopCycling:
        finishedLastCycle = True
        return
    try:
        toDeleteList = {}
        for guild in guildMegaTable:
            gmt = guildMegaTable[guild]
            for message in gmt.CachedLoggedMessages():
                if message.Expired():
                    messageObj = message.GetMessageObj()
                    if messageObj:
                        if not exists(toDeleteList,message.Channel):
                            toDeleteList[message.Channel] = []
                        toDeleteList[message.Channel].append(messageObj)
                        gmt.LoggedMessages.remove(message)
        if toDeleteList != {}:
            for channel in toDeleteList:
                try:
                    await client.get_channel(channel).delete_messages(toDeleteList[channel])
                except:
                    pass
    except Exception as exc:
        print("[LoggedMessages] Exception:",exc)
@tasks.loop(seconds=10)
async def constantChannelCheck(): #For queued channel clearing
    try:
        for guild in client.guilds:
            gmt = getMegaTable(guild)
            guildChannelList = guild.text_channels
            for channel in guildChannelList:
                if not exists(gmt.QueuedChannels,channel.name):
                    continue
                channelTime = gmt.QueuedChannels[channel.name]
                if channelTime < time.time():
                    gmt.QueuedChannels[channel.name] = time.time()+gmt.ChannelClearList[channel.name]
                    await cloneChannel(channel.id)
    except Exception as exc:
        print("[!] ChannelClear Exception:",exc)
@tasks.loop(seconds=90)
async def updateConfigFiles(): #So i dont have pre-coded values
    try:
        for guild in client.guilds:
            safeWriteToFile("storage/settings/"+str(guild.id)+".json",json.dumps(getMegaTable(guild).CreateSave()))
    except Exception as exc:
        print("[!] UpdateConfig Exception:",exc)
        await asyncio.sleep(1)
@tasks.loop(seconds=2)
async def VCCheck():
    try:
        for vc in VCList:
            if vc.is_playing():
                VCList[vc]["lastActiveTime"] = time.time()
            elif time.time()-VCList[vc]["idleTimeout"] > VCList[vc]["lastActiveTime"]:
                await vc.disconnect()
    except Exception as exc:
        print("[! VCCheck Exception:",exc)
@tasks.loop(seconds=5)
async def keepGuildInviteUpdated():
    for guild in client.guilds:
        gmt = getMegaTable(guild)
        if not gmt.InviteTrack:
            gmt.InviteTrack = await getGuildInviteStats(guild)
constantMessageCheck.start()
constantChannelCheck.start()
updateConfigFiles.start()
VCCheck.start()
keepGuildInviteUpdated.start()

async def forceUpdate(msg,args):
    global stopCycling
    print("Client was force-exited via forceUpdate()",time.time())
    print("Hanging until messageCheck has finished its cycle or 20s, whatever is shorter")
    stopCycling = True
    sleepTime = 0
    while True:
        if finishedLastCycle == True or sleepTime>=20: #? idk
            break
        sleepTime+=1
        await asyncio.sleep(1)
    print("Invoking save - sleep time:",sleepTime)
    await updateConfigFiles()
    print("Save finished")
    print("Closing")
    await client.close()
Command("d -update",forceUpdate,0,"Updates the bot, force saving configs",{},None,"dev")

async def cmds(msg,args): # Group specific
    cmdList = {"admin":adminCommands}
    for command in userCommands:
        cmdInfo = userCommands[command]
        if not exists(cmdList,cmdInfo.Group):
            cmdList[cmdInfo.Group] = {}
        cmdList[cmdInfo.Group][command] = cmdInfo
    if exists(args,1):
        group = exists(cmdList,args[1]) and cmdList[args[1]]
        if not group: # Stupid
            await msg.channel.send(embed=fromdict({"title":"Invalid group","description":f"The group '{args[1]}' doesnt exist","color":colours["error"]}))
            return
        finalText = "**Syntax**\n`<>` is a required argument, `[]` is an optional argument\n\n**Commands**" # Copied from old version - maybe revisit
        for command in group:
            cmdInfo = group[command]
            argMessageContent = ""
            for argName in cmdInfo.DescArgs:
                argRequired = cmdInfo.DescArgs[argName]
                argMessageContent += " "+((argRequired and f"<{argName}>") or f"[{argName}]")
            finalText += "\n`"+command+argMessageContent+"` - "+cmdInfo.Description
        await msg.channel.send(embed=fromdict({"title":"Commands within "+args[1],"description":finalText,"color":colours["info"]}))
    else: # Generalised (No group)
        finalText = f"do `{args[0]} <group> to get more information on a group`"
        for group in cmdList:
            finalText += f"\n**{group}**\n"
            for command in cmdList[group]:
                finalText += f"`{command}` "
        await msg.channel.send(embed=fromdict({"title":"Commands","description":finalText[1:],"color":colours["info"]})) # [1:] to avoid extra \n
Command(["commands","cmds"],cmds,1,"List all commands",{"group":False},None,"general")

async def setLogChannel(msg,args):
    if not exists(args,1):
        await msg.channel.send(embed=fromdict({"title":"No channel","description":"Please provide a channel, either by mentioning it or by putting its ID","color":colours["error"]}))
        return
    wantedChannel = numRegex.search(args[1]) and client.get_channel(int(numRegex.search(args[1]).group()))
    if not wantedChannel:
        await msg.channel.send(embed=fromdict({"title":"Not found","description":"The channel provided either doesnt exist, or i cant access it","color":colours["error"]}))
        return
    if wantedChannel.guild.id != msg.guild.id:
        await msg.channel.send(embed=fromdict({"title":"No","description":"Your log channel must be in your guild, not someone else's","color":colours["error"]}))
        return
    getMegaTable(msg).LogChannel = wantedChannel.id
    await msg.channel.send(embed=fromdict({"title":"Success","description":"Set log channel successfully","color":colours["success"]}))
Command("setlogs",setLogChannel,3,"Set the log channel to the channel provided",{"channel":True},None,"admin")

async def clearAllInvites(msg,args):
    try:
        invites = await msg.guild.invites()
    except:
        await msg.channel.send("Failed to get invites")
    else:
        for invite in invites:
            try:
                await invite.delete()
            except:
                print(":(")
            else:
                print(":)")
Command("clearinvites",clearAllInvites,5,"Clears all invites in the server, deleting them",{},None,"admin")

async def blockWord(msg,args):
    if not exists(args,2):
        await msg.channel.send(embed=fromdict({'title':'Error','description':'You must include a word to ban and its time until deletion','color':colours['error']}),delete_after=10)
        return
    success,result = strToTimeAdd(args[2])
    if not success:
        await msg.channel.send(embed=fromdict({'title':'Error','description':result,'color':colours['error']}),delete_after=10)
        return
    word = args[1].lower()
    getMegaTable(msg).WordBlockList[word] = result
    await msg.channel.send(embed=fromdict({'title':'Success','description':'Any messages containing '+word+' will be deleted after '+simplifySeconds(result),'color':colours['success']}))
Command("blockword",blockWord,0,"Add a word to the filter list",{"word":True,"deletion time":True},None,"admin")
async def unblockWord(msg,args):
    if not exists(args,1):
        await msg.channel.send(embed=fromdict({'title':'Error','description':'You must include a word to unban','color':colours['error']}),delete_after=10)
        return
    word = args[1].lower()
    try:
        getMegaTable(msg).WordBlockList.pop(word)
    except:
        await msg.channel.send(embed=fromdict({'title':'Not Blocked','description':f'{word} was not blocked','color':colours['success']}))
    else:
        await msg.channel.send(embed=fromdict({'title':'Success','description':f'{word} is allowed again','color':colours['success']}))
Command("unblockword",unblockWord,0,"Remove a word from the filter list",{"word":True},None,"admin")

async def list_admin(msg,args): # God this looks horrible. NOTE: Patch this up at some point NOTE 2: Maybe patchable with GMT :)
    if len(args) < 2:
        await msg.channel.send(embed=fromdict({'title':'Settings List','description':'To get a list of what you are looking for, please use one of the following sub-commands:\n`list words`\n`list channels`\n`list tags`','color':colours['info']}))
        return
    gmt = getMegaTable(msg)
    index = 0
    finalMessage = ""
    if args[1] == "words":
        for i in gmt.WordBlockList:
            if gmt.WordBlockList[i] != None:
                index += 1
                finalMessage = finalMessage+'\n#'+str(index)+' - "'+i+'" '+simplifySeconds(gmt.WordBlockList[i])
        await msg.channel.send(embed=fromdict({'title':'Blocked Word List','description':f'List of banned words, and how long until the message gets deleted:{finalMessage}','color':colours['info']}))
    elif args[1] == "channels":
        for i in gmt.ChannelClearList:
            if gmt.ChannelClearList:
                index += 1
                finalMessage = finalMessage+'\n#'+str(index)+' - "'+i+'" every '+simplifySeconds(gmt.ChannelClearList[i])
        await msg.channel.send(embed=fromdict({'title':'Clear Channel List','description':f'List of channels that are set to clear every so often:{finalMessage}','color':colours['info']}))
    elif args[1] == "tags":
        for i in gmt.NSFWBlockList:
            index += 1
            finalMessage = finalMessage+'\n#'+str(index)+' - "'+i+'"'
        await msg.channel.send(embed=fromdict({'title':'Blocked Tags List','description':f'List of tags that are blocked on the NSFW commands:{finalMessage}','color':colours['info']}))
    else:
        await msg.channel.send(embed=fromdict({'title':'Settings List','description':'To get a list of what you are looking for, please use one of the following sub-commands:\n`list words`\n`list channels`\n`list tags`','color':colours['info']}))
        return
Command("list",list_admin,0,"View the list of settings to do with administration",{"subsection":False},None,"admin")

async def clearChannel(msg,args):
    if len(args) < 2:
        await msg.channel.send(embed=fromdict({'title':'Error','description':'You must include a channel name','color':colours['error']}),delete_after=30)
        return
    channelName = args[1] # Cant do ID cause deleting a channel removes the ID :)
    frequency = exists(args,2) and args[2]
    if frequency:
        success,result = strToTimeAdd(frequency)
        if not success:
            await msg.channel.send(embed=fromdict({'title':'Error','description':result,'color':colours['error']}),delete_after=30)
            return
        if result < 300:
            await msg.channel.send(embed=fromdict({'title':'Too short','description':'The minimum frequency time is 5 minutes','color':colours['error']}),delete_after=30)
            return
        getMegaTable(msg).AddChannelClear(channelName,result)
        await msg.channel.send(embed=fromdict({'title':'Success','description':channelName+' is queued to clear every '+simplifySeconds(result),'color':colours['success']}))
    else:
        guildChannelList = msg.guild.text_channels
        for t in guildChannelList:
            if channelName == t.name:
                await cloneChannel(t.id)
Command("clearchannel",clearChannel,0,"Add a channel to be cleared every so often OR clear now (no frequency)",{"channelName":True,"frequency":False},None,"admin")
async def unclearChannel(msg,args):
    if len(args) < 2:
        await msg.channel.send(embed=fromdict({'title':'Error','description':'You must include a channel name to stop clearing','color':colours['error']}),delete_after=30)
        return
    channelName = args[1]
    getMegaTable(msg).RemoveChannelClear(channelName)
    await msg.channel.send(embed=fromdict({'title':'Success','description':channelName+' will no longer be cleared','color':colours['success']}))
Command("unclearchannel",unclearChannel,0,"Stop a channel from being auto-cleared",{"channelName":True},None,"admin")

async def publicVote(msg,args):
    if len(args) < 2:
        await msg.channel.send(embed=fromdict({'title':'Error','description':'You gotta include the thing to vote on','color':colours['error']}),delete_after=30)
        return
    attachments = msg.attachments
    imageUrl = (exists(attachments,0) and attachments[0].url) or ""
    author = msg.author
    wantedReactions = []
    findWantedReaction = regex.compile('^{[^\]]+}$')
    index = -1
    for i in args: #Get user-defined reactions ( [:reaction:] )
        index += 1
        if findWantedReaction.search(i):
            wantedReactions.append(i[1:-1])
            args[index] = None
    args[0] = None
    msgContent = ""
    for i in args:
        if i: #mhm
            msgContent = msgContent + i + " "
    voteMsg = await msg.channel.send(embed=fromdict({'author':{'name':author.name+"#"+author.discriminator+' is calling a vote','icon_url':str(author.avatar_url)},'description':msgContent,'image':{'url':imageUrl},'color':colours['info']}))
    try:
        await msg.delete()
    except:
        pass
    if wantedReactions == []:
        await voteMsg.add_reaction("⬆️")
        await voteMsg.add_reaction("⬇")
    else:
        for i in wantedReactions:
            try:
                await voteMsg.add_reaction(i)
            except:
                pass #User input sanitasion cause some guys gonna go [haha]
Command("vote",publicVote,10,"Make a public vote about anything with an optional image",{"text":True,"imagefile":False},None,"general")

async def blockMedia(msg,args):
    if len(args) < 2:
        await msg.channel.send(embed=fromdict({'title':'Error','description':'You must include the time until deletion','color':colours['error']}),delete_after=10)
        return
    success,result = strToTimeAdd(args[1])
    if not success:
        await msg.channel.send(embed=fromdict({'title':'Error','description':result,'color':colours['error']}),delete_after=30)
        return
    getMegaTable(msg).MediaFilters[msg.channel.id] = result
    await msg.channel.send(embed=fromdict({'title':'Success','description':'All media will be deleted after '+simplifySeconds(result),'color':colours['success']}))
Command("blockmedia",blockMedia,0,"Remove all media in a channel after a certain duration",{"deletiontime":True},None,"admin")
async def unblockMedia(msg,args):
    getMegaTable(msg).MediaFilters.pop(msg.channel.id)
    await msg.channel.send(embed=fromdict({'title':'Success','description':'Media will no longer be removed','color':colours['success']}))
Command("unblockmedia",unblockMedia,0,"Stop auto-filtering a channel's media",{},None,"admin")

print('attempting import')
''' Load modules from the modules folder
Only use this for storing commands that dont rely on other commands, as load order is random
This is so i dont clog up the entirety of this main script with like 2k lines
The main code can be found in modules/__main__.py '''
from modules.__main__ import load_modules
def loadModules(origin=None):
    exec_list = load_modules(origin)
    for contents in exec_list:
        try:
            exec(contents,globals())
        except Exception as exc:
            print("[Modules] Module import error ->",exc)
loadModules("Main")
async def loadModulesAsync(msg,args):
    loadModules("User "+msg.author.name)
Command("d -reload modules",loadModulesAsync,0,"Reloads all the modules",{},None,"dev")

print('done commands')
for i in os.listdir('storage/settings'):
    try:
        j = json.loads(open('storage/settings/'+i).read())
    except:
        print("[JSON] Load failed for file",i)
    else:
        getMegaTable(j['Guild']).LoadSave(j)
print('loaded config')