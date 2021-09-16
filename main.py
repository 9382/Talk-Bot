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
            open(filename,"rb").write(backup)
            print("[Safe Write] Failed to write to",filename,":",exc)
        else:
            print("[Safe Write] Failed to write to",filename,"with no backup available:",exc)
        return
    return True
def currentDate():
    return str(datetime.fromtimestamp(math.floor(time.time()))) #Long function list be like
fromdict = discord.Embed.from_dict
numRegex = regex.compile('\d+')
colours = {'info':0x5555DD,'error':0xFF0000,'success':0x00FF00,'warning':0xFFAA00,'plain':0xAAAAAA}
wordBlockList = {}
loggedMessages = {}
channelList = {}
queuedChannels = {}
nsfwBlockedTerms = {}
mediaFilterList = {}
logChannelList = {}
guildInviteTrack = {}
async def setFilterTime(msg,bufferTime):
    deleteTime = time.time()+bufferTime
    if bufferTime > 0:
        loggedMessages[msg] = deleteTime
    else:
        try:
            await msg.delete()
        except:
            loggedMessages[msg] = deleteTime
    return True
findMediaRegex = regex.compile("https?://(cdn\.discordapp\.com/attachments/|tenor\.com/view/)")
async def filterMessage(msg,forceFilter=False): #Main filter handler, just await it with msg var to filter it
    if exists(loggedMessages,msg): #If already queued for deletion
        return True
    if not exists(wordBlockList,msg.guild.id): #on_ready causing on_error loop, gonna try catch with this. Why it isnt already catching idfk
        wordBlockList[msg.guild.id] = {}
    if not exists(mediaFilterList,str(msg.channel.id)): #this would probably fail too, so doing this pre-emptively
        mediaFilterList[str(msg.channel.id)] = None
    for i in wordBlockList[msg.guild.id]:
        bufferTime = wordBlockList[msg.guild.id][i]
        if bufferTime == None:
            continue
        if msg.content.lower().find(i) != -1 or forceFilter:
            print("[Filter] Msg Filtered:",msg.content,'|->',i)
            return await setFilterTime(msg,bufferTime)
        for embed in msg.embeds:
            if embed.title and embed.title.lower().find(i) != -1:
                return await setFilterTime(msg,bufferTime)
            if embed.description and embed.description.lower().find(i) != -1:
                return await setFilterTime(msg,bufferTime)
    bufferTime = mediaFilterList[str(msg.channel.id)]
    if bufferTime != None:
        if findMediaRegex.search(msg.content.lower()):
            return await setFilterTime(msg,bufferTime)
        for i in msg.attachments:
            if findMediaRegex.search(i.url.lower()):
                return await setFilterTime(msg,bufferTime)
        for embed in msg.embeds:
            if embed.image:
                return await setFilterTime(msg,bufferTime)
async def getGuildInviteStats(guild):
    toReturn = {}
    try:
        invites = await guild.invites()
    except:
        return
    for invite in invites:
        toReturn[invite.id] = {"m":invite.inviter,"u":invite.uses}
    return toReturn
client = commands.Bot(command_prefix=prefix,help_command=None,intents=discord.Intents(guilds=True,messages=True,members=True))
#Note that due to the on_message handler, i cant use the regular @bot.event shit, so custom handler it is
logChannels = {'errors':872153712347467776,'boot-ups':872208035093839932}
@client.event
async def on_error(error,*args,**kwargs):
    if exists(args,0):
        causingCommand = args[0].content
    else:
        causingCommand = "<none>"
    print("[Fatal Error] Causing command:",causingCommand,"error:")
    traceback.print_exc(file=sys.stderr)
    try: #Notifying of error
        pass# await args[0].channel.send(embed=fromdict({'title':'Fatal Error','description':'A fatal error has occured and has been automatically reported to the creator','color':colours['error']}))
    except Exception as exc:
        print("[Fatal Error] Failed to alert the user of the fail:",exc)
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
        pass
@client.event
async def on_guild_join(guild):
    guildInviteTrack[guild.id] = await getGuildInviteStats(guild)
    logChannelList[guild.id] = None
