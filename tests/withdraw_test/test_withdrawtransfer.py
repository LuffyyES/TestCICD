import unittest
import time
import logging
import requests
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from config.constant import LANGUAGE_SETTINGS, CREDENTIALS
from tests.authentication_test.base_test import BaseTest

# 0 will also added the account !
# the insufficient balance
# withdrawable calculation (withdrawable amount + non-withdrawal amount)


class TestWithdrawTransfer(BaseTest):

    def __init__(self, methodName="runTest", language=None, browser=None):
        super().__init__(methodName, language, browser)

    def setUp(self):
        super().setUp()
        self.navigate_to_login_page()
        self.perform_login(CREDENTIALS["duplicated_user"]["username"], CREDENTIALS["duplicated_user"]["password"])
        self.navigate_to_bank_transfer()

    def tearDown(self):
        if hasattr(self, "driver"):
            self.driver.quit()

    def navigate_to_bank_transfer(self):
        self.navigate_to_reload_page("withdraw")
        bank_transfer = WebDriverWait(self.driver,
                                      10).until(EC.element_to_be_clickable((By.ID, "wallet-tab-bank_transfer")))
        bank_transfer.click()
        time.sleep(2)

    def handleWithdrawRequest(self, ID, isReject=False, isProcessing=False):
        if isReject:
            url = CREDENTIALS["RejectWithdrawRequest"].format(BO_base_url = CREDENTIALS["BO_base_url"], ID=ID)
        elif isProcessing:
            url = CREDENTIALS["ProcessingWithdrawRequest"].format(BO_base_url = CREDENTIALS["BO_base_url"], ID=ID)
        else:
            url = CREDENTIALS["ApproveWithdrawRequest"].format(BO_base_url = CREDENTIALS["BO_base_url"], ID=ID)

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

    def switchToCompleteTurnoverAcc(self):
        self.logout()
        self.perform_login(CREDENTIALS["complete_turnover"]["username"], CREDENTIALS["complete_turnover"]["password"])
        self.navigate_to_bank_transfer()

    def getWithdrawableAmount(self):

        #waitid
        withdrawable_text = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located(
                (By.XPATH, "//div[contains(@class, 'MuiBox-root')]//p[contains(@class, 'MuiTypography-body1')][2]")
            )
        ).text.strip()
        self.logger.info(f"Found withdrawable amount element: {withdrawable_text}")

        time.sleep(2)

        if not withdrawable_text:
            self.fail("Withdrawable amount text is empty")

        self.logger.info(f"Raw withdrawable amount text: {withdrawable_text}")
        cleanAmount = withdrawable_text.replace("RM ", "").strip()
        cleanAmount = cleanAmount.replace(",", "")
        self.logger.info(f"Cleaned amount: {cleanAmount}")

        if cleanAmount:
            return cleanAmount
        else:
            self.fail("Could not extract amount from withdrawable text")

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

    """
    def test_01_ChooseBankAccount(self):
        try:
            if (
                len(
                    self.select_dropdown_option(
                        expand_icon_index=0, item_css_selector="li.MuiMenuItem-root", choose_account=True
                    )
                ) > 1
            ):
                self.logger.info("Found account")
                self.driver.refresh()
                self.select_dropdown_option(
                    expand_icon_index=0, item_css_selector="li.MuiMenuItem-root", extract_acc=True
                )
            else:
                self.genericAddAccount(checkMaxAccounts=True)
        except Exception as e:
            self.fail(f"Test failed: {str(e)}")

    def test_02_ChooseAmount(self):
        try:
            amountSection = WebDriverWait(self.driver,
                                          10).until(EC.presence_of_element_located((By.ID, 'amount-toggle-group')))
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", amountSection)
            time.sleep(1)
            self.choose_amount(0)
        except Exception as e:
            self.fail(f"Test failed: {str(e)}")

    def test_03_EmptyFields(self):
        try:
            # Test with all fields empty
            self.generic_submit(
                expected_result="failure", check_general_error=True, id="swal2-html-container",
                expected_error=LANGUAGE_SETTINGS[self.language]["errors"]["empty_fields"],
                submit="submit-withdraw-button"
            )

            # Test with empty bank account
            self.select_random_amount()
            amount_field = WebDriverWait(self.driver,
                                         20).until(EC.visibility_of_element_located((By.ID, "reload-amount-input")))
            self.generic_submit(
                expected_result="failure", check_general_error=True, id="swal2-html-container",
                expected_error=LANGUAGE_SETTINGS[self.language]["errors"]["empty_fields"],
                submit="submit-withdraw-button"
            )
            self.clear_details(clearButton="clear-text")

            # Test with empty amount
            self.choose_random_bank_account()
            self.generic_submit(field=amount_field, expected_result="failure", submit="submit-withdraw-button")
        except Exception as e:
            self.fail(f"Test failed: {str(e)}")

    def test_04_AddBankAccount(self):
        try:
            self.genericAddAccount()
        except Exception as e:
            self.fail(f"Test failed: {str(e)}")

    def test_05_AddInvalidAcc(self):
        try:
            self.driver.refresh()

            # Test duplicated account
            self.genericAddAccount(checkDuplicated=True)
            closeAddAccountBox = WebDriverWait(self.driver,
                                               3).until(EC.element_to_be_clickable((By.ID, "close-modal-button")))
            closeAddAccountBox.click()
            self.driver.refresh()

            # Test invalid account
            self.genericAddAccount(checkInvalidAcc=True)
            closeAddAccountBox = WebDriverWait(self.driver,
                                               3).until(EC.element_to_be_clickable((By.ID, "close-modal-button")))
            closeAddAccountBox.click()

            # Test max accounts
            self.driver.refresh()
            self.genericAddAccount(checkMaxAccounts=True)
        except Exception as e:
            self.fail(f"Test failed: {str(e)}")

    def test_06_ClearButton(self):
        try:
            initialButtonTexts = [self.get_all_button_texts()[0]]
            self.choose_random_bank_account()
            self.select_random_amount()
            time.sleep(2)

            self.clear_details(clearButton="clear-text")
            time.sleep(2)

            amountField = WebDriverWait(self.driver,
                                        10).until(EC.presence_of_element_located((By.ID, "reload-amount-input")))
            finalButtonTexts = [self.get_all_button_texts()[0]]

            if (
                amountField.get_attribute("value") == ""
                and all(initial == final for initial, final in zip(initialButtonTexts, finalButtonTexts))
            ):
                self.logger.info("All fields are cleared as expected.")
            else:
                self.fail("The fields were not cleared correctly.")
        except Exception as e:
            self.fail(f"Test failed: {str(e)}")

    def test_07_InvalidAmount(self):
        try:
            self.check_invalid_amount(
                amount_field_id="reload-amount-input", submit_button_id="submit-withdraw-button",
                clear_button_id="clear-text", withdrawal=True
            )
        except Exception as e:
            self.fail(f"Test failed: {str(e)}")

    """

    def test_08_IncompleteTurnover(self):
        try:
            initialBalance = self.extract_total_balance()
            self.logger.info(f"Initial Balance: {initialBalance}")
            self.choose_random_bank_account()
            self.select_random_amount()
            userID = self.get_id_number()
            turnoverIncomplete, locked_by_list = self.checkIncompleteTurnover(
                userID, checkIncomplete=True, language=self.language
            )
            self.logger.info(f"Turnover Incomplete: {turnoverIncomplete}")

            if turnoverIncomplete:
                self.generic_submit(
                    expected_result="failure", check_general_error=True, id="swal2-html-container",
                    expected_error=LANGUAGE_SETTINGS[self.language]["errors"]["withdraw_turnover_incomplete"],
                    submit="submit-withdraw-button", turnoverIncomplete="True", locked_by_list=locked_by_list
                )
            else:
                self.fail("Error popout and error message not shown")

            finalBalance = self.extract_total_balance()
            self.logger.info(f"Final Balance: {finalBalance}")
            self.assertEqual(initialBalance, finalBalance, msg="Balance mismatch")
        except Exception as e:
            self.fail(f"Test failed: {str(e)}")

    """
    def test_09_CompleteTurnoverApprove(self):
        try:
            self.performWithdrawTest(is_reject=False, is_processing=False)
        except Exception as e:
            self.fail(f"Test failed: {str(e)}")

    def test_10_CompleteTurnoverReject(self):
        try:
            self.performWithdrawTest(is_reject=True, is_processing=False)
        except Exception as e:
            self.fail(f"Test failed: {str(e)}")

    def test_11_CompleteTurnoverProcessing(self):
        try:
            self.performWithdrawTest(is_reject=False, is_processing=True)
        except Exception as e:
            self.fail(f"Test failed: {str(e)}")

    def test_12_ExceedWithdrawalBalance(self):
        try:
            self.switchToCompleteTurnoverAcc()
            initialBalance = self.extract_total_balance()
            self.logger.info(f"Initial Balance: {initialBalance}")
            self.choose_random_bank_account()

            cleanAmount = self.getWithdrawableAmount()
            maxAmount = int(float(cleanAmount))

            amount = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.ID, "reload-amount-input")))
            exceedAmount = maxAmount + 100
            amount.clear()
            amount.send_keys(str(exceedAmount))

            self.generic_submit(
                expected_result="failure", check_general_error=True, id="swal2-html-container",
                expected_error=LANGUAGE_SETTINGS[self.language]["errors"]["insufficient_main_wallet"],
                submit="submit-withdraw-button"
            )

            finalBalance = self.extract_total_balance()
            self.assertEqual(initialBalance, finalBalance, msg="Balance mismatch")

        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed: {str(e)}")

    """


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    unittest.main()
