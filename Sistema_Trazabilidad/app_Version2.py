import os
import json
import re
from flask import Flask, request, jsonify, render_template
from datetime import datetime

app = Flask(__name__)

APP_DIR = os.path.dirname(os.path.abspath(__file__))
RULES_FILE = os.path.join(APP_DIR, 'rules.json')
LOG_FILE = os.path.join(APP_DIR, 'log.json')

def apply_rule(text, rule):
    try:
        # Nuevo sistema de reconocimiento por secuencias
        if 'sequence_pattern' in rule:
            return apply_sequence_rule(text, rule)
        # Sistema de reconocimiento carácter por carácter
        elif 'character_pattern' in rule:
            return apply_character_rule(text, rule)
        else:
            # Mantener compatibilidad con reglas antiguas de regex
            match = re.search(rule['pattern'], text)
            if not match: return None
            part_number = match.group(rule['partNumberIndex']).strip()
            
            # Verificar si hay índice de lote válido
            lot_number_index = rule.get('lotNumberIndex', -1)
            if lot_number_index != -1 and lot_number_index <= len(match.groups()):
                lot_number = match.group(lot_number_index).strip()
            else:
                lot_number = ''  # Sin lote
                
            return {'partNumber': part_number, 'lotNumber': lot_number}
    except Exception as e:
        print(f"Error aplicando regla para el texto '{text}' con el patrón '{rule.get('pattern', rule.get('character_pattern', rule.get('sequence_pattern', '')))}': {e}")
        return None

def apply_sequence_rule(text, rule):
    """
    Aplica reglas basadas en secuencias de separadores (espacios, tabs, etc.)
    """
    try:
        sequences = rule['sequence_pattern']
        
        # Dividir el texto según las secuencias definidas
        parts = [text]
        current_position = 0
        
        for i, sequence in enumerate(sequences):
            new_parts = []
            for part in parts:
                if sequence['type'] == 'spaces':
                    # Buscar la cantidad exacta de espacios consecutivos
                    space_pattern = ' ' * sequence['count']
                    split_parts = part.split(space_pattern, 1)  # Solo dividir en la primera ocurrencia
                    new_parts.extend(split_parts)
                elif sequence['type'] == 'tabs':
                    # Buscar tabs
                    tab_pattern = '\t' * sequence['count']
                    split_parts = part.split(tab_pattern, 1)
                    new_parts.extend(split_parts)
                elif sequence['type'] == 'newlines':
                    # Buscar saltos de línea
                    newline_pattern = '\n' * sequence['count']
                    split_parts = part.split(newline_pattern, 1)
                    new_parts.extend(split_parts)
                elif sequence['type'] == 'custom':
                    # Separador personalizado
                    custom_pattern = sequence['separator'] * sequence['count']
                    split_parts = part.split(custom_pattern, 1)
                    new_parts.extend(split_parts)
                else:
                    new_parts.append(part)
            parts = new_parts
        
        # Extraer número de parte y lote según los índices definidos
        part_number_index = rule['partNumberIndex']
        lot_number_index = rule['lotNumberIndex']
        
        if len(parts) <= max(part_number_index, lot_number_index):
            return None
            
        part_number = parts[part_number_index].strip()
        lot_number = parts[lot_number_index].strip()
        
        # Aplicar longitudes máximas si están definidas
        if 'partNumberMaxLength' in rule:
            part_number = part_number[:rule['partNumberMaxLength']]
        if 'lotNumberMaxLength' in rule:
            lot_number = lot_number[:rule['lotNumberMaxLength']]
        
        # *** NUEVA FUNCIONALIDAD: Extracción específica del lote ***
        if 'lotNumberStart' in rule and 'lotNumberLength' in rule:
            start_pos = rule['lotNumberStart']
            length = rule['lotNumberLength']
            
            print(f"🎯 Aplicando extracción específica del lote:")
            print(f"- Lote original: '{lot_number}'")
            print(f"- Posición inicio: {start_pos}")
            print(f"- Longitud: {length}")
            print(f"- Lote original length: {len(lot_number)}")
            
            if len(lot_number) >= start_pos + length:
                lot_number = lot_number[start_pos:start_pos + length].strip()
                print(f"- Lote extraído: '{lot_number}'")
            else:
                print(f"❌ Lote muy corto para extracción específica")
        
        return {'partNumber': part_number, 'lotNumber': lot_number}
        
    except Exception as e:
        print(f"Error en reconocimiento por secuencias: {e}")
        return None

