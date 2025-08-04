from flask import Flask, request, jsonify
from flask_cors import CORS
from g4f.client import Client

app = Flask(__name__)
CORS(app)

# ✅ GET request support for browser visits
@app.route("/", methods=["GET"])
def home():
    return "✅ ChatGPT Automation VPS is running. Send a POST request to get blog titles."

# ✅ Main POST route for Make.com, etc.
@app.route("/", methods=["POST"])
def generate_titles():
    try:
        data = request.get_json()
        keyword = data.get("keyword", "").strip()

        if not keyword:
            return jsonify({"error": "Keyword is required"}), 400

        prompt = f"Give me 5 unique blog titles on the topic: {keyword}. Return only titles in list format, no intro or explanation."

        client = Client()
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
        )

        output = response.choices[0].message.content

        # Extract list of titles (optional cleanup)
        titles = [line.strip("•-1234567890. ") for line in output.split("\n") if line.strip()]
        return jsonify({"titles": titles})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=10000)
