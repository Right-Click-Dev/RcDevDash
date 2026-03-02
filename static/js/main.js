// RcDevDash Main JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    [...tooltipTriggerList].map(el => new bootstrap.Tooltip(el));

    // Auto-dismiss flash alerts after 5 seconds
    document.querySelectorAll('.alert:not(.alert-permanent)').forEach(alert => {
        setTimeout(() => {
            alert.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
            alert.style.opacity = '0';
            alert.style.transform = 'translateY(-8px)';
            setTimeout(() => {
                const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
                bsAlert.close();
            }, 400);
        }, 5000);
    });

    // Task checkbox toggle handler (project detail page)
    document.querySelectorAll('.task-checkbox:not(.lead-task-checkbox):not(.dev-task-checkbox)').forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            const taskId = this.dataset.taskId;
            const taskItem = this.closest('.task-item');

            this.disabled = true;

            fetch(`/api/task/${taskId}/toggle`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    taskItem.classList.toggle('task-completed', data.completed);
                    const taskText = taskItem.querySelector('p');
                    taskText.classList.toggle('text-decoration-line-through', data.completed);
                    taskText.classList.toggle('text-muted', data.completed);
                } else {
                    this.checked = !this.checked;
                    alert('Error updating task: ' + (data.error || 'Unknown error'));
                }
            })
            .catch(() => {
                this.checked = !this.checked;
                alert('Error updating task. Please try again.');
            })
            .finally(() => { this.disabled = false; });
        });
    });

    // Form validation
    document.querySelectorAll('form[data-validate="true"]').forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!form.checkValidity()) {
                e.preventDefault();
                e.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });

    // Confirm delete actions
    document.querySelectorAll('[data-confirm-delete]').forEach(button => {
        button.addEventListener('click', function(e) {
            if (!confirm(this.dataset.confirmDelete || 'Are you sure you want to delete this item?')) {
                e.preventDefault();
            }
        });
    });

    // Auto-focus first input in modals
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('shown.bs.modal', function() {
            const firstInput = this.querySelector('input:not([type="hidden"]), textarea, select');
            if (firstInput) firstInput.focus();
        });
    });

    // Number input validation (prevent negative)
    document.querySelectorAll('input[type="number"]').forEach(input => {
        input.addEventListener('input', function() {
            if (this.value < 0) this.value = 0;
        });
    });

    // Animate progress bars on load
    document.querySelectorAll('.progress-bar').forEach(bar => {
        const targetWidth = bar.style.width;
        bar.style.width = '0%';
        requestAnimationFrame(() => {
            requestAnimationFrame(() => { bar.style.width = targetWidth; });
        });
    });

    // Theme toggle
    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
        const icon = themeToggle.querySelector('i');

        function updateThemeIcon() {
            const dark = document.documentElement.getAttribute('data-theme') === 'dark';
            icon.className = dark ? 'bi bi-sun-fill' : 'bi bi-moon-fill';
        }

        updateThemeIcon();

        themeToggle.addEventListener('click', function() {
            const current = document.documentElement.getAttribute('data-theme');
            const next = current === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', next);
            localStorage.setItem('theme', next);
            updateThemeIcon();
        });
    }
});

// Toast notification utility
function showToast(message, type = 'info') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        container.style.zIndex = '1090';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;

    container.appendChild(toast);
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
    toast.addEventListener('hidden.bs.toast', () => toast.remove());
}
