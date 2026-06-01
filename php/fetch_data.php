<?php
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');

set_time_limit(300);

require '../vendor/autoload.php';

use Aws\S3\S3Client;
use Aws\S3\Exception\S3Exception;

try{
    $dotenv = Dotenv\Dotenv::createImmutable(dirname(__DIR__));
    $dotenv->load();
}catch(Exception $e){
    http_response_code(500);
    echo json_encode([['title' => 'Server error', 
    'address' => 'No .env: ' . $e->getMessage(), 'url' => '#', 'images' => []]], JSON_UNESCAPED_UNICODE);
    exit;
}

$platformInputs = isset($_GET['platforms']) ? trim($_GET['platforms']) : '';
$platforms = !empty($platformInputs) ? explode(',', $platformInputs) : [];
$combined = isset($_GET['combined']) ? $_GET['combined'] === 'true' : false;

if(empty($platforms)){
    echo json_encode([]);
    exit;
}

try{
    $s3Client = new S3Client([
        'verion' => 'latest',
        'region' => $_ENV['AWS_REGION'],
        'credentials' => [
            'key' => $_ENV['AWS_ACCESS_KEY_ID'],
            'secret' => $_ENV['AWS_SECRET_ACCESS_KEY'],
            'token'  => $_ENV['AWS_SESSION_TOKEN']
        ]
    ]);

    $bucketName = $_ENV['AWS_BUCKET_NAME'];

    $olxOffers = [];
    $otodomOffers = [];

    foreach($platforms as $platform){
        $prefix = ($platform === 'olx.pl') ? 'olx/' : 'otodom/';

        $objects = $s3Client->getIterator('ListObjects', [
            'Bucket' => $bucketName,
            'Prefix' => $prefix
        ]);

        foreach($objects as $object){
            $key = $object['Key'];

            if(strpos($key, 'ai_verdict.json') !== false){
                try{
                    $result = $s3Client->getObject([
                        'Bucket' => $bucketName,
                        'Key' => $key
                    ]);

                    $jsonData = $result['Body']->getContents();
                    $offerData = json_decode($jsonData, true);
                    $isCombinedVerdict = isset($offerData['ai_verdict']['is_combined']) ? $offerData['ai_verdict']['is_combined'] : null;

                    if($combined && $isCombinedVerdict !== true) {continue;}
                    if (!$combined && $isCombinedVerdict !== false) {continue;}

                    if ($platform === 'olx.pl') {
                        $olxOffers[] = $offerData;
                    } else {
                        $otodomOffers[] = $offerData;
                    }
                }catch(Exception $e){
                    continue;
                }
            }
        }
    }

    $finalOffers = array_merge($olxOffers, $otodomOffers);

    echo json_encode($finalOffers, JSON_UNESCAPED_UNICODE);

} catch (S3Exception $e) {
    http_response_code(500);
    echo json_encode([['title' => 'AWS S3 Error', 'address' => $e->getAwsErrorMessage(), 'url' => '#', 'images' => []]], JSON_UNESCAPED_UNICODE);
} catch (Exception $e) {
    http_response_code(500);
    echo json_encode([['title' => 'Error', 'address' => $e->getMessage(), 'url' => '#', 'images' => []]], JSON_UNESCAPED_UNICODE);
}
?>