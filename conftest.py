# # conftest.py

# import os
# import pytest
# from selenium import webdriver
# from selenium.webdriver.chrome.service import Service
# from selenium.webdriver.chrome.options import Options
# from webdriver_manager.chrome import ChromeDriverManager
# from utils import config


# @pytest.fixture(scope="session")
# def driver():
#     """Setup and teardown for Selenium WebDriver."""
#     chrome_options = Options()
#     chrome_options.add_argument("--start-maximized")
#     chrome_options.add_argument("--disable-notifications")
#     chrome_options.add_argument("--disable-infobars")
#     chrome_options.add_argument("--disable-popup-blocking")

#     # Optional: Run headless in CI
#     if os.getenv("HEADLESS", "false").lower() == "true":
#         chrome_options.add_argument("--headless")

#     service = Service(ChromeDriverManager().install())
#     driver = webdriver.Chrome(service=service, options=chrome_options)
#     driver.get(config.BASE_URL)

#     yield driver  # Provide the driver to tests
#     driver.quit()


# @pytest.hookimpl(hookwrapper=True)
# def pytest_runtest_makereport(item, call):
#     """Capture screenshot for failed tests."""
#     outcome = yield
#     rep = outcome.get_result()
#     if rep.when == "call" and rep.failed:
#         driver = item.funcargs.get("driver")
#         if driver:
#             screenshot_path = os.path.join(config.SCREENSHOT_DIR, f"{item.name}.png")
#             driver.save_screenshot(screenshot_path)
#             print(f"📸 Screenshot saved: {screenshot_path}")

# conftest.py

import os
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from utils import config


@pytest.fixture(params=["desktop", "mobile"], scope="session")
def driver(request):
    """Setup and teardown for Selenium WebDriver (desktop + mobile)."""
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
        print("📱 Running in mobile emulation mode (iPhone 12)")
    else:
        chrome_options.add_argument("--start-maximized")
        print("💻 Running in desktop mode")

    # Optional: headless mode for CI
    if os.getenv("HEADLESS", "false").lower() == "true":
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.get(config.BASE_URL)

    yield driver  # Provide the driver to tests

    print(f"🧹 Closing {mode} driver session")
    driver.quit()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Capture screenshots for failed tests."""
    outcome = yield
    rep = outcome.get_result()
    if rep.when == "call" and rep.failed:
        driver = item.funcargs.get("driver")
        if driver:
            os.makedirs(config.SCREENSHOT_DIR, exist_ok=True)
            screenshot_path = os.path.join(config.SCREENSHOT_DIR, f"{item.name}.png")
            driver.save_screenshot(screenshot_path)
            print(f"📸 Screenshot saved: {screenshot_path}")
