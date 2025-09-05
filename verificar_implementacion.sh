#!/bin/bash
# Script de verificación para la implementación AJAX de Control de modelos

echo "=== VERIFICACIÓN DE IMPLEMENTACIÓN AJAX - CONTROL DE MODELOS ==="
echo ""

# Verificar que el contenedor existe en MaterialTemplate.html
echo "1. Verificando contenedor en MaterialTemplate.html..."
if grep -q "control-modelos-visor-unique-container" "app/templates/MaterialTemplate.html"; then
    echo "   ✅ Contenedor 'control-modelos-visor-unique-container' encontrado"
else
    echo "   ❌ Contenedor no encontrado"
fi

# Verificar que la función AJAX existe en scriptMain.js
echo "2. Verificando función AJAX en scriptMain.js..."
if grep -q "mostrarControlModelosVisor" "app/static/js/scriptMain.js"; then
    echo "   ✅ Función 'mostrarControlModelosVisor' encontrada"
else
    echo "   ❌ Función AJAX no encontrada"
fi

# Verificar que la ruta existe en routes.py
echo "3. Verificando ruta AJAX en routes.py..."
if grep -q "/control-modelos-visor-ajax" "app/routes.py"; then
    echo "   ✅ Ruta '/control-modelos-visor-ajax' encontrada"
else
    echo "   ❌ Ruta AJAX no encontrada"
fi

# Verificar que el template AJAX existe
echo "4. Verificando template AJAX..."
if [ -f "app/templates/INFORMACION BASICA/control_modelos_visor_ajax.html" ]; then
    echo "   ✅ Template 'control_modelos_visor_ajax.html' encontrado"
else
    echo "   ❌ Template AJAX no encontrado"
fi

# Verificar que el botón está actualizado en la lista
echo "5. Verificando botón en lista..."
if grep -q "mostrarControlModelosVisor" "app/templates/LISTAS/LISTA_INFORMACIONBASICA.html"; then
    echo "   ✅ Botón actualizado en LISTA_INFORMACIONBASICA.html"
else
    echo "   ❌ Botón no actualizado"
fi

# Verificar que el contenedor está incluido en hideAllMaterialContainers
echo "6. Verificando inclusión en hideAllMaterialContainers..."
if grep -q "control-modelos-visor-unique-container" "app/static/js/scriptMain.js"; then
    echo "   ✅ Contenedor incluido en hideAllMaterialContainers"
else
    echo "   ❌ Contenedor no incluido en función de ocultado"
fi

echo ""
echo "=== VERIFICACIÓN COMPLETADA ==="
echo ""
echo "PASOS PARA PROBAR:"
echo "1. Ejecutar el servidor Flask"
echo "2. Navegar a 'Información Básica'"
echo "3. Hacer clic en 'Control de modelos'"
echo "4. Verificar que se carga el visor MySQL"
echo ""
echo "PATRÓN IMPLEMENTADO:"
echo "- Contenedor único: control-modelos-visor-unique-container"
echo "- Sufijo único: -modelos-visor"
echo "- Función AJAX: mostrarControlModelosVisor()"
echo "- Ruta AJAX: /control-modelos-visor-ajax"
echo "- Template: control_modelos_visor_ajax.html"
