console.log('Background script loaded');

let pendingPassword = null;
let pendingAutofill = null;
let autofillTabId = null;
let cachedPasswords = null;

// Consolidar listeners de mensajes
browser.runtime.onMessage.addListener((request, sender, sendResponse) => {
    console.log('Message received:', request.action);
    
    if (request.action === 'checkPassword') {
        console.log('🔐 [BG] Processing checkPassword', {
            email: request.email,
            url: request.url,
            passwordLength: request.password ? request.password.length : 0
        });
        pendingPassword = {
            url: request.url,
            email: request.email,
            password: request.password
        };
        
        console.log('🔐 [BG] Pending password stored:', {
            url: pendingPassword.url,
            email: pendingPassword.email,
            passwordLength: pendingPassword.password ? pendingPassword.password.length : 0
        });
        
        // Guardar en storage local para persistencia
        browser.storage.local.set({
            popupMode: 'save',
            popupData: pendingPassword
        }).then(() => {
            console.log('🔐 [BG] Storage saved, opening popup window...');
            browser.windows.create({
                url: browser.runtime.getURL('htmls/password-popup.html'),
                type: 'popup',
                width: 400,
                height: 350,
                left: 100,
                top: 100
            }).catch((error) => {
                console.error('🔐 [BG] Error opening popup window:', error);
            });
        }).catch(err => {
            console.error('🔐 [BG] Error saving to storage:', err);
        });
        sendResponse({ received: true });
        
    } else if (request.action === 'getSavedPasswords') {
        console.log('Getting saved passwords');
        fetchAndCachePasswords().then(passwords => {
            sendResponse({ passwords: passwords });
        }).catch(err => {
            console.error('Error fetching passwords:', err);
            sendResponse({ passwords: [] });
        });
        return true; // Indica que la respuesta será asíncrona
        
    } else if (request.action === 'requestAutofill') {
        console.log('Autofill requested for URL:', request.url, 'Tab ID:', sender.tab.id);
        autofillTabId = sender.tab.id;
        fetchAndShowAutofill(request.url, sender.tab.id);
        sendResponse({ received: true });
        
    } else if (request.action === 'getPopupMode') {
        console.log('🔐 [BG] Getting popup mode request');
        browser.storage.local.get(['popupMode', 'popupData'], (result) => {
            console.log('🔐 [BG] Storage retrieved:', result);
            console.log('🔐 [BG] Popup mode from storage:', result.popupMode);
            console.log('🔐 [BG] Popup data from storage:', result.popupData);
            sendResponse({ mode: result.popupMode, data: result.popupData });
        });
        return true; // Indica que la respuesta será asíncrona
        
    } else if (request.action === 'getPasswordData') {
        console.log('Sending password data:', {
            url: pendingPassword?.url,
            email: pendingPassword?.email,
            passwordLength: pendingPassword?.password ? pendingPassword.password.length : 0
        });
        sendResponse({ data: pendingPassword });
        
    } else if (request.action === 'getAutofillData') {
        console.log('Sending autofill data:', {
            email: pendingAutofill?.email
        });
        sendResponse({ data: pendingAutofill });
        
    } else if (request.action === 'savePassword') {
        console.log('Save password request received:', {
            url: request.data?.url,
            email: request.data?.email,
            passwordLength: request.data?.password ? request.data.password.length : 0
        });
        savePassword(request.data);
        sendResponse({ success: true });
        
    } else if (request.action === 'autofillConfirmed') {
        console.log('Autofill confirmed, sending to tab:', autofillTabId);
        if (autofillTabId) {
            browser.tabs.sendMessage(autofillTabId, {
                action: 'autofillCredentials',
                data: request.data
            }).catch(err => console.error('Error sending autofill to tab:', err));
        }
        sendResponse({ success: true });
        
    } else if (request.action === 'passwordSaved') {
        console.log('Password saved, clearing data');
        pendingPassword = null;
        pendingAutofill = null;
        cachedPasswords = null;
        browser.storage.local.set({
            popupMode: null,
            popupData: null
        });
        sendResponse({ success: true });
    }
});

