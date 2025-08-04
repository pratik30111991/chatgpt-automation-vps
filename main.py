from flask import Flask, request, jsonify
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from pyppeteer import launch
import asyncio
import os

app = Flask(__name__)

# Google Sheet Info
SHEET_ID = "1oQq97-NHOOsfLA1GE_2A3rjKm9Jgv3kPmj4vicZFE_M"
RANGE_NAME = "ChatGPT Credential!A2:D2"

# Load credentials from Google Service Account JSON
SERVICE_ACCOUNT_FILE = "service_account.json"  # Upload this in Render dashboard

def get_gsheet_credentials():
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    return credentials

def get_chatgpt_login():
    creds = get_gsheet_credentials()
    service = build("sheets", "v4", credentials=creds)
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=SHEET_ID, range=RANGE_NAME).execute()
    values = result.get("values", [])
    if not values or len(values[0]) < 4:
        return None
    _, username, email, password = values[0]
    return email, password

async def get_chatgpt_titles(keyword, email, password):
    browser = await launch(headless=True, args=['--no-sandbox'])
    page = await browser.newPage()

    try:
        # Step 1: Open ChatGPT login page
        await page.goto("https://chat.openai.com/auth/login")
        await page.waitForSelector("button", timeout=15000)
        await page.click('button:has-text("Log in")')

        # Step 2: Enter Email
        await page.waitForSelector('input[type="email"]', timeout=15000)
        await page.type('input[type="email"]', email)
        await page.click('button[type="submit"]')

        # Step 3: Enter Password
        await page.waitForSelector('input[type="password"]', timeout=15000)
        await page.type('input[type="password"]', password)
        await page.click('button[type="submit"]')

        # Step 4: Wait for ChatGPT UI to load
        await page.waitForNavigation()
        await page.goto("https://chat.openai.com/")
        await page.waitForSelector("textarea", timeout=20000)

        # Step 5: Send prompt
        prompt = f'"{keyword}" related blog title (give 5 unique titles)'
        await page.type("textarea", prompt)
        await page.keyboard.press("Enter")

        # Step 6: Wait for response
        await page.waitForTimeout(20000)  # Wait for 20 seconds (adjust if needed)

        # Step 7: Extract generated titles
        elements = await page.querySelectorAll("div.markdown p")
        titles = []
        for el in elements:
            text = await page.evaluate('(el) => el.innerText', el)
            if len(text.strip()) > 5:
                titles.append(text.strip())
            if len(titles) >= 5:
                break

        await browser.close()
        return titles if titles else ["No response or titles found"]

    except Exception as e:
        await browser.close()
        return [f"Error occurred: {str(e)}"]

@app.route("/", methods=["POST"])
def generate_titles():
    data = request.get_json()
    print("Received data:", data)

    keyword = data.get("keyword")
    if not keyword:
        return jsonify({"error": "Missing 'keyword' in request"}), 400

    email, password = get_chatgpt_login()
    if not email or not password:
        return jsonify({"error": "Unable to fetch ChatGPT credentials"}), 500

    print(f"Logging in with {email}")
    titles = asyncio.get_event_loop().run_until_complete(get_chatgpt_titles(keyword, email, password))
    print("Generated titles:", titles)
    return jsonify({"titles": titles})

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=10000)
