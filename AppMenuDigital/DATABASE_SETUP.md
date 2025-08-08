# Configuración de Base de Datos MySQL con XAMPP

## Requisitos Previos

1. **XAMPP instalado y funcionando**
2. **Servicios Apache y MySQL iniciados**
3. **Base de datos `menu_digital` creada en phpMyAdmin**

## Pasos para Configurar la Base de Datos

### 1. Iniciar XAMPP
- Abre XAMPP Control Panel
- Inicia los servicios **Apache** y **MySQL**
- Haz clic en "Admin" de MySQL para abrir phpMyAdmin

### 2. Crear la Base de Datos
1. En phpMyAdmin, haz clic en "Nueva" en el panel izquierdo
2. Nombre de la base de datos: `menu_digital`
3. Collation: `utf8mb4_unicode_ci`
4. Haz clic en "Crear"

### 3. Crear las Tablas
1. Selecciona la base de datos `menu_digital`
2. Ve a la pestaña "SQL"
3. Copia y pega el contenido del archivo `database_setup.sql`
4. Haz clic en "Continuar"

### 4. Verificar la Configuración
Las siguientes tablas deben estar creadas:
- `usuarios` - Para almacenar información de usuarios registrados
- `productos` - Para almacenar los productos del menú

## Configuración de la Aplicación

### Archivo config.py
La configuración ya está ajustada para XAMPP:
```python
MYSQL_HOST = 'localhost'
MYSQL_USER = 'root'
MYSQL_PASSWORD = ''  # Contraseña vacía por defecto
MYSQL_DB = 'menu_digital'
```

### Si tu XAMPP tiene contraseña
Si configuraste una contraseña para el usuario root en XAMPP, modifica el archivo `config.py`:
```python
MYSQL_PASSWORD = 'tu_contraseña_aqui'
```

## Verificar la Conexión

1. Ejecuta la aplicación: `python Main.py`
2. Si no hay errores de conexión, la configuración es correcta
3. Puedes registrar usuarios y ver el menú

## Solución de Problemas

### Error: "Access denied for user 'root'@'localhost'"
- Verifica que MySQL esté iniciado en XAMPP
- Confirma que el usuario root no tenga contraseña (o usa la correcta)

### Error: "Unknown database 'menu_digital'"
- Asegúrate de haber creado la base de datos en phpMyAdmin
- Verifica el nombre exacto de la base de datos

### Error: "Table doesn't exist"
- Ejecuta el script SQL en phpMyAdmin para crear las tablas

## Estructura de la Base de Datos

### Tabla: usuarios
- `id` - ID único del usuario
- `nombre` - Nombre completo del usuario
- `email` - Email único del usuario
- `password` - Contraseña hasheada
- `fecha_registro` - Fecha de registro automática

### Tabla: productos
- `id` - ID único del producto
- `nombre` - Nombre del producto
- `descripcion` - Descripción del producto
- `precio` - Precio del producto
- `imagen` - Nombre del archivo de imagen
- `categoria` - Categoría del producto 