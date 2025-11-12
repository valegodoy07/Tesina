from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
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

def _log_db_info(tag: str):
    """Log de información de base de datos (solo para debug)"""
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
    categorias = ['desayunos', 'almuerzos', 'cenas', 'meriendas', 'postres', 'bebidas', 'comida_sin_tac', 'promociones', 'veggie']
    productos_por_categoria = {c: [] for c in categorias}
    
    cur = None
    try:
        # Intentar obtener cursor
        try:
            cur = mysql.connection.cursor()
        except Exception as conn_error:
            print(f"[index] Error de conexión a BD: {conn_error}")
            # Si no hay conexión, continuar con productos vacíos
            cur = None
        
        if cur:
            try:
                # Crear tabla si no existe
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS productos (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        nombre VARCHAR(150) NOT NULL,
                        descripcion TEXT NULL,
                        precio DECIMAL(10,2) NOT NULL,
                        imagen VARCHAR(255) NULL,
                        categoria VARCHAR(50) NULL
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)
                mysql.connection.commit()
                
                # Leer y procesar productos
                try:
                    cur.execute("SELECT id, nombre, precio, categoria, imagen, descripcion FROM productos ORDER BY id DESC")
                    filas_raw = cur.fetchall()
                    
                    # Procesar y convertir categorías a minúsculas
                    filas = []
                    for row in filas_raw:
                        if row and len(row) >= 4:
                            cat_lower = (row[3] or '').lower().strip() if len(row) > 3 else ''
                            fila = (
                                row[0],
                                row[1],
                                float(row[2]) if row[2] else 0.0,
                                cat_lower,
                                row[4] if len(row) > 4 and row[4] else '',
                                row[5] if len(row) > 5 and row[5] else ''
                            )
                            filas.append(fila)
                except Exception as select_error:
                    print(f"[index] ERROR en SELECT: {select_error}")
                    import traceback
                    traceback.print_exc()
                    filas = []
                
                # Procesar productos por categoría
                for f in filas:
                    try:
                        if f and len(f) >= 4:
                            producto_id = f[0]
                            producto_nombre = f[1] if len(f) > 1 else 'Sin nombre'
                            producto_precio = float(f[2]) if len(f) > 2 and f[2] else 0.0
                            cat = (f[3] or '').lower().strip() if len(f) > 3 else ''
                            producto_imagen = (f[4] or '') if len(f) > 4 else ''
                            producto_descripcion = (f[5] or '') if len(f) > 5 else ''
                            
                            if cat and cat in categorias:
                                producto_completo = (producto_id, producto_nombre, producto_precio, cat, producto_imagen, producto_descripcion)
                                productos_por_categoria[cat].append(producto_completo)
                    except Exception as e:
                        print(f"[index] Error procesando producto: {e}")
                        continue
            except Exception as db_error:
                print(f"[index] Error en consulta BD: {db_error}")
            finally:
                if cur:
                    try:
                        cur.close()
                    except:
                        pass
        
    except Exception as e:
        print(f"[index] ERROR general: {e}")
        import traceback
        traceback.print_exc()
    
    ctx = {'productos_por_categoria': productos_por_categoria}
    if 'user_id' in session:
        ctx['usuario'] = session.get('nombre')
    
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
    categorias_validas = ['desayunos', 'almuerzos', 'meriendas', 'cenas', 'postres', 'bebidas', 'comida_sin_tac', 'promociones', 'veggie']
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
    productos_lista = []
    pedidos = []
    
    conn = None
    cur = None
    try:
        # Usar la misma conexión para todo
        conn = mysql.connection
        cur = conn.cursor()
        
        print(f"\n[mozo_dashboard] ===== CARGANDO PANEL DE MOZO =====")
        print(f"[mozo_dashboard] Conexión obtenida: {type(conn)}")
        
        # Verificar base de datos
        try:
            cur.execute("SELECT DATABASE()")
            db_result = cur.fetchone()
            db_name = db_result[0] if db_result else "DESCONOCIDA"
            print(f"[mozo_dashboard] Usando base de datos: {db_name}")
        except Exception as db_error:
            print(f"[mozo_dashboard] Error verificando BD: {db_error}")
        
        # Cargar productos de la tabla productos
        try:
            cur.execute("""
                SELECT id, nombre, precio, categoria, imagen, descripcion 
                FROM productos 
                ORDER BY id DESC
            """)
            productos_lista = cur.fetchall()
            print(f"[mozo_dashboard] Productos cargados: {len(productos_lista)}")
        except Exception as prod_error:
            print(f"[mozo_dashboard] Error cargando productos: {prod_error}")
            import traceback
            traceback.print_exc()
            productos_lista = []
        
        # Asegurar que la columna mesa y nombre_cliente existen
        try:
            cur.execute("DESCRIBE pedidos")
            cols = [row[0].lower() for row in cur.fetchall()]
            print(f"[mozo_dashboard] Columnas en tabla pedidos: {cols}")
            
            if 'mesa' not in cols:
                print(f"[mozo_dashboard] Agregando columna 'mesa'...")
                cur.execute("ALTER TABLE pedidos ADD COLUMN mesa VARCHAR(50) NULL")
                conn.commit()
            
            if 'nombre_cliente' not in cols:
                print(f"[mozo_dashboard] Agregando columna 'nombre_cliente'...")
                cur.execute("ALTER TABLE pedidos ADD COLUMN nombre_cliente VARCHAR(100) NULL")
                conn.commit()
        except Exception as alter_error:
            print(f"[mozo_dashboard] Error verificando/agregando columnas: {alter_error}")
            import traceback
            traceback.print_exc()

        # Verificar que la tabla pedidos existe y tiene datos
        try:
            cur.execute("SELECT COUNT(*) FROM pedidos")
            total_pedidos = cur.fetchone()[0]
            print(f"[mozo_dashboard] Total pedidos en BD: {total_pedidos}")
        except Exception as count_error:
            print(f"[mozo_dashboard] Error contando pedidos: {count_error}")
            total_pedidos = 0

        # Obtener pedidos de clientes
        try:
            cur.execute(
                """
                SELECT p.id, COALESCE(p.mesa, '') AS mesa, 
                       COALESCE(p.nombre_cliente, u.nombre, 'Cliente') AS cliente,
                       p.estado, p.creado_en
                FROM pedidos p
                LEFT JOIN usuarios u ON p.usuario_id = u.id
                ORDER BY p.id DESC
                """
            )
            base_rows = cur.fetchall()
            print(f"[mozo_dashboard] Consulta ejecutada - Encontrados {len(base_rows)} pedidos en BD")
            
            if len(base_rows) == 0:
                print(f"[mozo_dashboard] ⚠ No hay pedidos en la tabla 'pedidos'")
            else:
                print(f"[mozo_dashboard] Primeros pedidos: IDs {[r[0] for r in base_rows[:5]]}")
        except Exception as query_error:
            print(f"[mozo_dashboard] ✗ ERROR en consulta de pedidos: {query_error}")
            import traceback
            traceback.print_exc()
            base_rows = []

        # Procesar cada pedido y obtener sus items
        for row in base_rows:
            pedido_id = row[0]
            try:
                # Intentar obtener items desde productos primero, luego desde menu
                cur.execute(
                    """
                    SELECT pi.cantidad, pi.precio_unitario, 
                           COALESCE(pr.nombre, m.Nombre_Menu, CONCAT('Producto ID:', pi.menu_id)) AS nombre_producto,
                           COALESCE(pi.notas, '') AS notas
                    FROM pedido_items pi
                    LEFT JOIN productos pr ON pi.menu_id = pr.id
                    LEFT JOIN menu m ON pi.menu_id = m.id
                    WHERE pi.pedido_id = %s
                    ORDER BY pi.id
                    """,
                    (pedido_id,)
                )
                items = cur.fetchall()
                total = sum(float(it[0]) * float(it[1]) for it in items) if items else 0.0
                
                if len(items) > 0:
                    print(f"  ✓ Pedido {pedido_id}: {len(items)} items encontrados - Total: ${total:.2f}")
                else:
                    print(f"  ⚠ Pedido {pedido_id}: SIN ITEMS")
                    # Verificar si hay items en la tabla
                    cur.execute("SELECT COUNT(*) FROM pedido_items WHERE pedido_id = %s", (pedido_id,))
                    count = cur.fetchone()[0]
                    print(f"    Items en BD para pedido {pedido_id}: {count}")
                
                pedidos.append((row[0], row[1], row[2], row[3], row[4], items, total))
            except Exception as e:
                print(f"[mozo_dashboard] ✗ Error obteniendo items del pedido {pedido_id}: {e}")
                import traceback
                traceback.print_exc()
                items = []
                total = 0.0
                pedidos.append((row[0], row[1], row[2], row[3], row[4], items, total))

        print(f"[mozo_dashboard] Total pedidos procesados: {len(pedidos)}")
        print(f"[mozo_dashboard] ================================\n")
        
        cur.close()
        conn.close()
        return render_template('mozo.html', pedidos=pedidos, productos=productos_lista)
    except Exception as e:
        print(f"[mozo_dashboard] ✗ ERROR general: {e}")
        import traceback
        traceback.print_exc()
        flash('Error al cargar panel de mozo', 'error')
        if cur:
            try:
                cur.close()
            except:
                pass
        if conn:
            try:
                conn.close()
            except:
                pass
        return render_template('mozo.html', pedidos=[], productos=[])

