const DEFAULT_BACKEND = "http://localhost:8000/api/v1";
const DEFAULT_FRONTEND = "http://localhost:3000";
const STATUS_EL = document.getElementById("status");
const backendUrlEl = document.getElementById("backendUrl");
const frontendUrlEl = document.getElementById("frontendUrl");
const pageTypeBadgeEl = document.getElementById("pageTypeBadge");
const projectSelectEl = document.getElementById("projectSelect");
const refreshProjectsBtn = document.getElementById("refreshProjectsBtn");
const createdByEl = document.getElementById("createdBy");
const saveBtn = document.getElementById("saveBtn");
const captureBtn = document.getElementById("captureBtn");
const ingestBtn = document.getElementById("ingestBtn");
const quizBtn = document.getElementById("quizBtn");
const quizSettingsCardEl = document.getElementById("quizSettingsCard");
const quizChunkMinutesEl = document.getElementById("quizChunkMinutes");
const quizQuestionsPerChunkEl = document.getElementById("quizQuestionsPerChunk");
const lastAddedCardEl = document.getElementById("lastAddedCard");
const lastAddedTextEl = document.getElementById("lastAddedText");
const ingestResultCardEl = document.getElementById("ingestResultCard");
const topicsGridEl = document.getElementById("topicsGrid");
const ingestSummaryEl = document.getElementById("ingestSummary");
const openInGraphbitEl = document.getElementById("openInGraphbit");

let statusResetTimer = null;
const CREATE_PROJECT_OPTION = "__create_new_project__";
let lastSelectedProjectId = "";
const DEFAULT_QUIZ_CHUNK_MINUTES = 25;
const DEFAULT_QUIZ_QUESTIONS_PER_CHUNK = 2;

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

function updateYouTubeOnlyUI(isYouTube) {
  if (isYouTube) {
    ingestBtn.classList.remove("hidden");
    quizBtn.classList.remove("hidden");
    quizSettingsCardEl.classList.remove("hidden");
  } else {
    ingestBtn.classList.add("hidden");
    quizBtn.classList.add("hidden");
    quizSettingsCardEl.classList.add("hidden");
    ingestResultCardEl.classList.add("hidden");
  }
}

