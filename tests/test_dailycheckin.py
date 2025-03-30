import os
import unittest
import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from config.constant import LANGUAGE_SETTINGS, CREDENTIALS, API_URL
from tests.authentication_test.base_test import BaseTest
import time
import requests

class RewardClass():
    def __init__(self, token, language):
        self.token = token
        self.language = language
        self.api_url = API_URL
        self.current_day_reward = None
    
    def get_rewards(self):
        headers = {
            "Authorization": f"Bearer {self.token}",
            "language": self.language
        }
        response = requests.get(f"{self.api_url}/api/reward", headers=headers)
        response.raise_for_status()
        current_week_reward = response.json().get("data")
        current_day_reward = self.get_current_day_reward(current_week_reward)
        return current_week_reward, current_day_reward
    
    def get_current_day_reward(self, rewards):
        for r in rewards:
            user_consecutive_days = r["user_consecutive_days"] + 1
            reward_consecutive_days = r['reward']['consecutive_days']
            if user_consecutive_days == reward_consecutive_days:
                self.current_day_reward = r
                return r
        return None
    
    
    def get_reward_type(self, reward_id):
        try:
            response = requests.get(f"{self.api_url}/api/rewards/{reward_id}")
            response.raise_for_status()
            result = response.json().get("data")
            if not result or 'reward_type' not in result:
                raise ValueError("Invalid reward data returned from API.")
            return result['reward_type']
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching reward type: {e}")
            return None

    def create_reward_dict(self):
        try:
            
            reward_dict = {}
            if self.current_day_reward['reward']['reward_id'] != 0:
                reward_type = self.get_reward_type(self.current_day_reward['reward']['reward_id'])
                if reward_type is not None:
                    reward_dict[reward_type] = float(self.current_day_reward['reward']['reward_value'])

            if self.current_day_reward['is_special']:
                special_reward_type = self.get_reward_type(self.current_day_reward['reward']['special_reward_id'])
                if special_reward_type in reward_dict:
                    reward_dict[special_reward_type] += float(self.current_day_reward['reward']['special_reward_value'])
                else:
                    reward_dict[special_reward_type] = float(self.current_day_reward['reward']['special_reward_value'])

            return reward_dict
        except Exception as e:
            self.logger.error(f"Error creating reward dictionary: {e}")
            return None
    
    def get_vip_id(self):
        return self.current_day_reward.get("reward").get("user_vip_id") if self.current_day_reward else None

