/**
 * RecallGraph – YouTube Content Script
 *
 * Runs on youtube.com/watch pages.
 * Extracts video title and channel name from the DOM
 * and responds to messages from the popup.
 */

(() => {
  /**
   * Pull the video title from YouTube's DOM.
   * Tries multiple selectors because YouTube's SPA
   * layout can vary between the classic and new renderers.
   */
  function getVideoTitle() {
    // Primary: yt player title
    const h1 = document.querySelector(
      "h1.ytd-watch-metadata yt-formatted-string, " +
      "h1.title yt-formatted-string, " +
      "#title h1 yt-formatted-string"
    );
    if (h1?.textContent?.trim()) return h1.textContent.trim();

    // Fallback: og:title meta tag
    const meta = document.querySelector('meta[property="og:title"]');
    if (meta?.content?.trim()) return meta.content.trim();

    // Last resort: document title minus suffix
    return document.title.replace(" - YouTube", "").trim();
  }

  /**
   * Pull the channel name from YouTube's DOM.
   */
  function getChannelName() {
    // Primary: channel link inside the watch metadata
    const link = document.querySelector(
      "ytd-channel-name yt-formatted-string a, " +
      "#channel-name yt-formatted-string a, " +
      "#owner-name a"
    );
    if (link?.textContent?.trim()) return link.textContent.trim();

    // Fallback
    const byline = document.querySelector(".ytd-video-owner-renderer #text a");
    if (byline?.textContent?.trim()) return byline.textContent.trim();

    return "";
  }

  // Listen for messages from the popup
  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    if (msg.type === "GET_VIDEO_INFO") {
      sendResponse({
        title: getVideoTitle(),
        channel: getChannelName(),
      });
    }
    // Return true to keep the message port open for async responses
    return true;
  });
})();
