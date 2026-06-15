const textarea = document.getElementById("markdown");
const printBtn = document.getElementById("print");
const statusDiv = document.getElementById("status");
const previewEl = document.getElementById("preview");

// Replaced at runtime from GET /config so the preview tracks THERMAL_LINE_WIDTH.
let lineWidth = 48;

async function loadConfig() {
  try {
    const res = await fetch("/config");
    if (!res.ok) return;
    const data = await res.json();
    if (Number.isInteger(data.line_width) && data.line_width > 0) {
      lineWidth = data.line_width;
      previewEl.style.width = `${lineWidth}ch`;
      updatePreview();
    }
  } catch {
    // Keep the 48-column fallback.
  }
}

// ── editor helpers ───────────────────────────────────────────

function injectText(text) {
  const start = textarea.selectionStart;
  textarea.value = textarea.value.substring(0, start) + text + textarea.value.substring(start);
  textarea.setSelectionRange(start + text.length, start + text.length);
  textarea.focus();
}

function encloseSelectedText(characters) {
  const start = textarea.selectionStart;
  const end = textarea.selectionEnd;
  const selected = textarea.value.substring(start, end);
  const enclosed = characters + selected + characters;
  textarea.value = textarea.value.substring(0, start) + enclosed + textarea.value.substring(end);
  textarea.setSelectionRange(
    start + characters.length,
    start + characters.length + selected.length,
  );
  textarea.focus();
}

function convertToList(type) {
  const start = textarea.selectionStart;
  const end = textarea.selectionEnd;
  const lines = textarea.value
    .substring(start, end)
    .split("\n")
    .map((line, i) => (type === "1" ? `${i + 1}. ${line}` : `${type} ${line}`));
  textarea.value =
    textarea.value.substring(0, start) + lines.join("\n") + textarea.value.substring(end);
  textarea.focus();
}

document.getElementById("editorButtons").addEventListener("click", (e) => {
  const btn = e.target.closest("[data-action]");
  if (!btn) return;
  e.preventDefault();
  switch (btn.dataset.action) {
    case "H1":
      injectText("# ");
      break;
    case "H2":
      injectText("## ");
      break;
    case "B":
      encloseSelectedText("**");
      break;
    case "U":
      encloseSelectedText("__");
      break;
    case "alignLeft":
      injectText("[align=left]");
      break;
    case "alignCenter":
      injectText("[align=center]");
      break;
    case "alignRight":
      injectText("[align=right]");
      break;
    case "qr":
      injectText("[qr=]");
      break;
    case "L-":
      injectText("[effect=line--]");
      break;
    case "L*":
      injectText("[effect=line-*]");
      break;
    case "checkList":
      convertToList("[ ]");
      break;
    case "bulletList":
      convertToList("*");
      break;
    case "numberList":
      convertToList("1");
      break;
    case "T1":
      textarea.value = btn.dataset.template.replaceAll("\\n", "\n");
      break;
  }
  updatePreview();
});

// ── preview renderer ─────────────────────────────────────────

function escapeHtml(str) {
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function parseInline(text) {
  // Escape HTML first so content inside tags is safe, then apply formatting.
  return escapeHtml(text)
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/__(.+?)__/g, "<u>$1</u>");
}

function renderLine(raw) {
  if (raw.trim() === "") return '<div class="receipt-line">&nbsp;</div>';

  let line = raw;
  let align = "left";

  // [effect=line-X]
  const effect = line.match(/^\[effect=line-(.)\]/);
  if (effect) {
    return `<div class="receipt-line">${escapeHtml(effect[1].repeat(lineWidth))}</div>`;
  }

  // [align=...]
  const alignMatch = line.match(/^\[align=(left|center|right)\]/);
  if (alignMatch) {
    align = alignMatch[1];
    line = line.slice(alignMatch[0].length).trim();
  }

  // [qr=...]
  const qr = line.match(/^\[qr=(.*?)\]/);
  if (qr) {
    const url = qr[1] || "";
    if (!url)
      return `<div class="receipt-line ${align}"><span class="receipt-qr">▣ QR: (empty)</span></div>`;
    const justify = align === "center" ? "center" : align === "right" ? "flex-end" : "flex-start";
    return `<div class="receipt-line" style="display:flex;justify-content:${justify}"><canvas class="qr-canvas" data-url="${escapeHtml(url)}" width="120" height="120"></canvas></div>`;
  }

  // headings
  let cls = `receipt-line ${align}`;
  if (line.startsWith("## ")) {
    line = line.slice(3);
    cls += " h2";
  } else if (line.startsWith("# ")) {
    line = line.slice(2);
    cls += " h1";
  }

  return `<div class="${cls}">${parseInline(line)}</div>`;
}

async function updatePreview() {
  const md = textarea.value;
  if (!md.trim()) {
    previewEl.innerHTML =
      '<span class="text-gray-300 text-xs italic">Start typing to see a preview…</span>';
    return;
  }

  previewEl.innerHTML = md.split("\n").map(renderLine).join("");

  // Render any QR codes into their canvas elements.
  for (const canvas of previewEl.querySelectorAll(".qr-canvas")) {
    try {
      await QRCode.toCanvas(canvas, canvas.dataset.url, {
        width: 120,
        margin: 1,
        color: { dark: "#000000", light: "#ffffff" },
      });
    } catch {
      const ctx = canvas.getContext("2d");
      ctx.font = "10px monospace";
      ctx.fillText("invalid URL", 4, 14);
    }
  }
}

// Debounced live update while typing
let previewTimer;
textarea.addEventListener("input", () => {
  clearTimeout(previewTimer);
  previewTimer = setTimeout(updatePreview, 120);
});

// ── print ────────────────────────────────────────────────────

function setStatus(message, ok) {
  statusDiv.textContent = message;
  statusDiv.className = ok
    ? "text-sm px-3 py-2 rounded-lg bg-green-50 text-green-700 border border-green-200"
    : "text-sm px-3 py-2 rounded-lg bg-red-50 text-red-700 border border-red-200";
}

async function handlePrint() {
  const markdown = textarea.value.trim();
  if (!markdown) return;

  printBtn.disabled = true;
  printBtn.textContent = "Printing…";
  statusDiv.textContent = "";
  statusDiv.className = "";

  try {
    const response = await fetch("/print", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ markdown }),
    });
    const result = await response.json();

    if (response.ok) {
      setStatus("Sent to printer.", true);
    } else {
      setStatus("Error: " + (result.detail || "Failed to print"), false);
    }
  } catch (err) {
    setStatus("Error: " + err.message, false);
  } finally {
    printBtn.disabled = false;
    printBtn.textContent = "Print";
  }
}

printBtn.addEventListener("click", handlePrint);

textarea.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
    e.preventDefault();
    handlePrint();
  }
});

loadConfig();
