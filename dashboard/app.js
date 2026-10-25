// RedLiner Frontend Controller — Zapier UI/UX White Theme

let currentParsedDoc = null;
let currentRedlineResult = null;
let currentFilename = "vendor_saas_agreement.docx";

document.addEventListener("DOMContentLoaded", () => {
  initTabs();
  initParserAndRedliner();
  initVendorRadar();
  initEmailDispatcher();
  initHelpersAudit();

  // Load standard sample by default on boot
  loadSampleContract("vendor_saas_agreement.docx");
  loadVendors();
  loadLogs();
});

// Toast notification helper
function showToast(message, duration = 3500) {
  const container = document.getElementById("toast-container");
  const toast = document.createElement("div");
  toast.className = "toast";
  toast.innerText = message;
  container.appendChild(toast);
  setTimeout(() => {
    toast.remove();
  }, duration);
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
    <p><strong>File:</strong> ${parsedDoc.filename}</p>
    <p><strong>Format:</strong> ${parsedDoc.file_type.toUpperCase()}</p>
    <p><strong>Paragraphs:</strong> ${parsedDoc.total_paragraphs}</p>
    <p><strong>Clauses Detected:</strong> ${parsedDoc.clauses.length}</p>
  `;

  chipsContainer.innerHTML = "";
  for (const [cType, count] of Object.entries(parsedDoc.clause_distribution)) {
    const chip = document.createElement("span");
    chip.className = "clause-chip";
    chip.innerHTML = `<span>${cType}</span><strong>${count}</strong>`;
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
    currentRedlineResult = result;
    renderRedlineResult(result);
    showToast(`Redline complete: ${result.violations_detected} guardrail violations detected!`);
    loadLogs();
  } catch (err) {
    showToast(`Redline error: ${err.message}`);
  } finally {
    btn.disabled = false;
    btn.innerText = "⚡ Run Legal Playbook Redline";
  }
}

function renderRedlineResult(result) {
  const container = document.getElementById("diff-cards-container");
  const summaryBanner = document.getElementById("redline-summary-banner");
  const actionButtons = document.getElementById("redline-action-buttons");
  const downloadBtn = document.getElementById("download-docx-btn");
  const violationsBadge = document.getElementById("violations-count-badge");

  violationsBadge.innerText = `${result.violations_detected} edits`;

  // Summary Banner
  summaryBanner.style.display = "block";
  document.getElementById("summary-banner-title").innerText = `${result.violations_detected} Playbook Violations Tracked in Word OpenXML`;
  document.getElementById("summary-banner-desc").innerText = result.summary;

  const bannerBadges = document.getElementById("summary-banner-badges");
  bannerBadges.innerHTML = `
    <span class="badge badge-critical">${result.critical_count} Critical</span>
    <span class="badge badge-high">${result.violations_detected - result.critical_count} High/Med</span>
  `;

  // Download button
  actionButtons.style.display = "flex";
  downloadBtn.href = `/api/redliner/download/${result.output_docx_filename}`;
  downloadBtn.setAttribute("download", result.output_docx_filename);

  // Render diff cards
  container.innerHTML = "";
  result.actions.forEach(act => {
    const card = document.createElement("div");
    card.className = "diff-card";

    let badgeClass = "badge-medium";
    if (act.severity === "CRITICAL") badgeClass = "badge-critical";
    if (act.severity === "HIGH") badgeClass = "badge-high";

    card.innerHTML = `
      <div class="diff-card-header">
        <div class="diff-clause-title">${act.clause_type}: ${act.rule_name}</div>
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
          ${escapeHtml(act.comment).replace(/\\n/g, "<br>")}
        </div>
      </div>
    `;

    container.appendChild(card);
  });

  // Also update email tab preview defaults
  updateEmailPreview(result);
}

function escapeHtml(text) {
  if (!text) return "";
  const div = document.createElement("div");
  div.innerText = text;
  return div.innerHTML;
}

// ---------------- 2. Vendor Intelligence Radar ----------------
let allVendors = [];

function initVendorRadar() {
  const searchInput = document.getElementById("vendor-search-input");
  const btnAll = document.getElementById("btn-filter-all");
  const btnLow = document.getElementById("btn-filter-low");
  const btnFlagged = document.getElementById("btn-filter-flagged");
  const btnAssess = document.getElementById("btn-assess-new-vendor");

  searchInput.addEventListener("input", (e) => {
    filterVendors(e.target.value);
  });

  btnAll.addEventListener("click", () => renderVendors(allVendors));
  btnLow.addEventListener("click", () => {
    renderVendors(allVendors.filter(v => v.risk_tier === "LOW"));
  });
  btnFlagged.addEventListener("click", () => {
    renderVendors(allVendors.filter(v => v.sanction_pep_status !== "CLEARED" || v.risk_score >= 50));
  });

  btnAssess.addEventListener("click", promptNewVendorAssessment);
}

async function loadVendors() {
  try {
    const res = await fetch("/api/vendor/search?limit=60");
    if (!res.ok) throw new Error("Failed to load vendors");
    allVendors = await res.json();
    renderVendors(allVendors);
    document.getElementById("vendor-count-badge").innerText = `${allVendors.length} vendors`;
    document.getElementById("kpi-vendors-count").innerText = allVendors.length;
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
        No matching vendor records found.
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

    const certTags = v.compliance_certifications.map(c => `<span class="cert-tag">${c}</span>`).join(" ");

    card.innerHTML = `
      <div class="vendor-header">
        <div>
          <div class="vendor-name">${escapeHtml(v.company_name)}</div>
          <div class="vendor-domain">${escapeHtml(v.domain)} • ${escapeHtml(v.country)}</div>
        </div>
        <span class="badge ${tierBadgeClass}">${v.risk_tier} RISK (${v.risk_score})</span>
      </div>

      <div class="vendor-meta-grid">
        <div class="vendor-meta-item">
          <span>Credit Score</span>
          <span>${v.credit_score}/100 (${v.financial_rating})</span>
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
  const name = prompt("Enter Vendor Name or Domain to screen (e.g., 'CloudScale Systems' or 'cloudscale.io'):");
  if (!name || !name.trim()) return;

  try {
    const res = await fetch(`/api/vendor/assess?name=${encodeURIComponent(name.trim())}`);
    if (!res.ok) throw new Error("Assessment failed");
    const profile = await res.json();
    showToast(`Screened ${profile.company_name}: Risk Tier = ${profile.risk_tier} (${profile.risk_score})`);
    loadVendors();
    loadLogs();
  } catch (err) {
    showToast(`Error: ${err.message}`);
  }
}

