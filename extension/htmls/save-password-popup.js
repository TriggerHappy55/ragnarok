const siteUrlSpan = document.getElementById('siteUrl');
const emailText = document.getElementById('emailText');
const breachWarning = document.getElementById('breachWarning');
const cancelBtn = document.getElementById('cancelBtn');
const saveBtn = document.getElementById('saveBtn');

let passwordData = null;
let isVulnerable = false;

// Obtener datos del background script cuando se abre el popup
document.addEventListener('DOMContentLoaded', async () => {
    try {
        const response = await browser.runtime.sendMessage({
            action: 'getPasswordData'
        });
        
        console.log('Password data received:', response.data);
        
        if (response.data) {
            passwordData = response.data;
            console.log('Password data stored:', passwordData);
            siteUrlSpan.textContent = response.data.url || 'Desconocido';
            emailText.textContent = response.data.email || 'No proporcionado';
            
            if (response.data.password_vulnerada) {
                breachWarning.style.display = 'block';
                isVulnerable = true;
            }
        }
    } catch (error) {
        console.error('Error getting password data:', error);
    }
});

cancelBtn.addEventListener('click', () => {
    window.close();
});

saveBtn.addEventListener('click', async () => {
    try {
        if (!passwordData) {
            console.error('No password data available');
            return;
        }

        // Usar el email del DOM como fallback si passwordData.email es vacío
        const email = passwordData.email || emailText.textContent;
        const url = passwordData.url || siteUrlSpan.textContent;
        
        console.log('Saving password with data:', {
            email: email,
            url: url,
            password: passwordData.password ? '***' : 'MISSING'
        });

        const response = await browser.runtime.sendMessage({
            action: 'savePassword',
            data: {
                url: url,
                email: email,
                password: passwordData.password,
                autologin: false,
                comentario: 'Guardada automáticamente'
            }
        });

        console.log('Save response:', response);

        if (response.success) {
            console.log('Password saved successfully');
            await browser.runtime.sendMessage({
                action: 'passwordSaved'
            });
            window.close();
        }
    } catch (error) {
        console.error('Error saving password:', error);
    }
});
