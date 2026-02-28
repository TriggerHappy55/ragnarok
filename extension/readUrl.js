document.addEventListener("DOMContentLoaded", async () => {

	const mensaje = document.getElementById("mensaje");
	const boton = document.getElementById("cambiar");
	const casillaTexto = document.getElementById("input-text");

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
	
	let mostrandoUrl = true;

	boton.addEventListener("click", () =>{
		if(mostrandoUrl)
			mensaje.textContent="Bienvenida a ragnarok"
		else{
			const url = tabs[0].url;
			const host = new URL(url).hostname;
			const limpio = host.replace("www.", "");
			mensaje.textContent= `Bienvenida a ${limpio}`
		}
		mostrandoUrl = !mostrandoUrl;
	})
	casillaTexto.addEventListener("change", () =>{
		const texto = casillaTexto.value;
		mensaje.textContent = `Introdujiste ${texto}`
	})
});
