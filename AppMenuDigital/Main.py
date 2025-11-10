from flask import Flask, render_template, request, redirect, url_for, flash, session
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
try:
    from .config import Config
except ImportError:
    from config import Config
import os
import pymysql

app = Flask(__name__)

# Configuración de la aplicación
app.config['SECRET_KEY'] = Config.SECRET_KEY
app.config['MYSQL_PORT'] = Config.MYSQL_PORT
app.config['MYSQL_HOST'] = Config.MYSQL_HOST
app.config['MYSQL_USER'] = Config.MYSQL_USER
app.config['MYSQL_PASSWORD'] = Config.MYSQL_PASSWORD
app.config['MYSQL_DB'] = Config.MYSQL_DB
print(f"[startup] DB host={app.config['MYSQL_HOST']} port={app.config['MYSQL_PORT']} user={app.config['MYSQL_USER']} db={app.config['MYSQL_DB']}")
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'images')
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10 MB
_ALLOWED_IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.avif'}

# Asegurar carpeta de imágenes
try:
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
except Exception as e:
    print(f"[startup] No se pudo crear carpeta de imágenes: {e}")

# Clase MySQL personalizada usando pymysql
class MySQL:
    def __init__(self, app=None):
        self.app = app
    
    @property
    def connection(self):
        return pymysql.connect(
            host=self.app.config['MYSQL_HOST'],
            port=self.app.config['MYSQL_PORT'],
            user=self.app.config['MYSQL_USER'],
            password=self.app.config['MYSQL_PASSWORD'],
            database=self.app.config['MYSQL_DB'],
            autocommit=False,
            charset='utf8mb4',
            connect_timeout=5
        )
mysql = MySQL(app)
# (revert) Sin configuración de subida de imágenes

# Inicializar MySQL
# Función para obtener conexión a la base de datos
def get_db_connection():
    connection = pymysql.connect(
        host=app.config['MYSQL_HOST'],
        user=app.config['MYSQL_USER'],
        password=app.config['MYSQL_PASSWORD'],
        database=app.config['MYSQL_DB'],
        cursorclass=pymysql.cursors.DictCursor
    )
    return connection

def _log_db_info(tag: str):
    try:
        conn = mysql.connection
        cur = conn.cursor()
        cur.execute("SELECT DATABASE()")
        dbn = cur.fetchone()[0]
        cur.execute("SELECT VERSION()")
        ver = cur.fetchone()[0]
        cur.execute("SELECT CURRENT_USER()")
        usr = cur.fetchone()[0]
        print(f"[db-info:{tag}] database={dbn} version={ver} current_user={usr}")
        cur.close()
    except Exception as e:
        print(f"[db-info:{tag}] error: {e}")

# (revert) Sin inicialización automática de tablas
# Context processor to expose cart count in all templates
@app.context_processor
def inject_cart_count():
    try:
        cart = session.get('cart', {})
        total_qty = 0
        for entry in cart.values():
            try:
                total_qty += int(entry.get('qty', 1))
            except Exception:
                total_qty += 1
        return {'cart_count': total_qty}
    except Exception:
        return {'cart_count': 0}


