const form = document.getElementById("resolveForm");
const urlInput = document.getElementById("urlInput");
const pasteBtn = document.getElementById("pasteBtn");
const modeSelect = document.getElementById("modeSelect");
const qualitySelect = document.getElementById("qualitySelect");
const audioSelect = document.getElementById("audioSelect");
const apiKeyInput = document.getElementById("apiKeyInput");
const submitBtn = document.getElementById("submitBtn");
const btnText = document.getElementById("btnText");
const statusBox = document.getElementById("statusBox");
const resultBox = document.getElementById("resultBox");
const platformBadge = document.getElementById("platformBadge");
const resultTitle = document.getElementById("resultTitle");
const resultAuthor = document.getElementById("resultAuthor");
const itemsList = document.getElementById("itemsList");
const endpointPreview = document.getElementById("endpointPreview");

endpointPreview.textContent = `${window.location.origin}/api/v1/resolve`;

const savedKey = localStorage.getItem("clipsave_api_key") || "";
if (savedKey) {
  apiKeyInput.value = savedKey;
}

apiKeyInput.addEventListener("input", () => {
  localStorage.setItem("clipsave_api_key", apiKeyInput.value.trim());
});

pasteBtn.addEventListener("click", async () => {
  try {
    const text = await navigator.clipboard.readText();
    if (text) urlInput.value = text;
  } catch {
    urlInput.focus();
  }
});

function setStatus(msg, type) {
  statusBox.textContent = msg;
  statusBox.className = `status ${type}`;
}

function clearStatus() {
  statusBox.className = "status hidden";
}

function formatBytes(bytes) {
  if (!bytes) return "";
  const mb = bytes / (1024 * 1024);
  return mb >= 1 ? `${mb.toFixed(1)} MB` : `${Math.round(bytes / 1024)} KB`;
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  resultBox.classList.add("hidden");
  itemsList.innerHTML = "";
  submitBtn.disabled = true;
  btnText.textContent = "Đang xử lý...";
  setStatus("Đang bóc tách & chuẩn hóa media không watermark...", "loading");

  const headers = { "Content-Type": "application/json" };
  const key = apiKeyInput.value.trim();
  if (key) headers["X-API-Key"] = key;

  try {
    const resp = await fetch("/api/v1/resolve", {
      method: "POST",
      headers,
      body: JSON.stringify({
        url: urlInput.value.trim(),
        mode: modeSelect.value,
        quality: qualitySelect.value,
        audio_format: audioSelect.value,
        ios_compatible: true,
      }),
    });

    const data = await resp.json();
    if (!resp.ok) {
      throw new Error(data.detail || data.message || "Không thể xử lý đường dẫn.");
    }

    clearStatus();
    platformBadge.textContent = data.platform;
    resultTitle.textContent = data.title;
    resultAuthor.textContent = data.author ? `Tác giả: ${data.author}` : "";

    data.items.forEach((item, index) => {
      const row = document.createElement("div");
      row.className = "item-row";

      const info = document.createElement("div");
      info.className = "item-info";
      const label = item.type === "video" ? "Video" : item.type === "image" ? "Ảnh" : "Âm thanh";
      const dims = item.width && item.height ? `${item.width}x${item.height}` : "";
      const size = formatBytes(item.size_bytes);
      const details = [item.ext.toUpperCase(), dims, size].filter(Boolean).join(" • ");

      info.innerHTML = `<strong>${label} #${index + 1}</strong><span class="muted">${details}</span>`;

      const link = document.createElement("a");
      link.className = "download-link";
      link.href = item.download_url;
      link.download = item.filename;
      link.textContent = "Tải về";

      row.appendChild(info);
      row.appendChild(link);
      itemsList.appendChild(row);
    });

    resultBox.classList.remove("hidden");
  } catch (err) {
    setStatus(err.message || "Có lỗi xảy ra.", "error");
  } finally {
    submitBtn.disabled = false;
    btnText.textContent = "Phân tích & Tải xuống";
  }
});
