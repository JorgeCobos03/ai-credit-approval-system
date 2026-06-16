const currency = new Intl.NumberFormat("es-MX", {
  style: "currency",
  currency: "MXN",
  maximumFractionDigits: 0,
});

const state = {
  applications: [],
  metrics: null,
};

const $ = (selector) => document.querySelector(selector);

function text(value, fallback = "--") {
  return value === null || value === undefined || value === "" ? fallback : value;
}

function statusClass(status) {
  const normalized = String(status || "PENDING").toLowerCase();
  if (normalized.includes("approved")) return "approved";
  if (normalized.includes("rejected")) return "rejected";
  return "pending";
}

function formatPercent(value) {
  return `${Number(value || 0).toFixed(0)}%`;
}

function setBar(selector, count, max) {
  const width = max ? Math.max(6, (count / max) * 100) : 0;
  $(selector).style.width = `${width}%`;
}

function setSegment(selector, count, total) {
  const width = total ? (count / total) * 100 : 0;
  $(selector).style.width = `${width}%`;
}

function renderRiskDots(riskIndex) {
  const dots = 20;
  const activeDots = Math.round((riskIndex / 100) * dots);
  const tone = riskIndex >= 70 ? "danger" : riskIndex >= 40 ? "warn" : "";

  $("#riskDots").innerHTML = Array.from({ length: dots }, (_, index) => {
    const active = index < activeDots ? `active ${tone}`.trim() : "";
    return `<i class="${active}"></i>`;
  }).join("");

  $("#riskCaption").textContent = riskIndex >= 70
    ? "Riesgo alto"
    : riskIndex >= 40
      ? "Riesgo medio"
      : "Riesgo controlado";
}

function reasonSummary(rawReason) {
  const raw = rawReason || "";
  const lower = raw.toLowerCase();
  const codes = [];
  const reasons = [];
  let headline = "Sin datos suficientes para explicar la decision.";

  if (!raw) {
    return {
      headline: "Aun no hay un motivo clave.",
      detail: "Cuando exista una solicitud evaluada, aqui se mostrara la razon principal en lenguaje claro.",
      codes: "CODIGO: SIN_DATOS",
    };
  }

  if (lower.includes("application approved")) {
    headline = "Solicitud aceptada.";
    reasons.push("La solicitud cumple las reglas principales de evaluacion.");
    codes.push("DECISION_APPROVED");
  }

  if (lower.includes("application rejected")) {
    headline = "Solicitud rechazada.";
    codes.push("DECISION_REJECTED");
  }

  if (lower.includes("score below minimum")) {
    headline = "Solicitud rechazada por score crediticio bajo.";
    reasons.push("El score obtenido no alcanza el minimo requerido de 500 puntos.");
    codes.push("SCORE_BELOW_MINIMUM");
  }

  if (lower.includes("monthly income below minimum")) {
    headline = "Solicitud rechazada por ingreso mensual insuficiente.";
    reasons.push("El ingreso mensual reportado esta por debajo del minimo requerido de 10000.");
    codes.push("INCOME_BELOW_MINIMUM");
  }

  if (lower.includes("bank seniority below")) {
    headline = "Solicitud rechazada por poca antiguedad bancaria.";
    reasons.push("La antiguedad bancaria es menor a los 12 meses requeridos.");
    codes.push("BANK_SENIORITY_BELOW_MINIMUM");
  }

  if (lower.includes("blacklisted")) {
    headline = "Solicitud rechazada por lista negra.";
    reasons.push("La persona solicitante aparece marcada como restringida.");
    codes.push("APPLICANT_BLACKLISTED");
  }

  if (lower.includes("document name does not match")) {
    headline = "Solicitud rechazada por diferencia en el documento.";
    reasons.push("El nombre detectado en el documento no coincide con la solicitud.");
    codes.push("DOCUMENT_NAME_MISMATCH");
  }

  if (lower.includes("address does not match")) {
    headline = "Solicitud rechazada por diferencia de direccion.";
    reasons.push("La direccion del documento no coincide de forma suficiente con la solicitud.");
    codes.push("DOCUMENT_ADDRESS_MISMATCH");
  }

  if (lower.includes("document expired")) {
    headline = "Solicitud rechazada por documento vencido.";
    reasons.push("La vigencia detectada en el documento ya expiro.");
    codes.push("DOCUMENT_EXPIRED");
  }

  if (lower.includes("all business rules satisfied")) {
    reasons.push("Score, ingreso, antiguedad bancaria y validaciones principales cumplen los criterios.");
    codes.push("RULES_OK");
  }

  const uniqueReasons = [...new Set(reasons)];
  const uniqueCodes = [...new Set(codes)];

  return {
    headline,
    detail: uniqueReasons.length
      ? `Razones: ${uniqueReasons.join(" ")}`
      : "Razones: revisar el detalle tecnico de la evaluacion.",
    codes: `Codigos: ${uniqueCodes.length ? uniqueCodes.join(", ") : "MOTIVO_NO_CLASIFICADO"}`,
  };
}

