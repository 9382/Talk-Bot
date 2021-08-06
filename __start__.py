from dotenv import dotenv_values
from time import sleep
import asyncio
import os
auth = dotenv_values()['BOTAUTH']
while True:
	print("Starting...")
	try:
		from main import client
	except ImportError as exc:
		print("[!] Import error for client:",exc)
	else:
		print("main imported successfully - running...")
		try:
		    client.run(auth)
		except Exception as exc:
			print("[!] client.run exited:",exc)
	print("Checking for updates for client...")
	for i in os.listdir('update'):
		print(i)
	sleep(2)