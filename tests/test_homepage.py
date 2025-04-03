import datetime
import unittest
import time
import logging
import random
import requests
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from config.constant import CREDENTIALS, LANGUAGE_SETTINGS
from tests.authentication_test.base_test import BaseTest
from tests.test_init import TestInit
from selenium.webdriver.firefox.options import Options
from selenium.webdriver import Firefox
from selenium.webdriver import Chrome
from selenium import webdriver
import json
import urllib.parse
from selenium.webdriver.common.action_chains import ActionChains

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
    
class TestHomepage(BaseTest):

    def __init__(self, methodName="runTest", language=None, browser=None):
        super().__init__(methodName, language, browser)
        self.test_init = TestInit(methodName="runTest", language=language, browser=browser)

    def setUp(self):
        if not self.browser or not self.language:
            raise ValueError("Browser or language is not set.")
        self.logger.info(f"Setting up {self.browser} browser for {self.language} language...")
        self.driver = self.initialize_browser(self.browser)
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
    
    def check_img_response(self, img_url):
        """Check if image URL is valid"""
        response = requests.get(img_url)
        response.raise_for_status()
        return True
    
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
            actual_image_url = urllib.parse.unquote(encoded_url)
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
    
    def verify_navigation(self, expected_endpoint):
        # Wait for redirection and verify URL, make sure base url is correct
        current_url = self.driver.current_url
        # get base url by using urlparse
        base_url = urllib.parse.urlparse(current_url).netloc
        protocol = urllib.parse.urlparse(current_url).scheme
        
        expected_url_part = f"{protocol}://{base_url}/{expected_endpoint}"
        
        self.logger.info(f"Expected URL: {expected_url_part}")
        
        WebDriverWait(self.driver, 15).until(
            lambda driver: expected_url_part in driver.current_url
        )
        
        self.assertEqual(expected_url_part, self.driver.current_url,
                    f"Navigation to {expected_endpoint} failed. \nFound: {self.driver.current_url} \nExpected: {expected_url_part}")
        
    def test_01_TopBarInfo(self):
        try:
            self.logger.info("Starting top bar info test...")
            self.setup_test_user(register_new=True)
            self.navigate_to_home_and_handle_popups()
            
            user_data = HomepageData.user_api(self, self.username, self.password)
            self.logger.info(f"User data: {user_data}")
            
            # find avatar by img alt
            avatar_element = self.wait_for_element(By.XPATH, f"//img[@alt='profile_avatar']")
            avatar_src = avatar_element.get_attribute("src")
            
            expected_avatar = user_data['avatar']
            
            # Use the new general-purpose image comparison function
            self.compare_image_urls(avatar_src, expected_avatar, image_type="Avatar")

            user_id = self.wait_for_element(By.ID, f"user-profile-id").text.split(": ")[1].strip()
            self.logger.info(f"User ID: {user_id}")
            
            expected_user_id = user_data['id']
            self.assertEqual(str(user_id), str(expected_user_id), f"User ID mismatch. \nFound: {user_id} \nExpected: {expected_user_id}")

            language = self.wait_for_element(By.ID, f"language-selector-dropdown").text.lower()
            self.assertEqual(language, self.language, f"Language mismatch. \nFound: {language} \nExpected: {self.language}")
            
            # check if language image is displayed
            language_img = self.wait_for_element(By.XPATH, f"//img[@alt='{language}-icon']")
            self.assertTrue(language_img.is_displayed(), f"Language image is not displayed for {language} language")

            self.logger.info("Top bar info test passed")

        except Exception as e:
            self.fail(f"Test failed: {str(e)}")
    
    def test_02_ActionElement(self):
        try:

            action = ActionChains(self.driver)  
            
            self.logger.info("Starting action element test...")
            self.setup_test_user(register_new=True)
    
            self.make_deposit(888.88)
            self.navigate_to_home_and_handle_popups()
            
            user_data = HomepageData.user_api(self, self.username, self.password)
            self.logger.info(f"User data: {user_data}")
            
            # wallet balance
            wallet_element = self.wait_for_element(By.ID, f"home-wallet-balance")
            self.logger.info(f"Wallet balance: {wallet_element.text}")
            
            expected_wallet_balance = user_data['total_balance']
            expected_wallet_text = LANGUAGE_SETTINGS[self.language]["home_page"]["wallet_balance"].format(balance=expected_wallet_balance)
            self.assertEqual(wallet_element.text, expected_wallet_text, f"Wallet balance mismatch. \nFound: {wallet_element.text} \nExpected: {expected_wallet_text}")

            coin_icon = self.wait_for_element(By.XPATH, f"//img[@alt='coin_icon']")
            self.assertTrue(coin_icon.is_displayed(), f"Coin icon is not displayed")
            
            self.make_deposit(100)

            parent_div = wallet_element.find_element(By.XPATH, "./..")
            
            # Find the refresh button within the parent div
            refresh_button = parent_div.find_element(By.XPATH, ".//button")
            
            # Click the refresh button
            self.logger.info("Clicking wallet balance refresh button")
            action.move_to_element(refresh_button).click().perform()
            
            # Wait for balance to refresh
            time.sleep(8)
            
            # Verify balance updated
            updated_wallet_balance = self.wait_for_element(By.ID, "home-wallet-balance").text
            self.logger.info(f"Updated wallet balance: {updated_wallet_balance}")
            
            expected_wallet_balance = float(user_data['total_balance']) + 100
            expected_wallet_text = LANGUAGE_SETTINGS[self.language]["home_page"]["wallet_balance"].format(balance=expected_wallet_balance)
            self.assertEqual(updated_wallet_balance, expected_wallet_text, f"Wallet balance mismatch. \nFound: {updated_wallet_balance} \nExpected: {expected_wallet_text}")

        except Exception as e:
            self.fail(f"Test failed: {str(e)}")

    def test_03_NavigateToHistory(self):
        try:
            
            
            self.logger.info("Starting navigate to history test...")
            self.setup_test_user(register_new=True)
            self.navigate_to_home_and_handle_popups()
            
            # Wait for redirection and verify URL, make sure base url is correct
            current_url = self.driver.current_url
            # get base url by using urlparse
            base_url = urllib.parse.urlparse(current_url).netloc
            protocol = urllib.parse.urlparse(current_url).scheme
            
            history_button = self.wait_for_element(By.ID, "home-history-button")
            self.assertTrue(history_button.is_displayed(), f"History button is not displayed")
            
            # scroll to make the button at center of the page
            self.scroll_element_to_center(history_button)
            self.action.move_to_element(history_button).click().perform()
            
            time.sleep(5)
            redirected_url = self.driver.current_url
            
            expected_history_button_href = f"{protocol}://{base_url}/{self.language}/wallet/history"
            self.assertIn(expected_history_button_href, redirected_url, f"History button href mismatch. \nFound: {redirected_url} \nExpected: {expected_history_button_href}")
  
            self.logger.info("Navigate to history test passed")
            
        except Exception as e:
            self.fail(f"Test failed: {str(e)}")
            
    def test_04_ActionTabs(self):
        try:
            self.logger.info("Starting action tabs test...")
            self.setup_test_user(register_new=True)
            
            # Wait for redirection and verify URL, make sure base url is correct
            current_url = self.driver.current_url
            # get base url by using urlparse
            base_url = urllib.parse.urlparse(current_url).netloc
            protocol = urllib.parse.urlparse(current_url).scheme
        
            # deposit button
            deposit_button = self.wait_for_element(By.ID, "home-deposit-button")
            self.assertTrue(deposit_button.is_displayed(), f"Deposit button is not displayed")
            
            expected_deposit_button_text = LANGUAGE_SETTINGS[self.language]["home_page"]["deposit"]
            self.assertEqual(deposit_button.text, expected_deposit_button_text, f"Deposit button text mismatch. \nFound: {deposit_button.text} \nExpected: {expected_deposit_button_text}")
            
            deposit_button_href = deposit_button.get_attribute("href")
            expected_deposit_button_href = f"{protocol}://{base_url}/{self.language}/wallet/deposit"
            self.assertEqual(deposit_button_href, expected_deposit_button_href, f"Deposit button href mismatch. \nFound: {deposit_button_href} \nExpected: {expected_deposit_button_href}")
            
            # withdraw button
            withdraw_button = self.wait_for_element(By.ID, "home-withdrawal-button")
            self.assertTrue(withdraw_button.is_displayed(), f"Withdraw button is not displayed")
            
            expected_withdraw_button_text = LANGUAGE_SETTINGS[self.language]["home_page"]["withdraw"]
            self.assertEqual(withdraw_button.text, expected_withdraw_button_text, f"Withdraw button text mismatch. \nFound: {withdraw_button.text} \nExpected: {expected_withdraw_button_text}")
            
            withdraw_button_href = withdraw_button.get_attribute("href")
            expected_withdraw_button_href = f"{protocol}://{base_url}/{self.language}/wallet/withdrawal"
            self.assertEqual(withdraw_button_href, expected_withdraw_button_href, f"Withdraw button href mismatch. \nFound: {withdraw_button_href} \nExpected: {expected_withdraw_button_href}")
            
            transfer_button = self.wait_for_element(By.ID, "home-transfer-button")
            self.assertTrue(transfer_button.is_displayed(), f"Transfer button is not displayed")
            
            expected_transfer_button_text = LANGUAGE_SETTINGS[self.language]["home_page"]["transfer"]
            self.assertEqual(transfer_button.text, expected_transfer_button_text, f"Transfer button text mismatch. \nFound: {transfer_button.text} \nExpected: {expected_transfer_button_text}")
            
            transfer_button_href = transfer_button.get_attribute("href")
            expected_transfer_button_href = f"{protocol}://{base_url}/{self.language}/wallet/transfer"
            self.assertEqual(transfer_button_href, expected_transfer_button_href, f"Transfer button href mismatch. \nFound: {transfer_button_href} \nExpected: {expected_transfer_button_href}")
            
            rebate_button = self.wait_for_element(By.ID, "home-rebate-button")
            self.assertTrue(rebate_button.is_displayed(), f"Rebate button is not displayed")
            
            expected_rebate_button_text = LANGUAGE_SETTINGS[self.language]["home_page"]["rebate"]
            self.assertEqual(rebate_button.text, expected_rebate_button_text, f"Rebate button text mismatch. \nFound: {rebate_button.text} \nExpected: {expected_rebate_button_text}")
            
            rebate_button_href = rebate_button.get_attribute("href")
            expected_rebate_button_href = f"{protocol}://{base_url}/{self.language}/wallet/rebate"
            self.assertEqual(rebate_button_href, expected_rebate_button_href, f"Rebate button href mismatch. \nFound: {rebate_button_href} \nExpected: {expected_rebate_button_href}")
            
            self.logger.info("Action tabs test passed")
            
        except Exception as e:
            self.fail(f"Test failed: {str(e)}")
            
    def test_05_RecentGame(self):
        try:
            self.logger.info("Starting recent game test...")
            self.setup_test_user(register_new=True)
            
            home_data = HomepageData.home_api(self, self.username, self.password)
            self.logger.info(f"Home data: {home_data}")
                        
            recent_img = self.wait_for_element(By.XPATH, f"//img[@alt='newbie-image']")
            recent_img_src = recent_img.get_attribute("src")
            self.logger.info(f"Recent image src: {recent_img_src}")
            
            self.assertIn("Newbie", recent_img_src, f"Recent image src does not contain 'Newbie'")
            
            # recent game balance
            recent_balance = self.wait_for_element(By.ID, "recent-activity-balance").text
            self.logger.info(f"Recent balance: {recent_balance}")
            
            expected_recent_balance = LANGUAGE_SETTINGS[self.language]["home_page"]["game_balance"].format(balance=0)
            
            self.assertEqual(recent_balance, expected_recent_balance, f"Recent balance is not {expected_recent_balance}")
            
            # check if click the button will create new tab
            recent_game_button = self.wait_for_element(By.ID, "start-game-button")
            self.assertTrue(recent_game_button.is_displayed(), f"Recent game button is not displayed")
            
            button_text = recent_game_button.text
            expected_button_text = LANGUAGE_SETTINGS[self.language]["home_page"]["claim_play_now"]
            
            self.assertEqual(button_text, expected_button_text, f"Button text mismatch. \nFound: {button_text} \nExpected: {expected_button_text}")
            
            # check if redirected to deposit page
            # Wait for redirection and verify URL, make sure base url is correct
            current_url = self.driver.current_url
            # get base url by using urlparse
            base_url = urllib.parse.urlparse(current_url).netloc
            protocol = urllib.parse.urlparse(current_url).scheme
            
            expected_url_part = f"{protocol}://{base_url}/{self.language}/wallet/deposit"
            
            self.logger.info(f"Expected URL: {expected_url_part}")
            
            self.scroll_element_to_center(recent_game_button)
            
            self.action.move_to_element_with_offset(recent_game_button, 50, 0).click().perform()
            
            WebDriverWait(self.driver, 30).until(
                lambda driver: expected_url_part in driver.current_url
            )
            
            self.assertIn(expected_url_part, self.driver.current_url,
                        f"Navigation failed. \nFound: {self.driver.current_url} \nExpected: {expected_url_part}")
            
            # LOGOUT
            
            self.navigate_to_setting_page(self.language)
            logout_button = self.wait_for_element(By.ID, "logout-list-item")
            self.action.move_to_element(logout_button).click().perform()
            time.sleep(5)
            
            self.navigate_to_home_and_handle_popups()
            self.setup_test_user(register_new=False)
            
            home_data = HomepageData.home_api(self, self.username, self.password)
            self.logger.info(f"Home data: {home_data}")
                        
            recent_img = self.wait_for_element(By.XPATH, f"//img[@alt='newbie-image']")
            recent_img_src = recent_img.get_attribute("src")
            
            expected_recent_img_src = home_data['free_section_game']['logo']
            self.compare_image_urls(recent_img_src, expected_recent_img_src, image_type="Recent Game Image")  
            
            # recent game balance
            recent_balance = self.wait_for_element(By.ID, "recent-activity-balance").text
            self.logger.info(f"Recent balance: {recent_balance}")
            
            # if .00 then int else format to 2 decimal places
            expected_recent_balance = int(float(home_data['game_balance'])) if home_data['game_balance'].endswith('.00') else format(round(float(home_data['game_balance']), 2), '.2f')
            expected_recent_balance = LANGUAGE_SETTINGS[self.language]["home_page"]["game_balance"].format(balance=expected_recent_balance)
            self.assertEqual(recent_balance, expected_recent_balance, f"Recent balance is not {expected_recent_balance}")
            
            # check if click the button will create new tab
            recent_game_button = self.wait_for_element(By.ID, "start-game-button", 30)
            self.assertTrue(recent_game_button.is_displayed(), f"Recent game button is not displayed")
            
            button_text = recent_game_button.text
            expected_button_text = LANGUAGE_SETTINGS[self.language]["home_page"]["claim_play_now"]
            
            self.assertEqual(button_text, expected_button_text, f"Button text mismatch. \nFound: {button_text} \nExpected: {expected_button_text}")
            
            self.scroll_element_to_center(recent_game_button)
            self.action.move_to_element_with_offset(recent_game_button, 50, 0).click().perform()
            
            # check if new tab is created
            self.assertEqual(len(self.driver.window_handles), 2, f"New tab is not created")
            
            # close the new tab
            self.driver.switch_to.window(self.driver.window_handles[0])
            
            self.logger.info("Recent game test passed")
            
        except Exception as e:
            self.fail(f"Test failed: {str(e)}")
    
    def test_06_Reward(self):
        try:
            self.logger.info("Starting reward test...")
            self.setup_test_user(register_new=True)
            
            # Wait for redirection and verify URL, make sure base url is correct
            current_url = self.driver.current_url
            # get base url by using urlparse
            base_url = urllib.parse.urlparse(current_url).netloc
            protocol = urllib.parse.urlparse(current_url).scheme
            
            reward_button = self.wait_for_element(By.ID, "reward-button")
            self.assertTrue(reward_button.is_displayed(), f"Reward button is not displayed")
            
            self.action.move_to_element(reward_button).click().perform()
            
            time.sleep(5)
            redirected_url = self.driver.current_url
            expected_reward_button_href = f"{protocol}://{base_url}/{self.language}/profile/reward"
            self.assertIn(expected_reward_button_href, redirected_url, f"Reward button href mismatch. \nFound: {redirected_url} \nExpected: {expected_reward_button_href}")
            
            self.logger.info("Reward test passed")
        except Exception as e:
            self.fail(f"Test failed: {str(e)}")
    
    def test_07_4D(self):
        try:
            self.logger.info("Starting reward test...")
            self.setup_test_user(register_new=True)
            
            date_element = self.wait_for_element(By.ID, "DynamicBuyInDate").text.replace(" ", "")
            expected_date_element = LANGUAGE_SETTINGS[self.language]["home_page"]["buy_in_date"].format(date=datetime.datetime.now().strftime("%d/%m/%Y")).replace(" ", "")
            self.assertEqual(date_element, expected_date_element, f"Date element text mismatch. \nFound: {date_element} \nExpected: {expected_date_element}")
            
            four_d_button = self.wait_for_element(By.ID, "grand-dragon-button")
            self.assertTrue(four_d_button.is_displayed(), f"4D button is not displayed")
            self.action.move_to_element(four_d_button).click().perform()
            
            four_d_element =  self.wait_for_element(By.ID, "numberLottCard")
            self.assertTrue(four_d_element.is_displayed(), f"4D element is not displayed")
            
            self.logger.info("4D test passed")

        except Exception as e:
            self.fail(f"Test failed: {str(e)}")
    
    def test_08_Livepage(self):
        try:
            self.logger.info("Starting live page test...")
            self.setup_test_user(register_new=True)
            
            # Wait for redirection and verify URL, make sure base url is correct
            current_url = self.driver.current_url
            # get base url by using urlparse
            base_url = urllib.parse.urlparse(current_url).netloc
            protocol = urllib.parse.urlparse(current_url).scheme
            
            live_button = self.wait_for_element(By.ID, "lucky-girl-button")
            self.assertTrue(live_button.is_displayed(), f"Live button is not displayed")
            
            # scroll to make the button at center of the page
            self.scroll_element_to_center(live_button)
            self.action.move_to_element(live_button).click().perform()
            
            time.sleep(5)
            redirected_url = self.driver.current_url
            
            expected_live_button_href = f"{protocol}://{base_url}/{self.language}/bobolive"
            self.assertIn(expected_live_button_href, redirected_url, f"Live button href mismatch. \nFound: {redirected_url} \nExpected: {expected_live_button_href}")
            
            self.logger.info("Live page test passed")

        except Exception as e:
            self.fail(f"Test failed: {str(e)}")
    
    def test_09_Promotion(self):
        try:
            self.logger.info("Starting promotion test...")
            self.setup_test_user(register_new=True)
            
            # Wait for redirection and verify URL, make sure base url is correct
            current_url = self.driver.current_url
            # get base url by using urlparse
            base_url = urllib.parse.urlparse(current_url).netloc
            protocol = urllib.parse.urlparse(current_url).scheme
            
            promotion_button = self.wait_for_element(By.ID, "promotions-button")
            self.assertTrue(promotion_button.is_displayed(), f"Promotion button is not displayed")
            
            # scroll to make the button at center of the page
            self.scroll_element_to_center(promotion_button)
            self.action.move_to_element(promotion_button).click().perform()
            
            time.sleep(5)
            redirected_url = self.driver.current_url
            
            expected_promotion_button_href = f"{protocol}://{base_url}/{self.language}/promotions"
            self.assertIn(expected_promotion_button_href, redirected_url, f"Promotion button href mismatch. \nFound: {redirected_url} \nExpected: {expected_promotion_button_href}")
            
            self.logger.info("Promotion test passed")

        except Exception as e:
            self.fail(f"Test failed: {str(e)}")
    
    def test_10_MayLike(self):
        try:
            self.logger.info("Starting may like test...")
            self.setup_test_user(register_new=True)
            
            may_like_element = self.wait_for_element(By.CSS_SELECTOR, "div.mui-theme-1k6gy3d")
            self.assertTrue(may_like_element.is_displayed(), f"May like element is not displayed")
            
            self.scroll_element_to_center(may_like_element)
            
            home_data = HomepageData.home_api(self, self.username, self.password)
            
            guess_games = home_data['guess_you_like_games']
            
            for game in guess_games:
                game_element_id = f"game-slide-{game['id']}"
                game_element = self.driver.find_element(By.ID, game_element_id)
                self.scroll_element_to_center(game_element)
                self.assertTrue(game_element.is_displayed(), f"{game['id']} button is not displayed")
                
                game_img_element = self.wait_for_element(By.ID, f"game-logo-{game['id']}")
                game_img_src = game_img_element.get_attribute("src")
                
                expected_game_img_src = game['logo']
                
                self.compare_image_urls(game_img_src, expected_game_img_src, image_type="Game Image")
                
                game_name_element = self.wait_for_element(By.ID, f"game-name-{game['id']}")
                game_name = game_name_element.get_attribute("title")
                
                expected_game_name = game['name']
                
                self.assertEqual(game_name, expected_game_name, f"Game name mismatch. \nFound: {game_name} \nExpected: {expected_game_name}")

            self.logger.info("May like test passed")
            
        except Exception as e:
            self.fail(f"Test failed: {str(e)}")
        
    def test_11_HotGames(self):
        try:
            self.logger.info("Starting hot games test...")
            self.setup_test_user(register_new=True)
            
            provider_data = HomepageData.provider_api(self, self.username, self.password)
            
            categories = set(provider['category'] for provider in provider_data)
            
            for category in categories:
                self.logger.info(f"Testing category: {category}")
                
                if category == "4d":
                    tab_element = self.wait_for_element(By.ID, f"hot-games-tab-{category.upper()}")
                else:
                    tab_element = self.wait_for_element(By.ID, f"hot-games-tab-{category}")
                
                self.scroll_element_to_center(tab_element)
                
                self.action.move_to_element(tab_element).click().perform()
                
                time.sleep(5)
                
                # get all category games from provider_data
                category_games = [game for game in provider_data if game['category'] == category and game['is_maintenance'] == 0]
                
                games_elements = self.driver.find_elements(By.CSS_SELECTOR, "[id^='link-'],[id^='card-'],[id^='game-image-']")
                
                self.assertEqual(len(games_elements), len(category_games), f"Number of games mismatch. \nFound: {len(games_elements)} \nExpected: {len(category_games)}")
                
                for game in category_games:
                    self.logger.info(f"Testing game: {game['name']}")
                    
                    game_element = self.wait_for_element(By.CSS_SELECTOR, f"[id^='link-{game['id']}'],[id^='card-{game['id']}'],[id^='game-image-{game['id']}']")
                    
                    self.assertTrue(game_element.is_displayed(), f"{game['name']} button is not displayed")
                    
                    self.logger.info(f"Game element: {game_element.tag_name}")
                    # game logo that img inside the game_element
                    if game_element.tag_name.lower() == "img" or game_element.tag_name.lower() == "svg":
                        game_img_element = game_element
                    else:
                        game_img_element = game_element.find_element(By.CSS_SELECTOR, "img,svg")
                    
                    game_img_src = game_img_element.get_attribute("src")
                    
                    expected_game_img_src = game['img']
                    
                    self.compare_image_urls(game_img_src, expected_game_img_src, image_type="Game Image")
                    
                    if game_element.tag_name.lower() == "img" or game_element.tag_name.lower() == "svg":
                        game_name_element = self.wait_for_element(By.ID, f"game-name-{game['id']}")
                    else:
                        game_name_element = game_element.find_element(By.CSS_SELECTOR, "p")
                    
                    game_name = game_name_element.text
                    
                    expected_game_name = game['name']
                    
                    self.assertEqual(game_name, expected_game_name, f"Game name mismatch. \nFound: {game_name} \nExpected: {expected_game_name}")
                    
                    self.logger.info(f"Game: {game['name']} test passed")
                
                self.logger.info(f"Category: {category} test passed")
                
            self.logger.info("Hot games test passed")
            
        except Exception as e:
            self.fail(f"Test failed: {str(e)}")
                
    def test_12_SearchGame(self):
        try:
            self.logger.info("Starting search game test...")
            self.setup_test_user(register_new=True)
            
            search_input = self.wait_for_element(By.ID, "hot-games-search")
            
            keyword = "play"
            
            # use action to click and input "play"
            self.scroll_element_to_center(search_input)
            self.action.move_to_element(search_input).click().perform()
            # use action to input "play"
            self.action.send_keys(keyword).perform()
            
            time.sleep(5)
            
            provider_data = HomepageData.provider_api(self, self.username, self.password)
            
            categories = set(provider['category'] for provider in provider_data)
            
            for category in categories:
                self.logger.info(f"Testing category: {category}")
                
                if category == "4d":
                    tab_element = self.wait_for_element(By.ID, f"hot-games-tab-{category.upper()}")
                else:
                    tab_element = self.wait_for_element(By.ID, f"hot-games-tab-{category}")
                
                self.scroll_element_to_center(tab_element)
                
                self.action.move_to_element(tab_element).click().perform()
                
                time.sleep(5)
                
                # get all category games from provider_data
                category_games = [game for game in provider_data if game['category'] == category and game['is_maintenance'] == 0 and keyword.lower() in game['name'].lower()]
                
                games_elements = self.driver.find_elements(By.CSS_SELECTOR, "[id^='link-'],[id^='card-'],[id^='game-image-']")
                
                self.assertEqual(len(games_elements), len(category_games), f"Number of games mismatch. \nFound: {len(games_elements)} \nExpected: {len(category_games)}")
                
                if len(category_games) == 0:
                    # find if there is there is no_search_result_1 or no_search_result_2 in the page by using text
                    expected_no_search_result_1 = LANGUAGE_SETTINGS[self.language]["home_page"]["no_search_result_1"]
                    expected_no_search_result_2 = LANGUAGE_SETTINGS[self.language]["home_page"]["no_search_result_2"]
                    
                    no_search_result_1_elements = self.driver.find_elements(By.XPATH, f"//p[contains(text(), '{expected_no_search_result_1}')]")
                    no_search_result_2_elements = self.driver.find_elements(By.XPATH, f"//div[contains(text(), '{expected_no_search_result_2}')]")
                    
                    self.assertTrue(len(no_search_result_1_elements) > 0 or len(no_search_result_2_elements) > 0, f"No search result is not displayed")
                
                else:
                    for game in category_games:
                        self.logger.info(f"Testing game: {game['name']}")
                        
                        self.wait_for_element(By.CSS_SELECTOR, f"[id^='link-{game['id']}'],[id^='card-{game['id']}'],[id^='game-image-{game['id']}']")
                        
                        self.logger.info(f"Game: {game['name']} test passed")
                
                self.logger.info(f"Category: {category} test passed")
                            
            self.logger.info("Search game test passed")
            
        except Exception as e:
            self.fail(f"Test failed: {str(e)}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    unittest.main()
