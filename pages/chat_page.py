import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from utils import config
from utils.wait_utils import wait_for_invisibility, wait_for_text_stable
from utils.formatters import sanitize_text
from typing import List
import os
from selenium.webdriver.support import expected_conditions as EC



class ChatPage:
    def __init__(self, driver, logger=None):
        self.driver = driver
        self.wait = WebDriverWait(driver, config.LONG_WAIT)
        self.logger = logger

                # store last prompt timestamp and last prompt text
        self.last_prompt = None
        self._sent_ts = None

        # common short-progress/interim phrases the model emits while aggregating
        self._interim_phrases = [
            "let me check", "just a moment", "one moment", "searching", "fetching",
            "i'm checking", "let me look", "loading", "processing", "give me a moment",
            "please wait"
        ]


        # Locators
        self.input = (By.XPATH, "//p[@class='is-empty is-editor-empty' or @contenteditable='true' or @role='textbox' or //textarea]")
        self.send_btn = (By.XPATH, "//button[@id='send-message-button' or contains(., 'Send') or @aria-label='Send']")
        self.spinner = (By.CSS_SELECTOR, "[data-testid='loading'], .typing, .spinner, .loader")
        self.container = (By.CSS_SELECTOR, "[data-testid='conversation'], .messages, .chat-history, [role='log']")

        # Candidate selectors for assistant messages (broad on purpose)
        self.ai_message_candidates = [
            (By.XPATH,"(//div[starts-with(@id, 'message-') and not(contains(@class,'user-message'))])[last()]"),
            (By.CSS_SELECTOR, "div[data-testid='assistant-message']"),
            (By.CSS_SELECTOR, "div.message.ai-response"),
            (By.CSS_SELECTOR, "div[class*='assistant'] p"),
            (By.CSS_SELECTOR, "div[role='log'] div.message"),
            (By.CSS_SELECTOR, ".chat-message.bot, .chat-message.ai"),
            (By.CSS_SELECTOR, "div[class*='message']"),
            (By.CSS_SELECTOR, "p[data-testid*='message']"),
        ]

    def _ai_elements(self) -> List:
        """
        Return the first non-empty set of assistant message elements.
        """
        for sel in self.ai_message_candidates:
            try:
                els = self.driver.find_elements(*sel)
                if els:
                    return els
            except StaleElementReferenceException:
                continue
        return []

    def _expand_more(self, container):
        """
        Expand 'Read more'/'Show more' buttons inside the latest AI message block.
        """
        try:
            more_buttons = container.find_elements(
                By.XPATH,
                ".//button[contains(., 'Read more') or contains(., 'Show more') or contains(., 'See more')]"
            )
            for btn in more_buttons:
                try:
                    if btn.is_displayed() and btn.is_enabled():
                        btn.click()
                        time.sleep(0.2)
                except Exception:
                    continue
        except Exception:
            pass

    def is_ready(self) -> bool:
        """
        Check that the chat box input is ready.
        """
        try:
            self.wait.until(EC.visibility_of_element_located(self.input))
            if self.logger:
                self.logger.info(sanitize_text("Chat input box is visible"), extra={"step": "is_ready"})
            return True
        except TimeoutException:
            if self.logger:
                self.logger.error(sanitize_text("Chat input box not found"), extra={"step": "is_ready"})
            return False

    def send_message(self, text: str):
        """
        Send a prompt to the chatbot (robust handling for contenteditable).
        Stores the last prompt so we can resend if session times out and logs send time.
        """
        import time

        self.last_prompt = text

        try:
            el = self.wait.until(EC.element_to_be_clickable(self.input))
        except Exception as e:
            if self.logger:
                self.logger.error(sanitize_text(f"Could not locate clickable input: {e}"), extra={"step": "send_message"})
            return

        sent_ok = False
        try:
            el.click()
            try:
                self.driver.execute_script("arguments[0].innerText = '';", el)
            except Exception:
                pass

            el.send_keys(text)
            el.send_keys("\n")
            sent_ok = True
            if self.logger:
                self.logger.info(sanitize_text(f"Sent text via send_keys: {text[:120]}"), extra={"step": "send_message"})
        except Exception:
            js = """
            const el = arguments[0];
            const text = arguments[1];
            el.focus();
            if ('value' in el) el.value = text;
            el.innerText = text;
            el.dispatchEvent(new InputEvent('input', {bubbles: true}));
            """
            try:
                self.driver.execute_script(js, el, text)
                sent_ok = True
                if self.logger:
                    self.logger.info(sanitize_text(f"Sent text via JS fallback: {text[:120]}"), extra={"step": "send_message"})
            except Exception as e:
                if self.logger:
                    self.logger.error(sanitize_text(f"JS fallback failed: {e}"), extra={"step": "send_message"})

            try:
                el.send_keys("\n")
            except Exception:
                pass

        # Finally: click send button if available (some UIs require explicit click)
        try:
            btn = WebDriverWait(self.driver, 2).until(EC.element_to_be_clickable(self.send_btn))
            try:
                btn.click()
                sent_ok = True
                if self.logger:
                    self.logger.info("Clicked send button", extra={"step": "send_message"})
            except Exception:
                if self.logger:
                    self.logger.debug("Clicked send button attempt failed; relying on Enter", extra={"step": "send_message"})
        except Exception:
            if self.logger:
                self.logger.debug("Send button not clickable or not present; relying on Enter", extra={"step": "send_message"})

        try:
            self._sent_ts = time.time()
            if self.logger:
                self.logger.info(
                    {"event": "prompt_sent", "prompt_len": len(text), "prompt_preview": sanitize_text(text)[:120]},
                    extra={"step": "send_message", "ts": self._sent_ts}
                )
        except Exception:
            pass

        if not sent_ok and self.logger:
            self.logger.warning("Prompt send may have failed (no confirmed send action)", extra={"step": "send_message"})

    def wait_for_ai_response(self, timeout: int = 60, min_acceptable_len: int = None) -> str:
        """
        Robust wait for AI response with special handling for short/interim replies.
        Returns sanitized final text (longest observed snapshot).
        """
        # use config defaults if not provided
        if min_acceptable_len is None:
            min_acceptable_len = getattr(config, "MIN_ACCEPTABLE_LEN", 80)

        poll = getattr(config, "POLL_INTERVAL", 0.25)
        extra_wait = getattr(config, "EXTRA_WAIT_AFTER_SHORT", 8)
        max_extra = getattr(config, "MAX_EXTRA_WAIT", 30)

        start = time.time()
        end = start + timeout

        container_sel = "[data-testid='conversation'], .messages, .chat-history, [role='log']"
        try:
            container = self.driver.find_element(By.CSS_SELECTOR, container_sel)
        except Exception:
            container = None

        # baseline child count
        baseline = 0
        if container:
            try:
                baseline = int(self.driver.execute_script("return arguments[0].children.length || 0;", container))
            except Exception:
                baseline = 0

        # start_index indicates where new assistant blocks begin
        start_index = baseline

        best_text = ""
        last_growth_ts = None
        stable_window = 2.5
        started = False
        stream_start = None
        max_stream = max(90, timeout)  # don't prematurely kill streams

        def perf_resource_count():
            """Return count of performance resources if available, otherwise -1."""
            try:
                return int(self.driver.execute_script(
                    "return (window.performance && window.performance.getEntriesByType) ? window.performance.getEntriesByType('resource').length : -1"
                ))
            except Exception:
                return -1

        initial_resource_count = perf_resource_count()

        while time.time() < end:
            try:
                # detect spinner presence
                try:
                    spinner_present = bool(self.driver.find_elements(*self.spinner))
                except Exception:
                    spinner_present = False

                # child count
                curr_count = 0
                if container:
                    try:
                        curr_count = int(self.driver.execute_script("return arguments[0].children.length || 0;", container))
                    except Exception:
                        curr_count = 0

                elements = self._ai_elements()
                combined = "\n\n".join(e.text.strip() for e in elements if e.text.strip()).strip() if elements else ""

                # interim phrase detection
                try:
                    lower = combined.lower()
                except Exception:
                    lower = ""
                is_interim_phrase = any(p in lower for p in getattr(self, "_interim_phrases", []))

                # detect start
                if not started:
                    if curr_count > baseline:
                        started = True
                        start_index = baseline
                        stream_start = time.time()
                        last_growth_ts = None
                    elif combined and len(combined) >= 5 and combined != best_text:
                        # some UIs stream by editing the last block
                        started = True
                        start_index = max(0, baseline - 1)
                        stream_start = time.time()
                        last_growth_ts = None

                if started:
                    # update longest snapshot
                    if len(combined) > len(best_text):
                        best_text = combined
                        last_growth_ts = time.time()
                    else:
                        # stable period reached
                        if last_growth_ts and (time.time() - last_growth_ts) >= stable_window:
                            # wait for spinner to disappear (best-effort)
                            if spinner_present:
                                try:
                                    WebDriverWait(self.driver, 3).until(EC.invisibility_of_element_located(self.spinner))
                                except Exception:
                                    pass

                            final = sanitize_text(best_text)
                            # consider interim phrases also as indication to wait
                            if (len(final) < min_acceptable_len) or is_interim_phrase:
                                # monitor for additional growth up to max_extra total
                                extra_deadline = time.time() + min(max_extra, extra_wait)
                                if self.logger:
                                    self.logger.warning(
                                        {"event": "short_or_interim_detected", "chars": len(final), "is_interim": is_interim_phrase},
                                        extra={"step": "wait_for_ai_response"}
                                    )
                                prev_resource_count = perf_resource_count()
                                while time.time() < extra_deadline:
                                    time.sleep(poll)
                                    try:
                                        elements2 = self._ai_elements()
                                        combined2 = "\n\n".join(e.text.strip() for e in elements2[start_index:] if e.text.strip()).strip() if elements2 else ""
                                    except Exception:
                                        combined2 = combined
                                    # resource activity check
                                    curr_resource_count = perf_resource_count()
                                    resource_activity = (curr_resource_count > prev_resource_count) if (prev_resource_count >= 0 and curr_resource_count >= 0) else False

                                    # spinner check
                                    try:
                                        spinner_now = bool(self.driver.find_elements(*self.spinner))
                                    except Exception:
                                        spinner_now = False

                                    # update best_text if grown
                                    if len(combined2) > len(best_text):
                                        best_text = combined2
                                        prev_resource_count = curr_resource_count
                                        last_growth_ts = time.time()
                                        if self.logger:
                                            self.logger.info({"event": "observed_growth", "chars": len(best_text)}, extra={"step": "wait_for_ai_response"})
                                    else:
                                        # if resource activity or spinner present, continue waiting
                                        if resource_activity or spinner_now:
                                            prev_resource_count = curr_resource_count
                                            continue
                                        # else no activity; break early
                                        break

                                final2 = sanitize_text(best_text)
                                if self.logger:
                                    # log response timing if we had a sent timestamp
                                    received_ts = time.time()
                                    delay = None
                                    try:
                                        if getattr(self, "_sent_ts", None):
                                            delay = round(received_ts - self._sent_ts, 2)
                                    except Exception:
                                        delay = None
                                    self.logger.info(
                                        {"event": "response_received", "chars": len(final2), "delay_s": delay},
                                        extra={"step": "wait_for_ai_response"}
                                    )
                                # save debug if still small (optional)
                                if len(final2) < min_acceptable_len:
                                    try:
                                        run_id = os.environ.get("RUN_ID", "local")
                                        idx = int(time.time())
                                        png = f"{config.SCREENSHOT_DIR}/debug-{run_id}-{idx}.png"
                                        html = f"{config.SCREENSHOT_DIR}/debug-{run_id}-{idx}.html"
                                        os.makedirs(config.SCREENSHOT_DIR, exist_ok=True)
                                        try:
                                            self.driver.save_screenshot(png)
                                        except Exception:
                                            pass
                                        try:
                                            with open(html, "w", encoding="utf-8") as fh:
                                                fh.write(self.driver.page_source)
                                        except Exception:
                                            pass
                                        if self.logger:
                                            self.logger.info(f"Saved debug artifacts for short response: {png}, {html}", extra={"step": "wait_for_ai_response"})
                                    except Exception:
                                        pass
                                return final2

                            # normal return
                            if self.logger:
                                received_ts = time.time()
                                delay = None
                                try:
                                    if getattr(self, "_sent_ts", None):
                                        delay = round(received_ts - self._sent_ts, 2)
                                except Exception:
                                    delay = None
                                self.logger.info(
                                    {"event": "response_received", "chars": len(final), "delay_s": delay},
                                    extra={"step": "wait_for_ai_response"}
                                )
                            return final

                    # streaming safety cap
                    if stream_start and (time.time() - stream_start) > max_stream:
                        if self.logger:
                            self.logger.warning("Stream exceeded max_stream, returning best snapshot", extra={"step": "wait_for_ai_response"})
                        return sanitize_text(best_text)

                time.sleep(poll)

            except StaleElementReferenceException:
                time.sleep(0.15)
            except Exception as e:
                if self.logger:
                    self.logger.debug(f"wait_for_ai_response exception: {e}", extra={"step": "wait_for_ai_response"})
                time.sleep(0.25)

        # timeout fallback
        if self.logger:
            self.logger.warning("Timeout reached — returning best observed response", extra={"step": "wait_for_ai_response"})
        return sanitize_text(best_text)

        


    def container_direction(self) -> str:
        """
        Detect whether chat layout is Left-to-Right (LTR) or Right-to-Left (RTL).
        """
        direction = ""
        try:
            el = self.wait.until(EC.presence_of_element_located(self.container))
            direction = (el.get_attribute("dir") or el.value_of_css_property("direction") or "").lower()
        except (NoSuchElementException, TimeoutException):
            try:
                body = self.driver.find_element(By.TAG_NAME, "body")
                direction = (body.get_attribute("dir") or body.value_of_css_property("direction") or "").lower()
            except Exception:
                direction = ""

        if not direction:
            direction = "ltr"

        if self.logger:
            self.logger.info(sanitize_text(f"Chat container direction detected: {direction}"), extra={"step": "container_direction"})
        return direction

    def start_new_chat(self, timeout: int = 8) -> bool:
        """
        Click the UI's 'New Chat' control to open a fresh conversation.
        Returns True if the click (or JS click fallback) was attempted, False otherwise.
        """
        try:
            btn = self.driver.find_element(By.XPATH, "//a[@id='sidebar-new-chat-button' or contains(., 'New chat')]")
            if not btn or not btn.is_displayed():
                if self.logger:
                    self.logger.warning("New Chat button not visible", extra={"step": "start_new_chat"})
                return False

            try:
                btn.click()
            except Exception:
                try:
                    self.driver.execute_script("arguments[0].click();", btn)
                except Exception:
                    if self.logger:
                        self.logger.error("Failed to click 'New Chat' button", extra={"step": "start_new_chat"})
                    return False

            try:
                WebDriverWait(self.driver, timeout).until(
                    lambda d: d.find_element(By.CSS_SELECTOR, "textarea, div[contenteditable='true']")
                )
            except Exception:
                if self.logger:
                    self.logger.warning("Chat input not detected after New Chat click — continuing", extra={"step": "start_new_chat"})

            if self.logger:
                self.logger.info("New chat opened", extra={"step": "start_new_chat"})
            return True
        except Exception as e:
            if self.logger:
                self.logger.error(sanitize_text(f"Error clicking 'New Chat' button: {e}"), extra={"step": "start_new_chat"})
            return False
