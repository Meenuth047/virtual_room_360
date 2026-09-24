const params = new URLSearchParams(window.location.search);
const roomId = params.get("id");
let selectedFiles = [];
let viewer = null;

function showError(msg) {
  const el = document.getElementById("room-error");
  el.textContent = msg;
  el.classList.add("visible");
}
function hideError() {
  document.getElementById("room-error").classList.remove("visible");
}

async function init() {
  if (!roomId) {
    window.location.href = "/dashboard.html";
    return;
  }
  const user = await requireAuth();
  if (!user) return;
  document.getElementById("welcome-text").textContent = `Welcome, ${user.name}`;

  document.getElementById("logout-btn").addEventListener("click", async () => {
    await Api.post("/api/auth/logout");
    window.location.href = "/index.html";
  });

  await loadRoom();
  await loadExistingImages();
  bindUpload();
  bindActions();
}

async function loadRoom() {
  let room;
  try {
    room = await Api.get(`/api/rooms/${roomId}`);
  } catch (e) {
    showError("This room could not be found.");
    return;
  }
  document.getElementById("room-name").textContent = room.name;
  document.getElementById("room-meta").textContent =
    `${room.category_name} · Updated ${new Date(room.updated_at).toLocaleString()}`;

  document.getElementById("edit-name").value = room.name;
  document.getElementById("edit-desc").value = room.description || "";

  if (room.panorama && room.panorama.processing_status === "complete") {
    document.getElementById("viewer-section").style.display = "block";
    initViewer();
  } else if (room.panorama && room.panorama.processing_status === "failed") {
    showError(room.panorama.error_message || "The last panorama generation attempt failed.");
  }
}

function initViewer() {
  const wrap = document.getElementById("viewer-wrap");
  viewer = new PanoramaViewer(wrap);
  const loadingEl = document.getElementById("viewer-loading");
  viewer.onLoaded = () => { loadingEl.style.display = "none"; };
  viewer.onError = () => { loadingEl.textContent = "Could not load the panorama image."; };
  viewer.loadImage(`/api/rooms/${roomId}/panorama-file`);

  document.getElementById("zoom-in-btn").addEventListener("click", () => viewer.zoom(-8));
  document.getElementById("zoom-out-btn").addEventListener("click", () => viewer.zoom(8));
  document.getElementById("fullscreen-btn").addEventListener("click", () => {
    if (wrap.requestFullscreen) wrap.requestFullscreen();
  });
}

async function loadExistingImages() {
  const data = await Api.get(`/api/rooms/${roomId}/images`);
  document.getElementById("selected-count").textContent =
    data.images.length > 0 ? `${data.images.length} photos already uploaded to this room` : "No images selected";
}

function bindUpload() {
  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("file-input");

  dropzone.addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", (e) => addFiles(Array.from(e.target.files)));

  dropzone.addEventListener("dragover", (e) => { e.preventDefault(); dropzone.classList.add("dragover"); });
  dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));
  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragover");
    addFiles(Array.from(e.dataTransfer.files));
  });

  document.getElementById("clear-all-btn").addEventListener("click", () => {
    selectedFiles = [];
    renderThumbs();
  });
}

const ALLOWED_TYPES = ["image/jpeg", "image/png", "image/webp"];
const MAX_FILE_MB = 15;

function addFiles(files) {
  hideError();
  for (const f of files) {
    if (!ALLOWED_TYPES.includes(f.type)) {
      showError(`${f.name} is not a supported image type.`);
      continue;
    }
    if (f.size > MAX_FILE_MB * 1024 * 1024) {
      showError(`${f.name} exceeds the ${MAX_FILE_MB}MB size limit.`);
      continue;
    }
    selectedFiles.push(f);
  }
  if (selectedFiles.length > 40) {
    showError("You can select at most 40 photos at a time.");
    selectedFiles = selectedFiles.slice(0, 40);
  }
  renderThumbs();
}

function renderThumbs() {
  const grid = document.getElementById("thumb-grid");
  grid.innerHTML = "";
  selectedFiles.forEach((f, idx) => {
    const item = document.createElement("div");
    item.className = "thumb-item";
    const img = document.createElement("img");
    img.src = URL.createObjectURL(f);
    item.appendChild(img);

    const removeBtn = document.createElement("button");
    removeBtn.className = "remove-btn";
    removeBtn.textContent = "×";
    removeBtn.addEventListener("click", () => {
      selectedFiles.splice(idx, 1);
      renderThumbs();
    });
    item.appendChild(removeBtn);
    grid.appendChild(item);
  });
  document.getElementById("selected-count").textContent =
    selectedFiles.length > 0 ? `Selected Images: ${selectedFiles.length}` : "No images selected";
}

function bindActions() {
  document.getElementById("upload-btn").addEventListener("click", async () => {
    hideError();
    if (selectedFiles.length === 0) {
      showError("Please select at least one photo to upload.");
      return;
    }
    const btn = document.getElementById("upload-btn");
    btn.disabled = true;
    btn.textContent = "Uploading…";
    try {
      const formData = new FormData();
      selectedFiles.forEach((f) => formData.append("files", f));
      await Api.postForm(`/api/rooms/${roomId}/images`, formData);
      selectedFiles = [];
      renderThumbs();
      await loadExistingImages();
    } catch (e) {
      showError(e.message);
    } finally {
      btn.disabled = false;
      btn.textContent = "Upload Photos";
    }
  });

  document.getElementById("generate-btn").addEventListener("click", async () => {
    hideError();
    const btn = document.getElementById("generate-btn");
    btn.disabled = true;
    document.getElementById("progress-panel").style.display = "block";
    try {
      await Api.post(`/api/rooms/${roomId}/generate`);
      await loadRoom();
    } catch (e) {
      showError(e.message);
    } finally {
      btn.disabled = false;
      document.getElementById("progress-panel").style.display = "none";
    }
  });

  document.getElementById("edit-room-btn").addEventListener("click", () => {
    document.getElementById("edit-modal").style.display = "flex";
  });
  document.getElementById("edit-cancel").addEventListener("click", () => {
    document.getElementById("edit-modal").style.display = "none";
  });
  document.getElementById("edit-save").addEventListener("click", async () => {
    const name = document.getElementById("edit-name").value.trim();
    const description = document.getElementById("edit-desc").value.trim();
    if (!name) return;
    try {
      await Api.put(`/api/rooms/${roomId}`, { name, description });
      document.getElementById("edit-modal").style.display = "none";
      await loadRoom();
    } catch (e) {
      showError(e.message);
    }
  });

  document.getElementById("delete-room-btn").addEventListener("click", async () => {
    if (!confirm("Delete this room and all its photos/panorama? This cannot be undone.")) return;
    await Api.del(`/api/rooms/${roomId}`);
    window.location.href = "/dashboard.html";
  });
}

init();
