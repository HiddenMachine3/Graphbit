/**
 * RecallGraph – Background Service Worker
 *
 * Minimal service worker for Manifest V3 compliance.
 * Handles extension lifecycle events.
 */

// Log installation
chrome.runtime.onInstalled.addListener((details) => {
  if (details.reason === "install") {
    console.log("RecallGraph extension installed.");
  } else if (details.reason === "update") {
    console.log(`RecallGraph extension updated to v${chrome.runtime.getManifest().version}`);
  }
});

// Optional: update badge when navigating to YouTube
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === "complete" && tab.url?.includes("youtube.com/watch")) {
    chrome.action.setBadgeText({ text: "▶", tabId });
    chrome.action.setBadgeBackgroundColor({ color: "#d946ef", tabId });
  } else if (changeInfo.status === "complete") {
    chrome.action.setBadgeText({ text: "", tabId });
  }
});
