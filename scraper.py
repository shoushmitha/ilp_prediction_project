"""
IPL Live Data Scraper
Scrapes live match scores, points table, and schedules from ESPNCricinfo.
Used as a fallback / supplement to CricAPI when API quota runs out.
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import os
from datetime import datetime

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# ─────────────────────────────────────────────────────
# 1. Scrape Live IPL Score from ESPNCricinfo
# ─────────────────────────────────────────────────────
def scrape_live_ipl_score():
    """
    Scrapes the live IPL match score from ESPNCricinfo.
    Returns a dict with match_title, score, status, and timestamp.
    """
    url = "https://www.espncricinfo.com/live-cricket-score"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Target live score cards
        match_cards = soup.find_all("div", class_=lambda c: c and "match-score-block" in c)

        ipl_matches = []
        for card in match_cards:
            title_tag = card.find("p", class_=lambda c: c and "series-name" in c)
            title = title_tag.get_text(strip=True) if title_tag else ""

            if "IPL" not in title and "Indian Premier League" not in title:
                continue

            score_tag = card.find("div", class_=lambda c: c and "score" in c)
            score = score_tag.get_text(strip=True) if score_tag else "N/A"

            status_tag = card.find("div", class_=lambda c: c and "status" in c)
            status = status_tag.get_text(strip=True) if status_tag else "N/A"

            ipl_matches.append({
                "match_title": title,
                "score": score,
                "status": status,
                "source": "ESPNCricinfo (Scraper)",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })

        return ipl_matches if ipl_matches else _fallback_score()

    except Exception as e:
        print(f"[Scraper Error] scrape_live_ipl_score: {e}")
        return _fallback_score()


# ─────────────────────────────────────────────────────
# 2. Scrape IPL 2025 Points Table from CricBuzz
# ─────────────────────────────────────────────────────
def scrape_ipl_points_table(year: int = 2025):
    """
    Scrapes IPL points table from Cricbuzz.
    Parameters:
        year (int): The IPL season year. Default is 2025.
    Returns:
        list of dicts: Each dict has Team, M, W, L, NR, Pts, NRR.
    """
    url = f"https://www.cricbuzz.com/cricket-series/ipl-{year}/points-table"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        table = soup.find("table")
        if not table:
            print("[Scraper] Points table not found on Cricbuzz.")
            return []

        rows = table.find_all("tr")[1:]  # skip header
        teams = []
        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 7:
                teams.append({
                    "Team":   cols[0].get_text(strip=True),
                    "M":      cols[1].get_text(strip=True),
                    "W":      cols[2].get_text(strip=True),
                    "L":      cols[3].get_text(strip=True),
                    "NR":     cols[4].get_text(strip=True),
                    "Pts":    cols[5].get_text(strip=True),
                    "NRR":    cols[6].get_text(strip=True),
                })
        return teams

    except Exception as e:
        print(f"[Scraper Error] scrape_ipl_points_table: {e}")
        return []


# ─────────────────────────────────────────────────────
# 3. Scrape IPL Schedule from ESPNCricinfo
# ─────────────────────────────────────────────────────
def scrape_ipl_schedule(year: int = 2025):
    """
    Scrapes the IPL fixture/schedule.
    Parameters:
        year (int): IPL season year.
    Returns:
        list of dicts with match details.
    """
    url = f"https://www.espncricinfo.com/series/ipl-{year}/schedule-fixtures"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        fixtures = []
        match_blocks = soup.find_all("div", class_=lambda c: c and "match-info" in c)

        for block in match_blocks:
            date_tag = block.find("span", class_=lambda c: c and "date" in c)
            teams_tags = block.find_all("span", class_=lambda c: c and "team-name" in c)
            venue_tag = block.find("span", class_=lambda c: c and "venue" in c)

            date = date_tag.get_text(strip=True) if date_tag else "TBD"
            teams = " vs ".join([t.get_text(strip=True) for t in teams_tags]) if teams_tags else "TBD"
            venue = venue_tag.get_text(strip=True) if venue_tag else "TBD"

            fixtures.append({"Date": date, "Match": teams, "Venue": venue})

        return fixtures

    except Exception as e:
        print(f"[Scraper Error] scrape_ipl_schedule: {e}")
        return []


# ─────────────────────────────────────────────────────
# 4. Scrape Top Batsmen Stats from ESPNCricinfo
# ─────────────────────────────────────────────────────
def scrape_top_batsmen(year: int = 2025):
    """
    Scrapes top run scorers for the IPL season.
    Parameters:
        year (int): IPL season year.
    Returns:
        list of dicts with Player, Team, Runs, Avg, SR.
    """
    url = f"https://www.espncricinfo.com/series/ipl-{year}/most-runs"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        table = soup.find("table")
        if not table:
            return []

        rows = table.find_all("tr")[1:]
        batsmen = []
        for row in rows[:10]:
            cols = row.find_all("td")
            if len(cols) >= 8:
                batsmen.append({
                    "Player": cols[1].get_text(strip=True),
                    "Team":   cols[2].get_text(strip=True),
                    "Runs":   cols[4].get_text(strip=True),
                    "Avg":    cols[6].get_text(strip=True),
                    "SR":     cols[7].get_text(strip=True),
                })
        return batsmen

    except Exception as e:
        print(f"[Scraper Error] scrape_top_batsmen: {e}")
        return []


# ─────────────────────────────────────────────────────
# 5. Scrape Top Bowlers Stats
# ─────────────────────────────────────────────────────
def scrape_top_bowlers(year: int = 2025):
    """
    Scrapes top wicket takers for the IPL season.
    Parameters:
        year (int): IPL season year.
    Returns:
        list of dicts with Player, Team, Wkts, Avg, Econ.
    """
    url = f"https://www.espncricinfo.com/series/ipl-{year}/most-wickets"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        table = soup.find("table")
        if not table:
            return []

        rows = table.find_all("tr")[1:]
        bowlers = []
        for row in rows[:10]:
            cols = row.find_all("td")
            if len(cols) >= 8:
                bowlers.append({
                    "Player": cols[1].get_text(strip=True),
                    "Team":   cols[2].get_text(strip=True),
                    "Wkts":   cols[4].get_text(strip=True),
                    "Avg":    cols[5].get_text(strip=True),
                    "Econ":   cols[6].get_text(strip=True),
                })
        return bowlers

    except Exception as e:
        print(f"[Scraper Error] scrape_top_bowlers: {e}")
        return []


# ─────────────────────────────────────────────────────
# 6. Scrape IPL Season Champion / Winner
# ─────────────────────────────────────────────────────
def scrape_ipl_winner(year: int = 2026):
    """
    Scrapes the IPL champion for the given year from ESPNCricinfo.
    Falls back to Wikipedia if ESPNCricinfo fails.
    Returns a dict with champion, runner_up, result, venue, player_of_match, etc.
    """
    # Try ESPNCricinfo series page
    try:
        url = f"https://www.espncricinfo.com/series/ipl-{year}/results"
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Look for the final match result card
        cards = soup.find_all("div", class_=lambda c: c and "match-info" in c)
        for card in cards:
            text = card.get_text(" ", strip=True).lower()
            if "final" in text:
                teams_tags = card.find_all("span", class_=lambda c: c and "team-name" in c)
                status_tag = card.find("div", class_=lambda c: c and "status" in c)
                teams = [t.get_text(strip=True) for t in teams_tags]
                status = status_tag.get_text(strip=True) if status_tag else ""
                if len(teams) >= 2 and "won" in status.lower():
                    winner = teams[0] if teams[0].lower() in status.lower() else teams[1]
                    runner_up = teams[1] if winner == teams[0] else teams[0]
                    return {
                        "champion": winner,
                        "runner_up": runner_up,
                        "result": status,
                        "final_date": f"May {year}",
                        "venue": "TBD",
                        "source": "ESPNCricinfo",
                    }
    except Exception as e:
        print(f"[Scraper] ESPNCricinfo winner scrape failed: {e}")

    # Try Wikipedia IPL page as fallback
    try:
        url = f"https://en.wikipedia.org/wiki/{year}_Indian_Premier_League"
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Look for the infobox champion cell
        infobox = soup.find("table", class_="infobox")
        if infobox:
            rows = infobox.find_all("tr")
            champion = None
            runner_up = None
            for row in rows:
                th = row.find("th")
                td = row.find("td")
                if th and td:
                    label = th.get_text(strip=True).lower()
                    value = td.get_text(strip=True)
                    if "champion" in label or "winner" in label:
                        champion = value
                    elif "runner" in label or "finalist" in label:
                        runner_up = value
            if champion:
                return {
                    "champion": champion,
                    "runner_up": runner_up or "TBD",
                    "result": f"{champion} won the IPL {year} title",
                    "final_date": f"May {year}",
                    "venue": "TBD",
                    "source": "Wikipedia",
                }
    except Exception as e:
        print(f"[Scraper] Wikipedia winner scrape failed: {e}")

    return None


# ─────────────────────────────────────────────────────
# 6. Save Scraped Data to JSON Cache
# ─────────────────────────────────────────────────────
def save_scraped_cache(data: dict, filename: str = "scraped_cache.json"):
    """
    Saves scraped data as a local JSON cache file.
    Parameters:
        data (dict): Data to cache.
        filename (str): Cache filename. Default: scraped_cache.json
    """
    cache_path = os.path.join(os.path.dirname(__file__), "data", filename)
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"[Cache] Saved to {cache_path}")


def load_scraped_cache(filename: str = "scraped_cache.json"):
    """
    Loads cached scraped data.
    Parameters:
        filename (str): Cache filename.
    Returns:
        dict or None
    """
    cache_path = os.path.join(os.path.dirname(__file__), "data", filename)
    if os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


# ─────────────────────────────────────────────────────
# Helper: Fallback data when scraping fails
# ─────────────────────────────────────────────────────
def _fallback_score():
    return [{
        "match_title": "IPL 2025 - Live Match",
        "score": "Data unavailable - check cricbuzz.com",
        "status": "Scraper temporarily unavailable",
        "source": "Fallback",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }]


# ─────────────────────────────────────────────────────
# CLI Test Runner
# ─────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 50)
    print("🏏 IPL LIVE SCRAPER TEST")
    print("=" * 50)

    print("\n📡 Live Scores:")
    scores = scrape_live_ipl_score()
    for s in scores:
        print(f"  {s['match_title']} | {s['score']} | {s['status']}")

    print("\n📊 Points Table (2025):")
    table = scrape_ipl_points_table(2025)
    for row in table[:5]:
        print(f"  {row}")

    print("\n📅 Schedule:")
    schedule = scrape_ipl_schedule(2025)
    for match in schedule[:5]:
        print(f"  {match}")

    print("\n🏏 Top Batsmen:")
    batsmen = scrape_top_batsmen(2025)
    for b in batsmen[:5]:
        print(f"  {b}")

    print("\n🎳 Top Bowlers:")
    bowlers = scrape_top_bowlers(2025)
    for b in bowlers[:5]:
        print(f"  {b}")

    # Save all scraped data to cache
    all_data = {
        "live_scores": scores,
        "points_table": table,
        "schedule": schedule,
        "top_batsmen": batsmen,
        "top_bowlers": bowlers,
        "cached_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    save_scraped_cache(all_data)
    print("\n✅ All data cached successfully!")
