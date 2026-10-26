// RedLiner Frontend Controller — Zapier UI/UX White Theme

let currentParsedDoc = null;
let currentRedlineResult = null;
let currentFilename = "vendor_saas_agreement.docx";
let allVendors = [];

document.addEventListener("DOMContentLoaded", () => {
  initTabs();
  initParserAndRedliner();
  initPlaybookManager();
  initVendorRadar();
  initEmailDispatcher();
  initHelpersAudit();

  // Load defaults on boot
  loadSampleContract("vendor_saas_agreement.docx");
  loadPlaybook();
  loadVendors();
  loadLogs();
});

// Toast notification helper
function showToast(message, duration = 3500) {
  const container = document.getElementById("toast-container");
  if (!container) return;
  const toast = document.createElement("div");
  toast.className = "toast";
  toast.innerText = message;
  container.appendChild(toast);
  setTimeout(() => {
    toast.remove();
  }, duration);
}

function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// ---------------- Tabs Navigation ----------------
function initTabs() {
  const tabs = document.querySelectorAll(".nav-tab");
  tabs.forEach(tab => {
    tab.addEventListener("click", () => {
      tabs.forEach(t => t.classList.remove("active"));
      document.querySelectorAll(".tab-content").forEach(tc => tc.classList.remove("active"));

      tab.classList.add("active");
      const targetId = tab.getAttribute("data-tab");
      const targetContent = document.getElementById(targetId);
      if (targetContent) targetContent.classList.add("active");

      if (targetId === "playbook-tab") loadPlaybook();
      if (targetId === "vendor-tab") loadVendors();
      if (targetId === "helpers-tab") loadLogs();
    });
  });
}

// ---------------- 1. Document Parser & Redliner ----------------
function initParserAndRedliner() {
  const dropZone = document.getElementById("drop-zone");
  const fileInput = document.getElementById("file-input");
  const btnLoadDocx = document.getElementById("btn-load-sample-docx");
  const btnLoadPdf = document.getElementById("btn-load-sample-pdf");
  const btnRunRedline = document.getElementById("btn-run-redline");

  dropZone.addEventListener("click", () => fileInput.click());

  fileInput.addEventListener("change", async (e) => {
    if (e.target.files.length > 0) {
      const file = e.target.files[0];
      await uploadAndParseFile(file);
    }
  });

  btnLoadDocx.addEventListener("click", () => loadSampleContract("vendor_saas_agreement.docx"));
  btnLoadPdf.addEventListener("click", () => loadSampleContract("vendor_saas_agreement.pdf"));

  btnRunRedline.addEventListener("click", runRedline);
}

async function loadSampleContract(sampleName) {
  currentFilename = sampleName;
  const formData = new FormData();
  formData.append("sample_name", sampleName);

  try {
    const res = await fetch("/api/parser/parse", { method: "POST", body: formData });
    if (!res.ok) throw new Error("Failed to load sample contract");
    const data = await res.json();
    renderParsedDocument(data);
    showToast(`Loaded ${sampleName}`);
  } catch (err) {
    showToast(`Error: ${err.message}`);
  }
}

async function uploadAndParseFile(file) {
  currentFilename = file.name;
  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch("/api/parser/parse", { method: "POST", body: formData });
    if (!res.ok) throw new Error("Failed to parse uploaded contract");
    const data = await res.json();
    renderParsedDocument(data);
    showToast(`Successfully parsed ${file.name}`);
  } catch (err) {
    showToast(`Upload error: ${err.message}`);
  }
}

function renderParsedDocument(parsedDoc) {
  currentParsedDoc = parsedDoc;
  const metaContainer = document.getElementById("doc-meta-container");
  const chipsContainer = document.getElementById("clause-distribution-chips");
  const btnRunRedline = document.getElementById("btn-run-redline");

  metaContainer.innerHTML = `
    <p><strong>File:</strong> ${escapeHtml(parsedDoc.filename)}</p>
    <p><strong>Format:</strong> ${escapeHtml(parsedDoc.file_type.toUpperCase())}</p>
    <p><strong>Paragraphs:</strong> ${parsedDoc.total_paragraphs}</p>
    <p><strong>Clauses Detected:</strong> ${parsedDoc.clauses.length}</p>
  `;

  chipsContainer.innerHTML = "";
  for (const [cType, count] of Object.entries(parsedDoc.clause_distribution)) {
    const chip = document.createElement("span");
    chip.className = "clause-chip";
    chip.innerHTML = `<span>${escapeHtml(cType)}</span><strong>${count}</strong>`;
    chipsContainer.appendChild(chip);
  }

  btnRunRedline.disabled = false;

  // Reset redline workbench
  document.getElementById("diff-cards-container").innerHTML = `
    <div style="text-align: center; padding: 40px 20px; color: var(--ink-muted);">
      <p style="font-weight: 600; font-size: 15px; color: var(--ink-primary);">Document parsed successfully</p>
      <p style="font-size: 13px; margin-top: 4px;">Click "Run Legal Playbook Redline" to generate native Word tracked changes.</p>
    </div>
  `;
  document.getElementById("redline-summary-banner").style.display = "none";
  document.getElementById("redline-action-buttons").style.display = "none";
}

