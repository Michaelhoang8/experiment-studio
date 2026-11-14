/* DOM text is escaped before markup interpolation; all writes go through the API. */
"use strict";
let state = { experiments: [] };
const $ = (selector) => document.querySelector(selector);
const escape = (value) =>
  String(value).replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const percent = (value) => `${(value * 100).toFixed(2)}%`;
const empty = (message) => `<p class="empty">${message}</p>`;
function notice(message, error = false) {
  $("#notice").textContent = message;
  $("#notice").className = message ? `notice${error ? " error" : ""}` : "";
}
function stats(target, items) {
  $(target).innerHTML = items
    .map(
      ([label, value]) =>
        `<div class="stat"><small>${label}</small><strong>${value}</strong></div>`,
    )
    .join("");
}
let refreshSequence = 0;
async function refresh() {
  const sequence = ++refreshSequence;
  let received;
  try {
    received = await window.restTransport.send("/api/state", { method: "GET" });
  } catch (error) {
    if (sequence !== refreshSequence) return;
    throw error;
  }
  if (sequence !== refreshSequence) return;
  const { response, text } = received;
  if (!response.ok)
    throw new Error("Could not load workspace. Check the server and refresh.");
  let next;
  try {
    next = JSON.parse(text);
    if (!next || !["experiments"].every((key) => Array.isArray(next[key])))
      throw Error();
  } catch {
    throw Error(
      "The workspace returned an unreadable response. Check the server and refresh.",
    );
  }
  state = next;
  render();
}

function comparisonReport(comparison) {
  const interval = comparison.difference_interval
    .map((value) => (value * 100).toFixed(2))
    .join(" to ");
  const p =
    comparison.p_value === null
      ? "Unavailable"
      : comparison.p_value < 0.0001
        ? "< 0.0001"
        : comparison.p_value.toFixed(4);
  const status = {
    insufficient_counts:
      "Counts are too sparse for the normal-approximation test.",
    difference_detected: "Evidence of a difference at the 5% level.",
    inconclusive:
      "No clear evidence of a difference at the 5% level. This does not establish equivalence.",
  }[comparison.status];
  return `<p class="help">95% interval for B − A: <strong>${interval} pp</strong></p><details class="comparison-details"><summary>Comparison method &amp; evidence</summary><p>${escape(status)}</p><p>Two-sided p-value: <strong>${escape(p)}</strong></p><p class="help">The adjusted interval uses Agresti–Caffo; the test uses pooled variance. These methods can disagree near a cutoff. The test requires at least 5 expected successes and failures in each variant.</p><p class="help">Assumes independent randomized groups and a fixed stopping point. No correction for repeated looks or multiple comparisons. A p-value is not the probability that B is better, and statistical evidence does not measure business value.</p></details>`;
}

function experimentContext(experiment) {
  if (!experiment.hypothesis && !experiment.primary_metric) return "";
  return `<details><summary>Experiment context</summary>${experiment.primary_metric ? `<p><strong>Primary conversion metric</strong><br>${escape(experiment.primary_metric)}</p>` : ""}${experiment.hypothesis ? `<p><strong>Hypothesis</strong><br>${escape(experiment.hypothesis)}</p>` : ""}</details>`;
}

let selectedExperiment = null;
function intervalPlot(e) {
  const max = Math.min(
      1,
      Math.max(e.a_interval[1], e.b_interval[1], 0.01) * 1.15,
    ),
    x = (n) => 85 + (n / max) * 535;
  let chart = `<svg class="interval-chart" viewBox="0 0 680 240" role="img" aria-label="Variant conversion rates with 95 percent Wilson confidence intervals"><title>Conversion rates and Wilson intervals, axis from 0 to ${percent(max)}</title>`;
  for (let i = 0; i <= 4; i++) {
    const n = (max * i) / 4;
    chart += `<line x1="${x(n)}" x2="${x(n)}" y1="30" y2="190" class="plot-grid"/><text x="${x(n)}" y="215" text-anchor="middle">${percent(n)}</text>`;
  }
  ["a", "b"].forEach((v, i) => {
    const y = 70 + i * 85,
      lo = x(e[v + "_interval"][0]),
      hi = x(e[v + "_interval"][1]);
    chart += `<g class="variant-${v}"><text x="25" y="${y + 5}">${v.toUpperCase()}</text><line x1="${lo}" x2="${hi}" y1="${y}" y2="${y}" class="ci-range"/><path d="M ${lo} ${y - 8} v 16 M ${hi} ${y - 8} v 16" class="ci-cap"/><circle cx="${x(e[v + "_rate"])}" cy="${y}" r="7"/><text x="${x(e[v + "_rate"])}" y="${y - 20}" text-anchor="middle">${percent(e[v + "_rate"])}</text></g>`;
  });
  return chart + "</svg>";
}
function render() {
  const entries = state.experiments;
  if (!entries.some((e) => String(e.id) === String(selectedExperiment)))
    selectedExperiment = entries[0]?.id;
  const e = entries.find((e) => String(e.id) === String(selectedExperiment));
  if (!e) {
    $("#experiment-results").innerHTML =
      '<div class="panel"><h2>No saved analyses</h2><p>Enter visitor and conversion counts for both variants.</p></div>';
    return;
  }
  $("#experiment-results").innerHTML =
    `<label class="analysis-picker">Saved analysis<select id="analysis-select">${entries.map((item) => `<option value="${escape(item.id)}" ${item.id === e.id ? "selected" : ""}>${escape(item.name)}</option>`).join("")}</select></label><article class="panel experiment-report"><h2>${escape(e.name)}</h2>${experimentContext(e)}<div class="plot-scroll">${intervalPlot(e)}</div><p class="plot-caption">Conversion rate · dots are estimates · bars show 95% Wilson intervals</p><div class="variant-counts">${["a", "b"].map((v) => `<div><small>Variant ${v.toUpperCase()}</small><strong>${percent(e[v + "_rate"])}</strong><span>${e[v + "_conversions"]} conversions / ${e[v + "_visitors"]} visitors</span><span>95% CI ${percent(e[v + "_interval"][0])}–${percent(e[v + "_interval"][1])}</span></div>`).join("")}</div><div class="result-bottom"><div>Absolute difference<strong>${(e.difference * 100).toFixed(2)} pp</strong></div><div>Relative lift<strong>${e.relative_lift === null ? "N/A" : percent(e.relative_lift)}</strong></div></div>${comparisonReport(e.comparison)}</article>`;
  $("#analysis-select").onchange = (event) => {
    selectedExperiment = event.target.value;
    render();
    $("#analysis-select").focus();
  };
  if (
    !document.body.classList.contains("still-life") &&
    !matchMedia("(prefers-reduced-motion: reduce)").matches
  )
    $(".interval-chart").animate(
      [
        { opacity: 0.3, transform: "translateY(4px)" },
        { opacity: 1, transform: "translateY(0)" },
      ],
      { duration: 400, easing: "ease-out" },
    );
}

