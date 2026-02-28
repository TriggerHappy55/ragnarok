// Content script que detecta cuando se ingresa una contraseña

// Detectar cuando se completa un formulario de login
document.addEventListener('submit', async (e) => {
    const form = e.target;
    
    // Buscar inputs de contraseña y email
    const passwordInputs = form.querySelectorAll('input[type="password"]');
    const emailInputs = form.querySelectorAll('input[type="email"], input[type="text"][name*="email" i], input[type="text"][name*="user" i]');
    
    if (passwordInputs.length > 0) {
        const password = passwordInputs[0].value;
        const email = emailInputs.length > 0 ? emailInputs[0].value : '';
        
        if (password) {
            // Enviar mensaje a background para mostrar notificación
            browser.runtime.sendMessage({
                action: 'checkPassword',
                password: password,
                email: email,
                url: window.location.hostname
            });
        }
    }
}, true);

