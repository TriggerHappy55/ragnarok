console.log('Background script loaded');

let pendingPassword = null;
let pendingAutofill = null;
let popupMode = null;
let popupData = null;
let autofillTabId = null;
let cachedPasswords = null;

// Consolidar listeners de mensajes
browser.runtime.onMessage.addListener((request, sender, sendResponse) => {
    console.log('Message received:', request.action);
    
    if (request.action === 'checkPassword') {
        console.log('Processing checkPassword', {
            email: request.email,
            url: request.url,
            passwordLength: request.password ? request.password.length : 0
        });
        pendingPassword = {
            url: request.url,
            email: request.email,
            password: request.password
        };
        
        console.log('Pending password stored:', {
            url: pendingPassword.url,
            email: pendingPassword.email,
            passwordLength: pendingPassword.password ? pendingPassword.password.length : 0
        });
        
        // Abrir popup con openOptionsPage
        popupMode = 'save';
        popupData = pendingPassword;
        browser.runtime.openOptionsPage().catch((error) => {
            console.error('Error opening options page:', error);
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
        console.log('Getting popup mode:', popupMode);
        sendResponse({ mode: popupMode, data: popupData || popupMode === 'save' ? pendingPassword : pendingAutofill });
        
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
        console.log('Password saved, clearing pendingPassword');
        pendingPassword = null;
        popupMode = null;
        popupData = null;
        cachedPasswords = null; // Limpiar caché
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

            // Abrir popup con openOptionsPage
            popupMode = 'autofill';
            popupData = pendingAutofill;
            console.log('Opening options page for autofill');
            browser.runtime.openOptionsPage().catch((error) => {
                console.error('Error opening options page:', error);
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
        console.log('savePassword function called with:', {
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
            
            console.log('Sending to API:', {
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
                console.log('Password saved successfully to API');
            } else {
                console.error('Error saving password to API:', response.statusText);
                const errorBody = await response.text();
                console.error('Error body:', errorBody);
            }
        } else {
            console.error('No auth token found');
        }
    } catch (error) {
        console.error('Error saving password:', error);
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

            // Abrir popup con openOptionsPage
            popupMode = 'autofill';
            popupData = pendingAutofill;
            console.log('Opening options page for autofill');
            browser.runtime.openOptionsPage().catch((error) => {
                console.error('Error opening options page:', error);
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
        console.log('savePassword function called with:', {
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
            
            console.log('Sending to API:', {
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
                console.log('Password saved successfully to API');
            } else {
                console.error('Error saving password to API:', response.statusText);
                const errorBody = await response.text();
                console.error('Error body:', errorBody);
            }
        } else {
            console.error('No auth token found');
        }
    } catch (error) {
        console.error('Error saving password:', error);
    }
}