@client.event
async def on_member_join(member):
    guild = member.guild
    if not exists(guildInviteTrack,guild.id) or not guildInviteTrack[guild.id]:
        guildInviteTrack[guild.id] = await getGuildInviteStats(guild)
        return
    invitesBefore = guildInviteTrack[guild.id]
    invitesAfter = await getGuildInviteStats(guild)
    if not invitesAfter:
        return
    for inviteId in invitesAfter:
        inviteInfo = invitesAfter[inviteId]
        if not exists(invitesBefore,inviteId):
            invitesBefore[inviteId] = {"m":inviteInfo["m"],"u":0}
        if invitesBefore[inviteId]["u"] < inviteInfo["u"]:
            if logChannelList[guild.id]:
                await client.get_channel(logChannelList[guild.id]).send(embed=fromdict({"title":"Invite Log","description":f"User <@{member.id}> ({member}) has joined through <@{inviteInfo['m'].id}> ({inviteInfo['m']})'s invite (discord.gg/{inviteId})\nInvite is at {inviteInfo['u']} uses","color":colours["info"]}))
            break
    guildInviteTrack[guild.id] = invitesAfter
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
def addCommand(command,function,ratelimit,description,descriptionArgs,extraInfo,group,descriptionReference=None): #function must be async and have msg,args
    if type(command) != str: #Probably a table, probably declaring multiple aliases
        for commandalias in command:
            addCommand(commandalias,function,ratelimit,description,descriptionArgs,extraInfo,group,descriptionReference) #Encourages self calling but oh well who cares, shouldnt self-call more than once
            descriptionReference = descriptionReference or commandalias
        return
    if descriptionReference:
        description = "See `"+descriptionReference+"`"
    if group == "dev": #Dev functions, no public access allowed
        if exists(devCommands,command):
            print("[AddCmd] Dev command '"+command+"' was declared twice")
        devCommands[command] = {"f":function,"a":extraInfo,"d":description,"r":ratelimit,"i":descriptionArgs}
    elif group == "admin": #Requires administrator permission or equivilant (e.g. server owner)
        if exists(adminCommands,command):
            print("[AddCmd] Admin command '"+command+"' was declared twice")
        adminCommands[command] = {"f":function,"a":extraInfo,"d":description,"r":ratelimit,"i":descriptionArgs}
    else: #Regular command available to all users
        if exists(userCommands,command):
            print("[AddCmd] User command '"+command+"' was declared twice")
        userCommands[command] = {"f":function,"a":extraInfo,"d":description,"r":ratelimit,"i":descriptionArgs,'g':group} #Group is used to shorten ##cmds
ratelimitInfo = {}
async def doTheCheck(msg,args,command,commandInfo): #Dont wanna type this 3 times
    if not exists(ratelimitInfo,msg.author.id): #Prevent ratelimit logic from erroring
        ratelimitInfo[msg.author.id] = {}
    callingCommand = prefix+command
    if msg.content.lower().startswith(callingCommand) and (not msg.content[len(callingCommand)] or msg.content[len(callingCommand)] == " " or msg.content[len(callingCommand)] == "\n"): #Find the fitting command if it exists
        arg0 = args[0]
        args[0] = arg0[:len(callingCommand)]
        if arg0[len(callingCommand)+1:]:
            args.insert(1,arg0[len(callingCommand)+1:]) #Fix the issue of ##CMD\nText missing the Text part
        if not exists(ratelimitInfo[msg.author.id],commandInfo['f']): #Prevent ratelimit logic from erroring
            ratelimitInfo[msg.author.id][commandInfo['f']] = {'t':0,'a':False} #Based off of the called function to prevent alias abuse
        ratelimitVars = ratelimitInfo[msg.author.id][commandInfo['f']]
        validPoint = ratelimitVars['t'] + commandInfo['r']
        if validPoint > time.time(): #If lastTime + rateLimit > currentTime: Dont allow
            if not ratelimitVars['a']: #If not already warned: Warn
                ratelimitVars['a'] = True
                validTime = validPoint-time.time()
                await msg.channel.send(embed=fromdict({'title':'Slow Down','description':'That command is limited for '+str(validTime)[:4]+' more seconds','color':colours['warning']}),delete_after=validTime)
            return True
        ratelimitVars['t'] = time.time() #Update last time, passed rate limit check
        ratelimitVars['a'] = False #The 'a' is just so you cant make the bot spam cooldown messages for the same command
        if commandInfo["a"] != None:
            await commandInfo["f"](msg,args,commandInfo["a"])
        else:
            await commandInfo["f"](msg,args)
        return True
    return False
