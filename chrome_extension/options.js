/**
 * options.js — IPL Live Predictor Extension Settings
 * Saves & loads configuration from chrome.storage.local
 */

// ── Load saved settings on page open ─────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  chrome.storage.local.get(
    ["CRICKET_API_KEY", "notifications_enabled", "auto_refresh", "ipl_only"],
    (data) => {
      if (data.CRICKET_API_KEY) {
        document.getElementById("api-key-input").value = data.CRICKET_API_KEY;
      }
      setToggle("toggle-notifications", data.notifications_enabled !== false);
      setToggle("toggle-autorefresh",   data.auto_refresh !== false);
      setToggle("toggle-iplonly",        data.ipl_only !== false);
    }
  );
});

// ── Save Settings ─────────────────────────────────────────────────────
function saveSettings() {
  const apiKey        = document.getElementById("api-key-input").value.trim();
  const notifications = document.getElementById("toggle-notifications").checked;
  const autoRefresh   = document.getElementById("toggle-autorefresh").checked;
  const iplOnly       = document.getElementById("toggle-iplonly").checked;

  if (!apiKey) {
    showStatus("⚠️ Please enter a valid CricAPI key.", "error");
    return;
  }

  chrome.storage.local.set(
    {
      CRICKET_API_KEY:        apiKey,
      notifications_enabled:  notifications,
      auto_refresh:           autoRefresh,
      ipl_only:               iplOnly,
    },
    () => {
      // Notify background service worker of the updated key
      chrome.runtime.sendMessage({ type: "SET_API_KEY",          key:     apiKey });
      chrome.runtime.sendMessage({ type: "TOGGLE_NOTIFICATIONS", enabled: notifications });

      showStatus("✅ Settings saved successfully!", "success");
    }
  );
}

// ── Helpers ───────────────────────────────────────────────────────────
function setToggle(id, value) {
  const el = document.getElementById(id);
  if (el) el.checked = value;
}

function showStatus(msg, type) {
  const el = document.getElementById("status-msg");
  el.textContent    = msg;
  el.className      = `status-msg ${type}`;
  el.style.display  = "block";
  setTimeout(() => { el.style.display = "none"; }, 3000);
}
