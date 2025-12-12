/**
 * API Client v2 - Helper para consumir las nuevas APIs estandarizadas
 * Este módulo facilita la migración de las APIs legacy a las APIs v2
 */

const ApiClient = {
    /**
     * URL base para las APIs v2
     */
    baseUrl: '/api/v2',
    
    /**
     * Headers por defecto
     */
    defaultHeaders: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    },

    /**
     * Realizar petición GET
     * @param {string} endpoint - Endpoint relativo
     * @param {Object} params - Parámetros de query
     * @returns {Promise<Object>} Respuesta parseada
     */
    async get(endpoint, params = {}) {
        const url = new URL(`${this.baseUrl}${endpoint}`, window.location.origin);
        Object.entries(params).forEach(([key, value]) => {
            if (value !== null && value !== undefined && value !== '') {
                url.searchParams.append(key, value);
            }
        });

        try {
            const response = await fetch(url, {
                method: 'GET',
                headers: this.defaultHeaders
            });
            return this._handleResponse(response);
        } catch (error) {
            return this._handleError(error);
        }
    },

    /**
     * Realizar petición POST
     * @param {string} endpoint - Endpoint relativo
     * @param {Object} data - Datos a enviar
     * @returns {Promise<Object>} Respuesta parseada
     */
    async post(endpoint, data = {}) {
        try {
            const response = await fetch(`${this.baseUrl}${endpoint}`, {
                method: 'POST',
                headers: this.defaultHeaders,
                body: JSON.stringify(data)
            });
            return this._handleResponse(response);
        } catch (error) {
            return this._handleError(error);
        }
    },

    /**
     * Realizar petición PUT
     * @param {string} endpoint - Endpoint relativo
     * @param {Object} data - Datos a enviar
     * @returns {Promise<Object>} Respuesta parseada
     */
    async put(endpoint, data = {}) {
        try {
            const response = await fetch(`${this.baseUrl}${endpoint}`, {
                method: 'PUT',
                headers: this.defaultHeaders,
                body: JSON.stringify(data)
            });
            return this._handleResponse(response);
        } catch (error) {
            return this._handleError(error);
        }
    },

    /**
     * Realizar petición DELETE
     * @param {string} endpoint - Endpoint relativo
     * @returns {Promise<Object>} Respuesta parseada
     */
    async delete(endpoint) {
        try {
            const response = await fetch(`${this.baseUrl}${endpoint}`, {
                method: 'DELETE',
                headers: this.defaultHeaders
            });
            return this._handleResponse(response);
        } catch (error) {
            return this._handleError(error);
        }
    },

    /**
     * Manejar respuesta del servidor
     * @private
     */
    async _handleResponse(response) {
        const data = await response.json();
        
        // Las APIs v2 siempre devuelven {success, code, message, data, meta}
        if (!data.success) {
            // Lanzar error con información del servidor
            const error = new Error(data.message || 'Error en la operación');
            error.code = data.code;
            error.errors = data.errors;
            error.status = response.status;
            throw error;
        }
        
        return data;
    },

    /**
     * Manejar errores de red
     * @private
     */
    _handleError(error) {
        // Si ya es un error procesado, relanzar
        if (error.code) throw error;
        
        // Error de red
        const networkError = new Error('Error de conexión. Verifique su conexión a internet.');
        networkError.code = 'NETWORK_ERROR';
        networkError.status = 0;
        throw networkError;
    }
};

/**
 * Plan API Client
 */
