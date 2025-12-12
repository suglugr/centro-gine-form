<?php
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

require_once 'db_config.php';

if (!isset($_GET['id'])) {
    echo json_encode(['success' => false, 'message' => 'No ID provided']);
    exit;
}

$id = intval($_GET['id']);

$conn = getConnection();

$stmt = $conn->prepare("SELECT * FROM registros WHERE id = ?");
$stmt->bind_param("i", $id);
$stmt->execute();
$result = $stmt->get_result();

if ($result->num_rows > 0) {
    $record = $result->fetch_assoc();
    echo json_encode([
        'success' => true,
        'record' => $record
    ]);
} else {
    echo json_encode([
        'success' => false,
        'message' => 'Record not found'
    ]);
}

$stmt->close();
$conn->close();
?>