# Esta ruta ya no se necesita - comentada porque no se crean pedidos desde el panel de mozos
# @app.route('/mozo/pedidos/crear', methods=['POST'])
# @mozo_required
# def mozo_pedido_crear():
#     ...

@app.route('/mozo/productos/crear', methods=['POST'])
@mozo_required
def mozo_productos_crear():
    nombre = request.form.get('nombre', '').strip()
    precio = request.form.get('precio', '').strip()
    categoria_raw = request.form.get('categoria') or ''
    categoria = categoria_raw.lower().strip()  # Asegurar que esté en minúsculas y sin espacios
    descripcion = request.form.get('descripcion', '').strip()
    categorias_validas = ['desayunos','almuerzos','meriendas','cenas','postres','bebidas','comida_sin_tac','promociones','veggie']
    
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
    
    conn = None
    cur = None
    try:
        # Obtener conexión y cursor - USAR LA MISMA CONEXIÓN para todo
        conn = mysql.connection
        cur = conn.cursor()
        
        # Crear tabla si no existe
        try:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS productos (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    nombre VARCHAR(150) NOT NULL,
                    descripcion TEXT NULL,
                    precio DECIMAL(10,2) NOT NULL,
                    imagen VARCHAR(255) NULL,
                    categoria VARCHAR(50) NULL,
                    INDEX idx_categoria (categoria)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            conn.commit()
        except Exception as table_error:
            print(f"[mozo_productos_crear] ERROR creando tabla: {table_error}")
            import traceback
            traceback.print_exc()
            cur.close()
            flash(f'Error al crear tabla: {str(table_error)}', 'error')
            return redirect(url_for('mozo_dashboard'))
        
        # Manejo de subida de archivo
        imagen_url = request.form.get('imagen', '').strip()  # URL de imagen si se proporciona
        imagen = imagen_url  # Inicializar con la URL si existe
        
        f = request.files.get('imagen_file')
        if f and getattr(f, 'filename', ''):
            from werkzeug.utils import secure_filename
            import time
            import hashlib
            
            filename = secure_filename(f.filename)
            _, ext = os.path.splitext(filename)
            
            if ext.lower() not in _ALLOWED_IMAGE_EXTS:
                flash('Formato de imagen no permitido. Formatos permitidos: JPG, PNG, GIF, WEBP, AVIF', 'error')
                cur.close()
                return redirect(url_for('mozo_dashboard'))
            
            # Generar nombre único para evitar sobrescrituras
            timestamp = int(time.time())
            hash_part = hashlib.md5(f"{nombre}_{timestamp}".encode()).hexdigest()[:8]
            unique_filename = f"{timestamp}_{hash_part}{ext}"
            
            dest = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            
            try:
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                f.save(dest)
                
                if os.path.exists(dest):
                    imagen = f"images/{unique_filename}"
                else:
                    flash('No se pudo guardar la imagen', 'error')
                    cur.close()
                    return redirect(url_for('mozo_dashboard'))
            except Exception as e:
                print(f"[mozo_productos_crear] ERROR guardando imagen: {e}")
                import traceback
                traceback.print_exc()
                flash(f'Error al guardar la imagen: {str(e)}', 'error')
                cur.close()
                return redirect(url_for('mozo_dashboard'))
        elif not imagen_url:
            imagen = ''
        
        # Verificar que no exista un producto con el mismo nombre
        cur.execute("SELECT id FROM productos WHERE nombre = %s", (nombre,))
        existing = cur.fetchone()
        if existing:
            flash(f'Ya existe un producto con el nombre "{nombre}"', 'warning')
        
        # Asegurar que la categoría esté en minúsculas antes de insertar
        categoria_final = categoria.lower().strip()
        if categoria_final not in categorias_validas:
            flash(f'Categoría "{categoria_final}" no válida. Categorías válidas: {", ".join(categorias_validas)}', 'error')
            cur.close()
            return redirect(url_for('mozo_dashboard'))
        
        # Insertar producto
        try:
            cur.execute(
                "INSERT INTO productos (nombre, descripcion, precio, imagen, categoria) VALUES (%s, %s, %s, %s, %s)",
                (nombre, descripcion, precio_val, imagen, categoria_final)
            )
            product_id = cur.lastrowid
        except Exception as insert_error:
            print(f"[mozo_productos_crear] ERROR en INSERT: {insert_error}")
            import traceback
            traceback.print_exc()
            conn.rollback()
            cur.close()
            flash(f'Error al insertar producto: {str(insert_error)}', 'error')
            return redirect(url_for('mozo_dashboard'))
        
        # Hacer commit
        try:
            conn.commit()
        except Exception as commit_error:
            print(f"[mozo_productos_crear] ERROR en commit: {commit_error}")
            import traceback
            traceback.print_exc()
            conn.rollback()
            cur.close()
            flash(f'Error al guardar producto: {str(commit_error)}', 'error')
            return redirect(url_for('mozo_dashboard'))
        
        cur.close()
        flash(f'Producto "{nombre}" agregado al menú correctamente', 'success')
        
    except Exception as e:
        print(f"[mozo_productos_crear] ERROR general: {e}")
        import traceback
        traceback.print_exc()
        try:
            if conn:
                conn.rollback()
        except:
            pass
        flash(f'Error al agregar producto: {str(e)}', 'error')
        if cur:
            try:
                cur.close()
            except:
                pass
    
    return redirect(url_for('mozo_dashboard'))

@app.route('/mozo/productos/<int:producto_id>/eliminar', methods=['POST'])
@mozo_required
def mozo_productos_eliminar(producto_id: int):
    """Eliminar un producto del menú"""
    try:
        cur = mysql.connection.cursor()
        
        # Obtener nombre del producto antes de eliminarlo
        cur.execute("SELECT nombre FROM productos WHERE id = %s", (producto_id,))
        producto = cur.fetchone()
        
        if not producto:
            flash('Producto no encontrado', 'error')
            cur.close()
            return redirect(url_for('mozo_dashboard'))
        
        nombre_producto = producto[0]
        
        # Eliminar el producto
        cur.execute("DELETE FROM productos WHERE id = %s", (producto_id,))
        mysql.connection.commit()
        cur.close()
        
        flash(f'Producto "{nombre_producto}" eliminado correctamente', 'success')
        print(f"[mozo_productos_eliminar] Producto {producto_id} eliminado: {nombre_producto}")
    except Exception as e:
        print(f"[mozo_productos_eliminar] Error: {e}")
        import traceback
        traceback.print_exc()
        try:
            mysql.connection.rollback()
        except:
            pass
        flash(f'Error al eliminar producto: {str(e)}', 'error')
    
    return redirect(url_for('mozo_dashboard'))

@app.route('/mozo/productos/<int:producto_id>/editar', methods=['POST'])
@mozo_required
def mozo_productos_editar(producto_id: int):
    """Editar un producto del menú"""
    nombre = request.form.get('nombre')
    precio = request.form.get('precio')
    categoria = (request.form.get('categoria') or '').lower()
    descripcion = request.form.get('descripcion', '')
    imagen = request.form.get('imagen', '')
    
    categorias_validas = ['desayunos', 'almuerzos', 'cenas', 'meriendas', 'postres', 'bebidas', 'comida_sin_tac', 'promociones', 'veggie']
    
    if not nombre or not precio or not categoria:
        flash('Todos los campos son requeridos', 'error')
        return redirect(url_for('mozo_dashboard'))
    
    try:
        precio_val = float(precio)
        if precio_val <= 0:
            flash('El precio debe ser mayor a 0', 'error')
            return redirect(url_for('mozo_dashboard'))
    except ValueError:
        flash('El precio no es válido', 'error')
        return redirect(url_for('mozo_dashboard'))
    
    if categoria not in categorias_validas:
        flash('Debes seleccionar una categoría válida', 'error')
        return redirect(url_for('mozo_dashboard'))
    
    cur = None
    try:
        cur = mysql.connection.cursor()
        
        # Verificar que el producto existe
        cur.execute("SELECT id FROM productos WHERE id = %s", (producto_id,))
        if not cur.fetchone():
            flash('Producto no encontrado', 'error')
            cur.close()
            return redirect(url_for('mozo_dashboard'))
        
        # Manejo de subida de archivo
        f = request.files.get('imagen_file')
        if f and getattr(f, 'filename', ''):
            from werkzeug.utils import secure_filename
            filename = secure_filename(f.filename)
            if filename:
                _, ext = os.path.splitext(filename)
                if ext.lower() not in _ALLOWED_IMAGE_EXTS:
                    flash('Formato de imagen no permitido', 'error')
                    cur.close()
                    return redirect(url_for('mozo_dashboard'))
                
                # Generar nombre único
                import time
                unique_filename = f"{int(time.time())}_{filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                try:
                    f.save(filepath)
                    imagen = f"images/{unique_filename}"
                    print(f"[mozo_productos_editar] Imagen guardada: {imagen}")
                except Exception as save_error:
                    print(f"[mozo_productos_editar] Error guardando imagen: {save_error}")
                    flash('Error al guardar la imagen', 'error')
                    cur.close()
                    return redirect(url_for('mozo_dashboard'))
        
        # Actualizar producto
        if imagen:
            cur.execute("""
                UPDATE productos 
                SET nombre = %s, descripcion = %s, precio = %s, imagen = %s, categoria = %s
                WHERE id = %s
            """, (nombre, descripcion, precio_val, imagen, categoria, producto_id))
        else:
            # Si no hay nueva imagen, mantener la anterior
            cur.execute("""
                UPDATE productos 
                SET nombre = %s, descripcion = %s, precio = %s, categoria = %s
                WHERE id = %s
            """, (nombre, descripcion, precio_val, categoria, producto_id))
        
        mysql.connection.commit()
        cur.close()
        
        flash(f'Producto "{nombre}" actualizado correctamente', 'success')
        print(f"[mozo_productos_editar] Producto {producto_id} actualizado: {nombre}")
    except Exception as e:
        print(f"[mozo_productos_editar] Error: {e}")
        import traceback
        traceback.print_exc()
        try:
            mysql.connection.rollback()
        except:
            pass
        flash(f'Error al actualizar producto: {str(e)}', 'error')
        if cur:
            cur.close()
    
    return redirect(url_for('mozo_dashboard'))

@app.route('/mozo/pedidos-cliente/<int:pedido_id>/estado', methods=['POST'])
@mozo_required
def mozo_pedido_cliente_estado(pedido_id: int):
    """Permite a los mozos actualizar el estado de pedidos de clientes"""
    nuevo_estado = request.form.get('estado', '').strip()
    
    print(f"\n[mozo_pedido_cliente_estado] ===== ACTUALIZANDO ESTADO =====")
    print(f"[mozo_pedido_cliente_estado] Pedido ID: {pedido_id}")
    print(f"[mozo_pedido_cliente_estado] Nuevo estado recibido: '{nuevo_estado}'")
    print(f"[mozo_pedido_cliente_estado] Form data completo: {request.form}")
    
    if not nuevo_estado:
        flash('Debes seleccionar un estado válido', 'error')
        print(f"[mozo_pedido_cliente_estado] ✗ Error: No se recibió estado")
        return redirect(url_for('mozo_dashboard'))
    
    estados_validos = ['pendiente', 'en_preparacion', 'listo', 'entregado', 'cancelado']
    if nuevo_estado not in estados_validos:
        flash(f'Estado "{nuevo_estado}" no es válido', 'error')
        print(f"[mozo_pedido_cliente_estado] ✗ Error: Estado '{nuevo_estado}' no válido")
        return redirect(url_for('mozo_dashboard'))
    
    conn = None
    cur = None
    try:
        ensure_client_orders_tables()
        conn = mysql.connection
        cur = conn.cursor()
        
        # Verificar estado actual del pedido
        cur.execute("SELECT estado, nombre_cliente, mesa FROM pedidos WHERE id = %s", (pedido_id,))
        pedido_actual = cur.fetchone()
        
        if not pedido_actual:
            flash('Pedido no encontrado', 'error')
            print(f"[mozo_pedido_cliente_estado] ✗ Error: Pedido {pedido_id} no encontrado")
            cur.close()
            return redirect(url_for('mozo_dashboard'))
        
        estado_anterior = pedido_actual[0]
        print(f"[mozo_pedido_cliente_estado] Estado anterior: '{estado_anterior}'")
        print(f"[mozo_pedido_cliente_estado] Estado nuevo: '{nuevo_estado}'")
        
        # Actualizar el estado
        cur.execute("UPDATE pedidos SET estado=%s WHERE id=%s", (nuevo_estado, pedido_id))
        rows_affected = cur.rowcount
        print(f"[mozo_pedido_cliente_estado] Filas afectadas por UPDATE: {rows_affected}")
        
        if rows_affected == 0:
            print(f"[mozo_pedido_cliente_estado] ⚠ ADVERTENCIA: No se actualizó ninguna fila")
            flash('No se pudo actualizar el estado del pedido', 'error')
            cur.close()
            return redirect(url_for('mozo_dashboard'))
        
        # Hacer commit
        conn.commit()
        print(f"[mozo_pedido_cliente_estado] ✓ Commit realizado")
        
        # Verificar que se actualizó correctamente
        cur.execute("SELECT estado FROM pedidos WHERE id = %s", (pedido_id,))
        estado_verificado = cur.fetchone()
        if estado_verificado:
            estado_final = estado_verificado[0]
            print(f"[mozo_pedido_cliente_estado] Estado verificado después del commit: '{estado_final}'")
            if estado_final != nuevo_estado:
                print(f"[mozo_pedido_cliente_estado] ✗ ERROR: El estado no se actualizó correctamente!")
                print(f"[mozo_pedido_cliente_estado]   Esperado: '{nuevo_estado}', Obtenido: '{estado_final}'")
                flash(f'Error: El estado no se actualizó correctamente', 'error')
            else:
                print(f"[mozo_pedido_cliente_estado] ✓ Estado actualizado correctamente")
                flash(f'Estado del pedido actualizado a "{nuevo_estado}"', 'success')
        else:
            print(f"[mozo_pedido_cliente_estado] ✗ ERROR: No se pudo verificar el estado")
            flash('Error al verificar el estado actualizado', 'error')
        
        cur.close()
        print(f"[mozo_pedido_cliente_estado] ================================\n")
        
    except Exception as e:
        print(f"[mozo_pedido_cliente_estado] ✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        try:
            if conn:
                conn.rollback()
        except:
            pass
        flash(f'Error al actualizar estado: {str(e)}', 'error')
        if cur:
            try:
                cur.close()
            except:
                pass
    
    return redirect(url_for('mozo_dashboard'))

@app.route('/mozo/pedidos-cliente/<int:pedido_id>/eliminar', methods=['POST'])
@mozo_required
def mozo_pedido_cliente_eliminar(pedido_id: int):
    """Eliminar un pedido de cliente (solo pedidos entregados o cancelados)"""
    conn = None
    cur = None
    try:
        ensure_client_orders_tables()
        conn = mysql.connection
        cur = conn.cursor()
        
        print(f"\n[mozo_pedido_cliente_eliminar] ===== ELIMINANDO PEDIDO =====")
        print(f"[mozo_pedido_cliente_eliminar] Pedido ID: {pedido_id}")
        
        # Verificar el estado del pedido antes de eliminar
        cur.execute("SELECT estado, nombre_cliente, mesa FROM pedidos WHERE id = %s", (pedido_id,))
        pedido = cur.fetchone()
        
        if not pedido:
            flash('Pedido no encontrado', 'error')
            print(f"[mozo_pedido_cliente_eliminar] ✗ Error: Pedido {pedido_id} no encontrado")
            cur.close()
            return redirect(url_for('mozo_dashboard'))
        
        estado = pedido[0]
        nombre_cliente = pedido[1] or 'Cliente'
        mesa = pedido[2] or 'N/A'
        
        print(f"[mozo_pedido_cliente_eliminar] Estado: {estado}, Cliente: {nombre_cliente}, Mesa: {mesa}")
        
        # Solo permitir eliminar pedidos entregados o cancelados
        if estado not in ['entregado', 'cancelado']:
            flash(f'No se puede eliminar un pedido con estado "{estado}". Solo se pueden eliminar pedidos entregados o cancelados.', 'warning')
            print(f"[mozo_pedido_cliente_eliminar] ✗ Error: Estado '{estado}' no permite eliminación")
            cur.close()
            return redirect(url_for('mozo_dashboard'))
        
        # Primero eliminar los items del pedido (por si CASCADE no funciona)
        try:
            cur.execute("DELETE FROM pedido_items WHERE pedido_id = %s", (pedido_id,))
            items_eliminados = cur.rowcount
            print(f"[mozo_pedido_cliente_eliminar] Items eliminados: {items_eliminados}")
        except Exception as items_error:
            print(f"[mozo_pedido_cliente_eliminar] ⚠ Advertencia al eliminar items: {items_error}")
            # Continuar de todas formas, puede que CASCADE lo haga automáticamente
        
        # Eliminar el pedido
        cur.execute("DELETE FROM pedidos WHERE id = %s", (pedido_id,))
        rows_affected = cur.rowcount
        print(f"[mozo_pedido_cliente_eliminar] Filas afectadas por DELETE: {rows_affected}")
        
        if rows_affected == 0:
            flash('No se pudo eliminar el pedido', 'error')
            print(f"[mozo_pedido_cliente_eliminar] ✗ Error: No se eliminó ninguna fila")
            cur.close()
            return redirect(url_for('mozo_dashboard'))
        
        # Hacer commit
        conn.commit()
        print(f"[mozo_pedido_cliente_eliminar] ✓ Commit realizado")
        
        flash(f'Pedido #{pedido_id} eliminado correctamente (Cliente: {nombre_cliente}, Mesa: {mesa})', 'success')
        print(f"[mozo_pedido_cliente_eliminar] ✓ Pedido {pedido_id} eliminado exitosamente")
        print(f"[mozo_pedido_cliente_eliminar] ================================\n")
        
        cur.close()
        
    except Exception as e:
        print(f"[mozo_pedido_cliente_eliminar] ✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        try:
            if conn:
                conn.rollback()
                print(f"[mozo_pedido_cliente_eliminar] Rollback realizado")
        except Exception as rollback_error:
            print(f"[mozo_pedido_cliente_eliminar] Error en rollback: {rollback_error}")
        flash(f'Error al eliminar pedido: {str(e)}', 'error')
        if cur:
            try:
                cur.close()
            except:
                pass
    
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
                nombre_cliente VARCHAR(100) NULL,
                creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
            )
            """
        )
        # Asegurar que las columnas existan (por si la tabla ya existía sin ellas)
        try:
            cur.execute("DESCRIBE pedidos")
            cols = [row[0].lower() for row in cur.fetchall()]
            if 'mesa' not in cols:
                cur.execute("ALTER TABLE pedidos ADD COLUMN mesa VARCHAR(50) NULL")
            if 'nombre_cliente' not in cols:
                cur.execute("ALTER TABLE pedidos ADD COLUMN nombre_cliente VARCHAR(100) NULL")
            mysql.connection.commit()
        except Exception as e:
            print(f"Error verificando columnas de pedidos: {e}")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS pedido_items (
                id INT AUTO_INCREMENT PRIMARY KEY,
                pedido_id INT NOT NULL,
                menu_id INT NOT NULL,
                cantidad INT NOT NULL DEFAULT 1,
                precio_unitario DECIMAL(10,2) NOT NULL,
                notas TEXT NULL,
                FOREIGN KEY (pedido_id) REFERENCES pedidos(id) ON DELETE CASCADE
            )
            """
        )
        # Asegurar que la columna notas existe (por si la tabla ya existía sin ella)
        try:
            cur.execute("DESCRIBE pedido_items")
            cols = [row[0].lower() for row in cur.fetchall()]
            if 'notas' not in cols:
                cur.execute("ALTER TABLE pedido_items ADD COLUMN notas TEXT NULL")
                mysql.connection.commit()
        except Exception as e:
            print(f"Error verificando columna notas en pedido_items: {e}")
        # Intentar eliminar la foreign key restrictiva a menu si existe
        try:
            cur.execute("""
                SELECT CONSTRAINT_NAME 
                FROM information_schema.KEY_COLUMN_USAGE 
                WHERE TABLE_NAME = 'pedido_items' 
                AND TABLE_SCHEMA = DATABASE()
                AND REFERENCED_TABLE_NAME = 'menu'
            """)
            fk_result = cur.fetchone()
            if fk_result:
                fk_name = fk_result[0]
                cur.execute(f"ALTER TABLE pedido_items DROP FOREIGN KEY {fk_name}")
                mysql.connection.commit()
                print(f"[ensure_client_orders_tables] Foreign key {fk_name} eliminada de pedido_items")
        except Exception as e:
            print(f"[ensure_client_orders_tables] No se pudo eliminar foreign key (puede que no exista): {e}")
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
    nombre_cliente = session.get('nombre_cliente', '')
    mesa_carrito = session.get('mesa_carrito', '')
    
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
                        'notas': entry.get('notas', ''),
                    })
                else:
                    # Producto de la base de datos - usar tabla productos
                    try:
                        cur.execute("SELECT id, nombre, precio FROM productos WHERE id=%s", (pid,))
                        row = cur.fetchone()
                    except:
                        # Si no existe en productos, intentar en menu
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
                        'notas': entry.get('notas', ''),
                    })
            except Exception as e:
                print(f"Error cargando item {pid}: {e}")
                continue
        cur.close()
    except Exception as e:
        print(f"Error cargando carrito: {e}")
    return render_template('cart.html', items=items, total=total, nombre_cliente=nombre_cliente, mesa_carrito=mesa_carrito)

