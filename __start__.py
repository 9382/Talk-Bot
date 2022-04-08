from dotenv import dotenv_values
from sys import platform
from time import sleep
import asyncio
import os
auth = dotenv_values()["BOTAUTH"]
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
        log(f"[!] client.run exited: {exc}")
log("Checking for updates for client...")
for i in os.listdir("update"): #What a mess
    log("[Updater] "+i)
    if i == "__start__.py":
        log("Please update __start__ manually instead of through auto-update")
        continue
    trueName = i.replace("^","/")
    if trueName != i:
        log(f"Sub-folder detected: {i.split('^')}")
        os.makedirs("/".join(trueName.split("/")[:-1]),exist_ok=True)
    newContent = open("update/"+i,newline="").read()
    oldFile = open(trueName,"w",newline="")
    try:
        oldFile.write(newContent)
        log(f"Successfully written update for {trueName}")
    except Exception as exc:
        log(f"[!] Update for {trueName} failed: {exc}")
    else:
        os.remove("update/"+i)
    oldFile.close()
log("Rebooting...")
if platform.startswith("win"): #win32/win64
    os.system("start __start__.py")
else: #Assume linux - use sh
    os.system("./start.sh")