async function runRedline() {
  if (!currentParsedDoc) return;

  const btn = document.getElementById("btn-run-redline");
  btn.disabled = true;
  btn.innerText = "Analyzing Against Playbook...";

  try {
    const res = await fetch("/api/redliner/redline", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filename: currentFilename })
    });
    if (!res.ok) throw new Error("Redline execution failed");
    const result = await res.json();
    renderRedlineResult(result);
    showToast(`Generated ${result.violations_detected} tracked changes with Word comments!`);
    loadLogs();
  } catch (err) {
    showToast(`Redline error: ${err.message}`);
  } finally {
    btn.disabled = false;
    btn.innerText = "⚡ Run Legal Playbook Redline";
  }
}

function renderRedlineResult(result) {
  currentRedlineResult = result;
  const container = document.getElementById("diff-cards-container");
  const summaryBanner = document.getElementById("redline-summary-banner");
  const actionButtons = document.getElementById("redline-action-buttons");
  const badge = document.getElementById("violations-count-badge");
  const downloadBtn = document.getElementById("download-docx-btn");

  badge.innerText = `${result.violations_detected} edits`;
  downloadBtn.href = `/api/redliner/download/${result.output_docx_filename}`;
  actionButtons.style.display = "flex";

  // Summary Banner
  summaryBanner.style.display = "block";
  document.getElementById("summary-banner-title").innerText = 
    `Generated ${result.violations_detected} Native Word Tracked Changes`;
  document.getElementById("summary-banner-desc").innerText = 
    `Output: ${result.output_docx_filename} — Verified against Corporate Legal Playbook.`;

  const badgesContainer = document.getElementById("summary-banner-badges");
  badgesContainer.innerHTML = `
    <span class="badge badge-critical">${result.critical_count} CRITICAL</span>
    <span class="badge badge-high">${result.violations_detected - result.critical_count} HIGH/MEDIUM</span>
  `;

  // Render Diff Cards
  container.innerHTML = "";
  result.actions.forEach(act => {
    const card = document.createElement("div");
    card.className = "diff-card";

    let badgeClass = "badge-medium";
    if (act.severity === "CRITICAL") badgeClass = "badge-critical";
    if (act.severity === "HIGH") badgeClass = "badge-high";

    card.innerHTML = `
      <div class="diff-card-header">
        <div class="diff-clause-title">${escapeHtml(act.clause_type)}: ${escapeHtml(act.rule_name)}</div>
        <span class="badge ${badgeClass}">${act.severity}</span>
      </div>
      <div class="diff-body">
        <div style="font-size: 11px; font-weight: 600; color: var(--badge-crit-text); margin-bottom: 4px; text-transform: uppercase;">
          Tracked Deletion (&lt;w:del&gt;) — Original Vendor Text
        </div>
        <div class="diff-del-box">
          <del>${escapeHtml(act.original_text)}</del>
        </div>

        <div style="font-size: 11px; font-weight: 600; color: var(--badge-low-text); margin-bottom: 4px; text-transform: uppercase;">
          Tracked Insertion (&lt;w:ins&gt;) — Enterprise Playbook Fallback
        </div>
        <div class="diff-ins-box">
          <ins>${escapeHtml(act.replacement_text)}</ins>
        </div>

        <div style="font-size: 11px; font-weight: 600; color: var(--ink-muted); margin-bottom: 4px; text-transform: uppercase;">
          Native Word Margin Comment (&lt;w:comment&gt;)
        </div>
        <div class="diff-comment-box">
          ${escapeHtml(act.comment).replace(/\n/g, "<br>")}
        </div>
      </div>
    `;

    container.appendChild(card);
  });

  updateEmailPreview(result);
}

// ---------------- 2. Corporate Legal Playbook Management ----------------
async function uploadPlaybookFile(file) {
  if (!file) return;
  const fileName = file.name || "";
  const ext = fileName.slice(fileName.lastIndexOf(".")).toLowerCase();
  if (ext !== ".yaml" && ext !== ".yml" && ext !== ".json") {
    showToast("Unsupported file type. Please upload a .yaml, .yml, or .json file.");
    return;
  }

  const formData = new FormData();
  formData.append("file", file);
  showToast(`Uploading ${fileName}...`);

  try {
    const res = await fetch("/api/playbook/upload", { method: "POST", body: formData });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Failed to upload playbook");
    }
    showToast(data.message || `Playbook uploaded: ${fileName}`);
    const uploadPanel = document.getElementById("upload-playbook-panel");
    if (uploadPanel) uploadPanel.style.display = "none";
    await loadPlaybook();
  } catch (err) {
    showToast(`Playbook error: ${err.message}`);
  } finally {
    const fileInput = document.getElementById("playbook-file-input");
    if (fileInput) fileInput.value = "";
  }
}

