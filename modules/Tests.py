#Seperate script to improve ##cmds ordering and for convenience
TestCommandList = []
def AddCommand(a,b,c,d,e,f):
    TestCommandList.append(Command(a,b,c,d,e,f,"dev"))

async def forceOnError(msg,args):
    try:
        _[_] #Cause safe error
    except:
        await on_error("on_message",msg) #Cause on_error response
AddCommand("d -test onerror",forceOnError,0,"Forces an error to test the error logging",{},None)
async def forceOnReady(msg,args):
    await on_ready()
AddCommand("d -test onready",forceOnReady,0,"Runs the on_ready function",{},None)
async def testConfirmations2(msg,args):
    await msg.channel.send("Got past confirmation, adding a wait")
    await asyncio.sleep(3)
    await msg.channel.send("Confirmation over")
async def testConfirmations(msg,args):
    await getMegaTable(msg).CreateConfirmation(msg,args,testConfirmations2)
AddCommand("d -test confirmations",testConfirmations,0,"Tests the Confirmations feature",{},None)
async def testReactionListener2(msg,emoji,score):
    score += 1
    await msg.edit(content=f"This message + {score}")
    await UpdateReactionWatch(msg,"all",score)
async def testReactionListener(msg,args):
    message = await msg.channel.send("This message + 0")
    await message.add_reaction("⬅️")
    WatchReaction(message,msg.author,"⬅️",testReactionListener2,0)
AddCommand("d -test reactions",testReactionListener,0,"Tests the Reaction Listener",{},None)
async def testPagedEmbed(msg,args): #user, channel, title, content, pagelimit
    await createPagedEmbed(msg.author,msg.channel,msg.author.name,["A","B","C","D","E","F","G","H","I","J"],4)
AddCommand("d -test pagedembed",testPagedEmbed,0,"Runs the createPagedEmbed function",{},None)
async def testContentLimit(msg,args):
    await msg.channel.send(truncateText("a"*3200))
AddCommand("d -test truncate",testContentLimit,0,"Tests the truncateText feature",{},None)

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
            print(f"Critical fail run of {command.Name}: {exc}")
        score[0] += 1
    await msg.channel.send(f"All tests finished: Final score {score[1]} out of {score[0]}")
    print("Test-All final score",score)
Command("d -test all",testAll,0,"Runs all 'd -test' commands and returns the success score",{},None,"dev")
AddCommand = None
