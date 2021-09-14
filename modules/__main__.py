# Handler for the modules folder
# __import__ isnt friendly with sub-dirs, fromfile makes no sense, and ive got no wifi to figure out how, so exec it is
import os
__all__ = ["command_list"]
command_list = []
for fname in os.listdir("modules"):
    if not fname.endswith(".py"):
        continue
    if not os.path.isfile("modules/"+fname):
        continue
    fname = fname[:-3]
    if fname == "__main__":
        continue
    try:
        exec(f"from modules.{fname} import Commands")
    except Exception as exc:
        print(exc)
    else:
        command_list.extend(Commands)
print("Module importer finished")