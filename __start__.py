from dotenv import dotenv_values
from sys import platform
from time import sleep
import asyncio
import os
auth = dotenv_values()['BOTAUTH']
print("Starting...",os.getcwd())
try:
    from main import client,log
except Exception as exc:
    print("[!] Import error for client:",exc)
    def log(content):
        print("[__start__ no-log]",content)
    sleep(3)
else:
    _log = log
    def log(content):
        _log("[__start__] "+content)
    log("main imported successfully - running...")
    try:
        client.run(auth)
    except Exception as exc:
        log("[!] client.run exited: "+str(exc))
log("Checking for updates for client...")
for i in os.listdir('update'): #What a mess
    log("[Updater] "+i)
    if i == "__start__.py":
        log("Please update __start__ manually instead of through auto-update. Trust me, you dont want that headache")
        continue
    trueName = i.replace("^","/")
    if trueName != i:
        log("Sub-folder detected: "+str(i.split("^")))
    newFile = open('update/'+i,newline='').read()
    backup = None
    if os.path.isfile(i):
        backup = open(trueName,newline='').read()
    else:
        log("No backup can be made for "+trueName)
    oldFile = open(trueName,"w",newline='')
    try:
        oldFile.write(newFile)
        log("Successfully written update for "+trueName)
    except Exception as exc:
        if backup:
            try:
                oldFile.write(backup)
            except:
                log(f"[!] Update for {trueName} failed (Backup failed): "+str(exc))
            else:
                log(f"[!] Update for {trueName} failed (Backup written): "+str(exc))
        else:
            log(f"[!] Update for {trueName} failed (No backup): "+str(exc))
    else:
        os.remove('update/'+i)
    oldFile.close()
log("Rebooting...")
if platform.startswith("win"): #win32/win64
    os.system('start __start__.py')
else: #Assume linux - use sh
    os.system('./start.sh')
