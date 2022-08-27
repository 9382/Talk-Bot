from dotenv import dotenv_values
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
import os
#Please modify the below options by utilising the .env file instead of directly editing them
env = dotenv_values()
prefix = env["PREFIX"]
DevID = int(env["DEVID"])
logChannels = {"errors":int(env["ERRORLOG"]),"boot-ups":int(env["BOOTLOG"])} # These are different from the guild-defined LogChannel and act as telemetry
colours = {"info":int(env["CINFO"],16),"error":int(env["CERR"],16),"success":int(env["CWORK"],16),"warning":int(env["CWARN"],16),"plain":0xAAAAAA} #Plain is kept plain

#Base functions
def exists(table,value):
    try:
        table[value]
        return True
    except:
        return False
def tempFile(extension="txt"):
    #Create a temporary file name and its file - helps avoid naming conflicts
    name = f"storage/temp/Talk-Bot-{time.time()}.{extension}"
    open(name,"x")
    return name
def currentDate():
    #The current date in YYYY-MM-DD hh:mm:ss
    return str(datetime.fromtimestamp(time.time()//1))
def safeWriteToFile(filename,content,mode="w",encoding="UTF-8"):
    #Writes contents to a file, auto-creating the directory should it be missing
    if filename.find("\\") > -1:
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
    #Manages the writing to a daily log file for debugging
    print(f"[Log {currentDate()[11:]}]",content)
    success,result = safeWriteToFile(f"storage/logs/{currentDate()[:10]}.log",f"[{currentDate()[11:]}] {content}\n","a")
    if not success:
        print(f"[Log {currentDate()[11:]}] Failed to write to log file: {result}")
    return success
log(f"Starting main - the time is {time.time()} or {currentDate()}")
timeMultList = {"s":1,"m":60,"h":3600,"d":86400}
def strToTimeAdd(duration):
    #Converts stringtime to seconds
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
def simplifySeconds(seconds):
    #Turn seconds into full sentence D/H/M/S
    if seconds <= 0:
        return "0 seconds"
    days,seconds = int(seconds//86400),seconds%86400
    hours,seconds = int(seconds//3600),seconds%3600
    minutes,seconds = int(seconds//60),seconds%60
    totalSet = []
    if days > 0:
        totalSet.append(f"{days} day(s)")
    if hours > 0:
        totalSet.append(f"{hours} hour(s)")
    if minutes > 0:
        totalSet.append(f"{minutes} minute(s)")
    if seconds > 0:
        totalSet.append(f"{seconds} second(s)")
    return ", ".join(totalSet[:-1])+(totalSet[:-1] and " and " or "")+totalSet[-1]
def truncateText(text,limit=1950):
    #For avoiding issues with message max length
    Ltext = len(text)
    if Ltext < limit:
        return text
    return text[:limit] + f"... [Excluded {Ltext-limit} bytes]"
fromdict = discord.Embed.from_dict
numRegex = regex.compile("\d+")
findMediaRegex = regex.compile("https?://((cdn|media)\.discordapp\.(com|net)/attachments/|tenor\.com/view/)") #See FilterMessage

#GMT
guildMegaTable = {}
class FilteredMessage:
    #Object used to represent a filtered message
    def __init__(self,expiry,msgid=None,channelid=None,messageObj=None):
        if messageObj:
            msgid = messageObj.id
            channelid = messageObj.channel.id
        self.Deletion = expiry
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
        self.Expiry = time.time()+20
    async def Alert(self):
        if not self.Expired():
            await self.msg.channel.send("Hey, are you sure? Reply (y/yes) or (n/no) - Expires in 20 seconds",delete_after=self.Expiry-time.time())
    def Expired(self):
        return time.time() > self.Expiry
    async def Check(self,msg):
        content = msg.content.lower()
        if content == "yes" or content == "y":
            await msg.channel.send("Alright, continuing...")
            return True #Function must be called outside of here to avoid a race condition
        else:
            await msg.channel.send("Alright, aborting...",delete_after=5)
class GuildObject:
    #The main object used to reference a guild and its settings
    def __init__(self,gid):
        self.Guild = gid
        self.WordBlockList = {}
        self.NSFWBlockList = []
        self.InviteTrack = None
        self.LogChannels = {}
        self.MediaFilters = {}
        self.ChannelClearList = {}
        self.QueuedChannels = {}
        self.LoggedMessages = {}
        self.Confirmations = {}
        self.ChannelLimits = {}
        self.ProtectedMessages = {}
        self.FilterNicknames = False
        self.ModRole = 0 #NOTE: Consider auto-checking if they fit a certain permission? E.g. manage roles. Could be more elegant
        if exists(guildMegaTable,gid):
            log(f"[GMT] Guild {gid} was declared twice")
        guildMegaTable[gid] = self
    async def Log(self,category,*,content=None,embed=None):
        #Logs content to a server's set log channel
        if exists(self.LogChannels,category):
            channel = client.get_channel(self.LogChannels[category])
            if channel:
                if embed:
                    embed.set_footer(text=currentDate())
                    file = None
                    if len(embed.description) > 3950: #We dont use truncateText here because it could be important
                        logfile = tempFile()
                        open(logfile,"w",encoding="UTF-16",newline="").write(embed.description)
                        file = discord.File(logfile) #This feels slightly weirdly done, but eh
                        tempembed = embed.to_dict() #Can only be set in intialising when in object form
                        tempembed["description"] = "[Embed description passed 3950 Byte limit. Check the file provided for the embed description]"
                        embed = fromdict(tempembed)
                content = content and truncateText(content)
                return await channel.send(content=content,embed=embed,file=file)
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
        else:
            return False
        if exists(self.QueuedChannels,channel):
            self.QueuedChannels.pop(channel)
        return True
    async def AddToFilter(self,msg,buffer): 
        #Helper of FilterMessage
        if msg.id in self.ProtectedMessages and self.ProtectedMessages[msg.id] > time.time():
            return False
        print("[Filter] Msg Filtered ->",buffer,msg.content)
        # if buffer <= 0: #May conflict with ratelimits or filter protection
        #     try:
        #         await msg.delete()
        #         return buffer
        #     except:
        #         pass
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
    def CreateConfig(self):
        #Creates a dictionary with the guild's settings
        return {"Guild":self.Guild,
                "WordBlockList":self.WordBlockList,
                "ChannelClearList":self.ChannelClearList,
                "NSFWBlockList":self.NSFWBlockList,
                "LogChannels":self.LogChannels,
                "MediaFilters":self.MediaFilters,
                "QueuedChannels":self.QueuedChannels,
                "ChannelLimits":self.ChannelLimits,
                "ProtectedMessages":self.ProtectedMessages,
                "FilterNicknames":self.FilterNicknames,
                "ModRole":self.ModRole,
                "LoggedMessages":self.FormatLoggedMessages()}
    def LoadConfig(self,settings):
        #Loads a dictionary as the guild's settings
        for catagory,data in settings.items():
            try:
                if catagory == "LoggedMessages":
                    self.LoggedMessages = {}
                    for channel,messages in data.items():
                        for message,expiry in messages.items():
                            self.LoggedMessages[int(message)] = FilteredMessage(expiry,int(message),int(channel))
                elif hasattr(self,catagory):
                    if type(data) != type(getattr(self,catagory)):
                        log(f"[GuildObject {self.Guild}] Invalid data type for {catagory} ({type(data)} vs {type(getattr(self,catagory))})")
                    else:
                        if type(data) == dict:
                            #Auto-translate keys that could be an integer into an integer, as JSON can only store keys as string
                            #This'll prevent bad str() practice in some functions relying on data
                            for key in list(data.keys()):
                                try:
                                    keyint = int(key)
                                except ValueError:
                                    pass
                                else:
                                    data[keyint] = data[key]
                                    data.pop(key)
                        setattr(self,catagory,data)
                else:
                    log(f"[GuildObject {self.Guild}] Unknown catagory {catagory}")
            except Exception as exc:
                log(f"[GuildObject {self.Guild}] Invalid catagory data in {catagory} leading to {exc}")
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
        self.Confirmations.pop(user)
        if confirmationObj.Expired():
            return
        if await confirmationObj.Check(msg):
            await confirmationObj.Function(confirmationObj.msg,confirmationObj.args)
        return True
    def ProtectMessage(self,msg,expiry):
        if hasattr(msg,"id"):
            msg = msg.id
        self.ProtectedMessages[msg] = time.time() + expiry #Just more convenient
def getMegaTable(obj):
    gid = None
    t = type(obj)
    if t in [discord.Message,discord.PartialMessage,discord.Member]:
        gid = obj.guild.id
    elif t == int:
        gid = obj
    elif hasattr(obj,"guild"): #Guild or FakeXYZ
        gid = obj.guild.id
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
MessageLogBlacklist = {} #Dont log self-deleted messages
async def clearMessageList(channel,messages): #Max of 100 for bulkdelete, so we split it
    index = 0
    for message in messages:
        MessageLogBlacklist[message.id] = time.time() #Cleared from MLB by clearBacklogs
    while index*100 < len(messages):
        try:
            await channel.delete_messages(messages[index*100:100+index*100])
        except Exception as exc:
            log(f"[BulkDelete {channel.id}] Failed to delete {len(messages[index*100:100+index*100])} messages: {exc}")
            return False,exc
        index += 1
    return True,None
CustomMessageCache = {} #Incase of a reboot, we use recent history as a custom "cache message" system
#NOTE: Consider clearing messages after they are stupidly old
HistoryClearRatelimit = {}
async def checkHistoryClear(msg):
    #Checks for and removes messages beyond the message count limit
    #This is always ran last, and therefore how long this takes really doesnt matter
    if type(msg.channel) == discord.VoiceChannel:
        #Discord decided they would add chat channels to voice channels. and discord.py does NOT like it :) (Temporary fix)
        return
    gmt = getMegaTable(msg)
    cid = msg.channel.id
    lastCheck = (cid in HistoryClearRatelimit and HistoryClearRatelimit[cid]) or 0
    if lastCheck < time.time(): #Limit cause history call is quite intensive
        HistoryClearRatelimit[cid] = time.time() + 2.5
        if cid in gmt.ChannelLimits:
            msgLimit = gmt.ChannelLimits[cid]
            try:
                channelHistory = [message async for message in msg.channel.history(limit=msgLimit+15)]
                for message in channelHistory:
                    if not exists(CustomMessageCache,message.id):
                        CustomMessageCache[message.id] = {"m":message,"t":time.time()}
                await clearMessageList(msg.channel,channelHistory[msgLimit:])
            except Exception as exc:
                print(f"[History {msg.guild.id}] Failed to do a ChannelLimit clear: {exc}")
        else: #Just store the last 150 messages into CustomMessagesCache, and dont care about history clearing
            channelHistory = [message async for message in msg.channel.history(limit=150)]
            for message in channelHistory:
                if not exists(CustomMessageCache,message.id):
                    CustomMessageCache[message.id] = {"m":message,"t":time.time()}

performanceCheck = False #For timing the time taken of a command to execute
devCommands = {} #basically testing and back-end commands
adminCommands = {} #This will take priority over user commands should a naming conflict exist
modCommands = {} #These are moderation commands that dont need to be hidden behind admin. Mid priority
userCommands = {}
class Command:
    def __init__(self,cmd,function,ratelimit,description,descriptionArgs,extraArg,group):
        #Defines and sets up a command
        if type(cmd) == list: #Declaring multiple aliases
            for cmdalias in cmd:
                Command(cmdalias,function,ratelimit,description,descriptionArgs,extraArg,group) #Feels a lil clunky?
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
        elif group == "mod":
            wantedTable = modCommands
        else:
            wantedTable = userCommands
        if exists(wantedTable,cmd): #Only warns, still replaces
            log(f"[AddCmd] Command {cmd} was declared twice for group {group}")
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
        timeToExecute = time.perf_counter()
        if self.ExtraArg != None:
            await self.Function(msg,args,self.ExtraArg)
        else:
            await self.Function(msg,args)
        timeToExecute = time.perf_counter() - timeToExecute
        if user == DevID and performanceCheck:
            await msg.channel.send(f"[DEV] Processing time for {self.Name}: {timeToExecute}")
        await checkHistoryClear(msg)
        return True,0
async def checkCommandList(msg,args,commandTable):
    #Checks a command table against a message, and looks for a match
    arg0 = args[0]
    if "\n" in arg0:
        args[0] = arg0.split("\n")[0]
        args.insert(1,arg0.split("\n")[1])
    c = msg.content.lower()
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
ReactionListenList = [] #NOTE: Theres gotta be a better system
class WatchReaction:
    #Creates a listener for a message and its reactions
    def __init__(self,msg,user,emoji,function,args):
        self.Message = msg #For easier usage, it must be a message object. PartialMessage should still work
        self.UserId = (type(user) == int and user) or user.id #The user whitelisted to react to it
        self.Emoji = emoji
        self.Function = function
        self.Args = args
        self.Expiry = time.time() #If unused, it becomes unwatched
        ReactionListenList.append(self)
    def Expired(self):
        return time.time() > self.Expiry+300
    async def RemoveReaction(self):
        try:
            await self.Message.remove_reaction(self.Emoji,client.user)
        except:
            pass #Message has probably been deleted. (Note: Couldnt find a property saying if it was deleted, so you get try except instead)
    async def Check(self,msg,user,emoji):
        if self.Expired():
            await self.RemoveReaction()
            ReactionListenList.remove(self)
        elif msg.id == self.Message.id and user.id == self.UserId:
            self.Expiry = time.time()
            if emoji == self.Emoji:
                try: #Remove user's reaction for convenience
                    await msg.remove_reaction(emoji,user)
                except: #Dont care if it doesnt work
                    pass
                await self.Function(msg,self.Emoji,self.Args)
                return True
    def Update(self,args):
        if self.Expired():
            ReactionListenList.remove(self)
            return
        self.Args = args
        self.Expiry = time.time()
        return True
async def UpdateReactionWatch(msg,emoji,args):
    for listener in list(ReactionListenList):
        if listener.Message.id == msg.id and (emoji == "all" or emoji == listener.Emoji):
            listener.Update(args)
async def changePageEmbed(msg,emoji,args):
    #Helper of createPagedEmbed
    title,preText,pagedContent,maxPage,page = args[0],args[1],args[2],args[3],args[4] #:cringe:
    page += (emoji=="➡️" and 1) or -1
    page = min(max(0,page),maxPage) #Limit page
    await msg.edit(embed=fromdict({"title":title,"description":preText+"\n".join(pagedContent[page]),"footer":{"text":f"Page {page+1}/{maxPage+1}"},"color":colours["info"]}))
    await UpdateReactionWatch(msg,"all",[title,preText,pagedContent,maxPage,page])
async def createPagedEmbed(user,channel,title,content,pageLimit=10,preText="",deleteAfter=None):
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
        return await channel.send(embed=fromdict({"title":title,"description":preText+"\n".join(pagedContent[0]),"color":colours["info"]}),delete_after=deleteAfter)
    embed = await channel.send(embed=fromdict({"title":title,"description":preText+"\n".join(pagedContent[0]),"footer":{"text":f"Page 1/{maxPage+1}"},"color":colours["info"]}),delete_after=deleteAfter)
    for e in ["⬅️","➡️"]:
        await embed.add_reaction(e)
        WatchReaction(embed,user,e,changePageEmbed,[title,preText,pagedContent,maxPage,0])
    return embed

#Random functions
async def cloneChannel(channelid,cause):
    #Clones a channel, essentially clearing it. The channel retains all bot-set and regular settings
    try:
        channel = client.get_channel(channelid)
        newchannel = await channel.clone(reason=f"Recreating text channel | {cause}")
        gmt = getMegaTable(channel.guild) # Move over channel settings
        if channelid in gmt.MediaFilters:
            gmt.MediaFilters[newchannel.id] = gmt.MediaFilters[channelid]
            gmt.MediaFilters.pop(channelid)
        if channelid in gmt.ChannelLimits:
            gmt.ChannelLimits[newchannel.id] = gmt.ChannelLimits[channelid]
            gmt.ChannelLimits.pop(channelid)
        await channel.delete() #Delete after creation of replacement incase it freaks
        newchannel.position = channel.position #Because clone doesnt include position
        await newchannel.send(embed=fromdict({"title":"Success","description":channel.name+" has been re-made and cleared","color":colours["success"]}),delete_after=60)
        print("[CloneChannel] Successfully cloned channel",channel.name)
        return newchannel
    except Exception as exc:
        log("[CloneChannel] Exception: "+str(exc)) #NOTE: Check for permission errors to avoid clogging of logs
def findVoiceClient(guildId):
    #Returns any existing voice client object for the guild
    for voiceObj in client.voice_clients:
        if voiceObj.guild.id == guildId:
            return voiceObj
VCList = {} #Unmaintained due to minimal use
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
def getChannelByName(guild,channelname):
    for channel in guild.text_channels:
        if channel.name == channelname:
            return channel
def HasPermission(member,permission,channel=None):
    assert hasattr(discord.Permissions,permission),f"{permission} is not a valid permission"
    if channel:
        return getattr(channel.permissions_for(member),permission)
    else:
        return getattr(member.guild_permissions,permission)

#Client creation
client = commands.Bot(command_prefix=prefix,help_command=None,intents=discord.Intents(guilds=True,messages=True,members=True,reactions=True,voice_states=True,message_content=True))

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
                if msgid in gmt.ProtectedMessages and gmt.ProtectedMessages[msgid] > time.time():
                    gmt.LoggedMessages.pop(msgid)
                    continue
                messageObj = message.Expired() and message.GetMessageObj()
                if messageObj:
                    if not exists(toDeleteList,message.Channel):
                        toDeleteList[message.Channel] = []
                    toDeleteList[message.Channel].append(messageObj)
                    gmt.LoggedMessages.pop(msgid)
        for channel,msglist in toDeleteList.items():
            if client.get_channel(channel): #This can somehow be None
                await clearMessageList(client.get_channel(channel),msglist)
    except:
        await on_error("Task CheckMessages")

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
                    await cloneChannel(channel.id,"Queued deletion")
    except:
        await on_error("Task CheckChannels")

@tasks.loop(seconds=150)
async def updateConfigFiles():
    #Runs through all the GMTs and updates their relevant json
    try:
        for guild in client.guilds:
            success,result = safeWriteToFile(f"storage/settings/{guild.id}.json",json.dumps(getMegaTable(guild).CreateConfig(),separators=(',', ':')))
            if success:
                print(f"[GuildObject {guild.id}] Saving: {result}")
            else:
                log(f"[GuildObject {guild.id}] Saving: {result}")
    except:
        await on_error("Task UpdateConfig")

@tasks.loop(seconds=5)
async def clearBacklogs():
    #Clears old entires in large lists or dictionaries
    try:
        for reaction in list(ReactionListenList): #Temporary copy to avoid size-change issues
            if reaction.Expired():
                await reaction.RemoveReaction()
                ReactionListenList.remove(reaction)
        for msgid,queuetime in dict(MessageLogBlacklist).items():
            if time.time() > queuetime+30: #Probably deleted by now
                MessageLogBlacklist.pop(msgid)
        for msgid,msgdata in dict(CustomMessageCache).items():
            if time.time() > msgdata["t"]+172800: #2 Days. Hopefully, the bot wont reboot often and this wont matter. (Possibly too long?)
                CustomMessageCache.pop(msgid)
    except:
        await on_error("Task ClearBacklogs")

@tasks.loop(seconds=2)
async def VCCheck():
    #Auto disconnects from a VC after inactivity
    try:
        for vc in VCList:
            if vc.is_playing():
                VCList[vc]["lastActiveTime"] = time.time()
            elif time.time()-VCList[vc]["idleTimeout"] > VCList[vc]["lastActiveTime"]:
                await vc.disconnect()
    except:
        await on_error("Task VCCheck")

@tasks.loop(seconds=15)
async def keepGuildInviteUpdated():
    #Keeps the guild invite tracking updated if there is none
    for guild in client.guilds:
        gmt = getMegaTable(guild)
        gmt.InviteTrack = gmt.InviteTrack or await getGuildInviteStats(guild)

@tasks.loop(seconds=600)
async def heartbeat():
    log(f"Alive ({currentDate()[11:]})")

@client.event
async def setup_hook():
    log("Starting setup")
    constantMessageCheck.start()
    constantChannelCheck.start()
    updateConfigFiles.start()
    clearBacklogs.start()
    VCCheck.start()
    keepGuildInviteUpdated.start()
    heartbeat.start()
    log("Finished setup")

#Client
ErrorTermBlacklist = ["Connection reset by peer","403 Forbidden","404 Not Found","500 Internal Server Error","503 Service Unavailable","504 Gateway Time-out"]
@client.event
async def on_error(event,*args,**kwargs):
    #Error handler
    args = truncateText("\n".join([str(v) for v in args]))
    error = traceback.format_exc()
    for term in ErrorTermBlacklist:
        if error.find(term) > -1:
            log(f"[Fatal Error {event}] Ignored uncaught exception - matched term '{term}'")
            return
    log(f"[Fatal Error {event}] Command Arguments: {args}\nError: {error}")
    if logChannels["errors"] <= 1: #No log channel set
        return
    try: #Logging
        errorFile = tempFile()
        file = open(errorFile,"w",encoding="UTF-16",newline="") #UTF-16 just incase it all goes to hell
        try:
            file.write(error)
        except Exception as exc:
            log(f"[Fatal Error {event}] Error Log file failed to write: {exc}")
            pass
        file.close()
        await client.get_channel(logChannels["errors"]).send(f"Error in client {event}\nTime: {currentDate()}\nCommand Arguments: {args}",file=discord.File(errorFile))
        os.remove(errorFile)
    except Exception as exc:
        log(f"[Fatal Error {event}] Failed to log error at {currentDate()}: {exc}")
uptime = 0
@client.event
async def on_ready():
    global uptime
    await client.change_presence(activity=discord.Game(name=f"{prefix}cmds"))
    log("connected v"+discord.__version__)
    uptime = time.time()//1
    if logChannels["boot-ups"] > 1: #Check if log channel is set
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
        if await checkCommandList(msg,args,devCommands):
            return
    if msg.author.guild_permissions.administrator:
        if await checkCommandList(msg,args,adminCommands):
            return
    if gmt.ModRole in [role.id for role in msg.author.roles] or msg.author.guild_permissions.administrator:
        if await checkCommandList(msg,args,modCommands):
            return
    if await checkCommandList(msg,args,userCommands):
        return
    await checkHistoryClear(msg) #Since its fired after a command, add a check here
@client.event
async def on_raw_message_edit(msg):
    #On message edit to avoid filter bypassing and to log
    try:
        messageObj = await discord.PartialMessage(channel=client.get_channel(int(msg.data["channel_id"])),id=int(msg.data["id"])).fetch()
    except:
        return
    gmt = getMegaTable(messageObj)
    await gmt.FilterMessage(messageObj)
    content = exists(msg.data,"content") and msg.data["content"]
    if content and not(client.user and messageObj.author.id == client.user.id): #Not worried about logging embed edits
        msgid = msg.message_id
        cached = msg.cached_message or exists(CustomMessageCache,msgid) and CustomMessageCache[msgid]["m"]
        attachments = " ".join([o.url for o in messageObj.attachments]) #Attachments cant change via edits, so only get one
        attachmentfinal = attachments and f"\n**Attached Files**\n{attachments}" or "" #If i make this embed line any longer i might just cry, so we move a bit here
        await gmt.Log("messages",embed=fromdict({"title":"Message Edited","description":f"<@{messageObj.author.id}> ({messageObj.author}) edited a message in <#{messageObj.channel.id}>\n(ID [{messageObj.id}]({messageObj.jump_url})){attachmentfinal}\n**Previous Content**\n{cached and cached.content or '<unknown>'}\n**New Content**\n{content}","color":colours["warning"]}))
@client.event
async def on_raw_message_delete(msg):
    #For logging deleted messages
    msgid = msg.message_id
    cached = msg.cached_message or exists(CustomMessageCache,msgid) and CustomMessageCache[msgid]["m"]
    if cached and not exists(MessageLogBlacklist,msgid): #No point logging a deletion if we dont know what was deleted (maybe? might be worth posting anyways, unsure)
        if (client.user and client.user.id != cached.author.id): #Dont report self
            attachments = " ".join([o.url for o in cached.attachments])
            attachmentfinal = attachments and f"\n**Attached Files**\n{attachments}" or ""
            await getMegaTable(cached).Log("messages",embed=fromdict({"title":"Message Deleted","description":f"A message from <@{cached.author.id}> ({cached.author}) was deleted from <#{cached.channel.id}>{attachmentfinal}\n**Old Content**\n{cached.content}","color":colours["error"]}))
@client.event
async def on_reaction_add(reaction,user):
    if user.id == client.user.id: #If its the bot
        return
    for listener in list(ReactionListenList):
        await listener.Check(reaction.message,user,reaction.emoji)
@client.event
async def on_guild_join(guild):
    log(f"Entered new guild: {guild.id}")
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
        if not exists(invitesBefore,invId):
            invitesBefore[invId] = {"m":invInfo["m"],"u":0}
        if invitesBefore[invId]["u"] < invInfo["u"]:
            await gmt.Log("invites",embed=fromdict({"title":"Invite Log","description":f"User <@{member.id}> ({member}) has joined through <@{invInfo['m'].id}> ({invInfo['m']})'s invite (discord.gg/{invId})\nInvite is at {invInfo['u']} uses","color":colours["info"]}))
            break
    gmt.InviteTrack = invitesAfter
@client.event
async def on_member_update(before,after):
    #Log nickname changes.
    #TODO: Add filtering the new nickname here too
    gmt = getMegaTable(before)
    if after.nick and gmt.FilterNicknames:
        for word in gmt.WordBlockList:
            if after.nick.lower().find(word) > -1:
                try:
                    await after.edit(nick=None,reason=f"User nickname violated filter of '{word}'")
                    return
                except:
                    pass #Lacking permissions
    if before.nick != after.nick:
        logmsg = await gmt.Log("users",embed=fromdict({"title":"User Log","description":f"User <@{before.id}> ({before}) has changed their nickname from {before.nick} to {after.nick}","color":colours["info"]}))
        if logmsg:
            gmt.ProtectMessage(logmsg.id,1209600) #14 Days

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
    loadModules(f"User {msg.author}")
    await msg.channel.send(":+1:") #Confirmation
Command("d -reload modules",loadModulesAsync,0,"Reloads all the modules",{},None,"dev")

#Finish off - load configs
log("done commands, loading configs")
for i in os.listdir("storage/settings"):
    try:
        j = json.loads(open("storage/settings/"+i).read())
    except:
        log("[JSON] Load failed for file "+i)
    else:
        if not exists(j,"Guild"):
            log("[JSON] Guild index missing for file "+i)
            continue
        getMegaTable(j["Guild"]).LoadConfig(j)
log("loaded configs, main is finished")
