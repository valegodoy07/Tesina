# P&C Restobar - Aplicación Web

Una aplicación web moderna para un restobar desarrollada con Flask, Python y MySQL.

## Características

- ✅ Sistema de autenticación completo (registro e inicio de sesión)
- ✅ Base de datos MySQL para almacenar usuarios y productos
- ✅ Interfaz moderna y responsive
- ✅ Menú digital con productos dinámicos
- ✅ Perfil de usuario personalizado
- ✅ Diseño atractivo con animaciones

## Requisitos Previos

1. **Python 3.8 o superior**
2. **MySQL Server** (XAMPP, WAMP, o MySQL standalone)
3. **pip** (gestor de paquetes de Python)

## Instalación

### 1. Clonar o descargar el proyecto

```bash
git clone <url-del-repositorio>
cd AppMenuDigital
```

### 2. Crear un entorno virtual (recomendado)

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar MySQL

1. Asegúrate de que MySQL esté ejecutándose en tu sistema
2. La aplicación se conectará automáticamente a:
   - Host: localhost
   - Usuario: root
   - Contraseña: (vacía)
   - Base de datos: restobar_db (se creará automáticamente)

### 5. Configurar la aplicación

Si necesitas cambiar la configuración de MySQL, edita el archivo `Main.py`:

```python
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'tu_contraseña'
app.config['MYSQL_DB'] = 'restobar_db'
```

## Ejecutar la aplicación

```bash
python Main.py
```

La aplicación estará disponible en: `http://localhost:5000`

## Estructura del Proyecto

```
AppMenuDigital/
├── Main.py                 # Aplicación principal Flask
├── requirements.txt        # Dependencias de Python
├── README.md              # Este archivo
├── Templates/             # Plantillas HTML
│   ├── Index.html         # Página principal
│   ├── Login.html         # Página de login
│   ├── Registro.html      # Página de registro
│   ├── menu.html          # Página del menú
│   └── perfil.html        # Página del perfil
└── Statics/               # Archivos estáticos
    ├── Styles.css         # Estilos CSS
    └── Script.js          # JavaScript (opcional)
```

## Funcionalidades

### Página Principal
- Diseño atractivo con imagen de fondo
- Navegación intuitiva
- Botones de login/registro para usuarios no autenticados
- Información del usuario logueado

### Sistema de Autenticación
- **Registro**: Crear nueva cuenta con validación
- **Login**: Iniciar sesión con email y contraseña
- **Logout**: Cerrar sesión de forma segura
- **Perfil**: Ver información personal del usuario

### Menú Digital
- Productos cargados desde la base de datos
- Diseño responsive con tarjetas de productos
- Imágenes, descripciones y precios
- Efectos hover y animaciones

### Base de Datos
La aplicación crea automáticamente:
- Tabla `usuarios` para almacenar información de usuarios
- Tabla `productos` para el menú del restobar
- Datos de ejemplo para productos

## Personalización

### Agregar Productos
Para agregar productos al menú, puedes:

1. **Modificar directamente en el código** (líneas 50-60 en Main.py):
```python
productos_ejemplo = [
    ('Nuevo Producto', 'Descripción del producto', 15000.00, 'imagen.png', 'categoria'),
    # Agregar más productos aquí
]
```

2. **Usar phpMyAdmin** (si tienes XAMPP/WAMP):
   - Acceder a phpMyAdmin
   - Seleccionar la base de datos `restobar_db`
   - Ir a la tabla `productos`
   - Insertar nuevos registros

### Cambiar Estilos
Edita el archivo `Statics/Styles.css` para personalizar:
- Colores del tema
- Tipografías
- Layout y espaciado
- Efectos y animaciones

## Solución de Problemas

### Error de conexión a MySQL
- Verifica que MySQL esté ejecutándose
- Confirma las credenciales en `Main.py`
- Asegúrate de que el puerto 3306 esté disponible

### Error de dependencias
```bash
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

### Error de puerto ocupado
Si el puerto 5000 está ocupado, cambia en `Main.py`:
```python
app.run(debug=True, host='0.0.0.0', port=5001)  # Cambiar puerto
```

## Tecnologías Utilizadas

- **Backend**: Flask (Python)
- **Base de Datos**: MySQL
- **Frontend**: HTML5, CSS3, JavaScript
- **Autenticación**: Werkzeug (hashing de contraseñas)
- **Sesiones**: Flask-Session

## Licencia

Este proyecto es de uso educativo y comercial.

## Soporte

Para soporte técnico o preguntas, contacta al desarrollador.

---

¡Disfruta tu aplicación de restobar! 🍽️ 