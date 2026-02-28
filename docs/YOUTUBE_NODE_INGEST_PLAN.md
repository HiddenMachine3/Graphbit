# YouTube → Graph Node Ingestion — Hackathon Plan

## TL;DR

User opens a YouTube video → clicks the Graphbit extension → selects (or creates) a project → clicks **"Add to Graph"** → the backend fetches the transcript, extracts topics with the LLM/keyword pipeline, and upserts them as knowledge graph nodes. The user can then open their project in the main app and see the nodes live.

---

## Feasibility Assessment

### What Already Exists (Do Not Rebuild)

| Layer | Piece | Location |
|---|---|---|
| Extension | Full popup UI with project select, create-new-project, YouTube detection, status feedback | `extension/popup.{html,js,css}` |
| Extension | `isYouTubeUrl()` URL detection, `detectPageType()` badge | `extension/popup.js` |
| Backend | YouTube transcript fetching (`youtube_transcript_api`) with proxy + fallback chain | `Backend/app/services/video_transcripts.py` |
| Backend | Topic extraction — OpenAI → local HF model → keyword fallback | `Backend/app/services/topic_extraction.py` |
| Backend | **`POST /api/v1/graph/ingest/video`** — transcript → topics → chapter node + topic nodes + edges, all in one call | `Backend/app/api/graph.py` (L649) |
| Backend | `POST /api/v1/materials` — already auto-imports YouTube transcripts from URL alone | `Backend/app/api/materials.py` |
| Backend | `POST /api/v1/projects` — create project from extension | `Backend/app/api/projects.py` |
| Frontend | Graph viewer that reads nodes from the same DB | `frontend/app/graph/` |

### The Gap (What We Actually Need to Build)

The extension today only calls `POST /materials`. It does **not** call `POST /graph/ingest/video`, so no graph nodes are created.

**Total new code needed:**
- ~60 lines of JS in the extension (`popup.js` — new button + new API call)
- ~20 lines of HTML (a small results panel showing extracted topics)
- ~10 lines of CSS (topic tag chips)
- Optionally: a thin new backend endpoint to do material + ingest in one shot (saves one round-trip, nice-to-have)

**This is a 4–6 hour build, not a multi-day one.**

---

## Architecture (Minimal Flow)

```
[YouTube Tab]
     │
     ▼
[Extension Popup]
  - Detects YouTube URL automatically
  - Loads project list from GET /projects
  - User picks project (or creates one via POST /projects)
  - User clicks "Add to Graph"
     │
     ▼  POST /api/v1/graph/ingest/video
     {
       project_id, video_url, title (tab.title),
       transcript: ""   ← backend fetches it
     }
     │
     ▼
[Backend: graph.py /graph/ingest/video]
  1. fetch_youtube_transcript(video_url)       ← already works
  2. extract_topics_from_text(transcript)      ← already works
  3. Upsert chapter node + topic nodes + edges ← already works
  4. Return { topics, chapter_node_id, graph } ← already works
     │
     ▼
[Extension Popup]
  - Renders extracted topic chips
  - Shows "N nodes added to <project>" status
     │
     ▼
[Main App — Graph View]
  - User refreshes / navigates to graph
  - New nodes are visible immediately (same DB)
```

---

## What We Build: Scope for the Hackathon

### Phase 1 — Core Flow (must-have, ~3 hrs)

- [ ] **New "Add to Graph" button** in the extension popup  
  - Visible only when on a YouTube URL (use existing `isYouTubeUrl()`)
  - Calls `POST /api/v1/graph/ingest/video` with `{ project_id, video_url, title }`
  - Shows a loading state ("Extracting topics…")

- [ ] **Results panel** in the popup  
  - Renders extracted topic names as chips/tags
  - Shows "X nodes added · Y edges created"
  - Shows a deep-link: "Open in Graphbit →" pointing to `<frontend_url>/graph?project_id=...`

- [ ] **Project creation flow** (already exists in popup, just confirm it still works end-to-end with the new button)

### Phase 2 — Polish (nice-to-have, ~1–2 hrs)

