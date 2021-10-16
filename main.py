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
        self.LoggedMessages = {}
        self.Confirmations = {}
        self.ChannelLimits = {}
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
        if buffer == None: # Failsafe, just in case
            return
        print("[Filter] Msg Filtered ->",msg.content,buffer)
        if buffer <= 0:
            try:
                asyncio.run(msg.delete())
                return buffer
            except:
                pass
        self.LoggedMessages[msg.id] = FilteredMessage(time.time()+buffer,messageObj=msg)
        return buffer
    async def FilterMessage(self,msg,forced=False): # Now guild specific, how nice :)
        if exists(self.LoggedMessages,msg.id):
            return self.LoggedMessages[msg.id].Deletion-time.time()
        if forced:
            return await self.AddToFilter(msg,int(forced))
        for word in self.WordBlockList: #Word filter > Media filter
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
    def FormatLoggedMessages(self):
        LoggedMessagesSave = {}
        LMCache = self.LoggedMessages
        for msgid in LMCache:
            message = LMCache[msgid]
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
                "ChannelLimits":self.ChannelLimits,
                "LoggedMessages":self.FormatLoggedMessages()}
    def LoadSave(self,data):
        for catagory in data:
            try:
                if catagory == "LoggedMessages":
                    self.LoggedMessages = {}
                    for channel in data["LoggedMessages"]:
                        for message in data["LoggedMessages"][channel]:
                            expirey = data["LoggedMessages"][channel][message]
                            self.LoggedMessages[int(message)] = FilteredMessage(expirey,int(message),int(channel))
                elif hasattr(self,catagory):
                    setattr(self,catagory,data[catagory])
                else:
                    print(f"[GuildObject {str(self.Guild)}] Unknown Catagory",catagory)
            except:
                print(f"[GuildObject {str(self.Guild)}] Invalid catagory data",catagory)
    async def CreateConfirmation(self,msg,args,function):
        confirmationObj = Confirmation(msg,args,function)
        self.Confirmations[msg.author.id] = confirmationObj
        await confirmationObj.Alert()
        return confirmationObj
    async def CheckConfirmation(self,msg):
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
    if type(obj) == discord.Message or type(obj) == discord.PartialMessage:
        gid = obj.guild.id
    elif type(obj) == discord.Guild:
        gid = obj.id
    elif type(obj) == int:
        gid = obj
    if gid:
        if not exists(guildMegaTable,gid):
            guildMegaTable[gid] = GuildObject(gid)
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
        return "0 seconds" #Maybe set it to "now"?
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
ReactionListenList = []
class WatchReaction: #More classes
    def __init__(self,msg,user,emoji,function,args):
        self.MsgId = (type(msg) == int and msg) or msg.id
        self.UserId = (type(user) == int and user) or user.id #The user whitelisted to react to it
        self.Emoji = emoji
        self.Function = function
        self.Args = args
        self.Expirey = time.time()+60
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
    title,preText,pagedContent,maxPage,page = args[0],args[1],args[2],args[3],args[4]
    page += (emoji=="➡️" and 1) or -1
    page = min(max(0,page),maxPage) #Limit page
    await msg.edit(embed=fromdict({"title":title,"description":preText+"\n".join(pagedContent[page]),"footer":{"text":f"Page {str(page+1)}/{str(maxPage+1)}"},"color":colours["info"]}))
    await UpdateReactionWatch(msg,"all",[title,preText,pagedContent,maxPage,page])
