import os
import json
import pandas as pd

deliveries = []

folder_path = r"C:\Users\admin\OneDrive\Desktop\Documents\ipl_prediction_project\data\ipl_json"

for file in os.listdir(folder_path):

    if file.endswith(".json"):

        match_id = file.replace(".json", "")

        with open(os.path.join(folder_path, file), "r") as f:

            data = json.load(f)

            innings = data["innings"]

            for inning_index, inning in enumerate(innings, start=1):

                team = inning["team"]

                overs = inning["overs"]

                for over_data in overs:

                    over_number = over_data["over"]

                    for delivery in over_data["deliveries"]:

                        batter = delivery["batter"]
                        bowler = delivery["bowler"]

                        runs = delivery["runs"]["total"]

                        wicket = 0

                        if "wickets" in delivery:
                            wicket = 1

                        row = {
                            "match_id": match_id,
                            "inning": inning_index,
                            "batting_team": team,
                            "over": over_number,
                            "batter": batter,
                            "bowler": bowler,
                            "total_runs": runs,
                            "wicket": wicket
                        }

                        deliveries.append(row)

df = pd.DataFrame(deliveries)

df.to_csv(df.to_csv(r"C:\Users\admin\OneDrive\Desktop\Documents\ipl_prediction_project\data\ipl_json\deliveries.csv", index=False))

print("deliveries.csv created successfully")