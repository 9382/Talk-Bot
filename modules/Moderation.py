validLogChannels = ["invites","messages","users"] #Adjust this manually
async def setLogChannel(msg,args):
    if not exists(args,1):
        await msg.channel.send(embed=fromdict({"title":"Log channel categories","description":"Valid log channel categories:\n"+"\n".join([f"`{c}`" for c in validLogChannels]),"color":colours["info"]}))
        return
    category = args[1].lower()
    if not category in validLogChannels:
        await msg.channel.send(embed=fromdict({"title":"Invalid category","description":f"{category} is not a valid category","color":colours["error"]}))
        return
    if exists(args,2):
        wantedChannel = numRegex.search(args[2]) and client.get_channel(int(numRegex.search(args[2]).group()))
        if not wantedChannel or wantedChannel.guild.id != msg.guild.id:
            await msg.channel.send(embed=fromdict({"title":"Not found","description":"The channel provided either doesnt exist, or i cant access it","color":colours["error"]}))
            return
        getMegaTable(msg).LogChannels[category] = wantedChannel.id
        await msg.channel.send(embed=fromdict({"title":"Success","description":f"Set log channel for {category} successfully","color":colours["success"]}))
    else: #Maybe make this a seperate command?
        try:
            getMegaTable(msg).LogChannels.pop(category)
        except:
            pass
        await msg.channel.send(embed=fromdict({"title":"Success","description":f"No longer logging {category}","color":colours["success"]}))
Command("setlogs",setLogChannel,3,"Set the log channel to the channel provided (provide no arguments for a list of log channels)",{"category":False,"channel":False},None,"admin")

async def prune(msg,args):
    if not HasPermission(msg.author,"manage_messages",msg.channel):
        await msg.channel.send(embed=fromdict({"title":"Error","description":"You don't have the permission to use that command here","color":colours["error"]}))
        return
    pruneAmount = exists(args,1) and numRegex.search(args[1]) and min(1000,max(0,int(numRegex.search(args[1]).group())))
    if pruneAmount:
        #await msg.channel.delete_messages(await msg.channel.history(limit=pruneAmount+1).flatten()) #+1 due to command message
        success,result = await clearMessageList(msg.channel,[message async for message in msg.channel.history(limit=pruneAmount+1)]) #+1 due to command message
        if success:
            await msg.channel.send(embed=fromdict({"title":"Success","description":f"{pruneAmount} message(s) have been cleared","color":colours["success"]}))
        else:
            await msg.channel.send(embed=fromdict({"title":"Error","description":f"The bot failed to prune the messages. Check its permissions, or try again\n`{result}`","color":colours["error"]}))
            log(f"[Prune {msg.guild.id}] Failed to prune {pruneAmount}+1: {result}")
    else:
        await msg.channel.send(embed=fromdict({"title":"Error","description":"Prune amount must be an integer","color":colours["error"]}),delete_after=10)
Command(["prune","purge"],prune,5,"Prunes a set amount of messages in the channel (Max 1000)",{"messages":True},None,"mod")

async def setmodrole(msg,args,removing):
    gmt = getMegaTable(msg)
    if removing:
        gmt.ModRole = 0
        await msg.channel.send(embed=fromdict({"title":"Success","description":"Removed any active moderator level role","color":colours["success"]}))
        return
    wantedRole = exists(args,1) and numRegex.search(args[1]) and int(numRegex.search(args[1]).group())
    if not wantedRole:
        await msg.channel.send(embed=fromdict({"title":"Error","description":"You must provide a role to become the moderator role","color":colours["error"]}),delete_after=10)
        return
    modrole = msg.guild.get_role(wantedRole)
    if not modrole:
        await msg.channel.send(embed=fromdict({"title":"Error","description":f"{wantedRole} does not point to a valid role","color":colours["error"]}),delete_after=10)
        return
    await msg.channel.send(embed=fromdict({"title":"Success","description":f"<@&{wantedRole}> now has moderator command permissions{gmt.ModRole and f', and <@&{gmt.ModRole}> has lost them' or ''}","color":colours["success"]}))
    gmt.ModRole = wantedRole #Have to use ID to allow saving
