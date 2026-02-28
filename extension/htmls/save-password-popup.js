const siteUrlSpan = document.getElementById('siteUrl');
const emailText = document.getElementById('emailText');
const breachWarning = document.getElementById('breachWarning');
const cancelBtn = document.getElementById('cancelBtn');
const saveBtn = document.getElementById('saveBtn');

let passwordData = null;
let isVulnerable = false;

// Recibir datos del background script
browser.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'showSavePopup') {
        passwordData = request.data;
        siteUrlSpan.textContent = request.data.url || 'Desconocido';
        emailText.textContent = request.data.email || 'No proporcionado';
        
        if (request.data.password_vulnerada) {
            breachWarning.style.display = 'block';
            isVulnerable = true;
        }
    }
});

cancelBtn.addEventListener('click', () => {
    window.close();
});

saveBtn.addEventListener('click', async () => {
    try {
        const result = await new Promise((resolve) => {
            browser.storage.local.get(['authToken'], resolve);
        });

        if (result.authToken && passwordData) {
            const response = await fetch(
                'https://ragnarok-uegm.onrender.com/passwords',
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${result.authToken}`
                    },
                    body: JSON.stringify({
                        url: passwordData.url,
                        email: passwordData.email,
                        password: passwordData.password,
                        autologin: false,
                        comentario: 'Guardada automáticamente'
                    })
                }
            );

            if (response.ok) {
                window.close();
            }
        }
    } catch (error) {
        console.error('Error guardando contraseña:', error);
    }
});
