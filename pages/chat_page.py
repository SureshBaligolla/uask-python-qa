


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

        # Candidate selectors for assistant messages (broad on purpose)
        self.ai_message_candidates = [
            (By.CSS_SELECTOR, "div[data-testid='assistant-message']"),
            (By.CSS_SELECTOR, "div.message.ai-response"),
            (By.CSS_SELECTOR, "div[class*='assistant'] p"),
            (By.CSS_SELECTOR, "div[role='log'] div.message"),
            (By.CSS_SELECTOR, ".chat-message.bot, .chat-message.ai"),
            (By.CSS_SELECTOR, "div[class*='message']"),
            (By.CSS_SELECTOR, "p[data-testid*='message']"),
        ]

    # ---------- Utilities ----------

    def _ai_elements(self):
        """Return the first non-empty set of assistant message elements."""
        for sel in self.ai_message_candidates:
            try:
                els = self.driver.find_elements(*sel)
                if els:
                    return els
            except StaleElementReferenceException:
                continue
        return []

    def _expand_more(self, container):
        """Expand 'Read more'/'Show more' buttons inside the latest AI message block."""
        try:
            more_buttons = container.find_elements(
                By.XPATH,
                ".//button[contains(., 'Read more') or contains(., 'Show more') or contains(., 'See more')]"
            )
            for btn in more_buttons:
                try:
                    if btn.is_displayed() and btn.is_enabled():
                        btn.click()
                        time.sleep(0.25)
                except Exception:
                    pass
        except Exception:
            pass

    # ---------- Public API ----------

    def is_ready(self):
        """Check that the chat box input is ready."""
        try:
            self.wait.until(EC.visibility_of_element_located(self.input))
            print("✅ Chat input box is visible.")
            return True
        except TimeoutException:
            print("❌ Chat input box not found.")
            return False

    def send_message(self, text: str):
        """Send a prompt to the chatbot."""
        try:
            box = self.wait.until(EC.element_to_be_clickable(self.input))
            box.clear()
            box.send_keys(text)
            print(f"💬 Sent text: {text}")

            # Press Enter
            box.send_keys("\n")

            # Click Send if button exists
            try:
                btn = self.driver.find_element(*self.send_btn)
                if btn.is_displayed() and btn.is_enabled():
                    btn.click()
                    print("🖱️ Clicked send button.")
            except NoSuchElementException:
                pass

        except Exception as e:
            print(f"❌ Error sending message: {e}")

    def wait_for_ai_response(self, timeout: int = 30) -> str:
        """
        Capture the full AI response for the *current* prompt only.

        Strategy:
        - Record a baseline of existing assistant messages before the response starts.
        - Wait for new messages to appear or the last existing message to start changing.
        - Aggregate text from all *new* blocks since the baseline.
        - Never “shrink” if the DOM virtualizes on scroll: keep the longest snapshot seen.
        - Return when content hasn't grown for ~3 seconds.
        """
        start_time = time.time()
        end_time = start_time + timeout

        # Baseline snapshot (before new response)
        pre_elements = self._ai_elements()
        baseline_count = len(pre_elements)
        pre_last_text = pre_elements[-1].text.strip() if baseline_count else ""
        print(f"📌 Baseline messages: {baseline_count}")

        sequence_started = False
        start_index = baseline_count  # index of first new message when sequence starts

        best_text = ""                 # longest combined text observed (never shrinks)
        last_elements_count = baseline_count
        last_growth_ts = None          # when best_text last increased
        stable_window = 3.0            # seconds without growth to consider "done"

        while time.time() < end_time:
            try:
                # If there's a known spinner/typing indicator, pause briefly
                try:
                    if self.driver.find_elements(*self.spinner):
                        time.sleep(0.4)
                        continue
                except Exception:
                    pass

                elements = self._ai_elements()
                curr_count = len(elements)

                # Detect the start of a new response sequence
                if not sequence_started:
                    if curr_count > baseline_count:
                        sequence_started = True
                        start_index = baseline_count
                        last_growth_ts = None
                        print("🆕 New AI response sequence detected (new blocks appended).")
                        # small pause to let first chunk render
                        time.sleep(0.4)
                    else:
                        # Some UIs stream by editing the last existing block
                        curr_last = elements[-1].text.strip() if curr_count else ""
                        if curr_count == baseline_count and curr_last and curr_last != pre_last_text:
                            sequence_started = True
                            start_index = max(0, baseline_count - 1)
                            last_growth_ts = None
                            print("🆕 New AI response detected (last block is streaming).")
                            time.sleep(0.4)

                if not sequence_started:
                    time.sleep(0.25)
                    continue

                # Expand "Read more" within newest block if present
                try:
                    if elements:
                        self._expand_more(elements[-1])
                except Exception:
                    pass

                # Build combined text from new blocks only
                combined_now = "\n\n".join(
                    e.text.strip() for e in elements[start_index:] if e.text.strip()
                ).strip()

                # If DOM virtualization temporarily drops earlier chunks, never shrink:
                if len(combined_now) > len(best_text):
                    best_text = combined_now
                    last_growth_ts = time.time()
                    print(f"⏳ AI response growing: {len(best_text)} chars, blocks={curr_count - start_index}")
                else:
                    # No growth — check stability window
                    if last_growth_ts and (time.time() - last_growth_ts) >= stable_window:
                        print(f"✅ Final AI response captured ({len(best_text)} chars).")
                        return best_text

                # Keep an eye on block count changes too (informational)
                if curr_count != last_elements_count:
                    last_elements_count = curr_count

            except StaleElementReferenceException:
                # DOM re-render — brief pause and retry
                time.sleep(0.2)
            except Exception as e:
                print(f"⚠️ Error capturing AI response: {e}")
                time.sleep(0.3)

            time.sleep(0.25)

        print(f"⚠️ Timeout reached — returning best observed response ({len(best_text)} chars).")
        return best_text

    def container_direction(self):
        """Detect whether chat layout is Left-to-Right (LTR) or Right-to-Left (RTL)."""
        try:
            el = self.wait.until(EC.presence_of_element_located(self.container))
            direction = (el.get_attribute("dir") or el.value_of_css_property("direction") or "").lower()
        except (NoSuchElementException, TimeoutException):
            try:
                body = self.driver.find_element(By.TAG_NAME, "body")
                direction = (body.get_attribute("dir") or body.value_of_css_property("direction") or "").lower()
            except NoSuchElementException:
                direction = ""

        if not direction:
            direction = "ltr"

        print(f"🧭 Chat container direction detected: {direction}")
        return direction