# WF_011 - Analisis de Mejoras del Repositorio

> **Estado:** Documento homologado
> **Origen:** Consolida `ANALISIS_MEJORAS_REPO.md`
> **Uso:** Backlog tecnico priorizado de seguridad, arquitectura, mantenibilidad y operacion.

---

## Resumen

Este documento registra mejoras tecnicas detectadas en el repositorio MES ILSAN. No representa cambios aplicados; es una lista priorizada para planificar remediacion.

## Prioridades

| Prioridad | Area | Motivo |
|---|---|---|
| Alta | Seguridad | Riesgo directo sobre cuentas, sesiones o acceso. |
| Alta/Media | Arquitectura y datos | Riesgo de fallos operativos o deuda estructural. |
| Media | Mantenibilidad | Dificulta cambios seguros. |
| Media/Baja | Higiene de repositorio | Reduce claridad y aumenta ruido. |
| Baja | Observabilidad | Mejora diagnostico y soporte. |

## Seguridad

### Hashing de passwords

Problema:

- Uso de SHA-256 rapido y sin sal para passwords.
- Comparacion directa de hashes.
- Existen imports de herramientas mas seguras que deberian aprovecharse.

Accion recomendada:

- Migrar a `generate_password_hash` y `check_password_hash`.
- Rehashear en el proximo login exitoso para no romper usuarios existentes.

### Credencial admin por defecto

Problema:

- Existe riesgo si `admin / admin123` queda activo en ambientes reales.

Accion recomendada:

- Forzar cambio de password en primer login.
- O exigir password inicial por variable de entorno.

### `SECRET_KEY` con fallback

Problema:

- Un fallback hardcodeado permite firmar sesiones si llega a produccion.

Accion recomendada:

- Fallar al arrancar en produccion si falta `SECRET_KEY`.
- Permitir fallback solo en desarrollo local controlado.

### Cookies de sesion

Problema:

- Faltan flags explicitos como `SESSION_COOKIE_SECURE`, `HTTPONLY`, `SAMESITE` y expiracion.

Accion recomendada:

```python
app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)
```

### SQL dinamico

Estado:

- El riesgo actual parece bajo si los f-strings solo interpolan identificadores controlados por servidor.

Accion recomendada:

- Documentar la regla: nunca interpolar input de usuario en SQL.
- Mantener whitelist para columnas, tablas o expresiones.

## Arquitectura y Capa de Datos

### Acceso a datos fragmentado

Problema:

- Existen multiples wrappers o clientes MySQL/SQLite, algunos activos y otros legacy.

Accion recomendada:

- Declarar `config_mysql.py` como owner del pool.
- Eliminar o archivar codigo muerto solo despues de confirmar referencias.

### Manejo silencioso de errores

Problema:

- Si `execute_query` traga errores, se ocultan fallos reales y se dificulta diagnostico.

Accion recomendada:

- Log estructurado.
- Retornar errores controlados.
- Evitar `except` amplios sin contexto.

### Reemplazos fragiles SQL

Problema:

- Conversiones SQLite/MySQL por texto pueden romper queries complejas.

Accion recomendada:

- Reducir conversiones ad hoc.
- Separar queries por dialecto cuando sea necesario.

## Calidad y Mantenibilidad

| Hallazgo | Accion |
|---|---|
| Archivos muy grandes | Seguir extraccion a blueprints y helpers por dominio. |
| Decoradores proxy repetidos | Usar fachada central en `app/api/shared`. |
| `print()` como logging | Migrar gradualmente a `logging`. |
| Falta de pruebas | Agregar smoke tests para rutas criticas y permisos. |
| TODO/FIXME acumulados | Clasificar y convertir a backlog real. |

## Higiene del Repositorio

Acciones recomendadas:

- Revisar binarios o datos operativos versionados.
- Mantener una sola configuracion de despliegue activa por ambiente.
- Eliminar archivos de compatibilidad vacios o triviales si ya no cumplen funcion.
- Documentar excepciones si se conservan por despliegue.

## Observabilidad

Recomendaciones:

- Logging por modulo.
- Correlation IDs para operaciones AJAX criticas.
- Registro de errores de API con usuario/ruta/contexto no sensible.
- Health checks de DB.

## Tabla de Remediacion Sugerida

| Orden | Accion | Riesgo |
|---|---|---|
| 1 | Proteger `SECRET_KEY` y cookies | Alto |
| 2 | Migrar hashing de passwords | Alto |
| 3 | Controlar credencial admin inicial | Alto |
| 4 | Estandarizar acceso a datos | Medio |
| 5 | Mejorar logging de errores DB/API | Medio |
| 6 | Agregar smoke tests de login/permisos/modulos | Medio |
| 7 | Limpiar codigo muerto confirmado | Bajo/Medio |

## Lo que No Conviene Tocar sin Necesidad

- Patrones de permisos que ya esten funcionando hasta tener pruebas.
- Rutas legacy criticas sin mapa de consumidores.
- Migraciones DB sin respaldo.
- Integraciones de PDA/embarques sin prueba en flujo real.

## Documento Legacy Cubierto

- `ANALISIS_MEJORAS_REPO.md`