# Rutas de la aplicación
@app.route('/')
def index():
    # Cargar dinámicamente productos por categoría para el Index
    categorias = ['desayunos', 'almuerzos', 'cenas', 'meriendas', 'postres', 'bebidas', 'comida_sin_tac', 'promociones']
    productos_por_categoria = {c: [] for c in categorias}
    cur = None
    
    print("[index] Iniciando carga de productos...")
    
    try:
        cur = mysql.connection.cursor()
        print("[index] Cursor creado")
        
        # Asegurar que existe la tabla productos
        cur.execute("""
            CREATE TABLE IF NOT EXISTS productos (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nombre VARCHAR(150) NOT NULL,
                descripcion TEXT NULL,
                precio DECIMAL(10,2) NOT NULL,
                imagen VARCHAR(255) NULL,
                categoria VARCHAR(50) NULL
            )
        """)
        mysql.connection.commit()
        print("[index] Tabla productos verificada/creada")
        
        # Leer TODOS los productos primero para debug
        cur.execute("SELECT COUNT(*) FROM productos")
        total = cur.fetchone()[0]
        print(f"[index] Total de productos en tabla: {total}")
        
        # Leer de la tabla productos
        cur.execute("""
            SELECT id, nombre, precio, LOWER(COALESCE(categoria, '')) as cat, COALESCE(imagen, ''), COALESCE(descripcion, '')
            FROM productos
            ORDER BY id DESC
        """)
        filas = cur.fetchall()
        print(f"[index] Productos encontrados en consulta: {len(filas)}")
        
        # Mostrar todos los productos encontrados
        for f in filas:
            print(f"[index] Producto raw: id={f[0]}, nombre={f[1]}, precio={f[2]}, cat={f[3]}, imagen={f[4]}")
            cat = (f[3] or '').lower().strip()
            print(f"[index] Categoría procesada: '{cat}'")
            
            # Filtrar solo las categorías válidas
            if cat in categorias:
                productos_por_categoria[cat].append(f)
                print(f"[index] ✓ Producto agregado a categoría: {cat}")
            else:
                print(f"[index] ✗ Categoría '{cat}' no está en la lista de categorías válidas")
        
        # Debug: mostrar cuántos productos hay por categoría
        print("[index] Resumen por categoría:")
        for cat, prods in productos_por_categoria.items():
            print(f"[index]   - {cat}: {len(prods)} productos")
            if prods:
                for p in prods:
                    print(f"[index]     * {p[1]} (${p[2]})")
        
    except Exception as e:
        print(f"[index] ERROR al cargar productos: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if cur:
            cur.close()
            print("[index] Cursor cerrado")

    ctx = {'productos_por_categoria': productos_por_categoria}
    if 'user_id' in session:
        ctx['usuario'] = session.get('nombre')
    
    print(f"[index] Retornando template con {sum(len(p) for p in productos_por_categoria.values())} productos totales")
    return render_template('Index.html', **ctx)

@app.route('/menu')
def menu():
    try:
        ensure_menu_table_exists()
        ensure_menu_table_upgrade()
        cur = mysql.connection.cursor()
        cur.execute("SELECT id, Nombre_Menu, Precio, COALESCE(Categoria, ''), COALESCE(Imagen, '') FROM menu ORDER BY id DESC")
        productos = cur.fetchall()
        cur.close()
        return render_template('menu.html', productos=productos)
    except Exception as e:
        print(f"Error al cargar productos (menu): {e}")
        return render_template('menu.html', productos=[])

# ===== Páginas por categoría (estáticas por ahora) =====
@app.route('/categoria/<nombre>')
def categoria(nombre: str):
    # Normalizamos nombre para plantilla
    nombre_lower = nombre.lower()
    categorias_validas = ['desayunos', 'almuerzos', 'meriendas', 'cenas', 'postres', 'bebidas', 'comida_sin_tac', 'promociones']
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
            conn = mysql.connection
            cur = conn.cursor()
            # Selecciona columnas explícitas para evitar dependencia de orden
            cur.execute("SELECT id, nombre, email, password FROM usuarios WHERE email = %s LIMIT 1", (email,))
            user = cur.fetchone()
            print(f"[login] fetched user for {email}: {bool(user)}")

            password_ok = False
            upgraded = False
            if user:
                stored_pwd = user[3]
                try:
                    password_ok = check_password_hash(stored_pwd, password)
                except Exception as e:
                    print(f"[login] check_password_hash error: {e}")
                    password_ok = False
                if not password_ok:
                    # Fallback: si la DB tuviese texto plano (migración)
                    try:
                        password_ok = (stored_pwd == password)
                        if password_ok and not (isinstance(stored_pwd, str) and stored_pwd.startswith('pbkdf2:')):
                            new_hash = generate_password_hash(password)
                            cur.execute("UPDATE usuarios SET password=%s WHERE id=%s", (new_hash, user[0]))
                            conn.commit()
                            upgraded = True
                            print("[login] upgraded password hash for user id", user[0])
                    except Exception as e:
                        print(f"[login] legacy password check error: {e}")
                        password_ok = False

            if user and password_ok:
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
                # Determinar rol mozo si el email pertenece a mozos activos
                try:
                    cur2 = mysql.connection.cursor()
                    cur2.execute("SELECT id, activo FROM mozos WHERE email=%s", (session['email'],))
                    mozo_row = cur2.fetchone()
                    cur2.close()
                    if mozo_row and (mozo_row[1] == 1 or mozo_row[1] is True):
                        session['rol'] = 'mozo'
                        session['mozo_id'] = mozo_row[0]
                    elif is_admin or session.get('user_id') == 1:
                        session['rol'] = 'admin'
                    else:
                        session['rol'] = 'usuario'
                except Exception:
                    session['rol'] = 'admin' if (is_admin or session.get('user_id') == 1) else 'usuario'
                flash('¡Inicio de sesión exitoso!' + (' (contraseña actualizada)' if upgraded else ''), 'success')
                _log_db_info('login')
                return redirect(url_for('index'))
            else:
                flash('Email o contraseña incorrectos', 'error')
                print(f"[login] invalid credentials for {email}")
                
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
            ensure_core_tables()
            conn = mysql.connection
            cur = conn.cursor()
            
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
            # Registrar también como mozo activo por defecto
            try:
                cur.execute("INSERT INTO mozos (nombre, email, activo) VALUES (%s, %s, %s)", (nombre, email, 1))
            except Exception:
                # Si ya existe en mozos por UNIQUE email, ignoramos
                pass

            conn.commit()
            new_id = cur.lastrowid
            print(f"[registro] usuario creado id={new_id} email={email}")
            cur.close()
            _log_db_info('registro')
            
            flash('¡Registro exitoso! Ahora puedes iniciar sesión', 'success')
            return redirect(url_for('login'))
            
        except Exception as e:
            print(f"Error en registro: {e}")
            flash('Error al registrar usuario', 'error')
    
    return render_template('Registro.html')

def ensure_core_tables():
    try:
        cur = mysql.connection.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS usuarios (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nombre VARCHAR(100) NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        mysql.connection.commit()
        cur.close()
    except Exception as e:
        print(f"Error asegurando tabla usuarios: {e}")

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

# ===== Utilidades de Mozo =====
def mozo_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if 'user_id' not in session:
            flash('Debes iniciar sesión', 'error')
            return redirect(url_for('login'))
        if session.get('rol') != 'mozo' or not session.get('mozo_id'):
            flash('Acceso solo para mozos', 'error')
            return redirect(url_for('index'))
        return view_func(*args, **kwargs)
    return wrapped

def ensure_pedidos_tables():
    try:
        # Asegurar tablas base necesarias
        ensure_mozos_table_exists()
        ensure_menu_table_exists()

        cur = mysql.connection.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS pedidos_mozo (
                id INT AUTO_INCREMENT PRIMARY KEY,
                mozo_id INT NOT NULL,
                mesa VARCHAR(20) NOT NULL,
                estado VARCHAR(20) DEFAULT 'abierto',
                notas TEXT,
                creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT fk_pedidos_mozo_mozo FOREIGN KEY (mozo_id) REFERENCES mozos(id)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS pedido_items_mozo (
                id INT AUTO_INCREMENT PRIMARY KEY,
                pedido_id INT NOT NULL,
                producto_id INT NOT NULL,
                cantidad INT NOT NULL DEFAULT 1,
                CONSTRAINT fk_pedido_items_mozo_pedido FOREIGN KEY (pedido_id) REFERENCES pedidos_mozo(id),
                CONSTRAINT fk_pedido_items_mozo_menu FOREIGN KEY (producto_id) REFERENCES menu(id)
            )
            """
        )
        mysql.connection.commit()
        cur.close()
    except Exception as e:
        print(f"Error asegurando tablas de pedidos: {e}")

def ensure_mozos_table_exists():
    try:
        cur = mysql.connection.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS mozos (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nombre VARCHAR(100) NOT NULL,
                email VARCHAR(120) UNIQUE,
                telefono VARCHAR(30),
                activo TINYINT(1) DEFAULT 1
            )
            """
        )
        mysql.connection.commit()
        cur.close()
    except Exception as e:
        print(f"Error asegurando tabla mozos: {e}")


def ensure_menu_table_upgrade():
    try:
        cur = mysql.connection.cursor()
        cur.execute("DESCRIBE menu")
        cols = [row[0].lower() for row in cur.fetchall()]
        if 'imagen' not in cols:
            try:
                cur.execute("ALTER TABLE menu ADD COLUMN Imagen VARCHAR(255) NULL")
            except Exception:
                pass
        if 'categoria' not in cols:
            try:
                cur.execute("ALTER TABLE menu ADD COLUMN Categoria VARCHAR(50) NULL")
            except Exception:
                pass
        if 'descripcion' not in cols:
            try:
                cur.execute("ALTER TABLE menu ADD COLUMN Descripcion TEXT NULL")
            except Exception:
                pass
        mysql.connection.commit()
        cur.close()
    except Exception as e:
        print(f"No se pudo verificar/actualizar columnas de menu: {e}")

def ensure_menu_table_exists():
    try:
        cur = mysql.connection.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS menu (
                id INT AUTO_INCREMENT PRIMARY KEY,
                Nombre_Menu VARCHAR(150) NOT NULL,
                Precio DECIMAL(10,2) NOT NULL,
                Categoria VARCHAR(50) NULL,
                Imagen VARCHAR(255) NULL,
                Descripcion TEXT NULL
            )
            """
        )
        mysql.connection.commit()
        cur.close()
    except Exception as e:
        print(f"Error creando tabla menu si no existe: {e}")

def ensure_productos_table_exists():
    try:
        cur = mysql.connection.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS productos (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nombre VARCHAR(150) NOT NULL,
                descripcion TEXT NULL,
                precio DECIMAL(10,2) NOT NULL,
                imagen VARCHAR(255) NULL,
                categoria VARCHAR(50) NULL
            )
            """
        )
        mysql.connection.commit()
        cur.close()
    except Exception as e:
        print(f"Error creando tabla productos si no existe: {e}")

# ===== Panel de Control (Admin) =====
@app.route('/admin')
@admin_required
def admin_dashboard():
    try:
        # Asegurar tablas necesarias para métricas
        try:
            ensure_client_orders_tables()
        except Exception:
            pass
        ensure_menu_table_upgrade()
        cur = mysql.connection.cursor()
        
        # Obtener productos
        try:
            cur.execute("SELECT id, Nombre_Menu, Precio, COALESCE(Categoria, ''), COALESCE(Imagen, ''), COALESCE(Descripcion, '') FROM menu ORDER BY id DESC")
            productos = cur.fetchall()
        except Exception:
            productos = []
        
        # Obtener estadísticas para el panel de control
        stats = {}
        try:
            # Total de productos
            cur.execute("SELECT COUNT(*) FROM menu")
            stats['total_productos'] = cur.fetchone()[0] or 0
        except Exception:
            stats['total_productos'] = 0
        
        try:
            # Pedidos pendientes
            cur.execute("SELECT COUNT(*) FROM pedidos WHERE estado = 'pendiente'")
            stats['pedidos_pendientes'] = cur.fetchone()[0] or 0
        except Exception:
            stats['pedidos_pendientes'] = 0
        
        try:
            # Total de pedidos
            cur.execute("SELECT COUNT(*) FROM pedidos")
            stats['total_pedidos'] = cur.fetchone()[0] or 0
        except Exception:
            stats['total_pedidos'] = 0
        
        cur.close()
        return render_template('admin.html', categorias=[], productos=productos, stats=stats)
    except Exception as e:
        print(f"Error al cargar dashboard admin: {e}")
        flash('Error al cargar el panel de administración', 'error')
        return render_template('admin.html', categorias=[], productos=[], stats={})

# ===== Panel de Mozo =====
@app.route('/mozo')
@mozo_required
def mozo_dashboard():
    ensure_client_orders_tables()
    try:
        cur = mysql.connection.cursor()
        # Asegurar que la columna mesa existe
        try:
            cur.execute("DESCRIBE pedidos")
            cols = [row[0].lower() for row in cur.fetchall()]
            if 'mesa' not in cols:
                cur.execute("ALTER TABLE pedidos ADD COLUMN mesa VARCHAR(50) NULL")
                mysql.connection.commit()
        except Exception:
            pass

        # Obtener pedidos de clientes (no pedidos del mozo)
        cur.execute(
            """
            SELECT p.id, COALESCE(p.mesa, '') AS mesa, COALESCE(u.nombre, '') AS cliente,
                   p.estado, p.creado_en
            FROM pedidos p
            LEFT JOIN usuarios u ON p.usuario_id = u.id
            ORDER BY p.id DESC
            """
        )
        base_rows = cur.fetchall()

        pedidos = []
        for row in base_rows:
            pedido_id = row[0]
            try:
                cur.execute(
                    """
                    SELECT pi.cantidad, pi.precio_unitario, m.Nombre_Menu
                    FROM pedido_items pi
                    JOIN menu m ON pi.menu_id = m.id
                    WHERE pi.pedido_id = %s
                    """,
                    (pedido_id,)
                )
                items = cur.fetchall()
                total = sum(float(it[0]) * float(it[1]) for it in items)
            except Exception:
                items = []
                total = 0.0

            pedidos.append((row[0], row[1], row[2], row[3], row[4], items, total))

        cur.close()
        return render_template('mozo.html', pedidos=pedidos)
    except Exception as e:
        print(f"Error cargando panel mozo: {e}")
        flash('Error al cargar panel de mozo', 'error')
        return render_template('mozo.html', pedidos=[])

# Esta ruta ya no se necesita - comentada porque no se crean pedidos desde el panel de mozos
# @app.route('/mozo/pedidos/crear', methods=['POST'])
# @mozo_required
# def mozo_pedido_crear():
#     ...

@app.route('/mozo/productos/crear', methods=['POST'])
@mozo_required
def mozo_productos_crear():
    nombre = request.form.get('nombre')
    precio = request.form.get('precio')
    categoria = (request.form.get('categoria') or '').lower()
    imagen = request.form.get('imagen') or ''
    descripcion = request.form.get('descripcion') or ''
    categorias_validas = ['desayunos','almuerzos','meriendas','cenas','postres','bebidas','comida_sin_tac','promociones']
    if not nombre:
        flash('El nombre del producto es obligatorio', 'error')
        return redirect(url_for('mozo_dashboard'))
    if not precio:
        flash('El precio es obligatorio', 'error')
        return redirect(url_for('mozo_dashboard'))
    try:
        precio_val = float(precio)
    except Exception:
        flash('El precio no es válido', 'error')
        return redirect(url_for('mozo_dashboard'))
    if not categoria or categoria not in categorias_validas:
        flash('Debes seleccionar una categoría válida', 'error')
        return redirect(url_for('mozo_dashboard'))
    try:
        # Asegurar que existe la tabla productos
        cur = mysql.connection.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS productos (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nombre VARCHAR(150) NOT NULL,
                descripcion TEXT NULL,
                precio DECIMAL(10,2) NOT NULL,
                imagen VARCHAR(255) NULL,
                categoria VARCHAR(50) NULL
            )
        """)
        mysql.connection.commit()
        
        # Manejo de subida de archivo
        f = request.files.get('imagen_file')
        if f and getattr(f, 'filename', ''):
            from werkzeug.utils import secure_filename
            filename = secure_filename(f.filename)
            _, ext = os.path.splitext(filename)
            if ext.lower() not in _ALLOWED_IMAGE_EXTS:
                flash('Formato de imagen no permitido', 'error')
                cur.close()
                return redirect(url_for('mozo_dashboard'))
            dest = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            try:
                f.save(dest)
                imagen = f"images/{filename}"
            except Exception as e:
                print(f"Error guardando imagen: {e}")
                flash('No se pudo guardar la imagen', 'error')
                cur.close()
                return redirect(url_for('mozo_dashboard'))
        
        # Insertar en la tabla productos
        cur.execute(
            "INSERT INTO productos (nombre, descripcion, precio, imagen, categoria) VALUES (%s, %s, %s, %s, %s)",
            (nombre, descripcion, precio_val, imagen, categoria)
        )
        product_id = cur.lastrowid
        mysql.connection.commit()
        print(f"[mozo_productos_crear] Producto insertado en 'productos' - id={product_id} nombre={nombre} cat={categoria} precio={precio_val}")
        cur.close()
        flash(f'Producto "{nombre}" agregado al menú correctamente', 'success')
    except Exception as e:
        print(f"Error mozo creando producto: {e}")
        import traceback
        traceback.print_exc()
        flash('Error al agregar producto', 'error')
    return redirect(url_for('mozo_dashboard'))

@app.route('/mozo/pedidos-cliente/<int:pedido_id>/estado', methods=['POST'])
@mozo_required
def mozo_pedido_cliente_estado(pedido_id: int):
    """Permite a los mozos actualizar el estado de pedidos de clientes"""
    nuevo_estado = request.form.get('estado', 'pendiente')
    try:
        ensure_client_orders_tables()
        cur = mysql.connection.cursor()
        cur.execute("UPDATE pedidos SET estado=%s WHERE id=%s", (nuevo_estado, pedido_id))
        mysql.connection.commit()
        cur.close()
        flash('Estado del pedido actualizado', 'success')
    except Exception as e:
        print(f"Error actualizando estado pedido cliente: {e}")
        flash('Error al actualizar estado', 'error')
    return redirect(url_for('mozo_dashboard'))

# ===== CRUD Categorías =====
@app.route('/admin/categorias/crear', methods=['POST'])
@admin_required
def admin_categorias_crear():
    nombre = request.form.get('nombre')
    orden = request.form.get('orden')
    if not nombre:
        flash('El nombre de la categoría es obligatorio', 'error')
        return redirect(url_for('admin_dashboard'))
    try:
        cur = mysql.connection.cursor()
        # Esquema actual: columnas `Nombre`, `orden`
        cur.execute("INSERT INTO categorias (Nombre, orden) VALUES (%s, %s)", (nombre, orden or ''))
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
    orden = request.form.get('orden')
    try:
        cur = mysql.connection.cursor()
        cur.execute("UPDATE categorias SET Nombre=%s, orden=%s WHERE id=%s", (nombre, orden or '', categoria_id))
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

# ===== CRUD Productos (tabla `menu`) =====
@app.route('/admin/productos/crear', methods=['POST'])
@admin_required
def admin_productos_crear():
    nombre = request.form.get('nombre')
    precio = request.form.get('precio')
    categoria = request.form.get('categoria')
    imagen = request.form.get('imagen')
    descripcion = request.form.get('descripcion', '')
    if not (nombre and precio):
        flash('Nombre y precio son obligatorios', 'error')
        return redirect(url_for('admin_dashboard'))
    try:
        ensure_menu_table_upgrade()
        cur = mysql.connection.cursor()
        cur.execute(
            "INSERT INTO menu (Nombre_Menu, Precio, Categoria, Imagen, Descripcion) VALUES (%s, %s, %s, %s, %s)",
            (nombre, precio, categoria, imagen, descripcion)
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
    precio = request.form.get('precio')
    categoria = request.form.get('categoria')
    imagen = request.form.get('imagen')
    descripcion = request.form.get('descripcion', '')
    try:
        ensure_menu_table_upgrade()
        cur = mysql.connection.cursor()
        cur.execute(
            "UPDATE menu SET Nombre_Menu=%s, Precio=%s, Categoria=%s, Imagen=%s, Descripcion=%s WHERE id=%s",
            (nombre, precio, categoria, imagen, descripcion, producto_id)
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
        cur.execute("DELETE FROM menu WHERE id=%s", (producto_id,))
        mysql.connection.commit()
        cur.close()
        flash('Producto eliminado', 'success')
    except Exception as e:
        print(f"Error eliminando producto: {e}")
        flash('Error al eliminar producto', 'error')
    return redirect(url_for('admin_dashboard'))

# ===== Carrito de compras (cliente) =====
def ensure_client_orders_tables():
    try:
        cur = mysql.connection.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS pedidos (
                id INT AUTO_INCREMENT PRIMARY KEY,
                usuario_id INT NULL,
                estado VARCHAR(20) DEFAULT 'pendiente',
                mesa VARCHAR(50) NULL,
                creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS pedido_items (
                id INT AUTO_INCREMENT PRIMARY KEY,
                pedido_id INT NOT NULL,
                menu_id INT NOT NULL,
                cantidad INT NOT NULL DEFAULT 1,
                precio_unitario DECIMAL(10,2) NOT NULL,
                FOREIGN KEY (pedido_id) REFERENCES pedidos(id),
                FOREIGN KEY (menu_id) REFERENCES menu(id)
            )
            """
        )
        mysql.connection.commit()
        cur.close()
    except Exception as e:
        print(f"Error asegurando tablas de pedidos cliente: {e}")

