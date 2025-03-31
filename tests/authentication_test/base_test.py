import unittest
import time
from selenium import webdriver
import logging
import random
import requests
import re
from datetime import datetime, timedelta
import os
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.safari.service import Service as SafariService
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.safari.options import Options as SafariOptions
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, UnexpectedAlertPresentException
from config.constant import HEADLESS, CREDENTIALS, LANGUAGE_SETTINGS, PROFILE_URL, API_URL
import tempfile
import requests
import string
from urllib.parse import urlparse
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.safari.webdriver import SafariRemoteConnection
from selenium.webdriver.remote.command import Command
from selenium.webdriver.remote.remote_connection import RemoteConnection
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.remote_connection import ClientConfig
from selenium.webdriver.safari.options import Options as SafariOptions


class ContinueOnFailureTestResult(unittest.TestResult):

    def addFailure(self, test, err):
        self.failures.append((test, err))
        print(f"Test Failed: {test}")

    def addError(self, test, err):
        self.errors.append((test, err))
        print(f"Test Error: {test}")


class BaseTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.logger = logging.getLogger(cls.__name__)
        cls.logger.setLevel(logging.DEBUG)

    @classmethod
    def initialize_browser(cls, browser):
        if browser == "chrome":
            options = ChromeOptions()
            if HEADLESS:
                options.add_argument("--headless")
            service = ChromeService()
            return webdriver.Chrome(service=service, options=options)
        elif browser == "firefox":
            options = FirefoxOptions()
            firefox_options = options

            # Allow specific URLs to open external applications without prompting
            firefox_options.set_preference("network.protocol-handler.external-default", True)
            firefox_options.set_preference("network.protocol-handler.warn-external-default", False)

            # Configure Telegram protocol handlers
            firefox_options.set_preference("network.protocol-handler.external.telegram", True)
            firefox_options.set_preference("network.protocol-handler.warn-external.telegram", False)
            firefox_options.set_preference("network.protocol-handler.external.tg", True)
            firefox_options.set_preference("network.protocol-handler.warn-external.tg", False)

            # Trust t.me domain for Telegram links
            firefox_options.set_preference("permissions.default.desktop-notification", 1)

            # Explicitly allow https://t.me
            firefox_options.set_preference("network.autoconfig.url", "https://t.me")
            firefox_options.set_preference("network.autoconfig.enabled", True)

            # Add t.me to the list of allowed remote domains
            firefox_options.set_preference("dom.allow_scripts_to_close_windows", True)

            # Set permissions for opening external applications
            firefox_options.set_preference("browser.link.open_newwindow", 3)
            firefox_options.set_preference("browser.link.open_newwindow.restriction", 0)

            # Disable safe browsing checks for this test
            firefox_options.set_preference("browser.safebrowsing.enabled", False)
            if HEADLESS:
                options.add_argument("--headless")
            service = FirefoxService()
            return webdriver.Firefox(service=service, options=options)
        elif browser == "safari":
            options = SafariOptions()
            if HEADLESS:
                options.add_argument("--headless")
            service = SafariService()
            return webdriver.Safari(service=service, options=options)
        elif browser == "edge":
            options = EdgeOptions()
            if HEADLESS:
                options.add_argument("--headless")
            service = EdgeService()
            return webdriver.Edge(service=service, options=options)
        else:
            raise ValueError(f"Unsupported browser: {browser}")

    def __init__(self, methodName="runTest", language=None, browser=None):
        super().__init__(methodName)
        self.language = language
        self.browser = browser

        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.INFO)

        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

        log_filename = f"test_{self.__class__.__name__.lower()}_output.log"

        try:
            file_handler = logging.FileHandler(log_filename, mode='a', encoding='utf-8')
            file_handler.setLevel(logging.INFO)

            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(formatter)

            self.logger.addHandler(file_handler)
            self.logger.propagate = False

            self.logger.info(f"Logger initialized for {self.__class__.__name__}")
        except Exception as e:
            print(f"Error setting up logger: {str(e)}")

        self.login_field_locators = {
            "login_id": (By.ID, "usernameTextField"),
            "password": (By.ID, "passwordTextField")
        }

        self.register_field_locators = {
            "login_id": (By.ID, "register-login-id"),
            "password": (By.ID, "register-password"),
            "full_name": (By.ID, "register-full-name"),
            "phone_no": (By.ID, "register-phone-number")
        }

    def setUp(self):
        if not self.browser or not self.language:
            raise ValueError("Browser or language is not set.")
        self.logger.info(f"Setting up {self.browser} browser for {self.language} language...")
        self.driver = self.initialize_browser(self.browser)
        self.url = LANGUAGE_SETTINGS[self.language]["home_url"]
        self.driver.get(self.url)
        # size of iphone X, as desktop UI is not ready
        self.driver.set_window_size(375, 812)

    #id
    def navigate_to_login_page(self):
        self.annoucement_close_button()
        loginPage_button = WebDriverWait(self.driver,
                                         10).until(EC.element_to_be_clickable((By.ID, "unlogged-login-button")))
        loginPage_button.click()

    def verify_login(self, expected_username):
        self.annoucement_close_button()
        self.daily_checkin_close_button()
        self.click_navigation_bar("footer-profile-button")
        time.sleep(4)

        displayed_text = WebDriverWait(self.driver,
                                       10).until(EC.visibility_of_element_located((By.ID, "username"))).text
        self.logger.info(f"Displayed text: {displayed_text}")

        self.assertEqual(
            displayed_text, expected_username, f"Expected username: '{expected_username}', but got: '{displayed_text}'"
        )

    def navigate_to_register_page(self):
        self.annoucement_close_button()
        registerPage_button = WebDriverWait(self.driver,
                                            10).until(EC.element_to_be_clickable((By.ID, "unlogged-register-button")))
        registerPage_button.click()

    #id
    def click_navigation_bar(self, buttomNavigationBar):
        """
        Click on a navigation bar link
        Args:
            language (str): Language code (e.g., 'en', 'bm', 'cn')
            section (str): Section name (e.g., 'home', 'profile', 'games')
       
        try:
            xpath = f'//a[@href="/{language}/{section}"]'
            link = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.XPATH, xpath)))
            link.click()
            self.logger.info(f"Successfully clicked navigation link: /{language}/{section}")
            time.sleep(2)
        except Exception as e:
            self.logger.error(f"Failed to click navigation link /{language}/{section}: {str(e)}")
            self.fail(f"Could not click navigation link: {str(e)}")
        """
        try:
            link = self.driver.find_element(By.ID, buttomNavigationBar)
            actions = ActionChains(self.driver)
            actions.move_to_element(link).click().perform()
            time.sleep(2)
        except Exception as e:
            self.fail(f"Could not click navigation link: {str(e)}")

    #id
    def navigate_to_setting_page(self, language):
        self.click_navigation_bar("footer-profile-button")

        setting_link = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.ID, "settings-button")))
        setting_link.click()

    def navigate_to_profile_page(self, language):
        self.click_navigation_bar("footer-profile-button")

    def navigate_to_profile_menu(self, element_id):
        actions = ActionChains(self.driver)
        self.click_navigation_bar("footer-profile-button")
        time.sleep(5)
        link = self.driver.find_element(By.ID, element_id)
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", link)
        actions.move_to_element(link).click().perform()
        time.sleep(5)
    
    def navigate_to_live_page(self):
        self.click_navigation_bar("footer-live-button")
        time.sleep(2)
        self.boboLiveLogin()

    def navigate_AccSecurity(self):
        AccSecurity_page = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'a[href="setting/account"]'))
        )
        AccSecurity_page.click()

    def navigate_PaymentSetting(self):
        AccSecurity_page = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'a[href="setting/payment"]'))
        )
        AccSecurity_page.click()

    def navigate_ChangePassword(self):
        AccSecurity_page = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'a[href="setting/account/password"]'))
        )
        AccSecurity_page.click()

    def navigate_to_resetPassword_page(self):
        self.navigate_ChangePassword()

        AccPassword_page = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable(
                (By.XPATH, '//button[@type="button" and @role="tab" and contains(text(), "accPassword")]')
            )
        )
        AccPassword_page.click()

    def annoucement_close_button(self):
        action = ActionChains(self.driver)
        try:
            close_button = WebDriverWait(self.driver,
                                         10).until(EC.element_to_be_clickable((By.ID, "announcement-close-button")))

            action.move_to_element(close_button).click().perform()
        except TimeoutException:
            self.logger.info("No announcement popup found")
            pass

    def daily_checkin_close_button(self, close_mission=True):
        action = ActionChains(self.driver)
        try:
            close_button = WebDriverWait(self.driver,
                                         10).until(EC.element_to_be_clickable((By.ID, "close-modal-button")))

            action.move_to_element(close_button).click().perform()
            time.sleep(2)
            if close_mission:
                close_button = WebDriverWait(self.driver,
                                             10).until(EC.element_to_be_clickable((By.ID, "not-yet-check-in-close")))
                action.move_to_element(close_button).click().perform()
                time.sleep(2)
        except TimeoutException:
            self.logger.info("No checkin popup found")
            pass

    def perform_login(self, username, password, close_mission=True):
        self.enter_credentials(username, password)
        self.click_login_button()
        time.sleep(5)
        self.annoucement_close_button()
        time.sleep(2)
        self.daily_checkin_close_button(close_mission)

    def get_field(self, field_name, form_type="login"):
        if form_type == "login":
            locator_type, locator_value = self.login_field_locators[field_name]
        elif form_type == "register":
            locator_type, locator_value = self.register_field_locators[field_name]
        else:
            raise ValueError(f"Invalid form type: {form_type}")

        return WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located((locator_type, locator_value)))

    def enter_credentials(self, username, password):
        try:
            username_field = self.get_field("login_id", "login")
            username_field.clear()
            username_field.send_keys(username)

            password_field = self.get_field("password", "login")
            password_field.clear()
            password_field.send_keys(password)

        except Exception as e:
            self.logger.error(f"Error while entering credentials: {str(e)}")
            self.fail(f"Failed to enter credentials: {str(e)}")

    def click_login_button(self):
        login_button = WebDriverWait(self.driver, 20).until(EC.element_to_be_clickable((By.ID, "loginButton")))
        login_button.click()

    #id
    def success_icon(self):
        success_icon = WebDriverWait(self.driver,
                                     10).until(EC.visibility_of_element_located((By.CLASS_NAME, "swal2-success-ring")))
        self.assertTrue(success_icon.is_displayed(), "Success icon is not displayed")
        WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located((By.ID, "swal2-title")))

    #id
    def confirm_button(self):
        ok_button = WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.CLASS_NAME, "swal2-confirm")))
        ok_button.click()

    def handle_popup(self, expected_message):
        try:
            popup = WebDriverWait(self.driver,
                                  10).until(EC.visibility_of_element_located((By.ID, "swal2-html-container")))
            popup_text = popup.text
            self.assertIn(
                expected_message, popup_text,
                f"Expected message to include: '{expected_message}', but got: '{popup_text}'"
            )
            self.confirm_button()
        except TimeoutException:
            self.fail(f"Popup did not appear for the expected message: '{expected_message}'")
        except NoSuchElementException as e:
            self.fail(f"Element not found: {str(e)}")

    def check_field_validation_message(self, field, expected_message):
        try:
            validation_message = field.get_attribute("validationMessage")

            self.assertEqual(
                validation_message, expected_message,
                f"Expected validation message for field does not match. Found: '{validation_message}'"
            )
        except UnexpectedAlertPresentException as e:
            self.logger.error("Cannot see the validation message due to an exception.")
            self.fail("Validation Message does not appear")

    def error_box(self, expected_error_message, secondText=None):
        #id
        error_icon = WebDriverWait(self.driver,
                                   5).until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".swal2-icon")))
        self.assertTrue(error_icon.is_displayed(), "Error message is not displayed")

        invalidError = WebDriverWait(self.driver,
                                     10).until(EC.visibility_of_element_located((By.ID, "swal2-html-container")))
        self.assertIn(
            expected_error_message, invalidError.text,
            f"Popup message does not contain the expected text: {expected_error_message}"
        )
        if secondText:
            self.assertIn(
                secondText, invalidError.text, f"Popup message does not contain the expected text: {secondText}"
            )

        self.confirm_button()

    def success_box(self):
        success_icon = WebDriverWait(self.driver,
                                     10).until(EC.visibility_of_element_located((By.CLASS_NAME, "swal2-success-ring")))
        self.assertTrue(success_icon.is_displayed(), "Success icon is not displayed")

    def warning_box(self):
        warning_icon = WebDriverWait(self.driver,
                                     10).until(EC.visibility_of_element_located((By.CLASS_NAME, "swal2-icon-warning")))
        self.assertTrue(warning_icon.is_displayed(), "Warning icon is not displayed")

    def toggle_password_visibility(self, password_input, password):
        visibility_toggle = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label="toggle password visibility"]'))
        )
        assert (
            password_input.get_attribute("type") == "password"
        ), "Password field should initially be of type 'password'"

        visibility_toggle.click()
        time.sleep(2)
        assert (password_input.get_attribute("type") == "text"), "Password field should be of type 'text' when visible"
        assert (password_input.get_attribute("value") == password), "Visible password should match the entered password"

        visibility_toggle.click()
        time.sleep(2)
        assert (password_input.get_attribute("type") == "password"), "Password field should revert to type 'password'"

    def navigate_to_reload_page(self, tab):
        driver = self.driver

        if tab == "deposit":
            section_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "home-deposit-button")))
            section_button.click()
            time.sleep(2)

        elif tab == "withdraw":
            section_button = WebDriverWait(driver,
                                           10).until(EC.element_to_be_clickable((By.ID, "home-withdrawal-button")))
            section_button.click()
            time.sleep(2)

        elif tab == "transfer":
            section_button = WebDriverWait(driver,
                                           10).until(EC.element_to_be_clickable((By.ID, "home-transfer-button")))
            section_button.click()
            time.sleep(2)

    def choose_amount(self, index):
        driver = self.driver
        time.sleep(1)

        try:
            amount_section = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.ID, "amount-toggle-group"))
            )
            self.logger.info(f"Number of amount sections: {len(amount_section)}")

            buttons = amount_section[index].find_elements(By.CSS_SELECTOR, 'button[id^="amount-toggle-"]')

            self.logger.info(f"Number of amount buttons: {len(buttons)}")

            input_field = WebDriverWait(driver,
                                        10).until(EC.presence_of_element_located((By.ID, "reload-amount-input")))

            for button in buttons:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                time.sleep(1)

                try:
                    button.click()
                except Exception:
                    driver.execute_script("arguments[0].click();", button)

                time.sleep(1)

                button_value = button.get_attribute("value")
                input_value = input_field.get_attribute("value")

                self.logger.info(f"Clicked button with value: {button_value}")
                self.logger.info(f"Input field text: {input_value}")

                if button_value == input_value:
                    self.logger.info(
                        f"Text matched: Button value '{button_value}' matches input field text '{input_value}'"
                    )
                else:
                    self.logger.error(
                        f"Text did not match: Button value '{button_value}' does not match input field text '{input_value}'"
                    )

        except Exception as e:
            self.fail(f"Failed to test amount buttons: {str(e)}")

    def open_dropdown(self, expand_icon_index):
        driver = self.driver
        try:
            expand_more_icons = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, "button.MuiButton-outlinedPrimary svg[data-testid='ExpandMoreIcon']")
                )
            )
            self.logger.info(f"Expand more icons: {expand_more_icons}")
            expand_more_icons[expand_icon_index].click()
            time.sleep(1)

        except Exception as e:
            self.fail(f"Failed to open dropdown: {str(e)}")

    def check_disable_item(self, item, item_text):
        try:
            item.click()
            self.fail(f"Disabled item '{item_text}' should not be clickable.")
        except Exception as e:
            self.logger.info(f"Confirmed disabled item '{item_text}' is not clickable as expected.")

    def check_selected_item(self, selected_text, item_text):
        if item_text == selected_text:
            self.logger.info(f"Text matched: {item_text}")
        else:
            self.logger.error(f"Text did not match: Expected '{item_text}', but got '{selected_text}'")

    def click_usage_details_button(self):
        try:
            button = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.ID, "use-details-button")))
            button.click()
            self.logger.info(f"Successfully clicked button")
        except Exception as e:
            self.logger.error(f"Failed to click button: {str(e)}")
            self.fail(f"Could not click button: {str(e)}")

    # bonus%, turnover, minimum reload, maximum reload
    #change
    def check_promo_details(self, extractedPercentage, language):
        driver = self.driver
        self.logger.info("View promo details")
        self.click_usage_details_button()
        bonusTitle = WebDriverWait(self.driver,
                                   10).until(EC.presence_of_element_located((By.ID, "promo-percentage"))).text
        self.logger.info(bonusTitle)
        bonusTitle2 = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, "bonus-value"))).text
        self.logger.info(bonusTitle2)
        try:
            self.assertEqual(
                extractedPercentage, bonusTitle,
                msg=f"Expected text '{extractedPercentage}' does not match actual text '{bonusTitle}'"
            )
            self.assertEqual(
                extractedPercentage, bonusTitle2,
                msg=f"Expected text '{extractedPercentage}' does not match actual text '{bonusTitle2}'"
            )

        except AssertionError as e:
            self.logger.error(f"Assertion failed: {str(e)}")
            self.fail("Not equal content")

        bonusDesc = WebDriverWait(self.driver,
                                  10).until(EC.presence_of_element_located((By.ID, "promo-name"))).text  #Max 300.00
        self.logger.info(bonusDesc)

        #waitid
        time.sleep(1)
        close_button = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-testid="CloseIcon"]'))
        )
        close_button.click()
        time.sleep(2)

    def check_match_record(self, date, index):
        driver = self.driver

        while True:
            time.sleep(1)
            table_rows = driver.find_elements(By.CSS_SELECTOR, "tbody.MuiTableBody-root tr")
            self.logger.info(f"Found {len(table_rows)} rows in the current page")

            for row in table_rows:
                date_cell = row.find_element(By.CSS_SELECTOR, "td.MuiTableCell-body")
                date_str = date_cell.text.split(' ')[0]
                self.logger.info(f"Checking date: {date_str}")
                day, month, year = date_str.split('/')
                try:
                    if index == 0 or index == 1:
                        if index == 0:
                            self.logger.info("Today")
                        else:
                            self.logger.info("Yesterday")
                        self.assertEqual(date_str, date, "Wrong Result")
                        self.logger.info("Matched")
                    elif index == 2:
                        self.logger.info("1 Week")
                        self.assertIn(date_str, date, "Date not found in dates_list")
                        self.logger.info("Matched")
                    elif index == 3:
                        self.logger.info("1 Month")
                        self.logger.info(f"Extracted month: {month}")
                        self.assertEqual(month, date, "Date not found in dates_list")
                        self.logger.info("Matched")
                    else:
                        self.logger.info("3 months")
                        self.logger.info(len(date))
                        self.assertIn(month, date, "Date not found in dates_list")
                        self.logger.info("Matched")
                except AssertionError as e:
                    self.logger.error(f"Assertion failed: {str(e)}")
                    self.fail("Wrong Date Display")

            time.sleep(2)
            next_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "button[aria-label='Go to next page']"))
            )

            # Check if the button is clickable and not disabled
            if "Mui-disabled" not in next_button.get_attribute("class"):
                driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                next_button.click()
            else:
                self.logger.info("Next button is disabled; no more pages left.")
                break

            WebDriverWait(driver,
                          10).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "tbody.MuiTableBody-root")))

            table_rows = driver.find_elements(By.CSS_SELECTOR, "tbody.MuiTableBody-root tr")
            self.logger.info(f"Found {len(table_rows)} rows after navigating to the next page")

            WebDriverWait(driver, 2).until(EC.visibility_of(table_rows[0]))

    #Test Specific
    #Test "Bet Record"
    def select_specific_info(self, index, record_type=None):
        driver = self.driver
        try:
            if record_type:
                self.open_dropdown(index)

                options = WebDriverWait(driver, 10).until(
                    EC.visibility_of_all_elements_located((By.CSS_SELECTOR, "li.MuiMenuItem-root"))
                )
                option = options[0].text
                self.logger.info(f"Selecting option: {option}")
                options[0].click()
            else:
                self.select_dropdown_option(
                    expand_icon_index=1, item_css_selector="li.MuiMenuItem-root", selected_index=1,
                    bank_transfer_reload=False, extract_text=False, language=self.language, scan_reload=False,
                    history=True
                )

        except Exception as e:
            self.fail(f"Failed to randomly select an option: {str(e)}")

    #check record!!
    def calculate_date(self, index):
        current_date = datetime.now()

        #Retrieve current date
        if index == 0:
            formatted_today = current_date.strftime("%d/%m/%Y")
            self.logger.info(f"Current Date: {formatted_today}")
            self.check_match_record(formatted_today, index)

        #Retrieve yesterday date
        elif index == 1:
            yesterday = current_date - timedelta(days=1)
            formatted_yesterday = yesterday.strftime("%d/%m/%Y")
            self.logger.info(f"Yesterday Date: {formatted_yesterday}")
            self.check_match_record(formatted_yesterday, index)

        #Retrieve previous 1 week
        elif index == 2:
            dates_list = []
            for i in range(7):
                date = current_date - timedelta(days=i)
                dates_list.append(date.strftime("%d/%m/%Y"))
            self.logger.info("Dates from today back to the previous week:")
            for date in dates_list:
                self.logger.info(date)
            self.check_match_record(dates_list, index)

        #Retrieve current month
        elif index == 3:
            current_month = current_date.strftime("%m")
            self.logger.info(f"Current Month: {current_month}")
            self.check_match_record(current_month, index)

        #Retrieve previous 3 months
        else:
            current_month_int = current_date.month
            previous_months = []
            previous_months.append(f"{current_month_int:02}")
            for i in range(1, 3):
                previous_month = current_month_int - i
                if previous_month <= 0:
                    previous_month += 12
                previous_months.append(f"{previous_month:02}")
            self.logger.info("Dates previous months:")
            for month in previous_months:
                self.logger.info(month)
            self.check_match_record(previous_months, index)

    # promo popo not dropdownlist wrong info
    def select_dropdown_option(
        self, expand_icon_index, item_css_selector, extract_acc=None, usage_details=None, reload=None,
        choose_account=None, check_add_account=None, choose_history_date=None, check_start_end_disable=False
    ):
        driver = self.driver

        self.open_dropdown(expand_icon_index)

        options = WebDriverWait(driver,
                                3).until(EC.visibility_of_all_elements_located((By.CSS_SELECTOR, item_css_selector)))

        self.logger.info(f"Found {len(options)} options")
        if choose_account:
            return options
        bank_list = []
        for index in range(len(options)):

            options = WebDriverWait(driver, 3).until(
                EC.visibility_of_all_elements_located((By.CSS_SELECTOR, item_css_selector))
            )

            item = options[index]
            itemText = item.text
            self.logger.info(f"Clicking on item: {itemText}")

            if check_add_account:
                bank_list.append(itemText)
                continue
            else:
                driver.execute_script("arguments[0].scrollIntoView(true);", item)
                WebDriverWait(driver, 3).until(EC.element_to_be_clickable(item)).click()

                time.sleep(1)
                if choose_history_date:
                    self.calculate_date(index)
                if check_start_end_disable:
                    start_date = driver.find_element(By.ID, "start-date-picker")
                    end_date = driver.find_element(By.ID, "end-date-picker")

                    start_disabled = not start_date.is_enabled()
                    end_disabled = not end_date.is_enabled()
                    self.assertTrue(start_disabled, "Start date is not disabled")
                    self.assertTrue(end_disabled, "End date is not disabled")
                if reload:
                    #waitid
                    promo_button = WebDriverWait(driver, 3).until(
                        EC.presence_of_element_located((
                            By.CSS_SELECTOR,
                            "[data-field='selectedPromo'] button.MuiButton-outlinedPrimary p.MuiTypography-body1"
                        ))
                    )
                    selected_text = promo_button.text
                    self.logger.info(f"Selected text: {selected_text}")
                    self.logger.info(selected_text)
                    self.check_selected_item(selected_text, itemText)
                    if usage_details:
                        if "%" in itemText:
                            for part in itemText.split():
                                if "%" in part:
                                    number = float(part.replace('%', ''))
                                    extractedPercentage = f"{number:.2f}%"
                                    self.logger.info(f"Extracted percentage: {extractedPercentage}")
                                    break
                        self.check_promo_details(
                            extractedPercentage, self.language
                        )  #pass (Max 300.00, and mini reload)
                if extract_acc:
                    itemText = itemText.split('\n')[-1] if itemText else None
                    #waitid
                    bankAccountText = WebDriverWait(driver, 3).until(
                        EC.presence_of_element_located((
                            By.CSS_SELECTOR,
                            "[data-field='userBank'] button.MuiButton-outlinedPrimary p.MuiTypography-body1"
                        ))
                    )
                    selected_text = bankAccountText.text

                #if (expand_icon_index == 2 and not history) or usagedetails:  #check promo details
                #   self.check_promo_details(original_text, language)
                if index < len(options) - 1:
                    self.open_dropdown(expand_icon_index)
                else:
                    break

            time.sleep(1)
        if check_add_account:
            return bank_list

    def select_random_amount(self):
        driver = self.driver
        try:
            amount_section = WebDriverWait(driver,
                                           10).until(EC.presence_of_element_located((By.ID, "amount-toggle-group")))
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", amount_section)
            time.sleep(1)

            buttons = amount_section.find_elements(By.TAG_NAME, 'button')
            self.logger.info(f"Number of buttons found: {len(buttons)}")

            random_button = random.choice(buttons)
            self.logger.info(f"Selected button: {random_button}")
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", random_button)
            time.sleep(1)
            random_button.click()
            self.logger.info("Clicked")

            button_value = random_button.get_attribute("value")
            self.logger.info(f"Randomly selected amount button with value: {button_value}")
            return button_value

        except Exception as e:
            self.fail(f"Failed to randomly select an amount: {str(e)}")

    def select_random_promo(self, expand_icon_index):
        driver = self.driver
        try:
            self.open_dropdown(expand_icon_index)

            promo_options = WebDriverWait(driver, 10).until(
                EC.visibility_of_all_elements_located((By.CSS_SELECTOR, "li.MuiMenuItem-root"))
            )

            available_promos = list(promo_options)

            while available_promos:
                random_promo = random.choice(available_promos)
                random_promo_text = random_promo.text
                available_promos.remove(random_promo)

                if "Mui-disabled" in random_promo.get_attribute("class"):
                    self.logger.info(f"Found disabled promo: {random_promo_text}, trying another.")
                    continue

                self.logger.info(f"Randomly selecting promo option: {random_promo_text}")

                time.sleep(2)
                WebDriverWait(driver, 10).until(EC.element_to_be_clickable(random_promo)).click()

                return random_promo_text

            self.logger.warning("No enabled promo options found.")

        except Exception as e:
            self.fail(f"Failed to randomly select a promo option: {str(e)}")

    def handleDeposit(self, ID, isReject=False, isProcessing=False):
        if isReject:
            url = CREDENTIALS["RejectDepositRequest"].format(BO_base_url = CREDENTIALS["BO_base_url"], ID=ID)
        elif isProcessing:
            url = CREDENTIALS["ProcessingDepositRequest"].format(BO_base_url = CREDENTIALS["BO_base_url"], ID=ID)
        else:
            url = CREDENTIALS["ApproveDepositRequest"].format(BO_base_url = CREDENTIALS["BO_base_url"], ID=ID)

        response = requests.get(url)

        if isReject:
            if response.status_code == 200:
                self.logger.info(f"Successfully rejected deposit for ID {ID}")
            else:
                self.logger.error(f"Failed to reject. Status code: {response.status_code}")
                self.fail("Reject deposit failed")
        elif isProcessing:
            if response.status_code == 200:
                self.logger.info(f"Successfully processing deposit for ID {ID}")
            else:
                self.logger.error(f"Failed to processing. Status code: {response.status_code}")
                self.fail("Processing deposit failed")

        else:
            if response.status_code == 200:
                self.logger.info(f"Successfully approved deposit for ID {ID}")
            else:
                self.logger.error(f"Failed to approve. Status code: {response.status_code}")
                self.fail("Approve deposit failed")

    def generic_submit(
        self, field=None, expected_result=None, check_general_error=None, check_ewallet_number=None,
        expected_error=None, submit=None, id=None, turnoverIncomplete=None, locked_by_list=None, transfer_check=False,
        turnoverList=None
    ):
        driver = self.driver
        time.sleep(2)
        submit_button = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.ID, submit)))
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_button)
        time.sleep(3)
        submit_button.click()
        time.sleep(2)

        if expected_result == "success":
            try:
                if submit == "submit-withdraw-button":
                    self.logger.info("Submit withdraw button clicked")
                    success_popup = WebDriverWait(self.driver, 10).until(
                        EC.visibility_of_element_located((By.ID, "result-modal-title"))
                    )
                    success_popup_text = success_popup.text
                    self.assertEqual(
                        success_popup_text, LANGUAGE_SETTINGS[self.language]["success"]["withdraw_success"],
                        "Success popup not shown"
                    )
                    #waitid
                    OkButton = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((
                            By.XPATH,
                            "//div[contains(@class, 'MuiBox-root')]//p[@id='result-modal-title']/../..//button"
                        ))
                    )
                    OkButton.click()
                    time.sleep(1)

                else:
                    self.success_box()
            except:
                self.fail("Cannot submit successfully")

        elif expected_result == "failure":
            time.sleep(1)
            if check_general_error:
                self.check_general_error(
                    expected_error, id, turnoverIncomplete=turnoverIncomplete, locked_by_list=locked_by_list,
                    transfer_check=transfer_check, turnoverList=turnoverList
                )
            elif check_ewallet_number:
                #change (if enter chracter or 0 / neg )
                self.logger.info("Invalid ewallet number")
            else:
                self.logger.info("Fail")
                self.check_field_validation_message(field, LANGUAGE_SETTINGS[self.language]["errors"]["field_missing"])

    def check_general_error(
        self, expected_error_message=None, id=None, turnoverIncomplete=False, locked_by_list=None, transfer_check=False,
        turnoverList=None
    ):
        driver = self.driver
        if id:
            popup = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, id)))
            popup_text = popup.text

            if turnoverIncomplete:
                self.logger.info(f"Turnover incomplete: {turnoverList}")
                base_error = (
                    LANGUAGE_SETTINGS[self.language]["errors"]["bonus_locked"]
                    if transfer_check else LANGUAGE_SETTINGS[self.language]["errors"]["withdraw_turnover_incomplete"]
                )

                try:
                    # First check if message starts with base error
                    self.assertTrue(
                        popup_text.startswith(base_error),
                        f"Error message '{popup_text}' does not start with '{base_error}'"
                    )

                    if locked_by_list or turnoverList:
                        if transfer_check:
                            start_bracket = popup_text.find('(')
                            end_bracket = popup_text.find(')')
                            if start_bracket != -1 and end_bracket != -1:
                                popup_providers = popup_text[start_bracket + 1:end_bracket].split(', ')
                                found_match = any(item in popup_providers for item in locked_by_list
                                                  ) or any(item in popup_providers for item in turnoverList)
                                self.assertTrue(
                                    found_match,
                                    f"None of the expected providers {locked_by_list} or {turnoverList} found in popup message {popup_providers}"
                                )
                            else:
                                self.fail(f"No brackets found in popup text: {popup_text}")
                        else:
                            popup_items = re.search(r'\((.*?)\)', popup_text)
                            if popup_items:
                                popup_items = set(item.strip() for item in popup_items.group(1).split(','))
                                expected_items = set(locked_by_list)
                                self.assertEqual(
                                    popup_items, expected_items,
                                    f"Locked by items don't match. Expected: {expected_items}, Got: {popup_items}"
                                )
                            else:
                                self.fail("No items found between parentheses in popup text")

                except AssertionError as e:
                    self.logger.error(f"Assertion failed: {str(e)}")
                    self.fail(str(e))
            else:
                self.assertEqual(
                    expected_error_message, popup_text,
                    f"Popup text does not contain the expected field label '{expected_error_message}'"
                )
        else:
            error_icon = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "div.swal2-icon.swal2-error.swal2-icon-show"))
            )
            self.assertTrue(error_icon.is_displayed(), "Error icon is not displayed after submit")

        self.confirm_button()

    def click_submit_button(self, texts, history=None, add_account=None):
        for text in texts:
            try:
                if history:
                    button = WebDriverWait(self.driver, 20).until(
                        EC.element_to_be_clickable((By.XPATH, f"//button[contains(text(), '{text}')]"))
                    )
                elif add_account:
                    button = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable(
                            (By.XPATH, f"//button//p[contains(text(), '{text}')]//parent::button")
                        )
                    )
                    button.click()
                else:
                    button = WebDriverWait(self.driver, 30).until(
                        EC.element_to_be_clickable((By.XPATH, f'//button[.//p[contains(text(), "{text}")]]'))
                    )
                self.driver.execute_script("arguments[0].scrollIntoView(true);", button)
                button.click()
                self.logger.info(f"Clicked the submit button with text: {text}")
                break
            except Exception:
                self.logger.error(f"Button with text '{text}' not found or not clickable within the timeout.")

    def get_all_button_texts(self, history=None):

        driver = self.driver

        buttons = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "button.MuiButton-outlinedPrimary"))
        )

        button_texts = []
        self.logger.info(button_texts)

        for button in buttons:
            try:
                if history:
                    button_text = button.text.strip()
                    self.logger.info(button_text)
                else:
                    button_text = button.find_element(By.CSS_SELECTOR, "p.MuiTypography-root").text.strip()
                button_texts.append(button_text)
            except Exception as e:
                self.logger.error(f"Failed to get text from button: {str(e)}")

        self.logger.info(len(button_texts))
        return button_texts

    def upload_from_camera(self):
        driver = self.driver
        try:
            camera_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "upload-camera-button")))
            camera_button.click()
            time.sleep(2)
            take_photo_button = WebDriverWait(driver,
                                              10).until(EC.element_to_be_clickable((By.ID, "camera-capture-button")))
            take_photo_button.click()
            return True
        except Exception as e:
            self.fail("Cannot upload using camera feature")
            return False
        return True

    def upload_from_gallery(self, replace=False, checkLargeFile=False):
        if checkLargeFile:
            self.test_image_url = PROFILE_URL["large_image_url"]
        else:
            if replace:
                self.test_image_url = PROFILE_URL["replace_image_url"]
            else:
                self.test_image_url = PROFILE_URL["valid_image_url"]

        driver = self.driver
        gallery_text = LANGUAGE_SETTINGS[self.language]["change_profile"]["gallery"]
        try:
            # Get the filename from URL
            filename = os.path.basename(urlparse(self.test_image_url).path)

            # Create a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as temp_file:
                try:
                    response = requests.get(self.test_image_url)
                    response.raise_for_status()  # Raises an HTTPError for bad responses
                    temp_file.write(response.content)
                    self.test_image_path = temp_file.name
                except requests.exceptions.RequestException as e:
                    self.fail(f"Failed to download image from URL: {e}")
                    return False

            if not os.path.exists(self.test_image_path):
                raise FileNotFoundError(f"Test image not found at {self.test_image_path}")
                
            # Make the file readable by all users (world-readable)
            os.chmod(self.test_image_path, 0o644)
            self.logger.info(f"Changed file permissions to make it world-readable: {self.test_image_path}")

            time.sleep(2)
            gallery_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "upload-gallery-button")))
            gallery_button.click()
            self.logger.info(f"Clicked '{gallery_text}' button")

            file_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']"))
            )
            self.logger.info("File input element located.")
            file_input.send_keys(self.test_image_path)
            time.sleep(2)
            self.logger.info(f"Uploaded image from {self.test_image_path}")

        except Exception as e:
            self.logger.error(f"Failed to upload from gallery: {str(e)}")
            self.fail("Cannot upload using choose from gallery feature")
            return False

        return True

    def verify_uploaded_image(self, remove):
        driver = self.driver

        if remove:
            WebDriverWait(driver, 10).until(EC.invisibility_of_element_located((By.ID, "receipt-img")))
            return True
        else:
            image = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "receipt-img")))
            image.get_attribute('src')

            if image.is_displayed():
                self.logger.info("Image has been uploaded and displayed correctly.")
                return True
            else:
                self.logger.error("Image was not displayed correctly.")
                return False

    def check_balance(self, total_amount=None, games_amount=None, language=None, return_balance=None):
        driver = self.driver
        time.sleep(2)
        deposit_balance_element = WebDriverWait(driver,
                                                10).until(EC.visibility_of_element_located((By.ID, "wallet-balance")))

        deposit_balance_text = deposit_balance_element.text.strip()
        deposit_balance_text = deposit_balance_text.replace("RM", "").strip()

        self.logger.info(f"Deposit Balance: {deposit_balance_text}")

        if return_balance:
            return deposit_balance_text

        balance_errors = []

        if total_amount != deposit_balance_text:
            balance_errors.append(
                f"Total amount ({total_amount}) does not match deposit balance ({deposit_balance_text})"
            )

        if games_amount != deposit_balance_text:
            balance_errors.append(
                f"Games amount ({games_amount}) does not match deposit balance ({deposit_balance_text})"
            )

        if total_amount != games_amount:
            balance_errors.append(f"Total amount ({total_amount}) does not match games amount ({games_amount})")

        if balance_errors:
            for error in balance_errors:
                self.logger.error(error)
            self.fail("Balance mismatch found")

    #havent test
    def extract_amount(self, div_selector, p_index):
        driver = self.driver
        div = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.CSS_SELECTOR, div_selector)))
        p_elements = div.find_elements(By.TAG_NAME, "p")

        if len(p_elements) > p_index:
            amount_text = p_elements[p_index].text.strip()
            amount_value = float(amount_text.split()[-1])
            return amount_value

    #havent test
    def check_non_withdrawable(self):
        driver = self.driver

        non_withdrawable_amount = self.extract_amount("div.MuiPaper-root.mui-theme-l6njlf", 1)
        non_withdrawable_section = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "div.MuiPaper-root.mui-theme-l6njlf"))
        )
        non_withdrawable_section.click()
        time.sleep(2)
        parent_divs = driver.find_elements(
            By.CLASS_NAME, "MuiPaper-root.MuiPaper-elevation.MuiPaper-rounded.MuiPaper-elevation0.mui-theme-ppvpol"
        )
        total_amount = 0
        for parent_div in parent_divs:
            second_p = parent_div.find_element(
                By.XPATH, ".//div[contains(@class, 'MuiBox-root mui-theme-3mllz6')]//p[1]"
            )
            amount = second_p.text
            if amount.startswith("RM"):
                amount = amount[2:]
            total_amount += int(amount)
        self.logger.info(total_amount)
        try:
            self.assertEqual(total_amount, non_withdrawable_amount, "Non-Withdrawable Amount does not match!")
        except AssertionError as e:
            self.logger.error("Non-Withdrawable Amount do not match")
            self.fail(f"Non-Withdrawable Amount do not match: {str(e)}")

    #havent test
    def check_games_balance(self):
        driver = self.driver

        self.click_navigation_bar("footer-game-button")
        games_balance_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'a.MuiButtonBase-root'))
        )

        games_balance = games_balance_element.text
        games_amount = games_balance.replace("RM", "").strip()
        return games_amount

    def enter_voucher(self, voucher):
        driver = self.driver
        voucher_field = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, "promo-code-input")))
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", voucher_field)
        voucher_field.send_keys(voucher)
        time.sleep(1)
        arrow_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "apply-button")))
        arrow_button.click()
        self.logger.info("Clicked the arrow button successfully")
        time.sleep(1)

    def check_disable_field(self, item, check=None):
        is_disabled = ('Mui-disabled' in item.get_attribute('class') or item.get_attribute('disabled') is not None)

        if is_disabled:
            self.logger.info("The field is disabled.")
            if check:
                return True
        else:
            if check:
                return False
            self.logger.info("The field is not disabled.")
            self.fail("The field is expected to be disabled but is not.")

    def verifyFieldDisable(self, fieldName, check=None):
        driver = self.driver
        try:
            #id
            fieldButton = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, f"[data-field='{fieldName}'] button.MuiButton-outlinedPrimary")
                )
            )

            self.logger.info(f"Checking if {fieldName} field is disabled")
            return self.check_disable_field(fieldButton, check=check)

        except Exception as e:
            self.logger.error(f"Failed to verify {fieldName} field state: {str(e)}")
            return False

    def apply_valid_voucher(self, expand_icon_index, deposit_banktransfer):
        driver = self.driver
        self.enter_voucher(CREDENTIALS["deposit"]["valid_voucher"])
        try:
            WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "svg[data-testid='CheckCircleOutlineIcon']"))
            )
        except:
            self.fail("Cannot apply the valid voucher")
        time.sleep(2)
        self.choose_promo_code(
            driver, expand_icon_index, self.language, deposit_banktransfer=deposit_banktransfer,
            voucher_code=CREDENTIALS["deposit"]["valid_voucher"]
        )
        if self.verify_voucher_field_disable(check=True):
            self.logger.info("Pass: Promo voucher was cleared correctly after selecting the Popo promo.")
        else:
            self.fail("The voucher input field does not disable")

    def generic_apply_invalid_voucher(self, invalidVoucher):
        driver = self.driver
        self.enter_voucher(invalidVoucher)
        #waitid
        #WebDriverWait(driver, 10).until(
        #    EC.visibility_of_element_located((By.CSS_SELECTOR, "svg[data-testid='CancelOutlinedIcon']"))
        #)

    def verify_clear_functionality(
        self, initial_button_texts, button_indices, check_image_removal=None, transferChecking=False
    ):
        driver = self.driver
        try:
            if transferChecking:
                amount_field = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "amount-input")))
                final_button_texts = [self.get_all_button_texts()[index] for index in button_indices]

                if (
                    amount_field.get_attribute("value") == ""
                    and all(initial == final for initial, final in zip(initial_button_texts, final_button_texts))
                ):
                    self.logger.info("Transfer fields are cleared as expected.")
                else:
                    self.fail("The transfer fields were not cleared correctly.")
                return

            amount_field = WebDriverWait(driver,
                                         10).until(EC.presence_of_element_located((By.ID, "reload-amount-input")))
            voucherField = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "promo-code-input")))

            final_button_texts = [self.get_all_button_texts()[index] for index in button_indices]

            image_removed = True
            if check_image_removal:
                image_removed = self.verify_uploaded_image(remove=True)

            if (
                amount_field.get_attribute("value") == ""
                and all(initial == final for initial, final in zip(initial_button_texts, final_button_texts))
                and not self.verifyFieldDisable("voucher", check=True)
                and not self.verifyFieldDisable("selectedPromo", check=True)
                and voucherField.get_attribute("value") == "" and image_removed
            ):
                self.logger.info("All fields are cleared as expected.")
            else:
                self.fail("The fields were not cleared correctly.")
        except Exception as e:
            self.fail(f"Failed to verify clear button functionality: {str(e)}")

    def verify_added_account(self, bank_chosen, entered_acc, setting=False):
        if setting:
            bank_list = []
            self.logger.info("Checking for existing accounts in Setting page")
            try:
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
                accounts = bank_list
            except Exception as e:
                self.logger.error(f"Error finding accounts: {str(e)}")
                return False, 0

        else:
            accounts = self.select_dropdown_option(
                expand_icon_index=0, item_css_selector="li.MuiMenuItem-root", extract_acc=False, check_add_account=True
            )

        self.logger.info(f"Found {len(accounts)} accounts")
        for acc in accounts:
            accDetails = acc.splitlines()
            self.logger.info(f"Account details: {accDetails}")  # Debug log

            if setting:
                # Handle 4-line format for settings page
                if len(accDetails) == 4:
                    name, bank, acc, extra = accDetails
                    self.logger.info(f"Bank: {bank}, Name: {name}, Account: {acc}")
                    if bank.lower() == bank_chosen.lower() and acc == entered_acc:
                        self.logger.info("Match found!")
                        return True, len(accounts)
            else:
                # Handle 3-line format for non-settings page
                if len(accDetails) == 3:
                    name, bank, acc = accDetails
                    self.logger.info(f"Bank: {bank}, Name: {name}, Account: {acc}")
                    if bank.lower() == bank_chosen.lower() and acc == entered_acc:
                        self.logger.info("Match found!")
                        return True, len(accounts)

            self.logger.warning(f"Unexpected account format: {len(accDetails)} lines")

        self.logger.info("No match found.")
        return False, len(accounts)

    def genericAddAccount(
        self, checkDuplicated=False, checkMaxAccounts=False, checkInvalidAcc=False, bank_list=None, setting=False
    ):
        try:
            time.sleep(2)
            if bank_list:
                existingAccounts = bank_list
            else:
                existingAccounts = self.select_dropdown_option(
                    expand_icon_index=0, item_css_selector="li.MuiMenuItem-root", extract_acc=False,
                    check_add_account=True
                )

            if checkMaxAccounts:

                currentAccountCount = len(existingAccounts)
                self.logger.info(f"Current number of accounts: {currentAccountCount}")

                if currentAccountCount >= 5:
                    time.sleep(2)
                    self.addSingleAccount(existingAccounts, checkMaxAccounts=True, setting=setting)
                    return
                else:
                    while currentAccountCount < 5:
                        verificationResult, currentAccountCount = self.addSingleAccount(
                            existingAccounts, setting=setting
                        )
                        time.sleep(2)
                        self.logger.info(f"Added account. Current count: {currentAccountCount}")

                    self.addSingleAccount(existingAccounts, checkMaxAccounts=True, setting=setting)
                    return

            if checkDuplicated and existingAccounts:
                accDetails = existingAccounts[0].splitlines()
                if setting:
                    if len(accDetails) == 4:
                        _, bankToDuplicate, accToDuplicate, _ = accDetails
                        self.logger.info(
                            f"Attempting to duplicate - Bank: {bankToDuplicate}, Account: {accToDuplicate}"
                        )
                else:
                    if len(accDetails) == 3:
                        _, bankToDuplicate, accToDuplicate = accDetails
                        self.logger.info(
                            f"Attempting to duplicate - Bank: {bankToDuplicate}, Account: {accToDuplicate}"
                        )
                self.addSingleAccount(
                    existingAccounts, bankToDuplicate=bankToDuplicate, accToDuplicate=accToDuplicate, setting=setting
                )
                return

            if checkInvalidAcc:
                self.addSingleAccount(existingAccounts, checkInvalidAcc=True, setting=setting)
                return

            self.addSingleAccount(existingAccounts, setting=setting)

        except Exception as e:
            self.logger.error(f"Test failed: {str(e)}")
            self.fail(f"Test failed: {str(e)}")

    def addSingleAccount(
        self, existingAccounts=None, bankToDuplicate=None, accToDuplicate=None, checkInvalidAcc=False,
        checkMaxAccounts=False, setting=False
    ):
        driver = self.driver
        try:
            if setting:
                addAccountButton = WebDriverWait(driver,
                                                 10).until(EC.element_to_be_clickable((By.ID, "add-account-button")))
                addAccountButton.click()
                time.sleep(2)
            else:
                addAccountButton = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "add-bank-account-button"))
                )
                addAccountButton.click()
            time.sleep(2)

            WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.ID, "add-bank-form")))
            bankDropdown = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.ID, "bank-select")))
            bankDropdown.click()
            time.sleep(2)

            options = WebDriverWait(driver, 3).until(
                EC.presence_of_all_elements_located((By.XPATH, '//ul[@role="listbox"]//li'))
            )
            self.logger.info(len(options))
            if checkInvalidAcc:
                random.choice(options).click()
                self.addInvalidAcc()
                return

            existing_banks = []
            existing_acc_numbers = []
            if existingAccounts:
                for acc in existingAccounts:
                    accDetails = acc.splitlines()
                    if len(accDetails) == 3:
                        _, bank, acc_num = accDetails
                        existing_banks.append(bank)
                        existing_acc_numbers.append(acc_num)

            if bankToDuplicate:
                for option in options:
                    if option.text == bankToDuplicate:
                        option.click()
                        bankChosen = bankToDuplicate
                        accountNumber = accToDuplicate
                        break
            else:
                while True:
                    self.logger.info(len(options))
                    randomOption = random.choice(options)
                    self.logger.info(randomOption.text)
                    bankChosen = randomOption.text
                    accountNumber = ''.join(random.choices('123456789', k=random.randint(8, 12)))

                    if bankChosen not in existing_banks and accountNumber not in existing_acc_numbers:
                        randomOption.click()
                        break
                    bankDropdown.click()
                    time.sleep(1)

            accNumberField = WebDriverWait(driver,
                                           3).until(EC.visibility_of_element_located((By.ID, "acc-number-input")))
            accNumberField.send_keys(accountNumber)
            enteredAcc = accNumberField.get_attribute("value")
            time.sleep(2)

            confirmButton = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.ID, "submit-bank-button")))
            confirmButton.click()
            time.sleep(2)

            if checkMaxAccounts:
                self.check_general_error(
                    expected_error_message=LANGUAGE_SETTINGS[self.language]["errors"]["max_accounts"],
                    id="swal2-html-container"
                )
                return
            elif bankToDuplicate:
                self.check_general_error(
                    expected_error_message=LANGUAGE_SETTINGS[self.language]["errors"]["duplicated_account"],
                    id="swal2-html-container"
                )
                return
            else:
                self.logger.info("success")
                self.success_box()
                self.confirm_button()
                time.sleep(3)
                verificationResult, numAccounts = self.verify_added_account(bankChosen, enteredAcc, setting=setting)
                if verificationResult:
                    return True, numAccounts
                else:
                    self.fail("Account was not added")

        except Exception as e:
            self.logger.error(f"Unable to add account: {str(e)}")
            self.fail(f"Unable to add account: {str(e)}")

    def addInvalidAcc(self):
        driver = self.driver

        accNumberField = WebDriverWait(driver, 3).until(EC.visibility_of_element_located((By.ID, "acc-number-input")))
        letters = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
        specialChars = '!@#$%^&*()_+-=[]{}|;:,.<>?'
        invalidLength = random.randint(8, 12)
        invalid_chars = letters + specialChars
        invalidInput = ''.join(random.choice(invalid_chars) for _ in range(invalidLength))
        accNumberField.send_keys(invalidInput)
        enteredAcc = accNumberField.get_attribute("value")
        self.logger.info(f"Value in field after attempt: {enteredAcc}")
        if enteredAcc == "":
            self.logger.info("Success: Invalid characters were blocked")
        else:
            self.fail(f"Invalid characters were accepted: {enteredAcc}")

    def choose_random_bank_account(self):
        self.scrollToSection("wallet-form-bankAccount")
        time.sleep(1)
        bankOptions = self.select_dropdown_option(
            expand_icon_index=0, item_css_selector="li.MuiMenuItem-root", extract_acc=False, choose_account=True
        )
        self.logger.info(f"Total bank options: {len(bankOptions)}")

        if (len(bankOptions) == 1):
            self.logger.info("No bank options available, adding one account")
            self.addSingleAccount()
            self.driver.refresh()
            bankOptions = self.select_dropdown_option(
                expand_icon_index=0, item_css_selector="li.MuiMenuItem-root", extract_acc=False, choose_account=True
            )
        else:
            available_options = bankOptions[:-1]
            if available_options:
                random_bank = random.choice(available_options)
                self.logger.info(f"Randomly selected bank: {random_bank.text}")
                random_bank.click()
            else:
                self.fail("No available bank accounts to select (excluding last option)")

    def clear_details(self, clearButton=None):
        driver = self.driver
        clear_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, clearButton)))
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", clear_button)
        time.sleep(1)
        clear_button.click()

    def extract_total_balance(self):
        driver = self.driver
        time.sleep(1)

        self.scrollToSection("wallet-balance")
        WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, "wallet-balance")))
        self.logger.info("Refreshing balance")
        balance_refresh = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "refresh-button")))
        balance_refresh.click()
        time.sleep(5)
        self.logger.info("Done refreshing balance")
        BalanceStr = self.check_balance(language=self.language, return_balance=True)
        if not BalanceStr:
            self.fail("Cannot get initial balance")
        walletBalance = float(BalanceStr.replace(',', ''))
        self.logger.info(f"Initial Balance: {walletBalance:.2f}")
        return walletBalance

    def getPromoDetails(self, promo_text, checkPromo=False, remainingPromos=None, verifyInvalidVoucher=False):
        try:
            payload = {
                "username": CREDENTIALS["duplicated_user"]["username"],
                "password": CREDENTIALS["duplicated_user"]["password"]
            }
            response = requests.post(f"{CREDENTIALS['BO_base_url']}/api/login", json=payload)
            response.raise_for_status()
            data = response.json()

            if data.get("code") != 200:
                self.fail(f"Login failed: {data.get('message')}")

            token = data["data"]["token"]
            headers = {
                "Authorization": f"Bearer {token}",
                "language": self.language
            }

            response = requests.get(f"{CREDENTIALS['BO_base_url']}/api/depositInfo", headers=headers)
            response.raise_for_status()
            promoList = response.json().get("data", {}).get("popoPromo", [])

            if verifyInvalidVoucher:
                apiPromoValues = [promo["optionCode"] for promo in promoList]
                is_not_in_list = promo_text not in apiPromoValues
                self.logger.info(f"Voucher '{promo_text}' {'is not' if is_not_in_list else 'is'} in promo list")
                return is_not_in_list, apiPromoValues

            if checkPromo:
                promoList = [promo["optionValue"] for promo in promoList]

                ui_promo_values = [promo.text for promo in remainingPromos]

                missing_in_ui = set(promoList) - set(ui_promo_values)
                extra_in_ui = set(ui_promo_values) - set(promoList)

                if missing_in_ui or extra_in_ui:
                    self.logger.warning("Promo mismatch detected!")
                    if missing_in_ui:
                        self.logger.warning(f"Promos in API but not in UI: {missing_in_ui}")
                    if extra_in_ui:
                        self.logger.warning(f"Promos in UI but not in API: {extra_in_ui}")
                    return False
                self.logger.info("All remaining promos match API response")
                return True

            for promo in promoList:
                if promo["optionValue"] == promo_text:
                    bonus = float(promo["details"]["bonus"])
                    bonus_type = promo["details"]["bonusType"]
                    maxReward = float(promo["details"]["maximumReward"])
                    minReload = float(promo["details"]["minimumReload"])
                    self.logger.info(
                        f"API Promo details - Bonus: {bonus}, Type: {bonus_type}, Max Reward: {maxReward}, Min Reload: {minReload}"
                    )
                    return bonus, bonus_type, maxReward, minReload

            self.fail(f"Promo not found in API response: {promo_text}")

        except Exception as e:
            self.fail(f"Failed to get promo details from API: {str(e)}")

    def getPromoOptions(self):
        self.open_dropdown(0)
        promoOptions = WebDriverWait(self.driver,
                                     3).until(EC.visibility_of_all_elements_located((By.ID, "promotion-item")))
        self.logger.info(len(promoOptions))
        return promoOptions

    def scrollToSection(self, field_name):
        try:
            section = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, field_name)))
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", section)
            self.logger.info(f"Scrolled to {field_name} section")
            time.sleep(1)
        except Exception as e:
            self.fail(f"Failed to scroll to {field_name} section: {str(e)}")

    def verifyBonusBalance(self, initialBalance, reloadAmount, promoText="No Promo", bonusAmount=0, Fail=False):
        #balanceSection = WebDriverWait(self.driver, 10).until(
        #    EC.presence_of_element_located((By.CSS_SELECTOR, "div.MuiBox-root p.MuiTypography-body1"))
        #)
        #self.driver.execute_script("arguments[0].scrollIntoView(true);", balanceSection)
        #time.sleep(1)
        self.logger.info(f"Bonus Amount: {bonusAmount}")

        if Fail:
            self.logger.info(f"Fail: {Fail}")
            expectedFinal = initialBalance
        else:
            self.logger.info(f"Reload amount: {reloadAmount}")
            expectedFinal = initialBalance + float(reloadAmount) + bonusAmount
        self.logger.info(f"Expected Final Balance: {expectedFinal:.2f}")

        finalBalance = self.extract_total_balance()

        try:
            self.assertEqual(
                expectedFinal, finalBalance,
                msg=f"Balance mismatch for {promoText}: Expected {expectedFinal:.2f}, got {finalBalance:.2f}"
            )
            self.logger.info(f"Balance verification successful for promo: {promoText}")
        except AssertionError as e:
            self.fail(str(e))

    def calculateBonusAmount(self, reloadAmount, bonus, bonusType, maxReward):
        if bonusType == "Percentage":
            bonusAmount = float(reloadAmount) * (bonus / 100)
            if bonusAmount > maxReward:
                self.logger.info(
                    f"Bonus amount {bonusAmount:.2f} exceeds max reward {maxReward:.2f}, using max reward instead"
                )
                bonusAmount = maxReward
        else:
            bonusAmount = bonus
        return bonusAmount

    def checkInvalidVoucher(self, invalidVoucher, submitButton=None):
        invalidVoucher = CREDENTIALS["deposit"]["invalid_voucher"]
        self.generic_apply_invalid_voucher(invalidVoucher)
        isNotInList, apiPromoValues = self.getPromoDetails(promo_text=invalidVoucher, verifyInvalidVoucher=True)

        if isNotInList:
            self.logger.info(f"Voucher '{invalidVoucher}' is not in available promos: {apiPromoValues}")

            self.generic_submit(expected_result="failure", submit=submitButton, check_general_error=True)
            if self.verifyFieldDisable("selectedPromo", check=True) and self.verifyFieldDisable("voucher", check=True):
                self.logger.info(
                    "The selectedPromo and voucher input fields are disabled after applying invalid voucher."
                )
            else:
                self.fail("The selectedPromo and voucher input fields did not disable")
        else:
            self.fail(f"Voucher '{invalidVoucher}' was found in promo list when it should be invalid")

    def check_invalid_amount(
        self, amount_field_id="reload-amount-input", submit_button_id=None, clear_button_id=None, choose_receipt=False,
        withdrawal=False, transfer=False
    ):
        driver = self.driver

        if transfer:
            amount_field_id = "amount-input"
            test_cases = [("1.234", LANGUAGE_SETTINGS[self.language]["errors"]["amount_decimal_places"], False, False),
                          ("-100", LANGUAGE_SETTINGS[self.language]["errors"]["zero_amount_invalid"], False, False),
                          ("abc", LANGUAGE_SETTINGS[self.language]["errors"]["amount_decimal_places"], False, False),
                          ("!@#", LANGUAGE_SETTINGS[self.language]["errors"]["amount_decimal_places"], False, False),
                          ("0", LANGUAGE_SETTINGS[self.language]["errors"]["zero_amount_invalid"], False, False)]

        elif withdrawal:
            test_cases = [("29", LANGUAGE_SETTINGS[self.language]["errors"]["withdraw_less_than_50"], False, False),
                          ("000", None, True, False), ("abc", None, True, False), ("!@#", None, True, False),
                          ("0", None, False, True), ("-", None, False, True)]
        else:
            test_cases = [
                ("50001", LANGUAGE_SETTINGS[self.language]["errors"]["deposit_more_than_50000"], False, False),
                ("29", LANGUAGE_SETTINGS[self.language]["errors"]["deposit_less_than_30"], False, False),
                ("000", None, True, False), ("abc", None, True, False), ("!@#", None, True, False),
                ("0", None, False, True), ("-", None, False, True)
            ]

        for amount, expected_error, zero_value, no_input in test_cases:
            try:
                if not transfer:
                    self.scrollToSection("wallet-form-amount")

                amount_field = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, amount_field_id)))
                amount_field.clear()
                amount_field.send_keys(amount)
                time.sleep(1)

                if transfer:
                    self.generic_submit(
                        expected_result="failure", check_general_error=True, id="swal2-title",
                        expected_error=expected_error, submit=submit_button_id
                    )
                    driver.refresh()
                    self.selectWalletByAmount(0, mode='highest')
                    time.sleep(1)
                    self.selectWalletByAmount(1, mode='lowest')
                else:
                    if no_input:
                        actual_value = amount_field.get_attribute("value")
                        self.assertEqual(
                            "", actual_value,
                            f"Amount input should be empty but got '{actual_value}' for input: {amount}"
                        )
                        self.logger.info(f"Successfully verified input '{amount}' results in empty field")
                        self.clear_details(clearButton=clear_button_id)
                    elif zero_value:
                        actual_value = amount_field.get_attribute("value")
                        self.assertEqual(
                            "0", actual_value,
                            f"Amount input should be '0' but got '{actual_value}' for input: {amount}"
                        )
                        self.logger.info(f"Successfully verified invalid input '{amount}' is reset to 0")
                        self.clear_details(clearButton=clear_button_id)
                    else:
                        if choose_receipt:
                            self.logger.info("Choose receipt")
                            self.choose_receipt()
                        self.generic_submit(
                            expected_result="failure", check_general_error=True, id="swal2-title",
                            expected_error=expected_error, submit=submit_button_id
                        )
                        self.clear_details(clearButton=clear_button_id)

                time.sleep(2)

            except Exception as e:
                self.fail(f"Test failed for amount '{amount}': {str(e)}")

    def paymentGateway(self):
        WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located((By.CLASS_NAME, "swal2-success-ring")))
        dummyBank = WebDriverWait(self.driver,
                                  10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#Main_Bank img")))
        dummyBank.click()
        time.sleep(2)
        username_input = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Your Username']"))
        )
        username_input.send_keys("abc")
        time.sleep(2)
        password_input = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Your Password']"))
        )
        password_input.send_keys("123")
        time.sleep(2)
        login_button = WebDriverWait(self.driver,
                                     10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.btn.btn-default")))
        login_button.click()
        time.sleep(5)
        confirm_button = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@onclick='ConfirmBankAccount()']"))
        )
        confirm_button.click()
        time.sleep(5)
        continue_button = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@onclick='ConfirmUserResponse()']"))
        )
        continue_button.click()
        time.sleep(7)

    def choose_receipt(self):
        driver = self.driver
        self.scrollToSection("wallet-form-uploadReceipt")
        time.sleep(1)
        try:
            add_photo_button = WebDriverWait(driver,
                                             10).until(EC.element_to_be_clickable((By.ID, "upload-receipt-button")))
            add_photo_button.click()
            self.upload_receipt(choose_from_gallery=True)
        except Exception as e:
            self.fail("Cannot upload receipt")

    def upload_receipt(self, choose_from_gallery=None):
        try:
            if choose_from_gallery:
                upload_success = self.upload_from_gallery(replace=False)
                self.assertTrue(upload_success, "Failed to upload image from gallery")
            else:
                upload_success = self.upload_from_camera()
                self.assertTrue(upload_success, "Failed to upload image from camera")

            image_uploaded = self.verify_uploaded_image(remove=False)
            self.assertTrue(image_uploaded, "No image was uploaded or displayed")
        except AssertionError:
            self.fail("Failed to upload receipt using choose from gallery feature.")

    def get_id_number(self):
        driver = self.driver
        try:
            id_element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "user-profile-id")))

            id_text = id_element.text
            id_number = id_text.split(":")[-1].strip()
            self.logger.info(f"Found ID number: {id_number}")
            return id_number
        except Exception as e:
            self.fail("Cannot get ID number")

    def submitReloadWithPromo(
        self, submitButtonId, chooseReceipt=False, isQuickReload=False, testMinReload=False, equalDepositLimit=False,
        greaterDepositLimit=False, lessDepositLimit=False
    ):
        driver = self.driver
        totalReloadAmount = 0
        try:
            time.sleep(2)
            self.scrollToSection("wallet-form-popoPromo")
            time.sleep(2)
            initialPromoOptions = self.getPromoOptions()
            initialPromoTexts = [promo.text for promo in initialPromoOptions]
            self.logger.info(f"Found {len(initialPromoTexts)} promo options")
            time.sleep(2)
            driver.refresh()

            for promoText in initialPromoTexts:
                initialBalance = self.extract_total_balance()

                self.scrollToSection("wallet-form-popoPromo")
                self.scrollToSection("wallet-form-amount")

                if testMinReload:
                    bonus, bonusType, maxReward, minReload = self.getPromoDetails(promoText)
                    formattedMinReload = str(int(float(minReload)))
                    self.logger.info(f"Min reload: {formattedMinReload}")

                    if float(minReload) < 30:
                        self.logger.info(f"Skipping promo with minimum reload {formattedMinReload} < 30")
                        continue
                    amountField = WebDriverWait(driver,
                                                10).until(EC.element_to_be_clickable((By.ID, "reload-amount-input")))
                    self.logger.info(promoText)
                    if equalDepositLimit:
                        reloadAmount = formattedMinReload
                    elif greaterDepositLimit:
                        reloadAmount = str(int(float(formattedMinReload)) + 1)
                    elif lessDepositLimit:
                        lessThanMin = random.randint(1, int(float(minReload)) - 1)
                        reloadAmount = str(lessThanMin)
                    amountField.send_keys(reloadAmount)
                    self.logger.info(f"Reload amount: {reloadAmount}")
                    self.logger.info(f"Testing minimum reload with amount {reloadAmount} < {formattedMinReload}")

                else:
                    reloadAmount = self.select_random_amount()
                    self.logger.info(f"Reload amount for promo: {promoText}")
                time.sleep(2)

                if chooseReceipt:
                    self.choose_receipt()
                    time.sleep(1)

                currentPromoOptions = self.getPromoOptions()
                currentNumPromos = len(currentPromoOptions)
                self.logger.info(f"Current available promos: {currentNumPromos}")

                if currentNumPromos == 0:
                    self.logger.info("No more promos available, ending test")
                    break

                promo_found = False
                for current_promo in currentPromoOptions:
                    if current_promo.text == promoText:
                        promo = current_promo
                        promo_found = True
                        break

                if not promo_found:
                    self.logger.info(f"Promo {promoText} no longer available, skipping...")
                    continue

                self.logger.info(f"Testing promo: {promoText}")

                if not testMinReload:
                    bonus, bonusType, maxReward, minReload = self.getPromoDetails(promoText)
                    formattedMinReload = f"{float(minReload):.2f}"

                bonusAmount = self.calculateBonusAmount(float(reloadAmount), bonus, bonusType, maxReward)
                self.logger.info(f"Final Bonus amount: {bonusAmount}")

                promo.click()
                time.sleep(1)

                if testMinReload and lessDepositLimit:
                    # Test error message for insufficient reload amount
                    self.generic_submit(
                        expected_result="failure", expected_error=
                        f"{LANGUAGE_SETTINGS[self.language]['errors']['insufficient_reload']} {formattedMinReload}",
                        check_general_error=True, id="swal2-title", submit=submitButtonId
                    )
                    continue

                if float(reloadAmount) < float(formattedMinReload):
                    while float(reloadAmount) < float(formattedMinReload):
                        self.logger.info(
                            f"Reload amount {reloadAmount} is less than the minimum reload amount {formattedMinReload}, trying new amount..."
                        )
                        reloadAmount = self.select_random_amount()
                        self.logger.info(f"New reload amount: {reloadAmount}")
                        time.sleep(1)

                    bonusAmount = self.calculateBonusAmount(float(reloadAmount), bonus, bonusType, maxReward)
                    self.logger.info(f"Final Bonus amount: {bonusAmount}")

                ID = self.get_id_number()
                if float(reloadAmount) < 30:
                    self.generic_submit(
                        expected_result="failure", check_general_error=True, id="swal2-title",
                        expected_error=LANGUAGE_SETTINGS[self.language]["errors"]["deposit_less_than_30"],
                        submit=submitButtonId
                    )
                    continue
                else:
                    self.generic_submit(expected_result="success", submit=submitButtonId)
                totalReloadAmount += float(reloadAmount)
                self.logger.info(f"Total reload amount: {totalReloadAmount}")

                if isQuickReload:
                    self.paymentGateway()
                    time.sleep(2)
                    self.confirm_button()
                else:
                    self.handleDeposit(ID)
                    time.sleep(2)

                self.verifyBonusBalance(initialBalance, reloadAmount, promoText=promoText, bonusAmount=bonusAmount)
                if equalDepositLimit or greaterDepositLimit:
                    break

                time.sleep(2)
            return totalReloadAmount
        except Exception as e:
            self.fail(f"Test failed: {str(e)}")

    def checkDepositLimit(self, chooseReceipt=False):
        # < deposit limit
        self.submitReloadWithPromo(
            submitButtonId="submit-button", chooseReceipt=chooseReceipt, isQuickReload=False, testMinReload=True,
            lessDepositLimit=True
        )
        self.logger.info("Finished testing < deposit limit")
        # = deposit limit
        self.submitReloadWithPromo(
            submitButtonId="submit-button", chooseReceipt=chooseReceipt, isQuickReload=False, testMinReload=True,
            equalDepositLimit=True
        )
        self.logger.info("Finished testing = deposit limit")
        # > deposit limit
        self.submitReloadWithPromo(
            submitButtonId="submit-button", chooseReceipt=chooseReceipt, isQuickReload=False, testMinReload=True,
            greaterDepositLimit=True
        )
        self.logger.info("Finished testing > deposit limit")

    """
    def clickMiniGameWidget(self, href_value):
        #id
        mini_game_container = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "div.MuiBox-root.mui-theme-164q5tj"))
        )
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", mini_game_container)
        time.sleep(1)

        mini_game_container.click()

        self.logger.info("Successfully clicked the mini game widget container")

        css_selector = f"a[href='{href_value}']"
        link_element = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, css_selector)))
        link_element.click()
    """

    def clickMiniGameWidget(self, href_value):
        #id
        mini_game_container = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "div.MuiBox-root.mui-theme-164q5tj"))
        )
        # self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", mini_game_container)
        ActionChains(self.driver).move_to_element(mini_game_container).click().perform()
        time.sleep(1)

        mini_game_container.click()

        self.logger.info("Successfully clicked the mini game widget container")

        css_selector = f"a[href='{href_value}']"
        link_element = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, css_selector)))
        link_element.click()

    def navigateHomePage(self):
        self.url = LANGUAGE_SETTINGS[self.language]["home_url"]
        self.driver.get(self.url)
        #Now close the popup
        self.annoucement_close_button()
        self.daily_checkin_close_button()

        time.sleep(2)

    def checkSpinTicket(self):
        self.navigateHomePage()
        time.sleep(2)
        self.logger.info("Checking spin ticket")
        self.clickMiniGameWidget("lucky_wheel")
        self.driver.refresh()
        time.sleep(5)
        spinTicket = self.driver.find_element(By.ID, "chance-text-wrapper")
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", spinTicket)
        time.sleep(1)
        spinTicketText = spinTicket.text
        spinTicketCount = int(''.join(filter(str.isdigit, spinTicketText)))
        self.logger.info(f"Spin ticket count: {spinTicketCount}")
        return spinTicketCount

    def checkBBPoint(self):
        driver = self.driver
        self.click_navigation_bar("footer-profile-button")
        self.driver.refresh()
        time.sleep(2)
        #id
        bb_points_element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "bb_point_value")))

        formattedBBPoints = bb_points_element.text.strip()
        initialBBPoints = int(formattedBBPoints.replace(',', ''))
        self.logger.info(f"Found BB points: {formattedBBPoints}")
        self.logger.info(f"BB Points: {formattedBBPoints}")
        return initialBBPoints

    def boboLiveLogin(self, username=None, password=None):
        try:
            time.sleep(2)
            login_button = WebDriverWait(self.driver,
                                         10).until(EC.element_to_be_clickable((By.ID, "bobolive-login-button")))
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", login_button)
            login_button.click()

            login_input = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, ":r0:")))
            login_input.send_keys(username if username else self.username)

            password_input = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, ":r1:")))
            password_input.send_keys(password if password else self.password)

            submit_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))
            )
            submit_button.click()

            time.sleep(5)
            self.driver.refresh()
            
            time.sleep(5)
        except Exception as e:
            pass

    def checkBBCoins(self):
        self.logger.info("Getting BB Coins amount")
        self.navigateHomePage()
        live_button = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.ID, "footer-live-button")))

        self.logger.info("Clicking Live button")
        live_button.click()
        time.sleep(1)

        self.boboLiveLogin()

        coin_element = WebDriverWait(self.driver, 10).until(
            EC.visibility_of_element_located(
                (By.XPATH, "//div[contains(@class, 'MuiChip-root')]//img[@alt='bbtv_coin']/following-sibling::span")
            )
        )

        coins_amount = coin_element.text.replace(",", "").strip()
        self.logger.info(f"Current BB Coins amount: {coins_amount}")

        self.assertTrue(coins_amount.isdigit(), "Coins amount is not a number")

        self.driver.back()
        time.sleep(1)
        return int(coins_amount)

    def get4DCards(self):
        self.logger.info("Getting 4D Cards amount")

        self.navigate_to_4d_tabs()
        
       # Wait for 4D Cards text element
        self.logger.info("Getting 4D Cards text")
        cards_element = WebDriverWait(self.driver,
                                      10).until(EC.visibility_of_element_located((By.ID, "totalCardNumberText")))

        # Extract number from text
        cards_text = cards_element.text
        separator = LANGUAGE_SETTINGS[self.language]["check_in"][":"]
        cards_amount = cards_text.split(f"{separator}")[1].replace(",", "").strip()  # Split "4D Cards: 2" to get number
        self.logger.info(f"Current 4D Cards amount: {cards_amount}")

        self.assertTrue(cards_amount.isdigit(), "4D Cards amount is not a number")

        return int(cards_amount)

    def getWalletBalance(self):
        self.logger.info("Getting wallet balance")

        self.driver.get(self.url)

        self.annoucement_close_button()
        self.daily_checkin_close_button()

        # Wait for wallet balance element
        balance_element = WebDriverWait(self.driver,
                                        10).until(EC.visibility_of_element_located((By.ID, "home-wallet-balance")))

        # Get balance text and remove "RM" and spaces
        balance_text = balance_element.text.replace("RM", "").replace(",", "").strip()

        try:
            # Convert to float
            balance = round(float(balance_text), 2)
            self.logger.info(f"Converted balance amount: {balance}")
            return balance

        except ValueError:
            self.logger.error(f"Failed to convert balance text to number: {balance_text}")
            raise

    def verifyReward(self, reward_type, reward_before, reward_after, expected_increase):
        self.logger.info(f"Verifying {reward_type} rewards")

        self.logger.info(f"Total expected increase: {expected_increase}")
        self.logger.info(f"Actual increase: {reward_after - reward_before}")

        # Verify reward increase matches expected amount
        self.assertEqual(
            round(float(reward_after - reward_before), 2), round(float(expected_increase), 2),
            f"{reward_type} did not increase by expected amount {expected_increase}"
        )

        self.logger.info(f"{reward_type} rewards verified successfully")

    def checkSpinTicketAndBBPoint(self, initialSpinTickets, initialBBPoints, reloadAmount, isRejectOrProcessing=False):
        initialSpinTickets = int(initialSpinTickets)
        initialBBPoints = int(initialBBPoints)

        if isRejectOrProcessing:
            expectedIncrease = 0
        else:
            expectedIncrease = int(float(reloadAmount)) // 50
        self.logger.info(f"Expected increase: {expectedIncrease}")

        finalSpinTickets = self.checkSpinTicket()

        time.sleep(2)
        finalBBPoints = self.checkBBPoint()
        self.logger.info(f"Final Spin tickets: {finalSpinTickets}")
        self.logger.info(f"Final BB Points: {finalBBPoints}")

        expectedSpinTickets = initialSpinTickets + expectedIncrease
        expectedBBPoints = initialBBPoints + expectedIncrease
        try:
            self.assertEqual(
                finalSpinTickets, expectedSpinTickets,
                f"Spin tickets did not increase correctly. Expected: {expectedSpinTickets}, Got: {finalSpinTickets}"
            )

            self.assertEqual(
                finalBBPoints, expectedBBPoints,
                f"BB points did not increase correctly. Expected: {expectedBBPoints}, Got: {finalBBPoints}"
            )
        except AssertionError as e:
            self.fail(f"Spin ticket and BB point failed to increase correctly: {str(e)}")

    def logout(self):
        self.click_navigation_bar("footer-profile-button")
        self.click_navigation_bar("settings-button")
        self.click_navigation_bar("logout-list-item")
        time.sleep(2)

    def successMessage(self, id, successMessage=None):
        try:
            successText = WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located((By.ID, id)))
            if successMessage:
                self.assertEqual(successText.text, successMessage, msg="Success message not found")
            else:
                self.logger.info(f"Success message found: {successText.text}")
            self.confirm_button()
        except Exception as e:
            self.fail(f"Success message not found: {str(e)}")

    def run(self, result=None):
        if result is None:
            result = ContinueOnFailureTestResult()
        return super().run(result)

    def checkIncompleteTurnover(self, userID, checkIncomplete=False, language=None, transfer_check=False):
        turnoverAPI = CREDENTIALS["CheckTurnover"].format(BO_base_url = CREDENTIALS["BO_base_url"], ID=userID, language=language)
        locked_by_list = []

        response = requests.get(turnoverAPI)

        if response.status_code == 200:
            self.logger.info(f"Turnover API Response: {response.json()}")
            turnoverData = response.json()
            if len(turnoverData) == 0:
                self.logger.info("No turnover data found")
                self.logger.info(f"Locked by list: {locked_by_list}")
                return False, locked_by_list
            else:
                hasIncomplete = False
                for turnover in turnoverData:
                    self.logger.info(f"Progress: {turnover['progress']}")
                    self.logger.info(f"Target: {turnover['target']}")
                    progress = float(turnover['progress'])
                    target = float(turnover['target'])
                    locked = turnover['lockedby']

                    if transfer_check:
                        if locked.startswith('Promo:'):
                            promo_code = locked.replace('Promo:', '').strip()
                            locked_by_list.append(promo_code)
                            if checkIncomplete and progress < target:
                                hasIncomplete = True
                    else:
                        locked_by_list.append(locked)
                        if checkIncomplete and progress < target:
                            hasIncomplete = True

                uniqueLockedBy = list(set(locked_by_list))
                return (hasIncomplete, uniqueLockedBy) if checkIncomplete else (False, uniqueLockedBy)
        else:
            self.logger.error(f"Failed to check turnover. Status code: {response.status_code}")
            self.fail("Check turnover failed")

    def switchAccount(self, username, password):
        self.logout()
        self.perform_login(username, password)

    def login(self, username, password):
        payload = {
            "username": username,
            "password": password
        }
        response = requests.post(f"{CREDENTIALS['BO_base_url']}/api/v2/login", json=payload)
        response.raise_for_status()
        data = response.json()

        if data.get("code") == 200:
            token = data["data"]["token"]
            self.logger.info("Login successful!")
            return token
        else:
            self.logger.error(f"Login failed: {data.get('message')}")
            return None

    def get_game_ids(self, headers):
        response = requests.get(f"{CREDENTIALS['BO_base_url']}/api/transfers", headers=headers)
        response.raise_for_status()
        result = response.json().get("data")
        result = sorted(self.parse_game_ids(result), key=lambda x: x["id"])
        return result

    def parse_game_ids(self, data):
        account_game_list = []
        for account in data.get("accountList", []):
            if account["id"] == 0 or account["id"] == -1:
                account_game_list.append({
                    "id": account["id"],
                    "name": account["label"],
                    "credit": account["credit"],
                    "has_failed_transfer": account.get("has_failed_transfer", False)
                })

            for game in account.get("games", []):
                game_entry = {
                    "id": game["id"],
                    "name": game["name"],
                    "credit": game["credit"],
                    "has_failed_transfer": game.get("has_failed_transfer", False)
                }
                account_game_list.append(game_entry)

        return account_game_list

    def navigate_to_transfer(self):
        self.navigate_to_reload_page("transfer")
        time.sleep(2)

    def generate_valid_phone(self):
        phone = "1"

        remaining_length = random.randint(8, 9)
        remaining_digits = ''.join(random.choices(string.digits, k=remaining_length))

        return f"{phone}{remaining_digits}"

    def get_vip_levels(self, language=None):
        token = self.login(self.username, self.password)
        headers = {
            "Authorization": f"Bearer {token}",
            "Language": language if language else self.language
        }
        response = requests.get(f"{API_URL}/api/uservip", headers=headers)
        response.raise_for_status()
        vip_levels = response.json().get("data")
        return vip_levels

    def performWithdrawTest(self, is_reject=False, is_processing=False):
        try:
            self.switchToCompleteTurnoverAcc()
            initialBalance = self.extract_total_balance()
            self.logger.info(f"Initial Balance: {initialBalance}")
            self.choose_random_bank_account()

            amount = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.ID, "reload-amount-input")))
            self.driver.execute_script("arguments[0].scrollIntoView(true);", amount)
            time.sleep(1)
            cleanAmount = self.getWithdrawableAmount()

            maxAmount = int(float(cleanAmount))
            minAmount = 50

            if maxAmount <= minAmount:
                self.fail(f"Insufficient balance for withdrawal (minimum: {minAmount})")

            withdrawBalance = random.randint(minAmount, maxAmount - 1)
            self.logger.info(f"Attempting to enter amount: {withdrawBalance}")

            amount.clear()
            amount.send_keys(str(withdrawBalance))
            self.logger.info(f"Entered value: {amount.get_attribute('value')}")
            time.sleep(2)

            self.generic_submit(expected_result="success", submit="submit-withdraw-button")

            ID = self.get_id_number()
            self.handleWithdrawRequest(ID, isReject=is_reject, isProcessing=is_processing)
            time.sleep(2)

            finalBalance = self.extract_total_balance()
            if is_reject:
                expectedBalance = initialBalance
            else:
                expectedBalance = initialBalance - withdrawBalance
            self.assertEqual(finalBalance, expectedBalance, msg="Balance mismatch")

        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed: {str(e)}")

    def get_turnover_ids(self, userID, language=None):
        try:
            turnoverAPI = CREDENTIALS["CheckTurnover"].format(BO_base_url = CREDENTIALS["BO_base_url"], ID=userID, language=language)
            turnover_ids = []

            response = requests.get(turnoverAPI)
            if response.status_code == 200:
                turnoverData = response.json()
                self.logger.info(f"Turnover data: {turnoverData}")

                for item in turnoverData:
                    if 'id' in item:
                        turnover_ids.append(item['id'])

                self.logger.info(f"Found turnover IDs: {turnover_ids}")
                return turnover_ids
            else:
                self.logger.error(f"Failed to get turnover data. Status code: {response.status_code}")
                return []

        except Exception as e:
            self.logger.error(f"Error getting turnover IDs: {str(e)}")
            return []

    def modify_turnover_status(self, userID, turnoverIDs, action_type="unlock", partial=False):

        try:
            turnover_actions = {
                "success": 1,
                "in_progress": 0,
                "unlock": -1
            }

            action = turnover_actions.get(action_type)
            if action is None:
                self.logger.error(f"Invalid action type: {action_type}")
                return False

            if partial and len(turnoverIDs) > 1:
                num_to_complete = random.randint(1, len(turnoverIDs) - 1)
                selected_ids = random.sample(turnoverIDs, num_to_complete)
                self.logger.info(f"Partially completing {num_to_complete} out of {len(turnoverIDs)} turnovers")
            else:
                selected_ids = turnoverIDs

            for turnover_id in selected_ids:
                modify_url = CREDENTIALS["ModifyTurnover"].format(BO_base_url = CREDENTIALS["BO_base_url"], userID=userID, turnover_id=turnover_id, action=action)
                self.logger.info(f"Attempting to {action_type} turnover ID: {turnover_id}")

                response = requests.get(modify_url)
                if response.status_code == 200:
                    self.logger.info(f"Successfully {action_type} turnover ID: {turnover_id}")
                else:
                    self.logger.error(
                        f"Failed to {action_type} turnover ID {turnover_id}. Status code: {response.status_code}"
                    )
                    return False

            return True

        except Exception as e:
            self.logger.error(f"Error modifying turnover: {str(e)}")
            return False

    def get_user_vip_id(self):
        token = self.login(self.username, self.password)
        headers = {
            "Authorization": f"Bearer {token}",
        }
        response = requests.get(f"{API_URL}/api/user", headers=headers)
        response.raise_for_status()
        vip_id = response.json().get("data")["vip"]
        return vip_id

    def get_user_id(self):
        token = self.login(self.username, self.password)
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        response = requests.get(f"{CREDENTIALS['BO_base_url']}/api/user", headers=headers)
        return response.json().get("data")["id"]

    def get_user_vip_id(self):
        token = self.login(self.username, self.password)
        headers = {
            "Authorization": f"Bearer {token}",
        }
        response = requests.get(f"{API_URL}/api/user", headers=headers)
        response.raise_for_status()
        vip_id = response.json().get("data")["vip"]
        return vip_id

    def get_user_info(self, info_name, language=None):
        token = self.login(self.username, self.password)
        headers = {
            "Authorization": f"Bearer {token}",
            "Language": language if language else self.language
        }
        response = requests.get(f"{API_URL}/api/user", headers=headers)
        response.raise_for_status()
        user_info = response.json().get("data")
        return user_info.get(info_name)
    
    def navigate_to_4d_tabs(self):
        self.logger.info("Navigating to 4D tabs")

        # Wait for 4D tab button to be visible
        tab_button = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//button[@role='tab'][contains(., '4D')]"))
        )

        # Scroll to element and click
        self.logger.info("Scrolling to 4D tab")
        self.driver.execute_script("arguments[0].scrollIntoView(true);", tab_button)
        time.sleep(1)

        self.logger.info("Clicking 4D tab")
        self.driver.execute_script("arguments[0].click();", tab_button)
        time.sleep(3)
    
    def bobolive_topup_diamond(self):
        self.logger.info("Topping up diamond")
        self.navigate_to_live_page()
        topup_button = self.driver.find_element(By.ID, "bobolive-topup-button")
        topup_button.click()
        time.sleep(3)
        amount_element = self.driver.find_element(By.ID, "amount")
        amount_element.click()
        amount_element.send_keys("30")
        time.sleep(2)
        self.driver.find_element(By.ID, "bobolive-topup-submit-button").click()
        time.sleep(5)
        self.paymentGateway()
        time.sleep(2)
        self.success_icon()
        self.confirm_button()
        time.sleep(2)
    
    def add_4d_cards_api(self, userID, amount):
        token = self.login(self.username, self.password)
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
        }
        data = {
            "user_id": str(userID),
            "amount": str(amount),
            "pass": "123456",
        }
        response = requests.post(f"{CREDENTIALS['Add4dCards'].format(BO_base_url = CREDENTIALS["BO_base_url"])}", headers=headers, json=data)
        response.raise_for_status()
    
    def get_4d_history_api(self, four_d_number="", start_date="", end_date="", is_won="", page="", per_page=""):
        token = self.login(self.username, self.password)
        headers = {
            "Authorization": f"Bearer {token}",
        }
        data = {
            "four_d_number": four_d_number,
            "start_date": start_date,
            "end_date": end_date,
            "is_won": is_won,
            "page": page,
            "per_page": per_page,
        }
        response = requests.post(f"{CREDENTIALS['Get4dHistory'].format(BO_base_url = CREDENTIALS["BO_base_url"])}", headers=headers, json=data)
        response.raise_for_status()
        return response.json().get("data")
    
    def bet_4d_api(self, four_d_number, date_time_str, bet_platforms, source, type, coupon_id, B="0", S="0", SA="0", SB="0", SC="0", SD="0", SE="0"):
        try:
            # Extract date_only from date_time_str (assuming UTC format like "2025-03-18T02:48:02.715Z")
            date_only = date_time_str.split('T')[0] if 'T' in date_time_str else date_time_str
            
            # Get authentication token
            token = self.login(self.username, self.password)
            
            url = CREDENTIALS['Bet4d'].format(BO_base_url = CREDENTIALS["BO_base_url"])

            user_id = self.get_user_id()
            payload = {'pass': '123456',
            'user_id': user_id,
            'bet_number': four_d_number,
            'bet_number_list': four_d_number,
            'bet_dates': date_only,
            'bet_platforms': bet_platforms,
            'source': source,
            'B': B,
            'S': S,
            'SA': SA,
            'SB': SB,
            'SC': SC,
            'SD': SD,
            'SE': SE,
            'type': type,
            'coupon_id': coupon_id,
            'user_bet_time': date_time_str,
            'show_id': "-1",
            'user_bet_date': date_only}
            files=[

            ]
            headers = {
            'Accept': 'application/json',
            'Authorization': f"Bearer {token}"
            }
            
            self.logger.info(f"Payload: {payload}")
            

            response = requests.request("POST", url, headers=headers, data=payload, files=files)

            self.logger.info(response.text)
        
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API request failed: {str(e)}")
        except Exception as e:
            self.logger.error(f"An error occurred: {str(e)}")
        
    def update_bet_result(self, bet_record_id, action, amount):
        token = self.login(self.username, self.password)
        
        payload = {'pass': '123456',
        'betRecordId': bet_record_id,
        'action': action,
        'amount': amount,
        'username': self.username}
        
        files=[

        ]
        headers = {
        'Accept': 'application/json',
        'Authorization': f"Bearer {token}"
        }

        response = requests.request("POST", CREDENTIALS['UpdateBetResult'].format(BO_base_url = CREDENTIALS["BO_base_url"]), headers=headers, data=payload, files=files)
        response.raise_for_status()