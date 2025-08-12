# main_safe.py
from flask import Flask, request, jsonify
from flask_cors import CORS
from g4f.client import Client
import re, json, html

app = Flask(__name__)
CORS(app)

def clean_title(title: str) -> str:
    if not isinstance(title, str):
        return ""

    t = title.strip()

    # --- NEW: Try to parse JSON string to remove wrapping quotes ---
    try:
        parsed = json.loads(t)
        if isinstance(parsed, str):
            t = parsed.strip()
    except Exception:
        pass

    # Normalize whitespace
    t = re.sub(r'[\r\n\t]+', ' ', t)
    t = re.sub(r'\s{2,}', ' ', t)

    # Remove wrapping quotes if still present
    if (t.startswith('"') and t.endswith('"')) or (t.startswith("'") and t.endswith("'")):
        t = t[1:-1]

    # Unescape HTML entities
    t = html.unescape(t)

    # Remove leftover control chars
    t = re.sub(r'[\x00-\x1f\x7f]+', '', t)

    # Trim again
    return t.strip()

@app.route("/", methods=["GET"])
def home():
    return "✅ ChatGPT Automation VPS (safe) running."

@app.route("/", methods=["POST"])
def handle():
    try:
        data = request.get_json(force=True, silent=True)
        if not data:
            return jsonify({"error": "Invalid or empty JSON"}), 400

        # CLEAN mode (Make.com will call this)
        if 'title' in data:
            titles = data['title']
            if isinstance(titles, str):
                titles_str = titles.strip()
                # Try parse as JSON array
                try:
                    parsed = json.loads(titles_str)
                    if isinstance(parsed, list):
                        titles = parsed
                    elif isinstance(parsed, str):
                        titles = [parsed]
                except Exception:
                    # Fallback split
                    if '\n' in titles_str:
                        titles = [s.strip() for s in titles_str.split('\n') if s.strip()]
                    elif '","' in titles_str:
                        titles = [p.strip().strip('"').strip() for p in titles_str.split('","') if p.strip()]
                    else:
                        titles = [titles_str]

            if isinstance(titles, list):
                cleaned = [clean_title(t) for t in titles if isinstance(t, str) and clean_title(t)]
            else:
                cleaned = [clean_title(str(titles))] if titles else []

            return jsonify({"titles": cleaned}), 200

        # GENERATE mode (old behavior)
        keyword = data.get("keyword", "").strip()
        if not keyword:
            return jsonify({"error": "Keyword is required when no title provided"}), 400

        prompt = f"Give me 5 unique blog titles on the topic: {keyword}. Return only titles in list format, no intro or explanation."
        client = Client()
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
        )
        output = response.choices[0].message.content
        raw_titles = [line.strip("•-1234567890. ") for line in output.split("\n") if line.strip()]
        cleaned_titles = [clean_title(t) for t in raw_titles if t]
        return jsonify({"titles": cleaned_titles}), 200

    except Exception as e:
        return jsonify({"error": "Server error", "details": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
