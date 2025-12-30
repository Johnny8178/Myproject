from flask import Flask, jsonify, send_file, request
from analyzer import HongduAnalyzer
import os
import traceback

app = Flask(__name__)

@app.route('/analyze', methods=['GET'])
def analyze():
    symbol = request.args.get('symbol', '600316')
    analyzer = HongduAnalyzer()
    try:
        print(f"[LOG] 开始分析 symbol={symbol}")
        analyzer.sync_data(symbol)
        analyzer.run_focused_logic(symbol)
        print(f"[LOG] 分析完成 symbol={symbol}")
    except Exception as e:
        print(f"[ERROR] 分析失败: {e}")
        traceback.print_exc()
        return jsonify({'error': f'分析失败: {str(e)}'}), 500
    # 优先找 symbol 相关图片
    output_dir = 'output'
    files = [f for f in os.listdir(output_dir) if (symbol in f or f.startswith('focused_main_wave_')) and f.endswith('.png')]
    print(f"[LOG] output目录图片: {files}")
    if not files:
        print("[ERROR] 没有找到分析图片")
        return jsonify({'error': 'No analysis image found'}), 404
    latest_img = sorted(files)[-1]
    img_url = f'/static/{latest_img}'
    print(f"[LOG] 返回图片: {img_url}")
    return jsonify({'img_url': img_url})

@app.route('/static/<filename>')
def serve_image(filename):
    return send_file(os.path.join('output', filename), mimetype='image/png')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
