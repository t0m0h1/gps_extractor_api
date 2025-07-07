from flask import Flask, request, jsonify, render_template
from gps_utils import get_gps
import os
from werkzeug.utils import secure_filename
from PIL import Image
from PIL.ExifTags import TAGS
from PIL.TiffImagePlugin import IFDRational
import base64

# Initialize the Flask application
app = Flask(__name__)

# Configure the upload folder
app.config['UPLOAD_FOLDER'] = 'uploads'

# Create the upload folder if it doesn't exist
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])


# Function to convert various data types
def convert_value(value):
    if isinstance(value, IFDRational):
        return float(value)
    elif isinstance(value, bytes):
        # Try decode, else base64 encode
        try:
            return value.decode('utf-8', errors='ignore')
        except Exception:
            return base64.b64encode(value).decode('utf-8')
    elif isinstance(value, dict):
        return {k: convert_value(v) for k, v in value.items()}
    elif isinstance(value, (list, tuple)):
        return [convert_value(v) for v in value]
    else:
        return value


# Function to extract full EXIF data from an image
def extract_full_exif(filepath):
    exif_data = {}
    try:
        img = Image.open(filepath)
        info = img._getexif()
        if not info:
            return None

        for tag, value in info.items():
            decoded = TAGS.get(tag, tag)
            exif_data[decoded] = convert_value(value)

    except Exception as e:
        print(f"Error extracting EXIF: {e}")
        return None

    return exif_data


# Route for the index page
@app.route('/')
def index():
    return render_template('index.html')


# Route to extract GPS data from uploaded image
@app.route('/api/extract-gps', methods=['POST'])
def extract_gps():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    gps_data = get_gps(filepath)
    full_exif = extract_full_exif(filepath)

    if not gps_data:
        return jsonify({'error': 'No GPS data found in image', 'exif': full_exif}), 404

    gps_data["map_link"] = f"https://maps.google.com/?q={gps_data['latitude']},{gps_data['longitude']}"

    return jsonify({
        'gps': gps_data,
        'exif': full_exif
    })


# Run the application
if __name__ == '__main__':
    app.run(debug=True)
