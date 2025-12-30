from flask import Flask, send_file, jsonify
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

@app.route('/api/chart', methods=['GET'])
def get_chart():
    # 只返回 output 目录下最新图片，不再每次请求都运行 main.py
    output_dir = 'output'
    files = [f for f in os.listdir(output_dir) if f.endswith('.png')]
    if not files:
        return jsonify({'error': 'No chart found'}), 404
    latest_file = max(files, key=lambda x: os.path.getmtime(os.path.join(output_dir, x)))
    return send_file(os.path.join(output_dir, latest_file), mimetype='image/png')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
