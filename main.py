from flask import Flask, request, jsonify
import openai

app = Flask(__name__)

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ChatGPT automation server is running"})

@app.route("/", methods=["POST"])
def generate_response():
    data = request.get_json()
    prompt = data.get("prompt")
    
    if not prompt:
        return jsonify({"error": "Prompt not provided"}), 400

    # Your OpenAI API call logic here
    # For now, return a fake response
    return jsonify({"response": f"Generated response for prompt: {prompt}"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
