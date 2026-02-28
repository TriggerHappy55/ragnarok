// Content script que detecta cuando se ingresa una contraseña

let autofillPending = false;
let savedPasswords = [];
let currentDropdown = null;

// Palabras clave para detectar campos de email/usuario (40+ variaciones)
const emailKeywords = [
    'email', 'e-mail', 'mail', 'e_mail', 'emailaddress', 'email_address', 'email-address',
    'user', 'username', 'user_name', 'user-name', 'userid', 'user_id', 'user-id',
    'login', 'loginname', 'login_name', 'login-name', 'loginid', 'login_id', 'login-id',
    'account', 'accountname', 'account_name', 'account-name', 'accountid', 'account_id',
    'member', 'membername', 'member_name', 'memberid', 'member_id',
    'person', 'personname', 'person_name', 'personid', 'person_id',
    'credential', 'credentials', 'identifier', 'id', 'uid', 'uname',
    'contact', 'contactemail', 'contact_email', 'primaryemail',
    'username_or_email', 'email_or_username', 'email_or_login',
    'usuario', 'nombre_usuario', 'nombreusuario',
    'correo', 'direccionemail', 'direccion_email',
    'login_email', 'email_login', 'emaillogin',
    'handle', 'nickname', 'name', 'fullname', 'firstname', 'authorname',
    'phone', 'telephone', 'mobile', 'cellphone'
];

function getEmailInput() {
    let emailInputs = document.querySelectorAll('input[type="email"]');
    
    if (emailInputs.length === 0) {
        const selectors = emailKeywords.map(kw => `input[type="text"][name*="${kw}" i]`).join(', ');
        emailInputs = document.querySelectorAll(selectors);
    }
    
    if (emailInputs.length === 0) {
        const selectors = emailKeywords.map(kw => `input[id*="${kw}" i]`).join(', ');
        emailInputs = document.querySelectorAll(selectors);
    }
    
    if (emailInputs.length === 0) {
        const selectors = emailKeywords.map(kw => `input[placeholder*="${kw}" i]`).join(', ');
        emailInputs = document.querySelectorAll(selectors);
    }
    
    if (emailInputs.length === 0) {
        emailInputs = document.querySelectorAll('input[type="text"]');
    }
    
    return emailInputs.length > 0 ? emailInputs[0] : null;
}

function fetchSavedPasswords() {
    console.log('🔐 Fetching saved passwords from background');
    browser.runtime.sendMessage({
        action: 'getSavedPasswords'
    }).then(response => {
        if (response.passwords) {
            savedPasswords = response.passwords;
            console.log('🔐 Fetched', savedPasswords.length, 'saved passwords');
        }
    }).catch(err => {
        console.error('🔐 Error fetching passwords:', err);
    });
}

function createDropdown(emailInput, suggestions) {
    // Remover dropdown anterior si existe
    if (currentDropdown) {
        currentDropdown.remove();
    }

    const dropdown = document.createElement('div');
    dropdown.className = 'ragnarok-autocomplete-dropdown';
    dropdown.style.cssText = `
        position: absolute;
        background: white;
        border: 1px solid #ccc;
        border-top: none;
        max-height: 200px;
        overflow-y: auto;
        width: ${emailInput.offsetWidth}px;
        z-index: 10000;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        font-family: Arial, sans-serif;
        font-size: 14px;
    `;

    suggestions.forEach((suggestion, index) => {
        const item = document.createElement('div');
        item.className = 'ragnarok-autocomplete-item';
        item.style.cssText = `
            padding: 10px 12px;
            cursor: pointer;
            border-bottom: 1px solid #eee;
            transition: background-color 0.2s;
        `;
        item.textContent = suggestion.email;
        
        item.addEventListener('mouseover', () => {
            item.style.backgroundColor = '#f0f0f0';
        });
        
        item.addEventListener('mouseout', () => {
            item.style.backgroundColor = 'white';
        });
        
        item.addEventListener('click', () => {
            emailInput.value = suggestion.email;
            emailInput.dispatchEvent(new Event('input', { bubbles: true }));
            emailInput.dispatchEvent(new Event('change', { bubbles: true }));
            
            // Rellenar contraseña también
            const passwordInputs = document.querySelectorAll('input[type="password"]');
            if (passwordInputs.length > 0) {
                passwordInputs[0].value = suggestion.password;
                passwordInputs[0].dispatchEvent(new Event('input', { bubbles: true }));
                passwordInputs[0].dispatchEvent(new Event('change', { bubbles: true }));
            }
            
            dropdown.remove();
            currentDropdown = null;
            console.log('🔐 Autocomplete selected:', suggestion.email);
        });
        
        dropdown.appendChild(item);
    });

    const rect = emailInput.getBoundingClientRect();
    dropdown.style.position = 'fixed';
    dropdown.style.top = (rect.bottom) + 'px';
    dropdown.style.left = rect.left + 'px';

    document.body.appendChild(dropdown);
    currentDropdown = dropdown;
}

