import unittest
import time
from selenium import webdriver
import random
import string
import logging
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.safari.service import Service as SafariService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, NoSuchWindowException
from config.constant import LANGUAGE_SETTINGS, CREDENTIALS
from .base_test import BaseTest, ContinueOnFailureTestResult

# ID validation
# verify can login or not after successfully registration
# new password got space how?


class TestRegister(BaseTest):

    def __init__(self, methodName="runTest", language=None, browser=None):
        super().__init__(methodName, language, browser)
        self.field_locators = {
            "login_id": (By.ID, "register-login-id"),
            "password": (By.ID, "register-password"),
            "confirm_password": (By.ID, "register-confirm-password"),
            "full_name": (By.ID, "register-full-name"),
            "phone_no": (By.ID, "register-phone-number")
        }

    def setUp(self):
        super().setUp()
        self.navigate_to_register_page()

    def tearDown(self):
        if hasattr(self, "driver"):
            self.driver.quit()

    def get_field(self, field_name):
        locator_type, locator_value = self.field_locators[field_name]
        return WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located((locator_type, locator_value)))

    def fill_registration_form(self, credentials):
        fields = {
            "login_id": credentials["username"],
            "password": credentials["password"],
            "confirm_password": credentials["password"],
            "full_name": credentials["fullname"],
            "phone_no": credentials["phone_number"]
        }
        for field_name, value in fields.items():
            field = self.get_field(field_name)
            field.clear()
            field.send_keys(value)

    def click_register_button(self):
        button = WebDriverWait(self.driver, 2).until(EC.element_to_be_clickable((By.ID, 'register-submit-button')))
        button.click()

    def validate_field(self, field_name, invalid_value, expected_error_message):

        random_username = self.generate_valid_username()
        self.logger.info(f"Using generated username: {random_username}")

        credentials = {
            "username": random_username,
            "password": random_username,
            "fullname": random_username,
            "phone_number": self.generate_valid_phone()
        }
        credentials[field_name] = invalid_value
        self.fill_registration_form(credentials)
        self.click_register_button()

        try:
            self.error_box(expected_error_message)

        except Exception as e:
            self.fail(f"Test failed: {str(e.msg)}")

    def generate_valid_username(self):

        capital = random.choice(string.ascii_uppercase)
        lower = random.choice(string.ascii_lowercase)
        digit = random.choice(string.digits)

        remaining_length = random.randint(7, 9)

        remaining_chars = ''.join(random.choices(string.ascii_letters + string.digits, k=remaining_length))

        username = list(capital + lower + digit + remaining_chars)
        random.shuffle(username)

        return ''.join(username)

    def generate_valid_phone(self):
        phone = "1"

        remaining_length = random.randint(8, 9)
        remaining_digits = ''.join(random.choices(string.digits, k=remaining_length))

        return f"{phone}{remaining_digits}"

    def test_01_EmptyFields(self):
        driver = self.driver
        fields = LANGUAGE_SETTINGS[self.language]["fields"]
        field_mapping = {
            "login_id": "username",
            "password": "password",
            "confirm_password": "password",
            "full_name": "fullname",
            "phone_no": "phone_number"
        }
        filled_fields = set()

        try:
            for field_name, field_label in fields.items():
                field = self.get_field(field_name)
                self.logger.info(f"Found field element: {field_name}")

                driver.execute_script("arguments[0].scrollIntoView(true);", field)
                time.sleep(2)
                self.click_register_button()
                try:
                    time.sleep(1)
                    #id
                    popup = WebDriverWait(driver,
                                          10).until(EC.visibility_of_element_located((By.ID, "swal2-html-container")))
                    popup_text = popup.text

                    empty_field_messages = []
                    for fname, label in fields.items():
                        if fname not in filled_fields:
                            empty_field_messages.append(f"{label}")

                    expected_message = ", ".join(empty_field_messages) + " " + LANGUAGE_SETTINGS[
                        self.language]['errors']['is_required']
                    self.assertIn(
                        expected_message, popup_text,
                        f"Popup text does not contain the expected message '{expected_message}'"
                    )

                    popup_icon = driver.find_element(By.CSS_SELECTOR, ".swal2-icon-content")
                    self.assertEqual(popup_icon.text, "!", "Error icon text does not match expected value")
                    self.confirm_button()

                except Exception as e:
                    self.fail("Cannot get the error message")

                current_field = self.get_field(field_name)
                current_field.send_keys(CREDENTIALS["duplicated_user"][field_mapping[field_name]])
                filled_fields.add(field_name)

        except Exception as e:
            self.fail(f"Test failed: {str(e.msg)}")

    def test_02_DuplicatedUser(self):
        time.sleep(2)
        self.fill_registration_form(CREDENTIALS["duplicated_user"])
        self.click_register_button()
        try:
            self.error_box(
                LANGUAGE_SETTINGS[self.language]["errors"]["duplicate_account"],
                secondText=LANGUAGE_SETTINGS[self.language]["errors"]["phone_already_exists"]
            )
        except Exception as e:
            self.fail(f"Test failed: {str(e.msg)}")

    def test_03_PasswordVisibility(self):
        try:
            password_field = self.get_field("password")
            password = CREDENTIALS["duplicated_user"]["password"]
            password_field.clear()
            password_field.send_keys(password)
            #id
            visibility_toggle = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.ID, "toggle-password-visibility"))
            )
            self.assertEqual(
                password_field.get_attribute("type"), "password",
                "Password field should initially be of type 'password'"
            )

            visibility_toggle.click()
            time.sleep(2)
            self.assertEqual(
                password_field.get_attribute("type"), "text", "Password field should be of type 'text' when visible"
            )
            self.assertEqual(
                password_field.get_attribute("value"), password, "Visible password should match the entered password"
            )

            visibility_toggle.click()
            time.sleep(2)
            self.assertEqual(
                password_field.get_attribute("type"), "password", "Password field should revert to type 'password'"
            )

        except Exception as e:
            self.fail(f"Test failed: {str(e.msg)}")

    def test_04_PasswordValidation(self):
        time.sleep(2)

        random_username = self.generate_valid_username()
        self.logger.info(f"Using generated username: {random_username}")

        credentials = {
            "username": random_username,
            "password": random_username,
            "fullname": random_username,
            "phone_number": self.generate_valid_phone()
        }

        try:
            # Test password validation for less than 8 digits
            credentials["password"] = CREDENTIALS["invalidDigit_password"]["password"]
            self.fill_registration_form(credentials)
            self.click_register_button()

            try:
                self.error_box(LANGUAGE_SETTINGS[self.language]["errors"]["password_less_than_8"])
                time.sleep(2)
            except Exception as e:
                self.fail("Password less than 8 digits was incorrectly accepted.")

            # Test password without capital letter
            credentials["password"] = CREDENTIALS["Password_WithoutCapital"]["password"]
            self.fill_registration_form(credentials)
            self.click_register_button()

            try:
                self.error_box(LANGUAGE_SETTINGS[self.language]["errors"]["password_format_wrong"])
            except Exception as e:
                self.fail("Failed to check the password validation that requires at least one capital letter.")

            # Test password without number
            credentials["password"] = CREDENTIALS["Password_WithoutNumber"]["password"]
            self.fill_registration_form(credentials)
            self.click_register_button()

            try:
                self.error_box(LANGUAGE_SETTINGS[self.language]["errors"]["password_format_wrong"])
            except Exception as e:
                self.fail("Failed to check the password validation that requires at least one number.")

        except Exception as e:
            self.fail(f"Test failed: {str(e.msg)}")

    #015 and duplicated phone number, length<9, length>10
    def test_05_PhoneNumberValidation(self):

        # Test length < 9
        try:
            self.validate_field(
                "phone_number", "123", LANGUAGE_SETTINGS[self.language]["errors"]["invalid_phone_format"]
            )
        except Exception as e:
            self.fail("Phone number with fewer than 9 digits is accepted")
        time.sleep(2)

        # Test duplicated phone number
        try:
            self.validate_field(
                "phone_number", CREDENTIALS["duplicated_user"]["phone_number"],
                LANGUAGE_SETTINGS[self.language]["errors"]["phone_already_exists"]
            )
        except Exception as e:
            self.fail("Duplicated Phone number is accepted")

        #Test length > 10
        try:
            self.validate_field(
                "phone_number", "123456789123", LANGUAGE_SETTINGS[self.language]["errors"]["invalid_phone_format"]
            )
        except Exception as e:
            self.fail("Phone number with more than 10 digits is accepted")
        time.sleep(2)

        # Test phone number with non-numeric character
        try:
            self.validate_field(
                "phone_number", "abc", LANGUAGE_SETTINGS[self.language]["errors"]["invalid_phone_format"]
            )
        except Exception as e:
            self.fail("Phone number with phone number with non-numeric character is accepted")
        time.sleep(2)

        # Test phone number starting with "015"
        try:
            self.validate_field(
                "phone_number", "153527352", LANGUAGE_SETTINGS[self.language]["errors"]["invalid_phone_format"]
            )
        except Exception as e:
            self.fail("Phone number with phone number starting with '015' is accepted")
        time.sleep(2)

    def test_06_UsernameValidation(self):
        driver = self.driver
        #username with special character
        try:
            self.validate_field(
                "username", "Try@123456", LANGUAGE_SETTINGS[self.language]["errors"]["invalid_username"]
            )
        except Exception as e:
            self.fail("Username with special character is accepted")

        #username with invalid length (length >12)
        try:
            self.validate_field(
                "username", "Try12345678910", LANGUAGE_SETTINGS[self.language]["errors"]["username_larger_than_12"]
            )
        except Exception as e:
            self.fail("Username with special character is accepted")

    def test_07_Register(self):
        try:

            random_username = self.generate_valid_username()
            self.logger.info(f"Using generated username: {random_username}")

            credentials = {
                "username": random_username,
                "password": random_username,
                "confirm_password": random_username,
                "fullname": random_username,
                "phone_number": self.generate_valid_phone()
            }

            self.logger.info(f"Using generated phone: {credentials['phone_number']}")

            self.fill_registration_form(credentials)
            self.click_register_button()

            #id
            success_icon = WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located((By.CLASS_NAME, "swal2-success-ring"))
            )
            self.assertTrue(success_icon.is_displayed(), "Success icon is not displayed")

            success_message = WebDriverWait(self.driver,
                                            10).until(EC.visibility_of_element_located((By.ID, "swal2-title")))
            success_text = success_message.text
            self.assertIn(
                LANGUAGE_SETTINGS[self.language]["errors"]["registration_success"], success_text,
                "Success message does not contain the expected text"
            )
            self.confirm_button()
            time.sleep(4)

            try:
                self.verify_login(random_username)
            except Exception as e:
                self.fail("Login with new account failed")

        except Exception as e:
            self.fail(f"Test failed: {str(e.msg)}")

    def test_08_NavigatetoLoginPage(self):
        login_navigtor = WebDriverWait(self.driver,
                                       10).until(EC.visibility_of_element_located((By.ID, 'register-login-link')))
        login_navigtor.click()
        self.logger.info("Navigating to login page")
        try:
            texts = ["Log Masuk", "登录", "Log In"]

            for text in texts:
                try:
                    element = WebDriverWait(self.driver, 2).until(
                        EC.visibility_of_element_located((By.XPATH, f'//p[contains(text(), "{text}")]'))
                    )
                    element_text = element.text
                    self.assertEqual(element_text, text, f"Expected text '{text}' but got '{element_text}'")
                    return

                except Exception as e:
                    continue

        except Exception as e:
            self.fail(f"Test failed: {str(e.msg)}")

    def test_11_ClearButton(self):
        try:
            test_cases = [{
                "type": "promo",
                "action": lambda: self.select_random_promo(0)
            }, {
                "type": "voucher",
                "action": lambda: self.enter_voucher(CREDENTIALS["deposit"]["valid_voucher"])
            }]

            initial_button_texts = [self.get_all_button_texts()[0], self.get_all_button_texts()[1]]

            for test_case in test_cases:
                self.logger.info(f"Testing clear button with {test_case['type']}")

                # Common setup steps
                self.select_random_amount()
                time.sleep(1)
                self.choose_receipt()

                # Execute specific action (promo or voucher)
                test_case["action"]()
                time.sleep(1)

                # Clear and verify
                self.clear_details(clearButton="clear-button")
                time.sleep(2)
                self.verify_clear_functionality(initial_button_texts, [0, 1], check_image_removal=True)

        except Exception as e:
            self.fail(f"Test failed: {str(e)}")


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestRegister)
    runner = unittest.TextTestRunner(resultclass=ContinueOnFailureTestResult)
    runner.run(suite)