async function post(path, data) {
  let response, raw;
  try {
    const received = await window.restTransport.send(path, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Portfolio-Client": "browser",
      },
      body: JSON.stringify(data),
    });
    response = received.response;
    raw = received.text;
  } catch (error) {
    if (path === "/api/movements" && data.request_key)
      throw Error(
        `${error.message} The movement may have been saved. Keep the same inputs to retry with the same request key; it will not change stock twice.`,
      );
    throw Error(window.restTransport.recoveryMessage(error, "POST"));
  }
  let result;
  try {
    result = JSON.parse(raw);
    if (!result || typeof result !== "object" || Array.isArray(result))
      throw Error();
  } catch {
    throw Error(
      "The server returned an unreadable response. The write may have completed; refresh the workspace before retrying.",
    );
  }
  if (!response.ok) {
    const error = new Error(result.error || "Request failed");
    error.status = response.status;
    throw error;
  }
  return result;
}
function wireForm(id, path, numbers) {
  let pendingMovement = null;
  const feedback = document.createElement("p");
  feedback.className = "form-feedback";
  feedback.setAttribute("role", "status");
  $(id).append(feedback);
  $(id).addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget,
      button = form.querySelector("button");
    if (form.dataset.saving) return;
    const data = Object.fromEntries(new FormData(form));
    numbers.forEach((key) => (data[key] = Number(data[key])));
    if (path === "/api/movements") {
      const signature = JSON.stringify(data);
      if (!pendingMovement || pendingMovement.signature !== signature)
        pendingMovement = { signature, key: crypto.randomUUID() };
      data.request_key = pendingMovement.key;
    }
    const controls = [...form.elements],
      disabled = controls.map((control) => control.disabled);
    form.dataset.saving = "true";
    form.setAttribute("aria-busy", "true");
    controls.forEach((control) => (control.disabled = true));
    const originalLabel = button.textContent;
    const feedback = form.querySelector(".form-feedback");
    feedback.textContent = "Saving…";
    button.disabled = true;
    button.textContent = "Saving…";
    try {
      const saved = await post(path, data);
      selectedExperiment = saved.id ?? null;
      pendingMovement = null;
      form.reset();
      const message = saved.replayed
        ? "Previously saved movement confirmed. Stock was not changed twice."
        : "Saved to your workspace.";
      try {
        await refresh();
        notice(message);
        feedback.textContent = message;
      } catch (error) {
        const message =
          "Saved successfully, but the workspace could not refresh. Reload to see the latest data.";
        notice(message, true);
        feedback.textContent = message;
      }
    } catch (error) {
      notice(error.message, true);
      feedback.textContent = error.message;
    } finally {
      controls.forEach((control, i) => (control.disabled = disabled[i]));
      button.textContent = originalLabel;
      delete form.dataset.saving;
      form.setAttribute("aria-busy", "false");
    }
  });
}

wireForm("#experiment-form", "/api/experiments", [
  "a_visitors",
  "a_conversions",
  "b_visitors",
  "b_conversions",
]);

const titles = { experiments: "Experiment Studio" };
function navigate(page) {
  page = "experiments";
  window.designIdentity(page);
  document
    .querySelectorAll(".page")
    .forEach((section) => (section.hidden = section.id !== page));
  document.querySelectorAll("[data-page]").forEach((button) => {
    button.classList.toggle("selected", button.dataset.page === page);
    button.setAttribute("aria-pressed", String(button.dataset.page === page));
  });
  $("#breadcrumb").textContent = titles[page];
  document.title = `${titles[page]}`;
  notice("");
}
document.querySelectorAll("[data-page]").forEach((button) =>
  button.addEventListener("click", () => {
    location.hash = button.dataset.page;
  }),
);
window.addEventListener("hashchange", () => navigate(location.hash.slice(1)));
$("#export").addEventListener("click", () => {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(state, null, 2)], { type: "application/json" }),
  );
  const link = document.createElement("a");
  link.href = url;
  link.download = "experiment-studio-workspace.json";
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});
navigate(location.hash.slice(1));
refresh().catch((error) => notice(error.message, true));
