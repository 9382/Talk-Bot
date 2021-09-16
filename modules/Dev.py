# Pretty much every command under "dev" will be here

async def d_exec(msg,args):
    try:
        exec(msg.content[10:])
    except Exception as exc:
        print("[Dev] Nice custom exec, but it failed. Command:",msg.content[10:],"Exception:",exc)
    else:
        print("[Dev] Successful exec")
addCommand("d -exec",d_exec,0,"",{},None,"dev")

async def presetAudioTest(msg,args):
    if not msg.author.voice:
        return
    if not exists(args,1):
        args.insert(1,"sigma")
    file = "storage/temp/"+args[1]+".mp3"
    vc = await connectToVC(msg.author.voice.channel,idleTimeout=1,ignorePlaying=True) #Join
    if not vc:
        await msg.channel.send("Couldnt join the vc, probably cause i was busy")
        return
    vc.play(await discord.FFmpegOpusAudio.from_probe(file)) #Audio
addCommand("presetaudio",presetAudioTest,0,"",{},None,"dev")

def createScore(n1,n2):
    return 100-((n1+n2)%100)
async def scoreTest2(msg,args):
    targetUser1 = exists(args,1) and numRegex.search(args[1]) and msg.guild.get_member(int(numRegex.search(args[1]).group()))
    if not targetUser1:
        targetUser1 = random.choice(msg.guild.members)
    targetUser2 = exists(args,2) and numRegex.search(args[2]) and msg.guild.get_member(int(numRegex.search(args[2]).group()))
    if not targetUser2:
        targetUser2 = random.choice(msg.guild.members)
    await msg.channel.send(embed=fromdict({'title':'Score with '+targetUser1.name+' and '+targetUser2.name,'description':str(createScore(targetUser1.id,targetUser2.id))}))
addCommand("compare",scoreTest2,0,"",{},None,"dev")

async def circularMask(im):
    size = (im.size[0]*3,im.size[1]*3)
    mask = Image.new("L",size)
    d = ImageDraw.Draw(mask)
    d.ellipse((0,0)+size,fill=255)
    mask = mask.resize(im.size,Image.ANTIALIAS)
    im.putalpha(mask)
async def imageComp(msg,args):
    targetUser = random.choice(msg.guild.members)
    background = Image.open('storage/assets/imageTest.png') #Image.new("RGBA",size,0) for plain backgronds
    imageFile = Image.open(io.BytesIO(requests.get(targetUser.avatar_url_as(static_format="png",size=256)).content)) #What a mess
    await circularMask(imageFile)
    background.paste(imageFile,(8,8)) #Used to be for red box, now just obscure placement
    d = ImageDraw.Draw(background)
    d.text((137,269),targetUser.name,fill="black",anchor="mt",font=ImageFont.truetype('calibri.ttf',35))
    fileName = 'image_output_'+str(time.time())+".png"
    background.save(fileName)
    await msg.channel.send(targetUser.name+' in a box',file=discord.File(fileName))
    os.remove(fileName)
addCommand("imaget",imageComp,0,"",{},None,"dev")

async def printThis(msg,args):
    print(msg.content)
addCommand("ddd",printThis,0,"",{},None,"dev")
async def gimmePing(msg,args):
    startTime = time.time()
    message = await msg.channel.send("<???> ms")
    await message.edit(content=str(round((time.time()-startTime)*1000))+" ms")
addCommand("ping",gimmePing,0,"",{},None,"dev")

# This is only in here as the feature is most likely not going to exist anymore, its more a relic of a past plan
ttsQueue = []
handlingTTS = False
async def speakTTS(msg,args): # This is a bit of a mess. Maybe an improve, how about that?
    global ttsQueue
    global handlingTTS
    if not msg.author.voice:
        await msg.channel.send(embed=fromdict({'title':'No VC','description':'You must be in a voice channel when using this command','color':colours['error']}),delete_after=10)
        return
    if len(ttsQueue) >= 3:
        await msg.channel.send(embed=fromdict({"title":"Queue Full","description":"The TTS Queue is currently full, wait for the current one to finish first","color":colours['error']}),delete_after=10)
        return
    if len(msg.content)-6 > 130:
        await msg.channel.send(embed=fromdict({"title":"Too Long","description":"TTS is capped at 130 characters. Your message is "+str(len(msg.content)-6),"color":colours["error"]}),delete_after=10)
        return
    if len(msg.content)-6 < 1:
        await msg.channel.send(embed=fromdict({"title":"No Content","description":"You need to provide something to speak","color":colours["error"]}),delete_after=10)
        return
    ttsQueue.append({"m":msg.content[6:],"c":msg.author.voice.channel})
    ### NOTE: Rewrite this into a @tasks.loop() loop, to avoid illogical handling as shown below :)
    if not handlingTTS:
        handlingTTS = True
        while len(ttsQueue) > 0:
            dialouge = ttsQueue[0]
            vc = await connectToVC(dialouge["c"])
            if not vc:
                await asyncio.sleep(1)
                continue
            ttsQueue.pop(0)
            ttsObject = pyttsx3.init()
            fileName = tempFile("mp3")
            ttsObject.setProperty("voice",ttsObject.getProperty('voices')[0].id)
            ttsObject.setProperty('rate',160)
            ttsObject.save_to_file(dialouge["m"],fileName)
            ttsObject.runAndWait()
            while True: #Keeps thinking its not connected even though it is. Logic
                try:
                    vc.play(await discord.FFmpegOpusAudio.from_probe(fileName)) #Audio
                except:
                    pass
                else:
                    break
            while vc.is_playing():
                await asyncio.sleep(0.5)
            try:
                os.remove(fileName)
            except:
                pass
        handlingTTS = False
addCommand("tts",speakTTS,3,"Speak whatever you put into your vc as Text-To-Speech",{"text":True},None,"dev")