@app.route('/cart/add/<int:producto_id>', methods=['POST'])
def cart_add(producto_id: int):
    qty = int(request.form.get('qty', '1'))
    mesa = request.form.get('mesa', '').strip()
    nombre_cliente = request.form.get('nombre_cliente', '').strip()
    notas = request.form.get('notas', '').strip()
    
    cart = _get_cart()
    key = str(producto_id)
    
    # Guardar nombre del cliente y mesa en la sesión
    if nombre_cliente:
        session['nombre_cliente'] = nombre_cliente
    if mesa:
        session['mesa_carrito'] = mesa
    
    # Obtener nombre del producto para el mensaje
    try:
        cur = mysql.connection.cursor()
        # Intentar obtener de productos primero
        cur.execute("SELECT nombre FROM productos WHERE id = %s", (producto_id,))
        row = cur.fetchone()
        if not row:
            # Si no está en productos, buscar en menu
            cur.execute("SELECT Nombre_Menu FROM menu WHERE id = %s", (producto_id,))
            row = cur.fetchone()
        nombre_producto = row[0] if row else 'Producto'
        cur.close()
    except:
        nombre_producto = 'Producto'
    
    # Si el producto ya está en el carrito, incrementar cantidad
    if key in cart:
        cart[key]['qty'] = int(cart[key].get('qty', 1)) + qty
        # Si hay nuevas notas, agregarlas o actualizarlas
        if notas:
            notas_existentes = cart[key].get('notas', '')
            if notas_existentes:
                cart[key]['notas'] = f"{notas_existentes}; {notas}"
            else:
                cart[key]['notas'] = notas
        flash(f'Cantidad actualizada: {nombre_producto} x{qty} agregado al carrito', 'success')
    else:
        cart[key] = {'qty': qty}
        if notas:
            cart[key]['notas'] = notas
        flash(f'{nombre_producto} agregado al carrito (Cantidad: {qty})', 'success')
    
    # Guardar nombre del cliente y mesa en cada item del carrito
    if nombre_cliente:
        cart[key]['nombre_cliente'] = nombre_cliente
    if mesa:
        cart[key]['mesa'] = mesa
    
    session['cart'] = cart
    return redirect(url_for('index'))

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
    
    # Obtener nombre del cliente, mesa y datos del formulario
    nombre_cliente = request.form.get('nombre_cliente', '').strip() or session.get('nombre_cliente', '').strip()
    mesa = request.form.get('mesa', '').strip() or session.get('mesa_carrito', '').strip()
    
    if not nombre_cliente:
        flash('Debes indicar el nombre del cliente', 'error')
        return redirect(url_for('cart_view'))
    
    if not mesa:
        flash('Debes indicar el número de mesa', 'error')
        return redirect(url_for('cart_view'))
    
    ensure_client_orders_tables()
    conn = None
    cur = None
    try:
        # Usar la misma conexión para todo
        conn = mysql.connection
        cur = conn.cursor()
        
        print(f"\n[CHECKOUT] ===== PROCESANDO PEDIDO DESDE CARRITO =====")
        print(f"[CHECKOUT] Cliente: {nombre_cliente}, Mesa: {mesa}, Items en carrito: {len(cart)}")
        
        # Verificar base de datos
        try:
            cur.execute("SELECT DATABASE()")
            db_result = cur.fetchone()
            db_name = db_result[0] if db_result else "DESCONOCIDA"
            print(f"[CHECKOUT] Usando base de datos: {db_name}")
        except Exception as db_error:
            print(f"[CHECKOUT] Error verificando BD: {db_error}")
        
        # Verificar si las columnas existen
        try:
            cur.execute("DESCRIBE pedidos")
            cols = [row[0].lower() for row in cur.fetchall()]
            print(f"[CHECKOUT] Columnas en tabla pedidos: {cols}")
            
            if 'mesa' not in cols:
                print(f"[CHECKOUT] Agregando columna 'mesa'...")
                cur.execute("ALTER TABLE pedidos ADD COLUMN mesa VARCHAR(50) NULL")
                conn.commit()
            
            if 'nombre_cliente' not in cols:
                print(f"[CHECKOUT] Agregando columna 'nombre_cliente'...")
                cur.execute("ALTER TABLE pedidos ADD COLUMN nombre_cliente VARCHAR(100) NULL")
                conn.commit()
        except Exception as alter_error:
            print(f"[CHECKOUT] Error verificando/agregando columnas: {alter_error}")
            import traceback
            traceback.print_exc()
        
        # Obtener usuario_id si está logueado
        usuario_id = session.get('user_id') if 'user_id' in session else None
        
        # Crear el pedido
        print(f"[CHECKOUT] Creando pedido en BD...")
        cur.execute(
            "INSERT INTO pedidos (usuario_id, estado, mesa, nombre_cliente) VALUES (%s, %s, %s, %s)",
            (usuario_id, 'pendiente', mesa, nombre_cliente)
        )
        pedido_id = cur.lastrowid
        print(f"[CHECKOUT] ✓ Pedido creado con ID: {pedido_id}")
        
        # Hacer commit del pedido antes de agregar items
        conn.commit()
        print(f"[CHECKOUT] ✓ Commit del pedido realizado")
        
        # Agregar items del carrito
        items_agregados = 0
        for pid, entry in cart.items():
            try:
                cantidad = int(entry.get('qty', 1))
                print(f"[CHECKOUT] Procesando item: {pid}, cantidad: {cantidad}")
                menu_id = None
                precio = 0.0
                nombre_producto = 'Producto'
                
                # Si es un producto temporal, usar los datos guardados
                if entry.get('temp') and 'precio' in entry:
                    precio = float(entry.get('precio', 0))
                    nombre_producto = entry.get('nombre', 'Producto')
                    # Para productos temporales, buscar si existe en productos o menu
                    try:
                        cur.execute("SELECT id, precio FROM productos WHERE nombre=%s LIMIT 1", (nombre_producto,))
                        row = cur.fetchone()
                        if row:
                            menu_id = row[0]
                            precio = float(row[1])
                        else:
                            cur.execute("SELECT id, Precio FROM menu WHERE Nombre_Menu=%s LIMIT 1", (nombre_producto,))
                            row = cur.fetchone()
                            if row:
                                menu_id = row[0]
                                precio = float(row[1])
                    except Exception as e:
                        print(f"Error buscando producto temporal {nombre_producto}: {e}")
                else:
                    # Buscar precio en productos primero
                    try:
                        cur.execute("SELECT id, precio, nombre FROM productos WHERE id=%s", (pid,))
                        row = cur.fetchone()
                        if row:
                            precio = float(row[1])
                            nombre_producto = row[2] if len(row) > 2 else 'Producto'
                            # Verificar si existe en menu con el mismo ID, si no, usar el ID de productos directamente
                            cur.execute("SELECT id FROM menu WHERE id=%s", (pid,))
                            menu_row = cur.fetchone()
                            if menu_row:
                                menu_id = menu_row[0]
                            else:
                                # Si no existe en menu, usar el ID de productos directamente
                                # (la foreign key ya no es restrictiva)
                                menu_id = row[0]
                                print(f"[CHECKOUT] Producto {nombre_producto} (ID: {pid}) no está en menu, usando ID de productos")
                        else:
                            # Si no está en productos, buscar en menu
                            cur.execute("SELECT id, Precio, Nombre_Menu FROM menu WHERE id=%s", (pid,))
                            row = cur.fetchone()
                            if not row:
                                print(f"[CHECKOUT] Producto con ID {pid} no encontrado en productos ni menu - SKIP")
                                continue
                            precio = float(row[1])
                            menu_id = row[0]
                            nombre_producto = row[2] if len(row) > 2 else 'Producto'
                    except Exception as e:
                        print(f"[CHECKOUT] Error obteniendo precio para producto {pid}: {e}")
                        import traceback
                        traceback.print_exc()
                        continue
                
                if not menu_id:
                    print(f"No se pudo encontrar menu_id para producto {pid}")
                    continue
                
                # Obtener notas del item del carrito
                notas_item = entry.get('notas', '') or ''
                
                # Insertar item del pedido
                cur.execute(
                    "INSERT INTO pedido_items (pedido_id, menu_id, cantidad, precio_unitario, notas) VALUES (%s, %s, %s, %s, %s)",
                    (pedido_id, menu_id, cantidad, precio, notas_item)
                )
                items_agregados += 1
                notas_msg = f" (Notas: {notas_item})" if notas_item else ""
                print(f"[CHECKOUT] ✓ Item agregado: {nombre_producto} x{cantidad} = ${precio * cantidad}{notas_msg}")
            except Exception as e:
                print(f"[CHECKOUT] ✗ Error agregando item {pid} al pedido: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        # Hacer commit final de todos los items usando la MISMA conexión
        conn.commit()
        print(f"[CHECKOUT] ✓ Commit final realizado - {items_agregados} items agregados al pedido {pedido_id}")
        
        # Verificar que se guardaron items
        try:
            cur.execute("SELECT COUNT(*) FROM pedido_items WHERE pedido_id = %s", (pedido_id,))
            items_count = cur.fetchone()[0]
            print(f"[CHECKOUT] Verificación: {items_count} items en pedido {pedido_id}")
        except Exception as verify_error:
            print(f"[CHECKOUT] Error verificando items: {verify_error}")
        
        cur.close()
        conn.close()
        
        print(f"\n{'='*60}")
        print(f"[CHECKOUT] Pedido creado exitosamente:")
        print(f"  - Pedido ID: {pedido_id}")
        print(f"  - Cliente: {nombre_cliente}")
        print(f"  - Mesa: {mesa}")
        print(f"  - Estado: pendiente")
        print(f"{'='*60}\n")
        
        # Vaciar carrito y datos de sesión
        session['cart'] = {}
        session.pop('mesa_carrito', None)
        session.pop('nombre_cliente', None)
        
        print(f"[CHECKOUT] ===== PEDIDO COMPLETADO EXITOSAMENTE =====")
        print(f"[CHECKOUT] Pedido #{pedido_id} - Cliente: {nombre_cliente} - Mesa: {mesa} - Items: {items_agregados}")
        flash(f'Pedido enviado correctamente. Pedido #{pedido_id} - Cliente: {nombre_cliente} - Mesa: {mesa}', 'success')
        return redirect(url_for('index'))
    except Exception as e:
        print(f"[CHECKOUT] ✗ ERROR en checkout: {e}")
        import traceback
        traceback.print_exc()
        try:
            if conn:
                conn.rollback()
        except:
            pass
        flash('Error al procesar el pedido', 'error')
        if cur:
            try:
                cur.close()
            except:
                pass
        if conn:
            try:
                conn.close()
            except:
                pass
        return redirect(url_for('cart_view'))

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
                    SELECT pi.cantidad, pi.precio_unitario, 
                           COALESCE(pr.nombre, m.Nombre_Menu, CONCAT('Producto ID:', pi.menu_id)) AS nombre_producto,
                           COALESCE(pi.notas, '') AS notas
                    FROM pedido_items pi
                    LEFT JOIN productos pr ON pi.menu_id = pr.id
                    LEFT JOIN menu m ON pi.menu_id = m.id
                    WHERE pi.pedido_id = %s
                    ORDER BY pi.id
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
