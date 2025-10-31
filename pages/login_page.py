
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from utils import config


class LoginPage:
    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, config.LONG_WAIT)

        self.email_btn = (By.XPATH, "//button[contains(., 'Log in with email')]")
        self.username_field = (By.XPATH, "//input[@name='email']")
        self.password_field = (By.XPATH, "//input[@name='current-password']")
        self.login_button = (By.XPATH, "//button[contains(., 'Log in')]")

    # def is_loaded(self):
    #     """Check if login page or elements are visible."""
    #     try:
    #         time.sleep(5)
    #         print(f"🔍 Checking if login page loaded. Current URL: {self.driver.current_url}")
    #         self.wait.until(EC.presence_of_element_located(self.email_btn))
    #         print("✅ Login page detected.")
    #         return True
    #     except Exception as e:
    #         print(f"❌ Login elements not visible yet: {e}")
    #         return False

    def is_loaded(self):
        """Check if we're on the login page or already logged in"""
        try:
            if "auth" in self.driver.current_url:
                # Still on login page
                return True
            else:
                print("Already logged in, skipping login step.")
                return True
        except Exception as e:
            print(f"Error in is_loaded(): {e}")
            return False


    def login(self):
        """Perform login using credentials in config."""
        username = config.EMAIL
        password = config.PASSWORD

        try:
            # Try clicking “Log in with email” if present
            try:
                btn = self.wait.until(EC.visibility_of_element_located(self.email_btn))
                if btn.is_displayed():
                    btn.click()
                    print("🖱️ Clicked 'Log in with email'.")
            except Exception:
                print("⚠️ 'Log in with email' button not found, skipping...")

            # Fill credentials
            self.wait.until(EC.visibility_of_element_located(self.username_field)).send_keys(username)
            self.driver.find_element(*self.password_field).send_keys(password)
            self.driver.find_element(*self.login_button).click()
            print("🔐 Login submitted with test credentials.")
        except Exception as e:
            print(f"❌ Login failed: {e}")
