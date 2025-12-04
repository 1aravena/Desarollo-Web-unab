/**
 * Cocina - Panel de Órdenes
 * Historia: B-08 Impresión Automática de Órdenes
 */

let ordenesActuales = [];
let filtroActual = 'todos';
let ordenSeleccionada = null;

// Ocultar menús que no son para cocineros
function ocultarMenusNoCocinero() {
    const navbar = document.querySelector('#mainNav .navbar-nav');
    if (!navbar) return;
    
    // Links que el cocinero NO debe ver (solo cocina y volver a tienda)
    const linksAOcultar = ['Dashboard', 'Productos', 'Reportes', 'Ranking', 'Notificaciones'];
    
    navbar.querySelectorAll('.nav-item').forEach(item => {
        const link = item.querySelector('a');
        if (link) {
            const texto = link.textContent.trim();
            if (linksAOcultar.some(l => texto.includes(l))) {
                item.style.display = 'none';
            }
        }
    });
    
    // Cambiar el título del navbar
    const brandSpan = document.querySelector('.navbar-brand span');
    if (brandSpan) {
        brandSpan.textContent = 'La Fornace - Cocina';
    }
}

// Cargar órdenes al iniciar
document.addEventListener('DOMContentLoaded', async function() {
    // Verificar autenticación
    if (!api.isAuthenticated()) {
        window.location.href = '../tu-cuenta/login.html';
        return;
    }
    
    // Verificar rol (admin o cocinero)
    try {
        const user = await api.get('/auth/me');
        if (!user || !['admin', 'administrador', 'cocinero'].includes(user.rol)) {
            alert('No tienes permisos para acceder al panel de cocina');
            window.location.href = '../index.html';
            return;
        }
        
        // Si es cocinero, ocultar enlaces a otras secciones de admin
        if (user.rol === 'cocinero') {
            ocultarMenusNoCocinero();
        }
    } catch (error) {
        console.error('Error verificando permisos:', error);
        window.location.href = '../tu-cuenta/login.html';
        return;
    }
    
    await cargarOrdenes();
    
    // Event listeners para filtros
    document.querySelectorAll('input[name="filtroEstado"]').forEach(function(radio) {
        radio.addEventListener('change', function() {
            filtroActual = this.value;
            renderizarOrdenes();
        });
    });
});

// Cargar órdenes desde la API
async function cargarOrdenes() {
    var container = document.getElementById('ordenes-container');
    container.innerHTML = '<div class="text-center py-5"><div class="spinner-border text-primary" role="status"></div><p class="mt-2">Cargando órdenes...</p></div>';
    
    try {
        // Cargar todos los pedidos (el endpoint filtra según rol)
        ordenesActuales = await api.get('/pedidos');
        
        if (!Array.isArray(ordenesActuales)) {
            ordenesActuales = [];
        }
        
        console.log('Órdenes cargadas:', ordenesActuales.length);
        renderizarOrdenes();
    } catch (error) {
        console.error('Error al cargar órdenes:', error);
        container.innerHTML = '<div class="alert alert-danger">' +
            '<strong>Error al cargar órdenes:</strong> ' + error.message +
            '<br><small>Verifica que la API esté funcionando y tengas permisos de administrador/cocinero.</small>' +
            '</div>';
    }
}

// Actualizar órdenes
async function actualizarOrdenes() {
    await cargarOrdenes();
    mostrarExito('Órdenes actualizadas');
}

// Formatear fecha ISO a formato legible
function formatearFechaHora(fechaISO) {
    if (!fechaISO) return { fecha: 'Sin fecha', hora: '' };
    var fecha = new Date(fechaISO);
    return {
        fecha: fecha.toLocaleDateString('es-CL'),
        hora: fecha.toLocaleTimeString('es-CL', { hour: '2-digit', minute: '2-digit' })
    };
}