function showAutocomplete(emailInput) {
    const searchValue = emailInput.value.toLowerCase();
    
    if (!searchValue || searchValue.length === 0) {
        if (currentDropdown) {
            currentDropdown.remove();
            currentDropdown = null;
        }
        return;
    }

    const suggestions = savedPasswords.filter(p => 
        p.email.toLowerCase().includes(searchValue)
    );

    if (suggestions.length > 0) {
        createDropdown(emailInput, suggestions);
    } else if (currentDropdown) {
        currentDropdown.remove();
        currentDropdown = null;
    }
}

function detectLoginForm() {
    const passwordInputs = document.querySelectorAll('input[type="password"]');
    console.log('🔐 Checking for login form, found password inputs:', passwordInputs.length);
    return passwordInputs.length > 0;
}

function requestAutofill() {
    if (autofillPending) return;
    autofillPending = true;
    
    const currentUrl = window.location.hostname;
    console.log('🔐 Requesting autofill for:', currentUrl);
    
    browser.runtime.sendMessage({
        action: 'requestAutofill',
        url: currentUrl
    }).catch(err => {
        console.error('🔐 Error requesting autofill:', err);
        autofillPending = false;
    });
}

function autofillForm(email, password) {
    console.log('🔐 Autofilling form with email:', email);
    
    let emailInputs = document.querySelectorAll('input[type="email"]');
    
    if (emailInputs.length === 0) {
        const selectors = emailKeywords.map(kw => `input[type="text"][name*="${kw}" i]`).join(', ');
        emailInputs = document.querySelectorAll(selectors);
    }
    
    if (emailInputs.length === 0) {
        const selectors = emailKeywords.map(kw => `input[id*="${kw}" i]`).join(', ');
        emailInputs = document.querySelectorAll(selectors);
    }
    
    if (emailInputs.length === 0) {
        const selectors = emailKeywords.map(kw => `input[placeholder*="${kw}" i]`).join(', ');
        emailInputs = document.querySelectorAll(selectors);
    }
    
    if (emailInputs.length === 0) {
        emailInputs = document.querySelectorAll('input[type="text"]');
    }
    
    const passwordInputs = document.querySelectorAll('input[type="password"]');
    
    console.log('🔐 Found inputs - Email fields:', emailInputs.length, 'Password fields:', passwordInputs.length);
    
    if (emailInputs.length > 0 && emailInputs[0].value === '') {
        emailInputs[0].value = email;
        emailInputs[0].focus();
        emailInputs[0].dispatchEvent(new Event('input', { bubbles: true }));
        emailInputs[0].dispatchEvent(new Event('change', { bubbles: true }));
        emailInputs[0].dispatchEvent(new KeyboardEvent('keydown', { bubbles: true }));
        emailInputs[0].dispatchEvent(new KeyboardEvent('keyup', { bubbles: true }));
        emailInputs[0].blur();
        console.log('✅ Email field filled with:', email);
    }
    
    if (passwordInputs.length > 0 && passwordInputs[0].value === '') {
        passwordInputs[0].value = password;
        passwordInputs[0].focus();
        passwordInputs[0].dispatchEvent(new Event('input', { bubbles: true }));
        passwordInputs[0].dispatchEvent(new Event('change', { bubbles: true }));
        passwordInputs[0].dispatchEvent(new KeyboardEvent('keydown', { bubbles: true }));
        passwordInputs[0].dispatchEvent(new KeyboardEvent('keyup', { bubbles: true }));
        passwordInputs[0].blur();
        console.log('✅ Password field filled');
    }
}

// Escuchar mensajes desde background
browser.runtime.onMessage.addListener((request, sender, sendResponse) => {
    console.log('🔐 Content script received message:', request.action);
    
    if (request.action === 'autofillCredentials') {
        console.log('🔐 Received autofill credentials in content script:', request.data);
        autofillForm(request.data.email, request.data.password);
        sendResponse({ filled: true });
    }
});

// Función para iniciar la detección
function initializeAutofillDetection() {
    console.log('🔐 Initializing autofill detection');
    
    // Fetch saved passwords
    fetchSavedPasswords();
    
    if (detectLoginForm()) {
        console.log('🔐 Login form found immediately');
        requestAutofill();
        
        // Agregar listener al campo de email para autocomplete
        const emailInput = getEmailInput();
        if (emailInput) {
            emailInput.addEventListener('input', () => {
                showAutocomplete(emailInput);
            });
            
            emailInput.addEventListener('blur', () => {
                setTimeout(() => {
                    if (currentDropdown) {
                        currentDropdown.remove();
                        currentDropdown = null;
                    }
                }, 200);
            });
            
            emailInput.addEventListener('focus', () => {
                showAutocomplete(emailInput);
            });
        }
    }
}