function renderMetrics() {
  const metrics = state.metrics || {};
  const apps = state.applications || [];
  const total = metrics.total_applications ?? apps.length;
  const approved = apps.filter((app) => app.status === "APPROVED").length;
  const rejected = apps.filter((app) => app.status === "REJECTED").length;
  const pending = apps.filter((app) => (app.document_verified || "PENDING") === "PENDING").length;
  const max = Math.max(approved, rejected, pending, 1);
  const approval = metrics.approved_percentage ?? (total ? (approved / total) * 100 : 0);
  const rejection = metrics.rejected_percentage ?? (total ? (rejected / total) * 100 : 0);
  const riskIndex = Math.round(rejection * 0.7 + (pending / Math.max(apps.length, 1)) * 30);

  $("#approvalValue").textContent = formatPercent(approval);
  $(".approval-ring").style.setProperty("--value", Number(approval || 0));
  $("#approvedValue").textContent = formatPercent(approval);
  $("#rejectedValue").textContent = formatPercent(rejection);
  $("#todayValue").textContent = metrics.total_applications_today ?? 0;
  $("#totalApplications").textContent = total;
  $("#riskIndex").textContent = `${riskIndex}/100`;
  const topReason = reasonSummary(metrics.top_rejection_reason);
  $("#topReason").textContent = topReason.headline;
  $("#topReasonDetail").textContent = topReason.detail;
  $("#topReasonCodes").textContent = topReason.codes;
  $("#topReason").title = metrics.top_rejection_reason || "Sin datos";

  $("#approvedCount").textContent = approved;
  $("#rejectedCount").textContent = rejected;
  $("#pendingCount").textContent = pending;
  setBar("#approvedBar", approved, max);
  setBar("#rejectedBar", rejected, max);
  setBar("#pendingBar", pending, max);
  setSegment("#totalApprovedSegment", approved, total);
  setSegment("#totalRejectedSegment", rejected, total);
  setSegment("#totalPendingSegment", pending, total);
  renderRiskDots(riskIndex);
}

function renderTable() {
  const rows = state.applications.map((app) => {
    const badgeClass = statusClass(app.status);
    const reason = app.rejection_reason || "Validaciones completas";
    return `
      <tr>
        <td><strong>${app.name}</strong><br><span class="muted">${app.address || "Sin direccion"}</span></td>
        <td><span class="badge ${badgeClass}">${app.status || "PENDING"}</span></td>
        <td>${app.score ?? "--"}</td>
        <td>${currency.format(app.monthly_income || 0)}</td>
        <td>${app.risk_flag || "LOW"}</td>
        <td class="muted">${reason}</td>
      </tr>
    `;
  });

  $("#applicationsTable").innerHTML = rows.join("") || `
    <tr>
      <td colspan="6" class="muted">No hay solicitudes registradas.</td>
    </tr>
  `;
}

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(`HTTP ${response.status}`);
    error.payload = payload;
    throw error;
  }
  return payload;
}

