const emailDisplay = document.getElementById('emailDisplay');
const cancelBtn = document.getElementById('cancelBtn');
const confirmBtn = document.getElementById('confirmBtn');

let credentialsData = null;

// Recibir datos del background script
document.addEventListener('DOMContentLoaded', async () => {
    try {
        const response = await browser.runtime.sendMessage({
            action: 'getAutofillData'
        });
        
        if (response.data) {
            credentialsData = response.data;
            emailDisplay.textContent = response.data.email || 'No disponible';
        }
    } catch (error) {
        console.error('Error getting autofill data:', error);
    }
});

cancelBtn.addEventListener('click', () => {
    window.close();
});

confirmBtn.addEventListener('click', async () => {
    try {
        if (!credentialsData) {
            console.error('No credentials data available');
            return;
        }

        console.log('Sending autofill confirmation');
        await browser.runtime.sendMessage({
            action: 'autofillConfirmed',
            data: credentialsData
        });
        
        window.close();
    } catch (error) {
        console.error('Error confirming autofill:', error);
    }
});
