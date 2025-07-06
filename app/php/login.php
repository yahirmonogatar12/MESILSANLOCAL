<?php
error_reporting(E_ALL);
ini_set('display_errors', 1);

header('Content-Type: application/json');

try {
session_start();
require_once '../includes/auth.php';

header('Content-Type: application/json');

$user = $_POST['username'] ?? '';
$pass = $_POST['password'] ?? '';

if (empty($user) || empty($pass)) {
    echo json_encode(['success' => false, 'message' => 'Usuario y contraseña requeridos']);
    exit;
}

// Verificar usuario
if (isset($usuarios[$user]) {
    if (password_verify($pass, $usuarios[$user]['contrasena'])) {
        $_SESSION['usuario'] = $user;
        $_SESSION['area'] = $usuarios[$user]['area'];
        
        echo json_encode([
            'success' => true,
            'redirect' => $usuarios[$user]['area'] . 'Template.html'
        ]);
        exit;
    }
}

echo json_encode(['success' => false, 'message' => 'Credenciales incorrectas']);
} catch (Exception $e) {
    echo json_encode(['success' => false, 'message' => 'Error: ' . $e->getMessage()]);
}
?>
