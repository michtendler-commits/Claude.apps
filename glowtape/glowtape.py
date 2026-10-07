#!/usr/bin/env python3
"""GLOWTAPE — a retro neon text-to-video maker on OpenAI's Sora 2 API.

Everything is in this one file. It starts a tiny local server that shows the
app at http://localhost:8788 and passes the app's requests on to OpenAI, so
the browser never calls OpenAI directly (browsers block that for local files).

Run:  python3 glowtape.py
"""
import http.server
import json
import ssl
import sys
import urllib.error
import urllib.request
import webbrowser

PORT = 8788
OPENAI = "https://api.openai.com"
FORWARD_HEADERS = ("authorization", "content-type")

PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>GLOWTAPE</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Monoton&family=VT323&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #0d0221;
    --pink: #ff2a6d;
    --cyan: #05d9e8;
    --purple: #b967ff;
    --yellow: #fffb96;
    --text: #f6e7ff;
    --dim: #8a7aa8;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  html, body { background: var(--bg); }
  body {
    color: var(--text);
    font-family: 'VT323', 'Courier New', monospace;
    font-size: 20px;
    min-height: 100vh;
    overflow-x: hidden;
    background:
      radial-gradient(ellipse at 50% 0%, rgba(185,103,255,.25), transparent 60%),
      var(--bg);
  }
  /* Synthwave floor grid */
  body::before {
    content: ''; position: fixed; left: -50%; right: -50%; bottom: 0; height: 45vh;
    background-image:
      linear-gradient(rgba(255,42,109,.55) 1px, transparent 1px),
      linear-gradient(90deg, rgba(255,42,109,.55) 1px, transparent 1px);
    background-size: 60px 40px;
    transform: perspective(300px) rotateX(60deg);
    transform-origin: bottom;
    animation: grid 2.5s linear infinite;
    mask-image: linear-gradient(to top, #000 10%, transparent);
    -webkit-mask-image: linear-gradient(to top, #000 10%, transparent);
    pointer-events: none; z-index: 0;
  }
  @keyframes grid { to { background-position: 0 40px, 0 0; } }
  /* Scanlines over everything */
  body::after {
    content: ''; position: fixed; inset: 0; pointer-events: none; z-index: 50;
    background: repeating-linear-gradient(to bottom, rgba(0,0,0,.18) 0 1px, transparent 1px 3px);
  }
  button, input, textarea, select { font: inherit; color: inherit; }
  button { cursor: pointer; }

  .wrap {
    position: relative; z-index: 1;
    max-width: 760px; margin: 0 auto; padding: 22px 16px 60px;
    display: flex; flex-direction: column; align-items: center; gap: 20px;
  }
  h1 {
    font-family: 'Monoton', cursive; font-weight: 400;
    font-size: clamp(42px, 11vw, 78px); letter-spacing: 4px;
    color: var(--pink);
    text-shadow: 0 0 6px var(--pink), 0 0 22px var(--pink), 0 0 44px var(--purple);
    animation: flicker 6s infinite;
  }
  @keyframes flicker {
    0%, 93%, 96%, 100% { opacity: 1; }
    94%, 95% { opacity: .55; }
  }
  .tagline { color: var(--cyan); text-shadow: 0 0 8px var(--cyan); margin-top: -14px; letter-spacing: 3px; }
  .key-btn {
    position: absolute; top: 18px; right: 16px;
    background: none; border: 1px solid var(--dim); color: var(--dim);
    padding: 2px 10px; font-size: 16px;
  }
  .key-btn:hover { color: var(--cyan); border-color: var(--cyan); }

  /* CRT screen */
  .tv {
    width: 100%; padding: 14px; border-radius: 22px;
    background: linear-gradient(145deg, #2a1650, #150a2e);
    border: 2px solid var(--purple);
    box-shadow: 0 0 18px rgba(185,103,255,.6), inset 0 0 20px rgba(0,0,0,.6);
  }
  .screen {
    position: relative; aspect-ratio: 16 / 9; width: 100%;
    background: #05010d; border-radius: 14px; overflow: hidden;
    display: flex; align-items: center; justify-content: center; text-align: center;
    box-shadow: inset 0 0 40px rgba(5,217,232,.25);
  }
  .screen.portrait { aspect-ratio: 9 / 16; max-height: 70vh; width: auto; margin: 0 auto; }
  .screen video { width: 100%; height: 100%; object-fit: contain; }
  .noise {
    position: absolute; inset: -50%; opacity: .12;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='120' height='120'%3E%3Cfilter id='n'%3E%3CfeTurbulence baseFrequency='.9' numOctaves='2'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
    animation: noise .3s steps(3) infinite;
  }
  @keyframes noise { 0% { transform: translate(0,0); } 33% { transform: translate(-8%,5%); } 66% { transform: translate(6%,-7%); } }
  .screen-msg { position: relative; padding: 16px; font-size: 26px; color: var(--cyan); text-shadow: 0 0 8px var(--cyan); }
  .screen-msg small { display: block; font-size: 18px; color: var(--dim); text-shadow: none; margin-top: 6px; }
  .screen-msg.error { color: var(--pink); text-shadow: 0 0 8px var(--pink); }
  .rec { color: var(--pink); text-shadow: 0 0 8px var(--pink); animation: blink 1s steps(2) infinite; }
  @keyframes blink { 50% { opacity: 0; } }
  .meter { width: min(320px, 70vw); height: 14px; border: 2px solid var(--cyan); margin: 10px auto 0; padding: 2px; }
  .meter div { height: 100%; width: 0; background: var(--cyan); box-shadow: 0 0 10px var(--cyan); transition: width .6s; }

  /* The four buttons */
  .deck { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; width: 100%; }
  .pad {
    position: relative; min-width: 0; min-height: 84px; padding: 10px 8px;
    background: rgba(13,2,33,.85); border: 2px solid var(--c); border-radius: 12px;
    color: var(--c); text-shadow: 0 0 8px var(--c);
    box-shadow: 0 0 10px var(--c), inset 0 0 10px rgba(0,0,0,.5);
    font-size: 22px; letter-spacing: 2px;
    display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 2px;
    transition: transform .1s, box-shadow .2s;
  }
  .pad:hover { box-shadow: 0 0 22px var(--c), inset 0 0 14px rgba(0,0,0,.5); }
  .pad:active { transform: scale(.97); }
  .pad .icon { font-size: 28px; line-height: 1; }
  .pad .sub {
    font-size: 15px; color: var(--text); text-shadow: none; letter-spacing: 0; opacity: .75;
    max-width: 100%; overflow: hidden; white-space: nowrap; text-overflow: ellipsis;
  }
  .pad img.thumb { position: absolute; top: 6px; right: 6px; width: 30px; height: 30px; object-fit: cover; border-radius: 6px; border: 1px solid var(--c); }
  .p-prompt { --c: var(--cyan); }
  .p-photo { --c: var(--purple); }
  .p-char { --c: var(--yellow); }
  .create {
    --c: var(--pink);
    grid-column: 1 / -1; min-height: 76px;
    font-family: 'Monoton', cursive; font-size: 34px; letter-spacing: 6px;
    background: linear-gradient(180deg, rgba(255,42,109,.25), rgba(13,2,33,.9));
  }
  .create:disabled { opacity: .5; cursor: wait; }

  /* Tape shelf */
  .shelf { width: 100%; }
  .shelf h2 { font-weight: 400; font-size: 22px; color: var(--purple); text-shadow: 0 0 8px var(--purple); margin-bottom: 8px; letter-spacing: 2px; }
  .tapes { display: flex; gap: 10px; overflow-x: auto; padding: 10px 10px 6px 0; }
  .tape {
    flex: 0 0 150px; width: 150px; min-width: 0; text-align: left; padding: 8px 10px; position: relative;
    background: #1b0d36; border: 1px solid var(--dim); border-radius: 6px;
  }
  .tape.active { border-color: var(--cyan); box-shadow: 0 0 10px var(--cyan); }
  .tape .label {
    background: var(--yellow); color: #1b0d36; font-size: 16px; padding: 2px 6px; border-radius: 2px;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }
  .tape .reels { display: flex; justify-content: space-around; margin-top: 8px; }
  .tape .reels span { width: 22px; height: 22px; border-radius: 50%; border: 3px dashed var(--dim); }
  .tape.busy .reels span { animation: spin 2s linear infinite; border-color: var(--pink); }
  .tape .state { font-size: 15px; color: var(--dim); margin-top: 4px; }
  .tape .x { position: absolute; top: -8px; right: -8px; width: 22px; height: 22px; border-radius: 50%; background: var(--bg); border: 1px solid var(--dim); font-size: 14px; line-height: 1; display: none; }
  .tape:hover .x { display: block; }
  @keyframes spin { to { transform: rotate(360deg); } }
  .empty-shelf { color: var(--dim); font-size: 18px; }

  /* Dialogs */
  dialog {
    margin: auto; width: min(480px, calc(100% - 32px));
    background: #150a2e; color: var(--text);
    border: 2px solid var(--c, var(--cyan)); border-radius: 14px; padding: 18px;
    box-shadow: 0 0 24px var(--c, var(--cyan));
  }
  dialog::backdrop { background: rgba(5,1,13,.75); }
  dialog h3 { font-weight: 400; font-size: 28px; color: var(--c, var(--cyan)); text-shadow: 0 0 8px var(--c, var(--cyan)); letter-spacing: 2px; }
  dialog p { color: var(--dim); font-size: 18px; margin: 4px 0 12px; }
  dialog label { display: block; color: var(--dim); font-size: 17px; margin: 10px 0 4px; }
  dialog input[type=text], dialog input[type=password], dialog textarea, dialog select {
    width: 100%; background: #0d0221; border: 1px solid var(--dim); border-radius: 8px;
    padding: 8px 10px; outline: none; font-size: 20px;
  }
  dialog textarea { min-height: 120px; resize: vertical; }
  dialog input:focus, dialog textarea:focus, dialog select:focus { border-color: var(--c, var(--cyan)); }
  dialog .row { display: flex; gap: 10px; justify-content: flex-end; margin-top: 14px; flex-wrap: wrap; }
  dialog .grid3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
  .btn {
    background: none; border: 1px solid var(--dim); border-radius: 8px; padding: 4px 14px; font-size: 20px;
  }
  .btn:hover { border-color: var(--text); }
  .btn.go { border-color: var(--c, var(--cyan)); color: var(--c, var(--cyan)); text-shadow: 0 0 6px var(--c, var(--cyan)); }
  .btn.warn:hover { border-color: var(--pink); color: var(--pink); }
  #promptDialog { --c: var(--cyan); }
  #charDialog, #charEdit { --c: var(--yellow); }
  #keyDialog { --c: var(--pink); }
  a { color: var(--cyan); }

  .chars { display: flex; flex-direction: column; gap: 8px; margin-top: 6px; max-height: 280px; overflow-y: auto; }
  .char {
    display: flex; align-items: center; gap: 10px; padding: 6px 8px;
    border: 1px solid var(--dim); border-radius: 8px; cursor: pointer; text-align: left; background: none; width: 100%;
  }
  .char.on { border-color: var(--yellow); box-shadow: 0 0 8px var(--yellow); }
  .char .face { width: 40px; height: 40px; border-radius: 8px; background: #2a1650; object-fit: cover; flex: none; display: flex; align-items: center; justify-content: center; }
  .char .who { flex: 1; min-width: 0; }
  .char .who b { font-weight: 400; color: var(--yellow); }
  .char .who div { font-size: 16px; color: var(--dim); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .char .tick { color: var(--yellow); width: 20px; }
  .char .edit { font-size: 16px; color: var(--dim); padding: 0 4px; }
  .face-pick { display: flex; align-items: center; gap: 10px; }
  .face-pick img { width: 48px; height: 48px; border-radius: 8px; object-fit: cover; }

  .toast {
    position: fixed; left: 50%; bottom: 18px; transform: translateX(-50%); z-index: 60;
    background: #150a2e; border: 1px solid var(--cyan); color: var(--cyan);
    padding: 8px 16px; border-radius: 8px; max-width: calc(100% - 32px); font-size: 19px;
    opacity: 0; pointer-events: none; transition: opacity .25s;
  }
  .toast.show { opacity: 1; }
  .toast.error { border-color: var(--pink); color: var(--pink); }

  @media (max-width: 520px) {
    .wrap { padding-top: 56px; }
    .deck { gap: 8px; }
    .pad { font-size: 18px; min-height: 76px; }
    .create { font-size: 26px; }
  }
  @media (prefers-reduced-motion: reduce) {
    body::before, .noise, h1, .rec, .tape.busy .reels span { animation: none; }
  }
</style>
</head>
<body>
<div class="wrap">
  <button class="key-btn" id="keyBtn">⚙ SETUP</button>
  <h1>GLOWTAPE</h1>
  <div class="tagline">PRESS CREATE · MAKE A MOVIE</div>

  <div class="tv"><div class="screen" id="screen"></div></div>

  <div class="deck">
    <button class="pad p-prompt" id="promptBtn"><span class="icon">✎</span>PROMPT<span class="sub" id="promptSub">tap to write</span></button>
    <button class="pad p-photo" id="photoBtn"><span class="icon">▣</span>ADD PHOTO<span class="sub" id="photoSub">optional</span></button>
    <button class="pad p-char" id="charBtn"><span class="icon">☺</span>ADD CHARACTER<span class="sub" id="charSub">optional</span></button>
    <button class="pad create" id="createBtn">CREATE</button>
  </div>
  <input type="file" id="photoInput" accept="image/png,image/jpeg,image/webp" hidden>

  <div class="shelf">
    <h2>▶ YOUR TAPES</h2>
    <div class="tapes" id="tapes"></div>
  </div>
</div>

<dialog id="promptDialog">
  <h3>✎ PROMPT</h3>
  <p>Describe your video: who, what, where, and how the camera moves.</p>
  <textarea id="promptInput" placeholder="A neon-lit DeLorean racing down a rainy city street at night, camera tracking alongside"></textarea>
  <div class="row">
    <button class="btn" id="ideaBtn">🎲 IDEA</button>
    <button class="btn" data-close>CANCEL</button>
    <button class="btn go" id="promptSave">DONE</button>
  </div>
</dialog>

<dialog id="charDialog">
  <h3>☺ CHARACTERS</h3>
  <p>Tap characters to put them in your next video. They're saved for next time.</p>
  <div class="chars" id="charList"></div>
  <div class="row">
    <button class="btn" id="charNew">+ NEW CHARACTER</button>
    <button class="btn go" data-close>DONE</button>
  </div>
</dialog>

<dialog id="charEdit">
  <h3 id="charEditTitle">NEW CHARACTER</h3>
  <label for="charName">Name</label>
  <input type="text" id="charName" placeholder="Captain Nova" maxlength="40">
  <label for="charDesc">What they look like</label>
  <textarea id="charDesc" placeholder="A tall woman with a silver buzz cut, mirrored aviator sunglasses and a glowing pink leather jacket"></textarea>
  <label>Photo (optional)</label>
  <div class="face-pick">
    <img id="charFace" alt="" hidden>
    <button class="btn" id="charFaceBtn">CHOOSE PHOTO</button>
    <input type="file" id="charFaceInput" accept="image/png,image/jpeg,image/webp" hidden>
  </div>
  <div class="row">
    <button class="btn warn" id="charDelete">DELETE</button>
    <button class="btn" data-close>CANCEL</button>
    <button class="btn go" id="charSave">SAVE</button>
  </div>
</dialog>

<dialog id="keyDialog">
  <h3>⚙ SETUP</h3>
  <p>Paste your OpenAI API key. It's saved only in this browser. Get one at
    <a href="https://platform.openai.com/api-keys" target="_blank" rel="noopener">platform.openai.com/api-keys</a>.
    Videos are billed to your OpenAI account.</p>
  <label for="keyInput">API key</label>
  <input type="password" id="keyInput" placeholder="sk-..." autocomplete="off">
  <div class="grid3">
    <div><label for="modelSel">Quality</label>
      <select id="modelSel"><option value="sora-2">Fast</option><option value="sora-2-pro">Pro</option></select></div>
    <div><label for="secSel">Length</label>
      <select id="secSel"><option value="4">4 sec</option><option value="8">8 sec</option><option value="12">12 sec</option></select></div>
    <div><label for="sizeSel">Shape</label>
      <select id="sizeSel"><option value="1280x720">Wide</option><option value="720x1280">Tall</option></select></div>
  </div>
  <p id="costLine" style="margin-top:10px"></p>
  <div class="row">
    <button class="btn" data-close>CANCEL</button>
    <button class="btn go" id="keySave">SAVE</button>
  </div>
</dialog>

<div class="toast" id="toast"></div>

<script>
// ============================================
// GLOWTAPE — retro neon video maker on Sora 2
// ============================================

const API = '/v1';          // forwarded to OpenAI by glowtape.py
const POLL_MS = 5000;
const PRICE = { 'sora-2': 0.10, 'sora-2-pro': 0.30 };   // approx. USD per second

const IDEAS = [
  'A neon-lit DeLorean racing down a rainy city street at night, camera tracking alongside',
  'A cat in sunglasses roller-skating through an 80s arcade, colorful lights reflecting on the floor',
  'A giant retro robot dancing on a beach at sunset, palm trees swaying, VHS look',
  'Slow drone shot over a glowing synthwave city with a huge pink sun on the horizon',
  'An astronaut playing electric guitar on the moon, Earth rising behind, music video style',
  'A skateboarder doing tricks in an empty mall at night, neon signs flickering',
  'A dolphin jumping through a ring of neon light over a calm purple ocean',
  'Close-up of a cassette tape spinning in a boombox, then the camera pulls back to a rooftop party',
];

const $ = (id) => document.getElementById(id);

// ---------- Storage ----------
const store = {
  get(k, d) { try { const v = localStorage.getItem('gt.' + k); return v === null ? d : JSON.parse(v); } catch { return d; } },
  set(k, v) { try { localStorage.setItem('gt.' + k, JSON.stringify(v)); return true; } catch { return false; } },
};

let dbp;
function idb(mode, fn) {
  dbp = dbp || new Promise((res) => {
    const r = indexedDB.open('glowtape', 1);
    r.onupgradeneeded = () => r.result.createObjectStore('tapes');
    r.onsuccess = () => res(r.result);
    r.onerror = () => res(null);
  });
  return dbp.then(db => db && new Promise((res) => {
    const q = fn(db.transaction('tapes', mode).objectStore('tapes'));
    q.onsuccess = () => res(q.result);
    q.onerror = () => res(null);
  }));
}

// ---------- State ----------
let apiKey = store.get('key', '');
let settings = store.get('settings', { model: 'sora-2', seconds: '8', size: '1280x720' });
let characters = store.get('characters', []);   // {id, name, desc, face (data URL)}
let tapes = store.get('tapes', []);             // newest first
let prompt = store.get('draft', '');
let photo = null;                               // File for the start image
let picked = new Set();                         // character ids in the next video
let current = tapes[0] ? tapes[0].id : null;    // tape shown on screen
const urls = {};
const polling = new Set();

const saveTapes = () => store.set('tapes', tapes);

// ---------- API ----------
async function api(path, opts = {}) {
  if (!apiKey) { openKey(); throw new Error('Add your OpenAI API key in SETUP first.'); }
  let res;
  try {
    res = await fetch(API + path, { ...opts, headers: { Authorization: 'Bearer ' + apiKey, ...(opts.headers || {}) } });
  } catch {
    throw new Error('Lost connection to GLOWTAPE. Is the Terminal window still running glowtape.py?');
  }
  if (!res.ok) {
    let msg = 'Error ' + res.status;
    try { const j = await res.json(); if (j.error && j.error.message) msg = j.error.message; } catch {}
    if (res.status === 401) msg = 'OpenAI rejected your API key. Check it in SETUP.';
    throw new Error(msg);
  }
  return res;
}

// Start images must match the video size exactly: crop to fill.
async function fitImage(src, size) {
  const [w, h] = size.split('x').map(Number);
  const img = await createImageBitmap(src);
  const c = document.createElement('canvas'); c.width = w; c.height = h;
  const s = Math.max(w / img.width, h / img.height);
  c.getContext('2d').drawImage(img, (w - img.width * s) / 2, (h - img.height * s) / 2, img.width * s, img.height * s);
  return new Promise(r => c.toBlob(r, 'image/png'));
}

// Multipart body built by hand as bytes (works in every browser and viewer).
async function multipart(fields) {
  const b = '----glowtape' + Math.random().toString(36).slice(2);
  const enc = new TextEncoder(), parts = [];
  for (const [name, v] of Object.entries(fields)) {
    if (v == null) continue;
    if (v instanceof Blob) {
      parts.push(enc.encode(`--${b}\r\nContent-Disposition: form-data; name="${name}"; filename="start.png"\r\nContent-Type: image/png\r\n\r\n`));
      parts.push(new Uint8Array(await v.arrayBuffer()), enc.encode('\r\n'));
    } else {
      parts.push(enc.encode(`--${b}\r\nContent-Disposition: form-data; name="${name}"\r\n\r\n${v}\r\n`));
    }
  }
  parts.push(enc.encode(`--${b}--\r\n`));
  const out = new Uint8Array(parts.reduce((n, p) => n + p.length, 0));
  let o = 0; for (const p of parts) { out.set(p, o); o += p.length; }
  return { body: out.buffer, type: `multipart/form-data; boundary=${b}` };
}

// ---------- Create ----------
function fullPrompt() {
  const cast = characters.filter(c => picked.has(c.id));
  if (!cast.length) return prompt;
  const lines = cast.map(c => `- ${c.name}: ${c.desc || 'as shown in the reference image'}`);
  return `${prompt}\n\nCharacters in this video (keep their appearance consistent):\n${lines.join('\n')}`;
}

async function create() {
  if (!prompt.trim()) { toast('Write a PROMPT first.', true); openPrompt(); return; }
  const btn = $('createBtn');
  btn.disabled = true; btn.textContent = 'SENDING';
  try {
    // Your photo wins; otherwise use the first picked character's photo as the start image.
    const face = characters.find(c => picked.has(c.id) && c.face);
    const start = photo || (face ? await (await fetch(face.face)).blob() : null);
    const { body, type } = await multipart({
      model: settings.model, prompt: fullPrompt(), seconds: settings.seconds, size: settings.size,
      input_reference: start ? await fitImage(start, settings.size) : null,
    });
    const job = await (await api('/videos', { method: 'POST', headers: { 'Content-Type': type }, body })).json();
    tapes.unshift({ id: job.id, prompt, size: settings.size, status: job.status || 'queued', progress: 0, createdAt: Date.now() });
    current = job.id;
    saveTapes(); render(); poll(job.id);
    toast('Recording… usually takes 1–5 minutes.');
  } catch (e) {
    toast(e.message, true);
  } finally {
    btn.disabled = false; btn.textContent = 'CREATE';
  }
}

async function poll(id) {
  if (polling.has(id)) return;
  polling.add(id);
  try {
    while (tapes.some(t => t.id === id)) {
      let job;
      try { job = await (await api('/videos/' + id)).json(); }
      catch (e) {
        if (/not found/i.test(e.message)) return update(id, { status: 'failed', error: 'This video expired on OpenAI.' });
        await wait(POLL_MS * 2); continue;
      }
      update(id, { status: job.status, progress: job.progress || 0 });
      if (job.status === 'completed') return fetchVideo(id);
      if (job.status === 'failed') return update(id, { error: (job.error && job.error.message) || 'Recording failed.' });
      await wait(POLL_MS);
    }
  } finally { polling.delete(id); }
}

async function fetchVideo(id) {
  try {
    const blob = await (await api(`/videos/${id}/content`)).blob();
    await idb('readwrite', s => s.put(blob, id));
    urls[id] = URL.createObjectURL(blob);
    update(id, { status: 'ready' });
    toast('Your tape is ready! ▶');
  } catch (e) {
    update(id, { status: 'failed', error: 'Download failed: ' + e.message });
  }
}

function update(id, patch) {
  const t = tapes.find(t => t.id === id);
  if (t) { Object.assign(t, patch); saveTapes(); render(); }
}
const wait = (ms) => new Promise(r => setTimeout(r, ms));

// ---------- Render ----------
const esc = (s) => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
let shownKey = '';

function render() {
  // Button labels
  $('promptSub').textContent = prompt.trim() ? prompt.trim() : 'tap to write';
  $('photoSub').textContent = photo ? 'added · tap to remove' : 'optional';
  $('photoBtn').querySelector('img')?.remove();
  if (photo) {
    const img = document.createElement('img'); img.className = 'thumb'; img.src = photoUrl; $('photoBtn').appendChild(img);
  }
  const cast = characters.filter(c => picked.has(c.id)).map(c => c.name);
  $('charSub').textContent = cast.length ? cast.join(', ') : 'optional';

  // Screen (only rebuild when what it shows changes, so playback isn't interrupted)
  const t = tapes.find(t => t.id === current);
  const key = t ? `${t.id}|${t.status}|${Math.round(t.progress)}|${!!urls[t.id]}` : 'idle';
  if (key !== shownKey) {
    shownKey = key;
    const scr = $('screen');
    scr.classList.toggle('portrait', !!t && t.size === '720x1280');
    if (!t) {
      scr.innerHTML = `<div class="noise"></div><div class="screen-msg">NO SIGNAL<small>Write a prompt, then press CREATE</small></div>`;
    } else if (t.status === 'ready' && urls[t.id]) {
      scr.innerHTML = `<video src="${urls[t.id]}" controls autoplay loop playsinline></video>`;
    } else if (t.status === 'ready') {
      scr.innerHTML = `<div class="noise"></div><div class="screen-msg">LOADING TAPE…</div>`;
    } else if (t.status === 'failed') {
      scr.innerHTML = `<div class="noise"></div><div class="screen-msg error">TAPE ERROR<small>${esc(t.error || '')}</small></div>`;
    } else {
      scr.innerHTML = `<div class="noise"></div><div class="screen-msg"><span class="rec">● REC</span> ${t.status === 'queued' ? 'WAITING IN LINE' : 'RECORDING'} ${t.progress ? Math.round(t.progress) + '%' : ''}
        <div class="meter"><div style="width:${Math.max(3, t.progress)}%"></div></div><small>${esc(t.prompt)}</small></div>`;
    }
  }

  // Tape shelf
  $('tapes').innerHTML = tapes.length ? tapes.map(t => {
    const busy = t.status === 'queued' || t.status === 'in_progress' || t.status === 'completed';
    const state = t.status === 'ready' ? '▶ PLAY' : t.status === 'failed' ? '✕ ERROR' : `● REC ${Math.round(t.progress)}%`;
    return `<button class="tape ${t.id === current ? 'active' : ''} ${busy ? 'busy' : ''}" data-id="${t.id}">
      <div class="label">${esc(t.prompt)}</div>
      <div class="reels"><span></span><span></span></div>
      <div class="state">${state}</div>
      <span class="x" data-del="${t.id}" title="Delete">✕</span>
    </button>`;
  }).join('') : `<div class="empty-shelf">No tapes yet.</div>`;
}

// ---------- Prompt ----------
function openPrompt() { $('promptInput').value = prompt; $('promptDialog').showModal(); $('promptInput').focus(); }
$('promptBtn').onclick = openPrompt;
$('ideaBtn').onclick = () => { $('promptInput').value = IDEAS[Math.floor(Math.random() * IDEAS.length)]; };
$('promptSave').onclick = () => {
  prompt = $('promptInput').value.trim(); store.set('draft', prompt);
  $('promptDialog').close(); render();
};

// ---------- Photo ----------
let photoUrl = '';
$('photoBtn').onclick = () => {
  if (photo) { photo = null; URL.revokeObjectURL(photoUrl); $('photoInput').value = ''; render(); return; }
  $('photoInput').click();
};
$('photoInput').onchange = (e) => {
  const f = e.target.files[0]; if (!f) return;
  photo = f; photoUrl = URL.createObjectURL(f); render();
  toast('Photo added. Your video will start from it.');
};

// ---------- Characters ----------
let editing = null, editFace = null;

function renderChars() {
  $('charList').innerHTML = characters.length ? characters.map(c => `
    <div class="char ${picked.has(c.id) ? 'on' : ''}" data-id="${c.id}">
      <span class="tick">${picked.has(c.id) ? '✔' : ''}</span>
      ${c.face ? `<img class="face" src="${c.face}" alt="">` : `<span class="face">☺</span>`}
      <span class="who"><b>${esc(c.name)}</b><div>${esc(c.desc)}</div></span>
      <button class="btn edit" data-edit="${c.id}">EDIT</button>
    </div>`).join('') : `<p>No characters yet. Make one!</p>`;
}
$('charBtn').onclick = () => { renderChars(); $('charDialog').showModal(); };
$('charList').onclick = (e) => {
  const edit = e.target.closest('[data-edit]');
  if (edit) return openCharEdit(characters.find(c => c.id === edit.dataset.edit));
  const row = e.target.closest('.char'); if (!row) return;
  picked.has(row.dataset.id) ? picked.delete(row.dataset.id) : picked.add(row.dataset.id);
  renderChars(); render();
};
$('charNew').onclick = () => openCharEdit(null);

function openCharEdit(c) {
  editing = c; editFace = c ? c.face : null;
  $('charEditTitle').textContent = c ? 'EDIT CHARACTER' : 'NEW CHARACTER';
  $('charName').value = c ? c.name : '';
  $('charDesc').value = c ? c.desc : '';
  $('charFace').hidden = !editFace; if (editFace) $('charFace').src = editFace;
  $('charDelete').hidden = !c;
  $('charEdit').showModal();
}
$('charFaceBtn').onclick = () => $('charFaceInput').click();
$('charFaceInput').onchange = async (e) => {
  const f = e.target.files[0]; if (!f) return;
  // Shrink so it fits in browser storage.
  const img = await createImageBitmap(f);
  const s = Math.min(1, 768 / Math.max(img.width, img.height));
  const c = document.createElement('canvas'); c.width = img.width * s; c.height = img.height * s;
  c.getContext('2d').drawImage(img, 0, 0, c.width, c.height);
  editFace = c.toDataURL('image/jpeg', 0.85);
  $('charFace').src = editFace; $('charFace').hidden = false;
  e.target.value = '';
};
$('charSave').onclick = () => {
  const name = $('charName').value.trim();
  if (!name) { toast('Give your character a name.', true); return; }
  const data = { name, desc: $('charDesc').value.trim(), face: editFace };
  if (editing) Object.assign(editing, data);
  else { const c = { id: 'c' + Date.now(), ...data }; characters.push(c); picked.add(c.id); }
  if (!store.set('characters', characters)) toast('Storage is full: try a smaller photo.', true);
  $('charEdit').close(); renderChars(); render();
};
$('charDelete').onclick = () => {
  if (!editing || !confirm(`Delete ${editing.name}?`)) return;
  characters = characters.filter(c => c !== editing); picked.delete(editing.id);
  store.set('characters', characters); $('charEdit').close(); renderChars(); render();
};

// ---------- Setup ----------
function updateCost() {
  $('costLine').textContent = `≈ $${(PRICE[$('modelSel').value] * Number($('secSel').value)).toFixed(2)} per video`;
}
function openKey() {
  $('keyInput').value = apiKey;
  $('modelSel').value = settings.model; $('secSel').value = settings.seconds; $('sizeSel').value = settings.size;
  updateCost(); $('keyDialog').showModal();
}
$('keyBtn').onclick = openKey;
$('modelSel').onchange = $('secSel').onchange = updateCost;
$('keySave').onclick = () => {
  apiKey = $('keyInput').value.trim(); store.set('key', apiKey);
  settings = { model: $('modelSel').value, seconds: $('secSel').value, size: $('sizeSel').value };
  store.set('settings', settings);
  $('keyDialog').close(); toast(apiKey ? 'Saved. Ready to create!' : 'API key removed.');
  resume();
};

// ---------- Tapes ----------
$('tapes').onclick = async (e) => {
  const del = e.target.closest('[data-del]');
  if (del) {
    e.stopPropagation();
    const id = del.dataset.del;
    if (!confirm('Delete this tape?')) return;
    tapes = tapes.filter(t => t.id !== id); saveTapes();
    await idb('readwrite', s => s.delete(id));
    if (urls[id]) { URL.revokeObjectURL(urls[id]); delete urls[id]; }
    if (current === id) current = tapes[0] ? tapes[0].id : null;
    api('/videos/' + id, { method: 'DELETE' }).catch(() => {});
    return render();
  }
  const tape = e.target.closest('.tape');
  if (tape) { current = tape.dataset.id; render(); }
};

// ---------- Misc ----------
document.querySelectorAll('[data-close]').forEach(b => b.onclick = () => b.closest('dialog').close());
$('createBtn').onclick = create;

let toastT;
function toast(msg, err) {
  const t = $('toast'); t.textContent = msg; t.className = 'toast show' + (err ? ' error' : '');
  clearTimeout(toastT); toastT = setTimeout(() => t.className = 'toast', err ? 6000 : 3500);
}

async function resume() {
  for (const t of tapes) {
    if (t.status === 'ready' && !urls[t.id]) {
      const blob = await idb('readonly', s => s.get(t.id));
      if (blob) urls[t.id] = URL.createObjectURL(blob);
      else if (apiKey) fetchVideo(t.id);
    } else if (['queued', 'in_progress', 'completed'].includes(t.status) && apiKey) {
      poll(t.id);
    }
  }
  render();
}

render();
resume();
if (!apiKey) setTimeout(openKey, 500);
</script>
</body>
</html>
"""


def ssl_context():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


CTX = ssl_context()


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/v1/"):
            return self.proxy()
        if self.path.split("?")[0] in ("/", "/index.html"):
            return self.send(200, "text/html; charset=utf-8", PAGE.encode())
        self.send_error(404)

    def do_POST(self):
        self.proxy()

    def do_DELETE(self):
        self.proxy()

    def send(self, status, ctype, data):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def proxy(self):
        if not self.path.startswith("/v1/"):
            return self.send_error(404)
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else None
        headers = {k: v for k, v in self.headers.items() if k.lower() in FORWARD_HEADERS}
        req = urllib.request.Request(OPENAI + self.path, data=body, headers=headers, method=self.command)
        try:
            resp = urllib.request.urlopen(req, context=CTX, timeout=300)
        except urllib.error.HTTPError as e:
            resp = e
        except Exception as e:
            print(f"  ! Could not reach OpenAI: {e}", file=sys.stderr)
            hint = ""
            if "CERTIFICATE_VERIFY_FAILED" in str(e):
                hint = (" Fix: open Applications > Python 3.x and double-click"
                        " 'Install Certificates.command', then restart GLOWTAPE.")
                print("   " + hint, file=sys.stderr)
            msg = {"error": {"message": f"GLOWTAPE could not reach OpenAI ({type(e).__name__}).{hint}"}}
            return self.send(502, "application/json", json.dumps(msg).encode())
        with resp:
            self.send(resp.status, resp.headers.get("Content-Type", "application/octet-stream"), resp.read())

    def log_message(self, fmt, *args):
        if self.command != "GET":
            print(f"  {self.command} {self.path.split('?')[0]}")


def main():
    try:
        server = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    except OSError:
        print(f"GLOWTAPE is already running. Open http://localhost:{PORT} in your browser.")
        webbrowser.open(f"http://localhost:{PORT}")
        return
    url = f"http://localhost:{PORT}"
    print("")
    print("  G L O W T A P E")
    print(f"  Running at {url}")
    print("  Keep this window open while you use it. Press Ctrl+C to stop.")
    print("")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Stopped.")


if __name__ == "__main__":
    main()
