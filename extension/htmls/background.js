console.log('Background script loaded');

// Escuchar mensajes desde content scripts
browser.runtime.onMessage.addListener((request, sender, sendResponse) => {
    console.log('Message received:', request);
    sendResponse({ received: true });
});
