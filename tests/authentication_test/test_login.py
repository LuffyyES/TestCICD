import unittest
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from config.constant import LANGUAGE_SETTINGS, CREDENTIALS
from selenium.webdriver.support.ui import WebDriverWait
from .base_test import BaseTest, ContinueOnFailureTestResult


class TestLogin(BaseTest):

    def __init__(self, methodName="runTest", language=None, browser=None):
        super().__init__(methodName, language, browser)

    def setUp(self):
        super().setUp()
        self.navigate_to_login_page()

    def tearDown(self):
        if hasattr(self, "driver"):
            self.driver.quit()

    def generic_login(self, username, password, expected_result="success"):
        try:
            self.enter_credentials(username, password)
            self.click_login_button()
            time.sleep(4)

            if expected_result == "success":
                time.sleep(4)
                self.verify_login(username)
            elif expected_result == "failure":
                self.handle_popup(LANGUAGE_SETTINGS[self.language]["errors"]["invalid_login"])
            else:
                return

        except Exception as e:
            self.fail(f"Login attempt failed: {str(e.msg)}")

    def test_01_EmptyFields(self):
        self.logger.info("Starting test_01_EmptyFields...")
        try:
            time.sleep(2)

            login_id_field = self.get_field("login_id")
            password_field = self.get_field("password")
            self.logger.info("Got login and password fields")

            try:
                # Test empty both fields
                self.generic_login("", "", expected_result="field_missing")
                self.logger.info("Testing empty fields validation")

            except Exception:
                self.fail("Empty all fields validation failed")

            try:
                self.check_field_validation_message(
                    login_id_field, LANGUAGE_SETTINGS[self.language]["errors"]["field_missing"]
                )
            except Exception:
                self.fail("Empty password field validation failed")

            try:
                # Test empty password field
                self.generic_login(CREDENTIALS["valid_user"]["username"], "", expected_result="field_missing")
                self.check_field_validation_message(
                    password_field, LANGUAGE_SETTINGS[self.language]["errors"]["field_missing"]
                )
            except Exception:
                self.fail("Empty username field validation failed")

            try:
                # Test empty username field
                self.generic_login("", CREDENTIALS["valid_user"]["password"], "field_missing")
                self.check_field_validation_message(
                    login_id_field, LANGUAGE_SETTINGS[self.language]["errors"]["field_missing"]
                )
            except Exception:
                self.fail("Empty username field validation failed")

        except Exception as e:
            self.logger.error(f"Test failed: {str(e)}")
            self.fail(f"Test failed: {str(e)}")

    def test_02_InvalidLogin(self):
        self.logger.info(f"Running test_02_InvalidLogin for {self.language} language...")
        driver = self.driver
        try:
            self.generic_login(
                CREDENTIALS["invalid_user"]["username"], CREDENTIALS["invalid_user"]["password"],
                expected_result="failure"
            )

            driver.refresh()
            self.generic_login(
                CREDENTIALS["valid_user"]["username"], CREDENTIALS["invalid_user"]["password"],
                expected_result="failure"
            )

            driver.refresh()
            self.generic_login(
                CREDENTIALS["invalid_user"]["username"], CREDENTIALS["valid_user"]["password"],
                expected_result="failure"
            )
        except Exception as e:
            self.fail(f"Test failed: {str(e.msg)}")

    def test_03_PasswordVisibility(self):
        self.logger.info(f"Running test_03_PasswordVisibility for {self.language} language...")
        try:
            password_input = self.get_field("password")
            password = CREDENTIALS["valid_user"]["password"]
            password_input.clear()
            password_input.send_keys(password)
            time.sleep(2)

            visibility_toggle = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label="toggle password visibility"]'))
            )

            self.assertEqual(
                password_input.get_attribute("type"), "password",
                "Password field should initially be of type 'password'"
            )

            visibility_toggle.click()
            time.sleep(2)
            password_input = self.get_field("password")
            self.assertEqual(
                password_input.get_attribute("type"), "text",
                "Password field should change to type 'text' when visibility is toggled"
            )
            self.assertEqual(
                password_input.get_attribute("value"), password, "Visible password should match the entered password"
            )

            visibility_toggle.click()
            time.sleep(2)
            password_input = self.get_field("password")
            self.assertEqual(
                password_input.get_attribute("type"), "password",
                "Password field should change back to type 'password' when visibility is toggled again"
            )

        except Exception as e:
            self.fail(f"Test failed: {str(e.msg)}")

    def test_04_Login(self):
        self.logger.info(f"Running test_04_Login for {self.language} language...")
        try:
            self.generic_login(
                CREDENTIALS["valid_user"]["username"], CREDENTIALS["valid_user"]["password"], expected_result="success"
            )
        except Exception as e:
            self.fail(f"Test failed: {str(e.msg)}")

    # def test_05_NavigateToRegisterPage(self):
    #     self.logger.info(
    #         f"Running test_05_NavigateToRegisterPage for {self.language} language..."
    #     )
    #     try:
    #         register_navigator = WebDriverWait(self.driver, 10).until(
    #             EC.element_to_be_clickable((By.CSS_SELECTOR, 'a[href="register"]'))
    #         )
    #         register_navigator.click()

    #         register_texts = ["Daftar Baru", "登记", "Register"]
    #         for text in register_texts:
    #             try:
    #                 WebDriverWait(self.driver, 10).until(
    #                     EC.visibility_of_element_located(
    #                         (By.XPATH, f"//*[contains(text(), '{text}')]")
    #                     )
    #                 )
    #                 break
    #             except TimeoutException:
    #                 continue
    #         else:
    #             self.fail("Register button not found")
    #     except (NoSuchElementException, TimeoutException) as e:
    #         self.fail(f"Failed to navigate to Register Page: {str(e)}")

    def test_06_ForgotPassword(self):
        self.logger.info(f"Running test_06_ForgotPassword for {self.language} language...")
        try:
            forgot_pwd_link = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'a.MuiTypography-root[href*="wa.me/601172302563"]'))
            )
            forgot_pwd_link.click()

            WebDriverWait(self.driver, 10).until(EC.url_contains('whatsapp.com'))

            expected_text = LANGUAGE_SETTINGS[self.language]["messages"]["forgot_password"]
            text_element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, f"//*[contains(text(), '{expected_text}')]"))
            )
            self.logger.info(f"Text element: {text_element}")
            self.assertTrue(
                text_element.is_displayed(), "Expected text 'I have forgotten my password' not found on WhatsApp page"
            )

        except Exception as e:
            self.fail(f"Test failed: {str(e)}")


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestLogin)
    runner = unittest.TextTestRunner(resultclass=ContinueOnFailureTestResult)
    runner.run(suite)
