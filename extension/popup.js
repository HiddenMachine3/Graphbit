const DEFAULT_BACKEND = "http://localhost:8000/api/v1";
const STATUS_EL = document.getElementById("status");
const backendUrlEl = document.getElementById("backendUrl");
const pageTypeBadgeEl = document.getElementById("pageTypeBadge");
const projectSelectEl = document.getElementById("projectSelect");
const refreshProjectsBtn = document.getElementById("refreshProjectsBtn");
const createdByEl = document.getElementById("createdBy");
const saveBtn = document.getElementById("saveBtn");
const captureBtn = document.getElementById("captureBtn");
const lastAddedCardEl = document.getElementById("lastAddedCard");
const lastAddedTextEl = document.getElementById("lastAddedText");

let statusResetTimer = null;
const CREATE_PROJECT_OPTION = "__create_new_project__";
let lastSelectedProjectId = "";

function setStatus(message, level = "info") {
  STATUS_EL.textContent = message;
  STATUS_EL.className = `status ${level}`;

  if (statusResetTimer) {
    clearTimeout(statusResetTimer);
    statusResetTimer = null;
  }

  if (level !== "info") {
    statusResetTimer = setTimeout(() => {
      STATUS_EL.textContent = "Ready.";
      STATUS_EL.className = "status info";
    }, 2800);
  }
}

function setBusy(button, busyText, isBusy) {
  if (!button.dataset.defaultText) {
    button.dataset.defaultText = button.textContent;
  }
  button.disabled = isBusy;
  button.textContent = isBusy ? busyText : button.dataset.defaultText;
}

function normalizeApiBase(url) {
  let base = (url || "").trim().replace(/\/+$/, "");
  if (!base) base = DEFAULT_BACKEND;
  if (!/\/api\/v1$/i.test(base)) {
    base = `${base}/api/v1`;
  }
  return base;
}

function isYouTubeUrl(url) {
  return /^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.be)\//i.test(url || "");
}

function detectPageType(url) {
  if (!url) return { label: "Unknown page", className: "" };
  if (isYouTubeUrl(url)) return { label: "YouTube tab", className: "youtube" };
  if (/^file:\/\//i.test(url)) return { label: "Local HTML file", className: "file" };
  return { label: "Web page", className: "html" };
}

function formatRelativeTime(isoString) {
  if (!isoString) return "just now";
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) return "just now";
  const diffMs = Date.now() - date.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return "just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDay = Math.floor(diffHr / 24);
  return `${diffDay}d ago`;
}

function updateLastAddedUI(lastAdded) {
  if (!lastAdded || !lastAdded.title || !lastAdded.projectId) {
    lastAddedCardEl.classList.add("hidden");
    lastAddedTextEl.textContent = "No materials added yet.";
    return;
  }

  const shortTitle = (lastAdded.title || "Untitled").trim().slice(0, 80);
  lastAddedTextEl.textContent = `${shortTitle} • ${lastAdded.projectId} • ${formatRelativeTime(lastAdded.at)}`;
  lastAddedCardEl.classList.remove("hidden");
}

async function updatePageContextBadge() {
  try {
    const tab = await getActiveTab();
    const { label, className } = detectPageType(tab?.url || "");
    pageTypeBadgeEl.textContent = label;
    pageTypeBadgeEl.className = `badge ${className}`.trim();
  } catch {
    pageTypeBadgeEl.textContent = "Unknown page";
    pageTypeBadgeEl.className = "badge";
  }
}

async function getActiveTab() {
  const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
  return tabs[0];
}

async function getPageContent(tabId) {
  const [result] = await chrome.scripting.executeScript({
    target: { tabId },
    func: () => {
      const rawText = (document.body?.innerText || "").replace(/\n{3,}/g, "\n\n").trim();
      const html = document.documentElement?.outerHTML || "";
      return {
        pageTitle: document.title || "Untitled Page",
        pageUrl: location.href,
        contentText: rawText,
        htmlLength: html.length,
      };
    },
  });
  return result?.result || null;
}

async function loadSettings() {
  const { backendUrl, selectedProjectId, createdBy, lastAdded } = await chrome.storage.sync.get([
    "backendUrl",
    "selectedProjectId",
    "createdBy",
    "lastAdded",
  ]);

  backendUrlEl.value = backendUrl || DEFAULT_BACKEND;
  createdByEl.value = createdBy || "browser-extension";
  updateLastAddedUI(lastAdded);

  await updatePageContextBadge();
  await loadProjects(selectedProjectId || "");
}

async function saveSettings() {
  setBusy(saveBtn, "Saving...", true);
  const selectedProjectId = projectSelectEl.value || "";
  const backendUrl = normalizeApiBase(backendUrlEl.value);
  backendUrlEl.value = backendUrl;
  try {
    await chrome.storage.sync.set({
      backendUrl,
      selectedProjectId,
      createdBy: createdByEl.value.trim(),
    });
    setStatus("Defaults saved.", "success");
  } finally {
    setBusy(saveBtn, "Saving...", false);
  }
}

function renderProjectOptions(projects, preferredId = "") {
  projectSelectEl.innerHTML = "";

  if (!Array.isArray(projects) || projects.length === 0) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "No projects available";
    projectSelectEl.appendChild(option);

    const createOption = document.createElement("option");
    createOption.value = CREATE_PROJECT_OPTION;
    createOption.textContent = "+ Create new project";
    projectSelectEl.appendChild(createOption);

    projectSelectEl.value = "";
    lastSelectedProjectId = "";
    return;
  }

  for (const project of projects) {
    const option = document.createElement("option");
    option.value = project.id;
    const name = (project.name || "Untitled Project").trim();
    option.textContent = `${name} (${project.id})`;
    projectSelectEl.appendChild(option);
  }

  const createOption = document.createElement("option");
  createOption.value = CREATE_PROJECT_OPTION;
  createOption.textContent = "+ Create new project";
  projectSelectEl.appendChild(createOption);

  if (preferredId && projects.some((project) => project.id === preferredId)) {
    projectSelectEl.value = preferredId;
  } else {
    projectSelectEl.value = projects[0].id;
  }

  lastSelectedProjectId = projectSelectEl.value;
}

