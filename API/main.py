from fastapi import FastAPI, HTTPException, Cookie, Response
from pydantic import BaseModel
from typing import Optional, List
import json
import base64
import os
import uuid
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import hashlib

app = FastAPI()

# Diccionario para almacenar sesiones activas
sesiones_activas = {}

# Modelos de datos
class User(BaseModel):
    email: str
    nombre: str
    password: str

class UserUpdate(BaseModel):
    email: Optional[str] = None
    nombre: Optional[str] = None

class PasswordChange(BaseModel):
    password_actual: str
    password_nueva: str

class Password(BaseModel):
    userid: int
    url: str
    email: str
    password: str
    autologin: bool = False
    comentario: Optional[str] = None

class PasswordUpdate(BaseModel):
    password: Optional[str] = None
    autologin: Optional[bool] = None

class LoginData(BaseModel):
    email: str
    password: str

# Funciones de encriptación
def generar_clave_usuario(password_usuario: str, salt: bytes) -> bytes:
    """Genera una clave única para cada usuario basada en su contraseña"""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password_usuario.encode()))
    return key

def encriptar_password(password: str, clave: bytes) -> str:
    """Encripta una contraseña usando Fernet"""
    f = Fernet(clave)
    encrypted = f.encrypt(password.encode())
    return encrypted.decode()

def desencriptar_password(password_encriptada: str, clave: bytes) -> str:
    """Desencripta una contraseña usando Fernet"""
    try:
        f = Fernet(clave)
        decrypted = f.decrypt(password_encriptada.encode())
        return decrypted.decode()
    except:
        return "[ERROR: No se puede desencriptar]"

def hash_password(password: str, salt: str) -> str:
    """Hashea la contraseña del usuario para almacenamiento seguro"""
    combinado = password + salt
    return hashlib.sha256(combinado.encode()).hexdigest()

def verificar_password(password: str, salt: str, hash_almacenado: str) -> bool:
    """Verifica si la contraseña proporcionada coincide con el hash almacenado"""
    return hash_password(password, salt) == hash_almacenado

