import os
import base64
from functools import wraps

from flask import Flask, request, jsonify, render_template, abort
from werkzeug.utils import secure_filename
from PIL import Image
from PIL.ExifTags import TAGS
from PIL.TiffImagePlugin import IFDRational

import stripe
from gps_utils import get_gps  # Your existing GPS extraction utility


# Initialise Flask app early so decorators work
app = Flask(__name__)

# Configuration
app.config['UPLOAD_FOLDER'] = 'uploads'
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Stripe setup
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
STRIPE_ENDPOINT_SECRET = os.getenv('STRIPE_ENDPOINT_SECRET')

# Valid API keys for your API (comma-separated env var)
VALID_API_KEYS = set(os.getenv("VALID_API_KEYS", "demo-key-123").split(","))


# Decorator to require API key in header
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


# Routes

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


@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': 'price_XXXXXXX',  # Replace with your Stripe price ID
                'quantity': 1,
            }],
            mode='subscription',
            success_url='https://yourdomain.com/success?session_id={CHECKOUT_SESSION_ID}',
            cancel_url='https://yourdomain.com/cancel',
        )
        return jsonify({'id': session.id})
    except Exception as e:
        return jsonify(error=str(e)), 403


@app.route('/webhook', methods=['POST'])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get('stripe-signature')

    if not STRIPE_ENDPOINT_SECRET:
        return 'Webhook endpoint secret not configured', 500

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_ENDPOINT_SECRET)
    except ValueError:
        return 'Invalid payload', 400
    except stripe.error.SignatureVerificationError:
        return 'Invalid signature', 400

    # Handle the checkout session completed event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        # TODO: mark user subscription active in your DB here
        print(f"Checkout session completed: {session['id']}")

    return '', 200


if __name__ == '__main__':
    app.run(debug=True)
