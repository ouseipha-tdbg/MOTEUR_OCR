const $ = (s) => document.querySelector(s);
const LS_KEY = (dt) => `ocr-lab.fields.${dt}`;

let LAST_RESULTS = [];
let LAST_DOC_TYPE = "";

async function init() {
  const r = await fetch("/engines").then(r => r.json());
  const docSel = $("#doc_type");
  r.doc_types.forEach(t => {
    const o = document.createElement("option");
    o.value = t; o.textContent = t;
    docSel.appendChild(o);
  });
  const engBox = $("#engines-list");
  r.engines.forEach(e => {
    const lbl = document.createElement("label");
    lbl.innerHTML = `<input type="checkbox" name="engine" value="${e}" ${e === "paddle" ? "checked" : ""}> ${e}`;
    engBox.appendChild(lbl);
  });
}

$("#ocr-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const form = ev.target;
  const engines = [...form.querySelectorAll("input[name=engine]:checked")].map(x => x.value);
  if (!engines.length) return alert("Sélectionne au moins un moteur");

  const fd = new FormData();
  fd.append("doc_type", form.doc_type.value);
  fd.append("engines", engines.join(","));
  fd.append("recto", form.recto.files[0]);
  if (form.verso.files[0]) fd.append("verso", form.verso.files[0]);

  const btn = $("#run-btn");
  btn.disabled = true;
  $("#status").textContent = "OCR en cours...";
  $("#results").innerHTML = "";
  $("#field-picker").innerHTML = "";

  try {
    const t0 = performance.now();
    const res = await fetch("/ocr", { method: "POST", body: fd }).then(r => r.json());
    const elapsed = Math.round(performance.now() - t0);
    $("#status").textContent = `Terminé en ${elapsed} ms · ${res.results.length} moteur(s)`;
    LAST_RESULTS = res.results;
    LAST_DOC_TYPE = res.doc_type;
    renderFieldPicker(res.results, res.doc_type);
    renderResults(res.results, getVisibleFields(res.doc_type, res.results));
  } catch (e) {
    $("#status").textContent = "Erreur: " + e.message;
  } finally {
    btn.disabled = false;
  }
});

function collectAllFields(results) {
  const set = new Set();
  results.forEach(r => {
    if (!r.parsed) return;
    Object.keys(r.parsed).forEach(k => set.add(k));
  });
  return [...set];
}

function getVisibleFields(docType, results) {
  const all = collectAllFields(results);
  const saved = localStorage.getItem(LS_KEY(docType));
  if (!saved) return new Set(all);  // par défaut tout affiché
  const parsed = new Set(JSON.parse(saved));
  // n'affiche que les champs qui existent
  return new Set(all.filter(k => parsed.has(k)));
}

function renderFieldPicker(results, docType) {
  const box = $("#field-picker");
  const all = collectAllFields(results);
  if (!all.length) return;

  const visible = getVisibleFields(docType, results);

  const header = document.createElement("div");
  header.className = "picker-header";
  header.innerHTML = `
    <strong>Champs à afficher (${visible.size}/${all.length})</strong>
    <span class="picker-actions">
      <button type="button" id="pick-all">Tout</button>
      <button type="button" id="pick-none">Aucun</button>
      <button type="button" id="pick-invert">Inverser</button>
    </span>
  `;
  box.appendChild(header);

  const grid = document.createElement("div");
  grid.className = "picker-grid";
  all.forEach(k => {
    const id = `f-${k}`;
    const lbl = document.createElement("label");
    lbl.innerHTML = `<input type="checkbox" id="${id}" ${visible.has(k) ? "checked" : ""}> ${k}`;
    lbl.querySelector("input").addEventListener("change", () => onPickerChange(docType));
    grid.appendChild(lbl);
  });
  box.appendChild(grid);

  $("#pick-all").addEventListener("click", () => setAll(docType, true));
  $("#pick-none").addEventListener("click", () => setAll(docType, false));
  $("#pick-invert").addEventListener("click", () => {
    box.querySelectorAll(".picker-grid input").forEach(cb => cb.checked = !cb.checked);
    onPickerChange(docType);
  });
}

function setAll(docType, checked) {
  document.querySelectorAll("#field-picker .picker-grid input").forEach(cb => cb.checked = checked);
  onPickerChange(docType);
}

function onPickerChange(docType) {
  const checked = [...document.querySelectorAll("#field-picker .picker-grid input:checked")]
    .map(cb => cb.id.replace(/^f-/, ""));
  localStorage.setItem(LS_KEY(docType), JSON.stringify(checked));
  const visible = new Set(checked);
  renderResults(LAST_RESULTS, visible);
  const total = document.querySelectorAll("#field-picker .picker-grid input").length;
  $("#field-picker .picker-header strong").textContent = `Champs à afficher (${checked.length}/${total})`;
}

function renderResults(results, visibleFields) {
  const box = $("#results");
  box.innerHTML = "";
  results.forEach(r => {
    const card = document.createElement("div");
    card.className = "card";
    const badgeClass = r.error ? "badge err" : "badge";
    const badgeTxt = r.error ? "erreur" : `${(r.confidence*100).toFixed(0)}% · ${r.elapsed_ms}ms`;
    let body = "";
    if (r.error) {
      body = `<pre>${escapeHtml(r.error)}</pre>`;
    } else {
      const rows = Object.entries(r.parsed || {})
        .filter(([k]) => visibleFields.has(k))
        .map(([k, v]) => `<tr><td>${k}</td><td>${escapeHtml(formatVal(v))}</td></tr>`).join("");
      body = `
        <table>${rows}</table>
        <details><summary>Texte brut (${r.lines.length} lignes)</summary>
        <pre>${escapeHtml(r.full_text)}</pre></details>
      `;
    }
    card.innerHTML = `<h3>${r.engine}<span class="${badgeClass}">${badgeTxt}</span></h3>${body}`;
    box.appendChild(card);
  });
}

function formatVal(v) {
  if (v == null) return "";
  if (Array.isArray(v)) return v.join(", ");
  if (typeof v === "object") return JSON.stringify(v, null, 2);
  return String(v);
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
}

init();