// Renderizar órdenes
function renderizarOrdenes() {
    var container = document.getElementById('ordenes-container');
    var vacioDiv = document.getElementById('ordenes-vacias');
    
    // Filtrar por estado (excluir entregados y anulados por defecto en cocina)
    var ordenesFiltradas = ordenesActuales;
    
    if (filtroActual === 'todos') {
        // En "todos", mostrar solo los relevantes para cocina (no entregados ni anulados)
        ordenesFiltradas = ordenesActuales.filter(function(o) {
            return ['pendiente', 'confirmado', 'en_preparacion', 'en_camino'].indexOf(o.estado) !== -1;
        });
    } else {
        ordenesFiltradas = ordenesActuales.filter(function(o) {
            return o.estado === filtroActual;
        });
    }
    
    // Ordenar por fecha (más recientes primero)
    ordenesFiltradas.sort(function(a, b) {
        return new Date(b.fecha) - new Date(a.fecha);
    });
    
    if (ordenesFiltradas.length === 0) {
        container.style.display = 'none';
        vacioDiv.style.display = 'block';
        return;
    }
    
    container.style.display = 'block';
    vacioDiv.style.display = 'none';
    
    var html = '';
    ordenesFiltradas.forEach(function(orden) {
        var estadoInfo = obtenerInfoEstadoCocina(orden.estado);
        var fechaHora = formatearFechaHora(orden.fecha);
        
        // Obtener items del pedido (están en items_json)
        var items = (orden.items_json && orden.items_json.items) ? orden.items_json.items : [];
        var resumenItems = items.map(function(item) {
            var itemText = item.cantidad + 'x ' + item.nombre;
            
            // Agregar tamaño si existe
            if (item.tamanio && item.tamanio.nombre) {
                itemText += ' (' + item.tamanio.nombre + ')';
            }
            
            // Agregar extras si existen
            if (item.extras && item.extras.length > 0) {
                var extrasTexto = item.extras.map(function(e) { return e.nombre; }).join(', ');
                itemText += '<br><small class="text-success">+ ' + extrasTexto + '</small>';
            }
            
            if (item.notas) {
                itemText += '<br><small class="text-muted">Notas: ' + item.notas + '</small>';
            }
            return itemText;
        }).join('<br>');
        
        html += '<div class="card mb-3 shadow-sm border-0 border-start border-' + estadoInfo.colorBorder + ' border-4">' +
            '<div class="card-body">' +
                '<div class="row">' +
                    '<div class="col-md-8">' +
                        '<div class="d-flex justify-content-between align-items-start mb-2">' +
                            '<h5 class="mb-0">Orden #' + orden.id + '</h5>' +
                            '<span class="badge ' + estadoInfo.clase + ' fs-6">' + estadoInfo.texto + '</span>' +
                        '</div>' +
                        '<p class="text-muted mb-2">' +
                            '<small>' +
                                '<strong>Fecha:</strong> ' + fechaHora.fecha + ' ' + fechaHora.hora +
                                (orden.eta_minutos ? '<br><strong>ETA:</strong> ' + orden.eta_minutos + ' minutos' : '') +
                            '</small>' +
                        '</p>' +
                        '<p class="mb-2"><strong>Items:</strong><br>' + (resumenItems || 'Sin items') + '</p>' +
                        '<p class="mb-1"><small class="text-muted"><strong>Dirección:</strong> ' + orden.direccion + '</small></p>' +
                        '<p class="mb-0"><small class="text-muted"><strong>Teléfono:</strong> ' + orden.telefono + '</small></p>' +
                        (orden.instrucciones_especiales ? '<p class="mb-0 mt-2"><small class="text-warning"><strong>Instrucciones:</strong> ' + orden.instrucciones_especiales + '</small></p>' : '') +
                    '</div>' +
                    '<div class="col-md-4 text-md-end mt-3 mt-md-0">' +
                        '<p class="fs-5 fw-bold text-primary mb-3">' + formatearPrecio(orden.total) + '</p>' +
                        '<button class="btn btn-outline-primary btn-sm mb-2 w-100" onclick="verTicket(' + orden.id + ')">' +
                            '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-receipt me-1" viewBox="0 0 16 16">' +
                                '<path d="M1.92.506a.5.5 0 0 1 .434.14L3 1.293l.646-.647a.5.5 0 0 1 .708 0L5 1.293l.646-.647a.5.5 0 0 1 .708 0L7 1.293l.646-.647a.5.5 0 0 1 .708 0L9 1.293l.646-.647a.5.5 0 0 1 .708 0l.646.647.646-.647a.5.5 0 0 1 .708 0l.646.647.646-.647a.5.5 0 0 1 .801.13l.5 1A.5.5 0 0 1 15 2v12a.5.5 0 0 1-.053.224l-.5 1a.5.5 0 0 1-.8.13L13 14.707l-.646.647a.5.5 0 0 1-.708 0L11 14.707l-.646.647a.5.5 0 0 1-.708 0L9 14.707l-.646.647a.5.5 0 0 1-.708 0L7 14.707l-.646.647a.5.5 0 0 1-.708 0L5 14.707l-.646.647a.5.5 0 0 1-.708 0L3 14.707l-.646.647a.5.5 0 0 1-.801-.13l-.5-1A.5.5 0 0 1 1 14V2a.5.5 0 0 1 .053-.224l.5-1a.5.5 0 0 1 .367-.27z"/>' +
                            '</svg>' +
                            'Ver Ticket' +
                        '</button>';
        
        if (estadoInfo.mostrarBotonEstado) {
            html += '<button class="btn btn-' + estadoInfo.botonClase + ' btn-sm w-100" onclick="cambiarEstadoOrden(' + orden.id + ', \'' + estadoInfo.siguienteEstado + '\')">' +
                estadoInfo.botonTexto +
                '</button>';
        }
        
        if (orden.estado === 'en_camino') {
            html += '<button class="btn btn-success btn-sm w-100 mt-2" onclick="cambiarEstadoOrden(' + orden.id + ', \'entregado\')">' +
                'Marcar Entregado' +
                '</button>';
        }
        
        html += '</div></div></div></div>';
    });
    
    container.innerHTML = html;
}

