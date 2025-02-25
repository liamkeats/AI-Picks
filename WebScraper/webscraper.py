import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# Get the current directory where the script is located
script_dir = os.path.dirname(os.path.realpath(__file__))

# Set the path to chromedriver.exe in the same directory as the script
chromedriver_path = os.path.join(script_dir, "chromedriver.exe")

# Initialize the service with the chromedriver path
service = Service(executable_path=chromedriver_path)
driver = webdriver.Chrome(service=service)

# Opening website
driver.get("https://google.com")

input_element = driver.find_element(By.CLASS_NAME, "gLFyf")
input_element.clear()
input_element.send_keys("tech with tim" + Keys.ENTER)


time.sleep(100)

driver.quit()
