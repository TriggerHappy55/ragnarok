const backBtn = document.getElementById('backBtn');
const longitud = document.getElementById('longitud');

backBtn.addEventListener('click', () => {
    window.location.href = './popup.html';
});
const mayusculas = document.getElementById('mayusculas');
const minusculas = document.getElementById('minusculas');
const digitos = document.getElementById('digitos');
const simbolos = document.getElementById('simbolos');
const generateBtn = document.getElementById('generateBtn');
const copyBtn = document.getElementById('copyBtn');
const errorDiv = document.getElementById('error');
const resultDiv = document.getElementById('result');
const passwordDisplay = document.getElementById('passwordDisplay');

let generatedPassword = '';

// Check if logged in
browser.storage.local.get(['authToken'], (result) => {
    if (!result.authToken) {
        window.location.href = './login.html';
    }
});

generateBtn.addEventListener('click', async () => {
    errorDiv.textContent = '';
    resultDiv.classList.remove('show');

    const longValue = parseInt(longitud.value);
    
    if (longValue < 4 || longValue > 128) {
        errorDiv.textContent = 'La longitud debe estar entre 4 y 128';
        return;
    }

    if (!mayusculas.checked && !minusculas.checked && !digitos.checked && !simbolos.checked) {
        errorDiv.textContent = 'Selecciona al menos una opción';
        return;
    }

    generateBtn.disabled = true;
    generateBtn.textContent = 'Generando...';

    try {
        const result = await new Promise((resolve) => {
            browser.storage.local.get(['authToken'], resolve);
        });

        const response = await fetch('https://ragnarok-uegm.onrender.com/generate-password', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${result.authToken}`
            },
            body: JSON.stringify({
                longitud: longValue,
                mayusculas: mayusculas.checked,
                minusculas: minusculas.checked,
                digitos: digitos.checked,
                simbolos: simbolos.checked
            })
        });

        console.log('Response status:', response.status);

        if (!response.ok) {
            throw new Error(`Error ${response.status}`);
        }

        const data = await response.json();
        generatedPassword = data.password || data.contraseña;
        
        passwordDisplay.textContent = generatedPassword;
        resultDiv.classList.add('show');
    } catch (error) {
        console.error('Error:', error);
        errorDiv.textContent = 'Error al generar contraseña: ' + error.message;
    } finally {
        generateBtn.disabled = false;
        generateBtn.textContent = 'Generar Contraseña';
    }
});

copyBtn.addEventListener('click', () => {
    navigator.clipboard.writeText(generatedPassword).then(() => {
        copyBtn.textContent = '✓ Copiado!';
        setTimeout(() => {
            copyBtn.textContent = 'Copiar al Portapapeles';
        }, 2000);
    }).catch(() => {
        alert('Error al copiar');
    });
});
