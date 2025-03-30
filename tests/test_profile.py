import os
import re
import unittest
import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from config.constant import LANGUAGE_SETTINGS, CREDENTIALS, LIVE_AGENT_URL, PROFILE_URL
from tests.authentication_test.base_test import BaseTest
import tempfile
import requests
from urllib.parse import urlparse, unquote
from selenium.webdriver.common.action_chains import ActionChains
from tests.test_init import TestInit

class HomepageData(BaseTest):
    """Class to manage homepage data and operations"""
    
    def user_api(self, username, password):
        """Get user data from API"""
        token = self.login(username, password)
        headers = {
            "Authorization": f"Bearer {token}"
        }
        response = requests.get(f"{CREDENTIALS['GetUser'].format(BO_base_url=CREDENTIALS['BO_base_url'])}", headers=headers)
        response.raise_for_status() 
        return response.json()['data']

    def provider_api(self, username, password):
        """Get provider data from API"""
        token = self.login(username, password)
        headers = {
            "Authorization": f"Bearer {token}",
            "language": self.language
        }
        response = requests.get(f"{CREDENTIALS['GetProvider'].format(BO_base_url=CREDENTIALS['BO_base_url'])}", headers=headers)
        return response.json()['data']

    def home_api(self, username, password):
        """Get home data from API"""
        token = self.login(username, password)
        headers = {
            "Authorization": f"Bearer {token}"
        }
        response = requests.get(f"{CREDENTIALS['GetHome'].format(BO_base_url=CREDENTIALS['BO_base_url'])}", headers=headers)
        return response.json()['data']
        

