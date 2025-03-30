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
from config.constant import LIVE_AGENT_URL
from tests.authentication_test.base_test import BaseTest
from tests.test_init import TestInit
from selenium.webdriver.firefox.options import Options
from selenium.webdriver import Firefox
from selenium.webdriver import Chrome
from selenium import webdriver


class TestLiveAgent(BaseTest):

    def __init__(self, methodName="runTest", language=None, browser=None):
        super().__init__(methodName, language, browser)
        self.test_init = TestInit(methodName="runTest", language=language, browser=browser)

    def setUp(self):
        super().setUp()

        max_attempts = 3
        attempt = 0

        while attempt < max_attempts:
            result = self.test_init.register_new_account()

            if result and isinstance(result, tuple) and len(result) == 2:
                self.username, self.password = result

                if self.username is not None:
                    self.logger.info(f"Successfully registered account: {self.username}")
                    break

            attempt += 1
            self.logger.error(f"Registration attempt {attempt} failed. Got result: {result}")

            if attempt < max_attempts:
                self.logger.info("Retrying registration...")
                time.sleep(2)
            else:
                raise Exception("Failed to register new account after maximum attempts")

        self.navigate_to_login_page()
        self.perform_login(self.username, self.password)
        self.userID = self.get_id_number()
        self.logger.info(f"User ID: {self.userID}")
        self.navigate_to_live_agent()

    def tearDown(self):
        if hasattr(self, "driver"):
            self.driver.quit()

    def navigate_to_live_agent(self):
        live_agent_section = self.driver.find_element(By.ID, "chatbot-girl-button")
        live_agent_section.click()

    def check_whatsapp_url(self):
        try:
            WebDriverWait(self.driver, 10).until(lambda d: len(d.window_handles) > 1)

            self.driver.switch_to.window(self.driver.window_handles[-1])

            current_url = self.driver.current_url
            self.logger.info(f"Redirected to URL: {current_url}")

            expected_whatsapp_base_url = LIVE_AGENT_URL["whatsapp_base_url"]

            self.assertTrue(
                current_url.startswith(expected_whatsapp_base_url),
                f"Not redirected to expected URL. Got: {current_url}"
            )
            phone_match = re.search(r"phone=(\d+)", current_url)
            self.assertIsNotNone(phone_match, "Could not extract phone number from URL")

            phone_number = phone_match.group(1)
            self.logger.info(f"Found phone number: {phone_number}")

            self.assertTrue(phone_number.isdigit(), "Phone number should contain only digits")
            self.assertTrue(len(phone_number) >= 11, "Phone number is too short to be valid")
            self.assertTrue(len(phone_number) <= 12, "Phone number is too long to be valid")

            self.logger.info("✓ Successfully redirected to WhatsApp with valid phone number")

            self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[0])

        except Exception as e:
            self.logger.error(f"Redirection verification failed: {str(e)}")
            self.fail(f"Failed to verify redirection: {str(e)}")

    def test_01_AIChatRedirection(self):
        try:
            time.sleep(2)
            AI_chat = self.driver.find_element(By.ID, "chatbot-button-livechat")
            AI_chat.click()
            time.sleep(2)
            try:
                WebDriverWait(self.driver, 10).until(lambda d: len(d.window_handles) > 1)
                self.driver.switch_to.window(self.driver.window_handles[-1])

                current_url = self.driver.current_url
                self.logger.info(f"Redirected to URL: {current_url}")

                expected_chatbot_base_url = LIVE_AGENT_URL["chatbot_base_url"]

                self.assertTrue(
                    current_url.startswith(expected_chatbot_base_url),
                    f"Not redirected to expected URL. Got: {current_url}"
                )

                expected_lang_param = f"lang={self.language}"
                self.assertIn(
                    expected_lang_param, current_url,
                    f"Language parameter is incorrect. Expected: {expected_lang_param}"
                )
                self.logger.info("✓ Successfully redirected to chatbot with correct parameters")

                self.driver.close()
                self.driver.switch_to.window(self.driver.window_handles[0])

            except Exception as e:
                self.logger.error(f"Redirection verification failed: {str(e)}")
                self.fail(f"Failed to verify redirection: {str(e)}")
        except Exception as e:
            self.fail(f"Test failed: {str(e)}")

    def test_02_AIWhatsappRedirection(self):
        try:
            time.sleep(2)
            AI_chat = self.driver.find_element(By.ID, "chatbot-button-bobo_ai_whatsapp")
            AI_chat.click()
            time.sleep(2)
            self.check_whatsapp_url()

        except Exception as e:
            self.fail(f"Test failed: {str(e)}")

    def test_03_AITelegramRedirection(self):
        try:
            time.sleep(2)
            AI_chat = self.driver.find_element(By.ID, "chatbot-button-bobo_telegram")
            AI_chat.click()
            self.logger.info("Telegram button clicked")
            time.sleep(4)
            WebDriverWait(self.driver, 10).until(lambda d: len(d.window_handles) > 1)

            self.driver.switch_to.window(self.driver.window_handles[-1])

            current_url = self.driver.current_url
            self.logger.info(f"Redirected to URL: {current_url}")
            time.sleep(2)

            expected_telegram_base_url = LIVE_AGENT_URL["telegram_base_url"]
            self.assertTrue(
                current_url.startswith(expected_telegram_base_url),
                f"Not redirected to expected Telegram URL. Got: {current_url}"
            )

            self.logger.info("✓ Successfully redirected to Telegram")

            self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[0])

        except Exception as e:
            self.fail(f"Test failed: {str(e)}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    unittest.main()