// ---------------- 3. Cloudflare Email Dispatcher ----------------
function initEmailDispatcher() {
  const inboundForm = document.getElementById("inbound-webhook-form");
  const outboundForm = document.getElementById("outbound-dispatch-form");
  const btnRefreshPreview = document.getElementById("btn-refresh-email-preview");
  const btnViewWorkbench = document.getElementById("btn-view-redlines-workbench");

  if (btnViewWorkbench) {
    btnViewWorkbench.addEventListener("click", () => {
      // Switch to Tab 1
      const tab1Btn = document.querySelector('.nav-tab[data-tab="redliner-tab"]');
      if (tab1Btn) tab1Btn.click();
      runRedline();
    });
  }

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
      
      // Update Pipeline Stepper UI
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
    btn.innerText = "Dispatching via Cloudflare...";

    try {
      const res = await fetch("/api/email/dispatch-counter-proposal", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error("Dispatch failed");
      const data = await res.json();

      document.getElementById("dispatch-receipt-box").style.display = "block";
      document.getElementById("receipt-details").innerText = 
        `Delivered to ${data.email_details.recipient_email} with native tracked changes attachment (${data.email_details.redlined_docx_filename}). Deal Reference: ${data.email_details.deal_reference}`;

      showToast("Counter-proposal email dispatched with tracked changes .docx!");
      loadLogs();
    } catch (err) {
      showToast(`Dispatch error: ${err.message}`);
    } finally {
      btn.disabled = false;
      btn.innerText = "🚀 Dispatch Counter-Proposal Email";
    }
  });
}

