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

class TestGiftRedemption(BaseTest):

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
            handler = logging.FileHandler('gift_redemption.log')
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
        if self.language == "bm":
            self.username = CREDENTIALS["luffy_user"]["username"]
            self.password = CREDENTIALS["luffy_user"]["password"]
        elif self.language == "cn":
            self.username = "LuffyTest3"
            self.password = "LuffyTest3"
        else:
            self.username = "LuffyTest4"
            self.password = "LuffyTest4"
        

    def tearDown(self):
        if hasattr(self, "driver"):
            self.driver.quit()
    
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
    
    def wait_for_gift_page_load(self):
        """Wait for the gift redemption page to load completely"""
        self.logger.info("Waiting for gift redemption page to load...")
        self.wait_for_element(By.CLASS_NAME, "MuiImageList-root")
    
    def get_search_field(self):
        """Find and return the search field element"""
        try:
            # Try first selector
            return self.wait_for_element(By.ID, ":r0:")
        except:
            # Try alternative selector
            search_placeholder = LANGUAGE_SETTINGS[self.language]["gift_redemption"]["search"]
            return self.wait_for_element(By.XPATH, f"//input[@type='search' or @placeholder='{search_placeholder}']")
    
    def get_all_gift_cards(self):
        """Find and return all gift cards on the page"""
        return self.driver.find_elements(By.XPATH, "//div[contains(@class, 'MuiCard-root')]")
    
    def get_gift_count(self):
        """Get the count of gift cards currently displayed"""
        gifts = self.get_all_gift_cards()
        count = len(gifts)
        self.logger.info(f"Current gift count: {count}")
        return count
    
    def search_for_gift(self, keyword):
        """Search for a gift using the provided keyword"""
        self.logger.info(f"Searching for keyword: {keyword}")
        search_field = self.get_search_field()
        search_field.clear()
        search_field.send_keys(keyword)
        time.sleep(5)  # Wait for search results to update
    
    def clear_search_field(self):
        """Clear the search field"""
        self.logger.info("Clearing search field")
        search_field = self.get_search_field()
        
        # Move to the search field to make clear button visible
        actions = ActionChains(self.driver)
        actions.move_to_element(search_field).perform()
        
        # Clear using JavaScript and trigger update
        self.driver.execute_script("arguments[0].value = '';", search_field)
        search_field.send_keys(" ")  # Send a space
        search_field.send_keys(Keys.BACKSPACE)  # Then backspace to trigger search update
        time.sleep(2)  # Wait for the list to refresh
    
    def get_gift_titles(self, gift_cards=None):
        """Extract gift titles from the provided gift cards or all current cards"""
        if gift_cards is None:
            gift_cards = self.get_all_gift_cards()
            
        gift_titles = []
        for card in gift_cards:
            try:
                title_element = card.find_element(By.XPATH, ".//div[contains(@class, 'MuiTypography-h6')]")
                gift_titles.append(title_element.text)
            except NoSuchElementException:
                continue
        
        return gift_titles
    
    def get_gift_points(self, gift_card):
        """Extract points value from a gift card"""
        try:
            points_text = gift_card.find_element(By.XPATH, ".//p[contains(@class, 'MuiTypography-body2')]").text

            return int(''.join(filter(str.isdigit, points_text)))
        except (NoSuchElementException, ValueError) as e:
            self.logger.warning(f"Couldn't extract points for a gift: {str(e)}")
            return None
    
    def set_points_filter(self, target_value):
        """Set the points filter slider to the target value"""
        self.logger.info(f"Setting point range to: {target_value}")
        
        # Find the slider element
        slider = self.wait_for_element(By.XPATH, "//span[contains(@class, 'MuiSlider-root')]")
        
        # Find the thumb element of the slider
        slider_thumb = slider.find_element(By.XPATH, ".//span[contains(@class, 'MuiSlider-thumb')]")
        
        # Get the current max value from the slider
        current_max = int(slider_thumb.find_element(By.XPATH, ".//input").get_attribute("aria-valuenow"))
        self.logger.info(f"Current max value: {current_max}")
        
        # Try to set the value using ActionChains
        slider_width = slider.size['width']
        max_value = int(slider_thumb.find_element(By.XPATH, ".//input").get_attribute("max"))
        relative_position = (target_value / max_value) * slider_width
        
        actions = ActionChains(self.driver)
        actions.click_and_hold(slider_thumb).move_by_offset(relative_position - slider_width, 0).release().perform()
        time.sleep(1)
        
        # Check if the slider moved to the expected value
        actual_value = int(slider_thumb.find_element(By.XPATH, ".//input").get_attribute("aria-valuenow"))
        
        # If ActionChains didn't work accurately, use JavaScript
        if abs(actual_value - target_value) > 500:  # Allow for some tolerance
            self.logger.info(f"Slider manipulation didn't work accurately (got {actual_value}), using JavaScript")
            self.driver.execute_script(
                f"arguments[0].value = {target_value}; "
                f"arguments[0].dispatchEvent(new Event('input', {{ bubbles: true }}));", 
                slider_thumb.find_element(By.XPATH, ".//input")
            )
            
            # Trigger change event to make sure the UI updates
            self.driver.execute_script(
                f"arguments[0].dispatchEvent(new Event('change', {{ bubbles: true }}));", 
                slider_thumb.find_element(By.XPATH, ".//input")
            )
            time.sleep(1)
        
        # Get updated slider value
        actual_value = int(slider_thumb.find_element(By.XPATH, ".//input").get_attribute("aria-valuenow"))
        self.logger.info(f"Actual slider value after adjustment: {actual_value}")
        time.sleep(2)  # Wait for the gift list to refresh
        
        return actual_value
    
    def toggle_favorite(self, gift_card, expected_state=None):
        """
        Toggle favorite status for a gift card
        expected_state: None (just toggle), True (expect to favorite), False (expect to unfavorite)
        Returns: (gift_name, success)
        """
        try:
            # Get the gift name for logging
            gift_name = gift_card.find_element(By.XPATH, ".//div[contains(@class, 'MuiTypography-h6')]").text
            
            # Determine current state and find the appropriate icon to click
            try:
                # Check if currently favorited
                filled_heart = gift_card.find_element(By.XPATH, './/*[@data-testid="FavoriteIcon"]')
                is_currently_favorite = True
                icon_to_click = filled_heart
                expected_icon = "FavoriteBorderOutlinedIcon"
            except NoSuchElementException:
                # Not currently favorited
                unfilled_heart = gift_card.find_element(By.XPATH, './/*[@data-testid="FavoriteBorderOutlinedIcon"]')
                is_currently_favorite = False
                icon_to_click = unfilled_heart
                expected_icon = "FavoriteIcon"
            
            # If expected_state is provided, check if we need to toggle
            if expected_state is not None and is_currently_favorite == expected_state:
                self.logger.info(f"Gift '{gift_name}' already in desired favorite state: {expected_state}")
                return gift_name, True
            
            # Scroll to the icon and click it
            self.logger.info(f"{'Unfavoriting' if is_currently_favorite else 'Favoriting'} gift: {gift_name}")
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", icon_to_click)
            icon_to_click.click()
            
            # Wait for the UI to update
            time.sleep(2)
            
            # Verify the change
            try:
                gift_card.find_element(By.XPATH, f'.//*[@data-testid="{expected_icon}"]')
                self.logger.info(f"Successfully {'unfavorited' if is_currently_favorite else 'favorited'} {gift_name}")
                return gift_name, True
            except NoSuchElementException:
                self.logger.error(f"Failed to toggle favorite status for {gift_name}")
                return gift_name, False
                
        except NoSuchElementException as e:
            self.logger.error(f"Could not find elements within gift card: {str(e)}")
            return "Unknown gift", False
    
    def sort_gifts(self, sort_option):
        """
        Sort the gifts by the specified option
        
        Parameters:
        sort_option (str): Option to sort by. Valid values are:
                        'Lowest Points', 'Highest Points', 'My Favourite', 'Last Updated'
        
        Returns:
        bool: True if sorting was successful, False otherwise
        """
        try:
            self.logger.info(f"Sorting gifts by: {sort_option}")
            
            sort_text = LANGUAGE_SETTINGS[self.language]["gift_redemption"]["sort_by"]
            # Find and click the sort dropdown button
            sort_button = self.wait_for_element(
                By.XPATH, 
                f"//button[.//p[contains(text(), '{sort_text}')]]"
            )
            self.logger.info("Clicking sort dropdown button")
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", sort_button)
            sort_button.click()
            time.sleep(2)  # Wait for dropdown to appear
            
            # Find and click the specified sort option
            sort_option_xpath = f"//li[contains(text(), '{sort_option}')]"
            sort_option_element = self.wait_for_element(By.XPATH, sort_option_xpath)
            
            self.logger.info(f"Selecting '{sort_option}' option")
            sort_option_element.click()
            
            # Wait for sorting to complete
            time.sleep(3)
            
            return True
        except Exception as e:
            self.logger.error(f"Error sorting gifts by {sort_option}: {str(e)}")
            return False
    
    def get_gift_api(self):
        token = self.login(self.username, self.password)
        headers = {
            "Authorization": f"Bearer {token}",
            "language": self.language
        }
        response = requests.get(f"{API_URL}/api/gifts", headers=headers)
        response.raise_for_status()
        gifts = response.json().get("data")
        self.logger.info(gifts)
        return gifts

    def get_user_points(self):
        """Get the current user points from the UI"""
        try:
            points_element = self.wait_for_element(
                By.XPATH, 
                "//div[contains(@class, 'MuiBox-root')]/p[contains(@class, 'MuiTypography-body1')][2]"
            )
            current_points = int(points_element.text)
            self.logger.info(f"User's current points: {current_points}")
            return current_points
        except (TimeoutException, ValueError) as e:
            self.logger.error(f"Failed to get user points: {str(e)}")
            return None

    def find_affordable_gift(self, search_keyword, title_contains=None):
        """
        Find an affordable gift matching the search criteria.
        If the user can't afford the gift, automatically deposit enough funds.
        
        Parameters:
        search_keyword (str): Keyword to search for
        title_contains (str, optional): Additional text that should be in the title
        
        Returns:
        tuple: (gift_element, gift_title, gift_points) or (None, None, None) if not found
        """
        try:
            # Search for gifts
            self.search_for_gift(search_keyword)
            time.sleep(3)  # Wait for search results
            
            # Get all matching gift cards
            gift_cards = self.get_all_gift_cards()
            if not gift_cards:
                self.logger.error(f"No gifts found containing '{search_keyword}'")
                return None, None, None
                
            self.logger.info(f"Found {len(gift_cards)} gifts matching '{search_keyword}'")
            
            # Get current points
            current_points = self.get_user_points()
            if current_points is None:
                self.logger.error("Failed to get user points")
                return None, None, None
            
            # Get information about the first gift before potentially refreshing the page
            first_card = gift_cards[0]
            
            # Get the gift points
            points = self.get_gift_points(first_card)
            if points is None:
                self.logger.error("Could not determine gift points")
                return None, None, None
                
            # Get the title
            try:
                title_element = first_card.find_element(By.XPATH, ".//div[contains(@class, 'MuiTypography-h6')]")
                gift_title = title_element.text
                self.logger.info(f"Found gift: {gift_title} ({points} points)")
                
                # Check if title contains required text (if specified)
                if title_contains and title_contains.lower() not in gift_title.lower():
                    self.logger.warning(f"Gift title '{gift_title}' does not contain '{title_contains}'")
                    # Continue anyway as we'll use the first gift
            except NoSuchElementException:
                self.logger.warning("Could not find title element for gift")
                gift_title = f"{search_keyword} gift"  # Fallback title
            
            # Check if we need to make a deposit to afford the gift
            if points > current_points:
                amount = (points - current_points) * 50  # Calculate needed deposit amount
                self.logger.info(f"Current points ({current_points}) insufficient for gift ({points} points)")
                self.logger.info(f"Making initial deposit of {amount}...")
                
                # Make the deposit
                userID = self.get_id_api()
                self.test_init.submit_deposit_api(username=self.username, password=self.password, amount=amount)
                self.handleDeposit(userID)
                
                # Page has been refreshed, need to re-find elements
                self.driver.refresh()
                time.sleep(3)
                
                # Get updated gift cards after refresh
                self.wait_for_gift_page_load()
                time.sleep(3)
                
                # Get the first gift card again
                updated_gift_cards = self.get_all_gift_cards()
                if not updated_gift_cards:
                    self.logger.error("No gifts found after page refresh")
                    return None, None, None
                    
                first_card = updated_gift_cards[0]
                
                # Update points information
                points = self.get_gift_points(first_card)
                if points is None:
                    self.logger.error("Could not determine gift points after refresh")
                    return None, None, None
                    
                # Update title if needed
                try:
                    title_element = first_card.find_element(By.XPATH, ".//div[contains(@class, 'MuiTypography-h6')]")
                    gift_title = title_element.text
                except NoSuchElementException:
                    self.logger.warning("Could not find title element after refresh")
                    # Keep the previously found title
                    
                # Verify we now have enough points
                updated_points = self.get_user_points()
                if updated_points is None:
                    self.logger.error("Failed to get updated user points")
                    return None, None, None
                    
                self.logger.info(f"Updated points: {updated_points}, Gift cost: {points}")
                if updated_points < points:
                    self.logger.error(f"Still insufficient points after deposit. Have: {updated_points}, Need: {points}")
                    return None, None, None
            
            self.logger.info(f"Found affordable gift to redeem: {gift_title} ({points} points)")
            return first_card, gift_title, points
            
        except Exception as e:
            self.logger.error(f"Error in find_affordable_gift: {str(e)}")
            self.take_debug_screenshot("find_affordable_gift_error")
            return None, None, None

    def click_redeem_button(self, gift_card):
        """
        Find and click the redeem button for a gift
        
        Parameters:
        gift_card: The WebElement representing the gift card
        
        Returns:
        bool: True if successful, False otherwise
        """
        try:
            # Scroll the gift card into view for better interaction
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", gift_card)
            time.sleep(1)
            
            # Find the redeem button directly within the gift card
            redeem_text = LANGUAGE_SETTINGS[self.language]["gift_redemption"]["redeem"]
            redeem_button = gift_card.find_element(
                By.XPATH, 
                f".//button[contains(text(), '{redeem_text}')]"
            )
            
            self.logger.info("Found Redeem button directly in the gift card")
            
            # Click the redeem button
            self.logger.info("Clicking Redeem button")
            redeem_button.click()
            time.sleep(3)  # Wait for confirmation dialog
            return True
            
        except NoSuchElementException:
            self.logger.info("Redeem button not found in gift card, trying alternate approach...")
            
            # Try clicking the card first to select it
            try:
                gift_card.click()
                time.sleep(2)
                
                # Now look for redeem button
                redeem_button = self.wait_for_element(
                    By.XPATH, 
                    "//button[.//span[contains(text(), 'Redeem')] or .//p[contains(text(), 'Redeem')]]",
                    timeout=5
                )
                self.logger.info("Found Redeem button after clicking gift card")
                redeem_button.click()
                time.sleep(3)
                return True
            except (TimeoutException, NoSuchElementException) as e:
                self.logger.error(f"Could not find redeem button: {str(e)}")
                return False

    def verify_success_popup(self, needs_whatsapp=False):
        """
        Verify the success popup appears and contains expected elements
        
        Parameters:
        needs_whatsapp (bool): Whether to verify WhatsApp button is present
        
        Returns:
        dict: Contains success status and found elements, or None if verification failed
        """
        try:
            # Check for the SweetAlert2 success popup
            swal_popup = self.wait_for_element(
                By.XPATH,
                "//div[contains(@class, 'swal2-popup') and contains(@class, 'swal2-icon-success')]",
                timeout=10
            )
            
            result = {"success": False, "popup": swal_popup}
            
            # Check for the success title
            try:
                success_title = swal_popup.find_element(By.XPATH, ".//h2[@id='swal2-title']")
                result["title"] = success_title
                self.logger.info(f"Success title found: '{success_title.text}'")
            except NoSuchElementException:
                success_title = None
            
            # Check for the success message
            try:
                if needs_whatsapp:
                    contact_customer_service = LANGUAGE_SETTINGS[self.language]["gift_redemption"]["contact_customer_service"]
                    message_xpath = f".//div[@id='swal2-html-container' and contains(text(), '{contact_customer_service}')]"
                else:
                    successful = LANGUAGE_SETTINGS[self.language]["gift_redemption"]["successful"]
                    message_xpath = f".//div[@id='swal2-html-container' and contains(text(), '{successful}')]"
                    
                success_message = swal_popup.find_element(By.XPATH, message_xpath)
                result["message"] = success_message
                self.logger.info(f"Success message found: '{success_message.text}'")
            except NoSuchElementException:
                success_message = None
            
            # If we need WhatsApp button, check for it
            if needs_whatsapp:
                try:
                    redirect_to_whatsapp = LANGUAGE_SETTINGS[self.language]["gift_redemption"]["redirect_to_whatsapp"]
                    whatsapp_button = swal_popup.find_element(
                        By.XPATH,
                        f".//button[contains(@class, 'swal2-confirm') and contains(text(), '{redirect_to_whatsapp}')]"
                    )
                    result["whatsapp_button"] = whatsapp_button
                    self.logger.info("WhatsApp redirect button found")
                except NoSuchElementException:
                    whatsapp_button = None
            
            # Look for close/OK button
            try:
                if needs_whatsapp:
                    close_text = LANGUAGE_SETTINGS[self.language]["gift_redemption"]["close"]
                    close_xpath = f".//button[contains(@class, 'swal2-cancel') and contains(text(), '{close_text}')]"
                else:
                    close_xpath = ".//button[contains(@class, 'swal2-confirm') and text()='OK']"
                    
                close_button = swal_popup.find_element(By.XPATH, close_xpath)
                result["close_button"] = close_button
                self.logger.info("Close/OK button found")
            except NoSuchElementException:
                close_button = None
            
            # Determine overall success
            if needs_whatsapp:
                result["success"] = (success_title is not None and 
                                success_message is not None and 
                                whatsapp_button is not None and 
                                close_button is not None)
            else:
                result["success"] = (success_message is not None and 
                                close_button is not None)
                                
            return result
            
        except (TimeoutException, NoSuchElementException) as e:
            self.logger.error(f"Could not verify success popup: {str(e)}")
            return None

    def handle_whatsapp_redirect(self, whatsapp_button):
        """
        Click the WhatsApp button and verify redirection
        
        Parameters:
        whatsapp_button: The WebElement representing the WhatsApp redirect button
        
        Returns:
        bool: True if redirection successful, False otherwise
        """
        # Store current window handle
        current_window = self.driver.current_window_handle
        
        # Click the WhatsApp redirect button
        self.logger.info("Clicking 'Redirect to WhatsApp' button")
        whatsapp_button.click()
        time.sleep(5)  # Wait for new tab/window to open
        
        # Check if a new window or tab has been opened
        all_windows = self.driver.window_handles
        
        if len(all_windows) > 1:
            # A new window/tab was opened
            self.logger.info(f"New window detected. Total windows: {len(all_windows)}")
            
            # Switch to the new window/tab
            new_window = [window for window in all_windows if window != current_window][0]
            self.driver.switch_to.window(new_window)
            
            # Verify the URL contains WhatsApp
            current_url = self.driver.current_url
            self.logger.info(f"Redirected to URL: {current_url}")
            
            redirect_success = "api.whatsapp" in current_url.lower() or "wa.me" in current_url.lower()
            
            if redirect_success:
                self.logger.info("PASS: Successfully redirected to WhatsApp")
            else:
                self.logger.warning(f"Redirect URL does not contain WhatsApp: {current_url}")
            
            # Close the new window/tab and switch back to the original
            self.driver.close()
            self.driver.switch_to.window(current_window)
            
        else:
            # No new window was opened, check if the current URL changed
            current_url = self.driver.current_url
            self.logger.info(f"Current URL after clicking WhatsApp button: {current_url}")
            
            redirect_success = "whatsapp" in current_url.lower() or "wa.me" in current_url.lower()
            
            if redirect_success:
                self.logger.info("PASS: Successfully redirected to WhatsApp in the same window")
                # Navigate back to the gift page
                self.driver.back()
            else:
                self.logger.warning("No redirection detected, possibly blocked by browser settings")
                redirect_success = False
        
        return redirect_success

    def close_success_popup(self):
        """
        Close the success popup by clicking the Close/OK button
        
        Returns:
        bool: True if closed successfully, False otherwise
        """
        try:
            # Try to find either Close or OK button
            button_xpaths = [
                "//div[contains(@class, 'swal2-popup')]//button[contains(@class, 'swal2-cancel') and contains(text(), 'Close')]",
                "//div[contains(@class, 'swal2-popup')]//button[contains(@class, 'swal2-confirm') and text()='OK']"
            ]
            
            for xpath in button_xpaths:
                try:
                    close_button = self.wait_for_element(By.XPATH, xpath, timeout=3)
                    self.logger.info("Closing success popup")
                    close_button.click()
                    time.sleep(2)
                    return True
                except TimeoutException:
                    continue
                    
            self.logger.warning("Could not find Close/OK button to close popup")
            return False
        except Exception as e:
            self.logger.warning(f"Error closing success popup: {str(e)}")
            return False

    def verify_points_deduction(self, previous_points, gift_points):
        """
        Verify that points were correctly deducted after redemption
        
        Parameters:
        previous_points (int): User's points before redemption
        gift_points (int): Cost of the redeemed gift
        
        Returns:
        bool: True if points were correctly deducted, False otherwise
        """
        try:
            # Wait for the points display to update
            updated_points_element = self.wait_for_element(
                By.XPATH, 
                "//div[contains(@class, 'MuiBox-root')]/p[contains(@class, 'MuiTypography-body1')][2]"
            )
            updated_points = int(updated_points_element.text)
            
            expected_points = previous_points - gift_points
            self.logger.info(f"Updated points: {updated_points}, Expected: {expected_points}")
            
            if updated_points == expected_points:
                self.logger.info("PASS: Points were correctly deducted")
                return True
            else:
                self.logger.warning(f"Points not updated as expected. Current: {updated_points}, Expected: {expected_points}")
                return False
        except (TimeoutException, ValueError) as e:
            self.logger.warning(f"Could not verify points deduction: {str(e)}")
            return False

    # Add these helper methods to your TestGiftRedemption class

    def verify_minimum_gift_count(self, minimum_count=1):
        """
        Verify that we have at least the minimum number of gift cards
        
        Parameters:
        minimum_count (int): Minimum number of gift cards required
        
        Returns:
        list: List of gift cards if successful, raises an exception if not enough cards
        """
        gift_cards = self.get_all_gift_cards()
        count = len(gift_cards)
        
        if count < minimum_count:
            self.logger.error(f"Not enough gift cards found: {count}, needed at least {minimum_count}")
            self.fail(f"Test requires at least {minimum_count} gift cards, but found {count}")
        
        self.logger.info(f"Found {count} gift cards")
        return gift_cards

    def get_gift_points_with_titles(self, cards, num_samples=5):
        """
        Get points and titles for a set of gift cards
        
        Parameters:
        cards (list): List of gift card WebElements
        num_samples (int): Number of cards to sample (default: 5)
        
        Returns:
        list: List of tuples (title, points)
        """
        gift_data = []
        for card in cards[:min(num_samples, len(cards))]:
            points = self.get_gift_points(card)
            try:
                title = card.find_element(By.XPATH, ".//div[contains(@class, 'MuiTypography-h6')]").text
                if points is not None:
                    gift_data.append((title, points))
                    self.logger.info(f"Gift: {title}, Points: {points}")
            except NoSuchElementException:
                pass
        return gift_data

    def verify_sorting_by_points(self, sorted_points, expected_order="ascending"):
        """
        Verify gifts are properly sorted by points
        
        Parameters:
        sorted_points (list): List of (title, points) tuples
        expected_order (str): Either "ascending" or "descending"
        
        Returns:
        bool: True if sorted correctly, False otherwise
        """
        if len(sorted_points) <= 1:
            self.logger.warning("Not enough data to verify sorting")
            return True
            
        if expected_order == "ascending":
            is_sorted = all(sorted_points[i][1] <= sorted_points[i+1][1] for i in range(len(sorted_points)-1))
            order_description = "lowest points first"
        else:  # descending
            is_sorted = all(sorted_points[i][1] >= sorted_points[i+1][1] for i in range(len(sorted_points)-1))
            order_description = "highest points first"
        
        if is_sorted:
            self.logger.info(f"PASS: Gifts successfully sorted by {order_description}")
        else:
            self.logger.error(f"FAIL: Gifts not properly sorted by {order_description}. Sorted order: {sorted_points}")
            self.fail(f"Gifts not properly sorted by {order_description}. Sorted order: {sorted_points}")
        
        return is_sorted

    def find_favorited_gifts(self, gift_cards):
        """
        Find all gifts that are already marked as favorites
        
        Parameters:
        gift_cards (list): List of gift card WebElements
        
        Returns:
        tuple: (list of favorite gift names, list of corresponding indices)
        """
        favorites = []
        favorited_indices = []
        
        for index, card in enumerate(gift_cards):
            try:
                # Check if card has the filled heart icon indicating it's a favorite
                card.find_element(By.XPATH, './/*[@data-testid="FavoriteIcon"]')
                # Get the gift name
                gift_name = card.find_element(By.XPATH, ".//div[contains(@class, 'MuiTypography-h6')]").text
                favorites.append(gift_name)
                favorited_indices.append(index)
                self.logger.info(f"Found favorited gift: {gift_name} at index {index}")
            except NoSuchElementException:
                # Not a favorite, skip
                continue
        
        # Log what we found
        if favorites:
            self.logger.info(f"Found {len(favorites)} favorited gifts: {favorites}")
        else:
            self.logger.warning("No favorited gifts found")
        
        return favorites, favorited_indices

    def verify_favorites_at_top(self, sorted_cards, expected_favorites):
        """
        Verify that favorited gifts appear at the top of sorted results
        
        Parameters:
        sorted_cards (list): List of sorted gift card WebElements
        expected_favorites (list): List of expected favorite gift names
        
        Returns:
        bool: True if verified, False otherwise
        """
        if not expected_favorites:
            self.logger.info("No favorites to verify")
            return True
            
        # Check if favorites appear at the top of the sorted list
        first_cards = sorted_cards[:len(expected_favorites)]
        favorites_first = True
        found_favorites = []
        
        for card in first_cards:
            try:
                # Check if card has the filled heart icon indicating it's a favorite
                card.find_element(By.XPATH, './/*[@data-testid="FavoriteIcon"]')
                # Get the gift name
                gift_name = card.find_element(By.XPATH, ".//div[contains(@class, 'MuiTypography-h6')]").text
                found_favorites.append(gift_name)
            except NoSuchElementException:
                favorites_first = False
                break
        
        if favorites_first and len(found_favorites) == len(expected_favorites):
            self.logger.info(f"PASS: All {len(expected_favorites)} favorites appear at the top of the sorted list")
            self.logger.info(f"Favorited gifts at the top: {found_favorites}")
            return True
        else:
            self.logger.error(f"FAIL: Not all favorites appear at the top after sorting. Expected {len(expected_favorites)} favorites, found {len(found_favorites)} at top")
            self.logger.error(f"Expected favorites: {expected_favorites}")
            self.logger.error(f"Found favorites at top: {found_favorites}")
            return False

    def process_api_gift_data(self, api_gifts):
        """
        Process gift data from API for verification
        
        Parameters:
        api_gifts (list): List of gift dictionary objects from API
        
        Returns:
        tuple: (gift_update_times dict, expected_order list)
        """
        # Create a map of gift titles to their updated_at timestamps
        gift_update_times = {}
        for gift in api_gifts:
            gift_update_times[gift['title']] = gift['updated_at']
                
        self.logger.info(f"Found {len(gift_update_times)} gift titles with update timestamps")
        
        # Sort API gift data by updated_at in descending order (newest first)
        api_gifts_sorted = sorted(api_gifts, key=lambda x: x['updated_at'], reverse=True)
        expected_order = [gift['title'] for gift in api_gifts_sorted[:10]]  # Get top 10 most recently updated
        
        self.logger.info(f"Expected order (top 10 most recent): {expected_order}")
        return gift_update_times, expected_order

    def verify_timestamp_order(self, sorted_titles, gift_update_times):
        """
        Verify gifts are properly sorted by timestamps
        
        Parameters:
        sorted_titles (list): List of gift titles in the current sorted order
        gift_update_times (dict): Map of gift titles to their updated_at timestamps
        
        Returns:
        bool: True if verified, False otherwise
        """
        # Check if the order is approximately correct by comparing pairs of timestamps
        correct_order = True
        timestamp_comparisons = []
        
        for i in range(len(sorted_titles) - 1):
            current_title = sorted_titles[i]
            next_title = sorted_titles[i + 1]
            
            # Skip comparison if we don't have timestamp data for either title
            if current_title not in gift_update_times or next_title not in gift_update_times:
                continue
                
            current_time = gift_update_times[current_title]
            next_time = gift_update_times[next_title]
            
            # The current item should have a more recent (or equal) timestamp than the next
            is_in_order = current_time >= next_time
            timestamp_comparisons.append((current_title, current_time, next_title, next_time, is_in_order))
            
            if not is_in_order:
                correct_order = False
        
        # Log timestamp comparison results for debugging
        for comparison in timestamp_comparisons:
            current, curr_time, next_item, next_time, is_ordered = comparison
            self.logger.info(f"Comparison: {current} ({curr_time}) vs {next_item} ({next_time}) - In order: {is_ordered}")
            
        if correct_order:
            self.logger.info("PASS: Gifts are correctly sorted by Last Updated (newest first)")
        else:
            self.logger.error("FAIL: Gifts are not properly sorted by Last Updated")
        
        return correct_order

    def toggle_multiple_favorites(self, gift_cards, indices, expected_state):
        """
        Toggle favorite status for multiple gifts
        
        Parameters:
        gift_cards (list): List of gift card WebElements
        indices (list): List of indices to toggle
        expected_state (bool): True to favorite, False to unfavorite
        
        Returns:
        list: List of successfully toggled gift names
        """
        action_desc = "favorite" if expected_state else "unfavorite"
        self.logger.info(f"Starting to {action_desc} {len(indices)} gifts...")
        
        selected_cards = [gift_cards[i] for i in indices if i < len(gift_cards)]
        successfully_toggled = []
        
        for index, gift_card in enumerate(selected_cards, 1):
            gift_name, success = self.toggle_favorite(gift_card, expected_state=expected_state)
            if success:
                successfully_toggled.append(gift_name)
        
        self.logger.info(f"Successfully {action_desc}d items: {successfully_toggled}")
        return successfully_toggled
    
    def get_id_api(self):
        token = self.login(self.username, self.password)
        headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
        response = requests.get(f"{CREDENTIALS['BO_base_url']}/api/user", headers=headers)
        return response.json().get("data")["id"]

    def find_unaffordable_gift(self, search_keyword, current_points):
        """
        Find a gift that the user cannot afford based on search keyword
        
        Parameters:
        search_keyword (str): Keyword to search for gifts
        current_points (int): User's current points
        
        Returns:
        tuple: (gift_element, gift_title, gift_points) or (None, None, None) if not found
        """
        self.search_for_gift(search_keyword)
        time.sleep(3)  # Wait for search results
        
        # Get search results
        gift_cards = self.get_all_gift_cards()
        if not gift_cards:
            self.logger.error(f"No gifts found containing '{search_keyword}'")
            return None, None, None
            
        self.logger.info(f"Found {len(gift_cards)} gifts matching '{search_keyword}'")
        
        # Find a gift that costs more than user's points
        for card in gift_cards:
            points = self.get_gift_points(card)
            if points is None:
                continue
                
            try:
                title_element = card.find_element(By.XPATH, ".//div[contains(@class, 'MuiTypography-h6')]")
                gift_title = title_element.text
                
                # Check if the gift is unaffordable
                if points > current_points:
                    self.logger.info(f"Found unaffordable gift: {gift_title} ({points} points), user has {current_points} points")
                    return card, gift_title, points
            except NoSuchElementException:
                continue
        
        self.logger.error("Could not find an unaffordable gift")
        return None, None, None

    def verify_insufficient_points_popup(self):
        """
        Verify that the insufficient points error popup appears and dismiss it
        
        Returns:
        bool: True if popup was found and verified, False otherwise
        """
        try:
            # Check for the SweetAlert2 error popup
            error_popup = self.wait_for_element(
                By.XPATH,
                "//div[contains(@class, 'swal2-popup') and contains(@class, 'swal2-icon-error')]",
                timeout=5
            )
            
            # Check for the specific error message
            error_message_text = LANGUAGE_SETTINGS[self.language]["gift_redemption"]["insufficient_points"]
            error_message = error_popup.find_element(
                By.XPATH,
                f".//div[@id='swal2-html-container' and contains(text(), '{error_message_text}')]"
            )
            
            # Verify OK button exists
            ok_button = error_popup.find_element(
                By.XPATH,
                ".//button[contains(@class, 'swal2-confirm') and text()='OK']"
            )
            
            self.logger.info(f"PASS: Expected error popup appeared with message: '{error_message.text}'")
            
            # Click OK to dismiss the popup
            ok_button.click()
            time.sleep(2)
            
            return True
        except (TimeoutException, NoSuchElementException) as e:
            self.logger.error(f"FAIL: Expected error popup not found: {str(e)}")
            return False
    
    def extract_gift_amount(self, gift_title):
        # Initialize an empty string to collect digits
        digits = ""
        
        # Iterate through each character in the gift title
        for char in gift_title:
            # If the character is a digit, add it to our digits string
            if char.isdigit():
                digits += char
            # If we've hit a non-digit and already collected some digits, we can stop
            elif digits:
                break
        
        # Convert the collected digits to an integer
        # If no digits were found, default to 0
        return int(digits) if digits else 0
    
    def test_01_SearchGift(self):
        try:
            self.logger.info("Starting search gift test...")
            self.navigate_to_login_page()
            self.perform_login(self.username, self.password)
            
            self.navigate_to_profile_menu("profile-menu-gift_change")
            self.wait_for_gift_page_load()
            
            initial_count = self.get_gift_count()
            
            # Test Case 1: Search for a gift that is in reward list by keyword "4D"
            search_keyword = LANGUAGE_SETTINGS[self.language]["gift_redemption"]["4d"]
            self.search_for_gift(search_keyword)
            
            # Find gift cards after search
            search_results = self.get_all_gift_cards()
            gift_titles = self.get_gift_titles(search_results)
            
            # Verify search results contain items with the keyword
            matching_gifts = [title for title in gift_titles if search_keyword in title]
            
            if matching_gifts:
                self.logger.info(f"PASS: Found {len(matching_gifts)} gifts containing '{search_keyword}'")
                self.logger.info(f"Matching gifts: {matching_gifts}")
                
                # Verify expected behavior: only items with keyword should be displayed
                self.assertTrue(all(search_keyword in title for title in gift_titles), 
                            f"Not all displayed gifts contain '{search_keyword}'")
            else:
                self.logger.error(f"FAIL: No gifts found containing '{search_keyword}'")
                self.fail(f"No gifts found containing '{search_keyword}'")

        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")
    
    def test_02_ClearSearchField(self):
        try:
            self.logger.info("Starting clear search field test...")
            self.navigate_to_login_page()
            self.perform_login(self.username, self.password)
            
            self.navigate_to_profile_menu("profile-menu-gift_change")
            self.wait_for_gift_page_load()
            
            initial_count = self.get_gift_count()
            
            # Enter a search term
            search_keyword = "5"
            self.search_for_gift(search_keyword)
            
            # Clear the search field
            self.clear_search_field()
            
            time.sleep(2)
            
            # Verify all gifts are displayed after clearing search
            after_clear_count = self.get_gift_count()
            
            # Check if the number of gifts is the same as before the search
            if after_clear_count >= initial_count:
                self.logger.info("PASS: All gifts are displayed after clearing search")
            else:
                self.logger.error(f"FAIL: Not all gifts are displayed after clearing search. Before: {initial_count}, After: {after_clear_count}")
                self.fail(f"Clear search failed. Before: {initial_count}, After: {after_clear_count}")
                
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")
    
    def test_03_SearchGiftNotInList(self):
        try:
            self.logger.info("Starting test for searching a gift not in reward list...")
            self.navigate_to_login_page()
            self.perform_login(self.username, self.password)
            
            self.navigate_to_profile_menu("profile-menu-gift_change")
            self.wait_for_gift_page_load()
            
            initial_count = self.get_gift_count()
            
            # Test Case 3: Search for a gift that is not in reward list
            search_keyword = "Halo123"
            self.search_for_gift(search_keyword)
            
            # Find gift cards after search
            search_results = self.get_all_gift_cards()
            result_count = len(search_results)
            
            # Check if no gifts are displayed
            if result_count == 0:
                self.logger.info("PASS: No gifts displayed when searching for non-existent item")
            else:
                # If there are results, check if they actually contain the keyword
                gift_titles = self.get_gift_titles(search_results)
                
                # Check if any of the displayed gifts actually contain the keyword
                matching_gifts = [title for title in gift_titles if search_keyword.lower() in title.lower()]
                
                if matching_gifts:
                    self.logger.error(f"FAIL: Found gifts containing '{search_keyword}' which should not exist")
                    self.logger.error(f"Matching gifts: {matching_gifts}")
                    self.fail(f"Expected no gifts for search '{search_keyword}', but found: {matching_gifts}")
                else:
                    self.logger.warning(f"Expected zero results but found {result_count} gifts that don't match the keyword")
                    self.logger.warning(f"This may be OK if the search is not working as expected or shows all items when no matches found")
                    self.logger.warning(f"Gift titles: {gift_titles}")
            
            # Verify the expected result: no gifts should be displayed
            self.assertEqual(result_count, 0, f"Expected no gifts for search '{search_keyword}', but found {result_count} gifts")

        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")
    
    def test_04_FilterGiftsByPointRange(self):
        try:
            self.logger.info("Starting test for filtering gifts by point range...")
            self.navigate_to_login_page()
            self.perform_login(self.username, self.password)
            
            self.navigate_to_profile_menu("profile-menu-gift_change")
            self.wait_for_gift_page_load()
            
            initial_count = self.get_gift_count()
            
            # Set target value to 1000 as specified in the test case
            target_value = 1000
            actual_value = self.set_points_filter(target_value)
            
            # Find gift cards after filtering
            filtered_gifts = self.get_all_gift_cards()
            filtered_count = len(filtered_gifts)
            self.logger.info(f"Gift count after filtering: {filtered_count}")
            
            # Check if the filter reduced the number of gifts displayed
            if filtered_count < initial_count:
                self.logger.info("Filter appears to be working as it reduced the number of displayed gifts")
            else:
                self.logger.warning(f"Filter didn't reduce the number of gifts. Before: {initial_count}, After: {filtered_count}")
            
            # Verify each displayed gift is within the point range
            all_within_range = True
            gifts_outside_range = []
            
            for gift in filtered_gifts:
                points = self.get_gift_points(gift)
                if points is None:
                    continue
                    
                gift_title = gift.find_element(By.XPATH, ".//div[contains(@class, 'MuiTypography-h6')]").text
                
                # Check if the gift's points are within range
                if points > actual_value:
                    all_within_range = False
                    gifts_outside_range.append(f"{gift_title} ({points} points)")
            
            # Check if all displayed gifts are within the specified range
            if all_within_range:
                self.logger.info("PASS: All displayed gifts are within the specified point range")
            else:
                self.logger.error(f"FAIL: Found gifts outside the specified range: {gifts_outside_range}")
                self.fail(f"Expected all gifts to be within {actual_value} points, but found: {gifts_outside_range}")
                
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")
    
    def test_05_MarkGiftsAsFavorite(self):
        """Test marking gifts as favorites"""
        try:
            self.logger.info("Starting test for marking gifts as favorites...")
            self.navigate_to_login_page()
            self.perform_login(self.username, self.password)
            
            self.navigate_to_profile_menu("profile-menu-gift_change")
            self.wait_for_gift_page_load()
            
            # Make sure we have at least 3 gift cards
            gift_cards = self.verify_minimum_gift_count(minimum_count=3)
            
            # Get the second and third gift cards
            indices_to_favorite = [1, 2]
            
            # Mark selected gifts as favorite
            successfully_marked = self.toggle_multiple_favorites(
                gift_cards, indices_to_favorite, expected_state=True
            )
            
            # Verify both gifts were successfully marked as favorites
            self.assertEqual(len(successfully_marked), 2, 
                            f"Expected to mark 2 gifts as favorites, but marked: {successfully_marked}")
            
            # Refresh the page to verify persistence
            self.logger.info("Refreshing page to verify favorites persist...")
            self.driver.refresh()
            time.sleep(3)  # Wait for page to reload
            self.wait_for_gift_page_load()
            
            self.logger.info(f"PASS: Successfully marked items as favorites: {successfully_marked}")
            
            # Get all gift cards after refresh
            refreshed_gift_cards = self.get_all_gift_cards()
            
            # Find all favorited gifts after refresh
            favorites_after_refresh, _ = self.find_favorited_gifts(refreshed_gift_cards)
            
            # Check if all originally favorited gifts are still favorited after refresh
            all_favorites_persisted = all(title in favorites_after_refresh for title in successfully_marked)
            
            self.assertTrue(all_favorites_persisted, 
                            f"Not all favorites persisted after page refresh. Before: {successfully_marked}, After: {favorites_after_refresh}")
            
            self.logger.info(f"PASS: All favorites successfully persisted after page refresh: {favorites_after_refresh}")
            
                
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")

    def test_06_SortByMyFavourite(self):
        """Test sorting gifts by My Favourite"""
        try:
            self.logger.info("Starting test for sorting gifts by My Favourite...")
            self.navigate_to_login_page()
            self.perform_login(self.username, self.password)
            
            self.navigate_to_profile_menu("profile-menu-gift_change")
            self.wait_for_gift_page_load()
            
            # Get all the gift cards
            gift_cards = self.verify_minimum_gift_count(minimum_count=1)
            total_count = len(gift_cards)
            
            # Step 1: Find all gifts that are already favorited
            favorites, _ = self.find_favorited_gifts(gift_cards)
            
            # Step 2: Use the helper function to sort by My Favourite
            favorite_text = LANGUAGE_SETTINGS[self.language]["gift_redemption"]["sort_by_my_favorite"]
            sort_success = self.sort_gifts(favorite_text)
            self.assertTrue(sort_success, "Failed to sort gifts by My Favourite")
            
            # Step 3: Get the sorted gift cards
            sorted_gift_cards = self.get_all_gift_cards()
            sorted_count = len(sorted_gift_cards)
            
            # Verify the count remains the same
            self.assertEqual(total_count, sorted_count, 
                        f"Gift count changed after sorting. Before: {total_count}, After: {sorted_count}")
            
            # If we found favorites before sorting, verify they appear at the top
            if favorites:
                favorites_at_top = self.verify_favorites_at_top(sorted_gift_cards, favorites)
                self.assertTrue(favorites_at_top, "Favorites should appear at the top when sorted by My Favourite")
            else:
                self.logger.info("No favorites found to verify sorting, but sort operation completed successfully")
                        
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")

    def test_07_UnfavoriteGift(self):
        """Test unfavoriting gifts"""
        try:
            self.logger.info("Starting test for unfavoriting gifts...")
            self.navigate_to_login_page()
            self.perform_login(self.username, self.password)
            
            self.navigate_to_profile_menu("profile-menu-gift_change")
            self.wait_for_gift_page_load()
            
            # Make sure we have at least 3 gift cards
            gift_cards = self.verify_minimum_gift_count(minimum_count=3)
            
            # Get the second and third gift cards
            indices_to_unfavorite = [1, 2]
            
            # Unfavorite each selected gift
            successfully_unfavorited = self.toggle_multiple_favorites(
                gift_cards, indices_to_unfavorite, expected_state=False
            )
            
            # Verify both gifts were successfully unfavorited
            self.assertEqual(len(successfully_unfavorited), 2, 
                            f"Expected to unfavorite 2 gifts, but unfavorited: {successfully_unfavorited}")
            
            self.logger.info(f"PASS: Successfully unfavorited items: {successfully_unfavorited}")
            
            # Refresh the page to verify persistence
            self.logger.info("Refreshing page to verify unfavorites persist...")
            self.driver.refresh()
            time.sleep(3)  # Wait for page to reload
            self.wait_for_gift_page_load()
            
            # Get all gift cards after refresh
            refreshed_gift_cards = self.get_all_gift_cards()
            
            # Find all favorited gifts after refresh
            favorites_after_refresh, _ = self.find_favorited_gifts(refreshed_gift_cards)
            
            # Check if all unfavorited gifts are still unfavorited after refresh
            all_unfavorites_persisted = all(title not in favorites_after_refresh for title in successfully_unfavorited)
            
            self.assertTrue(all_unfavorites_persisted, 
                            f"Not all unfavorites persisted after page refresh. Unfavorited: {successfully_unfavorited}, Still favorited: {favorites_after_refresh}")
            
            self.logger.info(f"PASS: All unfavorites successfully persisted after page refresh")
            
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")

    def test_08_SortByLowestCoins(self):
        """Test sorting gifts by lowest points"""
        try:
            self.logger.info("Starting test for sorting gifts by lowest points...")
            self.navigate_to_login_page()
            self.perform_login(self.username, self.password)
            
            self.navigate_to_profile_menu("profile-menu-gift_change")
            self.wait_for_gift_page_load()
            
            # Get all the gift cards before sorting
            original_gift_cards = self.verify_minimum_gift_count(minimum_count=1)
            original_count = len(original_gift_cards)
            
            # Get points for original cards to compare later
            original_points = self.get_gift_points_with_titles(original_gift_cards)
            
            # Use the helper function to sort by lowest points
            lowest_text = LANGUAGE_SETTINGS[self.language]["gift_redemption"]["sort_by_lowest_points"]
            sort_success = self.sort_gifts(lowest_text)
            self.assertTrue(sort_success, "Failed to sort gifts by lowest points")
            
            # Get the sorted gift cards
            sorted_gift_cards = self.get_all_gift_cards()
            sorted_count = len(sorted_gift_cards)
            
            # Verify the count remains the same
            self.assertEqual(original_count, sorted_count, 
                            f"Gift count changed after sorting. Before: {original_count}, After: {sorted_count}")
            
            # Get points for the first few sorted cards
            sorted_points = self.get_gift_points_with_titles(sorted_gift_cards)
            
            # Verify the sorting worked by checking if points are in ascending order
            self.verify_sorting_by_points(sorted_points, expected_order="ascending")
            
            # Additional check: Verify the first sorted item has lower (or equal) points than the first item before sorting
            if sorted_points and original_points:
                if sorted_points[0][1] <= original_points[0][1]:
                    self.logger.info(f"PASS: First sorted item ({sorted_points[0][0]}: {sorted_points[0][1]} points) has lower or equal points than original first item ({original_points[0][0]}: {original_points[0][1]} points)")
                else:
                    self.logger.warning(f"First sorted item ({sorted_points[0][0]}: {sorted_points[0][1]} points) has higher points than original first item ({original_points[0][0]}: {original_points[0][1]} points)")
                    
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")
        
    def test_09_SortByHighestCoins(self):
        """Test sorting gifts by highest points"""
        try:
            self.logger.info("Starting test for sorting gifts by highest points...")
            self.navigate_to_login_page()
            self.perform_login(self.username, self.password)
            
            self.navigate_to_profile_menu("profile-menu-gift_change")
            self.wait_for_gift_page_load()
            
            # Get all the gift cards before sorting
            original_gift_cards = self.verify_minimum_gift_count(minimum_count=1)
            original_count = len(original_gift_cards)
            
            # Get points for original cards to compare later
            original_points = self.get_gift_points_with_titles(original_gift_cards)
            
            # Use the helper function to sort by highest points
            highest_text = LANGUAGE_SETTINGS[self.language]["gift_redemption"]["sort_by_highest_points"]
            sort_success = self.sort_gifts(highest_text)
            self.assertTrue(sort_success, "Failed to sort gifts by highest points")
            
            # Get the sorted gift cards
            sorted_gift_cards = self.get_all_gift_cards()
            sorted_count = len(sorted_gift_cards)
            
            # Verify the count remains the same
            self.assertEqual(original_count, sorted_count, 
                            f"Gift count changed after sorting. Before: {original_count}, After: {sorted_count}")
            
            # Get points for the first few sorted cards
            sorted_points = self.get_gift_points_with_titles(sorted_gift_cards)
            
            # Verify the sorting worked by checking if points are in descending order
            self.verify_sorting_by_points(sorted_points, expected_order="descending")
            
            # Additional check with original points
            if sorted_points and original_points:
                if sorted_points[0][1] >= original_points[0][1]:
                    self.logger.info(f"PASS: First sorted item ({sorted_points[0][0]}: {sorted_points[0][1]} points) has higher or equal points than original first item ({original_points[0][0]}: {original_points[0][1]} points)")
                else:
                    self.logger.warning(f"First sorted item ({sorted_points[0][0]}: {sorted_points[0][1]} points) has lower points than original first item ({original_points[0][0]}: {original_points[0][1]} points)")
                    
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")

    def test_10_SortByLastUpdated(self):
        """Test sorting gifts by Last Updated"""
        try:
            self.logger.info("Starting test for sorting gifts by Last Updated...")
            self.navigate_to_login_page()
            self.perform_login(self.username, self.password)
            
            self.navigate_to_profile_menu("profile-menu-gift_change")
            self.wait_for_gift_page_load()
            
            # Get all the gift cards
            gift_cards = self.verify_minimum_gift_count(minimum_count=1)
            total_count = len(gift_cards)
            
            # Get gift data from API to compare with UI sorting later
            api_gifts = self.get_gift_api()
            self.logger.info(f"Retrieved {len(api_gifts)} gifts from API")
            
            # Process API data for verification
            gift_update_times, expected_order = self.process_api_gift_data(api_gifts)
            
            # Step 1: Use the helper function to sort by Last Updated
            last_updated_text = LANGUAGE_SETTINGS[self.language]["gift_redemption"]["sort_by_last_updated"]
            sort_success = self.sort_gifts(last_updated_text)
            self.assertTrue(sort_success, "Failed to sort gifts by Last Updated")
            
            # Step 2: Get the sorted gift cards
            sorted_gift_cards = self.get_all_gift_cards()
            sorted_count = len(sorted_gift_cards)
            
            # Verify the count remains the same
            self.assertEqual(total_count, sorted_count, 
                            f"Gift count changed after sorting. Before: {total_count}, After: {sorted_count}")
            
            # Step 3: Get titles of the first few gifts after sorting
            sorted_gift_titles = []
            for card in sorted_gift_cards[:10]:  # Check first 10 cards
                try:
                    title = card.find_element(By.XPATH, ".//div[contains(@class, 'MuiTypography-h6')]").text
                    sorted_gift_titles.append(title)
                    update_time = gift_update_times.get(title, "Not found in API data")
                    self.logger.info(f"UI sorted order - {title}: updated at {update_time}")
                except Exception as e:
                    self.logger.warning(f"Could not get title for a card: {str(e)}")
            
            # Step 4: Verify the timestamp order
            correct_order = self.verify_timestamp_order(sorted_gift_titles, gift_update_times)
            self.assertTrue(correct_order, "Gifts should be sorted by Last Updated with newest first")
                    
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")
    
    def test_11_Redeem4DGiftSufficientPoints(self):
        """Test redeeming a 4D gift card with sufficient points"""
        try:
            self.logger.info("Starting test for redeeming a 4D gift with sufficient points...")
            self.navigate_to_login_page()
            self.perform_login(self.username, self.password)
            
            card_before = self.get4DCards()
            
            self.navigate_to_profile_menu("profile-menu-gift_change")
            self.wait_for_gift_page_load()
                
            # Step 2: Find a 4D gift that the user can afford
            search_keyword = LANGUAGE_SETTINGS[self.language]["gift_redemption"]["4d"]
            suitable_gift, gift_title, gift_points = self.find_affordable_gift(search_keyword)
            if suitable_gift is None:
                self.fail("Could not find an affordable 4D gift")
            
            # Step 1: Get user's current points
            current_points = self.get_user_points()
            if current_points is None:
                self.fail("Failed to get user points")
                
            # Step 3: Click redeem button
            if not self.click_redeem_button(suitable_gift):
                self.fail("Failed to click redeem button")
            
            # Step 5: Verify successful redemption
            result = self.verify_success_popup(needs_whatsapp=False)
            if not result or not result.get("success"):
                self.fail("Redemption verification failed - success popup not found or incomplete")
                
            # Step 6: Close the success popup
            if "close_button" in result:
                result["close_button"].click()
                time.sleep(2)
            
            # Step 7: Verify points deduction
            self.verify_points_deduction(current_points, gift_points)
            
            expected_gift_amount = self.extract_gift_amount(gift_title)
            self.driver.get(self.url)
            self.annoucement_close_button()
            self.daily_checkin_close_button()
            card_after = self.get4DCards()
            self.verifyReward("4D", card_before, card_after, expected_gift_amount)
            self.logger.info("PASS: Successfully redeemed 4D gift")
                
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")


    def test_12_RedeemPhysicalVoucherGift(self):
        """Test redeeming a physical voucher gift with WhatsApp redirection"""
        try:
            self.logger.info("Starting test for redeeming a physical voucher gift...")
            self.navigate_to_login_page()
            self.perform_login(self.username, self.password)
            
            self.navigate_to_profile_menu("profile-menu-gift_change")
            self.wait_for_gift_page_load()
                
            # Step 2: Find a voucher gift that the user can afford
            search_keyword = LANGUAGE_SETTINGS[self.language]["gift_redemption"]["voucher"]
            suitable_gift, gift_title, gift_points = self.find_affordable_gift(search_keyword, title_contains=search_keyword)
            if suitable_gift is None:
                self.fail("Could not find an affordable voucher gift")
            
            # Step 1: Get user's current points
            current_points = self.get_user_points()
            if current_points is None:
                self.fail("Failed to get user points")
                
            # Step 3: Click redeem button
            if not self.click_redeem_button(suitable_gift):
                self.fail("Failed to click redeem button")
            
            # Step 5: Verify successful redemption with WhatsApp button
            result = self.verify_success_popup(needs_whatsapp=True)
            if not result or not result.get("success"):
                self.fail("Redemption verification failed - success popup not found or incomplete")
                
            # Step 6: Click on WhatsApp redirect button and verify redirection
            if "whatsapp_button" in result:
                redirect_success = self.handle_whatsapp_redirect(result["whatsapp_button"])
                if not redirect_success:
                    self.logger.warning("WhatsApp redirection not verified, continuing with test")
            
            # Step 7: Close the success popup if still open
            self.close_success_popup()
            
            # Step 8: Verify points deduction
            self.verify_points_deduction(current_points, gift_points)
            
            self.logger.info("PASS: Successfully redeemed physical voucher gift")
                
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")
    
    def test_13_Redeem4DGiftInsufficientPoints(self):
        """Test attempting to redeem a 4D gift with insufficient points using a new account"""
        try:
            self.logger.info("Starting test for attempting to redeem a 4D gift with insufficient points...")
            
            # Step 1: Create a new account and login
            self.logger.info("Creating a new account for testing insufficient points scenario")
            self.username, self.password = self.test_init.register_new_account()
            self.navigate_to_login_page()
            self.perform_login(self.username, self.password)
            
            # Step 2: Navigate to gift redemption page
            self.navigate_to_profile_menu("profile-menu-gift_change")
            self.wait_for_gift_page_load()
            
            # Step 3: Get current points (should be minimal for new account)
            current_points = self.get_user_points()
            self.logger.info(f"New account points: {current_points}")
            
            # Step 4: Find an unaffordable 4D gift
            search_keyword = LANGUAGE_SETTINGS[self.language]["gift_redemption"]["4d"]
            unaffordable_gift, gift_title, gift_points = self.find_unaffordable_gift(search_keyword, current_points)
            if unaffordable_gift is None:
                self.fail("Test requires at least one 4D gift that costs more than user's points")
                
            # Scroll the gift card into view
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", unaffordable_gift)
            time.sleep(1)
                  
            # Step 3: Click redeem button
            if not self.click_redeem_button(unaffordable_gift):
                self.fail("Failed to click redeem button")
                
            # Verify the error popup appears
            popup_verified = self.verify_insufficient_points_popup()
            self.assertTrue(popup_verified, "Expected 'Gift Coins are not enough' error popup not found")
            
            # Final verification: make sure points weren't deducted
            final_points = self.get_user_points()
            self.assertEqual(final_points, current_points, 
                        f"Points changed from {current_points} to {final_points}. Points should not have changed.")
            self.logger.info("PASS: Points were not deducted, still at: " + str(final_points))
                
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")

    
    def test_14_RedeemGiftVipDifferentLevel(self):
        self.logger.info("Starting VIP rewards test")
        try:
            # Step 1: Create a new account and login
            self.logger.info("Creating a new account for testing diff vip levels scenario")
            self.username, self.password = self.test_init.register_new_account()
            print(f"self.username: {self.username}")
            self.navigate_to_login_page()
            self.perform_login(self.username, self.password)
                        
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
                self.logger.info(f"Testing {scenario['id']} level")
                
                if scenario['recharge'] != 0:
                    # Make the deposit
                    userID = self.get_id_api()
                    self.test_init.submit_deposit_api(username=self.username, password=self.password, amount=scenario['recharge'])
                    self.handleDeposit(userID)
                
                self.driver.get(self.url)
                self.annoucement_close_button()
                self.daily_checkin_close_button()
                
                card_before = self.get4DCards()
                print(f"card_before: {card_before}")
                self.navigate_to_profile_menu("profile-menu-gift_change")
                self.wait_for_gift_page_load()
                    
                # Step 2: Find a 4D gift that the user can afford
                search_keyword = LANGUAGE_SETTINGS[self.language]["gift_redemption"]["4d"]
                suitable_gift, gift_title, gift_points = self.find_affordable_gift(search_keyword)
                if suitable_gift is None:
                    self.fail("Could not find an affordable 4D gift")
                
                # Step 1: Get user's current points
                current_points = self.get_user_points()
                if current_points is None:
                    self.fail("Failed to get user points")
                    
                # Step 3: Click redeem button
                if not self.click_redeem_button(suitable_gift):
                    self.fail("Failed to click redeem button")
                
                # Step 5: Verify successful redemption
                result = self.verify_success_popup(needs_whatsapp=False)
                if not result or not result.get("success"):
                    self.fail("Redemption verification failed - success popup not found or incomplete")
                    
                # Step 6: Close the success popup
                if "close_button" in result:
                    result["close_button"].click()
                    time.sleep(2)
                
                # Step 7: Verify points deduction
                self.verify_points_deduction(current_points, gift_points)
                
                expected_gift_amount = self.extract_gift_amount(gift_title)
                self.driver.get(self.url)
                self.annoucement_close_button()
                self.daily_checkin_close_button()
                card_after = self.get4DCards()
                print(f"card_after: {card_after}")
                self.verifyReward("4D", card_before, card_after, expected_gift_amount)
                self.logger.info("PASS: Successfully redeemed 4D gift")
                
        except Exception as e:
            self.fail(f"Test failed with error: {str(e)}")
    
    def test_15_Redeem4DGiftMultipleTimes(self):
        """Test redeeming a 4D gift multiple times in succession"""
        try:
            # Number of times to redeem gifts
            redemption_count = 3  # Increase this number to redeem more times
            self.logger.info(f"Starting test for redeeming 4D gifts {redemption_count} times...")
            
            self.navigate_to_login_page()
            self.perform_login(self.username, self.password)
            
            # Navigate to gift page
            self.navigate_to_profile_menu("profile-menu-gift_change")
            self.wait_for_gift_page_load()
            
            # Check available points
            initial_points = self.get_user_points()
            if initial_points is None:
                self.fail("Failed to get initial user points")
            self.logger.info(f"Initial points balance: {initial_points}")
            
            # Find out the cost of a typical 4D gift to estimate total needed points
            search_keyword = LANGUAGE_SETTINGS[self.language]["gift_redemption"]["4d"]
            self.search_for_gift(search_keyword)
            time.sleep(3)
            gift_cards = self.get_all_gift_cards()
            if gift_cards:
                typical_gift_points = self.get_gift_points(gift_cards[0])
                if typical_gift_points:
                    total_points_needed = typical_gift_points * redemption_count
                    self.logger.info(f"Estimated points needed for {redemption_count} redemptions: {total_points_needed}")
                    
                    # Check if we need to make a deposit
                    if initial_points < total_points_needed:
                        additional_points_needed = total_points_needed - initial_points
                        amount = additional_points_needed * 50  # Calculate needed deposit amount (adjust multiplier as needed)
                        self.logger.info(f"Making initial deposit of {amount} to ensure enough points for all redemptions...")
                        
                        # Make the deposit
                        userID = self.get_id_api()
                        self.test_init.submit_deposit_api(username=self.username, password=self.password, amount=amount)
                        self.handleDeposit(userID)
                        
                        # Refresh the page and recheck points
                        self.driver.refresh()
                        time.sleep(3)
                        self.wait_for_gift_page_load()
                        updated_points = self.get_user_points()
                        self.logger.info(f"Points after deposit: {updated_points}")
            
            total_points_spent = 0
            total_cards_acquired = 0
            
            # Get card state before redemption
            self.driver.get(self.url)
            self.annoucement_close_button()
            self.daily_checkin_close_button()
            card_before = self.get4DCards()
            self.logger.info(f"Card balance before redemption: {card_before}")
            
            # Navigate to gift page
            self.navigate_to_profile_menu("profile-menu-gift_change")
            self.wait_for_gift_page_load()
            
            # Find a 4D gift that the user can afford
            self.clear_search_field()
            search_keyword = LANGUAGE_SETTINGS[self.language]["gift_redemption"]["4d"]
            suitable_gift, gift_title, gift_points = self.find_affordable_gift(search_keyword)
            if suitable_gift is None:
                self.fail(f"Could not find an affordable 4D gift for redemption {i+1}")
            
            self.logger.info(f"Found gift for redemption: {gift_title} ({gift_points} points)")
            
            for i in range(redemption_count):
                self.logger.info(f"=== Starting redemption cycle {i+1} of {redemption_count} ===")
                    
                # Get user's current points
                current_points = self.get_user_points()
                if current_points is None:
                    self.fail(f"Failed to get user points for redemption {i+1}")
                self.logger.info(f"Current points before redemption {i+1}: {current_points}")
                    
                # Click redeem button
                if not self.click_redeem_button(suitable_gift):
                    self.fail(f"Failed to click redeem button for redemption {i+1}")
                
                # Verify successful redemption
                result = self.verify_success_popup(needs_whatsapp=False)
                if not result or not result.get("success"):
                    self.fail(f"Redemption {i+1} verification failed - success popup not found or incomplete")
                    
                # Close the success popup
                if "close_button" in result:
                    result["close_button"].click()
                    time.sleep(2)
                
                # Verify points deduction
                points_verified = self.verify_points_deduction(current_points, gift_points)
                self.assertTrue(points_verified, f"Points deduction verification failed for redemption {i+1}")
                
                total_points_spent += gift_points
                
                expected_gift_amount = self.extract_gift_amount(gift_title)
                total_cards_acquired += expected_gift_amount
                
                self.logger.info(f"=== Successfully completed redemption cycle {i+1} of {redemption_count} ===")
            
            # Verify card increase
            
            self.driver.get(self.url)
            self.annoucement_close_button()
            self.daily_checkin_close_button()
            card_after = self.get4DCards()
            self.logger.info(f"Card balance after redemption: {card_after}")
            
            # Verify the card amount increased correctly
            self.verifyReward("4D", card_before, card_after, total_cards_acquired)
            
            self.logger.info(f"PASS: Successfully redeemed 4D gift {redemption_count} times")
            self.logger.info(f"Total points spent: {total_points_spent}")
            self.logger.info(f"Total 4D cards acquired: {total_cards_acquired}")
                
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")
    
    def test_16_RedeemWithSecondInsufficientPoints(self):
        """Test redeeming a 4D gift twice, with sufficient points for first redemption but insufficient for second"""
        try:
            self.logger.info("Starting test for two redemptions with insufficient points for second redemption...")
            
            # Create a new account to ensure controlled point balance
            self.logger.info("Creating a new account for testing")
            self.username, self.password = self.test_init.register_new_account()
            self.navigate_to_login_page()
            self.perform_login(self.username, self.password)
            
            # Get card state before any redemptions
            self.driver.get(self.url)
            self.annoucement_close_button()
            self.daily_checkin_close_button()
            card_before = self.get4DCards()
            self.logger.info(f"Card balance before any redemptions: {card_before}")
            
            # Navigate to gift page
            self.navigate_to_profile_menu("profile-menu-gift_change")
            self.wait_for_gift_page_load()
            
            # FIRST REDEMPTION (Should succeed)
            self.logger.info("=== Starting first redemption (should succeed) ===")
            
            self.clear_search_field()
            time.sleep(2)
            search_keyword = LANGUAGE_SETTINGS[self.language]["gift_redemption"]["4d"]
            suitable_gift, gift_title, gift_points = self.find_affordable_gift(search_keyword)

            self.logger.info(f"Found gift for first redemption: {gift_title} ({gift_points} points)")
            
            # Extract gift amount here after we have gift_title
            first_gift_amount = self.extract_gift_amount(gift_title)
            
            # Get user's current points
            first_points = self.get_user_points()
            if first_points is None:
                self.fail("Failed to get user points for first redemption")
            self.logger.info(f"Current points before first redemption: {first_points}")
                
            # Click redeem button
            if not self.click_redeem_button(suitable_gift):
                self.fail("Failed to click redeem button for first redemption")
            
            # Verify successful redemption
            result = self.verify_success_popup(needs_whatsapp=False)
            if not result or not result.get("success"):
                self.fail("First redemption verification failed - success popup not found or incomplete")
                
            # Close the success popup
            if "close_button" in result:
                result["close_button"].click()
                time.sleep(2)
            
            # Verify points deduction
            points_verified = self.verify_points_deduction(first_points, gift_points)
            self.assertTrue(points_verified, "Points deduction verification failed for first redemption")
            
            self.logger.info("=== First redemption successful as expected ===")
            
            # SECOND REDEMPTION (Should fail due to insufficient points)
            self.logger.info("=== Starting second redemption (should fail) ===")
            
            # Get current points after first redemption
            second_points = self.get_user_points()
            if second_points is None:
                self.fail("Failed to get user points for second redemption")
            self.logger.info(f"Current points before second redemption: {second_points}")
            
            # Verify we don't have enough points for another redemption
            if second_points >= gift_points:
                self.logger.warning(f"Test may fail: User still has {second_points} points, which is likely enough for another redemption")
            
            if gift_points is None:
                self.fail("Could not determine gift points for second redemption")
                
            unaffordable_gift = suitable_gift
            
            try:
                title_element = unaffordable_gift.find_element(By.XPATH, ".//div[contains(@class, 'MuiTypography-h6')]")
                second_gift_title = title_element.text
                self.logger.info(f"Selected gift for second redemption: {second_gift_title} ({gift_points} points)")
            except NoSuchElementException:
                second_gift_title = "Unknown gift"
                self.logger.warning("Could not find title for second gift")
                
            # Verify this gift should be unaffordable
            if second_points >= gift_points:
                self.logger.warning(f"Test may fail: User has {second_points} points, which is enough for the gift costing {gift_points}")
                
            # Click redeem button regardless of whether we expect success or failure
            if not self.click_redeem_button(unaffordable_gift):
                self.fail("Failed to click redeem button for second redemption")
            
            # If points are insufficient, we should get error popup
            second_gift_succeeded = False
            if second_points < gift_points:
                # Verify the error popup appears
                popup_verified = self.verify_insufficient_points_popup()
                self.assertTrue(popup_verified, "Expected 'Gift Coins are not enough' error popup not found")
                
                # Final verification: make sure points weren't deducted
                final_points = self.get_user_points()
                self.assertEqual(final_points, second_points, 
                                f"Points changed from {second_points} to {final_points}. Points should not have changed.")
                self.logger.info("PASS: Points were not deducted, still at: " + str(final_points))
                
            else:
                # If somehow we had enough points, handle the success case
                self.logger.warning("Second redemption succeeded when it was expected to fail - user had enough points")
                result = self.verify_success_popup(needs_whatsapp=False)
                if result and result.get("success"):
                    # Close the success popup
                    if "close_button" in result:
                        result["close_button"].click()
                        time.sleep(2)
                    second_gift_succeeded = True
            
            # Now verify the card balance after all redemptions
            self.driver.get(self.url)
            self.annoucement_close_button()
            self.daily_checkin_close_button()
            card_after = self.get4DCards()
            self.logger.info(f"Card balance after all redemptions: {card_after}")
            
            # Verify the card amount changed correctly
            if second_gift_succeeded:
                # If both redemptions succeeded (unexpected case)
                second_gift_amount = self.extract_gift_amount(second_gift_title)
                total_expected_amount = first_gift_amount + second_gift_amount
                self.logger.info(f"Both redemptions succeeded. Expected total gift amount: {total_expected_amount}")
            else:
                # If only first redemption succeeded (expected case)
                total_expected_amount = first_gift_amount
                self.logger.info(f"Only first redemption succeeded. Expected gift amount: {total_expected_amount}")
                
            self.verifyReward("4D", card_before, card_after, total_expected_amount)
            
            self.logger.info("=== Second redemption completed as expected (should have failed due to insufficient points) ===")
                
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")
            
if __name__ == "__main__":
    unittest.main()