def _get_cart():
    return session.setdefault('cart', {})

@app.route('/cart')
def cart_view():
    cart = _get_cart()
    items = []
    total = 0.0
    try:
        cur = mysql.connection.cursor()
        for pid, entry in cart.items():
            try:
                # Si es un producto temporal
                if entry.get('temp', False):
                    cantidad = int(entry.get('qty', 1))
                    precio = float(entry.get('precio', 0))
                    subtotal = cantidad * precio
                    total += subtotal
                    items.append({
                        'id': pid,
                        'nombre': entry.get('nombre', 'Producto'),
                        'precio': precio,
                        'cantidad': cantidad,
                        'subtotal': subtotal,
                    })
                else:
                    # Producto de la base de datos
                    cur.execute("SELECT id, Nombre_Menu, Precio FROM menu WHERE id=%s", (pid,))
                    row = cur.fetchone()
                    if not row:
                        continue
                    cantidad = int(entry.get('qty', 1))
                    precio = float(row[2])
                    subtotal = cantidad * precio
                    total += subtotal
                    items.append({
                        'id': row[0],
                        'nombre': row[1],
                        'precio': precio,
                        'cantidad': cantidad,
                        'subtotal': subtotal,
                    })
            except Exception as e:
                print(f"Error cargando item {pid}: {e}")
                continue
        cur.close()
    except Exception as e:
        print(f"Error cargando carrito: {e}")
    return render_template('cart.html', items=items, total=total)

