"use strict";
const $ = (s) => document.querySelector(s);
const money = (n) =>
  new Intl.NumberFormat("es-MX", {
    style: "currency",
    currency: "MXN",
    maximumFractionDigits: 0,
  }).format(n || 0);
const labels = {
  REVIEW: "Por revisar",
  PENDING: "Pendiente",
  APPROVED: "Aprobada",
  REJECTED: "Rechazada",
  MATCHED: "Coincidencia detectada",
  LOW: "Bajo",
  MEDIUM: "Medio",
  HIGH: "Alto",
};
const icons = {
  grid: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
  folder:
    '<path d="M3 7V5a2 2 0 0 1 2-2h5l2 3h7a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z"/><path d="M3 9h18"/>',
  sliders:
    '<path d="M5 3v5m0 4v9M12 3v10m0 4v4M19 3v2m0 4v12M2 8h6M9 17h6M16 5h6"/>',
  book: '<path d="M12 5c-4-3-8-2-9-1v15c3-1 6-1 9 1 3-2 6-2 9-1V4c-2-1-5-2-9 1Z"/><path d="M12 5v15"/>',
  refresh:
    '<path d="M20 7v5h-5M4 17v-5h5M5 8a8 8 0 0 1 13-3l2 3M4 16l2 3a8 8 0 0 0 13-3"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  check: '<path d="m5 12 4 4L19 6"/>',
  arrow: '<path d="m5 17 14-14M9 3h10v10"/>',
  document: '<path d="M6 3h9l4 4v14H6Z"/><path d="M14 3v5h5M9 12h7M9 16h5"/>',
  search: '<circle cx="10" cy="10" r="6"/><path d="m15 15 5 5"/>',
  download: '<path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5"/>',
};
document
  .querySelectorAll("[data-icon]")
  .forEach(
    (el) =>
      (el.innerHTML =
        '<svg viewBox="0 0 24 24" aria-hidden="true">' +
        (icons[el.dataset.icon] || "") +
        "</svg>"),
  );
