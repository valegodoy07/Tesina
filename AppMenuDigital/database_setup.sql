-- Script para crear las tablas necesarias en la base de datos menu_digital
-- Ejecutar este script en phpMyAdmin de XAMPP

-- Crear tabla de usuarios
CREATE TABLE IF NOT EXISTS usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Crear tabla de productos del menú
CREATE TABLE IF NOT EXISTS productos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    descripcion TEXT,
    precio DECIMAL(10,2) NOT NULL,
    imagen VARCHAR(255),
    categoria VARCHAR(50) DEFAULT 'general'
);

-- Crear tabla de categorías
CREATE TABLE IF NOT EXISTS categorias (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) UNIQUE NOT NULL,
    descripcion VARCHAR(255)
);

-- Crear tabla de mozos
CREATE TABLE IF NOT EXISTS mozos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    email VARCHAR(120) UNIQUE,
    telefono VARCHAR(30),
    activo TINYINT(1) DEFAULT 1
);

-- Insertar productos de ejemplo (opcional)
INSERT INTO productos (nombre, descripcion, precio, imagen, categoria) VALUES
('Milanesa con papas fritas', 'Deliciosa milanesa acompañada de papas fritas crujientes', 10000.00, 'milanesa-tesina.png', 'platos_principales'),
('Café', 'Café recién preparado', 3000.00, 'cafe.png', 'bebidas'),
('Pizza', 'Pizza artesanal con ingredientes frescos', 7000.00, 'pizza.png', 'platos_principales'),
('Hamburguesa', 'Hamburguesa con carne, lechuga, tomate y queso', 8000.00, 'hamburguesa.png', 'platos_principales'),
('Ensalada César', 'Ensalada fresca con lechuga, crutones y aderezo especial', 6000.00, 'ensalada.png', 'entradas'),
('Limonada', 'Limonada natural refrescante', 2500.00, 'limonada.png', 'bebidas'); 

-- Insertar categorías de ejemplo (opcional)
INSERT INTO categorias (nombre, descripcion) VALUES
('platos_principales', 'Platos fuertes y principales'),
('entradas', 'Entradas y aperitivos'),
('bebidas', 'Bebidas frías y calientes')
ON DUPLICATE KEY UPDATE descripcion = VALUES(descripcion);