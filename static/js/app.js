const serverTiming = 700;
let maxFileSize = 100 * 1024 * 1024;
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
  ".mp4",
  ".mov",
  ".webm",
  ".avi",
  ".mkv",
];
const allowedMimeTypes = [
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  "application/vnd.openxmlformats-officedocument.presentationml.presentation",
  "text/plain",
  "text/csv",
  "image/png",
  "image/jpeg",
  "image/webp",
  "video/mp4",
  "video/quicktime",
  "video/webm",
  "video/x-msvideo",
  "video/x-matroska",
  "application/octet-stream",
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
  const hostnameInput = document.getElementById("receiver-hostname");
  const receiverHostname = hostnameInput?.value?.trim() || null;
  const payload = { employee_code: employeeCode };
  if (receiverHostname) {
    payload.hostname = receiverHostname;
  }

  const response = await fetch("/session/create", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || "Unable to create session.");
  }

  return response.json();
}

function bindDashboard() {
  const form = document.getElementById("qr-form");
  const downloadAllButton = document.getElementById("download-all-button");
  const receiverHostnameError = document.getElementById("receiver-hostname-error");
  const receiverHostnameInput = document.getElementById("receiver-hostname");
  const uploadedFilesList = document.getElementById("uploaded-files-list");
  const dashboardStatusBadge = document.getElementById("dashboard-status-badge");
  const dashboardStatusText = document.getElementById("dashboard-status-text");
  let sessionId = null;
  let statusPoll = null;
  let pollInFlight = false;

  if (!form) return;

  const hostnameError = receiverHostnameError?.value?.trim();
  const generateButton = document.getElementById("generate-qr");
  if (generateButton) {
    generateButton.disabled = false;
  }

  // On initial load, mark the receiver progress as 'Create session' current
  updateReceiverProgress(null);

  if (hostnameError && hostnameError.toLowerCase() !== "none") {
    setDashboardMessage(hostnameError, true);
    if (generateButton) {
      generateButton.disabled = true;
    }
  }

  function updateReceiverProgress(status) {
    const steps = Array.from(document.querySelectorAll("#receiver-progress-steps .progress-step"));
    if (!steps.length) return;

    // Before a session exists, mark "Create session" as current. Once one has
    // been created, only a known session state may change the workflow.
    if (!status && !sessionId) {
      steps.forEach((s) => s.classList.remove("progress-step--complete", "progress-step--current", "progress-step--future"));
      steps[0]?.classList.add("progress-step--current");
      steps[1]?.classList.add("progress-step--future");
      steps[2]?.classList.add("progress-step--future");
      return;
    }

    const normalized = (status || "created").toLowerCase();
    if (!["created", "waiting", "pending", "open", "uploading", "uploaded", "downloaded", "expired", "failed"].includes(normalized)) {
      return;
    }

    steps.forEach((s) => s.classList.remove("progress-step--complete", "progress-step--current", "progress-step--future"));

    if (["created", "waiting", "pending", "open", "uploading", "failed"].includes(normalized)) {
      // Session exists: create session completed, upload current
      steps[0]?.classList.add("progress-step--complete");
      steps[1]?.classList.add("progress-step--current");
      steps[2]?.classList.add("progress-step--future");
      return;
    }

    if (normalized === "uploaded") {
      steps[0]?.classList.add("progress-step--complete");
      steps[1]?.classList.add("progress-step--complete");
      steps[2]?.classList.add("progress-step--current");
      return;
    }

    if (normalized === "downloaded") {
      steps.forEach((s) => s.classList.add("progress-step--complete"));
      return;
    }

    if (normalized === "expired") {
      steps[0]?.classList.add("progress-step--complete");
      steps[1]?.classList.add("progress-step--future");
      steps[2]?.classList.add("progress-step--future");
      return;
    }

  }

  function setStatusBadge(status) {
    if (!dashboardStatusBadge || !dashboardStatusText) return;
    const normalized = status?.toLowerCase() || "waiting";
    const disableDownloads = normalized === "downloaded";
    dashboardStatusBadge.className = "status-pill";
    dashboardStatusText.textContent = "Waiting for file upload...";

    if (["waiting", "created", "pending", "open"].includes(normalized)) {
      dashboardStatusBadge.textContent = "WAITING";
      dashboardStatusBadge.classList.add("status-pill--waiting");
      dashboardStatusText.textContent = "Waiting for employee upload.";
      downloadAllButton.disabled = true;
    } else if (normalized === "uploading") {
      dashboardStatusBadge.textContent = "UPLOADING";
      dashboardStatusBadge.classList.add("status-pill--waiting");
      dashboardStatusText.textContent = "Files are being securely stored. Please wait.";
      downloadAllButton.disabled = true;
    } else if (normalized === "uploaded") {
      dashboardStatusBadge.textContent = "UPLOAD COMPLETE";
      dashboardStatusBadge.classList.add("status-pill--success");
      dashboardStatusText.textContent = "Files have been uploaded and are ready to download.";
      downloadAllButton.disabled = false;
    } else if (normalized === "downloaded") {
      dashboardStatusBadge.textContent = "COMPLETE";
      dashboardStatusBadge.classList.add("status-pill--success");
      dashboardStatusText.textContent = "The session has been downloaded.";
      downloadAllButton.disabled = true;
    } else if (normalized === "expired") {
      dashboardStatusBadge.textContent = "EXPIRED";
      dashboardStatusBadge.classList.add("status-pill--error");
      dashboardStatusText.textContent = "This session has expired.";
      downloadAllButton.disabled = true;
    } else if (normalized === "failed") {
      dashboardStatusBadge.textContent = "UPLOAD FAILED";
      dashboardStatusBadge.classList.add("status-pill--error");
      dashboardStatusText.textContent = "The file upload could not be completed.";
      downloadAllButton.disabled = true;
    } else {
      dashboardStatusBadge.textContent = "UPDATING";
      dashboardStatusBadge.classList.add("status-pill--waiting");
      dashboardStatusText.textContent = "Session status is being updated.";
      downloadAllButton.disabled = true;
    }

    document.querySelectorAll(".download-file-button").forEach((button) => {
      button.disabled = disableDownloads;
    });

    updateReceiverProgress(normalized);
  }

  function updateDownloadedFileStatus(status, filename) {
    setStatusBadge(status);
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
      emptyMessage.className = "uploaded-file-empty";
      emptyMessage.textContent = "No files have been uploaded yet.";
      uploadedFilesList.appendChild(emptyMessage);
      return;
    }

    files.forEach((file) => {
      const item = document.createElement("li");
      item.className = "uploaded-file-item";
      const metaLabel = file.content_type ? `${file.content_type}` : "File";
      item.innerHTML = `
        <div class="uploaded-file-meta">
          <div>
            <strong>${file.filename}</strong>
            <p>${metaLabel}</p>
          </div>
          <div>
            <span>${formatBytes(file.size)}</span>
            <button type="button" class="download-file-button" data-filename="${encodeURIComponent(file.filename)}">Download</button>
          </div>
        </div>
      `;
      const button = item.querySelector("button");
      button?.addEventListener("click", () => {
        if (!sessionId) return;
        button.disabled = true;
        if (downloadAllButton) {
          downloadAllButton.disabled = true;
        }
        const filename = decodeURIComponent(button.dataset.filename || "");
        const url = `/download/${sessionId}?filename=${filename}`;
        try {
          window.open(url, "_blank");
        } catch (e) {
          window.location.href = url;
        }
        if (!statusPoll) {
          statusPoll = setInterval(pollSessionStatus, 3000);
        }
      });
      uploadedFilesList.appendChild(item);
    });
  }

  async function pollSessionStatus() {
    if (!sessionId || pollInFlight) return;

    const sessionIdToCheck = sessionId;
    pollInFlight = true;

    try {
      const response = await fetch(`/session/${sessionIdToCheck}`);
      // A session may have been regenerated while this request was in flight.
      if (sessionId !== sessionIdToCheck) return;

      if (!response.ok) {
        if (response.status === 404) {
          setDashboardMessage("Session not found.", true);
          setStatusBadge("unavailable");
          clearInterval(statusPoll);
          statusPoll = null;
        } else if (response.status === 410) {
          setDashboardMessage("Session expired.", true);
          setStatusBadge("expired");
          clearInterval(statusPoll);
          statusPoll = null;
        }
        return;
      }

      const session = await response.json();
      if (sessionId !== sessionIdToCheck) return;

      // A successful response is authoritative: remove any stale polling error.
      setDashboardMessage("");
      await renderUploadedFiles(session.files);
      const status = session.status || "waiting";
      updateDownloadedFileStatus(status, session.files?.[0]?.filename ?? null);
      if (status === "downloaded" || status === "expired") {
        clearInterval(statusPoll);
        statusPoll = null;
      }
    } catch (error) {
      // Network, proxy, timeout, and JSON failures are transient. Keep the
      // last known valid state visible and let the next poll retry.
    } finally {
      pollInFlight = false;
    }
  }

  downloadAllButton?.addEventListener("click", () => {
    if (!sessionId) return;
    const label = downloadAllButton.querySelector(".button-label-text");
    downloadAllButton.disabled = true;
    document.querySelectorAll(".download-file-button").forEach((button) => {
      button.disabled = true;
    });
    if (label) label.textContent = "Preparing download...";

    const url = `/download/${sessionId}?archive=true`;
    // Open the archive in a new tab so the current page can continue polling
    try {
      window.open(url, "_blank");
    } catch (e) {
      // fallback to navigation if popup blocked
      window.location.href = url;
    }

    // Ensure polling is active so we pick up the server marking the session as downloaded
    if (!statusPoll) {
      statusPoll = setInterval(pollSessionStatus, 3000);
    }

    setTimeout(() => {
      if (label) label.textContent = "Download All Files";
    }, 2000);
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
  listItem.className = "uploaded-file-item selected-file-item";
  listItem.dataset.index = String(index);

  const fileMeta = document.createElement("div");
  fileMeta.className = "uploaded-file-meta selected-file-meta";

  const fileDetails = document.createElement("div");
  const name = document.createElement("strong");
  name.className = "selected-file-name";
  name.textContent = file.name;

  const size = document.createElement("p");
  size.className = "selected-file-size";
  size.textContent = formatBytes(file.size);
  fileDetails.append(name, size);

  const removeButton = document.createElement("button");
  removeButton.type = "button";
  removeButton.className = "download-file-button remove-file-button";
  removeButton.textContent = "Remove";

  fileMeta.append(fileDetails, removeButton);
  listItem.append(fileMeta);
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

  const stepperItems = Array.from(document.querySelectorAll(".stepper-item"));
  const expiryValue = document.getElementById("session-expiry-value");
  if (expiryValue?.textContent) {
    expiryValue.textContent = formatTimestampToIST(expiryValue.textContent.trim());
  }

  const maxFileSizeValue = document.getElementById("max-file-size-value")?.dataset.maxFileSize;
  if (maxFileSizeValue) {
    maxFileSize = Number(maxFileSizeValue) * 1024 * 1024;
  }

  let selectedFiles = [];
  let uploadState = "initial";

  function updateStepState(state) {
    uploadState = state;
    stepperItems.forEach((item) => {
      const step = Number(item.dataset.step);
      item.classList.remove("stepper-item--active", "stepper-item--complete", "stepper-item--future");
      if (state === "initial") {
        item.classList.add(step === 1 ? "stepper-item--active" : "stepper-item--future");
      } else if (state === "ready") {
        if (step === 1) item.classList.add("stepper-item--complete");
        else if (step === 2) item.classList.add("stepper-item--active");
        else item.classList.add("stepper-item--future");
      } else if (state === "uploading") {
        if (step < 2) item.classList.add("stepper-item--complete");
        else if (step === 2) item.classList.add("stepper-item--active");
        else item.classList.add("stepper-item--future");
      } else if (state === "complete") {
        item.classList.add("stepper-item--complete");
      }
    });
  }

  updateStepState("initial");

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
      const mimeType = (file.type || "application/octet-stream").split(";")[0].trim().toLowerCase();
      if (!allowedExtensions.includes(extension) && !allowedMimeTypes.includes(mimeType)) {
        console.log("FILE VALIDATION", {
          name: file.name,
          mimeType: file.type,
          normalizedMimeType: mimeType,
          extension,
          allowedExtensions,
          allowedMimeTypes,
        });
        showUploadStatus("One or more files are invalid.", "error");
        if (uploadMessage) uploadMessage.textContent = `Invalid file type: ${file.name}`;
        return;
      }
      if (file.size > maxFileSize) {
        showUploadStatus("One or more files exceed the maximum size.", "error");
        if (uploadMessage) uploadMessage.textContent = `File too large: ${file.name}. Maximum is ${formatBytes(maxFileSize)}.`;
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
    updateStepState("ready");
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
    updateStepState("uploading");

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
      updateStepState("complete");
    } catch (error) {
      showUploadStatus(error.message || "Upload failed.", "error");
      if (uploadMessage) uploadMessage.textContent = error.message;
      uploadButton.disabled = false;
      cancelButton.disabled = false;
      updateProgress(0);
      updateStepState("ready");
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
