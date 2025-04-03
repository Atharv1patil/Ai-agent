from flask import Flask, request, jsonify
import logging
import json
import google.generativeai as genai
import os
import time
import requests
import base64
from io import BytesIO

from flask_cors import CORS
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import WebDriverException, TimeoutException

load_dotenv() 

# Initialize Flask app and logging
app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    logger.warning("GEMINI_API_KEY not found in environment variables")
genai.configure(api_key=GEMINI_API_KEY)

### Interaction Functions (from the first code)

def generate_automation_instructions(command):
    """Generate automation steps from a natural language command using Gemini API for browser interactions."""
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        prompt = f"""
        Convert the following natural language command into specific browser automation steps:
        Command: {command}

        Return a JSON object with the following structure:
        {{
            "steps": [
                {{
                    "action": "navigate" | "click" | "type" | "select" | "wait" | "screenshot",
                    "params": {{
                        // Parameters specific to the action
                    }}
                }}
            ]
        }}

        Important guidelines:
        1. For selectors, provide multiple alternatives separated by commas when possible
        2. For search inputs, use multiple possible selectors like "input[name='q'], input[type='search'], textarea[name='q']"
        3. Always include a wait step after navigation
        4. For Google searches, use "input[name='q'], textarea[name='q']"
        5. For YouTube, use "input#search" as the search input selector
        6. For GitHub login, use "input#login_field" for username, "input#password" for password, "input[type='submit']" for login button

        Example:
        Command: "Log into GitHub with username 'myuser' and password 'mypassword', search for 'flask', and take a screenshot"
        {{
            "steps": [
                {{
                    "action": "navigate",
                    "params": {{ "url": "https://github.com/login" }}
                }},
                {{
                    "action": "wait",
                    "params": {{ "time": 2000 }}
                }},
                {{
                    "action": "type",
                    "params": {{ "selector": "input#login_field", "text": "myuser" }}
                }},
                {{
                    "action": "type",
                    "params": {{ "selector": "input#password", "text": "mypassword" }}
                }},
                {{
                    "action": "click",
                    "params": {{ "selector": "input[type='submit']" }}
                }},
                {{
                    "action": "wait",
                    "params": {{ "time": 2000 }}
                }},
                {{
                    "action": "type",
                    "params": {{ "selector": "input[name='q']", "text": "flask", "press_enter": true }}
                }},
                {{
                    "action": "wait",
                    "params": {{ "time": 2000 }}
                }},
                {{
                    "action": "screenshot",
                    "params": {{ "filename": "github_search.png" }}
                }}
            ]
        }}
        Only return the JSON object, nothing else.
        """
        response = model.generate_content(prompt)
        response_text = response.text
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        return json.loads(response_text)
    except Exception as e:
        logger.error(f"Error generating interaction instructions: {str(e)}")
        raise

def execute_browser_automation(instructions, browser_type='chrome'):
    """Execute browser automation steps using Selenium while keeping the browser open."""
    driver = None
    try:
        if browser_type.lower() == 'chrome':
            driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()))
        else:
            return {"status": "error", "message": "Unsupported browser type"}

        driver.implicitly_wait(10)

        for step in instructions.get('steps', []):
            action = step.get('action')
            params = step.get('params', {})
            logger.info(f"Executing {action}: {params}")

            if action == 'navigate':
                driver.get(params['url'])
                WebDriverWait(driver, 20).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
            elif action == 'click':
                selectors = [s.strip() for s in params['selector'].split(',')]
                element = None
                for selector in selectors:
                    try:
                        element = WebDriverWait(driver, 20).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                        break
                    except TimeoutException:
                        continue
                if element:
                    element.click()
                else:
                    raise Exception(f"Click failed for selectors: {params['selector']}")
            elif action == 'type':
                selectors = [s.strip() for s in params['selector'].split(',')]
                text = params['text']
                element = None
                for selector in selectors:
                    try:
                        element = WebDriverWait(driver, 20).until(
                            EC.visibility_of_element_located((By.CSS_SELECTOR, selector)))
                        break
                    except TimeoutException:
                        continue
                if element:
                    element.clear()
                    element.send_keys(text)
                    if params.get('press_enter', False):
                        element.send_keys(Keys.RETURN)
                        WebDriverWait(driver, 20).until(
                            lambda d: d.execute_script("return document.readyState") == "complete")
                else:
                    raise Exception(f"Type failed for selectors: {params['selector']}")
            elif action == 'wait':
                if 'time' in params:
                    time.sleep(params['time'] / 1000)
                elif 'selector' in params:
                    WebDriverWait(driver, 20).until(
                        EC.visibility_of_element_located((By.CSS_SELECTOR, params['selector']))
                    )
            # elif action == 'screenshot':
                # driver.save_screenshot(params.get('filename', 'screenshot.png'))

        return {"status": "success", "message": "Browser remains open for inspection"}
    except Exception as e:
        logger.error(f"Interaction error: {str(e)}")
        return {"status": "error", "message": str(e)}
    finally:
        if driver:
            logger.info("Browser remains open - close manually when finished")

### Extraction Functions (from the second code)

