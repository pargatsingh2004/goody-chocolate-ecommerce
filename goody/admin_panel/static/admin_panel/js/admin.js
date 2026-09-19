// Small shared behaviours for the custom admin panel.
document.addEventListener('DOMContentLoaded', function () {

  // Mobile sidebar toggle
  var toggleBtn = document.getElementById('sidebarToggle');
  var sidebar = document.querySelector('.admin-sidebar');
  if (toggleBtn && sidebar) {
    toggleBtn.addEventListener('click', function () {
      sidebar.classList.toggle('show');
    });
  }

  // Confirmation modal before delete — any element with data-confirm-delete
  // triggers the shared #confirmDeleteModal and submits the linked form.
  var confirmModalEl = document.getElementById('confirmDeleteModal');
  var pendingForm = null;

  document.querySelectorAll('[data-confirm-delete]').forEach(function (el) {
    el.addEventListener('click', function (e) {
      e.preventDefault();
      pendingForm = el.closest('form') || document.getElementById(el.getAttribute('data-form-id'));
      var label = el.getAttribute('data-confirm-delete') || 'this item';
      var bodyEl = document.getElementById('confirmDeleteBody');
      if (bodyEl) {
        bodyEl.textContent = 'Are you sure you want to delete ' + label + '? This action cannot be undone.';
      }
      if (window.bootstrap && confirmModalEl) {
        var modal = bootstrap.Modal.getOrCreateInstance(confirmModalEl);
        modal.show();
      } else if (pendingForm) {
        pendingForm.submit();
      }
    });
  });

  var confirmBtn = document.getElementById('confirmDeleteBtn');
  if (confirmBtn) {
    confirmBtn.addEventListener('click', function () {
      if (pendingForm) pendingForm.submit();
    });
  }

  // Auto-submit filter forms when a select changes
  document.querySelectorAll('[data-auto-submit]').forEach(function (el) {
    el.addEventListener('change', function () {
      el.closest('form').submit();
    });
  });
});
