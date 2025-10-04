/**
 * Mock Data - Datos de prueba para La Fornace
 * Sprint 3 - Desarrollo Web y Móvil
 */

// ========================================
// PRODUCTOS - Pizzas del Menú
// ========================================
const pizzas = [
    {
      id: 1,
      nombre: "Hawaiana",
      descripcion: "Piña, jamón y mozzarella",
      imagen: "image/hawaiana1_1691158490_medium.jpg",
      precios: {
        mediana: 19600,
        grande: 22700
      },
      ingredientes: ["Mozzarella", "Jamón", "Piña"]
    },
    {
      id: 2,
      nombre: "Pepperoni",
      descripcion: "Mozzarella y pepperoni",
      imagen: "image/superpepperoni__1691158022_medium.jpg",
      precios: {
        mediana: 19600,
        grande: 22700
      },
      ingredientes: ["Mozzarella", "Pepperoni"]
    },
    {
      id: 3,
      nombre: "Vegetariana",
      descripcion: "Champiñones, pimentón, aceitunas",
      imagen: "image/vegetariana1_1691158337_medium.jpg",
      precios: {
        mediana: 22000,
        grande: 25900
      },
      ingredientes: ["Doble mozzarella", "Aceitunas", "Champiñones", "Pimentón", "Cebolla"]
    }
  ];
  
  // ========================================
  // USUARIO - Datos del perfil
  // ========================================
  const usuario = {
    id: 1,
    nombre: "Juan Pérez",
    email: "usuario@ejemplo.com",
    telefono: "+56 9 1234 5678",
    direccion: "Av. Libertador Bernardo O'Higgins 1234, Santiago",
    suscritoPromos: true
  };
  
  // ========================================
  // PEDIDOS - Historial
  // ========================================
  const pedidos = [
    {
      id: 1001,
      fecha: "2025-10-01",
      hora: "19:30",
      estado: "entregado",
      items: [
        { pizzaId: 1, nombre: "Hawaiana", tamaño: "grande", cantidad: 2, precio: 22700 },
        { pizzaId: 2, nombre: "Pepperoni", tamaño: "mediana", cantidad: 1, precio: 19600 }
      ],
      total: 64900,
      direccion: "Av. Libertador Bernardo O'Higgins 1234, Santiago"
    },
    {
      id: 1002,
      fecha: "2025-09-28",
      hora: "20:15",
      estado: "entregado",
      items: [
        { pizzaId: 3, nombre: "Vegetariana", tamaño: "grande", cantidad: 1, precio: 25900 }
      ],
      total: 25900,
      direccion: "Av. Libertador Bernardo O'Higgins 1234, Santiago"
    },
    {
      id: 1003,
      fecha: "2025-09-25",
      hora: "18:45",
      estado: "anulado",
      items: [
        { pizzaId: 1, nombre: "Hawaiana", tamaño: "mediana", cantidad: 1, precio: 19600 }
      ],
      total: 19600,
      direccion: "Av. Libertador Bernardo O'Higgins 1234, Santiago",
      motivoAnulacion: "Error en la dirección de entrega"
    }
  ];
  
  // ========================================
  // REPORTES - Ventas
  // ========================================
  const reporteVentas = {
    periodo: "Septiembre 2025",
    totalVentas: 2450000,
    cantidadPedidos: 87,
    promedioTicket: 28161,
    ventasPorDia: [
      { fecha: "2025-09-01", ventas: 85000, pedidos: 3 },
      { fecha: "2025-09-02", ventas: 120000, pedidos: 4 },
      { fecha: "2025-09-03", ventas: 95000, pedidos: 3 },
      // ... más datos
    ]
  };
  
  // ========================================
  // RANKING - Pizzas más vendidas
  // ========================================
  const ranking = [
    { pizzaId: 2, nombre: "Pepperoni", cantidadVendida: 45, totalVentas: 987000 },
    { pizzaId: 1, nombre: "Hawaiana", cantidadVendida: 38, totalVentas: 862400 },
    { pizzaId: 3, nombre: "Vegetariana", cantidadVendida: 29, totalVentas: 751100 }
  ];
  
  // ========================================
  // CARRITO - Temporal (se guarda en localStorage)
  // ========================================
  let carrito = [];
  
  // ========================================
  // FUNCIONES AUXILIARES
  // ========================================
  
  // Formatear precio chileno
  function formatearPrecio(precio) {
    return `$${precio.toLocaleString('es-CL')}`;
  }
  
  // Obtener pizza por ID
  function obtenerPizza(id) {
    return pizzas.find(p => p.id === id);
  }
  
  // Agregar al carrito
  function agregarAlCarrito(pizzaId, tamaño, cantidad = 1) {
    const pizza = obtenerPizza(pizzaId);
    if (!pizza) return false;
    
    const item = {
      id: Date.now(),
      pizzaId: pizzaId,
      nombre: pizza.nombre,
      tamaño: tamaño,
      precio: pizza.precios[tamaño],
      cantidad: cantidad,
      imagen: pizza.imagen
    };
    
    carrito.push(item);
    guardarCarrito();
    return true;
  }
  
  // Guardar carrito en localStorage
  function guardarCarrito() {
    localStorage.setItem('carritoLaFornace', JSON.stringify(carrito));
  }
  
  // Cargar carrito desde localStorage
  function cargarCarrito() {
    const carritoGuardado = localStorage.getItem('carritoLaFornace');
    if (carritoGuardado) {
      carrito = JSON.parse(carritoGuardado);
    }
    return carrito;
  }
  
  // Calcular total del carrito
  function calcularTotalCarrito() {
    return carrito.reduce((total, item) => total + (item.precio * item.cantidad), 0);
  }
  
  // Vaciar carrito
  function vaciarCarrito() {
    carrito = [];
    localStorage.removeItem('carritoLaFornace');
  }
  
  