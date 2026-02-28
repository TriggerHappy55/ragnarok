from fastapi import FastAPI, HTTPException, Cookie, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Set
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
import glob
import shutil
from pathlib import Path

#Rutas relativas
API_DIR = Path(__file__).parent
SRC_DIR = API_DIR.parent / "src"

# Rutas de los archivos JSON en src (plantillas)
SRC_USERS_JSON = SRC_DIR / "users.json"
SRC_PASSWORDS_JSON = SRC_DIR / "passwords.json"

# Rutas de destino en api
API_USERS_JSON = API_DIR / "users.json"
API_PASSWORDS_JSON = API_DIR / "passwords.json"

# Copiar archivos siempre (sobrescribiendo)
def copiar_json_plantillas():
    """Copia los JSON de ../src a ../api sobrescribiendo siempre"""
    print("Copiando plantillas JSON (sobrescribiendo)...")

    # Copiar users.json (siempre)
    if SRC_USERS_JSON.exists():
        shutil.copy2(SRC_USERS_JSON, API_USERS_JSON)
        print(f"Copiado {SRC_USERS_JSON} a {API_USERS_JSON}")
    else:
        print(f"Plantilla {SRC_USERS_JSON} no encontrada")

    # Copiar passwords.json (siempre)
    if SRC_PASSWORDS_JSON.exists():
        shutil.copy2(SRC_PASSWORDS_JSON, API_PASSWORDS_JSON)
        print(f"Copiado {SRC_PASSWORDS_JSON} a {API_PASSWORDS_JSON}")
    else:
        print(f"Plantilla {SRC_PASSWORDS_JSON} no encontrada")

# Ejecutar la copia al iniciar
copiar_json_plantillas()

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

# Cache para contraseñas vulneradas
contrasenas_vulneradas: Set[str] = set()

# Cargar contraseñas vulneradas al iniciar la aplicación
def cargar_contrasenas_vulneradas():
    """Carga todas las contraseñas de los archivos en la carpeta rockyou"""
    global contrasenas_vulneradas
    contrasenas_vulneradas = set()
    
    # Buscar todos los archivos .txt en la carpeta rockyou
    #archivos_txt = glob.glob('../rockyou/*.txt')
    ROCKYOU_DIR = Path(__file__).parent.parent / "rockyou"
    archivos_txt = list(ROCKYOU_DIR.glob("*.txt"))
    
    if not archivos_txt:
        print("ADVERTENCIA: No se encontraron archivos .txt en la carpeta rockyou")
        print("Asegúrate de que la carpeta 'rockyou' existe y contiene archivos .txt")
        return
    
    total_cargadas = 0
    for archivo in archivos_txt:
        try:
            # Intentar con UTF-8 primero
            with open(archivo, 'r', encoding='utf-8') as f:
                lineas = f.readlines()
                
            for linea in lineas:
                password = linea.strip()  # Eliminar espacios y saltos de línea
                if password:  # Ignorar líneas vacías
                    contrasenas_vulneradas.add(password)
            
            print(f"Cargadas {len(contrasenas_vulneradas) - total_cargadas} contraseñas desde {archivo}")
            total_cargadas = len(contrasenas_vulneradas)
            
        except UnicodeDecodeError:
            # Si falla UTF-8, intentar con latin-1
            try:
                with open(archivo, 'r', encoding='latin-1') as f:
                    lineas = f.readlines()
                
                for linea in lineas:
                    password = linea.strip()
                    if password:
                        contrasenas_vulneradas.add(password)
                
                print(f"Cargadas {len(contrasenas_vulneradas) - total_cargadas} contraseñas desde {archivo} (latin-1)")
                total_cargadas = len(contrasenas_vulneradas)
                
            except Exception as e:
                print(f"Error al cargar {archivo}: {e}")
        except Exception as e:
            print(f"Error al procesar {archivo}: {e}")
    
    print(f"\nTOTAL: {len(contrasenas_vulneradas)} contraseñas vulneradas cargadas en memoria")
    
    # Mostrar algunas contraseñas de ejemplo para verificar
    if len(contrasenas_vulneradas) > 0:
        ejemplos = sorted(list(contrasenas_vulneradas))[:10]
        print(f"Ejemplos de las primeras 10: {ejemplos}")

# Cargar las contraseñas al iniciar
print("Cargando contraseñas vulneradas...")
cargar_contrasenas_vulneradas()

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

# Función simplificada para verificar si una contraseña está vulnerada
def verificar_password_vulnerada(password: str) -> bool:
    """
    Verifica si una contraseña está en la lista de vulneradas.
    Versión simple para archivos con una contraseña por línea.
    """
    if not password or not contrasenas_vulneradas:
        return False
    
    # Comparación directa (case-sensitive como en tus archivos)
    return password in contrasenas_vulneradas

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
        with open(API_USERS_JSON, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"users": []}

