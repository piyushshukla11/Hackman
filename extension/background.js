/**
 * PRISM Review Intelligence - Background Service Worker (MV3)
 */

chrome.runtime.onInstalled.addListener(() => {
  // Set default settings
  chrome.storage.local.get(["apiUrl", "token", "tenantId"], (items) => {
    if (!items.apiUrl) {
      chrome.storage.local.set({ apiUrl: "http://localhost:8000" });
    }
    if (!items.token) {
      chrome.storage.local.set({ token: "demo-token" });
    }
    if (!items.tenantId) {
      chrome.storage.local.set({ tenantId: "default" });
    }
  });
  console.log("PRISM Review Intelligence Extension installed successfully.");
});

// Update badge count when tab is active or updated
chrome.tabs.onActivated.addListener((activeInfo) => {
  updateTabBadge(activeInfo.tabId);
});

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === "complete") {
    updateTabBadge(tabId);
  }
});

function updateTabBadge(tabId) {
  chrome.tabs.sendMessage(tabId, { action: "DETECT_REVIEWS" }, (response) => {
    if (chrome.runtime.lastError || !response) {
      chrome.action.setBadgeText({ tabId, text: "" });
      return;
    }
    const count = response.count || 0;
    if (count > 0) {
      chrome.action.setBadgeText({ tabId, text: String(count) });
      chrome.action.setBadgeBackgroundColor({ tabId, color: "#06B6D4" });
    } else {
      chrome.action.setBadgeText({ tabId, text: "" });
    }
  });
}

// Relay messages if requested
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "UPDATE_BADGE" && sender.tab) {
    const count = request.count || 0;
    const tabId = sender.tab.id;
    if (count > 0) {
      chrome.action.setBadgeText({ tabId, text: String(count) });
      chrome.action.setBadgeBackgroundColor({ tabId, color: "#06B6D4" });
    } else {
      chrome.action.setBadgeText({ tabId, text: "" });
    }
    sendResponse({ status: "badge_updated" });
  }
  return true;
});
