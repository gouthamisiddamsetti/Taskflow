/**
 * Taskflow Interactive Frontend Logic
 * Team 1: Frontend UI/UX
 */

document.addEventListener('DOMContentLoaded', () => {
    setupModals();
});

function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('active');
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('active');
    }
}

function setupModals() {
    // Close modal on backdrop click
    document.querySelectorAll('.modal-overlay').forEach(overlay => {
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                overlay.classList.remove('active');
            }
        });
    });
}

// Quick status updater for employee and lead boards
async function updateTaskStatus(taskId, newStatus) {
    try {
        const response = await fetch(`/api/tasks/${taskId}/status`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: newStatus })
        });
        const data = await response.json();
        if (response.ok) {
            window.location.reload();
        } else {
            alert(data.error || 'Failed to update status');
        }
    } catch (err) {
        console.error('Error updating status:', err);
    }
}

// Open Blocker Modal
function triggerBlockerModal(taskId, taskCode) {
    document.getElementById('blockerTaskId').value = taskId;
    document.getElementById('blockerTaskCode').innerText = taskCode;
    openModal('blockerModal');
}

// Submit Blocker Form
async function submitBlocker(event) {
    event.preventDefault();
    const taskId = document.getElementById('blockerTaskId').value;
    const reason = document.getElementById('blockerReason').value;

    try {
        const response = await fetch(`/api/tasks/${taskId}/blocker`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ blocker_reason: reason })
        });
        if (response.ok) {
            closeModal('blockerModal');
            window.location.reload();
        } else {
            const data = await response.json();
            alert(data.error || 'Failed to report blocker');
        }
    } catch (err) {
        console.error('Error reporting blocker:', err);
    }
}

// Open Review / Signoff Modal
function triggerReviewModal(taskId, taskCode, isLead) {
    document.getElementById('reviewTaskId').value = taskId;
    document.getElementById('reviewTaskCode').innerText = taskCode;
    openModal('reviewModal');
}

// Submit Review Action (Submit, Approve, Reject)
async function submitReviewAction(action) {
    const taskId = document.getElementById('reviewTaskId').value;
    const notes = document.getElementById('reviewNotes').value;

    try {
        const response = await fetch(`/api/tasks/${taskId}/review`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: action, notes: notes })
        });
        if (response.ok) {
            closeModal('reviewModal');
            window.location.reload();
        } else {
            const data = await response.json();
            alert(data.error || 'Failed to process review');
        }
    } catch (err) {
        console.error('Error processing review:', err);
    }
}

// Submit New Task (Lead delegation)
async function submitCreateTask(event) {
    event.preventDefault();
    const form = document.getElementById('createTaskForm');
    const submitButton = document.getElementById('createTaskSubmitButton');
    const errorBox = document.getElementById('createTaskError');
    const formData = new FormData(form);
    const payload = Object.fromEntries(formData.entries());
    errorBox.hidden = true;
    errorBox.textContent = '';
    submitButton.disabled = true;
    submitButton.textContent = 'Assigning...';

    try {
        const response = await fetch('/api/tasks', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (response.ok) {
            closeModal('createTaskModal');
            window.location.reload();
        } else {
            const data = await response.json();
            errorBox.textContent = data.error || 'Failed to assign task.';
            errorBox.hidden = false;
        }
    } catch (error) {
        errorBox.textContent = 'Unable to assign task right now. Check your connection and try again.';
        errorBox.hidden = false;
    } finally {
        submitButton.disabled = false;
        submitButton.textContent = 'Assign Work';
    }
}
