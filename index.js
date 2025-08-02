const express = require('express');
const puppeteer = require('puppeteer');
const bodyParser = require('body-parser');
const app = express();
const PORT = process.env.PORT || 3000;

app.use(bodyParser.json());

app.post('/', async (req, res) => {
  const prompt = req.body.prompt || "No prompt received";
  try {
    const browser = await puppeteer.launch({
      headless: "new",
      args: ["--no-sandbox", "--disable-setuid-sandbox"],
    });
    const page = await browser.newPage();
    await page.goto("https://chat.openai.com", { waitUntil: "load" });

    await page.waitForSelector("textarea");
    await page.type("textarea", `"${prompt}" related blog title`);
    await page.keyboard.press("Enter");

    await page.waitForSelector(".markdown", { timeout: 60000 });
    const response = await page.evaluate(() => {
      return Array.from(document.querySelectorAll(".markdown"))
        .map(el => el.innerText)
        .join("\n\n");
    });

    await browser.close();
    res.json({ result: response });
  } catch (err) {
    console.error(err);
    res.status(500).send("Automation error: " + err.message);
  }
});

app.listen(PORT, () => console.log(`✅ Server running on port ${PORT}`));
