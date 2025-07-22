import sqlite3
import bcrypt

def verificar_password(username, password):
    conn = sqlite3.connect('app/database/ISEMM_MES.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT password_hash FROM usuarios_sistema WHERE username = ?', (username,))
    result = cursor.fetchone()
    
    if result:
        password_hash = result[0]
        if bcrypt.checkpw(password.encode('utf-8'), password_hash):
            print(f"{username}/{password}: ✓ VÁLIDO")
            return True
        else:
            print(f"{username}/{password}: ✗ INVÁLIDO")
            return False
    else:
        print(f"{username}: No encontrado")
        return False

# Probar diferentes combinaciones
usuarios = ['Jesus', 'admin', 'Yahir']
passwords = ['123', 'admin', 'admin123', 'password']

for usuario in usuarios:
    print(f"\nProbando usuario: {usuario}")
    for password in passwords:
        verificar_password(usuario, password)
