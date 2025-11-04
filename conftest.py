# conftest.py
import os
import pytest
import time
import uuid
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from utils import config
from utils.logger import setup_logger
import allure

@pytest.fixture(scope="session")
def run_id():
    rid = time.strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:6]
    os.environ["RUN_ID"] = rid
    return rid

@pytest.fixture(scope="session")
def logger(run_id):
    logger = setup_logger(run_id)
    return logger

@pytest.fixture(params=["desktop", "mobile"], scope="session")
def driver(request, logger, run_id):
    """
    Setup and teardown for Selenium WebDriver (desktop + mobile).
    """
    chrome_options = Options()
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--disable-popup-blocking")

    mode = request.param

    if mode == "mobile":
        mobile_emulation = {
            "deviceMetrics": {"width": 390, "height": 844, "pixelRatio": 3.0},
            "userAgent": (
                "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1"
            )
        }
        chrome_options.add_experimental_option("mobileEmulation", mobile_emulation)
        logger.info("Running in mobile emulation mode", extra={"mode": "mobile", "run_id": run_id})
    else:
        chrome_options.add_argument("--start-maximized")
        logger.info("Running in desktop mode", extra={"mode": "desktop", "run_id": run_id})

    if os.getenv("HEADLESS", "false").lower() == "true":
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        logger.info("Headless mode enabled", extra={"run_id": run_id})

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.get(config.BASE_URL)

    yield driver

    logger.info(f"Closing {mode} driver session", extra={"mode": mode, "run_id": run_id})
    driver.quit()

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    Capture screenshots and attach run log for failed tests.
    """
    outcome = yield
    rep = outcome.get_result()
    if rep.when == "call" and rep.failed:
        driver = item.funcargs.get("driver")
        logger = item.funcargs.get("logger")
        run_id = os.environ.get("RUN_ID")
        if driver:
            os.makedirs(config.SCREENSHOT_DIR, exist_ok=True)
            screenshot_path = os.path.join(config.SCREENSHOT_DIR, f"{item.name}.png")
            driver.save_screenshot(screenshot_path)
            try:
                allure.attach.file(screenshot_path, name="screenshot", attachment_type=allure.attachment_type.PNG)
            except Exception:
                pass
        # Attach run log
        log_path = os.path.join("reports", f"run-{run_id}.log") if run_id else None
        if log_path and os.path.exists(log_path):
            try:
                allure.attach.file(log_path, name="run-log", attachment_type=allure.attachment_type.TEXT)
            except Exception:
                pass
