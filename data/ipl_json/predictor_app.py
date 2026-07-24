import streamlit as st
import pandas as pd
import joblib
import requests
import os
import sys
from datetime import datetime

# ─── 1. FILE PATHS & SETUP ───────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MATCHES_PATH = os.path.join(BASE_DIR, "matches.csv")
DELIV_PATH = os.path.join(BASE_DIR, "deliveries.csv")
MODEL_PATH = os.path.join(BASE_DIR, "xgb_model.pkl")

# Add parent directory to sys.path to dynamically import api.py & scraper.py
sys.path.append(os.path.abspath(os.path.join(BASE_DIR, "..", "..")))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".env"))

# ─── 2. TEAM & VENUE STANDARDISATION ──────────────────────────────────────────
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
st.set_page_config(page_title="IPL AI Match Predictor Engine", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700;800&family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');
    
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
    
    .stApp p, .stApp label, .stApp span, .stApp li, .stApp td {
        color: #334155 !important;
    }
    
    div.block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    .premium-card {
        background: rgba(255, 255, 255, 0.75) !important;
        border: 1px solid rgba(99, 102, 241, 0.15) !important;
        border-radius: 20px;
        padding: 24px;
        backdrop-filter: blur(20px) saturate(180%);
        box-shadow: 0 10px 25px rgba(148, 163, 184, 0.12);
        margin-bottom: 24px;
        transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1) !important;
    }
    
    .premium-card:hover {
        border-color: rgba(99, 102, 241, 0.45) !important;
        transform: translateY(-4px);
        box-shadow: 0 16px 35px rgba(99, 102, 241, 0.15) !important;
    }
    
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
        text-shadow: 0 1px 3px rgba(0,0,0,0.5);
    }
    
    .metric-value {
        font-size: 18px;
        font-weight: 700;
        color: #4f46e5 !important;
        line-height: 1.6;
        margin-top: 10px;
    }
    
    .metric-label {
        font-size: 12px;
        color: #64748b !important;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        font-weight: 800;
    }

    div[data-baseweb="select"] > div {
        background-color: #ffffff !important;
        color: #0f172a !important;
        border: 1px solid rgba(203, 213, 225, 0.8) !important;
        border-radius: 12px !important;
    }
    
    input {
        background-color: #ffffff !important;
        color: #0f172a !important;
        border-radius: 12px !important;
        border: 1px solid rgba(203, 213, 225, 0.8) !important;
    }
    
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
    }
