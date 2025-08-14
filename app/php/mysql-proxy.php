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

// Database configuration - Credenciales actualizadas
$host = 'up-de-fra1-mysql-1.db.run-on-seenode.com';
$port = 11550;
$database = 'db_rrpq0erbdujn';
$username = 'db_rrpq0erbdujn';
$password = '5fUNbSRcPP3LN9K2I33Pr0ge';

try {
    // Create PDO connection
    $dsn = "mysql:host=$host;port=$port;dbname=$database;charset=utf8mb4";
    $pdo = new PDO($dsn, $username, $password, [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        PDO::MYSQL_ATTR_SSL_VERIFY_SERVER_CERT => false
    ]);

    // Get request data
    $input = json_decode(file_get_contents('php://input'), true);
    
    if (!$input || !isset($input['sql'])) {
        throw new Exception('SQL query is required');
    }

    $sql = $input['sql'];
    $params = isset($input['params']) ? $input['params'] : [];

    // Prepare and execute query
    $stmt = $pdo->prepare($sql);
    $stmt->execute($params);

    // Get results
    if (stripos($sql, 'SELECT') === 0 || stripos($sql, 'SHOW') === 0) {
        $data = $stmt->fetchAll();
    } else {
        $data = ['affected_rows' => $stmt->rowCount()];
    }

    // Return success response
    echo json_encode([
        'success' => true,
        'data' => $data
    ]);

} catch (Exception $e) {
    // Return error response
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'error' => $e->getMessage()
    ]);
}
?>
