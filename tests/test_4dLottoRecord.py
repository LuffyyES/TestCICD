import os
import random
import unittest
import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from config.constant import API_URL, FOUR_D_PRIZES, LANGUAGE_SETTINGS
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
from datetime import datetime, timedelta
import json

class Test4dLottoRecord(BaseTest):

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
            handler = logging.FileHandler('4d_lotto_record.log')
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
        
        
        userID = self.get_user_id()
        self.add_4d_cards_api(userID, 25)
        
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
    
    def navigate_to_home_and_handle_popups(self, close_mission=True):
        """Navigate to home page and handle any popups."""
        self.driver.get(self.url)
        self.annoucement_close_button()
        self.daily_checkin_close_button(close_mission)
    
    def check_if_today_date_in_element(self):
        # First find the parent card element
        card_element = self.driver.find_element(By.ID, "numberLottCard")
        
        # Format today's date in the same format as in the HTML (DD/MM/YYYY)
        today_date_str = datetime.now().strftime("%d/%m/%Y")
        self.logger.info(f"Today's date string: {today_date_str}")
        
        # Find all paragraph elements within the card
        paragraph_elements = card_element.find_elements(By.TAG_NAME, "p")
        
        # Check if any paragraph contains today's date
        for element in paragraph_elements:
            if today_date_str in element.text:
                self.logger.info(f"Found today's date in element: {element.text}")
                return True
        
        self.logger.warning(f"Today's date ({today_date_str}) not found in any paragraph element")
        return False
    
    def click_number_stack(self):
        number_card = self.driver.find_element(By.ID, "numberStack")
        wait = WebDriverWait(self.driver, 10)
        # Wait until the element is clickable
        wait.until(EC.element_to_be_clickable(number_card))
        self.driver.execute_script("arguments[0].click();", number_card)
    
    def enter_number_card(self, need_click_stack=True, need_verify_number_card=True, need_delete_existing_number=False, value_enter="", expected_value=""):
        if need_click_stack:
            self.click_number_stack()
        time.sleep(2)
        number_cards = self.driver.find_elements(By.CSS_SELECTOR, "[id^='four-digit-']")
        self.logger.info(f"Found {len(number_cards)} number cards in the UI")
        self.assertEqual(len(number_cards), 4, "Number of cards is not correct")
        
        for number_card in number_cards:
            number_card.click()
            if need_delete_existing_number:
                self.logger.info("Deleting existing number")
                # Method 1: Standard clear() method
                self.logger.info("Method 1: Standard clear() method")
                number_card.clear()

                # Method 2: Send CTRL+A and then DELETE/BACKSPACE
                self.logger.info("Method 2: Send CTRL+A and then DELETE/BACKSPACE")
                number_card.send_keys(Keys.CONTROL + 'a')
                number_card.send_keys(Keys.DELETE)  # or Keys.BACK_SPACE

                # Method 3: JavaScript clear
                self.logger.info("Method 3: JavaScript clear")
                self.driver.execute_script("arguments[0].value = '';", number_card)

                # Method 4: Detailed interaction
                self.logger.info("Method 4: Detailed interaction")
                number_card.click()
                number_card.send_keys(Keys.HOME)
                number_card.send_keys(Keys.SHIFT + Keys.END)
                number_card.send_keys(Keys.DELETE)
                
            number_card.send_keys(value_enter)
        
        if need_verify_number_card:
            self.verify_number_card(number_cards, expected_value)
    
    def verify_number_card(self, number_cards, expected_value):
        for index, number_card in enumerate(number_cards):
            value = number_card.get_attribute("value")
            self.logger.info(f"Value in card {index}: {value}")
            self.assertEqual(str(value), str(expected_value), f"Digit in field {index} is incorrect")
            
    def generate_4d_record(self, number_of_records, four_d_number=None):
        
        for _ in range(number_of_records):
            platforms = "GD"
            
            random_date = datetime.now() - timedelta(days=random.randint(0, 4))
            date_time_str = random_date.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
            
            if four_d_number is None:
                random_number = random.randint(1000, 9999)
            else:
                random_number = four_d_number
            
            random_amount = random.choice([0.5, 1.0, 1.5])
            
            self.bet_4d_api(random_number, date_time_str, platforms, "whitelabel", "coupon", "2", B=random_amount)
        
    
    def test_01_InfoShown(self):
        try:
            self.logger.info("Starting 4D Lotto Record test...")
            self.setup_test_user(register_new=True)
            
            self.navigate_to_4d_tabs()
            
            self.wait_for_element(By.ID, "numberLottCard")
            
            number_card = self.driver.find_element(By.ID, "numberStack")
            wait = WebDriverWait(self.driver, 10)
            # Wait until the element is clickable
            wait.until(EC.element_to_be_clickable(number_card))
            
            # Find all number cards in UI
            number_cards = self.driver.find_elements(By.CSS_SELECTOR, "[id^='numberBox-']")
            self.logger.info(f"Found {len(number_cards)} number cards in the UI")
            self.assertEqual(len(number_cards), 4, "Number of cards is not correct")
            
            # Check if today's date appears in the card element
            has_today_date = self.check_if_today_date_in_element()
            self.assertTrue(has_today_date, "Today's date not found in the element")
            
            prizes = FOUR_D_PRIZES
            self.logger.info(f"Prizes: {prizes}")
            
            for i, prize in enumerate(prizes):
                if i <= 2:
                    self.logger.info(f"Prize {i}: {prize}")
                    prize_element = self.driver.find_element(By.ID, f"prizeText-{i}")
                    prize_text = prize_element.text.replace(" ", "").replace("RM", "").replace(",", "")
                    self.assertEqual(prize_text, str(prize), f"Prize text for {i} is not correct")
                else:
                    i = i - 3
                    self.logger.info(f"Prize {i}: {prize}")
                    prize_element = self.driver.find_element(By.ID, f"specialPrizeValue-{i}")
                    prize_text = prize_element.text.replace(" ", "").replace("RM", "").replace(",", "")
                    self.assertEqual(prize_text, str(prize), f"Prize text for {i} is not correct")

        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")
    
    def test_02_EnterNumber(self):
        try:
            self.logger.info("Starting 4D Lotto Record test...")
            self.setup_test_user(register_new=True)
            
            self.navigate_to_4d_tabs()
            self.wait_for_element(By.ID, "numberLottCard")
            
            self.enter_number_card(value_enter="1", expected_value="1")
            
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")
    
    def test_03_EnterAlphabet(self):
        try:
            self.logger.info("Starting 4D Lotto Record test...")
            self.setup_test_user(register_new=True)
            
            self.navigate_to_4d_tabs()

            self.enter_number_card("A", "")
            
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")
    
    def test_04_BetEmptyNumber(self):
        try:
            self.logger.info("Starting 4D Lotto Bet test...")
            self.setup_test_user(register_new=True)
            self.navigate_to_4d_tabs()
            
            self.wait_for_element(By.ID, "numberLottCard")
            time.sleep(2)
            
            bet_button = self.driver.find_element(By.ID, "betButton")
            self.driver.execute_script("arguments[0].click();", bet_button)
            
            time.sleep(2)
            
            try:
                self.wait_for_element(By.ID, "closeButtonStep1", timeout=15)
                self.fail("Bet should not be successful")
            except:
                self.logger.info("Bet failed as expected")
            
            self.enter_number_card(need_click_stack=False, need_verify_number_card=False, value_enter="", expected_value="")
            
            bet_button = self.driver.find_element(By.ID, "betButton")
            self.driver.execute_script("arguments[0].click();", bet_button)
            
            time.sleep(2)
            
            try:
                self.wait_for_element(By.ID, "closeButtonStep1", timeout=15)
                self.fail("Bet should not be successful")
            except:
                self.logger.info("Bet failed as expected")
                
            self.logger.info("4D Lotto Bet test completed successfully")
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")

    def test_05_VerifyNumberOf4dCardsSame(self):
        actions = ActionChains(self.driver)

        try:
            self.logger.info("Starting 4D Lotto Record test...")
            self.setup_test_user(register_new=True)
            self.navigate_to_4d_tabs()
            cards_in_tab = self.driver.find_element(By.ID, "totalCardNumberText").text.split(LANGUAGE_SETTINGS[self.language]["check_in"][":"])[1]
            self.logger.info(f"Cards in tab: {cards_in_tab}")
            
            bet_button = self.driver.find_elements(By.ID, "betButton")
            actions.move_to_element(bet_button[0]).click().perform()

            cards_in_modal = self.driver.find_element(By.ID, "totalCardNumber").text.split(LANGUAGE_SETTINGS[self.language]["check_in"][":"])[1]
            
            self.logger.info(f"Cards in modal: {cards_in_modal}")
            
            number_cards = self.driver.find_elements(By.CSS_SELECTOR, "[id^='four-digit-']")
            self.logger.info(f"Found {len(number_cards)} number cards in the UI")
            self.assertEqual(len(number_cards), 4, "Number of cards is not correct")
            
            for number_card in number_cards:
                actions.move_to_element(number_card).click().perform()
                number_card.send_keys("1")
            
            bet_button = self.driver.find_elements(By.ID, "betButton")
            actions.move_to_element(bet_button[1]).click().perform()
            time.sleep(2)
            
            time.sleep(3)
            
            remaining_text = self.driver.find_element(By.ID, "totalCardNumberStep1").text
            number_of_cards_step1 = remaining_text.split(LANGUAGE_SETTINGS[self.language]["check_in"][":"])[1].strip()
            
            self.logger.info(f"Cards in step 1: {number_of_cards_step1}")
            
            self.assertTrue(cards_in_modal == cards_in_tab == number_of_cards_step1, "Number of cards is not correct")
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")
    
    def test_06_AddAndMinusButton(self):
        actions = ActionChains(self.driver)
        try:
            self.logger.info("Starting 4D Lotto Add and Minus Button test...")
            self.setup_test_user(register_new=True)
            self.navigate_to_4d_tabs()
            
            self.wait_for_element(By.ID, "numberLottCard")
            time.sleep(2)
            random_number = random.randint(0, 9)
            
            self.enter_number_card(value_enter=random_number, expected_value=random_number)
            
            bet_button = self.driver.find_elements(By.ID, "betButton")
            self.driver.execute_script("arguments[0].click();", bet_button[1])
            time.sleep(2)
            
            # Get the initial card count values
            remaining_text = self.driver.find_element(By.ID, "totalCardNumberStep1").text
            card_remain_before = remaining_text.split(LANGUAGE_SETTINGS[self.language]["check_in"][":"])[1].strip()
            initial_remain_count = int(card_remain_before)
            self.logger.info(f"Initial cards remaining: {initial_remain_count}")
            
            # Initial card count in bet should be 1
            initial_bet_count = int(self.driver.find_element(By.ID, "cardNumberBox").text)
            self.assertEqual(initial_bet_count, 0, "Initial bet card count should be 0")
            
            # Find the add and minus buttons
            add_button = self.driver.find_element(By.ID, "addButton")
            minus_button = self.driver.find_element(By.ID, "removeButton")
            
            # Test the add button
            actions.move_to_element(add_button).click().perform()
            time.sleep(1)
            
            # Verify bet cards increased
            bet_cards = self.driver.find_element(By.ID, "cardNumberBox").text
            self.assertEqual(bet_cards, "1", "After clicking add button, bet card count should be 2")
            
            # Verify remaining cards decreased
            remaining_text = self.driver.find_element(By.ID, "totalCardNumberStep1").text
            card_remain_after_add = remaining_text.split(LANGUAGE_SETTINGS[self.language]["check_in"][":"])[1].strip()
            self.assertEqual(int(card_remain_after_add), initial_remain_count - 1, 
                            "Remaining cards should decrease by 1 after adding a card")
            
            # Test the minus button
            actions.move_to_element(minus_button).click().perform()
            time.sleep(1)
            
            # Verify bet cards decreased
            bet_cards = self.driver.find_element(By.ID, "cardNumberBox").text
            self.assertEqual(bet_cards, "0", "After clicking minus button, bet card count should be 1")
            
            # Verify remaining cards increased
            remaining_text = self.driver.find_element(By.ID, "totalCardNumberStep1").text
            card_remain_after_minus = remaining_text.split(LANGUAGE_SETTINGS[self.language]["check_in"][":"])[1].strip()
            self.assertEqual(int(card_remain_after_minus), initial_remain_count, 
                            "Remaining cards should increase back to original count after removing a card")
            
            # Test that number doesn't become negative when minus button is clicked at zero
            self.logger.info("Testing that card count doesn't become negative...")
            # Ensure bet card count is at 0
            while int(self.driver.find_element(By.ID, "cardNumberBox").text) > 0:
                actions.move_to_element(minus_button).click().perform()
            
            # Try clicking minus button when count is already 0
            actions.move_to_element(minus_button).click().perform()
            time.sleep(1)
            
            # Verify bet cards still 0 and not negative
            bet_cards = self.driver.find_element(By.ID, "cardNumberBox").text
            self.assertEqual(bet_cards, "0", "Bet card count should not go below 0")
            
            # Verify remaining cards unchanged
            remaining_text = self.driver.find_element(By.ID, "totalCardNumberStep1").text
            card_remain_after_zero_minus = remaining_text.split(LANGUAGE_SETTINGS[self.language]["check_in"][":"])[1].strip()
            self.assertEqual(int(card_remain_after_zero_minus), initial_remain_count, 
                            "Remaining cards should not change when trying to remove from 0 bet cards")
            
            # Test maximum cards (add until we can't add more)
            for i in range(initial_remain_count):
                actions.move_to_element(add_button).click().perform()
            
            # Verify bet cards
            bet_cards = self.driver.find_element(By.ID, "cardNumberBox").text
            expected_max = initial_remain_count
            self.assertEqual(int(bet_cards), expected_max, 
                            f"Maximum bet card count should be {expected_max}")
            
            # Verify remaining cards is zero
            remaining_text = self.driver.find_element(By.ID, "totalCardNumberStep1").text
            card_remain_after_max = remaining_text.split(LANGUAGE_SETTINGS[self.language]["check_in"][":"])[1].strip()
            self.assertEqual(int(card_remain_after_max), 0, 
                            "Remaining cards should be 0 after adding all available cards")
            
            self.logger.info("Add and Minus Button test completed successfully")
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")
    
    def test_07_Bet4d(self):
        actions = ActionChains(self.driver)
        try:
            self.logger.info("Starting 4D Lotto Bet test...")
            self.setup_test_user(register_new=True)
            self.navigate_to_4d_tabs()
            
            self.wait_for_element(By.ID, "numberLottCard")
            time.sleep(2)
            cards_in_tab_before = int(self.driver.find_element(By.ID, "totalCardNumberText").text.split(LANGUAGE_SETTINGS[self.language]["check_in"][":"])[1])
            self.logger.info(f"Cards in tab before: {cards_in_tab_before}")
            random_number = random.randint(0, 9)
            bet_number = f"{random_number}{random_number}{random_number}{random_number}"  # Store your actual bet number
            
            self.enter_number_card(value_enter=random_number, expected_value=random_number)
            
            bet_button = self.driver.find_elements(By.ID, "betButton")
            self.driver.execute_script("arguments[0].click();", bet_button[1])
            
            time.sleep(2)
            
            add_button = self.driver.find_element(By.ID, "addButton")
            minus_button = self.driver.find_element(By.ID, "removeButton")
            
            actions.move_to_element(add_button).click().perform()
            time.sleep(1)
            actions.move_to_element(add_button).click().perform()
            time.sleep(1)
            actions.move_to_element(add_button).click().perform()
            time.sleep(1)
            
            actions.move_to_element(minus_button).click().perform()
            time.sleep(1)
            
            cards_number = self.driver.find_element(By.ID, "cardNumberBox").text
            self.assertEqual(cards_number, "2", "Number of cards is not correct")
            
            confirm_button = self.driver.find_element(By.ID, "confirmButton")
            actions.move_to_element(confirm_button).click().perform()
            
            self.wait_for_element(By.ID, "betSuccess", timeout=15)
            
            today_date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            today_short_date = datetime.now().strftime("%y%m%d %H:%M")  # For receipt format (e.g., 250318)
            
            record_button = self.driver.find_element(By.ID, "checkBetRecordButton")
            actions.move_to_element(record_button).click().perform()
            
            time.sleep(10)
            
            # Find all records and click the most recent one
            ui_records = self.driver.find_elements(By.CSS_SELECTOR, "[id^='lotto-history-item-']")
            new_record = ui_records[0]
            
            # Validate the record in the list
            record_id = new_record.get_attribute("id")
            card_name = new_record.find_element(By.ID, f"{record_id}-title").text
            timestamp = new_record.find_element(By.ID, f"{record_id}-date").text
            card_count = new_record.find_element(By.ID, f"{record_id}-amount").text
            
            self.assertEqual(card_name, LANGUAGE_SETTINGS[self.language]["4d"]["card_name"], "Card name mismatch for record")
            card_count_expected = f"{LANGUAGE_SETTINGS[self.language]['4d']['4d_card']}x2"
            self.assertEqual(card_count.replace(" ", ""), card_count_expected.replace(" ", ""), "Card count mismatch for record")
            
            # Get the ID from the record URL
            href = new_record.get_attribute("href")
            record_id = href.split("id=")[1]
            
            # Verify timestamp is recent
            ui_timestamp = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
            api_timestamp_obj = datetime.strptime(today_date_str, "%Y-%m-%d %H:%M:%S")
            time_diff = abs((ui_timestamp - api_timestamp_obj).total_seconds())
            self.assertTrue(time_diff <= 60, 
                        f"Timestamp difference too large ({time_diff} seconds) for record. UI: {timestamp}, Now: {today_date_str}")
            
            # Click to view the receipt details
            actions.move_to_element(new_record).click().perform()
            time.sleep(3)
            
            # Verify URL contains correct ID
            current_url = self.driver.current_url
            self.assertTrue(f"id={record_id}" in current_url, f"URL does not contain correct ID. URL: {current_url}, Expected ID: {record_id}")
            
            receipt_title = self.driver.find_elements(By.ID, f"receipt-card-inv-{record_id}")
            
            # Verify receipt details
            receipt_card_name = receipt_title[1].text
            self.assertEqual(receipt_card_name, LANGUAGE_SETTINGS[self.language]["4d"]["card_name"], "Receipt card name mismatch")
            
            # Check for invoice number format
            invoice_text = receipt_title[0].text
            self.assertTrue(invoice_text.startswith("Inv:"), "Invoice number format incorrect")
                        
            # Check date format
            receipt_date = self.driver.find_element(By.ID, f"receipt-card-date-{record_id}").text
            self.assertTrue(today_short_date in receipt_date, f"Receipt date doesn't match today's date. Receipt: {receipt_date}, Expected: {today_short_date}")
            
            # Check lottery brand (GD)
            brand_text = self.driver.find_element(By.ID, f"receipt-card-brands-{record_id}").text
            self.assertTrue("GD" in brand_text, "Lottery brand incorrect")
            
            # Check bet number and card count
            bet_info = self.driver.find_element(By.ID, f"receipt-card-betting-number-{record_id}").text
            bet_parts = bet_info.split("=")
            receipt_bet_number = bet_parts[0].strip()
            receipt_card_count = bet_parts[1].strip()
            
            # Verify bet number matches what we entered (may need to adjust this based on how numbers are entered and displayed)
            self.assertEqual(receipt_bet_number, bet_number, "Bet number in receipt incorrect")
            self.assertEqual(receipt_card_count, f"2 x {LANGUAGE_SETTINGS[self.language]['4d']['4d_card_receipt']}", "Card count in receipt incorrect")
            
            # Check total amount
            total_amount = self.driver.find_element(By.ID, f"receipt-card-total-amount-{record_id}").text
            self.assertTrue("RM1.00" in total_amount, "Total amount incorrect")
            
            self.navigate_to_home_and_handle_popups()
            self.navigate_to_4d_tabs()
            cards_in_tab_after = int(self.driver.find_element(By.ID, "totalCardNumberText").text.split(LANGUAGE_SETTINGS[self.language]["check_in"][":"])[1])
            self.logger.info(f"Cards in tab after: {cards_in_tab_after}")
            self.assertEqual(cards_in_tab_after, cards_in_tab_before - 2, "Cards in tab after is not correct")
            
            self.logger.info("4D Lotto Bet test completed successfully")
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")
    
    def test_08_ChangeNumber(self):
        try:
            self.logger.info("Starting 4D Lotto Change Number test...")
            self.setup_test_user(register_new=True)
            self.navigate_to_4d_tabs()
            
            self.wait_for_element(By.ID, "numberLottCard")
            
            self.enter_number_card(value_enter="1", expected_value="1")
            
            bet_button = self.driver.find_elements(By.ID, "betButton")
            bet_button[1].click()
            
            time.sleep(2)
            bet_number = self.driver.find_element(By.ID, "fourDigitDisplay").text
            
            self.assertEqual(bet_number, "1111", "Bet number is not correct")
            time.sleep(1)
            
            change_button = self.driver.find_element(By.ID, "backButton")
            change_button.click()
            
            time.sleep(2)
            
            self.enter_number_card(need_click_stack=False, need_delete_existing_number=True, value_enter="2", expected_value="2")
            
            bet_button = self.driver.find_elements(By.ID, "betButton")
            bet_button[1].click()
            
            time.sleep(2)
            
            bet_number = self.driver.find_element(By.ID, "fourDigitDisplay").text
            
            self.assertEqual(bet_number, "2222", "Bet number is not correct")
        
            self.logger.info("4D Lotto Change Number test completed successfully")
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")
    
    def test_09_4dHistoryRecord(self):
        try:
            self.logger.info("Starting 4D Lotto Record test...")
            self.setup_test_user(register_new=True)
            
            self.generate_4d_record(number_of_records=3)
                
            # Get records from API
            records_total_api = self.get_4d_history_api(four_d_number="", start_date="", end_date="", is_won="", page="", per_page="").get("total")
            records_list_api = self.get_4d_history_api(four_d_number="", start_date="", end_date="", is_won="", page="", per_page=records_total_api).get("data")
            self.logger.info(f"Records list API: {records_list_api}")
            
            self.navigate_to_profile_menu("profile-menu-lotto_history")
            
            time.sleep(5)
            
            # Wait for UI elements to load
            self.wait_for_element(By.CSS_SELECTOR, "a[id^='lotto-history-item-']")
            
            # Get all list items from UI
            ui_records = self.driver.find_elements(By.CSS_SELECTOR, "a[id^='lotto-history-item-']")
            
            # Verify number of records matches
            self.assertEqual(len(ui_records), len(records_list_api), 
                            f"UI shows {len(ui_records)} records but API returned {len(records_list_api)}")
            
            # Compare data for each record
            for i, (ui_record, api_record) in enumerate(zip(ui_records, records_list_api)):
                record_id = ui_record.get_attribute("id")
                # Extract data from UI
                card_name = ui_record.find_element(By.ID, f"{record_id}-title").text
                timestamp = ui_record.find_element(By.ID, f"{record_id}-date").text
                card_count = ui_record.find_element(By.ID, f"{record_id}-amount").text
                
                # Format API timestamp to match UI format
                api_timestamp = api_record.get("created_at", "").replace(" ", " ")
                
                # Verify individual fields
                self.assertEqual(card_name, LANGUAGE_SETTINGS[self.language]["4d"]["card_name"], f"Card name mismatch for record {i+1}")
                self.assertEqual(timestamp, api_timestamp, f"Timestamp mismatch for record {i+1}")
                card_count_expected = f"{LANGUAGE_SETTINGS[self.language]['4d']['4d_card']}x{api_record.get('card_used')}"
                self.assertEqual(card_count.replace(" ", ""), card_count_expected.replace(" ", ""), 
                                f"Card count mismatch for record {i+1}")
                
                # Verify href contains correct ID
                href = ui_record.get_attribute("href")
                self.assertTrue(f"id={api_record.get('id')}" in href, 
                            f"Incorrect ID in href for record {i+1}")
            
            self.logger.info("4D Lotto Record test completed successfully")
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")

    
    def test_10_WinRecord(self):
        actions = ActionChains(self.driver)
        try:
            self.logger.info("Starting Win Recordtest...")
            self.setup_test_user(register_new=True)
            
            self.generate_4d_record(1)
            
            # Get records from API
            records_total_api = self.get_4d_history_api(four_d_number="", start_date="", end_date="", is_won="", page="", per_page="").get("total")
            records_list_api = self.get_4d_history_api(four_d_number="", start_date="", end_date="", is_won="", page="", per_page=records_total_api).get("data")
            
            self.logger.info(f"Records list API: {records_list_api}")
            
            self.update_bet_result(records_list_api[0].get("id"), "win", "100")
            
            # Get records from API
            records_total_api = self.get_4d_history_api(four_d_number="", start_date="", end_date="", is_won="1", page="", per_page="").get("total")
            records_list_api = self.get_4d_history_api(four_d_number="", start_date="", end_date="", is_won="1", page="", per_page=records_total_api).get("data")
            
            if len(records_list_api) == 0:
                self.fail("No records found")
            
            self.navigate_to_profile_menu("profile-menu-lotto_history")
            
            # Find the tab by its text and href
            tab = self.wait_for_element(By.CSS_SELECTOR, "a[href='?tab=2']")
            time.sleep(2)
            actions.move_to_element(tab).click().perform()
            
            time.sleep(1)
            
            # Wait for UI elements to load
            self.wait_for_element(By.CSS_SELECTOR, "a[id^='lotto-win-item-']")
            
            # Get all list items from UI
            ui_records = self.driver.find_elements(By.CSS_SELECTOR, "a[id^='lotto-win-item-']")
            
            # Verify number of records matches
            self.assertEqual(len(ui_records), len(records_list_api), 
                            f"UI shows {len(ui_records)} records but API returned {len(records_list_api)}")
            
            # Compare data for each record
            for i, (ui_record, api_record) in enumerate(zip(ui_records, records_list_api)):
                record_id = ui_record.get_attribute("id")
                # Extract data from UI
                card_name = ui_record.find_element(By.ID, f"{record_id}-title").text
                card_desc = ui_record.find_element(By.ID, f"{record_id}-bet-number").text
                timestamp = ui_record.find_element(By.ID, f"{record_id}-date").text
                win_amount = ui_record.find_element(By.ID, f"{record_id}-amount").text
                
                # Format API timestamp to match UI format
                api_timestamp = api_record.get("created_at", "").replace(" ", " ")
                
                # Verify individual fields
                self.assertEqual(card_name, LANGUAGE_SETTINGS[self.language]["4d"]["win_title"], f"Card name mismatch for record {i+1}")
                self.assertEqual(card_desc, LANGUAGE_SETTINGS[self.language]["4d"]["win_desc"].format(bet_number=api_record.get('betting_number')), f"Card desc mismatch for record {i+1}")
                self.assertEqual(timestamp, api_timestamp, f"Timestamp mismatch for record {i+1}")
                self.assertEqual(win_amount, 
                                 f"+RM{int(float(api_record.get('total_rewards'))) if float(api_record.get('total_rewards')).is_integer() else float(api_record.get('total_rewards'))}", 
                                 f"Card count mismatch for record {i+1}")
                
                # Verify href contains correct ID
                href = ui_record.get_attribute("href")
                self.assertTrue(f"id={api_record.get('id')}" in href, 
                            f"Incorrect ID in href for record {i+1}")
            
            self.logger.info("4D Lotto Record test completed successfully")
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")
    
    def test_11_WinReceipt(self):
        try:
            self.logger.info("Starting 4D Lotto Win Receipt test...")
            self.setup_test_user(register_new=True)
            
            self.generate_4d_record(1)
            records_total_api = self.get_4d_history_api(four_d_number="", start_date="", end_date="", is_won="", page="", per_page="").get("total")
            records_list_api = self.get_4d_history_api(four_d_number="", start_date="", end_date="", is_won="", page="", per_page="").get("data")
            
            if len(records_list_api) == 0:
                self.fail("No records found")
            
            self.update_bet_result(records_list_api[0].get("id"), "win", "100")
            
            self.navigate_to_profile_menu("profile-menu-lotto_history")
            time.sleep(1)
            
            # Find the tab by its text and href
            tab = self.driver.find_element(By.CSS_SELECTOR, "a[href='?tab=2']")
            time.sleep(2)
            tab.click()
            
            time.sleep(1)
            
            # Get records from API
            records_total_api = self.get_4d_history_api(four_d_number="", start_date="", end_date="", is_won="1", page="", per_page="").get("total")
            records_list_api = self.get_4d_history_api(four_d_number="", start_date="", end_date="", is_won="1", page="", per_page=records_total_api).get("data")
            if len(records_list_api) == 0:
                self.fail("No records found")
            
            self.logger.info(f"Records list API: {records_list_api}")
            
            first_record = records_list_api[0]
            card_used = first_record.get("card_used")
            bet_number = first_record.get("betting_number")
            created_at = first_record.get("created_at")
            brands = first_record.get("brands")
            date_str = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")
            short_date = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S").strftime("%y%m%d %H:%M")
            
            time.sleep(10)
            
            # Find all records and click the most recent one
            ui_records = self.driver.find_elements(By.CSS_SELECTOR, "a[id^='lotto-win-item-']")
            new_record = ui_records[0]
            # Get the ID from the record URL
            record_id = new_record.get_attribute("href").split("id=")[1]
            # Click to view the receipt details
            new_record.click()
            time.sleep(3)
            
            # Verify URL contains correct ID
            current_url = self.driver.current_url
            self.assertTrue(f"id={record_id}" in current_url, f"URL does not contain correct ID. URL: {current_url}, Expected ID: {record_id}")
            
            receipt_title = self.driver.find_elements(By.ID, f"receipt-card-inv-{record_id}")
            
            # Verify receipt details
            receipt_card_name = receipt_title[1].text
            self.assertEqual(receipt_card_name, LANGUAGE_SETTINGS[self.language]["4d"]["card_name"], "Receipt card name mismatch")
            
            # Check for invoice number format
            invoice_text = receipt_title[0].text
            self.assertTrue(invoice_text.startswith("Inv:"), "Invoice number format incorrect")
                        
            # Check date format
            receipt_date = self.driver.find_element(By.ID, f"receipt-card-date-{record_id}").text
            self.assertTrue(short_date in receipt_date, f"Receipt date doesn't match today's date. Receipt: {receipt_date}, Expected: {short_date}")
            
            # Check lottery brand (GD)
            brand_text = self.driver.find_element(By.ID, f"receipt-card-brands-{record_id}").text
            self.assertTrue(brands in brand_text, f"Expected {brands} in {brand_text}")
            
            # Check bet number and card count
            bet_info = self.driver.find_element(By.ID, f"receipt-card-betting-number-{record_id}").text
            bet_parts = bet_info.split("=")
            receipt_bet_number = bet_parts[0].strip()
            receipt_card_count = bet_parts[1].strip()
            
            # Verify bet number matches what we entered (may need to adjust this based on how numbers are entered and displayed)
            self.assertEqual(receipt_bet_number, bet_number, "Bet number in receipt incorrect")
            self.assertEqual(receipt_card_count, f"{card_used} x {LANGUAGE_SETTINGS[self.language]['4d']['4d_card_receipt']}", "Card count in receipt incorrect")
            
            # Check total amount
            total_amount = self.driver.find_element(By.ID, f"receipt-card-total-amount-{record_id}").text
            self.assertTrue(f"RM{float(first_record.get('total_amount'))}" in total_amount, "Total amount incorrect")
            
            self.logger.info("4D Lotto Bet test completed successfully")
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")
            
    def test_12_Search4DRecord(self):
        try:
            self.logger.info("Starting 4D Lotto Search Record test...")
            self.setup_test_user(register_new=True)
            
            self.generate_4d_record(1, four_d_number="1111")
            self.generate_4d_record(1, four_d_number="1222")
            self.generate_4d_record(3)
            self.navigate_to_profile_menu("profile-menu-lotto_history")
            
            records_total_api = self.get_4d_history_api(four_d_number="", start_date="", end_date="", is_won="1", page="", per_page="").get("total")
            records_list_api = self.get_4d_history_api(four_d_number="", start_date="", end_date="", is_won="1", page="", per_page=records_total_api).get("data")
            
            # Find and input search term
            search_input = self.driver.find_element(By.ID, ":R34qflajttrafkq:")
            search_input.send_keys("1")
            
            # Wait for search results
            time.sleep(2)
            
            # Find all search result records
            search_results = self.driver.find_elements(By.CSS_SELECTOR, "a.MuiListItem-root")
            
            if len(search_results) == 0:
                self.fail("No search results found")
            
            # Log total number of results
            self.logger.info(f"Found {len(search_results)} search results")
            
            # Iterate through each search result
            for i, result in enumerate(search_results):
                href = result.get_attribute("href")
                record_id = href.split("id=")[1]
                self.logger.info(f"Record ID: {record_id}")
                
                # Find the matching record in records_list_api
                matching_record = next((record for record in records_list_api if str(record['id']) == record_id), None)
                
                if matching_record:
                    bet_number = matching_record['betting_number']
                    self.logger.info(f"Bet Number: {bet_number}")
                    
                    self.assertTrue(bet_number.startswith("1"), 
                        f"Bet number {bet_number} does not start with 1 for result {i+1}")
                    
                    # Further processing with bet_number
                else:
                    self.logger.warning(f"No matching record found for ID: {record_id}")
            
            
            self.logger.info("4D Lotto Search Record test completed successfully")
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")
    
    def test_13_Filter4DRecordByStartAndEndDates(self):
        try:
            self.logger.info("Starting 4D Lotto Filter Record By Date test...")
            self.setup_test_user(register_new=True)

            self.generate_4d_record(10)
            self.navigate_to_profile_menu("profile-menu-lotto_history")
            
            records_total_api_before = self.get_4d_history_api(four_d_number="", start_date="", end_date="", is_won="", page="", per_page="").get("total")
            records_list_api_before = self.get_4d_history_api(four_d_number="", start_date="", end_date="", is_won="", page="", per_page=records_total_api_before).get("data")
            
            if len(records_list_api_before) == 0:
                self.fail("No records found")
            
            # Get today's date
            today_date = datetime.now()
            yesterday_date = today_date - timedelta(days=1)

            # Format dates as they appear in the data-day attribute
            today_str = today_date.strftime('%Y-%m-%d')
            yesterday_str = yesterday_date.strftime('%Y-%m-%d')

            # Click calendar icon
            calendar_icon = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='CalendarMonthIcon']")
            calendar_icon.click()
            time.sleep(1)  # Wait for calendar to appear

            # Click on the dates
            self.driver.find_element(By.CSS_SELECTOR, f"[data-day='{yesterday_str}'] button").click()
            self.driver.find_element(By.CSS_SELECTOR, f"[data-day='{today_str}'] button").click()
            
            time.sleep(1)
            
            ok_button = self.driver.find_element(By.XPATH, "//button[text()='OK']")
            ok_button.click()
            
            # Wait for search results
            time.sleep(2)
            
            # Find all search result records
            filter_results = self.driver.find_elements(By.CSS_SELECTOR, "a.MuiListItem-root")
            
            if len(filter_results) == 0:
                self.fail("No search results found")
            
            self.logger.info(f"Found {len(filter_results)} filter results")
            
            records_total_api_after = self.get_4d_history_api(four_d_number="", start_date=yesterday_str, end_date=today_str, is_won="", page="", per_page="").get("total")
            records_list_api_after = self.get_4d_history_api(four_d_number="", start_date=yesterday_str, end_date=today_str, is_won="", page="", per_page=records_total_api_after).get("data")
            
            if len(records_list_api_after) == 0:
                self.fail("No records found")

            
            for i, result in enumerate(records_list_api_after):
                try:
                    record_id = result.get("id")
                    
                    self.driver.find_element(By.ID, f"lotto-history-item-{record_id}")

                except Exception as e:
                    self.logger.error(f"Error finding record card for ID: {record_id}")
                    self.fail(f"Error finding record card for ID: {record_id}")
            
            self.logger.info("4D Lotto Filter Record By Start And End Dates test completed successfully")
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")
    
    def test_14_Filter4DRecordByOneDate(self):
        try:
            self.logger.info("Starting 4D Lotto Filter Record By One Date test...")
            self.setup_test_user(register_new=True)

            self.generate_4d_record(10)
            self.navigate_to_profile_menu("profile-menu-lotto_history")
            
            records_total_api_before = self.get_4d_history_api(four_d_number="", start_date="", end_date="", is_won="", page="", per_page="").get("total")
            
            if int(records_total_api_before) == 0:
                self.fail("No records found")
            
            # Get today's date
            today_date = datetime.now()

            # Format dates as they appear in the data-day attribute
            today_str = today_date.strftime('%Y-%m-%d')

            # Click calendar icon
            calendar_icon = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='CalendarMonthIcon']")
            calendar_icon.click()
            time.sleep(1)  # Wait for calendar to appear

            # Click on the dates
            self.driver.find_element(By.CSS_SELECTOR, f"[data-day='{today_str}'] button").click()
            
            time.sleep(1)
            
            ok_button = self.driver.find_element(By.XPATH, "//button[text()='OK']")
            ok_button.click()
            
            # Wait for search results
            time.sleep(2)
            
            # Find all search result records
            filter_results = self.driver.find_elements(By.CSS_SELECTOR, "a.MuiListItem-root")
            
            if len(filter_results) == 0:
                self.fail("No search results found")
            
            self.logger.info(f"Found {len(filter_results)} filter results")
            
            records_total_api_after = self.get_4d_history_api(four_d_number="", start_date=today_str, end_date=today_str, is_won="", page="", per_page="").get("total")
            records_list_api_after = self.get_4d_history_api(four_d_number="", start_date=today_str, end_date=today_str, is_won="", page="", per_page=records_total_api_after).get("data")
            
            if int(records_total_api_after) == 0:
                self.fail("No records found")

            
            for i, result in enumerate(records_list_api_after):
                try:
                    record_id = result.get("id")
                    
                    self.driver.find_element(By.ID, f"lotto-history-item-{record_id}")

                except Exception as e:
                    self.logger.error(f"Error finding record card for ID: {record_id}")
                    self.fail(f"Error finding record card for ID: {record_id}")
            
            self.logger.info("4D Lotto Filter Record By Start And End Dates test completed successfully")
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")
    
    def test_15_SearchWinRecord(self):
        try:
            self.logger.info("Starting 4D Lotto Search Win Record test...")
            self.setup_test_user(register_new=True)
            
            self.generate_4d_record(1, four_d_number="1111")
            self.generate_4d_record(1, four_d_number="1222")
            self.generate_4d_record(1, four_d_number="1333")
            self.generate_4d_record(7)
            
            all_records_total_api = self.get_4d_history_api(four_d_number="", start_date="", end_date="", is_won="", page="", per_page="").get("total")
            all_records_list_api = self.get_4d_history_api(four_d_number="", start_date="", end_date="", is_won="", page="", per_page=all_records_total_api).get("data")
            
            if int(all_records_total_api) == 0:
                self.fail("No records found")
                
            # Separate indices into two groups
            valid_indices = []  
            other_indices = []   

            for i, record in enumerate(all_records_list_api):
                try:
                    bettting_number = record.get("betting_number", "")
                    in_range = False
                    
                    if str(bettting_number).startswith("1"):
                        valid_indices.append(i)
                        in_range = True
                            
                    if not in_range:
                        other_indices.append(i)
                        
                except (json.JSONDecodeError, KeyError):
                    # If we can't parse the dates, consider it as "other"
                    other_indices.append(i)

            # Get random indices from each category
            valid_to_select = min(2, len(valid_indices))
            other_to_select = min(2, len(other_indices))

            selected_recent = []
            selected_other = []

            if valid_to_select > 0:
                selected_recent = random.sample(valid_indices, valid_to_select)
                
            if other_to_select > 0:
                selected_other = random.sample(other_indices, other_to_select)

            # Combine the selections
            selected_indices = selected_recent + selected_other
            
            if len(selected_indices) == 0:
                self.fail("No records found")

            # Use the selected indices
            for index in selected_indices:
                record_id = all_records_list_api[index]["id"]
                self.update_bet_result(record_id, "win", 100)
                
            win_records_total_api = self.get_4d_history_api(four_d_number="", start_date="", end_date="", is_won="1", page="", per_page="").get("total")
            win_records_list_api = self.get_4d_history_api(four_d_number="", start_date="", end_date="", is_won="1", page="", per_page=win_records_total_api).get("data")
            
            if int(win_records_total_api) == 0:
                self.fail("No win records found")
            
            self.navigate_to_profile_menu("profile-menu-lotto_history")
            tab = self.driver.find_element(By.CSS_SELECTOR, "a[href='?tab=2']")
            time.sleep(2)
            tab.click()
            time.sleep(2)
            # Find and input search term
            search_input = self.driver.find_element(By.ID, ":R34qflajttrafkq:")
            search_input.send_keys("1")
            
            # Wait for search results
            time.sleep(2)
            
            # Find all search result records
            search_results = self.driver.find_elements(By.CSS_SELECTOR, "a.MuiListItem-root")
            
            if len(search_results) == 0:
                self.fail("No search results found")
            
            # Log total number of results
            self.logger.info(f"Found {len(search_results)} search results")
            
            # Iterate through each search result
            for i, result in enumerate(search_results):
                href = result.get_attribute("href")
                record_id = href.split("id=")[1]
                self.logger.info(f"Record ID: {record_id}")
                
                # Find the matching record in records_list_api
                matching_record = next((record for record in win_records_list_api if str(record['id']) == record_id), None)
                
                if matching_record:
                    bet_number = matching_record['betting_number']
                    self.logger.info(f"Bet Number: {bet_number}")
                    
                    self.assertTrue(bet_number.startswith("1"), 
                        f"Bet number {bet_number} does not start with 1 for result {i+1}")
                    
                    # Further processing with bet_number
                else:
                    self.logger.warning(f"No matching record found for ID: {record_id}")
            
            
            self.logger.info("4D Lotto Search Record test completed successfully")
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")
    
    def test_16_FilterWinRecordByStartAndEndDates(self):
        try:
            self.logger.info("Starting 4D Lotto Filter Win Record By Date test...")
            self.setup_test_user(register_new=True)

            self.generate_4d_record(10)
            
            all_records_total_api = self.get_4d_history_api(four_d_number="", start_date="", end_date="", is_won="", page="", per_page="").get("total")
            all_records_list_api = self.get_4d_history_api(four_d_number="", start_date="", end_date="", is_won="", page="", per_page=all_records_total_api).get("data")
            
            if int(all_records_total_api) == 0:
                self.fail("No records found")
            
            # Get today's date
            today_date = datetime.now()
            yesterday_date = today_date - timedelta(days=1)

            # Format dates as they appear in the data-day attribute
            today_str = today_date.strftime('%Y-%m-%d')
            yesterday_str = yesterday_date.strftime('%Y-%m-%d')
            
            # Separate indices into two groups: within date range and outside date range
            recent_indices = []  # For records between yesterday and today
            other_indices = []   # For records outside that range

            for i, record in enumerate(all_records_list_api):
                # Parse bet_dates from string to list
                try:
                    bet_dates = json.loads(record["bet_dates"])
                    in_range = False
                    
                    for date_str in bet_dates:
                        # Check if date is between yesterday and today
                        if yesterday_str <= date_str <= today_str:
                            recent_indices.append(i)
                            in_range = True
                            break  # We found a date in range
                            
                    if not in_range:
                        other_indices.append(i)
                        
                except (json.JSONDecodeError, KeyError):
                    # If we can't parse the dates, consider it as "other"
                    other_indices.append(i)

            # Get random indices from each category
            recent_to_select = min(2, len(recent_indices))
            other_to_select = min(2, len(other_indices))

            selected_recent = []
            selected_other = []

            if recent_to_select > 0:
                selected_recent = random.sample(recent_indices, recent_to_select)
                
            if other_to_select > 0:
                selected_other = random.sample(other_indices, other_to_select)

            # Combine the selections
            selected_indices = selected_recent + selected_other
            
            if len(selected_indices) == 0:
                self.fail("No records found")

            # Use the selected indices
            for index in selected_indices:
                record_id = all_records_list_api[index]["id"]
                self.update_bet_result(record_id, "win", 100)

                
            self.navigate_to_profile_menu("profile-menu-lotto_history")
            tab = self.driver.find_element(By.CSS_SELECTOR, "a[href='?tab=2']")
            time.sleep(2)
            tab.click()
            time.sleep(2)
            # Click calendar icon
            calendar_icon = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='CalendarMonthIcon']")
            calendar_icon.click()
            time.sleep(1)  # Wait for calendar to appear

            # Click on the dates
            self.driver.find_element(By.CSS_SELECTOR, f"[data-day='{yesterday_str}'] button").click()
            self.driver.find_element(By.CSS_SELECTOR, f"[data-day='{today_str}'] button").click()
            
            time.sleep(1)
            
            ok_button = self.driver.find_element(By.XPATH, "//button[text()='OK']")
            ok_button.click()
            
            # Wait for search results
            time.sleep(2)
            
            # Find all search result records
            filter_results = self.driver.find_elements(By.CSS_SELECTOR, "a.MuiListItem-root")
            
            if len(filter_results) == 0:
                self.fail("No search results found")
            
            self.logger.info(f"Found {len(filter_results)} filter results")
            
            win_records_total_api = self.get_4d_history_api(four_d_number="", start_date=yesterday_str, end_date=today_str, is_won="1", page="", per_page="").get("total")
            win_records_list_api = self.get_4d_history_api(four_d_number="", start_date=yesterday_str, end_date=today_str, is_won="1", page="", per_page=win_records_total_api).get("data")
            
            if int(win_records_total_api) == 0:
                self.fail("No records found")

            
            for i, result in enumerate(win_records_list_api):
                try:
                    record_id = result.get("id")
                    
                    self.driver.find_element(By.ID, f"lotto-win-item-{record_id}")

                except Exception as e:
                    self.logger.error(f"Error finding record card for ID: {record_id}")
                    self.fail(f"Error finding record card for ID: {record_id}")
            
            self.logger.info("4D Lotto Filter Record By Start And End Dates test completed successfully")
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")
    
    def test_17_FilterWinRecordByOneDate(self):
        try:
            self.logger.info("Starting 4D Lotto Filter Win Record By One Date test...")
            self.setup_test_user(register_new=True)

            self.generate_4d_record(10)
            
            all_records_total_api= self.get_4d_history_api(four_d_number="", start_date="", end_date="", is_won="", page="", per_page="").get("total")
            all_records_list_api = self.get_4d_history_api(four_d_number="", start_date="", end_date="", is_won="", page="", per_page=all_records_total_api).get("data")
            
            if int(all_records_total_api) == 0:
                self.fail("No records found")
            
            # Get today's date
            today_date = datetime.now()

            # Format dates as they appear in the data-day attribute
            today_str = today_date.strftime('%Y-%m-%d')
            
            # Separate indices into two groups: within date range and outside date range
            recent_indices = []  # For records between yesterday and today
            other_indices = []   # For records outside that range

            for i, record in enumerate(all_records_list_api):
                # Parse bet_dates from string to list
                try:
                    bet_dates = json.loads(record["bet_dates"])
                    in_range = False
                    
                    for date_str in bet_dates:
                        # Check if date is between yesterday and today
                        if date_str == today_str:
                            recent_indices.append(i)
                            in_range = True
                            break  # We found a date in range
                            
                    if not in_range:
                        other_indices.append(i)
                        
                except (json.JSONDecodeError, KeyError):
                    # If we can't parse the dates, consider it as "other"
                    other_indices.append(i)

            # Get random indices from each category
            recent_to_select = min(2, len(recent_indices))
            other_to_select = min(2, len(other_indices))

            selected_recent = []
            selected_other = []

            if recent_to_select > 0:
                selected_recent = random.sample(recent_indices, recent_to_select)
                
            if other_to_select > 0:
                selected_other = random.sample(other_indices, other_to_select)

            # Combine the selections
            selected_indices = selected_recent + selected_other
            
            if len(selected_indices) == 0:
                self.fail("No records found")

            # Use the selected indices
            for index in selected_indices:
                record_id = all_records_list_api[index]["id"]
                self.update_bet_result(record_id, "win", 100)

                
            self.navigate_to_profile_menu("profile-menu-lotto_history")
            tab = self.driver.find_element(By.CSS_SELECTOR, "a[href='?tab=2']")
            time.sleep(2)
            tab.click()
            time.sleep(2)
            # Click calendar icon
            calendar_icon = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='CalendarMonthIcon']")
            calendar_icon.click()
            time.sleep(1)  # Wait for calendar to appear

            # Click on the dates
            self.driver.find_element(By.CSS_SELECTOR, f"[data-day='{today_str}'] button").click()
            
            time.sleep(1)
            
            ok_button = self.driver.find_element(By.XPATH, "//button[text()='OK']")
            ok_button.click()
            
            # Wait for search results
            time.sleep(2)
            
            # Find all search result records
            filter_results = self.driver.find_elements(By.CSS_SELECTOR, "a.MuiListItem-root")
            
            if len(filter_results) == 0:
                self.fail("No search results found")
            
            self.logger.info(f"Found {len(filter_results)} filter results")
            
            win_records_total_api = self.get_4d_history_api(four_d_number="", start_date=today_str, end_date=today_str, is_won="1", page="", per_page="").get("total")
            win_records_list_api = self.get_4d_history_api(four_d_number="", start_date=today_str, end_date=today_str, is_won="1", page="", per_page=win_records_total_api).get("data")
            
            if int(win_records_total_api) == 0:
                self.fail("No records found")

            
            for i, result in enumerate(win_records_list_api):
                try:
                    record_id = result.get("id")
                    
                    self.driver.find_element(By.ID, f"lotto-win-item-{record_id}")

                except Exception as e:
                    self.logger.error(f"Error finding record card for ID: {record_id}")
                    self.fail(f"Error finding record card for ID: {record_id}")
            
            self.logger.info("4D Lotto Filter Record By Start And End Dates test completed successfully")
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")

    def test_18_RewardAfterWin(self):
        try:
            self.logger.info("Starting 4D Lotto Reward After Win test...")
            self.setup_test_user(register_new=True)
            
            self.generate_4d_record(3)
            
            wallet_balance_before = self.getWalletBalance()
            
            records_total_api = self.get_4d_history_api(four_d_number="", start_date="", end_date="", is_won="", page="", per_page="").get("total")
            records_list_api = self.get_4d_history_api(four_d_number="", start_date="", end_date="", is_won="", page="", per_page=records_total_api).get("data")
            
            if len(records_list_api) == 0:
                self.fail("No records found")
            
            prize = 100
            self.update_bet_result(records_list_api[0].get("id"), "win", prize)
            
            win_records_total_api = self.get_4d_history_api(four_d_number="", start_date="", end_date="", is_won="1", page="", per_page="").get("total")
            win_records_list_api = self.get_4d_history_api(four_d_number="", start_date="", end_date="", is_won="1", page="", per_page=win_records_total_api).get("data")
            
            if len(win_records_list_api) == 0:
                self.fail("No win records found")
            
            wallet_balance_after = self.getWalletBalance()
            
            self.verifyReward(reward_type="FREE CREDIT", reward_before=wallet_balance_before, reward_after=wallet_balance_after, expected_increase=prize)
            
            self.logger.info("4D Lotto Reward After Win test completed successfully")
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")
            
    def test_19_CheckLiveRoomRemaining4DCard(self):
        try:
            self.logger.info("Starting 4D Lotto Check Live Room Remaining 4D Card test...")
            self.setup_test_user(register_new=True)
            
            self.navigate_to_4d_tabs()

            cards_in_tab = self.driver.find_element(By.ID, "totalCardNumberText").text.split(LANGUAGE_SETTINGS[self.language]["check_in"][":"])[1]
            self.logger.info(f"Cards in tab: {cards_in_tab}")
            
            self.navigate_to_live_page()
            time.sleep(2)
            
            live_link = self.driver.find_element(By.CLASS_NAME, "live_link")
            live_link.click()
            
            time.sleep(2)
            
            close_button = self.driver.find_element(By.CSS_SELECTOR, "button.mui-theme-7pi2se")
            close_button.click()
            
            time.sleep(2)
            
            WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.ID, "bobolive-fourD-widget")))
            four_d_tab = self.driver.find_element(By.ID, "bobolive-fourD-widget")
            self.driver.execute_script("arguments[0].click();", four_d_tab)
            
            time.sleep(5)
            
            cards_in_live_room = self.driver.find_element(By.CSS_SELECTOR, "p.mui-theme-1vsn7f2, p.mui-theme-1u7a8fq").text
            self.logger.info(f"Cards in live room: {cards_in_live_room}")
            
            self.assertEqual(cards_in_live_room, cards_in_tab, "Cards in live room is not equal to cards in tab")
            
            self.logger.info("4D Lotto Check Live Room Remaining 4D Card test completed successfully")
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")
    
    
            
            
            
if __name__ == "__main__":
    unittest.main()
