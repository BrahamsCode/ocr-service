from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from app.config import get_settings

router = APIRouter(tags=["dev"])


PLAYGROUND_HTML = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>OCR Service · Playground</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  :root {
    --bg: #0f172a;
    --panel: #1e293b;
    --panel-2: #273449;
    --border: #334155;
    --text: #e2e8f0;
    --muted: #94a3b8;
    --accent: #38bdf8;
    --accent-2: #0ea5e9;
    --ok: #22c55e;
    --warn: #f59e0b;
    --err: #ef4444;
    --mono: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.5;
  }
  header {
    padding: 18px 28px;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: rgba(15, 23, 42, 0.85);
    backdrop-filter: blur(8px);
    position: sticky;
    top: 0;
    z-index: 10;
  }
  header h1 { margin: 0; font-size: 18px; font-weight: 600; }
  header .badge {
    background: var(--panel-2);
    color: var(--muted);
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 12px;
    font-family: var(--mono);
  }
  main {
    max-width: 1280px;
    margin: 0 auto;
    padding: 24px;
    display: grid;
    grid-template-columns: 380px 1fr;
    gap: 24px;
  }
  @media (max-width: 900px) {
    main { grid-template-columns: 1fr; }
  }
  .panel {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 18px;
  }
  .panel h2 {
    margin: 0 0 14px 0;
    font-size: 13px;
    font-weight: 600;
    text-transform: uppercase;
    color: var(--muted);
    letter-spacing: 0.05em;
  }
  label { display: block; font-size: 13px; color: var(--muted); margin-bottom: 6px; }
  input, select {
    width: 100%;
    background: var(--bg);
    border: 1px solid var(--border);
    color: var(--text);
    padding: 9px 12px;
    border-radius: 6px;
    font-size: 14px;
    font-family: inherit;
  }
  input:focus, select:focus { outline: none; border-color: var(--accent); }
  .row { margin-bottom: 14px; }

  .dropzone {
    border: 2px dashed var(--border);
    border-radius: 10px;
    padding: 28px 16px;
    text-align: center;
    cursor: pointer;
    transition: all 0.15s;
    background: var(--bg);
  }
  .dropzone:hover, .dropzone.drag {
    border-color: var(--accent);
    background: rgba(56, 189, 248, 0.05);
  }
  .dropzone .hint { color: var(--muted); font-size: 13px; margin-top: 6px; }
  .dropzone.has-file { border-style: solid; border-color: var(--accent); }
  .file-info {
    font-family: var(--mono);
    font-size: 12px;
    color: var(--accent);
    word-break: break-all;
  }

  button.primary {
    width: 100%;
    background: var(--accent-2);
    color: #fff;
    border: none;
    padding: 11px;
    border-radius: 6px;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.15s;
  }
  button.primary:hover:not(:disabled) { background: var(--accent); }
  button.primary:disabled { opacity: 0.5; cursor: not-allowed; }

  .meta-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 10px;
    margin-bottom: 18px;
  }
  .meta-card {
    background: var(--panel-2);
    border-radius: 8px;
    padding: 10px 12px;
  }
  .meta-card .k { font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; }
  .meta-card .v { font-size: 16px; font-weight: 600; margin-top: 2px; }
  .meta-card .v.ok   { color: var(--ok); }
  .meta-card .v.warn { color: var(--warn); }

  .fields {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: 10px;
  }
  .field {
    background: var(--panel-2);
    padding: 10px 14px;
    border-radius: 8px;
    border-left: 3px solid var(--border);
  }
  .field.has-value { border-left-color: var(--ok); }
  .field.empty     { border-left-color: var(--err); opacity: 0.6; }
  .field .k { font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; }
  .field .v {
    font-family: var(--mono);
    font-size: 14px;
    margin-top: 4px;
    word-break: break-all;
  }
  .field .v.empty { color: var(--muted); font-style: italic; }

  .raw-section { margin-top: 22px; }
  details { background: var(--panel-2); border-radius: 8px; }
  details summary { padding: 12px 16px; cursor: pointer; font-weight: 600; font-size: 14px; }
  details[open] summary { border-bottom: 1px solid var(--border); }
  pre.raw {
    margin: 0;
    padding: 16px;
    font-family: var(--mono);
    font-size: 12px;
    white-space: pre-wrap;
    word-break: break-word;
    max-height: 420px;
    overflow-y: auto;
    color: var(--muted);
  }

  .warnings {
    background: rgba(245, 158, 11, 0.1);
    border: 1px solid var(--warn);
    color: var(--warn);
    border-radius: 8px;
    padding: 10px 14px;
    margin-bottom: 14px;
    font-size: 13px;
  }
  .warnings ul { margin: 4px 0 0 18px; padding: 0; }

  .error {
    background: rgba(239, 68, 68, 0.1);
    border: 1px solid var(--err);
    color: var(--err);
    padding: 14px;
    border-radius: 8px;
    font-size: 13px;
    font-family: var(--mono);
    white-space: pre-wrap;
  }

  .empty-state {
    text-align: center;
    padding: 80px 20px;
    color: var(--muted);
  }
  .empty-state svg { opacity: 0.3; margin-bottom: 14px; }
  .spinner {
    display: inline-block;
    width: 14px;
    height: 14px;
    border: 2px solid rgba(255,255,255,0.3);
    border-top-color: #fff;
    border-radius: 50%;
    animation: spin 0.7s linear infinite;
    vertical-align: middle;
    margin-right: 6px;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
</head>
<body>

<header>
  <h1>🔎 OCR Service · Playground</h1>
  <span class="badge" id="serviceBadge">cargando…</span>
</header>

<main>
  <aside class="panel">
    <h2>Configuración</h2>

    <div class="row">
      <label for="apiKey">API Key (X-API-Key)</label>
      <input type="password" id="apiKey" placeholder="pegá tu API_KEY">
    </div>

    <div class="row">
      <label for="endpoint">Endpoint</label>
      <select id="endpoint">
        <option value="/parse/xml">/parse/xml — XML UBL (100% precisión, ~1ms)</option>
        <option value="/ocr/invoice">/ocr/invoice — facturas SUNAT (OCR)</option>
        <option value="/ocr/guide">/ocr/guide — guías de remisión (OCR)</option>
        <option value="/ocr/text">/ocr/text — texto crudo (OCR)</option>
      </select>
    </div>

    <div class="row">
      <label>Archivo (PDF, JPG, PNG, WEBP, TIFF)</label>
      <div class="dropzone" id="dropzone">
        <div id="dropDefault">
          📄 <strong>Arrastrá un archivo</strong> o hacé click<br>
          <span class="hint">XML (preferido) · PDF · imagen · max 20 MB</span>
        </div>
        <div id="dropChosen" style="display:none">
          <div class="file-info" id="fileName"></div>
          <span class="hint" id="fileSize"></span>
        </div>
      </div>
      <input type="file" id="fileInput" accept=".pdf,.xml,.jpg,.jpeg,.png,.webp,.tiff,.tif" hidden>
    </div>

    <button class="primary" id="submitBtn" disabled>Analizar documento</button>
  </aside>

  <section class="panel" id="results">
    <h2>Resultado</h2>
    <div class="empty-state" id="emptyState">
      <svg width="56" height="56" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
        <polyline points="14 2 14 8 20 8"/>
        <line x1="9" y1="13" x2="15" y2="13"/>
        <line x1="9" y1="17" x2="15" y2="17"/>
      </svg>
      <div>Subí un documento para ver los campos extraídos.</div>
    </div>
    <div id="resultBody" style="display:none"></div>
  </section>
</main>

<script>
const $  = (id) => document.getElementById(id);
const apiKeyInput = $('apiKey');
const endpointSel = $('endpoint');
const fileInput   = $('fileInput');
const dropzone    = $('dropzone');
const submitBtn   = $('submitBtn');
const dropDefault = $('dropDefault');
const dropChosen  = $('dropChosen');
const fileNameEl  = $('fileName');
const fileSizeEl  = $('fileSize');
const emptyState  = $('emptyState');
const resultBody  = $('resultBody');
const badge       = $('serviceBadge');

// API key: server-injected default, with localStorage override
const SERVER_API_KEY = "__API_KEY__";
apiKeyInput.value = localStorage.getItem('ocr.apiKey') || SERVER_API_KEY || '';
apiKeyInput.addEventListener('change', () => localStorage.setItem('ocr.apiKey', apiKeyInput.value));

let chosenFile = null;

// /health al cargar
fetch('/health').then(r => r.json()).then(h => {
  badge.textContent = `${h.service} ${h.version} · tess ${h.tesseract.version || 'N/A'}`;
  badge.style.color = h.status === 'ok' ? 'var(--ok)' : 'var(--warn)';
}).catch(() => { badge.textContent = 'health: error'; badge.style.color = 'var(--err)'; });

// Drag & drop
dropzone.addEventListener('click', () => fileInput.click());
dropzone.addEventListener('dragover', (e) => { e.preventDefault(); dropzone.classList.add('drag'); });
dropzone.addEventListener('dragleave', () => dropzone.classList.remove('drag'));
dropzone.addEventListener('drop', (e) => {
  e.preventDefault();
  dropzone.classList.remove('drag');
  if (e.dataTransfer.files.length) setFile(e.dataTransfer.files[0]);
});
fileInput.addEventListener('change', () => {
  if (fileInput.files.length) setFile(fileInput.files[0]);
});

function setFile(f) {
  chosenFile = f;
  fileNameEl.textContent = f.name;
  fileSizeEl.textContent = (f.size / 1024).toFixed(1) + ' KB · ' + (f.type || 'unknown');
  dropDefault.style.display = 'none';
  dropChosen.style.display = 'block';
  dropzone.classList.add('has-file');
  submitBtn.disabled = false;
}

submitBtn.addEventListener('click', submit);

async function submit() {
  if (!chosenFile) return;
  const apiKey = apiKeyInput.value.trim();
  const endpoint = endpointSel.value;
  if (!apiKey) { alert('Falta la API Key'); return; }

  submitBtn.disabled = true;
  submitBtn.innerHTML = '<span class="spinner"></span> Procesando…';
  emptyState.style.display = 'none';
  resultBody.style.display = 'block';
  resultBody.innerHTML = '<div class="empty-state"><span class="spinner"></span> Procesando…</div>';

  const fd = new FormData();
  fd.append('file', chosenFile);

  const t0 = performance.now();
  try {
    const r = await fetch(endpoint, {
      method: 'POST',
      headers: { 'X-API-Key': apiKey },
      body: fd
    });
    const elapsed = Math.round(performance.now() - t0);
    const text = await r.text();
    let data;
    try { data = JSON.parse(text); } catch { data = { raw: text }; }
    if (!r.ok) {
      renderError(r.status, data, elapsed);
    } else {
      render(data, elapsed);
    }
  } catch (err) {
    renderError(0, { detail: err.message }, Math.round(performance.now() - t0));
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = 'Analizar documento';
  }
}

function escape(s) {
  return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

function render(data, elapsed) {
  const meta = data.meta || {};
  const fields = data.fields || (data.pages ? null : data);
  const warnings = data.warnings || [];

  let html = '';

  // Meta cards
  html += '<div class="meta-grid">';
  if (data.source) html += metaCard('Source', data.source, 'ok');
  else html += metaCard('Engine', meta.engine || '—');
  if (data.document_type) html += metaCard('Tipo doc.', data.document_type, 'ok');
  if (meta.confidence != null) html += metaCard('Confianza', meta.confidence + '%', meta.confidence >= 80 ? 'ok' : 'warn');
  if (meta.processing_ms != null) html += metaCard('Procesamiento', meta.processing_ms + ' ms');
  html += metaCard('Round-trip', elapsed + ' ms');
  if (meta.page_count != null) html += metaCard('Páginas', meta.page_count);
  if (meta.preprocessed != null) html += metaCard('Preprocess', meta.preprocessed ? 'sí' : 'no');
  if (meta.raw_text_length != null) html += metaCard('Chars', meta.raw_text_length);
  html += '</div>';

  // Items (líneas de detalle, sólo /parse/xml)
  if (Array.isArray(data.items) && data.items.length) {
    html += '<details open style="margin-bottom:14px"><summary>Ítems / Líneas (' + data.items.length + ')</summary>';
    data.items.forEach((it, idx) => {
      html += '<div style="padding:10px 16px;border-top:1px solid var(--border);font-family:var(--mono);font-size:12px">';
      html += '<div style="color:var(--accent);margin-bottom:4px">#' + (idx + 1) + '</div>';
      Object.entries(it).forEach(([k, v]) => {
        if (v !== null && v !== undefined && v !== '') {
          html += '<div><span style="color:var(--muted)">' + escape(k) + ':</span> ' + escape(v) + '</div>';
        }
      });
      html += '</div>';
    });
    html += '</details>';
  }

  // Warnings
  if (warnings.length) {
    html += '<div class="warnings"><strong>⚠ Advertencias</strong><ul>';
    warnings.forEach(w => { html += '<li>' + escape(w) + '</li>'; });
    html += '</ul></div>';
  }

  // Fields (estructurado)
  if (fields && typeof fields === 'object' && !Array.isArray(fields)) {
    html += '<div class="fields">';
    Object.entries(fields).forEach(([k, v]) => {
      const isEmpty = v === null || v === undefined || v === '' || (Array.isArray(v) && !v.length);
      const display = isEmpty ? 'sin extraer' : (typeof v === 'object' ? JSON.stringify(v) : v);
      html += '<div class="field ' + (isEmpty ? 'empty' : 'has-value') + '">';
      html += '<div class="k">' + escape(k) + '</div>';
      html += '<div class="v ' + (isEmpty ? 'empty' : '') + '">' + escape(display) + '</div>';
      html += '</div>';
    });
    html += '</div>';
  }

  // Páginas (endpoint /ocr/text)
  if (data.pages && Array.isArray(data.pages)) {
    html += '<div class="raw-section"><details open><summary>Páginas (' + data.pages.length + ')</summary>';
    data.pages.forEach((p, i) => {
      html += '<div style="padding:12px 16px;border-top:1px solid var(--border)">';
      html += '<div style="font-size:12px;color:var(--muted);margin-bottom:6px">Página ' + (i+1) + '</div>';
      html += '<pre class="raw" style="max-height:200px;padding:0">' + escape(p.text || p) + '</pre>';
      html += '</div>';
    });
    html += '</details></div>';
  }

  // Raw text
  if (data.raw_text) {
    html += '<div class="raw-section"><details><summary>Texto crudo (' + data.raw_text.length + ' chars)</summary>';
    html += '<pre class="raw">' + escape(data.raw_text) + '</pre>';
    html += '</details></div>';
  }

  // JSON completo
  html += '<div class="raw-section"><details><summary>JSON completo</summary>';
  html += '<pre class="raw">' + escape(JSON.stringify(data, null, 2)) + '</pre>';
  html += '</details></div>';

  resultBody.innerHTML = html;
}

function metaCard(k, v, cls) {
  return '<div class="meta-card"><div class="k">' + escape(k) + '</div><div class="v ' + (cls || '') + '">' + escape(v) + '</div></div>';
}

function renderError(status, data, elapsed) {
  let msg = `HTTP ${status} (${elapsed} ms)\n\n`;
  msg += typeof data === 'string' ? data : JSON.stringify(data, null, 2);
  resultBody.innerHTML = '<div class="error">' + escape(msg) + '</div>';
}
</script>

</body>
</html>
"""


@router.get("/playground", response_class=HTMLResponse, include_in_schema=False)
async def playground() -> HTMLResponse:
    """UI de prueba — drag&drop + visualización de campos extraídos. Sólo no-prod."""
    settings = get_settings()
    if settings.environment == "production":
        raise HTTPException(status_code=404, detail="Not found")
    html = PLAYGROUND_HTML.replace("__API_KEY__", settings.api_key)
    return HTMLResponse(content=html)
