/**
 * popup.js — IPL Live Predictor Chrome Extension
 * Connects to localhost:8501 (Streamlit) and CricAPI for live data.
 */

// ── Config ──────────────────────────────────────────────────────────
const CONFIG = {
  STREAMLIT_URL:  "http://localhost:8501",
  CRICAPI_URL:    "https://api.cricapi.com/v1/currentMatches",
  // API key is stored in chrome.storage so it never appears in plain text
  REFRESH_INTERVAL_MS: 60000, // 1 minute auto-refresh
};

// ── DOM Helpers ─────────────────────────────────────────────────────
const $  = (id) => document.getElementById(id);
const show = (id) => { const el = $(id); if (el) el.style.display = ""; };
const hide = (id) => { const el = $(id); if (el) el.style.display = "none"; };
const setText = (id, txt) => { const el = $(id); if (el) el.textContent = txt; };

// ── Entry Point ─────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", async () => {
  updateTimestamp();
  await refreshData();

  // Auto-refresh every minute
  setInterval(async () => {
    updateTimestamp();
    await refreshData();
  }, CONFIG.REFRESH_INTERVAL_MS);
});

// ── Main Refresh ─────────────────────────────────────────────────────
async function refreshData() {
  showLoadingCard();
  hide("error-box");
  hide("stats-grid");
  hide("prediction-section");

  try {
    // 1. Fetch API key from chrome.storage
    const apiKey = await getStoredApiKey();

    // 2. Try CricAPI first
    let matchData = null;
    if (apiKey) {
      matchData = await fetchFromCricAPI(apiKey);
    }

    // 3. Fallback: ping local Streamlit for cached data
    if (!matchData) {
      matchData = await fetchFromLocalStreamlit();
    }

    // 4. Render what we have
    if (matchData) {
      renderMatchCard(matchData);
      renderStats(matchData);
      renderPredictionBar(matchData);
      show("stats-grid");
      show("prediction-section");
    } else {
      showFallbackCard();
    }
  } catch (err) {
    showError(`Connection error: ${err.message}`);
  }
}

// ── CricAPI Fetch ────────────────────────────────────────────────────
async function fetchFromCricAPI(apiKey) {
  try {
    const res = await fetch(
      `${CONFIG.CRICAPI_URL}?apikey=${apiKey}&offset=0`,
      { method: "GET" }
    );
    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    const json = await res.json();
    if (json.status !== "success" || !json.data?.length) return null;

    // Filter for IPL matches
    const iplMatches = json.data.filter(
      (m) => m.name?.includes("IPL") || m.name?.includes("Indian Premier League")
    );
    const match = iplMatches.length ? iplMatches[0] : json.data[0];

    // Format score
    const scoreArr = match.score || [];
    const scoreParts = scoreArr.map(
      (s) => `${s.inning || ""}: ${s.r ?? 0}/${s.w ?? 0} (${s.o ?? 0} ov)`
    );
    const scoreStr = scoreParts.join(" | ") || "Score N/A";

    return {
      match_title: match.name,
      score:       scoreStr,
      status:      match.status,
      source:      "CricAPI",
      team1:       (match.teams || [])[0] || "Team A",
      team2:       (match.teams || [])[1] || "Team B",
      win_prob:    estimateWinProb(scoreArr),
      total_matches: json.data.length,
      avg_score:   "--",
    };
  } catch (e) {
    console.warn("[CricAPI] Failed:", e.message);
    return null;
  }
}

// ── Streamlit Local Fetch ─────────────────────────────────────────────
async function fetchFromLocalStreamlit() {
  try {
    // Hit Streamlit health endpoint to check if server is running
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 3000);
    const res = await fetch(CONFIG.STREAMLIT_URL, {
      signal: controller.signal,
    });
    clearTimeout(timeout);

    if (res.ok) {
      // Server is up — return a generic "dashboard is live" payload
      return {
        match_title: "IPL Dashboard is Running",
        score:       "Open full dashboard for live data",
        status:      "Streamlit server active on localhost:8501",
        source:      "Local Streamlit",
        team1:       "—",
        team2:       "—",
        win_prob:    50,
        total_matches: "—",
        avg_score:   "—",
      };
    }
    return null;
  } catch {
    return null;
  }
}

// ── Render Functions ─────────────────────────────────────────────────
function renderMatchCard(data) {
  const card = $("match-card");
  card.innerHTML = `
    <div class="match-title" title="${data.match_title}">${data.match_title}</div>
    <div class="match-score">${data.score}</div>
    <div class="match-status">${data.status}</div>
    <div style="font-size:10px;color:#666;margin-top:6px;">Source: ${data.source}</div>
  `;
}

function renderStats(data) {
  setText("stat-total-matches", data.total_matches ?? "—");
  setText("stat-top-team",      data.team1 ?? "—");
  setText("stat-avg-score",     data.avg_score ?? "—");
  setText("stat-season",        "2025");
}

function renderPredictionBar(data) {
  const prob = Math.max(5, Math.min(95, data.win_prob ?? 50));
  const bar  = $("pred-bar");
  if (bar) {
    bar.style.width = `${prob}%`;
    setText("pred-team1-pct",  `${prob}%`);
    setText("pred-team1-name", data.team1 || "Team A");
    setText("pred-team2-name", data.team2 || "Team B");
  }
}

function showLoadingCard() {
  const card = $("match-card");
  if (card) {
    card.innerHTML = `
      <div class="loading">
        <div class="spinner"></div>
        Fetching live data…
      </div>`;
  }
}

function showFallbackCard() {
  const card = $("match-card");
  if (card) {
    card.innerHTML = `
      <div class="match-title">No live IPL match right now</div>
      <div class="match-status" style="margin-top:6px;">
        Open the full dashboard for historical stats & predictions.
      </div>`;
  }
}

function showError(msg) {
  const box = $("error-box");
  if (box) {
    box.textContent = `⚠️ ${msg}`;
    box.style.display = "";
  }
  showFallbackCard();
}

// ── Win Probability Estimator ─────────────────────────────────────────
function estimateWinProb(scoreArr) {
  if (!scoreArr || scoreArr.length < 1) return 50;
  const r1 = scoreArr[0]?.r ?? 0;
  const r2 = scoreArr[1]?.r ?? 0;
  if (r1 + r2 === 0) return 50;
  return Math.round((r1 / (r1 + r2)) * 100);
}

// ── Helpers ───────────────────────────────────────────────────────────
function updateTimestamp() {
  const el = $("last-updated");
  if (el) el.textContent = new Date().toLocaleTimeString();
}

async function getStoredApiKey() {
  return new Promise((resolve) => {
    chrome.storage.local.get(["CRICKET_API_KEY"], (res) => {
      resolve(res.CRICKET_API_KEY || null);
    });
  });
}

function openDashboard() {
  chrome.tabs.create({ url: CONFIG.STREAMLIT_URL });
}