# Funciones para manejar los JSONs
def leer_json_users():
    try:
        with open('users.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"users": []}

def guardar_json_users(datos):
    with open('users.json', 'w') as f:
        json.dump(datos, f, indent=2)

def leer_json_passwords():
    try:
        with open('passwords.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"passwords": []}

def guardar_json_passwords(datos):
    with open('passwords.json', 'w') as f:
        json.dump(datos, f, indent=2)

# Endpoints de Usuarios
@app.post("/register")
def registrar_usuario(user: User):
    datos_users = leer_json_users()
    
    for usuario in datos_users["users"]:
        if usuario["email"] == user.email:
            raise HTTPException(status_code=400, detail="Email ya registrado")
    
    if datos_users["users"]:
        nuevo_uid = max(u["uid"] for u in datos_users["users"]) + 1
    else:
        nuevo_uid = 1
    
    # Generar un salt único para este usuario
    salt = base64.urlsafe_b64encode(os.urandom(16)).decode()
    
    # Hashear la contraseña del usuario (NO guardarla en texto plano)
    password_hash = hash_password(user.password, salt)
    
    nuevo_usuario = {
        "uid": nuevo_uid,
        "email": user.email,
        "nombre": user.nombre,
        "password_hash": password_hash,  # Guardamos el hash, no la contraseña
        "salt": salt
    }
    
    datos_users["users"].append(nuevo_usuario)
    guardar_json_users(datos_users)
    
    return {
        "mensaje": "Usuario registrado correctamente", 
        "uid": nuevo_uid,
        "email": user.email,
        "nombre": user.nombre
    }

@app.post("/login")
def login(login_data: LoginData, response: Response):
    datos_users = leer_json_users()
    
    for usuario in datos_users["users"]:
        if usuario["email"] == login_data.email:
            # Verificar la contraseña usando el hash
            if verificar_password(login_data.password, usuario["salt"], usuario["password_hash"]):
                # Generar clave de encriptación para este usuario usando su contraseña
                salt_bytes = base64.urlsafe_b64decode(usuario["salt"])
                clave = generar_clave_usuario(login_data.password, salt_bytes)
                
                # Crear token de sesión único
                token_sesion = str(uuid.uuid4())
                
                # Guardar la clave en memoria asociada al token
                sesiones_activas[token_sesion] = {
                    "uid": usuario["uid"],
                    "clave": clave,
                    "nombre": usuario["nombre"]
                }
                
                # Establecer cookie con el token
                response.set_cookie(
                    key="session_token",
                    value=token_sesion,
                    httponly=True,
                    max_age=3600,
                    secure=False,
                    samesite="lax"
                )
                
                return {
                    "mensaje": "Login exitoso",
                    "uid": usuario["uid"],
                    "nombre": usuario["nombre"],
                    "email": usuario["email"]
                }
    
    raise HTTPException(status_code=401, detail="Email o contraseña incorrectos")

@app.post("/logout")
def logout(response: Response, session_token: Optional[str] = Cookie(None)):
    """Cerrar sesión"""
    if session_token and session_token in sesiones_activas:
        del sesiones_activas[session_token]
    
    response.delete_cookie("session_token")
    return {"mensaje": "Sesión cerrada correctamente"}

def verificar_sesion(session_token: Optional[str] = Cookie(None)):
    """Función auxiliar para verificar la sesión"""
    if not session_token or session_token not in sesiones_activas:
        raise HTTPException(status_code=401, detail="No hay sesión activa")
    return sesiones_activas[session_token]

@app.put("/users/{userid}")
def actualizar_usuario(userid: int, user_update: UserUpdate, session_token: Optional[str] = Cookie(None)):
    """Actualizar solo nombre y/o email del usuario"""
    sesion = verificar_sesion(session_token)
    if sesion["uid"] != userid:
        raise HTTPException(status_code=403, detail="No tienes permiso para modificar este usuario")
    
    datos_users = leer_json_users()
    
    for i, usuario in enumerate(datos_users["users"]):
        if usuario["uid"] == userid:
            if user_update.email is not None:
                for u in datos_users["users"]:
                    if u["email"] == user_update.email and u["uid"] != userid:
                        raise HTTPException(status_code=400, detail="Email ya está en uso")
                datos_users["users"][i]["email"] = user_update.email
            
            if user_update.nombre is not None:
                datos_users["users"][i]["nombre"] = user_update.nombre
            
            guardar_json_users(datos_users)
            
            return {
                "mensaje": "Usuario actualizado correctamente",
                "uid": datos_users["users"][i]["uid"],
                "email": datos_users["users"][i]["email"],
                "nombre": datos_users["users"][i]["nombre"]
            }
    
    raise HTTPException(status_code=404, detail="Usuario no encontrado")

@app.post("/users/{userid}/change-password")
def cambiar_password(userid: int, password_change: PasswordChange, session_token: Optional[str] = Cookie(None)):
    """Cambiar la contraseña del usuario"""
    sesion = verificar_sesion(session_token)
    if sesion["uid"] != userid:
        raise HTTPException(status_code=403, detail="No tienes permiso para cambiar esta contraseña")
    
    datos_users = leer_json_users()
    
    for i, usuario in enumerate(datos_users["users"]):
        if usuario["uid"] == userid:
            # Verificar contraseña actual usando el hash
            if not verificar_password(password_change.password_actual, usuario["salt"], usuario["password_hash"]):
                raise HTTPException(status_code=401, detail="Contraseña actual incorrecta")
            
            # Generar nuevo salt para la nueva contraseña
            nuevo_salt = base64.urlsafe_b64encode(os.urandom(16)).decode()
            
            # Hashear la nueva contraseña
            nuevo_password_hash = hash_password(password_change.password_nueva, nuevo_salt)
            
            # Actualizar usuario con nueva contraseña y salt
            datos_users["users"][i]["password_hash"] = nuevo_password_hash
            datos_users["users"][i]["salt"] = nuevo_salt
            
            guardar_json_users(datos_users)
            
            # Nota: Al cambiar la contraseña, se genera un nuevo salt y por lo tanto
            # una nueva clave de encriptación. Esto significa que las contraseñas
            # guardadas anteriormente ya no podrán desencriptarse.
            # En un sistema real, habría que re-encriptar todas las contraseñas
            # con la nueva clave o mantener un historial de claves.
            
            return {
                "mensaje": "Contraseña cambiada correctamente",
                "uid": userid,
                "nota": "Las contraseñas guardadas anteriormente ya no son accesibles con la nueva contraseña"
            }
    
    raise HTTPException(status_code=404, detail="Usuario no encontrado")

@app.get("/users/me")
def obtener_mi_usuario(session_token: Optional[str] = Cookie(None)):
    """Obtener información del usuario actual"""
    sesion = verificar_sesion(session_token)
    datos_users = leer_json_users()
    
    for usuario in datos_users["users"]:
        if usuario["uid"] == sesion["uid"]:
            return {
                "uid": usuario["uid"],
                "email": usuario["email"],
                "nombre": usuario["nombre"]
            }
    
    raise HTTPException(status_code=404, detail="Usuario no encontrado")

# Endpoints de Contraseñas de sitios web
@app.get("/passwords")
def obtener_mis_passwords(session_token: Optional[str] = Cookie(None)):
    """Ver todas mis contraseñas (desencriptadas automáticamente)"""
    sesion = verificar_sesion(session_token)
    datos_pass = leer_json_passwords()
    
    # Filtrar contraseñas del usuario y desencriptarlas
    passwords_usuario = []
    for p in datos_pass["passwords"]:
        if p["userid"] == sesion["uid"]:
            password_desc = p.copy()
            password_desc["password"] = desencriptar_password(p["password"], sesion["clave"])
            passwords_usuario.append(password_desc)
    
    return passwords_usuario

@app.get("/passwords/{id}")
def obtener_password(id: int, session_token: Optional[str] = Cookie(None)):
    """Obtener una contraseña específica desencriptada"""
    sesion = verificar_sesion(session_token)
    datos_pass = leer_json_passwords()
    
    for password in datos_pass["passwords"]:
        if password["id"] == id:
            if password["userid"] != sesion["uid"]:
                raise HTTPException(status_code=403, detail="No tienes permiso para ver esta contraseña")
            
            password_desc = password.copy()
            password_desc["password"] = desencriptar_password(password["password"], sesion["clave"])
            return password_desc
    
    raise HTTPException(status_code=404, detail="Contraseña no encontrada")

@app.post("/passwords")
def crear_password(password: Password, session_token: Optional[str] = Cookie(None)):
    """Crear una nueva contraseña (se guarda encriptada automáticamente)"""
    sesion = verificar_sesion(session_token)
    
    # Asegurar que la contraseña pertenece al usuario de la sesión
    if password.userid != sesion["uid"]:
        raise HTTPException(status_code=403, detail="No puedes crear contraseñas para otro usuario")
    
    datos_pass = leer_json_passwords()
    
    # Crear nuevo ID para la contraseña
    if datos_pass["passwords"]:
        nuevo_id = max(p["id"] for p in datos_pass["passwords"]) + 1
    else:
        nuevo_id = 1
    
    # Encriptar la contraseña antes de guardarla usando la clave de la sesión
    password_encriptada = encriptar_password(password.password, sesion["clave"])
    
    nueva_password = {
        "id": nuevo_id,
        "userid": sesion["uid"],
        "url": password.url,
        "email": password.email,
        "password": password_encriptada,
        "autologin": password.autologin,
        "comentario": password.comentario
    }
    
    datos_pass["passwords"].append(nueva_password)
    guardar_json_passwords(datos_pass)
    
    # Devolver la contraseña desencriptada
    respuesta = nueva_password.copy()
    respuesta["password"] = password.password
    return respuesta

@app.patch("/passwords/{id}")
def actualizar_password(id: int, password_update: PasswordUpdate, session_token: Optional[str] = Cookie(None)):
    """Actualizar SOLO la contraseña y/o autologin de un sitio web"""
    sesion = verificar_sesion(session_token)
    datos_pass = leer_json_passwords()
    
    for i, p in enumerate(datos_pass["passwords"]):
        if p["id"] == id:
            if p["userid"] != sesion["uid"]:
                raise HTTPException(status_code=403, detail="No tienes permiso para modificar esta contraseña")
            
            # Actualizar SOLO los campos permitidos
            if password_update.password is not None:
                datos_pass["passwords"][i]["password"] = encriptar_password(password_update.password, sesion["clave"])
            
            if password_update.autologin is not None:
                datos_pass["passwords"][i]["autologin"] = password_update.autologin
            
            guardar_json_passwords(datos_pass)
            
            # Devolver la contraseña actualizada (desencriptada)
            password_actualizada = datos_pass["passwords"][i].copy()
            password_actualizada["password"] = password_update.password or desencriptar_password(p["password"], sesion["clave"])
            
            return {
                "mensaje": "Contraseña actualizada correctamente",
                "id": password_actualizada["id"],
                "url": password_actualizada["url"],
                "email": password_actualizada["email"],
                "autologin": password_actualizada["autologin"],
                "comentario": password_actualizada.get("comentario")
            }
    
    raise HTTPException(status_code=404, detail="Contraseña no encontrada")

@app.delete("/passwords/{id}")
def eliminar_password(id: int, session_token: Optional[str] = Cookie(None)):
    """Eliminar una contraseña"""
    sesion = verificar_sesion(session_token)
    datos_pass = leer_json_passwords()
    
    password_encontrada = None
    for p in datos_pass["passwords"]:
        if p["id"] == id:
            password_encontrada = p
            break
    
    if not password_encontrada:
        raise HTTPException(status_code=404, detail="Contraseña no encontrada")
    
    if password_encontrada["userid"] != sesion["uid"]:
        raise HTTPException(status_code=403, detail="No tienes permiso para eliminar esta contraseña")
    
    datos_pass["passwords"] = [p for p in datos_pass["passwords"] if p["id"] != id]
    guardar_json_passwords(datos_pass)
    
    return {"mensaje": "Contraseña eliminada correctamente"}

@app.get("/autologin/{url}")
def verificar_autologin(url: str, session_token: Optional[str] = Cookie(None)):
    """Verificar autologin para una URL"""
    sesion = verificar_sesion(session_token)
    datos_pass = leer_json_passwords()
    
    for password in datos_pass["passwords"]:
        if password["url"] == url and password["userid"] == sesion["uid"]:
            return {
                "autologin": password["autologin"],
                "url": password["url"],
                "email": password["email"],
                "password": desencriptar_password(password["password"], sesion["clave"]) if password["autologin"] else None
            }
    
    return {"autologin": False}

@app.get("/debug/sesiones")
def ver_sesiones():
    """Endpoint SOLO para depuración - muestra sesiones activas"""
    return {token: {"uid": data["uid"], "nombre": data["nombre"]} for token, data in sesiones_activas.items()}

@app.get("/debug/passwords-raw")
def ver_passwords_raw():
    """Endpoint SOLO para depuración - muestra las contraseñas encriptadas"""
    return leer_json_passwords()

@app.get("/debug/users-raw")
def ver_users_raw():
    """Endpoint SOLO para depuración - muestra los usuarios (sin contraseñas en texto plano)"""
    datos = leer_json_users()
    # Ocultamos los hashes y salts para seguridad
    for user in datos["users"]:
        user["password_hash"] = "[OCULTO]"
        user["salt"] = "[OCULTO]"
    return datos

@app.get("/")
def home():
    return {
        "mensaje": "API de contraseñas multi-usuario CON ENCRIPTACIÓN AUTOMÁTICA",
        "nota": "Las contraseñas de los usuarios se guardan hasheadas, no en texto plano. Las contraseñas de sitios web se encriptan automáticamente con la clave derivada de la contraseña del usuario.",
        "endpoints": {
            "POST /register": "Registrar nuevo usuario (contraseña hasheada automáticamente)",
            "POST /login": "Iniciar sesión (establece cookie automática)",
            "POST /logout": "Cerrar sesión",
            "GET /users/me": "Ver mi información",
            "PUT /users/{userid}": "Actualizar mi nombre/email",
            "POST /users/{userid}/change-password": "Cambiar mi contraseña",
            
            "GET /passwords": "Ver TODAS mis contraseñas (desencriptadas automáticamente)",
            "POST /passwords": "Crear nueva contraseña (se encripta automáticamente)",
            "GET /passwords/{id}": "Ver una contraseña específica",
            "PATCH /passwords/{id}": "Actualizar password/autologin",
            "DELETE /passwords/{id}": "Eliminar contraseña",
            "GET /autologin/{url}": "Verificar autologin para una URL"
        }
    }
