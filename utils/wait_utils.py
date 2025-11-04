# utils/wait_utils.py
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from typing import Iterable, Tuple
from utils import openai_validator, config

def wait_for_element(driver, locator, timeout=10):
    return WebDriverWait(driver, timeout).until(EC.presence_of_element_located(locator))

def wait_for_invisibility(driver, locator, timeout=5):
    return WebDriverWait(driver, timeout).until(EC.invisibility_of_element_located(locator))

def wait_for_text_stable(driver, locator, timeout=30, stable_period=1.5, poll_interval=0.25):
    """
    Wait until text at locator stabilizes (unchanged) for stable_period seconds.
    Returns last observed text.
    """
    end = time.time() + timeout
    last = None
    stable_since = None
    while time.time() < end:
        try:
            el = driver.find_element(*locator)
            text = el.text.strip()
        except Exception:
            text = ""
        if text == last:
            if stable_since is None:
                stable_since = time.time()
            elif (time.time() - stable_since) >= stable_period:
                return text
        else:
            last = text
            stable_since = None
        time.sleep(poll_interval)
    return last or ""





