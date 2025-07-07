# gps_extractor_api

✅ GPS Extractor & Mapper API – Project Plan

🔹 Inputs
Image file (JPEG or similar with EXIF metadata)
🔹 Outputs
Latitude & Longitude
Altitude (if available)
Google Maps static link or Leaflet preview (optional)
JSON response



Online GPS Extractor & Map Viewer API

A RESTful API that accepts photo uploads, extracts GPS coordinates and EXIF metadata from the image’s embedded data, and returns the information in JSON format. Designed for easy integration with frontend apps or other services requiring geolocation data extraction from photos.

Features

1. Image Upload Endpoint
Accepts image files via HTTP POST requests (multipart/form-data).
Validates the uploaded file format.
2. GPS Data Extraction
Parses EXIF metadata to extract GPS coordinates (latitude, longitude).
Extracts altitude when available.
Converts GPS data into usable decimal degrees.
3. EXIF Metadata Retrieval
Returns detailed EXIF metadata key-value pairs extracted from the image.
4. Map Link Generation
Generates a Google Maps URL linking directly to the extracted GPS coordinates.
5. Error Handling
Returns clear error messages if:
No file is provided,
File is invalid or corrupted,
No GPS data exists in the image.
6. JSON Response Format
Returns structured JSON including:
gps object with latitude, longitude, altitude, and map_link.
exif object containing additional metadata.
error message if applicable.
