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
addAttack("{attacker} stabs {victim} for {damage}",14,16)
addAttack("{attacker} blows up {victim} for {damage}",23,25)
addAttack("{attacker} beats {victim} in a bet for {damage}",9,11)
addAttack("{attacker} smacks {victim} with a guitar for {damage}",13,15)
addAttack("{attacker} strangles {victim} for {damage}",18,20)
addAttack("{attacker} smacks {victim} for {damage}",5,7)
addAttack("{attacker} kicks {victim} for {damage}",3,5)
addAttack("{attacker} uses the n word on {victim} for {damage}",20,22)
addAttack("{attacker} is super effective on {victim} for {damage}",25,27)
addAttack("{attacker} burns {victim} for {damage}",17,19)
addAttack("{attacker} cancels {victim} on twitter for no damage",0,0)
addAttack("{attacker} drinks {victim}'s gender fluid for {damage}",12,14)
addAttack("{attacker} makes {victim} cringe for {damage}",21,23)
addAttack("{attacker} draws furry porn of {victim} for {damage}",17,19)
addAttack("{attacker} IRA's {victim}'s car for {damage}",23,25)
addAttack("{attacker} watches {victim} have ptsd for {damage}",8,10)
addAttack("{attacker} watches {victim} become trans for {damage}",24,26)
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