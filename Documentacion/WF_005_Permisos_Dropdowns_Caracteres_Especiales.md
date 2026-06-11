# WF_005 - Permisos de Dropdowns con Caracteres Especiales

> **Version:** 1.0
> **Fecha:** 2026-06-10
> **Prerequisitos:** [WF_001](./WF_001_Nuevos_Modulos_AJAX_Templates.md), [WF_002](./WF_002_Crear_Template_Completo.md), [WF_003](./WF_003_Integracion_API_JS_Template.md), [WF_004](./WF_004_Estilos_Persistentes_Modulos_AJAX.md)
> **Caso real:** Modulos `PPM's IQC`, `PPM's LQC` y `PPM's OQC` en `Control de calidad`

---

## Resumen

Este documento cubre un problema detectado en la pantalla de administracion de permisos:

```text
/admin/permisos-dropdowns
```

El caso aparecio al agregar permisos de modulos cuyos nombres contienen apostrofes, por ejemplo:

```text
PPM's IQC
PPM's LQC
PPM's OQC
```

El usuario activaba el switch de permiso, el switch quedaba visualmente verde, pero la tarjeta seguia en rojo y el permiso no se guardaba correctamente para el rol.

---

## Relacion con WF_001 a WF_004

Se revisaron los flujos existentes:

| Documento | Que cubre | Aplica a este caso |
|---|---|---|
| `WF_001` | Alta de botones en `LISTA_*.html`, `data-permiso-*`, sincronizacion y asignacion por rol | Parcialmente |
| `WF_002` | Creacion completa de template, CSS, JS, contenedor y sincronizacion de permisos | Parcialmente |
| `WF_003` | Integracion de API backend y JS frontend del modulo | No directamente |
| `WF_004` | Persistencia de CSS en fragments AJAX | No directamente |

Ninguno documentaba el riesgo especifico de renderizar permisos con caracteres especiales dentro de JavaScript inline. Por eso este caso queda documentado como `WF_005`.

---

## Problema Observado

### Sintomas

En la pantalla de permisos:

1. Los permisos `PPM's IQC`, `PPM's LQC` y `PPM's OQC` aparecian listados.
2. Al activar el switch, el switch cambiaba a verde.
3. La tarjeta completa seguia con borde/fondo rojo.
4. Al recargar o volver a consultar el rol, el permiso seguia sin estar asignado.
5. Otros permisos sin apostrofe funcionaban correctamente.

### Impacto

- El administrador podia creer que el permiso quedo activo cuando no se guardo.
- Los usuarios del rol afectado no veian los nuevos modulos en el sidebar.
- El problema era facil de confundir con falta de sincronizacion de permisos, pero los registros si existian en `permisos_botones`.

---

## Causa Raiz

La pantalla `admin/gestionar_permisos_dropdowns.html` generaba el handler del switch usando JavaScript inline:

```html
onchange="togglePermission('${permission.pagina}', '${permission.seccion}', '${permission.boton}', this.checked)"
```

Cuando `permission.seccion` o `permission.boton` contenia un apostrofe, el JavaScript generado quedaba roto.

Ejemplo conceptual:

```javascript
togglePermission('LISTA_CONTROL_DE_CALIDAD', 'PPM's', 'PPM's LQC', true)
```

El apostrofe de `PPM's` cerraba la cadena antes de tiempo. El navegador podia cambiar el estado visual del checkbox, pero el handler no ejecutaba correctamente el guardado.

---

## Solucion Aplicada

La correccion se hizo en:

```text
app/templates/admin/gestionar_permisos_dropdowns.html
```

### 1. Eliminar JavaScript inline para permisos dinamicos

En lugar de insertar `togglePermission(...)` dentro del atributo `onchange`, se creo el checkbox sin handler inline:

```html
<input type="checkbox" class="permission-toggle-input">
```

Y se enlazo el evento desde JavaScript:

```javascript
const toggleInput = permissionElement.querySelector('.permission-toggle-input');
toggleInput.addEventListener('change', function() {
    togglePermission(permission.pagina, permission.seccion, permission.boton, this.checked);
});
```

Con esto los valores reales se mantienen como datos JavaScript, no como texto interpolado dentro de un atributo HTML.

### 2. Escapar texto visible

Tambien se agrego `escapeHtml()` para renderizar textos de permisos sin permitir que caracteres especiales rompan el HTML:

```javascript
function escapeHtml(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}
```

Se usa para:

- titulo del permiso,
- pagina,
- seccion,
- descripcion.

---

## Regla para Nuevos Desarrollos

Cuando se renderice informacion que viene de base de datos o de atributos `data-permiso-*`:

1. No interpolar valores dinamicos en handlers inline como `onclick`, `onchange`, `onkeyup`.
2. Usar `addEventListener()` para eventos.
3. Usar `dataset` o closures para conservar valores dinamicos.
4. Escapar texto visible con una funcion equivalente a `escapeHtml()`.
5. Probar al menos un permiso con caracteres especiales:
   - apostrofe: `PPM's`
   - comillas dobles: `Modulo "A"`
   - ampersand: `A&B`
   - acentos: `Inspeccion / Inspección`

---

## Checklist de Diagnostico

Si un permiso aparece listado pero no queda activo:

```text
[ ] Confirmar que existe en permisos_botones y activo = 1
[ ] Confirmar que la pantalla /admin/listar_permisos_dropdowns devuelve id valido
[ ] Revisar consola del navegador por SyntaxError o errores de handler inline
[ ] Confirmar que /admin/actualizar_permisos_dropdowns_rol responde success = true
[ ] Confirmar que rol_permisos_botones contiene rol_id + permiso_boton_id
[ ] Invalidar cache con auth_system.invalidar_cache_permisos_botones()
[ ] Recargar /inicio o cerrar/abrir sesion si el usuario ya tenia permisos cacheados
```

Consulta de apoyo:

```sql
SELECT id, pagina, seccion, boton, descripcion, activo
FROM permisos_botones
WHERE pagina = 'LISTA_CONTROL_DE_CALIDAD'
  AND (seccion LIKE '%PPM%' OR boton LIKE '%PPM%')
ORDER BY seccion, boton, id;
```

Asignaciones por rol:

```sql
SELECT r.id AS rol_id, r.nombre, pb.id AS permiso_id, pb.pagina, pb.seccion, pb.boton
FROM roles r
JOIN rol_permisos_botones rpb ON rpb.rol_id = r.id
JOIN permisos_botones pb ON pb.id = rpb.permiso_boton_id
WHERE r.nombre = 'calidad'
  AND pb.pagina = 'LISTA_CONTROL_DE_CALIDAD'
  AND pb.seccion = 'PPM''s'
ORDER BY pb.boton;
```

---

## Recomendacion de Mantenimiento

La pantalla de administracion de permisos debe tratar todos los nombres de pagina, seccion y boton como datos externos. Aunque hoy vengan de templates internos, tambien pueden sincronizarse desde HTML o ser modificados en BD.

Por lo tanto:

- no usar handlers inline para permisos,
- no concatenar HTML con texto sin escapar,
- mantener la persistencia por `id` de `permisos_botones`,
- re-renderizar la tarjeta despues de guardar para que la clase `enabled` / `disabled` refleje el estado real del arreglo local.

