-- phpMyAdmin SQL Dump
-- version 4.9.0.1
-- https://www.phpmyadmin.net/
--
-- Servidor: 127.0.0.1:3307
-- Tiempo de generación: 17-11-2025 a las 16:17:18
-- Versión del servidor: 10.4.6-MariaDB
-- Versión de PHP: 7.2.22

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
SET AUTOCOMMIT = 0;
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Base de datos: `menudigital`
--

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `categorias`
--

CREATE TABLE `categorias` (
  `id` int(11) NOT NULL,
  `nombre` varchar(100) NOT NULL,
  `descripcion` varchar(255) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

--
-- Volcado de datos para la tabla `categorias`
--

INSERT INTO `categorias` (`id`, `nombre`, `descripcion`) VALUES
(1, 'desayunos', ''),
(2, 'entradas', 'Entradas y aperitivos'),
(3, 'bebidas', 'Bebidas frías y calientes');

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `menu`
--

CREATE TABLE `menu` (
  `id` int(11) NOT NULL,
  `Nombre_Menu` varchar(150) NOT NULL,
  `Precio` decimal(10,2) NOT NULL,
  `Categoria` varchar(50) DEFAULT NULL,
  `Imagen` varchar(255) DEFAULT NULL,
  `Descripcion` text DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `mozos`
--

CREATE TABLE `mozos` (
  `id` int(11) NOT NULL,
  `nombre` varchar(100) NOT NULL,
  `email` varchar(120) DEFAULT NULL,
  `telefono` varchar(30) DEFAULT NULL,
  `activo` tinyint(1) DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

--
-- Volcado de datos para la tabla `mozos`
--

INSERT INTO `mozos` (`id`, `nombre`, `email`, `telefono`, `activo`) VALUES
(7, 'MARI', 'mar@gmail.com', NULL, 1),
(8, 'vale', 'godoy@gmail.com', NULL, 1),
(9, 'ara', 'ara@gmail.com', NULL, 1),
(10, 'pepe', 'pepe@gmail.com', NULL, 1),
(11, 'Pepe', 'pepe123@gmail.com', NULL, 1),
(12, 'Pablo', 'pablo@gmail.com', NULL, 1);

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `pedidos`
--

CREATE TABLE `pedidos` (
  `id` int(11) NOT NULL,
  `usuario_id` int(11) DEFAULT NULL,
  `estado` varchar(20) DEFAULT 'pendiente',
  `mesa` varchar(50) DEFAULT NULL,
  `creado_en` timestamp NOT NULL DEFAULT current_timestamp(),
  `nombre_cliente` varchar(100) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

--
-- Volcado de datos para la tabla `pedidos`
--

INSERT INTO `pedidos` (`id`, `usuario_id`, `estado`, `mesa`, `creado_en`, `nombre_cliente`) VALUES
(21, NULL, 'entregado', '2', '2025-11-14 21:15:54', 'lA'),
(22, NULL, 'pendiente', '2', '2025-11-15 13:47:27', 'lA'),
(26, NULL, 'entregado', '7', '2025-11-16 20:34:04', 'Vale');

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `pedido_items`
--

CREATE TABLE `pedido_items` (
  `id` int(11) NOT NULL,
  `pedido_id` int(11) NOT NULL,
  `menu_id` int(11) NOT NULL,
  `cantidad` int(11) NOT NULL DEFAULT 1,
  `precio_unitario` decimal(10,2) NOT NULL,
  `notas` text DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

--
-- Volcado de datos para la tabla `pedido_items`
--

INSERT INTO `pedido_items` (`id`, `pedido_id`, `menu_id`, `cantidad`, `precio_unitario`, `notas`) VALUES
(24, 21, 39, 1, '5000.00', ''),
(25, 22, 39, 1, '5000.00', 'nnn'),
(29, 26, 53, 1, '10000.00', ''),
(30, 26, 55, 1, '6500.00', 'Sin cebolla');

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `productos`
--

CREATE TABLE `productos` (
  `id` int(11) NOT NULL,
  `nombre` varchar(100) NOT NULL,
  `descripcion` text DEFAULT NULL,
  `precio` decimal(10,2) NOT NULL,
  `imagen` varchar(255) DEFAULT NULL,
  `categoria` varchar(50) DEFAULT 'general'
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

--
-- Volcado de datos para la tabla `productos`
--

INSERT INTO `productos` (`id`, `nombre`, `descripcion`, `precio`, `imagen`, `categoria`) VALUES
(35, 'Café latte + medialunas de manteca', '', '5000.00', 'images/1762984524_6edf7e6f.jpg', 'desayunos'),
(36, 'Tostadas con palta, tomate cherry y huevo poché', 'Pan integral con palta, cherry y huevo poché blando', '9000.00', 'images/1762985725_b312821f.png', 'desayunos'),
(37, 'Yogur natural con granola y frutas frescas', 'Yogur artesanal con granola crocante y frutas de estación', '8000.00', 'images/1763379155_Yogur_artesanal_con_granola_crocante_y_frutas_de_estacion.png', 'desayunos'),
(38, 'Panqueques con miel y frutos rojos', 'Panqueques dorados bañados en miel y frutos del bosque.', '6000.00', 'images/1763379143_panqueques.png', 'desayunos'),
(39, 'Huevos revueltos con espinaca y pan tostado', 'Clásico desayuno proteico con espinaca y tostadas.', '5000.00', 'images/1763379130_tostado.png', 'desayunos'),
(40, 'Ensalada César con pollo grillado', 'Lechuga romana, pollo grillado, croutons y parmesano.', '10000.00', 'images/1763378995_caesar.png', 'almuerzos'),
(41, 'Milanesa napolitana con papas fritas', 'Bife empanado con salsa, jamón y mozzarella gratinada.', '15000.00', 'images/1763379113_mila.png', 'almuerzos'),
(42, 'Ravioles caseros con salsa fileto', 'Ravioles caseros con salsa fileto', '10000.00', 'images/1763379093_rav.png', 'almuerzos'),
(43, 'Wrap de pollo con vegetales y papas rústicas', 'Tortilla con pollo, vegetales y salsa especial', '15000.00', 'images/1763041329_e3dc1b98.jpg', 'almuerzos'),
(44, 'Salmón a la plancha con puré de batata', 'Filete dorado con puré suave y espárragos.', '10000.00', 'images/1763379189_salmon.webp', 'almuerzos'),
(45, 'Café con leche + tostadas con mermelada', '', '6000.00', 'images/1763041945_8836b7c7.jpg', 'meriendas'),
(46, 'Licuado de frutas + tostado', '', '5500.00', 'images/1763378946_tostado.png', 'meriendas'),
(47, 'Submarino + medialuna rellena de dulce de leche', '', '4500.00', 'images/1763042467_e0d9ceaf.jpg', 'meriendas'),
(48, 'Mini cheesecake + espresso', '', '5500.00', 'images/1763378916_No-Bake-Coffee-Cheesecake-portion-2.jpg', 'meriendas'),
(49, 'Bife de chorizo con puré rústico y criolla', '', '10000.00', 'images/1763042693_dc2f9daf.jpeg', 'cenas'),
(50, 'Risotto de hongos y parmesano', 'Arroz con salsa de hongos y queso', '6500.00', 'images/1763378852_rissoto.jpg', 'cenas'),
(51, 'Hamburguesa gourmet con papas', 'Pan de papa, medallón de carne, lechuga, tomate, huevo frito, Jamón y porción de papas fritas', '11.00', 'images/1763378837_hamburguesa.jpg', 'cenas'),
(52, 'Pizza', 'Masa madre, jamon y queso', '9000.00', 'images/1763378823_pizza.jpg', 'cenas'),
(53, 'Tacos', 'Tortilla con pollo, vegetales y salsa especial', '10000.00', 'images/1763378797_tacos.jpg', 'cenas'),
(54, 'Salmon', 'Salmon con ensalada fria', '15000.00', 'images/1763378784_salmon.webp', 'cenas'),
(55, 'Arroz a la criolla', 'Arroz al wock con verduras, zanahoria, pimiento, cebolla', '6500.00', 'images/1763378774_arroz.avif', 'almuerzos'),
(56, '2x1 En Pizzas', '', '9000.00', 'images/1763378757_pizza.jpg', 'promociones'),
(57, 'Desayuno completo', 'Café, tostadas con palta, huevo, jamón y queso y pequeña difusión de jugo de naranja', '11000.00', 'images/1763378740_desayuno_completo.jpg', 'promociones'),
(59, 'Hamburguesas de lentejas', '', '2000.00', 'images/1763325372_1d9d375d.webp', 'veggie'),
(60, 'jugo de naranja', 'naranja recien exprimida', '1500.00', 'images/1763379789_a35f6054.jpg', 'bebidas'),
(61, 'coca cola', '', '2500.00', 'images/1763379846_b5f15b3e.webp', 'bebidas'),
(62, 'Agua', '', '1500.00', 'images/1763379876_734829a6.jpg', 'bebidas'),
(63, 'Difusin de cafe', '', '1500.00', 'images/1763379939_66d87f3a.png', 'bebidas'),
(64, 'Limonada', '', '1500.00', 'images/1763380006_9968f895.jpg', 'bebidas'),
(65, 'Ensalada Mediterranea', '', '3000.00', 'images/1763380251_b89726e5.jpg', 'veggie'),
(66, 'Hamburguesa de lentejas', 'Hamburguesa de lenteja, tomate, lechuga, huevo y pan de papa', '6000.00', 'images/1763380326_66cb427d.jpeg', 'veggie'),
(67, 'Tacos vegetarianos', '', '8000.00', 'images/1763380359_4a2fc89a.jpeg', 'veggie'),
(68, 'Pan de banana (sin gluten)', '', '2000.00', 'images/1763380679_810ba0fe.webp', 'comida_sin_tac'),
(69, 'Ñoquis de papa', '', '7500.00', 'images/1763391944_noquis_sin_tacc.jpg', 'comida_sin_tac');

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `usuarios`
--

CREATE TABLE `usuarios` (
  `id` int(11) NOT NULL,
  `nombre` varchar(100) NOT NULL,
  `email` varchar(100) NOT NULL,
  `password` varchar(255) NOT NULL,
  `fecha_registro` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

--
-- Volcado de datos para la tabla `usuarios`
--

INSERT INTO `usuarios` (`id`, `nombre`, `email`, `password`, `fecha_registro`) VALUES
(7, 'MARI', 'mar@gmail.com', 'pbkdf2:sha256:600000$fmb1XyMhyFgweteT$172b56039a96c45f72719c064bfd8f2495009735a477a041ea5fcdb76b55c029', '2025-11-05 16:50:33'),
(8, 'vale', 'godoy@gmail.com', 'pbkdf2:sha256:600000$DxRMSpgpzRJv7wpt$40f6b4f58630e2c9ece27eef86244d39bcb3f4d1c3ecf934ee83c143bc591a3d', '2025-11-05 18:10:59'),
(10, 'ara', 'ara@gmail.com', 'pbkdf2:sha256:600000$oaFIchhQ8d01ChLu$11b78584fafe5cc50c7cbbab09df4143d147795ce440d971ec8811c7eaf739c1', '2025-11-12 16:20:19'),
(11, 'pepe', 'pepe@gmail.com', 'pepe123', '2025-11-13 13:44:54'),
(12, 'Pepe', 'pepe123@gmail.com', 'pepe123', '2025-11-15 13:56:10'),
(13, 'Pablo', 'pablo@gmail.com', 'pablo123', '2025-11-16 20:34:41');

--
-- Índices para tablas volcadas
--

--
-- Indices de la tabla `categorias`
--
ALTER TABLE `categorias`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `nombre` (`nombre`);

--
-- Indices de la tabla `menu`
--
ALTER TABLE `menu`
  ADD PRIMARY KEY (`id`);

--
-- Indices de la tabla `mozos`
--
ALTER TABLE `mozos`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `email` (`email`);

--
-- Indices de la tabla `pedidos`
--
ALTER TABLE `pedidos`
  ADD PRIMARY KEY (`id`),
  ADD KEY `usuario_id` (`usuario_id`);

--
-- Indices de la tabla `pedido_items`
--
ALTER TABLE `pedido_items`
  ADD PRIMARY KEY (`id`),
  ADD KEY `pedido_id` (`pedido_id`),
  ADD KEY `menu_id` (`menu_id`);

--
-- Indices de la tabla `productos`
--
ALTER TABLE `productos`
  ADD PRIMARY KEY (`id`);

--
-- Indices de la tabla `usuarios`
--
ALTER TABLE `usuarios`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `email` (`email`);

--
-- AUTO_INCREMENT de las tablas volcadas
--

--
-- AUTO_INCREMENT de la tabla `categorias`
--
ALTER TABLE `categorias`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

--
-- AUTO_INCREMENT de la tabla `menu`
--
ALTER TABLE `menu`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=12;

--
-- AUTO_INCREMENT de la tabla `mozos`
--
ALTER TABLE `mozos`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=13;

--
-- AUTO_INCREMENT de la tabla `pedidos`
--
ALTER TABLE `pedidos`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=28;

--
-- AUTO_INCREMENT de la tabla `pedido_items`
--
ALTER TABLE `pedido_items`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=33;

--
-- AUTO_INCREMENT de la tabla `productos`
--
ALTER TABLE `productos`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=71;

--
-- AUTO_INCREMENT de la tabla `usuarios`
--
ALTER TABLE `usuarios`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=14;

--
-- Restricciones para tablas volcadas
--

--
-- Filtros para la tabla `pedidos`
--
ALTER TABLE `pedidos`
  ADD CONSTRAINT `pedidos_ibfk_1` FOREIGN KEY (`usuario_id`) REFERENCES `usuarios` (`id`);

--
-- Filtros para la tabla `pedido_items`
--
ALTER TABLE `pedido_items`
  ADD CONSTRAINT `pedido_items_ibfk_1` FOREIGN KEY (`pedido_id`) REFERENCES `pedidos` (`id`);
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
