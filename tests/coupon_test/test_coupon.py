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

# check the expired date
# check expired coupon cannot click (check date) (expired / used)
# check line 81


class TestCouponPage(BaseTest):

    def __init__(self, methodName="runTest", language=None, browser=None):
        super().__init__(methodName)
        self.language = language
        self.browser = browser
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

        file_handler = logging.FileHandler("test_coupon_output.log")
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
        self.perform_login(CREDENTIALS["valid_user"]["username"], CREDENTIALS["valid_user"]["password"])
        self.navigate_to_coupon()

    def tearDown(self):
        if hasattr(self, "driver"):
            self.driver.quit()

    def navigate_to_coupon(self):
        driver = self.driver
        section_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'a[href="wallet/voucher"]'))
        )
        section_button.click()
        time.sleep(2)
        promo_voucher_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "div.MuiBox-root.mui-theme-69i1ev p.MuiTypography-root.MuiTypography-body1")
            )
        )
        promo_voucher_text = promo_voucher_element.text
        voucher_page_text = ["Promo Voucher", "优惠卷", "Wang Kupon Promo"]
        self.logger.info(f"Promo Voucher text: {promo_voucher_text}")
        self.assertIn(
            promo_voucher_text, voucher_page_text,
            f"Promo Voucher text '{promo_voucher_text}' is not in the expected list."
        )

    def verify_voucher_result(self, menu_item_text):
        driver = self.driver

        if menu_item_text not in ["全部", "Semua", "All"]:
            time.sleep(2)
            try:
                voucher_elements = WebDriverWait(driver, 20).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.MuiBox-root.mui-theme-1ykux15"))
                )
                self.logger.info(len(voucher_elements))
                if (len(voucher_elements) > 0):
                    for index in range(len(voucher_elements)):
                        time.sleep(2)
                        voucher_elements = WebDriverWait(driver, 10).until(
                            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.MuiBox-root.mui-theme-1ykux15"))
                        )
                        voucher = voucher_elements[index]
                        text_element = voucher.find_element(By.XPATH, "//div[@class='MuiBox-root mui-theme-0']/p[2]")

                        text_content = text_element.text
                        self.logger.info(text_content)
                        try:
                            self.assertIn(menu_item_text, text_content, "Incorrect filterd result")
                        except:
                            self.fail("Incorrect result is displayed.")
                else:
                    self.logger.info("No related result")
            except:
                self.logger.info("No result")
        else:
            self.logger.info("All is selected")

    """
    def test_01_ClaimVoucher(self):
        driver = self.driver
        try:
            voucher_divs = driver.find_elements(
                By.CSS_SELECTOR, "div.MuiGrid-root.MuiGrid-item.MuiGrid-grid-xs-12.MuiGrid-grid-md-6.mui-theme-iol86l"
            )
            self.logger.info(f"Found {len(voucher_divs)} voucher divs.")

            if voucher_divs:
                random_index = random.randint(0, len(voucher_divs) - 1)
                selected_div = voucher_divs[random_index]

                #change the coding style
                if self.language == "en" or self.language == "bm":
                    voucher_code_element = selected_div.find_element(
                        By.CSS_SELECTOR, 'p.MuiTypography-root.MuiTypography-body1.mui-theme-1vx0imh'
                    )
                elif self.language == "cn":
                    voucher_code_element = selected_div.find_element(
                        By.CSS_SELECTOR, 'p.MuiTypography-root.MuiTypography-body1.mui-theme-1kzflv9'
                    )

                voucher_code = voucher_code_element.text.split('\n')[-1].strip()
                self.logger.info(f"Randomly selected voucher code: {voucher_code}")

                button = selected_div.find_element(By.CSS_SELECTOR, 'button.MuiButtonBase-root.MuiButton-root')
                button_text_before_click = button.text
                self.logger.info(f"Button text after clicking: {button_text_before_click}")

                button.click()
                time.sleep(1)

                try:
                    button_text_after_click = button.text
                    self.logger.info(f"Button text after clicking: {button_text_after_click}")
                    deposit_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, 'a[href="deposit"]'))
                    )
                    deposit_button.click()
                    self.choose_promo_code(
                        driver, 2, self.language, deposit_banktransfer=False, voucher_code=voucher_code
                    )
                    time.sleep(2)

                except Exception as e:
                    self.fail(f"Cannot use the voucher: {e}")
            else:
                self.fail("No vouchers found.")

        except Exception as e:
            self.fail(f"Test failed: {e}")

    """

    def test_02_FilterVoucher(self):
        driver = self.driver

        try:
            self.open_dropdown(0)
            time.sleep(1)

            menu_items = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.XPATH, "//a[@role='menuitem']"))
            )

            self.logger.info(f"Total menu items found: {len(menu_items)}")

            for index in range(len(menu_items)):
                menu_items = driver.find_elements(By.XPATH, "//a[@role='menuitem']")
                menu_item = menu_items[index]
                menu_item_text = menu_item.text.strip()
                self.logger.info(f"Menu item {index + 1}: {menu_item_text}")

                WebDriverWait(driver, 10).until(EC.element_to_be_clickable(menu_item))
                menu_item.click()

                time.sleep(1)

                button = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "div.MuiBox-root.mui-theme-ohbggj button.MuiButton-outlinedPrimary")
                    )
                )
                button_text = button.text.strip()
                self.logger.info(button_text)
                #try:
                #   self.assertEqual(button_text, menu_item_text, "Not equal content")
                #except AssertionError as e:
                #    self.fail(f"Not Equal Content")
                self.verify_voucher_result(menu_item_text)

                self.open_dropdown(0)
                time.sleep(1)
        except Exception as e:
            self.fail(f"Test failed: {e}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    unittest.main()
