from time import sleep
from dotenv import dotenv_values
import os
auths = dotenv_values()
while True:
	print("Starting client.run")
	try:
		from main import client
	except ImportError as exc:
		print("[!] Import error for client:",exc)
	else:
		print("main imported successfully - running...")
		client.run(botauth)
	print("Checking for updates for client...")
