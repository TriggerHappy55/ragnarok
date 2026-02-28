console.log('Background script loaded');

let pendingPassword = null;

// Escuchar mensajes desde content scripts
browser.runtime.onMessage.addListener((request, sender, sendResponse) => {
    console.log('Message received:', request.action);
    
    if (request.action === 'checkPassword') {
        console.log('Processing checkPassword');
        // Guardar temporalmente los datos de la contraseña
        pendingPassword = {
            url: request.url,
            email: request.email,
            password: request.password
        };
        
        // Mostrar notificación
        browser.notifications.create('save-password-notification', {
            type: 'basic',
            iconUrl: browser.runtime.getURL('htmls/icon.png'),
            title: 'Guardar Contraseña',
            message: `¿Quieres guardar la contraseña para ${request.email} en ${request.url}?`,
            buttons: [
                { title: 'No guardar' },
                { title: 'Guardar' }
            ]
        });
    }
    
    sendResponse({ received: true });
});

// Escuchar clicks en notificaciones
browser.notifications.onButtonClicked.addListener((notificationId, buttonIndex) => {
    if (notificationId === 'save-password-notification') {
        if (buttonIndex === 1 && pendingPassword) {
            // Guardar contraseña
            savePassword(pendingPassword);
        }
        browser.notifications.clear(notificationId);
    }
});

async function savePassword(data) {
    try {
        const result = await new Promise((resolve) => {
            browser.storage.local.get(['authToken'], resolve);
        });

        if (result.authToken) {
            await fetch(
                'https://ragnarok-uegm.onrender.com/passwords',
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${result.authToken}`
                    },
                    body: JSON.stringify({
                        url: data.url,
                        email: data.email,
                        password: data.password,
                        autologin: false,
                        comentario: 'Guardada automáticamente'
                    })
                }
            );
            console.log('Password saved successfully');
        }
    } catch (error) {
        console.error('Error saving password:', error);
    }
}