Command("setmodrole",setmodrole,3,"Set the role that allows people to run moderator level commands",{"role":True},False,"admin")
Command("removemodrole",setmodrole,3,"Removes the current mdoerator level role",{},True,"admin")

async def serverFilterInfo(msg,args):
    gmt = getMegaTable(msg)
    description = ""
    #Word filters
    description += f"**Word Filters**\n"
    if len(gmt.WordBlockList) > 0:
        for word,delay in gmt.WordBlockList.items():
            description += f"`{word}` - {simplifySeconds(delay)}\n"
    else:
        description += f"None\n"
    #NSFW Tag Blacklist
    description += "\n**NSFW Tag Blacklist**\n"
    if len(gmt.NSFWBlockList) > 0:
        for word in gmt.NSFWBlockList:
            description += f"`{word}`\n"
    else:
        description += f"None\n"
    #Channel stuff
    description += f"\n**Message Limits**\n"
    if len(gmt.ChannelLimits) > 0:
        for channel,limit in gmt.ChannelLimits.items():
            description += f"<#{channel}> - {limit} messages\n"
    else:
        description += f"None\n"
    description += f"\n**Media Filters**\n"
    if len(gmt.MediaFilters) > 0:
        for channel,delay in gmt.MediaFilters.items():
            description += f"<#{channel}> - {simplifySeconds(delay)}\n"
    else:
        description += f"None\n"
    gmt.ProtectMessage((await msg.channel.send(embed=fromdict({"title":"Filter Info","description":description,"color":colours["info"]}))),180)
Command("filters",serverFilterInfo,0,"Get information about the filter settings of the server",{},None,"mod")

async def serverModerationInfo(msg,args):
    gmt = getMegaTable(msg)
    description = ""
    #Display certain guild settings
    description += f"**Mod Role**\n{gmt.ModRole and f'<@&{gmt.ModRole}>' or 'None'}\n\n"
    #Display current filters
    description += f"**Filters**\nWord block list: {len(gmt.WordBlockList)} words\nNSFW tag blacklist: {len(gmt.NSFWBlockList)} tags\n"
    description += f"Message limits: {len(gmt.ChannelLimits)} entries\nMedia filters: {len(gmt.MediaFilters)} entries\n(For more information, see `{prefix}filters`)\n\n"
    description += f"**Nickname Filtering**\n{gmt.FilterNicknames and 'Enabled' or 'Disabled'}\n\n"
    #Display channels used for logging
    description += "**Log Channels**\n"
    lc = gmt.LogChannels
    for logtype in validLogChannels:
        description += f"{logtype}: {logtype in lc and f'<#{lc[logtype]}>' or 'None'}\n"
    #Display channel clear timings
    description += "\n**Channel Timers**\n"
    ccl,qc = gmt.ChannelClearList,gmt.QueuedChannels
    if len(ccl) > 0:
        for channel,timer in ccl.items():
            description += f"<#{getChannelByName(msg.guild,channel).id}>: Cleared every {simplifySeconds(timer)}\n"
    else:
        description += "None\n"
    #Send final message
    gmt.ProtectMessage((await msg.channel.send(embed=fromdict({"title":"Moderation Info","description":description,"color":colours["info"]}))),180)
Command("modinfo",serverModerationInfo,0,"Get information about the moderation settings of the server",{},None,"mod")