</style>
""", unsafe_allow_html=True)

# ─── 4. LOAD DATA ─────────────────────────────────────────────────────────────
@st.cache_data
def load_historical_data():
    if not os.path.exists(MATCHES_PATH) or not os.path.exists(DELIV_PATH):
        return None, None
    m_df = pd.read_csv(MATCHES_PATH)
    d_df = pd.read_csv(DELIV_PATH)
    
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

if matches_df is not None and deliveries_df is not None:
    deliveries_df["match_id"] = deliveries_df["match_id"].astype(str)
    matches_df["match_id"] = matches_df["match_id"].astype(str)
    
    if "total_match_runs" not in matches_df.columns:
        match_runs = deliveries_df.groupby("match_id")["total_runs"].sum().reset_index()
        match_runs.columns = ["match_id", "total_match_runs"]
        matches_df = matches_df.merge(match_runs, on="match_id", how="left")

# Page Header
st.title("🤖 IPL Match Predictor Engine")
st.markdown("---")

# ─── 5. SIDEBAR CONFIG & CREDENTIALS ──────────────────────────────────────────
st.sidebar.header("🛠️ API Config & Keys")

groq_key = st.sidebar.text_input(
    "Groq API Key",
    value=os.getenv("GROQ_API_KEY", ""),
    type="password",
    help="Activate Groq AI Overlay Mode using Llama 3.3!"
)

gemini_key = st.sidebar.text_input(
    "Google Gemini API Key",
    value=os.getenv("GEMINI_API_KEY", ""),
    type="password",
    help="Activate Google Gemini AI Overlay Mode!"
)

# ─── 6. PREDICTOR LOGIC ───────────────────────────────────────────────────────
if matches_df is None:
    st.error("Historical dataset matches.csv is missing. Please check file path!")
else:
    all_teams = sorted(list(set(matches_df["team1"].dropna().unique()) | set(matches_df["team2"].dropna().unique())))
    all_venues = sorted(matches_df["venue"].dropna().unique())
    
    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        sel_team1 = st.selectbox("Select Team 1 (Home/Bat First)", all_teams, index=0)
    with col_m2:
        sel_team2 = st.selectbox("Select Team 2 (Away/Chase First)", all_teams, index=min(1, len(all_teams)-1))
    with col_m3:
        sel_venue = st.selectbox("Select Venue", all_venues, index=0)
        
    # Dynamic Pitch & Venue Report Card
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
            # Compute Form
            def compute_form(team, n=5):
                t_matches = matches_df[(matches_df["team1"] == team) | (matches_df["team2"] == team)].tail(n)
                if len(t_matches) == 0:
                    return 0.5
                return (t_matches["winner"] == team).sum() / len(t_matches)
            
            t1_form = compute_form(sel_team1)
            t2_form = compute_form(sel_team2)
            
            # Compute H2H
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
            
            # Compute Venue Win Rate
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
            
            # Venue average score
            v_past = matches_df[matches_df["venue"] == sel_venue]["total_match_runs"].dropna()
            v_avg = v_past.mean() if len(v_past) > 0 else matches_df["total_match_runs"].mean()
            
            toss_advantage = 1 if sel_toss_winner == sel_team1 else 0
            season_val = datetime.now().year
            
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
            
            if not os.path.exists(MODEL_PATH):
                st.error("xgb_model.pkl is missing. Please build/train the model first!")
            else:
                model = joblib.load(MODEL_PATH)
                feat_df = pd.DataFrame([features])
                model_features = model.get_booster().feature_names if hasattr(model, "get_booster") else feat_df.columns.tolist()
                feat_df = feat_df[model_features]
                
                prob = model.predict_proba(feat_df)[0]
                t1_prob = prob[1] * 100
                t2_prob = prob[0] * 100
                
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
                
                st.subheader("📊 Matchup Parameters & Features")
                col_p1, col_p2, col_p3 = st.columns(3)
                with col_p1:
                    st.markdown(f"""
                    <div class='premium-card'>
                        <div class='metric-label'>Form (Last 5)</div>
                        <div class='metric-value'>{sel_team1}: {t1_form*100:.0f}%<br/>{sel_team2}: {t2_form*100:.0f}%</div>
                    </div>
                    """, unsafe_allow_html=True)
                with col_p2:
                    if h2h_total > 0:
                        st.markdown(f"""
                        <div class='premium-card'>
                            <div class='metric-label'>Head to Head</div>
                            <div class='metric-value'>
                                {sel_team1}: {h2h_t1_wins} wins ({h2h_t1_pct:.0f}%)<br/>
                                {sel_team2}: {h2h_t2_wins} wins ({h2h_t2_pct:.0f}%)<br/>
                                <span style='font-size:12px;color:#94a3b8;'>Total Matches: {h2h_total}</span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div class='premium-card'>
                            <div class='metric-label'>Head to Head</div>
                            <div class='metric-value'>No past matches</div>
                        </div>
                        """, unsafe_allow_html=True)
                with col_p3:
                    st.markdown(f"""
                    <div class='premium-card'>
                        <div class='metric-label'>Venue Win Rate</div>
                        <div class='metric-value'>{sel_team1}: {v_t1*100:.0f}%<br/>{sel_team2}: {v_t2*100:.0f}%</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Groq / Gemini AI hybrid prediction overlay
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
                        
                        Historical statistics:
                        - {sel_team1} recent form (last 5 wins): {t1_form * 100:.1f}%
                        - {sel_team2} recent form (last 5 wins): {t2_form * 100:.1f}%
                        - Historical H2H: {h2h_val * 100:.1f}%
                        - {sel_team1} venue win rate: {v_t1 * 100:.1f}%
                        - {sel_team2} venue win rate: {v_t2 * 100:.1f}%
                        - Venue average score: {v_avg:.1f} runs
                        - Toss winner: {sel_toss_winner} (decided to {sel_toss_decision})
                        
                        Baseline Win Probability:
                        - {sel_team1} win probability: {t1_prob:.1f}%
                        - {sel_team2} win probability: {t2_prob:.1f}%
                        
                        Provide:
                        1. A hybrid probability overlay (incorporating recent squad changes, pitch conditions, and key match dynamics).
                        2. 2-3 sentences of expert analytical reasoning.
                        3. Identify 1 key player battle.
                        
                        Return the response as a valid JSON object only with these exact keys: "team1_hybrid_prob", "team2_hybrid_prob", "analysis", "player_battle". Do not include markdown code block formatting, return raw JSON.
                        """
                        try:
                            if groq_key:
                                url = "https://api.groq.com/openai/v1/chat/completions"
                                payload = {
                                    "model": "llama-3.3-70b-specdec",
                                    "messages": [{"role": "user", "content": prompt}],
                                    "response_format": {"type": "json_object"}
                                }
                                headers = {
                                    "Authorization": f"Bearer {groq_key}",
                                    "Content-Type": "application/json"
                                }
                                resp = requests.post(url, headers=headers, json=payload, timeout=12)
                                if resp.status_code == 200:
                                    raw_text = resp.json()["choices"][0]["message"]["content"].strip()
                                else:
                                    raw_text = None
                                    st.warning(f"Groq API Error: {resp.text}")
                            else:
                                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
                                payload = {"contents": [{"parts": [{"text": prompt}]}]}
                                headers = {"Content-Type": "application/json"}
                                resp = requests.post(url, headers=headers, json=payload, timeout=12)
                                if resp.status_code == 200:
                                    raw_text = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                                else:
                                    raw_text = None
                                    st.warning("Could not reach Gemini API.")
                            
                            if raw_text:
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
