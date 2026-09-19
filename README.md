# Odia Voice Papers

Batch-first Odia speech-to-text document generator using a vanilla HTML, CSS, and JavaScript frontend. The browser records WebM/Opus audio at 48 kbps or uploads a supported file, then the FastAPI backend submits it to Sarvam's Batch Speech-to-Text API.

## Requirements

- Python 3.11+
- Sarvam API key in `SARVAM_API_KEY`

Audio input is intentionally limited to **10 minutes and 4 MB**. Browser recordings use WebM/Opus at 48 kbps. This keeps uploads below Vercel's 4.5 MB Function request-body limit without external file storage. Generated DOCX files use the **Kalinga** font for headings and transcript content.

Sarvam returns Unicode Odia text and does not support or emit font-specific Akruti encoding. Akruti is therefore not added to the export options; using it would require a separate, tested Unicode-to-Akruti conversion layer and an installed Akruti font on the viewing machine.

## Run the app

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
$env:SARVAM_API_KEY = "your-key"
uvicorn backend.app.main:app --reload --port 8000
```

Open http://127.0.0.1:8000. FastAPI serves the static frontend and the `/api` endpoints; no Node.js runtime is required.

## Vercel

The repository includes a Python serverless entrypoint in `api/index.py` and static-file routing in `vercel.json`. For Vercel Hobby compatibility, the browser polls Sarvam job status through the backend; no Vercel Cron Job is required.

Set these Vercel environment variables:

- `SARVAM_API_KEY`
Keep the browser page open until the batch transcript completes. Vercel Hobby does not support frequent Cron Jobs, so closing the page stops status polling. The current SQLite repository is suitable for a personal, low-volume deployment only; Vercel functions have ephemeral filesystems, so documents and jobs are not guaranteed to survive across instances or redeployments. This design deliberately uses no external storage and limits audio uploads to 4 MB.

Deploy from the repository root with the Vercel dashboard or `vercel` CLI. No Node.js build step is required for the application runtime.
