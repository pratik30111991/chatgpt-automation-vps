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
        time.sleep(5)

        # Login (basic version, you can automate if needed)
        # Replace these with your actual credentials if auto-login is set up
        page.fill("textarea", prompt)
        page.keyboard.press("Enter")
        time.sleep(10)

        response = page.locator(".markdown").last.inner_text()
        browser.close()

    return jsonify({"response": response})

# THIS PART IS MANDATORY ON RENDER:
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