def apply_character_rule(text, rule):
    """
    Aplica reglas basadas en reconocimiento carácter por carácter
    """
    try:
        char_pattern = rule['character_pattern']
        part_number_start = rule['partNumberStart']
        part_number_length = rule['partNumberLength']
        lot_number_start = rule.get('lotNumberStart', -1)
        lot_number_length = rule.get('lotNumberLength', 0)
        
        # Verificar que el texto tenga la longitud mínima esperada
        min_length = part_number_start + part_number_length
        if lot_number_start != -1:
            min_length = max(min_length, lot_number_start + lot_number_length)
        
        if len(text) < min_length:
            return None
        
        # Verificar patrón carácter por carácter
        if len(text) != len(char_pattern):
            return None
            
        for i, (char_text, char_pattern) in enumerate(zip(text, char_pattern)):
            if char_pattern == 'X':  # X = cualquier carácter
                continue
            elif char_pattern == 'N':  # N = cualquier número
                if not char_text.isdigit():
                    return None
            elif char_pattern == 'A':  # A = cualquier letra
                if not char_text.isalpha():
                    return None
            elif char_pattern == 'AN':  # AN = alfanumérico
                if not char_text.isalnum():
                    return None
            else:  # Carácter específico debe coincidir exactamente
                if char_text != char_pattern:
                    return None
        
        # Extraer número de parte
        part_number = text[part_number_start:part_number_start + part_number_length].strip()
        
        # Extraer número de lote solo si está definido
        if lot_number_start != -1 and lot_number_length > 0:
            lot_number = text[lot_number_start:lot_number_start + lot_number_length].strip()
        else:
            lot_number = ''  # Sin lote
        
        return {'partNumber': part_number, 'lotNumber': lot_number}
        
    except Exception as e:
        print(f"Error en reconocimiento carácter por carácter: {e}")
        return None

def read_json_file(file_path, default_data):
    if not os.path.exists(file_path):
        with open(file_path, 'w') as f: json.dump(default_data, f, indent=4)
        return default_data
    try:
        with open(file_path, 'r') as f: return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return default_data

def write_json_file(file_path, data):
    try:
        with open(file_path, 'w') as f: json.dump(data, f, indent=4)
        return True
    except Exception as e:
        print(f"ERROR al escribir en {file_path}: {e}")
        return False

@app.route('/api/process_scan', methods=['POST'])
def process_scan_endpoint():
    text = request.json['text']
    rules = read_json_file(RULES_FILE, {})
    for supplier, rule in rules.items():
        result = apply_rule(text, rule)
        if result:
            return jsonify({'status': 'success', 'supplier': supplier, 'data': result})
    return jsonify({'status': 'new_rule_needed', 'text': text})

