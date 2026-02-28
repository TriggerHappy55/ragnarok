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

console.log('🔐 DOM elements found:', {
    saveModeContainer: !!saveModeContainer,
    autofillModeContainer: !!autofillModeContainer,
    siteUrlSpan: !!siteUrlSpan,
    emailText: !!emailText,
    saveCancelBtn: !!saveCancelBtn,
    saveSaveBtn: !!saveSaveBtn,
    autofillEmailDisplay: !!autofillEmailDisplay,
    autofillCancelBtn: !!autofillCancelBtn,
    autofillConfirmBtn: !!autofillConfirmBtn
});

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
    console.log('🔐 showSaveMode called with data:', data);
    
    if (!saveModeContainer) {
        console.error('🔐 saveModeContainer not found!');
        return;
    }
    
    saveModeContainer.style.display = 'block';
    autofillModeContainer.style.display = 'none';
    
    passwordData = data;
    if (data) {
        console.log('🔐 Setting form values:', { url: data.url, email: data.email });
        siteUrlSpan.textContent = data.url || 'Desconocido';
        emailText.textContent = data.email || 'No proporcionado';
        
        if (data.password_vulnerada) {
            breachWarning.style.display = 'block';
        }
    } else {
        console.warn('🔐 showSaveMode called with no data');
    }
}

function showAutofillMode(data) {
    console.log('🔐 showAutofillMode called with data:', data);
    
    if (!autofillModeContainer) {
        console.error('🔐 autofillModeContainer not found!');
        return;
    }
    
    saveModeContainer.style.display = 'none';
    autofillModeContainer.style.display = 'block';
    
    autofillData = data;
    if (data) {
        console.log('🔐 Setting autofill email:', data.email);
        autofillEmailDisplay.textContent = data.email || 'No disponible';
    } else {
        console.warn('🔐 showAutofillMode called with no data');
    }
}

// Save mode handlers
if (!saveCancelBtn) {
    console.error('🔐 saveCancelBtn not found!');
} else {
    console.log('🔐 saveCancelBtn found, adding listener');
    saveCancelBtn.addEventListener('click', () => {
        console.log('🔐 Cancel button clicked');
        window.close();
    });
}

if (!saveSaveBtn) {
    console.error('🔐 saveSaveBtn not found!');
} else {
    console.log('🔐 saveSaveBtn found, adding listener');
    saveSaveBtn.addEventListener('click', async () => {
        console.log('🔐 Save button clicked');
        try {
            if (!passwordData) {
                console.error('🔐 No password data available');
                return;
            }

            const email = passwordData.email || emailText.textContent;
            const url = passwordData.url || siteUrlSpan.textContent;
            
            console.log('🔐 Saving password with data:', {
                email: email,
                url: url,
                passwordLength: passwordData.password ? passwordData.password.length : 0
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

            console.log('🔐 Save response:', response);

            if (response.success) {
                console.log('🔐 Password saved successfully, sending passwordSaved message');
                await browser.runtime.sendMessage({
                    action: 'passwordSaved'
                });
                console.log('🔐 Closing popup');
                window.close();
            }
        } catch (error) {
            console.error('🔐 Error saving password:', error);
        }
    });
}

// Autofill mode handlers
if (!autofillCancelBtn) {
    console.error('🔐 autofillCancelBtn not found!');
} else {
    console.log('🔐 autofillCancelBtn found, adding listener');
    autofillCancelBtn.addEventListener('click', () => {
        console.log('🔐 Autofill cancel clicked');
        window.close();
    });
}

if (!autofillConfirmBtn) {
    console.error('🔐 autofillConfirmBtn not found!');
} else {
    console.log('🔐 autofillConfirmBtn found, adding listener');
    autofillConfirmBtn.addEventListener('click', async () => {
        console.log('🔐 Autofill confirm clicked');
        try {
            if (!autofillData) {
                console.error('🔐 No autofill data available');
                return;
            }

            console.log('🔐 Sending autofill confirmation');
            await browser.runtime.sendMessage({
                action: 'autofillConfirmed',
                data: autofillData
            });
            
            console.log('🔐 Closing popup');
            window.close();
        } catch (error) {
            console.error('🔐 Error confirming autofill:', error);
        }
    });
}
