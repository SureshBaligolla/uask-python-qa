# tests/test_ui_load.py
def test_chat_widget_loads(driver):
    from pages.login_page import LoginPage
    from pages.chat_page import ChatPage

    login = LoginPage(driver)
    chat = ChatPage(driver)

    assert login.is_loaded(), "❌ Login page failed to load"
    login.login()
    assert chat.is_ready(), "❌ Chat widget not visible"

    print("✅ Chat widget loaded correctly on:", driver.execute_script("return navigator.userAgent;"))


