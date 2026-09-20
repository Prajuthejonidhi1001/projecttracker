/* Project Scheduler client-side helpers */
(function () {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    // Sidebar toggle for small screens
    var toggle = document.getElementById("sidebarToggle");
    var sidebar = document.getElementById("sidebar");
    if (toggle && sidebar) {
      toggle.addEventListener("click", function () {
        sidebar.classList.toggle("open");
      });
    }

    // Data-driven confirmation modal. Elements with data-confirm open it and,
    // on confirm, submit the target <form> (data-confirm-form) or follow the URL
    // (data-confirm-href) or submit the nearest form.
    setupConfirmationModal();
    setupReorder(); // no-op unless handles present
  });

  function setupConfirmationModal() {
    var modalEl = document.getElementById("confirmModal");
    if (!modalEl) return;
    var modal = new bootstrap.Modal(modalEl);
    var okBtn = document.getElementById("confirmOk");
    var titleEl = document.getElementById("confirmTitle");
    var bodyEl = document.getElementById("confirmBody");

    document.querySelectorAll("[data-confirm]").forEach(function (trigger) {
      trigger.addEventListener("click", function (e) {
        e.preventDefault();
        titleEl.textContent = trigger.getAttribute("data-confirm-title") || "Are you sure?";
        bodyEl.textContent = trigger.getAttribute("data-confirm-body") || "Proceed with this action?";
        var target = trigger.getAttribute("data-confirm-form") || trigger.getAttribute("data-confirm-href");
        okBtn.onclick = function () {
          modal.hide();
          if (trigger.getAttribute("data-confirm-form")) {
            document.getElementById(trigger.getAttribute("data-confirm-form")).submit();
          } else if (trigger.getAttribute("data-confirm-href")) {
            window.location.href = trigger.getAttribute("data-confirm-href");
          } else {
            var form = trigger.closest("form");
            if (form) form.submit();
          }
        };
        modal.show();
      });
    });
  }

  // Step reordering: table rows carry data-step-id; the whole table is an HTML
  // form (id="reorderForm"). Drag handles are link-buttons; arrows move rows.
  function setupReorder() {
    var form = document.getElementById("reorderForm");
    if (!form) return;

    var move = function (row, dir) {
      var target = dir > 0 ? row.nextElementSibling : row.previousElementSibling;
      if (target) row.parentNode.insertBefore(row, dir > 0 ? target.nextElementSibling : target);
      syncHiddenInputs(form);
    };

    form.querySelectorAll("[data-move]").forEach(function (btn) {
      btn.addEventListener("click", function (e) {
        e.preventDefault();
        var row = btn.closest("tr");
        var dir = parseInt(btn.getAttribute("data-move"), 10);
        move(row, dir);
      });
    });

    form.querySelector("[data-save-order]") &&
      form.querySelector("[data-save-order]").addEventListener("click", function (e) {
        e.preventDefault();
        syncHiddenInputs(form);
        form.submit();
      });

    function syncHiddenInputs(formEl) {
      var container = formEl.querySelector("input[name='step_order']");
      if (!container) return;
      var ids = [];
      formEl.querySelectorAll("tr[data-step-id]").forEach(function (r) {
        ids.push(r.getAttribute("data-step-id"));
      });
      container.value = ids.join(",");
    }
  }
})();