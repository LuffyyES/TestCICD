import os
import unittest
import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from config.constant import API_URL, LANGUAGE_SETTINGS, CREDENTIALS
from tests.authentication_test.base_test import BaseTest
import pyperclip
from PIL import Image
import io
from pyzbar.pyzbar import decode
from urllib.parse import urlparse, parse_qs
from tests.test_init import TestInit
from typing import Dict, Any, Optional, List, Union, Tuple, BinaryIO, TypeVar, Type
import requests
import random
import json
import re

class TestDailyMission(BaseTest):

    def __init__(
        self, methodName: str = 'runTest', language: Optional[str] = None, browser: Optional[str] = None
    ) -> None:
        super().__init__(methodName)
        self.language = language
        self.browser = browser
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False

        if not self.logger.handlers:
            handler = logging.FileHandler('daily_mission.log')
            handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            self.logger.addHandler(handler)

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
        # self.username, self.password = self.test_init.register_new_account()
        

    def tearDown(self):
        if hasattr(self, "driver"):
            self.driver.quit()
    
    def get_mission_api(self):
        """Get missions data from API"""
        token = self.login(self.username, self.password)
        headers = {
            "Authorization": f"Bearer {token}",
            "Language": self.language
        }
        response = requests.get(f"{API_URL}/api/getdailymissions", headers=headers)
        response.raise_for_status()
        missions = response.json().get("data")
        return missions
    
    def setup_test_user(self, register_new=False, close_mission=True):
        """Set up test user - either create new or use existing"""
        if register_new:
            # 使用测试ID创建唯一的账户名
            self.username, self.password = self.test_init.register_new_account()
        else:
            if self.language == "cn":
                self.username = "LuffyTest1"
                self.password = "LuffyTest1"
            elif self.language == "en":
                self.username = "LuffyTest2"
                self.password = "LuffyTest2"
            elif self.language == "bm":
                self.username = "LuffyTest3"
                self.password = "LuffyTest3"
            
        while self.username == None or self.password == None:
            ## try again
            self.username, self.password = self.test_init.register_new_account()
        
        self.navigate_to_login_page()
        self.perform_login(self.username, self.password, close_mission)
        return self.username, self.password
    
    def navigate_to_missions_page(self):
        """Navigate to the missions page and wait for it to load"""
        self.clickMiniGameWidget("missions")
        # Wait for any mission to load
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[id^='mission-card-']"))
        )
        self.logger.info("Missions page loaded successfully")
    
    def find_mission_by_type(self, missions, condition_type):
        """Find a mission by its condition type"""
        for mission in missions:
            if mission.get("condition_type") == condition_type:
                return mission
        return None
    
    def find_mission_by_condition_type(self, missions, condition_type):
        """Find a mission by its redirect tag"""
        for mission in missions:
            if mission.get("condition_type") == condition_type:
                return mission
        return None
    
    def get_mission_localized_data(self, mission):
        """Get localized title and description for a mission based on language setting"""
        mission_title = mission.get("title")
        mission_desc = mission.get("desc")
        
        # Find translations if they exist
        if "translations" in mission:
            for translation in mission.get("translations", []):
                if translation.get("locale") == self.language:
                    # Use translated title and description if available
                    json_data = translation.get("json", {})
                    if json_data:
                        mission_title = json_data.get("title", mission_title)
                        mission_desc = json_data.get("description", mission_desc)
                    break
        
        return mission_title, mission_desc
    
    def verify_mission_card_elements(self, mission):
        """Verify all elements in a mission card are displayed correctly"""
        mission_id = mission.get("id")
        mission_title, mission_desc = self.get_mission_localized_data(mission)
        
        try:
            # Find the mission card
            mission_element = self.driver.find_element(By.ID, f"mission-card-{mission_id}")
            
            # Verify title
            title_element = mission_element.find_element(By.ID, f"mission-title-{mission_id}")
            self.assertEqual(mission_title, title_element.text, 
                           f"Title mismatch for mission ID {mission_id}")
            
            # Verify description
            desc_element = mission_element.find_element(By.ID, f"mission-desc-{mission_id}")
            self.assertEqual(mission_desc, desc_element.text, 
                           f"Description mismatch for mission ID {mission_id}")
            
            # Verify progress bar
            progress_bar = mission_element.find_element(By.ID, f"mission-progress-{mission_id}")
            self.assertTrue(progress_bar.is_displayed(), f"Progress bar not displayed for mission ID {mission_id}")
            
            # Verify action button
            claim_button = mission_element.find_element(By.ID, f"mission-claim-button-{mission_id}")
            self.assertTrue(claim_button.is_displayed(), f"Claim button not displayed for mission ID {mission_id}")
            
            # Verify progress text
            progress_text = mission_element.find_element(By.ID, f"mission-progress-text-{mission_id}")
            
            if mission.get("condition_type") in ["deposit", "withdraw_with_minimum"]:
                expected_text = f"{int(float(mission.get('progress')))} / {int(float(mission.get('target')))}"
            else:
                expected_text = f"RM{int(float(mission.get('progress')))} / RM{int(float(mission.get('target')))}"
            
            self.assertEqual(expected_text, progress_text.text, 
                           f"Progress text mismatch for mission ID {mission_id}")
            
            # Verify mission icon
            icon_element = mission_element.find_element(By.ID, f"mission-icon-{mission_id}")
            self.assertTrue(icon_element.is_displayed(), f"Icon not displayed for mission ID {mission_id}")
            
            self.logger.info(f"Successfully verified mission ID {mission_id}: {mission_title}")
            return True
        
        except (NoSuchElementException, AssertionError) as e:
            self.logger.error(f"Verification failed for mission ID {mission_id}: {str(e)}")
            return False
    
    def verify_mission_card_elements_popup(self, mission):
        """Verify all elements in a mission card are displayed correctly"""
        mission_id = mission.get("id")
        mission_title, _ = self.get_mission_localized_data(mission)
        
        try:
            # Find the mission card            
            # Verify title
            title_element = self.driver.find_element(By.ID, f"not-yet-check-in-mission-title-{mission_id}")
            self.assertEqual(mission_title, title_element.text, 
                           f"Title mismatch for mission ID {mission_id}")
            
            # Verify progress bar
            progress_bar = self.driver.find_element(By.ID, f"not-yet-check-in-mission-progress-{mission_id}")
            self.assertTrue(progress_bar.is_displayed(), f"Progress bar not displayed for mission ID {mission_id}")
            
            # Verify action button
            claim_button = self.driver.find_element(By.ID, f"not-yet-check-in-redirect-button-{mission_id}")
            self.assertTrue(claim_button.is_displayed(), f"Claim button not displayed for mission ID {mission_id}")
            
            # Verify progress text
            progress_text = self.driver.find_element(By.ID, f"not-yet-check-in-mission-progress-text-{mission_id}")
            
            if mission.get("condition_type") in ["deposit", "withdraw_with_minimum"]:
                expected_text = f"{int(float(mission.get('progress')))} / {int(float(mission.get('target')))}"
            else:
                expected_text = f"RM{int(float(mission.get('progress')))} / RM{int(float(mission.get('target')))}"
            
            self.assertEqual(expected_text, progress_text.text, 
                           f"Progress text mismatch for mission ID {mission_id}")
            
            self.logger.info(f"Successfully verified mission ID {mission_id}: {mission_title}")
            return True
        
        except (NoSuchElementException, AssertionError) as e:
            self.logger.error(f"Verification failed for mission ID {mission_id}: {str(e)}")
            return False
    
    def make_deposit(self, amount):
        """Make a deposit of the specified amount"""
        self.logger.info(f"Making a deposit of RM{amount}...")
        user_id = self.get_user_id()
        self.test_init.submit_deposit_api(username=self.username, password=self.password, amount=amount)
        self.handleDeposit(user_id)
    
    def verify_mission_progress(self, mission_id, expected_progress=None):
        """Verify mission progress in UI matches API data"""
        # Get updated mission data from API
        updated_missions = self.get_mission_api()
        updated_mission = None
        
        for mission in updated_missions:
            if mission.get("id") == mission_id:
                updated_mission = mission
                break
        
        if not updated_mission:
            self.fail(f"Could not find mission with ID {mission_id} in API response")
        
        target = float(updated_mission.get("target", 0))
        progress = min(float(updated_mission.get("progress", 0)), target)
        condition_type = updated_mission.get("condition_type", "")
        
        # If expected progress is provided, verify it
        if expected_progress is not None:
            self.assertEqual(expected_progress, progress, 
                           f"Mission progress mismatch. Expected: {expected_progress}, Got: {progress}")
        
        # Find the mission card in UI
        mission_element = self.driver.find_element(By.ID, f"mission-card-{mission_id}")
        
        # Check progress bar
        progress_bar = mission_element.find_element(By.ID, f"mission-progress-{mission_id}")
        progress_value = int(progress_bar.get_attribute("aria-valuenow"))
        expected_progress_value = min(100, int(round((progress / target) * 100))) if target > 0 else 0
        
        self.assertEqual(expected_progress_value, progress_value, 
                       f"Progress bar value mismatch. Expected: {expected_progress_value}%, Got: {progress_value}%")
        
        # Check progress text
        progress_text_element = mission_element.find_element(By.ID, f"mission-progress-text-{mission_id}")
        actual_progress_text = progress_text_element.text
        
        # Determine expected progress text based on condition type
        if condition_type in ["topup", "withdraw", "loss"]:
            expected_progress_text = f"RM{int(progress)} / RM{int(target)}"
        else:
            expected_progress_text = f"{int(progress)} / {int(target)}"
        
        self.assertEqual(expected_progress_text, actual_progress_text, 
                       f"Progress text mismatch. Expected: '{expected_progress_text}', Got: '{actual_progress_text}'")
        
        self.logger.info(f"Successfully verified mission progress for ID {mission_id}: {progress}/{target}")
        return progress, target
    
    def verify_mission_progress_popup(self, mission_id, expected_progress=None):
        """Verify mission progress in UI matches API data"""
        # Get updated mission data from API
        updated_missions = self.get_mission_api()
        updated_mission = None
        
        for mission in updated_missions:
            if mission.get("id") == mission_id:
                updated_mission = mission
                break
        
        if not updated_mission:
            self.fail(f"Could not find mission with ID {mission_id} in API response")
        
        target = float(updated_mission.get("target", 0))
        progress = min(float(updated_mission.get("progress", 0)), target)
        condition_type = updated_mission.get("condition_type", "")
        
        # If expected progress is provided, verify it
        if expected_progress is not None:
            self.assertEqual(expected_progress, progress, 
                           f"Mission progress mismatch. Expected: {expected_progress}, Got: {progress}")
        
        # Find the mission card in UI
        mission_element = self.driver.find_element(By.ID, f"not-yet-check-in-mission-{mission_id}")
        
        # Check progress bar
        progress_bar = mission_element.find_element(By.ID, f"not-yet-check-in-mission-progress-{mission_id}")
        progress_value = int(progress_bar.get_attribute("aria-valuenow"))
        expected_progress_value = min(100, int(round((progress / target) * 100))) if target > 0 else 0
        
        self.assertEqual(expected_progress_value, progress_value, 
                       f"Progress bar value mismatch. Expected: {expected_progress_value}%, Got: {progress_value}%")
        
        # Check progress text
        progress_text_element = mission_element.find_element(By.ID, f"not-yet-check-in-mission-progress-text-{mission_id}")
        actual_progress_text = progress_text_element.text
        
        # Determine expected progress text based on condition type
        if condition_type in ["topup", "withdraw", "loss"]:
            expected_progress_text_1 = f"RM{float(progress):.2f} / RM{int(target)}"
            expected_progress_text_2 = f"RM{int(progress)} / RM{int(target)}"
        else:
            expected_progress_text_1 = f"{float(progress):.2f} / {int(target)}"
            expected_progress_text_2 = f"{int(progress)} / {int(target)}"
        
        is_valid = expected_progress_text_1 == actual_progress_text or expected_progress_text_2 == actual_progress_text
        
        self.assertTrue(is_valid, 
                       f"Progress text mismatch. Expected: '{expected_progress_text_1}' or '{expected_progress_text_2}', Got: '{actual_progress_text}'")
        
        self.logger.info(f"Successfully verified mission progress for ID {mission_id}: {progress}/{target}")
        return progress, target
    
    def claim_mission_reward(self, mission_id):
        """Claim a completed mission reward and verify success"""
        # Find the mission card
        mission_element = self.driver.find_element(By.ID, f"mission-card-{mission_id}")
        claim_button = mission_element.find_element(By.ID, f"mission-claim-button-{mission_id}")
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", claim_button)
        
        # Get button text
        button_text = claim_button.find_element(By.CSS_SELECTOR, ".MuiTypography-root").text
        
        # Check if already claimed
        claimed_text = LANGUAGE_SETTINGS[self.language]["daily_mission"]["claimed"]
        if button_text.lower() == claimed_text:
            self.logger.warning(f"Mission already claimed. Button text: '{button_text}'")
            return False
        
        # Click claim button
        self.logger.info(f"Clicking claim button with text: '{button_text}'")
        claim_button.click()
        
        # Wait for success modal
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".swal2-popup.swal2-modal.swal2-icon-success"))
        )
        
        # Verify success message
        success_title = self.driver.find_element(By.ID, "swal2-title").text
        success_message = LANGUAGE_SETTINGS[self.language]["daily_mission"]["success"]
        self.assertEqual(success_message, success_title, 
                   f"Success message not showing correctly: '{success_title}', expected: '{success_message}'")
        
        self.logger.info(f"Successfully claimed reward. Success message: '{success_title}'")
        
        # Click OK on success modal
        ok_button = self.driver.find_element(By.CSS_SELECTOR, ".swal2-confirm")
        ok_button.click()
        
        return True
    
    def claim_mission_reward_popup(self, mission_id):
        """Claim a completed mission reward and verify success"""
        # Find the mission card
        mission_element = self.driver.find_element(By.ID, f"not-yet-check-in-mission-{mission_id}")
        claim_button = mission_element.find_element(By.ID, f"not-yet-check-in-claim-button-{mission_id}")
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", claim_button)
        
        # Get button text
        button_text = claim_button.find_element(By.CSS_SELECTOR, ".MuiTypography-root").text
        
        # Check if already claimed
        claimed_text = LANGUAGE_SETTINGS[self.language]["daily_mission"]["claimed"]
        if button_text.lower() == claimed_text:
            self.logger.warning(f"Mission already claimed. Button text: '{button_text}'")
            return False
        
        # Click claim button
        self.logger.info(f"Clicking claim button with text: '{button_text}'")
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", claim_button)
        claim_button.click()
        
        self.logger.info(f"Successfully claimed reward'")
        
        return True
    
    def verify_mission_claimed_status(self, mission_id):
        """Verify mission is marked as claimed in both API and UI"""
        # Check API claimed status
        final_missions = self.get_mission_api()
        final_mission = None
        
        for mission in final_missions:
            if mission.get("id") == mission_id:
                final_mission = mission
                break
        
        if final_mission:
            is_claimed = final_mission.get("is_claimed", 0)
            self.assertEqual(1, is_claimed, "Mission is not marked as claimed in API")
            self.logger.info("Mission successfully marked as claimed in API")
        else:
            self.logger.warning(f"Could not find mission with ID {mission_id} in API check")
        
        try_count = 2
        
        for _ in range(try_count):
            
            # Wait for missions to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, f"mission-card-{mission_id}"))
            )
            
            # Check button text and state
            mission_element = self.driver.find_element(By.ID, f"mission-card-{mission_id}")
            claimed_button = mission_element.find_element(By.ID, f"mission-claim-button-{mission_id}")
            
            button_text = claimed_button.find_element(By.CSS_SELECTOR, ".MuiTypography-root").text
            claimed_text = LANGUAGE_SETTINGS[self.language]["daily_mission"]["claimed"]
            self.assertEqual(claimed_text, button_text, f"Button text is not '{claimed_text}', got '{button_text}' instead")
            
            # Verify button is disabled
            self.assertFalse(claimed_button.is_enabled(), "Claim button is not disabled after claim")
            
            self.logger.info("Successfully verified button changed to 'Claimed' and is disabled")
            
            self.driver.refresh()
        return True
    
    def verify_mission_claimed_status_popup(self, mission_id):
        """Verify mission is marked as claimed in both API and UI"""
        # Check API claimed status
        final_missions = self.get_mission_api()
        final_mission = None
        
        for mission in final_missions:
            if mission.get("id") == mission_id:
                final_mission = mission
                break
        
        if final_mission:
            is_claimed = final_mission.get("is_claimed", 0)
            self.assertEqual(1, is_claimed, "Mission is not marked as claimed in API")
            self.logger.info("Mission successfully marked as claimed in API")
        else:
            self.logger.warning(f"Could not find mission with ID {mission_id} in API check")
        
        try_count = 2
        
        for _ in range(try_count):
            
            # Wait for missions to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, f"not-yet-check-in-mission-{mission_id}"))
            )
            
            # Check button text and state
            mission_element = self.driver.find_element(By.ID, f"not-yet-check-in-mission-{mission_id}")
            claimed_button = mission_element.find_element(By.ID, f"not-yet-check-in-claim-button-{mission_id}")
            
            button_text = claimed_button.find_element(By.CSS_SELECTOR, ".MuiTypography-root").text
            claimed_text = LANGUAGE_SETTINGS[self.language]["daily_mission"]["claimed"]
            self.assertEqual(claimed_text, button_text, f"Button text is not '{claimed_text}', got '{button_text}' instead")
            
            # Verify button is disabled
            self.assertFalse(claimed_button.is_enabled(), "Claim button is not disabled after claim")
            
            self.logger.info("Successfully verified button changed to 'Claimed' and is disabled")
            
            self.navigate_to_home_and_handle_popups(close_mission=False)
        return True

    def extract_amount_from_text(self, text, currency_prefix="RM"):
        """
        Extracts amount values from text in multiple languages.

        Args:
            text (str): The text to extract amounts from
            currency_prefix (str): Currency prefix to look for (default: "RM")

        Returns:
            float or None: The extracted amount or None if no amount found

        Examples:
            - "Top up RM300 daily" would return 300.0
            - "每天存款RM300 或以上" would return 300.0
            - "Deposit 3 times" would return 3.0
            - "3 kali" would return 3.0
            - "No amount here" would return None
        """

        # Try to find currency amount pattern (e.g., "RM300", "RM 300", "RM300.50")
        if currency_prefix:
            currency_pattern = fr'{currency_prefix}\s*(\d+(?:\.\d+)?)'
            currency_match = re.search(currency_pattern, text)
            if currency_match:
                return float(currency_match.group(1))

        # Multilingual patterns for quantity indicators
        # English: times, time, deposits, x
        # Malay: kali, kali sehari, kali dalam sehari
        # Chinese: 次, 倍, 遍, 次数
        quantity_indicators = r'(?:times|time|deposits|x|kali(?:\s+(?:sehari|dalam\s+sehari)?)|次|倍|遍|次数)'

        # Try to find numeric values with quantity indicators in multiple languages
        number_pattern = fr'(\d+(?:\.\d+)?)\s*{quantity_indicators}'
        number_match = re.search(number_pattern, text)
        if number_match:
            return float(number_match.group(1))

        # Also check for patterns where the number comes after the indicator (common in some languages)
        # Example: "次数3" (Chinese for "3 times")
        reverse_pattern = fr'{quantity_indicators}\s*(\d+(?:\.\d+)?)'
        reverse_match = re.search(reverse_pattern, text)
        if reverse_match:
            return float(reverse_match.group(1))

        # Look for amounts with currency words spelled out in different languages
        # English: dollars, $, USD
        # Malay: ringgit
        # Chinese: 元, 块, 马币 (Malaysian currency in Chinese)
        currency_words = r'(?:dollars|\$|USD|ringgit|元|块|马币)'
        spelled_currency_pattern = fr'(\d+(?:\.\d+)?)\s*{currency_words}'
        spelled_currency_match = re.search(spelled_currency_pattern, text)
        if spelled_currency_match:
            return float(spelled_currency_match.group(1))

        # Check for reverse order (currency word first, then amount)
        # Example: "ringgit 300" or "元300"
        reverse_currency_pattern = fr'{currency_words}\s*(\d+(?:\.\d+)?)'
        reverse_currency_match = re.search(reverse_currency_pattern, text)
        if reverse_currency_match:
            return float(reverse_currency_match.group(1))

        # As a last resort, try to find any numeric value in the text
        any_number_pattern = r'(\d+(?:\.\d+)?)'
        any_number_match = re.search(any_number_pattern, text)
        if any_number_match:
            return float(any_number_match.group(1))

        # No amount found
        return None
    
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

    def request_withdraw_api(self, amount, bank):
        token = self.login(self.username, self.password)
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {
            "amount": amount,
            "bank": bank
        }
        response = requests.post(f"{CREDENTIALS['BO_base_url']}/api/withdraw", headers=headers, json=payload)
        response.raise_for_status()
    
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
    
    def get_vip_name_by_id(self, data, vip_id):
        """
        Retrieves the VIP name for a specific ID from the JSON data.
        
        Args:
            data_str (str): JSON string containing VIP data
            vip_id (int): The VIP ID to search for
            
        Returns:
            str: The VIP name if found, None otherwise
        """
        try:
            # Search for the VIP with the specified ID
            for vip in data:
                if vip["id"] == vip_id:
                    return vip["vipname"]
            
            # If no matching ID is found
            return None

        except json.JSONDecodeError:
            print("Invalid JSON format")
            return None
        except KeyError as e:
            print(f"Missing key in JSON data: {e}")
            return None
    
    def navigate_to_home_and_handle_popups(self, close_mission=True):
        """Navigate to home page and handle any popups."""
        self.driver.get(self.url)
        self.annoucement_close_button()
        self.daily_checkin_close_button(close_mission)

    def get_all_balances(self):
        """Get all balance types in one method."""
        return {
            "wallet": self.getWalletBalance(),
            "cards": self.get4DCards(),
            "bb_coins": self.checkBBCoins(),
            "spin_tickets": self.checkSpinTicket()
        }

    def wait_for_deposit_processing(self, timeout=30):
        """
        Wait for deposit to be processed by the system.
        
        Args:
            timeout (int): Maximum time to wait in seconds
        """
        self.logger.info(f"Waiting up to {timeout} seconds for deposit to be processed")
        # Implementation depends on how you can check if a deposit is processed
        # This could be a simple time.sleep() or a more sophisticated wait with WebDriverWait
        import time
        time.sleep(timeout)

    def verify_reward_received(self, reward_type, expected_value, initial_balances, final_balances):
        """
        Verify that the correct reward was received.
        
        Args:
            reward_type (str): Type of reward (bonus, ticket, spin, coin)
            expected_value (float): Expected value increase
            initial_balances (dict): Balances before claiming reward
            final_balances (dict): Balances after claiming reward
        """
        expected_increase = float(expected_value)
        
        # Define which balance should increase based on reward type
        reward_mapping = {
            "bonus": "wallet",
            "ticket": "cards",
            "spin": "spin_tickets",
            "coin": "bb_coins"
        }
        
        # Check if reward type is valid
        if reward_type not in reward_mapping:
            self.fail(f"Unknown reward type: {reward_type}")
            return
        
        # Get the balance key that should change
        target_balance = reward_mapping[reward_type]
        
        # Verify the target balance increased by the expected amount
        initial = initial_balances[target_balance]
        final = final_balances[target_balance]
        actual_increase = final - initial
        
        self.assertAlmostEqual(
            actual_increase, expected_increase, 
            msg=f"{reward_type} balance did not increase by expected amount. "
                f"Expected increase: {expected_increase}, Actual increase: {actual_increase}"
        )
        
        # Verify other balances didn't change
        for balance_type, balance_key in reward_mapping.items():
            if balance_type != reward_type:
                self.assertEqual(
                    initial_balances[balance_key], final_balances[balance_key],
                    f"{balance_type} balance changed unexpectedly"
                )
    
    def simulate_game_records(self, user_id, amount, type, provider_id=2):
        """ type 0: loss, type 1: win"""
        
        token = self.login(self.username, self.password)
        headers = {
            "Authorization": f"Bearer {token}",
        }
        response = requests.get(f"{API_URL}/api/simulate-game-records?passcode=99999&user_id={user_id}&amount={amount}&type={type}&provider_id={provider_id}", headers=headers)
        response.raise_for_status()
    
    def simulate_reset_mission_next_day(self, user_id):
        
        token = self.login(self.username, self.password)
        headers = {
            "Authorization": f"Bearer {token}",
        }
        response = requests.get(f"{API_URL}/api/simulate-daily-mission?passcode=99999&user_id={user_id}", headers=headers)
        response.raise_for_status()
    
    def verify_navigation(self, url):
        # Wait for redirection and verify URL
        WebDriverWait(self.driver, 15).until(
            lambda driver: f"/{self.language}/{url}" in driver.current_url
        )
        
        expected_url_part = f"/{self.language}/{url}"
        self.assertIn(expected_url_part, self.driver.current_url,
                    f"URL redirection failed. Expected URL to contain '{expected_url_part}'")
    
    def get_reward(self, mission):
        vip_id = self.get_user_vip_id()
        vip_levels = self.get_vip_levels("en")
        vip_name = self.get_vip_name_by_id(vip_levels, vip_id).lower()
        rewards_by_vip = mission.get("rewards_by_vip", {})
        reward_value = rewards_by_vip.get(vip_name, {}).get("value", 0)
        reward_type = rewards_by_vip.get(vip_name, {}).get("type", "")
        
        return reward_value, reward_type
                
    def test_01_AllMissionShown(self):
        """Test to verify that all missions from the API are shown in the UI."""
        try:
            self.logger.info("Starting all mission shown test...")
            
            # Setup user and get missions
            self.setup_test_user(register_new=False)
            missions = self.get_mission_api()
            
            # Skip if no missions available
            if not missions:
                self.logger.warning("No missions returned from API, skipping test")
                self.skipTest("No missions available")
            
            self.logger.info(f"Received {len(missions)} missions from API")
            
            # Navigate to missions page
            self.navigate_to_missions_page()
            
            # Find all mission cards in UI
            mission_cards = self.driver.find_elements(By.CSS_SELECTOR, "[id^='mission-card-']")
            self.logger.info(f"Found {len(mission_cards)} mission cards in the UI")
            
            # Verify counts match
            self.assertEqual(len(missions), len(mission_cards), 
                           f"Mission count mismatch: API shows {len(missions)} missions but UI shows {len(mission_cards)}")
            
            # Verify each mission is displayed correctly
            verification_results = [self.verify_mission_card_elements(mission) for mission in missions]
            self.assertTrue(all(verification_results), "Some missions failed verification")
            
            self.logger.info("All missions verification completed successfully")
            
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")
    
    def test_02_MissionGoButtonRedirectsToDeposit(self):
        """Test to verify that clicking 'Go' button on a deposit mission redirects to the deposit page."""
        try:
            self.logger.info("Starting mission redirection test...")
            
            # Setup user and get missions
            self.setup_test_user()
            missions = self.get_mission_api()
            
            # Skip if no missions available
            if not missions:
                self.logger.warning("No missions returned from API, skipping test")
                self.skipTest("No missions available")
            
            # Find a deposit mission
            deposit_mission = self.find_mission_by_condition_type(missions, "deposit")
            if not deposit_mission:
                self.logger.warning("No deposit missions found, skipping test")
                self.skipTest("No deposit missions available")
            
            mission_id = deposit_mission.get("id")
            self.logger.info(f"Found deposit mission: ID {mission_id} - {deposit_mission['title']}")
            
            # Navigate to missions page
            self.navigate_to_missions_page()
            
            # Find and click the Go button
            mission_element = self.driver.find_element(By.ID, f"mission-card-{mission_id}")
            go_button = mission_element.find_element(By.ID, f"mission-claim-button-{mission_id}")
            
            self.logger.info("Clicking Go button...")
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", go_button)
            go_button.click()
            
            self.verify_navigation("wallet/deposit")
            
            self.logger.info(f"Successfully redirected to {self.driver.current_url}")
            
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")
    
    def test_03_MissionGoButtonRedirectsToWithdraw(self):
        """Test to verify that clicking 'Go' button on a withdraw mission redirects to the withdraw page."""
        try:
            self.logger.info("Starting mission redirection test...")
            
            # Setup user and get missions
            self.setup_test_user()
            missions = self.get_mission_api()
            
            # Skip if no missions available
            if not missions:
                self.logger.warning("No missions returned from API, skipping test")
                self.skipTest("No missions available")
            
            # Find a deposit mission
            withdraw_mission = self.find_mission_by_condition_type(missions, "withdraw")
            if not withdraw_mission:
                self.logger.warning("No withdraw missions found, skipping test")
                self.skipTest("No withdraw missions available")
            
            mission_id = withdraw_mission.get("id")
            self.logger.info(f"Found withdraw mission: ID {mission_id} - {withdraw_mission['title']}")
            
            # Navigate to missions page
            self.navigate_to_missions_page()
            
            # Find and click the Go button
            mission_element = self.driver.find_element(By.ID, f"mission-card-{mission_id}")
            go_button = mission_element.find_element(By.ID, f"mission-claim-button-{mission_id}")
            
            self.logger.info("Clicking Go button...")
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", go_button)
            go_button.click()
            
            self.verify_navigation("wallet/withdrawal")
            
            self.logger.info(f"Successfully redirected to {self.driver.current_url}")
            
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")
    
    def test_04_MissionGoButtonRedirectsToGames(self):
        """Test to verify that clicking 'Go' button on a games mission redirects to the games page."""
        try:
            self.logger.info("Starting mission redirection test...")
            
            # Setup user and get missions
            self.setup_test_user()
            missions = self.get_mission_api()
            
            # Skip if no missions available
            if not missions:
                self.logger.warning("No missions returned from API, skipping test")
                self.skipTest("No missions available")
            
            # Find a deposit mission
            loss_mission = self.find_mission_by_condition_type(missions, "loss")
            if not loss_mission:
                self.logger.warning("No loss missions found, skipping test")
                self.skipTest("No loss missions available")
            
            mission_id = loss_mission.get("id")
            self.logger.info(f"Found loss mission: ID {mission_id} - {loss_mission['title']}")
            
            # Navigate to missions page
            self.navigate_to_missions_page()
            
            # Find and click the Go button
            mission_element = self.driver.find_element(By.ID, f"mission-card-{mission_id}")
            go_button = mission_element.find_element(By.ID, f"mission-claim-button-{mission_id}")
            
            self.logger.info("Clicking Go button...")
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", go_button)
            go_button.click()
            
            self.verify_navigation("games")
            
            self.logger.info(f"Successfully redirected to {self.driver.current_url}")
            
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")
    
    def test_05_MissionEllipsisNavigatesToDetails(self):
        """Test to verify that clicking the ellipsis button navigates to the mission details page."""
        try:
            self.logger.info("Starting mission ellipsis navigation test...")
            
            # Setup user and get missions
            self.setup_test_user()
            missions = self.get_mission_api()
            
            # Skip if no missions available
            if not missions:
                self.logger.warning("No missions returned from API, skipping test")
                self.skipTest("No missions available")
            
            # Select the first mission for testing
            test_mission = missions[0]
            mission_id = test_mission.get("id")
            mission_title, _ = self.get_mission_localized_data(test_mission)
            
            self.logger.info(f"Selected mission for testing: ID {mission_id} - {mission_title}")
            
            # Navigate to missions page
            self.navigate_to_missions_page()
            
            # Find and click the ellipsis button
            ellipsis_button = self.driver.find_element(By.ID, f"mission-ellipsis-{mission_id}")
            self.logger.info("Clicking ellipsis button...")
            ellipsis_button.click()
            
            self.verify_navigation(f"missions?id={mission_id}")
            
            self.logger.info(f"Successfully redirected to {self.driver.current_url}")
            
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")

    def test_06_VerifyInfoDetailsPage(self):
        """Test to verify that the details page is displayed correctly."""
        try:
            self.logger.info("Starting mission details page verification test...")
            
            # Setup user and get missions
            self.setup_test_user()
            missions = self.get_mission_api()
            
            # Skip if no missions available
            if not missions:
                self.logger.warning("No missions returned from API, skipping test")
                self.skipTest("No missions available")
            
            # Select the first mission for testing
            test_mission = missions[0]
            mission_id = test_mission.get("id")
            mission_title, _ = self.get_mission_localized_data(test_mission)
            
            self.logger.info(f"Selected mission for testing: ID {mission_id} - {mission_title}")
            
            # Navigate to missions page
            self.navigate_to_missions_page()
            
            # Find and click the ellipsis button
            ellipsis_button = self.driver.find_element(By.ID, f"mission-ellipsis-{mission_id}")
            self.logger.info("Clicking ellipsis button...")
            ellipsis_button.click()
            
            time.sleep(2)
            
            # Verify details page elements
            # Icon
            detail_icon = self.driver.find_element(By.ID, f"mission-detail-icon-{mission_id}").get_attribute("src")
            expected_icon = test_mission.get("icon")
            self.assertEqual(detail_icon, expected_icon, "Mission detail icon mismatch")
            
            # Title
            title_element = self.driver.find_element(By.ID, f"mission-detail-title-{mission_id}")
            expected_title = test_mission.get("title")
            self.assertEqual(title_element.text, expected_title, "Mission detail title mismatch")
            
            # Progress bar
            progress_text= self.driver.find_element(By.ID, f"mission-detail-progress-text-{mission_id}")
            if test_mission.get("condition_type") in ["deposit", "withdraw_with_minimum"]:
                expected_text = f"{float(test_mission.get('progress')):.2f} / {int(float(test_mission.get('target')))}"
            else:
                expected_text = f"RM{float(test_mission.get('progress')):.2f} / RM{int(float(test_mission.get('target')))}"
            self.assertEqual(progress_text.text, expected_text, "Mission detail progress mismatch")
            
            # Steps
            steps = self.driver.find_elements(By.CSS_SELECTOR, "[id^='mission-detail-step-']")
            self.assertGreater(len(steps), 0, "No mission steps displayed")
            
            # Go button
            go_button = self.driver.find_element(By.ID, f"mission-detail-claim-button-{mission_id}")
            self.assertTrue(go_button.is_displayed(), "Go button not displayed on details page")
            
            # Step images
            step_images = self.driver.find_elements(By.CSS_SELECTOR, "[id^='mission-detail-step-image-']")
            for img in step_images:
                self.assertTrue(img.is_displayed(), f"Step image {img.get_attribute('id')} not displayed")
            
            self.logger.info("Successfully verified mission details page")
            
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")
    
    def test_07_MissionRewardsByVIPLevelShown(self):
        """Test to verify that mission rewards by VIP level are displayed correctly on mission details page."""
        try:
            self.logger.info("Starting mission rewards by VIP level verification test...")
            
            # Setup user and get missions
            self.setup_test_user(register_new=False)
            missions = self.get_mission_api()
            
            # Skip if no missions available
            if not missions:
                self.logger.warning("No missions returned from API, skipping test")
                self.skipTest("No missions available")
            
            # Find a mission that has rewards_by_vip data
            test_mission = None
            for mission in missions:
                if mission.get("rewards_by_vip"):
                    test_mission = mission
                    break
            
            if not test_mission:
                self.logger.warning("No mission with rewards_by_vip data found, skipping test")
                self.skipTest("No mission with rewards_by_vip data available")
            
            mission_id = test_mission.get("id")
            mission_title, _ = self.get_mission_localized_data(test_mission)
            rewards_by_vip = test_mission.get("rewards_by_vip", {})
            
            self.logger.info(f"Selected mission for testing: ID {mission_id} - {mission_title}")
            self.logger.info(f"Rewards by VIP data: {rewards_by_vip}")
            
            # Navigate to missions page
            self.navigate_to_missions_page()
            
            # Find and click the ellipsis button
            ellipsis_button = self.driver.find_element(By.ID, f"mission-ellipsis-{mission_id}")
            self.logger.info("Clicking ellipsis button...")
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", ellipsis_button)
            ellipsis_button.click()
        
            # Wait for the rewards section to be visible
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "how-to-claim-more-list"))
            )
            
            # Find the rewards card
            rewards_card = self.driver.find_elements(By.CSS_SELECTOR, ".MuiPaper-root.mui-theme-1ppyhjh")[1]
            self.assertTrue(rewards_card.is_displayed(), "Rewards card is not displayed")
            
            # Expected VIP levels and their order
            vip_levels_self_language = self.get_vip_levels()
            expected_vip_levels = [vip_level["vipname"] for vip_level in vip_levels_self_language]
            
            vip_levels_en = self.get_vip_levels("en")
            expected_vip_levels_en = [vip_level["vipname"] for vip_level in vip_levels_en]
            
            # Verify all VIP levels are displayed
            rewards_list_items = rewards_card.find_elements(By.CSS_SELECTOR, ".MuiListItem-root.mui-theme-19wp548")
            self.assertEqual(len(expected_vip_levels), len(rewards_list_items), f"Expected {len(expected_vip_levels)} VIP levels, got {len(rewards_list_items)}")
            
            # Verify each VIP level and its reward
            for i, item in enumerate(rewards_list_items):
                vip_level = expected_vip_levels[i].lower()
                vip_level_en = expected_vip_levels_en[i].lower()
                # Verify VIP level name
                level_name = item.find_element(By.CSS_SELECTOR, ".mui-theme-1b4k91k").text
                if vip_level != level_name.lower():
                    self.logger.warning(f"VIP level mismatch. Expected {vip_level}, got {level_name}")
                
                # Get reward value from the API data
                reward_value = rewards_by_vip.get(vip_level_en, {}).get("value", 0)
                reward_type = rewards_by_vip.get(vip_level_en, {}).get("type", "")
                
                # Verify reward value displayed in UI
                reward_text = item.find_element(By.CSS_SELECTOR, ".mui-theme-1y6uiyu").text
                
                # Format expected reward text based on reward type
                if reward_type == "bonus":
                    expected_reward_text = f"RM{reward_value:.2f}"
                    self.assertEqual(expected_reward_text, reward_text, 
                            f"Reward value mismatch for {level_name}. Expected {expected_reward_text}, got {reward_text}")
                else:
                    expected_reward_text = f"{reward_value}"
                    self.assertEqual(expected_reward_text, reward_text.split(" ")[0], 
                            f"Reward value mismatch for {level_name}. Expected {expected_reward_text}, got {reward_text}")
            
            self.logger.info("Successfully verified rewards by VIP level on mission details page")
            
        except NoSuchElementException as e:
            self.logger.error(f"Element not found: {str(e)}")
            self.fail(f"Test failed - element not found: {str(e)}")
        except AssertionError as e:
            self.logger.error(f"Assertion failed: {str(e)}")
            self.fail(f"Test failed - assertion error: {str(e)}")
        except TimeoutException as e:
            self.logger.error(f"Timeout waiting for element: {str(e)}")
            self.fail(f"Test failed - timeout waiting for element: {str(e)}")
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with unexpected error: {str(e)}")
    
    def test_08_UpgradeGetButton(self):
        """Test to verify upgrade & get button is working."""
        try:
            self.logger.info("Starting mission rewards by VIP level verification test...")
            
            # Setup user and get missions
            self.setup_test_user(register_new=False)
            missions = self.get_mission_api()
            
            # Skip if no missions available
            if not missions:
                self.logger.warning("No missions returned from API, skipping test")
                self.skipTest("No missions available")
            
            # Find a mission that has rewards_by_vip data
            test_mission = None
            for mission in missions:
                if mission.get("rewards_by_vip"):
                    test_mission = mission
                    break
            
            if not test_mission:
                self.logger.warning("No mission with rewards_by_vip data found, skipping test")
                self.skipTest("No mission with rewards_by_vip data available")
            
            mission_id = test_mission.get("id")
            
            # Navigate to missions page
            self.navigate_to_missions_page()
            
            # Find and click the ellipsis button
            ellipsis_button = self.driver.find_element(By.ID, f"mission-ellipsis-{mission_id}")
            self.logger.info("Clicking ellipsis button...")
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", ellipsis_button)
            ellipsis_button.click()
            
            # Wait for the rewards section to be visible
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "how-to-claim-more-list"))
            )
            
            # Find the upgrade button
            upgrade_button = self.driver.find_element(By.ID, "upgrade-get-button")
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", upgrade_button)
            
            # Verify the text of the upgrade button
            button_text = upgrade_button.text
            button_text_expected = LANGUAGE_SETTINGS[self.language]["daily_mission"]["upgrade"]
            self.assertEqual(button_text_expected, button_text, f"Expected '{button_text_expected}' in button text, got '{button_text}'")
            
            self.logger.info(f"Found upgrade button with text: '{button_text}'")
            
            upgrade_button.click()
            
            self.verify_navigation(f"profile/vip_page")
            
            self.logger.info("Successfully verified upgrade & get button is working and redirect to VIP page")
            
        except NoSuchElementException as e:
            self.logger.error(f"Element not found: {str(e)}")
            self.fail(f"Test failed - element not found: {str(e)}")
        except AssertionError as e:
            self.logger.error(f"Assertion failed: {str(e)}")
            self.fail(f"Test failed - assertion error: {str(e)}")
        except TimeoutException as e:
            self.logger.error(f"Timeout waiting for element: {str(e)}")
            self.fail(f"Test failed - timeout waiting for element: {str(e)}")
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with unexpected error: {str(e)}")
    
    def test_09_MissionProgressUpdatesAfterDeposit(self):
        """Test to verify that mission progress updates correctly after making a deposit."""
        try:
            self.logger.info("Starting mission progress tracking test...")
            
            # Setup user and get missions
            self.setup_test_user(register_new=False)
            
            initial_missions = self.get_mission_api()
            
            # Skip if no missions available
            if not initial_missions:
                self.logger.warning("No missions returned from API, skipping test")
                self.skipTest("No missions available")
            
            # Find a topup mission
            deposit_mission = self.find_mission_by_type(initial_missions, "topup")
            if not deposit_mission:
                self.logger.warning("No topup missions found, skipping test")
                self.skipTest("No topup missions available")
            
            mission_id = deposit_mission.get("id")
            initial_progress = float(deposit_mission.get("progress", 0))
            
            self.logger.info(f"Selected mission ID {mission_id} with initial progress {initial_progress}")
            
            # Make a deposit
            deposit_amount = 30
            self.make_deposit(deposit_amount)
            
            # Navigate to missions page
            self.navigate_to_missions_page()
            
            # Verify progress updated
            expected_progress = initial_progress + deposit_amount
            updated_progress, _ = self.verify_mission_progress(mission_id, expected_progress)
            
            # Check that progress has increased
            self.assertGreater(updated_progress, initial_progress, 
                             f"Mission progress did not increase after deposit")
            
            # Navigate to details page and verify progress there too
            ellipsis_button = self.driver.find_element(By.ID, f"mission-ellipsis-{mission_id}")
            ellipsis_button.click()
            
            # Wait for details page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "mission-detail-card"))
            )
            
            # Verify progress on details page
            detail_progress_bar = self.driver.find_element(By.ID, f"mission-detail-progress-{mission_id}")
            detail_progress_value = int(detail_progress_bar.get_attribute("aria-valuenow"))
            self.assertGreater(detail_progress_value, 0, 
                             f"Detail page progress bar value did not update, still at {detail_progress_value}%")
            
            self.logger.info("Successfully verified mission progress updates after deposit")
            
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")
    
    def test_10_TopUpMissionCompletionAndRewardClaim(self):
        """Test to verify topup mission completion and reward claiming functionality."""
        self.logger.info("Starting topup mission completion and reward claim test...")
        
        # Setup user and get missions
        self.setup_test_user(register_new=False)
        
        initial_missions = self.get_mission_api()
        
        # Skip if no missions available
        if not initial_missions:
            self.logger.warning("No missions returned from API, skipping test")
            self.skipTest("No missions available")
        self.logger.info(f"Initial missions: {initial_missions}")
        # Find a topup mission
        topup_mission = self.find_mission_by_type(initial_missions, "topup")
        if not topup_mission:
            self.logger.warning("No topup missions found, skipping test")
            self.skipTest("No topup missions available")
        
        mission_id = topup_mission.get("id")
        target_amount = int(float(topup_mission.get("target", 30)))
        initial_progress = int(float(topup_mission.get("progress", 0)))
        
        self.logger.info(f"Selected mission for testing: ID {mission_id}")
        self.logger.info(f"Target amount: {target_amount}, Initial progress: {initial_progress}")
        
        # # Get initial balances before completing the mission
        self.navigate_to_home_and_handle_popups()
        
        # Calculate deposit amount needed and complete mission if necessary
        amount_needed = target_amount - initial_progress
        if amount_needed <= 0:
            self.logger.info("Mission already completed, proceeding to claiming")
        else:
            # Make deposit to complete mission
            deposit_amount = max(30, amount_needed)
            self.logger.info(f"Making deposit of {deposit_amount} to complete mission")
            self.make_deposit(deposit_amount)
            
            # Allow time for the system to process the deposit
            self.wait_for_deposit_processing(timeout=30)
        
        
        initial_balances = self.get_all_balances()
        
        # Navigate to missions page
        self.navigate_to_home_and_handle_popups()
        self.navigate_to_missions_page()
        
        # Verify mission is completed
        progress, target = self.verify_mission_progress(mission_id)
        self.assertGreaterEqual(
            progress, target, 
            f"Mission not completed. Progress: {progress}, Target: {target}"
        )
        
        # Claim reward
        claimed = self.claim_mission_reward(mission_id)
        if not claimed:
            self.skipTest("Mission reward already claimed or not available for claiming")
        
        # Verify mission is marked as claimed
        self.verify_mission_claimed_status(mission_id)

        # Get reward value from the API data
        reward_value, reward_type = self.get_reward(topup_mission)
        self.logger.info(f"Expected reward: {reward_value} {reward_type}")

        # Get balances after claiming reward
        self.navigate_to_home_and_handle_popups()
        final_balances = self.get_all_balances()
        
        # Verify the correct reward was received
        self.verify_reward_received(reward_type, reward_value, initial_balances, final_balances)
    
    def test_11_CompleteAndClaimDepositMission(self):
        """Test to verify the complete flow of completing and claiming a deposit mission."""
        try:
            self.logger.info("Starting test for completing and claiming a deposit mission...")
            
            # 1. Setup user
            self.setup_test_user(register_new=False)
            
            self.navigate_to_home_and_handle_popups()
            
            # 2. Get missions data
            missions = self.get_mission_api()
            
            # Skip if no missions available
            if not missions:
                self.logger.warning("No missions returned from API, skipping test")
                self.skipTest("No missions available")
            
            # 3. Find a deposit mission that is not completed or claimed yet
            deposit_mission = self.find_mission_by_type(missions, "deposit")
            
            if not deposit_mission:
                self.logger.warning("No suitable deposit mission found, skipping test")
                self.skipTest("No suitable deposit mission available")
            
            # 4. Get mission details
            mission_id = deposit_mission.get("id")
            mission_title, mission_desc = self.get_mission_localized_data(deposit_mission)
            target = float(deposit_mission.get("target", 0))
            initial_progress = float(deposit_mission.get("progress", 0))

            
            self.logger.info(f"Selected mission: ID {mission_id} - {mission_title}")
            self.logger.info(f"Target: {target}, Initial progress: {initial_progress}")
            
            # 5. Navigate to missions page
            self.navigate_to_missions_page()
            
            # 8. Click the Go button to navigate to deposit page
            mission_button = self.driver.find_element(By.ID, f"mission-claim-button-{mission_id}")
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", mission_button)
            mission_button.click()
            
            # 9. Wait for navigation to deposit page
            WebDriverWait(self.driver, 15).until(
                lambda driver: f"{self.language}/wallet/deposit" in driver.current_url
            )
            self.logger.info(f"Successfully navigated to deposit page: {self.driver.current_url}")
            
            # 10. Calculate how much to deposit
            remaining_deposits = int(target - initial_progress)
            deposit_amount = self.extract_amount_from_text(mission_desc)  # Based on the mission description requiring RM300 or more
            
            self.logger.info(f"Need to make {remaining_deposits} deposits of RM{deposit_amount} each")
            
            user_id = self.get_user_id()
            for i in range(remaining_deposits):
                self.logger.info(f"Making deposit {i+1} of {remaining_deposits}...")
                # Make deposit using API
                self.test_init.submit_deposit_api(username=self.username, password=self.password, amount=deposit_amount)
                self.handleDeposit(user_id)
                
                # Wait a moment between deposits
                time.sleep(2)
            
            # 11. Navigate back to missions page
            self.navigate_to_home_and_handle_popups()
            
            initial_balances = self.get_all_balances()
            
            self.navigate_to_home_and_handle_popups()
            self.navigate_to_missions_page()
            
            # 12. Wait for missions to load and refresh data
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, f"mission-card-{mission_id}"))
            )
            
            progress, target = self.verify_mission_progress(mission_id)
            self.assertGreaterEqual(
                progress, target, 
                f"Mission not completed. Progress: {progress}, Target: {target}"
            )
            
            # Claim reward
            claimed = self.claim_mission_reward(mission_id)
            if not claimed:
                self.skipTest("Mission reward already claimed or not available for claiming")
            
            # Verify mission is marked as claimed
            self.verify_mission_claimed_status(mission_id)
    
            reward_value, reward_type = self.get_reward(deposit_mission)
            self.logger.info(f"Reward: {reward_value} {reward_type}")
            
            # Get balances after claiming reward
            self.navigate_to_home_and_handle_popups()
            final_balances = self.get_all_balances()
            
            # Verify the correct reward was received
            self.verify_reward_received(reward_type, reward_value, initial_balances, final_balances)
    
            self.logger.info(f"Successfully completed and claimed deposit mission: {mission_title}")
            
        except NoSuchElementException as e:
            self.logger.error(f"Element not found: {str(e)}")
            self.fail(f"Test failed - element not found: {str(e)}")
        except AssertionError as e:
            self.logger.error(f"Assertion failed: {str(e)}")
            self.fail(f"Test failed - assertion error: {str(e)}")
        except TimeoutException as e:
            self.logger.error(f"Timeout waiting for element: {str(e)}")
            self.fail(f"Test failed - timeout waiting for element: {str(e)}")
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with unexpected error: {str(e)}")
    
    def test_12_MissionProgressUpdatesAfterWithdraw(self):
        """Test to verify that mission progress updates correctly after making a withdraw."""
        try:
            self.logger.info("Starting withdraw mission progress tracking test...")
            
            # Setup user and get missions
            self.setup_test_user(register_new=False)
            
            initial_missions = self.get_mission_api()
            
            # Skip if no missions available
            if not initial_missions:
                self.logger.warning("No missions returned from API, skipping test")
                self.skipTest("No missions available")
            
            # Find a topup mission
            withdraw_mission = self.find_mission_by_type(initial_missions, "withdraw")
            if not withdraw_mission:
                self.logger.warning("No withdraw missions found, skipping test")
                self.skipTest("No withdraw missions available")
            
            mission_id = withdraw_mission.get("id")
            initial_progress = float(withdraw_mission.get("progress", 0))
            
            self.logger.info(f"Selected mission ID {mission_id} with initial progress {initial_progress}")
            
            # Make a deposit
            withdraw_amount = 30
                        
            userID = self.get_user_id()
            self.make_deposit(withdraw_amount)
            turnoverIDs = self.get_turnover_ids(userID, self.language)
            
            if turnoverIDs:                
                complete_success = self.modify_turnover_status(userID, turnoverIDs, action_type="success")
                if not complete_success:
                    self.fail("Failed to complete turnover")

            self.request_withdraw_api(withdraw_amount, "1")
            
            ID = self.get_user_id()
            self.handleWithdrawRequest(ID, isReject=False, isProcessing=False)
            
            # Navigate to missions page
            self.navigate_to_missions_page()
            
            # Verify progress updated
            expected_progress = initial_progress + withdraw_amount
            updated_progress, _ = self.verify_mission_progress(mission_id, expected_progress)
            
            # Check that progress has increased
            self.assertGreater(updated_progress, initial_progress, 
                             f"Mission progress did not increase after deposit")
            
            # Navigate to details page and verify progress there too
            ellipsis_button = self.driver.find_element(By.ID, f"mission-ellipsis-{mission_id}")
            ellipsis_button.click()
            
            # Wait for details page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "mission-detail-card"))
            )
            
            # Verify progress on details page
            detail_progress_bar = self.driver.find_element(By.ID, f"mission-detail-progress-{mission_id}")
            detail_progress_value = int(detail_progress_bar.get_attribute("aria-valuenow"))
            self.assertGreater(detail_progress_value, 0, 
                             f"Detail page progress bar value did not update, still at {detail_progress_value}%")
            
            self.logger.info("Successfully verified mission progress updates after deposit")
            
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")

    def test_13_WithdrawMissionCompletionAndRewardClaim(self):
        """Test to verify withdraw mission completion and reward claiming functionality."""
        self.logger.info("Starting withdraw mission completion and reward claim test...")
        
        # Setup user and get missions
        self.setup_test_user(register_new=False)
        
        initial_missions = self.get_mission_api()
        
        # Skip if no missions available
        if not initial_missions:
            self.logger.warning("No missions returned from API, skipping test")
            self.skipTest("No missions available")
        self.logger.info(f"Initial missions: {initial_missions}")
        # Find a topup mission
        withdraw_mission = self.find_mission_by_type(initial_missions, "withdraw")
        if not withdraw_mission:
            self.logger.warning("No withdraw missions found, skipping test")
            self.skipTest("No withdraw missions available")
        
        mission_id = withdraw_mission.get("id")
        target_amount = int(float(withdraw_mission.get("target", 30)))
        initial_progress = int(float(withdraw_mission.get("progress", 0)))
        
        # Get reward value from the API data
        reward_value, reward_type = self.get_reward(withdraw_mission)
        
        self.logger.info(f"Selected mission for testing: ID {mission_id}")
        self.logger.info(f"Target amount: {target_amount}, Initial progress: {initial_progress}")
        self.logger.info(f"Expected reward: {reward_value} {reward_type}")
        
        # # Get initial balances before completing the mission
        self.navigate_to_home_and_handle_popups()
        
        # Calculate deposit amount needed and complete mission if necessary
        amount_needed = target_amount - initial_progress
        if amount_needed <= 0:
            self.logger.info("Mission already completed, proceeding to claiming")
        else:
            userID = self.get_user_id()
            self.make_deposit(amount_needed)
            turnoverIDs = self.get_turnover_ids(userID, self.language)
            if turnoverIDs:                
                complete_success = self.modify_turnover_status(userID, turnoverIDs, action_type="success")
                if not complete_success:
                    self.fail("Failed to complete turnover")

            self.request_withdraw_api(amount_needed, "1")
            
            ID = self.get_user_id()
            self.handleWithdrawRequest(ID, isReject=False, isProcessing=False)
        
        initial_balances = self.get_all_balances()
        
        # Navigate to missions page
        self.navigate_to_home_and_handle_popups()
        self.navigate_to_missions_page()
        
        # Verify mission is completed
        progress, target = self.verify_mission_progress(mission_id)
        self.assertGreaterEqual(
            progress, target, 
            f"Mission not completed. Progress: {progress}, Target: {target}"
        )
        
        # Claim reward
        claimed = self.claim_mission_reward(mission_id)
        if not claimed:
            self.skipTest("Mission reward already claimed or not available for claiming")
        
        # Verify mission is marked as claimed
        self.verify_mission_claimed_status(mission_id)
        
        # Get balances after claiming reward
        self.navigate_to_home_and_handle_popups()
        final_balances = self.get_all_balances()
        
        # Verify the correct reward was received
        self.verify_reward_received(reward_type, reward_value, initial_balances, final_balances)
    
    def test_14_CompleteAndClaimWithdrawMinimumMission(self):
        """Test to verify the complete flow of completing and claiming a withdraw mission."""
        try:
            self.logger.info("Starting test for completing and claiming a withdraw mission...")
            
            # 1. Setup user
            self.setup_test_user(register_new=False)
            
            self.navigate_to_home_and_handle_popups()
            
            # 2. Get missions data
            missions = self.get_mission_api()
            
            # Skip if no missions available
            if not missions:
                self.logger.warning("No missions returned from API, skipping test")
                self.skipTest("No missions available")
            
            # 3. Find a deposit mission that is not completed or claimed yet
            withdraw_mission = self.find_mission_by_type(missions, "withdraw_with_minimum")
            
            if not withdraw_mission:
                self.logger.warning("No suitable deposit mission found, skipping test")
                self.skipTest("No suitable deposit mission available")
            
            # 4. Get mission details
            mission_id = withdraw_mission.get("id")
            mission_title, mission_desc = self.get_mission_localized_data(withdraw_mission)
            target = float(withdraw_mission.get("target", 0))
            initial_progress = float(withdraw_mission.get("progress", 0))

            
            self.logger.info(f"Selected mission: ID {mission_id} - {mission_title}")
            self.logger.info(f"Target: {target}, Initial progress: {initial_progress}")
            
            # 5. Navigate to missions page
            self.navigate_to_missions_page()
            
            # 8. Click the Go button to navigate to deposit page
            mission_button = self.driver.find_element(By.ID, f"mission-claim-button-{mission_id}")
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", mission_button)
            mission_button.click()
            
            # 9. Wait for navigation to withdraw page
            WebDriverWait(self.driver, 15).until(
                lambda driver: f"{self.language}/wallet/withdrawal" in driver.current_url
            )
            self.logger.info(f"Successfully navigated to withdraw page: {self.driver.current_url}")
            
            # 10. Calculate how much to withdraw
            remaining_withdrawals = int(target - initial_progress)
            withdraw_amount = self.extract_amount_from_text(mission_desc)  # Based on the mission description requiring RM300 or more
            
            self.logger.info(f"Need to make {remaining_withdrawals} withdrawals of RM{withdraw_amount} each")
            
            userID = self.get_user_id()
            for i in range(remaining_withdrawals):
                self.make_deposit(withdraw_amount)
                turnoverIDs = self.get_turnover_ids(userID, self.language)
                if turnoverIDs:                
                    complete_success = self.modify_turnover_status(userID, turnoverIDs, action_type="success")
                    if not complete_success:
                        self.fail("Failed to complete turnover")

                self.request_withdraw_api(withdraw_amount, "1")
                
                ID = self.get_user_id()
                self.handleWithdrawRequest(ID, isReject=False, isProcessing=False)
            
            # 11. Navigate back to missions page
            self.navigate_to_home_and_handle_popups()
            
            initial_balances = self.get_all_balances()
            
            self.navigate_to_home_and_handle_popups()
            self.navigate_to_missions_page()
            
            # 12. Wait for missions to load and refresh data
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, f"mission-card-{mission_id}"))
            )
            
            progress, target = self.verify_mission_progress(mission_id)
            self.assertGreaterEqual(
                progress, target, 
                f"Mission not completed. Progress: {progress}, Target: {target}"
            )
            
            # Claim reward
            claimed = self.claim_mission_reward(mission_id)
            if not claimed:
                self.skipTest("Mission reward already claimed or not available for claiming")
            
            # Verify mission is marked as claimed
            self.verify_mission_claimed_status(mission_id)
                
            reward_value, reward_type = self.get_reward(withdraw_mission)
            self.logger.info(f"Reward: {reward_value} {reward_type}")
            
            # Get balances after claiming reward
            self.navigate_to_home_and_handle_popups()
            final_balances = self.get_all_balances()
            
            # Verify the correct reward was received
            self.verify_reward_received(reward_type, reward_value, initial_balances, final_balances)
    
            self.logger.info(f"Successfully completed and claimed deposit mission: {mission_title}")
            
        except NoSuchElementException as e:
            self.logger.error(f"Element not found: {str(e)}")
            self.fail(f"Test failed - element not found: {str(e)}")
        except AssertionError as e:
            self.logger.error(f"Assertion failed: {str(e)}")
            self.fail(f"Test failed - assertion error: {str(e)}")
        except TimeoutException as e:
            self.logger.error(f"Timeout waiting for element: {str(e)}")
            self.fail(f"Test failed - timeout waiting for element: {str(e)}")
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with unexpected error: {str(e)}")

    def test_15_LossMissionCompletionAndRewardClaim(self):
        """Test to verify loss mission completion and reward claiming functionality."""
        self.logger.info("Starting loss mission completion and reward claim test...")
        
        # Setup user and get missions
        self.setup_test_user(register_new=False)
        
        initial_missions = self.get_mission_api()
        
        # Skip if no missions available
        if not initial_missions:
            self.logger.warning("No missions returned from API, skipping test")
            self.skipTest("No missions available")
        self.logger.info(f"Initial missions: {initial_missions}")
        # Find a topup mission
        loss_mission = self.find_mission_by_type(initial_missions, "loss")
        if not loss_mission:
            self.logger.warning("No loss missions found, skipping test")
            self.skipTest("No loss missions available")
        
        mission_id = loss_mission.get("id")
        target_amount = int(float(loss_mission.get("target", 30)))
        initial_progress = int(float(loss_mission.get("progress", 0)))
        
        self.logger.info(f"Selected mission for testing: ID {mission_id}")
        self.logger.info(f"Target amount: {target_amount}, Initial progress: {initial_progress}")
        
        # # Get initial balances before completing the mission
        self.navigate_to_home_and_handle_popups()
        
        # Calculate deposit amount needed and complete mission if necessary
        amount_needed = target_amount - initial_progress
        if amount_needed <= 0:
            self.logger.info("Mission already completed, proceeding to claiming")
        else:
            if amount_needed > 0:
                userID = self.get_user_id()
                self.simulate_game_records(userID, amount_needed, 0)
        
        initial_balances = self.get_all_balances()
        
        # Navigate to missions page
        self.navigate_to_home_and_handle_popups()
        self.navigate_to_missions_page()
        
        # Verify mission is completed
        progress, target = self.verify_mission_progress(mission_id)
        self.assertGreaterEqual(
            progress, target, 
            f"Mission not completed. Progress: {progress}, Target: {target}"
        )
        
        # Claim reward
        claimed = self.claim_mission_reward(mission_id)
        if not claimed:
            self.skipTest("Mission reward already claimed or not available for claiming")
        
        # Verify mission is marked as claimed
        self.verify_mission_claimed_status(mission_id)
    
        # Get reward value from the API data
        reward_value, reward_type = self.get_reward(loss_mission)
        self.logger.info(f"Expected reward: {reward_value} {reward_type}")
        
        # Get balances after claiming reward
        self.navigate_to_home_and_handle_popups()
        final_balances = self.get_all_balances()
        
        # Verify the correct reward was received
        self.verify_reward_received(reward_type, reward_value, initial_balances, final_balances)
    
    def test_16_SimulateResetMissionNextDay(self):
        """Test to simulate the reset of mission next day"""
        try:
            self.logger.info("Starting test for simulating mission reset next day...")
            
            # Setup user and get missions
            self.setup_test_user(register_new=False)
            
            initial_missions = self.get_mission_api()
            
            # Skip if no missions available
            if not initial_missions:
                self.logger.warning("No missions returned from API, skipping test")
                self.skipTest("No missions available")
                
            self.navigate_to_missions_page()
            time.sleep(1)
            
            count_completed_mission = 0
            
            for mission in initial_missions:
                self.logger.info(f"Checking mission {mission.get('title')}")
                mission_button_text = self.driver.find_element(By.ID, f"mission-claim-button-{mission.get('id')}").text
                claim_text = LANGUAGE_SETTINGS[self.language]["daily_mission"]["claim"]
                claimed_text = LANGUAGE_SETTINGS[self.language]["daily_mission"]["claimed"]
                if mission_button_text == claim_text or mission_button_text == claimed_text:
                    self.logger.info(f"Mission {mission.get('title')} is completed")
                    count_completed_mission += 1
            
            if count_completed_mission == 0:
                self.logger.info("No mission to complete, skipping test")
                self.skipTest("No mission to complete")
            
            self.logger.info(f"Completed {count_completed_mission} missions")
            
            userID = self.get_user_id()
            self.simulate_reset_mission_next_day(userID)
            
            self.logger.info("Simulating mission reset next day...")
            self.driver.refresh()
            time.sleep(1)
            count_completed_mission = 0
            count_progress_not_reset = 0
            for mission in initial_missions:
                mission_button_text = self.driver.find_element(By.ID, f"mission-claim-button-{mission.get('id')}").text
                claim_text = LANGUAGE_SETTINGS[self.language]["daily_mission"]["claim"]
                claimed_text = LANGUAGE_SETTINGS[self.language]["daily_mission"]["claimed"]
                if mission_button_text == claim_text or mission_button_text == claimed_text:
                    self.logger.info(f"Mission {mission.get('title')} is claimed, will complete and claim it")
                    count_completed_mission += 1
                
                progress_text = self.driver.find_element(By.ID, f"mission-progress-text-{mission.get('id')}").text.replace("RM", "")[0]
                if progress_text != "0":
                    count_progress_not_reset += 1
            
            if count_completed_mission != 0:
                self.fail(f"Mission {count_completed_mission} is completed, expected 0")
            
            if count_progress_not_reset != 0:
                self.fail(f"Mission {count_progress_not_reset} is not reset, expected 0")
            
            self.logger.info("Successfully simulated mission reset next day")       
            
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")
    
    
    def test_17_AttemptToClaimAgainAfterClaimed(self):
        """Test to verify that a completed and already claimed mission cannot be claimed again."""
        try:
            self.logger.info("Starting test for attempting to claim an already claimed mission...")
            
            # Setup user and get missions
            self.setup_test_user(register_new=False)
            
            initial_missions = self.get_mission_api()
            
            # Skip if no missions available
            if not initial_missions:
                self.logger.warning("No missions returned from API, skipping test")
                self.skipTest("No missions available")
            self.logger.info(f"Initial missions: {initial_missions}")
            # Find a topup mission
            topup_mission = self.find_mission_by_type(initial_missions, "topup")
            if not topup_mission:
                self.logger.warning("No topup missions found, skipping test")
                self.skipTest("No topup missions available")
            
            mission_id = topup_mission.get("id")
            target_amount = int(float(topup_mission.get("target", 30)))
            initial_progress = int(float(topup_mission.get("progress", 0)))
            
            self.logger.info(f"Selected mission for testing: ID {mission_id}")
            self.logger.info(f"Target amount: {target_amount}, Initial progress: {initial_progress}")
            
            # # Get initial balances before completing the mission
            self.navigate_to_home_and_handle_popups()
            
            # Calculate deposit amount needed and complete mission if necessary
            amount_needed = target_amount - initial_progress
            if amount_needed <= 0:
                self.logger.info("Mission already completed, proceeding to claiming")
            else:
                # Make deposit to complete mission
                deposit_amount = max(30, amount_needed)
                self.logger.info(f"Making deposit of {deposit_amount} to complete mission")
                self.make_deposit(deposit_amount)
                
                # Allow time for the system to process the deposit
                self.wait_for_deposit_processing(timeout=30)
            
            
            initial_balances = self.get_all_balances()
            
            # Navigate to missions page
            self.navigate_to_home_and_handle_popups()
            self.navigate_to_missions_page()
            
            # Verify mission is completed
            progress, target = self.verify_mission_progress(mission_id)
            self.assertGreaterEqual(
                progress, target, 
                f"Mission not completed. Progress: {progress}, Target: {target}"
            )
            
            # Claim reward
            claimed = self.claim_mission_reward(mission_id)
            if not claimed:
                self.skipTest("Mission reward already claimed or not available for claiming")
            
            # Verify mission is marked as claimed
            self.verify_mission_claimed_status(mission_id)
            
            # Find the claimed mission card
            mission_element = self.driver.find_element(By.ID, f"mission-card-{mission_id}")
            claim_button = mission_element.find_element(By.ID, f"mission-claim-button-{mission_id}")
            
            # Verify button text is "Claimed"
            button_text = claim_button.find_element(By.CSS_SELECTOR, ".MuiTypography-root").text
            claimed_text = LANGUAGE_SETTINGS[self.language]["daily_mission"]["claimed"]
            self.assertEqual(claimed_text, button_text, f"Expected button text '{claimed_text}', got '{button_text}'")
            
            # Verify button is disabled
            self.assertFalse(claim_button.is_enabled(), "Claim button should be disabled for claimed mission")
            
            # Try to click the button anyway (this should have no effect since it's disabled)
            try:
                claim_button.click()
                self.logger.info("Attempted to click disabled 'Claimed' button")
            except Exception as e:
                self.logger.info(f"As expected, couldn't click disabled button: {str(e)}")
                
            # Verify no popup appears
            try:
                # Brief wait to check if any popup appears
                WebDriverWait(self.driver, 3).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".swal2-popup"))
                )
                # If we get here, a popup appeared unexpectedly
                self.fail("Unexpected popup appeared after clicking claimed button")
            except TimeoutException:
                # This is expected - no popup should appear
                self.logger.info("As expected, no popup appeared after clicking claimed button")
                
            # Navigate to the mission details page to verify claimed status there
            ellipsis_button = self.driver.find_element(By.ID, f"mission-ellipsis-{mission_id}")
            ellipsis_button.click()
            
            # Wait for details page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "mission-detail-card"))
            )
            
            time.sleep(2)
            
            try_count = 2
            
            for i in range(try_count):
                # Find the claim button on details page
                detail_claim_button = self.driver.find_element(By.ID, f"mission-detail-claim-button-{mission_id}")
            
                button_text = detail_claim_button.find_element(By.CSS_SELECTOR, "p.MuiTypography-root").text
                    
                claimed_text = LANGUAGE_SETTINGS[self.language]["daily_mission"]["claimed"]
                self.assertEqual(claimed_text, button_text, f"Expected button text '{claimed_text}', got '{button_text}'")
                
                # Verify button is disabled on details page
                self.assertFalse(detail_claim_button.is_enabled(), "Claim button should be disabled on details page")
                
                # Try to click the button on details page anyway
                try:
                    detail_claim_button.click()
                    self.logger.info("Attempted to click disabled 'Claimed' button on details page")
                except Exception as e:
                    self.logger.info(f"As expected, couldn't click disabled button on details page: {str(e)}")
                
                # Verify no popup appears on details page
                try:
                    # Brief wait to check if any popup appears
                    WebDriverWait(self.driver, 3).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".swal2-popup"))
                    )
                    # If we get here, a popup appeared unexpectedly
                    self.fail("Unexpected popup appeared after clicking claimed button on details page")
                except TimeoutException:
                    # This is expected - no popup should appear
                    self.logger.info("As expected, no popup appeared after clicking claimed button on details page")
                    
                self.driver.refresh()
            
            # Get reward value from the API data
            reward_value, reward_type = self.get_reward(topup_mission)
            
            # Get balances after claiming reward
            self.navigate_to_home_and_handle_popups()
            final_balances = self.get_all_balances()
            
            # Verify the correct reward was received
            self.verify_reward_received(reward_type, reward_value, initial_balances, final_balances)
            
        except NoSuchElementException as e:
            self.logger.error(f"Element not found: {str(e)}")
            self.fail(f"Test failed - element not found: {str(e)}")
        except AssertionError as e:
            self.logger.error(f"Assertion failed: {str(e)}")
            self.fail(f"Test failed - assertion error: {str(e)}")
        except TimeoutException as e:
            # Only fail for timeouts not related to the expected absence of popups
            if "swal2-popup" not in str(e):
                self.logger.error(f"Timeout waiting for element: {str(e)}")
                self.fail(f"Test failed - timeout waiting for element: {str(e)}")
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with unexpected error: {str(e)}")
    
    def test_18_MissionProgressUpdatesAfterDeposit(self):
        """Test to verify that mission progress not updates after making a deposit (Normal Level User)."""
        try:
            self.logger.info("Starting mission progress tracking test...")
            
            # Setup user and get missions
            self.setup_test_user(register_new=True)
            initial_missions = self.get_mission_api()
            
            # Skip if no missions available
            if not initial_missions:
                self.logger.warning("No missions returned from API, skipping test")
                self.skipTest("No missions available")
            
            # Find a topup mission
            deposit_mission = self.find_mission_by_type(initial_missions, "topup")
            if not deposit_mission:
                self.logger.warning("No topup missions found, skipping test")
                self.skipTest("No topup missions available")
            
            mission_id = deposit_mission.get("id")
            initial_progress = float(deposit_mission.get("progress", 0))
            target = float(deposit_mission.get("target", 30))
            condition_type = deposit_mission.get("condition_type")
            self.logger.info(f"Selected mission ID {mission_id} with initial progress {initial_progress}")
            
            # Make a deposit
            deposit_amount = 30
            self.make_deposit(deposit_amount)
            
            # Navigate to missions page
            self.navigate_to_missions_page()
            
            # Find the mission card in UI
            mission_element = self.driver.find_element(By.ID, f"mission-card-{mission_id}")
            
            # Check progress bar
            progress_bar = mission_element.find_element(By.ID, f"mission-progress-{mission_id}")
            progress_value = int(progress_bar.get_attribute("aria-valuenow"))
            expected_progress_value = min(100, int(round((0 / target) * 100))) if target > 0 else 0
            
            self.assertEqual(expected_progress_value, progress_value, 
                        f"Progress bar value mismatch. Expected: {expected_progress_value}%, Got: {progress_value}%")
            
            # Check progress text
            progress_text_element = mission_element.find_element(By.ID, f"mission-progress-text-{mission_id}")
            actual_progress_text = progress_text_element.text
            
            # Determine expected progress text based on condition type
            if condition_type in ["topup", "withdraw", "loss"]:
                expected_progress_text = f"RM{int(0)} / RM{int(target)}"
            else:
                expected_progress_text = f"{int(0)} / {int(target)}"
            
            self.assertEqual(expected_progress_text, actual_progress_text, 
                        f"Progress text mismatch. Expected: '{expected_progress_text}', Got: '{actual_progress_text}'")
            
            self.logger.info(f"Successfully verified mission progress for ID {mission_id}: {0}/{target}")
            
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")
    
    def test_19_HomePagePopUpDailyMission(self):
        try:
            self.logger.info("Starting test for verifying mission show up in home modal...")
            
            # Setup user and get missions
            self.setup_test_user(register_new=False, close_mission=False)
            
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "not-yet-check-in-daily-mission-title"))
            )
            
            self.logger.info("Successfully verified mission show up in home modal")

        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")
    
    def test_20_HomePagePopUpAllMissionShown(self):
        """Test to verify that all missions from the API are shown in the pop up."""
        try:
            self.logger.info("Starting all mission shown test...")
            
            # Setup user and get missions
            self.setup_test_user(register_new=True, close_mission=False)
            missions = self.get_mission_api()
            
            # Skip if no missions available
            if not missions:
                self.logger.warning("No missions returned from API, skipping test")
                self.skipTest("No missions available")
            
            self.logger.info(f"Received {len(missions)} missions from API")
            
            # Find all mission cards in UI
            mission_cards = self.driver.find_elements(By.CSS_SELECTOR, "li[id^='not-yet-check-in-mission-']")
            self.logger.info(f"Found {len(mission_cards)} mission cards in the UI")
            
            # Verify counts match
            self.assertEqual(len(missions), len(mission_cards), 
                           f"Mission count mismatch: API shows {len(missions)} missions but UI shows {len(mission_cards)}")
            
            # Verify each mission is displayed correctly
            verification_results = [self.verify_mission_card_elements_popup(mission) for mission in missions]
            self.assertTrue(all(verification_results), "Some missions failed verification")
            
            self.logger.info("All missions verification completed successfully")
            
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")
    
    def test_21_HomePagePopUpNavigateToMissionsPage(self):
        try:
            self.logger.info("Starting test for verifying navigation to missions page...")
            
            # Setup user and get missions
            self.setup_test_user(register_new=False, close_mission=False)
            
            navigate_button = self.driver.find_element(By.ID, "not-yet-check-in-view-missions-button")
            
            navigate_button_text = navigate_button.text
            expected_text = LANGUAGE_SETTINGS[self.language]["daily_mission"]["view_missions"]
            
            self.assertEqual(navigate_button_text, expected_text, f"Expected button text '{expected_text}', got '{navigate_button_text}'")
            
            self.driver.execute_script("arguments[0].scrollIntoView(true);", navigate_button)
            navigate_button.click()
            
            self.verify_navigation("missions")
            
            self.logger.info("Successfully navigated to missions page")
            
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")
    
    def test_22_HomePagePopUpMissionGoButtonRedirectsToDeposit(self):
        """Test to verify that clicking 'Go' button from home modal redirects to the deposit page."""
        try:
            self.logger.info("Starting mission redirection test...")
            
            # Setup user and get missions
            self.setup_test_user(register_new=False, close_mission=False)
            missions = self.get_mission_api()
            
            # Skip if no missions available
            if not missions:
                self.logger.warning("No missions returned from API, skipping test")
                self.skipTest("No missions available")
            
            # Find a deposit mission
            deposit_mission = self.find_mission_by_condition_type(missions, "topup")
            if not deposit_mission:
                self.logger.warning("No deposit missions found, skipping test")
                self.skipTest("No deposit missions available")
            
            mission_id = deposit_mission.get("id")
            self.logger.info(f"Found deposit mission: ID {mission_id} - {deposit_mission['title']}")
            
            
            go_button = self.driver.find_element(By.ID, f"not-yet-check-in-redirect-button-{mission_id}")
            
            self.logger.info("Clicking Go button...")
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", go_button)
            go_button.click()
            
            self.verify_navigation("wallet/deposit")
            
            self.logger.info(f"Successfully redirected to {self.driver.current_url}")
            
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")
    
    def test_23_HomePagePopUpMissionGoButtonRedirectsToWithdraw(self):
        """Test to verify that clicking 'Go' button from home modal redirects to the withdraw page."""
        try:
            self.logger.info("Starting mission redirection test...")
            
            # Setup user and get missions
            self.setup_test_user(register_new=False, close_mission=False)
            missions = self.get_mission_api()
            
            # Skip if no missions available
            if not missions:
                self.logger.warning("No missions returned from API, skipping test")
                self.skipTest("No missions available")
            
            # Find a withdraw mission
            withdraw_mission = self.find_mission_by_condition_type(missions, "withdraw")
            if not withdraw_mission:
                self.logger.warning("No withdraw missions found, skipping test")
                self.skipTest("No withdraw missions available")
            
            mission_id = withdraw_mission.get("id")
            self.logger.info(f"Found withdrawal mission: ID {mission_id} - {withdraw_mission['title']}")
            
            
            go_button = self.driver.find_element(By.ID, f"not-yet-check-in-redirect-button-{mission_id}")
            
            self.logger.info("Clicking Go button...")
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", go_button)
            go_button.click()
            
            self.verify_navigation("wallet/withdrawal")
            
            self.logger.info(f"Successfully redirected to {self.driver.current_url}")
            
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")
    
    def test_24_HomePagePopUpMissionGoButtonRedirectsToGames(self):
        """Test to verify that clicking 'Go' button from home modal redirects to the games page."""
        try:
            self.logger.info("Starting mission redirection test...")
            
            # Setup user and get missions
            self.setup_test_user(register_new=False, close_mission=False)
            missions = self.get_mission_api()
            
            # Skip if no missions available
            if not missions:
                self.logger.warning("No missions returned from API, skipping test")
                self.skipTest("No missions available")
            
            # Find a loss mission
            loss_mission = self.find_mission_by_condition_type(missions, "loss")
            if not loss_mission:
                self.logger.warning("No loss missions found, skipping test")
                self.skipTest("No loss missions available")
            
            mission_id = loss_mission.get("id")
            self.logger.info(f"Found loss mission: ID {mission_id} - {loss_mission['title']}")
            
            
            go_button = self.driver.find_element(By.ID, f"not-yet-check-in-redirect-button-{mission_id}")
            
            self.logger.info("Clicking Go button...")
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", go_button)
            go_button.click()
            
            self.verify_navigation("games")
            
            self.logger.info(f"Successfully redirected to {self.driver.current_url}")
            
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")
    
    def test_25_HomePagePopUpMissionProgressUpdatesAfterDeposit(self):
        """Test to verify that mission progress updates correctly after making a deposit."""
        try:
            self.logger.info("Starting mission progress tracking test...")
            
            # Setup user and get missions
            self.setup_test_user(register_new=False, close_mission=False)
            
            # use this when test multiple language and browser
            userID = self.get_user_id()
            self.simulate_reset_mission_next_day(userID)
            
            initial_missions = self.get_mission_api()
            
            # Skip if no missions available
            if not initial_missions:
                self.logger.warning("No missions returned from API, skipping test")
                self.skipTest("No missions available")
            
            # Find a topup mission
            deposit_mission = self.find_mission_by_type(initial_missions, "topup")
            if not deposit_mission:
                self.logger.warning("No topup missions found, skipping test")
                self.skipTest("No topup missions available")
            
            mission_id = deposit_mission.get("id")
            initial_progress = float(deposit_mission.get("progress", 0))
            
            self.logger.info(f"Selected mission ID {mission_id} with initial progress {initial_progress}")
            
            # Make deposit
            # try_count = 2
            
            # for _ in range(try_count):
            #     deposit_amount = 30
            #     self.make_deposit(deposit_amount)
            
            deposit_amount = 30
            self.make_deposit(deposit_amount)
                
            self.navigate_to_home_and_handle_popups(close_mission=False)
            
            # Verify progress updated
            expected_progress = initial_progress + deposit_amount
            updated_progress, _ = self.verify_mission_progress_popup(mission_id, expected_progress)
            
            # Check that progress has increased
            self.assertGreater(updated_progress, initial_progress, 
                             f"Mission progress did not increase after deposit")
            
            self.logger.info("Successfully verified mission progress updates after deposit")
            
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")
    
    def test_26_HomePagePopUpTopUpMissionCompletionAndRewardClaim(self):
        """Test to verify topup mission completion and reward claiming functionality."""
        self.logger.info("Starting topup mission completion and reward claim test...")
        
        # Setup user and get missions
        self.setup_test_user(register_new=True,close_mission=False)
        
        initial_missions = self.get_mission_api()
        
        # Skip if no missions available
        if not initial_missions:
            self.logger.warning("No missions returned from API, skipping test")
            self.skipTest("No missions available")
        self.logger.info(f"Initial missions: {initial_missions}")
        # Find a topup mission
        topup_mission = self.find_mission_by_type(initial_missions, "topup")
        if not topup_mission:
            self.logger.warning("No topup missions found, skipping test")
            self.skipTest("No topup missions available")
        
        mission_id = topup_mission.get("id")
        target_amount = int(float(topup_mission.get("target", 30)))
        initial_progress = int(float(topup_mission.get("progress", 0)))
        
        
        self.logger.info(f"Selected mission for testing: ID {mission_id}")
        self.logger.info(f"Target amount: {target_amount}, Initial progress: {initial_progress}")
        
        # # Get initial balances before completing the mission
        self.navigate_to_home_and_handle_popups(close_mission=False)
        
        # Calculate deposit amount needed and complete mission if necessary
        amount_needed = target_amount - initial_progress
        if amount_needed <= 0:
            self.logger.info("Mission already completed, proceeding to claiming")
        else:
            try_count = 2
            for _ in range(try_count):
                # Make deposit to complete mission
                deposit_amount = max(30, amount_needed)
                self.logger.info(f"Making deposit of {deposit_amount} to complete mission")
                self.make_deposit(deposit_amount)
                
                self.wait_for_deposit_processing(timeout=2)
        
        initial_balances = self.get_all_balances()
        
        # Navigate to missions page
        self.navigate_to_home_and_handle_popups(close_mission=False)
        
        # Verify mission is completed
        progress, target = self.verify_mission_progress_popup(mission_id)
        self.assertGreaterEqual(
            progress, target, 
            f"Mission not completed. Progress: {progress}, Target: {target}"
        )
        
        # Claim reward
        claimed = self.claim_mission_reward_popup(mission_id)
        if not claimed:
            self.skipTest("Mission reward already claimed or not available for claiming")
        
        # Verify mission is marked as claimed
        self.verify_mission_claimed_status_popup(mission_id)
        
         # Get reward value from the API data
        reward_value, reward_type = self.get_reward(topup_mission)
        self.logger.info(f"Expected reward: {reward_value} {reward_type}")
        
        # Get balances after claiming reward
        self.navigate_to_home_and_handle_popups()
        final_balances = self.get_all_balances()
        
        # Verify the correct reward was received
        self.verify_reward_received(reward_type, reward_value, initial_balances, final_balances)
    
    def test_27_HomePagePopUpAttemptToClaimAgainAfterClaimed(self):
        """Test to verify that a completed and already claimed mission cannot be claimed again."""
        try:
            self.logger.info("Starting test for attempting to claim an already claimed mission...")
            
            # Setup user and get missions
            self.setup_test_user(register_new=True, close_mission=False)
            
            initial_missions = self.get_mission_api()
            
            # Skip if no missions available
            if not initial_missions:
                self.logger.warning("No missions returned from API, skipping test")
                self.skipTest("No missions available")
            # Find a topup mission
            topup_mission = self.find_mission_by_type(initial_missions, "topup")
            if not topup_mission:
                self.logger.warning("No topup missions found, skipping test")
                self.skipTest("No topup missions available")
            
            mission_id = topup_mission.get("id")
            target_amount = int(float(topup_mission.get("target", 30)))
            initial_progress = int(float(topup_mission.get("progress", 0)))
            
            self.logger.info(f"Selected mission for testing: ID {mission_id}")
            self.logger.info(f"Target amount: {target_amount}, Initial progress: {initial_progress}")
            
            # # Get initial balances before completing the mission
            self.navigate_to_home_and_handle_popups()
            
            # Calculate deposit amount needed and complete mission if necessary
            amount_needed = target_amount - initial_progress

            try_count = 2
            for _ in range(try_count):  
                # Make deposit to complete mission
                deposit_amount = max(30, amount_needed)
                self.logger.info(f"Making deposit of {deposit_amount} to complete mission")
                self.make_deposit(deposit_amount)
                
                # Allow time for the system to process the deposit
                self.wait_for_deposit_processing(timeout=2)
                
            # Navigate to missions page
            self.navigate_to_home_and_handle_popups()
            initial_balances = self.get_all_balances()
            
            self.navigate_to_home_and_handle_popups()
            self.navigate_to_missions_page()
            
            # Verify mission is completed
            progress, target = self.verify_mission_progress(mission_id)
            self.assertGreaterEqual(
                progress, target, 
                f"Mission not completed. Progress: {progress}, Target: {target}"
            )
            
            # Claim reward
            claimed = self.claim_mission_reward(mission_id)
            if not claimed:
                self.skipTest("Mission reward already claimed or not available for claiming")
            
            # Verify mission is marked as claimed
            self.verify_mission_claimed_status(mission_id)
            
            # Navigate to missions page
            self.navigate_to_home_and_handle_popups(close_mission=False)
            
            try_count = 2
            
            for _ in range(try_count):
                # Find the claimed mission card
                mission_element = self.driver.find_element(By.ID, f"not-yet-check-in-mission-title-{mission_id}")
                claim_button = self.driver.find_element(By.ID, f"not-yet-check-in-claim-button-{mission_id}")
                
                # Verify button text is "Claimed"
                button_text = claim_button.find_element(By.CSS_SELECTOR, ".MuiTypography-root").text
                claimed_text = LANGUAGE_SETTINGS[self.language]["daily_mission"]["claimed"]
                self.assertEqual(claimed_text, button_text, f"Expected button text '{claimed_text}', got '{button_text}'")
                
                # Verify button is disabled
                self.assertFalse(claim_button.is_enabled(), "Claim button should be disabled for claimed mission")
                
                # Try to click the button anyway (this should have no effect since it's disabled)
                try:
                    claim_button.click()
                    self.logger.info("Attempted to click disabled 'Claimed' button")
                except Exception as e:
                    self.logger.info(f"As expected, couldn't click disabled button: {str(e)}")
                    
                self.navigate_to_home_and_handle_popups(close_mission=False)
                time.sleep(2)
            
            # Get reward value from the API data
            reward_value, reward_type = self.get_reward(topup_mission)
            
            # Get balances after claiming reward
            self.navigate_to_home_and_handle_popups()
            final_balances = self.get_all_balances()
            
            # Verify the correct reward was received
            self.verify_reward_received(reward_type, reward_value, initial_balances, final_balances)
            
        except NoSuchElementException as e:
            self.logger.error(f"Element not found: {str(e)}")
            self.fail(f"Test failed - element not found: {str(e)}")
        except AssertionError as e:
            self.logger.error(f"Assertion failed: {str(e)}")
            self.fail(f"Test failed - assertion error: {str(e)}")
        except TimeoutException as e:
            # Only fail for timeouts not related to the expected absence of popups
            if "swal2-popup" not in str(e):
                self.logger.error(f"Timeout waiting for element: {str(e)}")
                self.fail(f"Test failed - timeout waiting for element: {str(e)}")
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with unexpected error: {str(e)}")
    
if __name__ == "__main__":
    unittest.main()