@app.route('/api/save_rule', methods=['POST'])
def save_rule_endpoint():
    data = request.json
    supplier = data.get('supplier', '').upper()
    full_text = data.get('fullText')
    part_number_text = data.get('partNumber')
    lot_number_text = data.get('lotNumber', '')  # Permitir lote vacío
    use_character_mode = data.get('characterMode', True)  # Por defecto usar modo carácter

    # Validar que al menos tengamos supplier, full_text y part_number
    if not all([supplier, full_text, part_number_text]):
        return jsonify({'status': 'error', 'message': 'Faltan datos para crear la regla (supplier, fullText, partNumber son requeridos)'}), 400

    pn_start = full_text.find(part_number_text)
    
    # Si no hay lote, establecer valores por defecto
    if not lot_number_text.strip():
        lot_start = -1
        lot_number_text = ''
    else:
        lot_start = full_text.find(lot_number_text)
        if lot_start == -1:
            return jsonify({'status': 'error', 'message': 'El número de lote seleccionado no se encontró en el texto original.'}), 400

    if pn_start == -1:
        return jsonify({'status': 'error', 'message': 'El número de parte seleccionado no se encontró en el texto original.'}), 400

    if use_character_mode:
        # Nuevo sistema: reconocimiento carácter por carácter
        character_pattern = create_character_pattern(full_text, part_number_text, lot_number_text, pn_start, lot_start)
        
        new_rule = {
            'character_pattern': character_pattern,
            'partNumberStart': pn_start,
            'partNumberLength': len(part_number_text)
        }
        
        # Solo agregar información del lote si existe
        if lot_number_text.strip() and lot_start != -1:
            new_rule['lotNumberStart'] = lot_start
            new_rule['lotNumberLength'] = len(lot_number_text)
        else:
            # Marcar que no hay lote
            new_rule['lotNumberStart'] = -1
            new_rule['lotNumberLength'] = 0
        
        rules = read_json_file(RULES_FILE, {})
        rules[supplier] = new_rule
        write_json_file(RULES_FILE, rules)
        return jsonify({'status': 'success', 'message': f'Regla carácter por carácter para {supplier} guardada ({"con lote" if lot_number_text.strip() else "sin lote"}).'})
    
    else:
        # Sistema antiguo (regex flexible) para compatibilidad
        if not lot_number_text.strip():
            # Si no hay lote, crear regla solo para número de parte
            prefix = full_text[0:pn_start]
            suffix = full_text[pn_start + len(part_number_text):]
            
            pattern = (f"^{re.escape(prefix)}"
                       f"(.+?)"
                       f"{re.escape(suffix)}$")

            new_rule = {
                'pattern': pattern,
                'partNumberIndex': 1,
                'lotNumberIndex': -1  # Indicar que no hay lote
            }
        else:
            # Lógica original para cuando hay lote
            if pn_start < lot_start:
                first_sel, second_sel = part_number_text, lot_number_text
                part_number_index, lot_number_index = 1, 2
            else:
                first_sel, second_sel = lot_number_text, part_number_text
                lot_number_index, part_number_index = 1, 2

            first_start = full_text.find(first_sel)
            first_end = first_start + len(first_sel)
            second_start = full_text.find(second_sel)
            second_end = second_start + len(second_sel)
            
            prefix = full_text[0:first_start]
            middle = full_text[first_end:second_start]
            suffix = full_text[second_end:]
            
            pattern = (f"^{re.escape(prefix)}"
                       f"(.+?)"
                       f"{re.escape(middle)}"
                       f"(.+?)"
                       f"{re.escape(suffix)}$")

            new_rule = {
                'pattern': pattern,
                'partNumberIndex': part_number_index,
                'lotNumberIndex': lot_number_index
            }

        rules = read_json_file(RULES_FILE, {})
        rules[supplier] = new_rule
        write_json_file(RULES_FILE, rules)
        return jsonify({'status': 'success', 'message': f'Regla de patrón flexible para {supplier} guardada ({"con lote" if lot_number_text.strip() else "sin lote"}).'})

def create_character_pattern(full_text, part_number_text, lot_number_text, pn_start, lot_start):
    """
    Crea un patrón carácter por carácter donde:
    - Caracteres específicos se mantienen como están
    - Números se marcan como 'N'
    - Letras se marcan como 'A'
    - Alfanuméricos se marcan como 'AN'
    - Las zonas de número de parte y lote se marcan como 'X' (cualquier carácter)
    """
    pattern = list(full_text)
    
    # Marcar la zona del número de parte como 'X' (cualquier carácter)
    for i in range(pn_start, pn_start + len(part_number_text)):
        pattern[i] = 'X'
    
    # Marcar la zona del lote como 'X' solo si existe lote
    if lot_number_text.strip() and lot_start != -1:
        for i in range(lot_start, lot_start + len(lot_number_text)):
            pattern[i] = 'X'
    
    # Para el resto de caracteres, determinar el tipo
    for i, char in enumerate(pattern):
        if char != 'X':  # Si no es una zona variable
            if char.isdigit():
                pattern[i] = 'N'  # Número específico
            elif char.isalpha():
                pattern[i] = 'A'  # Letra específica
            # Los caracteres especiales y espacios se mantienen como están
    
    return ''.join(pattern)