async function updatePageContextBadge() {
  try {
    const tab = await getActiveTab();
    const { label, className } = detectPageType(tab?.url || "");
    pageTypeBadgeEl.textContent = label;
    pageTypeBadgeEl.className = `badge ${className}`.trim();
    updateYouTubeOnlyUI(className === "youtube");
  } catch {
    pageTypeBadgeEl.textContent = "Unknown page";
    pageTypeBadgeEl.className = "badge";
    updateYouTubeOnlyUI(false);
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
  const {
    backendUrl,
    frontendUrl,
    selectedProjectId,
    createdBy,
    lastAdded,
    quizChunkMinutes,
    quizQuestionsPerChunk,
  } = await chrome.storage.sync.get([
    "backendUrl",
    "frontendUrl",
    "selectedProjectId",
    "createdBy",
    "lastAdded",
    "quizChunkMinutes",
    "quizQuestionsPerChunk",
  ]);

  backendUrlEl.value = backendUrl || DEFAULT_BACKEND;
  frontendUrlEl.value = frontendUrl || DEFAULT_FRONTEND;
  createdByEl.value = createdBy || "browser-extension";
  quizChunkMinutesEl.value = String(
    Number.isFinite(Number(quizChunkMinutes)) && Number(quizChunkMinutes) >= 1
      ? Math.floor(Number(quizChunkMinutes))
      : DEFAULT_QUIZ_CHUNK_MINUTES
  );
  quizQuestionsPerChunkEl.value = String(
    Number.isFinite(Number(quizQuestionsPerChunk)) && Number(quizQuestionsPerChunk) >= 1
      ? Math.floor(Number(quizQuestionsPerChunk))
      : DEFAULT_QUIZ_QUESTIONS_PER_CHUNK
  );
  updateLastAddedUI(lastAdded);

  await updatePageContextBadge();
  await loadProjects(selectedProjectId || "");
}

async function saveSettings() {
  setBusy(saveBtn, "Saving...", true);
  const selectedProjectId = projectSelectEl.value || "";
  const backendUrl = normalizeApiBase(backendUrlEl.value);
  const frontendUrl = (frontendUrlEl.value || "").trim().replace(/\/+$/, "") || DEFAULT_FRONTEND;
  const { chunkMinutes, questionsPerChunk } = getQuizSettings();
  backendUrlEl.value = backendUrl;
  frontendUrlEl.value = frontendUrl;
  try {
    await chrome.storage.sync.set({
      backendUrl,
      frontendUrl,
      selectedProjectId,
      createdBy: createdByEl.value.trim(),
      quizChunkMinutes: chunkMinutes,
      quizQuestionsPerChunk: questionsPerChunk,
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

function parseBoundedInt(rawValue, fallback, minValue, maxValue) {
  const parsed = Number.parseInt(String(rawValue ?? "").trim(), 10);
  if (!Number.isFinite(parsed)) return fallback;
  return Math.min(maxValue, Math.max(minValue, parsed));
}

function getQuizSettings() {
  const chunkMinutes = parseBoundedInt(
    quizChunkMinutesEl.value,
    DEFAULT_QUIZ_CHUNK_MINUTES,
    1,
    120
  );
  const questionsPerChunk = parseBoundedInt(
    quizQuestionsPerChunkEl.value,
    DEFAULT_QUIZ_QUESTIONS_PER_CHUNK,
    1,
    10
  );

  quizChunkMinutesEl.value = String(chunkMinutes);
  quizQuestionsPerChunkEl.value = String(questionsPerChunk);

  return { chunkMinutes, questionsPerChunk };
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

function renderTopicChips(topics) {
  topicsGridEl.innerHTML = "";
  (topics || []).forEach(({ topic, created }) => {
    const chip = document.createElement("span");
    chip.className = `topic-chip${created ? " topic-chip-new" : ""}`;
    chip.textContent = topic;
    if (created) chip.title = "New node";
    topicsGridEl.appendChild(chip);
  });
}

function toFiniteNumber(value) {
  const num = Number(value);
  return Number.isFinite(num) ? num : null;
}

function chunkTranscriptSegmentsByTime(segments, maxChunkSeconds) {
  const sorted = [...(segments || [])]
    .map((segment) => ({
      text: String(segment?.text || "").trim(),
      start: toFiniteNumber(segment?.start),
      duration: toFiniteNumber(segment?.duration),
    }))
    .filter((segment) => segment.text)
    .sort((a, b) => {
      const aStart = a.start ?? Number.POSITIVE_INFINITY;
      const bStart = b.start ?? Number.POSITIVE_INFINITY;
      return aStart - bStart;
    });

  if (!sorted.length) {
    return [];
  }

  const chunks = [];
  let cursorStart = sorted[0].start ?? 0;
  let current = {
    startSec: cursorStart,
    endSec: cursorStart,
    textParts: [],
  };

  for (const segment of sorted) {
    const segmentStart = segment.start ?? current.endSec;
    const segmentDuration = segment.duration ?? 3;
    const segmentEnd = Math.max(segmentStart, segmentStart + Math.max(segmentDuration, 0));

    if (current.textParts.length > 0 && segmentStart - current.startSec >= maxChunkSeconds) {
      chunks.push({
        startSec: current.startSec,
        endSec: Math.max(current.endSec, current.startSec),
        text: current.textParts.join(" ").trim(),
      });
      current = {
        startSec: segmentStart,
        endSec: segmentEnd,
        textParts: [],
      };
    }

    current.textParts.push(segment.text);
    current.endSec = Math.max(current.endSec, segmentEnd);
  }

  if (current.textParts.length > 0) {
    chunks.push({
      startSec: current.startSec,
      endSec: Math.max(current.endSec, current.startSec),
      text: current.textParts.join(" ").trim(),
    });
  }

  return chunks.filter((chunk) => chunk.text);
}

function splitTextIntoFallbackChunks(text, maxChars = 9000) {
  const source = String(text || "").trim();
  if (!source) return [];

  const paragraphs = source.split(/\n\s*\n/g).map((part) => part.trim()).filter(Boolean);
  const blocks = paragraphs.length ? paragraphs : source.split(/(?<=[.!?])\s+/g).map((part) => part.trim()).filter(Boolean);

  const chunks = [];
  let current = "";
  for (const block of blocks) {
    const candidate = current ? `${current}\n\n${block}` : block;
    if (candidate.length > maxChars && current) {
      chunks.push(current);
      current = block;
    } else {
      current = candidate;
    }
  }
  if (current) chunks.push(current);
  return chunks;
}

function buildTranscriptChunksForQuiz(transcriptText, transcriptSegments) {
  const { chunkMinutes } = getQuizSettings();
  const maxChunkSeconds = chunkMinutes * 60;
  const timedChunks = chunkTranscriptSegmentsByTime(transcriptSegments, maxChunkSeconds);
  if (timedChunks.length > 0) {
    return timedChunks;
  }

  const fallbackTextChunks = splitTextIntoFallbackChunks(transcriptText);
  return fallbackTextChunks.map((text, index) => {
    const startSec = index * maxChunkSeconds;
    const endSec = (index + 1) * maxChunkSeconds;
    return { startSec, endSec, text };
  });
}

async function generateQuizQuestionsForChunks(backendUrl, chunks, questionsPerChunk) {
  const chunkQuizzes = [];

  for (let index = 0; index < chunks.length; index += 1) {
    const chunk = chunks[index];
    const response = await fetch(`${backendUrl}/qa/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text: chunk.text,
        n: questionsPerChunk,
      }),
    });

    const responseText = await response.text();
    if (!response.ok) {
      throw new Error(`Chunk ${index + 1} QA failed (HTTP ${response.status}): ${responseText}`);
    }

    let parsed;
    try {
      parsed = JSON.parse(responseText);
    } catch {
      throw new Error(`Chunk ${index + 1} QA returned invalid JSON.`);
    }

    const qaPairs = Array.isArray(parsed?.qa_pairs) ? parsed.qa_pairs : [];
    const normalizedPairs = qaPairs
      .map((pair) => ({
        question: String(pair?.question || "").trim(),
        answer: String(pair?.answer || "").trim(),
      }))
      .filter((pair) => pair.question)
      .slice(0, questionsPerChunk);

    if (normalizedPairs.length > 0) {
      chunkQuizzes.push({
        startSec: chunk.startSec,
        endSec: chunk.endSec,
        qaPairs: normalizedPairs,
      });
    }
  }

  return chunkQuizzes;
}

async function startInVideoQuiz() {
  setBusy(quizBtn, "Preparing quiz…", true);
  try {
    const tab = await getActiveTab();
    if (!tab || !tab.id || !tab.url || !isYouTubeUrl(tab.url)) {
      setStatus("Open a YouTube video first.", "error");
      return;
    }

    const backendUrl = normalizeApiBase(backendUrlEl.value);
    backendUrlEl.value = backendUrl;

    setStatus("Fetching transcript…", "info");
    const transcriptResponse = await fetch(`${backendUrl}/materials/youtube/transcript-check`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ link: tab.url }),
    });

    const transcriptText = await transcriptResponse.text();
    if (!transcriptResponse.ok) {
      throw new Error(`Transcript fetch failed (HTTP ${transcriptResponse.status}): ${transcriptText}`);
    }

    const transcriptPayload = JSON.parse(transcriptText);
    const chunks = buildTranscriptChunksForQuiz(
      transcriptPayload?.transcript_text || "",
      transcriptPayload?.segments || []
    );
    const { chunkMinutes, questionsPerChunk } = getQuizSettings();

    if (!chunks.length) {
      setStatus("No transcript content found for quiz generation.", "error");
      return;
    }

    setStatus(`Generating questions for ${chunks.length} chunk${chunks.length !== 1 ? "s" : ""}…`, "info");
    const chunkQuizzes = await generateQuizQuestionsForChunks(backendUrl, chunks, questionsPerChunk);

    if (!chunkQuizzes.length) {
      setStatus("No quiz questions were generated.", "error");
      return;
    }

    await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      args: [chunkQuizzes, chunkMinutes, questionsPerChunk],
      func: (chunkQuizzesArg, chunkMinutesArg, questionsPerChunkArg) => {
        const video = document.querySelector("video");
        if (!video) {
          throw new Error("Could not find a YouTube video player on the page.");
        }

        if (window.__graphbitQuizState?.timerId) {
          clearInterval(window.__graphbitQuizState.timerId);
        }

        const sortedChunks = [...chunkQuizzesArg]
          .filter((chunk) => Array.isArray(chunk?.qaPairs) && chunk.qaPairs.length > 0)
          .sort((a, b) => Number(a.endSec || 0) - Number(b.endSec || 0));

        if (!sortedChunks.length) {
          throw new Error("No quiz chunks available to schedule.");
        }

        let nextChunkIndex = 0;
        const currentTime = Number(video.currentTime || 0);
        while (nextChunkIndex < sortedChunks.length && Number(sortedChunks[nextChunkIndex].endSec || 0) <= currentTime) {
          nextChunkIndex += 1;
        }

        const askChunkQuestions = (chunk, chunkIndex, totalChunks) => {
          video.pause();
          alert(`Quiz time (${chunkIndex + 1}/${totalChunks})!`);

          const qaPairs = Array.isArray(chunk.qaPairs) ? chunk.qaPairs : [];
          for (let i = 0; i < qaPairs.length; i += 1) {
            const pair = qaPairs[i] || {};
            const question = String(pair.question || "").trim();
            if (!question) continue;

            prompt(`Q${i + 1}: ${question}\n\nType your answer and press OK.`);
            const expectedAnswer = String(pair.answer || "").trim();
            if (expectedAnswer) {
              alert(`Expected answer:\n${expectedAnswer}`);
            }
          }

          video.play().catch(() => {});
        };

        const timerId = setInterval(() => {
          if (nextChunkIndex >= sortedChunks.length) {
            clearInterval(timerId);
            window.__graphbitQuizState = null;
            return;
          }

          const chunk = sortedChunks[nextChunkIndex];
          const endSec = Number(chunk.endSec || 0);
          if (Number(video.currentTime || 0) >= endSec) {
            askChunkQuestions(chunk, nextChunkIndex, sortedChunks.length);
            nextChunkIndex += 1;
          }
        }, 1000);

        window.__graphbitQuizState = {
          timerId,
          totalChunks: sortedChunks.length,
          startedAt: Date.now(),
        };

        alert(
          `Graphbit in-video quiz is active. The video will pause every ${chunkMinutesArg}-minute chunk to ask ${
            Number(questionsPerChunkArg) || sortedChunks[0]?.qaPairs?.length || 2
          } questions.`
        );
      },
    });

    setStatus(
      `In-video quiz started (${chunkQuizzes.length} chunk${chunkQuizzes.length !== 1 ? "s" : ""}, ${questionsPerChunk} question${questionsPerChunk !== 1 ? "s" : ""} each, ${chunkMinutes} minute${chunkMinutes !== 1 ? "s" : ""} per chunk).`,
      "success"
    );
  } catch (error) {
    setStatus(`Quiz setup failed: ${error.message}`, "error");
  } finally {
    setBusy(quizBtn, "Preparing quiz…", false);
  }
}

async function ingestVideoToGraph() {
  setBusy(ingestBtn, "Extracting topics…", true);
  ingestResultCardEl.classList.add("hidden");
  openInGraphbitEl.classList.add("hidden");
  try {
    const tab = await getActiveTab();
    if (!tab || !tab.url || !isYouTubeUrl(tab.url)) {
      setStatus("Not a YouTube tab.", "error");
      return;
    }

    const projectId = projectSelectEl.value || "";
    if (!projectId) {
      setStatus("Select a project first.", "error");
      return;
    }

    const backendUrl = normalizeApiBase(backendUrlEl.value);
    setStatus("Fetching transcript…", "info");

    const response = await fetch(`${backendUrl}/graph/ingest/video`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        project_id: projectId,
        video_url: tab.url,
        title: tab.title || "YouTube Video",
      }),
    });

    const responseText = await response.text();
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${responseText}`);
    }

    const result = JSON.parse(responseText);
    const topics = result.topics || [];
    const newCount = topics.filter((t) => t.created).length;
    const seqNum = result.sequence_number ?? null;

    renderTopicChips(topics);
    const seqLabel = seqNum ? ` · Video #${seqNum}` : "";
    ingestSummaryEl.textContent = `${newCount} new node${newCount !== 1 ? "s" : ""} · ${result.edges_added || 0} edges added${seqLabel}`;

    const { frontendUrl } = await chrome.storage.sync.get(["frontendUrl"]);
    const base = (frontendUrl || DEFAULT_FRONTEND).replace(/\/+$/, "");
    openInGraphbitEl.href = `${base}/graph?project_id=${encodeURIComponent(projectId)}`;
    openInGraphbitEl.classList.remove("hidden");
    ingestResultCardEl.classList.remove("hidden");

    setStatus(`Graph updated — ${topics.length} topic${topics.length !== 1 ? "s" : ""} extracted.`, "success");
  } catch (error) {
    setStatus(`Ingest failed: ${error.message}`, "error");
  } finally {
    setBusy(ingestBtn, "Extracting topics…", false);
  }
}

saveBtn.addEventListener("click", saveSettings);
captureBtn.addEventListener("click", addMaterial);
ingestBtn.addEventListener("click", ingestVideoToGraph);
quizBtn.addEventListener("click", startInVideoQuiz);
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
quizChunkMinutesEl.addEventListener("change", async () => {
  const { chunkMinutes } = getQuizSettings();
  await chrome.storage.sync.set({ quizChunkMinutes: chunkMinutes });
});
quizQuestionsPerChunkEl.addEventListener("change", async () => {
  const { questionsPerChunk } = getQuizSettings();
  await chrome.storage.sync.set({ quizQuestionsPerChunk: questionsPerChunk });
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
