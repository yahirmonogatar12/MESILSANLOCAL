#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para verificar la estructura de la base de datos
"""

import sqlite3

def verificar_estructura():
    """Verificar estructura de las tablas de permisos"""
    conn = sqlite3.connect('app/database/ISEMM_MES.db')
    cursor = conn.cursor()
    
    print("=== ESTRUCTURA DE permisos_botones ===")
    cursor.execute("PRAGMA table_info(permisos_botones)")
    columnas = cursor.fetchall()
    for columna in columnas:
        print(f"Columna: {columna[1]}, Tipo: {columna[2]}")
    
    print("\n=== ESTRUCTURA DE rol_permisos_botones ===")
    cursor.execute("PRAGMA table_info(rol_permisos_botones)")
    columnas = cursor.fetchall()
    for columna in columnas:
        print(f"Columna: {columna[1]}, Tipo: {columna[2]}")
    
    print("\n=== CONTENIDO DE permisos_botones ===")
    cursor.execute("SELECT * FROM permisos_botones LIMIT 10")
    registros = cursor.fetchall()
    for registro in registros:
        print(registro)
    
    conn.close()

if __name__ == "__main__":
    verificar_estructura()