class TestProfilePage(BaseTest):

    def __init__(self, methodName="runTest", language=None, browser=None):
        super().__init__(methodName, language, browser)
        self.test_init = TestInit(methodName="runTest", language=language, browser=browser)

    def setUp(self):
        if not self.browser or not self.language:
            raise ValueError("Browser or language is not set.")
        self.logger.info(f"Setting up {self.browser} browser for {self.language} language...")
        self.driver = self.initialize_browser(self.browser)
        assert self.driver is not None, "Browser initialization failed!"

        self.url = LANGUAGE_SETTINGS[self.language]["home_url"]
        self.driver.get(self.url)
        # self.driver.maximize_window()
        self.driver.set_window_size(375, 812)
        self.action = ActionChains(self.driver)
        

    def tearDown(self):
        if hasattr(self, "driver"):
            self.driver.quit()
    
    def setup_test_user(self, register_new=False):
        """Set up test user - either create new or use existing"""
        if register_new:
            self.logger.info("Registering new account...")
            self.username, self.password = self.test_init.register_new_account()
        else:
            if self.language == "bm":
                self.username = "LuffyTest1"
                self.password = "LuffyTest1"
            elif self.language == "cn":
                self.username = "LuffyTest2"
                self.password = "LuffyTest2"
            elif self.language == "en":
                self.username = "LuffyTest3"
                self.password = "LuffyTest3"
            else:
                self.username = "LuffyTest4"
                self.password = "LuffyTest4"
                
        while self.username == None or self.password == None:
            self.logger.info("Registering new account...")
            self.username, self.password = self.test_init.register_new_account()
            
        self.logger.info(f"Username: {self.username}, Password: {self.password}")
        self.navigate_to_login_page()
        self.perform_login(self.username, self.password)
        
        return self.username, self.password
    
    # Helper methods
    def wait_for_element(self, by, value, timeout=15):
        """Wait for an element to be present and return it"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return element
        except TimeoutException:
            self.logger.error(f"Element not found: {by}={value}")
            raise
    
    def scroll_element_to_center(self, element):
        # First scroll the element to center using JavaScript
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        
        # Then use ActionChains to move to that element (optional)
        actions = ActionChains(self.driver)
        actions.move_to_element(element).perform()
        
        # Add a small delay to let the scrolling complete
        import time
        time.sleep(1)
    
    def navigate_to_home_and_handle_popups(self, close_mission=True):
        """Navigate to home page and handle any popups."""
        self.driver.get(self.url)
        self.annoucement_close_button()
        self.daily_checkin_close_button(close_mission)
    
    def make_deposit(self, amount):
        """Make a deposit of the specified amount"""
        self.logger.info(f"Making a deposit of RM{amount}...")
        user_id = self.get_user_id()
        self.test_init.submit_deposit_api(username=self.username, password=self.password, amount=amount)
        self.handleDeposit(user_id)

    def verify_upload_success(self, isFromGallery = True):
        driver = self.driver

        try:
            profile_img_before = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'img[alt="profile_avatar"]'))
            )
            img_src_before = profile_img_before.get_attribute("src")
            self.logger.info(f"Profile image src before upload: {img_src_before}")

            if isFromGallery:
                upload_success = self.upload_from_gallery()
                if not upload_success:
                    self.logger.error("Image upload failed.")
                    return False
            else:
                self.driver.maximize_window()
                upload_success = self.upload_from_camera()
                self.driver.set_window_size(375, 812)
                if not upload_success:
                    self.logger.error("Image upload failed.")
                    return False
                

            self.logger.info("Waiting for upload to complete...")
            time.sleep(10)
            self.success_box()
            driver.refresh()
            self.logger.info("Page refreshed.")

            profile_img_after = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'img[alt="profile_avatar"]'))
            )
            sm_img_src_after = profile_img_after.get_attribute("src")
            self.logger.info(f"Small profile image src after upload: {sm_img_src_after}")
            
            lg_img_src_after = profile_img_after.get_attribute("src")
            self.logger.info(f"Large profile image src after upload: {lg_img_src_after}")

            if sm_img_src_after != img_src_before and sm_img_src_after:
                self.logger.info("Profile picture updated successfully with a new blob URL.")
                if sm_img_src_after == lg_img_src_after:
                    self.logger.info("Small profile picture and large profile picture is same.")
                    return True

            self.logger.warning("Profile picture URL did not change or is not a blob URL.")
            return False

        except (TimeoutException, NoSuchElementException) as e:
            self.logger.error(f"Verification failed: {str(e)}")
            return False
    
    def verify_invalid_format_upload(self):
        driver = self.driver
        try:
            # Find file input element
            file_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="file"]'))
            )
            
            # Upload invalid format file
            invalid_file_url = PROFILE_URL["invalid_format_url"]
            # Get the filename from URL
            filename = os.path.basename(urlparse(invalid_file_url).path)
            
            # Create a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as temp_file:
                try:
                    response = requests.get(invalid_file_url)
                    response.raise_for_status()  # Raises an HTTPError for bad responses
                    temp_file.write(response.content)
                    invalid_file_path = temp_file.name
                except requests.exceptions.RequestException as e:
                    self.fail(f"Failed to download image from URL: {e}")
                    return False

            if not os.path.exists(invalid_file_path):
                raise FileNotFoundError(f"Test image not found at {invalid_file_path}")
            
            os.chmod(invalid_file_path, 0o644)
            self.logger.info(f"Changed file permissions to make it world-readable: {invalid_file_path}")
            
            try:
                file_input.send_keys(invalid_file_path)
                self.logger.info(f"Attempting to upload invalid file: {invalid_file_path}")
            except Exception as e:
                self.logger.error(f"Error sending file path to input: {str(e)}")
                return True

            self.warning_box()
            self.logger.info("Error message disappeared as expected")
            return True

        except Exception as e:
            self.logger.error(f"Invalid format upload verification failed: {str(e)}")
            return False
    
    def compare_image_urls(self, ui_image_src, expected_image_url, image_type="Image"):
        """
        Compare an image URL from the UI with an expected URL from the API.
        
        Args:
            ui_image_src (str): The src attribute from the image element in the UI
            expected_image_url (str): The expected image URL from the API
            image_type (str): Type of image being compared (for logging purposes)
            
        Returns:
            bool: True if the URLs match after normalization
            
        Raises:
            AssertionError: If the URLs don't match, with detailed error message
        """
        self.logger.info(f"Comparing {image_type} URLs")
        self.logger.info(f"UI {image_type} src: {ui_image_src}")
        self.logger.info(f"Expected {image_type} URL: {expected_image_url}")
        
        # Verify the expected image URL is valid
        try:
            self.assertTrue(self.check_img_response(expected_image_url), 
                           f"Expected {image_type} URL is not valid: {expected_image_url}")
        except Exception as e:
            self.logger.error(f"Error validating expected {image_type} URL: {str(e)}")
            raise
            
        # Extract the actual image URL from the image src
        # The src might be a Next.js image URL that includes the actual URL as a parameter
        actual_image_url = None
        url_param_match = re.search(r'url=([^&]+)', ui_image_src)
        if url_param_match:
            encoded_url = url_param_match.group(1)
            actual_image_url = unquote(encoded_url)
        else:
            actual_image_url = ui_image_src
            
        self.logger.info(f"Extracted {image_type} URL: {actual_image_url}")
        
        # Normalize both URLs before comparison (remove trailing slashes, etc.)
        normalized_actual_url = actual_image_url.strip().rstrip('/') if actual_image_url else None
        normalized_expected_url = expected_image_url.strip().rstrip('/')
        
        # Check for None values
        if normalized_actual_url is None:
            raise AssertionError(f"Failed to extract {image_type} URL from source: {ui_image_src}")
            
        # Compare the URLs
        urls_match = normalized_actual_url == normalized_expected_url
        
        if not urls_match:
            error_msg = (f"{image_type} URL mismatch.\n"
                         f"Found:    {normalized_actual_url}\n"
                         f"Expected: {normalized_expected_url}")
            self.logger.error(error_msg)
            raise AssertionError(error_msg)

        self.check_img_response(normalized_expected_url)
            
        self.logger.info(f"{image_type} URLs match successfully")
        return True

    def check_img_response(self, img_url):
        """Check if image URL is valid"""
        response = requests.get(img_url)
        response.raise_for_status()
        return True

    def test_01_ChangeProfileGallery(self):
        driver = self.driver

        try:
            self.logger.info("Starting gallery upload test...")
            self.setup_test_user(register_new=True)
            self.navigate_to_profile_page(self.language)
            
            # upload
            self.logger.info("Starting gallery upload test...")
            edit_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "edit-avatar-button"))
            )
            edit_button.click()
            verification_success = self.verify_upload_success(True)
            self.assertTrue(verification_success, "Failed to verify profile picture update")

        except Exception as e:
            self.fail(f"Test failed with error: {str(e)}")
    
    # def test_02_ChangeProfileCamera(self):
    #     driver = self.driver

    #     try:
    #         self.logger.info("Starting gallery upload test...")
    #         self.setup_test_user(register_new=True)
    #         self.navigate_to_profile_page(self.language)
            
    #         # camera
    #         self.logger.info("Starting camera upload test...")
    #         edit_button = WebDriverWait(driver, 10).until(
    #             EC.element_to_be_clickable((By.ID, "edit-avatar-button"))
    #         )
    #         edit_button.click()
    #         verification_success = self.verify_upload_success(False)
    #         self.assertTrue(verification_success, "Failed to verify profile picture update")
    #     except Exception as e:
    #         self.fail(f"Test failed with error: {str(e)}")
    
    # def test_03_ChangeProfileInvalidFormat(self):
    #     driver = self.driver

    #     try:
    #         #invalid format
    #         self.logger.info("Starting invalid format upload test...")
    #         self.setup_test_user(register_new=True)
    #         self.navigate_to_profile_page(self.language)
            
    #         edit_button = WebDriverWait(driver, 10).until(
    #             EC.element_to_be_clickable((By.ID, "edit-avatar-button"))
    #         )
    #         edit_button.click()
    #         verification_success = self.verify_invalid_format_upload()
    #         self.assertTrue(verification_success, "Failed to verify invalid format upload")
    #     except Exception as e:
    #         self.fail(f"Test failed with error: {str(e)}")
    
    # def test_04_ChangeProfileLargeFile(self):
    #     driver = self.driver

    #     try:
    #         # Large File
    #         self.logger.info("Starting large file upload test...")
    #         edit_button = WebDriverWait(driver, 10).until(
    #             EC.element_to_be_clickable((By.ID, "edit-avatar-button"))
    #         )
    #         edit_button.click()
    #         self.upload_from_gallery(checkLargeFile=True)
    #         self.check_general_error(LANGUAGE_SETTINGS[self.language]["errors"]["large_file_type"], id="swal2-title")
    #     except Exception as e:
    #         self.fail(f"Test failed with error: {str(e)}")
           
    # def test_05_TopBarInfo(self):
    #     try:
    #         self.logger.info("Starting top bar info test...")
    #         self.setup_test_user(register_new=True)
            
    #         home_user_data = HomepageData.user_api(self, self.username, self.password)
    #         self.logger.info(f"User data: {home_user_data}")
            
    #         # find avatar by img alt
    #         avatar_element = self.wait_for_element(By.XPATH, f"//img[@alt='profile_avatar']")
    #         avatar_src = avatar_element.get_attribute("src")
            
    #         expected_avatar = home_user_data['avatar']
            
    #         # Use the new general-purpose image comparison function
    #         self.compare_image_urls(avatar_src, expected_avatar, image_type="Avatar")

    #         user_id = self.wait_for_element(By.ID, f"user-profile-id").text.split(": ")[1].strip()
    #         self.logger.info(f"User ID: {user_id}")
            
    #         expected_user_id = home_user_data['id']
    #         self.assertEqual(str(user_id), str(expected_user_id), f"User ID mismatch. \nFound: {user_id} \nExpected: {expected_user_id}")

    #         language = self.wait_for_element(By.ID, f"language-selector-dropdown").text.lower()
    #         self.assertEqual(language, self.language, f"Language mismatch. \nFound: {language} \nExpected: {self.language}")
            
    #         # check if language image is displayed
    #         language_img = self.wait_for_element(By.XPATH, f"//img[@alt='{language}-icon']")
    #         self.assertTrue(language_img.is_displayed(), f"Language image is not displayed for {language} language")

    #         self.logger.info("Top bar info test passed")

    #     except Exception as e:
    #         self.fail(f"Test failed: {str(e)}")
    
    # def test_06_Balance(self):
    #     try:
    #         self.logger.info("Starting balance test...")
    #         self.setup_test_user(register_new=False)
    #         self.navigate_to_profile_page(self.language)
            
    #         home_user_data = HomepageData.user_api(self, self.username, self.password)
    #         self.logger.info(f"User data: {home_user_data}")

    #         balance_text = self.wait_for_element(By.ID, "balance-total").text
    #         self.logger.info(f"Balance text: {balance_text}")
            
    #         expected_balance_text = LANGUAGE_SETTINGS[self.language]['profile']['balance']
            
    #         self.assertEqual(balance_text, expected_balance_text, "Balance text not displayed as expected. \nFound: {balance_text} \nExpected: {expected_balance_text}")
            
    #         balance_value = self.wait_for_element(By.ID, "profile-balance-value").text.replace(",", "")
    #         expected_balance_value = int(float(home_user_data['total_balance'])) if home_user_data['total_balance'].endswith('.00') else format(round(float(home_user_data['total_balance']), 2), '.2f')
    #         expected_balance_value_text = LANGUAGE_SETTINGS[self.language]['profile']['balance_value'].format(amount=expected_balance_value)
    #         self.assertEqual(balance_value, expected_balance_value_text, "Balance value not displayed as expected. \nFound: {balance_value} \nExpected: {expected_balance_value_text}")
            
    #         balance_button = self.wait_for_element(By.ID, "deposit-balance-button")
            
    #         current_url = self.driver.current_url
    #         # get base url by using urlparse
    #         base_url = urlparse(current_url).netloc
    #         protocol = urlparse(current_url).scheme
            
    #         size = balance_button.size
    #         width = size['width']
    #         height = size['height']
            
    #         x_offset = width - 5  
            
    #         # click right side of the button
    #         self.action.move_to_element(balance_button).move_by_offset(x_offset/2, 0).click().perform()
            
    #         # wait for the redirected url
    #         WebDriverWait(self.driver, 45).until(
    #             EC.url_to_be(f"{protocol}://{base_url}/{self.language}/wallet/deposit")
    #         )
            
    #         self.logger.info("Balance button test passed")
 
    #     except Exception as e:
    #         self.fail(f"Test failed: {str(e)}")
    
    # def test_07_BBPoints(self):
    #     try:
    #         self.logger.info("Starting BBPoints test...")
    #         self.setup_test_user(register_new=False)
    #         self.navigate_to_profile_page(self.language)
            
    #         home_user_data = HomepageData.user_api(self, self.username, self.password)
    #         self.logger.info(f"User data: {home_user_data}")

    #         bbpoints_text = self.wait_for_element(By.ID, "balance-bb").text
    #         self.logger.info(f"BBPoints text: {bbpoints_text}")
            
    #         expected_bbpoints_text = LANGUAGE_SETTINGS[self.language]['profile']['bbpoints']
            
    #         self.assertEqual(bbpoints_text, expected_bbpoints_text, "BBPoints text not displayed as expected. \nFound: {bbpoints_text} \nExpected: {expected_bbpoints_text}")
            
    #         bbpoints_button = self.wait_for_element(By.ID, "gift-redemption-button")
            
    #         current_url = self.driver.current_url
    #         # get base url by using urlparse
    #         base_url = urlparse(current_url).netloc
    #         protocol = urlparse(current_url).scheme
            
    #         size = bbpoints_button.size
    #         width = size['width']
    #         height = size['height']
            
    #         x_offset = width - 5  
            
    #         # click right side of the button
    #         self.action.move_to_element(bbpoints_button).move_by_offset(x_offset/2, 0).click().perform()
                        
    #         # wait for the redirected url
    #         WebDriverWait(self.driver, 45).until(
    #             EC.url_to_be(f"{protocol}://{base_url}/{self.language}/profile/gift_redemption")
    #         )

    #         self.logger.info("BBPoints button test passed")

    #     except Exception as e:
    #         self.fail(f"Test failed: {str(e)}")
    
    # def test_08_DepositButton(self):
    #     try:
    #         self.logger.info("Starting Deposit button test...")
    #         self.setup_test_user(register_new=False)
    #         self.navigate_to_profile_page(self.language)

    #         deposit_text = self.wait_for_element(By.CSS_SELECTOR, "p[id='profile-menu-deposit']").text
    #         self.logger.info(f"Deposit text: {deposit_text}")
            
    #         expected_deposit_text = LANGUAGE_SETTINGS[self.language]['profile']['deposit']
            
    #         self.assertEqual(deposit_text, expected_deposit_text, "Deposit text not displayed as expected. \nFound: {deposit_text} \nExpected: {expected_deposit_text}")
            
    #         deposit_button = self.wait_for_element(By.CSS_SELECTOR, "a[id='profile-menu-deposit']")
            
    #         current_url = self.driver.current_url
    #         # get base url by using urlparse
    #         base_url = urlparse(current_url).netloc
    #         protocol = urlparse(current_url).scheme
            
            
    #         # click right side of the button
    #         self.scroll_element_to_center(deposit_button)
    #         self.action.move_to_element(deposit_button).click().perform()
                        
    #         # wait for the redirected url
    #         WebDriverWait(self.driver, 45).until(
    #             EC.url_to_be(f"{protocol}://{base_url}/{self.language}/wallet/deposit")
    #         )

    #         self.logger.info("Deposit button test passed")

    #     except Exception as e:
    #         self.fail(f"Test failed: {str(e)}")
    
    # def test_09_WithdrawButton(self):
    #     try:
    #         self.logger.info("Starting Withdraw button test...")
    #         self.setup_test_user(register_new=False)
    #         self.navigate_to_profile_page(self.language)

    #         withdraw_text = self.wait_for_element(By.CSS_SELECTOR, "p[id='profile-menu-withdrawal']").text
    #         self.logger.info(f"Withdraw text: {withdraw_text}")
            
    #         expected_withdraw_text = LANGUAGE_SETTINGS[self.language]['profile']['withdraw']
            
    #         self.assertEqual(withdraw_text, expected_withdraw_text, "Withdraw text not displayed as expected. \nFound: {withdraw_text} \nExpected: {expected_withdraw_text}")
            
    #         withdraw_button = self.wait_for_element(By.CSS_SELECTOR, "a[id='profile-menu-withdrawal']")
            
    #         current_url = self.driver.current_url
    #         # get base url by using urlparse
    #         base_url = urlparse(current_url).netloc
    #         protocol = urlparse(current_url).scheme
            
            
    #         # click right side of the button
    #         self.scroll_element_to_center(withdraw_button)
    #         self.action.move_to_element(withdraw_button).click().perform()
                        
    #         # wait for the redirected url
    #         WebDriverWait(self.driver, 45).until(
    #             EC.url_to_be(f"{protocol}://{base_url}/{self.language}/wallet/withdrawal")
    #         )

    #         self.logger.info("Withdraw button test passed")

    #     except Exception as e:
    #         self.fail(f"Test failed: {str(e)}")

    # def test_10_TransferButton(self):
    #     try:
    #         self.logger.info("Starting Transfer button test...")
    #         self.setup_test_user(register_new=False)
    #         self.navigate_to_profile_page(self.language)

    #         transfer_text = self.wait_for_element(By.CSS_SELECTOR, "p[id='profile-menu-transfer']").text
    #         self.logger.info(f"Transfer text: {transfer_text}")
            
    #         expected_transfer_text = LANGUAGE_SETTINGS[self.language]['profile']['transfer']
            
    #         self.assertEqual(transfer_text, expected_transfer_text, "Transfer text not displayed as expected. \nFound: {transfer_text} \nExpected: {expected_transfer_text}")
            
    #         transfer_button = self.wait_for_element(By.CSS_SELECTOR, "a[id='profile-menu-transfer']")
            
    #         current_url = self.driver.current_url
    #         # get base url by using urlparse
    #         base_url = urlparse(current_url).netloc
    #         protocol = urlparse(current_url).scheme
            
            
    #         # click right side of the button
    #         self.scroll_element_to_center(transfer_button)
    #         self.action.move_to_element(transfer_button).click().perform()
                        
    #         # wait for the redirected url
    #         WebDriverWait(self.driver, 45).until(
    #             EC.url_to_be(f"{protocol}://{base_url}/{self.language}/wallet/transfer")
    #         )

    #         self.logger.info("Withdraw button test passed")

    #     except Exception as e:
    #         self.fail(f"Test failed: {str(e)}")
            
    # def test_11_RebateButton(self):
    #     try:
    #         self.logger.info("Starting Rebate button test...")
    #         self.setup_test_user(register_new=False)
    #         self.navigate_to_profile_page(self.language)

    #         rebate_text = self.wait_for_element(By.CSS_SELECTOR, "p[id='profile-menu-rebate']").text
    #         self.logger.info(f"Rebate text: {rebate_text}")
            
    #         expected_rebate_text = LANGUAGE_SETTINGS[self.language]['profile']['rebate']
            
    #         self.assertEqual(rebate_text, expected_rebate_text, "Rebate text not displayed as expected. \nFound: {rebate_text} \nExpected: {expected_rebate_text}")
            
    #         rebate_button = self.wait_for_element(By.CSS_SELECTOR, "a[id='profile-menu-rebate']")
            
    #         current_url = self.driver.current_url
    #         # get base url by using urlparse
    #         base_url = urlparse(current_url).netloc
    #         protocol = urlparse(current_url).scheme
            
            
    #         # click right side of the button
    #         self.scroll_element_to_center(rebate_button)
    #         self.action.move_to_element(rebate_button).click().perform()
                        
    #         # wait for the redirected url
    #         WebDriverWait(self.driver, 45).until(
    #             EC.url_to_be(f"{protocol}://{base_url}/{self.language}/wallet/rebate")
    #         )

    #         self.logger.info("Rebate button test passed")

    #     except Exception as e:
    #         self.fail(f"Test failed: {str(e)}")   
    
    # def test_12_PromotionButton(self):
    #     try:
    #         self.logger.info("Starting Promotion button test...")
    #         self.setup_test_user(register_new=False)
    #         self.navigate_to_profile_page(self.language)

    #         promotion_text = self.wait_for_element(By.CSS_SELECTOR, "p[id='profile-menu-promotion']").text
    #         self.logger.info(f"Promotion text: {promotion_text}")
            
    #         expected_promotion_text = LANGUAGE_SETTINGS[self.language]['profile']['promotion']
            
    #         self.assertEqual(promotion_text, expected_promotion_text, "Promotion text not displayed as expected. \nFound: {promotion_text} \nExpected: {expected_promotion_text}")
            
    #         promotion_button = self.wait_for_element(By.CSS_SELECTOR, "a[id='profile-menu-promotion']")
            
    #         current_url = self.driver.current_url
    #         # get base url by using urlparse
    #         base_url = urlparse(current_url).netloc
    #         protocol = urlparse(current_url).scheme
            
            
    #         # click right side of the button
    #         self.scroll_element_to_center(promotion_button)
    #         self.action.move_to_element(promotion_button).click().perform()
                        
    #         # wait for the redirected url
    #         WebDriverWait(self.driver, 45).until(
    #             EC.url_to_be(f"{protocol}://{base_url}/{self.language}/promotions")
    #         )

    #         self.logger.info("Promotion button test passed")

    #     except Exception as e:
    #         self.fail(f"Test failed: {str(e)}")     
    
    # def test_13_LottoRecordButton(self):
    #     try:
    #         self.logger.info("Starting Lotto Record button test...")
    #         self.setup_test_user(register_new=False)
    #         self.navigate_to_profile_page(self.language)

    #         lotto_record_text = self.wait_for_element(By.CSS_SELECTOR, "p[id='profile-menu-lotto_history']").text
    #         self.logger.info(f"Lotto Record text: {lotto_record_text}")
            
    #         expected_lotto_record_text = LANGUAGE_SETTINGS[self.language]['profile']['lotto_record']
            
    #         self.assertEqual(lotto_record_text, expected_lotto_record_text, "Lotto Record text not displayed as expected. \nFound: {lotto_record_text} \nExpected: {expected_lotto_record_text}")
            
    #         lotto_record_button = self.wait_for_element(By.CSS_SELECTOR, "a[id='profile-menu-lotto_history']")
            
    #         current_url = self.driver.current_url
    #         # get base url by using urlparse
    #         base_url = urlparse(current_url).netloc
    #         protocol = urlparse(current_url).scheme
            
            
    #         # click right side of the button
    #         self.scroll_element_to_center(lotto_record_button)
    #         self.action.move_to_element(lotto_record_button).click().perform()
                        
    #         # wait for the redirected url
    #         WebDriverWait(self.driver, 45).until(
    #             EC.url_to_be(f"{protocol}://{base_url}/{self.language}/profile/lotto")
    #         )

    #         self.logger.info("Lotto Record button test passed")

    #     except Exception as e:
    #         self.fail(f"Test failed: {str(e)}")
    
    # def test_14_GiftRedemptionButton(self):
    #     try:
    #         self.logger.info("Starting Gift Redemption button test...")
    #         self.setup_test_user(register_new=False)
    #         self.navigate_to_profile_page(self.language)

    #         gift_redemption_text = self.wait_for_element(By.CSS_SELECTOR, "p[id='profile-menu-gift_change']").text
    #         self.logger.info(f"Gift Redemption text: {gift_redemption_text}")
            
    #         expected_gift_redemption_text = LANGUAGE_SETTINGS[self.language]['profile']['gift_redemption']
            
    #         self.assertEqual(gift_redemption_text, expected_gift_redemption_text, "Gift Redemption text not displayed as expected. \nFound: {gift_redemption_text} \nExpected: {expected_gift_redemption_text}")
            
    #         gift_redemption_button = self.wait_for_element(By.CSS_SELECTOR, "a[id='profile-menu-gift_change']")
            
    #         current_url = self.driver.current_url
    #         # get base url by using urlparse
    #         base_url = urlparse(current_url).netloc
    #         protocol = urlparse(current_url).scheme
            
            
    #         # click right side of the button
    #         self.scroll_element_to_center(gift_redemption_button)
    #         self.action.move_to_element(gift_redemption_button).click().perform()
                        
    #         # wait for the redirected url
    #         WebDriverWait(self.driver, 45).until(
    #             EC.url_to_be(f"{protocol}://{base_url}/{self.language}/profile/gift_redemption")
    #         )

    #         self.logger.info("Gift Redemption button test passed")

    #     except Exception as e:
    #         self.fail(f"Test failed: {str(e)}")
    
    # def test_15_LiveAgentButton(self):
    #     try:
    #         self.logger.info("Starting Live Agent button test...")
    #         self.setup_test_user(register_new=False)
    #         self.navigate_to_profile_page(self.language)

    #         live_agent_text = self.wait_for_element(By.CSS_SELECTOR, "p[id='profile-menu-cs']").text
    #         self.logger.info(f"Live Agent text: {live_agent_text}")
            
    #         expected_live_agent_text = LANGUAGE_SETTINGS[self.language]['profile']['live_agent']
            
    #         self.assertEqual(live_agent_text, expected_live_agent_text, "Live Agent text not displayed as expected. \nFound: {live_agent_text} \nExpected: {expected_live_agent_text}")
            
    #         live_agent_button = self.wait_for_element(By.CSS_SELECTOR, "a[id='profile-menu-cs']")
            
    #         current_url = self.driver.current_url
    #         # get base url by using urlparse
    #         base_url = urlparse(current_url).netloc
    #         protocol = urlparse(current_url).scheme
            
            
    #         # click right side of the button
    #         self.scroll_element_to_center(live_agent_button)
    #         self.action.move_to_element(live_agent_button).click().perform()
                        
    #         # wait for the redirected url
    #         WebDriverWait(self.driver, 45).until(
    #             EC.url_to_be(LIVE_AGENT_URL['profile_whatsapp_url'])
    #         )

    #         self.logger.info("Gift Redemption button test passed")

    #     except Exception as e:
    #         self.fail(f"Test failed: {str(e)}")
            
if __name__ == "__main__":
    unittest.main()
