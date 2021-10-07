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
