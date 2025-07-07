import os
import base64
from functools import wraps

from flask import Flask, request, jsonify, render_template, abort
from flask import session, redirect, url_for, flash

from werkzeug.utils import secure_filename
from PIL import Image
from PIL.ExifTags import TAGS
from PIL.TiffImagePlugin import IFDRational

from gps_utils import get_gps  # Your existing GPS extraction utility


# Initialise Flask app
app = Flask(__name__)

# Load secret key from environment variable or set a default for development
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your_default_secret_key')  # replace with env var in prod


# For demo purposes, we will use a simple in-memory user store
users = {}


# Configuration
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'uploads')
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Valid API keys (comma-separated string from environment)
VALID_API_KEYS = set(os.getenv("VALID_API_KEYS", "demo-key-123").split(","))


# --- Utility Functions ---

def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('x-api-key')
        if not api_key or api_key not in VALID_API_KEYS:
            abort(401, description="Unauthorized: Invalid or missing API key")
        return f(*args, **kwargs)
    return decorated


def convert_value(value):
    """Convert EXIF values to serializable formats."""
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
    """Extract and convert all EXIF data from image."""
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


# --- Routes ---

@app.route('/')
def index():
    if 'user' in session:
        return redirect(url_for('home'))
    return render_template('index.html')


@app.route('/home')
def home():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('home.html', user=session['user'])


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


# Login, sign up, and logout routes

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').lower()
        password = request.form.get('password', '')
        user = users.get(email)
        if user and user['password'] == password:
            session['user'] = user['name']
            flash('Logged in successfully!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid email or password', 'error')
            return redirect(url_for('login'))
    return render_template('login.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not (name and email and password and confirm_password):
            flash('Please fill out all fields', 'error')
            return redirect(url_for('signup'))

        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return redirect(url_for('signup'))

        if email in users:
            flash('Email already registered', 'error')
            return redirect(url_for('signup'))

        users[email] = {'name': name, 'password': password}
        flash('Account created! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('signup.html')


@app.route('/logout')
def logout():
    session.pop('user', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


# --- Main Entry Point ---

if __name__ == '__main__':
    app.run(debug=True)
