# Handler for the modules folder
# __import__ isnt friendly with sub-dirs, fromfile makes no sense, and ive got no wifi to figure out how, so exec it is
import os
def loadModules(origin=None):
    print("Loading modules origin=",origin)
    for fname in os.listdir("modules"):
        if not fname.endswith(".py"):
            continue
        if not os.path.isfile("modules/"+fname):
            continue
        fname = fname[:-3]
        if fname == "__main__":
            continue
        try:
            exec(f"from modules import {fname}")
        except Exception as exc:
            print("[Modules]",fname,"failed:",exc)
async def loadModulesAsync(msg,args):
    loadModules("CMD -> "+msg.author.name)
addCommand("d -reload modules",loadModulesAsync,0,"",{},None,"dev")
loadModules("Import")
print("Module importer finished")