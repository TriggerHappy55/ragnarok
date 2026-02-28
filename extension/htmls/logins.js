import { guardarDato } from './data.js';

const inputUrl = document.getElementById('input-website');
const inputEmail = document.getElementById('input-user');
const inputPassword = document.getElementById('input-pass');
const inputComentario = document.getElementById('input-text');
const strengthDiv = document.getElementById('password-strength');
const saveBtn = document.getElementById('saveBtn');
const inputAutologin = document.getElementById('input-autologin');

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
                inputAutologin.checked = password.autologin || false;
            }
        }
    } catch (error) {
        console.error('Error cargando dato:', error);
    }
}

cargarDatoSeleccionado();

// Función para analizar contraseña
function analizarContraseña(pwd) {
    return {
        longitud: pwd.length,
        mayusculas: /[A-Z]/.test(pwd),
        minusculas: /[a-z]/.test(pwd),
        digitos: /[0-9]/.test(pwd),
        simbolos: /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(pwd)
    };
}

// Función para obtener fuerza de contraseña
async function obtenerFuerzaContraseña(pwd) {
    try {
        const result = await new Promise((resolve) => {
            browser.storage.local.get(['authToken'], resolve);
        });

        const analisis = analizarContraseña(pwd);
        
        console.log('Enviando analisis:', analisis);
        
        const queryParams = new URLSearchParams({
            password: pwd,
            longitud: analisis.longitud,
            mayusculas: analisis.mayusculas,
            minusculas: analisis.minusculas,
            digitos: analisis.digitos,
            simbolos: analisis.simbolos
        });
        
        const response = await fetch(`https://ragnarok-uegm.onrender.com/check-password-strength?${queryParams}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${result.authToken}`
            }
        });

        console.log('Response status:', response.status);

        if (!response.ok) {
            const errorText = await response.text();
            console.error('Error response:', errorText);
            throw new Error(`Error ${response.status}: ${errorText}`);
        }

        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error verificando fuerza:', error);
    }
    return null;
}

// Mostrar fuerza de contraseña al cambiar
inputPassword.addEventListener('change', async () => {
    if (inputPassword.value) {
        const fuerza = await obtenerFuerzaContraseña(inputPassword.value);
        if (fuerza) {
            strengthDiv.style.display = 'block';
            strengthDiv.textContent = `Fuerza: ${fuerza.fortaleza}`;
            
            const fortaleza = (fuerza.fortaleza || '').toLowerCase();
            if (fortaleza.includes('fuerte') || fortaleza.includes('strong')) {
                strengthDiv.style.backgroundColor = '#4CAF50';
                strengthDiv.style.color = 'white';
            } else if (fortaleza.includes('medio') || fortaleza.includes('medium')) {
                strengthDiv.style.backgroundColor = '#FFC107';
                strengthDiv.style.color = 'black';
            } else {
                strengthDiv.style.backgroundColor = '#f44336';
                strengthDiv.style.color = 'white';
            }
        }
    }
});

// Guardar datos cuando presione Enter o haga click en guardar
async function guardar() {
    const nuevoPassword = {
        url: inputUrl.value,
        email: inputEmail.value,
        password: inputPassword.value,
        autologin: inputAutologin.checked,
        comentario: inputComentario.value
    };
    
    try {
        await guardarDato(nuevoPassword);
        window.location.href = './popup.html';
    } catch (error) {
        console.error('Error al guardar:', error);
    }
}

// Agregar evento al botón guardar
saveBtn.addEventListener('click', guardar);

// Agregar evento al botón volver
backBtn.addEventListener('click', () => {
    window.location.href = './popup.html';
});

// Agregar evento para guardar con Enter
inputComentario.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        guardar();
    }
});

// Botón guardar (opcional - agregar a HTML si deseas)
window.guardar = guardar;
