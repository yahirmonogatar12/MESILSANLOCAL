<?php
// Datos de usuarios (en producción, usa una base de datos)
$usuarios = [
    'admin' => [
        'contrasena' => '$2y$10$hashedPassword...', // Contraseña hasheada con password_hash()
        'area' => 'Materiales'
    ],
    'produccion' => [
        'contrasena' => '$2y$10$hashedPassword...',
        'area' => 'Producción'
    ],
    'calidad' => [
        'contrasena' => '$2y$10$hashedPassword...',
        'area' => 'Calidad'
    ]
];

// Generar hashes (ejecutar una vez y guardar el resultado):
// echo password_hash('tu_contraseña', PASSWORD_BCRYPT);
?>