- [ ] **Duplicate guard** — if user hits the same video twice, show "Already in graph" instead of re-ingesting (backend already deduplicates nodes, just surface the response)
- [ ] **Topic preview before confirm** — call `POST /materials/youtube/transcript-check` first, show topics in a preview state, user confirms → then call ingest. (Backend endpoint already exists at `POST /api/v1/materials/youtube/transcript-check`)
- [ ] **Progress indicator** — transcript fetch can take 2–4 s; animate the status line
- [ ] **Auth token passthrough** — if the app uses JWT, pipe it from `chrome.storage` to the `Authorization` header

---

## API Calls Used

### Primary (new for this feature)

```
POST /api/v1/graph/ingest/video
Body:
{
  "project_id": "project-abc",
  "video_url":  "https://www.youtube.com/watch?v=VIDEO_ID",
  "title":      "MIT 6.006 Lecture 1: Algorithms"
}

Response:
{
  "chapter_node_id": "chapter_1",
  "chapter_created": true,
  "topics": [
    { "topic": "Dynamic Programming", "node_id": "topic_dynamic_programming", "created": true },
    ...
  ],
  "edges_added": 5,
  "graph": { ... }
}
```

### Already wired (extension already uses these)

```
GET  /api/v1/projects                 → populate project dropdown
POST /api/v1/projects                 → create new project
```

### Optional preview step (Phase 2)

```
POST /api/v1/materials/youtube/transcript-check
Body: { "link": "https://www.youtube.com/watch?v=..." }
Response: { "has_transcript": true, "transcript_text": "...", "chunks": [...] }
```

---

## File Change Map

| File | Change Type | What |
|---|---|---|
| `extension/popup.js` | **Edit** | Add `ingestVideoToGraph()` function; add new button click handler; render topic chips in result panel |
| `extension/popup.html` | **Edit** | Add `<button id="ingestBtn">` (YouTube-only); add `<div id="topicsResult">` panel |
| `extension/popup.css` | **Edit** | Add `.topic-chip`, `.topics-grid`, `.ingest-result` styles |
| `Backend/app/api/graph.py` | No change needed | Endpoint already complete |
| `Backend/app/api/materials.py` | No change needed | Transcript check endpoint already complete |
| `Backend/app/api/projects.py` | No change needed | |
| `frontend/` | No change needed | Graph view already reads from same DB |

**Total files changed: 3 (all in `extension/`).**

---

## Risks & Mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| YouTube blocks transcript fetch (private/restricted video) | Medium | Show clear error: "This video has no captions/transcript" |
| Topic extraction returns garbage (keyword fallback) | Low-Medium | Backend already has OpenAI → HF → keyword cascade; even keyword fallback produces reasonable results |
| CORS blocking extension → localhost | Low | `manifest.json` already has `host_permissions` for `localhost:8000` |
| Slow transcript fetch (3–5 s) | Certain | Show animated "Fetching transcript…" status; already have `setBusy()` helper |
| Duplicate nodes on re-ingest | None | Backend already deduplicates with `_topic_index_by_key` and `_chapter_index_by_source` |

---

## Hackathon Execution Order

```
Hour 0–1  │ Add ingestBtn to popup.html, wire click handler in popup.js
           │ Call /graph/ingest/video, handle response, render topic chips
Hour 1–2  │ CSS polish for topic chips + ingest result panel
           │ Test end-to-end: YouTube → nodes visible in frontend graph
Hour 2–3  │ Edge cases: no transcript, no project selected, network error
           │ "Open in Graphbit →" deep-link in result panel
Hour 3–4  │ (Phase 2) Add transcript-check preview modal
           │ (Phase 2) Duplicate detection messaging
Hour 4+   │ Demo prep, screenshots, README update
```

---

## Demo Script (for judges)

1. Open `https://www.youtube.com/watch?v=<any lecture video>`
2. Click the Graphbit extension icon
3. Badge reads **"YouTube tab"** automatically
4. Select project (or type a new name → project created live)
5. Click **"Add to Graph"**
6. Extension shows "Fetching transcript…" → "Extracting topics…"
7. Topic chips appear: `[ Dynamic Programming ] [ Recursion ] [ Time Complexity ] …`
8. Click **"Open in Graphbit →"**
9. Frontend graph view shows new nodes — connected, live

**Total user clicks: 3. No copy-paste. No manual tagging.**

---

## Non-Goals (explicitly out of scope for hackathon)

- Timestamp-linked nodes (linking a node to a specific moment in the video)
- Bulk import of YouTube playlists
- OAuth / multi-user auth from the extension
- Mobile support
- Offline / service worker caching
