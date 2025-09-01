#!/usr/bin/env python3
"""
Script de instalación para P&C Restobar
Este script ayuda a configurar la aplicación automáticamente
"""

import os
import sys
import subprocess
import mysql.connector
from mysql.connector import Error

def print_banner():
    """Imprime el banner de bienvenida"""
    print("=" * 60)
    print("           P&C RESTOBAR - INSTALADOR")
    print("=" * 60)
    print()

def check_python_version():
    """Verifica la versión de Python"""
    print("🔍 Verificando versión de Python...")
    if sys.version_info < (3, 8):
        print("❌ Error: Se requiere Python 3.8 o superior")
        print(f"   Versión actual: {sys.version}")
        return False
    print(f"✅ Python {sys.version.split()[0]} - OK")
    return True

def install_dependencies():
    """Instala las dependencias de Python"""
    print("\n📦 Instalando dependencias...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencias instaladas correctamente")
        return True
    except subprocess.CalledProcessError:
        print("❌ Error al instalar dependencias")
        return False

def test_mysql_connection():
    """Prueba la conexión a MySQL"""
    print("\n🗄️  Probando conexión a MySQL...")
    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password='admin123'
        )
        if connection.is_connected():
            print("✅ Conexión a MySQL exitosa")
            connection.close()
            return True
    except Error as e:
        print(f"❌ Error de conexión a MySQL: {e}")
        print("\n💡 Soluciones:")
        print("   1. Asegúrate de que MySQL esté instalado y ejecutándose")
        print("   2. Verifica que el usuario 'root' no tenga contraseña")
        print("   3. Si usas XAMPP/WAMP, asegúrate de que MySQL esté activo")
        return False

def create_database():
    """Crea la base de datos y tablas"""
    print("\n🗄️  Configurando base de datos...")
    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password=''
        )
        cursor = connection.cursor()
        
        # Crear base de datos
        cursor.execute("CREATE DATABASE IF NOT EXISTS restobar_db")
        cursor.execute("USE restobar_db")
        
        # Crear tabla de usuarios
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nombre VARCHAR(100) NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Crear tabla de productos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS productos (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nombre VARCHAR(100) NOT NULL,
                descripcion TEXT,
                precio DECIMAL(10,2) NOT NULL,
                imagen VARCHAR(255),
                categoria VARCHAR(50) DEFAULT 'general'
            )
        """)
        
        # Insertar productos de ejemplo
        cursor.execute("SELECT COUNT(*) FROM productos")
        if cursor.fetchone()[0] == 0:
            productos_ejemplo = [
                ('Milanesa con papas fritas', 'Deliciosa milanesa acompañada de papas fritas crujientes', 10000.00, 'milanesa-tesina.png', 'platos_principales'),
                ('Café', 'Café recién preparado', 3000.00, 'cafe.png', 'bebidas'),
                ('Pizza', 'Pizza artesanal con ingredientes frescos', 7000.00, 'pizza.png', 'platos_principales'),
                ('Hamburguesa', 'Hamburguesa gourmet con queso y vegetales', 12000.00, 'hamburguesa.png', 'platos_principales'),
                ('Limonada', 'Limonada natural refrescante', 2500.00, 'limonada.png', 'bebidas')
            ]
            
            for producto in productos_ejemplo:
                cursor.execute("""
                    INSERT INTO productos (nombre, descripcion, precio, imagen, categoria)
                    VALUES (%s, %s, %s, %s, %s)
                """, producto)
        
        connection.commit()
        cursor.close()
        connection.close()
        print("✅ Base de datos configurada correctamente")
        return True
        
    except Error as e:
        print(f"❌ Error al configurar la base de datos: {e}")
        return False

def create_folders():
    """Crea las carpetas necesarias si no existen"""
    print("\n📁 Creando estructura de carpetas...")
    folders = ['Statics', 'Templates']
    for folder in folders:
        if not os.path.exists(folder):
            os.makedirs(folder)
            print(f"✅ Carpeta '{folder}' creada")
        else:
            print(f"✅ Carpeta '{folder}' ya existe")

def main():
    """Función principal del instalador"""
    print_banner()
    
    # Verificar Python
    if not check_python_version():
        return
    
    # Instalar dependencias
    if not install_dependencies():
        return
    
    # Crear carpetas
    create_folders()
    
    # Probar MySQL
    if not test_mysql_connection():
        print("\n⚠️  No se pudo conectar a MySQL.")
        print("   La aplicación puede no funcionar correctamente.")
        print("   Continúa con la instalación y configura MySQL manualmente.")
    
    # Configurar base de datos
    if test_mysql_connection():
        if not create_database():
            print("\n⚠️  No se pudo configurar la base de datos.")
            print("   Puedes configurarla manualmente ejecutando la aplicación.")
    
    print("\n" + "=" * 60)
    print("           INSTALACIÓN COMPLETADA")
    print("=" * 60)
    print("\n🎉 ¡La aplicación está lista para usar!")
    print("\n📋 Próximos pasos:")
    print("   1. Ejecuta: python Main.py")
    print("   2. Abre tu navegador en: http://localhost:5000")
    print("   3. Registra tu primera cuenta de usuario")
    print("\n📚 Para más información, consulta el archivo README.md")
    print("\n¡Disfruta tu aplicación de restobar! 🍽️")

if __name__ == "__main__":
    main() 