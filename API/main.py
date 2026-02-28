from fastapi import FastAPI, HTTPException, Cookie, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import json
import base64
import os
import uuid
import secrets
import string
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import hashlib

app = FastAPI()

# Configurar CORS para permitir cookies desde el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # Ajusta según tu frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

class PasswordGeneratorRequest(BaseModel):
    longitud: int
    mayusculas: bool = False
    minusculas: bool = False
    digitos: bool = False
    simbolos: bool = False

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
    except Exception as e:
        print(f"Error desencriptando: {e}")
        return "[ERROR: No se puede desencriptar]"

def hash_password(password: str, salt: str) -> str:
    """Hashea la contraseña del usuario para almacenamiento seguro"""
    combinado = password + salt
    return hashlib.sha256(combinado.encode()).hexdigest()

def verificar_password(password: str, salt: str, hash_almacenado: str) -> bool:
    """Verifica si la contraseña proporcionada coincide con el hash almacenado"""
    return hash_password(password, salt) == hash_almacenado

# Función para generar contraseñas seguras
def generar_password_seguro(longitud: int, mayusculas: bool, minusculas: bool, digitos: bool, simbolos: bool) -> str:
    """
    Genera una contraseña aleatoria segura basada en los criterios especificados.
    
    Args:
        longitud: Número de caracteres de la contraseña
        mayusculas: Incluir letras mayúsculas (A-Z)
        minusculas: Incluir letras minúsculas (a-z)
        digitos: Incluir dígitos (0-9)
        simbolos: Incluir símbolos especiales (!@#$%^&*()_+-=[]{}|;:,.<>?)
    
    Returns:
        Una contraseña aleatoria que cumple con los criterios especificados
    """
    # Validar que al menos un tipo de carácter esté seleccionado
    if not any([mayusculas, minusculas, digitos, simbolos]):
        raise ValueError("Debes seleccionar al menos un tipo de carácter")
    
    # Validar que la longitud sea positiva
    if longitud < 1:
        raise ValueError("La longitud debe ser al menos 1")
    
    # Validar que la longitud no sea excesiva (por seguridad)
    if longitud > 128:
        raise ValueError("La longitud máxima permitida es 128 caracteres")
    
    # Construir el conjunto de caracteres disponibles
    caracteres = ""
    
    if mayusculas:
        caracteres += string.ascii_uppercase
    if minusculas:
        caracteres += string.ascii_lowercase
    if digitos:
        caracteres += string.digits
    if simbolos:
        caracteres += "!@#$%^&*()_+-=[]{}|;:,.<>?"
    
    # Asegurar que la contraseña contenga al menos un carácter de cada tipo seleccionado
    password = []
    
    # Función para obtener un carácter aleatorio de un conjunto específico
    def get_random_char(char_set):
        return secrets.choice(char_set)
    
    # Añadir al menos un carácter de cada tipo seleccionado
    if mayusculas:
        password.append(get_random_char(string.ascii_uppercase))
    if minusculas:
        password.append(get_random_char(string.ascii_lowercase))
    if digitos:
        password.append(get_random_char(string.digits))
    if simbolos:
        password.append(get_random_char("!@#$%^&*()_+-=[]{}|;:,.<>?"))
    
    # Completar el resto de la longitud con caracteres aleatorios del conjunto completo
    caracteres_restantes = longitud - len(password)
    for _ in range(caracteres_restantes):
        password.append(secrets.choice(caracteres))
    
    # Mezclar la contraseña para evitar que los primeros caracteres sean siempre del mismo tipo
    secrets.SystemRandom().shuffle(password)
    
    # Unir la lista en una cadena
    return ''.join(password)

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
def registrar_usuario(user: User, response: Response):
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
    
    # Hashear la contraseña del usuario
    password_hash = hash_password(user.password, salt)
    
    nuevo_usuario = {
        "uid": nuevo_uid,
        "email": user.email,
        "nombre": user.nombre,
        "password_hash": password_hash,
        "salt": salt
    }
    
    datos_users["users"].append(nuevo_usuario)
    guardar_json_users(datos_users)
    
    # Auto-login después del registro
    return login(LoginData(email=user.email, password=user.password), response)

@app.post("/login")
def login(login_data: LoginData, response: Response):
    datos_users = leer_json_users()
    
    for usuario in datos_users["users"]:
        if usuario["email"] == login_data.email:
            # Verificar la contraseña usando el hash
            if verificar_password(login_data.password, usuario["salt"], usuario["password_hash"]):
                # Generar clave de encriptación para este usuario
                salt_bytes = base64.urlsafe_b64decode(usuario["salt"])
                clave = generar_clave_usuario(login_data.password, salt_bytes)
                
                # Crear token de sesión único
                token_sesion = str(uuid.uuid4())
                
                # Guardar la clave en memoria asociada al token
                sesiones_activas[token_sesion] = {
                    "uid": usuario["uid"],
                    "clave": clave,
                    "nombre": usuario["nombre"],
                    "email": usuario["email"]
                }
                
                # Establecer cookie con el token
                response.set_cookie(
                    key="session_token",
                    value=token_sesion,
                    httponly=True,
                    max_age=3600,
                    secure=False,  # En producción, cambiar a True (HTTPS)
                    samesite="lax",
                    path="/"  # Importante: disponible en toda la API
                )
                
                print(f"Login exitoso - Token: {token_sesion}")  # Debug
                print(f"Sesiones activas: {list(sesiones_activas.keys())}")  # Debug
                
                return {
                    "mensaje": "Login exitoso",
                    "uid": usuario["uid"],
                    "nombre": usuario["nombre"],
                    "email": usuario["email"],
                    "token": token_sesion  # Opcional: devolver token para depuración
                }
    
    raise HTTPException(status_code=401, detail="Email o contraseña incorrectos")

