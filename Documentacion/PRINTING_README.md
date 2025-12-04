# Sistema de Impresión de Etiquetas Zebra

Este documento explica la arquitectura y el funcionamiento del sistema de impresión de etiquetas para las impresoras Zebra en el sistema MES.

## Arquitectura General

El sistema de impresión utiliza una arquitectura de dos componentes para poder comunicar la aplicación web (que se ejecuta en el navegador) con las impresoras Zebra conectadas localmente a la máquina del usuario.

El flujo de comunicación es el siguiente:

`Frontend (Navegador Web)` -> `Servicio Local de Impresión (Python)` -> `Sistema Operativo (Windows)` -> `Impresora Zebra (USB)`

Esta arquitectura es necesaria debido a que los navegadores web, por razones de seguridad, no tienen acceso directo al hardware del sistema, como los puertos USB.

## Componentes

### 1. Frontend (JavaScript)

El frontend es la interfaz web que el usuario ve y con la que interactúa. En el contexto de la impresión, sus responsabilidades son:

-   **Recopilación de Datos**: Cuando el usuario hace clic en "Imprimir", el código JavaScript en la página (`Control de material de almacen.html`) recopila toda la información necesaria del formulario (código de material, lote, cantidad, etc.).
-   **Generación de ZPL**: Con los datos recopilados, se construye una cadena de texto en **ZPL (Zebra Programming Language)**. Este es el lenguaje de comandos que entienden las impresoras Zebra para diseñar y formatear la etiqueta.
-   **Llamada a la API Local**: El frontend envía el código ZPL generado al servicio local de impresión a través de una solicitud HTTP POST a la dirección `http://localhost:5003/print`.

### 2. Servicio Local de Impresión (`print_service.py`)

Este es un pequeño servidor web basado en Python (usando Flask) que debe estar en ejecución en cada máquina cliente que necesite imprimir etiquetas.

-   **Receptor de Trabajos de Impresión**: El servicio escucha en el puerto `5003` las solicitudes que vienen del frontend.
-   **Procesamiento de ZPL**: Extrae el código ZPL del cuerpo de la solicitud HTTP.
-   **Comunicación con la Impresora**: Utiliza la librería de Python `pywin32` para interactuar con el sistema de impresión de Windows.
    -   Busca una impresora instalada cuyo nombre coincida con los nombres configurados (por ejemplo, "ZDesigner ZT230-300dpi ZPL").
    -   Envía los datos ZPL en formato "RAW" (crudo) directamente a la impresora seleccionada.

## Cómo Funciona el Proceso de Impresión

1.  El usuario llena el formulario en la página "Control de material de almacén" y hace clic en **Imprimir**.
2.  El código JavaScript de la página genera el ZPL para la etiqueta.
3.  JavaScript envía este ZPL al servicio local en `http://localhost:5003/print`.
4.  El servicio `print_service.py`, que se está ejecutando en la misma máquina, recibe la solicitud.
5.  El servicio busca la impresora Zebra conectada.
6.  El servicio envía el ZPL a la impresora a través de las APIs de impresión de Windows.
7.  La impresora Zebra recibe los comandos ZPL y imprime la etiqueta física.

## Requisitos para el Funcionamiento

-   Tener el servicio `print_service.py` ejecutándose en la máquina del cliente.
-   Tener los drivers de la impresora Zebra instalados correctamente en Windows.
-   La impresora debe estar conectada (generalmente por USB) y encendida.

---

## Implementación a Nivel de Código

### Frontend (`Control de material de almacen.html`)

El proceso se inicia en la función `imprimirZebraAutomaticoConDatos`, que orquesta la generación del ZPL y el envío.

