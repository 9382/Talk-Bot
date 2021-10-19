async def setLogChannel(msg,args):
    if not exists(args,1):
        await msg.channel.send(embed=fromdict({"title":"No channel","description":"Please provide a channel, either by mentioning it or by putting its ID","color":colours["error"]}))
        return
    wantedChannel = numRegex.search(args[1]) and client.get_channel(int(numRegex.search(args[1]).group()))
    if not wantedChannel or wantedChannel.guild.id != msg.guild.id:
        await msg.channel.send(embed=fromdict({"title":"Not found","description":"The channel provided either doesnt exist, or i cant access it","color":colours["error"]}))
        return
    getMegaTable(msg).LogChannel = wantedChannel.id
    await msg.channel.send(embed=fromdict({"title":"Success","description":"Set log channel successfully","color":colours["success"]}))
Command("setlogs",setLogChannel,3,"Set the log channel to the channel provided",{"channel":True},None,"admin")

list_validSections = ["WordBlockList","NSFWBlockList"]
async def list_func(msg,args):
    if len(args) < 2:
        finalString = ""
        for item in list_validSections:
            finalString += f"\n`{item}`"
        await msg.channel.send(embed=fromdict({'title':'Settings List','description':'To get a list of what you are looking for, please use one of the following sub-commands:'+finalString,'color':colours['info']}))
        return
    section = args[1]#msg.content[7:]
    if not section in list_validSections:
        await msg.channel.send(embed=fromdict({'title':'Invalid','description':section+' is not a valid catagory','color':colours["error"]}))
        return
    parser = None
    if section == "WordBlockList":
        parser = lambda i,k,v : f"{str(i)}. `{k}` -> {simplifySeconds(v)}"
    if section == "NSFWBlockList":
        parser = lambda i,v : f"{str(i)}. `{v}`"
    array = getattr(getMegaTable(1),section)
    finalString = []
    index = 1
    if type(array) == dict:
        for k in array:
            finalString.append(parser(index,k,array[k]))
            index += 1
    else:
        for v in array:
            finalString.append(parser(index,v))
            index += 1
    await createPagedEmbed(msg.author,msg.channel,"List of moderation content",finalString)
Command("list",list_func,0,"View the list of settings to do with the server's administration",{"subsection":False},None,"admin")

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
        await msg.channel.send(embed=fromdict({'title':'Not Blocked','description':f'{word} was not blocked','color':colours['warning']}))
    else:
        await msg.channel.send(embed=fromdict({'title':'Success','description':f'{word} is allowed again','color':colours['success']}))
Command("unblockword",unblockWord,0,"Remove a word from the filter list",{"word":True},None,"admin")

async def clearChannel(msg,args):
    if len(args) < 2:
        await msg.channel.send(embed=fromdict({'title':'Error','description':'You must include a channel name','color':colours['error']}),delete_after=10)
        return
    channelName = args[1] # Cant do ID cause deleting a channel removes the ID :)
    frequency = exists(args,2) and args[2]
    if frequency:
        success,result = strToTimeAdd(frequency)
        if not success:
            await msg.channel.send(embed=fromdict({'title':'Error','description':result,'color':colours['error']}),delete_after=10)
            return
        if result < 300:
            await msg.channel.send(embed=fromdict({'title':'Too short','description':'The minimum frequency time is 5 minutes','color':colours['error']}),delete_after=10)
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
        await msg.channel.send(embed=fromdict({'title':'Error','description':'You must include a channel name to stop clearing','color':colours['error']}),delete_after=10)
        return
    channelName = args[1]
    getMegaTable(msg).RemoveChannelClear(channelName)
    await msg.channel.send(embed=fromdict({'title':'Success','description':channelName+' will no longer be cleared','color':colours['success']}))
Command("unclearchannel",unclearChannel,0,"Stop a channel from being auto-cleared",{"channelName":True},None,"admin")

async def blockMedia(msg,args):
    if len(args) < 2:
        await msg.channel.send(embed=fromdict({'title':'Error','description':'You must include the time until deletion','color':colours['error']}),delete_after=10)
        return
    success,result = strToTimeAdd(args[1])
    if not success:
        await msg.channel.send(embed=fromdict({'title':'Error','description':result,'color':colours['error']}),delete_after=10)
        return
    getMegaTable(msg).MediaFilters[msg.channel.id] = result
    await msg.channel.send(embed=fromdict({'title':'Success','description':'All media will be deleted after '+simplifySeconds(result),'color':colours['success']}))
Command("blockmedia",blockMedia,0,"Remove all media in a channel after a certain duration",{"deletiontime":True},None,"admin")
async def unblockMedia(msg,args):
    try:
        getMegaTable(msg).MediaFilters.pop(msg.channel.id)
    except:
        await msg.channel.send(embed=fromdict({'title':'Not Filtered','description':'This channel was not filtered','color':colours['warning']}))
    else:
        await msg.channel.send(embed=fromdict({'title':'Success','description':'Media will no longer be removed','color':colours['success']}))
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
        gmt.ChannelLimits[channel.id] = [msgLimit,0]
        await channel.send(embed=fromdict({"title":"Success","description":f"All messages after #{str(msgLimit)} will be auto-deleted","color":colours["success"]}))
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
        if silent:
            return False,None
        else:
            await msg.channel.send(embed=fromdict({"title":"Error","description":"Failed to get invites. Maybe try again, or check the bot's permissions","color":colours["error"]}))
            return
    successRate,totalCount = 0,0
    for invite in invites:
        try:
            await invite.delete()
            successRate += 1
        except:
            pass
        totalCount += 1
    if silent:
        return True,f"{str(successRate)}/{str(totalCount)}"
    else:
        await msg.channel.send(embed=fromdict({"title":"Success","description":f"{str(successRate)} out of {str(totalCount)} invites were successfully cleared","color":colours["success"]}))
async def clearInvitesConfirm(msg,args):
    await getMegaTable(msg).CreateConfirmation(msg,args,clearAllInvites)
Command("clearinvites",clearInvitesConfirm,5,"Clears all invites in the server, deleting them",{},None,"admin")

async def panic(msg,args):
    # Panic here
    pass
async def confirmPanic(msg,args):
    await getMegaTable(msg).CreateConfirmation(msg,args,panic)
Command("panic",confirmPanic,60,"Locks down the server, clearing invites and locking channels. Use this sparingly",{},None,"dev")
