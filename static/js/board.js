/* Project Scheduler — Kanban board. Reads window.PS_BOARD / window.PS_CSRF. */
(function () {
  "use strict";
  var BOARD = window.PS_BOARD || { columns: {} };
  var CSRF = window.PS_CSRF || "";

  function fmt(d) {
    if (!d) return "";
    var p = d.split("-");
    return p[1] + "/" + p[2];
  }

  function render() {
    var statuses = Object.keys(BOARD.columns);
    statuses.forEach(function (status) {
      var col = document.querySelector("[data-board-col='" + status + "']");
      if (!col) return;
      col.innerHTML = "";
      var countEl = document.querySelector("[data-col-status='" + status + "'][data-col-count]");
      var tasks = BOARD.columns[status] || [];
      if (countEl) countEl.textContent = tasks.length;
      tasks.forEach(function (t) {
        var card = document.createElement("div");
        card.className = "card board-card mb-2 small";
        card.draggable = true;
        card.dataset.taskId = t.id;
        var inner = "";
        inner += "<div class='card-body py-2'>";
        inner += "<div class='d-flex justify-content-between'><span class='text-muted' style='font-size:.7rem'>" + (t.wbs_code || "") + "</span>";
        inner += t.is_critical ? "<span class='badge text-bg-danger' style='font-size:.6rem'>CP</span>" : (t.is_milestone ? "<i class='bi bi-diamond text-warning'></i>" : "");
        inner += "</div>";
        inner += "<div class='fw-semibold' style='line-height:1.2'>" + t.name + "</div>";
        if (t.finish_date) inner += "<div class='text-muted' style='font-size:.72rem'>" + fmt(t.start_date) + " → " + fmt(t.finish_date) + "</div>";
        if (t.owner_name) inner += "<div class='text-muted' style='font-size:.7rem'>" + t.owner_name + "</div>";
        inner += "<div class='progress mt-1' style='height:5px'><div class='progress-bar' style='width:" + t.percent_complete + "%'></div></div>";
        inner += "</div>";
        card.innerHTML = inner;
        card.addEventListener("click", function () { window.location.hash = ""; });
        card.addEventListener("dragstart", function (e) { e.dataTransfer.setData("text/plain", t.id); card.classList.add("opacity-50"); });
        card.addEventListener("dragend", function () { card.classList.remove("opacity-50"); });
        col.appendChild(card);
      });
      if (!tasks.length) {
        var hint = document.createElement("div");
        hint.className = "text-muted text-center small py-4";
        hint.textContent = "No tasks";
        col.appendChild(hint);
      }
    });
  }

  document.querySelectorAll("[data-board-col]").forEach(function (col) {
    col.addEventListener("dragover", function (e) { e.preventDefault(); });
    col.addEventListener("drop", function (e) {
      e.preventDefault();
      var id = e.dataTransfer.getData("text/plain");
      var status = col.getAttribute("data-board-col");
      if (!id || !status) return;
      fetch("/api/project-tasks/" + id + "/", {
        method: "PATCH",
        headers: { "Content-Type": "application/json", "X-CSRFToken": CSRF },
        body: JSON.stringify({ status: status }),
      }).then(function (r) {
        if (!r.ok) return r.json().then(function (d) { throw new Error((d && (d.detail || JSON.stringify(d))) || "Failed"); });
        reloadBoard();
      }).catch(function (err) {
        var el = document.createElement("div");
        el.className = "alert alert-danger small mt-2";
        el.textContent = err.message;
        col.prepend(el);
        setTimeout(function () { el.remove(); }, 3000);
      });
    });
  });

  function reloadBoard() {
    var projectId = window.PS_PROJECT && window.PS_PROJECT.project && window.PS_PROJECT.project.id;
    if (!projectId) return;
    fetch("/api/projects/" + projectId + "/gantt/", { headers: { "X-CSRFToken": CSRF } })
      .then(function (r) { return r.json(); })
      .then(function (payload) {
        var cols = {};
        payload.tasks.forEach(function (t) { (cols[t.status] = cols[t.status] || []).push(t); });
        BOARD = { columns: cols };
        render();
      });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", render);
  else render();
})();