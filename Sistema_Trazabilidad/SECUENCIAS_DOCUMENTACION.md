# DOCUMENTACIÓN DEL SISTEMA DE SECUENCIAS

## ¿Qué son las secuencias?

Las secuencias te permiten crear reglas basadas en separadores específicos como:
- **Espacios**: 2 espacios consecutivos
- **Tabs**: Tabulaciones
- **Saltos de línea**: \n
- **Separadores personalizados**: ||, ::, etc.

## Ejemplos de uso

### Ejemplo 1: ROHM con 2 espacios
```
Texto: "ROHM  MCR50JZHJ181  0040002446102223HA05"
Separador: 2 espacios
Resultado:
- Proveedor: ROHM (índice 0)
- Número de parte: MCR50JZHJ181 (índice 1)
- Lote: 0040002446102223HA05 (índice 2)
```

### Configuración JSON para API:
```json
{
    "supplier": "ROHM",
    "fullText": "ROHM  MCR50JZHJ181  0040002446102223HA05",
    "sequences": [
        {"type": "spaces", "count": 2}
    ],
    "partNumberIndex": 1,
    "lotNumberIndex": 2,
    "partNumberMaxLength": 15,
    "lotNumberMaxLength": 20
}
```

### Ejemplo 2: Con tabulaciones
```
Texto: "SUPPLIER\tPART123\tLOT456"
Separador: 1 tab
```

### Configuración JSON:
```json
{
    "supplier": "EXAMPLE",
    "fullText": "SUPPLIER\tPART123\tLOT456",
    "sequences": [
        {"type": "tabs", "count": 1}
    ],
    "partNumberIndex": 1,
    "lotNumberIndex": 2
}
```

### Ejemplo 3: Separador personalizado
```
Texto: "VENDOR||PART789||BATCH101"
Separador: || (2 pipes)
```

### Configuración JSON:
```json
{
    "supplier": "VENDOR",
    "fullText": "VENDOR||PART789||BATCH101",
    "sequences": [
        {"type": "custom", "separator": "|", "count": 2}
    ],
    "partNumberIndex": 1,
    "lotNumberIndex": 2
}
```

### Ejemplo 4: Secuencias mixtas
```
Texto: "BRAND  PART123\tLOT456"
Separadores: 2 espacios, luego 1 tab
```

### Configuración JSON:
```json
{
    "supplier": "BRAND",
    "fullText": "BRAND  PART123\tLOT456",
    "sequences": [
        {"type": "spaces", "count": 2},
        {"type": "tabs", "count": 1}
    ],
    "partNumberIndex": 1,
    "lotNumberIndex": 2
}
```

## Tipos de secuencias disponibles:

1. **spaces**: Espacios consecutivos
   ```json
   {"type": "spaces", "count": 2}
   ```

2. **tabs**: Tabulaciones
   ```json
   {"type": "tabs", "count": 1}
   ```

3. **newlines**: Saltos de línea
   ```json
   {"type": "newlines", "count": 1}
   ```

4. **custom**: Separador personalizado
   ```json
   {"type": "custom", "separator": "|", "count": 2}
   ```

## Endpoints de la API:

1. **Crear regla por secuencias**: `POST /api/save_sequence_rule`
2. **Probar secuencia**: `POST /api/test_sequence`
3. **Ver ejemplos**: `GET /api/sequence_examples`
4. **Ver patrón de proveedor**: `GET /api/show_pattern/<supplier>`

## Ventajas del sistema de secuencias:

 **Precisión**: No usa regex flexible, solo busca separadores exactos
 **Simplicidad**: Fácil de configurar y entender
 **Flexibilidad**: Soporta múltiples tipos de separadores
 **Control de longitud**: Puedes limitar la longitud máxima de cada campo
 **Combinaciones**: Puedes combinar diferentes tipos de separadores

## Comparación con otros métodos:

| Método | Ventaja | Desventaja |
|--------|---------|------------|
| **Secuencias** | Preciso, simple | Requiere separadores consistentes |
| **Carácter por carácter** | Muy preciso | Requiere longitud fija |
| **Regex flexible** | Muy flexible | Puede dar falsos positivos |
