/**
 * ============================================================================
 * Scripts Compartidos - Pizzeria La Fornace
 * ============================================================================
 * 
 * Este archivo contiene funciones utilitarias compartidas por todas las
 * paginas del frontend. Se carga despues de api.js y antes del codigo
 * especifico de cada pagina.
 * 
 * Secciones:
 * ----------
 * 1. FORMATEO DE PRECIOS      - Formato moneda chilena (CLP)
 * 2. VALIDACIONES             - Email, telefono chileno
 * 3. MENSAJES Y ALERTAS       - Sistema de notificaciones Bootstrap
 * 4. UTILIDADES               - Formateo fechas, helpers varios
 * 5. GESTION DEL CARRITO      - LocalStorage para carrito (B-03)
 * 6. NAVEGACION               - Helpers de redireccion
 * 7. INICIALIZACION           - Configuracion al cargar DOM
 * 
 * Dependencias:
 * -------------
 * - Bootstrap 5.3.3 (CSS y JS)
 * - api.js (cliente HTTP)
 * 
 * Historias Relacionadas:
 * -----------------------
 * - B-03: Carrito de compras (gestion localStorage)
 * - E-07: RBAC (actualizarNavbarSesion segun rol)
 * - B-01: Contacto (funciones de validacion)
 * 
 * ============================================================================
 */

// ========================================
// FORMATEO DE PRECIOS
// ========================================

// Formatear precio chileno
function formatearPrecio(precio) {
  // Asegurar que el precio sea un número (puede venir como string de la API)
  const precioNumerico = parseFloat(precio) || 0;
  return '$' + precioNumerico.toLocaleString('es-CL');
}

// ========================================
// VALIDACIONES
// ========================================

// Validar email
function validarEmail(email) {
    const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return regex.test(email);
  }
  
  // Validar teléfono chileno
  function validarTelefono(telefono) {
    // Acepta formatos: +56912345678, +56 9 1234 5678, 912345678
    const regex = /^(\+?56)?(\s)?9\d{8}$/;
    const telefonoLimpio = telefono.replace(/\s/g, '');
    return regex.test(telefonoLimpio);
  }
  
  // ========================================
  // MENSAJES Y ALERTAS
  // ========================================
  
  // Mostrar mensaje de éxito
  function mostrarExito(mensaje, contenedorId = 'mensaje-container') {
    const contenedor = document.getElementById(contenedorId);
    if (!contenedor) return;
    
    contenedor.innerHTML = `
      <div class="alert alert-success alert-dismissible fade show" role="alert">
        ${mensaje}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
      </div>
    `;
    
    // Auto-ocultar después de 5 segundos
    setTimeout(() => {
      const alerta = contenedor.querySelector('.alert');
      if (alerta) {
        alerta.classList.remove('show');
        setTimeout(() => contenedor.innerHTML = '', 150);
      }
    }, 5000);
  }
  
  // Mostrar mensaje de error
  function mostrarError(mensaje, contenedorId = 'mensaje-container') {
    const contenedor = document.getElementById(contenedorId);
    if (!contenedor) return;
    
    contenedor.innerHTML = `
      <div class="alert alert-danger alert-dismissible fade show" role="alert">
        ${mensaje}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
      </div>
    `;
  }
  
  // Mostrar mensaje de información
  function mostrarInfo(mensaje, contenedorId = 'mensaje-container') {
    const contenedor = document.getElementById(contenedorId);
    if (!contenedor) return;
    
    contenedor.innerHTML = `
      <div class="alert alert-info alert-dismissible fade show" role="alert">
        ${mensaje}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
      </div>
    `;
  }
  
  // ========================================
  // UTILIDADES
  // ========================================
  
  // Formatear fecha DD/MM/YYYY
  function formatearFecha(fechaISO) {
    const fecha = new Date(fechaISO);
    const dia = String(fecha.getDate()).padStart(2, '0');
    const mes = String(fecha.getMonth() + 1).padStart(2, '0');
    const año = fecha.getFullYear();
    return `${dia}/${mes}/${año}`;
  }
  
  // Actualizar badge del carrito en navbar
  function actualizarBadgeCarrito() {
    const badge = document.getElementById('carrito-badge');
    if (badge && typeof cargarCarrito === 'function') {
      const carritoActual = cargarCarrito();
      const cantidad = carritoActual.reduce((total, item) => total + item.cantidad, 0);
      badge.textContent = cantidad;
    }
  }
  
  // Simular carga/procesamiento
  function simularProcesamiento(callback, tiempo = 1000) {
    // Mostrar spinner o deshabilitar botones
    setTimeout(callback, tiempo);
  }
  
  // ========================================
  // GESTIÓN DEL CARRITO
  // ========================================

