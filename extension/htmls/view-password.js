const viewUrl = document.getElementById('view-url');
const viewEmail = document.getElementById('view-email');
const viewPassword = document.getElementById('view-password');
const viewComentario = document.getElementById('view-comentario');
const viewAutologin = document.getElementById('view-autologin');
const deleteBtn = document.getElementById('deleteBtn');
const backBtn = document.getElementById('backBtn');
const confirmModal = document.getElementById('confirmModal');
const cancelBtn = document.getElementById('cancelBtn');
const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');

let currentPasswordId = null;

// Back button
backBtn.addEventListener('click', () => {
    window.location.href = './popup.html';
});

// Check if logged in
browser.storage.local.get(['authToken'], (result) => {
    if (!result.authToken) {
        window.location.href = './login.html';
    }
});

// Load password details
async function cargarDetalles() {
    try {
        const result = await new Promise((resolve) => {
            browser.storage.local.get(['selectedLoginId', 'authToken'], resolve);
        });
        
        if (!result.selectedLoginId || !result.authToken) {
            window.location.href = './popup.html';
            return;
        }

        currentPasswordId = result.selectedLoginId;

        const response = await fetch(
            `https://ragnarok-uegm.onrender.com/passwords/${result.selectedLoginId}`,
            {
                headers: {
                    'Authorization': `Bearer ${result.authToken}`
                }
            }
        );

        if (response.ok) {
            const password = await response.json();
            viewUrl.textContent = password.url || '-';
            viewEmail.textContent = password.email || '-';
            viewPassword.textContent = password.password || '-';
            viewComentario.textContent = password.comentario || '-';
            viewAutologin.checked = password.autologin || false;
        } else {
            window.location.href = './popup.html';
        }
    } catch (error) {
        console.error('Error cargando detalles:', error);
        window.location.href = './popup.html';
    }
}

// Show confirmation modal
deleteBtn.addEventListener('click', () => {
    confirmModal.classList.add('show');
});

// Cancel deletion
cancelBtn.addEventListener('click', () => {
    confirmModal.classList.remove('show');
});

// Close modal when clicking outside
confirmModal.addEventListener('click', (e) => {
    if (e.target === confirmModal) {
        confirmModal.classList.remove('show');
    }
});

// Confirm deletion
confirmDeleteBtn.addEventListener('click', async () => {
    try {
        const result = await new Promise((resolve) => {
            browser.storage.local.get(['authToken'], resolve);
        });

        const response = await fetch(
            `https://ragnarok-uegm.onrender.com/passwords/${currentPasswordId}`,
            {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${result.authToken}`
                }
            }
        );

        if (response.ok) {
            window.location.href = './popup.html';
        }
    } catch (error) {
        console.error('Error eliminando:', error);
    }
});

cargarDetalles();
