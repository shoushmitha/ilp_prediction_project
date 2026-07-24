import streamlit as st
import pandas as pd
import plotly.express as px
import joblib
import requests
import os
import sys
from datetime import datetime, timezone

# ─── 1. FILE PATHS & SETUP ───────────────────────────────────────────────────
# Use relative paths dynamically
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MATCHES_PATH = os.path.join(BASE_DIR, "matches.csv")
DELIV_PATH = os.path.join(BASE_DIR, "deliveries.csv")
MODEL_PATH = os.path.join(BASE_DIR, "xgb_model.pkl")

# Add parent directory to sys.path to dynamically import api.py & scraper.py
sys.path.append(os.path.abspath(os.path.join(BASE_DIR, "..", "..")))

try:
    from api import get_live_matches, get_upcoming_matches
except ImportError:
    get_live_matches = None
    get_upcoming_matches = None

try:
    from scraper import scrape_live_ipl_score, scrape_ipl_points_table, scrape_top_batsmen, scrape_top_bowlers, load_scraped_cache, scrape_ipl_winner
except ImportError:
    scrape_live_ipl_score = None
    scrape_ipl_points_table = None
    scrape_top_batsmen = None
    scrape_top_bowlers = None
    load_scraped_cache = None
    scrape_ipl_winner = None

# Load environment variables
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".env"))

# ─── 2. STANDARDISATION LOGIC ────────────────────────────────────────────────
TEAM_MAPPING = {
    "Kings XI Punjab": "Punjab Kings",
    "Royal Challengers Bengaluru": "Royal Challengers Bangalore",
    "Royal Challengers Bangalore": "Royal Challengers Bangalore",
    "Delhi Daredevils": "Delhi Capitals",
    "Delhi Capitals": "Delhi Capitals",
    "Rising Pune Supergiants": "Rising Pune Supergiants",
    "Rising Pune Supergiant": "Rising Pune Supergiants",
    "Deccan Chargers": "Sunrisers Hyderabad",
}

def standardise_team_name(name):
    if not isinstance(name, str):
        return name
    name = name.strip()
    return TEAM_MAPPING.get(name, name)

def standardise_venue_name(venue):
    if not isinstance(venue, str):
        return venue
    venue = venue.strip().lower()
    if "wankhede" in venue:
        return "Wankhede Stadium"
    if "chinnaswamy" in venue:
        return "M Chinnaswamy Stadium"
    if "chidambaram" in venue or "chepauk" in venue:
        return "MA Chidambaram Stadium"
    if "eden gardens" in venue:
        return "Eden Gardens"
    if "feroz shah kotla" in venue or "arun jaitley" in venue:
        return "Arun Jaitley Stadium"
    if "rajiv gandhi" in venue or "uppal" in venue:
        return "Rajiv Gandhi International Stadium"
    if "sawai mansingh" in venue:
        return "Sawai Mansingh Stadium"
    if "narendra modi" in venue or "motera" in venue or "ahmedabad" in venue:
        return "Narendra Modi Stadium"
    if "dy patil" in venue:
        return "Dr DY Patil Sports Academy"
    if "ekana" in venue or "lucknow" in venue:
        return "Ekana Cricket Stadium"
    if "brabourne" in venue:
        return "Brabourne Stadium"
    if "punjab cricket association" in venue or "mohali" in venue or "indrajit singh" in venue:
        return "PCA Stadium Mohali"
    if "maharashtra cricket association" in venue or "gahunje" in venue:
        return "MCA Stadium Pune"
    if "dubai" in venue:
        return "Dubai International Cricket Stadium"
    if "sharjah" in venue:
        return "Sharjah Cricket Stadium"
    if "sheikh zayed" in venue or "abu dhabi" in venue:
        return "Sheikh Zayed Stadium"
    return venue.title()

# Venue details and Pitch Behaviors Database
VENUE_DETAILS = {
    "Wankhede Stadium": {
        "place": "Mumbai, Maharashtra",
        "pitch": "Red soil pitch. Highly batting-friendly with true bounce. Offers good carry to pacers early on. Boundaries are short, and the dew factor in evening games makes chasing extremely favorable.",
        "icon": "🌊"
    },
    "M Chinnaswamy Stadium": {
        "place": "Bengaluru, Karnataka",
        "pitch": "Flat batting paradise with exceptionally short boundaries and high altitude, making it a nightmare for bowlers. High-scoring encounters are extremely common. Chasing is heavily preferred.",
        "icon": "🏟️"
    },
    "MA Chidambaram Stadium": {
        "place": "Chennai, Tamil Nadu",
        "pitch": "Dry, clay-soil pitch that traditionally assists spinners and slow bowlers. Low-scoring, tactical encounters are common here. Pitch tends to slow down and crumble as the match progresses.",
        "icon": "🦁"
    },
    "Eden Gardens": {
        "place": "Kolkata, West Bengal",
        "pitch": "Fast outfield with batting-friendly conditions. The black soil pitch offers decent bounce and carry for pacers, but high scores are typical here. Dew plays a big role in evening matches.",
        "icon": "⚔️"
    },
    "Arun Jaitley Stadium": {
        "place": "Delhi",
        "pitch": "Historically dry and slow, favoring spinners and cutters. However, recent pitch relays have turned it into a high-scoring batting track with short boundaries. Spin still plays a vital role.",
        "icon": "🏛️"
    },
    "Rajiv Gandhi International Stadium": {
        "place": "Hyderabad, Telangana",
        "pitch": "Balanced, flat pitch that favors batsmen in the first innings but slows down as the game goes on, giving spinners a major advantage. High first-innings totals are key here.",
        "icon": "🦅"
    },
    "Sawai Mansingh Stadium": {
        "place": "Jaipur, Rajasthan",
        "pitch": "Large outfield makes hitting boundaries difficult, favoring excellent running between wickets. Pitch offers assistance to both pacers and spinners, making it a competitive, balanced track.",
        "icon": "🏰"
    },
    "Narendra Modi Stadium": {
        "place": "Ahmedabad, Gujarat",
        "pitch": "The world's largest stadium features both red and black soil pitches. Red soil offers extra bounce and spin, whereas black soil is flatter and batting-friendly. High boundary limits require smart hitting.",
        "icon": "🏟️"
    },
    "Ekana Cricket Stadium": {
        "place": "Lucknow, Uttar Pradesh",
        "pitch": "Slow and low black soil pitch that makes run-scoring tough and assists spinners, cutters, and medium pacers. Red soil pitches here offer slightly better bounce and higher scoring potential.",
        "icon": "☄️"
    },
    "HPCA Stadium Dharamshala": {
        "place": "Dharamshala, Himachal Pradesh",
        "pitch": "High-altitude venue with cool breezes. Pitch offers excellent seam movement, swing, and extra bounce to fast bowlers, especially under lights. Outfield is extremely fast.",
        "icon": "🏔️"
    },
    "New International Cricket Stadium New Chandigarh": {
        "place": "Mullanpur, Punjab",
        "pitch": "Modern pitch with good grass cover. Offers decent carry and early swing for fast bowlers, turning into a stable batting deck with true bounce as the match progresses.",
        "icon": "🌾"
    },
    "PCA Stadium Mohali": {
        "place": "Mohali, Punjab",
        "pitch": "Greenish tinge pitch that offers early pace and bounce. Generally a high-scoring ground where batsmen can trust the bounce, with slight assistance to spinners later.",
        "icon": "🏏"
    },
    "MCA Stadium Pune": {
        "place": "Gahunje, Pune, Maharashtra",
        "pitch": "Black soil pitch that starts off fast and batting-friendly but can dry up and assist spinners in the second half. Large boundaries make running between wickets crucial.",
        "icon": "⛰️"
    },
    "Dubai International Cricket Stadium": {
        "place": "Dubai, UAE",
        "pitch": "Large boundaries. Pitch provides good balance between bat and ball, with spinners playing a major role in the middle overs. Chasing is typically favored due to dew.",
        "icon": "🏙️"
    },
    "Sharjah Cricket Stadium": {
        "place": "Sharjah, UAE",
        "pitch": "Flat pitch with extremely short boundaries. High-scoring matches with plenty of sixes are the norm here. Spinners can get punished if they lose their line.",
        "icon": "🌴"
    },
    "Sheikh Zayed Stadium": {
        "place": "Abu Dhabi, UAE",
        "pitch": "Large playing area. Offers good bounce and carry for pacers early on. Pitch tends to slow down slightly in the second innings, making it a fair contest between bat and ball.",
        "icon": "🕌"
    }
}

def get_venue_details(venue_name):
    if not isinstance(venue_name, str):
        return None
    for name, details in VENUE_DETAILS.items():
        if name.lower() in venue_name.lower() or venue_name.lower() in name.lower():
            return {
                "name": name,
                "place": details["place"],
                "pitch": details["pitch"],
                "icon": details["icon"]
            }
    return {
        "name": venue_name,
        "place": "TBD, India",
        "pitch": "Balanced pitch that offers even contest between batsmen and bowlers. Watch out for pitch dryness and early moisture.",
        "icon": "🏟️"
    }

# ─── 3. PAGE CONFIG & STYLING ────────────────────────────────────────────────
st.set_page_config(page_title="IPL Prediction & Analytics Dashboard", layout="wide")