function updateEmailPreview(redlineResult) {
  const previewBox = document.getElementById("outbound-body-preview");
  const vendorInput = document.getElementById("outbound-vendor-name");
  const contractInput = document.getElementById("outbound-contract-file");

  contractInput.value = redlineResult.output_docx_filename;

  const vendorName = vendorInput.value || "Vendor";
  const lines = [
    `Dear Vendor Legal Counsel,`,
    ``,
    `Thank you for sharing the draft agreement for ${vendorName}. Our enterprise legal and procurement teams have completed an initial review against our standard corporate onboarding playbook.`,
    ``,
    `To ensure alignment with our corporate governance, risk thresholds, and procurement standards, we have generated native tracked changes and margin comments in the attached Word document (${redlineResult.output_docx_filename}).`,
    ``,
    `Summary of Key Proposed Adjustments:`,
    `- Liability Cap: Realigned to mutual 12-month trailing fees standard cap.`,
    `- Payment Terms: Standardized to Net 60 days.`,
    `- Deliverables Ownership: Customer retains full rights in custom deliverables and data.`,
    `- Governing Law: Standardized under Delaware law with neutral AAA arbitration.`,
    ``,
    `Please review the attached native .docx document which contains complete Word tracked changes and explanatory margin comments.`,
    ``,
    `Best regards,`,
    `RedLiner Procurement & Legal Operations Team`
  ];

  previewBox.value = lines.join("\n");
}

// ---------------- 4. Helpers Audit & Telemetry ----------------
function initHelpersAudit() {
  const filterSelect = document.getElementById("log-filter-select");
  const btnRefresh = document.getElementById("btn-refresh-logs");

  filterSelect.addEventListener("change", (e) => {
    loadLogs(e.target.value);
  });

  btnRefresh.addEventListener("click", () => {
    loadLogs(filterSelect.value);
  });
}

async function loadLogs(logType = "all") {
  const tbody = document.getElementById("logs-table-body");
  try {
    const res = await fetch(`/api/helpers/logs?log_type=${logType}&limit=40`);
    if (!res.ok) throw new Error("Failed to load logs");
    const logs = await res.json();

    document.getElementById("logs-count-badge").innerText = `${logs.length} events`;

    if (logs.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="4" style="text-align: center; color: var(--ink-muted); padding: 30px;">
            No logs recorded in Helpers yet.
          </td>
        </tr>
      `;
      return;
    }

    tbody.innerHTML = "";
    logs.forEach(log => {
      const tr = document.createElement("tr");

      let categoryBadgeClass = "badge-medium";
      if (log.type === "redline") categoryBadgeClass = "badge-high";
      if (log.type === "vendor_risk") categoryBadgeClass = "badge-critical";
      if (log.type === "email") categoryBadgeClass = "badge-low";

      const timeFormatted = log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : "--";

      let detailSummary = "";
      if (log.event === "DOCUMENT_PARSED") {
        detailSummary = `Parsed ${log.paragraphs_count} paragraphs, ${log.clauses_identified} clauses from ${log.filename} (${log.elapsed_ms}ms)`;
      } else if (log.event === "REDLINE_EXECUTED") {
        detailSummary = `Applied ${log.actions_generated} redlines (${log.critical_violations} critical) to ${log.contract_name}`;
      } else if (log.event && log.event.startsWith("EMAIL")) {
        detailSummary = `${log.direction}: ${log.subject} (Party: ${log.party})`;
      } else if (log.event === "VENDOR_RISK_ASSESSED") {
        detailSummary = `${log.vendor_name} — Score: ${log.risk_score} (${log.risk_tier}), Sanctions: ${log.sanction_status}`;
      } else {
        detailSummary = JSON.stringify(log);
      }

      tr.innerHTML = `
        <td style="font-family: monospace; font-size: 11px; color: var(--ink-faint);">${timeFormatted}</td>
        <td><span class="badge ${categoryBadgeClass}">${log.type || "SYSTEM"}</span></td>
        <td style="font-weight: 600; color: var(--ink-primary); font-size: 12px;">${log.event || "LOG"}</td>
        <td style="font-size: 12px; color: var(--ink-body);">${escapeHtml(detailSummary)}</td>
      `;

      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error("Error loading logs:", err);
  }
}
