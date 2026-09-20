/* Project Scheduler — interactive Gantt chart.
 * Reads window.PS_PROJECT (payload rendered by the server), window.PS_CSRF.
 * Vanilla JS; depends on Bootstrap 5 (modal/offcanvas).
 */
(function () {
  "use strict";

  var DATA = window.PS_PROJECT || null;
  var CSRF = window.PS_CSRF || "";
  var STATE = {
    zoom: "2weeks",
    expanded: {},
    showCritical: true,
    showBaseline: false,
    showLinks: true,
    selectedId: null,
    search: "",
  };
  var ZOOMS = {
    day: { per: "day", width: 30 },
    week: { per: "day", width: 13 },
    "2weeks": { per: "day", width: 9 },
    month: { per: "week", width: 26 },
    quarter: { per: "month", width: 96 },
    year: { per: "month", width: 34 },
  };

  var els = {};
  var layout = {};
  var tasksById = {};
  var cascadeLock = false;

  /* ---------------- utilities ---------------- */
  function pad(n) { return String(n).padStart(2, "0"); }
  function iso(d) { return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate()); }
  function parse(s) {
    if (!s) return null;
    var m = String(s).match(/^(\d{4})-(\d{2})-(\d{2})/);
    if (!m) return null;
    return new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
  }
  function addDays(d, n) { return new Date(d.getFullYear(), d.getMonth(), d.getDate() + n); }
  function dayDiff(a, b) { return Math.round((a - b) / 86400000); }
  function sameDay(a, b) {
    return a && b && a.getFullYear() === b.getFullYear() &&
      a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
  }
  function fmt(d) {
    return d ? d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: d.getFullYear() !== new Date().getFullYear() ? "numeric" : undefined }) : "—";
  }
  function api(url, method, body) {
    var opts = { method: method || "GET", headers: { "X-CSRFToken": CSRF } };
    if (body !== undefined) {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(body);
    }
    return fetch(url, opts).then(function (r) {
      return r.json().then(function (data) {
        if (!r.ok) {
          var msg = data && (data.detail || data.error);
          if (data && typeof data === "object") {
            var first = Object.keys(data)[0];
            if (first && typeof data[first] === "string") msg = data[first];
          }
          throw new Error(msg || ("Request failed: " + r.status));
        }
        return data;
      });
    });
  }
  function qs(name) { return document.querySelector(name); }
  function toast(msg, ok) {
    var el = document.createElement("div");
    el.className = "alert alert-" + (ok ? "success" : "danger") + " alert-dismissible fade show small";
    el.style.position = "fixed";
    el.style.top = "10px";
    el.style.right = "10px";
    el.style.zIndex = 2000;
    el.innerHTML = "<span class=\"pe-2\">" + msg + "</span><button type=\"button\" class=\"btn-close\" data-bs-dismiss=\"alert\"></button>";
    document.body.appendChild(el);
    setTimeout(function () { el.remove(); }, 4000);
  }

  function isWorking(d) {
    if (DATA.use_calendar_days) return true;
    var wd = DATA.working_days || [0, 1, 2, 3, 4];
    if (wd.indexOf(d.getDay()) === -1) return false;
    var key = iso(d);
    return (DATA.holidays || []).indexOf(key) === -1;
  }

  /* ---------------- layout computation ---------------- */
  function buildLayout() {
    var today = new Date();
    today = new Date(today.getFullYear(), today.getMonth(), today.getDate());
    var mins = [today], maxs = [addDays(today, 4)];
    DATA.tasks.forEach(function (t) {
      if (t.start_date) mins.push(parse(t.start_date));
      if (t.finish_date) maxs.push(parse(t.finish_date));
      if (t.baseline_start) mins.push(parse(t.baseline_start));
      if (t.baseline_finish) maxs.push(parse(t.baseline_finish));
    });
    var min = new Date(Math.min.apply(null, mins.map(Number)));
    var max = new Date(Math.max.apply(null, maxs.map(Number)));
    min = addDays(min, -7);
    max = addDays(max, 7);
    var z = ZOOMS[STATE.zoom];
    var cols = [];
    if (z.per === "day") {
      var d = min;
      while (d <= max) { cols.push({ start: d, end: d, width: z.width }); d = addDays(d, 1); }
    } else if (z.per === "week") {
      var wk = new Date(min.getFullYear(), min.getMonth(), min.getDate());
      wk = addDays(wk, -(wk.getDay() || 7) + 1); // Monday
      while (wk <= max) { cols.push({ start: wk, end: addDays(wk, 6), width: z.width }); wk = addDays(wk, 7); }
    } else {
      var m = new Date(min.getFullYear(), min.getMonth(), 1);
      while (m <= max) {
        var end = new Date(m.getFullYear(), m.getMonth() + 1, 0);
        cols.push({ start: m, end: end, width: z.width });
        m = new Date(m.getFullYear(), m.getMonth() + 1, 1);
      }
    }
    var x = 0;
    cols.forEach(function (c) {
      c.x = x;
      x += c.width;
    });
    var topIdx = 0;
    cols.forEach(function (c) {
      var d = c.start;
      if (z.per === "day" || z.per === "week") {
        c.labelTop = d.toLocaleString("en-US", { month: "short", year: "numeric" });
        c.labelBot = z.per === "day"
          ? d.getDate() + "\n" + d.toLocaleDateString("en-US", { weekday: "narrow" })
          : "W" + weekNum(d) + "\n" + d.getDate() + "/" + (d.getMonth() + 1);
      } else {
        c.labelTop = String(d.getFullYear());
        c.labelBot = d.toLocaleDateString("en-US", { month: "short" }) + " " + d.getFullYear();
      }
    });
    layout = {
      min: min, max: max, cols: cols, today: today, width: x,
      pxPerDay: cols.length ? (x / (dayDiff(max, min) + 1)) : 10,
    };
  }

  function weekNum(d) {
    var onejan = new Date(d.getFullYear(), 0, 1);
    return Math.ceil(((d - onejan) / 86400000 + onejan.getDay() + 1) / 7);
  }

  function colAtDate(d) {
    var cols = layout.cols;
    var lo = 0, hi = cols.length - 1;
    while (lo <= hi) {
      var mid = (lo + hi) >> 1;
      if (d >= cols[mid].start && d <= cols[mid].end) return mid;
      if (d < cols[mid].start) hi = mid - 1;
      else lo = mid + 1;
    }
    return lo < 0 ? 0 : (lo >= cols.length ? cols.length - 1 : lo);
  }

  function xOf(d) {
    if (!d) return 0;
    var c = colsAt(d);
    if (!c) return 0;
    var span = dayDiff(c.end, c.start) + 1;
    var extra = (dayDiff(d, c.start) / span) * c.width;
    return c.x + extra;
  }
  function colsAt(d) { return layout.cols[colAtDate(d)]; }

  /* ---------------- visible rows ---------------- */
  function visibleTasks() {
    var out = [];
    var byParent = {};
    DATA.tasks.forEach(function (t) { (byParent[t.parent_id || ""] = byParent[t.parent_id || ""] || []).push(t); });
    var s = STATE.search.trim().toLowerCase();

    function matches(t) {
      if (!s) return true;
      return (t.name || "").toLowerCase().indexOf(s) >= 0 ||
        (t.wbs_code || "").toLowerCase().indexOf(s) >= 0 ||
        (t.owner_name || "").toLowerCase().indexOf(s) >= 0;
    }

    function walk(t, force) {
      var children = byParent[t.id] || [];
      var hasKids = children.length > 0;
      if (matches(t) || force) out.push(t);
      var expanded = STATE.expanded[t.id] === undefined ? true : STATE.expanded[t.id];
      if (hasKids && (expanded || s)) children.forEach(function (c) { walk(c, matches(t) || force); });
      else if (hasKids && !expanded && (matches(t) || force)) {
        out[out.length - 1]._hiddenChildren = children.length;
      }
    }
    (byParent[""] || []).forEach(function (t) { walk(t, false); });
    return out;
  }

  /* ---------------- render ---------------- */
  function render() {
    buildLayout();
    renderHeader();
    renderRows();
    renderStripes();
    renderToday();
    renderLinks();
  }

  function renderHeader() {
    els.header.innerHTML = "";
    var top = document.createElement("div");
    top.className = "gantt-header-row top";
    var bot = document.createElement("div");
    bot.className = "gantt-header-row bottom";
    var prevTop = "";
    var prevName = "";
    layout.cols.forEach(function (c) {
      if (c.labelTop !== prevTop) {
        var cell = document.createElement("div");
        cell.className = "gantt-header-cell";
        cell.style.left = c.x + "px";
        cell.style.width = (c.end <= layout.max ? xOf(addDays(c.end, 1)) : layout.width) - c.x + "px";
        cell.style.background = "#f1f5f9";
        cell.style.fontWeight = "600";
        cell.textContent = c.labelTop;
        top.appendChild(cell);
        prevTop = c.labelTop;
      }
      var b = document.createElement("div");
      b.className = "gantt-header-cell";
      b.style.left = c.x + "px";
      b.style.width = c.width + "px";
      var t = c.labelBot.split("\n");
      var strong = document.createElement("div");
      strong.style.lineHeight = "1.1";
      strong.innerHTML = "<strong>" + t[0] + "</strong>";
      b.appendChild(strong);
      if (t[1]) { var sub = document.createElement("div"); sub.textContent = t[1]; sub.style.fontSize = ".6rem"; b.appendChild(sub); }
      if (!isWorking(c.start)) b.classList.add("weekend");
      if (sameDay(c.start, layout.today) || (c.start <= layout.today && c.end >= layout.today)) b.classList.add("today");
      bot.appendChild(b);
      prevName = c.labelTop;
    });
    els.header.appendChild(top);
    els.header.appendChild(bot);
    els.header.style.width = layout.width + "px";
  }

  function renderRows() {
    var tasks = visibleTasks();
    els.rows.innerHTML = "";
    els.tableBody.innerHTML = "";
    var rowH = 32;
    var body = els.rows;
    body.style.height = (tasks.length * rowH) + "px";
    var byParent = {};
    DATA.tasks.forEach(function (t) { (byParent[t.parent_id || ""] = byParent[t.parent_id || ""] || []).push(t); });

    function ind(t) {
      var n = 0, x = t.parent_id;
      while (x) { n++; x = (tasksById[x] || {}).parent_id || null; }
      return n;
    }
    tasks.forEach(function (t, i) {
      var top = i * rowH;
      // timeline bar
      var barRow = document.createElement("div");
      barRow.className = "gantt-row-timeline" + (t.id === STATE.selectedId ? " selected" : "");
      barRow.style.position = "absolute";
      barRow.style.top = top + "px";
      barRow.style.left = "0";
      barRow.style.right = "0";
      barRow.dataset.taskId = t.id;
      if (t._hiddenChildren) {
        var ph = document.createElement("div");
        ph.className = "gantt-empty";
        ph.style.top = top + "px";
      }
      body.appendChild(barRow);
      // table row
      var tr = document.createElement("tr");
      if (t.id === STATE.selectedId) tr.className = "selected";
      var hasKids = !!byParent[t.id];
      var indent = ind(t);
      // indent cell
      var td0 = document.createElement("td");
      var toggle = hasKids ? "<span class='gantt-toggle-btn'>" +
        (STATE.expanded[t.id] === false ? "&#9654;" : "&#9660;") + "</span>"
        : "<span class='gantt-toggle-btn'>&nbsp;</span>";
      td0.innerHTML = toggle;
      td0.querySelector(".gantt-toggle-btn").addEventListener("click", function () { toggleExpand(t.id); });
      td0.style.paddingLeft = (6 + indent * 14) + "px";
      tr.appendChild(td0);
      // wbs
      var td1 = document.createElement("td");
      td1.textContent = t.wbs_code;
      tr.appendChild(td1);
      // name
      var td2 = document.createElement("td");
      var span = document.createElement("span");
      span.className = "gantt-row-name";
      if (t.is_summary) span.classList.add("gantt-summary-name");
      if (t.is_milestone) span.classList.add("gantt-milestone-name");
      span.textContent = t.name;
      if (t.is_milestone) span.textContent = "\u25C6 " + t.name;
      td2.appendChild(span);
      if (t.is_critical) { var cp = document.createElement("span"); cp.className = "badge text-bg-danger ms-1"; cp.textContent = "CP"; cp.title = "Critical path"; td2.appendChild(cp); }
      tr.appendChild(td2);
      // owner
      var td3 = document.createElement("td");
      td3.textContent = t.owner_name || "—";
      tr.appendChild(td3);
      // dates
      var tdStart = document.createElement("td");
      tdStart.textContent = t.start_date ? fmt(parse(t.start_date)) : "—";
      tr.appendChild(tdStart);
      var tdEnd = document.createElement("td");
      tdEnd.textContent = t.finish_date ? fmt(parse(t.finish_date)) : "—";
      tr.appendChild(tdEnd);
      // progress
      var tdP = document.createElement("td");
      tdP.style.textAlign = "right";
      tdP.textContent = Math.round(t.percent_complete) + "%";
      tr.appendChild(tdP);
      tr.addEventListener("click", function () { selectTask(t.id); });
      els.tableBody.appendChild(tr);

      // bar
      drawBar(barRow, t);
    });
  }

  function drawBar(row, t) {
    if (!t.start_date) return;
    var start = parse(t.start_date);
    var finish = parse(t.finish_date) || start;
    var x0 = xOf(start);
    var x1 = xOf(addDays(finish, 1));
    var width = Math.max(x1 - x0, t.is_milestone ? 14 : 8);

    // baseline overlay
    if (STATE.showBaseline && t.baseline_start && t.baseline_finish) {
      var b = document.createElement("div");
      b.className = "gantt-baseline-bar";
      var bs = parse(t.baseline_start);
      var bf = parse(t.baseline_finish);
      b.style.left = xOf(bs) + "px";
      b.style.width = (xOf(addDays(bf, 1)) - xOf(bs)) + "px";
      row.appendChild(b);
    }

    var bar = document.createElement("div");
    bar.className = "gantt-bar";
    bar.dataset.taskId = t.id;
    if (t.is_summary) bar.classList.add("summary");
    if (t.is_milestone) bar.classList.add("milestone");
    bar.classList.add(t.status);
    if (t.manual_scheduling) bar.classList.add("manual");
    if (STATE.showCritical && t.is_critical) bar.classList.add("critical");

    if (t.is_milestone) {
      bar.style.left = x0 + "px";
      bar.style.width = "14px";
      bar.style.height = "14px";
      var dia = document.createElement("div");
      dia.className = "gantt-diamond";
      bar.appendChild(dia);
    } else {
      bar.style.left = x0 + "px";
      bar.style.width = width + "px";
      var fill = document.createElement("div");
      fill.className = "gantt-bar-fill";
      fill.style.width = Math.min(100, Math.max(0, t.percent_complete)) + "%";
      bar.appendChild(fill);
      if (DATA.user && DATA.user.can_edit && !t.is_summary) {
        var rH = document.createElement("div");
        rH.className = "gantt-resize-handle right";
        rH.style.cursor = "ew-resize";
        bar.appendChild(rH);
      }
    }
    row.appendChild(bar);

    // interactions
    bar.addEventListener("click", function (e) { e.stopPropagation(); selectTask(t.id); });
    bar.addEventListener("dblclick", function (e) { e.stopPropagation(); openEditor(t.id); });
    if (DATA.user && DATA.user.can_edit && !t.is_summary) {
      installDrag(bar, t, row);
    }
    // summary bars collapse on double click too
    if (t.is_summary) {
      bar.style.cursor = "pointer";
      bar.addEventListener("dblclick", function () { toggleExpand(t.id); });
    }
  }

  function installDrag(bar, t, row) {
    var r = bar.querySelector(".gantt-resize-handle.right");
    var dragging = null;
    var pxPerDay = Math.max(layout.pxPerDay, 2);

    bar.addEventListener("mousedown", function (e) {
      if (e.target === r || e.button !== 0) return;
      e.preventDefault();
      dragging = { type: "move", startX: e.clientX, delta: 0, origLeft: parseFloat(bar.style.left) };
      bar.classList.add("dragging");
      document.addEventListener("mousemove", onMove);
      document.addEventListener("mouseup", onUp);
    });
    if (r) {
      r.addEventListener("mousedown", function (e) {
        e.stopPropagation();
        e.preventDefault();
        dragging = { type: "resize", startX: e.clientX, delta: 0, origWidth: parseFloat(bar.style.width), origLeft: parseFloat(bar.style.left) };
        bar.classList.add("dragging");
        document.addEventListener("mousemove", onMove);
        document.addEventListener("mouseup", onUp);
      });
    }
    function onMove(e) {
      if (!dragging) return;
      var dx = Math.round((e.clientX - dragging.startX));
      var days = Math.round(dx / pxPerDay);
      if (dragging.type === "move") {
        bar.style.left = (dragging.origLeft + days * pxPerDay) + "px";
      } else {
        var w = dragging.origWidth + dx;
        if (w >= pxPerDay) { bar.style.width = w + "px"; }
      }
      dragging.days = days;
    }
    function onUp() {
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
      bar.classList.remove("dragging");
      if (!dragging) return;
      var action = dragging.type;
      var days = dragging.days || 0;
      dragging = null;
      if (action === "move" && days !== 0) {
        api("/api/project-tasks/" + t.id + "/move/", "POST", { days: days })
          .then(reload).catch(function (err) { toast(err.message, false); reload(); });
      } else if (action === "resize" && days !== 0 && t.start_date && t.finish_date) {
        var finish = addDays(parse(t.finish_date), days);
        api("/api/project-tasks/" + t.id + "/resize/", "POST", { finish_date: iso(finish) })
          .then(reload).catch(function (err) { toast(err.message, false); reload(); });
      }
    }
  }

  /* ---------------- overlay layers ---------------- */
  function renderStripes() {
    els.stripes.innerHTML = "";
    var z = ZOOMS[STATE.zoom];
    if (z.per !== "day") return;
    layout.cols.forEach(function (c) {
      if (isWorking(c.start)) return;
      var d = document.createElement("div");
      d.className = "gantt-body-col weekend";
      d.style.left = c.x + "px";
      d.style.width = c.width + "px";
      els.stripes.appendChild(d);
    });
  }

  function renderToday() {
    els.today.style.left = xOf(layout.today) + "px";
    els.todayLabel.style.left = (xOf(layout.today) + 4) + "px";
  }

  function renderLinks() {
    els.links.innerHTML = "";
    if (!STATE.showLinks) return;
    var svg = els.links;
    var H = 32;
    svg.setAttribute("width", layout.width);
    svg.setAttribute("height", visibleTasks().length * H + 40);
    var idx = {};
    DATA.tasks.forEach(function (t, i) { idx[t.id] = i; });

    function rowTop(id) {
      var tasks = visibleTasks();
      for (var i = 0; i < tasks.length; i++) if (tasks[i].id === id) return i * H + H / 2;
      return -1;
    }
    var seen = {};
    DATA.dependencies.forEach(function (dep) {
      if (seen[dep.id]) return;
      seen[dep.id] = true;
      var p = DATA.tasks[idx[dep.predecessor]];
      var s = DATA.tasks[idx[dep.successor]];
      if (!p || !s || !p.start_date || !s.start_date) return;
      var y1 = rowTop(p.id);
      var y2 = rowTop(s.id);
      if (y1 < 0 || y2 < 0) return;
      var x1, x2;
      var ps = parse(p.start_date), pf = parse(p.finish_date) || ps;
      var ss = parse(s.start_date), sf = parse(s.finish_date) || ss;
      var dir = p.id !== s.id && idx[p.id] > idx[s.id] ? -1 : 1;
      switch (dep.dependency_type) {
        case "FS": x1 = xOf(addDays(pf, 1)); x2 = xOf(ss); break;
        case "SS": x1 = xOf(ps); x2 = xOf(ss); break;
        case "FF": x1 = xOf(addDays(pf, 1)); x2 = xOf(addDays(sf, 1)); break;
        default: x1 = xOf(ps); x2 = xOf(addDays(sf, 1));
      }
      if (dep.lag_days) x1 = xOf(addDays(pf, Number(dep.lag_days) + 1));
      var path = document.createElementNS("http://www.w3.org/2000/svg", "path");
      var mx = (x1 + x2) / 2;
      var dStr = "M " + x1 + " " + y1 + " L " + mx + " " + y1 + " L " + mx + " " + y2 + " L " + (x2 - (p.id === s.id ? 0 : (x2 > x1 ? 0 : 0))) + " " + y2;
      path.setAttribute("d", dStr);
      path.setAttribute("class", "gantt-link");
      path.setAttribute("stroke-dasharray", "1 0");
      svg.appendChild(path);
      var arrow = arrowPath(x2, y2);
      var a = document.createElementNS("http://www.w3.org/2000/svg", "path");
      a.setAttribute("d", arrow.d);
      a.setAttribute("class", "gantt-link arrow");
      a.setAttribute("transform", arrow.t);
      svg.appendChild(a);
    });
  }
  var DataRef = null;

  function arrowPath(x, y) {
    return { d: "M -4 -3 L 0 0 L -4 3 Z", t: "translate(" + x + "," + y + ")" };
  }

  /* ---------------- selection & detail ---------------- */
  function selectTask(id) {
    STATE.selectedId = id;
    render();
    loadDetail(id);
  }

  function loadDetail(id) {
    var panel = new bootstrap.Offcanvas(document.getElementById("taskDetailPanel"));
    els.detailBody.innerHTML = "<div class=\"text-muted py-4 text-center\"><i class=\"bi bi-arrow-clockwise\"></i> Loading…</div>";
    api("/api/project-tasks/" + id + "/").then(function (t) {
      panel.show();
      var canEdit = DATA.user.can_edit;
      var statOptions = [
        ["planning", "Planning"], ["not_started", "Not Started"], ["in_progress", "In Progress"],
        ["on_hold", "On Hold"], ["blocked", "Blocked"], ["delayed", "Delayed"], ["completed", "Completed"],
      ];
      els.detailTitle.textContent = t.wbs_code + " " + t.name;
      var html = "";
      html += "<dl class=\"row gantt-detail-meta mb-2\">";
      html += "<dt class=\"col-5\">Status</dt><dd class=\"col-7\"><select class='form-select form-select-sm' data-action='status' " + (canEdit ? "" : "disabled") + ">";
      statOptions.forEach(function (o) { html += "<option value='" + o[0] + "'" + (t.status === o[0] ? " selected" : "") + ">" + o[1] + "</option>"; });
      html += "</select></dd>";
      html += "<dt class=\"col-5\">Type</dt><dd class=\"col-7\">" + (t.type_label || t.task_type) + "</dd>";
      html += "<dt class=\"col-5\">Owner</dt><dd class=\"col-7\">" + (t.owner_name || "Unassigned") + "</dd>";
      html += "<dt class=\"col-5\">Start</dt><dd class=\"col-7\">" + fmt(parse(t.start_date)) + "</dd>";
      html += "<dt class=\"col-5\">Finish</dt><dd class=\"col-7\">" + fmt(parse(t.finish_date)) + "</dd>";
      html += "<dt class=\"col-5\">Duration</dt><dd class=\"col-7\">" + (t.duration_days === null || t.duration_days === undefined ? "—" : t.duration_days + " working days") + "</dd>";
      html += "<dt class=\"col-5\">Baseline</dt><dd class=\"col-7\">" + fmt(parse(t.baseline_start)) + " → " + fmt(parse(t.baseline_finish)) + "</dd>";
      html += "<dt class=\"col-5\">Critical</dt><dd class=\"col-7\">" + (t.is_critical ? "<span class='text-danger fw-semibold'>Yes</span>" : "No") + "</dd>";
      html += "<dt class=\"col-5\">Manual</dt><dd class=\"col-7\">" + (t.manual_scheduling ? "Yes" : "No") + "</dd>";
      html += "</dl>";
      html += "<label class='form-label small'>Progress</label>";
      html += "<div class='input-group input-group-sm mb-3'><input type='number' class='form-control' data-action='progress' min='0' max='100' value='" + Math.round(t.percent_complete) + "' " + (canEdit && !t.is_summary ? "" : "disabled") + "><button class='btn btn-outline-primary' data-action='saveProgress'>Set</button></div>";
      html += "<h6 class='small text-uppercase text-muted'>Dependencies</h6>";
      html += "<ul class='list-group list-group-flush mb-3' id='depList'>";
      if (t.is_summary) {
        html += "<li class='list-group-item small text-muted px-0'>Progress and dates roll up from children.</li>";
      } else {
        html += "<li class='list-group-item small text-muted px-0'>Drag bars on the chart to re-schedule; links propagate.</li>";
      }
      html += "</ul>";
      if (canEdit && !t.is_summary) {
        html += "<button class='btn btn-sm btn-outline-secondary w-100 mb-3' data-action='link'><i class='bi bi-diagram-3 me-1'></i>Link successor…</button>";
      }
      html += "<h6 class='small text-uppercase text-muted'>Comments</h6>";
      html += "<div id='commentList' class='mb-2'></div>";
      if (canEdit) {
        html += "<div class='input-group input-group-sm mb-3'><input class='form-control' id='commentInput' placeholder='Add comment…'><button class='btn btn-outline-primary' data-action='comment'>Post</button></div>";
      }
      if (canEdit) {
        html += "<hr>";
        html += "<button class='btn btn-sm btn-outline-secondary w-100 mb-2' data-action='edit'><i class='bi bi-pencil me-1'></i>Edit task</button>";
        html += "<button class='btn btn-sm btn-outline-danger w-100' data-action='delete'><i class='bi bi-trash me-1'></i>Delete task</button>";
      }
      els.detailBody.innerHTML = html;
      els.detailBody.querySelectorAll("[data-action=status]").forEach(function (sel) {
        sel.addEventListener("change", function () {
          api("/api/project-tasks/" + t.id + "/", "PATCH", { status: sel.value }).then(reload).catch(function (e) { toast(e.message, false); });
        });
      });
      var progInput = els.detailBody.querySelector("[data-action=progress]");
      if (progInput) {
        els.detailBody.querySelector("[data-action=saveProgress]").addEventListener("click", function () {
          api("/api/project-tasks/" + t.id + "/progress/", "POST", { percent_complete: Number(progInput.value) }).then(reload).catch(function (e) { toast(e.message, false); });
        });
      }
      var editBtn = els.detailBody.querySelector("[data-action=edit]");
      if (editBtn) editBtn.addEventListener("click", function () { openEditor(t.id); });
      var delBtn = els.detailBody.querySelector("[data-action=delete]");
      if (delBtn) delBtn.addEventListener("click", function () { deleteTask(t.id); });
      var linkBtn = els.detailBody.querySelector("[data-action=link]");
      if (linkBtn) linkBtn.addEventListener("click", function () { openDepModal(t.id); });
      var ctx = els.detailBody.querySelector("[data-action=comment]");
      if (ctx) {
        ctx.addEventListener("click", function () {
          var body = (els.detailBody.querySelector("#commentInput").value || "").trim();
          if (!body) return;
          api("/api/project-tasks/" + t.id + "/comments/", "POST", { body: body }).then(function () { loadDetail(t.id); }).catch(function (e) { toast(e.message, false); });
        });
      }
      loadDeps(t);
      loadComments(t);
    }).catch(function (err) { toast(err.message, false); });
  }

  function loadDeps(t) {
    api("/api/project-tasks/" + t.id + "/dependencies/").then(function (deps) {
      var list = document.getElementById("depList");
      if (!list) return;
      list.innerHTML = "";
      var byId = {};
      DATA.tasks.forEach(function (k) { byId[k.id] = k; });
      deps.forEach(function (dep) {
        var succ = byId[dep.successor];
        var li = document.createElement("li");
        li.className = "list-group-item small px-0 d-flex justify-content-between align-items-center";
        li.innerHTML = "<span>" + dep.dependency_type + " → " + (succ ? succ.name : "?") + (dep.lag_days ? " (+" + dep.lag_days + "d)" : "") + "</span>";
        if (DATA.user.can_edit) {
          var rm = document.createElement("button");
          rm.className = "btn btn-sm btn-link text-danger text-decoration-none p-0";
          rm.innerHTML = "<i class='bi bi-x-circle'></i>";
          rm.title = "Remove link";
          rm.addEventListener("click", function () {
            api("/api/dependencies/" + dep.id + "/", "DELETE").then(reload).catch(function (e) { toast(e.message, false); });
          });
          li.appendChild(rm);
        }
        list.appendChild(li);
      });
      if (!deps.length) {
        list.innerHTML = "<li class='list-group-item small text-muted px-0'>No successors linked.</li>";
      }
    });
  }

  function loadComments(t) {
    api("/api/project-tasks/" + t.id + "/comments/").then(function (comments) {
      var el = document.getElementById("commentList");
      if (!el) return;
      el.innerHTML = "";
      comments.forEach(function (c) {
        var w = document.createElement("div");
        w.className = "border-bottom small py-1";
        w.innerHTML = "<strong>" + (c.author_name || "system") + "</strong> <span class='text-muted'>" + (c.created_at || "").replace("T", " ").slice(0, 16) + "</span><div>" + c.body + "</div>";
        el.appendChild(w);
      });
      if (!comments.length) el.innerHTML = "<div class='text-muted small'>No comments.</div>";
    });
  }

  function deleteTask(id) {
    if (!confirm("Delete this task? Its links will be removed.")) return;
    api("/api/project-tasks/" + id + "/", "DELETE").then(function () {
      STATE.selectedId = null;
      reload();
    }).catch(function (e) { toast(e.message, false); });
  }

  function toggleExpand(id) {
    if (STATE.expanded[id] === undefined) STATE.expanded[id] = false;
    else STATE.expanded[id] = !STATE.expanded[id];
    render();
  }

  /* ---------------- editor ---------------- */
  function openEditor(id) {
    var modalEl = document.getElementById("taskEditorModal");
    var modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    var form = document.getElementById("taskEditorForm");
    form.reset();
    document.getElementById("taskEditorError").textContent = "";
    var t = id ? tasksById[id] : null;
    document.getElementById("taskEditorTitle").textContent = t ? ("Edit " + (t.wbs_code || "") + " " + t.name) : "New task";
    populateEditorSelects(form, t);
    if (t) {
      form.querySelector("[name=id]").value = t.id;
      form.querySelector("[name=name]").value = t.name;
      form.querySelector("[name=description]").value = t.description || "";
      form.querySelector("[name=task_type]").value = t.task_type;
      form.querySelector("[name=status]").value = t.status;
      form.querySelector("[name=priority]").value = t.priority;
      if (t.owner_id) form.querySelector("[name=owner]").value = t.owner_id;
      if (t.parent_id) form.querySelector("[name=parent]").value = t.parent_id;
      form.querySelector("[name=manual_scheduling]").value = String(t.manual_scheduling);
      form.querySelector("[name=start_date]").value = t.start_date || "";
      form.querySelector("[name=finish_date]").value = t.finish_date || "";
      form.querySelector("[name=duration_days]").value = t.duration_days === null || t.duration_days === undefined ? "" : t.duration_days;
      form.querySelector("[name=percent_complete]").value = t.percent_complete;
    } else {
      if (STATE.selectedId) {
        var sel = tasksById[STATE.selectedId];
        if (sel && !sel.is_milestone) form.querySelector("[name=parent]").value = sel.id;
      }
    }
    modal.show();
  }

  function populateEditorSelects(form, t) {
    var owners = {}, parents = [];
    DATA.tasks.forEach(function (task) {
      if (task.owner_id) owners[task.owner_id] = task.owner_name || task.owner_id;
      if (!task.is_milestone && task.id !== (t ? t.id : null)) {
        parents.push(task);
      }
    });
    var ownerSel = form.querySelector("[name=owner]");
    ownerSel.innerHTML = "<option value=''>Unassigned</option>";
    Object.keys(owners).forEach(function (uid) {
      ownerSel.appendChild(new Option(owners[uid], uid));
    });
    var parentSel = form.querySelector("[name=parent]");
    parentSel.innerHTML = "<option value=''>(None)</option>";
    parents.forEach(function (p) {
      if (t && taskIsSelfOrDescendant(p.id, t.id)) return;
      parentSel.appendChild(new Option(p.wbs_code + " " + p.name, p.id));
    });
  }

  function taskIsSelfOrDescendant(candidateId, rootId) {
    var x = candidateId;
    while (x) {
      if (x === rootId) return true;
      x = (tasksById[x] || {}).parent_id || null;
    }
    return false;
  }

  function initEditor() {
    var saveBtn = document.getElementById("taskEditorSave");
    saveBtn.addEventListener("click", function () {
      var form = document.getElementById("taskEditorForm");
      var id = form.querySelector("[name=id]").value;
      var payload = {};
      ["name", "description", "task_type", "status", "priority", "owner", "parent",
        "start_date", "finish_date", "duration_days", "percent_complete", "manual_scheduling"].forEach(function (k) {
        var v = form.querySelector("[name=" + k + "]").value;
        if (k === "parent" && v === "") v = null;
        if (k === "owner" && v === "") v = null;
        payload[k] = v;
      });
      payload.percent_complete = Number(payload.percent_complete || 0);
      if (payload.duration_days !== "") payload.duration_days = Number(payload.duration_days);
      else delete payload.duration_days;
      if (payload.task_type === "milestone") { payload.start_date = payload.start_date || null; payload.finish_date = payload.start_date; }
      if (payload.task_type === "milestone") payload.duration_days = 0;
      var url = "/api/project-tasks/";
      var method = "POST";
      if (id) { url = "/api/project-tasks/" + id + "/"; method = "PATCH"; }
      api(url, method, payload).then(function () {
        bootstrap.Modal.getOrCreateInstance(document.getElementById("taskEditorModal")).hide();
        reload();
      }).catch(function (e) {
        document.getElementById("taskEditorError").textContent = e.message;
      });
    });
  }

  /* ---------------- dependency modal ---------------- */
  function openDepModal(predecessorId) {
    var modal = new bootstrap.Modal(document.getElementById("depModal"));
    var p = tasksById[predecessorId];
    document.getElementById("depFromName").textContent = p ? (p.wbs_code + " " + p.name) : "";
    var sel = document.getElementById("depTo");
    sel.innerHTML = "<option value=''>Select task...</option>";
    DATA.tasks.forEach(function (t) {
      if (t.id !== predecessorId && !t.is_summary) {
        var opt = document.createElement("option");
        opt.value = t.id;
        opt.textContent = t.wbs_code + " " + t.name;
        sel.appendChild(opt);
      }
    });
    document.getElementById("depError").textContent = "";
    document.getElementById("depSave").onclick = function () {
      var succ = sel.value;
      if (!succ) { document.getElementById("depError").textContent = "Choose a task."; return; }
      api("/api/project-tasks/" + predecessorId + "/dependencies/", "POST", {
        successor: succ,
        dependency_type: document.getElementById("depType").value,
        lag_days: Number(document.getElementById("depLag").value || 0),
      }).then(function () {
        modal.hide();
        reload();
      }).catch(function (e) {
        document.getElementById("depError").textContent = e.message;
      });
    };
    modal.show();
  }

  /* ---------------- project actions ---------------- */
  function initToolbar() {
    document.getElementById("ganttToday").addEventListener("click", function () {
      els.timelineBody.scrollLeft = Math.max(0, xOf(layout.today) - 120);
      els.tableBody.scrollTop = 0;
    });
    document.querySelectorAll("#ganttZoomGroup [data-zoom]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        document.querySelectorAll("#ganttZoomGroup [data-zoom]").forEach(function (b) { b.classList.remove("btn-primary"); b.classList.add("btn-outline-secondary"); });
        btn.classList.remove("btn-outline-secondary");
        btn.classList.add("btn-primary");
        STATE.zoom = btn.getAttribute("data-zoom");
        render();
      });
    });
    document.getElementById("ganttExpandAll").addEventListener("click", function () {
      DATA.tasks.forEach(function (t) { STATE.expanded[t.id] = true; });
      render();
    });
    document.getElementById("ganttCollapseAll").addEventListener("click", function () {
      DATA.tasks.forEach(function (t) { if (!t.is_summary && !t.is_milestone) return; STATE.expanded[t.id] = false; });
      render();
    });
    document.getElementById("ganttToggleCritical").addEventListener("click", function () {
      STATE.showCritical = !STATE.showCritical;
      this.classList.toggle("btn-outline-secondary", !STATE.showCritical);
      this.classList.toggle("btn-primary", STATE.showCritical);
      render();
    });
    document.getElementById("ganttToggleBaseline").addEventListener("click", function () {
      STATE.showBaseline = !STATE.showBaseline;
      this.classList.toggle("btn-outline-secondary", !STATE.showBaseline);
      this.classList.toggle("btn-primary", STATE.showBaseline);
      render();
    });
    document.getElementById("ganttToggleLinks").addEventListener("click", function () {
      STATE.showLinks = !STATE.showLinks;
      this.classList.toggle("btn-outline-secondary", !STATE.showLinks);
      this.classList.toggle("btn-primary", STATE.showLinks);
      render();
    });
    document.getElementById("ganttSearch").addEventListener("input", function (e) {
      STATE.search = e.target.value;
      render();
    });
    var scheduleBtn = document.getElementById("ganttScheduleBtn");
    if (scheduleBtn) scheduleBtn.addEventListener("click", function () {
      scheduleBtn.disabled = true;
      scheduleBtn.innerHTML = "<span class='spinner-border spinner-border-sm me-1'></span>Running…";
      api("/api/projects/" + DATA.project.id + "/schedule/", "POST", {}).then(function () {
        toast("Auto-schedule complete.", true);
        reload();
      }).catch(function (e) {
        toast(e.message, false);
        reload();
      }).then(function () {
        scheduleBtn.disabled = false;
        scheduleBtn.innerHTML = "<i class='bi bi-lightning-charge me-1'></i>Auto Schedule";
      });
    });
    var baseBtn = document.getElementById("ganttBaselineBtn");
    if (baseBtn) baseBtn.addEventListener("click", function () {
      var name = prompt("Baseline name:", "Baseline " + new Date().toISOString().slice(0, 10));
      if (name === null) return;
      api("/api/projects/" + DATA.project.id + "/baseline/", "POST", { name: name || "Baseline" })
        .then(function () { toast("Baseline saved.", true); reload(); })
        .catch(function (e) { toast(e.message, false); });
    });
    var delBtn = document.getElementById("ganttDeleteTaskBtn");
    if (delBtn) delBtn.addEventListener("click", function () {
      if (STATE.selectedId) deleteTask(STATE.selectedId);
    });
    document.getElementById("ganttCreateTaskBtn").addEventListener("click", function () { openEditor(null); });
    document.getElementById("ganttCreateMilestoneBtn").addEventListener("click", function () {
      openEditor(null);
      var form = document.getElementById("taskEditorForm");
      form.querySelector("[name=task_type]").value = "milestone";
    });
    var csvLink = document.getElementById("ganttCsvLink");
    if (csvLink && DATA.project) {
      csvLink.href = "/api/projects/" + DATA.project.id + "/csv/";
    }
  }

  function reload() {
    api("/api/projects/" + DATA.project.id + "/gantt/").then(function (payload) {
      DATA = payload;
      window.PS_PROJECT = payload;
      tasksById = {};
      DATA.tasks.forEach(function (t) { tasksById[t.id] = t; });
      render();
    }).catch(function (e) { toast(e.message, false); });
  }

  function init() {
    if (!DATA) return;
    tasksById = {};
    DATA.tasks.forEach(function (t) { tasksById[t.id] = t; });
    els.header = document.getElementById("ganttTimelineHeader");
    els.rows = document.getElementById("ganttRows");
    els.links = document.getElementById("ganttLinks");
    els.stripes = document.createElement("div");
    els.stripes.className = "gantt-body-col-stripes";
    els.timelineBody_wrapper = document.getElementById("ganttTimelineBody");
    els.timelineBody_wrapper.appendChild(els.stripes);
    els.today = document.createElement("div");
    els.today.className = "gantt-today-line";
    els.todayLabel = document.createElement("div");
    els.todayLabel.className = "gantt-today-label";
    els.todayLabel.textContent = "Today";
    els.timelineBody_wrapper.appendChild(els.today);
    els.timelineBody_wrapper.appendChild(els.todayLabel);
    els.tableBody = document.getElementById("ganttTableBody");
    els.detailBody = document.getElementById("taskDetailBody");
    els.detailTitle = document.getElementById("taskDetailTitle");
    initToolbar();
    initEditor();
    render();
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") { bootstrap.Modal.getOrCreateInstance(document.getElementById("taskEditorModal") ).hide(); }
    });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();