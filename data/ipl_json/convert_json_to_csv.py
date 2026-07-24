import os
import json
import pandas as pd

matches = []

folder_path = r"C:\Users\admin\OneDrive\Desktop\Documents\ipl_prediction_project\data\ipl_json"

for file in os.listdir(folder_path):

    if file.endswith(".json"):

        with open(os.path.join(folder_path, file), "r") as f:

            data = json.load(f)

            info = data["info"]

            match = {
                "match_id": file.replace(".json", ""),
                "team1": info["teams"][0],
                "team2": info["teams"][1],
                "venue": info.get("venue", "Unknown"),
                "winner": info.get("outcome", {}).get("winner", "No Result"),
                "date": info["dates"][0]
            }

            matches.append(match)

df = pd.DataFrame(matches)

df.to_csv(df.to_csv(r"C:\Users\admin\OneDrive\Desktop\Documents\ipl_prediction_project\data\ipl_json\matches.csv", index=False))

print("matches.csv created successfully")