@app.route('/cart/add/<int:producto_id>', methods=['POST'])
def cart_add(producto_id: int):
    qty = int(request.form.get('qty', '1'))
    mesa = request.form.get('mesa', '')
    cart = _get_cart()
    key = str(producto_id)
    
    # Guardar la mesa en la sesión si no existe ya
    if mesa and 'mesa_carrito' not in session:
        session['mesa_carrito'] = mesa
    elif not mesa and 'mesa_carrito' in session:
        mesa = session['mesa_carrito']
    
    if key in cart:
        cart[key]['qty'] = int(cart[key].get('qty', 1)) + qty
    else:
        cart[key] = {'qty': qty}
    
    session['cart'] = cart
    flash('Producto agregado al carrito', 'success')
    return redirect(request.referrer or url_for('menu'))

@app.route('/cart/add/temp', methods=['POST'])
def cart_add_temp():
    nombre = request.form.get('nombre')
    precio = float(request.form.get('precio', 0))
    qty = int(request.form.get('qty', '1'))
    categoria = request.form.get('categoria', '')
    
    # Crear un ID único para el producto temporal usando hash del nombre
    import hashlib
    temp_id = 'temp_' + hashlib.md5(nombre.encode()).hexdigest()[:10]
    
    cart = _get_cart()
    if temp_id in cart:
        cart[temp_id]['qty'] += qty
    else:
        cart[temp_id] = {
            'qty': qty,
            'nombre': nombre,
            'precio': precio,
            'categoria': categoria,
            'temp': True
        }
    session['cart'] = cart
    flash(f'{nombre} agregado al carrito', 'success')
    return redirect(request.referrer or url_for('index'))

