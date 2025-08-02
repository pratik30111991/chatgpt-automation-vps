from flask import Flask, request, jsonify
from playwright.sync_api import sync_playwright
import time
import os

app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "ChatGPT automation server is running"})

@app.route("/", methods=["POST"])
def chatgpt_automation():
    data = request.get_json()
    prompt = data.get("prompt", "")

    if not prompt:
        return jsonify({"error": "No prompt provided"}), 400

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto("https://chat.openai.com")
        time.sleep(8)  # Give time to load

        # You must manually log in at least once in the browser to keep session cookies
        page.fill("textarea", prompt)
        page.keyboard.press("Enter")
        time.sleep(12)  # Wait for ChatGPT to generate

        response = page.locator(".markdown").last.inner_text()
        browser.close()

    return jsonify({"response": response})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