// Cargar carrito desde localStorage
function cargarCarrito() {
  try {
    const carritoJSON = localStorage.getItem('carritoLaFornace');
    // Verificar que exista y no sea undefined/null/vacío
    if (!carritoJSON || carritoJSON === 'undefined' || carritoJSON === 'null') {
      return [];
    }
    const carrito = JSON.parse(carritoJSON);
    // Asegurar que sea un array
    return Array.isArray(carrito) ? carrito : [];
  } catch (error) {
    console.error('Error al cargar carrito:', error);
    // Si hay error de parsing, limpiar y devolver array vacío
    localStorage.removeItem('carritoLaFornace');
    return [];
  }
}

// Guardar carrito en localStorage
function guardarCarrito(carritoData) {
  // Si se pasa un parámetro, usar ese; si no, usar el array vacío
  const carrito = Array.isArray(carritoData) ? carritoData : [];
  localStorage.setItem('carritoLaFornace', JSON.stringify(carrito));
  actualizarBadgeCarrito();
}

// Vaciar carrito
function vaciarCarrito() {
  localStorage.removeItem('carritoLaFornace');
  actualizarBadgeCarrito();
}

// Limpiar todos los datos de la aplicación (útil para debugging)
function limpiarDatosAplicacion() {
  localStorage.removeItem('carritoLaFornace');
  localStorage.removeItem('access_token');
  localStorage.removeItem('usuarioLaFornace');
  localStorage.removeItem('extrasLaFornace');
  console.log('Datos de la aplicación limpiados');
  window.location.reload();
}

// ========================================
// NAVEGACIÓN
// ========================================
  
  // Volver a la página anterior
  function volverAtras() {
    window.history.back();
  }
  
  // Ir a página específica
  function irA(url) {
    window.location.href = url;
  }
  
  // ========================================
  // INICIALIZACIÓN
  // ========================================
  
  // Ejecutar cuando el DOM esté listo
  document.addEventListener('DOMContentLoaded', function() {
    // Actualizar badge del carrito si existe
    actualizarBadgeCarrito();
    
    // Inicializar tooltips de Bootstrap si existen
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    if (typeof bootstrap !== 'undefined') {
      tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
      });
    }

    // Verificar sesión y actualizar navbar
    actualizarNavbarSesion();
  });

  // Actualizar navbar según estado de sesión
  function actualizarNavbarSesion() {
    const token = localStorage.getItem('access_token');
    const navbarNav = document.querySelector('#mainNav .navbar-nav');
    
    if (!navbarNav) return;

    // Buscar items existentes
    const tuCuentaItem = Array.from(navbarNav.children).find(li => li.querySelector('a')?.textContent.includes('Tu Cuenta'));
    const tusPedidosItem = Array.from(navbarNav.children).find(li => li.querySelector('a')?.textContent.includes('Tus Pedidos'));
    
    if (token && typeof api !== 'undefined') {
        // Usuario logueado - verificar rol
        api.get('/auth/me').then(user => {
            if (!user) return;
            
            const path = window.location.pathname;
            const isSubfolder = path.includes('/tu-cuenta/') || 
                              path.includes('/carrito/') || 
                              path.includes('/pedidos/');
            const prefix = isSubfolder ? '../' : '';
            
            // Si ya estamos en admin, no agregar más enlaces
            if (path.includes('/admin/')) {
                return;
            }
            
            // Administrador: acceso completo al panel admin
            if (user.rol === 'admin' || user.rol === 'administrador') {
                if (!document.getElementById('nav-admin')) {
                    const adminLi = document.createElement('li');
                    adminLi.className = 'nav-item';
                    adminLi.id = 'nav-admin';
                    adminLi.innerHTML = `<a class="nav-link text-warning" href="${prefix}admin/index.html">Administración</a>`;
                    
                    if (tuCuentaItem) {
                        navbarNav.insertBefore(adminLi, tuCuentaItem);
                    } else {
                        navbarNav.appendChild(adminLi);
                    }
                }
            }
            // Cocinero: acceso solo al panel de cocina
            else if (user.rol === 'cocinero') {
                if (!document.getElementById('nav-cocina')) {
                    const cocinaLi = document.createElement('li');
                    cocinaLi.className = 'nav-item';
                    cocinaLi.id = 'nav-cocina';
                    cocinaLi.innerHTML = `<a class="nav-link text-info" href="${prefix}admin/cocina.html">🍳 Panel Cocina</a>`;
                    
                    if (tuCuentaItem) {
                        navbarNav.insertBefore(cocinaLi, tuCuentaItem);
                    } else {
                        navbarNav.appendChild(cocinaLi);
                    }
                }
            }
        }).catch(err => {
            console.error('Error verificando sesión:', err);
        });

    } else {
        // Usuario no logueado - remover items especiales
        const adminItem = document.getElementById('nav-admin');
        const cocinaItem = document.getElementById('nav-cocina');
        if (adminItem) adminItem.remove();
        if (cocinaItem) cocinaItem.remove();
    }
  }

  function cerrarSesion(event) {
      event.preventDefault();
      if (confirm('¿Estás seguro de que deseas cerrar sesión?')) {
          if (typeof api !== 'undefined') {
              api.logout();
          } else {
              localStorage.removeItem('access_token');
              window.location.href = 'tu-cuenta/login.html';
          }
      }
  }

