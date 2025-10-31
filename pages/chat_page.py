# pages/chat_page.py

import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from utils import config


class ChatPage:
    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, config.LONG_WAIT)

        # Locators
        self.input = (By.XPATH, "//p[@class='is-empty is-editor-empty']")
        self.send_btn = (By.XPATH, "//button[@id='send-message-button']")
        self.spinner = (By.CSS_SELECTOR, "[data-testid='loading'], .typing, .spinner, .loader")
        self.container = (By.CSS_SELECTOR, "[data-testid='conversation'], .messages, .chat-history, [role='log']")

        # Possible AI message selectors
        self.ai_message_candidates = [
            (By.CSS_SELECTOR, "div[data-testid='assistant-message']"),
            (By.CSS_SELECTOR, "div.message.ai-response"),
            (By.CSS_SELECTOR, "div[class*='assistant'] p"),
            (By.CSS_SELECTOR, "div[role='log'] div.message"),
            (By.CSS_SELECTOR, ".chat-message.bot, .chat-message.ai"),
        ]

    def is_ready(self):
        """Confirm chat box is ready."""
        try:
            self.wait.until(EC.visibility_of_element_located(self.input))
            print("✅ Chat input box is visible.")
            return True
        except TimeoutException:
            print("❌ Chat input box not found.")
            return False

    def send_message(self, text):
        """Send a prompt to the chatbot."""
        try:
            box = self.wait.until(EC.element_to_be_clickable(self.input))
            box.clear()
            box.send_keys(text)
            print(f"💬 Sent text: {text}")

            # Try Enter first
            box.send_keys("\n")

            # Try clicking Send button if visible
            try:
                btn = self.driver.find_element(*self.send_btn)
                if btn.is_displayed():
                    btn.click()
                    print("🖱️ Clicked send button.")
            except NoSuchElementException:
                pass

        except Exception as e:
            print(f"❌ Error sending message: {e}")
    
    def wait_for_ai_response(self, timeout=8):
        """Wait for AI message to appear and ensure full message is visible."""
        end_time = time.time() + timeout
        last_text = ""

        while time.time() < end_time:
            try:
                # Skip spinner if message is still loading
                if self.driver.find_elements(*self.spinner):
                    time.sleep(0.5)
                    continue

                # Scroll down to make sure full chat message is rendered
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(0.5)

                # Try each possible chat message selector
                for sel in self.ai_message_candidates:
                    elements = self.driver.find_elements(*sel)
                    if elements:
                        txt = elements[-1].text.strip()
                        if txt and txt != last_text:
                            # If message grows in size (more text appears), update last_text
                            last_text = txt
                            # Wait briefly to see if message continues to expand
                            time.sleep(0.8)
                            continue
                        if txt:
                            print(f"🤖 AI Response detected: {txt}")
                            return txt
            except (StaleElementReferenceException, NoSuchElementException):
                pass

            time.sleep(0.4)

        print(f"⚠️ No AI response within timeout. Returning last known: {last_text}")
        return last_text


    # def wait_for_ai_response(self, timeout=15):
    #     """Wait for AI message to appear."""
    #     end_time = time.time() + timeout
    #     last_text = ""

    #     while time.time() < end_time:
    #         try:
    #             # Skip spinner
    #             if self.driver.find_elements(*self.spinner):
    #                 time.sleep(0.5)
    #                 continue

    #             # Try each selector
    #             for sel in self.ai_message_candidates:
    #                 elements = self.driver.find_elements(*sel)
    #                 if elements:
    #                     txt = elements[-1].text.strip()
    #                     if txt:
    #                         print(f"🤖 AI Response detected: {txt}")
    #                         return txt
    #                     last_text = txt
    #         except (StaleElementReferenceException, NoSuchElementException):
    #             pass

    #         time.sleep(0.4)

    #     print(f"⚠️ No AI response within timeout. Returning last known: {last_text}")
    #     return last_text




    def input_cleared(self):
        """Verify input is cleared after sending."""
        try:
            val = self.driver.find_element(*self.input).get_attribute("value")
            return val == "" or val is None
        except NoSuchElementException:
            return False

    # def container_direction(self):
    #     """Check if chat direction is LTR/RTL."""
    #     try:
    #         el = self.driver.find_element(*self.container)
    #         direction = el.get_attribute("dir") or el.value_of_css_property("direction")
    #         return direction
    #     except NoSuchElementException:
    #         body = self.driver.find_element(By.TAG_NAME, "body")
    #         return body.get_attribute("dir") or body.value_of_css_property("direction")
        
    def container_direction(self):
        """Detect whether chat layout is Left-to-Right (LTR) or Right-to-Left (RTL)."""
        try:
            # First, check if the main chat container exists
            el = self.wait.until(EC.presence_of_element_located(self.container))
            direction = (el.get_attribute("dir") or el.value_of_css_property("direction") or "").lower()
        except (NoSuchElementException, TimeoutException):
            # Fallback to body if container not found
            try:
                body = self.driver.find_element(By.TAG_NAME, "body")
                direction = (body.get_attribute("dir") or body.value_of_css_property("direction") or "").lower()
            except NoSuchElementException:
                direction = ""

        # Default to LTR if no direction found
        if not direction:
            direction = "ltr"

        print(f"🧭 Chat container direction detected: {direction}")
        return direction