// Obtener información del estado para cocina
function obtenerInfoEstadoCocina(estado) {
    var estados = {
        'pendiente': { 
            texto: 'Pendiente', 
            clase: 'bg-secondary',
            colorBorder: 'secondary',
            mostrarBotonEstado: true,
            botonTexto: 'Confirmar Pedido',
            botonClase: 'primary',
            siguienteEstado: 'confirmado'
        },
        'confirmado': { 
            texto: 'Confirmado', 
            clase: 'bg-primary',
            colorBorder: 'primary',
            mostrarBotonEstado: true,
            botonTexto: 'Iniciar Preparación',
            botonClase: 'warning',
            siguienteEstado: 'en_preparacion'
        },
        'en_preparacion': { 
            texto: 'En Preparación', 
            clase: 'bg-warning text-dark',
            colorBorder: 'warning',
            mostrarBotonEstado: true,
            botonTexto: 'Listo para Envío',
            botonClase: 'info',
            siguienteEstado: 'en_camino'
        },
        'en_camino': { 
            texto: 'En Camino', 
            clase: 'bg-info',
            colorBorder: 'info',
            mostrarBotonEstado: false
        },
        'entregado': { 
            texto: 'Entregado', 
            clase: 'bg-success',
            colorBorder: 'success',
            mostrarBotonEstado: false
        },
        'anulado': { 
            texto: 'Anulado', 
            clase: 'bg-danger',
            colorBorder: 'danger',
            mostrarBotonEstado: false
        },
        'cancelado': { 
            texto: 'Cancelado', 
            clase: 'bg-danger',
            colorBorder: 'danger',
            mostrarBotonEstado: false
        }
    };
    return estados[estado] || { texto: estado, clase: 'bg-secondary', colorBorder: 'secondary', mostrarBotonEstado: false };
}

// Ver ticket
function verTicket(ordenId) {
    ordenSeleccionada = ordenesActuales.find(function(o) {
        return o.id === ordenId;
    });
    if (!ordenSeleccionada) return;
    
    var ticket = generarTicket(ordenSeleccionada);
    document.getElementById('ticket-contenido').textContent = ticket;
    
    var modal = new bootstrap.Modal(document.getElementById('modalTicket'));
    modal.show();
}