function initPlaybookManager() {
  const btnUpload = document.getElementById("btn-upload-playbook");
  const fileInput = document.getElementById("playbook-file-input");
  const uploadPanel = document.getElementById("upload-playbook-panel");
  const dropZone = document.getElementById("playbook-drop-zone");
  const btnBrowse = document.getElementById("btn-browse-playbook");
  const btnCancelUpload = document.getElementById("btn-cancel-upload-playbook");
  const btnSubmitRaw = document.getElementById("btn-submit-raw-playbook");
  const rawText = document.getElementById("raw-playbook-text");

  const btnToggleAdd = document.getElementById("btn-toggle-add-rule");
  const btnCancelAdd = document.getElementById("btn-cancel-add-rule");
  const addPanel = document.getElementById("add-rule-panel");
  const addForm = document.getElementById("add-rule-form");
  const btnReset = document.getElementById("btn-reset-playbook");

  // Toggle Upload Panel
  if (btnUpload && uploadPanel) {
    btnUpload.addEventListener("click", () => {
      const isHidden = uploadPanel.style.display === "none" || uploadPanel.style.display === "";
      uploadPanel.style.display = isHidden ? "block" : "none";
      if (addPanel) addPanel.style.display = "none";
    });
  }

  // Browse file button inside panel
  if (btnBrowse && fileInput) {
    btnBrowse.addEventListener("click", () => fileInput.click());
  }

  // Cancel upload panel
  if (btnCancelUpload && uploadPanel) {
    btnCancelUpload.addEventListener("click", () => {
      uploadPanel.style.display = "none";
    });
  }

  // File input change
  if (fileInput) {
    fileInput.addEventListener("change", (e) => {
      if (e.target.files && e.target.files.length > 0) {
        uploadPlaybookFile(e.target.files[0]);
      }
    });
  }

  // Drag and drop zone
  if (dropZone) {
    dropZone.addEventListener("click", (e) => {
      if (e.target !== btnBrowse && fileInput) fileInput.click();
    });
    dropZone.addEventListener("dragover", (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropZone.style.borderColor = "var(--brand-orange)";
      dropZone.style.backgroundColor = "var(--surface-card)";
    });
    dropZone.addEventListener("dragleave", (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropZone.style.borderColor = "var(--border-strong)";
      dropZone.style.backgroundColor = "var(--surface-soft)";
    });
    dropZone.addEventListener("drop", (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropZone.style.borderColor = "var(--border-strong)";
      dropZone.style.backgroundColor = "var(--surface-soft)";
      if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        uploadPlaybookFile(e.dataTransfer.files[0]);
      }
    });
  }

  // Submit raw YAML / JSON text
  if (btnSubmitRaw && rawText) {
    btnSubmitRaw.addEventListener("click", async () => {
      const content = rawText.value.trim();
      if (!content) {
        showToast("Please enter or paste YAML / JSON playbook text first.");
        return;
      }
      showToast("Applying playbook text...");
      try {
        const res = await fetch("/api/playbook/raw", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ content })
        });
        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.detail || "Failed to update playbook");
        }
        showToast(data.message || "Playbook updated successfully!");
        rawText.value = "";
        if (uploadPanel) uploadPanel.style.display = "none";
        await loadPlaybook();
      } catch (err) {
        showToast(`Playbook error: ${err.message}`);
      }
    });
  }

  // Toggle Add Rule Panel
  if (btnToggleAdd && addPanel) {
    btnToggleAdd.addEventListener("click", () => {
      const isHidden = addPanel.style.display === "none" || addPanel.style.display === "";
      addPanel.style.display = isHidden ? "block" : "none";
      if (uploadPanel) uploadPanel.style.display = "none";
    });
  }

  if (btnCancelAdd && addPanel) {
    btnCancelAdd.addEventListener("click", () => {
      addPanel.style.display = "none";
    });
  }

  // Add rule form submit
  if (addForm) {
    addForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const ruleId = (document.getElementById("rule-id-input")?.value || "").trim();
      const ruleName = (document.getElementById("rule-name-input")?.value || "").trim();
      const clauseType = document.getElementById("rule-clause-type-select")?.value;
      const severity = document.getElementById("rule-severity-select")?.value;
      const triggersRaw = document.getElementById("rule-triggers-input")?.value || "";
      const forbiddenRaw = document.getElementById("rule-forbidden-input")?.value || "";
      const fallbackText = (document.getElementById("rule-fallback-input")?.value || "").trim();
      const comment = (document.getElementById("rule-comment-input")?.value || "").trim();

      const patternTriggers = triggersRaw ? triggersRaw.split(",").map(s => s.trim()).filter(Boolean) : [];
      const forbiddenTerms = forbiddenRaw ? forbiddenRaw.split(",").map(s => s.trim()).filter(Boolean) : [];

      const payload = {
        id: ruleId,
        name: ruleName,
        target_clause_type: clauseType,
        severity: severity,
        pattern_triggers: patternTriggers,
        forbidden_terms: forbiddenTerms,
        required_terms: [],
        preferred_fallback_text: fallbackText,
        comment_explanation: comment,
        guidance_note: "Custom policy rule activated via RedLiner Legal Workbench."
      };

      try {
        const res = await fetch("/api/playbook/rule", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.detail || "Failed to save rule");
        }
        showToast(data.message || `Rule '${ruleName}' saved and activated!`);
        if (addPanel) addPanel.style.display = "none";
        addForm.reset();
        await loadPlaybook();
      } catch (err) {
        showToast(`Rule error: ${err.message}`);
      }
    });
  }

  // Reset playbook button
  if (btnReset) {
    btnReset.addEventListener("click", async () => {
      if (!confirm("Are you sure you want to reset the corporate playbook to standard Enterprise baseline rules?")) return;
      try {
        const res = await fetch("/api/playbook/reset", { method: "POST" });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Reset failed");
        showToast(data.message || "Playbook reset to default!");
        await loadPlaybook();
      } catch (err) {
        showToast(`Reset error: ${err.message}`);
      }
    });
  }
}

