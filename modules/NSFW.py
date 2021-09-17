# Anything with NSFW gets chucked here

async def blockNSFWTag(msg,args):
    if len(args) < 2:
        await msg.channel.send(embed=fromdict({'title':'Error','description':'You must include a tag to block','color':colours['error']}),delete_after=30)
        return
    word = msg.content[11:].lower()
    getMegaTable(msg).NSFWBlockList.append(word)
    await msg.channel.send(embed=fromdict({'title':'Success','description':'Any posts containing \''+word+'\' will not be sent','color':colours['success']}))
addCommand("blocktag",blockNSFWTag,0,"Block certain tags from showing in NSFW commands",{"tag":True},None,"admin")
async def unblockNSFWTag(msg,args):
    if len(args) < 2:
        await msg.channel.send(embed=fromdict({'title':'Error','description':'You must include a tag to unblock','color':colours['error']}),delete_after=30)
        return
    word = msg.content[13:].lower()
    try:
        getMegaTable(msg).NSFWBlockList.remove(word)
    except:
        pass
    await msg.channel.send(embed=fromdict({'title':'Success','description':'Any posts containing \''+word+'\' will no longer be blocked','color':colours['success']}))
addCommand("unblocktag",unblockNSFWTag,0,"Allow certain tags to be in NSFW commands again",{"tag":True},None,"admin")

async def filterTagList(msg,tagList): #Why did i do this into a function again? idk
    for i in getMegaTable(msg).NSFWBlockList:
        if i in tagList.lower():
            return True #True means filtered
async def getPostList(msg,sitetype,tags): ##APIs be like
    returnContent = []
    anyMessageFiltered = False
    index = 0
    if sitetype == "rule34" or sitetype == "realbooru": #Literal identical format, must be by the same guys ig
        site = (sitetype == "rule34" and "rule34.xxx") or "realbooru.com"
        postList = requests.get(f'https://{site}/index.php?page=dapi&s=post&q=index&limit=100&tags='+tags).text
        postList = regex.sub('\nfemale','female',postList)
        postList = regex.sub('\nboots','boots',postList)
        postList = regex.sub('\n[ a-z]','▓',postList)
        getPostIDRegex = regex.compile(' id="\d+"')
        getImageURLRegex = (sitetype == "rule34" and regex.compile(' file_url="https://api-cdn(-\w*)*\.rule34\.xxx/images/\d+/[\w\d]+\.(\w)+')) or regex.compile(' file_url="https://realbooru\.com/images/\d+/[\w\d]+\.(\w)+')
        getPostTagsRegex = regex.compile(' tags="[^"]*"')
        for i in postList.split('\n'):
            if i.find('<post ') > -1: #If false, ive hit end (<posts>)
                postInfo = {}
                postID = numRegex.search(getPostIDRegex.search(i).group()).group()
                postInfo["postPage"] = f"https://{site}/index.php?page=post&s=view&id="+postID
                if getImageURLRegex.search(i):
                    fileURL = getImageURLRegex.search(i).group()[11:]
                else:
                    continue #Invalid post :)
                postInfo["fileURL"] = fileURL
                postInfo["fileType"] = ((fileURL.find('.mp4') > 0 or fileURL.find('.webm') > 0) and "Video") or "Image" #Yes
                tags = getPostTagsRegex.search(i).group()
                postInfo["tags"] = tags[8:-2]
                if not await filterTagList(msg,tags):
                    returnContent.append(postInfo)
                else:
                    anyMessageFiltered = True
    elif sitetype == "e621":
        postList = requests.get('https://e621.net/posts.json?limit=200&tags='+tags,headers={'User-Agent':'TalkBot/1.2'}).text
        loaded = json.loads(postList)["posts"]
        for i in loaded:
            postInfo = {}
            postInfo["postPage"] = "https://e621.net/posts/"+str(i["id"])
            postInfo["fileURL"] = i["file"]["url"]
            if not i["file"]["url"]:
                continue #This is caused by an image blocked due to account requirements
            postInfo["fileType"] = ((i["file"]["url"].find('.mp4') > 0 or i["file"]["url"].find('.webm') > 0) and "Video") or "Image"
            tags = ""
            for a in i["tags"]:
                for b in i["tags"][a]:
                    tags = tags+b+" "
            postInfo["tags"] = tags[:-1]
            if not await filterTagList(msg,tags):
                returnContent.append(postInfo)
            else:
                anyMessageFiltered = True
    elif sitetype == "danbooru": #Simplest one yet (mostly)
        postList = requests.get('https://danbooru.donmai.us/posts.json?limit=100&tags='+tags).text
        loaded = json.loads(postList)
        for i in loaded:
            if not exists(i,"id"):
                continue #Somehow posts without an ID can appear?? probs requirements
            postInfo = {}
            postInfo["postPage"] = "https://danbooru.donmai.us/posts/"+str(i["id"])
            postInfo["fileURL"] = i["file_url"]
            postInfo["fileType"] = ((i["file_url"].find('.mp4') > 0 or i["file_url"].find('.webm') > 0) and "Video") or "Image"
            postInfo["tags"] = i["tag_string"]
            if not await filterTagList(msg,i["tag_string"]):
                returnContent.append(postInfo)
            else:
                anyMessageFiltered = True
    if len(returnContent) == 0:
        if anyMessageFiltered:
            await msg.channel.send(embed=fromdict({'title':'Post Blocked','description':'The recieved post contained one or more blocked tags. Try again with a different search term if needed','color':colours['error']})) #No
        else:
            await msg.channel.send(embed=fromdict({'title':'No Posts','description':'No posts were found under your requested tags','color':colours['error']}))
        return
    return returnContent
