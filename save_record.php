<?php
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST');
header('Access-Control-Allow-Headers: Content-Type');

require_once 'db_config.php';

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    echo json_encode(['success' => false, 'message' => 'Invalid request method']);
    exit;
}

$input = json_decode(file_get_contents('php://input'), true);

if (!$input) {
    echo json_encode(['success' => false, 'message' => 'Invalid input data']);
    exit;
}

$nombre = isset($input['nombre']) ? trim($input['nombre']) : '';
$fecha_nacimiento = isset($input['fecha_nacimiento']) ? trim($input['fecha_nacimiento']) : '';
$edad = isset($input['edad']) ? trim($input['edad']) : '';
$fecha_impresion = isset($input['fecha_impresion']) ? trim($input['fecha_impresion']) : '';
$indicaciones = isset($input['indicaciones']) ? trim($input['indicaciones']) : '';
$notas = isset($input['notas']) ? trim($input['notas']) : '';

// Validation
if (empty($nombre) || empty($fecha_nacimiento) || empty($edad) || empty($fecha_impresion)) {
    echo json_encode(['success' => false, 'message' => 'Required fields are missing']);
    exit;
}

$conn = getConnection();

$stmt = $conn->prepare("INSERT INTO registros (nombre, fecha_nacimiento, edad, fecha_impresion, indicaciones, notas) VALUES (?, ?, ?, ?, ?, ?)");
$stmt->bind_param("ssisss", $nombre, $fecha_nacimiento, $edad, $fecha_impresion, $indicaciones, $notas);

if ($stmt->execute()) {
    echo json_encode([
        'success' => true,
        'message' => 'Record saved successfully',
        'id' => $conn->insert_id
    ]);
} else {
    echo json_encode([
        'success' => false,
        'message' => 'Error saving record: ' . $stmt->error
    ]);
}

$stmt->close();
$conn->close();
?>