from flask import Flask, render_template, request, redirect, url_for, flash, session
from functools import wraps
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config
import os

app = Flask(__name__)

# Configuración de la aplicación
app.config['SECRET_KEY'] = Config.SECRET_KEY
app.config['MYSQL_PORT'] = Config.MYSQL_PORT
app.config['MYSQL_HOST'] = Config.MYSQL_HOST
app.config['MYSQL_USER'] = Config.MYSQL_USER
app.config['MYSQL_PASSWORD'] = Config.MYSQL_PASSWORD
app.config['MYSQL_DB'] = Config.MYSQL_DB

# Inicializar MySQL
mysql = MySQL(app)

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

# ===== Páginas por categoría (estáticas por ahora) =====
@app.route('/categoria/<nombre>')
def categoria(nombre: str):
    # Normalizamos nombre para plantilla
    nombre_lower = nombre.lower()
    categorias_validas = ['desayunos', 'almuerzos', 'meriendas', 'cenas', 'postres', 'bebidas', 'promociones']
    if nombre_lower not in categorias_validas:
        flash('Categoría no encontrada', 'error')
        return redirect(url_for('index'))
    template_name = f"categoria_{nombre_lower}.html"
    try:
        # Si existiese DB: podríamos filtrar productos por categoria
        productos = []
        if nombre_lower != 'promociones':
            try:
                cur = mysql.connection.cursor()
                if nombre_lower == 'desayunos':
                    filtro = 'desayunos'
                elif nombre_lower == 'almuerzos':
                    filtro = 'almuerzos'
                elif nombre_lower == 'meriendas':
                    filtro = 'meriendas'
                elif nombre_lower == 'cenas':
                    filtro = 'cenas'
                elif nombre_lower == 'postres':
                    filtro = 'postres'
                elif nombre_lower == 'bebidas':
                    filtro = 'bebidas'
                else:
                    filtro = 'general'
                cur.execute("SELECT id, nombre, descripcion, precio, imagen FROM productos WHERE categoria=%s", (filtro,))
                productos = cur.fetchall()
                cur.close()
            except Exception as e:
                print(f"Error consultando productos por categoría: {e}")
        return render_template(template_name, productos=productos)
    except Exception:
        # fallback si no hay plantilla específica
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
                # Guardar email en sesión
                session['email'] = user[2]
                # Determinar si es admin (si existe la columna is_admin)
                is_admin = False
                try:
                    # user[5] sería is_admin si la tabla tiene: id, nombre, email, password, fecha_registro, is_admin
                    if len(user) > 5:
                        is_admin = bool(user[5])
                except Exception:
                    is_admin = False
                session['is_admin'] = is_admin
                flash('¡Inicio de sesión exitoso!', 'success')
                return redirect(url_for('index'))
            else:
                flash('Email o contraseña incorrectos', 'error')
                
        except Exception as e:
            print(f"Error en login: {e}")
            flash('Error al iniciar sesión', 'error')
    
    return render_template('Login.html')

# esta funcion maneja el registro de nuevos usuarios
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

# ===== Utilidades de Admin =====
def admin_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if 'user_id' not in session:
            flash('Debes iniciar sesión', 'error')
            return redirect(url_for('login'))
        # Permitir admin por bandera en sesión o usuario con id 1 como fallback
        if not session.get('is_admin', False) and session.get('user_id') != 1:
            flash('No tienes permisos de administrador', 'error')
            return redirect(url_for('index'))
        return view_func(*args, **kwargs)
    return wrapped

# ===== Panel de Control (Admin) =====
@app.route('/admin')
@admin_required
def admin_dashboard():
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT id, nombre, descripcion FROM categorias ORDER BY nombre")
        categorias = cur.fetchall()
        cur.execute("SELECT id, nombre, descripcion, precio, categoria, imagen FROM productos ORDER BY id DESC")
        productos = cur.fetchall()
        cur.execute("SELECT id, nombre, email, telefono, activo FROM mozos ORDER BY nombre")
        mozos = cur.fetchall()
        cur.close()
        return render_template('admin.html', categorias=categorias, productos=productos, mozos=mozos)
    except Exception as e:
        print(f"Error al cargar dashboard admin: {e}")
        flash('Error al cargar el panel de administración', 'error')
        return render_template('admin.html', categorias=[], productos=[], mozos=[])

# ===== CRUD Categorías =====
@app.route('/admin/categorias/crear', methods=['POST'])
@admin_required
def admin_categorias_crear():
    nombre = request.form.get('nombre')
    descripcion = request.form.get('descripcion')
    if not nombre:
        flash('El nombre de la categoría es obligatorio', 'error')
        return redirect(url_for('admin_dashboard'))
    try:
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO categorias (nombre, descripcion) VALUES (%s, %s)", (nombre, descripcion))
        mysql.connection.commit()
        cur.close()
        flash('Categoría creada', 'success')
    except Exception as e:
        print(f"Error creando categoría: {e}")
        flash('Error al crear categoría', 'error')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/categorias/<int:categoria_id>/actualizar', methods=['POST'])
@admin_required
def admin_categorias_actualizar(categoria_id: int):
    nombre = request.form.get('nombre')
    descripcion = request.form.get('descripcion')
    try:
        cur = mysql.connection.cursor()
        cur.execute("UPDATE categorias SET nombre=%s, descripcion=%s WHERE id=%s", (nombre, descripcion, categoria_id))
        mysql.connection.commit()
        cur.close()
        flash('Categoría actualizada', 'success')
    except Exception as e:
        print(f"Error actualizando categoría: {e}")
        flash('Error al actualizar categoría', 'error')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/categorias/<int:categoria_id>/eliminar', methods=['POST'])
