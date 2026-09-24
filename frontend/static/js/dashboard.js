let categories = [];
let rooms = [];
let activeCategoryId = null; // null = "All"

async function init() {
  const user = await requireAuth();
  if (!user) return;
  document.getElementById("welcome-text").textContent = `Welcome, ${user.name}`;

  document.getElementById("logout-btn").addEventListener("click", async () => {
    await Api.post("/api/auth/logout");
    window.location.href = "/index.html";
  });

  await loadCategories();
  await loadRooms();
  bindModals();
}

async function loadCategories() {
  categories = await Api.get("/api/categories");
  renderChips();
  populateCategorySelect();
}

async function loadRooms() {
  const path = activeCategoryId ? `/api/rooms?category_id=${activeCategoryId}` : "/api/rooms";
  rooms = await Api.get(path);
  renderRooms();
}

function renderChips() {
  const row = document.getElementById("category-chips");
  row.innerHTML = "";

  const allChip = document.createElement("div");
  allChip.className = "chip" + (activeCategoryId === null ? " active" : "");
  allChip.textContent = "All";
  allChip.addEventListener("click", () => { activeCategoryId = null; renderChips(); loadRooms(); });
  row.appendChild(allChip);

  categories.forEach((c) => {
    const chip = document.createElement("div");
    chip.className = "chip" + (activeCategoryId === c.id ? " active" : "");
    chip.textContent = `${c.name} (${c.room_count})`;
    chip.addEventListener("click", () => { activeCategoryId = c.id; renderChips(); loadRooms(); });
    row.appendChild(chip);
  });
}

function renderRooms() {
  const grid = document.getElementById("room-grid");
  const empty = document.getElementById("empty-state");
  grid.innerHTML = "";

  if (rooms.length === 0) {
    empty.style.display = "block";
    return;
  }
  empty.style.display = "none";

  rooms.forEach((r) => {
    const card = document.createElement("div");
    card.className = "room-card";

    const thumb = document.createElement("div");
    thumb.className = "room-thumb";
    if (r.has_panorama) {
      const img = document.createElement("img");
      img.src = `/api/rooms/${r.id}/thumbnail-file`;
      img.loading = "lazy";
      img.alt = r.name;
      thumb.appendChild(img);
    } else {
      thumb.textContent = "No panorama yet";
    }

    const body = document.createElement("div");
    body.className = "room-card-body";
    body.innerHTML = `
      <div class="room-name">${escapeHtml(r.name)}</div>
      <div class="room-meta">${escapeHtml(r.category_name)} · ${r.source_image_count || 0} source images</div>
    `;

    const actions = document.createElement("div");
    actions.className = "room-card-actions";
    const viewBtn = document.createElement("button");
    viewBtn.className = "btn-secondary btn-sm";
    viewBtn.textContent = "Open";
    viewBtn.addEventListener("click", () => { window.location.href = `/room.html?id=${r.id}`; });
    actions.appendChild(viewBtn);

    const delBtn = document.createElement("button");
    delBtn.className = "btn-danger btn-sm";
    delBtn.textContent = "Delete";
    delBtn.addEventListener("click", async () => {
      if (!confirm(`Delete "${r.name}"? This cannot be undone.`)) return;
      await Api.del(`/api/rooms/${r.id}`);
      await loadCategories();
      await loadRooms();
    });
    actions.appendChild(delBtn);

    card.appendChild(thumb);
    card.appendChild(body);
    card.appendChild(actions);
    grid.appendChild(card);
  });
}

function populateCategorySelect() {
  const select = document.getElementById("modal-category");
  select.innerHTML = categories.map((c) => `<option value="${c.id}">${escapeHtml(c.name)}</option>`).join("");
}

function bindModals() {
  const roomModal = document.getElementById("room-modal");
  document.getElementById("new-room-btn").addEventListener("click", () => {
    document.getElementById("modal-room-name").value = "";
    document.getElementById("modal-room-desc").value = "";
    document.getElementById("modal-error").classList.remove("visible");
    roomModal.style.display = "flex";
  });
  document.getElementById("modal-cancel").addEventListener("click", () => roomModal.style.display = "none");
  document.getElementById("modal-create").addEventListener("click", async () => {
    const name = document.getElementById("modal-room-name").value.trim();
    const category_id = parseInt(document.getElementById("modal-category").value, 10);
    const description = document.getElementById("modal-room-desc").value.trim() || null;
    if (!name) {
      const err = document.getElementById("modal-error");
      err.textContent = "Room name is required.";
      err.classList.add("visible");
      return;
    }
    try {
      const room = await Api.post("/api/rooms", { category_id, name, description });
      window.location.href = `/room.html?id=${room.id}`;
    } catch (e) {
      const err = document.getElementById("modal-error");
      err.textContent = e.message;
      err.classList.add("visible");
    }
  });

  const catModal = document.getElementById("category-modal");
  document.getElementById("new-category-btn").addEventListener("click", () => {
    document.getElementById("new-category-name").value = "";
    document.getElementById("category-error").classList.remove("visible");
    catModal.style.display = "flex";
  });
  document.getElementById("category-cancel").addEventListener("click", () => catModal.style.display = "none");
  document.getElementById("category-create").addEventListener("click", async () => {
    const name = document.getElementById("new-category-name").value.trim();
    if (!name) return;
    try {
      await Api.post("/api/categories", { name });
      catModal.style.display = "none";
      await loadCategories();
    } catch (e) {
      const err = document.getElementById("category-error");
      err.textContent = e.message;
      err.classList.add("visible");
    }
  });
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

init();
