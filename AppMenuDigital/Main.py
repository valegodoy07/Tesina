from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config
import os

app = Flask(__name__)

# Configuración de la aplicación
app.config['SECRET_KEY'] = Config.SECRET_KEY
app.config['MYSQL_HOST'] = Config.MYSQL_HOST
app.config['MYSQL_USER'] = Config.MYSQL_USER
app.config['MYSQL_PASSWORD'] = Config.MYSQL_PASSWORD
app.config['MYSQL_DB'] = Config.MYSQL_DB

# Inicializar MySQL
mysql = MySQL(app)

# Crear la base de datos y tabla de usuarios si no existe
def init_database():
    try:
        cur = mysql.connection.cursor()
        
        # Crear base de datos si no existe
        cur.execute("CREATE DATABASE IF NOT EXISTS restobar_db")
        cur.execute("USE restobar_db")
        
        # Crear tabla de usuarios
        cur.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nombre VARCHAR(100) NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Crear tabla de productos del menú
        cur.execute("""
            CREATE TABLE IF NOT EXISTS productos (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nombre VARCHAR(100) NOT NULL,
                descripcion TEXT,
                precio DECIMAL(10,2) NOT NULL,
                imagen VARCHAR(255),
                categoria VARCHAR(50) DEFAULT 'general'
            )
        """)
        
        # Insertar productos de ejemplo si la tabla está vacía
        cur.execute("SELECT COUNT(*) FROM productos")
        if cur.fetchone()[0] == 0:
            productos_ejemplo = [
                ('Milanesa con papas fritas', 'Deliciosa milanesa acompañada de papas fritas crujientes', 10000.00, 'milanesa-tesina.png', 'platos_principales'),
                ('Café', 'Café recién preparado', 3000.00, 'cafe.png', 'bebidas'),
                ('Pizza', 'Pizza artesanal con ingredientes frescos', 7000.00, 'pizza.png', 'platos_principales')
            ]
            
            for producto in productos_ejemplo:
                cur.execute("""
                    INSERT INTO productos (nombre, descripcion, precio, imagen, categoria)
                    VALUES (%s, %s, %s, %s, %s)
                """, producto)
        
        mysql.connection.commit()
        cur.close()
        print("Base de datos inicializada correctamente")
        
    except Exception as e:
        print(f"Error al inicializar la base de datos: {e}")

# Rutas de la aplicación
@app.route('/')
def index():
    if 'user_id' in session:
        return render_template('Index.html', usuario=session.get('nombre'))
    return render_template('Index.html')

@app.route('/menu')
def menu():
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM productos")
        productos = cur.fetchall()
        cur.close()
        return render_template('menu.html', productos=productos)
    except Exception as e:
        print(f"Error al cargar productos: {e}")
        return render_template('menu.html', productos=[])

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        try:
            cur = mysql.connection.cursor()
            cur.execute("SELECT * FROM usuarios WHERE email = %s", (email,))
            user = cur.fetchone()
            cur.close()
            
            if user and check_password_hash(user[3], password):
                session['user_id'] = user[0]
                session['nombre'] = user[1]
                flash('¡Inicio de sesión exitoso!', 'success')
                return redirect(url_for('index'))
            else:
                flash('Email o contraseña incorrectos', 'error')
                
        except Exception as e:
            print(f"Error en login: {e}")
            flash('Error al iniciar sesión', 'error')
    
    return render_template('Login.html')

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form['nombre']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            flash('Las contraseñas no coinciden', 'error')
            return render_template('Registro.html')
        
        try:
            cur = mysql.connection.cursor()
            
            # Verificar si el email ya existe
            cur.execute("SELECT * FROM usuarios WHERE email = %s", (email,))
            if cur.fetchone():
                flash('El email ya está registrado', 'error')
                cur.close()
                return render_template('Registro.html')
            
            # Crear nuevo usuario
            hashed_password = generate_password_hash(password)
            cur.execute("""
                INSERT INTO usuarios (nombre, email, password)
                VALUES (%s, %s, %s)
            """, (nombre, email, hashed_password))
            
            mysql.connection.commit()
            cur.close()
            
            flash('¡Registro exitoso! Ahora puedes iniciar sesión', 'success')
            return redirect(url_for('login'))
            
        except Exception as e:
            print(f"Error en registro: {e}")
            flash('Error al registrar usuario', 'error')
    
    return render_template('Registro.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Has cerrado sesión', 'info')
    return redirect(url_for('index'))

@app.route('/perfil')
def perfil():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM usuarios WHERE id = %s", (session['user_id'],))
        usuario = cur.fetchone()
        cur.close()
        
        return render_template('perfil.html', usuario=usuario)
    except Exception as e:
        print(f"Error al cargar perfil: {e}")
        flash('Error al cargar el perfil', 'error')
        return redirect(url_for('index'))

if __name__ == '__main__':
    init_database()
    app.run(debug=Config.DEBUG, host=Config.HOST, port=Config.PORT)