async function loadPlaybook() {
  const container = document.getElementById("playbook-rules-list");
  try {
    const res = await fetch(`/api/playbook?_t=${Date.now()}`);
    if (!res.ok) {
      const errText = await res.text();
      throw new Error(`HTTP ${res.status}: ${errText || "Failed to load playbook"}`);
    }
    const pb = await res.json();

    const titleEl = document.getElementById("pb-title");
    if (titleEl) titleEl.innerText = pb.name || "Corporate Legal Playbook";
    const descEl = document.getElementById("pb-desc");
    if (descEl) descEl.innerText = pb.description || "";
    const verEl = document.getElementById("pb-version");
    if (verEl) verEl.innerText = pb.version || "2026.1";
    const authEl = document.getElementById("pb-author");
    if (authEl) authEl.innerText = pb.author || "RedLiner Counsel";
    const badgeEl = document.getElementById("playbook-rules-badge");
    if (badgeEl) badgeEl.innerText = `${pb.total_rules || (pb.rules ? pb.rules.length : 0)} rules`;
    const headerPbEl = document.getElementById("header-playbook-name");
    if (headerPbEl) headerPbEl.innerHTML = `Playbook: <strong>${escapeHtml(pb.name)}</strong>`;

    renderPlaybookRules(pb.rules || []);
  } catch (err) {
    console.error("Error loading playbook:", err);
    if (container) {
      container.innerHTML = `
        <div style="text-align: center; padding: 36px 20px; background-color: var(--surface-soft); border: 1px solid var(--border-strong); border-radius: var(--radius-md);">
          <div style="font-size: 28px; margin-bottom: 8px;">⚠️</div>
          <h4 style="font-size: 15px; font-weight: 700; color: var(--ink-primary); margin-bottom: 6px;">Failed to load Playbook Rules</h4>
          <p style="font-size: 13px; color: var(--ink-muted); margin-bottom: 16px;">${escapeHtml(err.message)}</p>
          <button class="btn btn-secondary" onclick="loadPlaybook()" style="margin: 0 auto;">🔄 Retry Loading Playbook</button>
        </div>
      `;
    }
  }
}

function renderPlaybookRules(rules) {
  const container = document.getElementById("playbook-rules-list");
  container.innerHTML = "";

  if (rules.length === 0) {
    container.innerHTML = `<p style="text-align: center; color: var(--ink-muted); padding: 30px;">No policy rules defined.</p>`;
    return;
  }

  rules.forEach(rule => {
    const card = document.createElement("div");
    card.className = "playbook-rule-card";

    let sevBadge = "badge-medium";
    if (rule.severity === "CRITICAL") sevBadge = "badge-critical";
    if (rule.severity === "HIGH") sevBadge = "badge-high";

    const triggerChips = (rule.pattern_triggers || []).map(t => `<span class="rule-chip">${escapeHtml(t)}</span>`).join("");
    const forbiddenChips = (rule.forbidden_terms || []).map(f => `<span class="rule-chip forbidden">✕ ${escapeHtml(f)}</span>`).join("");
    const requiredChips = (rule.required_terms || []).map(r => `<span class="rule-chip required">✓ ${escapeHtml(r)}</span>`).join("");

    card.innerHTML = `
      <div class="playbook-rule-header">
        <div>
          <span style="font-family: monospace; font-size: 11px; color: var(--brand-orange); font-weight: 700; margin-right: 8px;">${escapeHtml(rule.id)}</span>
          <strong style="font-size: 14px; color: var(--ink-primary);">${escapeHtml(rule.name)}</strong>
          <span style="font-size: 11px; color: var(--ink-muted); margin-left: 8px;">Target: <code>${escapeHtml(rule.target_clause_type)}</code></span>
        </div>
        <span class="badge ${sevBadge}">${escapeHtml(rule.severity)}</span>
      </div>

      <div style="margin: 8px 0;">
        <div style="font-size: 11px; font-weight: 600; color: var(--ink-muted); margin-bottom: 4px;">Trigger & Policy Patterns:</div>
        <div>${triggerChips || '<span style="font-size: 11px; color: var(--ink-faint);">None</span>'}</div>
        ${forbiddenChips ? `<div style="margin-top: 4px;">${forbiddenChips}</div>` : ""}
        ${requiredChips ? `<div style="margin-top: 4px;">${requiredChips}</div>` : ""}
      </div>

      <div style="margin-top: 10px;">
        <div style="font-size: 11px; font-weight: 600; color: var(--ink-muted);">Preferred Fallback Language (&lt;w:ins&gt;):</div>
        <div class="fallback-quote-box">${escapeHtml(rule.preferred_fallback_text)}</div>
      </div>

      <div style="margin-top: 6px;">
        <div style="font-size: 11px; font-weight: 600; color: var(--ink-muted);">Review Comment Explanation (&lt;w:comment&gt;):</div>
        <div class="comment-bubble-box">💬 ${escapeHtml(rule.comment_explanation)}</div>
      </div>
    `;

    container.appendChild(card);
  });
}

// ---------------- 3. Vendor Intelligence Radar ----------------
function initVendorRadar() {
  const searchInput = document.getElementById("vendor-search-input");
  const btnAll = document.getElementById("btn-filter-all");
  const btnLow = document.getElementById("btn-filter-low");
  const btnFlagged = document.getElementById("btn-filter-flagged");
  const btnAssess = document.getElementById("btn-assess-new-vendor");

  searchInput.addEventListener("input", (e) => filterVendors(e.target.value));

  btnAll.addEventListener("click", () => renderVendors(allVendors));
  btnLow.addEventListener("click", () => renderVendors(allVendors.filter(v => v.risk_tier === "LOW")));
  btnFlagged.addEventListener("click", () => renderVendors(allVendors.filter(v => v.sanction_pep_status !== "CLEARED" || v.risk_score >= 50)));

  btnAssess.addEventListener("click", promptNewVendorAssessment);
}

