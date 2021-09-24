# The deathbattle module and command
import random
class dbAttack:
    def __init__(self,hitMsg,dmgMin,dmgMax):
        self.hitMsg = hitMsg
        self.dmgMin = dmgMin
        self.dmgMax = dmgMax
    def __str__(self):
        return self.hitMsg
    def format(self,attacker,victim,damage):
        return self.hitMsg.format(attacker="__**"+str(attacker)+"**__",victim="__**"+str(victim)+"**__",damage="__**"+str(damage)+" dmg**__")
    def hit(self):
        return random.randint(self.dmgMin,self.dmgMax)
class user:
    def __init__(self,name,UID,health=100):
        self.name = name
        self.UID = UID
        self.health = health
        self.maxhealth = health
        self.alive = True
    def __str__(self):
        return self.name
    def damage(self,amount):
        self.health = min(self.maxhealth,max(self.health-amount,0))
        self.alive = self.health > 0
class dbLog:
    def __init__(self,u1,u2,hitMsg):
        #self.u1 = u1
        self.u1hp = str(u1.health)+"hp"
        #self.u2 = u2
        self.u2hp = str(u2.health)+"hp"
        #self.attacker = attacker
        #self.victim = (attacker == u1 and u2) or u1
        self.hitMsg = hitMsg
    def __str__(self):
        return self.hitMsg
dbattleAttacks = []
def addAttack(hitMsg,min,max):
    dbattleAttacks.append(dbAttack(hitMsg,min,max))
addAttack("stock attack: {attacker} hit {victim} for {damage}",5,7)
def calculate(u1,u2):
    attacker = random.choice([u1,u2])
    victim = (attacker == u1 and u2) or u1
    log = []
    while u1.alive and u2.alive:
        attack = random.choice(dbattleAttacks)
        damage = attack.hit()
        victim.damage(damage)
        log.append(dbLog(u1,u2,attack.format(attacker,victim,damage)))
        attacker,victim = (attacker == u1 and (u2,u1)) or (u1,u2)
    return {'u1':u1,'u2':u2,'winner':(u1.alive and u1) or u2,'log':log}
async def deathBattle(msg,args):
    u2 = exists(args,1) and numRegex.search(args[1]) and msg.guild.get_member(int(numRegex.search(args[1]).group()))
    if not u2:
        u2 = random.choice(msg.guild.members)
    u1 = msg.author
    dbResults = db.calculate(db.user(u1.name,u1.id),db.user(u2.name,u2.id))
    dbMessage = await msg.channel.send(':anger: Death Battle!',embed=fromdict(
        {'author':{'name':u1.name+' is challenging '+u2.name},'fields':[{'name':u1.name,'value':'100','inline':True},{'name':u2.name,'value':'100','inline':True}],'color':colours['info']}
    ))
    previousAttacks = [None]*2
    await asyncio.sleep(2)
    for i in dbResults['log']:
        description = ""
        for h in previousAttacks:
            if h:
                description += h+"\n"
        description += i.hitMsg
        await dbMessage.edit(content=':anger: Death Battle!',embed=fromdict(
            {'author':{'name':u1.name+' is challenging '+u2.name},'description':description,'fields':[{'name':u1.name,'value':i.u1hp,'inline':True},{'name':u2.name,'value':i.u2hp,'inline':True}],'color':colours['info']}
        ))
        previousAttacks.pop(0)
        previousAttacks.append(i.hitMsg)
        await asyncio.sleep(1.6)
    description = ""
    for h in previousAttacks:
        if h:
            description += h+"\n"
    description += "__**"+dbResults['winner'].name+"**__ won the fight!"
    await dbMessage.edit(content=':anger: Death Battle!',embed=fromdict(
        {'author':{'name':u1.name+' is challenging '+u2.name},'description':description,'fields':[{'name':u1.name,'value':i.u1hp,'inline':True},{'name':u2.name,'value':i.u2hp,'inline':True}],'color':colours['info']}
    ))
Command("deathbattle",deathBattle,10,"Fight someone to the death!",{"@user":False},None,"dev")