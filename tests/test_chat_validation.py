# tests/test_chat_validation.py
import json
import pytest
import allure
import time
import time
import allure
from utils import wait_utils as waits
from pages.login_page import LoginPage
from pages.chat_page import ChatPage
from utils import openai_validator, config

from pages.login_page import LoginPage
from pages.chat_page import ChatPage
from utils import openai_validator, config
from utils.formatters import sanitize_text

@pytest.mark.parametrize("testdata", json.load(open("test_data/test-data.json", encoding="utf-8")))
def test_simple_chat_responses(driver, logger, run_id, testdata):
    """
    Validate chatbot responses semantically using OpenAI embeddings.
    Also validate multilingual behavior: English (LTR) and Arabic (RTL).
    """
    login_page = LoginPage(driver)
    chat_page = ChatPage(driver, logger=logger)

    assert login_page.is_loaded(), "Login page did not load properly"
    login_page.login()
    assert chat_page.is_ready(), "Chatbox not ready after login"

    # ENGLISH
    prompt_en = testdata.get("prompt_en")
    expected_en = testdata.get("expected_en")

    if prompt_en and expected_en:
        logger.info(sanitize_text("Sending English prompt"), extra={"step": "test_simple_chat_responses", "prompt": prompt_en[:120]})
        chat_page.send_message(prompt_en)
        actual_en = chat_page.wait_for_ai_response(timeout=30)

        # Retry once if incomplete
        if not actual_en or len(actual_en.strip()) < 50:
            logger.warning("English response seems incomplete, retrying", extra={"step": "test_simple_chat_responses"})
            time.sleep(1)
            extra = chat_page.wait_for_ai_response(timeout=10)
            if extra and len(extra) > len(actual_en or ""):
                actual_en = extra

        assert actual_en and actual_en.strip(), "No AI response captured for English prompt"

        similarity_en = openai_validator.calculate_similarity(expected_en, actual_en)

        logger.info(sanitize_text(f"English similarity: {similarity_en}"), extra={"step": "test_simple_chat_responses", "similarity": similarity_en})
        with allure.step("Attach English response details"):
            allure.attach(sanitize_text(prompt_en), name="English Prompt", attachment_type=allure.attachment_type.TEXT)
            allure.attach(sanitize_text(expected_en), name="Expected English Response", attachment_type=allure.attachment_type.TEXT)
            allure.attach(sanitize_text(actual_en), name="Actual English Response", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(round(similarity_en, 3)), name="English Similarity Score", attachment_type=allure.attachment_type.TEXT)
            if similarity_en < config.SIMILARITY_THRESHOLD_EN:
                try:
                    allure.attach(driver.get_screenshot_as_png(), name="English Screenshot", attachment_type=allure.attachment_type.PNG)
                except Exception:
                    pass

        assert similarity_en >= config.SIMILARITY_THRESHOLD_EN, f"Similarity too low ({similarity_en:.3f}) for prompt: {prompt_en}"

    # ARABIC
    prompt_ar = testdata.get("prompt_ar")
    expected_ar = testdata.get("expected_ar")

    if prompt_ar and expected_ar:
        logger.info(sanitize_text("Sending Arabic prompt"), extra={"step": "test_simple_chat_responses", "prompt_ar": prompt_ar[:120]})
        chat_page.send_message(prompt_ar)
        actual_ar = chat_page.wait_for_ai_response(timeout=35)

        if not actual_ar or len(actual_ar.strip()) < 50:
            logger.warning("Arabic response seems incomplete, retrying", extra={"step": "test_simple_chat_responses"})
            time.sleep(1)
            extra = chat_page.wait_for_ai_response(timeout=12)
            if extra and len(extra) > len(actual_ar or ""):
                actual_ar = extra

        assert actual_ar and actual_ar.strip(), "No AI response captured for Arabic prompt"

        similarity_ar = openai_validator.calculate_similarity(expected_ar, actual_ar)

        logger.info(sanitize_text(f"Arabic similarity: {similarity_ar}"), extra={"step": "test_simple_chat_responses", "similarity": similarity_ar})
        with allure.step("Attach Arabic response details"):
            allure.attach(sanitize_text(prompt_ar), name="Arabic Prompt", attachment_type=allure.attachment_type.TEXT)
            allure.attach(sanitize_text(expected_ar), name="Expected Arabic Response", attachment_type=allure.attachment_type.TEXT)
            allure.attach(sanitize_text(actual_ar), name="Actual Arabic Response", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(round(similarity_ar, 3)), name="Arabic Similarity Score", attachment_type=allure.attachment_type.TEXT)
            if similarity_ar < config.SIMILARITY_THRESHOLD_AR:
                try:
                    allure.attach(driver.get_screenshot_as_png(), name="Arabic Screenshot", attachment_type=allure.attachment_type.PNG)
                except Exception:
                    pass

        assert similarity_ar >= config.SIMILARITY_THRESHOLD_AR, f"Similarity too low ({similarity_ar:.3f}) for Arabic prompt: {prompt_ar}"

    allure.attach(json.dumps(testdata, indent=2, ensure_ascii=False), name="Test Data", attachment_type=allure.attachment_type.JSON)


def test_security_input_sanitization(driver):
    login_page = LoginPage(driver)
    chat_page = ChatPage(driver)

    login_page.login()
    assert chat_page.is_ready(), "Chatbox not ready"

    malicious_input = "<script>alert('xss')</script>"
    chat_page.send_message(malicious_input)
    response = chat_page.wait_for_ai_response(timeout=25, min_acceptable_len=20)

    assert "<script" not in response.lower(), "Chatbot returned raw <script> content"
    assert "alert(" not in response.lower(), "Chatbot returned JS payloads"

    allure.attach(malicious_input, name="Malicious Input", attachment_type=allure.attachment_type.TEXT)
    allure.attach(response, name="Chatbot Response", attachment_type=allure.attachment_type.TEXT)