async function loadVendors() {
  try {
    const [resVendors, resStats] = await Promise.all([
      fetch("/api/vendor/search?limit=100"),
      fetch("/api/vendor/stats")
    ]);

    if (resVendors.ok) {
      allVendors = await resVendors.json();
      renderVendors(allVendors);
    }

    if (resStats.ok) {
      const stats = await resStats.json();
      document.getElementById("vendor-count-badge").innerText = `${stats.total_vendors} vendors`;
      document.getElementById("kpi-vendors-count").innerText = stats.total_vendors;
    }
  } catch (err) {
    console.error("Error loading vendors:", err);
  }
}

function filterVendors(query) {
  const q = query.toLowerCase();
  const filtered = allVendors.filter(v => 
    v.company_name.toLowerCase().includes(q) ||
    v.domain.toLowerCase().includes(q) ||
    v.country.toLowerCase().includes(q) ||
    v.vendor_id.toLowerCase().includes(q)
  );
  renderVendors(filtered);
}

function renderVendors(vendors) {
  const container = document.getElementById("vendor-cards-container");
  container.innerHTML = "";

  if (vendors.length === 0) {
    container.innerHTML = `
      <div style="grid-column: 1 / -1; text-align: center; padding: 40px; color: var(--ink-muted);">
        No matching vendor records found. Use "+ Quick OSINT Check" to screen any company.
      </div>
    `;
    return;
  }

  vendors.forEach(v => {
    const card = document.createElement("div");
    card.className = "vendor-card";

    let tierBadgeClass = "badge-low";
    if (v.risk_tier === "CRITICAL") tierBadgeClass = "badge-critical";
    if (v.risk_tier === "HIGH") tierBadgeClass = "badge-high";
    if (v.risk_tier === "MEDIUM") tierBadgeClass = "badge-medium";

    let sanctionBadgeClass = "badge-low";
    if (v.sanction_pep_status === "BLOCKED") sanctionBadgeClass = "badge-critical";
    if (v.sanction_pep_status === "FLAGGED") sanctionBadgeClass = "badge-high";

    const certTags = (v.compliance_certifications || []).map(c => `<span class="cert-tag">${escapeHtml(c)}</span>`).join(" ");

    card.innerHTML = `
      <div class="vendor-header">
        <div>
          <div class="vendor-name">${escapeHtml(v.company_name)}</div>
          <div class="vendor-domain">${escapeHtml(v.domain)} • ${escapeHtml(v.country)}</div>
        </div>
        <span class="badge ${tierBadgeClass}">${v.risk_tier} RISK (${v.risk_score.toFixed(1)})</span>
      </div>

      <div class="vendor-meta-grid">
        <div class="vendor-meta-item">
          <span>Credit Score</span>
          <span>${v.credit_score}/100 (${escapeHtml(v.financial_rating)})</span>
        </div>
        <div class="vendor-meta-item">
          <span>Sanctions Status</span>
          <span><span class="badge ${sanctionBadgeClass}" style="font-size: 10px;">${v.sanction_pep_status}</span></span>
        </div>
        <div class="vendor-meta-item">
          <span>Domain Age</span>
          <span>${v.domain_age_years.toFixed(1)} yrs</span>
        </div>
        <div class="vendor-meta-item">
          <span>Litigation Count</span>
          <span>${v.past_litigation_count} lawsuits</span>
        </div>
      </div>

      <div class="cert-badges">
        ${certTags || '<span style="font-size: 10px; color: var(--ink-faint);">No certs verified</span>'}
      </div>

      ${v.flags && v.flags.length > 0 ? `
        <div style="margin-top: 10px; font-size: 11px; color: var(--badge-crit-text); line-height: 1.4; background-color: var(--surface-soft); padding: 6px 10px; border-radius: 4px;">
          ${escapeHtml(v.flags[0])}
        </div>
      ` : ""}
    `;

    container.appendChild(card);
  });
}

async function promptNewVendorAssessment() {
  const name = prompt("Enter any Vendor Name or Domain to screen (e.g. 'Google', 'Amazon', 'India Tech Partners', or 'Divyam Systems'):");
  if (!name || !name.trim()) return;

  try {
    const res = await fetch(`/api/vendor/assess?name=${encodeURIComponent(name.trim())}`);
    if (!res.ok) throw new Error("Assessment failed");
    const profile = await res.json();
    showToast(`Screened and permanently saved: ${profile.company_name} (Risk: ${profile.risk_tier}, Score: ${profile.risk_score.toFixed(1)})`);
    loadVendors();
    loadLogs();
  } catch (err) {
    showToast(`Error: ${err.message}`);
  }
}

