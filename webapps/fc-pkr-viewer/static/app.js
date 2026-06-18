function escapeHtml(value) {
  if (value === null || value === undefined) return "";

  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function switchTab(tab) {
  document.querySelectorAll(".tab").forEach(el => {
    el.classList.remove("active");
  });

  document.querySelectorAll(".panel").forEach(el => {
    el.classList.remove("active");
  });

  if (tab === "fc") {
    document.querySelectorAll(".tab")[0].classList.add("active");
    document.getElementById("fc-panel").classList.add("active");
    loadFederatedCatalog();
  } else {
    document.querySelectorAll(".tab")[1].classList.add("active");
    document.getElementById("pkr-panel").classList.add("active");
  }
}

function buildQuery(params) {
  const q = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value && value.trim() !== "") {
      q.append(key, value.trim());
    }
  });

  const s = q.toString();
  return s ? `?${s}` : "";
}

async function loadFederatedCatalog() {
  const resourceId = document.getElementById("fc-resource-id").value;
  const userId = document.getElementById("fc-user-id").value;
  const keyword = document.getElementById("fc-keyword").value;

  const query = buildQuery({
    resource_id: resourceId,
    user_id: userId,
    keyword: keyword,
  });

  const res = await fetch(`/api/fc${query}`);
  const data = await res.json();
  const items = Array.isArray(data) ? data : [data];

  document.getElementById("fc-summary").textContent =
    `${items.length} catalog entries`;

  const tbody = document.getElementById("fc-body");

  if (items.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" class="empty">No catalog entries found.</td></tr>`;
    return;
  }

  tbody.innerHTML = items.map(item => `
    <tr>
      <td><span class="pill">${escapeHtml(item.resource_id)}</span></td>
      <td class="mono">${escapeHtml(item.user_id)}</td>
      <td>${escapeHtml(item.description)}</td>
      <td class="mono">${escapeHtml(item.endpoint)}</td>
      <td class="mono">${escapeHtml(item.resource_path)}</td>
      <td class="mono">${escapeHtml(item.registered_at)}</td>
    </tr>
  `).join("");
}

async function loadPublicKey() {
  const userId = document.getElementById("pkr-user-id").value.trim();
  const tbody = document.getElementById("pkr-body");

  if (!userId) {
    document.getElementById("pkr-summary").textContent = "Enter user_id.";
    tbody.innerHTML = `<tr><td colspan="3" class="empty">No user_id specified.</td></tr>`;
    return;
  }

  const res = await fetch(`/api/pkr/${encodeURIComponent(userId)}`);
  const item = await res.json();

  if (!item) {
    document.getElementById("pkr-summary").textContent = "0 public key entries";
    tbody.innerHTML = `<tr><td colspan="3" class="empty">Public key not found.</td></tr>`;
    return;
  }

  document.getElementById("pkr-summary").textContent = "1 public key entry";

  tbody.innerHTML = `
    <tr>
      <td><span class="pill">${escapeHtml(item.user_id)}</span></td>
      <td class="mono">
        <div class="key-box">${escapeHtml(item.public_key)}</div>
      </td>
      <td class="mono">${escapeHtml(item.registered_at)}</td>
    </tr>
  `;
}

async function loadAllPublicKeys() {
  const res = await fetch("/api/pkr");
  const items = await res.json();

  document.getElementById("pkr-summary").textContent =
    `${items.length} public key entries`;

  const tbody = document.getElementById("pkr-body");

  if (items.length === 0) {
    tbody.innerHTML = `<tr><td colspan="3" class="empty">No public keys found.</td></tr>`;
    return;
  }

  tbody.innerHTML = items.map(item => `
    <tr>
      <td><span class="pill">${escapeHtml(item.user_id)}</span></td>
      <td class="mono">
        <div class="key-box">${escapeHtml(item.public_key)}</div>
      </td>
      <td class="mono">${escapeHtml(item.registered_at)}</td>
    </tr>
  `).join("");
}

loadFederatedCatalog();