// Generar ticket de cocina (B-08)
function generarTicket(orden) {
    var fechaHora = formatearFechaHora(orden.fecha);
    var items = (orden.items_json && orden.items_json.items) ? orden.items_json.items : [];
    
    var lineas = [
        '========================================',
        '        PIZZERÍA LA FORNACE',
        '        TICKET DE COCINA',
        '========================================',
        '',
        'Orden #: ' + orden.id,
        'Fecha: ' + fechaHora.fecha,
        'Hora: ' + fechaHora.hora,
        '',
        '----------------------------------------',
        'ITEMS DEL PEDIDO:',
        '----------------------------------------',
        ''
    ];
    
    items.forEach(function(item) {
        var itemLine = item.cantidad + 'x ' + item.nombre;
        
        // Agregar tamaño si existe
        if (item.tamanio && item.tamanio.nombre) {
            itemLine += ' (' + item.tamanio.nombre + ')';
        }
        
        lineas.push(itemLine);
        
        // Agregar extras si existen
        if (item.extras && item.extras.length > 0) {
            item.extras.forEach(function(extra) {
                lineas.push('    + ' + extra.nombre + ' (' + formatearPrecio(extra.precio) + ')');
            });
        }
        
        if (item.notas) {
            lineas.push('    Notas: ' + item.notas);
        }
        lineas.push('    Precio: ' + formatearPrecio(item.precio_unitario * item.cantidad));
        lineas.push('');
    });
    
    lineas.push('----------------------------------------');
    lineas.push('DIRECCIÓN DE ENTREGA:');
    lineas.push('----------------------------------------');
    lineas.push(orden.direccion);
    lineas.push('Tel: ' + orden.telefono);
    lineas.push('');
    
    if (orden.instrucciones_especiales) {
        lineas.push('INSTRUCCIONES ESPECIALES:');
        lineas.push(orden.instrucciones_especiales);
        lineas.push('');
    }
    
    if (orden.eta_minutos) {
        lineas.push('ETA: ' + orden.eta_minutos + ' minutos');
        lineas.push('');
    }
    
    lineas.push('----------------------------------------');
    lineas.push('SUBTOTAL: ' + formatearPrecio(orden.subtotal));
    lineas.push('ENVÍO: ' + formatearPrecio(orden.costo_envio));
    lineas.push('IVA: ' + formatearPrecio(orden.impuestos));
    
    if (orden.descuento > 0) {
        lineas.push('DESCUENTO: -' + formatearPrecio(orden.descuento));
    }
    
    lineas.push('----------------------------------------');
    lineas.push('TOTAL: ' + formatearPrecio(orden.total));
    lineas.push('----------------------------------------');
    lineas.push('');
    lineas.push('Estado: ' + obtenerInfoEstadoCocina(orden.estado).texto);
    lineas.push('Método de pago: ' + (orden.metodo_pago || 'No especificado'));
    lineas.push('');
    lineas.push('========================================');
    
    return lineas.join('\n');
}

// Imprimir ticket (B-08)
function imprimirTicket() {
    if (!ordenSeleccionada) return;
    
    // Crear ventana de impresión con el ticket
    var ticketContent = generarTicket(ordenSeleccionada);
    var printWindow = window.open('', '_blank');
    
    var htmlContent = '<!DOCTYPE html>' +
        '<html>' +
        '<head>' +
        '<title>Ticket Orden #' + ordenSeleccionada.id + '</title>' +
        '<style>' +
        'body { font-family: "Courier New", monospace; font-size: 12px; padding: 10px; max-width: 300px; margin: 0 auto; }' +
        'pre { white-space: pre-wrap; word-wrap: break-word; }' +
        '@media print { body { margin: 0; padding: 5px; } }' +
        '</style>' +
        '</head>' +
        '<body>' +
        '<pre>' + ticketContent + '</pre>' +
        '<script>window.onload = function() { window.print(); window.onafterprint = function() { window.close(); }; };<\/script>' +
        '</body>' +
        '</html>';
    
    printWindow.document.write(htmlContent);
    printWindow.document.close();
    
    mostrarExito('Ticket enviado a impresora');
    
    // Cerrar modal
    var modalEl = document.getElementById('modalTicket');
    var modal = bootstrap.Modal.getInstance(modalEl);
    if (modal) modal.hide();
}

// Cambiar estado de la orden (usa la API)
async function cambiarEstadoOrden(ordenId, nuevoEstado) {
    try {
        await api.patch('/pedidos/' + ordenId + '/estado', { estado: nuevoEstado });
        
        var nombreEstado = obtenerInfoEstadoCocina(nuevoEstado).texto;
        mostrarExito('Orden #' + ordenId + ' actualizada a: ' + nombreEstado);
        
        // Recargar órdenes desde la API
        await cargarOrdenes();
    } catch (error) {
        console.error('Error al cambiar estado:', error);
        mostrarError('Error al actualizar orden: ' + error.message);
    }
}