@app.post("/logout")
def logout(response: Response, session_token: Optional[str] = Cookie(None)):
    """Cerrar sesión"""
    print(f"Logout - Token recibido: {session_token}")  # Debug
    
    if session_token and session_token in sesiones_activas:
        del sesiones_activas[session_token]
        print(f"Sesión eliminada. Sesiones restantes: {list(sesiones_activas.keys())}")  # Debug
    
    response.delete_cookie("session_token", path="/")
    return {"mensaje": "Sesión cerrada correctamente"}

def verificar_sesion(session_token: Optional[str] = Cookie(None)):
    """Función auxiliar para verificar la sesión"""
    print(f"Verificando sesión - Token recibido: {session_token}")  # Debug
    print(f"Sesiones activas: {list(sesiones_activas.keys())}")  # Debug
    
    if not session_token:
        raise HTTPException(
            status_code=401, 
            detail="No hay token de sesión. Por favor, inicia sesión primero."
        )
    
    if session_token not in sesiones_activas:
        raise HTTPException(
            status_code=401, 
            detail="Sesión inválida o expirada. Por favor, inicia sesión nuevamente."
        )
    
    return sesiones_activas[session_token]

@app.get("/check-session")
def check_session(session_token: Optional[str] = Cookie(None)):
    """Verificar si la sesión es válida"""
    try:
        sesion = verificar_sesion(session_token)
        return {
            "valida": True,
            "uid": sesion["uid"],
            "nombre": sesion["nombre"],
            "email": sesion["email"]
        }
    except HTTPException:
        return {"valida": False}

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
            
            # Nota: Al cambiar la contraseña, se genera un nuevo salt
            # Las contraseñas guardadas anteriormente ya no podrán desencriptarse
            
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
    return {
        "uid": sesion["uid"],
        "email": sesion["email"],
        "nombre": sesion["nombre"]
    }

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
    
    datos_pass = leer_json_passwords()
    
    # Crear nuevo ID para la contraseña
    if datos_pass["passwords"]:
        nuevo_id = max(p["id"] for p in datos_pass["passwords"]) + 1
    else:
        nuevo_id = 1
    
    # Encriptar la contraseña antes de guardarla
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

