import unittest
import time
import logging
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, UnexpectedAlertPresentException
from config.constant import LANGUAGE_SETTINGS, CREDENTIALS
from tests.authentication_test.base_test import BaseTest, ContinueOnFailureTestResult
from selenium.webdriver.common.action_chains import ActionChains

# check <30 / alphebat ## if no success (amount<30)
# check bonus and maximum reward
# check validation of promo ( check date )
# clear button cannot clear the amount
## verify success , the success message and payment gateway
# 优惠卷 / 优惠码 text validation

# after submit, no clear field
# ask back end set the minimum amount to RM 30 not RM100

# after use the voucher and check will not appear under the promo voucher dropdown list
# document the promo voucher dropdownlist should list out not available when there is no other voucher claimed
# empty promo code cannot click the apply button

#test_04_InvalidAmount


class TestQuickReload(BaseTest):

    def __init__(self, methodName="runTest", language=None, browser=None):
        super().__init__(methodName, language, browser)

    def setUp(self):
        super().setUp()
        self.navigate_to_login_page()
        self.perform_login(CREDENTIALS["duplicated_user"]["username"], CREDENTIALS["duplicated_user"]["password"])

    def tearDown(self):
        if hasattr(self, "driver"):
            self.driver.quit()

    def navigate_to_quickreload(self):

        self.navigate_to_reload_page("deposit")

        bank_transfer = WebDriverWait(self.driver,
                                      10).until(EC.element_to_be_clickable((By.ID, "wallet-tab-quick_reload")))

        bank_transfer.click()
        time.sleep(2)

    def get_all_button_texts(self):

        driver = self.driver

        buttons = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "button.MuiButton-outlinedPrimary"))
        )

        button_texts = []

        for button in buttons:
            try:
                button_text = button.find_element(By.CSS_SELECTOR, "p.MuiTypography-root").text.strip()
                button_texts.append(button_text)
            except Exception as e:
                self.logger.error(f"Failed to get text from button: {str(e)}")

        return button_texts

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

    def cancelPaymentGateway(self):
        WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located((By.CLASS_NAME, "swal2-success-ring")))
        time.sleep(2)
        cancel_button = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//a[@onclick='CancelDeposit();']"))
        )
        cancel_button.click()
        time.sleep(2)

    """
    def test_01_EmptyFields(self):
        self.logger.info("Starting test_01_EmptyFields...")
        try:
            #self.click_navigation_bar("footer-wallet-button")
            #time.sleep(2)
            #self.click_navigation_bar("quick-reload-button")
            #time.sleep(2)

            self.generic_submit(expected_result="failure", submit="submit-button")
            self.error_box(LANGUAGE_SETTINGS[self.language]["errors"]["field_missing"])

        except Exception as e:
            self.logger.error(f"Test failed: {str(e)}")
            self.fail(f"Test failed: {str(e)}")


    def test_02_SubmitReloadWithPromo(self):
        self.logger.info("Starting test_02_SubmitReloadWithPromo...")
        try:
            self.click_navigation_bar("footer-wallet-button")
            time.sleep(2)
            self.click_navigation_bar("quick-reload-button")
            time.sleep(2)

            initialSpinTickets = self.checkSpinTicket()
            initialBBPoints = self.checkBBPoint()

            totalReloadAmount = self.submitReloadWithPromo(
                submitButtonId="submit-button", chooseReceipt=True, isQuickReload=True
            )

            self.checkSpinTicketAndBBPoint(initialSpinTickets, initialBBPoints, reloadAmount=totalReloadAmount)

        except Exception as e:
            self.logger.error(f"Test failed: {str(e)}")
            self.fail(f"Test failed: {str(e)}")

    def test_03_ClearButton(self):
        self.logger.info("Starting test_03_ClearButton...")
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
            self.logger.error(f"Test failed: {str(e)}")
            self.fail(f"Test failed: {str(e)}")

    def test_08_InvalidAmount(self):
        driver = self.driver
        self.navigate_to_quickreload()
        test_cases = [("29", LANGUAGE_SETTINGS[self.language]["errors"]["deposit_less_than_30"], False, False),
                      ("000", LANGUAGE_SETTINGS[self.language]["errors"]["deposit_less_than_30"], False, False),
                      ("50001", LANGUAGE_SETTINGS[self.language]["errors"]["deposit_more_than_50000"], False, False),
                      ("abc", None, True, False), ("!@#", None, True, False), ("0", None, False, True),
                      ("-", None, False, True)]

        for amount, expected_error, zeroValue, noInput in test_cases:
            try:
                self.scrollToSection("amount")
                amountField = WebDriverWait(driver,
                                            10).until(EC.element_to_be_clickable((By.ID, "reload-amount-input")))
                amountField.clear()
                amountField.send_keys(amount)
                time.sleep(1)

                if noInput:
                    actualValue = amountField.get_attribute("value")
                    self.assertEqual(
                        "", actualValue, f"Amount input should be empty but got '{actualValue}' for input: {amount}"
                    )
                    self.logger.info(f"Successfully verified input '{amount}' results in empty field")
                    self.clear_details(clearButton="clear-text")
                elif zeroValue:
                    actualValue = amountField.get_attribute("value")
                    self.assertEqual(
                        "0", actualValue, f"Amount input should be '0' but got '{actualValue}' for input: {amount}"
                    )
                    self.logger.info(f"Successfully verified invalid input '{amount}' is reset to 0")
                    self.clear_details(clearButton="clear-button")
                else:
                    self.generic_submit(
                        expected_result="failure", check_general_error=True, id="swal2-title",
                        expected_error=expected_error, submit="submit-reload-button"
                    )
                    self.clear_details(clearButton="clear-text")

                time.sleep(2)

            except Exception as e:
                self.fail(f"Test failed for amount '{amount}': {str(e)}")

    def test_05_ChoosePromo(self):
        driver = self.driver
        try:
            self.navigate_to_quickreload()
            self.scrollToSection("selectedPromo")
            self.select_dropdown_option(
                expand_icon_index=0, item_css_selector="li.MuiMenuItem-root", extract_acc=False, usage_details=True,
                history=False, reload=True
            )
            if self.verifyFieldDisable("voucher", check=True):
                self.logger.info("The voucher input field is disabled after selecting the promo.")
            else:
                self.fail("The voucher input field does not disable")

        except Exception as e:
            self.fail(f"Test failed: {str(e)}")

    """

    def test_06_EmptyFields(self):
        driver = self.driver
        self.navigate_to_quickreload()

        # empty amount
        amount_field = WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.ID, "reload-amount-input")))
        self.generic_submit(
            field=amount_field, expected_result="failure", check_general_error=False, submit="submit-reload-button"
        )

    """
    def test_07_ClearButton(self):
        driver = self.driver
        self.navigate_to_quickreload()
        try:
            initial_button_texts = [self.get_all_button_texts()[0], self.get_all_button_texts()[1]]

            self.select_random_amount()
            self.select_random_promo(0)

            self.enter_voucher("testing")
            time.sleep(1)

            self.clear_details()
            time.sleep(2)
            self.verify_clear_functionality(initial_button_texts, [0, 1], check_image_removal=True)
        except Exception as e:
            self.fail(f"Test failed: {str(e)}")

    def test_08_SubmitWithInvalidVoucher(self):
        try:
            self.navigate_to_quickreload()
            self.select_random_amount()
            invalidVoucher = CREDENTIALS["deposit"]["invalid_voucher"]
            self.checkInvalidVoucher(invalidVoucher, submitButton="submit-reload-button")

        except Exception as e:
            self.fail(f"Test failed: {str(e)}")

    def test_09_SubmitReloadWithoutPromo(self):
        try:
            self.navigate_to_quickreload()
            initialBalance = self.extract_total_balance()

            reload_amount = self.select_random_amount()
            self.logger.info(reload_amount)
            time.sleep(1)

            self.generic_submit(expected_result="success", submit="submit-reload-button")
            self.paymentGateway()
            time.sleep(2)
            self.confirm_button()
            self.verifyBonusBalance(initialBalance=initialBalance, reloadAmount=reload_amount)

        except Exception as e:
            self.fail(f"Test failed: {str(e)}")

    def test_10_CancelPaymentGateway(self):
        driver = self.driver
        try:
            self.navigate_to_quickreload()
            initialBalance = self.extract_total_balance()

            reload_amount = self.select_random_amount()
            self.logger.info(reload_amount)
            time.sleep(1)

            self.generic_submit(expected_result="success", submit="submit-reload-button")
            self.cancelPaymentGateway()
            time.sleep(2)
            self.check_general_error(
                LANGUAGE_SETTINGS[self.language]["errors"]["cancelPaymentGateway"], id="swal2-title"
            )
            self.verifyBonusBalance(initialBalance=initialBalance, reloadAmount=reload_amount, Fail=True)

        except Exception as e:
            self.fail(f"Test failed: {str(e)}")

    def test_10_SubmitReloadWithPromo(self):
        driver = self.driver
        try:
            self.navigate_to_quickreload()

            self.scrollToSection("selectedPromo")
            initialPromoOptions = self.getPromoOptions()
            numPromos = len(initialPromoOptions)
            self.logger.info(f"Found {numPromos} promo options")
            time.sleep(2)
            driver.refresh()

            for index in range(numPromos):
                initialBalance = self.extract_total_balance()

                self.scrollToSection("selectedPromo")
                self.scrollToSection("amount")

                reloadAmount = self.select_random_amount()
                self.logger.info(f"Reload amount for iteration {index + 1}: {reloadAmount}")
                time.sleep(2)

                currentPromoOptions = self.getPromoOptions()
                currentNumPromos = len(currentPromoOptions)
                self.logger.info(f"Current available promos: {currentNumPromos}")

                if currentNumPromos == 0:
                    self.logger.info("No more promos available, ending test")
                    break

                promo = currentPromoOptions[0]
                promoText = promo.text
                self.logger.info(f"Testing promo: {promoText}")

                bonus, bonus_type, maxReward, minReload = self.getPromoDetails(promoText)
                bonusAmount = self.calculateBonusAmount(reloadAmount, bonus, bonus_type, maxReward)
                self.logger.info(f"Final Bonus amount: {bonusAmount}")

                promo.click()
                time.sleep(1)
                formattedMinReload = f"{float(minReload):.2f}"
                if float(reloadAmount) < float(formattedMinReload):
                    self.logger.info(
                        f"Reload amount {reloadAmount} is less than the minimum reload amount {formattedMinReload} for this promo, skipping..."
                    )
                    self.generic_submit(
                        expected_result="failure", expected_error=
                        f"{LANGUAGE_SETTINGS[self.language]['errors']['insufficient_reload']} {formattedMinReload}",
                        check_general_error=True, id="swal2-title", submit="submit-reload-button"
                    )
                    continue
                self.generic_submit(expected_result="success", submit="submit-reload-button")
                self.paymentGateway()
                time.sleep(2)
                self.confirm_button()
                self.verifyBonusBalance(initialBalance, reloadAmount, promoText=promoText, bonusAmount=bonusAmount)
                time.sleep(2)

                driver.refresh()
                remainingPromos = self.getPromoOptions()
                self.logger.info(f"Remaining promos after iteration {index + 1}: {len(remainingPromos)}")
                self.getPromoDetails(promoText, checkPromo=True, remainingPromos=remainingPromos)
                driver.refresh()

        except Exception as e:
            self.fail(f"Test failed: {str(e)}")

    """


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestQuickReload)
    runner = unittest.TextTestRunner(resultclass=ContinueOnFailureTestResult)
    runner.run(suite)
