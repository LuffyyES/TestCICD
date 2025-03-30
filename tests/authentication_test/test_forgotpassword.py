import unittest
import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from config.constant import LANGUAGE_SETTINGS, CREDENTIALS
from tests.authentication_test.base_test import BaseTest

# test_05_WrongOldPassword and test_03_SuccessReset


class TestPasswordPage(BaseTest):

    def __init__(self, methodName="runTest", language=None, browser=None):
        super().__init__(methodName)
        self.language = language
        self.browser = browser
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

        file_handler = logging.FileHandler("test_forgotPassword_output.log")
        file_handler.setLevel(logging.INFO)

        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        file_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)

        self.logger.propagate = False

    def setUp(self):
        if not self.browser or not self.language:
            raise ValueError("Browser or language is not set.")
        self.logger.info(f"Setting up {self.browser} browser for {self.language} language...")
        self.driver = self.initialize_browser(self.browser)
        self.url = LANGUAGE_SETTINGS[self.language]["home_url"]
        self.driver.get(self.url)
        #self.driver.maximize_window()
        self.driver.set_window_size(375, 812)
        self.navigate_to_login_page()
        self.perform_login(CREDENTIALS["duplicated_user"]["username"], CREDENTIALS["duplicated_user"]["password"])
        self.navigate_to_setting_page(self.language)
        self.navigate_to_resetPassword_page()

    def tearDown(self):
        if hasattr(self, "driver"):
            self.driver.quit()

    def fill_password_fields(self, password_data):
        driver = self.driver
        password_fields = WebDriverWait(driver, 5).until(
            EC.visibility_of_all_elements_located((By.CSS_SELECTOR, 'input[type="password"], textarea'))
        )
        for field in password_fields:
            WebDriverWait(driver, 5).until(EC.element_to_be_clickable(field))
            placeholder = field.get_attribute("placeholder")
            field_name = placeholder.strip() if placeholder else ""
            if field_name in password_data:
                field.clear()
                field.send_keys(password_data[field_name])
                time.sleep(2)

    def click_confirm_button(self):
        confirm_button = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.MuiButton-containedPrimary"))
        )
        confirm_button.click()

    def handle_popup(self, expected_icon_text="!", expected_message=None):
        try:
            WebDriverWait(self.driver,
                          10).until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".swal2-icon-content")))
            popup_icon = self.driver.find_element(By.CSS_SELECTOR, ".swal2-icon-content")
            time.sleep(2)
            self.assertEqual(popup_icon.text, expected_icon_text, "Popup icon text does not match expected value")

            if expected_message:
                popup_message = self.driver.find_element(By.CSS_SELECTOR, ".swal2-html-container").text
                self.assertIn(expected_message, popup_message, "Popup message does not match expected value")

            ok_button = WebDriverWait(self.driver,
                                      5).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.swal2-confirm")))
            ok_button.click()
        except Exception as e:
            self.fail(f"Popup element not found: {str(e)}")

    """
    # Test ACCPassword
    def test_01_EmptyFields(self):
        driver = self.driver
        try:
            password_data = LANGUAGE_SETTINGS[self.language]["password_data"].copy()
            text_fields = ["currentPw", "newPw", "confirmNewPw"]
            index = 0

            for (field_label, field_value) in password_data.items():

                field = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.NAME, text_fields[index])))
                field.clear()

                confirm_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button.MuiButton-containedPrimary"))
                )
                confirm_button.click()

                try:
                    self.handle_popup(expected_icon_text="!")
                except Exception as e:
                    self.fail("Does not pop out error message")

                field = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.NAME, text_fields[index])))
                field.send_keys(field_value)

                self.assertEqual(
                    field.get_attribute("type"), "password", "Password field should initially be of type 'password'"
                )

                visibility_toggles = driver.find_elements(
                    By.CSS_SELECTOR, 'button[aria-label="toggle password visibility"]'
                )

                if len(visibility_toggles) < len(text_fields):
                    raise AssertionError("Not enough visibility toggle buttons found on the page.")

                visibility_toggle = visibility_toggles[index]

                visibility_toggle.click()
                time.sleep(2)

                WebDriverWait(
                    driver, 2
                ).until(lambda d: d.find_element(By.NAME, text_fields[index]).get_attribute("type") == "text")
                field = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.NAME, text_fields[index])))
                self.assertEqual(
                    field.get_attribute("type"), "text", "Password field should be of type 'text' when visible"
                )
                self.assertEqual(
                    field.get_attribute("value"), field_value, "Visible password should match the entered password"
                )

                visibility_toggle.click()

                WebDriverWait(
                    driver, 2
                ).until(lambda d: d.find_element(By.NAME, text_fields[index]).get_attribute("type") == "password")
                field = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.NAME, text_fields[index])))
                self.assertEqual(
                    field.get_attribute("type"), "password", "Password field should revert to type 'password'"
                )

                index += 1
                time.sleep(1)
        except Exception as e:
            self.fail(f"Test failed: {str(e)}")

    def test_02_DifferentNewPassword(self):
        password_data = LANGUAGE_SETTINGS[self.language]["password_data"].copy()
        last_key = list(password_data.keys())[-1]
        password_data[last_key] = "Halo3333"

        try:
            self.fill_password_fields(password_data)
            time.sleep(5)
            self.click_confirm_button()
            self.handle_popup(expected_message=LANGUAGE_SETTINGS[self.language]["errors"]["unmatch_password"])
            time.sleep(2)
        except Exception as e:
            self.fail(f"Failed to check the unmatched password: {str(e)}")


    def test_03_SuccessReset(self):
        password_data = LANGUAGE_SETTINGS[self.language]["password_data"].copy()
        self.fill_password_fields(password_data)
        self.click_confirm_button()
        self.success_icon()
        self.confirm_button()

        try:
            self.url = LANGUAGE_SETTINGS[self.language]["login_url"]
            self.driver.get(self.url)
            self.perform_login(CREDENTIALS["valid_user"]["username"], password_data[list(password_data.keys())[-1]])
            self.verify_login()
        except TimeoutException:
            self.fail("Failed to login with the new password.")
        except NoSuchElementException as e:
            self.fail(f"Element not found: {str(e)}")
            
    """

    def test_04_InvalidPasswordFormat(self):
        try:
            driver = self.driver
            # Test invalid password format (without uppercase, lowercase, and number)
            password_data = LANGUAGE_SETTINGS[self.language]["password_data"].copy()
            invalid_newPassword = "123"

            password_keys = list(password_data.keys())
            if len(password_keys) == 3:
                password_data[password_keys[1]] = invalid_newPassword
                password_data[password_keys[2]] = invalid_newPassword

            self.fill_password_fields(password_data)
            self.click_confirm_button()
            time.sleep(2)
            try:
                self.handle_popup(expected_message=LANGUAGE_SETTINGS[self.language]["errors"]["invalid_new_password"])
            except Exception as e:
                self.fail("Does not pop out error message")

            # Test incorrect password f
            driver.refresh()
            password_data = LANGUAGE_SETTINGS[self.language]["password_data"].copy()
            invalid_newPassword = "Try123"

            password_keys = list(password_data.keys())
            if len(password_keys) == 3:
                password_data[password_keys[1]] = invalid_newPassword
                password_data[password_keys[2]] = invalid_newPassword

            self.fill_password_fields(password_data)
            self.click_confirm_button()
            time.sleep(2)
            try:  ###
                self.handle_popup(
                    expected_message=LANGUAGE_SETTINGS[self.language]["errors"]["new_password_invalid_length"]
                )
            except Exception as e:
                self.fail("Does not pop out error message")

            # Test incorrect current password
            driver.refresh()
            password_data = LANGUAGE_SETTINGS[self.language]["password_data"].copy()
            invalid_newPassword = "Try123"

            password_keys = list(password_data.keys())
            if len(password_keys) == 3:
                password_data[password_keys[1]] = invalid_newPassword
                password_data[password_keys[2]] = invalid_newPassword

            self.fill_password_fields(password_data)
            self.click_confirm_button()
            time.sleep(2)
            try:  ###
                self.handle_popup(
                    expected_message=LANGUAGE_SETTINGS[self.language]["errors"]["new_password_invalid_length"]
                )
            except Exception as e:
                self.fail("Does not pop out error message")

            #Test change to the same password
            #driver.refresh()
            #password_data = LANGUAGE_SETTINGS[self.language]["password_data"].copy()
            #invalid_newPassword = "Try12345678"

        except Exception as e:
            self.fail(f"Test failed: {str(e)}")

    """
#GOT PROBLEM IN STAGING!
    def test_05_WrongOldPassword(self):
        password_data = LANGUAGE_SETTINGS[self.language]["password_data"].copy()
        unregistered_oldPassword = CREDENTIALS["unregister_user"]["password"]

        password_keys = list(password_data.keys())
        if len(password_keys) == 3:
            password_data[password_keys[0]] = unregistered_oldPassword
        self.fill_password_fields(password_data)
        self.click_confirm_button()
        try:
            self.handle_popup(expected_message=None)
        except NoSuchElementException as e:
            self.fail(f"Element not found: {str(e)}")
        except TimeoutException as e:
            self.fail("Failed to check if reset with unregistered password")
    """


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    unittest.main()
