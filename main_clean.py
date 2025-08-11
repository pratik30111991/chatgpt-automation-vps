from flask import Flask, request, jsonify
from flask_cors import CORS
from g4f.client import Client
import re

app = Flask(__name__)
CORS(app)

def clean_title(title: str) -> str:
    # Remove unwanted spaces
    title = title.strip()

    # Replace multiple spaces/tabs/newlines with single space
    title = re.sub(r'\s+', ' ', title)

    # Remove unwanted quotes
    title = title.replace('"', '').replace("'", '')

    # Remove HTML entities if any
    title = re.sub(r'&[a-z]+;', '', title)

    # Keep (-), /, _, numbers as they are — no removal here
    return title

@app.route("/", methods=["GET"])
def home():
    return "✅ ChatGPT Automation VPS (Clean Version) is running. Send a POST request to get blog titles."

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
        raw_titles = [line.strip("•-1234567890. ") for line in output.split("\n") if line.strip()]
        cleaned_titles = [clean_title(t) for t in raw_titles]

        return jsonify({"titles": cleaned_titles})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=10000)
