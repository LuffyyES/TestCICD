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
from config.constant import API_URL, CREDENTIALS, LANGUAGE_SETTINGS
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
from bs4 import BeautifulSoup

class TestPromotion(BaseTest):

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
    
    def scroll_to_element(self, element):
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
    
    def navigate_to_home_and_handle_popups(self, close_mission=True):
        """Navigate to home page and handle any popups."""
        self.driver.get(self.url)
        time.sleep(3)
        self.annoucement_close_button()
        self.daily_checkin_close_button(close_mission)
    
    def navigate_to_promotion_page(self):
        self.navigate_to_profile_menu("profile-menu-promotion")
    
    def get_all_promotion_api(self):
        token = self.login(self.username, self.password)
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Language": self.language
        }
        response = requests.get(f"{CREDENTIALS['GetAllPromotion'].format(BO_base_url = CREDENTIALS["BO_base_url"])}", headers=headers)
        response.raise_for_status()
        promotions = response.json().get("data").get("promotions")
        return promotions

    def normalize_with_bs4(self, html_str):
        soup = BeautifulSoup(html_str, 'html.parser')
        return soup.get_text().strip()
    
    def click_promo_and_get_redirect_url(self, promo_code):
        """Click on a promotion and return the redirect URL"""
        promotion_card = self.driver.find_element(By.ID, f"promo-card-{promo_code}")
        claim_button = promotion_card.find_element(By.ID, f"promo-claim-button-{promo_code}")
        self.scroll_to_element(claim_button)
        
        # Click near the left edge of the button
        button_rect = claim_button.rect
        x_offset = -button_rect['width']/2 + 5
        action = ActionChains(self.driver)
        action.move_to_element_with_offset(claim_button, x_offset, 0).click().perform()
        
        # Click on the step image in the modal
        self.wait_for_element(By.ID, "claim-modal")
        time.sleep(3)
        step_img = self.wait_for_element(By.ID, "step-image")
        action.move_to_element(step_img).click().perform()
        
        time.sleep(15)  # Wait for redirect

    def handle_login_if_needed(self, path, promo_code):
        """Handle login if redirected to login page"""
        if "login" in path:
            self.logger.info("Login page detected, logging in...")
            login_username = self.wait_for_element(By.ID, "usernameTextField")
            login_password = self.wait_for_element(By.ID, "passwordTextField")
            
            login_username.send_keys("LuffyTest1")
            login_password.send_keys("LuffyTest1")
            
            login_button = self.wait_for_element(By.ID, "loginButton")
            ActionChains(self.driver).move_to_element(login_button).click().perform()
            time.sleep(8)
            
            self.navigate_to_home_and_handle_popups()
            self.navigate_to_promotion_page()
            self.wait_for_element(By.CSS_SELECTOR, "ul.MuiImageList-root")
                
            # Click again after login
            self.click_promo_and_get_redirect_url(promo_code)
            

    def get_full_endpoint(self, parsed_url):
        """Get the full endpoint including query parameters from a parsed URL"""
        endpoint = parsed_url.path
        if parsed_url.query:
            query_params = parse_qs(parsed_url.query)
            query_parts = []
            for key, values in query_params.items():
                for value in values:
                    query_parts.append(f"{key}={value}")
            endpoint += f"?{'&'.join(query_parts)}"
        return endpoint  
    
    def test_01_InfoShown(self):
        action = ActionChains(self.driver)
        try:
            self.logger.info("Starting promotion test...")
            self.setup_test_user(register_new=True)
            self.navigate_to_promotion_page()
            
            self.wait_for_element(By.CSS_SELECTOR, "ul.MuiImageList-root")
            
            promotion_cards = self.driver.find_elements(By.CSS_SELECTOR, "[id^='promo-card-']")            
                
            all_promotions_api = self.get_all_promotion_api()
            self.logger.info(f"All promotions: {all_promotions_api}")
            
            self.assertEqual(len(promotion_cards), len(all_promotions_api), f"Number of promotion cards: {len(promotion_cards)} is not equal to number of promotions: {len(all_promotions_api)}")
            
            for item in list(all_promotions_api):
                self.logger.info(f"Promotion item: {item}")
                
                promo_code = item['promoCode']
                
                promotion_card = self.driver.find_element(By.ID, f"promo-card-{promo_code}")
                
                card_title = promotion_card.find_element(By.ID, f"promo-title-{promo_code}")
                self.assertEqual(card_title.text, item['title'], f"Card title: {card_title.text} is not equal to promotion name: {item['title']}")
                
                card_img = promotion_card.find_element(By.ID, f"promo-image-{promo_code}").get_attribute("src")
                self.assertEqual(card_img, item['imageUrl'], f"Card image: {card_img} is not equal to promotion description: {item['imageUrl']}")
                
                claim_button = promotion_card.find_element(By.ID, f"promo-claim-button-{promo_code}")
                expected_text = LANGUAGE_SETTINGS[self.language]["promotion"]["claim"]
                self.assertEqual(claim_button.text, expected_text, f"Claim button: {claim_button.text} is not equal to '{expected_text}'")
                
                self.scroll_to_element(claim_button)
                
                # Get button dimensions
                button_rect = claim_button.rect
                button_width = button_rect['width']

                x_offset = -button_width/2 + 3  # 5px from the left edge
                y_offset = 0  # maintain vertical center

                action = ActionChains(self.driver)
                action.move_to_element_with_offset(claim_button, x_offset, y_offset).click().perform()
                
                time.sleep(1)
                
                self.wait_for_element(By.ID, f"claim-modal")
                
                close_button = self.driver.find_element(By.ID, "close-button")
                
                action.move_to_element(close_button).click().perform()
                
                time.sleep(2)
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")
    
    def test_02_ModalInfoShown(self):
        action = ActionChains(self.driver)
        try:
            self.logger.info("Starting promotion test...")
            self.setup_test_user(register_new=True)
            self.navigate_to_promotion_page()
            
            self.wait_for_element(By.CSS_SELECTOR, "ul.MuiImageList-root")
            
            promotion_cards = self.driver.find_elements(By.CSS_SELECTOR, "[id^='promo-card-']")            
                
            all_promotions_api = self.get_all_promotion_api()
            self.logger.info(f"All promotions: {all_promotions_api}")
            
            self.assertEqual(len(promotion_cards), len(all_promotions_api), f"Number of promotion cards: {len(promotion_cards)} is not equal to number of promotions: {len(all_promotions_api)}")
            
            for item in all_promotions_api:                
                promo_code = item['promoCode']
                self.logger.info(f"Promotion item: {item}")
                
                promotion_card = self.driver.find_element(By.ID, f"promo-card-{promo_code}")
                
                claim_button = promotion_card.find_element(By.ID, f"promo-claim-button-{promo_code}")
                
                self.scroll_to_element(claim_button)
                
                # Get button dimensions
                button_rect = claim_button.rect
                button_width = button_rect['width']

                x_offset = -button_width/2 + 3  # 5px from the left edge
                y_offset = 0  # maintain vertical center

                action = ActionChains(self.driver)
                action.move_to_element_with_offset(claim_button, x_offset, y_offset).click().perform()
                
                time.sleep(1)
                
                self.wait_for_element(By.ID, f"claim-modal")
                
                step_img = self.wait_for_element(By.ID, f"step-image").get_attribute("src")
                self.assertEqual(step_img, item['stepImage'], f"Step image: {step_img} is not equal to promotion description: {item['stepImage']}")
                
                # Get the innerHTML from the element
                tnc_elements = self.wait_for_element(By.ID, f"tnc-content").get_attribute("innerHTML")

                normalized_tnc = self.normalize_with_bs4(tnc_elements)
                normalized_expected = self.normalize_with_bs4(item['tnc'])
                
                self.assertEqual(normalized_tnc, normalized_expected, 
                                f"TNC text content differs from expected") 
                
                close_button = self.driver.find_element(By.ID, "close-button")
                
                action.move_to_element(close_button).click().perform()
                
                time.sleep(2)
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")      
    
    def test_03_PromoRedirect(self):
        try:
            self.logger.info("Starting promotion test...")
            self.setup_test_user(register_new=True)
            self.navigate_to_promotion_page()
            
            self.wait_for_element(By.CSS_SELECTOR, "ul.MuiImageList-root")
            promotion_cards = self.driver.find_elements(By.CSS_SELECTOR, "[id^='promo-card-']")
            all_promotions_api = self.get_all_promotion_api()
            
            self.assertEqual(len(promotion_cards), len(all_promotions_api), 
                            f"Number of promotion cards: {len(promotion_cards)} != number of promotions: {len(all_promotions_api)}")
            
            # Test all promotions
            for promo in all_promotions_api:
                promo_code = promo['promoCode']
                self.logger.info(f"Testing promo code: {promo_code}")
                
                # Parse expected redirect data
                testing_url = urlparse(self.url)
                testing_base_url = f"{testing_url.scheme}://{testing_url.netloc}"
                
                redirect_url_api = promo['redirectUrl']
                redirect_api_parsed = urlparse(redirect_url_api)
                redirect_api_endpoint = redirect_api_parsed.path
                if redirect_api_parsed.query:
                    redirect_api_endpoint += f"?{redirect_api_parsed.query}"
                
                # First attempt to click promo
                self.click_promo_and_get_redirect_url(promo_code)
                redirect_url = self.driver.current_url
                parsed_url = urlparse(redirect_url)
                redirect_base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
                
                self.logger.info(f"Redirect URL: {redirect_url}")
                
                # Handle different base URL (login required)
                if redirect_base_url != testing_base_url:
                    self.handle_login_if_needed(parsed_url.path, promo_code)
                    
                    redirect_url = self.driver.current_url
                    parsed_url = urlparse(redirect_url)
                    redirect_base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
                    
                    if redirect_base_url != testing_base_url:
                        self.logger.error(f"Redirect base URL doesn't match testing base URL")
                        # self.fail(f"Redirect base URL doesn't match testing base URL")
                        
                # Verify final redirect
                redirect_endpoint = self.get_full_endpoint(parsed_url)
                self.assertEqual(redirect_api_endpoint, redirect_endpoint, 
                                f"Redirect endpoint doesn't match expected for promo code: {promo_code}")
                
                # Verify promo code in URL
                redirect_query_params = parse_qs(parsed_url.query)
                url_promo_code = redirect_query_params.get('promoCode', [None])[0]
                if url_promo_code:
                    self.assertEqual(promo_code, url_promo_code, f"URL promo code doesn't match expected for promo code: {promo_code}")
                
                if "/deposit" in redirect_endpoint:
                    if url_promo_code:
                        self.driver.get(f"{testing_base_url}/{redirect_endpoint}")
                        time.sleep(3)
                        self.wait_for_element(By.ID, "promo-code-input")
                        
                        # check if the promo code input is filled with the promo code
                        self.assertEqual(self.driver.find_element(By.ID, "promo-code-input").get_attribute("value"), promo_code, 
                                        f"Promo code input doesn't match expected for promo code: {promo_code}")
                    else:
                        self.logger.error(f"Redirect to deposit page but no promo code in URL")
                        # self.fail(f"Redirect to deposit page but no promo code in URL")
                        
                time.sleep(5)
                self.navigate_to_home_and_handle_popups()
                self.navigate_to_promotion_page()
                self.wait_for_element(By.CSS_SELECTOR, "ul.MuiImageList-root")
                
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")
    
    def test_04_CategoryFilter(self):
        action = ActionChains(self.driver)
        try:
            self.logger.info("Starting promotion test...")
            self.setup_test_user(register_new=True)
            self.navigate_to_promotion_page()
            
            self.wait_for_element(By.CSS_SELECTOR, "ul.MuiImageList-root")
            promotion_cards = self.driver.find_elements(By.CSS_SELECTOR, "[id^='promo-card-']")
            all_promotions_api = self.get_all_promotion_api()
            
            self.assertEqual(len(promotion_cards), len(all_promotions_api), 
                            f"Number of promotion cards: {len(promotion_cards)} != number of promotions: {len(all_promotions_api)}")
            
            category_list = [category['category'] for category in all_promotions_api]
            
            category_set = set(category_list)
            
            for category in category_set:
                self.logger.info(f"Testing category: {category}")
                
                # find button that has a span containing the category text
                category_button = self.wait_for_element(By.XPATH, f"//button[.//span[contains(text(), '{category}')]]")
                self.scroll_to_element(category_button)
                action.move_to_element(category_button).click().perform()
                time.sleep(5)
                
                # filter the all_promotions_api with the category
                filtered_promotions = [promo for promo in all_promotions_api if promo['category'] == category]
                
                # find the promotion cards that have the category
                filtered_promotion_cards = self.driver.find_elements(By.CSS_SELECTOR, "[id^='promo-card-']")
                
                self.assertEqual(len(filtered_promotion_cards), len(filtered_promotions), 
                                f"Number of promotion cards: {len(filtered_promotion_cards)} != number of promotions: {len(filtered_promotions)}")
                
                
                # check if all promotions in filtered_promotions are in filtered_promotion_cards
                for promo in filtered_promotions:
                    self.wait_for_element(By.ID, f"promo-card-{promo['promoCode']}")
            
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")
            
if __name__ == "__main__":
    unittest.main()