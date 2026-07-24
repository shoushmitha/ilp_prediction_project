# 🏏 IPL Championship Prediction System

[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.35-red?logo=streamlit)](https://streamlit.io)
[![CricAPI](https://img.shields.io/badge/CricAPI-Live-green)](https://cricapi.com)
[![Chrome Extension](https://img.shields.io/badge/Chrome-Extension-yellow?logo=googlechrome)](./chrome_extension/)
[![License](https://img.shields.io/badge/License-MIT-lightgrey)](./LICENSE)

> A full-stack IPL analytics dashboard with **live match scores**, **web scraping**, **ML-based win prediction**, and a **Chrome extension** for real-time notifications — all powered by CricAPI + BeautifulSoup.

---

## 📸 Screenshots

| Dashboard | Chrome Extension |
|-----------|-----------------|
| Live scores, points table, win % charts | Popup with live score + win probability |

---

## 🚀 Features

- 🔴 **Live match scores** via [CricAPI](https://cricapi.com) with automatic fallback to web scraping
- 📊 **Interactive Streamlit dashboard** — points table, venue analysis, playoff scenarios
- 🤖 **IPL 2026 Champion prediction** using historical match data (2008–2025)
- 🕷️ **Web scraper** for ESPNCricinfo & Cricbuzz (scores, stats, schedule)
- 🧩 **Chrome Extension** — live badge, win probability bar, OS notifications
- 📁 JSON match data from Cricsheet (2008–2025, 900+ matches)

---

## 📁 Project Structure

```
ipl_prediction_project/
├── api.py                    # CricAPI wrapper (live matches, series, players)
├── scraper.py                # Web scraper (ESPNCricinfo, Cricbuzz)
├── requirements.txt          # Python dependencies
├── .env                      # API keys (NOT committed to GitHub)
├── .gitignore
│
├── data/
│   ├── ipl_json/
│   │   ├── matches.csv       # Processed match data (2008–2025)
│   │   ├── deliveries.csv    # Ball-by-ball data
│   │   ├── streamlit_app.py  # Main dashboard app
│   │   └── *.json            # Raw Cricsheet JSON files
│   └── scraped_cache.json    # Cached scraper output
│
└── chrome_extension/
    ├── manifest.json         # Extension config (Manifest V3)
    ├── popup.html            # Extension popup UI
    ├── popup.js              # Popup logic — CricAPI + Streamlit bridge
    ├── background.js         # Service worker — polling + notifications
    ├── options.html          # Settings page (API key input)
    ├── options.js            # Settings logic
    └── icons/                # Extension icons (16, 48, 128px)
```

---

## ⚙️ Setup & Installation

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/ipl_prediction_project.git
cd ipl_prediction_project
```

### 2. Create Virtual Environment & Install Dependencies

```bash
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

pip install -r requirements.txt
```

### 3. Configure API Key

Create a `.env` file in the project root:

```env
CRICKET_API_KEY=your_cricapi_key_here
```

> 🔑 Get your free API key at [cricapi.com](https://cricapi.com) — free tier gives **100 calls/day**.

### 4. Run the Streamlit Dashboard

```bash
streamlit run data/ipl_json/streamlit_app.py
```

Open `http://localhost:8501` in your browser.

### 5. Run the Web Scraper (Optional)

```bash
python scraper.py
```

Scraped data is cached in `data/scraped_cache.json`.

---

## 🧩 Chrome Extension Setup

### Load as Unpacked Extension

1. Open Chrome → `chrome://extensions/`
2. Enable **Developer Mode** (top-right toggle)
3. Click **Load unpacked**
4. Select the `chrome_extension/` folder
5. The 🏏 icon appears in your Chrome toolbar

### Set Your API Key in the Extension

1. Click the extension icon → settings ⚙️
2. Paste your **CricAPI key**
3. Click **Save** — the extension now polls live data every minute

### How the Extension Works

| Feature | Description |
|---------|-------------|
| **Live Score** | Fetches from CricAPI every 60 seconds |
| **Win Probability** | Calculated from current innings scores |
| **OS Notifications** | Fires when match status changes |
| **Dashboard Button** | Opens `localhost:8501` in a new tab |
| **Fallback** | Pings local Streamlit if CricAPI quota exceeded |

---

## 📡 API Parameters Reference

### CricAPI — `api.py`

| Function | Endpoint | Parameters |
|----------|----------|------------|
| `get_live_matches(offset)` | `/currentMatches` | `apikey`, `offset` (default 0) |
| `get_series_list(offset)` | `/series` | `apikey`, `offset` |
| `get_match_info(match_id)` | `/match_info` | `apikey`, `id` |
| `get_player_info(name)` | `/players` | `apikey`, `search` |

### Scraper — `scraper.py`

| Function | Source | Parameters |
|----------|--------|------------|
| `scrape_live_ipl_score()` | ESPNCricinfo | none |
| `scrape_ipl_points_table(year)` | Cricbuzz | `year` (int, default 2025) |
| `scrape_ipl_schedule(year)` | ESPNCricinfo | `year` (int, default 2025) |
| `scrape_top_batsmen(year)` | ESPNCricinfo | `year` (int, default 2025) |
| `scrape_top_bowlers(year)` | ESPNCricinfo | `year` (int, default 2025) |
| `save_scraped_cache(data, filename)` | Local JSON | `data` dict, `filename` str |
| `load_scraped_cache(filename)` | Local JSON | `filename` str |

---

## 🤖 ML Prediction Model

The championship predictor uses:
- **Historical win rate** (2008–2025, 900+ matches)
- **Current season points** as feature weight
- **NRR (Net Run Rate)** as tiebreaker
- **Venue advantage** from venue analysis dashboard

---

## 🔄 Data Sources

| Source | Type | Coverage |
|--------|------|----------|
| [Cricsheet](https://cricsheet.org) | JSON ball-by-ball | IPL 2008–2024 |
| [CricAPI](https://cricapi.com) | REST API | Live & current |
| [ESPNCricinfo](https://espncricinfo.com) | Scraper | Live, stats, schedule |
| [Cricbuzz](https://cricbuzz.com) | Scraper | Points table |

---

## 📤 Adding to GitHub

```bash
# Initialize repo (if not already)
git init
git remote add origin https://github.com/YOUR_USERNAME/ipl_prediction_project.git

# Stage files (JSON data excluded via .gitignore)
git add .
git commit -m "🏏 Initial commit: IPL Prediction Dashboard + Chrome Extension"
git branch -M main
git push -u origin main
```

> ⚠️ **Never commit your `.env` file.** It's excluded by `.gitignore`.

---

## 🛠️ Troubleshooting

| Problem | Solution |
|---------|----------|
| `No live matches` | IPL season may be over; fallback mock data shown |
| `CricAPI quota exceeded` | Scraper auto-activates as fallback |
| `Extension shows no data` | Check API key in extension settings |
| `Streamlit not loading` | Run `streamlit run data/ipl_json/streamlit_app.py` |
| `CSV file not found` | Ensure `matches.csv` & `deliveries.csv` are in `data/ipl_json/` |

---

## 📜 License

MIT © 2025 — Free to use, modify, and distribute.