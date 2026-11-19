const folderForm = document.querySelector("#folder-form");
const folderInput = document.querySelector("#folder-url");
const filesSection = document.querySelector("#files-section");
const fileList = document.querySelector("#file-list");
const selectAll = document.querySelector("#select-all");
const selectionCount = document.querySelector("#selection-count");
const runButton = document.querySelector("#run-button");
const resultsSection = document.querySelector("#results-section");
const resultsList = document.querySelector("#results-list");
const batchSummary = document.querySelector("#batch-summary");
const exportButton = document.querySelector("#export-button");
const toast = document.querySelector("#toast");

let files = [];
let currentBatch = null;
let pollTimer = null;

function showError(message) {
  toast.textContent = message;
  toast.hidden = false;
  window.clearTimeout(showError.timer);
  showError.timer = window.setTimeout(() => { toast.hidden = true; }, 6000);
}

async function requestJson(url, options) {
  const response = await fetch(url, options);
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail || `Erreur serveur (${response.status}).`);
  }
  return payload;
}

function formatSize(bytes) {
  if (bytes === null || bytes === undefined) return "Taille inconnue";
  if (bytes < 1024) return `${bytes} o`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} Ko`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} Mo`;
}

function updateSelection() {
  const selected = fileList.querySelectorAll("input[type=checkbox]:checked").length;
  selectionCount.textContent = `${selected} sélectionné${selected > 1 ? "s" : ""}`;
  selectAll.checked = files.length > 0 && selected === files.length;
  selectAll.indeterminate = selected > 0 && selected < files.length;
  runButton.disabled = selected === 0;
}

function renderFiles() {
  fileList.replaceChildren();
  if (files.length === 0) {
    fileList.innerHTML = '<div class="empty-state">Aucun PDF ou image pris en charge dans ce dossier.</div>';
    selectAll.disabled = true;
  } else {
    selectAll.disabled = false;
    for (const file of files) {
      const row = document.createElement("label");
      row.className = "file-row";
      const isImage = file.mime_type.startsWith("image/");
      const icon = document.createElement("span");
      icon.className = `file-icon${isImage ? " image" : ""}`;
      icon.textContent = isImage ? "IMG" : "PDF";
      icon.setAttribute("aria-hidden", "true");
      const details = document.createElement("span");
      details.className = "file-name";
      const name = document.createElement("span");
      name.textContent = file.name;
      const meta = document.createElement("span");
      meta.className = "file-meta";
      meta.textContent = `${isImage ? "Image" : "PDF"} · ${formatSize(file.size)}`;
      details.append(name, meta);
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.value = file.id;
      checkbox.setAttribute("aria-label", `Sélectionner ${file.name}`);
      checkbox.addEventListener("change", updateSelection);
      row.append(icon, details, checkbox);
      fileList.append(row);
    }
  }
  updateSelection();
}

function renderResults(batch) {
  resultsList.replaceChildren();
  for (const file of batch.files) {
    const card = document.createElement("article");
    card.className = "result-card";
    const top = document.createElement("div");
    top.className = "result-top";
    const icon = document.createElement("span");
    const isImage = file.mime_type.startsWith("image/");
    icon.className = `file-icon${isImage ? " image" : ""}`;
    icon.textContent = isImage ? "IMG" : "PDF";
    const name = document.createElement("span");
    name.className = "file-name";
    name.textContent = file.name;
    const status = document.createElement("span");
    status.className = `result-status ${file.status}`;
    status.textContent = {
      pending: "En attente",
      processing: "Traitement…",
      done: "Terminé",
      failed: "Échec",
    }[file.status] || file.status;
    top.append(icon, name);
    if (file.method) {
      const method = document.createElement("span");
      method.className = "method-tag";
      method.textContent = file.method === "ocr" ? "OCR" : "PDF parser";
      top.append(method);
    }
    top.append(status);
    card.append(top);
    if (file.status === "done") {
      const text = document.createElement("pre");
      text.className = "result-text";
      text.textContent = file.text || "Aucun texte extrait.";
      card.append(text);
    } else if (file.status === "failed") {
      const error = document.createElement("p");
      error.className = "result-text result-error";
      error.textContent = file.error || "Une erreur inconnue est survenue.";
      card.append(error);
    }
    resultsList.append(card);
  }

  const done = batch.files.filter((file) => file.status === "done").length;
  const failed = batch.files.filter((file) => file.status === "failed").length;
  batchSummary.textContent = batch.status === "processing"
    ? `${done + failed} sur ${batch.files.length} fichier(s) terminé(s)…`
    : `${done} réussi(s)${failed ? ` · ${failed} en échec` : ""} sur ${batch.files.length} fichier(s).`;
  exportButton.disabled = batch.status !== "done";
}

async function pollBatch(batchId) {
  try {
    currentBatch = await requestJson(`/api/batches/${encodeURIComponent(batchId)}`);
    renderResults(currentBatch);
    if (currentBatch.status === "processing") {
      pollTimer = window.setTimeout(() => pollBatch(batchId), 900);
    }
  } catch (error) {
    showError(error.message);
    batchSummary.textContent = "Impossible de récupérer l’état du traitement.";
  }
}

folderForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = document.querySelector("#load-button");
  button.disabled = true;
  button.textContent = "Chargement…";
  try {
    const response = await requestJson("/api/drive/files", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ folder_url: folderInput.value.trim() }),
    });
    files = response.files;
    document.querySelector("#file-summary").textContent =
      `${files.length} document(s) pris en charge. Sélectionnez les fichiers à traiter.`;
    filesSection.hidden = false;
    resultsSection.hidden = true;
    renderFiles();
  } catch (error) {
    showError(error.message);
  } finally {
    button.disabled = false;
    button.innerHTML = 'Lister les fichiers <span aria-hidden="true">→</span>';
  }
});

selectAll.addEventListener("change", () => {
  fileList.querySelectorAll("input[type=checkbox]").forEach((checkbox) => {
    checkbox.checked = selectAll.checked;
  });
  updateSelection();
});

runButton.addEventListener("click", async () => {
  const fileIds = [...fileList.querySelectorAll("input[type=checkbox]:checked")]
    .map((checkbox) => checkbox.value);
  runButton.disabled = true;
  window.clearTimeout(pollTimer);
  try {
    const response = await requestJson("/api/batches", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        folder_url: folderInput.value.trim(),
        file_ids: fileIds,
        ocr_language: document.querySelector("#ocr-language").value,
      }),
    });
    resultsSection.hidden = false;
    currentBatch = {
      status: "processing",
      files: files.filter((file) => fileIds.includes(file.id)).map((file) => ({
        ...file, status: "pending",
      })),
    };
    renderResults(currentBatch);
    await pollBatch(response.batch_id);
    resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    showError(error.message);
  } finally {
    runButton.disabled = fileList.querySelectorAll("input[type=checkbox]:checked").length === 0;
  }
});

exportButton.addEventListener("click", () => {
  if (!currentBatch) return;
  const output = {
    batch_id: currentBatch.id,
    status: currentBatch.status,
    files: currentBatch.files,
  };
  const blob = new Blob([`${JSON.stringify(output, null, 2)}\n`], { type: "application/json" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `drive-to-text-${currentBatch.id}.json`;
  link.click();
  URL.revokeObjectURL(link.href);
});