// Detectar cuando se carga la página
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        console.log('🔐 DOM Content Loaded');
        setTimeout(initializeAutofillDetection, 100);
    });
} else {
    console.log('🔐 Document already loaded');
    setTimeout(initializeAutofillDetection, 100);
}

// Observar cambios en el DOM para detectar formularios dinámicos
const observer = new MutationObserver((mutations) => {
    if (detectLoginForm() && !autofillPending) {
        console.log('🔐 Login form detected via MutationObserver');
        requestAutofill();
        
        const emailInput = getEmailInput();
        if (emailInput && !emailInput.hasListener) {
            emailInput.hasListener = true;
            emailInput.addEventListener('input', () => {
                showAutocomplete(emailInput);
            });
            
            emailInput.addEventListener('blur', () => {
                setTimeout(() => {
                    if (currentDropdown) {
                        currentDropdown.remove();
                        currentDropdown = null;
                    }
                }, 200);
            });
            
            emailInput.addEventListener('focus', () => {
                showAutocomplete(emailInput);
            });
        }
    }
});

// Iniciar observador después de un delay
setTimeout(() => {
    try {
        observer.observe(document.body || document.documentElement, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeFilter: ['style', 'class', 'hidden']
        });
        console.log('🔐 MutationObserver started');
    } catch (e) {
        console.error('🔐 Error starting MutationObserver:', e);
    }
}, 300);

// Detectar cuando se ingresa una contraseña
function getAllPossibleEmails() {
    const emails = new Set();
    
    document.querySelectorAll('input[type="email"], input[type="text"]').forEach(input => {
        if (input.value && input.value.includes('@')) {
            emails.add(input.value);
        }
        if (input.value && (input.name?.toLowerCase().includes('email') || 
                           input.name?.toLowerCase().includes('user') ||
                           input.id?.toLowerCase().includes('email') ||
                           input.id?.toLowerCase().includes('user'))) {
            emails.add(input.value);
        }
    });
    
    try {
        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            const value = localStorage.getItem(key);
            if (value && typeof value === 'string' && value.includes('@') && value.length < 200) {
                emails.add(value);
            }
        }
    } catch (e) {
        console.log('🔐 Cannot access localStorage:', e);
    }
    
    try {
        for (let i = 0; i < sessionStorage.length; i++) {
            const key = sessionStorage.key(i);
            const value = sessionStorage.getItem(key);
            if (value && typeof value === 'string' && value.includes('@') && value.length < 200) {
                emails.add(value);
            }
        }
    } catch (e) {
        console.log('🔐 Cannot access sessionStorage:', e);
    }
    
    document.querySelectorAll('[data-email], [data-user], [data-login]').forEach(el => {
        const email = el.getAttribute('data-email') || el.getAttribute('data-user') || el.getAttribute('data-login');
        if (email && email.includes('@')) {
            emails.add(email);
        }
    });
    
    document.querySelectorAll('input[type="hidden"]').forEach(input => {
        if (input.value && input.value.includes('@')) {
            emails.add(input.value);
        }
    });
    
    return Array.from(emails);
}

// Detectar cuando se completa un formulario de login
document.addEventListener('submit', async (e) => {
    const form = e.target;
    const passwordInputs = form.querySelectorAll('input[type="password"]');
    
    if (passwordInputs.length > 0) {
        const password = passwordInputs[0].value;
        
        if (password) {
            const possibleEmails = getAllPossibleEmails();
            let email = '';
            
            const validEmails = possibleEmails.filter(e => 
                e && e.length > 3 && e.length < 100 && e.includes('@') && !e.includes('data:')
            );
            
            if (validEmails.length > 0) {
                email = validEmails[0];
            }
            
            console.log('🔐 Form submitted - Password detected');
            console.log('Found emails:', validEmails);
            console.log('Using email:', email);
            console.log('Site:', window.location.hostname);
            
            browser.runtime.sendMessage({
                action: 'checkPassword',
                password: password,
                email: email,
                url: window.location.hostname
            }).catch(err => console.error('Error sending message:', err));
        }
    }
}, true);

document.addEventListener('change', (e) => {
    if (e.target.type === 'password' && e.target.value) {
        console.log('🔐 Password field changed');
    }
}, true);

console.log('🔐 Content script injected and ready');