async function loadProjects(preferredId = "") {
  setBusy(refreshProjectsBtn, "Refreshing...", true);
  try {
    const backendUrl = normalizeApiBase(backendUrlEl.value);
    backendUrlEl.value = backendUrl;
    const response = await fetch(`${backendUrl}/projects`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });
    const text = await response.text();
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${text}`);
    }

    const projects = JSON.parse(text);
    renderProjectOptions(projects, preferredId);

    await chrome.storage.sync.set({
      backendUrl,
      selectedProjectId: projectSelectEl.value || "",
    });
    setStatus(`Loaded ${Array.isArray(projects) ? projects.length : 0} projects.`, "success");
  } catch (error) {
    renderProjectOptions([], "");
    setStatus(`Could not load projects: ${error.message}`, "error");
  } finally {
    setBusy(refreshProjectsBtn, "Refreshing...", false);
  }
}

async function createProject() {
  try {
    const projectNameInput = window.prompt("Enter new project name:", "My New Project");
    const projectName = (projectNameInput || "").trim();
    if (!projectName) {
      setStatus("Project creation canceled.", "info");
      if (lastSelectedProjectId) {
        projectSelectEl.value = lastSelectedProjectId;
      }
      return;
    }

    const backendUrl = normalizeApiBase(backendUrlEl.value);
    const createdBy = createdByEl.value.trim();
    setStatus("Creating project...", "info");

    const response = await fetch(`${backendUrl}/projects`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: projectName,
        description: "Created from Graphbit browser extension",
        ...(createdBy ? { created_by: createdBy } : {}),
      }),
    });

    const text = await response.text();
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${text}`);
    }

    const createdProject = JSON.parse(text);
    await loadProjects(createdProject.id || "");
    await chrome.storage.sync.set({ selectedProjectId: createdProject.id || "" });
    lastSelectedProjectId = createdProject.id || "";
    setStatus(`Created ${createdProject.name || createdProject.id}.`, "success");
  } catch (error) {
    setStatus(`Create project failed: ${error.message}`, "error");
  } finally {
    projectSelectEl.value = lastSelectedProjectId || "";
  }
}

async function addMaterial() {
  setBusy(captureBtn, "Adding material...", true);
  try {
    setStatus("Reading current page...", "info");

    const tab = await getActiveTab();
    if (!tab || !tab.id || !tab.url) {
      setStatus("No active tab found.", "error");
      return;
    }

    const backendUrl = normalizeApiBase(backendUrlEl.value);
    const projectId = projectSelectEl.value || "";
    const createdBy = createdByEl.value.trim();

    if (!projectId) {
      setStatus("Select a project first.", "error");
      return;
    }

    let payload;
    let addedTitle;

    if (isYouTubeUrl(tab.url)) {
      payload = {
        project_id: projectId,
        title: tab.title || "YouTube Material",
        source_url: tab.url,
        content_text: "",
      };
      addedTitle = payload.title;
    } else {
      const page = await getPageContent(tab.id);
      if (!page) {
        setStatus("Could not read page content.", "error");
        return;
      }

      const contentText = (page.contentText || "").trim();
      if (!contentText) {
        setStatus("No readable text content found on this page.", "error");
        return;
      }

      payload = {
        project_id: projectId,
        title: page.pageTitle || tab.title || "HTML Material",
        source_url: page.pageUrl || tab.url,
        content_text: contentText.slice(0, 250000),
      };
      addedTitle = payload.title;
    }

    if (createdBy) {
      payload.created_by = createdBy;
    }

    setStatus("Sending to backend...", "info");

    const response = await fetch(`${backendUrl}/materials`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const responseText = await response.text();
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${responseText}`);
    }

    const lastAdded = {
      title: addedTitle || "Material",
      projectId,
      at: new Date().toISOString(),
    };
    await chrome.storage.sync.set({ lastAdded });
    updateLastAddedUI(lastAdded);
    setStatus("Material added successfully.", "success");
  } catch (error) {
    setStatus(`Failed: ${error.message}`, "error");
  } finally {
    setBusy(captureBtn, "Adding material...", false);
  }
}

saveBtn.addEventListener("click", saveSettings);
captureBtn.addEventListener("click", addMaterial);
refreshProjectsBtn.addEventListener("click", async () => {
  setStatus("Refreshing projects...", "info");
  await loadProjects(projectSelectEl.value || "");
  await updatePageContextBadge();
});
backendUrlEl.addEventListener("change", async () => {
  await loadProjects(projectSelectEl.value || "");
});
createdByEl.addEventListener("change", async () => {
  await chrome.storage.sync.set({ createdBy: createdByEl.value.trim() });
});
projectSelectEl.addEventListener("change", async () => {
  if (projectSelectEl.value === CREATE_PROJECT_OPTION) {
    await createProject();
    return;
  }

  lastSelectedProjectId = projectSelectEl.value;
  await chrome.storage.sync.set({ selectedProjectId: lastSelectedProjectId });
  setStatus("Project selected.", "info");
});

document.addEventListener("DOMContentLoaded", loadSettings);
