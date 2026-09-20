/* Project Scheduler — calendar month view. Reads window.PS_CALENDAR. */
(function () {
  "use strict";
  var EVENTS = (window.PS_CALENDAR && window.PS_CALENDAR.events) || [];
  var cursor = new Date(new Date().getFullYear(), new Date().getMonth(), 1);

  function pad(n) { return String(n).padStart(2, "0"); }
  function key(d) { return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate()); }

  function render() {
    var title = document.getElementById("calTitle");
    var grid = document.getElementById("calendarGrid");
    title.textContent = cursor.toLocaleDateString("en-US", { month: "long", year: "numeric" });
    grid.innerHTML = "";
    var days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
    var head = document.createElement("div");
    head.className = "cal-grid mb-2";
    days.forEach(function (d) {
      var c = document.createElement("div");
      c.className = "text-center fw-semibold small";
      c.textContent = d;
      head.appendChild(c);
    });
    grid.appendChild(head);
    var body = document.createElement("div");
    body.className = "cal-grid";
    var startOffset = cursor.getDay();
    var dim = new Date(cursor.getFullYear(), cursor.getMonth() + 1, 0).getDate();
    var prevDim = new Date(cursor.getFullYear(), cursor.getMonth(), 0).getDate();

    for (var i = 0; i < 42; i++) {
      var day;
      var other = false;
      if (i < startOffset) { day = prevDim - startOffset + i + 1; other = true; }
      else if (i - startOffset >= dim) { day = i - startOffset - dim + 1; other = true; }
      else { day = i - startOffset + 1; }
      var dt = other
        ? new Date(cursor.getFullYear(), cursor.getMonth() + (i < startOffset ? -1 : 1), day)
        : new Date(cursor.getFullYear(), cursor.getMonth(), day);
      var cell = document.createElement("div");
      cell.className = "cal-cell" + (other ? " other-month" : "");
      var num = document.createElement("div");
      num.className = "cal-day-num";
      num.textContent = day;
      var today = key(dt) === key(new Date());
      if (today) { num.style.color = "#2563eb"; num.style.fontWeight = "700"; }
      cell.appendChild(num);
      var k = key(dt);
      EVENTS.forEach(function (ev) {
        if (k < (ev.start || "").slice(0, 10) || k > (ev.finish || "").slice(0, 10)) return;
        var a = document.createElement("a");
        a.className = "cal-event " + ev.status;
        a.href = "#";
        a.textContent = (ev.task_type === "milestone" ? "\u25C6 " : "") + ev.name;
        a.title = ev.name;
        a.addEventListener("click", function (e) { e.preventDefault(); });
        cell.appendChild(a);
      });
      body.appendChild(cell);
    }
    grid.appendChild(body);
  }

  document.getElementById("calPrev").addEventListener("click", function () {
    cursor = new Date(cursor.getFullYear(), cursor.getMonth() - 1, 1);
    render();
  });
  document.getElementById("calNext").addEventListener("click", function () {
    cursor = new Date(cursor.getFullYear(), cursor.getMonth() + 1, 1);
    render();
  });
  document.getElementById("calToday").addEventListener("click", function () {
    cursor = new Date(new Date().getFullYear(), new Date().getMonth(), 1);
    render();
  });

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", render);
  else render();
})();