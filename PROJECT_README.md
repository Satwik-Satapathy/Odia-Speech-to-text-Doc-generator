# Project Guide: Odia Voice Papers

## Project Overview

Odia Voice Papers is a browser-based tool that turns a short Odia audio recording into an editable document. Users can record audio with their microphone or select an existing audio file. The application submits the completed audio as a batch transcription job to Sarvam Saaras, displays the resulting Odia transcript for editing, and lets users download it in common document formats.

The project is built around a simple capture-to-document workflow: a vanilla HTML, CSS, and JavaScript frontend communicates with a Python FastAPI backend. The backend validates audio, keeps the Sarvam API key out of the browser, manages transcription jobs and document versions in SQLite, and generates exports.

## Pain Points Addressed

- **Manual transcription takes time:** Converts an Odia voice recording into a text draft using speech recognition.
- **Audio-to-document work is fragmented:** Combines recording or file selection, transcription, editing, and downloading in one workflow.
- **Transcription results need correction:** Provides an editable transcript rather than treating the machine-generated result as final.
- **Odia text needs Unicode-aware handling:** Keeps the transcript as Unicode Odia text and uses the Kalinga font in DOCX exports.
- **Long or oversized uploads can fail:** Applies a 10-minute and 4 MB audio limit that fits the current deployment request-size constraint.

## Features

- Record microphone audio in the browser as WebM/Opus, or upload a supported audio file.
- Enter a document title before submitting the audio.
- Validate supported formats, file size, and audio duration in the interface and backend.
- Submit Odia (`od-IN`) transcription jobs to Sarvam Saaras v3 in batch mode.
- Show job state and progress while the application checks for results.
- View the transcript and any returned segment timing or speaker labels.
- Search transcript segments and edit the document text.
- Autosave edits as document versions in the backend.
- Retry a failed transcription, subject to the three-attempt limit.
- Download the transcript as DOCX, Markdown, or plain text.
- Load a sample transcript to explore the editor without submitting audio.
- Keep active job identifiers in browser storage so a page refresh can resume checking an eligible in-progress job.

## User Flows

### 1. Transcribe a recording or audio file

1. Give the document a title.
2. Record audio with the microphone, or choose an existing supported audio file.
3. Keep the audio within 10 minutes and 4 MB.
4. Start batch transcription. The browser uploads the audio, and the backend submits it to Sarvam with Odia selected.
5. Follow the job status in the capture panel while the page checks for completion.
6. When the transcript is ready, review the text and any available transcript segments in the editor.

### 2. Edit and export a transcript

1. Correct or rewrite the generated text in the editor.
2. Wait for the autosave status to confirm the edit was saved.
3. Choose DOCX, MD, or TXT to download the current editor content.

### 3. Recover from a failed job

1. Read the failure message shown with the job status.
2. Use the retry action if it is available. Failed jobs can be retried up to three attempts.
3. Keep the page open while the retried batch job is being checked.

### 4. Preview the editor

Choose the sample-document action to put example Odia text in the editor. This is a local preview; it does not submit an audio job.

## Scope Notes

- Transcription is batch-based: recordings are uploaded as completed files, not streamed live to Sarvam.
- The current workflow targets Odia transcription. Translation and transliteration are not part of this flow.
- Active job tracking can resume after refresh when the browser has a stored job reference. The interface does not currently provide a document library for browsing all saved documents.
- Local SQLite storage is appropriate for development and low-volume use. On Vercel, the database uses ephemeral storage, so it is not a durable document archive.