@app.route('/cart/update', methods=['POST'])
def cart_update():
    cart = _get_cart()
    for key, value in request.form.items():
        if key.startswith('qty_'):
            pid = key.split('qty_')[-1]
            try:
                qty = max(0, int(value))
            except Exception:
                qty = 1
            if pid in cart:
                if qty <= 0:
                    del cart[pid]
                else:
                    cart[pid]['qty'] = qty
    session['cart'] = cart
    flash('Carrito actualizado', 'success')
    return redirect(url_for('cart_view'))

@app.route('/cart/remove/<int:producto_id>', methods=['POST'])
def cart_remove(producto_id: int):
    cart = _get_cart()
    key = str(producto_id)
    if key in cart:
        del cart[key]
        session['cart'] = cart
    flash('Producto eliminado del carrito', 'info')
    return redirect(url_for('cart_view'))

@app.route('/cart/checkout', methods=['POST'])
def cart_checkout():
    cart = _get_cart()
    if not cart:
        flash('El carrito está vacío', 'error')
        return redirect(url_for('cart_view'))
    
    # Obtener la mesa del formulario
    mesa = request.form.get('mesa', '').strip()
    if not mesa:
        flash('Debes indicar el número de mesa', 'error')
        return redirect(url_for('cart_view'))
    
    ensure_client_orders_tables()
    try:
        cur = mysql.connection.cursor()
        # Verificar si la columna mesa existe, si no, agregarla
        try:
            cur.execute("DESCRIBE pedidos")
            cols = [row[0].lower() for row in cur.fetchall()]
            if 'mesa' not in cols:
                cur.execute("ALTER TABLE pedidos ADD COLUMN mesa VARCHAR(50) NULL")
                mysql.connection.commit()
        except Exception:
            pass
        
        cur.execute("INSERT INTO pedidos (usuario_id, estado, mesa) VALUES (%s, %s, %s)", (session.get('user_id'), 'pendiente', mesa))
        pedido_id = cur.lastrowid
        for pid, entry in cart.items():
            try:
                int(pid)  # Verificar que es un ID válido
                cur.execute("SELECT Precio FROM menu WHERE id=%s", (pid,))
                row = cur.fetchone()
                if not row:
                    continue
                precio = float(row[0])
                cantidad = int(entry.get('qty', 1))
                cur.execute(
                    "INSERT INTO pedido_items (pedido_id, menu_id, cantidad, precio_unitario) VALUES (%s, %s, %s, %s)",
                    (pedido_id, pid, cantidad, precio)
                )
            except ValueError:
                # Ignorar IDs no numéricos (productos temporales)
                continue
        mysql.connection.commit()
        cur.close()
        # Vaciar carrito y mesa
        session['cart'] = {}
        session.pop('mesa_carrito', None)
        flash('Pedido enviado correctamente', 'success')
    except Exception as e:
        print(f"Error en checkout: {e}")
        flash('Error al procesar el pedido', 'error')
    return redirect(url_for('index'))

