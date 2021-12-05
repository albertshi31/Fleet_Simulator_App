import compress_json
import os
import json

for folder in ["Coral_Springs", "Eugene", "Greenwich", "Honolulu", "Oakland", "Savannah", "Trenton"]:
    for filename in os.listdir("static/"+folder):
        if filename.endswith(".json"):
            with open(os.path.join("static",folder, filename), "r") as f:
                data = json.load(f)
            compress_json.dump(data, os.path.join("static",folder, filename+".gz"))
            os.remove(os.path.join("static",folder, filename))
