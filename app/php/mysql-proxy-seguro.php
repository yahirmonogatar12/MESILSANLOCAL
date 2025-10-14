<?php
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, GET, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization');

// Handle preflight OPTIONS request
if ($_SERVER['REQUEST_METHOD'] == 'OPTIONS') {
    http_response_code(200);
    exit();
}

// Database configuration - Usa variables de entorno en producción
$host = getenv('MYSQL_HOST') ?: 'up-de-fra1-mysql-1.db.run-on-seenode.com';
$port = getenv('MYSQL_PORT') ?: 11550;
$database = getenv('MYSQL_DATABASE') ?: 'db_rrpq0erbdujn';
$username = getenv('MYSQL_USER') ?: 'db_rrpq0erbdujn';
$password = getenv('MYSQL_PASSWORD') ?: '';

// Security: API Key (opcional - descomenta para usar)
// $required_api_key = getenv('PROXY_API_KEY') ?: 'tu_api_key_secreta_aqui';

// Security: Tablas permitidas
$allowed_tables = [
    'materiales', 'inventario', 'movimientos_inventario', 'bom',
    'control_material_almacen', 'control_material_produccion', 
    'control_calidad', 'usuarios', 'work_orders', 'embarques',
    'InventarioRollosSMD', 'InventarioRollosIMD', 'InventarioRollosMAIN'
];

function validateQuery($sql) {
    global $allowed_tables;
    
    // Convertir a minúsculas para validación
    $sql_lower = strtolower($sql);
    
    // Prohibir operaciones peligrosas
    $dangerous_operations = ['drop', 'delete', 'truncate', 'alter', 'create'];
    foreach ($dangerous_operations as $op) {
        if (strpos($sql_lower, $op) !== false) {
            throw new Exception("Operación no permitida: $op");
        }
    }
    
    // Validar que solo se acceda a tablas permitidas
    foreach ($allowed_tables as $table) {
        if (strpos($sql_lower, $table) !== false) {
            return true;
        }
    }
    
    throw new Exception("Acceso a tabla no permitido");
}

try {
    // Verificar API Key (opcional)
    /*
    if (isset($required_api_key)) {
        $headers = getallheaders();
        if (!isset($headers['Authorization']) || $headers['Authorization'] !== 'Bearer ' . $required_api_key) {
            throw new Exception('API Key inválida o faltante');
        }
    }
    */

    // Create PDO connection
    $dsn = "mysql:host=$host;port=$port;dbname=$database;charset=utf8mb4";
    $pdo = new PDO($dsn, $username, $password, [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        PDO::MYSQL_ATTR_SSL_VERIFY_SERVER_CERT => false,
        PDO::ATTR_TIMEOUT => 30
    ]);

    // Get request data
    $input = json_decode(file_get_contents('php://input'), true);
    
    if (!$input || !isset($input['sql'])) {
        throw new Exception('SQL query is required');
    }

    $sql = $input['sql'];
    $params = isset($input['params']) ? $input['params'] : [];

    // Validar consulta
    validateQuery($sql);

    // Limitar resultados para SELECT
    if (stripos($sql, 'SELECT') === 0 && stripos($sql, 'LIMIT') === false) {
        $sql .= ' LIMIT 1000';
    }

    // Prepare and execute query
    $stmt = $pdo->prepare($sql);
    $stmt->execute($params);

    // Get results
    if (stripos($sql, 'SELECT') === 0 || stripos($sql, 'SHOW') === 0) {
        $data = $stmt->fetchAll();
        $response = [
            'success' => true,
            'data' => $data,
            'count' => count($data)
        ];
    } else {
        $affected = $stmt->rowCount();
        $response = [
            'success' => true,
            'affected_rows' => $affected,
            'data' => []
        ];
    }

    // Return success response
    echo json_encode($response);

} catch (PDOException $e) {
    // Log database errors
    error_log("Database Error: " . $e->getMessage());
    
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'error' => 'Error de base de datos',
        'details' => $e->getMessage()
    ]);
    
} catch (Exception $e) {
    // Log general errors
    error_log("API Error: " . $e->getMessage());
    
    http_response_code(400);
    echo json_encode([
        'success' => false,
        'error' => $e->getMessage()
    ]);
}
?>
