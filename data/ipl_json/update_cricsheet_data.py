"""
update_cricsheet_data.py
========================
Downloads the LATEST IPL ball-by-ball data from Cricsheet.org,
extracts only NEW match JSON files (not already in the folder),
then rebuilds matches.csv and deliveries.csv with ALL matches up to today.

Run with:   py update_cricsheet_data.py
"""

import os
import json
import zipfile
import requests
import pandas as pd
from datetime import datetime

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
JSON_DIR    = BASE_DIR                                          # same folder as this script
MATCHES_CSV = os.path.join(BASE_DIR, "matches.csv")
DELIV_CSV   = os.path.join(BASE_DIR, "deliveries.csv")
ZIP_PATH    = os.path.join(BASE_DIR, "_cricsheet_ipl_latest.zip")

# ── Cricsheet Download URL ─────────────────────────────────────────────────────
# This URL always points to the latest IPL JSON pack on Cricsheet
CRICSHEET_URL = "https://cricsheet.org/downloads/ipl_json.zip"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/124 Safari/537.36"
    )
}

# ── Step 1: Download ───────────────────────────────────────────────────────────
def download_cricsheet_zip():
    print("[1/4] Downloading latest IPL data from Cricsheet.org ...")
    try:
        resp = requests.get(CRICSHEET_URL, headers=HEADERS, stream=True, timeout=120)
        resp.raise_for_status()
        total = int(resp.headers.get("content-length", 0))
        downloaded = 0
        with open(ZIP_PATH, "wb") as f:
            for chunk in resp.iter_content(chunk_size=65536):
                f.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = downloaded * 100 // total
                    print(f"\r   Downloading... {pct}%", end="", flush=True)
        print(f"\n   Saved to: {ZIP_PATH}  ({downloaded // 1024} KB)")
        return True
    except Exception as e:
        print(f"\n[ERROR] Download failed: {e}")
        return False


# ── Step 2: Extract NEW files only ────────────────────────────────────────────
def extract_new_json_files():
    print("[2/4] Extracting new match JSON files ...")
    existing = set(
        f for f in os.listdir(JSON_DIR)
        if f.endswith(".json") and f[0].isdigit()
    )
    new_count = 0
    with zipfile.ZipFile(ZIP_PATH, "r") as zf:
        members = [m for m in zf.namelist() if m.endswith(".json")]
        print(f"   ZIP contains {len(members)} JSON files, you have {len(existing)} already.")
        for member in members:
            filename = os.path.basename(member)
            if not filename:
                continue
            if filename not in existing:
                zf.extract(member, JSON_DIR)
                # Move from subfolder if extracted into one
                extracted_path = os.path.join(JSON_DIR, member)
                target_path    = os.path.join(JSON_DIR, filename)
                if extracted_path != target_path and os.path.exists(extracted_path):
                    os.replace(extracted_path, target_path)
                new_count += 1

    print(f"   Added {new_count} new match files.")
    return new_count


# ── Step 3: Rebuild matches.csv ───────────────────────────────────────────────
def build_matches_csv():
    print("[3/4] Rebuilding matches.csv from ALL JSON files ...")
    matches = []
    json_files = sorted([
        f for f in os.listdir(JSON_DIR)
        if f.endswith(".json") and f[0].isdigit()
    ])
    skipped = 0
    for file in json_files:
        try:
            with open(os.path.join(JSON_DIR, file), "r", encoding="utf-8") as f:
                data = json.load(f)

            info = data.get("info", {})
            teams = info.get("teams", [])
            if len(teams) < 2:
                skipped += 1
                continue

            outcome  = info.get("outcome", {})
            winner   = outcome.get("winner", "No Result")
            if not winner:
                # Could be tied, D/L result etc.
                if outcome.get("result"):
                    winner = outcome.get("result")
                else:
                    winner = "No Result"

            toss = info.get("toss", {})
            match = {
                "match_id":       file.replace(".json", ""),
                "date":           info["dates"][0] if info.get("dates") else "",
                "venue":          info.get("venue", "Unknown"),
                "team1":          teams[0],
                "team2":          teams[1],
                "toss_winner":    toss.get("winner", ""),
                "toss_decision":  toss.get("decision", ""),
                "winner":         winner,
                "win_by_runs":    outcome.get("by", {}).get("runs", 0),
                "win_by_wickets": outcome.get("by", {}).get("wickets", 0),
                "player_of_match": (info.get("player_of_match") or [""])[0],
                "city":           info.get("city", ""),
                "season":         info.get("season", ""),
            }
            matches.append(match)
        except Exception as e:
            skipped += 1
            print(f"   [SKIP] {file}: {e}")

    df = pd.DataFrame(matches)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.sort_values("date").reset_index(drop=True)
    df.to_csv(MATCHES_CSV, index=False)
    print(f"   matches.csv: {len(df)} matches  |  skipped: {skipped}")
    return df