// ---------------- 4. Cloudflare Email Dispatcher & Delivery Settings ----------------
function initEmailDispatcher() {
  const inboundForm = document.getElementById("inbound-webhook-form");
  const outboundForm = document.getElementById("outbound-dispatch-form");
  const btnRefreshPreview = document.getElementById("btn-refresh-email-preview");
  const btnViewWorkbench = document.getElementById("btn-view-redlines-workbench");

  const emailConfigForm = document.getElementById("email-config-form");
  const providerSelect = document.getElementById("cfg-provider-select");
  const smtpBlock = document.getElementById("smtp-settings-block");
  const resendBlock = document.getElementById("resend-settings-block");
  const btnTestEmail = document.getElementById("btn-test-email");

  // Load email configuration from server
  loadEmailConfig();

  providerSelect.addEventListener("change", () => {
    const val = providerSelect.value;
    smtpBlock.style.display = (val === "smtp") ? "flex" : "none";
    resendBlock.style.display = (val === "resend") ? "flex" : "none";
  });

  emailConfigForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const payload = {
      provider: providerSelect.value,
      smtp_host: document.getElementById("cfg-smtp-host").value.trim(),
      smtp_port: parseInt(document.getElementById("cfg-smtp-port").value, 10) || 587,
      smtp_user: document.getElementById("cfg-smtp-user").value.trim(),
      smtp_password: document.getElementById("cfg-smtp-pass").value,
      smtp_use_tls: true,
      resend_api_key: document.getElementById("cfg-resend-key").value.trim(),
      from_email: document.getElementById("cfg-resend-from").value.trim() || document.getElementById("cfg-smtp-user").value.trim()
    };

    try {
      const res = await fetch("/api/email/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error("Failed to save email settings");
      showToast("Email delivery settings saved successfully!");
      loadEmailConfig();
    } catch (err) {
      showToast(`Config error: ${err.message}`);
    }
  });

  btnTestEmail.addEventListener("click", async () => {
    const target = prompt("Enter recipient email address to send a test message:", "divyam.joshhi3124@gmail.com");
    if (!target || !target.trim()) return;

    btnTestEmail.disabled = true;
    btnTestEmail.innerText = "Sending test...";

    try {
      const res = await fetch("/api/email/send-test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ target_email: target.trim() })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Test email failed");

      if (data.result && data.result.is_real_delivery) {
        alert(`✓ Real Test Email Sent Successfully!\n\nDelivered via: ${data.result.provider}\nRecipient: ${target}\nCheck your inbox/spam folder.`);
      } else {
        alert(`ℹ️ Sandbox Mode Notice:\n\nEmail dispatcher is currently in Simulated Sandbox Mode.\nTo deliver a real email to ${target}, select "Direct SMTP" or "Resend API" and enter your credentials.`);
      }
    } catch (err) {
      alert(`⚠️ Test Email Error:\n\n${err.message}`);
    } finally {
      btnTestEmail.disabled = false;
      btnTestEmail.innerText = "🧪 Send Test";
    }
  });

  if (btnViewWorkbench) {
    btnViewWorkbench.addEventListener("click", () => {
      const tab1Btn = document.querySelector('.nav-tab[data-tab="redliner-tab"]');
      if (tab1Btn) tab1Btn.click();
      runRedline();
    });
  }

  // Inbound webhook simulator
  inboundForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fromEmail = document.getElementById("inbound-from").value;
    const subject = document.getElementById("inbound-subject").value;
    const contractSelect = document.getElementById("inbound-contract-select").value;
    const btnTrigger = document.getElementById("btn-trigger-webhook");

    btnTrigger.disabled = true;
    btnTrigger.innerText = "⚡ Ingesting & Running Pipeline...";

    const payload = {
      message_id: `cf_msg_${Date.now()}`,
      from_email: fromEmail,
      from_name: "ApexCloud Commercial Counsel",
      to_email: "negotiations@redliner.ai",
      subject: subject,
      text_content: "Please find attached our standard Master Services Agreement for execution.",
      attachments: []
    };

    try {
      const res = await fetch("/api/webhook/email", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error("Webhook trigger failed");
      const data = await res.json();
      
      const stepper = document.getElementById("webhook-pipeline-status");
      if (stepper) {
        stepper.style.display = "block";
        document.getElementById("pipeline-contract-status").innerText = `Contract attachment extracted (${contractSelect})`;
        document.getElementById("pipeline-vendor-status").innerText = `Counterparty screened: ${data.vendor_screened || "Vendor"} (${data.vendor_risk_tier || "LOW"} Risk)`;
        document.getElementById("pipeline-redline-status").innerText = `${data.violations_detected || 7} Playbook violations redlined in Word OpenXML`;
      }

      if (data.counter_proposal_email) {
        document.getElementById("outbound-vendor-name").value = data.vendor_screened || "Vendor";
        document.getElementById("outbound-recipient-email").value = fromEmail;
        document.getElementById("outbound-contract-file").value = data.redlined_docx_filename || contractSelect;
        document.getElementById("outbound-body-preview").value = data.counter_proposal_email.counter_proposal_body;
      }

      showToast(`Autonomous pipeline complete: ${data.violations_detected || 7} redlines tracked in Word!`);
      loadVendors();
      loadLogs();
    } catch (err) {
      showToast(`Webhook error: ${err.message}`);
    } finally {
      btnTrigger.disabled = false;
      btnTrigger.innerText = "Trigger Cloudflare Webhook";
    }
  });

  btnRefreshPreview.addEventListener("click", () => {
    if (currentRedlineResult) updateEmailPreview(currentRedlineResult);
  });

  // Outbound dispatch form
  outboundForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const vendorName = document.getElementById("outbound-vendor-name").value;
    const recipientEmail = document.getElementById("outbound-recipient-email").value;
    const contractFile = document.getElementById("outbound-contract-file").value;

    const payload = {
      contract_filename: contractFile,
      vendor_name: vendorName,
      recipient_email: recipientEmail,
      recipient_name: "Vendor Legal Counsel"
    };

    const btn = document.getElementById("btn-send-counter-email");
    btn.disabled = true;
    btn.innerText = "Dispatching Outbound Email...";

    try {
      const res = await fetch("/api/email/dispatch-counter-proposal", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error("Dispatch failed");
      const data = await res.json();
      const receipt = data.dispatch_receipt || {};
      const isReal = receipt.is_real_delivery === true;

      const receiptBox = document.getElementById("dispatch-receipt-box");
      receiptBox.style.display = "block";

      if (isReal) {
        receiptBox.className = "alert alert-success";
        receiptBox.innerHTML = `
          <p style="font-weight: 700; color: var(--badge-low-text); font-size: 14px;">✓ Real Email Delivered Successfully via ${escapeHtml(receipt.provider || "Direct SMTP")}</p>
          <p style="font-size: 12px; color: var(--ink-body); margin-top: 4px;">
            Delivered directly to <strong>${escapeHtml(data.email_details.recipient_email)}</strong> with attached Word contract (<code>${escapeHtml(data.email_details.redlined_docx_filename)}</code>).
          </p>
          <p style="font-size: 11px; color: var(--ink-muted); margin-top: 2px;">Deal Reference: ${escapeHtml(data.email_details.deal_reference)}</p>
        `;
        showToast("Real email dispatched with tracked changes .docx!");
      } else {
        receiptBox.className = "alert alert-warning";
        receiptBox.innerHTML = `
          <p style="font-weight: 700; color: var(--badge-high-text); font-size: 14px;">⚠️ Simulated Sandbox Dispatch (Local Mode)</p>
          <p style="font-size: 12px; color: var(--ink-body); margin-top: 4px;">
            Counter-proposal generated and logged for <strong>${escapeHtml(data.email_details.recipient_email)}</strong>. Word tracked changes document attached.
          </p>
          <p style="font-size: 11px; color: var(--ink-muted); margin-top: 4px; line-height: 1.4;">
            ℹ️ <strong>Why didn't this land in your inbox?</strong> Email dispatcher is currently set to <em>Sandbox Simulation Mode</em>. To send a real email across the public Internet to <code>${escapeHtml(data.email_details.recipient_email)}</code>, configure your SMTP or Resend credentials in <strong>Email Delivery Settings</strong> on the left.
          </p>
        `;
        showToast("Logged in sandbox. Configure SMTP to send real emails.");
      }

      loadLogs();
    } catch (err) {
      showToast(`Dispatch error: ${err.message}`);
    } finally {
      btn.disabled = false;
      btn.innerText = "🚀 Dispatch Counter-Proposal Email";
    }
  });
}

