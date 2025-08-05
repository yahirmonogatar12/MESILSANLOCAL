#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para activar SMT Simple
"""

import os
import sys

def update_routes():
    """Actualizar archivo routes.py para incluir SMT simple"""
    routes_file = 'app/routes.py'
    
    try:
        # Leer archivo actual
        with open(routes_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verificar si ya está importado
        if 'smt_routes_simple' in content:
            print("✅ SMT Routes Simple ya está importado")
            return True
        
        # Agregar import y blueprint
        lines = content.split('\n')
        
        # Buscar donde agregar
        insert_pos = -1
        for i, line in enumerate(lines):
            if 'app.register_blueprint' in line or 'if __name__' in line:
                insert_pos = i
                break
        
        if insert_pos == -1:
            # Agregar al final
            lines.append('')
            lines.append('# SMT Routes Simple')
            lines.append('try:')
            lines.append('    from .smt_routes_simple import smt_bp')
            lines.append('    app.register_blueprint(smt_bp)')
            lines.append('    print("✅ SMT Routes Simple registradas")')
            lines.append('except Exception as e:')
            lines.append('    print(f"❌ Error importando SMT Routes Simple: {e}")')
            lines.append('')
            lines.append('@app.route("/smt-simple")')
            lines.append('def smt_simple():')
            lines.append('    """Página SMT simple sin filtros complicados"""')
            lines.append('    return render_template("smt_simple.html")')
        else:
            # Insertar antes de la línea encontrada
            new_lines = []
            new_lines.append('')
            new_lines.append('# SMT Routes Simple')
            new_lines.append('try:')
            new_lines.append('    from .smt_routes_simple import smt_bp')
            new_lines.append('    app.register_blueprint(smt_bp)')
            new_lines.append('    print("✅ SMT Routes Simple registradas")')
            new_lines.append('except Exception as e:')
            new_lines.append('    print(f"❌ Error importando SMT Routes Simple: {e}")')
            new_lines.append('')
            new_lines.append('@app.route("/smt-simple")')
            new_lines.append('def smt_simple():')
            new_lines.append('    """Página SMT simple sin filtros complicados"""')
            new_lines.append('    return render_template("smt_simple.html")')
            new_lines.append('')
            
            lines = lines[:insert_pos] + new_lines + lines[insert_pos:]
        
        # Escribir archivo actualizado
        with open(routes_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        print(f"✅ {routes_file} actualizado")
        return True
        
    except Exception as e:
        print(f"❌ Error actualizando routes: {e}")
        return False

def main():
    print("🚀 Activando SMT Simple...")
    
    # Actualizar routes
    if update_routes():
        print("✅ Routes actualizado")
    else:
        print("❌ Error actualizando routes")
        return
    
    print("\n📋 Para usar SMT Simple:")
    print("1. Reinicia el servidor Flask")
    print("2. Ve a: http://127.0.0.1:5000/smt-simple")
    print("3. Haz clic en 'Recargar Datos'")
    print("\n🎉 SMT Simple activado exitosamente!")

if __name__ == "__main__":
    main()