@client.event
async def on_message(msg):
    if not msg.guild or msg.author.id == client.user.id: #Only do stuff in guild, ignore messages by the bot
        if msg.guild:
            await filterMessage(msg)
        elif msg.author.id != client.user.id:
            await msg.channel.send(embed=fromdict({'title':'Not here','description':'This bot can only be used in a server, and not dms','color':colours['error']}))
        return
    await filterMessage(msg)
    if type(msg.author) == discord.User: #Webhook
        return
    if not exists(wordBlockList,msg.guild.id): #This entire exists() section is to avoid crashing later on
        wordBlockList[msg.guild.id] = {}
    if not exists(channelList,msg.guild.id):
        channelList[msg.guild.id] = {}
    if not exists(nsfwBlockedTerms,msg.guild.id):
        nsfwBlockedTerms[msg.guild.id] = []
    if not exists(mediaFilterList,msg.channel.id):
        mediaFilterList[msg.channel.id] = None
    args = msg.content.split(' ') #Please keep in mind the first argument is the calling command
    if msg.author.id == 260016427900076033: #Funny commands just for me
        for command in devCommands:
            if await doTheCheck(msg,args,command,devCommands[command]):
                return
    if msg.author.guild_permissions.administrator:
        for command in adminCommands:
            if await doTheCheck(msg,args,command,adminCommands[command]):
                return
    for command in userCommands:
        if await doTheCheck(msg,args,command,userCommands[command]):
            return
@client.event
async def on_raw_message_edit(msg): #On message edit to avoid bypassing
    try:
        messageObj = discord.PartialMessage(channel=client.get_channel(int(msg.data['channel_id'])),id=int(msg.data['id']))
    except:
        pass #Dont care if this errors since it bloody will and its not an issue
    else:
        await filterMessage(messageObj)
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
async def constantMessageCheck(): #For message filter
    global finishedLastCycle
    if stopCycling:
        finishedLastCycle = True
        return
    try:
        toDeleteList = {}
        loggedMessagesCache = loggedMessages #If table size changes during calculations, it errors. Thats bad
        for i in loggedMessagesCache:
            if not loggedMessagesCache[i]:
                continue
            if type(i) == discord.Message or type(i) == discord.PartialMessage:
                if loggedMessagesCache[i] < time.time():
                    if not exists(toDeleteList,i.channel.id):
                        toDeleteList[i.channel.id] = []
                    toDeleteList[i.channel.id].append(i)
                    loggedMessages[i] = None
            else:
                msgInfo = loggedMessagesCache[i]
                if not msgInfo["t"]: #IDEK how
                    loggedMessages[i] = None
                    continue
                msgInfo["c"] = int(msgInfo["c"]) #Dont ask, its to do with how it saved, ok?
                if msgInfo["t"] < time.time():
                    channel = client.get_channel(msgInfo["c"])
                    if channel:
                        if not exists(toDeleteList,msgInfo["c"]):
                            toDeleteList[msgInfo["c"]] = []
                        partialMessage = discord.PartialMessage(channel=channel,id=i)
                        if partialMessage:
                            toDeleteList[msgInfo["c"]].append(partialMessage)
                            loggedMessages[i] = None
        if toDeleteList != {}:
            for channel in toDeleteList:
                try:
                    await client.get_channel(channel).delete_messages(toDeleteList[channel])
                except Exception as exc:
                    pass# print("[?] BulkDelete",exc)
    except Exception as exc:
        print("[LoggedMessages] Exception:",exc)
@tasks.loop(seconds=10)
async def constantChannelCheck(): #For queued channel clearing
    try:
        for guild in client.guilds:
            guildChannelList = guild.text_channels
            if not exists(queuedChannels,guild.id): #No errors here, buddy
                queuedChannels[guild.id] = {}
            for channelName in queuedChannels[guild.id]:
                channelCloneTime = queuedChannels[guild.id][channelName]
                if channelCloneTime and channelCloneTime < time.time():
                    for t in guildChannelList:
                        if channelName == t.name:
                            queuedChannels[guild.id][channelName] = time.time()+channelList[guild.id][channelName]
                            await cloneChannel(t.id)
    except Exception as exc:
        print("[!] ChannelClear Exception:",exc)
