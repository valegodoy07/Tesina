import os
import secrets

class Config:
    # Configuración de la aplicación
    SECRET_KEY = secrets.token_hex(32)  # Genera una clave secreta de 64 caracteres hexadecimales
    
    # Configuración de MySQL para XAMPP
    MYSQL_HOST = 'localhost'
    MYSQL_USER = 'root'
    MYSQL_PASSWORD = 'admin123'  # Contraseña vacía por defecto en XAMPP
    MYSQL_DB = 'menudigital'  # Nombre de tu base de datos existente
    
    # Configuración del servidor
   # DEBUG = True
   # HOST = 'localhost'
   # PORT = 5000
    
    # Configuración de archivos estáticos
    STATIC_FOLDER = 'static'
    TEMPLATE_FOLDER = 'Templates'
    
    # Configuración de seguridad
    SESSION_COOKIE_SECURE = False  # Cambiar a True en producción con HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax' 