# NUEVO ENDPOINT: Generador de contraseñas seguras
@app.post("/generate-password")
def generar_password(request: PasswordGeneratorRequest):
    """
    Genera una contraseña segura basada en los criterios especificados.
    Este endpoint NO requiere autenticación y NO guarda la contraseña generada.
    """
    try:
        # Validar que la longitud sea razonable
        if request.longitud < 4:
            raise HTTPException(
                status_code=400, 
                detail="La longitud mínima es 4 caracteres por seguridad"
            )
        
        if request.longitud > 128:
            raise HTTPException(
                status_code=400, 
                detail="La longitud máxima permitida es 128 caracteres"
            )
        
        # Validar que al menos un tipo de carácter esté seleccionado
        if not any([request.mayusculas, request.minusculas, request.digitos, request.simbolos]):
            raise HTTPException(
                status_code=400, 
                detail="Debes seleccionar al menos un tipo de carácter (mayúsculas, minúsculas, dígitos o símbolos)"
            )
        
        # Generar la contraseña
        password = generar_password_seguro(
            longitud=request.longitud,
            mayusculas=request.mayusculas,
            minusculas=request.minusculas,
            digitos=request.digitos,
            simbolos=request.simbolos
        )
        
        # Calcular la entropía aproximada de la contraseña
        tipos_seleccionados = sum([request.mayusculas, request.minusculas, request.digitos, request.simbolos])
        if tipos_seleccionados == 1:
            if request.mayusculas:
                tamano_conjunto = 26
            elif request.minusculas:
                tamano_conjunto = 26
            elif request.digitos:
                tamano_conjunto = 10
            else:  # simbolos
                tamano_conjunto = 27  # Aproximadamente
        elif tipos_seleccionados == 2:
            if request.mayusculas and request.minusculas:
                tamano_conjunto = 52
            elif request.mayusculas and request.digitos:
                tamano_conjunto = 36
            elif request.mayusculas and request.simbolos:
                tamano_conjunto = 53
            elif request.minusculas and request.digitos:
                tamano_conjunto = 36
            elif request.minusculas and request.simbolos:
                tamano_conjunto = 53
            else:  # digitos y simbolos
                tamano_conjunto = 37
        elif tipos_seleccionados == 3:
            if request.mayusculas and request.minusculas and request.digitos:
                tamano_conjunto = 62
            elif request.mayusculas and request.minusculas and request.simbolos:
                tamano_conjunto = 79
            elif request.mayusculas and request.digitos and request.simbolos:
                tamano_conjunto = 63
            else:  # minusculas, digitos y simbolos
                tamano_conjunto = 63
        else:  # todos seleccionados
            tamano_conjunto = 89  # 26+26+10+27 aprox
        
        entropia = request.longitud * (tamano_conjunto.bit_length())
        
        # Determinar la fortaleza de la contraseña
        if entropia < 30:
            fortaleza = "Muy débil"
        elif entropia < 50:
            fortaleza = "Débil"
        elif entropia < 70:
            fortaleza = "Moderada"
        elif entropia < 90:
            fortaleza = "Fuerte"
        else:
            fortaleza = "Muy fuerte"
        
        return {
            "password": password,
            "longitud": request.longitud,
            "tipos_incluidos": {
                "mayusculas": request.mayusculas,
                "minusculas": request.minusculas,
                "digitos": request.digitos,
                "simbolos": request.simbolos
            },
            "entropia_aproximada": f"{entropia} bits",
            "fortaleza": fortaleza,
            "mensaje": "Contraseña generada correctamente. No se ha guardado en ningún lado."
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al generar la contraseña: {str(e)}")

# Endpoint adicional: Obtener fortaleza de una contraseña existente
@app.post("/check-password-strength")
def check_password_strength(password: str, request: Optional[PasswordGeneratorRequest] = None):
    """
    Analiza la fortaleza de una contraseña existente.
    Si no se proporcionan los criterios, se asume que se usaron todos los tipos de caracteres.
    """
    if not password:
        raise HTTPException(status_code=400, detail="Debes proporcionar una contraseña")
    
    longitud = len(password)
    
    # Determinar qué tipos de caracteres contiene la contraseña
    tiene_mayusculas = any(c.isupper() for c in password)
    tiene_minusculas = any(c.islower() for c in password)
    tiene_digitos = any(c.isdigit() for c in password)
    tiene_simbolos = any(not c.isalnum() for c in password)
    
    # Calcular tamaño del conjunto basado en los tipos presentes
    tamano_conjunto = 0
    if tiene_mayusculas:
        tamano_conjunto += 26
    if tiene_minusculas:
        tamano_conjunto += 26
    if tiene_digitos:
        tamano_conjunto += 10
    if tiene_simbolos:
        tamano_conjunto += 27  # Aproximado
    
    entropia = longitud * (tamano_conjunto.bit_length())
    
    # Determinar fortaleza
    if entropia < 30:
        fortaleza = "Muy débil"
    elif entropia < 50:
        fortaleza = "Débil"
    elif entropia < 70:
        fortaleza = "Moderada"
    elif entropia < 90:
        fortaleza = "Fuerte"
    else:
        fortaleza = "Muy fuerte"
    
    return {
        "longitud": longitud,
        "tipos_detectados": {
            "mayusculas": tiene_mayusculas,
            "minusculas": tiene_minusculas,
            "digitos": tiene_digitos,
            "simbolos": tiene_simbolos
        },
        "entropia_aproximada": f"{entropia} bits",
        "fortaleza": fortaleza,
        "recomendacion": "Usa mayúsculas, minúsculas, números y símbolos para mayor seguridad" if entropia < 50 else "Buena contraseña"
    }

# Endpoints de depuración
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
    """Endpoint SOLO para depuración - muestra los usuarios"""
    datos = leer_json_users()
    # Ocultamos los hashes y salts para seguridad
    for user in datos["users"]:
        user["password_hash"] = "[OCULTO]"
        user["salt"] = "[OCULTO]"
    return datos

@app.get("/")
def home():
    return {
        "mensaje": "API de contraseñas multi-usuario",
        "nota": "Las sesiones se manejan automáticamente con cookies. No necesitas enviar tokens manualmente.",
        "instrucciones": {
            "registro": "POST /register - Crea usuario y inicia sesión automáticamente",
            "login": "POST /login - Inicia sesión (establece cookie automática)",
            "verificar_sesion": "GET /check-session - Verifica si la cookie es válida",
            "ver_passwords": "GET /passwords - Obtiene tus contraseñas (usa la cookie automáticamente)"
        },
        "nuevos_endpoints_generador": {
            "POST /generate-password": "Genera una contraseña segura (NO requiere autenticación)",
            "POST /check-password-strength": "Analiza la fortaleza de una contraseña existente"
        },
        "ejemplo_uso_generador": {
            "url": "POST /generate-password",
            "body": {
                "longitud": 12,
                "mayusculas": True,
                "minusculas": True,
                "digitos": True,
                "simbolos": True
            }
        }
    }
