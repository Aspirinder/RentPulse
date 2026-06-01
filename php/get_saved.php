<?php
// Inform the browser that the response will be strictly in UTF-8 JSON format
header('Content-Type: application/json; charset=utf-8');
// Enable Cross-Origin Resource Sharing (CORS) for external frontend testing
header('Access-Control-Allow-Origin: *');

// Include the database connection credentials and initialization script
include 'db.php'; 

try {
    // Execute SQL query to select specific offer metadata ordered by latest additions
    $stmt = $conn->query("SELECT title, price, link FROM offers ORDER BY offer_id DESC");
    
    // Extract the records from the statement resource object as an associative array
    // (This guarantees rows map to object property strings like offer.title on frontend)
    $savedOffers = $stmt->fetch_all(MYSQLI_ASSOC);

    // Encode the PHP dataset array into a valid JSON string structure and return it
    // Added JSON_UNESCAPED_UNICODE parameter to preserve Polish characters natively (e.g., ł, ż, ś)
    echo json_encode($savedOffers, JSON_UNESCAPED_UNICODE);

} catch (Exception $e) {
    // Set HTTP response status code to 500 Internal Server Error
    http_response_code(500);
    
    // Output the error trace message structure to aid in debugging operations
    echo json_encode([
        'success' => false,
        'message' => 'DB Error: ' . $e->getMessage()
    ], JSON_UNESCAPED_UNICODE);
}