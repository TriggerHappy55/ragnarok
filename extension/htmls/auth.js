const API_URL = 'https://ragnarok-uegm.onrender.com';

console.log('auth.js loaded');

// DOM Elements
const loginForm = document.getElementById('loginForm');
const registerForm = document.getElementById('registerForm');
const toggleLink = document.getElementById('toggleLink');
const toggleText = document.getElementById('toggleText');

console.log('DOM Elements:', { loginForm, registerForm, toggleLink, toggleText });

// Login elements
const loginEmailInput = document.getElementById('loginEmail');
const loginPasswordInput = document.getElementById('loginPassword');
const loginBtn = document.getElementById('loginBtn');
const loginError = document.getElementById('loginError');

// Register elements
const registerNameInput = document.getElementById('registerName');
const registerEmailInput = document.getElementById('registerEmail');
const registerPasswordInput = document.getElementById('registerPassword');
const registerPasswordConfirmInput = document.getElementById('registerPasswordConfirm');
const registerBtn = document.getElementById('registerBtn');
const registerError = document.getElementById('registerError');
const registerSuccess = document.getElementById('registerSuccess');

// Redirect if already logged in
browser.storage.local.get(['authToken'], (result) => {
    if (result.authToken) {
        window.location.href = './popup.html';
    }
});

// Toggle between login and register
toggleLink.addEventListener('click', () => {
    loginForm.classList.toggle('hidden');
    registerForm.classList.toggle('hidden');
    
    if (loginForm.classList.contains('hidden')) {
        toggleText.innerHTML = 'Already have an account? <a id="toggleLink">Login</a>';
    } else {
        toggleText.innerHTML = "Don't have an account? <a id=\"toggleLink\">Register</a>";
    }
    
    // Re-attach click listener
    document.getElementById('toggleLink').addEventListener('click', arguments.callee);
});

// LOGIN HANDLER
loginBtn.addEventListener('click', async () => {
    console.log('Login button clicked');
    loginError.textContent = '';
    const email = loginEmailInput.value.trim();
    const password = loginPasswordInput.value.trim();

    console.log('Login attempt with:', { email, password });

    if (!email || !password) {
        loginError.textContent = 'Please fill in all fields';
        return;
    }

    loginBtn.disabled = true;
    loginBtn.textContent = 'Loading...';

    try {
        console.log('Fetching:', `${API_URL}/login`);
        const response = await fetch(`${API_URL}/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ email, password })
        });

        console.log('Response status:', response.status);

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.message || 'Login failed');
        }

        const data = await response.json();
        
        // Save token and user info
        await browser.storage.local.set({
            authToken: data.token || data.access_token,
            user: data.user
        });

        window.location.href = './popup.html';
    } catch (error) {
        console.error('Login error:', error);
        loginError.textContent = 'Error: ' + error.message;
        loginBtn.disabled = false;
        loginBtn.textContent = 'Login';
    }
});

// REGISTER HANDLER
registerBtn.addEventListener('click', async () => {
    console.log('Register button clicked');
    registerError.textContent = '';
    registerSuccess.textContent = '';
    
    const name = registerNameInput.value.trim();
    const email = registerEmailInput.value.trim();
    const password = registerPasswordInput.value.trim();
    const passwordConfirm = registerPasswordConfirmInput.value.trim();

    console.log('Register attempt with:', { name, email, password: '***' });

    if (!name || !email || !password || !passwordConfirm) {
        registerError.textContent = 'Please fill in all fields';
        return;
    }

    if (password !== passwordConfirm) {
        registerError.textContent = 'Passwords do not match';
        return;
    }

    if (password.length < 6) {
        registerError.textContent = 'Password must be at least 6 characters';
        return;
    }

    registerBtn.disabled = true;
    registerBtn.textContent = 'Loading...';

    try {
        console.log('Fetching:', `${API_URL}/register`);
        const response = await fetch(`${API_URL}/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ nombre: name, email, password })
        });

        console.log('Response status:', response.status);

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.message || 'Registration failed');
        }

        registerSuccess.textContent = 'Registration successful! Redirecting to login...';
        
        // Clear form and switch to login
        setTimeout(() => {
            registerNameInput.value = '';
            registerEmailInput.value = '';
            registerPasswordInput.value = '';
            registerPasswordConfirmInput.value = '';
            loginForm.classList.remove('hidden');
            registerForm.classList.add('hidden');
            toggleText.innerHTML = "Don't have an account? <a id=\"toggleLink\">Register</a>";
            document.getElementById('toggleLink').addEventListener('click', arguments.callee);
            loginBtn.disabled = false;
            loginBtn.textContent = 'Login';
        }, 1500);
    } catch (error) {
        console.error('Register error:', error);
        registerError.textContent = 'Error: ' + error.message;
        registerBtn.disabled = false;
        registerBtn.textContent = 'Register';
    }
});

// Allow login/register with Enter key
loginPasswordInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        loginBtn.click();
    }
});

registerPasswordConfirmInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        registerBtn.click();
    }
});

console.log('auth.js setup complete');
