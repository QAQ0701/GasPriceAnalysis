import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time

options = Options()
options.add_argument("--disable-blink-features=AutomationControlled")
# options.add_argument("--headless=new")  # optional: remove if you want to see browser
options.add_argument("--no-sandbox")
options.add_argument("--disable-gpu")

driver = webdriver.Chrome(options=options)

try:
    url = "https://www.gasbuddy.com/home"
    driver.get(url)
    time.sleep(5)

    # Extract gbcsrf token from JavaScript
    try:
        gbcsrf = driver.execute_script("return window.gbcsrf;")
        if not gbcsrf:
            raise ValueError("gbcsrf token not found in page.")
        print(f"gbcsrf token found: {gbcsrf}")
    except Exception as e:
        print("Could not retrieve gbcsrf:", e)
        gbcsrf = None

    # Dump cookies
    cookies = driver.get_cookies()

    # Save cookies + gbcsrf in a single JSON object
    data_to_save = {"cookies": cookies, "gbcsrf": gbcsrf}
    with open("./data/cookies/my_cookies.json", "w", encoding="utf-8") as f:
        json.dump(data_to_save, f, indent=2)
    print("Cookies + gbcsrf saved to my_cookies.json")

finally:
    driver.quit()