@admin_required
def admin_categorias_eliminar(categoria_id: int):
    try:
        cur = mysql.connection.cursor()
        cur.execute("DELETE FROM categorias WHERE id=%s", (categoria_id,))
        mysql.connection.commit()
        cur.close()
        flash('Categoría eliminada', 'success')
    except Exception as e:
        print(f"Error eliminando categoría: {e}")
        flash('Error al eliminar categoría', 'error')
    return redirect(url_for('admin_dashboard'))

# ===== CRUD Productos =====
@app.route('/admin/productos/crear', methods=['POST'])
@admin_required
def admin_productos_crear():
    nombre = request.form.get('nombre')
    descripcion = request.form.get('descripcion')
    precio = request.form.get('precio')
    imagen = request.form.get('imagen')
    categoria = request.form.get('categoria')
    if not (nombre and precio):
        flash('Nombre y precio son obligatorios', 'error')
        return redirect(url_for('admin_dashboard'))
    try:
        cur = mysql.connection.cursor()
        cur.execute(
            "INSERT INTO productos (nombre, descripcion, precio, imagen, categoria) VALUES (%s, %s, %s, %s, %s)",
            (nombre, descripcion, precio, imagen, categoria)
        )
        mysql.connection.commit()
        cur.close()
        flash('Producto creado', 'success')
    except Exception as e:
        print(f"Error creando producto: {e}")
        flash('Error al crear producto', 'error')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/productos/<int:producto_id>/actualizar', methods=['POST'])
@admin_required
def admin_productos_actualizar(producto_id: int):
    nombre = request.form.get('nombre')
    descripcion = request.form.get('descripcion')
    precio = request.form.get('precio')
    imagen = request.form.get('imagen')
    categoria = request.form.get('categoria')
    try:
        cur = mysql.connection.cursor()
        cur.execute(
            "UPDATE productos SET nombre=%s, descripcion=%s, precio=%s, imagen=%s, categoria=%s WHERE id=%s",
            (nombre, descripcion, precio, imagen, categoria, producto_id)
        )
        mysql.connection.commit()
        cur.close()
        flash('Producto actualizado', 'success')
    except Exception as e:
        print(f"Error actualizando producto: {e}")
        flash('Error al actualizar producto', 'error')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/productos/<int:producto_id>/eliminar', methods=['POST'])
@admin_required
def admin_productos_eliminar(producto_id: int):
    try:
        cur = mysql.connection.cursor()
        cur.execute("DELETE FROM productos WHERE id=%s", (producto_id,))
        mysql.connection.commit()
        cur.close()
        flash('Producto eliminado', 'success')
    except Exception as e:
        print(f"Error eliminando producto: {e}")
        flash('Error al eliminar producto', 'error')
    return redirect(url_for('admin_dashboard'))

# ===== CRUD Mozos =====
@app.route('/admin/mozos/crear', methods=['POST'])
@admin_required
def admin_mozos_crear():
    nombre = request.form.get('nombre')
    email = request.form.get('email')
    telefono = request.form.get('telefono')
    activo = 1 if request.form.get('activo') == 'on' else 0
    if not nombre:
        flash('El nombre del mozo es obligatorio', 'error')
        return redirect(url_for('admin_dashboard'))
    try:
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO mozos (nombre, email, telefono, activo) VALUES (%s, %s, %s, %s)", (nombre, email, telefono, activo))
        mysql.connection.commit()
        cur.close()
        flash('Mozo creado', 'success')
    except Exception as e:
        print(f"Error creando mozo: {e}")
        flash('Error al crear mozo', 'error')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/mozos/<int:mozo_id>/actualizar', methods=['POST'])
@admin_required
def admin_mozos_actualizar(mozo_id: int):
    nombre = request.form.get('nombre')
    email = request.form.get('email')
    telefono = request.form.get('telefono')
    activo = 1 if request.form.get('activo') == 'on' else 0
    try:
        cur = mysql.connection.cursor()
        cur.execute(
            "UPDATE mozos SET nombre=%s, email=%s, telefono=%s, activo=%s WHERE id=%s",
            (nombre, email, telefono, activo, mozo_id)
        )
        mysql.connection.commit()
        cur.close()
        flash('Mozo actualizado', 'success')
    except Exception as e:
        print(f"Error actualizando mozo: {e}")
        flash('Error al actualizar mozo', 'error')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/mozos/<int:mozo_id>/eliminar', methods=['POST'])
@admin_required
def admin_mozos_eliminar(mozo_id: int):
    try:
        cur = mysql.connection.cursor()
        cur.execute("DELETE FROM mozos WHERE id=%s", (mozo_id,))
        mysql.connection.commit()
        cur.close()
        flash('Mozo eliminado', 'success')
    except Exception as e:
        print(f"Error eliminando mozo: {e}")
        flash('Error al eliminar mozo', 'error')
    return redirect(url_for('admin_dashboard'))

@app.route('/perfil')
def perfil():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM usuarios WHERE idusuario  = %s", (session['user_id'],))
        usuario = cur.fetchone()
        cur.close()
        
        return render_template('perfil.html', usuario=usuario)
    except Exception as e:
        print(f"Error al cargar perfil: {e}")
        flash('Error al cargar el perfil', 'error')
        return redirect(url_for('index'))

if __name__ == '__main__':
    debug = getattr(Config, 'DEBUG', True)
    host = getattr(Config, 'HOST', '0.0.0.0')
    port = getattr(Config, 'PORT', 5000)
    app.run(debug=debug, host=host, port=port)
