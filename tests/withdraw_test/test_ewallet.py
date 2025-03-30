import unittest
import time
import logging
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from config.constant import LANGUAGE_SETTINGS, CREDENTIALS
from tests.authentication_test.base_test import BaseTest

# Wallet Number -> can type negative number
#empty field
#clear
#submit


class TestEWalletPage(BaseTest):

    def __init__(self, methodName="runTest", language=None, browser=None):
        super().__init__(methodName)
        self.language = language
        self.browser = browser
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

        file_handler = logging.FileHandler("test_withdraw_output.log")
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
        # size of iphone X, as desktop UI is not ready
        self.driver.set_window_size(375, 812)
        #self.driver.maximize_window()
        self.navigate_to_login_page()
        self.perform_login(CREDENTIALS["duplicated_user"]["username"], CREDENTIALS["duplicated_user"]["password"])
        self.navigate_to_ewallet()

    def tearDown(self):
        if hasattr(self, "driver"):
            self.driver.quit()

    def navigate_to_ewallet(self):

        ewallet_tabs = self.navigate_to_reload_page("withdraw", True)

        ewallet = ewallet_tabs[0]

        ewallet.click()
        time.sleep(2)

    def enter_wallet_number(self, number):
        driver = self.driver
        ewallet_field = WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.NAME, "walletNumber")))
        ewallet_field.send_keys(number)

    def test_01_CheckTotalAmount(self):
        try:
            games_amount = self.check_games_balance()
            self.logger.info(games_amount)
            self.url = LANGUAGE_SETTINGS[self.language]["home_url"]
            self.driver.get(self.url)
            self.navigate_to_ewallet()
            self.check_total_amount(self.language, games_amount)
        except Exception as e:
            self.fail(f"Test failed: {str(e)}")

    """
    def test_02_CheckNonWithdrawable(self):
        try:
            self.check_non_withdrawable()
        except Exception as e:
            self.fail(f"Test failed: {str(e)}")

    """

    def test_03_EmptyField(self):
        driver = self.driver
        #empty e-wallet
        self.enter_wallet_number("0123456789")
        self.select_random_amount(quick_scan=False)
        self.generic_submit(expected_result="failure", check_amount=False)

        #empty wallet number
        self.select_random_options(0)
        self.select_random_amount(quick_scan=False)
        self.generic_submit(expected_result="failure", check_amount=False)

        #empty amount
        self.select_random_options(0)
        self.enter_wallet_number("0123456789")
        amount_field = WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.NAME, "amount")))
        self.generic_submit(field=amount_field, expected_result="failure", check_amount=False)

    def test_04_ChooseEWallet(self):
        driver = self.driver
        try:
            self.select_dropdown_option(
                expand_icon_index=0, item_css_selector="li.MuiMenuItem-root", selected_index=0,
                bank_transfer_reload=False, extract_text=False, language=self.language, scan_reload=False,
                choose_bank=True
            )
        except Exception as e:
            self.fail(f"Test failed: {str(e)}")

    #check invalid (alphebat,<?)
    def test_05_ValidWalletNumber(self):
        driver = self.driver
        try:
            self.select_random_options(0)
            self.enter_wallet_number("0123456789")
            self.select_random_amount(quick_scan=False)
            self.submit_and_verify_submit(withdraw=True)

        except Exception as e:
            self.fail(f"Test failed: {str(e)}")

    def test_06_InValidWalletNumber(self):
        driver = self.driver
        try:
            initial_balance = self.extract_total_balance()

            self.select_random_options(0)
            self.enter_wallet_number("abc")
            self.select_random_amount(quick_scan=False)
            self.generic_submit(expected_result="failure", check_ewallet_number=True)

            final_balance = self.extract_total_balance()
            try:
                self.assertEqual(
                    initial_balance, final_balance,
                    msg=f"Balance mismatch: Can be withdraw by using invalid wallet number"
                )
            except AssertionError:
                self.fail("Balance mismatch")

        except Exception as e:
            self.fail(f"Test failed: {str(e)}")

    """
    def test_07_ChooseAmount(self):
        driver = self.driver
        try:
            amount_section = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.CLASS_NAME, "MuiGrid-root.MuiGrid-container.MuiGrid-spacing-xs-1.mui-theme-tuxzvu")
                )
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", amount_section)
            self.choose_amount(0)
        except Exception as e:
            self.fail(f"Test failed: {str(e)}")

    """

    def test_08_InvalidAmount(self):
        driver = self.driver

        try:
            initial_balance = self.extract_total_balance()
            self.select_random_options(0)
            self.enter_wallet_number("0123456789")
            self.enter_invalid_amount()
            self.generic_submit(expected_result="failure", check_amount=True)
            final_balance = self.extract_total_balance()
            try:
                self.assertEqual(
                    initial_balance, final_balance,
                    msg=f"Balance mismatch: Can be withdraw by using invalid wallet number"
                )
            except AssertionError:
                self.fail("Balance mismatch")
        except Exception as e:
            self.fail(f"Test failed: {str(e)}")

    def test_09_ClearButton(self):
        initial_button_texts = [self.get_all_button_texts()[0]]
        self.select_random_options(0)
        self.enter_wallet_number("0123456789")
        self.select_random_amount(quick_scan=False)

        texts = ["Bersihkan Pilihan", "清除选项", "Clear Selection"]
        self.click_submit_button(texts)
        time.sleep(2)
        #check wallet number
        self.verify_clear_functionality(initial_button_texts, [0])

    def test_10_SubmitWithdraw(self):
        self.select_random_options(0)
        self.enter_wallet_number("0123456789")
        self.select_random_amount(quick_scan=False)
        self.submit_and_verify_submit(withdraw=True)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    unittest.main()