async function loadDashboard() {
  $("#lastUpdate").textContent = "Actualizando";
  const [metrics, applications, score] = await Promise.all([
    fetchJson("/dashboard/metrics"),
    fetchJson("/applications/"),
    fetchJson("/scorecredito"),
  ]);

  state.metrics = metrics;
  state.applications = applications;
  $("#systemScore").textContent = score.score;
  renderMetrics();
  renderTable();
  $("#lastUpdate").textContent = new Date().toLocaleTimeString("es-MX", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formPayload(form) {
  const data = new FormData(form);
  return {
    name: data.get("name"),
    rfc: data.get("rfc"),
    curp: data.get("curp"),
    gender: data.get("gender"),
    monthly_income: Number(data.get("monthly_income")),
    bank_seniority_months: Number(data.get("bank_seniority_months")),
    is_blacklisted: data.get("is_blacklisted") === "on",
    address: data.get("address") || null,
  };
}

$("#refreshBtn").addEventListener("click", () => {
  loadDashboard().catch(showError);
});

$("#applicationForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  $("#formStatus").textContent = "Procesando";

  try {
    await fetchJson("/applications/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(formPayload(form)),
    });
    $("#formStatus").textContent = "Creada";
    form.reset();
    await loadDashboard();
  } catch (error) {
    showError(error);
  }
});

document.querySelector("#documentForm input[type='file']").addEventListener("change", (event) => {
  const file = event.currentTarget.files[0];
  $("#fileName").textContent = file ? file.name : "Seleccionar PDF";
});

$("#documentForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const data = new FormData(form);

  for (const [key, value] of [...data.entries()]) {
    if (value === "" || value === null) {
      data.delete(key);
    }
  }

  $("#documentStatus").textContent = "Procesando";

  try {
    const result = await fetchJson("/applications/from-document", {
      method: "POST",
      body: data,
    });

    renderDocumentResult(result);
    $("#documentStatus").textContent = "Evaluada";
    form.reset();
    $("#fileName").textContent = "Seleccionar PDF";
    await loadDashboard();
  } catch (error) {
    renderDocumentError(error);
  }
});

function renderDocumentResult(result) {
  const app = result.application || {};
  const extracted = result.extracted_data || {};
  const decision = $("#documentDecision");
  const badgeClass = statusClass(app.status);

  decision.className = badgeClass;
  decision.textContent = text(app.status, "PENDING");
  $("#documentScore").textContent = `Score ${text(app.score)}`;
  $("#extractedName").textContent = text(extracted.name || app.name);
  $("#extractedAddress").textContent = text(extracted.address || app.address);
  $("#documentVerified").textContent = text(result.document_verified);
  $("#documentRisk").textContent = text(result.risk_flag);
  $("#documentExplanation").textContent = text(result.decision_explanation, "Sin evaluacion reciente.");
}

function renderDocumentError(error) {
  const detail = error.payload?.detail;
  const extracted = detail?.extracted_data || {};
  const missing = detail?.missing_fields || [];

  $("#documentStatus").textContent = "Incompleto";
  $("#extractedName").textContent = text(extracted.name);
  $("#extractedAddress").textContent = text(extracted.address);
  $("#documentVerified").textContent = "--";
  $("#documentRisk").textContent = "--";
  $("#documentDecision").className = "rejected";
  $("#documentDecision").textContent = "PENDING";
  $("#documentScore").textContent = "Score --";
  $("#documentExplanation").textContent = missing.length
    ? `Faltan datos para evaluar: ${missing.join(", ")}.`
    : "No se pudo procesar el documento.";
}

function showError(error) {
  console.error(error);
  $("#formStatus").textContent = "Error";
  $("#lastUpdate").textContent = "Sin conexion";
}

loadDashboard().catch(showError);