@app.route('/api/log', methods=['POST'])
def save_log_entry():
    data = request.json
    log_entry = {
        "proveedor": data.get('supplier'), "numero_parte": data.get('partNumber'), "lote": data.get('lotNumber'),
        "usuario": "yahirmonogatar12", "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    logs = read_json_file(LOG_FILE, [])
    logs.insert(0, log_entry)
    write_json_file(LOG_FILE, logs)
    return jsonify({'status': 'success'})

@app.route('/api/data', methods=['GET'])
def get_initial_data():
    rules = read_json_file(RULES_FILE, {})
    logs = read_json_file(LOG_FILE, [])
    return jsonify({'rules': rules, 'logs': logs})

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/save_character_rule', methods=['POST'])
def save_character_rule_endpoint():
    """
    Endpoint específico para crear reglas carácter por carácter
    """
    data = request.json
    supplier = data.get('supplier', '').upper()
    full_text = data.get('fullText')
    part_number_text = data.get('partNumber')
    lot_number_text = data.get('lotNumber', '')  # Permitir lote vacío

    # Validar que al menos tengamos supplier, full_text y part_number
    if not all([supplier, full_text, part_number_text]):
        return jsonify({'status': 'error', 'message': 'Faltan datos para crear la regla (supplier, fullText, partNumber son requeridos)'}), 400

    pn_start = full_text.find(part_number_text)
    
    # Si no hay lote, establecer valores por defecto
    if not lot_number_text.strip():
        lot_start = -1
        lot_number_text = ''
    else:
        lot_start = full_text.find(lot_number_text)
        if lot_start == -1:
            return jsonify({'status': 'error', 'message': 'El número de lote seleccionado no se encontró en el texto original.'}), 400

    if pn_start == -1:
        return jsonify({'status': 'error', 'message': 'El número de parte seleccionado no se encontró en el texto original.'}), 400

    # Crear patrón carácter por carácter
    character_pattern = create_character_pattern(full_text, part_number_text, lot_number_text, pn_start, lot_start)
    
    new_rule = {
        'character_pattern': character_pattern,
        'partNumberStart': pn_start,
        'partNumberLength': len(part_number_text),
        'example_text': full_text,  # Guardar ejemplo para referencia
        'creation_mode': 'character_by_character'
    }
    
    # Solo agregar información del lote si existe
    if lot_number_text.strip() and lot_start != -1:
        new_rule['lotNumberStart'] = lot_start
        new_rule['lotNumberLength'] = len(lot_number_text)
    else:
        new_rule['lotNumberStart'] = -1
        new_rule['lotNumberLength'] = 0
    
    rules = read_json_file(RULES_FILE, {})
    rules[supplier] = new_rule
    write_json_file(RULES_FILE, rules)
    
    return jsonify({
        'status': 'success', 
        'message': f'Regla carácter por carácter para {supplier} guardada ({"con lote" if lot_number_text.strip() else "sin lote"}).',
        'pattern': character_pattern,
        'details': {
            'pattern_length': len(character_pattern),
            'part_number_position': f'{pn_start}-{pn_start + len(part_number_text)}',
            'lot_number_position': f'{lot_start}-{lot_start + len(lot_number_text)}' if lot_start != -1 else 'No definido (sin lote)'
        }
    })

@app.route('/api/show_pattern/<supplier>', methods=['GET'])
def show_pattern(supplier):
    """
    Muestra el patrón de cualquier tipo de regla de un proveedor
    """
    rules = read_json_file(RULES_FILE, {})
    supplier = supplier.upper()
    
    if supplier not in rules:
        return jsonify({'status': 'error', 'message': f'No se encontró regla para {supplier}'}), 404
    
    rule = rules[supplier]
    
    if 'sequence_pattern' in rule:
        return jsonify({
            'status': 'success',
            'supplier': supplier,
            'sequences': rule['sequence_pattern'],
            'part_number_index': rule['partNumberIndex'],
            'lot_number_index': rule['lotNumberIndex'],
            'part_number_max_length': rule.get('partNumberMaxLength', 'Sin límite'),
            'lot_number_max_length': rule.get('lotNumberMaxLength', 'Sin límite'),
            'example': rule.get('example_text', 'No disponible'),
            'mode': 'sequence_based'
        })
    elif 'character_pattern' in rule:
        return jsonify({
            'status': 'success',
            'supplier': supplier,
            'pattern': rule['character_pattern'],
            'part_number_position': f"Posición {rule['partNumberStart']}-{rule['partNumberStart'] + rule['partNumberLength']}",
            'lot_number_position': f"Posición {rule['lotNumberStart']}-{rule['lotNumberStart'] + rule['lotNumberLength']}",
            'example': rule.get('example_text', 'No disponible'),
            'mode': 'character_by_character'
        })
    else:
        return jsonify({
            'status': 'success',
            'supplier': supplier,
            'pattern': rule['pattern'],
            'part_number_index': rule['partNumberIndex'],
            'lot_number_index': rule['lotNumberIndex'],
            'mode': 'regex_flexible'
        })

@app.route('/api/save_sequence_rule', methods=['POST'])
def save_sequence_rule_endpoint():
    """
    Endpoint específico para crear reglas basadas en secuencias de separadores
    Ejemplo de uso:
    {
        "supplier": "ROHM",
        "fullText": "ROHM  MCR50JZHJ181  0040002446102223HA05",
        "sequences": [
            {"type": "spaces", "count": 2}
        ],
        "partNumberIndex": 1,
        "lotNumberIndex": 2,
        "partNumberMaxLength": 15,
        "lotNumberMaxLength": 10
    }
    """
    data = request.json
    supplier = data.get('supplier', '').upper()
    full_text = data.get('fullText')
    sequences = data.get('sequences', [])
    part_number_index = data.get('partNumberIndex', 1)
    lot_number_index = data.get('lotNumberIndex', 2)
    part_number_max_length = data.get('partNumberMaxLength')
    lot_number_max_length = data.get('lotNumberMaxLength')

    if not all([supplier, full_text, sequences]):
        return jsonify({'status': 'error', 'message': 'Faltan datos para crear la regla (supplier, fullText, sequences)'}), 400

    # Validar las secuencias
    for seq in sequences:
        if 'type' not in seq or 'count' not in seq:
            return jsonify({'status': 'error', 'message': 'Cada secuencia debe tener "type" y "count"'}), 400
        if seq['type'] not in ['spaces', 'tabs', 'newlines', 'custom']:
            return jsonify({'status': 'error', 'message': 'Tipo de secuencia no válido. Use: spaces, tabs, newlines, custom'}), 400
        if seq['type'] == 'custom' and 'separator' not in seq:
            return jsonify({'status': 'error', 'message': 'Las secuencias "custom" requieren el campo "separator"'}), 400

    # Crear la nueva regla
    new_rule = {
        'sequence_pattern': sequences,
        'partNumberIndex': part_number_index,
        'lotNumberIndex': lot_number_index,
        'creation_mode': 'sequence_based',
        'example_text': full_text
    }
    
    # Añadir longitudes máximas si están definidas
    if part_number_max_length:
        new_rule['partNumberMaxLength'] = part_number_max_length
    if lot_number_max_length:
        new_rule['lotNumberMaxLength'] = lot_number_max_length
    
    # Probar la regla con el texto de ejemplo
    test_result = apply_sequence_rule(full_text, new_rule)
    if not test_result:
        return jsonify({'status': 'error', 'message': 'La regla creada no funciona con el texto de ejemplo'}), 400
    
    # Guardar la regla
    rules = read_json_file(RULES_FILE, {})
    rules[supplier] = new_rule
    write_json_file(RULES_FILE, rules)
    
    return jsonify({
        'status': 'success', 
        'message': f'Regla por secuencias para {supplier} guardada.',
        'test_result': test_result,
        'rule_details': {
            'sequences': sequences,
            'part_number_index': part_number_index,
            'lot_number_index': lot_number_index,
            'example_extracted': {
                'partNumber': test_result['partNumber'],
                'lotNumber': test_result['lotNumber']
            }
        }
    })

@app.route('/api/test_sequence', methods=['POST'])
def test_sequence_endpoint():
    """
    Endpoint para probar una secuencia antes de guardarla
    """
    data = request.json
    full_text = data.get('fullText')
    sequences = data.get('sequences', [])
    part_number_index = data.get('partNumberIndex', 1)
    lot_number_index = data.get('lotNumberIndex', 2)
    
    if not all([full_text, sequences]):
        return jsonify({'status': 'error', 'message': 'Faltan datos para probar (fullText, sequences)'}), 400
    
    # Crear regla temporal para prueba
    temp_rule = {
        'sequence_pattern': sequences,
        'partNumberIndex': part_number_index,
        'lotNumberIndex': lot_number_index
    }
    
    # Probar la regla
    result = apply_sequence_rule(full_text, temp_rule)
    
    if result:
        return jsonify({
            'status': 'success',
            'message': 'La secuencia funciona correctamente',
            'extracted': result,
            'preview': {
                'partNumber': result['partNumber'],
                'lotNumber': result['lotNumber']
            }
        })
    else:
        return jsonify({
            'status': 'error',
            'message': 'La secuencia no pudo extraer los datos del texto'
        })

@app.route('/api/sequence_examples', methods=['GET'])
def get_sequence_examples():
    """
    Devuelve ejemplos de diferentes tipos de secuencias disponibles
    """
    examples = {
        "espacios": {
            "description": "Separación por espacios consecutivos",
            "example_text": "ROHM  MCR50JZHJ181  0040002446102223HA05",
            "sequence": [{"type": "spaces", "count": 2}],
            "result": "Proveedor: ROHM, Parte: MCR50JZHJ181, Lote: 0040002446102223HA05"
        },
        "tabs": {
            "description": "Separación por tabulaciones",
            "example_text": "ROHM\tMCR50JZHJ181\t0040002446102223HA05",
            "sequence": [{"type": "tabs", "count": 1}],
            "result": "Proveedor: ROHM, Parte: MCR50JZHJ181, Lote: 0040002446102223HA05"
        },
        "saltos_linea": {
            "description": "Separación por saltos de línea",
            "example_text": "ROHM\nMCR50JZHJ181\n0040002446102223HA05",
            "sequence": [{"type": "newlines", "count": 1}],
            "result": "Proveedor: ROHM, Parte: MCR50JZHJ181, Lote: 0040002446102223HA05"
        },
        "separador_personalizado": {
            "description": "Separación por caracteres personalizados",
            "example_text": "ROHM||MCR50JZHJ181||0040002446102223HA05",
            "sequence": [{"type": "custom", "separator": "|", "count": 2}],
            "result": "Proveedor: ROHM, Parte: MCR50JZHJ181, Lote: 0040002446102223HA05"
        },
        "mixto": {
            "description": "Combinación de diferentes separadores",
            "example_text": "ROHM  MCR50JZHJ181\t0040002446102223HA05",
            "sequence": [
                {"type": "spaces", "count": 2},
                {"type": "tabs", "count": 1}
            ],
            "result": "Proveedor: ROHM, Parte: MCR50JZHJ181, Lote: 0040002446102223HA05"
        }
    }
    
    return jsonify({
        'status': 'success',
        'examples': examples,
        'usage_instructions': {
            'create_rule': 'Usar POST /api/save_sequence_rule',
            'test_rule': 'Usar POST /api/test_sequence',
            'required_fields': ['supplier', 'fullText', 'sequences'],
            'optional_fields': ['partNumberIndex', 'lotNumberIndex', 'partNumberMaxLength', 'lotNumberMaxLength']
        }
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)