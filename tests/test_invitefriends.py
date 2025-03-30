import os
import unittest
import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from config.constant import LANGUAGE_SETTINGS, CREDENTIALS
from tests.authentication_test.base_test import BaseTest
import pyperclip
from PIL import Image
import io
from pyzbar.pyzbar import decode
from urllib.parse import urlparse, parse_qs

class TestInviteFriends(BaseTest):

    def __init__(self, methodName="runTest", language=None, browser=None):
        super().__init__(methodName)
        self.language = language
        self.browser = browser
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

        file_handler = logging.FileHandler("test_invite_output.log")
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
        # self.driver.maximize_window()
        self.driver.set_window_size(375, 812)
        self.navigate_to_login_page()
        self.username = CREDENTIALS["duplicated_user"]["username"]
        self.password = CREDENTIALS["duplicated_user"]["password"]
        self.perform_login(self.username, self.password)
        self.navigate_to_profile_page(self.language)

    def tearDown(self):
        if hasattr(self, "driver"):
            self.driver.quit()
    
    def open_invite_modal(self):
        driver = self.driver
        invite_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "qr-code-button"))
        )
        invite_button.click()
    
    def get_invite_code(self):
        driver = self.driver
        try:
            # Get the value from the input field
            input_elements = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.ID, "qr-code-textfield"))
            )
            input_value = input_elements[0].get_attribute("value")
            return input_value
        except Exception as e:
            self.logger.error(f"Get invite code failed: {str(e)}")
            return None
    
    def get_invite_link(self):
        driver = self.driver
        try:
            # Get the value from the input field
            input_elements = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.ID, "qr-code-textfield"))
            )
            input_value = input_elements[1].get_attribute("value")
            return input_value
        except Exception as e:
            self.logger.error(f"Get invite link failed: {str(e)}")
            return None
    
    def get_qrcode_link(self):
        driver = self.driver
        try:
            # Take a screenshot of the entire page
            screenshot = driver.get_screenshot_as_png()
            
            # Open the image and crop it to the bounding box around the SVG element
            with Image.open(io.BytesIO(screenshot)) as img:
                
                # Decode the QR code from the cropped image
                qr_code_data = decode(img)
                
                if qr_code_data:
                    qr_code_link = qr_code_data[0].data.decode()
                    return qr_code_link
                else:
                    self.fail("Test failed with error: Failed to decode QR Code")
                    return None
            
        except Exception as e:
            self.logger.error(f"Get invite link failed: {str(e)}")
            return None

    def verify_is_same(self, isLink=False):
        driver = self.driver
        
        try:
            # Click the copy button
            if isLink:
                input_value = self.get_invite_link()
                copy_buttons = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.ID, "copy-to-clipboard-button"))
                )
                copy_buttons[1].click()
            else:
                input_value = self.get_invite_code()
                copy_buttons = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.ID, "copy-to-clipboard-button"))
                )
                copy_buttons[0].click()
            
            time.sleep(1)
            
            # Get clipboard conten
            clipboard_content = pyperclip.paste()
            
            if input_value != clipboard_content:
                self.logger.warning(f"Clipboard content '{clipboard_content}' doesn't match input value '{input_value}'")
                return False, clipboard_content

            self.logger.info(f"Clipboard content '{clipboard_content}' match input value '{input_value}'")
            
            self.logger.info("Verification successful")
            return True, clipboard_content

        except Exception as e:
            self.logger.error(f"Verify invite code failed: {str(e)}")
            return False, clipboard_content
    
    def verify_navigation_and_autofill(self):
        driver = self.driver
        
        try:
            clipboard_content = pyperclip.paste()
            driver.get(clipboard_content)
            time.sleep(3)
            
            # Extract invite code from the URL
            url = driver.current_url
            expected_code = self.extract_code_from_url(url)
            
            # Verify referral ID auto filled
            self.logger.info("Verifying referral ID auto fill...")
            referral_id_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "register-referral-id"))
            )
            actual_referral = referral_id_element.get_attribute("value")
            if actual_referral != expected_code:
                self.logger.warning(f"Referral ID not auto filled. Expected: {expected_code}, Got: {actual_referral}")
                return False
                
            self.logger.info(f"Referral ID successfully auto filled with: {actual_referral}")
            return True
            
        except Exception as e:
            self.logger.error(f"Verify navigation and autofill failed: {str(e)}")
            return False
    
    def create_downline(self):
        driver = self.driver
        
        try:
            # Generate unique username using timestamp
            current_time = int(str(int(time.time()))[:9])
            register_acc = f"Tt{current_time}"
            self.logger.info(f"Registring Acc: {register_acc}")
            
            # Fill in registration form
            input_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "register-login-id"))
            )
            input_element.send_keys(register_acc)
            input_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "register-password"))
            )
            input_element.send_keys(register_acc)
            input_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "register-confirm-password"))
            )
            input_element.send_keys(register_acc)
            input_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "register-full-name"))
            )
            input_element.send_keys(register_acc)
            input_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "register-phone-number"))
            )
            input_element.send_keys(current_time)
            
            # Submit registration
            register_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "register-submit-button"))
            )
            register_button.click()
            
            # Verify registration success
            success_title = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "swal2-title"))
            )
            is_success = success_title.text == 'Register Successful'
            self.assertTrue(is_success, "Failed to register downline account")
            
            # Click confirm on success popup
            confirm_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CLASS_NAME, "swal2-confirm"))
            )
            confirm_button.click()
            time.sleep(5)
            return True
        except Exception as e:
            self.logger.error(f"Verify downline failed: {str(e)}")
            return False
    
    def topup(self):
        driver = self.driver
        
        try:
            # Navigate to profile page
            # self.annoucement_close_button()
            # time.sleep(2)
            self.daily_checkin_close_button()
            self.navigate_to_profile_page(self.language)
            time.sleep(2)
            
            # Click deposit button in profile menu
            deposit_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "profile-menu-deposit"))
            )
            deposit_button.click()
            time.sleep(5)
            
            # Enter deposit amount
            input_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "reload-amount-input"))
            )
            input_element.send_keys("250")
            time.sleep(1)
            
            # Select payment gateway
            payment_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Select payment gateway')]"))
            )
            payment_button.click()
            time.sleep(1)
            gateway_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "payment-gateway-item"))
            )
            gateway_button.click()
            time.sleep(1)
            
            # Submit deposit request
            submit_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "submit-reload-button"))
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", submit_button)
            time.sleep(1)
            submit_button.click()
            
            # Handle payment gateway and confirmation
            self.paymentGateway()
            time.sleep(2)
            self.confirm_button()
            time.sleep(2)
            return True
        except Exception as e:
            self.fail(f"Test failed: {str(e)}")
            return False
    
    def extract_code_from_url(self, url):
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        if 'code' not in query_params or len(query_params['code']) != 1:
            self.fail("Invite code not found in the QR code.")
        code = query_params['code'][0]
        return code
            
    def test_01_InviteFriendCode(self):
        driver = self.driver
        try:
            self.logger.info("Starting referral code test...")

            # Open invite modal
            self.open_invite_modal()
            
            verification_success = self.verify_is_same()
            self.assertTrue(verification_success, "Failed to verify invite code")
            
        except Exception as e:
            self.fail(f"Test failed with error: {str(e)}")
    
    def test_02_InviteFriendLink(self):
        driver = self.driver
        
        try:
            self.logger.info("Starting referral code test...")
            
            # Open invite modal
            self.open_invite_modal()
    
            # verify share link copy function
            success_status = self.verify_is_same(isLink=True)
            self.assertTrue(success_status, "Failed to verify share link copy function")
                
            # verify navigate and auto fill
            success_status = self.verify_navigation_and_autofill()
            self.assertTrue(success_status, "Failed to verify share link navigate and autofill function")
                
            self.logger.info("Verification successful")
                
        except Exception as e:
            self.fail(f"Test failed with error: {str(e)}")
    
    def test_03_InviteFriendQR(self):
        driver = self.driver
        
        try:
            self.logger.info("Starting QR code test...")
            
            # Open invite modal
            self.open_invite_modal()
            
            invite_link = self.get_invite_link()
            
            qr_code_link = self.get_qrcode_link()
            
            self.assertEqual(invite_link, qr_code_link, "Invite link and QR code do not match")
            self.logger.info(f"Invite link and QR code match")
     
        except Exception as e:
            self.fail(f"Test failed with error: {str(e)}")
    
    def test_04_VerifyAllInviteCodeSame(self):
        driver = self.driver
    
        try:
            self.logger.info("Starting QR code test...")
            
            # Open invite modal
            self.open_invite_modal()
            
            # Get the initial invite code from the modal
            initial_invite_code = self.get_invite_code()
            self.logger.info(f"Initial invite code: {initial_invite_code}")
            
            # Get the invite link and extract the invite code
            invite_link = self.get_invite_link()
            invite_code_link = self.extract_code_from_url(invite_link)
            self.logger.info(f"Invite code from link: {invite_code_link}")
            
            # Get the QR code link and extract the invite code
            qrcode_link = self.get_qrcode_link()
            invite_code_qrcode = self.extract_code_from_url(qrcode_link)
            self.logger.info(f"Invite code from QR code: {invite_code_qrcode}")
            
            # Verify that all codes are the same
            success_status = initial_invite_code == invite_code_link == invite_code_qrcode
            
            if not success_status:
                self.fail("Invite codes do not match.")
            
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
    
    def test_05_ShareToFriendFacebook(self):
        driver = self.driver
        
        try:
            self.logger.info("Starting Facebook share test...")
            
            # Open invite modal
            self.open_invite_modal()
            
            invite_code = self.get_invite_code()
            
            share_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "share-to-friends-button"))
            )
            share_button.click()
            
            #Facebook
            fb_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "share-facebook-button"))
            )
            fb_button.click()
            time.sleep(2)
            windows = driver.window_handles
            if len(windows) > 1:
                driver.switch_to.window(windows[-1])
            
            time.sleep(2)
            fb_share_url = driver.current_url
            fb_invite_code = fb_share_url[-len(invite_code):]
            self.assertEqual(invite_code, fb_invite_code, "Invite codes not same")
            self.logger.info("Facebook share link test passed")
     
        except Exception as e:
            self.fail(f"Test failed with error: {str(e)}")
    
    def test_06_ShareToFriendWhatsapp(self):
        driver = self.driver
        
        try:
            self.logger.info("Starting Whatsapp share test...")
            
            # Open invite modal
            self.open_invite_modal()
            
            invite_code = self.get_invite_code()
            
            share_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "share-to-friends-button"))
            )
            share_button.click()
            
            #Whatsapp
            ws_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "share-whatsapp-button"))
            )
            ws_button.click()
            time.sleep(2)
            windows = driver.window_handles
            if len(windows) > 1:
                driver.switch_to.window(windows[-1])
            
            time.sleep(2)
            ws_share_url = driver.current_url
            ws_invite_code = ws_share_url[-len(invite_code):]
            self.assertEqual(invite_code, ws_invite_code, "Invite codes not same")
            self.logger.info("Whatsapp share link test passed")
     
        except Exception as e:
            self.fail(f"Test failed with error: {str(e)}")
    
    def test_07_CreateDownline(self):
        driver = self.driver
        
        try:
            self.logger.info("Starting create downline test...")
            
            # Get initial member count
            member_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "effective-amount"))
            )
            new_member_before = int(member_element.text)
            
            # Open invite modal
            self.open_invite_modal()
            
            # get invitation link
            invite_link = self.get_invite_link()
            driver.get(invite_link)
            
            # Create downline account and perform top-up
            success_status = self.create_downline()
            self.assertTrue(success_status, "Failed to register downline")
            success_status = self.topup()
            self.assertTrue(success_status, "Failed to topup")
            
            # Log out and log back in as original user
            self.logout()
            self.perform_login(self.username, self.password)
            self.navigate_to_profile_page(self.language)
            
            # Verify member count increased by 1
            member_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "effective-amount"))
            )
            new_member_after = int(member_element.text)
            
            success_status = (new_member_after - new_member_before) == 1
            self.assertTrue(success_status, "Failed to verify downline")
                
        except Exception as e:
            self.fail(f"Test failed with error: {str(e)}")

if __name__ == "__main__":
    unittest.main()
