<?php
// Database configuration
$host = 'localhost';
$db_user = 'root';
$db_pass = '';
$db_name = 'rent_pulse_db';

// Create connection
$conn = new mysqli($host, $db_user, $db_pass, $db_name);

// Check connection
if ($conn->connect_error) {
    die("Connection failed: " . $conn->connect_error);
}

// Set charset to UTF-8 to support all languages (like Cyrillic or Polish)
$conn->set_charset("utf8mb4");
?>