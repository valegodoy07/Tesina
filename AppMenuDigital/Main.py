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

# (revert) Sin configuración de subida de imágenes

# Inicializar MySQL
mysql = MySQL(app)

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
    # Cargar dinámicamente productos por categoría para el Index (se agregan al final del bloque hardcodeado)
    categorias = ['desayunos', 'almuerzos', 'cenas', 'meriendas', 'postres', 'bebidas']
    productos_por_categoria = {c: [] for c in categorias}
    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT id, Nombre_Menu, Precio, LOWER(COALESCE(Categoria, '')) as cat, COALESCE(Imagen, '')
            FROM menu
            WHERE LOWER(COALESCE(Categoria, '')) IN ('desayunos','almuerzos','cenas','meriendas','postres','bebidas')
            ORDER BY id DESC
        """)
        filas = cur.fetchall()
        for f in filas:
            cat = (f[3] or '').lower()
            if cat in productos_por_categoria:
                productos_por_categoria[cat].append(f)
        cur.close()
    except Exception as e:
        print(f"Error al cargar productos para index: {e}")

    ctx = {'productos_por_categoria': productos_por_categoria}
    if 'user_id' in session:
        ctx['usuario'] = session.get('nombre')
    return render_template('Index.html', **ctx)

@app.route('/menu')
def menu():
    try:
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
            # Registrar también como mozo activo por defecto
            try:
                cur.execute("INSERT INTO mozos (nombre, email, activo) VALUES (%s, %s, %s)", (nombre, email, 1))
            except Exception:
                # Si ya existe en mozos por UNIQUE email, ignoramos
                pass

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
        cur = mysql.connection.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS pedidos (
                id INT AUTO_INCREMENT PRIMARY KEY,
                mozo_id INT NOT NULL,
                mesa VARCHAR(20) NOT NULL,
                estado VARCHAR(20) DEFAULT 'abierto',
                notas TEXT,
                creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (mozo_id) REFERENCES mozos(id)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS pedido_items (
                id INT AUTO_INCREMENT PRIMARY KEY,
                pedido_id INT NOT NULL,
                producto_id INT NOT NULL,
                cantidad INT NOT NULL DEFAULT 1,
                FOREIGN KEY (pedido_id) REFERENCES pedidos(id),
                FOREIGN KEY (producto_id) REFERENCES productos(id)
            )
            """
        )
        mysql.connection.commit()
        cur.close()
    except Exception as e:
        print(f"Error asegurando tablas de pedidos: {e}")


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
        mysql.connection.commit()
        cur.close()
    except Exception as e:
        print(f"No se pudo verificar/actualizar columnas de menu: {e}")

# ===== Panel de Control (Admin) =====
@app.route('/admin')
@admin_required
def admin_dashboard():
    try:
        ensure_menu_table_upgrade()
        cur = mysql.connection.cursor()
        try:
            cur.execute("SELECT id, Nombre_Menu, Precio, COALESCE(Categoria, ''), COALESCE(Imagen, '') FROM menu ORDER BY id DESC")
            productos = cur.fetchall()
        except Exception:
            productos = []
        mozos = []
        try:
            cur.execute("SELECT id, nombre, email, telefono, activo FROM mozos ORDER BY nombre")
            mozos = cur.fetchall()
        except Exception:
            mozos = []
        cur.close()
        return render_template('admin.html', categorias=[], productos=productos, mozos=mozos)
    except Exception as e:
        print(f"Error al cargar dashboard admin: {e}")
        flash('Error al cargar el panel de administración', 'error')
        return render_template('admin.html', categorias=[], productos=[], mozos=[])

# ===== Panel de Mozo =====
@app.route('/mozo')
@mozo_required
def mozo_dashboard():
    ensure_pedidos_tables()
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT id, mesa, estado, notas, creado_en FROM pedidos WHERE mozo_id=%s ORDER BY id DESC", (session['mozo_id'],))
        pedidos = cur.fetchall()
        cur.close()
        return render_template('mozo.html', pedidos=pedidos)
    except Exception as e:
        print(f"Error cargando panel mozo: {e}")
        flash('Error al cargar panel de mozo', 'error')
        return render_template('mozo.html', pedidos=[])

