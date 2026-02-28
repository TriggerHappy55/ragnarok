from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import json

app = FastAPI()

# Modelo de datos
class Password(BaseModel):
    id: Optional[int] = None
    url: str
    email: str
    password: str
    autologin: bool = False
    comentario: Optional[str] = None

# Funciones para manejar el JSON
def leer_json():
    try:
        with open('database.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # Si el archivo no existe, crear estructura básica
        return {"passwords": []}

def guardar_json(datos):
    with open('database.json', 'w') as f:
        json.dump(datos, f, indent=2)

# Endpoints
@app.get("/")
def home():
    return {"mensaje": "API de contraseñas"}

@app.get("/passwords")
def obtener_todas():
    datos = leer_json()
    return datos["passwords"]

@app.get("/passwords/{id}")
def obtener_una(id: int):
    datos = leer_json()
    for password in datos["passwords"]:
        if password["id"] == id:
            return password
    raise HTTPException(status_code=404, detail="No encontrado")

@app.post("/passwords")
def crear_password(password: Password):
    datos = leer_json()
    
    # Crear nuevo ID (corregido para evitar IDs duplicados)
    if datos["passwords"]:
        nuevo_id = max(p["id"] for p in datos["passwords"]) + 1
    else:
        nuevo_id = 1
    
    nuevo = password.dict()
    nuevo["id"] = nuevo_id
    nuevo["autologin"] = False
    
    datos["passwords"].append(nuevo)
    guardar_json(datos)
    return nuevo

@app.put("/passwords/{id}")
def actualizar_password(id: int, password: Password):
    datos = leer_json()
    
    for i, p in enumerate(datos["passwords"]):
        if p["id"] == id:
            # CORREGIDO: Actualizar campo por campo, no reemplazar todo
            datos["passwords"][i]["url"] = password.url
            datos["passwords"][i]["email"] = password.email
            datos["passwords"][i]["password"] = password.password
            datos["passwords"][i]["comentario"] = password.comentario
            # El id y autologin se mantienen igual
            # datos["passwords"][i]["autologin"] se mantiene como estaba
            
            guardar_json(datos)
            return datos["passwords"][i]
    
    raise HTTPException(status_code=404, detail="No encontrado")

@app.delete("/passwords/{id}")
def eliminar_password(id: int):
    datos = leer_json()
    
    datos["passwords"] = [p for p in datos["passwords"] if p["id"] != id]
    guardar_json(datos)
    return {"mensaje": "Eliminado correctamente"}

@app.get("/autologin/{url}")
def verificar_autologin(url: str):
    datos = leer_json()
    for password in datos["passwords"]:
        if password["url"] == url:
            return {"autologin": True, "datos": password}
    return {"autologin": False}
