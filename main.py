from flask import Flask, request, jsonify
from playwright.sync_api import sync_playwright
import time

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
        
        # 1. Go to ChatGPT
        page.goto("https://chat.openai.com/")
        time.sleep(5)

        # 2. Login
        page.click("text=Log in")
        time.sleep(3)
        page.fill("input[type='email']", "kimthy091@gmail.com")
        page.click("button:has-text('Continue')")
        time.sleep(3)
        page.fill("input[type='password']", "Kes@riya99")
        page.click("button:has-text('Continue')")
        time.sleep(7)

        # 3. Send Prompt
        page.fill("textarea", prompt)
        page.keyboard.press("Enter")
        time.sleep(15)

        # 4. Get Response
        content = page.locator(".markdown").last.inner_text()

        browser.close()

    return jsonify({"response": content})