def guardar_json_users(datos):
    with open(API_USERS_JSON, 'w') as f:
        json.dump(datos, f, indent=2)

def leer_json_passwords():
    try:
        with open(API_PASSWORDS_JSON, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"passwords": []}

def guardar_json_passwords(datos):
    with open(API_PASSWORDS_JSON, 'w') as f:
        json.dump(datos, f, indent=2)

# Endpoints de Usuarios
@app.post("/register")
def registrar_usuario(user: User, response: Response):
    datos_users = leer_json_users()
    
    # Verificar si la contraseña está vulnerada
    password_vulnerada = verificar_password_vulnerada(user.password)
    
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
    resultado_login = login(LoginData(email=user.email, password=user.password), response)
    
    # Si la contraseña está vulnerada, añadir advertencia
    if password_vulnerada:
        if isinstance(resultado_login, dict):
            resultado_login["advertencia"] = "La contraseña que has utilizado está en la lista de contraseñas vulneradas. Por seguridad, te recomendamos cambiarla inmediatamente."
    
    return resultado_login

@app.post("/login")
def login(login_data: LoginData, response: Response):
    datos_users = leer_json_users()
    
    for usuario in datos_users["users"]:
        if usuario["email"] == login_data.email:
            # Verificar la contraseña usando el hash
            if verificar_password(login_data.password, usuario["salt"], usuario["password_hash"]):
                # Verificar si la contraseña está vulnerada
                password_vulnerada = verificar_password_vulnerada(login_data.password)
                
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
                
                resultado = {
                    "mensaje": "Login exitoso",
                    "uid": usuario["uid"],
                    "nombre": usuario["nombre"],
                    "email": usuario["email"],
                    "token": token_sesion  # Opcional: devolver token para depuración
                }
                
                # Añadir advertencia si la contraseña está vulnerada
                if password_vulnerada:
                    resultado["advertencia"] = "Tu contraseña está en la lista de contraseñas vulneradas. Por seguridad, te recomendamos cambiarla inmediatamente."
                
                return resultado
    
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

@app.post("/users/{email}/change-password")
def cambiar_password(email: str, password_change: PasswordChange, session_token: Optional[str] = Cookie(None)):
    """Cambiar la contraseña del usuario"""
    sesion = verificar_sesion(session_token)
    if sesion["email"] != email:
        raise HTTPException(status_code=403, detail="No tienes permiso para cambiar esta contraseña")
    
    # Verificar si la nueva contraseña está vulnerada
    password_vulnerada = verificar_password_vulnerada(password_change.password_nueva)
    
    datos_users = leer_json_users()
    
    for i, usuario in enumerate(datos_users["users"]):
        if usuario["email"] == email:
            # Verificar contraseña actual usando el hash
            if not verificar_password(password_change.password_actual, usuario["salt"], usuario["password_hash"]):
                raise HTTPException(status_code=401, detail="Contraseña actual incorrecta")
            
            # Si la nueva contraseña está vulnerada, permitir el cambio pero advertir
            if password_vulnerada:
                print(f"ADVERTENCIA: Usuario {email} está cambiando a una contraseña vulnerada")
            
            # Generar nuevo salt para la nueva contraseña
            nuevo_salt = base64.urlsafe_b64encode(os.urandom(16)).decode()
            
            # Hashear la nueva contraseña
            nuevo_password_hash = hash_password(password_change.password_nueva, nuevo_salt)
            
            # Actualizar usuario con nueva contraseña y salt
            datos_users["users"][i]["password_hash"] = nuevo_password_hash
            datos_users["users"][i]["salt"] = nuevo_salt
            
            guardar_json_users(datos_users)
            
            resultado = {
                "mensaje": "Contraseña cambiada correctamente",
                "email": email,
                "nota": "Las contraseñas guardadas anteriormente ya no son accesibles con la nueva contraseña"
            }
            
            if password_vulnerada:
                resultado["advertencia"] = "La nueva contraseña está en la lista de contraseñas vulneradas. Por seguridad, elige una contraseña más segura."
            
            return resultado
    
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
            
            # Verificar si la contraseña está vulnerada
            password_desc["vulnerada"] = verificar_password_vulnerada(password_desc["password"])
            
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
            
            # Verificar si la contraseña está vulnerada
            password_desc["vulnerada"] = verificar_password_vulnerada(password_desc["password"])
            
            return password_desc
    
    raise HTTPException(status_code=404, detail="Contraseña no encontrada")

