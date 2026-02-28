import { agregarEventoClick } from './events.js';

export function renderizarObjetos(lista, contenedor) {
    lista.forEach(obj => {
        const div = document.createElement("div");
        div.textContent = obj.website;
        div.classList.add("card");

        agregarEventoClick(div, obj);

        contenedor.appendChild(div);
    });
}
