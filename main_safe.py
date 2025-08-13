from flask import Flask, request, jsonify
from flask_cors import CORS
from g4f.client import Client
import re, json, html, logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

app = Flask(__name__)
CORS(app)

def clean_title(title: str) -> str:
    if not isinstance(title, str):
        return ""

    t = title.strip()

    for _ in range(3):
        try:
            parsed = json.loads(t)
            if isinstance(parsed, str):
                t = parsed.strip()
            else:
                break
        except Exception:
            break

    t = re.sub(r'[\r\n\t]+', ' ', t)
    t = re.sub(r'\s{2,}', ' ', t)

    while (t.startswith('"') and t.endswith('"')) or (t.startswith("'") and t.endswith("'")):
        t = t[1:-1].strip()

    t = t.strip(", '\"")
    t = html.unescape(t)
    t = re.sub(r'[\x00-\x1f\x7f]+', '', t)

    return t.strip()

@app.route("/", methods=["GET"])
def home():
    return "✅ ChatGPT Automation VPS (safe) running."

@app.route("/", methods=["POST"])
def handle():
    try:
        data = request.get_json(force=True, silent=True)
        logging.info(f"📩 Incoming request: {json.dumps(data, ensure_ascii=False)}")

        if not data:
            logging.warning("⚠️ Empty or invalid JSON received.")
            return jsonify({"error": "Invalid or empty JSON"}), 400

        # Titles cleaning mode
        if 'title' in data:
            titles = data['title']
            logging.info(f"📝 Raw titles from request: {titles}")

            if isinstance(titles, str):
                titles_str = titles.strip()
                try:
                    parsed = json.loads(titles_str)
                    if isinstance(parsed, list):
                        titles = parsed
                    elif isinstance(parsed, str):
                        titles = [parsed]
                except Exception:
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

            logging.info(f"✅ Cleaned titles: {cleaned}")
            return jsonify({"titles": cleaned}), 200

        # Keyword must be present for generation
        keyword = data.get("keyword", "").strip()
        if not keyword:
            logging.error("❌ Missing keyword for generation.")
            return jsonify({"error": "Keyword is required when no title provided"}), 400

        generate_content = data.get("generate_content", False)
        logging.info(f"⚙️ generate_content flag is {generate_content}")

        client = Client()

        if generate_content:
            # Generate long detailed HTML content
            prompt = (
                f"Write a long, SEO-friendly, detailed blog article on the topic: {keyword}.\n\n"
                "Output must be clean HTML with these rules:\n"
                "- <h1> for main title, <h2> for section headings, <h3> for subheadings.\n"
                "- Use <b> for bold text, <i> for italic, and <u> for underline.\n"
                "- Use <p> for paragraphs.\n"
                "- Use <ul><li> for bullet points and <ol><li> for numbered lists.\n"
                "- Insert relevant emojis inline.\n"
                "- Keep formatting neat and consistent.\n"
                "- Preserve all special characters and emojis without escaping.\n"
                "- Do not include any Markdown, only pure HTML.\n"
                "- Make sure HTML is valid and well-structured.\n"
            )
            logging.info(f"🔍 Generating HTML content for keyword: {keyword}")

            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
            )

            content_html = response.choices[0].message.content

            # Remove any accidental markdown code fences
            content_html = re.sub(r'```html|```', '', content_html).strip()

            logging.info(f"🤖 Generated HTML content length: {len(content_html)} chars")

            return jsonify({
                "content": content_html,
                "format": "html"
            }), 200

        else:
            # Generate blog titles
            prompt = f"Give me 5 unique blog titles on the topic: {keyword}. Return only titles in list format, no intro or explanation."
            logging.info(f"🔍 Generating titles for keyword: {keyword}")

            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
            )

            output = response.choices[0].message.content
            raw_titles = [line.strip("•-1234567890. ") for line in output.split("\n") if line.strip()]
            cleaned_titles = [clean_title(t) for t in raw_titles if t]

            logging.info(f"🤖 GPT raw output: {output}")
            logging.info(f"✅ Cleaned generated titles: {cleaned_titles}")

            return jsonify({"titles": cleaned_titles}), 200

    except Exception as e:
        logging.exception("💥 Server error occurred")
        return jsonify({"error": "Server error", "details": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
