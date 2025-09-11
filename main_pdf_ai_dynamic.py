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

# Helpers
def extract_pdf_text(pdf_url: str) -> str:
    """Download PDF and extract text (returns cleaned single-line text)."""
    try:
        r = requests.get(pdf_url, stream=True, timeout=30)
        r.raise_for_status()
        pdf_file = io.BytesIO(r.content)
        reader = PdfReader(pdf_file)
        text_parts = []
        for page in reader.pages:
            try:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            except Exception:
                continue
        text = "\n".join(text_parts)
        # Basic cleanup
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    except Exception as e:
        logging.exception("PDF extraction error")
        return ""

def build_prompt_for_titles(pdf_text: str, user_instruction: str | None = None) -> str:
    """Build prompt to ask model for titles. Keeps a minimal enforced constraint
       that model must only use the PDF text."""
    # Enforced minimal constraint to ensure model stays in-document
    enforced = "Use ONLY the text between the markers below to create blog titles. Do not use outside knowledge."
    # Default instruction if user didn't provide custom
    default_instr = "Generate 5 unique, SEO-friendly blog titles specific to this document. Return only the titles, one per line."
    instruction = user_instruction.strip() if user_instruction else default_instr
    prompt = f"{enforced}\n\n{instruction}\n\n--- PDF CONTENT START ---\n{pdf_text}\n--- PDF CONTENT END ---"
    return prompt

def build_prompt_for_content(pdf_text: str, title: str, user_instruction: str | None = None) -> str:
    """Build prompt to ask model to write the article for a selected title using only PDF text."""
    enforced = "Use ONLY the text between the markers below to write the article. Do not use outside knowledge."
    default_instr = ("Write a long, SEO-friendly blog article for the given title. "
                     "Use only the PDF text. Respond in valid HTML using <h1>, <h2>, <p>, <ul>/<li> etc. "
                     "Do not include any Markdown. Return only the HTML.")
    instruction = user_instruction.strip() if user_instruction else default_instr
    prompt = (
        f"{enforced}\n\n{instruction}\n\nTitle: {title}\n\n"
        f"--- PDF CONTENT START ---\n{pdf_text}\n--- PDF CONTENT END ---"
    )
    return prompt

# Endpoints
@app.route("/", methods=["GET"])
def home():
    return "✅ PDF + Dynamic Titles API running."

@app.route("/pdf/titles", methods=["POST"])
def pdf_titles():
    """Extract PDF text and return 5 dynamic titles.
       Optional JSON fields:
         - pdf_url (required)
         - instruction (optional): custom instruction for title generation
         - max_chars (optional): how many chars of PDF to send (default 12000)
    """
    try:
        data = request.get_json(force=True, silent=True) or {}
        pdf_url = data.get("pdf_url")
        if not pdf_url:
            return jsonify({"error": "Missing pdf_url"}), 400

        max_chars = int(data.get("max_chars", 12000))
        user_instruction = data.get("instruction")

        logging.info(f"📥 INPUT (/pdf/titles): pdf_url={pdf_url}, max_chars={max_chars}, instruction={user_instruction}")

        pdf_text = extract_pdf_text(pdf_url)
        if not pdf_text:
            return jsonify({"error": "No text extracted from PDF"}), 400

        truncated = pdf_text[:max_chars]

        prompt = build_prompt_for_titles(truncated, user_instruction)

        client = Client()
        response = client.chat.completions.create(
            model="gpt-5-nano",
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.choices[0].message.content
        # Clean into lines (basic)
        titles = [line.strip(" \t•-1234567890. ") for line in raw.splitlines() if line.strip()]
        # Deduplicate & keep top 5
        seen = set(); uniq = []
        for t in titles:
            if t.lower() not in seen:
                seen.add(t.lower()); uniq.append(t)
            if len(uniq) >= 5:
                break

        logging.info(f"📤 OUTPUT (/pdf/titles): {uniq}")

        return jsonify({"titles": uniq, "fileSize": len(pdf_text)}), 200

    except Exception as e:
        logging.exception("Error in /pdf/titles")
        return jsonify({"error": "Server error", "details": str(e)}), 500

@app.route("/pdf/content", methods=["POST"])
def pdf_content():
    """Generate article HTML for a selected title using only PDF text.
       JSON fields:
         - pdf_url (required)
         - title (required)
         - instruction (optional)
         - max_chars (optional): default 20000
    """
    try:
        data = request.get_json(force=True, silent=True) or {}
        pdf_url = data.get("pdf_url")
        title = data.get("title")
        if not pdf_url or not title:
            return jsonify({"error": "Missing pdf_url or title"}), 400

        max_chars = int(data.get("max_chars", 20000))
        user_instruction = data.get("instruction")

        logging.info(f"📥 INPUT (/pdf/content): pdf_url={pdf_url}, title={title}, max_chars={max_chars}, instruction={user_instruction}")

        pdf_text = extract_pdf_text(pdf_url)
        if not pdf_text:
            return jsonify({"error": "No text extracted from PDF"}), 400

        truncated = pdf_text[:max_chars]
        prompt = build_prompt_for_content(truncated, title, user_instruction)

        client = Client()
        response = client.chat.completions.create(
            model="gpt-5-nano",
            messages=[{"role": "user", "content": prompt}],
        )
        content_html = response.choices[0].message.content
        # Remove accidental code fences
        content_html = re.sub(r'```html|```', '', content_html).strip()

        logging.info(f"📤 OUTPUT (/pdf/content): {len(content_html)} chars generated")

        return jsonify({"title": title, "content": content_html, "format": "html"}), 200

    except Exception as e:
        logging.exception("Error in /pdf/content")
        return jsonify({"error": "Server error", "details": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "12000")))
