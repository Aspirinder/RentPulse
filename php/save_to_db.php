<?php

header('Content-Type: application/json; charset=utf-8');

include 'db.php';

$rawInput = file_get_contents('php://input');
$offer = json_decode($rawInput, true);

if (!$offer || !isset($offer['Link'])) {
    http_response_code(400);
    echo json_encode(['success' => false, 'message' => 'Empty data']);
    exit;
}

$id = $offer['generated_id'];

try{

    $checkStmt = $conn->prepare("SELECT 1 FROM `offers` WHERE `offer_id` = ?");
    $checkStmt->bind_param("s", $id);
    $checkStmt->execute();
    $checkStmt->store_result();
    
    if ($checkStmt->num_rows > 0) {
        $checkStmt->close();
        echo json_encode(['status' => 'exists', 'message' => 'Already in DB']);
        exit;
    }
    $checkStmt->close();

    $title = $offer['Title'] ?? 'No title';
    $price = $offer['Price'] ?? null;
    $description = $offer['Description'] ?? null;
    $source = $offer['source_site'] ?? 'unknown';
    $link = $offer['Link'];

    $offerStmt = $conn->prepare("INSERT INTO `offers` (`offer_id`, `link`, `title`, `price`, `description`, `source`) 
    VALUES (?, ?, ?, ?, ?, ?)");

    $offerStmt->bind_param("ssssss", $id, $link, $title, $price, $description, $source);

    if (!$offerStmt->execute()) {
        http_response_code(500);
        echo json_encode(['status' => 'error', 'message' => 'Failed to save offer: ' . $offerStmt->error]);
        $offerStmt->close();
        exit;
    }
    $offerStmt->close();

    if (isset($offer['Images']) && is_array($offer['Images'])) {
        $imgStmt = $conn->prepare("INSERT INTO `offer_images` (`offer_id`, `image_url`) VALUES (?, ?)");
    
        foreach ($offer['Images'] as $imageUrl) {
            if (!empty($imageUrl)) {
                $imgStmt->bind_param("ss", $id, $imageUrl);
                $imgStmt->execute();
            }
        }
        $imgStmt->close();
    }

    echo json_encode(['status' => 'success', 'message' => 'Success save!']);

}catch(Exception $e){
    http_response_code(500);
    echo json_encode(['status' => 'error', 'message' => 'DB eror: ' . $e->getMessage()]);
}
?>