@tasks.loop(seconds=90)
async def updateConfigFiles(): #So i dont have pre-coded values
    # print("Updating config")
    try:
        for guild in client.guilds:
            if not exists(wordBlockList,guild.id):
                wordBlockList[guild.id] = {}
            if not exists(channelList,guild.id):
                channelList[guild.id] = {}
            if not exists(nsfwBlockedTerms,guild.id):
                nsfwBlockedTerms[guild.id] = []
            if not exists(logChannelList,guild.id):
                logChannelList[guild.id] = None
            fileName = 'storage/settings/'+str(guild.id)+".json"
            safeWriteToFile(fileName,json.dumps({"guild":guild.id,"wordBlockList":wordBlockList[guild.id],"channelList":channelList[guild.id],"nsfwBlockedTerms":nsfwBlockedTerms[guild.id],"logChannel":logChannelList[guild.id]}))
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
        if not exists(guildInviteTrack,guild.id) or not guildInviteTrack[guild.id]:
            guildInviteTrack[guild.id] = await getGuildInviteStats(guild)
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
    loggedMessagesCache2 = loggedMessages #If table size changes during calculations, it errors. Thats bad
    print("Invoking save - sleep time:",sleepTime)
    toSave = {}
    for message in loggedMessagesCache2:
        if type(message) == discord.Message or type(message) == discord.PartialMessage:
            if not loggedMessagesCache2[message]:
                continue
            if not exists(toSave,message.channel.id):
                toSave[message.channel.id] = {}
            toSave[message.channel.id][message.id] = loggedMessagesCache2[message]
        else:
            info = loggedMessagesCache2[message]
            if not info or not info["t"]:
                continue
            if not exists(toSave,info["c"]):
                toSave[info["c"]] = {}
            toSave[info["c"]][message] = info["t"]
    safeWriteToFile("storage/settings/deletion_queue.json",json.dumps(toSave))
    print("Deletion queue save finished")
    toSave = {}
    for channel in mediaFilterList:
        if mediaFilterList[channel] != None:
            toSave[channel] = mediaFilterList[channel]
    safeWriteToFile("storage/settings/media_filters.json",json.dumps(toSave))
    print("Media filter list save finished")
    await updateConfigFiles()
    print("Default save finished")
    print("Closing")
    await client.close()
addCommand("d -update",forceUpdate,0,"",{},None,"dev")

async def cmdList(msg,args): #just handles itself and its lovely
    isAdmin = msg.author.guild_permissions.administrator
    if not exists(args,1):
        allGroups = ["admin"] #only runs through userCommands
        allGroupsText = "\n`admin`"
        for command in userCommands:
            commandGroup = userCommands[command]['g']
            if not (commandGroup in allGroups):
                allGroups.append(commandGroup)
                allGroupsText += "\n`"+commandGroup+"`"
        await msg.channel.send(embed=fromdict({'title':'Select command list','description':'Please select a command subsection from this list:'+allGroupsText,'color':colours['info']}))
        return
    else:
        cmdList = (args[1] == "admin" and adminCommands) or (args[1] == "dev" and msg.author.id == 260016427900076033 and devCommands) or args[1]
    if type(cmdList) == str: # A general command, gotta find all matching cmd groups
        cmdList = {}
        for command in userCommands:
            commandInfo = userCommands[command]
            if commandInfo['g'].lower() == args[1].lower():
                cmdList[command] = commandInfo
    if cmdList == {}:
        await msg.channel.send(embed=fromdict({'title':'Invalid Group','description':'The group '+args[1]+' is not a valid group','color':colours['error']}),delete_after=30)
        return
    cmdMessageContent = "**Syntax**\n`<>` is a required argument, `[]` is an optional argument\n\n**Commands**"
    for command in cmdList:
        commandInfo = cmdList[command]
        argMessageContent = ""
        for argName in commandInfo['i']:
            argRequired = commandInfo['i'][argName]
            argMessageContent += " "+((argRequired and f"<{argName}>") or f"[{argName}]")
        cmdMessageContent += "\n`"+command+argMessageContent+"` - "+commandInfo['d']
    await msg.channel.send(embed=fromdict({'title':'Command List','description':cmdMessageContent,'color':colours['info']}))
