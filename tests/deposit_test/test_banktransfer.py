import unittest
import time
import logging
import random
import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from config.constant import LANGUAGE_SETTINGS, CREDENTIALS
from tests.authentication_test.base_test import BaseTest

# upload receipt using camera
# test


class TestBankTransfer(BaseTest):

    def __init__(self, methodName="runTest", language=None, browser=None):
        super().__init__(methodName, language, browser)

    def setUp(self):
        super().setUp()
        self.navigate_to_login_page()
        self.perform_login(CREDENTIALS["duplicated_user"]["username"], CREDENTIALS["duplicated_user"]["password"])
        self.navigate_to_bank_transfer()
        time.sleep(2)

    def tearDown(self):
        if hasattr(self, "driver"):
            self.driver.quit()

    def navigate_to_bank_transfer(self):

        self.navigate_to_reload_page("deposit")

        bank_transfer = WebDriverWait(self.driver,
                                      10).until(EC.element_to_be_clickable((By.ID, "wallet-tab-bank_transfer")))

        bank_transfer.click()
        time.sleep(2)

    def fillInDetails(self):
        reload_amount = self.select_random_amount()
        self.logger.info(reload_amount)
        time.sleep(2)
        self.choose_receipt()
        time.sleep(1)
        return reload_amount

    """
    def test_01_DefaultChooseBank(self):
        try:
            #id
            badge = WebDriverWait(self.driver,
                                  10).until(EC.visibility_of_element_located((By.CLASS_NAME, "MuiBadge-badge")))
            self.assertTrue(badge.is_displayed(), "Bank selection badge is not displayed")
            self.assertEqual(badge.text, "✓", "Bank selection checkmark is not present")

            bank_button = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, "bank-button-9")))

            # Verify bank details are displayed
            bank_name = self.driver.find_element(By.ID, "bank-address-9").text
            bank_owner = self.driver.find_element(By.ID, "bank-owner-9").text
            bank_number = self.driver.find_element(By.ID, "bank-number-9").text

            self.assertEqual(bank_name.lower(), "maybank", "Bank name is not correct")
            self.assertEqual(bank_owner, "BoBo Live Sdn Bhd", "Bank owner is not correct")
            self.assertTrue(bank_number, "Bank number is not displayed")

        except Exception as e:
            self.fail(f"Test failed: {str(e)}")

    def test_02_ClickCopyButtons(self):

        copyBankButtons = self.driver.find_elements(By.ID, "copy-address-button-9")
        copyOwnerButtons = self.driver.find_elements(By.ID, "copy-owner-button-9")
        copyNumberButtons = self.driver.find_elements(By.ID, "copy-number-button-9")

        copy_buttons = copyBankButtons + copyOwnerButtons + copyNumberButtons

        self.logger.info(f"Found {len(copy_buttons)} copy buttons.")

        for index, button in enumerate(copy_buttons):
            try:
                button.click()
                self.logger.info(f"Clicked copy button {index + 1}.")
                #id
                WebDriverWait(self.driver, 10).until(
                    EC.visibility_of_element_located(
                        (By.XPATH, "//div[contains(@class, 'MuiSnackbarContent-message')]")
                    )
                )

                snackbar_message = self.driver.find_element(
                    By.XPATH, "//div[contains(@class, 'MuiSnackbarContent-message')]"
                )

                if snackbar_message.is_displayed():
                    self.logger.info("Snackbar message is visible after clicking.")
                    self.logger.info(f"Snackbar message: {snackbar_message.text}")
                    time.sleep(1)
                else:
                    self.logger.warning("Snackbar message is NOT visible after clicking.")

            except Exception as e:
                self.logger.error(f"Error clicking copy button {index + 1}: {e}")

        self.logger.info("Finished clicking all copy buttons.")

    def test_03_ChooseAmount(self):
        driver = self.driver
        try:

            amountSection = WebDriverWait(driver,
                                          10).until(EC.presence_of_element_located((By.ID, 'amount-toggle-group')))
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", amountSection)
            time.sleep(1)
            self.choose_amount(0)
        except Exception as e:
            self.fail(f"Test failed: {str(e)}")

    #check is it upload correct image
    def test_04_UploadReceipt(self):
        driver = self.driver
        self.scrollToSection("wallet-form-uploadReceipt")
        time.sleep(1)
        try:
            add_photo_button = WebDriverWait(driver,
                                             10).until(EC.element_to_be_clickable((By.ID, "upload-receipt-button")))
            add_photo_button.click()
            #Upload Receipt using choose from gallery
            self.upload_receipt(choose_from_gallery=True)

            time.sleep(2)

            #Change Text
            try:
                button_text = add_photo_button.text.strip()
                self.logger.info(f"Upload button text: {button_text}")
                expected_texts = ["更换照片", "Change Photo", "Tukar Gambar"]
                self.assertIn(
                    button_text, expected_texts,
                    f'Upload button text did not match any expected values: {expected_texts}'
                )

            except AssertionError:
                self.fail("Upload button text did not appear or change.")

            #Replace Receipt
            try:
                add_photo_button.click()
                upload_success = self.upload_from_gallery(replace=True)
                self.assertTrue(upload_success, "Failed to upload image from gallery")

                image_uploaded = self.verify_uploaded_image(remove=False)
                self.assertTrue(image_uploaded, "No image was uploaded or displayed")
            except AssertionError:
                self.fail("Cannot replace the currrent receipt.")

            #Upload Receipt using camera
            #try:
            #add_photo_button.click()
            #self.upload_receipt(choose_from_gallery=False)
            #time.sleep(2)
            #except AssertionError:
            #    self.fail("Cannot upload the new receipt using camera feature.")

            #Remove Receipt
            try:
                time.sleep(2)
                close_button = WebDriverWait(driver,
                                             10).until(EC.element_to_be_clickable((By.ID, "receipt-close-icon")))
                close_button.click()

                time.sleep(2)
                image_removed = self.verify_uploaded_image(remove=True)
                self.assertTrue(image_removed, "No image was removed")
            except AssertionError as e:
                self.logger.error("Cannot remove the current receipt.")

        except Exception as e:
            self.fail(f"Test failed: {str(e)}")
  
    def test_05_InvalidReceipt(self):
        driver = self.driver
        self.scrollToSection("wallet-form-uploadReceipt")
        try:
            add_photo_button = WebDriverWait(driver,
                                             10).until(EC.element_to_be_clickable((By.ID, "upload-receipt-button")))
            add_photo_button.click()
            self.upload_from_gallery(checkLargeFile=True)
            self.check_general_error(LANGUAGE_SETTINGS[self.language]["errors"]["large_file_type"], id="swal2-title")
        except Exception as e:
            self.fail(f"Test failed: {str(e)}")

    def test_06_ChoosePromo(self):
        driver = self.driver
        try:
            self.scrollToSection("wallet-form-popoPromo")
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

    def test_07_SubmitWithInvalidVoucher(self):
        try:
            self.select_random_amount()
            self.choose_receipt()
            invalidVoucher = CREDENTIALS["deposit"]["invalid_voucher"]
            self.checkInvalidVoucher(invalidVoucher, submitButton="submit-button")

        except Exception as e:
            self.fail(f"Test failed: {str(e)}")

    #got issue (eg: payment method will clear the defualt selection and cannot replace the same image)
    
  

    def test_08_InvalidAmount(self):
        try:
            self.check_invalid_amount(
                amount_field_id="reload-amount-input", submit_button_id="submit-button", clear_button_id="clear-button",
                choose_receipt=True
            )
        except Exception as e:
            self.fail(f"Test failed: {str(e)}")
  """

    #approve
    def test_09_SubmitReloadWithoutPromo(self):
        driver = self.driver
        try:
            time.sleep(2)
            initialSpinTickets = self.checkSpinTicket()
            initialBBPoints = self.checkBBPoint()
            self.navigateHomePage()
            self.navigate_to_bank_transfer()
            self.logger.info(f"Initial Spin tickets: {initialSpinTickets}")
            self.logger.info(f"Initial BB Points: {initialBBPoints}")

            initialBalance = self.extract_total_balance()
            time.sleep(3)
            reload_amount = self.fillInDetails()
            self.generic_submit(expected_result="success", submit="submit-button")
            self.confirm_button()
            ID = self.get_id_number()
            self.handleDeposit(ID)
            time.sleep(2)

            self.verifyBonusBalance(initialBalance=initialBalance, reloadAmount=reload_amount)
            self.checkSpinTicketAndBBPoint(initialSpinTickets, initialBBPoints, reloadAmount=reload_amount)

        except Exception as e:
            self.fail(f"Test failed: {str(e)}")

    """

    #approve
    def test_10_SubmitReloadWithPromo(self):
        try:
            initialSpinTickets = self.checkSpinTicket()
            initialBBPoints = self.checkBBPoint()
            self.navigateHomePage()
            self.navigate_to_bank_transfer()
            self.logger.info(f"Initial Spin tickets: {initialSpinTickets}")
            self.logger.info(f"Initial BB Points: {initialBBPoints}")
            totalReloadAmount = self.submitReloadWithPromo(
                submitButtonId="submit-button", chooseReceipt=True, isQuickReload=False
            )
            self.logger.info(f"Total reload amount: {totalReloadAmount}")
            self.checkSpinTicketAndBBPoint(initialSpinTickets, initialBBPoints, reloadAmount=totalReloadAmount)

        except Exception as e:
            self.fail(f"Test failed: {str(e)}")

    def test_11_ClearButton(self):
        try:
            PromoOrVoucher = [{
                "type": "promo",
                "action": lambda: self.select_random_promo(0)
            }, {
                "type": "voucher",
                "action": lambda: self.enter_voucher("testing")
            }]

            initial_button_texts = [self.get_all_button_texts()[0], self.get_all_button_texts()[1]]

            for scenario in PromoOrVoucher:
                self.logger.info(f"Testing clear button with {scenario['type']}")

                # Common setup steps
                self.select_random_amount()
                time.sleep(1)
                self.choose_receipt()

                # Execute specific action (promo or voucher)
                scenario["action"]()
                time.sleep(1)

                # Clear and verify
                self.clear_details(clearButton="clear-button")
                time.sleep(2)
                self.verify_clear_functionality(initial_button_texts, [0, 1], check_image_removal=True)

        except Exception as e:
            self.fail(f"Test failed: {str(e)}")


    def test_12_EmptyFields(self):
        driver = self.driver

        # empty amount
        self.choose_receipt()
        amount_field = WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.ID, "reload-amount-input")))
        self.generic_submit(
            field=amount_field, expected_result="failure", check_general_error=False, submit="submit-button"
        )

        #empty receipt
        self.clear_details(clearButton="clear-button")
        time.sleep(2)
        self.select_random_amount()
        self.generic_submit(
            expected_result="failure", expected_error=LANGUAGE_SETTINGS[self.language]["errors"]["empty_fields"],
            check_general_error=True, id="swal2-title", submit="submit-button"
        )

    def test_13_checkMininumPromoDeposit(self):
        try:
            self.checkDepositLimit(chooseReceipt=True)
        except Exception as e:
            self.fail(f"Test failed: {str(e)}")

    def test_14_RejectDeposit(self):
        driver = self.driver
        try:
            time.sleep(2)
            initialSpinTickets = self.checkSpinTicket()
            initialBBPoints = self.checkBBPoint()
            self.navigateHomePage()
            self.navigate_to_bank_transfer()
            self.logger.info(f"Initial Spin tickets: {initialSpinTickets}")
            self.logger.info(f"Initial BB Points: {initialBBPoints}")

            initialBalance = self.extract_total_balance()
            reloadAmount = self.fillInDetails()

            self.generic_submit(expected_result="success", submit="submit-button")
            self.confirm_button()
            ID = self.get_id_number()
            self.handleDeposit(ID, isReject=True)
            time.sleep(2)

            finalBalance = self.extract_total_balance()
            self.assertEqual(initialBalance, finalBalance, "Balance mismatch")
            self.checkSpinTicketAndBBPoint(
                initialSpinTickets, initialBBPoints, reloadAmount=reloadAmount, isRejectOrProcessing=True
            )

        except Exception as e:
            self.fail(f"Test failed: {str(e)}")

    def test_15_ProcessDeposit(self):
        driver = self.driver
        try:
            time.sleep(2)
            initialSpinTickets = self.checkSpinTicket()
            initialBBPoints = self.checkBBPoint()
            self.navigateHomePage()
            self.navigate_to_bank_transfer()
            self.logger.info(f"Initial Spin tickets: {initialSpinTickets}")
            self.logger.info(f"Initial BB Points: {initialBBPoints}")

            initialBalance = self.extract_total_balance()
            reloadAmount = self.fillInDetails()

            self.generic_submit(expected_result="success", submit="submit-button")
            self.confirm_button()
            ID = self.get_id_number()
            self.handleDeposit(ID, isProcessing=True)
            time.sleep(2)

            finalBalance = self.extract_total_balance()
            self.assertEqual(initialBalance, finalBalance, "Balance mismatch")
            self.checkSpinTicketAndBBPoint(
                initialSpinTickets, initialBBPoints, reloadAmount=reloadAmount, isRejectOrProcessing=True
            )

        except Exception as e:
            self.fail(f"Test failed: {str(e)}")

    """


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    unittest.main()
