from flask import Flask, request, jsonify
import logging
import json
import google.generativeai as genai
import os
import time
import requests
import base64
import random
from io import BytesIO
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import (WebDriverException,
                                        TimeoutException,
                                        StaleElementReferenceException)

from flask_cors import CORS

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Gemini API
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    logger.warning("GEMINI_API_KEY not found in environment variables")
    GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"
genai.configure(api_key=GEMINI_API_KEY)


# Helper functions
def find_dynamic_element(driver, selector, timeout=20):
    """Find element using CSS or XPath with explicit waits and multiple strategies."""
    try:
        if selector.startswith(('//', './/')):
            return WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.XPATH, selector)))
        return WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
    except TimeoutException:
        logger.error(f"Timeout while waiting for element: {selector}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return None


def click_with_retry(driver, element):
    """Handle stale elements and alternative click methods."""
    try:
        element.click()
    except WebDriverException:
        driver.execute_script("arguments[0].click();", element)


def smart_wait(driver, selector=None, timeout=20):
    """Intelligent waiting mechanism."""
    if selector:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
    else:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete")


def generate_automation_instructions(command):
    """Generate automation steps with dynamic selectors using Gemini API."""
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        prompt = f"""
        Convert this command to automation steps with robust selectors:
        {command}

        Use these strategies:
        1. Prioritize data attributes: [data-testid], [data-qa], [data-id]
        2. Use semantic roles: [role='button'], [role='search']
        3. CSS substring matches: [id^='search'], [class*='input']
        4. XPath contains: //*[contains(text(), 'Submit')]
        5. Multiple fallbacks: "selector1, selector2"

        Return JSON with enhanced selectors.
        """
        response = model.generate_content(prompt)
        return parse_gemini_response(response.text)


def parse_gemini_response(response_text):
    """Extract JSON from Gemini response with error handling."""
    try:
        if "```json" in response_text:
            json_str = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            json_str = response_text.split("```")[1].split("```")[0]
        else:
            json_str = response_text
        return json.loads(json_str.strip())
    except Exception as e:
        logger.error(f"Error parsing response: {e}")
        raise


def execute_browser_automation(instructions, browser_type='chrome'):
    """Enhanced executor with dynamic element handling."""
    driver = None
    results = {"status": "success", "steps_results": []}

    try:
        # Browser setup
        options = webdriver.ChromeOptions()
        options.add_argument("--start-maximized")
        options.add_argument("--disable-blink-features=AutomationControlled")
        driver = webdriver.Chrome(
            service=ChromeService(ChromeDriverManager().install()),
            options=options
        )
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        # Dynamic interaction loop
        for step_index, step in enumerate(instructions.get('steps', [])):
            action = step.get('action')
            params = step.get('params', {})
            step_result = {"action": action, "params": params}

            try:
                if action == 'navigate':
                    driver.get(params['url'])
                    smart_wait(driver)
                    step_result["result"] = f"Navigated to {params['url']}"

                elif action == 'click':
                    element = find_dynamic_element(driver, params['selector'])
                    if element:
                        click_with_retry(driver, element)
                        smart_wait(driver)
                        step_result["result"] = f"Clicked {params['selector']}"
                    else:
                        raise Exception("Element not found")

                elif action == 'type':
                    element = find_dynamic_element(driver, params['selector'])
                    if element:
                        element.clear()
                        # Human-like typing
                        text = params['text']
                        for char in text:
                            element.send_keys(char)
                            time.sleep(random.uniform(0.05, 0.2))
                        if params.get('press_enter'):
                            element.send_keys(Keys.RETURN)
                            smart_wait(driver)
                        step_result["result"] = f"Typed {text}"
                    else:
                        raise Exception("Input not found")

                elif action == 'wait':
                    if 'time' in params:
                        time.sleep(params['time'] / 1000)
                        step_result["result"] = f"Waited {params['time']}ms"
                    elif 'selector' in params:
                        smart_wait(driver, params['selector'])
                        step_result["result"] = "Wait condition met"

                elif action == 'screenshot':
                    buff = BytesIO()
                    driver.save_screenshot(buff)
                    step_result["screenshot"] = base64.b64encode(buff.getvalue()).decode('utf-8')

                elif action == 'extract':
                    data = {}
                    elements = driver.find_elements(By.CSS_SELECTOR, params['selector'])
                    if not elements:
                        elements = driver.find_elements(By.XPATH, params['selector'])

                    for idx, el in enumerate(elements):
                        data[idx] = {
                            "text": el.text,
                            "attrs": el.get_attribute('outerHTML')
                        }
                    step_result["data"] = data

                step_result["status"] = "success"

            except Exception as e:
                step_result.update({
                    "status": "error",
                    "error": str(e),
                    "screenshot": base64.b64encode(
                        driver.get_screenshot_as_png()).decode('utf-8')
                })

            results["steps_results"].append(step_result)

        # Final verification
        results["final_state"] = driver.page_source[:1000]  # First 1000 chars
        results["final_screenshot"] = base64.b64encode(
            driver.get_screenshot_as_png()).decode('utf-8')

    except Exception as e:
        results.update({
            "status": "error",
            "message": str(e),
            "screenshot": base64.b64encode(
                driver.get_screenshot_as_png()).decode('utf-8') if driver else ""
        })

    finally:
        if driver:
            driver.quit()

    return results


def execute_extraction(extraction_plan):
    """Enhanced data extraction with dynamic content handling."""
    driver = None
    result = {"status": "success", "data": {}}

    try:
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        driver = webdriver.Chrome(
            service=ChromeService(ChromeDriverManager().install()),
            options=options
        )

        driver.get(extraction_plan['url'])

        # Dynamic content loading
        last_height = driver.execute_script("return document.body.scrollHeight")
        for _ in range(3):  # Max 3 scrolls
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

        # Multi-strategy extraction
        for field, selector in extraction_plan['selectors'].items():
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if not elements:
                elements = driver.find_elements(By.XPATH, selector)

            values = []
            for el in elements:
                content = el.text.strip() or el.get_attribute('innerHTML').strip()
                if content:
                    values.append(content)

            result['data'][field] = values if len(values) > 1 else values[0] if values else None

        result["screenshot"] = base64.b64encode(
            driver.get_screenshot_as_png()).decode('utf-8')

    except Exception as e:
        result.update({
            "status": "error",
            "message": str(e),
            "screenshot": base64.b64encode(
                driver.get_screenshot_as_png()).decode('utf-8') if driver else ""
        })

    finally:
        if driver:
            driver.quit()

    return result


@app.route('/automate', methods=['POST'])
def automation_handler():
    """Handle automation requests with enhanced capabilities."""
    data = request.json
    try:
        if 'command' in data:
            instructions = generate_automation_instructions(data['command'])
            result = execute_browser_automation(instructions)
            return jsonify({
                "original_command": data['command'],
                "generated_steps": instructions,
                "execution_result": result
            })
        elif 'steps' in data:
            result = execute_browser_automation(data)
            return jsonify(result)
        else:
            return jsonify({"error": "Invalid request format"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/extract', methods=['POST'])
def extraction_handler():
    """Handle data extraction requests."""
    data = request.json
    try:
        if 'command' in data:
            extraction_plan = generate_extraction_plan(data['command'])
        elif 'url' in data:
            extraction_plan = data
        else:
            return jsonify({"error": "Invalid request format"}), 400

        result = execute_extraction(extraction_plan)
        return jsonify({
            "original_request": data,
            "extraction_result": result
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)