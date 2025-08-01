import os

class Config:
    # Configuración de la aplicación
    SECRET_KEY = 'tu_clave_secreta_aqui_cambiala_en_produccion'
    
    # Configuración de MySQL
    MYSQL_HOST = 'localhost'
    MYSQL_USER = 'root'
    MYSQL_PASSWORD = ''
    MYSQL_DB = 'restobar_db'
    
    # Configuración del servidor
    DEBUG = True
    HOST = '0.0.0.0'
    PORT = 5000
    
    # Configuración de archivos estáticos
    STATIC_FOLDER = 'Statics'
    TEMPLATE_FOLDER = 'Templates'
    
    # Configuración de seguridad
    SESSION_COOKIE_SECURE = False  # Cambiar a True en producción con HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Configuración de la base de datos
    DB_AUTO_CREATE = True  # Crear base de datos automáticamente
    DB_SAMPLE_DATA = True   # Insertar datos de ejemplo 