class TestDailyCheckIn(BaseTest):

    def __init__(self, methodName="runTest", language=None, browser=None):
        super().__init__(methodName)
        self.language = language
        self.browser = browser
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

        file_handler = logging.FileHandler("test_daily_checkin.log")
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
        #self.driver.maximize_window()
        self.driver.set_window_size(375, 812)

    def tearDown(self):
        if hasattr(self, "driver"):
            self.driver.quit()
            
    def navigate_to_check_in_page(self):
        driver = self.driver
        
        # Wait for and find the mini tiger element
        mini_tiger_div = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "mui-theme-164q5tj"))
        )
        
        # Click the div containing the mini tiger
        mini_tiger_div.click()
        
        checkin_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'a[href="daily_check_in"]'))
        )
        checkin_button.click()
        
    def createAccount(self):
        driver = self.driver
        
        try:
            self.navigate_to_register_page()
            # Generate unique username using timestamp
            current_time = int(str(int(time.time()))[:9])
            self.register_acc = f"Tt{current_time}"
            self.logger.info(f"Registring Acc: {self.register_acc}")
            
            # Fill in registration form
            input_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "register-login-id"))
            )
            input_element.send_keys(self.register_acc)
            input_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "register-password"))
            )
            input_element.send_keys(self.register_acc)
            input_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "register-confirm-password"))
            )
            input_element.send_keys(self.register_acc)
            input_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "register-full-name"))
            )
            input_element.send_keys(self.register_acc)
            input_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "register-phone-number"))
            )
            input_element.send_keys(current_time)
            
            # Submit registration
            register_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "register-submit-button"))
            )
            register_button.click()
            
            time.sleep(2)
            
            # Verify registration success
            success_title = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "swal2-title"))
            )
            text = LANGUAGE_SETTINGS[self.language]['success']['register_success']
            is_success = success_title.text == text
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
    
    def checkIn_popup(self):
        self.logger.info("Checking if daily check-in popup is displayed")
        popup_modal = WebDriverWait(self.driver, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "div[role='presentation'][aria-labelledby='transition-modal-title']"))
        )
        self.assertTrue(popup_modal.is_displayed(), "Check in popup is not displayed")
    
    def verify_checkin_days(self):
        self.logger.info("Verifying check-in days count")
        
        text = LANGUAGE_SETTINGS[self.language]['check_in']['checked_in_days']
        days_text = WebDriverWait(self.driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, f"//p[contains(text(), '{text}')]//span"))
        )
        
        displayed_day = days_text.text
        self.logger.info(f"Current check-in days: {displayed_day}")
        
        self.assertTrue(displayed_day.isdigit(), "Check-in days number is not displayed correctly")
        
        return int(displayed_day)
    
    def checkin_box(self, expected_message):
        checked_in_icon = WebDriverWait(self.driver,
                                   5).until(EC.visibility_of_element_located((By.ID, "checked-in-close-button")))
        self.assertTrue(checked_in_icon.is_displayed(), "Checked in message is not displayed")

        checkedInMessage = self.driver.find_element(By.CSS_SELECTOR, "p.mui-theme-67atcp")
        
        self.assertIn(
            expected_message, checkedInMessage.text,
            f"Popup message does not contain the expected text: {expected_message}"
        )

    def verify_checkin_button_status(self):
        self.logger.info("Verifying check-in button functionality")
        checkin_button = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "check-in-button"))
        )
        
        self.logger.info("Clicking check-in button")
        checkin_button.click()
        
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#check-in-button[disabled]"))
        )
        
        self.assertTrue(checkin_button.get_attribute("disabled"), "Check-in button is not disabled after clicking")
        
    
    def get_bbcoins(self):
        self.logger.info("Getting BB Coins amount")
        live_button = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.ID, "footer-live-button"))
        )
        
        self.logger.info("Clicking Live button")
        live_button.click()
        time.sleep(1)
        
        coin_element = WebDriverWait(self.driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, "//div[contains(@class, 'MuiChip-root')]//img[@alt='bbtv_coin']/following-sibling::span"))
        )
        
        coins_amount = coin_element.text.replace(",","").strip()
        self.logger.info(f"Current BB Coins amount: {coins_amount}")
        
        self.assertTrue(coins_amount.isdigit(), "Coins amount is not a number")
        
        self.driver.back()
        time.sleep(1)
        return int(coins_amount)

    def get_4d_cards_amount(self):
        self.logger.info("Getting 4D Cards amount")
        
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
        time.sleep(1)
        
       # Wait for 4D Cards text element
        self.logger.info("Getting 4D Cards text")
        cards_element = WebDriverWait(self.driver, 10).until(
            EC.visibility_of_element_located((By.ID, "totalCardNumberText"))
        )
        
        # Extract number from text
        cards_text = cards_element.text
        separator = LANGUAGE_SETTINGS[self.language]["check_in"][":"]
        cards_amount = cards_text.split(f"{separator}")[1].replace(",","").strip()  # Split "4D Cards: 2" to get number
        self.logger.info(f"Current 4D Cards amount: {cards_amount}")
        
        self.assertTrue(cards_amount.isdigit(), "4D Cards amount is not a number")
        
        return int(cards_amount)
    
    def get_wallet_balance(self):
        self.logger.info("Getting wallet balance")
        
        # Wait for wallet balance element
        balance_element = WebDriverWait(self.driver, 10).until(
            EC.visibility_of_element_located((By.ID, "home-wallet-balance"))
        )
        
        # Get balance text and remove "RM" and spaces
        balance_text = balance_element.text.replace("RM", "").replace(",","").strip()
        self.logger.info(f"Original balance text: {balance_text}")
        
        try:
            # Convert to float
            balance = round(float(balance_text), 2)
            self.logger.info(f"Converted balance amount: {balance}")
            return balance
            
        except ValueError:
            self.logger.error(f"Failed to convert balance text to number: {balance_text}")
            raise
    
    def verify_rewards(self, reward_type, reward_before, reward_after, reward):
        self.logger.info(f"Verifying {reward_type} rewards")
        
        # Get 1 free 4d cards every day
        if reward_type == "ticket":
            expected_increase = 1
        else:
            expected_increase = 0
        
        if reward and reward_type in reward:
            expected_increase += reward[reward_type]
        
        self.logger.info(f"Total expected increase: {expected_increase}")
        self.logger.info(f"Actual increase: {reward_after - reward_before}")
        
        # Verify reward increase matches expected amount
        self.assertEqual(reward_after - reward_before, expected_increase, 
                        f"{reward_type} did not increase by expected amount {expected_increase}")
    
    def click_checkin_button(self):
        self.logger.info("Clicking check-in button")
        # Wait for check-in button to be clickable
        text = LANGUAGE_SETTINGS[self.language]['check_in']['check_in_now']
        checkin_button = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, f"//button[text()='{text}']"))
        )
        
        # Scroll and click button
        self.logger.info("Scrolling to check-in button")
        self.driver.execute_script("arguments[0].scrollIntoView(true);", checkin_button)
        time.sleep(1)
        self.logger.info("Executing click")
        self.driver.execute_script("arguments[0].click();", checkin_button)
        
        # Verify button text changed to Checked In
        self.logger.info("Verifying button status change")
        text = LANGUAGE_SETTINGS[self.language]['check_in']['checked_in']
        checked_button = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.XPATH, f"//button[text()='{text}']"))
        )
        
        self.assertTrue(checked_button.is_displayed(), "Check in button did not change to 'Checked In' status")
        
    def topup(self, amount):
        driver = self.driver
        MAX_AMOUNT = 2000
        remaining_amount = int(amount)
        
        try:
            self.annoucement_close_button()
            self.daily_checkin_close_button()
            self.navigate_to_profile_page(self.language)
            # Click deposit button in profile menu
            deposit_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "profile-menu-deposit"))
            )
            deposit_button.click()
            time.sleep(1)
            while remaining_amount > 0:
                # Calculate current batch amount
                current_amount = min(MAX_AMOUNT, remaining_amount)
                self.logger.info(f"Processing batch top-up: RM{current_amount}")
                
                # Enter deposit amount
                input_element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "reload-amount-input"))
                )
                input_element.send_keys(f"{current_amount}")
                time.sleep(1)
                
                # Select payment gateway
                text = LANGUAGE_SETTINGS[self.language]['deposit']['select_payment_gateway']
                payment_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, f"//button[contains(., '{text}')]"))
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
                self.driver.execute_script("arguments[0].click();", submit_button)
                
                # Handle payment gateway and confirmation
                self.paymentGateway()
                time.sleep(1)
                self.confirm_button()
                time.sleep(1)
                # Update remaining amount
                remaining_amount -= current_amount
                self.logger.info(f"Remaining amount to top-up: RM{remaining_amount}")
            return True
        except Exception as e:
            self.logger.error(f"Top-up failed with error: {str(e)}")
            self.fail(f"Test failed: {str(e)}")
            return False
    
    def checkin_process(self, isReset=False, isCheckinPage=False, isSpecialTest=False, isVipTest=False, vip_id=None, isNoSpecialTest=False):
        # Get initial rewards amounts
        self.logger.info("Getting initial reward amounts")
        wallet_before = self.get_wallet_balance()
        cards_before = self.get_4d_cards_amount()
        bbcoins_before = self.get_bbcoins()
        
        self.annoucement_close_button()
        
        # Get current check-in day     
        if isReset:
            current_day = int(self.verify_checkin_days())
            self.assertTrue(current_day==0, "check in day not reset")
        time.sleep(1)
        
        # Get current day reward
        reward_class = RewardClass(self.token, self.language)
        _, current_day_reward = reward_class.get_rewards()
        reward_dict = reward_class.create_reward_dict()
        
        if isVipTest:
           api_vip_id = reward_class.get_vip_id()
           self.assertEqual(api_vip_id, vip_id, "Vip id not updated")
        
        if isSpecialTest:
            self.assertTrue(current_day_reward['is_special'], "No special rewards")
        
        if isNoSpecialTest:
            self.assertTrue(not current_day_reward['is_special'], "Special rewards were given on non special days")
        
        if isCheckinPage:
            self.navigate_to_check_in_page()
            self.click_checkin_button()
        else:
            self.verify_checkin_button_status()
        time.sleep(1)
        
        self.checkin_box(current_day_reward['reward']['name'])
        
        self.driver.get(self.url)
        self.annoucement_close_button()
        time.sleep(1)
        
        # Get updated rewards amounts
        self.logger.info("Getting updated reward amounts")
        wallet_after = self.get_wallet_balance()
        cards_after = self.get_4d_cards_amount()
        bbcoins_after = self.get_bbcoins()
        
        self.annoucement_close_button()
        
        # Verify rewards increased correctly
        self.logger.info(f"Verifying check-in rewards")
        self.verify_rewards("coin", bbcoins_before, bbcoins_after, reward_dict)
        self.verify_rewards("ticket", cards_before, cards_after, reward_dict)
        self.verify_rewards("bonus", wallet_before, wallet_after, reward_dict)
    
    def simulate_check_in(self, user_id, days, last_check_in_days):
        response = requests.get(f'{API_URL}/api/simulate-checkin?user_id={user_id}&days={days}&passcode=99999&last_check_in_days={last_check_in_days}')
        if response.status_code == 200:
            return True
        else:
            return False
    
    def verify_day_changed(self):
        # Get current check-in day     
        current_day_before = int(self.verify_checkin_days())
        self.logger.info(f"Current check-in day: {current_day_before}")
        time.sleep(1)
        
        self.driver.get(self.url)
        self.annoucement_close_button()
        
        # Get current check-in day     
        current_day_after = int(self.verify_checkin_days())
        self.logger.info(f"Current check-in day: {current_day_after}")
        time.sleep(1)
        
        is_reset = current_day_before == 31 and current_day_after == 0
        self.assertTrue(is_reset, "Failed to reset after day31")
    
    def get_api_token(self, username, password):
        data = {
            "username": username,
            "password": password
        }
        response = requests.post(f"{API_URL}/api/login", data=data)
        response.raise_for_status()
        result = response.json().get("data")
        self.token = result['token']
    
    
    def get_vip_levels(self):
        headers = {
            "Authorization": f"Bearer {self.token}",
        }
        response = requests.get(f"{API_URL}/api/uservip", headers=headers)
        response.raise_for_status()
        vip_levels = response.json().get("data")
        return vip_levels

        
    def test_01_BasicCheckInFlowPopup(self):
        self.logger.info("Starting basic check-in flow test via popup")
        try:
            self.navigate_to_login_page()
            self.perform_login(CREDENTIALS["valid_user"]["username"], CREDENTIALS["valid_user"]["password"])
            self.get_api_token(CREDENTIALS["valid_user"]["username"], CREDENTIALS["valid_user"]["password"])
            
            user_id = self.get_id_number()
            
            simulate_success = self.simulate_check_in(user_id, 6, 1)
            if simulate_success:
                self.driver.refresh()
                self.annoucement_close_button()
                
                # Check popup visibility
                self.checkIn_popup()
                time.sleep(1)
                
                # Close check-in popup
                self.logger.info("Closing check-in popup")
                self.daily_checkin_close_button()
                
                # start check in and verify
                self.checkin_process()
            else:
                self.fail(f"Test failed with error: failed to simulate daily check in")
        except Exception as e:
            self.fail(f"Test failed with error: {str(e)}")
    
    def test_02_BasicCheckInFlowCheckInPage(self):
        self.logger.info("Starting basic check-in flow test via check-in page")
        try:
            self.navigate_to_login_page()
            self.perform_login(CREDENTIALS["valid_user"]["username"], CREDENTIALS["valid_user"]["password"])
            self.get_api_token(CREDENTIALS["valid_user"]["username"], CREDENTIALS["valid_user"]["password"])
            
            user_id = self.get_id_number()
            
            simulate_success = self.simulate_check_in(user_id, 4, 1)
            if simulate_success:
                
                # Refresh and check popup
                self.driver.refresh()
                self.annoucement_close_button()
                self.checkIn_popup()
                time.sleep(1)
                
                # Close popup
                self.daily_checkin_close_button()
                
                # start check in and verify
                self.checkin_process(isCheckinPage=True)
            else:
                self.fail(f"Test failed with error: failed to simulate daily check in")
        except Exception as e:
            self.fail(f"Test failed with error: {str(e)}")
        

    def test_03_CheckInFromDay1toDay31(self):
        self.logger.info("Starting 31-day check-in test")
        driver = self.driver
        
        try:
            self.createAccount()
            self.get_api_token(self.register_acc, self.register_acc)
            days = range(0,31)
            
            self.annoucement_close_button()
            self.navigate_to_check_in_page()
            
            user_id = self.get_id_number()
            
            # Test check-in for each day
            for d in days:
                
                # Simulate check-in for all days except day 0
                if d != 0:
                    simulate_success = self.simulate_check_in(user_id, d, 1)
                    if not simulate_success:
                        self.fail(f"Test failed with error: failed to simulate daily check in")
                
                driver.refresh()
                
                 # Perform check-in
                self.logger.info("Performing check-in")
                self.click_checkin_button()
                
                driver.refresh()
                time.sleep(1)
            time.sleep(1)
        except Exception as e:
            self.fail(f"Test failed with error: {str(e)}")

    def test_04_SpecialRewards(self):
        self.logger.info("Starting special rewards test")
        try:
            self.navigate_to_login_page()
            self.perform_login(CREDENTIALS["valid_user"]["username"], CREDENTIALS["valid_user"]["password"])
            self.get_api_token(CREDENTIALS["valid_user"]["username"], CREDENTIALS["valid_user"]["password"])
            user_id = self.get_id_number()
            special_days = [7, 14, 21, 31]
            for d in special_days:
                simulate_success = self.simulate_check_in(user_id, d-1, 1)
                if not simulate_success:
                    self.fail(f"Test failed with error: failed to simulate daily check in")
                    
                self.driver.refresh()
                self.annoucement_close_button()
                self.checkIn_popup()
                time.sleep(1)
                
                self.daily_checkin_close_button()
                
                self.checkin_process(isSpecialTest=True)
            
        except Exception as e:
            self.fail(f"Test failed with error: {str(e)}")
    
    def test_05_Day28NoSpecialRewards(self):
        self.logger.info("Starting special rewards test")
        try:
            self.navigate_to_login_page()
            self.perform_login(CREDENTIALS["valid_user"]["username"], CREDENTIALS["valid_user"]["password"])
            self.get_api_token(CREDENTIALS["valid_user"]["username"], CREDENTIALS["valid_user"]["password"])
            user_id = self.get_id_number()
            simulate_success = self.simulate_check_in(user_id, 27, 1)
            if not simulate_success:
                self.fail(f"Test failed with error: failed to simulate daily check in")
                
            self.driver.refresh()
            self.annoucement_close_button()
            self.checkIn_popup()
            time.sleep(1)
            
            self.daily_checkin_close_button()
            
            self.checkin_process(isNoSpecialTest=True)
            
        except Exception as e:
            self.fail(f"Test failed with error: {str(e)}")
    
    def test_06_ResetAfter1DayMissed(self):
        self.logger.info("Starting rewards reset after one day are missed")
        try:
            self.navigate_to_login_page()
            self.perform_login(CREDENTIALS["valid_user"]["username"], CREDENTIALS["valid_user"]["password"])
            self.get_api_token(CREDENTIALS["valid_user"]["username"], CREDENTIALS["valid_user"]["password"])
            
            user_id = self.get_id_number()
                
            # 1 day missed
            simulate_success = self.simulate_check_in(user_id, 6, 2)
            if simulate_success:
                self.driver.get(self.url)
                                
                self.annoucement_close_button()
                
                # Check popup visibility
                self.checkIn_popup()
                time.sleep(1)
                                
                # Close check-in popup
                self.daily_checkin_close_button()
                
                # start check in and verify
                self.checkin_process(isReset=True)
            else:
                self.fail(f"Test failed with error: failed to simulate daily check in")
                
        except Exception as e:
            self.fail(f"Test failed with error: {str(e)}")
    
    def test_07_ResetAfterManyDaysMissed(self):
        self.logger.info("Starting rewards reset after 7 days are missed")
        try:
            self.navigate_to_login_page()
            self.perform_login(CREDENTIALS["valid_user"]["username"], CREDENTIALS["valid_user"]["password"])
            self.get_api_token(CREDENTIALS["valid_user"]["username"], CREDENTIALS["valid_user"]["password"])
            
            user_id = self.get_id_number()
            
            # 7 days missed
            simulate_success = self.simulate_check_in(user_id, 6, 8)
            if simulate_success:
                self.driver.get(self.url)
                                
                self.annoucement_close_button()
                
                # Check popup visibility
                self.checkIn_popup()
                time.sleep(1)
                
                # Close check-in popup
                self.daily_checkin_close_button()
                
                # start check in and verify
                self.checkin_process(isReset=True)
            else:
                self.fail(f"Test failed with error: failed to simulate daily check in")
                
        except Exception as e:
            self.fail(f"Test failed with error: {str(e)}")

    def test_08_ResetAfterDay31(self):
        self.logger.info("Starting rewards reset after day 31 test")
        try:
            self.navigate_to_login_page()
            self.perform_login(CREDENTIALS["valid_user"]["username"], CREDENTIALS["valid_user"]["password"])
            self.get_api_token(CREDENTIALS["valid_user"]["username"], CREDENTIALS["valid_user"]["password"])
            
            user_id = self.get_id_number()
                
            simulate_success = self.simulate_check_in(user_id, 31, 1)
            if simulate_success:
                self.driver.get(self.url)
                
                
                self.annoucement_close_button()
                
                # Check popup visibility
                self.checkIn_popup()
                time.sleep(1)
                
                # Check if the day 31 changed to day 1
                self.verify_day_changed()
                
                # Close check-in popup
                self.daily_checkin_close_button()
                
                # start check in and verify
                self.checkin_process(isReset=True)
            else:
                self.fail(f"Test failed with error: failed to simulate daily check in")
                
        except Exception as e:
            self.fail(f"Test failed with error: {str(e)}")
    
    def test_09_VipReward(self):
        self.logger.info("Starting VIP rewards test")
        try:
            self.createAccount()
            self.get_api_token(self.register_acc, self.register_acc)
            
            user_id = self.get_id_number()
            
            vip_levels = self.get_vip_levels()
            # Automatically create test scenarios from defined constants
            test_scenarios = []
            previous_recharge = None
            for vip in sorted(vip_levels, key=lambda x: int(x['id'])):
                if previous_recharge is not None:
                    top_up = float(vip['recharge']) - previous_recharge
                else:
                    top_up = float(vip['recharge'])
                
                test_scenarios.append({
                    "id": vip["id"],
                    "recharge": top_up
                })
                
                previous_recharge = float(vip['recharge'])
                                    
            for scenario in test_scenarios:
                self.logger.info(f"Testing {scenario['id']} level rewards with top-up amount: {scenario['recharge']}")
                
                if scenario['recharge'] != 0:
                    self.topup(scenario['recharge'])
                
                simulate_success = self.simulate_check_in(user_id, 6, 1)
                if simulate_success:
                    self.driver.get(self.url)
                    
                    self.annoucement_close_button()
                    
                    # Check popup visibility
                    self.checkIn_popup()
                    time.sleep(1)
                    
                    # Close check-in popup
                    self.logger.info("Closing check-in popup")
                    self.daily_checkin_close_button()
                    
                    # start check in and verify
                    self.checkin_process(isVipTest=True, vip_id=scenario['id'])

                else:
                    self.fail(f"Test failed with error: failed to simulate daily check in")
                
        except Exception as e:
            self.fail(f"Test failed with error: {str(e)}")

if __name__ == "__main__":
    unittest.main()
