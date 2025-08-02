from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "ChatGPT automation server is running"})

@app.route("/", methods=["POST"])
def receive_prompt():
    data = request.get_json()
    prompt = data.get("prompt", "")

    # Log received prompt
    print("Received prompt:", prompt)

    # TODO: Send to Tampermonkey via browser automation (next step)
    with open("pending_prompt.txt", "w", encoding="utf-8") as f:
        f.write(prompt)

    return jsonify({"status": "Prompt received", "prompt": prompt})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