addCommand(["commands","cmds"],cmdList,1,"List all commands",{"section":False},None,"general")

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
    logChannelList[msg.guild.id] = wantedChannel.id
    await msg.channel.send(embed=fromdict({"title":"Success","description":"Set log channel successfully","color":colours["success"]}))
addCommand("setlogs",setLogChannel,3,"Set the log channel to the channel provided",{"channel":True},None,"admin")

async def blockWord(msg,args):
    if not exists(args,2):
        await msg.channel.send(embed=fromdict({'title':'Error','description':'You must include a word to ban and its time until deletion','color':colours['error']}),delete_after=10)
        return
    success,result = strToTimeAdd(args[2])
    if not success:
        await msg.channel.send(embed=fromdict({'title':'Error','description':result,'color':colours['error']}),delete_after=10)
        return
    word = args[1].lower()
    wordBlockList[msg.guild.id][word] = result
    await msg.channel.send(embed=fromdict({'title':'Success','description':'Any messages containing '+word+' will be deleted after '+simplifySeconds(result),'color':colours['success']}))
addCommand("blockword",blockWord,0,"Add a word to the filter list",{"word":True,"deletiontime":True},None,"admin")
async def unblockWord(msg,args):
    if not exists(args,1):
        await msg.channel.send(embed=fromdict({'title':'Error','description':'You must include a word to unban','color':colours['error']}),delete_after=10)
        return
    word = args[1].lower()
    wordBlockList[msg.guild.id][word] = None
    await msg.channel.send(embed=fromdict({'title':'Success','description':f'{word} is allowed again','color':colours['success']}))
addCommand("unblockword",unblockWord,0,"Remove a word from the filter list",{"word":True},None,"admin")

async def list_admin(msg,args): # God this looks horrible. NOTE: Patch this up at some point
    if len(args) < 2:
        await msg.channel.send(embed=fromdict({'title':'Settings List','description':'To get a list of what you are looking for, please use one of the following sub-commands:\n`list words`\n`list channels`\n`list tags`','color':colours['info']}))
        return
    index = 0
    finalMessage = ""
    if args[1] == "words":
        for i in wordBlockList[msg.guild.id]:
            if wordBlockList[msg.guild.id][i] != None:
                index += 1
                finalMessage = finalMessage+'\n#'+str(index)+' - "'+i+'" '+simplifySeconds(wordBlockList[msg.guild.id][i])
        await msg.channel.send(embed=fromdict({'title':'Blocked Word List','description':f'List of banned words, and how long until the message gets deleted:{finalMessage}','color':colours['info']}))
    elif args[1] == "channels":
        for i in channelList[msg.guild.id]:
            if channelList[msg.guild.id][i]:
                index += 1
                finalMessage = finalMessage+'\n#'+str(index)+' - "'+i+'" every '+simplifySeconds(channelList[msg.guild.id][i])
        await msg.channel.send(embed=fromdict({'title':'Clear Channel List','description':f'List of channels that are set to clear every so often:{finalMessage}','color':colours['info']}))
    elif args[1] == "tags":
        for i in nsfwBlockedTerms[msg.guild.id]:
            index += 1
            finalMessage = finalMessage+'\n#'+str(index)+' - "'+i+'"'
        await msg.channel.send(embed=fromdict({'title':'Blocked Tags List','description':f'List of tags that are blocked on the NSFW commands:{finalMessage}','color':colours['info']}))
    else:
        await msg.channel.send(embed=fromdict({'title':'Settings List','description':'To get a list of what you are looking for, please use one of the following sub-commands:\n`list words`\n`list channels`\n`list tags`','color':colours['info']}))
        return
addCommand("list",list_admin,0,"View the list of settings to do with administration",{"subsection":False},None,"admin")

async def clearChannel(msg,args):
    if len(args) < 2:
        await msg.channel.send(embed=fromdict({'title':'Error','description':'You must include a channel name','color':colours['error']}),delete_after=30)
        return
    channelName = args[1]
    frequency = exists(args,2) and args[2]
    if frequency:
        success,result = strToTimeAdd(frequency)
        if not success:
            await msg.channel.send(embed=fromdict({'title':'Error','description':result,'color':colours['error']}),delete_after=30)
            return
        channelList[msg.guild.id][channelName] = result
        queuedChannels[msg.guild.id][channelName] = time.time()+result
        await msg.channel.send(embed=fromdict({'title':'Success','description':channelName+' is queued to clear every '+simplifySeconds(result),'color':colours['success']}))
    else:
        guildChannelList = msg.guild.text_channels
        for t in guildChannelList:
            if channelName == t.name:
                await cloneChannel(t.id)
