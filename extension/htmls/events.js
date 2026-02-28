export function agregarEventoClick(elemento, objeto) {
    elemento.addEventListener("click", () => {
        browser.storage.local.set({ selectedLoginId: objeto.id });
        window.location.href = "./logins.html";
    });
}
