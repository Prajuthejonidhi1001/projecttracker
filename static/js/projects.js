/* Project Scheduler — list tab + dashboard rendering + minor UX. */
(function () {
  "use strict";
  var CSRF = window.PS_CSRF || "";

  function api(url, method, body) {
    return fetch(url, {
      method: method,
      headers: { "Content-Type": "application/json", "X-CSRFToken": CSRF },
      body: body ? JSON.stringify(body) : undefined,
    }).then(function (r) {
      return r.json().then(function (d) {
        if (!r.ok) {
          var msg = d && (d.detail || d.error);
          if (d && typeof d === "object") {
            var first = Object.keys(d)[0];
            if (first && typeof d[first] === "string") msg = d[first];
            else if (first) msg = JSON.stringify(d);
          }
          throw new Error(msg || ("Request failed: " + r.status));
        }
        return d;
      });
    });
  }

  function flash(msg, ok) {
    var el = document.createElement("div");
    el.className = "alert alert-" + (ok ? "success" : "danger") + " alert-dismissible fade show small";
    el.style.position = "fixed";
    el.style.top = "10px";
    el.style.right = "10px";
    el.style.zIndex = 2000;
    el.innerHTML = msg + "<button type='button' class='btn-close' data-bs-dismiss='alert'></button>";
    document.body.appendChild(el);
    setTimeout(function () { el.remove(); }, 3500);
  }

  /* ---------- list tab ---------- */
  function initListTab() {
    var table = document.getElementById("taskListTable");
    if (!table) return;

    document.querySelectorAll(".task-status-select").forEach(function (sel) {
      sel.addEventListener("change", function () {
        api("/api/project-tasks/" + sel.dataset.taskId + "/", "PATCH", { status: sel.value })
          .then(function () { flash("Status updated.", true); })
          .catch(function (e) { flash(e.message, false); });
      });
    });
    document.querySelectorAll(".task-progress-input").forEach(function (inp) {
      function commit() {
        var v = Number(inp.value);
        if (isNaN(v) || v < 0 || v > 100) { flash("Progress must be 0–100.", false); return; }
        api("/api/project-tasks/" + inp.dataset.taskId + "/progress/", "POST", { percent_complete: v })
          .then(function () { flash("Progress updated.", true); })
          .catch(function (e) { flash(e.message, false); });
      }
      inp.addEventListener("change", commit);
      inp.addEventListener("blur", commit);
    });

    var rows = Array.prototype.slice.call(document.querySelectorAll(".wbs-row"));
    var byParent = {};
    rows.forEach(function (r) {
      var p = r.getAttribute("data-parent-id");
      (byParent[p] = byParent[p] || []).push(r);
    });
    function descendants(id) {
      var out = [], stack = (byParent[id] || []).slice();
      while (stack.length) {
        var r = stack.shift();
        out.push(r);
        var c = byParent[r.getAttribute("data-task-id")] || [];
        stack = stack.concat(c);
      }
      return out;
    }
    document.querySelectorAll(".wbs-toggle").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var tr = btn.closest("tr");
        var id = tr.getAttribute("data-task-id");
        var kids = byParent[id] || [];
        var collapsed = kids.length && kids[0].style.display === "none";
        descendants(id).forEach(function (r) {
          r.style.display = collapsed ? "" : "none";
        });
        btn.innerHTML = collapsed ? "<i class='bi bi-chevron-down'></i>" : "<i class='bi bi-chevron-right'></i>";
      });
    });
    var expandAll = document.getElementById("listExpandAll");
    var collapseAll = document.getElementById("listCollapseAll");
    if (expandAll) expandAll.addEventListener("click", function () {
      rows.forEach(function (r) { r.style.display = ""; });
      document.querySelectorAll(".wbs-toggle").forEach(function (b) { b.innerHTML = "<i class='bi bi-chevron-down'></i>"; });
    });
    if (collapseAll) collapseAll.addEventListener("click", function () {
      rows.forEach(function (r) {
        if (r.getAttribute("data-parent-id")) r.style.display = "none";
      });
      document.querySelectorAll(".wbs-toggle").forEach(function (b) { b.innerHTML = "<i class='bi bi-chevron-right'></i>"; });
    });
    var searchEl = document.getElementById("listSearch");
    if (searchEl) searchEl.addEventListener("input", function () {
      var q = (searchEl.value || "").trim().toLowerCase();
      rows.forEach(function (r) {
        var text = (r.getAttribute("data-name") || "") + (r.getAttribute("data-owner") || "") + (r.getAttribute("data-wbs") || "");
        r.style.display = q && text.indexOf(q) < 0 ? "none" : "";
        if (q) {
          var parentId = r.getAttribute("data-parent-id");
          var parentRow = rows.find(function (x) { return x.getAttribute("data-task-id") === parentId; });
          if (parentRow) parentRow.style.display = "";
        }
      });
    });
  }

  /* ---------- dashboard tab ---------- */
  function initDashboard() {
    var root = document.getElementById("dashCards");
    if (!root) return;
    var D = window.PS_DASHBOARD || {};
    var s = D.summary || {};
    function set(id, v) { var el = document.getElementById(id); if (el) el.textContent = v; }
    set("cardPercent", Math.round(s.percent_complete || 0) + "%");
    set("cardCompleted", s.completed);
    set("cardInProgress", s.in_progress);
    set("cardOverdue", s.overdue);
    function listOf(id, arr, build) {
      var el = document.getElementById(id);
      if (!el) return;
      el.innerHTML = "";
      (arr || []).forEach(function (item) {
        var li = document.createElement("li");
        li.className = "list-group-item d-flex justify-content-between align-items-start";
        li.innerHTML = build(item);
        el.appendChild(li);
      });
      if (!(arr || []).length) el.innerHTML = "<li class='list-group-item text-muted small'>None</li>";
    }
    listOf("dashUpcoming", D.upcoming, function (t) {
      return "<div><a class='text-decoration-none' href='#' data-task='" + t.id + "'>" + t.wbs_code + " " + t.name + "</a></div><small class='text-muted'>" + t.start_date + " → " + t.finish_date + "</small>";
    });
    listOf("dashOverdue", D.overdue, function (t) {
      return "<div><a class='text-decoration-none text-danger' href='#' data-task='" + t.id + "'>" + t.wbs_code + " " + t.name + "</a></div><small class='text-muted'>due " + t.finish_date + "</small>";
    });
    listOf("dashMilestones", D.milestones, function (t) {
      return "<div><span class='text-warning me-1'>&#9670;</span>" + t.name + "</div><small class='text-muted'>" + t.start_date + "</small>";
    });
    var vEl = document.getElementById("dashVariance");
    if (vEl && D.variance) {
      var v = D.variance;
      var rows = "";
      rows += "<div class='d-flex justify-content-between border-bottom pb-1 mb-1'><span>Project slip</span><strong class='" + (v.project_slip_days > 0 ? "text-danger" : v.project_slip_days < 0 ? "text-success" : "") + "'>" + (v.project_slip_days === null || v.project_slip_days === undefined ? "n/a" : (v.project_slip_days > 0 ? "+" + v.project_slip_days : v.project_slip_days) + " days") + "</strong></div>";
      rows += "<div class='d-flex justify-content-between border-bottom pb-1 mb-1'><span>Tasks behind</span><strong>" + v.delayed_tasks + "</strong></div>";
      rows += "<div class='d-flex justify-content-between'><span>Worst slippage</span><strong class='text-danger'>" + (v.max_slip_days ? "+" + v.max_slip_days + " days" : "—") + "</strong></div>";
      vEl.innerHTML = rows;
    }
    document.querySelectorAll("#dashCards a[data-task], ul a[data-task]").forEach(function (a) {
      a.addEventListener("click", function (e) { e.preventDefault(); });
    });
  }

  /* ---------- csv export link ---------- */
  function initCsv() {
    var a = document.querySelector("[data-csv-export]");
    var pid = window.PS_PROJECT && window.PS_PROJECT.project && window.PS_PROJECT.project.id;
    if (a && pid) { a.href = "/api/projects/" + pid + "/csv/"; a.setAttribute("download", ""); }
  }

  function boot() {
    initCsv();
    if (document.getElementById("taskListTable")) initListTab();
    if (document.getElementById("dashCards")) initDashboard();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();