@app.route('/api/producto/<int:producto_id>')
def api_producto(producto_id):
    try:
        ensure_productos_table_exists()
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT id, nombre, precio, COALESCE(categoria, ''), COALESCE(imagen, ''), COALESCE(descripcion, '')
            FROM productos WHERE id = %s
        """, (producto_id,))
        row = cur.fetchone()
        cur.close()
        
        if row:
            imagen_url = row[4]
            # Si la imagen es una ruta relativa (images/...), convertirla a URL completa
            if imagen_url and not imagen_url.startswith('http://') and not imagen_url.startswith('https://'):
                imagen_url = url_for('static', filename=imagen_url)
            
            return jsonify({
                'id': row[0],
                'nombre': row[1],
                'precio': float(row[2]),
                'categoria': row[3],
                'imagen': imagen_url,
                'descripcion': row[5] or 'Sin descripción disponible'
            })
        else:
            return jsonify({'error': 'Producto no encontrado'}), 404
    except Exception as e:
        print(f"Error al obtener producto: {e}")
        return jsonify({'error': 'Error al obtener producto'}), 500

# ===== Vista de pedidos para administrador =====
@app.route('/admin/pedidos-nuevo')
@admin_required
def admin_pedidos_nuevo():
    ensure_client_orders_tables()
    try:
        cur = mysql.connection.cursor()
        try:
            cur.execute("DESCRIBE pedidos")
            cols = [row[0].lower() for row in cur.fetchall()]
            if 'mesa' not in cols:
                cur.execute("ALTER TABLE pedidos ADD COLUMN mesa VARCHAR(50) NULL")
                mysql.connection.commit()
        except Exception:
            pass

        cur.execute(
            """
            SELECT p.id, COALESCE(p.mesa, '') AS mesa, COALESCE(u.nombre, '') AS cliente,
                   p.estado, p.creado_en
            FROM pedidos p
            LEFT JOIN usuarios u ON p.usuario_id = u.id
            ORDER BY p.id DESC
            """
        )
        base_rows = cur.fetchall()

        pedidos = []
        for row in base_rows:
            pedido_id = row[0]
            try:
                cur.execute(
                    """
                    SELECT pi.cantidad, pi.precio_unitario, m.Nombre_Menu
                    FROM pedido_items pi
                    JOIN menu m ON pi.menu_id = m.id
                    WHERE pi.pedido_id = %s
                    """,
                    (pedido_id,)
                )
                items = cur.fetchall()
                total = sum(float(it[0]) * float(it[1]) for it in items)
            except Exception:
                items = []
                total = 0.0

            pedidos.append((row[0], row[1], row[2], row[3], row[4], items, total))

        cur.close()
    except Exception as e:
        print(f"Error listando pedidos nuevo: {e}")
        pedidos = []
    return render_template('admin_pedidos_nuevo.html', pedidos=pedidos)

@app.route('/admin/pedidos/<int:pedido_id>/estado', methods=['POST'])
@admin_required
def admin_pedido_cambiar_estado(pedido_id: int):
    nuevo_estado = request.form.get('estado', 'pendiente')
    try:
        cur = mysql.connection.cursor()
        cur.execute("UPDATE pedidos SET estado=%s WHERE id=%s", (nuevo_estado, pedido_id))
        mysql.connection.commit()
        cur.close()
        flash('Estado del pedido actualizado', 'success')
    except Exception as e:
        print(f"Error actualizando estado de pedido: {e}")
        flash('Error al actualizar estado del pedido', 'error')
    return redirect(url_for('admin_pedidos_nuevo'))

# Eliminar pedido (solo si ya fue entregado)
@app.route('/admin/pedidos/<int:pedido_id>/eliminar', methods=['POST'])
@admin_required
def admin_pedido_eliminar(pedido_id: int):
    try:
        cur = mysql.connection.cursor()
        # Verificar estado del pedido
        cur.execute("SELECT estado FROM pedidos WHERE id=%s", (pedido_id,))
        row = cur.fetchone()
        if not row:
            cur.close()
            flash('Pedido no encontrado', 'error')
            return redirect(url_for('admin_pedidos_nuevo'))
        estado = (row[0] or '').lower()
        if estado != 'entregado':
            cur.close()
            flash('Solo se pueden eliminar pedidos entregados', 'error')
            return redirect(url_for('admin_pedidos_nuevo'))

        # Borrar primero items, luego pedido
        cur.execute("DELETE FROM pedido_items WHERE pedido_id=%s", (pedido_id,))
        cur.execute("DELETE FROM pedidos WHERE id=%s", (pedido_id,))
        mysql.connection.commit()
        cur.close()
        flash('Pedido eliminado', 'success')
    except Exception as e:
        print(f"Error eliminando pedido {pedido_id}: {e}")
        flash('Error al eliminar pedido', 'error')
    return redirect(url_for('admin_pedidos_nuevo'))

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
        cur.execute("SELECT * FROM usuarios WHERE id = %s", (session['user_id'],))
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