@app.route('/mozo/pedidos/crear', methods=['POST'])
@mozo_required
def mozo_pedido_crear():
    ensure_pedidos_tables()
    mesa = request.form.get('mesa')
    notas = request.form.get('notas')
    if not mesa:
        flash('Debes indicar la mesa', 'error')
        return redirect(url_for('mozo_dashboard'))
    try:
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO pedidos (mozo_id, mesa, notas) VALUES (%s, %s, %s)", (session['mozo_id'], mesa, notas))
        mysql.connection.commit()
        cur.close()
        flash('Pedido creado', 'success')
    except Exception as e:
        print(f"Error creando pedido: {e}")
        flash('Error al crear pedido', 'error')
    return redirect(url_for('mozo_dashboard'))

@app.route('/mozo/pedidos/<int:pedido_id>/estado', methods=['POST'])
@mozo_required
def mozo_pedido_estado(pedido_id: int):
    nuevo_estado = request.form.get('estado', 'abierto')
    try:
        cur = mysql.connection.cursor()
        cur.execute("UPDATE pedidos SET estado=%s WHERE id=%s AND mozo_id=%s", (nuevo_estado, pedido_id, session['mozo_id']))
        mysql.connection.commit()
        cur.close()
        flash('Estado actualizado', 'success')
    except Exception as e:
        print(f"Error actualizando estado pedido: {e}")
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
    if not (nombre and precio):
        flash('Nombre y precio son obligatorios', 'error')
        return redirect(url_for('admin_dashboard'))
    try:
        ensure_menu_table_upgrade()
        cur = mysql.connection.cursor()
        cur.execute(
            "INSERT INTO menu (Nombre_Menu, Precio, Categoria, Imagen) VALUES (%s, %s, %s, %s)",
            (nombre, precio, categoria, imagen)
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
    try:
        ensure_menu_table_upgrade()
        cur = mysql.connection.cursor()
        cur.execute(
            "UPDATE menu SET Nombre_Menu=%s, Precio=%s, Categoria=%s, Imagen=%s WHERE id=%s",
            (nombre, precio, categoria, imagen, producto_id)
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
                creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(idusuario)
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
            except Exception:
                continue
        cur.close()
    except Exception as e:
        print(f"Error cargando carrito: {e}")
    return render_template('cart.html', items=items, total=total)

@app.route('/cart/add/<int:producto_id>', methods=['POST'])
def cart_add(producto_id: int):
    qty = int(request.form.get('qty', '1'))
    cart = _get_cart()
    key = str(producto_id)
    if key in cart:
        cart[key]['qty'] = int(cart[key].get('qty', 1)) + qty
    else:
        cart[key] = {'qty': qty}
    session['cart'] = cart
    flash('Producto agregado al carrito', 'success')
    return redirect(request.referrer or url_for('menu'))

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
    ensure_client_orders_tables()
    try:
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO pedidos (usuario_id, estado) VALUES (%s, %s)", (session.get('user_id'), 'pendiente'))
        pedido_id = cur.lastrowid
        for pid, entry in cart.items():
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
        mysql.connection.commit()
        cur.close()
        # Vaciar carrito
        session['cart'] = {}
        flash('Pedido enviado correctamente', 'success')
    except Exception as e:
        print(f"Error en checkout: {e}")
        flash('Error al procesar el pedido', 'error')
    return redirect(url_for('index'))

# ===== Vista de pedidos para administrador =====
@app.route('/admin/pedidos')
@admin_required
def admin_pedidos_list():
    ensure_client_orders_tables()
    pedidos = []
    try:
        cur = mysql.connection.cursor()
        cur.execute(
            "SELECT p.id, p.usuario_id, p.estado, p.creado_en, COALESCE(u.nombre, '') FROM pedidos p LEFT JOIN usuarios u ON p.usuario_id=u.idusuario ORDER BY p.id DESC"
        )
        pedidos = cur.fetchall()
        cur.close()
    except Exception as e:
        print(f"Error listando pedidos: {e}")
    return render_template('admin_pedidos.html', pedidos=pedidos)

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
    return redirect(url_for('admin_pedidos_list'))

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
