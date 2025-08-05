#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Probar formateo de fechas y horas SMT
"""

def format_scan_date(scan_date):
    """Convertir ScanDate de YYYYMMDD a YYYY-MM-DD"""
    if scan_date and len(str(scan_date)) == 8:
        date_str = str(scan_date)
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
    return scan_date

def format_scan_time(scan_time):
    """Convertir ScanTime de HHMMSS a HH:MM:SS"""
    if scan_time:
        time_str = str(scan_time).zfill(6)  # Asegurar 6 dígitos
        return f"{time_str[:2]}:{time_str[2:4]}:{time_str[4:6]}"
    return scan_time

def test_formatting():
    """Probar formatos"""
    
    # Casos de prueba para fechas
    test_dates = [20250805, '20250805', 20241225, '20241225']
    
    print("🗓️ Pruebas de formato de fecha:")
    for date in test_dates:
        formatted = format_scan_date(date)
        print(f"  {date} -> {formatted}")
    
    # Casos de prueba para horas
    test_times = [143025, '143025', 91530, '91530', 1234, '1234']
    
    print("\n⏰ Pruebas de formato de hora:")
    for time in test_times:
        formatted = format_scan_time(time)
        print(f"  {time} -> {formatted}")

if __name__ == "__main__":
    print("🧪 Probando formateo de fechas y horas SMT\n")
    test_formatting()
    print("\n✅ Funciones de formateo probadas")
