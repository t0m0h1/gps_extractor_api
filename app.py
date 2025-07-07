from flask import Flask, request, jsonify, render_template, abort
from gps_utils import get_gps
import os
from werkzeug.utils import secure_filename
from PIL import Image
from PIL.ExifTags import TAGS
from PIL.TiffImagePlugin import IFDRational
import base64
from functools import wraps

VALID_API_KEYS = set(os.getenv("VALID_API_KEYS", "demo-key-123").split(","))

def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('x-api-key')
        if not api_key or api_key not in VALID_API_KEYS:
            abort(401, description="Unauthorized: Invalid or missing API key")
        return f(*args, **kwargs)
    return decorated

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

def convert_value(value):
    if isinstance(value, IFDRational):
        return float(value)
    elif isinstance(value, bytes):
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

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/extract-gps', methods=['POST'])
@require_api_key
def extract_gps():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400

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

if __name__ == '__main__':
    app.run(debug=True)
