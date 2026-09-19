const state = { file: null, jobId: null, documentId: null, externalJobId: null, recording: false, recorder: null, parts: [], poll: null, segments: [] };
const $ = (id) => document.getElementById(id);
const title = $("title"), fileInput = $("file-input"), filePill = $("file-pill"), recordButton = $("record-button"), submitButton = $("submit-button"), editor = $("document-editor"), jobState = $("job-state"), jobMessage = $("job-message"), jobIdText = $("job-id"), progressWrap = $("progress-wrap"), progressBar = $("progress-bar"), saveState = $("save-state"), characterCount = $("character-count"), segmentCount = $("segment-count"), segmentList = $("segment-list"), segmentSearch = $("segment-search"), retryButton = $("retry-button");
let saveTimer;

function setJob(stateName, message, progress = 0) { jobState.textContent = stateName; jobState.className = `job-state ${stateName}`; jobMessage.textContent = message; progressBar.style.width = `${progress}%`; progressWrap.classList.toggle("hidden", stateName === "idle" || stateName === "ready" || stateName === "failed"); retryButton.classList.toggle("hidden", stateName !== "failed"); }
function showFile(file) { if (file.size > 4000000) { setJob("failed", "ଫାଇଲ୍ 4 MB ରୁ ଛୋଟ ହେବା ଆବଶ୍ୟକ"); submitButton.disabled = true; return; } state.file = file; filePill.innerHTML = `<span>♫</span><strong>${file.name}</strong><small>${(file.size / 1024 / 1024).toFixed(1)} MB</small>`; filePill.classList.remove("hidden"); submitButton.disabled = false; setJob("idle", `${file.name} ପ୍ରସ୍ତୁତ ଅଛି`); }
fileInput.addEventListener("change", async (event) => { const file = event.target.files[0]; if (!file) return; const duration = await readDuration(file); if (duration && duration > 600) { setJob("failed", "ଅଡିଓ ସେସନ୍ 10 ମିନିଟ୍ ରୁ ଅଧିକ ହୋଇପାରିବ ନାହିଁ"); submitButton.disabled = true; return; } showFile(file); });
title.addEventListener("input", () => { $("document-title").textContent = title.value || "ନୂଆ ଭଏସ୍ ନୋଟ୍"; });
editor.addEventListener("input", () => { characterCount.textContent = `${editor.value.length} characters`; saveState.textContent = "Edited locally"; clearTimeout(saveTimer); if (state.documentId) saveTimer = setTimeout(async () => { const response = await fetch(`/api/documents/${state.documentId}/content`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ content: editor.value }) }); saveState.textContent = response.ok ? "Autosaved" : "Autosave failed"; }, 700); });

recordButton.addEventListener("click", async () => {
  if (state.recording) { state.recorder.stop(); state.recording = false; recordButton.innerHTML = "<span>●</span> ରେକର୍ଡ କରନ୍ତୁ"; return; }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const mimeType = ["audio/webm;codecs=opus", "audio/webm"].find((type) => MediaRecorder.isTypeSupported(type));
    if (!mimeType) { stream.getTracks().forEach((track) => track.stop()); setJob("failed", "ଏହି browser ରେ WebM/Opus recording support ନାହିଁ"); return; }
    state.parts = []; state.recorder = new MediaRecorder(stream, { mimeType, audioBitsPerSecond: 48000 }); state.recording = true;
    state.recorder.ondataavailable = (event) => state.parts.push(event.data);
    state.recorder.onstop = async () => { stream.getTracks().forEach((track) => track.stop()); const file = new File(state.parts, "odia-recording.webm", { type: "audio/webm" }); const duration = await readDuration(file); if (duration > 600 || file.size > 4000000) { setJob("failed", "ରେକର୍ଡିଂ 10 ମିନିଟ୍ କିମ୍ବା 4 MB ସୀମା ଅତିକ୍ରମ କରିଛି"); return; } showFile(file); };
    state.recorder.start(); recordButton.innerHTML = "<span>■</span> ବନ୍ଦ କରନ୍ତୁ"; recordButton.classList.add("recording"); setJob("recording", "ରେକର୍ଡିଂ ଚାଲୁଛି...");
  } catch (error) { setJob("failed", "ମାଇକ୍ରୋଫୋନ୍ ଅନୁମତି ମିଳିଲା ନାହିଁ"); }
});

