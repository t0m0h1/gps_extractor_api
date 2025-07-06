from flask import Flask, request, jsonify, render_template
from gps_utils import get_gps
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/extract-gps', methods=['POST'])
def extract_gps():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    gps_data = get_gps(filepath)
    if not gps_data:
        return jsonify({'error': 'No GPS data found in image'}), 404

    gps_data["map_link"] = f"https://maps.google.com/?q={gps_data['latitude']},{gps_data['longitude']}"
    return jsonify(gps_data)

if __name__ == '__main__':
    app.run(debug=True)
