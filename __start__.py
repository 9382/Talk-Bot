from dotenv import dotenv_values
from sys import platform
from time import sleep
import asyncio
import os
auth = dotenv_values()['BOTAUTH']
print("Starting...")
try:
    from main import client
except Exception as exc:
    print("[!] Import error for client:",exc)
    sleep(3)
else:
    print("main imported successfully - running...")
    try:
        client.run(auth)
    except Exception as exc:
        print("[!] client.run exited:",exc)
print("Checking for updates for client...")
for i in os.listdir('update'): #What a mess
    print("[Updater]",i)
    if i == "__start__.py":
        print("Please update this file manually instead of through auto-update. Trust me, you dont want that headache")
        continue
    trueName = i.replace("^","/")
    if trueName != i:
        print("Sub-folder detected:",i.split("^"))
    newFile = open('update/'+i,newline='').read()
    print("Got update file",i)
    if os.path.isfile(i):
        backup = open(trueName,newline='').read()
        print("Created backup incase of disaster")
    else:
        print("No backup can be made")
    oldFile = open(trueName,"w",newline='')
    try:
        oldFile.write(newFile)
        print("Successfully written update for",trueName)
    except Exception as exc:
        if backup:
            oldFile.write(backup)
            print("[!] Update for",trueName,"failed (Backup written):",exc)
        else:
            print("[!] Update for",trueName,"failed (No backup):",exc)
    else:
        os.remove('update/'+i)
    oldFile.close()
print("Rebooting...")
if platform.startswith("win"): #win32/win64
    os.system('start __start__.py')
else: #Assume linux - use sh
    os.system('./start.sh')