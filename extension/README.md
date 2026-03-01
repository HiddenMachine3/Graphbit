# Graphbit Browser Extension

This extension captures material from the current browser tab and sends it to Graphbit backend.

- On YouTube tabs: sends `source_url` (backend auto-imports transcript).
- On other pages (including `file://` HTML): sends page text as `content_text`.
- On YouTube tabs: can also run **in-video quizzes** (25-minute transcript chunks, 2 questions per chunk).

## Files

- `manifest.json`
- `popup.html`
- `popup.css`
- `popup.js`

## Load in Chrome / Edge

1. Open extension manager:
   - Chrome: `chrome://extensions`
   - Edge: `edge://extensions`
2. Enable **Developer mode**.
3. Click **Load unpacked**.
4. Select this folder: `Graphbit/extension`.

## First-time setup in popup

1. Click **Advanced Settings** and set **Backend URL** (default: `http://localhost:8000/api/v1`).
2. Click **Refresh** to load existing projects.
3. Select a project from the **Project** dropdown.
4. To create a new project, expand the **Project** dropdown and choose **+ Create new project**.
4. Optionally set **Created By** in Advanced Settings.
5. Click **Save Defaults**.

## Usage

1. Open a YouTube video or any HTML page.
2. Click the extension icon.
3. Click **Add Current Page as Material**.
4. Confirm success in status message and **Last Added** card.

### In-video quiz on YouTube

1. Open a YouTube video tab.
2. Click the extension icon.
3. Click **Start In-Video Quiz**.
4. The extension fetches transcript segments, splits them into chunks of at most 25 minutes, and calls `POST /qa/generate` with `n=2` for each chunk.
5. During playback, the video pauses at each chunk boundary and prompts 2 questions, then resumes.

You can change both values in the popup under **Quiz Settings**:

- **Chunk Size (minutes)**
- **Questions per Chunk**

## Local HTML files (`file://`)

For local files, browser extensions usually need explicit permission:

- In extension details, enable **Allow access to file URLs**.

## Backend requirement

The backend must be running and reachable from browser.

Typical dev command:

```powershell
cd Backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