async def refilterbase(channel):
    gmt = getMegaTable(channel)
    try:
        messageList = [message async for message in channel.history(limit=None,after=datetime.fromtimestamp(time.time()//1-864000))] #All messages within 10 days (864000)
    except:
        return False,"Bot failed to fetch channel history"
    stats = {"Filt":0,"PreFilt":0,"Total":0}
    for message in messageList:
        stats["Total"] += 1
        if exists(gmt.LoggedMessages,message.id):
            stats["PreFilt"] += 1
            continue
        if await gmt.FilterMessage(message):
            stats["Filt"] += 1
    return True,stats
async def refilter(msg,args):
    imNotDead = await msg.channel.send(embed=fromdict({"Title":"Trying...","description":"Trying to refilter all messages. Give me a moment...","color":colours["info"]}))
    success,result = await refilterbase(msg.channel)
    await imNotDead.delete()
    if success:
        await msg.channel.send(embed=fromdict({"title":"Success","description":f"Successfully checked {result['Total']} messages.\n{result['Filt']} were filtered, and {result['PreFilt']} were already filtered","color":colours["success"]}))
    else:
        await msg.channel.send(embed=fromdict({"title":"Error","description":result,"color":colours["error"]}),delete_after=10)
Command("refilter",refilter,120,"Re-Filter's all messages of a chat within the last 10 days",{},None,"mod")
async def massrefilter(msg,args):
    imNotDead = await msg.channel.send(embed=fromdict({"Title":"Trying...","description":"Trying to refilter all messages in all channels. Give me a long moment...","color":colours["info"]}))
    fails,checks = 0,0
    stats = {"Filt":0,"PreFilt":0,"Total":0}
    for channel in msg.guild.channels:
        if type(channel) == discord.TextChannel:
            checks += 1
            success,result = await refilterbase(channel)
            if not success:
                fails += 1
            else:
                stats["Filt"] += result["Filt"]
                stats["PreFilt"] += result["PreFilt"]
                stats["Total"] += result["Total"]
    await imNotDead.delete()
    await msg.channel.send(embed=fromdict({"title":"Success","description":f"Successfully checked {stats['Total']} messages across {checks} channels.\n{fails} channels failed to refilter.\n{stats['Filt']} were filtered, and {stats['PreFilt']} were already filtered","color":colours["success"]}))
Command("massrefilter",massrefilter,600,"Re-Filter's all messages of every channel within the last 10 days",{},None,"mod")

async def protectMessage(msg,args): #Prevents a message from being filtered
    msgid = exists(args,1) and args[1]
    if not msgid:
        await msg.channel.send(embed=fromdict({"title":"Error","description":"You must provide the message ID to protect","color":colours["error"]}),delete_after=10)
        return
    try:
        msgid = int(msgid)
    except:
        await msg.channel.send(embed=fromdict({"title":"Error","description":"message ID must be a number","color":colours["error"]}),delete_after=10)
    else:
        getMegaTable(msg).ProtectMessage(msgid,9e9)
        await msg.channel.send(embed=fromdict({"title":"Success","description":str(msgid)+" is now protected","color":colours["success"]}))
Command("protect",protectMessage,2,"Prevents a message from being filtered",{"messageid":True},None,"mod")
async def unprotectMessage(msg,args):
    msgid = exists(args,1) and args[1]
    if not msgid:
        await msg.channel.send(embed=fromdict({"title":"Error","description":"You must provide the message ID to protect","color":colours["error"]}),delete_after=10)
        return
    try:
        msgid = int(msgid)
    except:
        await msg.channel.send(embed=fromdict({"title":"Error","description":"message ID must be a number","color":colours["error"]}),delete_after=10)
        return
    try:
        getMegaTable(msg).ProtectedMessages.pop(msgid)
    except:
        await msg.channel.send(embed=fromdict({"title":"Error","description":str(msgid)+" was never protected","color":colours["error"]}))
    else:
        await msg.channel.send(embed=fromdict({"title":"Success","description":str(msgid)+" is no longer protected","color":colours["success"]}))
Command("unprotect",unprotectMessage,2,"Removes a message ID from the protected list",{"messageid":True},None,"mod")

async def blockWord(msg,args):
    if not exists(args,2):
        await msg.channel.send(embed=fromdict({"title":"Error","description":"You must include a word to ban and its time until deletion","color":colours["error"]}),delete_after=10)
        return
    success,result = strToTimeAdd(args[2])
    if not success:
        await msg.channel.send(embed=fromdict({"title":"Error","description":result,"color":colours["error"]}),delete_after=10)
        return
    word = args[1].lower()
    getMegaTable(msg).WordBlockList[word] = result
    await msg.channel.send(embed=fromdict({"title":"Success","description":f"Any messages containing {word} will be deleted after {simplifySeconds(result)}","color":colours["success"]}))
Command("blockword",blockWord,1,"Add a word to the filter list",{"word":True,"deletion time":True},None,"admin")
async def unblockWord(msg,args):
    if not exists(args,1):
        await msg.channel.send(embed=fromdict({"title":"Error","description":"You must include a word to unban","color":colours["error"]}),delete_after=10)
        return
    word = args[1].lower()
    try:
        getMegaTable(msg).WordBlockList.pop(word)
    except:
        await msg.channel.send(embed=fromdict({"title":"Not Blocked","description":f"{word} was not blocked","color":colours["warning"]}))
    else:
        await msg.channel.send(embed=fromdict({"title":"Success","description":f"{word} is allowed again","color":colours["success"]}))
Command("unblockword",unblockWord,1,"Remove a word from the filter list",{"word":True},None,"admin")

async def setNickFilterState(msg,args):
    gmt = getMegaTable(msg)
    gmt.FilterNicknames = not gmt.FilterNicknames
    await msg.channel.send(embed=fromdict({"title":"Toggled","description":gmt.FilterNicknames and "Any new nicknames will now be filtered" or "Nicknames will no longer be filtered","color":colours["success"]}))
Command("filternicknames",setNickFilterState,1,"Toggle whether or not nicknames should be subject to the word filter",{},None,"admin")

async def clearChannel(msg,args):
    if len(args) < 2:
        await msg.channel.send(embed=fromdict({"title":"Error","description":"You must include a channel name","color":colours["error"]}),delete_after=10)
        return
    channelName = numRegex.search(args[1]) and client.get_channel(int(numRegex.search(args[1]).group())).name or args[1] #We need name as ID wont work after clearing
    frequency = exists(args,2) and args[2]
    if frequency:
        success,result = strToTimeAdd(frequency)
        if not success:
            await msg.channel.send(embed=fromdict({"title":"Error","description":result,"color":colours["error"]}),delete_after=10)
            return
        if result < 300:
            await msg.channel.send(embed=fromdict({"title":"Too short","description":"The minimum frequency time is 5 minutes","color":colours["error"]}),delete_after=10)
            return
        getMegaTable(msg).AddChannelClear(channelName,result)
        await msg.channel.send(embed=fromdict({"title":"Success","description":f"{channelName} is queued to clear every {simplifySeconds(result)}","color":colours["success"]}))
    else:
        guildChannelList = msg.guild.text_channels
        for t in guildChannelList:
            if channelName == t.name:
                await cloneChannel(t.id,f"{msg.author} {msg.author.id}")
                return
        await msg.channel.send(embed=fromdict({"title":"Error","description":f"Couldnt find a channel with the name {channelName}","color":colours["error"]}),delete_after=10)
Command("clearchannel",clearChannel,0,"Add a channel to be cleared every so often OR clear now (no frequency)",{"channelName":True,"frequency":False},None,"admin")
async def unclearChannel(msg,args):
    if len(args) < 2:
        await msg.channel.send(embed=fromdict({"title":"Error","description":"You must include a channel name to stop clearing","color":colours["error"]}),delete_after=10)
        return
    channelName = numRegex.search(args[1]) and client.get_channel(int(numRegex.search(args[1]).group())).name or args[1] #We need name as ID wont work after clearing
    if getMegaTable(msg).RemoveChannelClear(channelName):
        await msg.channel.send(embed=fromdict({"title":"Success","description":channelName+" will no longer be cleared","color":colours["success"]}))
    else:
        await msg.channel.send(embed=fromdict({"title":"Error","description":channelName+" was not being cleared","color":colours["error"]}),delete_after=10)
Command("unclearchannel",unclearChannel,0,"Stop a channel from being auto-cleared",{"channelName":True},None,"admin")

async def blockMedia(msg,args):
    if len(args) < 2:
        await msg.channel.send(embed=fromdict({"title":"Error","description":"You must include the time until deletion","color":colours["error"]}),delete_after=10)
        return
    success,result = strToTimeAdd(args[1])
    if not success:
        await msg.channel.send(embed=fromdict({"title":"Error","description":result,"color":colours["error"]}),delete_after=10)
        return
    getMegaTable(msg).MediaFilters[msg.channel.id] = result
    await msg.channel.send(embed=fromdict({"title":"Success","description":"All media will be deleted after "+simplifySeconds(result),"color":colours["success"]}))
Command("blockmedia",blockMedia,0,"Remove all media in a channel after a certain duration",{"deletiontime":True},None,"admin")
async def unblockMedia(msg,args):
    try:
        getMegaTable(msg).MediaFilters.pop(msg.channel.id)
    except:
        await msg.channel.send(embed=fromdict({"title":"Not Filtered","description":"This channel was not filtered","color":colours["warning"]}))
    else:
        await msg.channel.send(embed=fromdict({"title":"Success","description":"Media will no longer be removed","color":colours["success"]}))
Command("unblockmedia",unblockMedia,0,"Stop auto-filtering a channel's media",{},None,"admin")

async def controlMessageLimit(msg,args,removing):
    gmt = getMegaTable(msg)
    channel = msg.channel
    if not removing:
        msgLimit = exists(args,1) and numRegex.search(args[1]) and int(numRegex.search(args[1]).group())
        if not msgLimit:
            await channel.send(embed=fromdict({"title":"No Limit Specified","description":"You must specify a max number of messages before deletion","color":colours["error"]}),delete_after=10)
            return
        if msgLimit <= 0:
            await channel.send(embed=fromdict({"title":"No","description":"1 or more, no less","color":colours["error"]}),delete_after=10)
        gmt.ChannelLimits[channel.id] = msgLimit
        await channel.send(embed=fromdict({"title":"Success","description":f"All messages after #{msgLimit} will be auto-deleted","color":colours["success"]}))
    else:
        if exists(gmt.ChannelLimits,channel.id):
            gmt.ChannelLimits.pop(channel.id)
        await channel.send(embed=fromdict({"title":"Success","description":"Any existing message limit has been removed","color":colours["success"]}))
Command("setmessagelimit",controlMessageLimit,5,"Sets a max message limit on a channel, deleting any over the limit",{"number":True},False,"admin")
Command("removemessagelimit",controlMessageLimit,5,"Removes the max message limit on a channel",{},True,"admin")

async def clearAllInvites(msg,args,silent=False):
    try:
        invites = await msg.guild.invites()
    except:
        if not silent:
            await msg.channel.send(embed=fromdict({"title":"Error","description":"Failed to get invites. Maybe try again, or check the bot's permissions","color":colours["error"]}),delete_after=10)
        return False,None
    successRate,totalCount = 0,0
    for invite in invites:
        try:
            await invite.delete()
            successRate += 1
        except:
            pass
        totalCount += 1
    if not silent:
        await msg.channel.send(embed=fromdict({"title":"Success","description":f"{successRate} out of {totalCount} invites were successfully cleared","color":colours["success"]}))
    return True,f"{str(successRate)}/{str(totalCount)}"
async def clearInvitesConfirm(msg,args):
    await getMegaTable(msg).CreateConfirmation(msg,args,clearAllInvites)
Command("clearinvites",clearInvitesConfirm,5,"Clears all invites in the server, deleting them",{},None,"mod")

async def panic(msg,args): #Unfinished!
    finalString = ""
    success,result = await clearAllInvites(msg,args,True)
    finalString += "Invite clear: "+(success and f"Sucessfully cleared {result} invites\n") or "Failed\n"
    await msg.channel.send(embed=fromdict({"title":"Panic results:","description":finalString,"color":colours["info"]}))
async def confirmPanic(msg,args):
    await getMegaTable(msg).CreateConfirmation(msg,args,panic)
Command("panic",confirmPanic,60,"Locks down the server, clearing invites and locking channels. Use this sparingly (UNFINISHED)",{},None,"dev")
