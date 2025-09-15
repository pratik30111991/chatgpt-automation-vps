from flask import Flask, request, jsonify
from flask_cors import CORS
import requests, logging, re, io, os
from PyPDF2 import PdfReader
from g4f.client import Client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

app = Flask(__name__)
CORS(app)

# ----------------- Helpers -----------------
def extract_pdf_text(pdf_url: str) -> tuple[str, dict]:
    """Download PDF and extract text (returns cleaned text + page map)."""
    try:
        r = requests.get(pdf_url, stream=True, timeout=30)
        r.raise_for_status()
        pdf_file = io.BytesIO(r.content)
        reader = PdfReader(pdf_file)

        text_parts = []
        page_map = {}  # {page_num: text}
        for i, page in enumerate(reader.pages, start=1):
            try:
                page_text = page.extract_text()
                if page_text:
                    page_text = re.sub(r'\s+', ' ', page_text).strip()
                    text_parts.append(page_text)
                    page_map[i] = page_text
            except Exception:
                continue

        full_text = " ".join(text_parts)
        return full_text, page_map
    except Exception:
        logging.exception("PDF extraction error")
        return "", {}

def build_prompt_for_titles(pdf_text: str, user_instruction: str | None = None) -> str:
    enforced = "Use ONLY the text between the markers below to create blog titles. Do not use outside knowledge."
    default_instr = "Generate 5 unique, SEO-friendly blog titles specific to this document. Return only the titles, one per line."
    instruction = user_instruction.strip() if user_instruction else default_instr
    return f"{enforced}\n\n{instruction}\n\n--- PDF CONTENT START ---\n{pdf_text}\n--- PDF CONTENT END ---"

def build_prompt_for_content(pdf_text: str, title: str, user_instruction: str | None = None) -> str:
    enforced = "Use ONLY the text between the markers below to write the article. Do not use outside knowledge."
    default_instr = ("Write a long, SEO-friendly blog article for the given title. "
                     "Use only the PDF text. Respond in valid HTML using <h1>, <h2>, <p>, <ul>/<li> etc. "
                     "Do not include any Markdown. Return only the HTML.")
    instruction = user_instruction.strip() if user_instruction else default_instr
    return (
        f"{enforced}\n\n{instruction}\n\nTitle: {title}\n\n"
        f"--- PDF CONTENT START ---\n{pdf_text}\n--- PDF CONTENT END ---"
    )

# ----------------- Endpoints -----------------
@app.route("/", methods=["GET"])
def home():
    return "✅ PDF + Dynamic Titles API running."

@app.route("/pdf/titles", methods=["POST"])
def pdf_titles():
    try:
        data = request.get_json(force=True, silent=True) or {}
        pdf_url = data.get("pdf_url")
        if not pdf_url:
            return jsonify({"error": "Missing pdf_url"}), 400

        max_chars = int(data.get("max_chars", 12000))
        user_instruction = data.get("instruction")

        logging.info(f"📥 INPUT (/pdf/titles): pdf_url={pdf_url}, max_chars={max_chars}, instruction={user_instruction}")

        pdf_text, page_map = extract_pdf_text(pdf_url)
        if not pdf_text:
            return jsonify({
                "error": "No text extracted – scanned or unsupported PDF",
                "fileSize": 0,
                "pages_checked": len(page_map)
            }), 400

        truncated = pdf_text[:max_chars]
        prompt = build_prompt_for_titles(truncated, user_instruction)

        client = Client()
        response = client.chat.completions.create(
            model="gpt-5-nano",
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.choices[0].message.content

        # Clean into lines
        titles = [line.strip(" \t•-1234567890. ") for line in raw.splitlines() if line.strip()]
        seen, uniq = set(), []
        for t in titles:
            if t.lower() not in seen:
                seen.add(t.lower())
                uniq.append(t)
            if len(uniq) >= 5:
                break

        # Logging ke liye page info
        for i, t in enumerate(uniq, start=1):
            logging.info(f"✅ Title {i}: \"{t}\" (source: PDF, total pages={len(page_map)})")

        logging.info(f"📝 Extracted Pages={len(page_map)}, Characters={len(pdf_text)}")

        return jsonify({
            "titles": uniq,
            "fileSize": len(pdf_text),
            "pages_checked": len(page_map)
        }), 200

    except Exception as e:
        logging.exception("Error in /pdf/titles")
        return jsonify({"error": "Server error", "details": str(e)}), 500

@app.route("/pdf/content", methods=["POST"])
def pdf_content():
    try:
        data = request.get_json(force=True, silent=True) or {}
        pdf_url = data.get("pdf_url")
        title = data.get("title")
        if not pdf_url or not title:
            return jsonify({"error": "Missing pdf_url or title"}), 400

        max_chars = int(data.get("max_chars", 20000))
        user_instruction = data.get("instruction")

        logging.info(f"📥 INPUT (/pdf/content): pdf_url={pdf_url}, title={title}, max_chars={max_chars}, instruction={user_instruction}")

        pdf_text, page_map = extract_pdf_text(pdf_url)
        if not pdf_text:
            return jsonify({
                "error": "No text extracted – scanned or unsupported PDF",
                "fileSize": 0,
                "pages_checked": len(page_map)
            }), 400

        truncated = pdf_text[:max_chars]
        prompt = build_prompt_for_content(truncated, title, user_instruction)

        client = Client()
        response = client.chat.completions.create(
            model="gpt-5-nano",
            messages=[{"role": "user", "content": prompt}],
        )
        content_html = response.choices[0].message.content
        content_html = re.sub(r'```html|```', '', content_html).strip()

        logging.info(f"📤 OUTPUT (/pdf/content): {len(content_html)} chars generated")
        logging.info(f"📝 Extracted Pages={len(page_map)}, Characters={len(pdf_text)}")

        return jsonify({
            "title": title,
            "content": content_html,
            "format": "html",
            "fileSize": len(pdf_text),
            "pages_checked": len(page_map)
        }), 200

    except Exception as e:
        logging.exception("Error in /pdf/content")
        return jsonify({"error": "Server error", "details": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "12000")))