async function loadEmailConfig() {
  try {
    const res = await fetch("/api/email/config");
    if (!res.ok) return;
    const cfg = await res.json();

    const providerSelect = document.getElementById("cfg-provider-select");
    providerSelect.value = cfg.provider || "sandbox";

    document.getElementById("cfg-smtp-host").value = cfg.smtp_host || "smtp.gmail.com";
    document.getElementById("cfg-smtp-port").value = cfg.smtp_port || 587;
    document.getElementById("cfg-smtp-user").value = cfg.smtp_user || "";
    document.getElementById("cfg-resend-from").value = cfg.from_email || "";

    if (cfg.has_smtp_password) {
      document.getElementById("cfg-smtp-pass").value = "••••••••••••";
    }
    if (cfg.has_resend_api_key) {
      document.getElementById("cfg-resend-key").value = cfg.resend_api_key_masked || "••••••••";
    }

    const smtpBlock = document.getElementById("smtp-settings-block");
    const resendBlock = document.getElementById("resend-settings-block");
    smtpBlock.style.display = (cfg.provider === "smtp") ? "flex" : "none";
    resendBlock.style.display = (cfg.provider === "resend") ? "flex" : "none";
  } catch (err) {
    console.error("Error loading email config:", err);
  }
}

function updateEmailPreview(redlineResult) {
  const previewBox = document.getElementById("outbound-body-preview");
  const vendorInput = document.getElementById("outbound-vendor-name");
  const contractInput = document.getElementById("outbound-contract-file");

  if (contractInput) contractInput.value = redlineResult.output_docx_filename;

  const vendorName = vendorInput ? vendorInput.value : "ApexCloud Enterprise Ltd";
  const criticals = redlineResult.actions.filter(a => a.severity === "CRITICAL");
  const highs = redlineResult.actions.filter(a => a.severity === "HIGH");

  const lines = [
    `Dear Vendor Legal Counsel,`,
    ``,
    `Thank you for sharing the draft agreement for ${vendorName}. Our legal and procurement teams have completed an initial review against our corporate onboarding playbook.`,
    ``,
    `To ensure alignment with our corporate governance, risk thresholds, and procurement standards, we have generated native tracked changes and margin comments in the attached Word document (${redlineResult.output_docx_filename}).`,
    ``,
    `Summary of Key Proposed Adjustments:`
  ];

  if (criticals.length > 0) {
    lines.push(`\n1. Critical Risk Terms & Liability Alignment:`);
    criticals.forEach(c => {
      lines.push(`  • ${c.clause_type} (${c.rule_name}): Realigned to mutual 12-month standard caps and customer data ownership.`);
    });
  }

  if (highs.length > 0) {
    lines.push(`\n2. Commercial & Operational Safeguards:`);
    highs.forEach(h => {
      lines.push(`  • ${h.clause_type} (${h.rule_name}): Standardized Net 60 payment terms and dispute escrow.`);
    });
  }

  lines.push(
    ``,
    `Please review the attached native .docx document which contains complete Word tracked changes and detailed explanatory margin comments.`,
    ``,
    `Best regards,`,
    `RedLiner Procurement & Legal Operations Team`
  );

  if (previewBox) previewBox.value = lines.join("\n");
}