async def nsfwScrape(msg,args,sitetype): #I spent hours on this and idk if i should be happy about it
    if not msg.channel.is_nsfw():
        await msg.channel.send(embed=fromdict({'title':'Disallowed','description':'You can only use NSFW commands in channels marked as NSFW','color':colours['error']}),delete_after=10)
        return
    try: #Unstable script due to all the HTTP responses
        args.remove(args[0]) #Remove calling command, dont want that as a tag
        tags = ""
        for i in args:
            tags = tags+i+"+" #A trailing + is fine
        postList = None
        try:
            postList = await getPostList(msg,sitetype,tags)
        except Exception as exc:
            print("[NSFW] "+sitetype+" GetPosts Exception:",exc)
            await msg.channel.send(embed=fromdict({'title':'Unexpected Error','description':'Something unexpected went wrong, hopefully it wont happen again.\n\nError: '+str(exc),'color':colours['error']}))
            return
        if postList:
            chosenPost = random.choice(postList)
            await msg.channel.send(embed=fromdict({'title':f"{msg.author.name}'s {sitetype} search (Click here to go to the post)",'url':chosenPost["postPage"],'image':{'url':chosenPost["fileURL"]},'description':'**Tags**: '+regex.sub('_','\\_',chosenPost["tags"]),'color':colours['info']}))
            if chosenPost["fileType"] == "Video":
                await msg.channel.send(chosenPost["fileURL"])
    except Exception as exc:
        print("[NSFW] "+sitetype+" Exception:",exc)
        await msg.channel.send(embed=fromdict({'title':'Unexpected Error','description':'Something unexpected went wrong, hopefully it wont happen again.\n\nError: '+str(exc),'color':colours['error']}))
addCommand("r34",nsfwScrape,3,"Get an NSFW post on rule34 with optional tags",{"tags":False},"rule34","NSFW")
#addCommand("e621",nsfwScrape,3,"Get an NSFW post on e621 with optional tags",{"tags":False},"e621","NSFW")
addCommand("hentai",nsfwScrape,3,"Get an NSFW post on danbooru with optional tags",{"tags":False},"danbooru","NSFW")
addCommand("irl",nsfwScrape,3,"Get an NSFW post on realbooru with optional tags",{"tags":False},"realbooru","NSFW")