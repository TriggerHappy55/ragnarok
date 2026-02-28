import { cargarDatos } from './data.js';
import { renderizarObjetos } from './renderer.js';

const contenedor = document.getElementById("app");
const logoutBtn = document.getElementById("logout-btn");

// Logout handler
logoutBtn.addEventListener('click', () => {
    browser.storage.local.remove(['authToken', 'user'], () => {
        window.location.href = './login.html';
    });
});

// Check if logged in
browser.storage.local.get(['authToken'], async (result) => {
    if (!result.authToken) {
        window.location.href = './login.html';
        return;
    }
    
    const datos = await cargarDatos();
    renderizarObjetos(datos, contenedor);
});