const PlanApi = {
    /**
     * Listar planes
     * @param {Object} filters - Filtros opcionales
     * @returns {Promise<Array>} Lista de planes
     */
    async list(filters = {}) {
        const response = await ApiClient.get('/plan', filters);
        return response.data;
    },

    /**
     * Crear plan
     * @param {Object} planData - Datos del plan
     * @returns {Promise<Object>} Plan creado
     */
    async create(planData) {
        const response = await ApiClient.post('/plan', planData);
        return response.data;
    },

    /**
     * Obtener plan por lote
     * @param {string} lotNo - Número de lote
     * @returns {Promise<Object>} Plan
     */
    async get(lotNo) {
        const response = await ApiClient.get(`/plan/${lotNo}`);
        return response.data;
    },

    /**
     * Actualizar plan
     * @param {string} lotNo - Número de lote
     * @param {Object} updates - Campos a actualizar
     * @returns {Promise<Object>} Resultado
     */
    async update(lotNo, updates) {
        const response = await ApiClient.put(`/plan/${lotNo}`, updates);
        return response.data;
    },

    /**
     * Eliminar plan
     * @param {string} lotNo - Número de lote
     * @returns {Promise<Object>} Resultado
     */
    async delete(lotNo) {
        const response = await ApiClient.delete(`/plan/${lotNo}`);
        return response.data;
    },

    /**
     * Cambiar estado
     * @param {string} lotNo - Número de lote
     * @param {string} status - Nuevo estado
     * @param {string} reason - Motivo (opcional)
     * @returns {Promise<Object>} Resultado
     */
    async changeStatus(lotNo, status, reason = '') {
        const response = await ApiClient.post(`/plan/${lotNo}/status`, { status, reason });
        return response.data;
    },

    /**
     * Resumen por líneas
     * @param {string} date - Fecha (opcional)
     * @returns {Promise<Array>} Resumen
     */
    async linesSummary(date = null) {
        const params = date ? { date } : {};
        const response = await ApiClient.get('/plan/lines-summary', params);
        return response.data;
    },

    /**
     * Buscar en RAW
     * @param {string} partNo - Número de parte
     * @returns {Promise<Array>} Resultados
     */
    async searchRaw(partNo) {
        const response = await ApiClient.get('/raw/search', { part_no: partNo });
        return response.data;
    }
};

/**
 * Material API Client
 */
const MaterialApi = {
    /**
     * Listar materiales
     * @param {Object} options - Opciones de búsqueda y paginación
     * @returns {Promise<Object>} {data, meta}
     */
    async list(options = {}) {
        const response = await ApiClient.get('/materials', options);
        return { data: response.data, meta: response.meta };
    },

    /**
     * Obtener material
     * @param {string} codigo - Código del material
     * @returns {Promise<Object>} Material
     */
    async get(codigo) {
        const response = await ApiClient.get(`/materials/${codigo}`);
        return response.data;
    },

    /**
     * Crear material
     * @param {Object} materialData - Datos del material
     * @returns {Promise<Object>} Material creado
     */
    async create(materialData) {
        const response = await ApiClient.post('/materials', materialData);
        return response.data;
    },

    /**
     * Actualizar material
     * @param {string} codigo - Código del material
     * @param {Object} updates - Campos a actualizar
     * @returns {Promise<Object>} Resultado
     */
    async update(codigo, updates) {
        const response = await ApiClient.put(`/materials/${codigo}`, updates);
        return response.data;
    },

    /**
     * Actualizar stock
     * @param {string} codigo - Código del material
     * @param {number} cantidad - Cantidad
     * @param {string} tipo - ENTRADA o SALIDA
     * @param {string} motivo - Motivo (opcional)
     * @returns {Promise<Object>} Resultado
     */
    async updateStock(codigo, cantidad, tipo, motivo = '') {
        const response = await ApiClient.post(`/materials/${codigo}/stock`, {
            cantidad,
            tipo,
            motivo
        });
        return response.data;
    },

    /**
     * Resumen de inventario
     * @returns {Promise<Object>} Resumen
     */
    async summary() {
        const response = await ApiClient.get('/materials/summary');
        return response.data;
    },

    /**
     * Materiales con stock bajo
     * @returns {Promise<Array>} Lista
     */
    async lowStock() {
        const response = await ApiClient.get('/materials/low-stock');
        return response.data;
    },

    /**
     * Historial de movimientos
     * @param {Object} filters - Filtros
     * @returns {Promise<Array>} Movimientos
     */
    async movements(filters = {}) {
        const response = await ApiClient.get('/materials/movements', filters);
        return response.data;
    }
};

/**
 * BOM API Client
 */