# ── Step 4: Rebuild deliveries.csv ───────────────────────────────────────────
def build_deliveries_csv():
    print("[4/4] Rebuilding deliveries.csv (ball-by-ball) ...")
    deliveries = []
    json_files = sorted([
        f for f in os.listdir(JSON_DIR)
        if f.endswith(".json") and f[0].isdigit()
    ])
    skipped = 0
    for file in json_files:
        match_id = file.replace(".json", "")
        try:
            with open(os.path.join(JSON_DIR, file), "r", encoding="utf-8") as f:
                data = json.load(f)

            for inning_idx, inning in enumerate(data.get("innings", []), start=1):
                batting_team = inning.get("team", "")
                for over_data in inning.get("overs", []):
                    over_num = over_data.get("over", 0)
                    for delivery in over_data.get("deliveries", []):
                        runs_d   = delivery.get("runs", {})
                        wickets  = delivery.get("wickets", [])
                        extras_d = delivery.get("extras", {})
                        row = {
                            "match_id":     match_id,
                            "inning":       inning_idx,
                            "batting_team": batting_team,
                            "over":         over_num,
                            "batter":       delivery.get("batter", ""),
                            "bowler":       delivery.get("bowler", ""),
                            "non_striker":  delivery.get("non_striker", ""),
                            "batsman_runs": runs_d.get("batter", 0),
                            "extra_runs":   runs_d.get("extras", 0),
                            "total_runs":   runs_d.get("total", 0),
                            "extras_type":  ",".join(extras_d.keys()) if extras_d else "",
                            "wicket":       1 if wickets else 0,
                            "dismissal_kind": wickets[0].get("kind", "") if wickets else "",
                            "player_dismissed": (
                                wickets[0].get("player_out", "") if wickets else ""
                            ),
                        }
                        deliveries.append(row)
        except Exception as e:
            skipped += 1
            print(f"   [SKIP] {file}: {e}")

    df = pd.DataFrame(deliveries)
    df.to_csv(DELIV_CSV, index=False)
    print(f"   deliveries.csv: {len(df):,} ball records  |  skipped: {skipped}")
    return df


# ── Step 5: Print summary ─────────────────────────────────────────────────────
def print_summary(matches_df):
    print("\n" + "=" * 55)
    print("  IPL DATA UPDATE COMPLETE")
    print("=" * 55)
    if len(matches_df):
        matches_df["date"] = pd.to_datetime(matches_df["date"], errors="coerce")
        matches_df["season"] = matches_df["date"].dt.year
        seasons = matches_df["season"].value_counts().sort_index()
        print(f"  Total matches: {len(matches_df)}")
        print(f"  Date range:    {matches_df['date'].min().date()} to {matches_df['date'].max().date()}")
        print(f"\n  Matches per season:")
        for season, count in seasons.items():
            print(f"    {int(season)}: {count} matches")
    print("=" * 55)
    print("  Next step: run feature_engineering.py then train_model.py")
    print("=" * 55)


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 55)
    print("  CRICSHEET IPL DATA UPDATER")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 55 + "\n")

    ok = download_cricsheet_zip()
    if not ok:
        print("Could not download. Check your internet connection.")
        exit(1)

    extract_new_json_files()

    # Clean up zip
    if os.path.exists(ZIP_PATH):
        os.remove(ZIP_PATH)
        print("   Cleaned up zip file.")

    matches_df    = build_matches_csv()
    deliveries_df = build_deliveries_csv()

    print_summary(matches_df)