def generate_extraction_plan(command):
    """Generate an extraction plan from a natural language command using Gemini API."""
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        prompt = f"""
        Convert the following natural language extraction command into a structured extraction plan:
        Command: {command}

        Return a JSON object with the following structure:
        {{
            "url": "website URL to extract from",
            "selectors": {{
                "data_name1": "CSS selector for data type 1",
                "data_name2": "CSS selector for data type 2",
                ...
            }},
            "description": "Brief description of what we're extracting"
        }}

        Important guidelines:
        1. Determine the most appropriate website URL based on the command
        2. Provide accurate CSS selectors for the requested data
        3. Use descriptive names for the data types
        4. For news websites:
           - Headlines: ".headline, h1, h2, h3, .title"
           - Article text: ".article-body, .content, article p"
           - Authors: ".author, .byline"
           - Dates: ".date, .timestamp, time"
        5. For e-commerce websites:
           - Product names: ".product-name, .product-title, h1"
           - Prices: ".price, .product-price"
           - Ratings: ".rating, .stars"
           - Reviews: ".review, .comment"
        6. For social media:
           - Posts: ".post, .tweet, .content"
           - Usernames: ".username, .user-name, .handle"
           - Timestamps: ".timestamp, .time"

        Example:
        Command: "Extract all news headlines from CNN"
        {{
            "url": "https://www.cnn.com",
            "selectors": {{
                "headlines": ".headline, h3.cd__headline, .container__headline, .card__headline"
            }},
            "description": "Extracting news headlines from CNN's homepage"
        }}

        Example:
        Command: "Get product prices and names from Amazon for iPhone cases"
        {{
            "url": "https://www.amazon.com/s?k=iphone+cases",
            "selectors": {{
                "product_names": "h2 a.a-link-normal span, h2.a-size-mini",
                "prices": "span.a-price-whole, span.a-offscreen"
            }},
            "description": "Extracting iPhone case product names and prices from Amazon search results"
        }}

        Only return the JSON object, nothing else.
        """
        response = model.generate_content(prompt)
        response_text = response.text
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        return json.loads(response_text)
    except Exception as e:
        logger.error(f"Error generating extraction plan: {str(e)}")
        raise

def execute_extraction(extraction_plan, browser_type='chrome'):
    """Execute data extraction using Selenium based on the extraction plan."""
    driver = None
    try:
        if browser_type.lower() == 'chrome':
            options = webdriver.ChromeOptions()
            options.add_argument("--start-maximized")
            driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
        else:
            return {"status": "error", "message": "Unsupported browser type"}

        url = extraction_plan.get('url')
        selectors = extraction_plan.get('selectors', {})
        description = extraction_plan.get('description', 'Data extraction')

        logger.info(f"Executing extraction: {description} from {url}")

        driver.get(url)
        WebDriverWait(driver, 20).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )

        # Wait a bit more for dynamic content
        time.sleep(3)

        extracted_data = {}
        for data_name, selector in selectors.items():
            selector_list = [s.strip() for s in selector.split(',')]
            data_items = []

            for single_selector in selector_list:
                elements = driver.find_elements(By.CSS_SELECTOR, single_selector)
                if elements:
                    # Try to get text first
                    texts = [e.text.strip() for e in elements if e.text.strip()]
                    if texts:
                        data_items.extend(texts)
                    else:
                        # If no text, try to get attributes
                        for element in elements:
                            attr_value = (
                                element.get_attribute('src') or
                                element.get_attribute('href') or
                                element.get_attribute('alt') or
                                element.get_attribute('title')
                            )
                            if attr_value:
                                data_items.append(attr_value)

            # Remove duplicates while preserving order
            seen = set()
            extracted_data[data_name] = [x for x in data_items if not (x in seen or seen.add(x))]

        # Take a screenshot for verification
        # screenshot_path = "extraction_verification.png"
        # driver.save_screenshot(screenshot_path)
        # with open(screenshot_path, "rb") as image_file:
        #     screenshot_base64 = base64.b64encode(image_file.read()).decode('utf-8')

        return {
            "status": "success",
            "description": description,
            "url": url,
            "data": extracted_data,
            # "screenshot": screenshot_base64
        }
    except Exception as e:
        logger.error(f"Extraction error: {str(e)}")
        return {"status": "error", "message": str(e)}
    finally:
        if driver:
            logger.info("Browser remains open with extracted data")

### Flask Endpoints

@app.route('/interact', methods=['POST'])
def interact():
    """Handle browser interaction requests using natural language commands."""
    data = request.json
    if not data or 'command' not in data:
        return jsonify({"error": "Missing command"}), 400

    try:
        instructions = generate_automation_instructions(data['command'])
        result = execute_browser_automation(instructions, data.get('browser', 'chrome'))
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/extract', methods=['POST'])
def extract():
    """Extract data from a webpage using natural language commands or direct URL and selectors."""
    data = request.json
    if not data:
        return jsonify({"error": "Missing request data"}), 400

    if 'command' in data:
        try:
            extraction_plan = generate_extraction_plan(data['command'])
            result = execute_extraction(extraction_plan, data.get('browser', 'chrome'))
            result["original_command"] = data['command']
            result["generated_plan"] = extraction_plan
            return jsonify(result)
        except Exception as e:
            logger.error(f"Error in extract endpoint (command mode): {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500

    elif 'url' in data and 'selectors' in data:
        extraction_plan = {
            "url": data['url'],
            "selectors": data['selectors'],
            "description": "Manual extraction with provided selectors"
        }
        try:
            result = execute_extraction(extraction_plan, data.get('browser', 'chrome'))
            return jsonify(result)
        except Exception as e:
            logger.error(f"Error in extract endpoint (legacy mode): {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500

    else:
        return jsonify({"error": "Missing command or url/selectors"}), 400

### Run the Flask App

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)


