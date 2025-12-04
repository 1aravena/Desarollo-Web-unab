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
  // EXTRAS - Ingredientes adicionales disponibles
  // ========================================
  const extras = [
    {
      id: 1,
      nombre: "Queso Extra",
      descripcion: "Doble porción de mozzarella",
      precio: 2000,
      activo: true
    },
    {
      id: 2,
      nombre: "Pepperoni Extra",
      descripcion: "Porción adicional de pepperoni",
      precio: 3000,
      activo: true
    },
    {
      id: 3,
      nombre: "Champiñones Extra",
      descripcion: "Porción adicional de champiñones",
      precio: 1500,
      activo: true
    },
    {
      id: 4,
      nombre: "Aceitunas Extra",
      descripcion: "Porción adicional de aceitunas",
      precio: 1500,
      activo: true
    },
    {
      id: 5,
      nombre: "Jamón Extra",
      descripcion: "Porción adicional de jamón",
      precio: 2500,
      activo: true
    },
    {
      id: 6,
      nombre: "Piña Extra",
      descripcion: "Porción adicional de piña",
      precio: 1200,
      activo: true
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
  const pedidos = [];
  
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
  const ranking = [];
  
  // ========================================
  // CARRITO - Temporal (se guarda en localStorage)
  // ========================================
  // NOTA: Las funciones de carrito están definidas en scripts.js
  // cargarCarrito(), guardarCarrito(), vaciarCarrito()
  
  // ========================================
  // FUNCIONES AUXILIARES
  // ========================================
  
  // Formatear precio chileno
  function formatearPrecio(precio) {
    // Asegurar que el precio sea un número (puede venir como string de la API)
    const precioNumerico = parseFloat(precio) || 0;
    return `$${precioNumerico.toLocaleString('es-CL')}`;
  }
  
  // Obtener pizza por ID
  function obtenerPizza(id) {
    return pizzas.find(p => p.id === id);
  }
  
  // Obtener extra por ID
  function obtenerExtra(id) {
    // Primero intentar obtener desde localStorage
    const extrasGuardados = localStorage.getItem('extrasLaFornace');
    if (extrasGuardados) {
      try {
        const extrasLocal = JSON.parse(extrasGuardados);
        return extrasLocal.find(e => e.id === id);
      } catch (e) {
        console.error('Error parsing extras:', e);
      }
    }
    // Si no hay datos en localStorage, usar los datos por defecto
    return extras.find(e => e.id === id);
  }
  
  // Obtener extras activos
  function obtenerExtrasActivos() {
    // Primero intentar obtener desde localStorage
    const extrasGuardados = localStorage.getItem('extrasLaFornace');
    if (extrasGuardados) {
      try {
        const extrasLocal = JSON.parse(extrasGuardados);
        return extrasLocal.filter(e => e.activo);
      } catch (e) {
        console.error('Error parsing extras:', e);
      }
    }
    // Si no hay datos en localStorage, usar los datos por defecto
    return extras.filter(e => e.activo);
  }
  
  // Agregar al carrito (versión legacy - usar la función en index.html)
  function agregarAlCarritoLegacy(pizzaId, tamaño, cantidad = 1, extrasSeleccionados = []) {
    const pizza = obtenerPizza(pizzaId);
    if (!pizza) return false;
    
    // Calcular precio total incluyendo extras
    const precioBase = pizza.precios[tamaño];
    const precioExtras = extrasSeleccionados.reduce((total, extraId) => {
      const extra = obtenerExtra(extraId);
      return total + (extra ? extra.precio : 0);
    }, 0);
    const precioTotal = precioBase + precioExtras;
    
    const item = {
      id: Date.now(),
      pizzaId: pizzaId,
      nombre: pizza.nombre,
      tamaño: tamaño,
      precio: precioTotal,
      precioBase: precioBase,
      cantidad: cantidad,
      imagen: pizza.imagen,
      extras: extrasSeleccionados.map(extraId => obtenerExtra(extraId)).filter(Boolean)
    };
    
    let carrito = cargarCarrito();
    carrito.push(item);
    guardarCarrito(carrito);
    return true;
  }
  
  // Calcular total del carrito
  function calcularTotalCarrito() {
    const carrito = cargarCarrito();
    return carrito.reduce((total, item) => {
      const precio = item.precioUnitario || item.precio || 0;
      return total + (precio * item.cantidad);
    }, 0);
  }
  
  