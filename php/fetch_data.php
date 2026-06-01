<?php

// Specify that the response data is formatted as UTF-8 compliant JSON
header('Content-Type: application/json; charset=utf-8');
// Allow Cross-Origin Resource Sharing (CORS) for external client accessibility
header('Access-Control-Allow-Origin: *');


// Pull in the default Composer autoloader to resolve external package dependencies
require __DIR__ . '/../vendor/autoload.php';

try {
    // Attempt to parse the global environment parameters from the root directory
    $dotenv = Dotenv\Dotenv::createImmutable(dirname(__DIR__));
    $dotenv->load();
} catch (Exception $e) {
    // Terminate thread and return error state if the root configuration file is missing
    echo json_encode(['success' => false, 'message' => 'No .env configuration file detected.']);
    exit;
}

// Fetch the base target API Gateway URL from the active environment variables map
$baseApiUrl = $_ENV['AWS_API'] ?? null;

if (!$baseApiUrl) {
    echo json_encode(['success' => false, 'message' => 'No AWS_API parameters specified inside .env']);
    exit;
}

// Sanitize and extract incoming filtering metrics transmitted via HTTP GET request
$platformsInput = isset($_GET['platforms']) ? $_GET['platforms'] : ''; 
$combinedInput  = isset($_GET['combined']) ? $_GET['combined'] : 'false';

if (empty($platformsInput)) {
    echo json_encode(['status' => 'error', 'message' => 'No target execution platforms selected.']);
    exit;
}

// Explode the plain text platform string into an iterable array index collection
$platforms = explode(',', $platformsInput);

// Establish core configuration array map tracking structural parameters sent to AWS
$queryParams = [
    'combined' => $combinedInput,
    'page'     => 1 // Starts query loop at page index position 1
];

// Contextual fallback mapping evaluation:
// If only one platform checkbox is checked, explicitly set the query parameter key.
// If both platforms are active, do not declare a parameter, allowing AWS to merge records.
if (count($platforms) === 1) {
    if (in_array('olx.pl', $platforms)) {
        $queryParams['source'] = 'olx';
    } elseif (in_array('otodom.pl', $platforms)) {
        $queryParams['source'] = 'otodom';
    }
}

// Initialize internal application memory components
$allFinalOffers = []; // Master list holding all appended apartment datasets
$page = 1;            // Active pagination tracker variable

// Generate stream context configuration options ensuring proper network communication layers
$context = stream_context_create([
    'http' => [
        'timeout' => 10,                            // Safe termination script guard time (10 seconds max wait)
        'header'  => "Accept: application/json\r\n" // Declare strict explicit target parsing response type
    ]
]);

/* ==========================================================================
   1. MULTI-PAGE PAGINATION EXTRACTION LOOP (AWS API GATEWAY)
   ========================================================================== */
try {
    // Infinite loop runs indefinitely until breaking conditions are satisfied
    while (true) {
        // Overwrite the specific target pagination offset variable
        $queryParams['page'] = $page;

        // Formulate a completely clean external link query string
        $apiUrl = $baseApiUrl . "?" . http_build_query($queryParams);

        // Fetch contents from external cloud stream. Error warning outputs suppressed using '@' operator.
        $apiResponse = @file_get_contents($apiUrl, false, $context);

        // Breaking Condition 1: If the external link resource returns false, immediately end loop execution
        if ($apiResponse === false) { break; }

        // Decode the incoming plain text JSON content stream into native associative PHP indices
        $responseData = json_decode($apiResponse, true);

        // Breaking Condition 2: If the data array component is empty or undefined, all pages have been parsed
        if (!isset($responseData['data']) || !is_array($responseData['data']) || empty($responseData['data'])) {
            break; 
        }

        // Loop through the inner response block to map entries to client-side structures
        foreach ($responseData['data'] as $offer) {
            $allFinalOffers[] = [
                'generated_id' => $offer['generated_id'] ?? '',
                'Title'        => $offer['title'] ?? 'No title',
                'Price'        => $offer['price'] ?? 'No price',
                'Link'         => $offer['link'] ?? '#',
                'Images'       => $offer['images'] ?? [],
                'source_site'  => $offer['source_site'] ?? 'unknown',
                'is_combined'  => $offer['is_combined'] ?? false
            ];
        }

        // Increment the tracking variable pointer to request the next consecutive page block
        $page++;
        
        // Safety Break: Stop infinite data crawling if tracking index exceeds 20 pages
        if ($page > 20) { break; }
    }

    /* ==========================================================================
       2. OUTPUT RESPONSE GENERATION
       ========================================================================== */
    // Optional: add shuffle($allFinalOffers); right here if you want to mix olx and otodom results!
    
    // Convert finalized data array map into plain text JSON stream and echo to browser
    echo json_encode($allFinalOffers, JSON_UNESCAPED_UNICODE);

} catch (Exception $e) {
    // Append standard HTTP processing header status error code 500
    http_response_code(500);
    echo json_encode([
        'success' => false, 
        'message' => 'API Error: ' . $e->getMessage()
    ], JSON_UNESCAPED_UNICODE);
}