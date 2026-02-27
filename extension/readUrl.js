document.addEventListener("DOMContentLoaded", async () => {
  const mensaje = document.getElementById("mensaje");

  // Obtener la pestaña activa
  const tabs = await browser.tabs.query({
    active: true,
    currentWindow: true
  });

  const url = tabs[0].url;

  // Extraer el dominio (ej: amazon.com)
  const dominio = new URL(url).hostname;

  // Quitar "www."
  const limpio = dominio.replace("www.", "");

  mensaje.textContent = `Bienvenido a ${limpio}`;
});
