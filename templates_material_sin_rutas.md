# Templates de Control de Material sin Rutas AJAX

## Templates AJAX existentes en Control de material/:

### Templates que YA TIENEN rutas:
1. `historial_cambio_material_smt_ajax.html` → `/historial-cambio-material-smt-ajax`
2. `historial_cambio_material_maquina_ajax.html` → `/historial-cambio-material-maquina-ajax`
3. `line_material_status_es_ajax.html` → `/line-material-status-ajax` (en Control de produccion)
4. `CONTROL_DE_MATERIAL.html` → `/informacion_basica/control_de_material` (en INFORMACION BASICA)

### Templates que NECESITAN rutas (16 templates):
1. `ajuste_numero_parte_ajax.html`
2. `consultar_peps_ajax.html`
3. `control_almacen_ajax.html`
4. `control_entrada_salida_material_ajax.html`
5. `control_recibo_refacciones_ajax.html`
6. `control_retorno_ajax.html`
7. `control_salida_ajax.html`
8. `control_salida_refacciones_ajax.html`
9. `control_total_material_ajax.html`
10. `estandares_refacciones_ajax.html`
11. `estatus_inventario_refacciones_ajax.html`
12. `estatus_material_ajax.html`
13. `estatus_material_msl_ajax.html`
14. `historial_inventario_real_ajax.html`
15. `historial_material_ajax.html`
16. `inventario_rollos_smd_ajax.html`
17. `longterm_inventory_ajax.html`
18. `material_sustituto_ajax.html`
19. `recibo_pago_material_ajax.html`
20. `registro_material_real_ajax.html`

**NOTA**: Son 20 templates sin rutas, no 16 como se estimó inicialmente.

## Rutas AJAX a implementar:

```python
# Control de Material - Rutas AJAX faltantes

@app.route('/ajuste-numero-parte-ajax')
@login_requerido
def ajuste_numero_parte_ajax():
    """Template para Ajuste de número de parte"""
    return render_template('Control de material/ajuste_numero_parte_ajax.html')

@app.route('/consultar-peps-ajax')
@login_requerido
def consultar_peps_ajax():
    """Template para Consultar PEPS"""
    return render_template('Control de material/consultar_peps_ajax.html')

@app.route('/control-almacen-ajax')
@login_requerido
def control_almacen_ajax():
    """Template para Control de almacén"""
    return render_template('Control de material/control_almacen_ajax.html')

@app.route('/control-entrada-salida-material-ajax')
@login_requerido
def control_entrada_salida_material_ajax():
    """Template para Control de entrada y salida de material"""
    return render_template('Control de material/control_entrada_salida_material_ajax.html')

@app.route('/control-recibo-refacciones-ajax')
@login_requerido
def control_recibo_refacciones_ajax():
    """Template para Control de recibo de refacciones"""
    return render_template('Control de material/control_recibo_refacciones_ajax.html')

@app.route('/control-retorno-ajax')
@login_requerido
def control_retorno_ajax():
    """Template para Control de retorno"""
    return render_template('Control de material/control_retorno_ajax.html')

@app.route('/control-salida-ajax')
@login_requerido
def control_salida_ajax():
    """Template para Control de salida"""
    return render_template('Control de material/control_salida_ajax.html')

@app.route('/control-salida-refacciones-ajax')
@login_requerido
def control_salida_refacciones_ajax():
    """Template para Control de salida de refacciones"""
    return render_template('Control de material/control_salida_refacciones_ajax.html')

@app.route('/control-total-material-ajax')
@login_requerido
def control_total_material_ajax():
    """Template para Control total de material"""
    return render_template('Control de material/control_total_material_ajax.html')

@app.route('/estandares-refacciones-ajax')
@login_requerido
def estandares_refacciones_ajax():
    """Template para Estándares de refacciones"""
    return render_template('Control de material/estandares_refacciones_ajax.html')

@app.route('/estatus-inventario-refacciones-ajax')
@login_requerido
def estatus_inventario_refacciones_ajax():
    """Template para Estatus de inventario de refacciones"""
    return render_template('Control de material/estatus_inventario_refacciones_ajax.html')

@app.route('/estatus-material-ajax')
@login_requerido
def estatus_material_ajax():
    """Template para Estatus de material"""
    return render_template('Control de material/estatus_material_ajax.html')

@app.route('/estatus-material-msl-ajax')
@login_requerido
def estatus_material_msl_ajax():
    """Template para Estatus de material MSL"""
    return render_template('Control de material/estatus_material_msl_ajax.html')

@app.route('/historial-inventario-real-ajax')
@login_requerido
def historial_inventario_real_ajax():
    """Template para Historial de inventario real"""
    return render_template('Control de material/historial_inventario_real_ajax.html')

@app.route('/historial-material-ajax')
@login_requerido
def historial_material_ajax():
    """Template para Historial de material"""
    return render_template('Control de material/historial_material_ajax.html')

@app.route('/inventario-rollos-smd-ajax')
@login_requerido
def inventario_rollos_smd_ajax():
    """Template para Inventario de rollos SMD"""
    return render_template('Control de material/inventario_rollos_smd_ajax.html')

@app.route('/longterm-inventory-ajax')
@login_requerido
def longterm_inventory_ajax():
    """Template para Inventario a largo plazo"""
    return render_template('Control de material/longterm_inventory_ajax.html')

@app.route('/material-sustituto-ajax')
@login_requerido
def material_sustituto_ajax():
    """Template para Material sustituto"""
    return render_template('Control de material/material_sustituto_ajax.html')

@app.route('/recibo-pago-material-ajax')
@login_requerido
def recibo_pago_material_ajax():
    """Template para Recibo y pago de material"""
    return render_template('Control de material/recibo_pago_material_ajax.html')

@app.route('/registro-material-real-ajax')
@login_requerido
def registro_material_real_ajax():
    """Template para Registro de material real"""
    return render_template('Control de material/registro_material_real_ajax.html')
```