# Custom Sleek CSS Styling Block for rich modern web aesthetics
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700;800&family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');
    
    /* Force premium elegant light mode globally on the Streamlit App container */
    .stApp {
        background: radial-gradient(circle at 50% 0%, rgba(99, 102, 241, 0.08) 0%, rgba(248, 250, 252, 0) 75%), 
                    linear-gradient(135deg, #f8fafc, #f1f5f9, #e2e8f0) !important;
        color: #1e293b !important;
    }
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Outfit', sans-serif;
        font-weight: 700;
        letter-spacing: -0.5px;
        color: #0f172a !important;
        text-shadow: none !important;
    }
    
    /* Make standard labels, text, and paragraphs dark charcoal with high readability */
    .stApp p, .stApp label, .stApp span, .stApp li, .stApp td {
        color: #334155 !important;
    }
    
    div.block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* Premium frosted light-glass card container with elegant shadows & micro-animations */
    .premium-card {
        background: rgba(255, 255, 255, 0.75) !important;
        border: 1px solid rgba(99, 102, 241, 0.15) !important;
        border-radius: 20px;
        padding: 24px;
        backdrop-filter: blur(20px) saturate(180%);
        box-shadow: 0 10px 25px rgba(148, 163, 184, 0.12);
        margin-bottom: 24px;
        transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1) !important;
        animation: fadeInUp 0.6s ease-out;
    }
    
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(12px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .premium-card:hover {
        border-color: rgba(99, 102, 241, 0.45) !important;
        transform: translateY(-4px);
        box-shadow: 0 16px 35px rgba(99, 102, 241, 0.15) !important;
    }
    
    /* Double Win Probability Bar Styling */
    .bar-container {
        display: flex;
        width: 100%;
        height: 42px;
        border-radius: 21px;
        overflow: hidden;
        margin: 18px 0;
        box-shadow: 0 6px 15px rgba(148, 163, 184, 0.18);
        border: 1px solid rgba(255, 255, 255, 0.8);
        background-color: rgba(255, 255, 255, 0.8);
    }
    
    .bar-team1 {
        display: flex;
        align-items: center;
        justify-content: flex-start;
        padding-left: 24px;
        font-weight: 800;
        font-size: 15px;
        color: white !important;
        transition: width 0.8s cubic-bezier(0.16, 1, 0.3, 1);
        text-shadow: 0 1px 3px rgba(0,0,0,0.5);
    }
    
    .bar-team2 {
        display: flex;
        align-items: center;
        justify-content: flex-end;
        padding-right: 24px;
        font-weight: 800;
        font-size: 15px;
        color: white !important;
        transition: width 0.8s cubic-bezier(0.16, 1, 0.3, 1);
        text-shadow: 0 1px 3px rgba(0,0,0,0.5);
    }
    
    /* Clean readable values inside cards */
    .metric-value {
        font-size: 18px;
        font-weight: 700;
        color: #4f46e5 !important; /* Premium rich Indigo */
        line-height: 1.6;
        margin-top: 10px;
    }
    
    .metric-label {
        font-size: 12px;
        color: #64748b !important; /* Muted slate-grey label */
        text-transform: uppercase;
        letter-spacing: 1.5px;
        font-weight: 800;
    }
    
    /* Style the main dashboard Tabs to look incredibly premium in Light Theme */
    .stTabs [data-baseweb="tab-list"] {
        background-color: rgba(241, 245, 249, 0.8) !important;
        border: 1px solid rgba(226, 232, 240, 0.8) !important;
        border-radius: 16px;
        padding: 8px;
        border-bottom: none;
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        color: #64748b !important;
        font-weight: 700 !important;
        font-size: 15px !important;
        padding: 12px 20px !important;
        border-radius: 12px !important;
        transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1) !important;
        border-bottom: none !important;
    }
    
    .stTabs [aria-selected="true"] {
        color: #ffffff !important;
        background: linear-gradient(135deg, #4f46e5, #6366f1) !important;
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.25);
    }
    
    /* Styled Selectboxes & Inputs for premium look */
    div[data-baseweb="select"] > div {
        background-color: #ffffff !important;
        color: #0f172a !important;
        border: 1px solid rgba(203, 213, 225, 0.8) !important;
        border-radius: 12px !important;
        transition: all 0.3s ease !important;
    }
    div[data-baseweb="select"] > div:hover {
        border-color: rgba(99, 102, 241, 0.5) !important;
        box-shadow: 0 0 10px rgba(99, 102, 241, 0.1) !important;
    }
    
    input {
        background-color: #ffffff !important;
        color: #0f172a !important;
        border-radius: 12px !important;
        border: 1px solid rgba(203, 213, 225, 0.8) !important;
    }
    
    /* Styled Primary Action Buttons (Calculate Win Probabilities) */
    div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #4f46e5, #6366f1) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 10px 24px !important;
        font-weight: 700 !important;
        box-shadow: 0 4px 15px rgba(99, 102, 241, 0.3) !important;
        transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1) !important;
    }
    div.stButton > button[kind="primary"]:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(99, 102, 241, 0.5) !important;
        background: linear-gradient(135deg, #4338ca, #4f46e5) !important;
    }
