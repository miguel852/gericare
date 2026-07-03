const qs = (selector, scope = document) => scope.querySelector(selector);
const qsa = (selector, scope = document) => [...scope.querySelectorAll(selector)];

let lastDigest = "";

window.addEventListener("DOMContentLoaded", () => {
  bindFilters();
  bindTaskToggles();
  bindDigest();
  bindEventForm();
  bindFamilyTools();
  bindFocusMode();
  registerServiceWorker();
});

function bindFilters() {
  const search = qs("#residentSearch");
  qsa(".chip").forEach((button) => {
    button.addEventListener("click", () => {
      qsa(".chip").forEach((chip) => chip.classList.remove("active"));
      button.classList.add("active");
      filterResidents();
    });
  });
  search?.addEventListener("input", filterResidents);
}

function filterResidents() {
  const activeRisk = qs(".chip.active")?.dataset.risk || "all";
  const term = (qs("#residentSearch")?.value || "").trim().toLowerCase();

  qsa(".resident-card").forEach((card) => {
    const matchesRisk = activeRisk === "all" || card.dataset.risk === activeRisk;
    const matchesTerm = !term || card.dataset.search.includes(term);
    card.hidden = !(matchesRisk && matchesTerm);
  });

}

function bindTaskToggles() {
  qsa(".task-toggle").forEach((button) => {
    button.addEventListener("click", async () => {
      const taskId = button.dataset.taskId;
      const row = button.closest(".task-row");
      row.classList.add("loading");
      try {
        const response = await fetch(`/api/tasks/${taskId}/toggle`, { method: "POST" });
        if (!response.ok) throw new Error("Falha ao atualizar tarefa");
        const task = await response.json();
        row.classList.toggle("done", task.status === "done");
        toast(task.status === "done" ? "Tarefa concluida." : "Tarefa reaberta.");
      } catch (error) {
        toast(error.message);
      } finally {
        row.classList.remove("loading");
      }
    });
  });
}

function bindDigest() {
  const panel = qs("#digestPanel");
  const headline = qs("#digestHeadline");
  const summary = qs("#digestSummary");
  const actions = qs("#digestActions");

  qsa(".digest-button").forEach((button) => {
    button.addEventListener("click", async () => {
      try {
        const response = await fetch(`/api/residents/${button.dataset.residentId}/digest`);
        if (!response.ok) throw new Error("Resumo nao encontrado");
        const digest = await response.json();
        headline.textContent = digest.headline;
        summary.textContent = digest.summary;
        actions.innerHTML = "";
        digest.actions.forEach((action) => {
          const item = document.createElement("li");
          item.textContent = action;
          actions.appendChild(item);
        });
        lastDigest = `${digest.headline}\n\n${digest.summary}\n\nCondutas:\n- ${digest.actions.join("\n- ")}`;
        panel.classList.add("open");
      } catch (error) {
        toast(error.message);
      }
    });
  });

  qs("#closeDigest")?.addEventListener("click", () => panel.classList.remove("open"));
  qs("#copyDigest")?.addEventListener("click", async () => {
    if (!lastDigest) return;
    try {
      await navigator.clipboard.writeText(lastDigest);
      toast("Resumo copiado.");
    } catch {
      toast("Nao foi possivel copiar automaticamente.");
    }
  });
}

function bindEventForm() {
  qs("#openQuickEvent")?.addEventListener("click", () => {
    qs("#quickEvent")?.scrollIntoView({ behavior: "smooth", block: "center" });
    qs('#eventForm textarea[name="note"]')?.focus();
  });

  qs("#eventForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const residentId = data.get("resident_id");
    const payload = {
      resident_id: residentId ? Number(residentId) : null,
      event_type: "note",
      severity: data.get("severity"),
      note: data.get("note"),
    };

    try {
      const response = await fetch("/api/events", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!response.ok) throw new Error("Nao foi possivel salvar o evento");
      const created = await response.json();
      prependEvent(created);
      form.reset();
      toast("Evento salvo.");
    } catch (error) {
      toast(error.message);
    }
  });
}

function prependEvent(event) {
  const row = document.createElement("article");
  row.className = `event-row ${event.severity}`;
  row.innerHTML = `
    <span></span>
    <div>
      <strong>${escapeHtml(event.resident_name || "Plantao")}</strong>
      <small>${escapeHtml(event.note)}</small>
    </div>
  `;
  qs("#eventList")?.prepend(row);
}

function bindFamilyTools() {
  qsa(".copy-phone").forEach((button) => {
    button.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(button.dataset.phone);
        toast("Telefone copiado.");
      } catch {
        toast(button.dataset.phone);
      }
    });
  });
}

function bindFocusMode() {
  qs("#focusMode")?.addEventListener("click", () => {
    document.body.classList.toggle("focus-mode");
    toast(document.body.classList.contains("focus-mode") ? "Modo foco ligado." : "Modo foco desligado.");
  });
}

function registerServiceWorker() {
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/static/service-worker.js").catch(() => {});
  }
}

function toast(message) {
  const element = qs("#toast");
  element.textContent = message;
  element.classList.add("show");
  window.setTimeout(() => element.classList.remove("show"), 2200);
}

function escapeHtml(value) {
  const template = document.createElement("template");
  template.textContent = value;
  return template.innerHTML;
}
