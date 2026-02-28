import { guardarDato } from './data.js';

const inputUrl = document.getElementById('input-website');
const inputEmail = document.getElementById('input-user');
const inputPassword = document.getElementById('input-pass');
const inputComentario = document.getElementById('input-text');

// Agregar campo para autologin
const inputAutologin = document.createElement('input');
inputAutologin.type = 'checkbox';
inputAutologin.id = 'input-autologin';
inputAutologin.style.marginTop = '10px';
inputAutologin.style.width = 'auto';
const labelAutologin = document.createElement('label');
labelAutologin.htmlFor = 'input-autologin';
labelAutologin.textContent = ' Auto-login';
labelAutologin.style.marginLeft = '5px';
const autologinContainer = document.createElement('div');
autologinContainer.appendChild(inputAutologin);
autologinContainer.appendChild(labelAutologin);
document.body.insertBefore(autologinContainer, inputComentario.nextSibling);

// Check if logged in
browser.storage.local.get(['authToken'], (result) => {
    if (!result.authToken) {
        window.location.href = './login.html';
    }
});

// Cargar dato seleccionado si existe (desde API)
async function cargarDatoSeleccionado() {
    try {
        const result = await new Promise((resolve) => {
            browser.storage.local.get(['selectedLoginId', 'authToken'], resolve);
        });
        
        if (result.selectedLoginId && result.authToken) {
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
                inputUrl.value = password.url || '';
                inputEmail.value = password.email || '';
                inputPassword.value = password.password || '';
                inputComentario.value = password.comentario || '';
                inputAutologin.checked = password.autologint || false;
            }
        }
    } catch (error) {
        console.error('Error cargando dato:', error);
    }
}

cargarDatoSeleccionado();

// Guardar datos cuando presione Enter o haga click en guardar
async function guardar() {
    const nuevoPassword = {
        url: inputUrl.value,
        email: inputEmail.value,
        password: inputPassword.value,
        autologint: inputAutologin.checked,
        comentario: inputComentario.value
    };
    
    try {
        await guardarDato(nuevoPassword);
        alert('Guardado correctamente');
        window.location.href = './popup.html';
    } catch (error) {
        alert('Error al guardar: ' + error.message);
    }
}

// Agregar evento para guardar con Enter
inputComentario.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        guardar();
    }
});

// Botón guardar (opcional - agregar a HTML si deseas)
window.guardar = guardar;
