const viewUrl = document.getElementById('view-url');
const viewEmail = document.getElementById('view-email');
const viewPassword = document.getElementById('view-password');
const passwordText = document.getElementById('password-text');
const togglePasswordBtn = document.getElementById('togglePasswordBtn');
const viewComentario = document.getElementById('view-comentario');
const viewAutologin = document.getElementById('view-autologin');
const deleteBtn = document.getElementById('deleteBtn');
const changePasswordBtn = document.getElementById('changePasswordBtn');
const backBtn = document.getElementById('backBtn');
const confirmModal = document.getElementById('confirmModal');
const changePasswordModal = document.getElementById('changePasswordModal');
const cancelBtn = document.getElementById('cancelBtn');
const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');
const cancelChangeBtn = document.getElementById('cancelChangeBtn');
const confirmChangeBtn = document.getElementById('confirmChangeBtn');
const currentPassword = document.getElementById('currentPassword');
const newPassword = document.getElementById('newPassword');
const confirmNewPassword = document.getElementById('confirmNewPassword');

let currentPasswordId = null;
let currentEmail = null;
let currentPasswordValue = null;
let passwordVisible = false;

// Back button
backBtn.addEventListener('click', () => {
    window.location.href = './popup.html';
});

// Toggle password visibility
togglePasswordBtn.addEventListener('click', () => {
    passwordVisible = !passwordVisible;
    if (passwordVisible) {
        passwordText.textContent = currentPasswordValue || '-';
        togglePasswordBtn.textContent = '👁️‍🗨️';
    } else {
        passwordText.textContent = '•'.repeat((currentPasswordValue || '-').length);
        togglePasswordBtn.textContent = '👁️';
    }
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
            currentEmail = password.email;
            currentPasswordValue = password.password || '-';
            // Show password as dots initially
            passwordText.textContent = '•'.repeat(currentPasswordValue.length);
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

changePasswordModal.addEventListener('click', (e) => {
    if (e.target === changePasswordModal) {
        changePasswordModal.classList.remove('show');
    }
});

// Show change password modal
changePasswordBtn.addEventListener('click', () => {
    currentPassword.value = '';
    newPassword.value = '';
    confirmNewPassword.value = '';
    changePasswordModal.classList.add('show');
});

// Cancel change password
cancelChangeBtn.addEventListener('click', () => {
    changePasswordModal.classList.remove('show');
});

// Confirm change password
confirmChangeBtn.addEventListener('click', async () => {
    const current = currentPassword.value;
    const newPwd = newPassword.value;
    const confirmPwd = confirmNewPassword.value;

    if (!current || !newPwd || !confirmPwd) {
        return;
    }

    if (newPwd !== confirmPwd) {
        return;
    }

    if (newPwd.length < 6) {
        return;
    }

    try {
        const result = await new Promise((resolve) => {
            browser.storage.local.get(['authToken'], resolve);
        });

        const response = await fetch(
            `https://ragnarok-uegm.onrender.com/users/${currentEmail}/change-password`,
            {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${result.authToken}`
                },
                body: JSON.stringify({
                    password_actual: current,
                    password_nueva: newPwd
                })
            }
        );

        if (response.ok) {
            changePasswordModal.classList.remove('show');
            window.location.href = './popup.html';
        }
    } catch (error) {
        console.error('Error cambiando contraseña:', error);
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
