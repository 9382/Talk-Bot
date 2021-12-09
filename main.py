from discord.ext import commands
from discord.ext import tasks
from datetime import datetime
import re as regex
import traceback
import asyncio
import discord
import random
import math
import json
import time
import sys
import os
prefix = "##"
DevID = 260016427900076033
logChannels = {"errors":872153712347467776,"boot-ups":872208035093839932} # These are different from the guild-defined LogChannel channels, these are essentially telemetry
colours = {"info":0x5555DD,"error":0xFF0000,"success":0x00FF00,"warning":0xFFAA00,"plain":0xAAAAAA}

#Base functions
def exists(table,value):
    try:
        table[value]
        return True
    except:
        return False
def tempFile(extension="txt"):
    name = f"storage/temp/{time.time()}.{extension}"
    open(name,"x")
    return name
def currentDate():
    return str(datetime.fromtimestamp(time.time()//1))
def safeWriteToFile(filename,content,mode="w",encoding="UTF-8"):
    #Writes contents to a file, auto-creating the directory should it be missing
    try:
        os.makedirs("/".join(filename.replace("\\","/").split("/")[:-1]),exist_ok=True)
    except:
        return False,f"Couldnt make directory for {filename}"
    try:
        file = open(filename,mode,encoding=encoding,newline="")
    except:
        return False,f"Failed to open {filename}"
    try:
        file.write(content)
    except Exception as exc:
        file.close()
        return False,f"Failed to write content for {filename}"
    file.close()
    return True,f"Successfully wrote to {filename}"
def log(content):
    print(f"[Log {currentDate()[11:]}]",content)
    success,result = safeWriteToFile(f"storage/logs/{currentDate()[:10]}.log",f"[{currentDate()[11:]}] {content}\n","a")
    if not success:
        print(f"[Log {currentDate()[11:]}] Failed to write to log file: {result}")
    return success
log(f"Starting main - the time is {time.time()} or {currentDate()}")
timeMultList = {"s":1,"m":60,"h":3600,"d":86400}
def strToTimeAdd(duration):
    timeMult = duration[-1].lower()
    timeAmount = duration[:-1]
    try:
        timeAmount = int(timeAmount)
    except:
        return False,"timeAmount must be an integer"
    if timeMult in timeMultList:
        return True,timeAmount*timeMultList[timeMult]
    else:
        return False,"Time period must be s, m, h or d"
def simplifySeconds(seconds): #Feels like it could be cleaner, but eh
    if seconds <= 0:
        return "0 seconds"
    days,seconds = seconds//86400,seconds%86400
    hours,seconds = seconds//3600,seconds%3600
    minutes,seconds = seconds//60,seconds%60
    returnString = ""
    p = 0
    if seconds > 0:
        returnString = str(seconds)+" second(s)"
        p += 1
    if minutes > 0:
        returnString = (p==0 and str(minutes)+" minute(s)") or str(minutes)+" minute(s) and "+returnString
        p += 1
    if hours > 0:
        returnString = (p==0 and str(hours)+" hour(s)") or (p==1 and str(hours)+" hour(s) and "+returnString) or str(hours)+" hour(s), "+returnString
        p += 1
    if days > 0:
        returnString = (p==0 and str(days)+" day(s)") or (p==1 and str(days)+" day(s) and "+returnString) or str(days)+" day(s), "+returnString
    return returnString
fromdict = discord.Embed.from_dict
numRegex = regex.compile("\d+")
findMediaRegex = regex.compile("https?://((cdn|media)\.discordapp\.(com|net)/attachments/|tenor\.com/view/)") #See FilterMessage

#GMT
guildMegaTable = {}
class FilteredMessage:
    #Object used to represent a filtered message
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
class Confirmation:
    #Asks the user to confirm their action. See GuildObject for use
    def __init__(self,msg,args,function):
        self.msg = msg
        self.args = args
        self.Function = function
        self.Expirey = time.time()+20
    async def Alert(self):
        if not self.Expired():
            await self.msg.channel.send("Hey, are you sure? Reply (y/yes) or (n/no) - Expires in 20 seconds",delete_after=self.Expirey-time.time())
    def Expired(self):
        return time.time() > self.Expirey
    async def Check(self,msg):
        content = msg.content.lower()
        if content == "yes" or content == "y":
            await msg.channel.send("Alright, continuing...")
            await self.Function(self.msg,self.args)
        else:
            await msg.channel.send("Alright, aborting...",delete_after=5)
class GuildObject:
    #The main object used to reference a guild and its settings
    def __init__(self,gid):
        self.Guild = gid
        self.WordBlockList = {}
        self.NSFWBlockList = []
        self.InviteTrack = None
        self.LogChannel = None
        self.MediaFilters = {}
        self.ChannelClearList = {}
        self.QueuedChannels = {}
        self.LoggedMessages = {}
        self.Confirmations = {}
        self.ChannelLimits = {}
        self.ProtectedMessages = []
        if exists(guildMegaTable,gid):
            log(f"[GMT] Guild {gid} was declared twice")
        guildMegaTable[gid] = self
    async def Log(self,content=None,embed=None):
        #Logs content to a server's set log channel
        if self.LogChannel:
            channel = client.get_channel(self.LogChannel)
            if channel:
                await channel.send(content=content,embed=embed)
                return True
    def GetMediaFilter(self,channel):
        if exists(self.MediaFilters,channel):
            return self.MediaFilters[channel]
    def AddChannelClear(self,channel,cycle):
        #This helps handle QueuedChannels
        self.ChannelClearList[channel] = cycle
        self.QueuedChannels[channel] = time.time()+cycle
    def RemoveChannelClear(self,channel):
        #Read above
        if exists(self.ChannelClearList,channel):
            self.ChannelClearList.pop(channel)
        if exists(self.QueuedChannels,channel):
            self.QueuedChannels.pop(channel)
    async def AddToFilter(self,msg,buffer): 
        #Helper of FilterMessage
        print("[Filter] Msg Filtered ->",buffer,msg.content)
        if buffer <= 0:
            try:
                await msg.delete()
                return buffer
            except:
                pass
        self.LoggedMessages[msg.id] = FilteredMessage(time.time()+buffer,messageObj=msg)
        return buffer
    async def FilterMessage(self,msg,forced=False):
        #Filters a message based on the guild's settings
        if exists(self.LoggedMessages,msg.id):
            return self.LoggedMessages[msg.id].Deletion-time.time()
        if forced:
            return await self.AddToFilter(msg,int(forced))
        for word in self.WordBlockList: #Word filter > Media filter
            buffer = self.WordBlockList[word]
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
        return False
    def FormatLoggedMessages(self):
        #For saving LoggedMessages
        LoggedMessagesSave = {}
        for msgid,message in list(self.LoggedMessages.items()):
            if not exists(LoggedMessagesSave,message.Channel):
                LoggedMessagesSave[message.Channel] = {}
            LoggedMessagesSave[message.Channel][message.MessageId] = message.Deletion
        return LoggedMessagesSave
    def CreateSave(self):
        #Creates a dictionary with the guild's settings
        return {"Guild":self.Guild,
                "WordBlockList":self.WordBlockList,
                "ChannelClearList":self.ChannelClearList,
                "NSFWBlockList":self.NSFWBlockList,
                "LogChannel":self.LogChannel,
                "MediaFilters":self.MediaFilters,
                "QueuedChannels":self.QueuedChannels,
                "ChannelLimits":self.ChannelLimits,
                "ProtectedMessages":self.ProtectedMessages,
                "LoggedMessages":self.FormatLoggedMessages()}
    def LoadSave(self,settings):
        #Loads a dictionary as the guild's settings
        for catagory,data in settings.items():
            try:
                if catagory == "LoggedMessages":
                    self.LoggedMessages = {}
                    for channel,messages in data.items():
                        for message,expirey in messages.items():
                            self.LoggedMessages[message] = FilteredMessage(expirey,int(message),int(channel))
                elif hasattr(self,catagory):
                    setattr(self,catagory,data)
                else:
                    log(f"[GuildObject {self.Guild}] Unknown catagory {catagory}")
            except:
                log(f"[GuildObject {self.Guild}] Invalid catagory data {catagory}")
    async def CreateConfirmation(self,msg,args,function):
        #Creates a yes/no confirmation for the user
        confirmationObj = Confirmation(msg,args,function)
        self.Confirmations[msg.author.id] = confirmationObj
        await confirmationObj.Alert()
        return confirmationObj
    async def CheckConfirmation(self,msg):
        #Checks for any active confirmations for the user
        user = msg.author.id
        confirmationObj = exists(self.Confirmations,user) and self.Confirmations[user]
        if not confirmationObj:
            return
        if confirmationObj.Expired():
            self.Confirmations.pop(user)
            return
        await confirmationObj.Check(msg)
        self.Confirmations.pop(user)
        return True
def getMegaTable(obj):
    gid = None
    t = type(obj)
    if t == discord.Message or t == discord.PartialMessage:
        gid = obj.guild.id
    elif t == int:
        gid = obj
    elif hasattr(obj,"id"): #Guild or FakeXYZ
        gid = obj.id
    if gid:
        if not exists(guildMegaTable,gid):
            guildMegaTable[gid] = GuildObject(gid)
        return guildMegaTable[gid]
    else:
        log("[GMT] No GID found in "+str(obj))
async def getGuildInviteStats(guild):
    try:
        invites = await guild.invites()
    except:
        return
    toReturn = {}
    for invite in invites:
        toReturn[invite.id] = {"m":invite.inviter,"u":invite.uses}
    return toReturn

#Commands
HistoryClearRatelimit = {}
async def checkHistoryClear(msg):
    #Checks for and removes messages beyond the message count limit
    gmt = getMegaTable(msg)
    cid = str(msg.channel.id) #Dumb storage logic by JSON
    if exists(gmt.ChannelLimits,cid):
        msgLimit = gmt.ChannelLimits[cid]
        lastCheck = (exists(HistoryClearRatelimit,cid) and HistoryClearRatelimit[cid]) or 0
        if lastCheck < time.time(): #Limit cause history call is quite hard
            HistoryClearRatelimit[cid] = time.time() + 2
            try:
                channelHistory = await msg.channel.history(limit=msgLimit+15).flatten()
                await msg.channel.delete_messages(channelHistory[msgLimit:])
            except Exception as exc:
                print("[History] Failed to do:",msg.guild.id,exc)
devCommands = {} #basically testing and back-end commands
adminCommands = {} #This will take priority over user commands should a naming conflict exist
userCommands = {}
class Command:
    def __init__(self,cmd,function,ratelimit,description,descriptionArgs,extraArg,group):
        #Defines and sets up a command
        if type(cmd) == list: #Declaring multiple aliases
            for cmdalias in cmd:
                Command(cmdalias,function,ratelimit,description,descriptionArgs,extraArg,group) #Feels a lil clunky?
                description = cmd[0]
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
        if exists(wantedTable,cmd): #Only warns, still replaces
            print(f"[AddCmd] Command {cmd} was declared twice")
        wantedTable[cmd] = self
    async def Run(self,msg,args,bypassRL=False):
        #Runs a command, first doing a ratelimit check
        user = msg.author.id
        if exists(self.RateLimitList,user) and not bypassRL:
            rlInfo = self.RateLimitList[user]
            if rlInfo["t"] > time.time():
                if not rlInfo["r"]:
                    self.RateLimitList[user]["r"] = True
                    return False,rlInfo["t"]-time.time()
                else:
                    return False,-1
        self.RateLimitList[user] = {"t":time.time()+self.RateLimit,"r":False}
        if self.ExtraArg != None:
            await self.Function(msg,args,self.ExtraArg)
        else:
            await self.Function(msg,args)
        await checkHistoryClear(msg)
        return True,0
async def doTheCheck(msg,args,commandTable):
    #Checks a command table against a message, and looks for a match
    arg0 = args[0]
    if "\n" in arg0:
        args[0] = arg0.split("\n")[0]
        args.insert(1,arg0.split("\n")[1])
    c = msg.content
    for command in commandTable:
        cregion = len(prefix+command) #cregion = command region
        if prefix+command == c[:cregion] and (not exists(c,cregion) or c[cregion] == " " or c[cregion] == "\n"):
            success,result = await commandTable[command].Run(msg,args)
            if not success and result > 0:
                await msg.channel.send(embed=fromdict({"title":"Slow Down","description":f"That command is limited for {simplifySeconds(result//1)} more seconds","color":colours["warning"]}),delete_after=result)
            return True

#Reaction listening
#Note that reactions will not continue to be listened to when the bot updates/refreshes
#Consider adding a save into GMT for certain things (E.g. reaction roles)
ReactionListenList = []
class WatchReaction:
    #Creates a listener for a message and its reactions
    def __init__(self,msg,user,emoji,function,args):
        self.MsgId = (type(msg) == int and msg) or msg.id
        self.UserId = (type(user) == int and user) or user.id #The user whitelisted to react to it
        self.Emoji = emoji
        self.Function = function
        self.Args = args
        self.Expirey = time.time()+60 #If unused, it becomes unwatched
        ReactionListenList.append(self)
    def Expired(self):
        return time.time() > self.Expirey
    async def Check(self,msg,user,emoji):
        if self.Expired():
            ReactionListenList.remove(self)
        elif msg.id == self.MsgId and user.id == self.UserId:
            self.Expirey = time.time()+60
            if emoji == self.Emoji:
                await self.Function(msg,self.Emoji,self.Args)
                return True
    def Update(self,args):
        if self.Expired():
            ReactionListenList.remove(self)
            return
        self.Args = args
        self.Expirey = time.time()+60
        return True
async def UpdateReactionWatch(msg,emoji,args):
    ListenListCache = ReactionListenList
    for listener in ListenListCache:
        if listener.MsgId == msg.id and (emoji == "all" or emoji == listener.Emoji):
            listener.Update(args)
async def changePageEmbed(msg,emoji,args):
    #Helper of createPagedEmbed
    title,preText,pagedContent,maxPage,page = args[0],args[1],args[2],args[3],args[4]
    page += (emoji=="➡️" and 1) or -1
    page = min(max(0,page),maxPage) #Limit page
    await msg.edit(embed=fromdict({"title":title,"description":preText+"\n".join(pagedContent[page]),"footer":{"text":f"Page {page+1}/{maxPage+1}"},"color":colours["info"]}))
    await UpdateReactionWatch(msg,"all",[title,preText,pagedContent,maxPage,page])
async def createPagedEmbed(user,channel,title,content,pageLimit=10,preText=""):
    #Automatically creates an embed with multiple pages when data is too large to display
    pagedContent = []
    index = 0
    for text in content:
        if index % pageLimit == 0:
            pagedContent.insert(index//pageLimit,[])
        pagedContent[index//pageLimit].append(text)
        index += 1
    maxPage = index//pageLimit
    if maxPage == 0:
        return await channel.send(embed=fromdict({"title":title,"description":preText+"\n".join(pagedContent[0]),"color":colours["info"]}))
    embed = await channel.send(embed=fromdict({"title":title,"description":preText+"\n".join(pagedContent[0]),"footer":{"text":f"Page 1/{maxPage+1}"},"color":colours["info"]}))
    for e in ["⬅️","➡️"]:
        await embed.add_reaction(e)
        WatchReaction(embed,user,e,changePageEmbed,[title,preText,pagedContent,maxPage,0])
    return embed

#Random functions
async def cloneChannel(channelid):
    #Clones a channel, essentially clearing it. The channel retains all bot-set and regular settings
    try:
        channel = client.get_channel(channelid)
        newchannel = await channel.clone(reason="Recreating text channel")
        gmt = getMegaTable(channel.guild) # Move over channel settings
        if channelid in gmt.MediaFilters:
            gmt.MediaFilters[newchannel.id] = gmt.MediaFilters[channelid]
            gmt.MediaFilters.pop(channelid)
        if channelid in gmt.ChannelLimits:
            gmt.ChannelLimits[newchannel.id] = gmt.ChannelLimits[channelid]
            gmt.ChannelLimits.pop(channelid)
        await channel.delete()
        newchannel.position = channel.position #Because clone doesnt include position
        await newchannel.send(embed=fromdict({"title":"Success","description":channel.name+" has been re-made and cleared","color":colours["success"]}),delete_after=60)
        print("[CloneChannel] Successfully cloned channel",channel.name)
        return newchannel
    except Exception as exc:
        log("[CloneChannel] Exception: "+str(exc)) #Maybe unrequired?
#The voice functions below could be removable, as the bot doesnt have any VC functions right now
def findVoiceClient(guildId):
    #Returns any existing voice client object for the guild
    for voiceObj in client.voice_clients:
        if voiceObj.guild.id == guildId:
            return voiceObj
VCList = {} #Unmaintained and possibly broken
async def connectToVC(channel,idleTimeout=60,ignorePlaying=False):
    #This randomly broke itself after some time - channel.connect is hanging? I cant fix this
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

#Client
client = commands.Bot(command_prefix=prefix,help_command=None,intents=discord.Intents(guilds=True,messages=True,members=True,reactions=True))
@client.event
async def on_error(error,*args,**kwargs):
    #Error handler
    if exists(args,0):
        try:
            causingCommand = args[0].content
        except:
            causingCommand = str(args[0])
    else:
        causingCommand = "<none>"
    log(f"[Fatal Error] Causing command: {causingCommand}\nError:")
    traceback.print_exc(file=sys.stderr)
    try: #Logging
        errorFile = tempFile()
        file = open(errorFile,"w",encoding="UTF-16",newline="") #UTF-16 just incase it all goes to hell
        try:
            traceback.print_exc(file=file)
        except Exception as exc:
            log("[Fatal Error] Error Log file failed to write: "+str(exc))
            pass
        file.close()
        await client.get_channel(logChannels["errors"]).send(f"Error in client\nTime: {currentDate()}\nCausing command: {causingCommand}",file=discord.File(errorFile))
        os.remove(errorFile)
    except Exception as exc:
        log(f"[Fatal Error] Failed to log error: {currentDate()} {exc}")
uptime = 0
@client.event
async def on_ready():
    global uptime
    await client.change_presence(activity=discord.Game(name="##cmds"))
    log("connected v"+discord.__version__)
    uptime = time.time()//1
    try: #Notifying of start-up
        await client.get_channel(logChannels["boot-ups"]).send("Ive connected at "+currentDate())
    except:
        log("Failed to alert of bootup at "+currentDate())
@client.event
async def on_message(msg):
    #Everything trails off from here
    if not msg.guild or (client.user and msg.author.id == client.user.id): #Only do stuff in guild, ignore messages by the bot
        if msg.guild:
            await getMegaTable(msg).FilterMessage(msg)
        elif msg.author.id != client.user.id:
            await msg.channel.send(embed=fromdict({"title":"Not here","description":"This bot can only be used in a server, and not dms","color":colours["error"]}))
        return
    gmt = getMegaTable(msg)
    await gmt.FilterMessage(msg)
    if type(msg.author) == discord.User: #Webhook
        return
    if await gmt.CheckConfirmation(msg): #Confirmations arent commands, simple as that
        return await checkHistoryClear(msg)
    args = msg.content.split(" ") #Please keep in mind the first argument (normally) is the calling command
    if msg.author.id == DevID:
        if await doTheCheck(msg,args,devCommands):
            return
    if msg.author.guild_permissions.administrator:
        if await doTheCheck(msg,args,adminCommands):
            return
    if await doTheCheck(msg,args,userCommands):
        return
    await checkHistoryClear(msg) #Since its fired after a command, add a check here
@client.event
async def on_raw_message_edit(msg):
    #On message edit to avoid filter bypassing
    try:
        messageObj = await discord.PartialMessage(channel=client.get_channel(int(msg.data["channel_id"])),id=int(msg.data["id"])).fetch()
    except:
        pass
    else:
        await getMegaTable(messageObj).FilterMessage(messageObj)
@client.event
async def on_reaction_add(reaction,user):
    if user.id == client.user.id: #If its the bot
        return
    ListenListCache = ReactionListenList
    for listener in ListenListCache:
        await listener.Check(reaction.message,user,reaction.emoji)
@client.event
async def on_guild_join(guild):
    guildMegaTable[guild.id] = GuildObject(guild.id) #Force default settings
    getMegaTable(guild).InviteTrack = await getGuildInviteStats(guild) #Does this even work?
@client.event
async def on_member_join(member):
    #Checks the invites against the invite tracker, and logs any change
    guild = member.guild
    gmt = getMegaTable(guild)
    if not gmt.InviteTrack:
        gmt.InviteTrack = await getGuildInviteStats(guild)
        return
    invitesBefore = gmt.InviteTrack
    invitesAfter = await getGuildInviteStats(guild)
    if not invitesAfter:
        return
    for invId,invInfo in invitesAfter.items():
        if not exists(invitesBefore,inviteId):
            invitesBefore[inviteId] = {"m":invInfo["m"],"u":0}
        if invitesBefore[inviteId]["u"] < invInfo["u"]:
            await gmt.Log(embed=fromdict({"title":"Invite Log","description":f"User <@{member.id}> ({member}) has joined through <@{invInfo['m'].id}> ({invInfo['m']})'s invite (discord.gg/{inviteId})\nInvite is at {invInfo['u']} uses","color":colours["info"]}))
            break
    gmt.InviteTrack = invitesAfter

#Tasks
stopCycling = False
finishedLastCycle = False
@tasks.loop(seconds=2)
async def constantMessageCheck():
    #Runs through all the GMTs and deletes any filtered messages past their due time
    global finishedLastCycle #Weird stop but it works
    if stopCycling:
        finishedLastCycle = True
        return
    try:
        toDeleteList = {}
        for guild,gmt in guildMegaTable.items():
            for msgid,message in list(gmt.LoggedMessages.items()):
                if msgid in gmt.ProtectedMessages:
                    gmt.LoggedMessages.pop(msgid)
                    continue
                messageObj = message.Expired() and message.GetMessageObj()
                if messageObj:
                    if not exists(toDeleteList,message.Channel):
                        toDeleteList[message.Channel] = []
                    toDeleteList[message.Channel].append(messageObj)
                    gmt.LoggedMessages.pop(msgid)
        for channel,msglist in toDeleteList.items():
            try:
                await client.get_channel(channel).delete_messages(msglist)
            except Exception as exc:
                log(f"BulkDelete Exception C={channel} #ML={len(msglist)} - {exc}")
    except Exception as exc:
        log("[!] LoggedMessages Exception: "+str(exc))
constantMessageCheck.start()
@tasks.loop(seconds=10)
async def constantChannelCheck():
    #Checks and clears channels set to auto-clear after some time
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
        log("[!] ChannelClear Exception: "+str(exc))
constantChannelCheck.start()
@tasks.loop(seconds=150)
async def updateConfigFiles():
    #Runs through all the GMTs and updates them
    try:
        for guild in client.guilds:
            success,result = safeWriteToFile(f"storage/settings/{guild.id}.json",json.dumps(getMegaTable(guild).CreateSave()))
            print(f"[GuildObject {guild.id}] Saving: {result}")
    except Exception as exc:
        log("[!] UpdateConfig Exception: "+str(exc))
updateConfigFiles.start()
@tasks.loop(seconds=2)
async def VCCheck():
    #Auto disconnects from a VC after inactivity
    try:
        for vc in VCList:
            if vc.is_playing():
                VCList[vc]["lastActiveTime"] = time.time()
            elif time.time()-VCList[vc]["idleTimeout"] > VCList[vc]["lastActiveTime"]:
                await vc.disconnect()
    except Exception as exc:
        log("[!] VCCheck Exception: "+str(exc))
VCCheck.start()
@tasks.loop(seconds=15)
async def keepGuildInviteUpdated():
    #Keeps the guild invite tracking updated if there is none
    for guild in client.guilds:
        gmt = getMegaTable(guild)
        gmt.InviteTrack = gmt.InviteTrack or await getGuildInviteStats(guild)
keepGuildInviteUpdated.start()

#User Commands
async def forceUpdate(msg,args):
    #(Safely) close the bot down for updating
    global stopCycling
    log("Client was force-exited via forceUpdate() "+str(time.time()))
    log("Hanging until messageCheck has finished its cycle or 20s, whatever is shorter")
    stopCycling = True
    sleepTime = 0
    while True:
        if finishedLastCycle == True or sleepTime>=20: #Timeout worries
            break
        sleepTime+=1
        await asyncio.sleep(1)
    log("Invoking save - sleep time: "+str(sleepTime))
    await updateConfigFiles()
    log("Save finished, closing")
    await client.close()
Command("d -update",forceUpdate,0,"Updates the bot, force saving configs",{},None,"dev")
async def cmds(msg,args):
    cmdList = {"Admin":adminCommands}
    for command,cmdInfo in userCommands.items():
        if not exists(cmdList,cmdInfo.Group):
            cmdList[cmdInfo.Group] = {}
        cmdList[cmdInfo.Group][command] = cmdInfo
    if exists(args,1): #Group Specific
        group = None
        for catagory in cmdList:
            if args[1].lower() == catagory.lower():
                group = cmdList[catagory]
        if msg.author.id == 260016427900076033 and args[1].lower() == "dev":
            group = devCommands
        if not group:
            await msg.channel.send(embed=fromdict({"title":"Invalid group","description":f"The group '{args[1]}' doesnt exist","color":colours["error"]}))
            return
        finalText = []
        for command,cmdInfo in group.items():
            argMessageContent = ""
            for argName,argRequired in cmdInfo.DescArgs.items():
                argMessageContent += (argRequired and f"<{argName}>") or f"[{argName}]"
            finalText.append(f"`{command} {argMessageContent}` - {cmdInfo.Description}")
        await createPagedEmbed(msg.author,msg.channel,"Commands within "+args[1],finalText,10,"**Syntax**\n`<>` is a required argument, `[]` is an optional argument\n\n**Commands**\n")
    else: # Generalised (No group)
        finalText = f"do `{args[0]} <group>` to get more information on a group"
        for group,commands in cmdList.items():
            finalText += f"\n**{group}**\n"
            for command in commands:
                finalText += f"`{command}` "
        await msg.channel.send(embed=fromdict({"title":"Commands","description":finalText,"color":colours["info"]}))
Command(["commands","cmds"],cmds,1,"List all commands",{"group":False},None,"General")
async def publicVote(msg,args):
    if len(args) < 2:
        await msg.channel.send(embed=fromdict({"title":"Error","description":"You gotta include the thing to vote on","color":colours["error"]}),delete_after=10)
        return
    attachments = msg.attachments
    imageUrl = (exists(attachments,0) and attachments[0].url) or ""
    author = msg.author
    wantedReactions = []
    findWantedReaction = regex.compile("^{[^\]]+}$")
    for arg in args: #Get user-defined reactions ( {:reaction:} )
        if findWantedReaction.search(arg):
            wantedReactions.append(arg[1:-1])
            args.remove(arg)
    args.remove(args[0])
    await msg.delete()
    voteMsg = await msg.channel.send(embed=fromdict({"author":{"name":f"{author} is calling a vote","icon_url":str(author.avatar_url)},"description":" ".join(args),"image":{"url":imageUrl},"color":colours["info"]}))
    if wantedReactions == []:
        await voteMsg.add_reaction("⬆️")
        await voteMsg.add_reaction("⬇")
    else:
        for i in wantedReactions:
            try:
                await voteMsg.add_reaction(i)
            except:
                pass #Incase it doesnt have access to the emoji
Command("vote",publicVote,10,"Make a public vote about anything with an optional image",{"text":True,"imagefile":False},None,"General")

#Module importing
log("attempting import")
''' Load modules from the modules folder
Only use this for storing commands, as load order is random
This is so i dont clog up the entirety of this main script with like 2k lines '''
def loadModules(origin):
    log("Loading modules origin = "+origin)
    execList = {}
    for file in os.listdir("modules"):
        if not file.endswith(".py"):
            continue
        if not os.path.isfile("modules/"+file):
            continue
        execList[file] = bytes("#coding: utf-8\n","utf-8")+open("modules/"+file,"rb").read()
    for file,contents in execList.items():
        try:
            exec(contents,globals())
        except Exception as exc:
            log(f"[Modules] Module {file} import error -> {exc}")
loadModules("bootup")
async def loadModulesAsync(msg,args):
    loadModules("User "+msg.author.name)
Command("d -reload modules",loadModulesAsync,0,"Reloads all the modules",{},None,"dev")

#Finish off - load configs
log("done commands")
for i in os.listdir("storage/settings"):
    try:
        j = json.loads(open("storage/settings/"+i).read())
    except:
        log("[JSON] Load failed for file "+i)
    else:
        if not exists(j,"Guild"):
            log("[JSON] Guild index missing for file "+i)
            continue
        getMegaTable(j["Guild"]).LoadSave(j)
log("loaded config")

#On-boot tests
if exists(globals(),"FakeMessage"):
    log("Doing final tests")
    asyncio.run(on_message(FakeMessage("##d -test advanced",gid=-1,uid=DevID)))
    log("Finished tests")
else:
    log("No tests module found, skipping final tests")
