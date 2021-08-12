from dotenv import dotenv_values
from time import sleep
import asyncio
import os
auth = dotenv_values()['BOTAUTH']
print("Starting...")
try:
	from main import client
except ImportError as exc:
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
	print(i)
	if i == "__start__.py":
		print("Please update this file manually instead of through auto-update.")
		continue
	newFile = open('update/'+i,newline='').read()
	print("Got update file",i)
	if os.path.isfile(i):
		backup = open(i,newline='').read()
		print("Created backup incase of disaster")
	else:
		print("No backup required to be made")
	oldFile = open(i,"w",newline='')
	print("Got current file")
	try:
		oldFile.write(newFile)
		print("Successfully written update for",i)
	except Exception as exc:
		if backup:
			oldFile.write(backup)
			print("! Update for",i,"failed (Backup written):",exc)
		else:
			print("! Update for",i,"failed (No backup):",exc)
	else:
		os.remove('update/'+i)
	oldFile.close()
os.system('start __start__.py')