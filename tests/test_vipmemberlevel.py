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
import math
import re
class TestVipMemberLevel(BaseTest):

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
            handler = logging.FileHandler('vip_member_level.log')
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
        

    def tearDown(self):
        if hasattr(self, "driver"):
            self.driver.quit()
    
    def setup_test_user(self, register_new=False):
        """Set up test user - either create new or use existing"""
        if register_new:
            self.username, self.password = self.test_init.register_new_account()
        else:
            self.username = "LuffyTest5"
            self.password = "LuffyTest5"
        
        self.navigate_to_login_page()
        self.perform_login(self.username, self.password)
        return self.username, self.password
    
    # Helper methods
    def wait_for_element(self, by, value, timeout=10):
        """Wait for an element to be present and return it"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return element
        except TimeoutException:
            self.logger.error(f"Element not found: {by}={value}")
            raise
    
    def make_deposit(self, amount):
        """Make a deposit of the specified amount"""
        self.logger.info(f"Making a deposit of RM{amount}...")
        user_id = self.get_user_info("id")
        self.test_init.submit_deposit_api(username=self.username, password=self.password, amount=amount)
        self.handleDeposit(user_id)
    
    def extract_amount_from_text(self, text):
        match = re.search(r'RM(\d+(\.\d+)?)', text)
        if match:
            amount = match.group(1)
            return amount
        else:
            self.fail("No amount found in subtitle card text")
    
    def test_01_CurrentVipAndNextVipProfilePage(self):
        try:
            self.logger.info("Starting vip status profile page test...")
            self.setup_test_user(register_new=False)
            
            self.navigate_to_profile_page(self.language)
            self.wait_for_element(By.ID, "level-card")
            
            user_current_vip = self.get_user_info("current_vip")
            user_next_vip = self.get_user_info("next_vip")
            
            self.logger.info(f"Current VIP: {user_current_vip}")
            self.logger.info(f"Next VIP: {user_next_vip}")
            
            ui_current_vip = self.driver.find_element(By.ID, "vip-chip").text
            self.logger.info(f"Current VIP: {ui_current_vip}")
            
            ui_next_vip = self.driver.find_element(By.ID, "member-rank").text
            self.logger.info(f"Next VIP: {ui_next_vip}")
            
            ui_next_vip_text = self.driver.find_element(By.ID, "next-level-text").text
            
            self.assertEqual(ui_current_vip, user_current_vip, "Current VIP level is not correct")
            self.assertEqual(ui_next_vip, user_next_vip, "Next VIP level is not correct")
            self.assertEqual(ui_next_vip_text, user_next_vip, "Next VIP level text is not correct")

        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")
    
    def test_02_RemainingTopupAmountProfilePage(self):
        try:
            self.logger.info("Starting remaining topup amount profile page test...")
            self.setup_test_user(register_new=False)
            
            self.navigate_to_profile_page(self.language)
            
            user_next_vip = self.get_user_info("next_vip")
            all_vip_levels = self.get_vip_levels()
            self.logger.info(f"All VIP levels: {all_vip_levels}")
            
            user_topup_amount = self.get_user_info("paysum")
            self.logger.info(f"User topup amount: {user_topup_amount}")
            
            remaining_amount = 0
            
            for vip_level in all_vip_levels:
                if vip_level["vipname"] == user_next_vip:
                    remaining_amount = float(vip_level["recharge"]) - float(user_topup_amount)
                    self.logger.info(f"Remaining amount to reach next VIP: {remaining_amount}")
                else:
                    self.logger.info(f"User is not in the next VIP level")
            
            ui_remaining_amount = float(self.driver.find_element(By.ID, "recharge-amount-link").text.replace("RM", "").replace(",", ""))
            self.logger.info(f"UI remaining amount: {ui_remaining_amount}")
            
            self.assertEqual(remaining_amount, ui_remaining_amount, "Remaining amount is not correct")
            
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")
    
    def test_03_ProgressBarProfilePage(self):
        try:
            self.logger.info("Starting progress bar profile page test...")
            self.setup_test_user(register_new=False)
            
            self.navigate_to_profile_page(self.language)
            
            user_next_vip = self.get_user_info("next_vip")
            all_vip_levels = self.get_vip_levels()
            self.logger.info(f"All VIP levels: {all_vip_levels}")
            
            user_topup_amount = self.get_user_info("paysum")
            self.logger.info(f"User topup amount: {user_topup_amount}")
            
            recharge_amount = 0
            
            for vip_level in all_vip_levels:
                if vip_level["vipname"] == user_next_vip:
                    recharge_amount = float(vip_level["recharge"])
                    self.logger.info(f"Recharge amount: {recharge_amount}")
                else:
                    self.logger.info(f"User is not in the next VIP level")
            
            percentage = int(math.ceil((float(user_topup_amount) / float(recharge_amount)) * 100))
            self.logger.info(f"Calculated Percentage: {percentage}")
            
            progress_bar = self.driver.find_element(By.ID, "recharge-progress")
            ui_percentage = int(progress_bar.get_attribute("aria-valuenow"))
            self.logger.info(f"UI percentage: {ui_percentage}")
            
            self.assertTrue(abs(percentage - ui_percentage) <= 1, "Progress percentage is not correct")
            
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")
    
    def test_04_CheckVIPCardInfoUntilCurrentVIP(self):
        try:
            self.logger.info("Starting VIP level up test...")
            self.setup_test_user(register_new=False)

            self.navigate_to_profile_menu("level-card")
            time.sleep(1)
            
            all_vip_levels = self.get_vip_levels()
            self.logger.info(f"All VIP levels: {all_vip_levels}")
            
            all_vip_levels_en = self.get_vip_levels("en")
            self.logger.info(f"All VIP levels (EN): {all_vip_levels_en}")
            
            current_vip = self.get_user_info("current_vip")
            self.logger.info(f"Current VIP: {current_vip}")
            
            current_vip_en = self.get_user_info("current_vip", "en").lower()
            self.logger.info(f"Current VIP (EN): {current_vip_en}")
            
            for i, vip_level in enumerate(all_vip_levels):
                self.logger.info(f"VIP level: {vip_level}")
                self.logger.info(f"VIP level name: {vip_level['vipname']}")
                self.logger.info(f"VIP level recharge: {vip_level['recharge']}")
                vip_name = 'biasa' if vip_level['vipname'] == 'Normal' and self.language == 'bm' else vip_level['vipname'].lower()
                vip_name_en = all_vip_levels_en[i]['vipname'].lower()
                
                vip_card = self.driver.find_element(By.ID, f"vip-rank-{vip_name_en}")
                
                vip_card_text = vip_card.text
                self.logger.info(f"VIP card text: {vip_card_text}")
                
                self.assertTrue(vip_name in vip_card_text.lower(), f"Neither '{vip_name}' nor 'normal' is in the '{vip_card_text}'.lower()")
                
                vip_subtitle = self.driver.find_element(By.ID, f"vip-subtitle-{vip_name_en}").text
                self.logger.info(f"VIP subtitle: {vip_subtitle}")
                
                if i == 0:
                    expected_subtitle = LANGUAGE_SETTINGS[self.language]["vip_member_level"]["normal_subtitle"]
                    self.assertEqual(expected_subtitle, vip_subtitle, "VIP subtitle is not correct")
                else:
                    expected_subtitle = LANGUAGE_SETTINGS[self.language]["vip_member_level"]["surpassed_subtitle"]
                    self.assertEqual(expected_subtitle, vip_subtitle, "VIP subtitle is not correct")
                    progress_bar = self.driver.find_element(By.ID, f"vip-progress-bar-{vip_name_en}")
                    ui_percentage = int(progress_bar.get_attribute("aria-valuenow"))
                    self.logger.info(f"UI percentage: {ui_percentage}")
                    
                    self.assertEqual(ui_percentage, 100, "Progress percentage is not 100")
                
                if vip_name == current_vip.lower():
                    self.logger.info(f"Current VIP level found: {vip_name_en}")
                    break
        
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")
    
    def test_05_CheckVIPCardInfoFromCurrentVIPToLastVIP(self):
        try:
            self.logger.info("Starting VIP level up test...")
            self.setup_test_user(register_new=False)

            self.navigate_to_profile_menu("level-card")
            time.sleep(1)
            
            all_vip_levels = self.get_vip_levels()
            self.logger.info(f"All VIP levels: {all_vip_levels}")
            
            all_vip_levels_en = self.get_vip_levels("en")
            self.logger.info(f"All VIP levels (EN): {all_vip_levels_en}")
            
            current_vip = self.get_user_info("current_vip")
            self.logger.info(f"Current VIP: {current_vip}")
            
            current_vip_en = self.get_user_info("current_vip", "en").lower()
            self.logger.info(f"Current VIP (EN): {current_vip_en}")
            
            user_topup_amount = self.get_user_info("paysum")
            self.logger.info(f"User topup amount: {user_topup_amount}")
            
            start_check_vip = False
            
            count = 0
            
            for i, vip_level in enumerate(all_vip_levels):
                self.logger.info(f"VIP level: {vip_level}")
                self.logger.info(f"VIP level name: {vip_level['vipname']}")
                self.logger.info(f"VIP level recharge: {vip_level['recharge']}")
                vip_name = 'biasa' if vip_level['vipname'] == 'Normal' and self.language == 'bm' else vip_level['vipname'].lower()
                vip_name_en = all_vip_levels_en[i]['vipname'].lower()
                
                if start_check_vip:
                    recharge_amount = float(vip_level['recharge'])
                    topup_more = float(recharge_amount) - float(user_topup_amount)
                    self.logger.info(f"Topup more: {topup_more}")
                    
                    percentage = int(math.floor((float(user_topup_amount) / float(recharge_amount)) * 100))
                    self.logger.info(f"Calculated Percentage: {percentage}")
                    
                    vip_card = self.driver.find_element(By.ID, f"vip-rank-{vip_name_en}")
                    
                    vip_card_text = vip_card.text
                    self.logger.info(f"VIP card text: {vip_card_text}")
                    
                    self.assertTrue(vip_name in vip_card_text.lower(), f"'{vip_name}' not in the '{vip_card_text.lower()}'")
                
                    progress_bar = self.driver.find_element(By.ID, f"vip-progress-bar-{vip_name_en}")
                    ui_percentage = int(progress_bar.get_attribute("aria-valuenow"))
                    self.logger.info(f"UI percentage: {ui_percentage}")
                    
                    self.assertEqual(ui_percentage, percentage, f"Progress percentage is not {percentage}")
                    
                    vip_subtitle = self.driver.find_element(By.ID, f"vip-subtitle-{vip_name_en}").text
                    self.logger.info(f"VIP subtitle: {vip_subtitle}")
                    
                    expected_subtitle = LANGUAGE_SETTINGS[self.language]["vip_member_level"]["topup_subtitle"]
                    self.assertEqual(expected_subtitle.format(topup_more=int(topup_more), next_vip_name=vip_name).lower(), vip_subtitle.lower(), "VIP subtitle is not correct")

                    count += 1
                    
                if vip_name == current_vip.lower():
                    self.logger.info(f"Current VIP level found: {vip_name_en}")
                    start_check_vip = True
            
            if not start_check_vip:
                self.fail("Cannot find current VIP level")
            
            if count == 0:
                self.fail("The current VIP level is the last VIP level")
        
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")

    def test_06_CheckModalInfo(self):
        try:
            self.logger.info("Starting modal info test...")
            self.setup_test_user(register_new=False)
            
            self.navigate_to_profile_menu("level-card")
            
            all_vip_levels = self.get_vip_levels()
            self.logger.info(f"All VIP levels: {all_vip_levels}")
            
            all_vip_levels_en = self.get_vip_levels("en")
            self.logger.info(f"All VIP levels (EN): {all_vip_levels_en}")
            
            for i, vip_level in enumerate(all_vip_levels):
                self.logger.info(f"VIP level: {vip_level}")
                self.logger.info(f"VIP level name: {vip_level['vipname']}")
                self.logger.info(f"VIP level recharge: {vip_level['recharge']}")
                vip_name = 'biasa' if vip_level['vipname'] == 'Normal' and self.language == 'bm' else vip_level['vipname'].lower()
                vip_name_en = all_vip_levels_en[i]['vipname'].lower()
                
                if i != 0:
                    time.sleep(1)
                    details_button = self.driver.find_element(By.ID, f"rank-detail-button-{vip_name_en}")
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", details_button)
                    details_button.click()
                    time.sleep(1)
                    
                    recharge_amount = float(vip_level['recharge'])
                    self.logger.info(f"Recharge amount: {recharge_amount}")
                    
                    modal_title = self.driver.find_element(By.ID, f"vip-modal-rank-{vip_name_en}").text.lower()
                    self.logger.info(f"Modal title: {modal_title}")
                    
                    self.assertIn(vip_name, modal_title, f"'{vip_name}' not in the '{modal_title}'")
                    
                    qualification_text = self.driver.find_element(By.ID, f"vip-modal-qualification-{vip_name_en}").text.lower().replace("  ", " ")
                    qualification_text = qualification_text.rstrip()
                    self.logger.info(f"Qualification text: {qualification_text}")
                    expected_qualification_text = LANGUAGE_SETTINGS[self.language]["vip_member_level"]["qualification_text"].format(
                        recharge_amount="{:.2f}".format(recharge_amount), 
                        vip_name=vip_name
                    ).lower()
                    self.logger.info(f"Expected qualification text: {expected_qualification_text}")
                    self.assertEqual(qualification_text, expected_qualification_text, f"Qualification text is not correct")
                    
                    requirement_text = self.driver.find_element(By.ID, f"vip-modal-requirement-{vip_name_en}").text.lower().replace("  ", " ")
                    requirement_text = requirement_text.rstrip()
                    self.logger.info(f"Requirement text: {requirement_text}")
                    expected_requirement_text = LANGUAGE_SETTINGS[self.language]["vip_member_level"]["requirement_text"].format(
                        recharge_amount="{:.2f}".format(recharge_amount)
                    ).lower()
                    self.logger.info(f"Expected requirement text: {expected_requirement_text}")
                    self.assertEqual(requirement_text, expected_requirement_text, f"Requirement text is not correct")
                    
                    # Close the modal by clicking outside of it
                    backdrop = self.driver.find_element(By.CSS_SELECTOR, ".MuiModal-backdrop")
                    self.driver.execute_script("arguments[0].click();", backdrop)
                    time.sleep(1)
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")
    
    def test_07_CheckModalButton(self):
        try:
            self.logger.info("Starting modal info test...")
            self.setup_test_user(register_new=False)
            
            self.navigate_to_profile_menu("level-card")
            
            all_vip_levels = self.get_vip_levels()
            self.logger.info(f"All VIP levels: {all_vip_levels}")
            
            all_vip_levels_en = self.get_vip_levels("en")
            self.logger.info(f"All VIP levels (EN): {all_vip_levels_en}")
            
            current_vip = self.get_user_info("current_vip")
            self.logger.info(f"Current VIP: {current_vip}")
            
            current_vip_en = self.get_user_info("current_vip", "en").lower()
            self.logger.info(f"Current VIP (EN): {current_vip_en}")
            
            is_next_levels = False
            
            for i, vip_level in enumerate(all_vip_levels):
                self.logger.info(f"VIP level: {vip_level}")
                self.logger.info(f"VIP level name: {vip_level['vipname']}")
                self.logger.info(f"VIP level recharge: {vip_level['recharge']}")
                vip_name = 'biasa' if vip_level['vipname'] == 'Normal' and self.language == 'bm' else vip_level['vipname'].lower()
                vip_name_en = all_vip_levels_en[i]['vipname'].lower()
                
                if i != 0:
                    time.sleep(1)
                    details_button = self.driver.find_element(By.ID, f"rank-detail-button-{vip_name_en}")
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", details_button)
                    details_button.click()
                    time.sleep(1)
                    
                    if is_next_levels:
                        expected_button_text = LANGUAGE_SETTINGS[self.language]["vip_member_level"]["upgrade_button"]
                        button = self.driver.find_element(By.ID, f"vip-modal-button-{vip_name_en}")
                        button_text = button.text
                        
                        self.assertEqual(button_text, expected_button_text, f"Button text is not correct")
                        
                        button.click()
                        
                        # Wait for redirection and verify URL
                        WebDriverWait(self.driver, 15).until(
                            lambda driver: f"/{self.language}/wallet/deposit" in driver.current_url
                        )
                        
                        expected_url_part = f"/{self.language}/wallet/deposit"
                        self.assertIn(expected_url_part, self.driver.current_url,
                                    f"URL redirection failed. Expected URL to contain '{expected_url_part}'")
                        
                        self.logger.info(f"Successfully redirected to {self.driver.current_url}")
                        
                        self.driver.back()
                        time.sleep(1)
                        
                    else:
                        expected_button_text = LANGUAGE_SETTINGS[self.language]["vip_member_level"]["reached_button"]
                        button = self.driver.find_element(By.ID, f"vip-modal-button-{vip_name_en}")
                        button_text = button.text
                        
                        self.assertEqual(button_text, expected_button_text, f"Button text is not correct")

                        aria_disabled = button.get_attribute("aria-disabled")
                        self.assertEqual(aria_disabled, "true", "Button should have aria-disabled='true'")
                        
                        self.logger.info(f"Reached button is disabled")
                        
                        # Close the modal by clicking outside of it
                        backdrop = self.driver.find_element(By.CSS_SELECTOR, ".MuiModal-backdrop")
                        self.driver.execute_script("arguments[0].click();", backdrop)
                        time.sleep(1)
                    
                    if vip_name == current_vip.lower():
                        self.logger.info(f"Current VIP level found: {vip_name_en}")
                        is_next_levels = True

                else:
                    self.logger.info(f"Skipping VIP level: {vip_name_en}")
                        
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")
    
    def test_08_UpdateAfterDeposit(self):
        try:
            self.logger.info("Starting update after deposit test...")
            self.setup_test_user(register_new=True)
            
            self.navigate_to_profile_menu("level-card")
            
            next_vip = self.get_user_info("next_vip", "en")
            self.logger.info(f"Next VIP: {next_vip}")
            
            subtitle_card_text_before = self.driver.find_element(By.ID, f"vip-subtitle-{next_vip.lower()}").text
            self.logger.info(f"Subtitle card text before: {subtitle_card_text_before}")
            
            need_topup_before = float(self.extract_amount_from_text(subtitle_card_text_before))
            self.logger.info(f"Need topup before: {need_topup_before}")
            
            total_topup_amount_before = float(self.get_user_info("paysum"))
            self.logger.info(f"Total topup amount before: {total_topup_amount_before}")
            
            amount_to_topup = 30            
            self.make_deposit(amount_to_topup)
            
            self.driver.refresh()
            
            subtitle_card_text_after = self.driver.find_element(By.ID, f"vip-subtitle-{next_vip.lower()}").text
            self.logger.info(f"Subtitle card text after: {subtitle_card_text_after}")
            
            need_topup_after = float(self.extract_amount_from_text(subtitle_card_text_after))
            self.logger.info(f"Need topup after: {need_topup_after}")
            
            total_topup_amount_after = float(self.get_user_info("paysum"))
            self.logger.info(f"Total topup amount after: {total_topup_amount_after}")
            
            self.assertEqual(total_topup_amount_before + amount_to_topup, total_topup_amount_after, "Total topup amount is not correct")
            
            self.assertEqual(need_topup_before - amount_to_topup, need_topup_after, "Need topup amount is not correct")
        
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")
    
    def test_09_UpgradeLevelAfterDeposit(self):
        try:
            self.logger.info("Starting update after deposit test...")
            self.setup_test_user(register_new=True)
            
            self.navigate_to_profile_menu("level-card")
            
            next_vip = self.get_user_info("next_vip", "en")
            self.logger.info(f"Next VIP: {next_vip}")
            
            subtitle_card_text_before = self.driver.find_element(By.ID, f"vip-subtitle-{next_vip.lower()}").text
            self.logger.info(f"Subtitle card text before: {subtitle_card_text_before}")
            
            need_topup_before = float(self.extract_amount_from_text(subtitle_card_text_before))
            self.logger.info(f"Need topup before: {need_topup_before}")
            
            total_topup_amount_before = float(self.get_user_info("paysum"))
            self.logger.info(f"Total topup amount before: {total_topup_amount_before}")
            
            amount_to_topup = need_topup_before            
            self.make_deposit(amount_to_topup)
            
            self.driver.refresh()
            
            subtitle_card_text_after = self.driver.find_element(By.ID, f"vip-subtitle-{next_vip.lower()}").text
            self.logger.info(f"Subtitle card text after: {subtitle_card_text_after}")
            
            expected_subtitle_card_text_after = LANGUAGE_SETTINGS[self.language]["vip_member_level"]["surpassed_subtitle"]
            self.assertEqual(subtitle_card_text_after, expected_subtitle_card_text_after, "Subtitle card text is not correct")
            
            total_topup_amount_after = float(self.get_user_info("paysum"))
            self.logger.info(f"Total topup amount after: {total_topup_amount_after}")
            
            self.assertEqual(total_topup_amount_before + amount_to_topup, total_topup_amount_after, "Total topup amount is not correct")
                    
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")
    
    def test_10_UpdateAfterDepositProfilePage(self):
        try:
            self.logger.info("Starting update after deposit test...")
            self.setup_test_user(register_new=True)
            
            self.navigate_to_profile_page(self.language)
            self.wait_for_element(By.ID, "level-card")
            
            next_vip = self.get_user_info("next_vip", "en")
            self.logger.info(f"Next VIP: {next_vip}")
            
            ui_remaining_amount_before = float(self.driver.find_element(By.ID, "recharge-amount-link").text.replace("RM", "").replace(",", ""))
            self.logger.info(f"UI remaining amount before: {ui_remaining_amount_before}")
            
            total_topup_amount_before = float(self.get_user_info("paysum"))
            self.logger.info(f"Total topup amount before: {total_topup_amount_before}")
            
            amount_to_topup = 30            
            self.make_deposit(amount_to_topup)
            
            self.driver.refresh()
            
            ui_remaining_amount_after = float(self.driver.find_element(By.ID, "recharge-amount-link").text.replace("RM", "").replace(",", ""))
            self.logger.info(f"UI remaining amount after: {ui_remaining_amount_after}")
            
            total_topup_amount_after = float(self.get_user_info("paysum"))
            self.logger.info(f"Total topup amount after: {total_topup_amount_after}")
            
            self.assertEqual(total_topup_amount_before + amount_to_topup, total_topup_amount_after, "Total topup amount is not correct")
            
            self.assertEqual(ui_remaining_amount_before - amount_to_topup, ui_remaining_amount_after, "Need topup amount is not correct")
        
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")
    
    def test_11_UpgradeAfterDepositProfilePage(self):
        try:
            self.logger.info("Starting update after deposit test...")
            self.setup_test_user(register_new=True)
            
            self.navigate_to_profile_page(self.language)
            self.wait_for_element(By.ID, "level-card")
            
            all_vip_levels = self.get_vip_levels()
            self.logger.info(f"All VIP levels: {all_vip_levels}")
            
            next_vip = self.get_user_info("next_vip")
            self.logger.info(f"Next VIP: {next_vip}")
            
            ui_remaining_amount_before = float(self.driver.find_element(By.ID, "recharge-amount-link").text.replace("RM", "").replace(",", ""))
            self.logger.info(f"UI remaining amount before: {ui_remaining_amount_before}")
            
            total_topup_amount_before = float(self.get_user_info("paysum"))
            self.logger.info(f"Total topup amount before: {total_topup_amount_before}")
            
            amount_to_topup = ui_remaining_amount_before            
            self.make_deposit(amount_to_topup)
            
            self.driver.refresh()
            
            ui_member_level_after = self.driver.find_element(By.ID, "vip-chip").text
            self.logger.info(f"UI member level after: {ui_member_level_after}")
            
            self.assertEqual(ui_member_level_after, next_vip, "Member level is not correct")
            
            ui_remaining_amount_after = float(self.driver.find_element(By.ID, "recharge-amount-link").text.replace("RM", "").replace(",", ""))
            self.logger.info(f"UI remaining amount after: {ui_remaining_amount_after}")
            
            total_topup_amount_after = float(self.get_user_info("paysum"))
            self.logger.info(f"Total topup amount after: {total_topup_amount_after}")
            
            next_vip = self.get_user_info("next_vip")
            self.logger.info(f"Next VIP: {next_vip}")
            
            recharge_amount = 0
            
            for vip_level in all_vip_levels:
                if vip_level["vipname"] == next_vip:
                    recharge_amount = float(vip_level["recharge"])
                    self.logger.info(f"Recharge amount: {recharge_amount}")
                    break
                else:
                    self.logger.info(f"VIP level: {vip_level['vipname']} Skipped")
            
            expected_remaining_amount = recharge_amount - total_topup_amount_after
            self.logger.info(f"Expected remaining amount: {expected_remaining_amount}")
            
            self.assertEqual(ui_remaining_amount_after, expected_remaining_amount, "Remaining amount is not correct")
            
            self.assertEqual(total_topup_amount_before + amount_to_topup, total_topup_amount_after, "Total topup amount is not correct")
                    
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")
        
if __name__ == "__main__":
    unittest.main()