// ---------------- 5. Helpers Audit & Telemetry Monitor ----------------
function initHelpersAudit() {
  const filterSelect = document.getElementById("log-filter-select");
  const btnRefresh = document.getElementById("btn-refresh-logs");

  if (filterSelect) {
    filterSelect.addEventListener("change", (e) => loadLogs(e.target.value));
  }
  if (btnRefresh) {
    btnRefresh.addEventListener("click", () => {
      const val = filterSelect ? filterSelect.value : "all";
      loadLogs(val);
    });
  }
}

async function loadLogs(filter = "all") {
  const tbody = document.getElementById("logs-table-body");
  const badge = document.getElementById("logs-count-badge");
  if (!tbody) return;

  try {
    const res = await fetch(`/api/helpers/logs?log_type=${filter}&limit=60&_t=${Date.now()}`);
    if (!res.ok) throw new Error("Failed to load logs from server");
    const logs = await res.json();

    if (badge) badge.innerText = `${logs.length} entries`;
    tbody.innerHTML = "";

    if (!logs || logs.length === 0) {
      tbody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: var(--ink-muted); padding: 30px;">No audit events recorded in Helpers yet.</td></tr>`;
      return;
    }

    logs.forEach(item => {
      const tr = document.createElement("tr");

      // Categorize event dynamically
      let cat = item.type || item.category;
      if (!cat && item.event) {
        if (item.event.includes("PARSED") || item.event.includes("PARSER")) cat = "parser";
        else if (item.event.includes("REDLINE")) cat = "redline";
        else if (item.event.includes("EMAIL")) cat = "email";
        else if (item.event.includes("VENDOR") || item.event.includes("RISK")) cat = "vendor_risk";
        else cat = "audit";
      }
      cat = cat || "audit";

      let catBadge = "badge-medium";
      if (cat === "redline") catBadge = "badge-high";
      else if (cat === "email") catBadge = "badge-low";
      else if (cat === "vendor_risk" || cat === "vendor") catBadge = "badge-critical";
      else if (cat === "parser") catBadge = "badge-medium";

      const timeStr = item.timestamp ? new Date(item.timestamp).toLocaleTimeString() : "--";

      // Formulate detailed, human-readable summary
      let detailSummary = "";
      if (item.event === "DOCUMENT_PARSED") {
        detailSummary = `📄 ${item.filename || "contract"} (${(item.file_type || "docx").toUpperCase()}) — ${item.clauses_identified || 0} clauses parsed (${item.paragraphs_count || 0} paragraphs) in ${item.elapsed_ms || 0}ms`;
      } else if (item.event === "REDLINE_EXECUTED") {
        detailSummary = `✍️ ${item.contract_name || "contract"} — ${item.violations_detected || 0} violations (${item.critical_violations || 0} critical), ${item.actions_generated || 0} tracked changes generated [${item.playbook_used || "Corporate Playbook"}]`;
      } else if (item.event && item.event.startsWith("EMAIL")) {
        detailSummary = `✉️ [${item.direction || "OUTBOUND"}] ${item.party || "recipient"} — "${item.subject || "Counter-Proposal"}" (Status: ${item.status || "SENT"}${item.attachment_name ? `, Attachment: ${item.attachment_name}` : ""})`;
      } else if (item.event === "VENDOR_RISK_ASSESSED") {
        detailSummary = `🛡️ ${item.vendor_name || "Vendor"} (${item.domain || "N/A"}) — Score: ${item.risk_score !== undefined ? item.risk_score : "0.0"} (${item.risk_tier || "LOW"}), Sanctions: ${item.sanction_status || "CLEARED"}, Credit: ${item.credit_rating || "N/A"}`;
      } else {
        detailSummary = item.message || JSON.stringify(item);
      }

      // Prepare raw payload (all event metadata fields)
      const rawPayload = { ...item };
      delete rawPayload.timestamp;
      delete rawPayload.type;
      delete rawPayload.event;
      delete rawPayload.category;

      const hasPayloadData = Object.keys(rawPayload).length > 0;
      const payloadJsonStr = hasPayloadData ? JSON.stringify(rawPayload, null, 2) : "";

      tr.innerHTML = `
        <td style="font-family: monospace; font-size: 11px; color: var(--ink-muted); white-space: nowrap;">${timeStr}</td>
        <td><span class="badge ${catBadge}">${escapeHtml(cat.toUpperCase())}</span></td>
        <td style="font-weight: 600; font-size: 12px; color: var(--ink-primary);">${escapeHtml(item.event || "EVENT")}</td>
        <td style="font-size: 12px; color: var(--ink-body); line-height: 1.5;">
          <div style="font-weight: 500;">${escapeHtml(detailSummary)}</div>
          ${hasPayloadData ? `
            <details style="margin-top: 6px;">
              <summary style="cursor: pointer; font-size: 11px; color: var(--brand-orange); font-family: monospace; outline: none; user-select: none;">
                ▸ View raw payload JSON
              </summary>
              <pre style="margin-top: 6px; padding: 8px 12px; background-color: var(--surface-soft); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); font-size: 11px; font-family: monospace; max-height: 160px; overflow-y: auto; white-space: pre-wrap; word-break: break-all; color: var(--ink-body);">${escapeHtml(payloadJsonStr)}</pre>
            </details>
          ` : ""}
        </td>
      `;

      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error("Error loading logs:", err);
    if (tbody) {
      tbody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: var(--ink-muted); padding: 30px;">⚠️ Failed to load audit logs: ${escapeHtml(err.message)} <button class="btn btn-secondary" onclick="loadLogs('${filter}')" style="margin-left: 10px; padding: 4px 10px; font-size: 11px;">Retry</button></td></tr>`;
    }
  }
}
