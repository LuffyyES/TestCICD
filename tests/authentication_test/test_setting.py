import unittest
import logging
import time
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from config.constant import LANGUAGE_SETTINGS, CREDENTIALS
from tests.authentication_test.base_test import BaseTest
from selenium.common.exceptions import TimeoutException
import string
import random
from tests.test_init import TestInit


class TestSetting(BaseTest):

    def __init__(self, methodName="runTest", language=None, browser=None):
        super().__init__(methodName, language=language, browser=browser)
        self.test_init = TestInit(methodName="runTest", language=language, browser=browser)

    def setUp(self):
        try:
            super().setUp()
            result = self.test_init.register_new_account()
            if not result or not isinstance(result, tuple) or len(result) != 2:
                self.logger.error(f"Registration failed. Got result: {result}")
                raise Exception("Failed to register new account")

            self.username, self.password = result
            self.logger.info(f"Successfully registered account: {self.username}")

            self.navigate_to_login_page()
            self.perform_login(self.username, self.password)
            self.navigate_to_setting_page(self.language)

        except Exception as e:
            self.logger.error(f"Setup failed: {str(e)}")
            if hasattr(self, 'driver'):
                self.driver.quit()
            raise

    def tearDown(self):
        if hasattr(self, "driver"):
            self.driver.quit()

    def click_confirm_button(self):
        driver = self.driver
        container = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located(
                (By.XPATH, "//div[contains(@class, 'MuiBox-root') and contains(@class, 'mui-theme-1alh6im')]")
            )
        )
        buttons = container.find_elements(By.XPATH, ".//button")

        confirm_button = buttons[1]
        confirm_button.click()

    def fill_and_submit_form(self, input_data):
        empty_text_fields = self.driver.find_elements(By.CSS_SELECTOR, 'input[type="text"]')

        for input_field in empty_text_fields:
            if not input_field.get_attribute("value"):
                placeholder = input_field.get_attribute("placeholder")
                aria_label = input_field.get_attribute("aria-label")
                field_name = placeholder or aria_label

                if field_name and field_name in input_data:
                    input_field.send_keys(input_data[field_name])

        confirm_buttons = self.driver.find_elements(By.CSS_SELECTOR, "button")
        for button in confirm_buttons:
            if button.is_displayed() and button.is_enabled():
                button_text = button.text.strip().lower()
                if "confirm" in button_text:
                    button.click()
                    break

    def generate_random_username(self):
        length = random.randint(5, 15)
        chars = string.ascii_letters + string.digits + "!@#$%^&*()"
        return ''.join(random.choice(chars) for _ in range(length))

    def generate_valid_email(self):
        domains = ["gmail.com", "yahoo.com", "outlook.com", "testmail.com"]
        username = ''.join(random.choices(string.ascii_letters + string.digits, k=random.randint(5, 10)))
        return f"{username}@{random.choice(domains)}"

    def generate_short_phone(self):
        return str(random.randint(1, 99999999))

    def generate_long_phone(self):
        return str(random.randint(10000000000, 99999999999))

    def generate_invalid_start_phone(self):
        return f"15{random.randint(1000000, 9999999)}"

    def add_bank_account_button(self):

        addAccountButton = WebDriverWait(self.driver,
                                         10).until(EC.element_to_be_clickable((By.ID, "add-bank-account-button")))
        addAccountButton.click()

    def get_bank_list(self):
        bank_list = []
        options = WebDriverWait(self.driver, 5).until(
            EC.visibility_of_all_elements_located((By.CSS_SELECTOR, "li.MuiListItem-root"))
        )

        for index in range(len(options)):

            options = WebDriverWait(self.driver, 3).until(
                EC.visibility_of_all_elements_located((By.CSS_SELECTOR, "li.MuiListItem-root"))
            )

            item = options[index]
            itemText = item.text
            bank_list.append(itemText)
        return bank_list

    def verify_removed_account(self, bank, account):
        try:
            time.sleep(2)

            li_elements = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li[id^='account-item-']"))
            )

            for element in li_elements:
                text_lines = element.text.splitlines()
                if len(text_lines) >= 3:
                    current_bank = text_lines[1]
                    current_acc = text_lines[2]
                    if current_bank == bank and current_acc == account:
                        self.fail(f"Account {bank} - {account} was not removed")

            self.logger.info(f"Successfully verified removal of account {bank} - {account}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to verify account removal: {str(e)}")
            raise

    def generate_valid_password(self):
        uppercase = random.choice(string.ascii_uppercase)
        lowercase = ''.join(random.choices(string.ascii_lowercase, k=3))
        digits = ''.join(random.choices(string.digits, k=3))

        special_chars = '!@#$%^&*'
        special = ''
        if random.choice([True, False]):
            special = random.choice(special_chars)
            self.logger.info("Including special character in password")

        remaining_length = random.randint(1, 4)
        char_set = string.ascii_letters + string.digits
        if special:
            char_set += special_chars
        remaining_chars = ''.join(random.choices(char_set, k=remaining_length))

        password = list(uppercase + lowercase + digits + special + remaining_chars)
        random.shuffle(password)
        return ''.join(password)

    def generate_invalid_password(self, missing_criteria):
        match missing_criteria:
            case "uppercase":
                password = ''.join(random.choices(string.ascii_lowercase, k=5) + random.choices(string.digits, k=3))
            case "lowercase":
                password = ''.join(random.choices(string.ascii_uppercase, k=5) + random.choices(string.digits, k=3))
            case "number":
                password = ''.join(random.choices(string.ascii_letters, k=8))
            case "length":
                uppercase = random.choice(string.ascii_uppercase)
                lowercase = ''.join(random.choices(string.ascii_lowercase, k=3))
                digits = ''.join(random.choices(string.digits, k=3))
                password = list(uppercase + lowercase + digits)
                random.shuffle(password)
                password = ''.join(password[:7])
        return password

    def test_01_UpdateInfo(self):
        try:
            driver = self.driver
            self.navigate_AccSecurity()
            time.sleep(2)
            self.logger.info("Navigating to the account security page")

            list_items = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li[id^='acct-list-item-']"))
            )
            self.logger.info(f"Found {len(list_items)} account list items")

            for i in range(len(list_items)):
                if i == 1:
                    self.logger.info("Skipping userID item")
                    continue

                current_item = WebDriverWait(driver,
                                             10).until(EC.presence_of_element_located((By.ID, f"acct-list-item-{i}")))
                current_item_text = current_item.text
                self.logger.info(f"Current item text: {current_item_text}")

                try:
                    driver.execute_script("arguments[0].scrollIntoView(true);", current_item)
                    time.sleep(1)
                    current_item.click()
                    self.logger.info(f"Clicked on acct-list-item-{i}")
                    time.sleep(2)

                    text_field = WebDriverWait(driver,
                                               10).until(EC.presence_of_element_located((By.ID, "new-value-input")))
                    text_field.clear()

                    match i:
                        case 0:
                            input_text = self.generate_random_username()
                        case 2:
                            input_text = self.generate_valid_phone()
                        case 3:
                            input_text = self.generate_valid_email()

                    text_field.send_keys(input_text)
                    self.logger.info(f"Input text: {input_text}")
                    time.sleep(2)
                    confirm_button = WebDriverWait(driver,
                                                   10).until(EC.presence_of_element_located((By.ID, "confirm-button")))
                    confirm_button.click()
                    self.success_box()
                    self.confirm_button()

                    time.sleep(2)

                    updated_item = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.ID, f"acct-list-item-{i}"))
                    )
                    updated_text = updated_item.text.split("\n")[1]
                    self.logger.info(f"Updated text: {updated_text}")

                    match i:
                        case 2:
                            input_text = input_text[-2:]
                            updated_text = updated_text[-2:]
                            self.assertEqual(input_text, updated_text, "Phone number is not updated")
                        case 3:
                            input_text = input_text[:3]
                            updated_text = updated_text[:3]
                            self.assertEqual(
                                input_text, updated_text,
                                f"Email is not updated. Expected first 3 chars: {input_text}, Got: {updated_text}"
                            )
                        case _:
                            self.assertEqual(
                                input_text, updated_text,
                                f"Update failed for {current_item_text}. Expected: {input_text}, Got: {updated_text}"
                            )

                except Exception as e:
                    self.logger.error(f"Failed to process item {i}: {str(e)}")
                    raise

        except Exception as e:
            self.logger.error(f"Test failed: {str(e)}")
            self.fail(f"Test failed: {str(e)}")

    def test_02_UpdateInvalidPhoneNumber(self):
        driver = self.driver
        self.navigate_AccSecurity()
        time.sleep(2)
        list_items = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li[id^='acct-list-item-']"))
        )

        time.sleep(3)
        try:
            phone_tests = [
                ("abc", "", "Characters should not be accepted"),
                ("@#$%", "", "Special characters should not be accepted"),
                (
                    self.generate_short_phone(), LANGUAGE_SETTINGS[self.language]["errors"]["invalid_phone_format"],
                    "Phone number with fewer than 9 digits is accepted"
                ),
                (
                    CREDENTIALS['duplicated_user']['phone_number'],
                    LANGUAGE_SETTINGS[self.language]["errors"]["phone_already_exists"],
                    "Duplicated phone number is accepted"
                ),
                (
                    self.generate_long_phone(), LANGUAGE_SETTINGS[self.language]["errors"]["invalid_phone_format"],
                    "Phone number with more than 10 digits is accepted"
                ),
                (
                    self.generate_invalid_start_phone(),
                    LANGUAGE_SETTINGS[self.language]["errors"]["invalid_phone_format"],
                    "Phone number starting with '015' is accepted"
                )
            ]

            for test_input, expected_result, fail_message in phone_tests:
                list_items = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li[id^='acct-list-item-']"))
                )
                phone_item = list_items[2]

                phone_item = WebDriverWait(driver, 10).until(EC.element_to_be_clickable(phone_item))
                driver.execute_script("arguments[0].scrollIntoView(true);", phone_item)
                phone_item.click()
                time.sleep(3)
                self.logger.info(f"Testing: {fail_message}")

                text_field = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "new-value-input")))
                text_field.clear()
                text_field.send_keys(test_input)
                time.sleep(2)

                if expected_result == "":
                    actual_value = text_field.get_attribute("value")
                    self.assertEqual("", actual_value, fail_message)
                    driver.refresh()
                    continue

                confirm_button = WebDriverWait(driver,
                                               10).until(EC.presence_of_element_located((By.ID, "confirm-button")))
                confirm_button.click()

                invalidError = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, "swal2-title")))
                self.assertIn(expected_result, invalidError.text, fail_message)
                self.confirm_button()
                driver.refresh()

        except Exception as e:
            self.logger.error(f"Test failed: {str(e)}")
            self.fail(f"Test failed: {str(e)}")

    def test_03_AddAccount(self):
        try:
            time.sleep(2)
            self.navigate_PaymentSetting()
            self.logger.info("Navigated to settings page")

            try:
                bank_list = self.get_bank_list()
                self.addSingleAccount(bank_list=bank_list, setting=True)
                time.sleep(2)

            except TimeoutException:
                self.logger.info("No account found, adding single account")
                self.addSingleAccount(setting=True)
                return

        except Exception as e:
            self.logger.error(f"Test failed: {str(e)}")
            self.fail(f"Test failed: {str(e)}")

    def test_04_AddInvalidAccount(self):
        try:
            self.navigate_PaymentSetting()

            self.addSingleAccount(setting=True)
            bank_list = self.get_bank_list()
            self.genericAddAccount(checkDuplicated=True, bank_list=bank_list, setting=True)
            closeAddAccountBox = WebDriverWait(self.driver,
                                               3).until(EC.element_to_be_clickable((By.ID, "close-modal-button")))
            closeAddAccountBox.click()
            self.driver.refresh()

            self.genericAddAccount(checkInvalidAcc=True, bank_list=bank_list, setting=True)
            closeAddAccountBox = WebDriverWait(self.driver,
                                               3).until(EC.element_to_be_clickable((By.ID, "close-modal-button")))
            closeAddAccountBox.click()

            self.driver.refresh()
            self.genericAddAccount(checkMaxAccounts=True, bank_list=bank_list, setting=True)

        except Exception as e:
            self.fail(f"Test failed: {str(e)}")

    def test_05_RemoveBankAccount(self):
        driver = self.driver
        try:
            self.navigate_PaymentSetting()
            time.sleep(2)

            for _ in range(2):
                self.addSingleAccount(setting=True)
                driver.refresh()

            li_elements = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li[id^='account-item-']"))
            )
            self.logger.info(f"Found {len(li_elements)} bank accounts")

            random_li = random.choice(li_elements)
            _, bank, acc, _ = random_li.text.splitlines()
            self.logger.info(f"Removing account - Bank: {bank}, Account: {acc}")

            account_id = random_li.get_attribute('id').split('-')[-1]

            remove_button = random_li.find_element(By.ID, f"remove-account-button-{account_id}")
            remove_button.click()
            time.sleep(1)

            self.success_box()
            self.confirm_button()
            time.sleep(1)

            try:
                self.verify_removed_account(bank, acc)
                self.logger.info("Account removal verified successfully")
            except Exception as e:
                self.fail(f"Failed to verify account removal: {str(e)}")

        except Exception as e:
            self.logger.error(f"Test failed: {str(e)}")
            self.fail(f"Test failed: {str(e)}")

    def test_06_ResetPassword_EmptyField(self):
        driver = self.driver
        self.navigate_ChangePassword()
        time.sleep(2)

        try:
            password_fields = {
                "current-password": LANGUAGE_SETTINGS[self.language]["password_fields"]["current_password"],
                "new-password": LANGUAGE_SETTINGS[self.language]["password_fields"]["new_password"],
                "confirm-new-password": LANGUAGE_SETTINGS[self.language]["password_fields"]["confirm_new_password"]
            }
            filled_fields = set()
            test_password = self.generate_valid_password()
            self.logger.info(f"Using test password: {test_password}")

            for field_id, field_label in password_fields.items():

                submit_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "submit-button")))
                driver.execute_script("arguments[0].scrollIntoView(true);", submit_button)
                time.sleep(1)
                submit_button.click()

                try:
                    popup = WebDriverWait(driver,
                                          10).until(EC.visibility_of_element_located((By.ID, "swal2-html-container")))
                    popup_text = popup.text

                    empty_field_messages = []
                    for pwd_id, label in password_fields.items():
                        if pwd_id not in filled_fields:
                            empty_field_messages.append(f"{label}")

                    expected_message = ", ".join(empty_field_messages) + " " + LANGUAGE_SETTINGS[
                        self.language]['errors']['setting_password_empty']
                    self.logger.info(f"Expected message: {expected_message}")
                    self.logger.info(f"Actual message: {popup_text}")

                    self.assertIn(
                        expected_message, popup_text,
                        f"Popup text does not contain the expected message '{expected_message}'"
                    )

                    popup_icon = driver.find_element(By.CSS_SELECTOR, ".swal2-icon-content")
                    self.assertEqual(popup_icon.text, "!", "Error icon text does not match expected value")
                    time.sleep(2)
                    self.confirm_button()

                except Exception as e:
                    self.logger.error(f"Failed to verify error message: {str(e)}")
                    self.fail("Cannot get the error message")

                field_mapping = {
                    "current-password": self.password,
                    "new-password": test_password,
                    "confirm-new-password": test_password
                }
                if field_id in field_mapping:
                    current_field = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, field_id)))
                    current_field.send_keys(field_mapping[field_id])
                    filled_fields.add(field_id)
                    if field_id == "confirm-new-password":
                        continue

                time.sleep(2)

        except Exception as e:
            self.logger.error(f"Test failed: {str(e)}")
            self.fail(f"Test failed: {str(e)}")

    def test_07_ResetPassword_PasswordNotMatch(self):
        driver = self.driver
        self.navigate_ChangePassword()
        time.sleep(2)

        try:
            new_password = self.generate_valid_password()
            confirm_password = self.generate_valid_password()
            while confirm_password == new_password:
                confirm_password = self.generate_valid_password()

            self.logger.info(f"Testing with new_password: {new_password}, confirm_password: {confirm_password}")

            password_fields = {
                "current-password": self.password,
                "new-password": new_password,
                "confirm-new-password": confirm_password
            }

            for field_id, password in password_fields.items():
                field = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, field_id)))
                field.clear()
                field.send_keys(password)
                time.sleep(1)

            submit_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "submit-button")))
            submit_button.click()

            try:
                popup = WebDriverWait(driver,
                                      10).until(EC.visibility_of_element_located((By.ID, "swal2-html-container")))
                popup_text = popup.text

                expected_message = LANGUAGE_SETTINGS[self.language]["errors"]["unmatch_password"]

                self.assertEqual(
                    expected_message, popup_text,
                    f"Error message mismatch. Expected: '{expected_message}', Got: '{popup_text}'"
                )
                self.confirm_button()

            except Exception as e:
                self.logger.error(f"Failed to verify error message: {str(e)}")
                self.fail("Cannot get the error message")

        except Exception as e:
            self.logger.error(f"Test failed: {str(e)}")
            self.fail(f"Test failed: {str(e)}")

    def test_08_ResetPassword_PasswordValidation(self):
        driver = self.driver
        self.navigate_ChangePassword()
        time.sleep(2)

        try:
            test_cases = [{
                "missing": "uppercase",
                "error_key": "invalid_new_password"
            }, {
                "missing": "lowercase",
                "error_key": "invalid_new_password"
            }, {
                "missing": "number",
                "error_key": "invalid_new_password"
            }, {
                "missing": "length",
                "error_key": "new_password_invalid_length"
            }]

            for test_case in test_cases:
                invalid_password = self.generate_invalid_password(test_case["missing"])
                self.logger.info(f"Testing password validation - missing {test_case['missing']}")
                self.logger.info(f"Using invalid password: {invalid_password}")

                password_fields = {
                    "current-password": self.password,
                    "new-password": invalid_password,
                    "confirm-new-password": invalid_password
                }
                for field_id, password in password_fields.items():
                    field = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, field_id)))
                    field.send_keys(password)
                    time.sleep(1)

                submit_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "submit-button")))
                submit_button.click()
                try:
                    popup = WebDriverWait(driver,
                                          10).until(EC.visibility_of_element_located((By.ID, "swal2-html-container")))
                    popup_text = popup.text

                    expected_message = LANGUAGE_SETTINGS[self.language]["errors"][test_case["error_key"]]
                    self.logger.info(f"Expected message: {expected_message}")
                    self.logger.info(f"Actual message: {popup_text}")

                    self.assertEqual(
                        expected_message, popup_text,
                        f"Error message mismatch for {test_case['missing']}. Expected: '{expected_message}', Got: '{popup_text}'"
                    )

                    self.confirm_button()
                    time.sleep(1)
                    driver.refresh()

                except Exception as e:
                    self.logger.error(f"Failed to verify error message: {str(e)}")
                    self.fail(f"Error message verification failed: {str(e)}")

        except Exception as e:
            self.logger.error(f"Test failed: {str(e)}")
            self.fail(f"Test failed: {str(e)}")

    def test_09_ResetPassword_Success(self):
        driver = self.driver
        self.navigate_ChangePassword()
        time.sleep(2)

        try:
            new_password = self.generate_valid_password()
            confirm_password = new_password

            self.logger.info(f"Testing with new_password: {new_password}, confirm_password: {confirm_password}")

            password_fields = {
                "current-password": self.password,
                "new-password": new_password,
                "confirm-new-password": confirm_password
            }

            for field_id, password in password_fields.items():
                field = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, field_id)))
                field.clear()
                field.send_keys(password)
                time.sleep(1)

            submit_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "submit-button")))
            submit_button.click()

            self.success_box()
            success_text = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, "swal2-title")))
            expected_text = LANGUAGE_SETTINGS[self.language]["success"]["reset_password"]
            self.assertEqual(success_text.text, expected_text, "Success message does not match expected text")
            self.confirm_button()
            try:
                self.click_navigation_bar("logout-list-item")
                self.perform_login(self.username, new_password)
                self.verify_login(self.username)
            except Exception as e:
                self.logger.error(f"Failed to verify new password: {str(e)}")
                self.fail("Cannot login with new password")

        except Exception as e:
            self.logger.error(f"Test failed: {str(e)}")
            self.fail(f"Test failed: {str(e)}")

    def test_10_Password_Visibility(self):
        driver = self.driver
        self.navigate_ChangePassword()
        time.sleep(2)

        try:
            password_fields = {
                "current-password": self.password,
                "new-password": self.generate_valid_password(),
                "confirm-new-password": self.generate_valid_password()
            }

            for field_id, password in password_fields.items():
                password_field = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, field_id)))

                toggle_button = password_field.find_element(
                    By.XPATH, "following-sibling::div//button[@aria-label='toggle password visibility']"
                )

                password_field.send_keys(password)

                self.assertEqual(
                    password_field.get_attribute("type"), "password",
                    f"Password field {field_id} should be hidden initially"
                )

                toggle_button.click()
                time.sleep(1)

                self.assertEqual(
                    password_field.get_attribute("type"), "text",
                    f"Password field {field_id} should be visible after toggle"
                )
                toggle_button.click()
                time.sleep(1)

                self.assertEqual(
                    password_field.get_attribute("type"), "password",
                    f"Password field {field_id} should be hidden after second toggle"
                )

                self.logger.info(f"Successfully tested visibility toggle for {field_id}")

        except Exception as e:
            self.logger.error(f"Test failed: {str(e)}")
            self.fail(f"Test failed: {str(e)}")

    def test_11_logout_button(self):
        driver = self.driver
        time.sleep(2)
        try:
            self.click_navigation_bar("logout-list-item")
            try:
                WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, "loginButton")))
            except Exception as e:
                self.logger.error(f"Failed to verify logout: {str(e)}")
                self.fail(f"Failed to verify logout: {str(e)}")

        except Exception as e:
            self.logger.error(f"Failed to verify login: {str(e)}")
            self.fail(f"Failed to verify login: {str(e)}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    unittest.main()
