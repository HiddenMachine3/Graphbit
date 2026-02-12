/**
 * RecallGraph YouTube Ingest – Popup Logic
 *
 * Flow:
 *  1. Check if current tab is a YouTube watch page.
 *  2. Pull video info from the content script.
 *  3. Fetch project list from backend.
 *  4. User picks a project and clicks "Ingest Video".
 *  5. POST to /api/v1/graph/ingest/video → show results.
 */

const API_BASE = "http://localhost:8000/api/v1";

// ── DOM refs ──────────────────────────────────────────
const elNotYoutube   = document.getElementById("not-youtube");
const elMainUI       = document.getElementById("main-ui");
const elErrorState   = document.getElementById("error-state");
const elErrorMessage = document.getElementById("error-message");
const elRetryBtn     = document.getElementById("retry-btn");

const elVideoTitle     = document.getElementById("video-title");
const elVideoChannel   = document.getElementById("video-channel");
const elVideoThumbnail = document.getElementById("video-thumbnail");

const elProjectSelect = document.getElementById("project-select");
const elIngestBtn     = document.getElementById("ingest-btn");
const elBtnIcon       = document.getElementById("btn-icon");
const elBtnText       = document.getElementById("btn-text");

const elStatus        = document.getElementById("status");
const elResultDetails = document.getElementById("result-details");
const elResultChapter = document.getElementById("result-chapter");
const elResultTopics  = document.getElementById("result-topics");
const elResultEdges   = document.getElementById("result-edges");

// ── State ─────────────────────────────────────────────
let currentVideoInfo = null; // { url, title, channel }

// ── Helpers ───────────────────────────────────────────
function show(el)  { el.classList.remove("hidden"); }
function hide(el)  { el.classList.add("hidden"); }

function setStatus(message, type = "info") {
  elStatus.textContent = message;
  elStatus.className = type; // removes hidden, sets info|success|error
  show(elStatus);
}

function extractVideoId(url) {
  try {
    const u = new URL(url);
    return u.searchParams.get("v");
  } catch { return null; }
}

// ── Init ──────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", init);

async function init() {
  elRetryBtn.addEventListener("click", init);

  // Hide all screens
  hide(elNotYoutube);
  hide(elMainUI);
  hide(elErrorState);
  hide(elStatus);
  hide(elResultDetails);

  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

    if (!tab?.url || !tab.url.includes("youtube.com/watch")) {
      show(elNotYoutube);
      return;
    }

    show(elMainUI);

    // Get video info from the content script
    const videoInfo = await getVideoInfo(tab);
    currentVideoInfo = videoInfo;

    // Show video details
    elVideoTitle.textContent = videoInfo.title || "Untitled Video";
    elVideoChannel.textContent = videoInfo.channel || "";

    const videoId = extractVideoId(tab.url);
    if (videoId) {
      elVideoThumbnail.style.backgroundImage =
        `url(https://img.youtube.com/vi/${videoId}/mqdefault.jpg)`;
    }

    // Load projects
    await loadProjects();

  } catch (err) {
    console.error("Init error:", err);
    showError("Could not connect to RecallGraph backend. Is it running?");
  }
}

// ── Get video info via content script ─────────────────
async function getVideoInfo(tab) {
  try {
    // Try messaging the already-injected content script
    const response = await chrome.tabs.sendMessage(tab.id, { type: "GET_VIDEO_INFO" });
    if (response?.title) return { ...response, url: tab.url };
  } catch {
    // Content script might not be injected yet – inject it now
    try {
      await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        files: ["content.js"],
      });
      const response = await chrome.tabs.sendMessage(tab.id, { type: "GET_VIDEO_INFO" });
      if (response?.title) return { ...response, url: tab.url };
    } catch (e) {
      console.warn("Could not inject content script:", e);
    }
  }

  // Fallback: parse title from the tab
  return {
    url: tab.url,
    title: tab.title?.replace(" - YouTube", "").trim() || "Untitled Video",
    channel: "",
  };
}

// ── Load projects from backend ────────────────────────
async function loadProjects() {
  const res = await fetch(`${API_BASE}/projects`);
  if (!res.ok) throw new Error(`Failed to load projects: ${res.status}`);

  const projects = await res.json();

  elProjectSelect.innerHTML = "";

  if (projects.length === 0) {
    const opt = document.createElement("option");
    opt.value = "";
    opt.disabled = true;
    opt.selected = true;
    opt.textContent = "No projects found";
    elProjectSelect.appendChild(opt);
    return;
  }

  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.disabled = true;
  placeholder.selected = true;
  placeholder.textContent = "Select a project…";
  elProjectSelect.appendChild(placeholder);

  for (const proj of projects) {
    const opt = document.createElement("option");
    opt.value = proj.id;
    opt.textContent = proj.name;
    elProjectSelect.appendChild(opt);
  }

  // Auto-select if only one project
  if (projects.length === 1) {
    elProjectSelect.value = projects[0].id;
    elIngestBtn.disabled = false;
  }

  elProjectSelect.addEventListener("change", () => {
    elIngestBtn.disabled = !elProjectSelect.value;
  });

  elIngestBtn.addEventListener("click", handleIngest);
}

// ── Ingest ────────────────────────────────────────────
async function handleIngest() {
  if (!currentVideoInfo || !elProjectSelect.value) return;

  const projectId = elProjectSelect.value;

  // UI loading state
  elIngestBtn.disabled = true;
  elIngestBtn.classList.add("loading");
  elBtnIcon.innerHTML = '<span class="spinner"></span>';
  elBtnText.textContent = "Ingesting…";
  hide(elResultDetails);
  setStatus("Fetching transcript & extracting topics…", "info");

  try {
    const res = await fetch(`${API_BASE}/graph/ingest/video`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        project_id: projectId,
        video_url: currentVideoInfo.url,
        title: currentVideoInfo.title,
        channel: currentVideoInfo.channel || undefined,
      }),
    });

    if (!res.ok) {
      const errBody = await res.json().catch(() => ({}));
      throw new Error(errBody.detail || `Server returned ${res.status}`);
    }

    const data = await res.json();

    // Success UI
    setStatus("Video ingested successfully!", "success");

    elResultChapter.textContent = data.chapter_node_id || "—";
    elResultTopics.textContent = `${data.topics_added?.length ?? data.topics?.length ?? 0} topics`;
    elResultEdges.textContent = `${data.edges_added ?? 0} connections`;
    show(elResultDetails);

    // Update button
    elBtnIcon.textContent = "✓";
    elBtnText.textContent = "Done";

  } catch (err) {
    console.error("Ingest error:", err);
    setStatus(`Error: ${err.message}`, "error");

    // Re-enable button to allow retry
    elIngestBtn.disabled = false;
    elIngestBtn.classList.remove("loading");
    elBtnIcon.textContent = "⚡";
    elBtnText.textContent = "Retry Ingest";
  }
}

// ── Error screen ──────────────────────────────────────
function showError(message) {
  hide(elNotYoutube);
  hide(elMainUI);
  elErrorMessage.textContent = message;
  show(elErrorState);
}