@app.post("/passwords")
def crear_password(password: Password, session_token: Optional[str] = Cookie(None)):
    """Crear una nueva contraseña (se guarda encriptada automáticamente)"""
    sesion = verificar_sesion(session_token)
    
    # Verificar si la contraseña está vulnerada
    password_vulnerada = verificar_password_vulnerada(password.password)
    
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
    
    # Añadir advertencia si la contraseña está vulnerada
    if password_vulnerada:
        respuesta["advertencia"] = "Esta contraseña está en la lista de contraseñas vulneradas. Te recomendamos usar una contraseña más segura."
    
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
            
            password_vulnerada = False
            if password_update.password is not None:
                # Verificar si la nueva contraseña está vulnerada
                password_vulnerada = verificar_password_vulnerada(password_update.password)
                datos_pass["passwords"][i]["password"] = encriptar_password(password_update.password, sesion["clave"])
            
            if password_update.autologin is not None:
                datos_pass["passwords"][i]["autologin"] = password_update.autologin
            
            guardar_json_passwords(datos_pass)
            
            # Devolver la contraseña actualizada (desencriptada)
            password_actualizada = datos_pass["passwords"][i].copy()
            password_actualizada["password"] = password_update.password or desencriptar_password(p["password"], sesion["clave"])
            
            resultado = {
                "mensaje": "Contraseña actualizada correctamente",
                "id": password_actualizada["id"],
                "url": password_actualizada["url"],
                "email": password_actualizada["email"],
                "autologin": password_actualizada["autologin"],
                "comentario": password_actualizada.get("comentario")
            }
            
            if password_vulnerada:
                resultado["advertencia"] = "La nueva contraseña está en la lista de contraseñas vulneradas. Te recomendamos usar una contraseña más segura."
            
            return resultado
    
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
            password_texto = desencriptar_password(password["password"], sesion["clave"])
            
            resultado = {
                "autologin": password["autologin"],
                "url": password["url"],
                "email": password["email"],
                "password": password_texto if password["autologin"] else None
            }
            
            if password["autologin"]:
                # Verificar si la contraseña está vulnerada
                resultado["password_vulnerada"] = verificar_password_vulnerada(password_texto)
            
            return resultado
    
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
        
        # Verificar si la contraseña generada está vulnerada (aunque es muy improbable)
        password_vulnerada = verificar_password_vulnerada(password)
        
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
        
        resultado = {
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
        
        if password_vulnerada:
            resultado["advertencia"] = "La contraseña generada está en la lista de vulneradas (esto es extremadamente raro). Por favor, genera otra."
        
        return resultado
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al generar la contraseña: {str(e)}")

# Endpoint adicional: Obtener fortaleza de una contraseña existente
@app.post("/check-password-strength")
def check_password_strength(password: str):
    """
    Analiza la fortaleza de una contraseña existente y verifica si está vulnerada.
    """
    if not password:
        raise HTTPException(status_code=400, detail="Debes proporcionar una contraseña")
    
    # Verificar si la contraseña está vulnerada
    password_vulnerada = verificar_password_vulnerada(password)
    
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
    
    resultado = {
        "longitud": longitud,
        "tipos_detectados": {
            "mayusculas": tiene_mayusculas,
            "minusculas": tiene_minusculas,
            "digitos": tiene_digitos,
            "simbolos": tiene_simbolos
        },
        "entropia_aproximada": f"{entropia} bits",
        "fortaleza": fortaleza,
        "vulnerada": password_vulnerada,
        "recomendacion": []
    }
    
    # Generar recomendaciones personalizadas
    if password_vulnerada:
        resultado["recomendacion"].append("Esta contraseña está en la lista de contraseñas vulneradas. ¡NO LA USES!")
    
    if entropia < 50:
        resultado["recomendacion"].append("Usa mayúsculas, minúsculas, números y símbolos para mayor seguridad")
        resultado["recomendacion"].append("Aumenta la longitud de la contraseña")
    
    if not tiene_mayusculas:
        resultado["recomendacion"].append("Incluye letras mayúsculas")
    if not tiene_minusculas:
        resultado["recomendacion"].append("Incluye letras minúsculas")
    if not tiene_digitos:
        resultado["recomendacion"].append("Incluye números")
    if not tiene_simbolos:
        resultado["recomendacion"].append("Incluye símbolos especiales")
    
    if longitud < 8:
        resultado["recomendacion"].append("La longitud mínima recomendada es de 8 caracteres")
    elif longitud < 12:
        resultado["recomendacion"].append("Considera usar al menos 12 caracteres para mayor seguridad")
    
    if not resultado["recomendacion"]:
        resultado["recomendacion"].append("Excelente contraseña!")
    
    return resultado

# Endpoint para obtener estadísticas de vulnerabilidad del usuario
@app.get("/security-stats")
def obtener_estadisticas_seguridad(session_token: Optional[str] = Cookie(None)):
    """Obtiene estadísticas de seguridad del usuario"""
    sesion = verificar_sesion(session_token)
    
    # Obtener todas las contraseñas del usuario
    datos_pass = leer_json_passwords()
    passwords_usuario = [p for p in datos_pass["passwords"] if p["userid"] == sesion["uid"]]
    
    if not passwords_usuario:
        return {
            "total_passwords": 0,
            "passwords_vulneradas": 0,
            "porcentaje_vulneradas": 0,
            "mensaje": "No tienes contraseñas guardadas"
        }
    
    # Verificar cuántas están vulneradas
    passwords_vulneradas = 0
    for p in passwords_usuario:
        password_texto = desencriptar_password(p["password"], sesion["clave"])
        if verificar_password_vulnerada(password_texto):
            passwords_vulneradas += 1
    
    porcentaje = (passwords_vulneradas / len(passwords_usuario)) * 100
    
    resultado = {
        "total_passwords": len(passwords_usuario),
        "passwords_vulneradas": passwords_vulneradas,
        "porcentaje_vulneradas": round(porcentaje, 2)
    }
    
    if passwords_vulneradas > 0:
        resultado["recomendacion"] = f"Tienes {passwords_vulneradas} contraseñas vulneradas. Te recomendamos cambiarlas inmediatamente."
        resultado["urgencia"] = "ALTA" if porcentaje > 50 else "MEDIA"
    else:
        resultado["recomendacion"] = "¡Todas tus contraseñas son seguras!"
        resultado["urgencia"] = "BAJA"
    
    return resultado

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

@app.get("/debug/verificar-carga")
def verificar_carga_rockyou():
    """Endpoint para verificar que las contraseñas se cargaron correctamente"""
    if not contrasenas_vulneradas:
        return {
            "status": "error",
            "mensaje": "No hay contraseñas cargadas",
            "archivos_buscados": glob.glob('rockyou/*.txt'),
            "consejo": "Verifica que la carpeta 'rockyou' existe y contiene archivos .txt"
        }
    
    # Buscar algunas contraseñas comunes para verificar
    passwords_prueba = ["123456", "password", "iloveyou", "princess", "rockyou", "123456789", "abc123"]
    resultados = {}
    
    for p in passwords_prueba:
        resultados[p] = p in contrasenas_vulneradas
    
    return {
        "status": "ok",
        "total_contrasenas": len(contrasenas_vulneradas),
        "archivos_encontrados": glob.glob('rockyou/*.txt'),
        "verificacion_passwords_comunes": resultados,
        "muestra_primeras_20": sorted(list(contrasenas_vulneradas))[:20]
    }

@app.get("/debug/rockyou-stats")
def ver_rockyou_stats():
    """Endpoint SOLO para depuración - muestra estadísticas de rockyou"""
    return {
        "total_contrasenas_cargadas": len(contrasenas_vulneradas),
        "archivos_cargados": glob.glob('rockyou/*.txt')
    }

@app.get("/")
def home():
    return {
        "mensaje": "API de contraseñas multi-usuario con verificación de contraseñas vulneradas",
        "nota": "Las sesiones se manejan automáticamente con cookies. No necesitas enviar tokens manualmente.",
        "seguridad": {
            "verificacion_vulneradas": "✓ Las contraseñas se verifican automáticamente contra la base de datos rockyou",
            "archivos_cargados": f"{len(contrasenas_vulneradas)} contraseñas vulneradas en memoria",
            "advertencias": "Se muestran advertencias cuando se detectan contraseñas vulneradas"
        },
        "instrucciones": {
            "registro": "POST /register - Crea usuario y inicia sesión automáticamente",
            "login": "POST /login - Inicia sesión (establece cookie automática)",
            "verificar_sesion": "GET /check-session - Verifica si la cookie es válida",
            "ver_passwords": "GET /passwords - Obtiene tus contraseñas (con indicador de vulnerabilidad)",
            "security-stats": "GET /security-stats - Estadísticas de seguridad de tus contraseñas"
        },
        "nuevos_endpoints_generador": {
            "POST /generate-password": "Genera una contraseña segura (NO requiere autenticación)",
            "POST /check-password-strength": "Analiza la fortaleza de una contraseña existente y verifica si está vulnerada"
        },
        "debug_endpoints": {
            "GET /debug/verificar-carga": "Verifica que las contraseñas de rockyou se cargaron correctamente",
            "GET /debug/rockyou-stats": "Muestra estadísticas de las contraseñas cargadas"
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
