<?php
$data = json_decode(file_get_contents('php://input'), true);
if (isset($data['image'])) {
    $img = str_replace('data:image/jpeg;base64,', '', $data['image']);
    $img = str_replace(' ', '+', $img);
    $binaryData = base64_decode($img);
    
    // Ensure this directory exists in your XAMPP folder
    $dir = 'patient_media/';
    if (!file_exists($dir)) { mkdir($dir, 0777, true); }
    
    $filename = 'CAM_' . date("YmdHis") . '.jpg';
    file_put_contents($dir . $filename, $binaryData);
    
    echo json_encode(["status" => "success", "filename" => $filename]);
}
?>