1.  **Generación de ZPL**: La función `generarComandoZPLConDatos` crea el string ZPL.

    ```javascript
    function generarComandoZPLConDatos(datosEtiqueta, tipo = 'material') {
        // ... extrae datos como fecha, código, cantidad, etc.
        const fecha = new Date().toLocaleDateString('es-ES');
        const codigo = datosEtiqueta.codigo || '';
        const cantidadActual = String(datosEtiqueta.cantidadActual || '');
        const especificacion = String(datosEtiqueta.especificacionMaterial || '');

        // ... construye el string ZPL
        let comandoZPL = `
            ^XA
            ^PW392
            ^LL165
            ^FT15,0^BQN,2,5^FH\\^FDLA,${codigo}^FS
            ^FT170,1^A0N,32,30^FH\\^CI28^FD${codigo.split(',')[0] || codigo}^FS
            ^FT15,150^A0N,27,25^FH\\^CI28^FD${fecha}^FS
            ^FT170,100^A0N,30,28^FH\\^CI28^FD${especificacion}^FS
            ^FT210,75^A0N,28,26^FH\\^CI28^FD${cantidadActual}^FS
            ^PQ1,0,1,Y
            ^XZ
        `;
        return comandoZPL;
    }
    ```

2.  **Envío al Servicio Local**: La función `enviarAServicioWin32` toma el ZPL y lo envía al servicio local usando la API `fetch` de JavaScript.

    ```javascript
    async function enviarAServicioWin32(comandoZPL, codigo, configuracion) {
        const serviceUrl = configuracion.service_url || 'http://localhost:5003';

        // Enviar comando ZPL para impresión
        const printResponse = await fetch(`${serviceUrl}/print`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                zpl_content: comandoZPL, // El servicio espera este campo
                codigo: codigo,
                source: 'ILSAN_MES_Control_Almacen'
            })
        });

        const printResult = await printResponse.json();

        if (printResponse.ok && printResult.status === 'printed') {
            // Éxito
        } else {
            throw new Error(printResult.error || 'Error desconocido en impresión');
        }
    }
    ```

### Backend (`app/py/print_service.py`)

Este script de Python utiliza la librería `Flask` para crear el servidor web y `pywin32` para interactuar con el sistema de impresión de Windows.

1.  **Endpoint de Impresión**: Se define una ruta `/print` que acepta solicitudes `POST`.

    ```python
    @app.route("/print", methods=["POST"])
    def api_print():
        try:
            body = request.get_json()
            if not body or "zpl_content" not in body:
                abort(400, "JSON inválido, se requiere clave 'zpl_content'")

            zpl_str = body["zpl_content"]
            
            # Convertir string a bytes
            data = zpl_str.encode("utf-8")

            # Llamar a la función de impresión
            success, bytes_written = print_raw(data)

            if success:
                return jsonify({"status": "printed", ...})
            else:
                raise Exception("La impresión no se completó")
                
        except Exception as e:
            return jsonify({"status": "error", "error": str(e)}), 500
    ```

2.  **Función de Impresión Raw**: La función `print_raw` se encarga de la comunicación directa con la impresora.

    ```python
    import win32print

    def find_zebra_printer():
        # ... (lógica para buscar la impresora por nombre)
        # Devuelve el nombre de la impresora, ej: "ZDesigner ZT230-300dpi ZPL"

    def print_raw(data: bytes, printer_name: str = None):
        if not printer_name:
            printer_name = find_zebra_printer()
        
        if not printer_name:
            raise Exception("No se encontró impresora Zebra ZT230 disponible")
        
        try:
            # Abrir una conexión con la impresora
            hPrinter = win32print.OpenPrinter(printer_name)
            try:
                # Iniciar un nuevo trabajo de impresión
                job_id = win32print.StartDocPrinter(hPrinter, 1, ("Etiqueta MES", None, "RAW"))
                
                # Enviar los datos ZPL
                win32print.StartPagePrinter(hPrinter)
                bytes_written = win32print.WritePrinter(hPrinter, data)
                win32print.EndPagePrinter(hPrinter)
                
                # Finalizar el trabajo de impresión
                win32print.EndDocPrinter(hPrinter)
                
                return True, bytes_written
                
            finally:
                # Cerrar la conexión
                win32print.ClosePrinter(hPrinter)
                
        except Exception as e:
            raise Exception(f"Error en impresión: {str(e)}")
    ```
