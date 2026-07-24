/**
 * background.js — IPL Live Predictor Chrome Extension Service Worker
 * Runs in the background, polls for live data, and sends notifications.
 */

const CRICAPI_URL    = "https://api.cricapi.com/v1/currentMatches";
const ALARM_NAME     = "ipl-live-refresh";
const ALARM_PERIOD   = 1; // minutes

// ── Install / Update ──────────────────────────────────────────────────
chrome.runtime.onInstalled.addListener(({ reason }) => {
  if (reason === "install") {
    // Store default API key on first install
    // NOTE: Replace with the real key via the options page or popup settings
    chrome.storage.local.set({
      CRICKET_API_KEY: "",   // user must set this
      last_match: null,
      notifications_enabled: true,
    });

    // Show welcome notification
    chrome.notifications.create("welcome", {
      type:    "basic",
      iconUrl: "icons/icon48.png",
      title:   "🏏 IPL Live Predictor Installed!",
      message: "Click the extension icon to view live IPL scores and predictions.",
    });
  }

  // Create alarm for periodic background refresh
  chrome.alarms.create(ALARM_NAME, {
    delayInMinutes: 0.5,
    periodInMinutes: ALARM_PERIOD,
  });
});

// ── Alarm Handler (Background Polling) ───────────────────────────────
chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name !== ALARM_NAME) return;

  const stored = await getStorage(["CRICKET_API_KEY", "last_match", "notifications_enabled"]);
  const apiKey = stored.CRICKET_API_KEY;

  if (!apiKey) return; // No key, skip

  try {
    const res  = await fetch(`${CRICAPI_URL}?apikey=${apiKey}&offset=0`);
    const json = await res.json();

    if (json.status !== "success") return;

    const iplMatches = (json.data || []).filter(
      (m) => m.name?.includes("IPL") || m.name?.includes("Indian Premier League")
    );
    if (!iplMatches.length) return;

    const match    = iplMatches[0];
    const matchKey = `${match.name}-${match.status}`;
    const lastKey  = stored.last_match;

    // Notify only if the match/status changed
    if (matchKey !== lastKey && stored.notifications_enabled) {
      const scoreArr  = match.score || [];
      const scorePart = scoreArr
        .map((s) => `${s.r ?? 0}/${s.w ?? 0} (${s.o ?? 0})`)
        .join(" | ");

      chrome.notifications.create(`ipl-${Date.now()}`, {
        type:    "basic",
        iconUrl: "icons/icon48.png",
        title:   `🏏 ${match.name}`,
        message: `${scorePart || "Match started"} — ${match.status}`,
      });

      // Cache latest match state
      chrome.storage.local.set({ last_match: matchKey });
    }
  } catch (e) {
    console.error("[Background] Poll error:", e.message);
  }
});

// ── Message Handler (from popup) ─────────────────────────────────────
chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.type === "SET_API_KEY") {
    chrome.storage.local.set({ CRICKET_API_KEY: msg.key }, () => {
      sendResponse({ ok: true });
    });
    return true; // keep channel open for async
  }

  if (msg.type === "TOGGLE_NOTIFICATIONS") {
    chrome.storage.local.set({ notifications_enabled: msg.enabled }, () => {
      sendResponse({ ok: true });
    });
    return true;
  }
});

// ── Utility ───────────────────────────────────────────────────────────
function getStorage(keys) {
  return new Promise((resolve) => {
    chrome.storage.local.get(keys, resolve);
  });
}
