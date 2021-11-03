#Seperate script to improve ##cmds ordering and for convenience
TestCommandList = []
def AddCommand(a,b,c,d,e,f):
    cmdObject = Command(a,b,c,d,e,f,"dev")
    if a != "d -test onerror":
        TestCommandList.append(cmdObject)

async def horribleCoding(msg,args):
    [] # This is just designed to error
AddCommand("d -test error",horribleCoding,0,"Forces an error to test the error logging",{},None)
async def forceOnReady(msg,args):
    await on_ready()
AddCommand("d -test onready",forceOnReady,0,"Runs the on_ready function",{},None)
async def testConfirmations2(msg,args):
    await msg.channel.send("Got past confirmation")
async def testConfirmations(msg,args):
    print("Testing confirmations")
    await getMegaTable(msg).CreateConfirmation(msg,args,testConfirmations2)
AddCommand("d -test confirmations",testConfirmations,0,"Tests the Confirmations feature",{},None)
async def testReactionListener2(msg,emoji,score):
    score += 1
    await msg.edit(content=f"This message + {str(score)}")
    await UpdateReactionWatch(msg,"all",score)
async def testReactionListener(msg,args):
    message = await msg.channel.send("This message + 0")
    await message.add_reaction("⬅️")
    WatchReaction(message,msg.author,"⬅",testReactionListener2,0)
AddCommand("d -test reactions",testReactionListener,0,"Tests the Reaction Listener",{},None)
async def testPagedEmbed(msg,args): #user, channel, title, content, pagelimit
    await createPagedEmbed(msg.author,msg.channel,msg.author.name,["A","B","C","D","E","F","G","H","I","J"],4)
AddCommand("d -test pagedembed",testPagedEmbed,0,"Runs the createPagedEmbed function",{},None)

async def testAll(msg,args):
    score = [0,0]
    print("Test-All called")
    for command in TestCommandList:
        try: #If it errors, testAll cancels, so this method will be done
            if await command.Run(msg,args,True): #If successful:
                score[1] += 1
                print("Successful run of",command.Name)
            else:
                print("Failed run of",command.Name)
        except Exception as exc:
            print("Critical fail run of",command.Name,":",exc)
        score[0] += 1
    await msg.channel.send(f"All tests finished: Final score {str(score[1])} out of {str(score[0])}")
    print("Test-All final score",score)
Command("d -test all",testAll,0,"Runs all 'd -test' commands and returns the success score",{},None,"dev")
AddCommand = None

#Custom classes to match the discord handler
#These are just for testing offline or without actual messages
class FakeGuildPermissions:
    def __init__(self,admin):
        self.administrator = admin
class FakeChannel:
    def __init__(self,guild):
        self.id = random.randint(1,9)
        self.guild = guild
    async def send(self,content=None,embed=None,delete_after=None):
        print("Attempted to channel send\n",content,embed,delete_after)
        if embed:
            print("Embed title:",embed.title,"\nEmbed description:",embed.description)
        return FakeMessage(content,embed,self.guild.id)
    async def delete_messages(self,messages):
        print("Requested to BD",messages)
class FakeAuthor:
    def __init__(self,guild,id,admin):
        self.id = id or random.randint(10,99)
        self.guild = guild
        self.name = "Author"
        self.discriminator = "1234"
        self.guild_permissions = FakeGuildPermissions(admin)
class FakeGuild:
    def __init__(self,gid):
        self.id = gid
class FakeMessage:
    def __init__(self,content=None,embed=None,gid=None,uid=None):
        gid = gid or random.randint(100,999)
        self.id = random.randint(1000,9999)
        self.content = content
        self.guild = FakeGuild(gid)
        self.author = FakeAuthor(self.guild,uid,True)
        self.channel = FakeChannel(self.guild)
        self.embeds = (embed and [embed]) or []
    async def delete(self):
        print("Tried to delete message",self.id,self.content)

async def AdvancedTest(msg,args):
    print("Trying advanced test")
    fm = FakeMessage
    await on_message(fm("##blockword testing 1s",gid=-1)) #Should work - user is admin
    await on_message(fm("##list WordBlockList",gid=-1)) #Should work
    await on_message(fm("##d -exec crash()")) #Shouldnt work - user is not dev
    await on_message(fm("Talking and testing",gid=-1)) #Should be filtered
    await asyncio.sleep(1)
    await constantMessageCheck() #Should try delete
    print(getMegaTable(-1).ProtectedMessages) #Should have 1 item
Command("d -test advanced",AdvancedTest,10,"Runs a \"Simulated\" experience of the bot, using FakeMessage",{},None,"dev")