const serverTiming = 700;
const maxFileSize = 100 * 1024 * 1024;
const allowedExtensions = [
  ".pdf",
  ".docx",
  ".xlsx",
  ".pptx",
  ".txt",
  ".csv",
  ".png",
  ".jpg",
  ".jpeg",
  ".webp",
];

function formatBytes(bytes) {
  if (bytes === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const index = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / 1024 ** index).toFixed(1)} ${units[index]}`;
}

function parseUtcIsoString(isoString) {
  if (!isoString) return null;
  const normalized = isoString.trim();
  const utcString = /^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}$/.test(normalized)
    ? `${normalized}Z`
    : normalized;
  const date = new Date(utcString);
  return Number.isNaN(date.valueOf()) ? null : date;
}

function formatTimestampToIST(isoString) {
  const date = parseUtcIsoString(isoString);
  if (!date) return isoString || "—";

  const formatter = new Intl.DateTimeFormat("en-IN", {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
    timeZone: "Asia/Kolkata",
  });

  return `${formatter.format(date)} IST`;
}

function setElementText(id, text) {
  const element = document.getElementById(id);
  if (element) element.textContent = text;
}

function setExpiryText(id, timestamp) {
  const element = document.getElementById(id);
  if (element) element.textContent = formatTimestampToIST(timestamp);
}

function updateProgress(value) {
  const bar = document.getElementById("upload-progress");
  if (bar) bar.style.width = `${value}%`;
}

function showUploadStatus(message, severity = "info") {
  setElementText("upload-status", message);
  const banner = document.getElementById("upload-status-banner");
  if (banner) {
    banner.style.background = severity === "error" ? "#ffe7e7" : "#eef4ff";
    banner.style.borderColor = severity === "error" ? "#f5c2c2" : "#dfe7ff";
  }
}

function setDashboardMessage(message, isError = false) {
  const element = document.getElementById("dashboard-message");
  if (element) {
    element.textContent = message;
    element.style.color = isError ? "#d14343" : "#334580";
  }
}

async function createSession(employeeCode) {
  const response = await fetch("/session/create", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ employee_code: employeeCode }),
  });

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || "Unable to create session.");
  }

  return response.json();
}

function bindDashboard() {
  const form = document.getElementById("qr-form");
  const downloadButton = document.getElementById("download-file-button");
  const downloadAllButton = document.getElementById("download-all-button");
  const downloadFileName = document.getElementById("download-file-name");
  const uploadedFilesList = document.getElementById("uploaded-files-list");
  let sessionId = null;
  let statusPoll = null;

  if (!form) return;

  function updateDownloadedFileStatus(status, filename) {
    if (status === "uploaded") {
      setElementText("dashboard-status", "File received");
      if (downloadButton) downloadButton.disabled = false;
      if (downloadAllButton) downloadAllButton.disabled = false;
      if (downloadFileName) downloadFileName.textContent = filename ? `First file: ${filename}` : "Ready to download.";
    } else {
      setElementText("dashboard-status", "Waiting for file upload...");
      if (downloadButton) downloadButton.disabled = true;
      if (downloadAllButton) downloadAllButton.disabled = true;
      if (downloadFileName) downloadFileName.textContent = "";
    }
  }

  async function fetchDownloadFilename(sessionIdToCheck) {
    try {
      const response = await fetch(`/download/${sessionIdToCheck}`, {
        method: "HEAD",
      });
      if (!response.ok) return null;
      const disposition = response.headers.get("content-disposition") || "";
      const match = disposition.match(/filename="?([^";]+)"?/);
      return match ? match[1] : null;
    } catch {
      return null;
    }
  }

  async function renderUploadedFiles(files) {
    if (!uploadedFilesList) return;
    uploadedFilesList.innerHTML = "";

    if (!files?.length) {
      const emptyMessage = document.createElement("li");
      emptyMessage.textContent = "No files uploaded yet.";
      uploadedFilesList.appendChild(emptyMessage);
      return;
    }

    files.forEach((file) => {
      const item = document.createElement("li");
      item.className = "uploaded-file-item";
      item.innerHTML = `
        <strong>${file.filename}</strong>
        <span>${formatBytes(file.size)}</span>
        <button type="button" class="small-button" data-filename="${encodeURIComponent(file.filename)}">Download</button>
      `;
      const button = item.querySelector("button");
      button?.addEventListener("click", () => {
        if (!sessionId) return;
        const filename = decodeURIComponent(button.dataset.filename || "");
        window.location.href = `/download/${sessionId}?filename=${filename}`;
      });
      uploadedFilesList.appendChild(item);
    });
  }

  async function pollSessionStatus() {
    if (!sessionId) return;

    try {
      const response = await fetch(`/session/${sessionId}`);
      if (!response.ok) {
        if (response.status === 404) {
          setDashboardMessage("Session not found.", true);
        }
        return;
      }

      const session = await response.json();
      if (session.status === "uploaded" || session.status === "downloaded") {
        await renderUploadedFiles(session.files);
        const filename = session.files?.[0]?.filename ?? null;
        updateDownloadedFileStatus("uploaded", filename);
        clearInterval(statusPoll);
        statusPoll = null;
      }
    } catch (error) {
      setDashboardMessage("Unable to refresh session status.", true);
    }
  }

  downloadButton?.addEventListener("click", () => {
    if (!sessionId) return;
    window.location.href = `/download/${sessionId}`;
  });

  downloadAllButton?.addEventListener("click", () => {
    if (!sessionId) return;
    window.location.href = `/download/${sessionId}?archive=true`;
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const employeeCode = document.getElementById("employee-code").value.trim();
    if (!employeeCode) {
      setDashboardMessage("Employee code is required.", true);
      return;
    }

    setDashboardMessage("Generating transfer session...");

    try {
      const session = await createSession(employeeCode);
      sessionId = session.session_id;
      const qrPreview = document.getElementById("qr-preview");
      if (qrPreview) {
        qrPreview.innerHTML = `<img src="/session/${session.session_id}/qr" alt="Session QR code" class="qr-image" />`;
      }

      setElementText("dashboard-session-id", session.session_id);
      setExpiryText("dashboard-expiry", session.expires_at);
      updateDownloadedFileStatus(session.status, "");
      setDashboardMessage("QR code generated successfully.");

      if (statusPoll) {
        clearInterval(statusPoll);
      }
      statusPoll = setInterval(pollSessionStatus, 5000);
    } catch (error) {
      setDashboardMessage(error.message, true);
    }
  });
}

function getUploadSessionId() {
  const sessionElement = document.getElementById("session-id-value");
  if (sessionElement?.textContent) {
    return sessionElement.textContent.trim();
  }

  const match = window.location.pathname.match(/\/upload\/([a-f0-9\-]+)/i);
  return match ? match[1] : null;
}

function buildFileListItem(file, index) {
  const listItem = document.createElement("li");
  listItem.className = "selected-file-item";
  listItem.dataset.index = String(index);

  const nameSpan = document.createElement("span");
  nameSpan.className = "selected-file-name";
  nameSpan.textContent = file.name;

  const sizeSpan = document.createElement("span");
  sizeSpan.className = "selected-file-size";
  sizeSpan.textContent = formatBytes(file.size);

  const removeButton = document.createElement("button");
  removeButton.type = "button";
  removeButton.className = "remove-file-button";
  removeButton.textContent = "Remove";

  listItem.append(nameSpan, sizeSpan, removeButton);
  return listItem;
}

function uploadFilesToServer(sessionId, files) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `/upload/${sessionId}`);

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        updateProgress(Math.round((event.loaded / event.total) * 100));
      }
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText));
        } catch (error) {
          reject(new Error("Unexpected server response."));
        }
        return;
      }

      let message = `Upload failed with status ${xhr.status}.`;
      try {
        const payload = JSON.parse(xhr.responseText);
        message = payload.detail || payload.message || message;
      } catch {
        // ignore parse errors
      }
      reject(new Error(message));
    };

    xhr.onerror = () => reject(new Error("Network error during upload."));
    xhr.ontimeout = () => reject(new Error("Upload timed out."));

    const formData = new FormData();
    files.forEach((file) => {
      formData.append("files", file);
    });
    xhr.send(formData);
  });
}

function bindUploadPage() {
  const fileInput = document.getElementById("file-input");
  const uploadButton = document.getElementById("upload-button");
  const cancelButton = document.getElementById("cancel-button");
  const uploadMessage = document.getElementById("upload-message");
  const selectedFilesList = document.getElementById("selected-files");

  if (!fileInput || !uploadButton || !cancelButton || !selectedFilesList) return;

  const expiryValue = document.getElementById("session-expiry-value");
  if (expiryValue?.textContent) {
    expiryValue.textContent = formatTimestampToIST(expiryValue.textContent.trim());
  }

  let selectedFiles = [];

  function refreshFileList() {
    selectedFilesList.innerHTML = "";
    if (!selectedFiles.length) {
      const emptyMessage = document.createElement("li");
      emptyMessage.textContent = "No files selected.";
      selectedFilesList.appendChild(emptyMessage);
      return;
    }

    selectedFiles.forEach((file, index) => {
      const listItem = buildFileListItem(file, index);
      const removeButton = listItem.querySelector(".remove-file-button");
      removeButton?.addEventListener("click", () => {
        selectedFiles.splice(index, 1);
        refreshFileList();
        validateSelectedFiles();
      });
      selectedFilesList.appendChild(listItem);
    });
  }

  function validateSelectedFiles() {
    uploadButton.disabled = true;
    showUploadStatus("No files selected.");
    setElementText("selected-file-name", "None");
    setElementText("selected-file-size", "—");
    updateProgress(0);

    if (!selectedFiles.length) {
      if (uploadMessage) uploadMessage.textContent = "";
      return;
    }

    for (const file of selectedFiles) {
      const extension = file.name.substring(file.name.lastIndexOf(".")).toLowerCase();
      if (!allowedExtensions.includes(extension)) {
        showUploadStatus("One or more files are invalid.", "error");
        if (uploadMessage) uploadMessage.textContent = `Invalid file type: ${file.name}`;
        return;
      }
      if (file.size > maxFileSize) {
        showUploadStatus("One or more files exceed the maximum size.", "error");
        if (uploadMessage) uploadMessage.textContent = `File too large: ${file.name}`;
        return;
      }
    }

    uploadButton.disabled = false;
    showUploadStatus("Ready to upload.");
    if (uploadMessage) uploadMessage.textContent = "";
    setElementText("selected-file-name", `${selectedFiles.length} file(s) selected`);
    const totalSize = selectedFiles.reduce((sum, file) => sum + file.size, 0);
    setElementText("selected-file-size", formatBytes(totalSize));
    updateProgress(25);
  }

  fileInput.addEventListener("change", () => {
    selectedFiles = Array.from(fileInput.files ?? []).filter(Boolean);
    refreshFileList();
    validateSelectedFiles();
  });

  uploadButton.addEventListener("click", async () => {
    if (!selectedFiles.length) return;
    const sessionId = getUploadSessionId();
    if (!sessionId) {
      showUploadStatus("Unable to determine upload session.", "error");
      if (uploadMessage) uploadMessage.textContent = "Refresh the page and try again.";
      return;
    }

    uploadButton.disabled = true;
    cancelButton.disabled = true;
    showUploadStatus("Uploading files...");
    if (uploadMessage) uploadMessage.textContent = "";
    updateProgress(5);

    try {
      const result = await uploadFilesToServer(sessionId, selectedFiles);
      showUploadStatus("Upload successful.", "info");
      if (uploadMessage) uploadMessage.textContent = `Uploaded ${result.filenames.length} file(s).`;
      updateProgress(100);
      fileInput.value = "";
      selectedFiles = [];
      refreshFileList();
      uploadButton.disabled = true;
      cancelButton.disabled = false;
    } catch (error) {
      showUploadStatus(error.message || "Upload failed.", "error");
      if (uploadMessage) uploadMessage.textContent = error.message;
      uploadButton.disabled = false;
      cancelButton.disabled = false;
      updateProgress(0);
    }
  });

  cancelButton.addEventListener("click", () => {
    fileInput.value = "";
    selectedFiles = [];
    refreshFileList();
    uploadButton.disabled = true;
    showUploadStatus("Selection cancelled.");
    setElementText("selected-file-name", "None");
    setElementText("selected-file-size", "—");
    updateProgress(0);
    if (uploadMessage) uploadMessage.textContent = "";
    cancelButton.disabled = false;
  });
}

function attachPageBehavior() {
  if (document.body.dataset.page === "dashboard") {
    bindDashboard();
  }
  if (document.body.dataset.page === "upload") {
    bindUploadPage();
  }
  if (document.body.dataset.page === "transfer") {
    const expiryValue = document.getElementById("session-expiry-value");
    if (expiryValue?.textContent) {
      expiryValue.textContent = formatTimestampToIST(expiryValue.textContent.trim());
    }
  }
}

window.addEventListener("DOMContentLoaded", attachPageBehavior);
