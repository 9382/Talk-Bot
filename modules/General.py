async def helpcommand(msg,args):
    await msg.channel.send(embed=fromdict({"title":"Talk-Bot","description":f"""

"""}))
# Command("help",helpcommand,1,"Gives assistance")
async def cmds(msg,args):
    cmdList = {"Admin":adminCommands,"Moderator":modCommands}
    for command,cmdInfo in userCommands.items():
        if not exists(cmdList,cmdInfo.Group):
            cmdList[cmdInfo.Group] = {}
        cmdList[cmdInfo.Group][command] = cmdInfo
    if exists(args,1): #Group Specific
        group = None
        for catagory in cmdList:
            if args[1].lower() == catagory.lower():
                group = cmdList[catagory]
        if msg.author.id == DevID and args[1].lower() == "dev":
            group = devCommands
        if not group:
            await msg.channel.send(embed=fromdict({"title":"Invalid group","description":f"The group '{args[1]}' doesnt exist","color":colours["error"]}))
            return
        finalText = []
        for command,cmdInfo in group.items():
            argMessageContent = ""
            for argName,argRequired in cmdInfo.DescArgs.items():
                argMessageContent += (argRequired and f" <{argName}>") or f" [{argName}]"
            finalText.append(f"`{command}{argMessageContent}` - {cmdInfo.Description}")
        await createPagedEmbed(msg.author,msg.channel,"Commands within "+args[1].lower(),finalText,10,"**Syntax**\n`<>` is a required argument, `[]` is an optional argument\n\n**Commands**\n")
    else: # Generalised (No group)
        finalText = f"do `{args[0]} <group>` to get more information on a group"
        for group,commands in cmdList.items():
            finalText += f"\n**{group}**\n"
            for command in commands:
                finalText += f"`{command}` "
        await msg.channel.send(embed=fromdict({"title":"Commands","description":finalText,"color":colours["info"]}))
Command(["commands","cmds"],cmds,1,"List all commands",{"group":False},None,"General")
async def getPing(msg,args):
    startTime = time.time()
    message = await msg.channel.send("<???> ms")
    await message.edit(content=str(round((time.time()-startTime)*1000))+" ms")
Command("ping",getPing,0,"Check the bot's ping",{},None,"General")
async def guideSetup(msg,args):
    pass
Command("setup",guideSetup,1,"Not made yet",{},None,"dev")
async def publicVote(msg,args):
    if len(args) < 2:
        await msg.channel.send(embed=fromdict({"title":"Error","description":"You have to include the thing to vote on","color":colours["error"]}),delete_after=10)
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
    voteMsg = await msg.channel.send(embed=fromdict({"author":{"name":f"{author} is calling a vote","icon_url":author.display_avatar.url},"description":" ".join(args),"image":{"url":imageUrl},"color":colours["info"]}))
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