addCommand("clearchannel",clearChannel,0,"Add a channel to be cleared every so often OR clear now (no frequency)",{"channelName":True,"frequency":False},None,"admin")
async def unclearChannel(msg,args):
    if len(args) < 2:
        await msg.channel.send(embed=fromdict({'title':'Error','description':'You must include a channel name to stop clearing','color':colours['error']}),delete_after=30)
        return
    channelName = args[1]
    channelList[msg.guild.id][channelName] = None
    queuedChannels[msg.guild.id][channelName] = None
    await msg.channel.send(embed=fromdict({'title':'Success','description':channelName+' will no longer be cleared','color':colours['success']}))
addCommand("unclearchannel",unclearChannel,0,"Stop a channel from being auto-cleared",{"channelName":True},None,"admin")

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
    if await filterMessage(msg):
        await filterMessage(voteMsg,True) #Set the vote message for deletion
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
addCommand("vote",publicVote,10,"Make a public vote about anything with an optional image",{"text":True,"imagefile":False},None,"general")

async def blockMedia(msg,args):
    if len(args) < 2:
        await msg.channel.send(embed=fromdict({'title':'Error','description':'You must include the time until deletion','color':colours['error']}),delete_after=10)
        return
    success,result = strToTimeAdd(args[1])
    if not success:
        await msg.channel.send(embed=fromdict({'title':'Error','description':result,'color':colours['error']}),delete_after=30)
        return
    mediaFilterList[str(msg.channel.id)] = result
    await msg.channel.send(embed=fromdict({'title':'Success','description':'All media will be deleted after '+simplifySeconds(result),'color':colours['success']}))
addCommand("blockmedia",blockMedia,0,"Remove all media in a channel after a certain duration",{"deletiontime":True},None,"admin")
async def unblockMedia(msg,args):
    mediaFilterList[str(msg.channel.id)] = None
    await msg.channel.send(embed=fromdict({'title':'Success','description':'Media will no longer be removed','color':colours['success']}))
addCommand("unblockmedia",unblockMedia,0,"Stop auto-filtering a channel's media",{},None,"admin")

print('attempting import')
''' Load modules from the modules folder
Only use this for storing commands that dont rely on other commands, as load order is random
This is so i dont clog up the entirety of this main script with like 2k lines
The main code can be found in modules/__main__.py '''
from modules.__main__ import exec_list,load_modules
load_modules("Main")
async def loadModulesAsync(msg,args):
    load_modules("User "+msg.author.name)
addCommand("d -reload modules",loadModulesAsync,0,"",{},None,"dev")
print("Tuple acceptable")
for contents in exec_list:
    # try:
    exec(contents,globals())
    # except Exception as exc:
    #     print("[Modules] Module import error ->",exc)

print('done commands')
for i in os.listdir('storage/settings'):
    try:
        j = json.loads(open('storage/settings/'+i).read())
    except:
        print("[JSON] Load failed for file",i)
        continue #Failsafe
    if i == "deletion_queue.json":
        for channelid in j:
            for messageid in j[channelid]:
                loggedMessages[messageid] = {"c":channelid,"t":j[channelid][messageid]}
        continue
    if i == "media_filters.json":
        mediaFilterList = j #Redesign this to be guild specific, thanks!
        continue
    guild = j['guild']
    for tableType in j:
        if tableType == "wordBlockList":
            wordBlockList[guild] = j[tableType]
        if tableType == "channelList":
            channelList[guild] = j[tableType]
        if tableType == "nsfwBlockedTerms":
            nsfwBlockedTerms[guild] = j[tableType]
        if tableType == "logChannel":
            logChannelList[guild] = j[tableType]
    for i in channelList[guild]:
        if not channelList[guild][i]:
            continue
        if not exists(queuedChannels,guild):
            queuedChannels[guild] = {}
        queuedChannels[guild][i] = time.time()+channelList[guild][i]
print('loaded config')