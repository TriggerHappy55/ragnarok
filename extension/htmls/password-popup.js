const saveModeContainer = document.getElementById('saveModeContainer');
const autofillModeContainer = document.getElementById('autofillModeContainer');

// Save mode elements
const siteUrlSpan = document.getElementById('siteUrl');
const emailText = document.getElementById('emailText');
const breachWarning = document.getElementById('breachWarning');
const saveCancelBtn = document.getElementById('saveCancelBtn');
const saveSaveBtn = document.getElementById('saveSaveBtn');

// Autofill mode elements
const autofillEmailDisplay = document.getElementById('autofillEmailDisplay');
const autofillCancelBtn = document.getElementById('autofillCancelBtn');
const autofillConfirmBtn = document.getElementById('autofillConfirmBtn');

let mode = null; // 'save' o 'autofill'
let passwordData = null;
let autofillData = null;

document.addEventListener('DOMContentLoaded', async () => {
    console.log('🔐 Popup DOMContentLoaded fired');
    try {
        // Pequeño delay para asegurar que el background haya seteado el modo
        await new Promise(resolve => setTimeout(resolve, 100));
        
        console.log('🔐 Requesting popup mode from background...');
        const response = await browser.runtime.sendMessage({
            action: 'getPopupMode'
        });
        
        console.log('🔐 Popup mode response:', response);
        console.log('🔐 Mode:', response.mode);
        console.log('🔐 Data:', response.data);
        
        if (response.mode === 'save') {
            console.log('🔐 Showing save mode');
            mode = 'save';
            showSaveMode(response.data);
        } else if (response.mode === 'autofill') {
            console.log('🔐 Showing autofill mode');
            mode = 'autofill';
            showAutofillMode(response.data);
        } else {
            console.error('🔐 No mode received, popup will be empty. Mode:', response.mode);
            console.log('🔐 All storage:', response);
        }
    } catch (error) {
        console.error('🔐 Error getting popup mode:', error);
    }
});

function showSaveMode(data) {
    saveModeContainer.style.display = 'block';
    autofillModeContainer.style.display = 'none';
    
    passwordData = data;
    if (data) {
        siteUrlSpan.textContent = data.url || 'Desconocido';
        emailText.textContent = data.email || 'No proporcionado';
        
        if (data.password_vulnerada) {
            breachWarning.style.display = 'block';
        }
    }
}

function showAutofillMode(data) {
    saveModeContainer.style.display = 'none';
    autofillModeContainer.style.display = 'block';
    
    autofillData = data;
    if (data) {
        autofillEmailDisplay.textContent = data.email || 'No disponible';
    }
}

// Save mode handlers
saveCancelBtn.addEventListener('click', () => {
    window.close();
});

saveSaveBtn.addEventListener('click', async () => {
    try {
        if (!passwordData) {
            console.error('No password data available');
            return;
        }

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

// Autofill mode handlers
autofillCancelBtn.addEventListener('click', () => {
    window.close();
});

autofillConfirmBtn.addEventListener('click', async () => {
    try {
        if (!autofillData) {
            console.error('No autofill data available');
            return;
        }

        console.log('Sending autofill confirmation');
        await browser.runtime.sendMessage({
            action: 'autofillConfirmed',
            data: autofillData
        });
        
        window.close();
    } catch (error) {
        console.error('Error confirming autofill:', error);
    }
});