const BomApi = {
    /**
     * Listar modelos con BOM
     * @returns {Promise<Array>} Lista de modelos
     */
    async listModels() {
        const response = await ApiClient.get('/bom/models');
        return response.data;
    },

    /**
     * Obtener BOM de un modelo
     * @param {string} modelCode - Código del modelo
     * @returns {Promise<Object>} BOM
     */
    async get(modelCode) {
        const response = await ApiClient.get(`/bom/${modelCode}`);
        return response.data;
    },

    /**
     * Agregar item a BOM
     * @param {string} modelCode - Código del modelo
     * @param {Object} itemData - Datos del item
     * @returns {Promise<Object>} Item creado
     */
    async addItem(modelCode, itemData) {
        const response = await ApiClient.post(`/bom/${modelCode}/items`, itemData);
        return response.data;
    },

    /**
     * Actualizar item
     * @param {number} itemId - ID del item
     * @param {Object} updates - Campos a actualizar
     * @returns {Promise<Object>} Resultado
     */
    async updateItem(itemId, updates) {
        const response = await ApiClient.put(`/bom/items/${itemId}`, updates);
        return response.data;
    },

    /**
     * Eliminar item
     * @param {number} itemId - ID del item
     * @returns {Promise<Object>} Resultado
     */
    async deleteItem(itemId) {
        const response = await ApiClient.delete(`/bom/items/${itemId}`);
        return response.data;
    },

    /**
     * Importar BOM
     * @param {string} modelCode - Código del modelo
     * @param {Array} items - Lista de items
     * @returns {Promise<Object>} Resultado
     */
    async import(modelCode, items) {
        const response = await ApiClient.post(`/bom/${modelCode}/import`, { items });
        return response.data;
    },

    /**
     * Calcular requerimientos
     * @param {string} modelCode - Código del modelo
     * @param {number} quantity - Cantidad a producir
     * @returns {Promise<Object>} Requerimientos
     */
    async requirements(modelCode, quantity) {
        const response = await ApiClient.get(`/bom/${modelCode}/requirements`, { quantity });
        return response.data;
    },

    /**
     * Buscar componente
     * @param {string} query - Término de búsqueda
     * @returns {Promise<Array>} Resultados
     */
    async search(query) {
        const response = await ApiClient.get('/bom/search', { q: query });
        return response.data;
    }
};

/**
 * Toast/Notificación helper
 */
const Toast = {
    show(message, type = 'info') {
        // Si existe toastr, usarlo
        if (typeof toastr !== 'undefined') {
            toastr[type](message);
            return;
        }
        
        // Si existe SweetAlert, usarlo
        if (typeof Swal !== 'undefined') {
            Swal.fire({
                text: message,
                icon: type === 'error' ? 'error' : type === 'success' ? 'success' : 'info',
                toast: true,
                position: 'top-end',
                showConfirmButton: false,
                timer: 3000
            });
            return;
        }
        
        // Fallback a alert
        alert(message);
    },
    
    success(message) { this.show(message, 'success'); },
    error(message) { this.show(message, 'error'); },
    warning(message) { this.show(message, 'warning'); },
    info(message) { this.show(message, 'info'); }
};

/**
 * Helper para manejar errores de API
 */
function handleApiError(error) {
    console.error('API Error:', error);
    
    if (error.status === 401) {
        Toast.error('Sesión expirada. Por favor inicie sesión nuevamente.');
        window.location.href = '/login';
        return;
    }
    
    if (error.status === 403) {
        Toast.error('No tiene permisos para realizar esta acción.');
        return;
    }
    
    if (error.code === 'NETWORK_ERROR') {
        Toast.error('Error de conexión. Verifique su conexión a internet.');
        return;
    }
    
    // Error genérico
    Toast.error(error.message || 'Ha ocurrido un error');
}

// Exportar para uso global
window.ApiClient = ApiClient;
window.PlanApi = PlanApi;
window.MaterialApi = MaterialApi;
window.BomApi = BomApi;
window.Toast = Toast;
window.handleApiError = handleApiError;