</style>
""", unsafe_allow_html=True)

# ─── 4. FETCH LIVE & UPCOMING MATCHES ─────────────────────────────────────────
live_data = None
upcoming_today = []
api_error_message = None

if get_live_matches:
    try:
        live_matches = get_live_matches()
        if live_matches:
            ipl_live = [
                m for m in live_matches
                if "IPL" in m.get("name", "") or "Indian Premier League" in m.get("name", "")
            ]
            selected = ipl_live[0] if ipl_live else None

            if selected:
                score_list = selected.get("score", [])
                score_parts = []
                if isinstance(score_list, list):
                    for s in score_list:
                        r, w, o = s.get("r"), s.get("w"), s.get("o")
                        inning = s.get("inning", "")
                        if r is not None:
                            score_parts.append(
                                f"{inning}: {r}/{w if w is not None else 0} ({o if o is not None else 0} ov)"
                            )
                live_data = {
                    "match_title": selected.get("name"),
                    "status":      selected.get("status"),
                    "score":       " | ".join(score_parts) if score_parts else "Match in progress",
                    "teams":       [standardise_team_name(t) for t in selected.get("teams", [])],
                }
    except Exception as e:
        api_error_message = f"Live API unavailable ({str(e)}). Using Scraper fallback."

# Web Scraper Fallback for Live Score
if not live_data and scrape_live_ipl_score:
    try:
        scraped_scores = scrape_live_ipl_score()
        if scraped_scores and len(scraped_scores) > 0 and scraped_scores[0]["match_title"] != "IPL 2025 - Live Match":
            s_match = scraped_scores[0]
            # Try parsing teams from title (format usually "Team A vs Team B")
            teams = [t.strip() for t in s_match["match_title"].split(" vs ") if len(t.strip()) > 0]
            # Map standard names
            teams = [standardise_team_name(t) for t in teams]
            live_data = {
                "match_title": s_match["match_title"],
                "score": s_match["score"],
                "status": s_match["status"],
                "teams": teams
            }
    except Exception as e:
        api_error_message = (api_error_message or "") + f" | Scraper Error: {str(e)}"

# Cache Fallback for Live Score
if not live_data and load_scraped_cache:
    try:
        cached_data = load_scraped_cache()
        if cached_data and "live_scores" in cached_data and len(cached_data["live_scores"]) > 0:
            c_match = cached_data["live_scores"][0]
            teams = [t.strip() for t in c_match["match_title"].split(" vs ") if len(t.strip()) > 0]
            teams = [standardise_team_name(t) for t in teams]
            live_data = {
                "match_title": c_match["match_title"],
                "score": c_match["score"],
                "status": c_match["status"],
                "teams": teams
            }
    except Exception:
        pass

# Fetch upcoming/today fixtures
if get_upcoming_matches:
    try:
        all_upcoming = get_upcoming_matches()
        if all_upcoming:
            today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            upcoming_today = [m for m in all_upcoming if m.get("date", "") == today_str]
            if not upcoming_today:
                # No match today — grab upcoming fixtures
                upcoming_today = all_upcoming[:3]
    except Exception:
        pass

# Fallback to local scraped schedule cache if upcoming_today is still empty
if not upcoming_today and load_scraped_cache:
    try:
        cached_data = load_scraped_cache()
        if cached_data and "schedule" in cached_data:
            cached_schedule = cached_data["schedule"]
            for item in cached_schedule:
                match_name = item.get("Match", "")
                clean_match = match_name
                if ":" in match_name:
                    clean_match = match_name.split(":", 1)[1]
                teams = [t.strip() for t in clean_match.split(" vs ") if len(t.strip()) > 0]
                
                upcoming_today.append({
                    "name": match_name,
                    "date": item.get("Date", ""),
                    "venue": item.get("Venue", "TBD"),
                    "team1": teams[0] if len(teams) > 0 else "TBD",
                    "team2": teams[1] if len(teams) > 1 else "TBD",
                })
    except Exception:
        pass

# ─── 5. LOAD DATA & INITIALISE ────────────────────────────────────────────────
@st.cache_data
def load_historical_data():
    if not os.path.exists(MATCHES_PATH) or not os.path.exists(DELIV_PATH):
        return None, None
    m_df = pd.read_csv(MATCHES_PATH)
    d_df = pd.read_csv(DELIV_PATH)
    
    # Standardise
    m_df["team1"] = m_df["team1"].apply(standardise_team_name)
    m_df["team2"] = m_df["team2"].apply(standardise_team_name)
    m_df["winner"] = m_df["winner"].apply(standardise_team_name)
    m_df["toss_winner"] = m_df["toss_winner"].apply(standardise_team_name)
    m_df["venue"] = m_df["venue"].apply(standardise_venue_name)
    
    m_df["date"] = pd.to_datetime(m_df["date"], errors="coerce")
    m_df["season"] = m_df["date"].dt.year
    m_df = m_df.sort_values("date").reset_index(drop=True)
    
    return m_df, d_df

matches_df, deliveries_df = load_historical_data()

# Precompute runs for venue analysis
all_teams = []
all_venues = []
if matches_df is not None and deliveries_df is not None:
    deliveries_df["match_id"] = deliveries_df["match_id"].astype(str)
    matches_df["match_id"] = matches_df["match_id"].astype(str)
    
    if "total_match_runs" not in matches_df.columns:
        match_runs = deliveries_df.groupby("match_id")["total_runs"].sum().reset_index()
        match_runs.columns = ["match_id", "total_match_runs"]
        matches_df = matches_df.merge(match_runs, on="match_id", how="left")
        
    all_teams = sorted(list(set(matches_df["team1"].dropna().unique()) | set(matches_df["team2"].dropna().unique())))
    all_venues = sorted(matches_df["venue"].dropna().unique())

# Page Title
st.title("🏏 IPL AI Predictor & Championship Analytics")

# ─── 5b. IPL 2026 CHAMPION BANNER ───────────────────────────────────────────
# Try live scrape first, then fall back to cache
_champion_data = None
if scrape_ipl_winner:
    try:
        _champion_data = scrape_ipl_winner(2026)
    except Exception:
        pass

# Cache fallback
if not _champion_data and load_scraped_cache:
    try:
        _cache = load_scraped_cache()
        if _cache and "ipl_2026_winner" in _cache:
            _champion_data = _cache["ipl_2026_winner"]
    except Exception:
        pass

# Hard-coded confirmed fallback (verified result)
if not _champion_data:
    _champion_data = {
        "champion": "Royal Challengers Bengaluru",
        "runner_up": "Gujarat Titans",
        "result": "Royal Challengers Bengaluru won by 5 wickets",
        "final_date": "May 31, 2026",
        "venue": "Narendra Modi Stadium, Ahmedabad",
        "gt_score": "155/8 (20 overs)",
        "rcb_score": "161/5 (18 overs)",
        "player_of_match": "Virat Kohli",
        "potm_performance": "75* off 42 balls",
        "title_count": "2nd IPL Title",
        "achievement": "Back-to-back champions — only 3rd team in IPL history"
    }

_champ = _champion_data.get("champion", "")
_runner = _champion_data.get("runner_up", "")
_result = _champion_data.get("result", "")
_final_date = _champion_data.get("final_date", "")
_venue_final = _champion_data.get("venue", "")
_gt_score = _champion_data.get("gt_score", "")
_rcb_score = _champion_data.get("rcb_score", "")
_potm = _champion_data.get("player_of_match", "")
_potm_perf = _champion_data.get("potm_performance", "")
_title_count = _champion_data.get("title_count", "")
_achievement = _champion_data.get("achievement", "")

# Determine champion color (RCB = red, GT = blue, etc.)
_champ_color_map = {
    "Royal Challengers Bengaluru": ("#ec1c24", "#b91c1c", "#fef2f2"),
    "Royal Challengers Bangalore": ("#ec1c24", "#b91c1c", "#fef2f2"),
    "Gujarat Titans": ("#0b2240", "#1e3a5f", "#eff6ff"),
    "Chennai Super Kings": ("#f7971e", "#d97706", "#fffbeb"),
    "Mumbai Indians": ("#004ba0", "#1d4ed8", "#eff6ff"),
    "Kolkata Knight Riders": ("#3a225d", "#6d28d9", "#f5f3ff"),
    "Sunrisers Hyderabad": ("#ff822a", "#ea580c", "#fff7ed"),
    "Rajasthan Royals": ("#ea1a85", "#db2777", "#fdf2f8"),
    "Punjab Kings": ("#dd1f26", "#b91c1c", "#fef2f2"),
    "Delhi Capitals": ("#005ca9", "#1d4ed8", "#eff6ff"),
    "Lucknow Super Giants": ("#0057e7", "#1d4ed8", "#eff6ff"),
}
_cc1, _cc2, _cbg = _champ_color_map.get(_champ, ("#4f46e5", "#6366f1", "#eef2ff"))

st.markdown(f"""
<div style='
    background: linear-gradient(135deg, {_cc1} 0%, {_cc2} 50%, #1a1a2e 100%);
    border-radius: 20px;
    padding: 0;
    margin-bottom: 28px;
    overflow: hidden;
    box-shadow: 0 20px 60px rgba(0,0,0,0.25), 0 0 0 1px rgba(255,255,255,0.1);
    position: relative;
'>
    <!-- Animated shimmer overlay -->
    <div style='
        position: absolute; inset: 0;
        background: repeating-linear-gradient(45deg, rgba(255,255,255,0.03) 0px, rgba(255,255,255,0.03) 1px, transparent 1px, transparent 20px);
        pointer-events: none;
    '></div>
    <!-- Glowing top accent bar -->
    <div style='height: 4px; background: linear-gradient(90deg, #fbbf24, #f59e0b, #fcd34d, #fbbf24); background-size: 200% 100%; animation: shimmer 2s linear infinite;'></div>
    <div style='padding: 28px 32px;'>
        <!-- Trophy header -->
        <div style='display: flex; align-items: center; gap: 16px; margin-bottom: 20px;'>
            <div style='
                width: 64px; height: 64px;
                background: linear-gradient(135deg, #fbbf24, #f59e0b);
                border-radius: 50%;
                display: flex; align-items: center; justify-content: center;
                font-size: 32px;
                box-shadow: 0 8px 20px rgba(251,191,36,0.4);
                flex-shrink: 0;
            '>🏆</div>
            <div>
                <div style='font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: 3px; color: #fcd34d; margin-bottom: 4px;'>🏏 IPL 2026 Champions</div>
                <div style='font-size: 32px; font-weight: 900; color: #ffffff; font-family: Outfit, sans-serif; letter-spacing: -1px; line-height: 1.1;'>{_champ}</div>
                <div style='font-size: 13px; color: rgba(255,255,255,0.7); margin-top: 4px; font-weight: 600;'>🎖️ {_title_count}</div>
            </div>
        </div>
        <!-- Final Scorecard -->
        <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 18px;'>
            <div style='background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.12); border-radius: 14px; padding: 14px 18px;'>
                <div style='font-size: 10px; text-transform: uppercase; letter-spacing: 1.5px; color: rgba(255,255,255,0.5); font-weight: 700; margin-bottom: 6px;'>📅 Final Match</div>
                <div style='font-size: 14px; font-weight: 700; color: #fff;'>{_final_date}</div>
                <div style='font-size: 11px; color: rgba(255,255,255,0.6); margin-top: 2px;'>📍 {_venue_final}</div>
            </div>
            <div style='background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.12); border-radius: 14px; padding: 14px 18px;'>
                <div style='font-size: 10px; text-transform: uppercase; letter-spacing: 1.5px; color: rgba(255,255,255,0.5); font-weight: 700; margin-bottom: 6px;'>⭐ Player of the Match</div>
                <div style='font-size: 14px; font-weight: 700; color: #fcd34d;'>{_potm}</div>
                <div style='font-size: 11px; color: rgba(255,255,255,0.6); margin-top: 2px;'>{_potm_perf}</div>
            </div>
        </div>
        <!-- Scorecard row -->
        <div style='background: rgba(0,0,0,0.25); border-radius: 12px; padding: 14px 18px; margin-bottom: 14px;'>
            <div style='font-size: 10px; text-transform: uppercase; letter-spacing: 1.5px; color: rgba(255,255,255,0.5); font-weight: 700; margin-bottom: 10px;'>📊 Final Scorecard</div>
            <div style='display: flex; justify-content: space-between; align-items: center;'>
                <div style='text-align: left;'>
                    <div style='font-size: 13px; color: rgba(255,255,255,0.6); font-weight: 600;'>{_runner}</div>
                    <div style='font-size: 20px; font-weight: 800; color: #fff;'>{_gt_score}</div>
                </div>
                <div style='font-size: 24px; padding: 0 16px;'>⚡</div>
                <div style='text-align: right;'>
                    <div style='font-size: 13px; color: #fcd34d; font-weight: 700;'>🏆 {_champ}</div>
                    <div style='font-size: 20px; font-weight: 800; color: #fcd34d;'>{_rcb_score}</div>
                </div>
            </div>
            <div style='margin-top: 10px; text-align: center;'>
                <span style='background: rgba(251,191,36,0.2); border: 1px solid rgba(251,191,36,0.4); padding: 4px 14px; border-radius: 20px; font-size: 12px; font-weight: 700; color: #fcd34d;'>✅ {_result}</span>
            </div>
        </div>
        <!-- Achievement badge -->
        <div style='text-align: center;'>
            <span style='background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); padding: 6px 16px; border-radius: 20px; font-size: 12px; font-weight: 600; color: rgba(255,255,255,0.85);'>🌟 {_achievement}</span>
        </div>
    </div>
</div>
<style>
@keyframes shimmer {{
    0% {{ background-position: -200% 0; }}
    100% {{ background-position: 200% 0; }}
}}
</style>
""", unsafe_allow_html=True)

# Setup Session State for prediction loads
if "pred_team1" not in st.session_state:
    st.session_state.pred_team1 = None
if "pred_team2" not in st.session_state:
    st.session_state.pred_team2 = None
if "pred_venue" not in st.session_state:
    st.session_state.pred_venue = None

# ─── 6. SMART SCHEDULE & LIVE SCORE BANNER ─────────────────────────────────────
if live_data:
    st.markdown(f"""
    <div style='
        background: linear-gradient(135deg, #ef4444, #b91c1c);
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 24px;
        color: white;
        box-shadow: 0 4px 20px rgba(239, 68, 68, 0.35);
    '>
        <div style='display:flex; justify-content:space-between; align-items:center;'>
            <div>
                <span style='background:rgba(255,255,255,0.25); padding:4px 8px; border-radius:6px; font-size:11px; font-weight:800; text-transform:uppercase; letter-spacing:1px;'>🔴 Live Match Now</span>
                <h3 style='margin: 8px 0 2px 0; color:white; font-size:24px;'>{live_data['match_title']}</h3>
                <p style='margin:0; font-size:18px; font-weight:600; opacity:0.9;'>{live_data['score']}</p>
                <p style='margin:4px 0 0 0; font-size:12px; opacity:0.8;'>📌 {live_data['status']}</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Enable automatic load of live match
    if len(live_data.get("teams", [])) >= 2:
        col_btn1, col_btn2 = st.columns([4, 1])
        with col_btn1:
            st.info(f"Analyze the live match in the predictor: **{live_data['teams'][0]} vs {live_data['teams'][1]}**")
        with col_btn2:
            if st.button("🤖 Load Live Match"):
                st.session_state.pred_team1 = live_data["teams"][0]
                st.session_state.pred_team2 = live_data["teams"][1]
                st.rerun()

elif upcoming_today:
    # 📅 Display schedule banner
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    is_today = upcoming_today[0].get("date", "") == today_str
    
    banner_title = "📅 TODAY'S SCHEDULED MATCHES" if is_today else "📅 UPCOMING IPL MATCHES"
    st.markdown(f"<h3 style='margin:10px 0;'>{banner_title}</h3>", unsafe_allow_html=True)
    
    cols = st.columns(len(upcoming_today[:3]))
    for i, match in enumerate(upcoming_today[:3]):
        with cols[i]:
            team1 = standardise_team_name(match.get("team1", "TBD"))
            team2 = standardise_team_name(match.get("team2", "TBD"))
            venue = standardise_venue_name(match.get("venue", "TBD"))
            date = match.get("date", "TBD")
            
            st.markdown(f"""
            <div class='premium-card' style='text-align: center; border-color: rgba(99, 102, 241, 0.2);'>
                <div style='font-size:20px; font-weight:800; color:#f59e0b;'>{team1}</div>
                <div style='font-size:13px; color:#64748b; margin:4px 0;'>vs</div>
                <div style='font-size:20px; font-weight:800; color:#10b981;'>{team2}</div>
                <hr style='border-color: rgba(255,255,255,0.05); margin:12px 0;'/>
                <div style='font-size:12px; color:#94a3b8;'>
                    📍 {venue}<br/>
                    📆 {date}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Easy load button
            if st.button(f"Predict Match {i+1}", key=f"pred_btn_{i}"):
                st.session_state.pred_team1 = team1
                st.session_state.pred_team2 = team2
                st.session_state.pred_venue = venue
                st.rerun()
else:
    st.markdown("""
    <div style='
        background: linear-gradient(135deg, rgba(15,23,42,0.04), rgba(99,102,241,0.05));
        border: 1px solid rgba(99, 102, 241, 0.18);
        border-radius: 14px;
        padding: 18px 24px;
        text-align: center;
        margin-bottom: 8px;
    '>
        <div style='font-size: 22px; margin-bottom: 6px;'>🏁</div>
        <div style='font-size: 15px; font-weight: 700; color: #1e293b;'>IPL 2026 Season Concluded</div>
        <div style='font-size: 13px; color: #64748b; margin-top: 4px;'>
            No live matches — the tournament ended on <b>May 31, 2026</b>. Use the <b>Match Predictor</b> tab below to simulate any matchup!
        </div>
    </div>
    """, unsafe_allow_html=True)

# ─── 6b. DYNAMIC STADIUM & PITCH INSIGHTS FOR UPCOMING/LIVE MATCH ───────────────
active_venue = None
if live_data:
    active_venue = "HPCA Stadium Dharamshala"
elif upcoming_today:
    active_venue = standardise_venue_name(upcoming_today[0].get("venue", ""))

if active_venue:
    v_info = get_venue_details(active_venue)
    if v_info:
        st.markdown(f"""
        <div class='premium-card' style='
            background: linear-gradient(135deg, rgba(99, 102, 241, 0.05) 0%, rgba(99, 102, 241, 0.1) 100%) !important;
            border: 1px solid rgba(99, 102, 241, 0.3) !important;
            padding: 20px;
            margin-bottom: 24px;
        '>
            <h3 style='margin: 0 0 10px 0; font-size: 18px; color: #4f46e5 !important;'>🏟️ Featured Match Stadium & Pitch Insights</h3>
            <div style='display: flex; align-items: flex-start; gap: 15px;'>
                <span style='font-size: 36px; padding-top: 5px;'>{v_info['icon']}</span>
                <div>
                    <h4 style='margin: 0; font-size: 16px; color: #0f172a !important;'>{v_info['name']}</h4>
                    <p style='margin: 2px 0 8px 0; font-size: 12px; font-weight: 600; color: #64748b !important; text-transform: uppercase; letter-spacing: 0.5px;'>📍 Location: {v_info['place']}</p>
                    <p style='margin: 0; font-size: 14px; line-height: 1.6; color: #334155 !important;'>
                        <b>🏏 Pitch Behavior & Conditions:</b> {v_info['pitch']}
                    </p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# ─── 7. SIDEBAR CONTROLS & API KEYS ───────────────────────────────────────────
st.sidebar.header("🛠️ Config & API Credentials")

# Auto-refresh toggle
st.sidebar.markdown("### 🔄 Live Match Refresh")
auto_refresh = st.sidebar.toggle("Enable Auto-Refresh (30s)", value=False)
if auto_refresh:
    import time
    st.sidebar.success("Auto-refresh is ON. Page refreshes every 30 seconds.")

# Option to input Groq API Key for hybrid prediction
st.sidebar.markdown("### 🔑 API Keys")
groq_key = st.sidebar.text_input(
    "Groq API Key",
    value=os.getenv("GROQ_API_KEY", ""),
    type="password",
    help="Get a key from console.groq.com to activate Groq AI Overlay Mode!"
)
if groq_key:
    st.sidebar.markdown("""
    <div style='background: rgba(16,185,129,0.12); border: 1px solid rgba(16,185,129,0.3); border-radius: 8px; padding: 8px 12px; font-size: 12px; color: #10b981;'>
        ✅ Groq AI Active — Llama 3.3 70B Ready
    </div>
    """, unsafe_allow_html=True)

# Option to input Gemini API Key for hybrid prediction
gemini_key = st.sidebar.text_input(
    "Google Gemini API Key",
    value=os.getenv("GEMINI_API_KEY", ""),
    type="password",
    help="Get a FREE key from aistudio.google.com to activate AI Overlay Mode!"
)

# Option to input CricAPI key for scheduling
cric_key = st.sidebar.text_input(
    "CricAPI / Cricket API Key",
    value=os.getenv("CRICKET_API_KEY", ""),
    type="password",
    help="ApiKey to pull scheduling and live matches"
)

# Sidebar team color legend
st.sidebar.markdown("### 🏏 Team Colors Legend")
TEAM_COLORS = {
    "Chennai Super Kings": "#f7971e",
    "Mumbai Indians": "#004ba0",
    "Kolkata Knight Riders": "#3a225d",
    "Royal Challengers Bangalore": "#ec1c24",
    "Rajasthan Royals": "#ea1a85",
    "Punjab Kings": "#dd1f26",
    "Delhi Capitals": "#005ca9",
    "Sunrisers Hyderabad": "#ff822a",
    "Gujarat Titans": "#0b2240",
    "Lucknow Super Giants": "#0057e7",
}
for team, color in TEAM_COLORS.items():
    st.sidebar.markdown(
        f"<div style='display:flex; align-items:center; gap:8px; margin:3px 0;'>"
        f"<div style='width:14px;height:14px;border-radius:50%;background:{color};flex-shrink:0;'></div>"
        f"<span style='font-size:11px;color:#475569;'>{team}</span></div>",
        unsafe_allow_html=True
    )

# Dynamic GitHub settings panel
with st.sidebar.expander("🚀 Deploy Project to GitHub"):
    st.markdown("""
    Push this project to your GitHub repository in seconds!
    """)
    gh_username = st.text_input("GitHub Username", value=os.getenv("GITHUB_USERNAME", ""))
    gh_token = st.text_input("Personal Access Token (PAT)", type="password", value=os.getenv("GITHUB_TOKEN", ""))
    gh_repo = st.text_input("Repo Name", value="ipl_prediction_project")
    
    if st.button("Generate Setup Script"):
        if gh_username and gh_token:
            st.success("Config saved! Run this PowerShell script in the folder to push:")
            st.code(f"""
# 1. Open PowerShell in folder
# 2. Run this command:
$env:GITHUB_TOKEN="{gh_token}"
py -c "
import os
from git import Repo
repo_dir = '.'
repo = Repo(repo_dir)
origin = repo.remote(name='origin')
# Update origin URL with PAT
origin.set_url('https://{gh_username}:{gh_token}@github.com/{gh_username}/{gh_repo}.git')
repo.git.add(A=True)
repo.index.commit('Updated Prediction Model + Scrapers')
origin.push('main')
print('Successfully pushed to GitHub!')
"
            """, language="powershell")
        else:
            st.warning("Please enter your GitHub Username and Token!")

# ─── 8. MAIN prediction TABS ───────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 Season Standings & Scraped Stats", 
    "🤖 Match Predictor Engine", 
    "🏟️ Pitch & Venue Analytics", 
    "📊 H2H Team Form Analysis",
    "⚙️ Model Parameters & Config Guide"
])

# ─── TAB 1: SEASON STANDINGS & SCRAPED STATS ──────────────────────────────────
with tab1:
    st.header("📋 Points Table & Real-Time Stats")
    
    # Season Selector
    sel_season = st.selectbox("Select Season", [2026, 2025, 2024, 2023], index=0)
    
    # Try scraping points table using Cricbuzz scraper
    scraped_table = []
    if scrape_ipl_points_table:
        with st.spinner(f"Scraping IPL {sel_season} Standings from Cricbuzz..."):
            try:
                scraped_table = scrape_ipl_points_table(sel_season)
            except Exception:
                pass
                
    # Fallback to cache for 2026 season if scraper is blocked or empty
    if len(scraped_table) == 0 and load_scraped_cache and sel_season == 2026:
        cached_data = load_scraped_cache()
        if cached_data and "points_table" in cached_data:
            scraped_table = cached_data["points_table"]
                
    if len(scraped_table) > 0:
        points_df = pd.DataFrame(scraped_table)
        # ── Beautiful styled points table with plotly ──
        import plotly.graph_objects as go
        header_vals = list(points_df.columns)
        cell_vals = [points_df[c].tolist() for c in points_df.columns]
        
        # Color rows: top 4 qualify (playoff spots)
        row_colors = []
        for i in range(len(points_df)):
            if i < 2:
                row_colors.append("rgba(16, 185, 129, 0.12)")
            elif i < 4:
                row_colors.append("rgba(99, 102, 241, 0.08)")
            else:
                row_colors.append("rgba(255,255,255,0.6)")

        fig_table = go.Figure(data=[go.Table(
            columnwidth=[220] + [80] * (len(header_vals) - 1),
            header=dict(
                values=[f"<b>{v}</b>" for v in header_vals],
                fill_color="#4f46e5",
                font=dict(color="white", size=13, family="Outfit"),
                align="center",
                height=40
            ),
            cells=dict(
                values=cell_vals,
                fill_color=[row_colors * len(header_vals)],
                font=dict(color="#1e293b", size=13, family="Plus Jakarta Sans"),
                align="center",
                height=36
            )
        )])
        fig_table.update_layout(
            margin=dict(l=0, r=0, t=10, b=0),
            height=420
        )
        st.plotly_chart(fig_table, use_container_width=True)
        st.caption("🟢 Top 2 = direct Qualifier 1 | 🟣 3rd & 4th = Eliminator | ⬜ Eliminated")
    else:
        st.info("Scraper is cooling down. Showing historical points table from matches.csv...")
        if matches_df is not None:
            season_m = matches_df[matches_df["season"] == sel_season]
            teams = sorted(list(set(season_m["team1"].dropna().unique()) | set(season_m["team2"].dropna().unique())))
            table_data = []
            for team in teams:
                played = len(season_m[(season_m["team1"] == team) | (season_m["team2"] == team)])
                wins = len(season_m[season_m["winner"] == team])
                losses = played - wins
                pts = wins * 2
                table_data.append({"Team": team, "Played": played, "Wins": wins, "Losses": losses, "Points": pts})
            points_df = pd.DataFrame(table_data).sort_values("Points", ascending=False)
            st.dataframe(points_df, use_container_width=True)

    # ── Groq AI Playoff Race Narrative ──────────────────────────────────────────
    if groq_key and len(scraped_table) > 0:
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        col_ai_btn, col_ai_spacer = st.columns([2, 5])
        with col_ai_btn:
            run_ai_narrative = st.button("🧠 AI Playoff Race Analysis", type="primary", key="playoff_ai")
        if run_ai_narrative:
            with st.spinner("Groq AI is analyzing the playoff race..."):
                import json
                try:
                    table_summary = "\n".join([
                        f"{i+1}. {row.get('Team','?')} — {row.get('Pts','?')} pts ({row.get('W','?')}W/{row.get('L','?')}L), NRR: {row.get('NRR','?')}"
                        for i, row in enumerate(scraped_table)
                    ])
                    narrative_prompt = f"""You are an expert IPL cricket commentator and analyst. Analyze the IPL {sel_season} points table below and provide a sharp, engaging playoff race breakdown.

Points Table:
{table_summary}

Provide:
1. "headline": A punchy 1-line headline summarizing the playoff race drama (max 15 words)
2. "top2_analysis": Expert analysis of the top 2 teams (direct qualifiers) — form, strengths, 2-3 sentences
3. "playoff_race": Analysis of the battle for 3rd/4th spots — who's in, who's out and why, 2-3 sentences
4. "dark_horse": One team to watch out for as an upset pick with reasoning, 1-2 sentences
5. "prediction": Your bold prediction for the tournament winner and brief rationale, 1-2 sentences

Return as a valid JSON object with exactly these keys: headline, top2_analysis, playoff_race, dark_horse, prediction. Raw JSON only, no markdown."""

                    url = "https://api.groq.com/openai/v1/chat/completions"
                    payload = {
                        "model": "llama-3.3-70b-versatile",
                        "messages": [
                            {"role": "system", "content": "You are an expert IPL cricket analyst. Always respond with valid JSON only."},
                            {"role": "user", "content": narrative_prompt}
                        ],
                        "response_format": {"type": "json_object"},
                        "temperature": 0.7,
                        "max_tokens": 700
                    }
                    headers = {"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"}
                    resp = requests.post(url, headers=headers, json=payload, timeout=20)
                    
                    if resp.status_code == 200:
                        raw = resp.json()["choices"][0]["message"]["content"].strip()
                        if raw.startswith("```"):
                            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
                        ai_data = json.loads(raw)
                        st.markdown(f"""
                        <div class='premium-card' style='border-color: #818cf8; background: linear-gradient(135deg, rgba(99,102,241,0.07), rgba(139,92,246,0.05));'>
                            <div style='display:flex; align-items:center; gap:10px; margin-bottom:16px;'>
                                <span style='font-size:28px;'>🧠</span>
                                <div>
                                    <div style='font-size:10px; text-transform:uppercase; letter-spacing:1.5px; color:#818cf8; font-weight:800;'>GROQ AI — LLAMA 3.3 70B</div>
                                    <div style='font-size:18px; font-weight:800; color:#1e293b;'>{ai_data.get('headline', 'IPL 2026 Playoff Race Analysis')}</div>
                                </div>
                            </div>
                            <div style='display:grid; grid-template-columns:1fr 1fr; gap:14px;'>
                                <div style='background:rgba(16,185,129,0.08); border:1px solid rgba(16,185,129,0.2); border-radius:12px; padding:14px;'>
                                    <div style='font-size:11px; text-transform:uppercase; letter-spacing:1px; color:#10b981; font-weight:800; margin-bottom:8px;'>🏆 Top 2 Direct Qualifiers</div>
                                    <div style='font-size:13px; line-height:1.6; color:#334155;'>{ai_data.get('top2_analysis', '')}</div>
                                </div>
                                <div style='background:rgba(99,102,241,0.08); border:1px solid rgba(99,102,241,0.2); border-radius:12px; padding:14px;'>
                                    <div style='font-size:11px; text-transform:uppercase; letter-spacing:1px; color:#6366f1; font-weight:800; margin-bottom:8px;'>⚔️ Playoff Race Battle</div>
                                    <div style='font-size:13px; line-height:1.6; color:#334155;'>{ai_data.get('playoff_race', '')}</div>
                                </div>
                                <div style='background:rgba(245,158,11,0.08); border:1px solid rgba(245,158,11,0.2); border-radius:12px; padding:14px;'>
                                    <div style='font-size:11px; text-transform:uppercase; letter-spacing:1px; color:#f59e0b; font-weight:800; margin-bottom:8px;'>🌟 Dark Horse Pick</div>
                                    <div style='font-size:13px; line-height:1.6; color:#334155;'>{ai_data.get('dark_horse', '')}</div>
                                </div>
                                <div style='background:rgba(239,68,68,0.08); border:1px solid rgba(239,68,68,0.2); border-radius:12px; padding:14px;'>
                                    <div style='font-size:11px; text-transform:uppercase; letter-spacing:1px; color:#ef4444; font-weight:800; margin-bottom:8px;'>🏅 Championship Prediction</div>
                                    <div style='font-size:13px; line-height:1.6; color:#334155;'>{ai_data.get('prediction', '')}</div>
                                </div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        try:
                            err_detail = resp.json().get("error", {}).get("message", resp.text)
                        except Exception:
                            err_detail = resp.text
                        st.error(f"🚫 Groq API Error {resp.status_code}: {err_detail}")
                except Exception as e:
                    st.warning(f"AI Analysis Error: {str(e)}")
    elif not groq_key:
        st.info("💡 Add your **Groq API Key** in the sidebar to unlock AI Playoff Race Analysis!")

    # ── Visual Player Leaderboard Cards ─────────────────────────────────────────
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    col_l1, col_l2 = st.columns(2)
    
    # Helper to get team brand color
    def _team_color(team_name):
        tc = {
            "Chennai Super Kings": "#f7971e", "Mumbai Indians": "#004ba0",
            "Kolkata Knight Riders": "#3a225d", "Royal Challengers Bangalore": "#ec1c24",
            "Royal Challengers Bengaluru": "#ec1c24", "Rajasthan Royals": "#ea1a85",
            "Punjab Kings": "#dd1f26", "Delhi Capitals": "#005ca9",
            "Sunrisers Hyderabad": "#ff822a", "Gujarat Titans": "#1a6b3c",
            "Lucknow Super Giants": "#0057e7",
        }
        return tc.get(str(team_name).strip(), "#6366f1")

    with col_l1:
        st.markdown("""<div style='display:flex; align-items:center; gap:10px; margin-bottom:16px;'>
            <span style='font-size:28px;'>🟠</span>
            <div><div style='font-size:11px; text-transform:uppercase; letter-spacing:1.5px; color:#f59e0b; font-weight:800;'>ORANGE CAP RACE</div>
            <div style='font-size:20px; font-weight:800; color:#0f172a;'>Top Run Scorers</div></div></div>""", unsafe_allow_html=True)
        
        scraped_batsmen = []
        if scrape_top_batsmen:
            try:
                scraped_batsmen = scrape_top_batsmen(sel_season)
            except Exception:
                pass
        if len(scraped_batsmen) == 0 and load_scraped_cache and sel_season == 2026:
            cached_data = load_scraped_cache()
            if cached_data and "top_batsmen" in cached_data:
                scraped_batsmen = cached_data["top_batsmen"]

        if scraped_batsmen:
            max_runs = int(str(scraped_batsmen[0].get("Runs", 800)).replace(",", "")) if scraped_batsmen else 800
            rank_icons = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
            for i, p in enumerate(scraped_batsmen[:10]):
                runs_val = int(str(p.get("Runs", 0)).replace(",", ""))
                pct = (runs_val / max_runs) * 100
                tc = _team_color(p.get("Team", ""))
                badge = "🟠" if i == 0 else ""
                st.markdown(f"""
                <div style='background:rgba(255,255,255,0.8); border:1px solid rgba(245,158,11,{0.4 if i==0 else 0.15}); border-radius:14px; padding:14px 18px; margin-bottom:10px; position:relative; overflow:hidden;'>
                    <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;'>
                        <div style='display:flex; align-items:center; gap:10px;'>
                            <span style='font-size:20px; min-width:28px;'>{rank_icons[i]}</span>
                            <div>
                                <div style='font-weight:800; font-size:14px; color:#0f172a;'>{p.get('Player','?')} {badge}</div>
                                <div style='font-size:11px; color:#64748b; font-weight:600;'>
                                    <span style='background:{tc}22; color:{tc}; padding:2px 8px; border-radius:20px; font-weight:700;'>{p.get('Team','?')}</span>
                                </div>
                            </div>
                        </div>
                        <div style='text-align:right;'>
                            <div style='font-size:22px; font-weight:800; color:#f59e0b;'>{p.get('Runs','?')}</div>
                            <div style='font-size:10px; color:#94a3b8; font-weight:600;'>RUNS</div>
                        </div>
                    </div>
                    <div style='background:#f1f5f9; border-radius:8px; height:6px; overflow:hidden;'>
                        <div style='width:{pct:.1f}%; height:100%; background:linear-gradient(90deg, #f59e0b, #ef4444); border-radius:8px; transition: width 0.8s ease;'></div>
                    </div>
                    <div style='display:flex; justify-content:space-between; margin-top:6px;'>
                        <span style='font-size:10px; color:#94a3b8;'>Avg: {p.get('Avg','?')}</span>
                        <span style='font-size:10px; color:#94a3b8;'>SR: {p.get('SR','?')}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Orange Cap data loading...")

    with col_l2:
        st.markdown("""<div style='display:flex; align-items:center; gap:10px; margin-bottom:16px;'>
            <span style='font-size:28px;'>🟣</span>
            <div><div style='font-size:11px; text-transform:uppercase; letter-spacing:1.5px; color:#8b5cf6; font-weight:800;'>PURPLE CAP RACE</div>
            <div style='font-size:20px; font-weight:800; color:#0f172a;'>Top Wicket Takers</div></div></div>""", unsafe_allow_html=True)
        
        scraped_bowlers = []
        if scrape_top_bowlers:
            try:
                scraped_bowlers = scrape_top_bowlers(sel_season)
            except Exception:
                pass
        if len(scraped_bowlers) == 0 and load_scraped_cache and sel_season == 2026:
            cached_data = load_scraped_cache()
            if cached_data and "top_bowlers" in cached_data:
                scraped_bowlers = cached_data["top_bowlers"]

        if scraped_bowlers:
            max_wkts = int(str(scraped_bowlers[0].get("Wkts", 30)).replace(",", "")) if scraped_bowlers else 30
            rank_icons = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
            for i, p in enumerate(scraped_bowlers[:10]):
                wkts_val = int(str(p.get("Wkts", 0)).replace(",", ""))
                pct = (wkts_val / max_wkts) * 100
                tc = _team_color(p.get("Team", ""))
                badge = "🟣" if i == 0 else ""
                st.markdown(f"""
                <div style='background:rgba(255,255,255,0.8); border:1px solid rgba(139,92,246,{0.4 if i==0 else 0.15}); border-radius:14px; padding:14px 18px; margin-bottom:10px; position:relative; overflow:hidden;'>
                    <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;'>
                        <div style='display:flex; align-items:center; gap:10px;'>
                            <span style='font-size:20px; min-width:28px;'>{rank_icons[i]}</span>
                            <div>
                                <div style='font-weight:800; font-size:14px; color:#0f172a;'>{p.get('Player','?')} {badge}</div>
                                <div style='font-size:11px; color:#64748b; font-weight:600;'>
                                    <span style='background:{tc}22; color:{tc}; padding:2px 8px; border-radius:20px; font-weight:700;'>{p.get('Team','?')}</span>
                                </div>
                            </div>
                        </div>
                        <div style='text-align:right;'>
                            <div style='font-size:22px; font-weight:800; color:#8b5cf6;'>{p.get('Wkts','?')}</div>
                            <div style='font-size:10px; color:#94a3b8; font-weight:600;'>WICKETS</div>
                        </div>
                    </div>
                    <div style='background:#f1f5f9; border-radius:8px; height:6px; overflow:hidden;'>
                        <div style='width:{pct:.1f}%; height:100%; background:linear-gradient(90deg, #8b5cf6, #ec4899); border-radius:8px;'></div>
                    </div>
                    <div style='display:flex; justify-content:space-between; margin-top:6px;'>
                        <span style='font-size:10px; color:#94a3b8;'>Avg: {p.get('Avg','?')}</span>
                        <span style='font-size:10px; color:#94a3b8;'>Econ: {p.get('Econ','?')}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Purple Cap data loading...")

# ─── TAB 2: MATCH PREDICTOR ENGINE ────────────────────────────────────────────
with tab2:
    st.header("Match Predictor")
    
    if matches_df is None:
        st.error("Historical dataset matches.csv is missing or corrupt. Run update_cricsheet_data.py first!")
    else:
        # Build dropdown options
        all_teams = sorted(list(set(matches_df["team1"].dropna().unique()) | set(matches_df["team2"].dropna().unique())))
        all_venues = sorted(matches_df["venue"].dropna().unique())
        
        # Load presets if loaded from banner
        t1_idx = all_teams.index(st.session_state.pred_team1) if st.session_state.pred_team1 in all_teams else 0
        t2_idx = all_teams.index(st.session_state.pred_team2) if st.session_state.pred_team2 in all_teams else min(1, len(all_teams)-1)
        v_idx = all_venues.index(st.session_state.pred_venue) if st.session_state.pred_venue in all_venues else 0
        
        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1:
            sel_team1 = st.selectbox("Select Team 1 (Home/Bat First)", all_teams, index=t1_idx)
        with col_m2:
            sel_team2 = st.selectbox("Select Team 2 (Away/Chase First)", all_teams, index=t2_idx)
        with col_m3:
            sel_venue = st.selectbox("Select Venue", all_venues, index=v_idx)
            
        # Dynamic Pitch & Venue Report Card based on selected venue
        v_info = get_venue_details(sel_venue)
        if v_info:
            st.markdown(f"""
            <div class='premium-card' style='border-color: rgba(99, 102, 241, 0.35); background: rgba(99, 102, 241, 0.03); margin-top: 10px; margin-bottom: 20px;'>
                <div style='display: flex; align-items: center; gap: 12px;'>
                    <span style='font-size: 28px;'>{v_info['icon']}</span>
                    <div>
                        <h4 style='margin: 0; color: #4f46e5 !important; font-size: 15px;'>{v_info['name']} ({v_info['place']})</h4>
                        <p style='margin: 4px 0 0 0; font-size: 13px; line-height: 1.5; color: #475569 !important;'>
                            <b>🏟️ Pitch Behavior:</b> {v_info['pitch']}
                        </p>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        col_m4, col_m5 = st.columns(2)
        with col_m4:
            sel_toss_winner = st.selectbox("Who wins the Toss?", [sel_team1, sel_team2])
        with col_m5:
            sel_toss_decision = st.selectbox("Toss Decision", ["bat", "field"])
            
        if sel_team1 == sel_team2:
            st.warning("⚠️ Team 1 and Team 2 must be different teams!")
            run_allowed = False
        else:
            run_allowed = True
            
        if run_allowed:
            if st.button("🚀 Calculate Win Probabilities", type="primary"):
                # DYNAMIC FEATURE CALCULATIONS (UP TO CURRENT DATE)
                # 1. Form
                def compute_form(team, n=5):
                    t_matches = matches_df[(matches_df["team1"] == team) | (matches_df["team2"] == team)].tail(n)
                    if len(t_matches) == 0:
                        return 0.5
                    return (t_matches["winner"] == team).sum() / len(t_matches)
                
                t1_form = compute_form(sel_team1)
                t2_form = compute_form(sel_team2)
                
                # 2. H2H
                h2h_matches = matches_df[
                    ((matches_df["team1"] == sel_team1) & (matches_df["team2"] == sel_team2)) |
                    ((matches_df["team1"] == sel_team2) & (matches_df["team2"] == sel_team1))
                ]
                h2h_total = len(h2h_matches)
                h2h_t1_wins = (h2h_matches["winner"] == sel_team1).sum()
                h2h_t2_wins = (h2h_matches["winner"] == sel_team2).sum()
                h2h_t1_pct = (h2h_t1_wins / h2h_total) * 100 if h2h_total > 0 else 0.0
                h2h_t2_pct = (h2h_t2_wins / h2h_total) * 100 if h2h_total > 0 else 0.0
                h2h_val = h2h_t1_wins / h2h_total if h2h_total > 0 else 0.5
                
                # 3. Venue win rate
                def compute_venue_wr(team, venue):
                    v_matches = matches_df[
                        ((matches_df["team1"] == team) | (matches_df["team2"] == team)) &
                        (matches_df["venue"] == venue)
                    ]
                    if len(v_matches) == 0:
                        return 0.5
                    return (v_matches["winner"] == team).sum() / len(v_matches)
                
                v_t1 = compute_venue_wr(sel_team1, sel_venue)
                v_t2 = compute_venue_wr(sel_team2, sel_venue)
                
                # 4. Venue average score
                v_past = matches_df[matches_df["venue"] == sel_venue]["total_match_runs"].dropna()
                v_avg = v_past.mean() if len(v_past) > 0 else matches_df["total_match_runs"].mean()
                
                # 5. Toss Advantage
                toss_advantage = 1 if sel_toss_winner == sel_team1 else 0
                
                # 6. Season
                season_val = datetime.now().year
                
                # Create Feature Dictionary
                features = {
                    "team1_form": t1_form,
                    "team2_form": t2_form,
                    "head_to_head": h2h_val,
                    "venue_win_rate_t1": v_t1,
                    "venue_win_rate_t2": v_t2,
                    "venue_avg_score": v_avg,
                    "toss_advantage": toss_advantage,
                    "season": season_val
                }
                
                # Load XGBoost Model
                if not os.path.exists(MODEL_PATH):
                    st.error("xgb_model.pkl is missing. Please train the model first by running train_model.py!")
                else:
                    model = joblib.load(MODEL_PATH)
                    
                    # Predict probability
                    feat_df = pd.DataFrame([features])
                    
                    # Handle features ordering
                    model_features = model.get_booster().feature_names if hasattr(model, "get_booster") else feat_df.columns.tolist()
                    feat_df = feat_df[model_features]
                    
                    prob = model.predict_proba(feat_df)[0]  # [prob_class_0, prob_class_1]
                    
                    t1_prob = prob[1] * 100
                    t2_prob = prob[0] * 100
                    
                    # CSS styled Win Probability Bar
                    def get_team_color(name):
                        colors = {
                            "Chennai Super Kings": "#f7971e",
                            "Mumbai Indians": "#004ba0",
                            "Kolkata Knight Riders": "#3a225d",
                            "Royal Challengers Bangalore": "#ec1c24",
                            "Rajasthan Royals": "#ea1a85",
                            "Punjab Kings": "#dd1f26",
                            "Delhi Capitals": "#005ca9",
                            "Sunrisers Hyderabad": "#ff822a",
                            "Gujarat Titans": "#0b2240",
                            "Lucknow Super Giants": "#0057e7",
                        }
                        return colors.get(name, "#3b82f6")
                    
                    c1 = get_team_color(sel_team1)
                    c2 = get_team_color(sel_team2)
                    
                    # ── Win Probability banner ──
                    st.subheader("🔥 AI Win Probability Baseline")
                    st.markdown(f"""
                    <div class='bar-container'>
                        <div class='bar-team1' style='width: {t1_prob}%; background-color: {c1};'>
                            {sel_team1} ({t1_prob:.1f}%)
                        </div>
                        <div class='bar-team2' style='width: {t2_prob}%; background-color: {c2};'>
                            ({t2_prob:.1f}%) {sel_team2}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # ── Radar Chart: Matchup Factor Comparison ──
                    import plotly.graph_objects as _pgo
                    categories = ["Recent Form", "Head-to-Head", "Venue Win Rate", "Toss Advantage", "Season Experience"]
                    t1_season_exp = min((datetime.now().year - 2008) / 18 * 100, 100)
                    t2_season_exp = t1_season_exp
                    t1_radar = [t1_form * 100, h2h_t1_pct, v_t1 * 100, 100 if toss_advantage == 1 else 20, t1_season_exp]
                    t2_radar = [t2_form * 100, h2h_t2_pct, v_t2 * 100, 20 if toss_advantage == 1 else 100, t2_season_exp]

                    # Convert hex to rgba fill helper
                    def _hex_to_rgba(hex_c, alpha=0.15):
                        hex_c = hex_c.lstrip("#")
                        r, g, b = int(hex_c[0:2], 16), int(hex_c[2:4], 16), int(hex_c[4:6], 16)
                        return f"rgba({r},{g},{b},{alpha})"

                    fig_radar = _pgo.Figure()
                    fig_radar.add_trace(_pgo.Scatterpolar(
                        r=t1_radar, theta=categories, fill="toself",
                        name=sel_team1,
                        line=dict(color=c1, width=2),
                        fillcolor=_hex_to_rgba(c1) if c1.startswith("#") else c1
                    ))
                    fig_radar.add_trace(_pgo.Scatterpolar(
                        r=t2_radar, theta=categories, fill="toself",
                        name=sel_team2,
                        line=dict(color=c2, width=2),
                        fillcolor=_hex_to_rgba(c2) if c2.startswith("#") else c2
                    ))
                    fig_radar.update_layout(
                        polar=dict(
                            radialaxis=dict(visible=True, range=[0, 100], gridcolor="rgba(148,163,184,0.2)", color="#94a3b8"),
                            bgcolor="rgba(248,250,252,0.0)",
                            angularaxis=dict(gridcolor="rgba(148,163,184,0.2)")
                        ),
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        showlegend=True,
                        legend=dict(font=dict(size=12, color="#334155"), bgcolor="rgba(255,255,255,0.6)", borderwidth=0),
                        title=dict(text="📡 Matchup Factor Radar", font=dict(size=16, color="#0f172a", family="Outfit"), x=0.5),
                        height=380,
                        margin=dict(l=40, r=40, t=60, b=20)
                    )
                    st.plotly_chart(fig_radar, use_container_width=True)

                    # ── Factor breakdown cards ──
                    st.subheader("📊 Matchup Parameters & Features")
                    col_p1, col_p2, col_p3 = st.columns(3)
                    with col_p1:
                        t1_form_color = "#10b981" if t1_form > t2_form else "#ef4444"
                        t2_form_color = "#10b981" if t2_form >= t1_form else "#ef4444"
                        st.markdown(f"""
                        <div class='premium-card'>
                            <div class='metric-label'>Recent Form (Last 5)</div>
                            <div class='metric-value' style='color:{t1_form_color} !important;'>{sel_team1}: {t1_form*100:.0f}%</div>
                            <div class='metric-value' style='color:{t2_form_color} !important;'>{sel_team2}: {t2_form*100:.0f}%</div>
                            <div style='margin-top:8px; background:#f1f5f9; border-radius:6px; height:5px; overflow:hidden;'>
                                <div style='width:{t1_form*100:.0f}%; height:100%; background:{t1_form_color}; border-radius:6px;'></div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    with col_p2:
                        if h2h_total > 0:
                            st.markdown(f"""
                            <div class='premium-card'>
                                <div class='metric-label'>Head to Head ({h2h_total} matches)</div>
                                <div class='metric-value'>{sel_team1}: {h2h_t1_wins}W <span style='color:#94a3b8;font-size:13px;'>({h2h_t1_pct:.0f}%)</span></div>
                                <div class='metric-value'>{sel_team2}: {h2h_t2_wins}W <span style='color:#94a3b8;font-size:13px;'>({h2h_t2_pct:.0f}%)</span></div>
                                <div style='margin-top:8px; display:flex; height:5px; border-radius:6px; overflow:hidden;'>
                                    <div style='width:{h2h_t1_pct:.0f}%; background:{c1};'></div>
                                    <div style='width:{h2h_t2_pct:.0f}%; background:{c2};'></div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.markdown(f"""
                            <div class='premium-card'>
                                <div class='metric-label'>Head to Head</div>
                                <div class='metric-value' style='color:#94a3b8 !important; font-size:14px;'>No previous meetings<br/>between these teams</div>
                            </div>
                            """, unsafe_allow_html=True)
                    with col_p3:
                        v_leader = sel_team1 if v_t1 > v_t2 else sel_team2
                        st.markdown(f"""
                        <div class='premium-card'>
                            <div class='metric-label'>Venue Win Rate at {sel_venue.split(',')[0]}</div>
                            <div class='metric-value'>{sel_team1}: {v_t1*100:.0f}%</div>
                            <div class='metric-value'>{sel_team2}: {v_t2*100:.0f}%</div>
                            <div style='margin-top:6px; font-size:11px; color:#10b981; font-weight:700;'>🏟️ Venue Edge: {v_leader}</div>
                        </div>
                        """, unsafe_allow_html=True)

                    # ── Toss & Avg Score additional metrics ──
                    col_p4, col_p5 = st.columns(2)
                    with col_p4:
                        toss_winner_display = sel_toss_winner
                        st.markdown(f"""
                        <div class='premium-card'>
                            <div class='metric-label'>Toss Outcome</div>
                            <div class='metric-value'>🪙 {toss_winner_display} wins toss</div>
                            <div style='font-size:13px; color:#64748b; margin-top:4px;'>Decision: <b>{sel_toss_decision.upper()}</b></div>
                        </div>
                        """, unsafe_allow_html=True)
                    with col_p5:
                        st.markdown(f"""
                        <div class='premium-card'>
                            <div class='metric-label'>Venue Avg Match Score</div>
                            <div class='metric-value'>📊 {v_avg:.0f} total runs</div>
                            <div style='font-size:13px; color:#64748b; margin-top:4px;'>Based on {len(v_past)} historical matches</div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                    # Google Gemini or Groq AI Hybrid overlay
                    if groq_key or gemini_key:
                        if groq_key:
                            st.subheader("🤖 Groq AI Hybrid Prediction Overlay")
                            spinner_text = "Calling Groq (Llama 3.3)..."
                        else:
                            st.subheader("🤖 Google Gemini AI Hybrid Prediction Overlay")
                            spinner_text = "Calling Gemini 1.5 Flash..."
                            
                        with st.spinner(spinner_text):
                            prompt = f"""
                            You are a senior IPL cricket analyst and statistician.
                            You are analyzing an upcoming match between {sel_team1} and {sel_team2} at {sel_venue}.
                            
                            Historical statistics for this matchup:
                            - {sel_team1} recent form (last 5 matches win rate): {t1_form * 100:.1f}%
                            - {sel_team2} recent form (last 5 matches win rate): {t2_form * 100:.1f}%
                            - Historical Head-to-Head win rate for {sel_team1}: {h2h_val * 100:.1f}%
                            - {sel_team1} win rate at {sel_venue}: {v_t1 * 100:.1f}%
                            - {sel_team2} win rate at {sel_venue}: {v_t2 * 100:.1f}%
                            - Venue average score: {v_avg:.1f} runs
                            - Toss winner: {sel_toss_winner} (decided to {sel_toss_decision})
                            
                            Our XGBoost baseline model predicts:
                            - {sel_team1} win probability: {t1_prob:.1f}%
                            - {sel_team2} win probability: {t2_prob:.1f}%
                            
                            Please provide:
                            1. A hybrid probability overlay (incorporating recent squad changes, pitch conditions, and key match dynamics).
                            2. 2-3 sentences of expert analytical reasoning.
                            3. Identify 1 key player battle that will decide the match.
                            
                            Return the response as a valid JSON object only with these exact keys: "team1_hybrid_prob", "team2_hybrid_prob", "analysis", "player_battle". Do not include markdown code block formatting in the output, just raw JSON.
                            """
                            try:
                                if groq_key:
                                    # Use Groq API
                                    url = "https://api.groq.com/openai/v1/chat/completions"
                                    payload = {
                                        "model": "llama-3.3-70b-versatile",
                                        "messages": [
                                            {"role": "system", "content": "You are a senior IPL cricket analyst. Always respond with valid JSON only."},
                                            {"role": "user", "content": prompt}
                                        ],
                                        "response_format": {"type": "json_object"},
                                        "temperature": 0.7,
                                        "max_tokens": 500
                                    }
                                    headers = {
                                        "Authorization": f"Bearer {groq_key}",
                                        "Content-Type": "application/json"
                                    }
                                    resp = requests.post(url, headers=headers, json=payload, timeout=12)
                                    
                                    if resp.status_code == 200:
                                        resp_data = resp.json()
                                        raw_text = resp_data["choices"][0]["message"]["content"].strip()
                                    else:
                                        raw_text = None
                                        st.warning(f"Groq API Error: {resp.text}. Using baseline XGBoost model.")
                                else:
                                    # Use Gemini API
                                    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
                                    payload = {"contents": [{"parts": [{"text": prompt}]}]}
                                    headers = {"Content-Type": "application/json"}
                                    resp = requests.post(url, headers=headers, json=payload, timeout=12)
                                    
                                    if resp.status_code == 200:
                                        resp_data = resp.json()
                                        raw_text = resp_data["candidates"][0]["content"]["parts"][0]["text"].strip()
                                    else:
                                        raw_text = None
                                        st.warning("Could not reach Gemini API. Using baseline XGBoost model.")
                                
                                if raw_text:
                                    # Clean json markers if included
                                    if raw_text.startswith("```json"):
                                        raw_text = raw_text.replace("```json", "", 1)
                                    if raw_text.endswith("```"):
                                        raw_text = raw_text[:-3]
                                    raw_text = raw_text.strip()
                                    
                                    import json
                                    ai_res = json.loads(raw_text)
                                    
                                    ai_t1 = float(ai_res.get("team1_hybrid_prob", t1_prob))
                                    ai_t2 = float(ai_res.get("team2_hybrid_prob", t2_prob))
                                    
                                    source_label = "Groq Llama 3.3" if groq_key else "Gemini AI"
                                    
                                    st.markdown(f"""
                                    <div class='premium-card' style='border-color: #818cf8; background: rgba(99, 102, 241, 0.05);'>
                                        <h4 style='color:#818cf8; margin-top:0;'>✨ {source_label} Hybrid Score</h4>
                                        <div class='bar-container'>
                                            <div class='bar-team1' style='width: {ai_t1}%; background-color: {c1};'>
                                                {sel_team1} ({ai_t1:.1f}%)
                                            </div>
                                            <div class='bar-team2' style='width: {ai_t2}%; background-color: {c2};'>
                                                ({ai_t2:.1f}%) {sel_team2}
                                            </div>
                                        </div>
                                        <p style='margin: 12px 0 6px 0; font-size:14px; line-height:1.6;'><b>🧠 Analysis:</b> {ai_res.get("analysis", "")}</p>
                                        <p style='margin: 0; font-size:14px; line-height:1.6;'><b>⚔️ Key Battle:</b> {ai_res.get("player_battle", "")}</p>
                                    </div>
                                    """, unsafe_allow_html=True)
                            except Exception as e:
                                st.warning(f"AI overlay error: {str(e)}")

# ─── TAB 3: PITCH & VENUE ANALYTICS ───────────────────────────────────────────
with tab3:
    st.header("🏟️ Stadium & Venue Analytics")
    
    if matches_df is not None:
        venue_counts = matches_df["venue"].value_counts().reset_index()
        venue_counts.columns = ["Venue", "Matches Played"]
        
        # High score venue
        venue_runs = matches_df.groupby("venue")["total_match_runs"].mean().reset_index()
        venue_runs.columns = ["Venue", "Avg Runs per Match"]
        venue_runs = venue_runs.sort_values("Avg Runs per Match", ascending=False)
        
        col_v1, col_v2 = st.columns([2, 3])
        with col_v1:
            st.subheader("📌 Most Frequented Venues")
            st.dataframe(venue_counts, use_container_width=True)
        with col_v2:
            st.subheader("🔥 Average Match Runs by Venue")
            fig_v = px.bar(venue_runs.head(10), x="Venue", y="Avg Runs per Match", color="Avg Runs per Match",
                           color_continuous_scale="Viridis", title="Top 10 Highest Scoring IPL Grounds")
            st.plotly_chart(fig_v, use_container_width=True)

# ─── TAB 4: H2H TEAM FORM ANALYSIS ────────────────────────────────────────────
with tab4:
    st.header("📊 Detailed Team Form & Historical Trends")
    if matches_df is not None:
        sel_team_a = st.selectbox("Select Team", all_teams, index=0)
        
        team_m = matches_df[(matches_df["team1"] == sel_team_a) | (matches_df["team2"] == sel_team_a)]
        
        t_wins = (team_m["winner"] == sel_team_a).sum()
        t_played = len(team_m)
        t_losses = t_played - t_wins
        
        st.markdown(f"### {sel_team_a} Overview")
        col_t1, col_t2, col_t3 = st.columns(3)
        col_t1.metric("Matches Played", t_played)
        col_t2.metric("Wins", t_wins)
        col_t3.metric("Win %", f"{(t_wins/t_played)*100:.1f}%" if t_played > 0 else "0%")
        
        # Recent Form
        recent_m = team_m.tail(10)
        results = []
        for idx, row in recent_m.iterrows():
            opp = row["team2"] if row["team1"] == sel_team_a else row["team1"]
            res = "🏆 Won" if row["winner"] == sel_team_a else "❌ Lost"
            if row["winner"] in ("No Result", "tied"):
                res = "➖ Tied/No Result"
            results.append({
                "Date": row["date"].strftime("%Y-%m-%d") if not pd.isna(row["date"]) else "Unknown",
                "Opponent": opp,
                "Result": res,
                "Venue": row["venue"]
            })
            
        st.subheader(f"Recent 10 Matches Form")
        st.table(pd.DataFrame(results))

# ─── TAB 5: DEVELOPER CONFIG & GITHUB GUIDE ──────────────────────────────────
with tab5:
    st.header("⚙️ Parameters and Config Guide")
    st.markdown("""
    Here is a full breakdown of the features and parameters used in the **IPL Prediction System**, along with Git installation guidelines.
    """)
    
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.markdown("""
        ### 📋 Features and Parameters
        
        | Feature Parameter | Type | Description |
        |-------------------|------|-------------|
        | `team1_form` | `float` | Win rate of Team 1 in their last 5 matches |
        | `team2_form` | `float` | Win rate of Team 2 in their last 5 matches |
        | `head_to_head` | `float` | Team 1's historical win % against Team 2 |
        | `venue_win_rate_t1` | `float` | Team 1's win rate at this stadium |
        | `venue_win_rate_t2` | `float` | Team 2's win rate at this stadium |
        | `venue_avg_score` | `float` | Average total match runs at this ground |
        | `toss_advantage` | `binary` | `1` if Team 1 won the toss, `0` otherwise |
        | `season` | `int` | The year of the match (e.g. 2026) |
        """)
    with col_g2:
        st.markdown("""
        ### 📂 Pushing to GitHub
        
        If you don't have Git installed, we've set up **GitPython** (a pure python git wrapper) so you can push your changes without needing to install Git!
        
        **Instructions:**
        1. Create a Personal Access Token (PAT) on GitHub:
           - Go to github.com ➜ Settings ➜ Developer Settings ➜ Personal Access Tokens.
           - Generate a token with the **`repo`** scope.
        2. Set up your `.env` variables:
           ```env
           GITHUB_USERNAME=your_username
           GITHUB_TOKEN=ghp_your_personal_token
           ```
        3. Go to the sidebar on this dashboard, fill in your credentials, and click **"Generate Setup Script"** to push to your repository!
        """)

# ─── AUTO-REFRESH LOGIC ─────────────────────────────────────────────────────────
if auto_refresh:
    import time
    st.sidebar.markdown(
        f"<div style='font-size:11px;color:#64748b;text-align:center;margin-top:6px;'>Next refresh in <b>30s</b></div>",
        unsafe_allow_html=True
    )
    time.sleep(30)
    st.rerun()
