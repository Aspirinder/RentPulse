<?php
// Inform the client that the server returns format-compliant UTF-8 JSON
header('Content-Type: application/json; charset=utf-8');
// Enable Cross-Origin Resource Sharing (CORS) for smooth frontend communication
header('Access-Control-Allow-Origin: *');

// Include the active MySQLi connection instance ($conn)
include 'db.php';

// Read raw JSON data transmitted in the HTTP request body payload
$rawInput = file_get_contents('php://input');
// Decode the incoming raw JSON payload into an associative PHP array
$offer = json_decode($rawInput, true);

// Validation check: ensure the payload decoded successfully and contains a link
if (!$offer || !isset($offer['Link'])) {
    http_response_code(400);
    echo json_encode(['success' => false, 'message' => 'Empty data']);
    exit;
}

// Extract the pre-computed unique hash string acting as the primary identifier
$id = $offer['generated_id'];

try {
    // Prepare an efficient index check statement to see if this ID already exists
    $checkStmt = $conn->prepare("SELECT 1 FROM `offers` WHERE `offer_id` = ?");
    $checkStmt->bind_param("s", $id);
    $checkStmt->execute();
    $checkStmt->store_result();
    
    // If a row is matched, terminate execution and notify the client it is a duplicate
    if ($checkStmt->num_rows > 0) {
        $checkStmt->close();
        echo json_encode(['status' => 'exists', 'message' => 'Already in DB'], JSON_UNESCAPED_UNICODE);
        exit;
    }
    $checkStmt->close();

    /* ==========================================================================
       1. PRIMARY RECORD DATABASE INSERTION
       ========================================================================== */
    // Fallback definition parameters if incoming fields contain null values
    $title = $offer['Title'] ?? 'No title';
    $price = $offer['Price'] ?? null;
    $description = $offer['Description'] ?? null;
    $source = $offer['source_site'] ?? 'unknown';
    $link = $offer['Link'];

    // Construct the prepared query statement to write values to the core schema table
    $offerStmt = $conn->prepare("INSERT INTO `offers` (`offer_id`, `link`, `title`, `price`, `description`, `source`) 
    VALUES (?, ?, ?, ?, ?, ?)");

    // Bind parameters natively ensuring escaping sanitization layers execute perfectly
    $offerStmt->bind_param("ssssss", $id, $link, $title, $price, $description, $source);

    // Run execution logic check to evaluate physical system errors
    if (!$offerStmt->execute()) {
        http_response_code(500);
        echo json_encode(['status' => 'error', 'message' => 'Failed to save offer: ' . $offerStmt->error], JSON_UNESCAPED_UNICODE);
        $offerStmt->close();
        exit;
    }
    $offerStmt->close();

    /* ==========================================================================
       2. RELATED GALLERY ASSETS PROCESSING (ONE-TO-MANY RELATION)
       ========================================================================== */
    // Evaluate if specific array indexes exist and hold recursive array elements
    if (isset($offer['Images']) && is_array($offer['Images'])) {
        // Reuse a unique prepared statement descriptor resource to insert child image rows
        $imgStmt = $conn->prepare("INSERT INTO `offer_images` (`offer_id`, `image_url`) VALUES (?, ?)");
    
        // Loop through the image links collection to link URLs with the generated record ID
        foreach ($offer['Images'] as $imageUrl) {
            if (!empty($imageUrl)) {
                $imgStmt->bind_param("ss", $id, $imageUrl);
                $imgStmt->execute();
            }
        }
        $imgStmt->close();
    }

    // Success response delivery to the front-end interface listener
    echo json_encode(['status' => 'success', 'message' => 'Success save!'], JSON_UNESCAPED_UNICODE);

} catch (Exception $e) {
    http_response_code(500);
    echo json_encode([
        'status' => 'error', 
        'message' => 'DB error: ' . $e->getMessage()
    ], JSON_UNESCAPED_UNICODE);
}
?>