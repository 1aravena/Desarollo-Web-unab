/**
 * Scripts Compartidos - La Fornace
 * Sprint 3 - Desarrollo Web y Móvil
 */

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
  });
  
  