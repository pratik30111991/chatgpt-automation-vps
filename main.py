from flask import Flask, request, jsonify
app = Flask(__name__)

@app.route('/generate', methods=['POST'])
def generate():
    data = request.get_json()
    keyword = data.get('keyword', 'No keyword provided')
    return jsonify({
        "prompt": f'"{keyword}" related blog title',
        "status": "OK"
    })

@app.route('/')
def home():
    return '🟢 VPS is Running', 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
