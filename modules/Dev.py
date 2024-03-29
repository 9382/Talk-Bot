# Pretty much every command under "dev" will be here

async def d_exec(msg,args):
    mstart = 8 + len(prefix)
    try:
        exec(msg.content[mstart:],globals())
    except Exception as exc:
        print("[Dev] Nice custom exec, but it failed. Command:",msg.content[mstart:],"Exception:",exc)
        await msg.channel.send(":-1:")
    else:
        print("[Dev] Successful exec")
        await msg.channel.send(":+1:")
Command("d -exec",d_exec,0,"Executes pure python code in the global spec",{"code":True},None,"dev")
async def d_execa(msg,args):
    try:
        await globals()[args[2]]()
    except Exception as exc:
        print("[Dev] Nice custom async exec, but it failed. Command:",args[2],"Exception:",exc)
        await msg.channel.send(":-1: "+str(exc))
    else:
        print("[Dev] Successful async exec")
        await msg.channel.send(":+1:")
Command("d -execa",d_execa,0,"Executes the given function from globals asynchronously",{"function":True},None,"dev")

async def togglePerformanceCheck(msg,args):
    global performanceCheck
    performanceCheck = not performanceCheck
    await msg.channel.send(f"Performance check state set to {performanceCheck}")
Command("measure performance",togglePerformanceCheck,3,"Toggles the perfomance check of commands",{},None,"dev")

async def sendLogFile(msg,args):
    try:
        await msg.channel.send("Successfully sent file",file=discord.File("storage/logs/"+str(args[1])+".log"))
    except:
        await msg.channel.send("No such log file "+str(exists(args,1) and args[1]))
Command("sendlog",sendLogFile,0,"Sends the log file specified if it exists",{"log":True},None,"dev")

async def currentDateAsync(msg,args):
    await msg.channel.send(currentDate())
Command("cdate",currentDateAsync,0,"Sends the current date and time as a message",{},None,"dev")
async def whatIsUpTime(msg,args):
    currentUpTime = "Uptime: "+simplifySeconds(time.time()//1-uptime)
    log(currentUpTime)
    await msg.channel.send(currentUpTime)
Command("uptime",whatIsUpTime,0,"Sends and logs the bot's uptime since the last on_ready",{},None,"dev")

list_validSections = ["WordBlockList","NSFWBlockList","MediaFilters","ProtectedMessages","ChannelClearList","QueuedChannels","ChannelLimits","InviteTrack"]
async def oldModList(msg,args):
    if len(args) < 2:
        finalString = ""
        for item in list_validSections:
            finalString += f"\n`{item}`"
        await msg.channel.send(embed=fromdict({"title":"Settings List","description":"To get a list of what you are looking for, please use one of the following sub-commands:"+finalString,"color":colours["info"]}))
        return
    section = args[1]
    if not section in list_validSections:
        await msg.channel.send(embed=fromdict({"title":"Invalid","description":section+" is not a valid catagory","color":colours["error"]}),delete_after=10)
        return
    parser = None
    if section in ["WordBlockList","MediaFilters","ChannelClearList","QueuedChannels","ProtectedMessages"]:
        parser = lambda i,k,v : f"{i}. `{k}` -> {simplifySeconds(v)}"
    elif section in ["NSFWBlockList"]:
        parser = lambda i,v : f"{i}. `{v}`"
    elif section in ["ChannelLimits"]:
        parser = lambda i,k,v : f"{i}. `{k}` -> {v} Messages"
    elif section in ["InviteTrack"]:
        parser = lambda i,k,v : f"{i}. `{k}` -> {v}"
    array = getattr(getMegaTable(msg),section)
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
    if finalString == []:
        await msg.channel.send(embed=fromdict({"title":"No Content","description":"Nothing under this catagory","color":colours["warning"]}),delete_after=15)
    else:
        #Below message lasts 180 seconds, due to what it may contain. Im noting it here because this is a nightmare to read (NOTE: fixup somehow)
        getMegaTable(msg).ProtectMessage((await createPagedEmbed(msg.author,msg.channel,"List of moderation content",finalString,8,(section=="QueuedChannels" and "(Time until the next cycle)") or "",180)),180)
Command("list",oldModList,0,"View the raw list of settings to do with the server's administration",{"subsection":False},None,"dev")

async def presetAudioTest(msg,args):
    if not msg.author.voice:
        return
    if not exists(args,1):
        args.insert(1,"sigma")
    file = f"storage/temp/{args[1]}.mp3"
    vc = await connectToVC(msg.author.voice.channel,1,True) #Join
    if not vc:
        await msg.channel.send("Couldnt join the vc, probably cause i was busy")
        return
    #-vol XYZ
    #-af
    # aecho=0.8:0.88:6:0.4
    # aemphasis=level_in=1:level_out=1:mode=reproduction:type=col
    # aeval=val(0)|-val(1)
    # afftfilt=\"'real=re * (1-clip((b/nb)*b,0,1))':imag='im * (1-clip((b/nb)*b,0,1))'\"
    vc.play(await discord.FFmpegOpusAudio.from_probe(file)) #Audio
Command("presetaudio",presetAudioTest,0,"Test playing preset audio files",{"file":False},None,"dev")

#Consider removing the below code, the relevant feature is no longer expected to be made
def createScore(n1,n2):
    return 100-((n1+n2)%100)
async def scoreTest2(msg,args):
    targetUser1 = (exists(args,1) and numRegex.search(args[1]) and msg.guild.get_member(int(numRegex.search(args[1]).group()))) or random.choice(msg.guild.members) #long
    targetUser2 = (exists(args,2) and numRegex.search(args[2]) and msg.guild.get_member(int(numRegex.search(args[2]).group()))) or random.choice(msg.guild.members)
    await msg.channel.send(embed=fromdict({"title":f"Score with {targetUser1.name} and {targetUser2.name}","description":str(createScore(targetUser1.id,targetUser2.id)),"color":colours["info"]}))
Command("compare",scoreTest2,0,"Test the scoring system on user IDs",{"u1":False,"u2":False},None,"dev")

#Consider removing the below code, it serves little purpose, even as a POC
async def circularMask(im):
    size = (im.size[0]*3,im.size[1]*3)
    mask = Image.new("L",size)
    d = ImageDraw.Draw(mask)
    d.ellipse((0,0)+size,fill=255)
    mask = mask.resize(im.size,Image.ANTIALIAS)
    im.putalpha(mask)
async def imageComp(msg,args): #Just a POC, not used meaningfully
    from PIL import Image,ImageDraw,ImageFont,ImageChops
    import io
    targetUser = random.choice(msg.guild.members)
    background = Image.open("storage/assets/imageTest.png") #Image.new("RGBA",size,0) for plain backgronds
    imageFile = Image.open(io.BytesIO(requests.get(targetUser.avatar_url_as(static_format="png",size=256)).content)) #What a mess
    await circularMask(imageFile)
    background.paste(imageFile,(8,8)) #Used to be for red box, now just obscure placement
    d = ImageDraw.Draw(background)
    d.text((137,269),targetUser.name,fill="black",anchor="mt",font=ImageFont.truetype("calibri.ttf",35))
    fileName = f"image_output_{str(time.time())}.png"
    background.save(fileName)
    await msg.channel.send(targetUser.name+" in a box",file=discord.File(fileName))
    os.remove(fileName)
Command("imaget",imageComp,0,"An experiment with image editing",{"user":False},None,"dev")