async function readDuration(file) { return new Promise((resolve) => { const audio = document.createElement("audio"); audio.preload = "metadata"; audio.onloadedmetadata = () => { URL.revokeObjectURL(audio.src); resolve(Number.isFinite(audio.duration) ? audio.duration : null); }; audio.onerror = () => resolve(null); audio.src = URL.createObjectURL(file); }); }
submitButton.addEventListener("click", async () => {
  if (!state.file) return;
  const duration = await readDuration(state.file);
  if (duration && duration > 600) { setJob("failed", "ଅଡିଓ ସେସନ୍ 10 ମିନିଟ୍ ରୁ ଅଧିକ ହୋଇପାରିବ ନାହିଁ"); return; }
  if (state.file.size > 4000000) { setJob("failed", "ଫାଇଲ୍ 4 MB ରୁ ଛୋଟ ହେବା ଆବଶ୍ୟକ"); return; }
  submitButton.disabled = true; setJob("uploading", "ଅଡିଓ ଅପଲୋଡ୍ ହେଉଛି...", 8);
  const form = new FormData(); form.append("title", title.value); if (duration) form.append("duration_seconds", String(duration)); form.append("file", state.file);
  try {
    const response = await fetch("/api/documents", { method: "POST", body: form });
    if (!response.ok) throw new Error(await response.text());
    const result = await response.json(); state.documentId = result.document_id; state.jobId = result.job_id; state.externalJobId = result.external_job_id; localStorage.setItem("odiaVoiceJob", JSON.stringify({ documentId: state.documentId, jobId: state.jobId, externalJobId: state.externalJobId })); jobIdText.textContent = `Job ${state.jobId.slice(0, 8)}...`; setJob("queued", "Sarvam batch job ଧାଡ଼ିରେ ଅଛି...", 15); pollJob();
  } catch (error) { submitButton.disabled = false; setJob("failed", error.message || "ଅପଲୋଡ୍ ବିଫଳ ହେଲା"); }
});

function renderSegments(segments) { state.segments = segments; const query = segmentSearch.value.trim().toLowerCase(); segmentList.innerHTML = segments.filter((segment) => !query || segment.text.toLowerCase().includes(query)).map((segment) => { const start = segment.start_seconds == null ? "" : `${Number(segment.start_seconds).toFixed(1)}s`; const speaker = segment.speaker_id ? ` · ${segment.speaker_id}` : ""; return `<div class="segment-chip"><small>${start}${speaker}</small>${segment.text}</div>`; }).join(""); }
function pollJob() { clearInterval(state.poll); state.poll = setInterval(async () => { const query = state.externalJobId ? `?external_job_id=${encodeURIComponent(state.externalJobId)}&document_id=${encodeURIComponent(state.documentId)}` : ""; const response = await fetch(`/api/transcription-jobs/${state.jobId}${query}`); if (!response.ok) return; const result = await response.json(); setJob(result.state === "completed" || result.state === "partially_completed" ? "ready" : result.state, result.state === "processing" || result.state === "running" ? "Sarvam batch job ଚାଲୁଛି..." : result.error_message || "ଟ୍ରାନ୍ସକ୍ରିପ୍ଟ ପ୍ରସ୍ତୁତ", result.progress || 0); if (result.state === "completed" || result.state === "partially_completed") { clearInterval(state.poll); editor.value = result.transcript || ""; characterCount.textContent = `${editor.value.length} characters`; segmentCount.textContent = `${(result.segments || []).length} segments`; renderSegments(result.segments || []); saveState.textContent = "Saved locally"; localStorage.setItem("odiaVoiceTranscript", editor.value); } if (result.state === "failed" || result.state === "rejected") { clearInterval(state.poll); submitButton.disabled = false; } }, 5000); }

segmentSearch.addEventListener("input", () => renderSegments(state.segments));
retryButton.addEventListener("click", async () => { const response = await fetch(`/api/transcription-jobs/${state.jobId}/retry`, { method: "POST" }); if (response.ok) { setJob("queued", "ପୁଣି batch job ଆରମ୍ଭ ହେଉଛି...", 15); pollJob(); } });

$("sample-button").addEventListener("click", () => { const text = "ଏହା ଆମର ଓଡ଼ିଆ ଭାଷାର ଏକ ନମୁନା ଡକ୍ୟୁମେଣ୍ଟ। ଆପଣ ଏଠାରେ ନିଜର ଟ୍ରାନ୍ସକ୍ରିପ୍ଟ ସମ୍ପାଦନ କରିପାରିବେ।"; editor.value = text; characterCount.textContent = `${text.length} characters`; segmentCount.textContent = "1 segment"; setJob("ready", "ସମ୍ପାଦନ ପାଇଁ ନମୁନା ଲୋଡ୍ ହେଲା", 100); saveState.textContent = "Saved locally"; });

document.querySelectorAll("[data-format]").forEach((button) => button.addEventListener("click", async () => { const format = button.dataset.format; if (!editor.value) return; const response = state.documentId ? await fetch(`/api/documents/${state.documentId}/exports`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ format, content: editor.value, title: title.value }) }) : null; const blob = response ? await response.blob() : new Blob([editor.value], { type: "text/plain;charset=utf-8" }); const url = URL.createObjectURL(blob); const link = document.createElement("a"); link.href = url; link.download = `${title.value || "odia-document"}.${format === "docx" && !response ? "txt" : format}`; link.click(); URL.revokeObjectURL(url); }));

const savedJob = JSON.parse(localStorage.getItem("odiaVoiceJob") || "null");
if (savedJob?.jobId && savedJob?.externalJobId) { state.documentId = savedJob.documentId; state.jobId = savedJob.jobId; state.externalJobId = savedJob.externalJobId; jobIdText.textContent = `Job ${state.jobId.slice(0, 8)}...`; setJob("running", "ପୂର୍ବରୁ ଆରମ୍ଭ ହୋଇଥିବା batch job ଯାଞ୍ଚ ହେଉଛି...", 70); const savedTranscript = localStorage.getItem("odiaVoiceTranscript"); if (savedTranscript) { editor.value = savedTranscript; characterCount.textContent = `${editor.value.length} characters`; } pollJob(); }