async function fetchAndCachePasswords() {
    try {
        const result = await new Promise((resolve) => {
            browser.storage.local.get(['authToken'], resolve);
        });

        if (!result.authToken) {
            console.error('No auth token found');
            return [];
        }

        const response = await fetch(
            'https://ragnarok-uegm.onrender.com/passwords',
            {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${result.authToken}`
                }
            }
        );

        if (!response.ok) {
            console.error('Error fetching passwords:', response.statusText);
            return [];
        }

        const passwords = await response.json();
        cachedPasswords = passwords;
        console.log('🔐 Cached', passwords.length, 'passwords');
        return passwords;
    } catch (error) {
        console.error('Error fetching passwords:', error);
        return [];
    }
}

async function fetchAndShowAutofill(url, tabId) {
    try {
        console.log('fetchAndShowAutofill called with URL:', url);
        
        const result = await new Promise((resolve) => {
            browser.storage.local.get(['authToken'], resolve);
        });

        if (!result.authToken) {
            console.error('No auth token found');
            return;
        }

        // Hacer GET a /passwords
        const response = await fetch(
            'https://ragnarok-uegm.onrender.com/passwords',
            {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${result.authToken}`
                }
            }
        );

        if (!response.ok) {
            console.error('Error fetching passwords:', response.statusText);
            return;
        }

        const passwords = await response.json();
        cachedPasswords = passwords; // Cachear
        console.log('Fetched passwords:', passwords.length, 'passwords');
        console.log('All stored URLs:', passwords.map(p => p.url));

        // Normalizar URL actual
        const normalizeUrl = (urlStr) => {
            if (!urlStr) return '';
            const normalized = urlStr.toLowerCase().trim();
            // Remover www, protocolo, trailing slashes
            return normalized
                .replace(/^(https?:\/\/)?(www\.)?/, '')
                .replace(/\/$/, '')
                .split('/')[0]; // Solo el dominio
        };

        const currentUrlNormalized = normalizeUrl(url);
        console.log('Current URL normalized:', currentUrlNormalized);

        // Buscar coincidencia con la URL actual
        const matchedPassword = passwords.find(p => {
            const storedUrl = p.url || '';
            const storedUrlNormalized = normalizeUrl(storedUrl);
            
            console.log('Comparing:', { 
                stored: storedUrl, 
                storedNormalized: storedUrlNormalized,
                current: url,
                currentNormalized: currentUrlNormalized
            });
            
            // Múltiples estrategias de matching
            const exactMatch = storedUrlNormalized === currentUrlNormalized;
            const storedIncludes = storedUrlNormalized.includes(currentUrlNormalized);
            const currentIncludes = currentUrlNormalized.includes(storedUrlNormalized);
            const partialMatch = storedUrlNormalized.split('.').slice(-2).join('.') === 
                                 currentUrlNormalized.split('.').slice(-2).join('.');
            
            return exactMatch || storedIncludes || currentIncludes || partialMatch;
        });

        console.log('Match result:', matchedPassword ? 'Found' : 'Not found');

        if (matchedPassword) {
            console.log('Found matching password for:', url);
            console.log('Matched password:', { 
                email: matchedPassword.email, 
                url: matchedPassword.url 
            });
            
            pendingAutofill = {
                email: matchedPassword.email,
                password: matchedPassword.password
            };

            // Guardar en storage local y abrir popup
            browser.storage.local.set({
                popupMode: 'autofill',
                popupData: pendingAutofill
            }).then(() => {
                console.log('🔐 [BG] Opening popup window for autofill');
                browser.windows.create({
                    url: browser.runtime.getURL('htmls/password-popup.html'),
                    type: 'popup',
                    width: 400,
                    height: 300,
                    left: 100,
                    top: 100
                }).catch((error) => {
                    console.error('🔐 [BG] Error opening popup window:', error);
                });
            });
        } else {
            console.log('No matching password found for:', url);
            console.log('Stored URLs (normalized):', passwords.map(p => normalizeUrl(p.url)));
        }
    } catch (error) {
        console.error('Error fetching autofill credentials:', error);
    }
}


async function savePassword(data) {
    try {
        console.log('🔐 [BG] savePassword called with:', {
            url: data?.url,
            email: data?.email,
            passwordLength: data?.password ? data.password.length : 0
        });
        
        const result = await new Promise((resolve) => {
            browser.storage.local.get(['authToken'], resolve);
        });

        if (result.authToken) {
            const payload = {
                url: data.url,
                email: data.email,
                password: data.password,
                autologin: false,
                comentario: 'Guardada automáticamente'
            };
            
            console.log('🔐 [BG] Sending to API:', {
                url: payload.url,
                email: payload.email,
                passwordLength: payload.password ? payload.password.length : 0
            });
            
            const response = await fetch(
                'https://ragnarok-uegm.onrender.com/passwords',
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${result.authToken}`
                    },
                    body: JSON.stringify(payload)
                }
            );
            
            if (response.ok) {
                console.log('🔐 [BG] Password saved successfully to API');
            } else {
                console.error('🔐 [BG] Error saving password to API:', response.statusText);
                const errorBody = await response.text();
                console.error('🔐 [BG] Error body:', errorBody);
            }
        } else {
            console.error('🔐 [BG] No auth token found');
        }
    } catch (error) {
        console.error('🔐 [BG] Error saving password:', error);
    }
}



// Función para prueba manual desde console del background
window.testPopup = function() {
    console.log('🔐 Opening test popup...');
    browser.storage.local.set({
        popupMode: 'save',
        popupData: {
            url: 'test.com',
            email: 'test@example.com',
            password: 'test123'
        }
    }).then(() => {
        console.log('🔐 Test data saved to storage');
        browser.windows.create({
            url: browser.runtime.getURL('htmls/password-popup.html'),
            type: 'popup',
            width: 400,
            height: 350,
            left: 100,
            top: 100
        }).catch(err => {
            console.error('🔐 Error opening popup:', err);
        });
    });
};
console.log('🔐 Type window.testPopup() in console to test');
