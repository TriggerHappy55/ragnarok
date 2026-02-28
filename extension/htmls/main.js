import { cargarDatos } from './data.js';
import { renderizarObjetos } from './renderer.js';

const contenedor = document.getElementById("app");
const logoutBtn = document.getElementById("logout-btn");
const newBtn = document.getElementById("newBtn");
const generateBtn = document.getElementById("generateBtn");

// Logout handler
logoutBtn.addEventListener('click', () => {
    browser.storage.local.remove(['authToken', 'user'], () => {
        window.location.href = './login.html';
    });
});

// New button handler
newBtn.addEventListener('click', () => {
    window.location.href = './logins.html';
});

// Generate button handler
generateBtn.addEventListener('click', () => {
    window.location.href = './generator.html';
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
