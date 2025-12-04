/**
 * ============================================================================
 * Cliente API - Pizzeria La Fornace
 * ============================================================================
 * 
 * Este modulo centraliza todas las peticiones HTTP al backend.
 * Implementa el patron Singleton para garantizar una unica instancia.
 * 
 * Caracteristicas:
 * ----------------
 * - Manejo automatico de tokens JWT (E-06, E-07)
 * - Inyeccion de headers de autenticacion
 * - Manejo centralizado de errores
 * - Redireccion automatica en caso de sesion expirada (401)
 * - Metodos helper para GET, POST, PUT, PATCH, DELETE
 * 
 * Uso:
 * ----
 * // Peticion GET
 * const productos = await api.get('/productos/menu/completo');
 * 
 * // Peticion POST con autenticacion
 * await api.post('/carrito/items', { producto_id: 1, cantidad: 2 });
 * 
 * // Login (guarda token automaticamente)
 * await api.login('usuario@email.com', 'password');
 * 
 * Endpoints principales:
 * ----------------------
 * - /auth/*          : Autenticacion y usuarios
 * - /productos/*     : Menu y gestion de productos
 * - /carrito/*       : Carrito de compras
 * - /pedidos/*       : Pedidos y historial
 * - /anulaciones/*   : Solicitudes de anulacion
 * - /reportes/*      : Reportes y estadisticas
 * 
 * ============================================================================
 */

const API_BASE_URL = 'http://localhost:8000/api/v1';

class ApiClient {
    constructor() {
        this.baseUrl = API_BASE_URL;
    }

    // ========================================================================
    // GESTION DE TOKEN JWT
    // ========================================================================

    /**
     * Obtener token del almacenamiento local
     * El token se guarda al hacer login y se usa para autenticar peticiones
     */
    getToken() {
        return localStorage.getItem('access_token');
    }

    /**
     * Guardar token en almacenamiento local
     * @param {string} token - Token JWT recibido del servidor
     */
    setToken(token) {
        localStorage.setItem('access_token', token);
    }

    /**
     * Cerrar sesion: elimina token y redirige al login
     * Maneja correctamente la redireccion desde cualquier subcarpeta
     */
    logout() {
        localStorage.removeItem('access_token');
        
        // Detectar ruta base para redireccion correcta
        const path = window.location.pathname;
        
        if (path.includes('/tu-cuenta/') || path.includes('/carrito/') || path.includes('/admin/') || path.includes('/pedidos/')) {
            if (path.includes('/tu-cuenta/')) {
                window.location.href = 'login.html';
            } else {
                window.location.href = '../tu-cuenta/login.html';
            }
        } else {
            window.location.href = 'tu-cuenta/login.html';
        }
    }

    /**
     * Verificar si el usuario esta autenticado
     * @returns {boolean} true si existe un token guardado
     */
    isAuthenticated() {
        return !!this.getToken();
    }

    // ========================================================================
    // METODO PRINCIPAL DE PETICIONES HTTP
    // ========================================================================

    /**
     * Metodo generico para realizar peticiones HTTP
     * Inyecta automaticamente el token JWT si existe
     * 
     * @param {string} endpoint - Ruta del endpoint (ej: '/productos')
     * @param {string} method - Metodo HTTP (GET, POST, PUT, DELETE, PATCH)
     * @param {object} body - Cuerpo de la peticion (para POST, PUT, PATCH)
     * @param {object} headers - Headers adicionales
     * @returns {Promise<object>} Respuesta del servidor parseada como JSON
     */
    async request(endpoint, method = 'GET', body = null, headers = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        
        console.log(`[API] ${method} ${url}`);
        
        const defaultHeaders = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        };

        // Inyectar token JWT si existe (autenticacion Bearer)
        const token = this.getToken();
        if (token) {
            defaultHeaders['Authorization'] = `Bearer ${token}`;
        }

        const config = {
            method,
            headers: { ...defaultHeaders, ...headers }
        };

        if (body) {
            config.body = JSON.stringify(body);
        }

        try {
            const response = await fetch(url, config);
            
            // Manejar error 401 (sesion expirada o token invalido)
            if (response.status === 401) {
                if (!endpoint.includes('/auth/login')) {
                    this.logout();
                    return null;
                }
            }

            const data = await response.json();

            if (!response.ok) {
                // Extraer mensaje de error del formato de respuesta de FastAPI
                let errorMessage = 'Error en la peticion';
                
                if (data.detail) {
                    if (typeof data.detail === 'string') {
                        errorMessage = data.detail;
                    } else if (Array.isArray(data.detail)) {
                        // Errores de validacion de Pydantic
                        errorMessage = data.detail.map(err => {
                            const field = err.loc.length > 1 ? err.loc[err.loc.length - 1] : err.loc[0];
                            return `${field}: ${err.msg}`;
                        }).join(', ');
                    } else if (typeof data.detail === 'object') {
                        errorMessage = JSON.stringify(data.detail);
                    }
                } else if (data.message) {
                    errorMessage = data.message;
                }
                
                throw new Error(errorMessage);
            }

            return data;
        } catch (error) {
            console.error('[API] Error:', error);
            throw error;
        }
    }

    // ========================================================================
    // METODOS HELPER (atajos para los verbos HTTP comunes)
    // ========================================================================

    get(endpoint) {
        return this.request(endpoint, 'GET');
    }

    post(endpoint, body) {
        return this.request(endpoint, 'POST', body);
    }

    put(endpoint, body) {
        return this.request(endpoint, 'PUT', body);
    }

    patch(endpoint, body) {
        return this.request(endpoint, 'PATCH', body);
    }

    delete(endpoint) {
        return this.request(endpoint, 'DELETE');
    }

    // ========================================================================
    // METODOS DE AUTENTICACION
    // ========================================================================
    
    /**
     * Iniciar sesion con email y password
     * Guarda automaticamente el token JWT en localStorage
     * 
     * @param {string} email - Email del usuario
     * @param {string} password - Contrasena
     * @returns {Promise<object>} Respuesta con token y datos del usuario
     */
    async login(email, password) {
        try {
            const response = await this.post('/auth/login', {
                email: email,
                password: password
            });
            
            // Guardar token para futuras peticiones
            this.setToken(response.access_token);
            return response;
        } catch (error) {
            console.error("Error en login:", error);
            throw error;
        }
    }
}

// ============================================================================
// INSTANCIA GLOBAL
// ============================================================================
// Se crea una unica instancia que se usa en toda la aplicacion
const api = new ApiClient();

