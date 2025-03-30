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
import tempfile
import requests
from urllib.parse import urlparse
import urllib.parse
import json
import re
from tests.test_init import TestInit

class TestLuckyWheelSpinPage(BaseTest):

    def __init__(self, methodName="runTest", language=None, browser=None):
        super().__init__(methodName)
        self.language = language
        self.browser = browser
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

        file_handler = logging.FileHandler("test_wheelspin_output.log")
        file_handler.setLevel(logging.INFO)

        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        file_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)

        self.logger.propagate = False
        
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
        self.username = CREDENTIALS["valid_user"]["username"]
        self.password = CREDENTIALS["valid_user"]["password"]        

    def tearDown(self):
        if hasattr(self, "driver"):
            self.driver.quit()
    
    def get_api_token(self):
        data = {
            "username": self.username,
            "password": self.password
        }
        response = requests.post(f"{API_URL}/api/login", data=data)
        response.raise_for_status()
        result = response.json().get("data")
        self.token = result['token']
    
    def get_id_api(self):
        headers = {
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
        response = requests.get(f"{CREDENTIALS['BO_base_url']}/api/user", headers=headers)
        return response.json().get("data")["id"]
    
    def get_spin_api(self):
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Language": self.language
        }
        response = requests.get(f"{API_URL}/api/getPrizes?type=wheel", headers=headers)
        response.raise_for_status()
        prizes = response.json().get("data").get("prizes")
        spin_left = response.json().get("data").get("spin_left")
        tnc = response.json().get("data").get("tnc")
        return prizes, spin_left, tnc

    def get_probability_api(self):
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Language": self.language
        }
        response = requests.get(f"{API_URL}/api/getPrizesWithProbability", headers=headers)
        response.raise_for_status()
        data = response.json()
        prizes = data.get("data")
        return prizes
    
    def prize_popup(self):
        try:        
            success_img = WebDriverWait(self.driver,
                                        10).until(EC.visibility_of_element_located((By.ID, "lucky-wheel-success-icon")))
            if not success_img:
                raise Exception("Success image not found in modal")
            
            self.logger.info("Modal is displayed and content is verified.")
            
            return True
        
        except Exception as e:
            return False
        
    def click_spin_button(self):
        spin_button = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.ID, "spin-button"))
        )
        spin_button.click()
        
        time.sleep(5)
        status = self.prize_popup()
        self.assertTrue(status, "Success image not found in modal")
    
    def process_prize_text(self, text):
        self.logger.info(text)
        if "angpau" in text.lower():
            # angpau text: "MYR 118.88 Angpau"
            match = re.search(r'(\d+\.?\d*)', text)
            if match:
                amount = round(float(match.group(1)), 2)
            else:
                self.fail(f"Could not extract amount from Angpau text: {text}")
            type = "FreeCash"
            
        elif "rm" in text.lower():
            # freecash text: "RM3"
            amount = round(float(text.replace("RM", "")),2)
            type = "FreeCash"
            
        elif "4d" in text.lower():
            # 4dcard text: "2 Free 4D Card"
            text_list = text.split()
            amount = int(text_list[0])
            type = "4dCard"
            
        else:
            self.fail("Unknown Prize")
        
        return type, amount
            
    def get_spin_prize(self):
        # Wait for the modal to be visible
        prize_element = WebDriverWait(self.driver, 10).until(
            EC.visibility_of_element_located((By.ID, "prize-text"))
        )
        
        # Get the text from the second p element
        prize_text = prize_element.text
        
        self.logger.info(f"Prize won: {prize_text}")
        if not prize_text:
            self.fail("No prize details found.")
        
        prize, amount = self.process_prize_text(prize_text)
        
        return prize_text, prize, amount

    def verify_winner_list(self):
        try:
            self.clickMiniGameWidget("lucky_wheel")
            
            # First wait for the winner-list container to be visible
            WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located((By.ID, "winner-list")))
            
            # Then find all the individual winner entries (the direct child divs)
            data_entries = self.driver.find_elements(By.CSS_SELECTOR, "#winner-list > div.MuiBox-root")

            # Count the number of data entries
            num_data_entries = len(data_entries)
            
            # Get number of winners expected
            winners_expected = self.get_winner_list_length()
            
            self.assertEqual(num_data_entries, winners_expected, f"{num_data_entries} data entries are shown, not {winners_expected}")

        except Exception as e:
            self.fail(f"An error occurred: {e}")
    
    def get_winner_list_length(self):
        headers = {
            "Authorization": f"Bearer {self.token}"
        }
        response = requests.get(f"{API_URL}/api/prizes/history", headers=headers)
        response.raise_for_status()
        winners = response.json().get("data")
        winner_count = len(winners)
        return winner_count

    def verify_tnc(self):
        self.clickMiniGameWidget("lucky_wheel")
        tnc_elements = WebDriverWait(self.driver, 10).until(
            EC.visibility_of_element_located((By.ID, "tnc"))
        )
        
        tnc_inner = tnc_elements.get_attribute('innerHTML')
        
        _, _, tnc_expected = self.get_spin_api()
                
        self.assertIn(tnc_expected, tnc_inner, "expected TNC not found")
    
        
    def test_01_CantSpinWithoutChance(self):
        self.logger.info("Starting no chance test...")
        driver = self.driver

        try:
            self.username, self.password = self.test_init.register_new_account()
            self.get_api_token()
            self.navigate_to_login_page()
            self.perform_login(self.username, self.password)
            self.get_api_token()
            
            self.clickMiniGameWidget("lucky_wheel")
            
            spin_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.ID, "spin-button"))
            )
            spin_button.click()
            
            status = self.prize_popup()
            
            self.assertTrue(not status, "success modal popped up")
            
        except Exception as e:
            self.fail(f"Test failed with error: {str(e)}")

    def test_02_AddSpinAfterDeposit(self):
        self.logger.info("Starting add spin after deposit test...")
        driver = self.driver

        try:
            self.navigate_to_login_page()
            self.perform_login(self.username, self.password)
            self.get_api_token()
            spin_before = self.checkSpinTicket()
            driver.get(self.url)
            self.annoucement_close_button()
            self.daily_checkin_close_button()
            
            self.logger.info("2. Making initial deposit...")
            userID = self.get_id_api()
            self.test_init.submit_deposit_api(username=self.username, password=self.password, amount=50)
            self.handleDeposit(userID)
            
            spin_after = self.checkSpinTicket()
            self.verifyReward("spin" ,spin_before, spin_after, 1)
            
        except Exception as e:
            self.fail(f"Test failed with error: {str(e)}")

    def test_03_SpinTheWheel(self):
        self.logger.info("Starting spin wheel test...")
        
        try:
            self.navigate_to_login_page()
            self.perform_login(self.username, self.password)
            self.get_api_token()
            card_before = self.get4DCards()
            wallet_before = self.getWalletBalance()
            
            self.driver.get(self.url)
            self.annoucement_close_button()
            self.daily_checkin_close_button()
            
            self.clickMiniGameWidget("lucky_wheel")
            self.click_spin_button()
            text, prize, amount = self.get_spin_prize()
            self.logger.info(f"Get prize: {amount} {prize}")
            
            self.driver.get(self.url)
            
            if prize == "4dCard":
                card_after = self.get4DCards()
                self.verifyReward("4D" ,card_before, card_after, amount)
            elif prize == "FreeCash":
                wallet_after = self.getWalletBalance()
                self.verifyReward("Wallet" ,wallet_before, wallet_after, amount)
            else:
                self.fail("Unknown Prize")
        
        except Exception as e:
            self.fail(f"Test failed with error: {str(e)}")
    
    def test_04_TncShow(self):
        self.logger.info("Starting TnC test...")

        try:
            self.navigate_to_login_page()
            self.perform_login(self.username, self.password)
            self.get_api_token()
            self.verify_tnc()
        
        except Exception as e:
            self.fail(f"Test failed with error: {str(e)}")
        
    
    def test_05_WinnerListShow(self):
        self.logger.info("Starting winner list test...")

        try:
            self.navigate_to_login_page()
            self.perform_login(self.username, self.password)
            self.get_api_token()
            self.verify_winner_list()
        
        except Exception as e:
            self.fail(f"Test failed with error: {str(e)}")
        
    def test_06_NoProbabilityZeroItems(self):
        self.logger.info("Starting test to verify no zero probability prizes are awarded...")
        driver = self.driver
        try:
            # Login and get API token
            self.navigate_to_login_page()
            self.perform_login(self.username, self.password)
            self.get_api_token()
            
            # Get prizes displayed on the wheel
            wheel_prizes, spin_left, tnc = self.get_spin_api()
            wheel_prize_ids = [prize["id"] for prize in wheel_prizes]
            self.logger.info(f"Prizes shown on wheel (IDs): {wheel_prize_ids}")
            
            # Get prizes probability data from API
            probability_prizes = self.get_probability_api()
            
            # Create mapping of prize IDs to probabilities
            prize_probability_map = {prize["id"]: prize["probability"] for prize in probability_prizes}
            
            # Check if any wheel prizes have zero probability
            zero_probability_names = []  # Store just the names for easier text comparison
            
            for prize in wheel_prizes:
                prize_id = prize["id"]
                if prize_id in prize_probability_map and prize_probability_map[prize_id] == "0.00":
                    zero_probability_names.append(prize["name"])
            
            self.logger.info(f"Wheel prizes with zero probability: {zero_probability_names}")
            
            # If there are zero probability prizes on the wheel, let's spin and verify we don't get them
            if zero_probability_names:
                # Make initial deposit
                self.logger.info("Making initial deposit...")
                userID = self.get_id_api()
                self.test_init.submit_deposit_api(username=self.username, password=self.password, amount=1000)
                self.handleDeposit(userID)
                
                # Navigate to lucky wheel and spin it multiple times
                self.clickMiniGameWidget("lucky_wheel")
                received_prizes = []
                
                for i in range(20):
                    self.logger.info(f"Spinning wheel - attempt {i+1}/20")
                    time.sleep(1)
                    self.click_spin_button()
                    prize_text, prize_type, prize_amount = self.get_spin_prize()
                    received_prizes.append(prize_text)
                    
                    # Check if the prize text matches any of the zero probability prize names
                    for zero_name in zero_probability_names:
                        if zero_name in prize_text:
                            self.fail(f"Received a zero probability prize: {prize_text}")
                    
                    self.logger.info(f"Received prize: {prize_text} (Type: {prize_type}, Amount: {prize_amount})")
                    
                    # Close prize popup
                    time.sleep(3)
                    close_button = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-testid="CloseIcon"]'))
                    )
                    close_button.click()
                    time.sleep(1)
                
                self.logger.info(f"Total spins: 20, Received prizes: {received_prizes}")
                self.logger.info("All received prizes have non-zero probability as expected")
                
        except Exception as e:
            self.fail(f"Test failed with error: {str(e)}")

    
if __name__ == "__main__":
    unittest.main()
