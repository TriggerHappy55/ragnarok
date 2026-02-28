const API_URL = 'https://ragnarok-uegm.onrender.com/passwords';

async function getAuthToken() {
    const result = await new Promise((resolve) => {
        browser.storage.local.get(['authToken'], resolve);
    });
    return result.authToken;
}

async function getHeaders() {
    const token = await getAuthToken();
    if (!token) {
        window.location.href = './login.html';
        throw new Error('No auth token');
    }
    return {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
    };
}

export async function cargarDatos() {
    try {
        const headers = await getHeaders();
        const response = await fetch(API_URL, { headers });
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        return await response.json();
    } catch (error) {
        console.error('Error cargando datos:', error);
        return [];
    }
}

export async function guardarDato(nuevoPassword) {
    try {
        const headers = await getHeaders();
        const response = await fetch(API_URL, {
            method: 'POST',
            headers,
            body: JSON.stringify(nuevoPassword)
        });
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        return await response.json();
    } catch (error) {
        console.error('Error guardando dato:', error);
        throw error;
    }
}