async def createPagedEmbed(user,channel,title,content,pageLimit=10,preText=""): #For long lists in embeds
    pagedContent = []
    index = 0
    for text in content:
        if index % pageLimit == 0:
            pagedContent.insert(index//pageLimit,[])
        pagedContent[index//pageLimit].append(text)
        index += 1
    maxPage = index//pageLimit
    if maxPage == 0:
        await channel.send(embed=fromdict({"title":title,"description":preText+"\n".join(pagedContent[0]),"color":colours["info"]}))
        return
    embed = await channel.send(embed=fromdict({"title":title,"description":preText+"\n".join(pagedContent[0]),"footer":{"text":f"Page 1/{str(maxPage+1)}"},"color":colours["info"]}))
    for e in ["⬅️","➡️"]: #No, i dont know why sublime is different for ➡️
        await embed.add_reaction(e)
        WatchReaction(embed,user,e,changePageEmbed,[title,preText,pagedContent,maxPage,0])
client = commands.Bot(command_prefix=prefix,help_command=None,intents=discord.Intents(guilds=True,messages=True,members=True,reactions=True))
#Note that due to the on_message handler, i cant use the regular @bot.command decorator, so custom handler it is
logChannels = {'errors':872153712347467776,'boot-ups':872208035093839932} # These are different from the guild-defined LogChannel channels, these are for the bot to tell me whats wrong or ok
@client.event
async def on_error(error,*args,**kwargs):
    if exists(args,0):
        try:
            causingCommand = args[0].content
        except:
            causingCommand = args[0]
    else:
        causingCommand = "<none>"
    print("[Fatal Error] Causing command:",causingCommand,"error:")
    traceback.print_exc(file=sys.stderr)
    try: #Logging
        errorFile = tempFile()
        file = open(errorFile,"w",encoding="ANSI",newline='')
        try:
            traceback.print_exc(file=file)
        except Exception as exc:
            print("[Fatal Error] Error Log file failed to write:",exc)
            pass
        file.close()
        await client.get_channel(logChannels['errors']).send("Error in client\nTime: "+currentDate()+"\nCausing command: "+str(causingCommand),file=discord.File(errorFile))
        os.remove(errorFile)
    except Exception as exc:
        print("[Fatal Error] Failed to log:",currentDate(),exc)
@client.event
async def on_ready():
    await client.change_presence(activity=discord.Game(name='##cmds'))
    print('connected v'+discord.__version__)
    try: #Notifying of start-up
        await client.get_channel(logChannels['boot-ups']).send("Ive connected at "+currentDate())
    except:
        print("Failed to alert of bootup at",currentDate())
@client.event
async def on_reaction_add(reaction,user):
    if user.id == client.user.id: #If its me
        return
    ListenListCache = ReactionListenList
    for listener in ListenListCache:
        await listener.Check(reaction.message,user,reaction.emoji)
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
    async def Run(self,msg,args,bypassRL=False):
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
        return True,0
async def doTheCheck(msg,args,commandTable): #Dont wanna type this 3 times
    arg0 = args[0]
    if '\n' in arg0:
        args[0] = arg0.split('\n')[0]
        args.insert(1,arg0.split('\n')[1])
    c = msg.content
    for command in commandTable:
        cregion = len(prefix+command) #command region
        if prefix+command == c[:cregion] and (not exists(c,cregion) or c[cregion] == " " or c[cregion] == "\n"):
            success,result = await commandTable[command].Run(msg,args)
            if not success:
                if result != -1: # If first repeat:
                    await msg.channel.send(embed=fromdict({'title':'Slow Down','description':'That command is limited for '+simplifySeconds(math.floor(result))+' more seconds','color':colours['warning']}),delete_after=result)
            return True
async def checkHistoryClear(msg):
    gmt = getMegaTable(msg)
    if msg.channel.id in gmt.ChannelLimits:
        msgLimitInfo = gmt.ChannelLimits[msg.channel.id]
        msgLimit,lastCheck = msgLimitInfo[0],msgLimitInfo[1]
        if lastCheck + 2 > time.time(): #Limit cause history call is quite hard
            gmt.ChannelLimits[msg.channel.id][1] = time.time()
            try:
                messageList = await msg.channel.history(limit=msgLimit+15).flatten() #msgLimit+15 to catch missed
            except Exception as exc:
                print("[History] Failed to fetch:",exc)
            else:
                for message in messageList[msgLimit:]:
                    await gmt.FilterMessage(message,1) #1 to avoid deletion now, and queue it in the seperate task later
@client.event
async def on_message(msg):
    if not msg.guild or msg.author.id == client.user.id: #Only do stuff in guild, ignore messages by the bot
        if msg.guild:
            await getMegaTable(msg).FilterMessage(msg)
        elif msg.author.id != client.user.id:
            await msg.channel.send(embed=fromdict({'title':'Not here','description':'This bot can only be used in a server, and not dms','color':colours['error']}))
        return
    gmt = getMegaTable(msg)
    await gmt.FilterMessage(msg)
    await checkHistoryClear(msg) # This has quite a heavy wait time (upwards of 0.5) - consider threading or a better method
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
        gmt = getMegaTable(channel.guild) # Move over channel settings
        if channelid in gmt.MediaFilters:
            gmt.MediaFilters[newchannel.id] = gmt.MediaFilters[channelid]
        if channelid in gmt.ChannelLimits:
            gmt.ChannelLimits[newchannel.id] = gmt.ChannelLimits[channelid]
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
    global finishedLastCycle #Weird stop but it works
    if stopCycling:
        finishedLastCycle = True
        return
    try:
        toDeleteList = {}
        for guild in guildMegaTable:
            gmt = guildMegaTable[guild]
            LMCache = gmt.LoggedMessages
            for msgid in LMCache:
                message = LMCache[msgid]
                if message.Expired():
                    messageObj = message.GetMessageObj()
                    if messageObj:
                        if not exists(toDeleteList,message.Channel):
                            toDeleteList[message.Channel] = []
                        toDeleteList[message.Channel].append(messageObj)
                        gmt.LoggedMessages.pop(message.MessageId)
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

async def cmds(msg,args):
    cmdList = {"Admin":adminCommands}
    for command in userCommands:
        cmdInfo = userCommands[command]
        if not exists(cmdList,cmdInfo.Group):
            cmdList[cmdInfo.Group] = {}
        cmdList[cmdInfo.Group][command] = cmdInfo
    if exists(args,1): #Group Specific
        group = exists(cmdList,args[1]) and cmdList[args[1]]
        if msg.author.id == 260016427900076033 and args[1] == "dev":
            group = devCommands
        if not group:
            await msg.channel.send(embed=fromdict({"title":"Invalid group","description":f"The group '{args[1]}' doesnt exist","color":colours["error"]}))
            return
        finalText = []
        for command in group:
            cmdInfo = group[command]
            argMessageContent = ""
            for argName in cmdInfo.DescArgs:
                argRequired = cmdInfo.DescArgs[argName]
                argMessageContent += " "+((argRequired and f"<{argName}>") or f"[{argName}]")
            finalText.append("`"+command+argMessageContent+"` - "+cmdInfo.Description)
        await createPagedEmbed(msg.author,msg.channel,"Commands within "+args[1],finalText,10,"**Syntax**\n`<>` is a required argument, `[]` is an optional argument\n\n**Commands**\n")
    else: # Generalised (No group)
        finalText = f"do `{args[0]} <group>` to get more information on a group"
        for group in cmdList:
            finalText += f"\n**{group}**\n"
            for command in cmdList[group]:
                finalText += f"`{command}` "
        await msg.channel.send(embed=fromdict({"title":"Commands","description":finalText,"color":colours["info"]}))
Command(["commands","cmds"],cmds,1,"List all commands",{"group":False},None,"general")

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

print('attempting import')
''' Load modules from the modules folder
Only use this for storing commands, as load order is random
This is so i dont clog up the entirety of this main script with like 2k lines '''
def loadModules(origin=None):
    print("Loading modules origin=",origin)
    exec_list = []
    for fname in os.listdir("modules"):
        if not fname.endswith(".py"):
            continue
        if not os.path.isfile("modules/"+fname):
            continue
        if fname == "__main__.py":
            continue
        exec_list.append(bytes("#coding: utf-8\n","utf-8")+open("modules/"+fname,"rb").read())
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
        try:
            getMegaTable(j['Guild']).LoadSave(j)
        except:
            print("[JSON] Guild index failed for file",i)
print('loaded config')