const state = {
  demo: true,
  user: null,
  config: {},
  items: [],
  metrics: null,
  page: 1,
  total: 0,
  selected: null,
  loadId: 0,
};
const esc = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
let toastTimer;
function toast(message) {
  $("#toast").textContent = message;
  $("#toast").hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => ($("#toast").hidden = true), 6500);
}
async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      "X-Credit-Request": "1",
      ...(options.body instanceof FormData
        ? {}
        : { "Content-Type": "application/json" }),
      ...options.headers,
    },
  });
  if (!response.ok) {
    let body;
    try {
      body = await response.json();
    } catch {
      body = { detail: "No se pudo completar la operación." };
    }
    if (
      response.status === 401 &&
      path !== "/auth/login" &&
      path !== "/auth/me"
    ) {
      state.user = null;
      showLogin();
    }
    const detail = Array.isArray(body.detail)
      ? body.detail
          .map((x) => x.loc.slice(1).join(".") + ": " + x.msg)
          .join("\n")
      : body.detail;
    throw new Error(
      typeof detail === "string"
        ? detail
        : "Revisa los datos e intenta de nuevo.",
    );
  }
  return response.json();
}
function assessment(d) {
  const r = d.annual_rate / 1200,
    p = r
      ? (d.requested_amount * r) / -Math.expm1(-d.term_months * Math.log1p(r))
      : d.requested_amount / d.term_months;
  const ratio = (p + d.monthly_debt) / d.monthly_income,
    available = Math.max(0, d.monthly_income * 0.35 - d.monthly_debt);
  const factors = [
    {
      label: "Carga mensual de deuda ≤ 35%",
      passed: ratio <= 0.35,
      detail: (ratio * 100).toFixed(1) + "% del ingreso mensual",
    },
    {
      label: "Ingreso mínimo de $10,000 MXN",
      passed: d.monthly_income >= 10000,
      detail: money(d.monthly_income) + " MXN declarados",
    },
    {
      label: "Antigüedad bancaria ≥ 12 meses",
      passed: d.bank_seniority_months >= 12,
      detail: d.bank_seniority_months + " meses declarados",
    },
    {
      label: "Sin alerta interna reportada",
      passed: !d.is_blacklisted,
      detail: "Alerta declarada; no representa consulta a un buró",
    },
  ];
  return {
    score: Math.round(
      Math.max(
        0,
        Math.min(
          100,
          100 -
            Math.max(0, ratio - 0.15) * 120 -
            (d.monthly_income < 10000 ? 15 : 0) -
            (d.bank_seniority_months < 12 ? 15 : 0) -
            (d.is_blacklisted ? 40 : 0),
        ),
      ),
    ),
    monthly_payment: p,
    total_payment: p * d.term_months,
    debt_to_income: ratio * 100,
    max_amount: r
      ? (available * -Math.expm1(-d.term_months * Math.log1p(r))) / r
      : available * d.term_months,
    factors,
    notice:
      "Estimación con tasa fija, sin comisiones ni seguros. Requiere verificación documental y decisión humana.",
  };
}
const demoCases = [
  ["Comercial del Centro", 120000, 35000, 3000, "REVIEW", 0],
  ["Estudio Norte", 80000, 42000, 2500, "APPROVED", 0],
  ["María Torres · ejemplo", 45000, 23000, 1500, "REVIEW", 1],
  ["Distribuidora Horizonte", 250000, 68000, 6000, "APPROVED", 2],
  ["Taller Roble", 95000, 18000, 7000, "REJECTED", 3],
  ["Ana López · ejemplo", 60000, 27000, 3000, "REVIEW", 4],
  ["Servicios Nube", 150000, 51000, 5000, "APPROVED", 5],
  ["Grupo Alameda", 180000, 55000, 6000, "REVIEW", 6],
].map(
  ([name, requested_amount, monthly_income, monthly_debt, status, days], i) => {
    const d = {
      requested_amount,
      monthly_income,
      monthly_debt,
      term_months: 24,
      annual_rate: 24,
      bank_seniority_months: 36,
      is_blacklisted: false,
    };
    return {
      ...d,
      id: 1008 - i,
      name,
      status,
      assessment: assessment(d),
      document_verified: status === "APPROVED" ? "MATCHED" : "PENDING",
      version: 1,
      created_at: new Date(Date.now() - days * 86400000).toISOString(),
      risk_flag: status === "REJECTED" ? "HIGH" : "LOW",
      audit: [],
    };
  },
);
function demoMetrics() {
  const daily = Array.from({ length: 7 }, (_, i) => {
    const date = new Date(Date.now() - (6 - i) * 86400000)
      .toISOString()
      .slice(0, 10);
    return {
      date,
      count: demoCases.filter((c) => c.created_at.startsWith(date)).length,
    };
  });
  return {
    total_applications: demoCases.length,
    total_applications_today: daily[6].count,
    review: 4,
    approved: 3,
    rejected: 1,
    approved_percentage: 37.5,
    requested_volume: demoCases.reduce((a, c) => a + c.requested_amount, 0),
    pending_documents: 5,
    daily,
  };
}
function rowHTML(c) {
  const a = c.assessment,
    name = esc(c.name),
    initials = esc(
      c.name
        .split(" ")
        .slice(0, 2)
        .map((w) => w[0])
        .join(""),
    );
  const date = new Date(
    c.created_at.endsWith("Z") ? c.created_at : c.created_at + "Z",
  ).toLocaleDateString("es-MX", { day: "2-digit", month: "short" });
  return (
    '<tr><td><div class="person"><span class="avatar">' +
    initials +
    "</span><span><strong>" +
    name +
    "</strong><small>EXP-" +
    String(c.id).padStart(5, "0") +
    (state.demo ? " · Ficticio" : "") +
    "</small></span></div></td><td>" +
    (c.requested_amount == null ? "Sin monto" : money(c.requested_amount)) +
    '</td><td><span class="badge ' +
    esc(c.status) +
    '">' +
    esc(labels[c.status] || c.status) +
    "</span></td><td>" +
    (a
      ? '<span class="score"><span class="score-track"><i style="width:' +
        Math.max(0, Math.min(100, a.score)) +
        '%"></i></span>' +
        a.score +
        '<span class="subtle">/100</span></span>'
      : "Histórico") +
    "</td><td>" +
    esc(date) +
    '</td><td><button class="row-button" data-case="' +
    c.id +
    '" aria-label="Abrir expediente de ' +
    name +
    '">↗</button></td></tr>'
  );
}
function renderRows(target, items) {
  $(target).innerHTML = items.length
    ? items.map(rowHTML).join("")
    : '<tr><td colspan="6" class="empty">No hay solicitudes que mostrar. Crea una nueva o ajusta los filtros.</td></tr>';
}
function renderMetrics() {
  const m = state.metrics;
  $("#totalMetric").textContent = m.total_applications;
  $("#navCount").textContent = m.total_applications;
  $("#todayMetric").textContent =
    m.total_applications_today + " recibidas hoy · UTC";
  $("#reviewMetric").textContent = m.review;
  $("#approvalMetric").textContent = m.approved_percentage + "%";
  $("#volumeMetric").textContent = money(m.requested_volume);
  $("#docsInsight").textContent =
    m.pending_documents + " documentos por revisar";
  const max = Math.max(1, ...m.daily.map((d) => d.count));
  $("#activityChart").innerHTML = m.daily
    .map(
      (d) =>
        '<div class="chart-column"><span class="chart-number">' +
        d.count +
        '</span><div class="chart-bar" style="height:' +
        Math.max(2, (d.count / max) * 128) +
        'px" title="' +
        d.count +
        " solicitudes el " +
        d.date +
        '"></div><span class="chart-day">' +
        new Date(d.date + "T12:00:00Z").toLocaleDateString("es-MX", {
          weekday: "short",
          timeZone: "UTC",
        }) +
        "</span></div>",
    )
    .join("");
  $("#weekTotal").textContent =
    m.daily.reduce((s, d) => s + d.count, 0) + " en la semana";
}
async function load() {
  const requestId = ++state.loadId,
    search = $("#search").value.trim(),
    status = $("#statusFilter").value;
  $("#refresh").disabled = true;
  try {
    let list, recent, m;
    if (state.demo) {
      const rows = demoCases.filter(
        (c) =>
          (!status || c.status === status) &&
          c.name.toLowerCase().includes(search.toLowerCase()),
      );
      list = {
        items: rows.slice((state.page - 1) * 10, state.page * 10),
        total: rows.length,
      };
      recent = { items: demoCases.slice(0, 5) };
      m = demoMetrics();
    } else
      [list, recent, m] = await Promise.all([
        api(
          "/applications/?" +
            new URLSearchParams({
              search,
              status,
              page: state.page,
              page_size: 10,
            }),
        ),
        api("/applications/?page_size=5"),
        api("/dashboard/metrics"),
      ]);
    if (requestId !== state.loadId) return;
    state.items = list.items;
    state.total = list.total;
    state.metrics = m;
    renderMetrics();
    renderRows("#allRows", list.items);
    renderRows("#recentRows", recent.items);
    $("#recentCount").textContent = "(" + recent.items.length + ")";
    $("#pageInfo").textContent =
      list.total +
      " solicitudes · Página " +
      state.page +
      " de " +
      Math.max(1, Math.ceil(list.total / 10));
    $("#prevPage").disabled = state.page <= 1;
    $("#nextPage").disabled = state.page * 10 >= list.total;
  } catch (e) {
    toast(e.message);
  } finally {
    if (requestId === state.loadId) $("#refresh").disabled = false;
  }
}
function navigate() {
  const id = location.hash.slice(1) || "overview";
  const page = ["overview", "applications", "simulator", "guide"].includes(id)
    ? id
    : "overview";
  document
    .querySelectorAll(".page")
    .forEach((el) => (el.hidden = el.id !== page));
  document.querySelectorAll("[data-page]").forEach((el) => {
    el.classList.toggle("active", el.dataset.page === page);
    if (el.dataset.page === page) el.setAttribute("aria-current", "page");
    else el.removeAttribute("aria-current");
  });
  $("#pageTitle").textContent = {
    overview: "Resumen",
    applications: "Solicitudes",
    simulator: "Simulador",
    guide: "Centro de ayuda",
  }[page];
}
function updateSessionUI() {
  $("#demoBanner").hidden = !state.demo;
  $("#workspaceMode").textContent = state.demo
    ? "Vista de demostración"
    : "Organización · acceso privado";
  $("#accountName").textContent = state.demo
    ? "Modo demostración"
    : state.user.username;
  $("#accountCaption").textContent = state.demo
    ? "Conectar mi espacio"
    : "Cerrar sesión";
  $(".profile .avatar").textContent = state.demo
    ? "D"
    : state.user.username[0].toUpperCase();
  $("#loginButton").textContent = state.demo
    ? "Iniciar sesión ↗"
    : "Cerrar sesión";
  $("#aiMode").textContent = state.demo
    ? "Vista demo"
    : state.config.ai_configured
      ? "IA conectada"
      : "Análisis local";
}
function showLogin() {
  $("#loginError").textContent = "";
  $("#setupHint").textContent = state.config.login_configured
    ? ""
    : "El administrador debe configurar APP_PASSWORD en Render para habilitar el acceso. La demostración no expone datos reales.";
  if (!$("#loginDialog").open) $("#loginDialog").showModal();
}
async function account() {
  if (state.demo) {
    showLogin();
    return;
  }
  try {
    await api("/auth/logout", { method: "POST" });
    state.demo = true;
    state.user = null;
    state.selected = null;
    state.page = 1;
    $("#search").value = "";
    $("#statusFilter").value = "";
    document.querySelectorAll("dialog[open]").forEach((d) => d.close());
    updateSessionUI();
    await load();
    toast("Sesión cerrada.");
  } catch (e) {
    toast(e.message);
  }
}
function financialData(form) {
  const d = Object.fromEntries(new FormData(form));
  for (const k of [
    "monthly_income",
    "monthly_debt",
    "requested_amount",
    "term_months",
    "annual_rate",
    "bank_seniority_months",
  ])
    d[k] = Number(d[k]);
  d.is_blacklisted = form.elements.is_blacklisted?.checked || false;
  return d;
}
function factorsHTML(a) {
  return a.factors
    .map(
      (f) =>
        '<div class="factor ' +
        (f.passed ? "" : "warn") +
        '"><span>' +
        (f.passed ? "✓" : "!") +
        "</span><div>" +
        esc(f.label) +
        "<small>" +
        esc(f.detail) +
        "</small></div></div>",
    )
    .join("");
}
function analysisHTML(a) {
  return (
    '<div class="summary-grid"><div><small>Pago mensual estimado</small><strong>' +
    money(a.monthly_payment) +
    "</strong></div><div><small>Carga de deuda</small><strong>" +
    (Math.round(a.debt_to_income * 10) / 10).toFixed(1) +
    "%</strong></div><div><small>Total estimado a pagar</small><strong>" +
    money(a.total_payment) +
    "</strong></div><div><small>Monto a 35% de capacidad</small><strong>" +
    money(a.max_amount) +
    "</strong></div></div>" +
    factorsHTML(a) +
    '<p class="helper">' +
    esc(a.notice) +
    "</p>"
  );
}
async function openCase(id) {
  try {
    const c = state.demo
      ? demoCases.find((x) => x.id === id)
      : await api("/applications/" + id);
    if (!c) return;
    state.selected = c;
    $("#caseContent").innerHTML =
      '<p class="eyebrow">EXP-' +
      String(c.id).padStart(5, "0") +
      (state.demo ? " · DATOS FICTICIOS" : "") +
      "</p><h2>" +
      esc(c.name) +
      '</h2><span class="badge ' +
      esc(c.status) +
      '">' +
      esc(labels[c.status] || c.status) +
      "</span>" +
      (c.assessment
        ? '<p class="muted">Índice interno: ' +
          c.assessment.score +
          "/100 · Monto: " +
          money(c.requested_amount) +
          " · " +
          c.term_months +
          " meses</p>" +
          analysisHTML(c.assessment)
        : '<p class="helper">Expediente histórico creado con la política anterior. Crea una nueva solicitud con monto, deuda y plazo para evaluarlo con la política actual.</p>') +
      '<div class="detail-section"><h3>Verificación documental</h3><p class="muted">' +
      esc(labels[c.document_verified] || c.document_verified) +
      " · Una coincidencia textual no acredita autenticidad.</p>" +
      (c.rejection_reason
        ? '<p class="helper">' + esc(c.rejection_reason) + "</p>"
        : "") +
      '<label class="button file-button" style="margin-top:12px">Adjuntar comprobante PDF<input id="caseFile" type="file" accept="application/pdf" ' +
      (state.demo || !c.assessment ? "disabled" : "") +
      '></label><p class="helper">8 MB · 12 páginas · se procesa sin conservar el archivo. Una nueva carga devuelve el caso a revisión.</p></div>' +
      '<div class="copilot-box"><span class="ai-label">✧ COPILOTO DEL EXPEDIENTE</span><div class="copilot-actions"><button class="button compact" data-ai="summary">Resumen ejecutivo</button><button class="button compact" data-ai="checklist">Verificaciones</button><button class="button compact" data-ai="customer_message">Mensaje al cliente</button></div><p class="copilot-output" id="copilotOutput">Selecciona una tarea. Los borradores requieren revisión antes de su uso.</p><p class="helper" id="copilotNotice">Solo se comparten indicadores financieros y estados; no se envía información identificativa.</p></div>' +
      '<div class="detail-section"><h3>Decisión del responsable</h3><form id="reviewForm" class="review-form"><label>Resultado<select name="decision"><option value="REVIEW">Mantener en revisión</option><option value="APPROVED">Aprobar</option><option value="REJECTED">Rechazar</option></select></label><label>Justificación<textarea name="note" required minlength="10" maxlength="2000" rows="3" placeholder="Documenta la evidencia y el motivo de la decisión."></textarea></label><button class="button primary" ' +
      (state.demo || state.user?.role !== "admin" || !c.assessment
        ? "disabled"
        : "") +
      '>Registrar decisión</button></form><p class="helper">' +
      (state.demo
        ? "Inicia sesión para registrar decisiones reales."
        : "Solo admin puede decidir. Aprobar requiere un comprobante coincidente. La decisión queda registrada con fecha y responsable.") +
      "</p></div>" +
      '<div class="detail-section"><h3>Bitácora del expediente</h3>' +
      (c.audit?.length
        ? c.audit
            .map(
              (e) =>
                '<div class="audit-event"><small>' +
                esc(e.created_at) +
                " UTC · " +
                esc(e.actor) +
                "</small><strong>" +
                esc(
                  {
                    CREATED: "Solicitud creada",
                    REVIEWED: "Decisión registrada",
                    DOCUMENT_CHECKED: "Documento revisado",
                    COPILOT: "Copiloto consultado",
                  }[e.action] || e.action,
                ) +
                "</strong><p>" +
                esc(
                  e.detail.note ||
                    e.detail.result ||
                    e.detail.task ||
                    e.detail.policy_version ||
                    "",
                ) +
                "</p></div>",
            )
            .join("")
        : '<p class="helper">Sin eventos registrados en esta vista.</p>') +
      "</div>";
    if (!$("#caseDialog").open) $("#caseDialog").showModal();
  } catch (e) {
    toast(e.message);
  }
}
document.addEventListener("click", async (e) => {
  const close = e.target.closest("[data-close]");
  if (close) $("#" + close.dataset.close).close();
  const row = e.target.closest("[data-case]");
  if (row) await openCase(Number(row.dataset.case));
  const ai = e.target.closest("[data-ai]");
  if (!ai) return;
  const selected = state.selected,
    buttons = [...document.querySelectorAll("[data-ai]")];
  buttons.forEach((b) => (b.disabled = true));
  $("#copilotOutput").textContent = "Preparando el análisis…";
  try {
    let result;
    if (state.demo)
      result = {
        text:
          ai.dataset.ai === "customer_message"
            ? "Gracias por tu solicitud. Para continuar con la revisión, confirma tus ingresos y compromisos mensuales y adjunta un comprobante de domicilio vigente. El equipo revisará el expediente antes de comunicar una decisión."
            : ai.dataset.ai === "checklist"
              ? "1. Confirmar ingresos con estados de cuenta.\n2. Verificar compromisos mensuales vigentes.\n3. Revisar identidad y comprobante de domicilio.\n4. Registrar evidencia y decisión del responsable."
              : "El escenario estima un pago de " +
                money(selected.assessment.monthly_payment) +
                " al mes y una carga de deuda de " +
                selected.assessment.debt_to_income.toFixed(1) +
                "%.\n\nLa solicitud permanece sujeta a verificación documental y revisión del responsable.",
        notice: "Ejemplo local con datos ficticios. No generado por IA.",
      };
    else
      result = await api("/applications/" + selected.id + "/copilot", {
        method: "POST",
        body: JSON.stringify({ task: ai.dataset.ai }),
      });
    if (state.selected?.id === selected.id) {
      $("#copilotOutput").textContent = result.text;
      $("#copilotNotice").textContent = result.notice;
    }
  } catch (err) {
    $("#copilotOutput").textContent = err.message;
  } finally {
    buttons.forEach((b) => (b.disabled = false));
  }
});
$("#caseContent").addEventListener("change", async (e) => {
  if (e.target.id !== "caseFile" || !e.target.files.length) return;
  const file = e.target.files[0],
    id = state.selected.id;
  if (file.size > 8 * 1024 * 1024) {
    toast("El PDF no puede superar 8 MB.");
    return;
  }
  const form = new FormData();
  form.append("file", file);
  e.target.disabled = true;
  toast("Extrayendo y comparando el comprobante…");
  try {
    const result = await api("/applications/" + id + "/documents", {
      method: "POST",
      body: form,
    });
    await openCase(id);
    await load();
    toast(
      result.document_verified === "MATCHED"
        ? "Coincidencia detectada. El expediente está listo para revisión."
        : "Documento procesado. Revisa las diferencias detectadas.",
    );
  } catch (err) {
    toast(err.message);
    e.target.disabled = false;
  }
});
$("#caseContent").addEventListener("submit", async (e) => {
  if (e.target.id !== "reviewForm") return;
  e.preventDefault();
  const button = e.target.querySelector("button"),
    c = state.selected;
  button.disabled = true;
  try {
    const d = Object.fromEntries(new FormData(e.target));
    d.version = c.version;
    await api("/applications/" + c.id + "/review", {
      method: "POST",
      body: JSON.stringify(d),
    });
    await openCase(c.id);
    await load();
    toast("Decisión registrada en la bitácora.");
  } catch (err) {
    toast(err.message);
    button.disabled = false;
  }
});
$("#simulateForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const button = e.target.querySelector("button");
  button.disabled = true;
  try {
    const d = financialData(e.target),
      result = state.demo
        ? assessment(d)
        : await api("/simulate", { method: "POST", body: JSON.stringify(d) });
    $("#simulationOutput").innerHTML =
      '<span class="big-payment">' +
      money(result.monthly_payment) +
      "</span><p>Pago mensual estimado" +
      (state.demo ? " · simulación local" : "") +
      "</p>" +
      analysisHTML(result);
  } catch (err) {
    toast(err.message);
  } finally {
    button.disabled = false;
  }
});
document.querySelectorAll(".new-case").forEach((b) =>
  b.addEventListener("click", () => {
    if (state.demo) {
      showLogin();
      return;
    }
    $("#newDialog").showModal();
  }),
);
$("#loginForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const button = e.target.querySelector("button");
  button.disabled = true;
  $("#loginError").textContent = "";
  try {
    state.user = await api("/auth/login", {
      method: "POST",
      body: JSON.stringify(Object.fromEntries(new FormData(e.target))),
    });
    state.demo = false;
    state.page = 1;
    $("#search").value = "";
    $("#statusFilter").value = "";
    $("#loginDialog").close();
    e.target.reset();
    updateSessionUI();
    await load();
    toast("Espacio privado conectado.");
  } catch (err) {
    $("#loginError").textContent = err.message;
  } finally {
    button.disabled = false;
  }
});
$("#createForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const button = e.target.querySelector("button");
  button.disabled = true;
  try {
    const created = await api("/applications/", {
      method: "POST",
      body: JSON.stringify(financialData(e.target)),
    });
    $("#newDialog").close();
    e.target.reset();
    $("#extractNotice").textContent = "";
    state.page = 1;
    await load();
    await openCase(created.id);
    toast("Solicitud creada. Pendiente de revisión.");
  } catch (err) {
    toast(err.message);
  } finally {
    button.disabled = false;
  }
});
$("#extractFile").addEventListener("change", async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  if (file.size > 8 * 1024 * 1024) {
    toast("El PDF no puede superar 8 MB.");
    return;
  }
  e.target.disabled = true;
  $("#extractNotice").textContent = "Extrayendo campos del documento…";
  const form = new FormData();
  form.append("file", file);
  try {
    const d = await api("/applications/extract-document", {
      method: "POST",
      body: form,
    });
    let filled = 0;
    for (const k of [
      "name",
      "address",
      "rfc",
      "monthly_income",
      "bank_seniority_months",
    ]) {
      if (d[k] !== null && d[k] !== undefined) {
        $("#createForm").elements[k].value = d[k];
        filled++;
      }
    }
    $("#extractNotice").textContent =
      filled +
      " campos detectados. Confirma y corrige los datos antes de crear el expediente. " +
      d.warnings.join(" ");
  } catch (err) {
    $("#extractNotice").textContent = err.message;
  } finally {
    e.target.disabled = false;
    e.target.value = "";
  }
});
$("#exportButton").addEventListener("click", async () => {
  if (state.demo) {
    toast("Inicia sesión para exportar expedientes reales.");
    return;
  }
  const button = $("#exportButton");
  button.disabled = true;
  try {
    const params = new URLSearchParams({
        search: $("#search").value.trim(),
        status: $("#statusFilter").value,
      }),
      response = await fetch("/applications/export.csv?" + params);
    if (!response.ok)
      throw new Error("No se pudo exportar. Verifica tu sesión.");
    const url = URL.createObjectURL(await response.blob()),
      link = document.createElement("a");
    link.href = url;
    link.download = "creditos.csv";
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    toast("Exportación descargada y registrada.");
  } catch (err) {
    toast(err.message);
  } finally {
    button.disabled = false;
  }
});
let searchTimer;
$("#search").addEventListener("input", () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    state.page = 1;
    load();
  }, 300);
});
$("#statusFilter").addEventListener("change", () => {
  state.page = 1;
  load();
});
$("#prevPage").addEventListener("click", () => {
  state.page--;
  load();
});
$("#nextPage").addEventListener("click", () => {
  state.page++;
  load();
});
$("#refresh").addEventListener("click", load);
$("#loginButton").addEventListener("click", account);
$("#accountButton").addEventListener("click", account);
$("#bannerLogin").addEventListener("click", showLogin);
$("#reviewQueue").addEventListener("click", () => {
  location.hash = "applications";
  $("#statusFilter").value = "REVIEW";
  state.page = 1;
  load();
});
$("#exploreAI").addEventListener("click", () => {
  location.hash = "applications";
  toast("Abre un expediente y elige una tarea del copiloto.");
});
window.addEventListener("hashchange", navigate);
async function init() {
  navigate();
  try {
    state.config = await api("/config");
  } catch {
    toast("No hay conexión con el servidor. Puedes explorar la demostración.");
  }
  try {
    state.user = await api("/auth/me");
    state.demo = false;
  } catch {
    state.demo = true;
  }
  updateSessionUI();
  await load();
}
init();
