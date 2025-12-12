<?php
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

require_once 'db_config.php';

$conn = getConnection();

$sql = "SELECT id, nombre, fecha_nacimiento, edad, fecha_impresion, indicaciones, notas, created_at FROM registros ORDER BY created_at DESC";
$result = $conn->query($sql);

$records = [];
if ($result->num_rows > 0) {
    while ($row = $result->fetch_assoc()) {
        $records[] = $row;
    }
}

echo json_encode([
    'success' => true,
    'records' => $records
]);

$conn->close();
?>