# Handler for the modules folder
# __import__ isnt friendly with sub-dirs, fromfile makes no sense, and ive got no wifi to figure out how, so exec it is
# Note 2: I gave up with globals, im not researching how to make them work with eachother, so its bytes exec time :) :) :)
import os
__all__ = ["load_modules"]
def load_modules(origin=None):
    print("Loading modules origin=",origin)
    exec_list = []
    for fname in os.listdir("modules"):
        if not fname.endswith(".py"):
            continue
        if not os.path.isfile("modules/"+fname):
            continue
        if fname == "__main__.py":
            continue
        exec_list.append(bytes("#coding: utf-8\n","utf-8")+open("modules/"+fname,"rb").read())
    return exec_list