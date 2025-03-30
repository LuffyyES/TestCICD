#spamdeposit

import unittest
import requests
import random
import string
import concurrent.futures
import logging
import time
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, Tuple, BinaryIO, TypeVar, Type
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from urllib3 import PoolManager
from config.constant import CREDENTIALS
from tests.test_init import TestInit

retry_strategy = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])

T = TypeVar('T')


class CustomAdapter(HTTPAdapter):

    def init_poolmanager(self, connections: int, maxsize: int, block: bool = False) -> None:
        self.poolmanager = PoolManager(num_pools=connections, maxsize=maxsize, block=block, retries=self.max_retries)

    def _get_pool_manager_kwargs(self) -> Dict[str, Any]:
        return {
            'num_pools': self._pool_connections,
            'maxsize': self._pool_maxsize,
            'block': self._pool_block,
            'retries': self.max_retries
        }


http = requests.Session()
adapter = CustomAdapter(pool_connections=25, pool_maxsize=25, max_retries=retry_strategy)
http.mount("https://", adapter)
http.mount("http://", adapter)


class TestSpamDeposit(unittest.TestCase):
    USER_COUNT = 20
    MAX_WORKERS = 5

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
            handler = logging.FileHandler('spam_deposit_test.log')
            handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            self.logger.addHandler(handler)

        self.test_init = TestInit(methodName="runTest", language=language, browser=browser)
        self.IMAGE_URL = CREDENTIALS["image_url"]
        self.IMAGE_FILENAME = CREDENTIALS["image_path"]
        self.image_path = self.download_image()

    def download_image(self):
        max_retries = 3
        retry_delay = 1
        image_path = Path(self.IMAGE_FILENAME)

        for attempt in range(max_retries):
            try:
                self.logger.info(f"Attempting to download image from {self.IMAGE_URL}")

                response = http.get(self.IMAGE_URL, timeout=30)
                response.raise_for_status()

                content_type = response.headers.get('content-type', '')
                if not content_type.startswith('image/'):
                    raise ValueError(f"Response is not an image. Content-Type: {content_type}")

                image_path.write_bytes(response.content)
                self.logger.info(f"Successfully downloaded image to {image_path}")
                return image_path

            except Exception as e:
                self.logger.warning(f"Image download attempt {attempt + 1} failed: {str(e)}")

                if attempt < max_retries - 1:
                    self.logger.info(f"Waiting {retry_delay}s before retry...")
                    time.sleep(retry_delay)
                    retry_delay *= 2

                    self.IMAGE_URL = CREDENTIALS["replace_image_url"]
                    self.logger.info(f"Switching to alternate URL: {self.IMAGE_URL}")
                    continue

        try:
            self.logger.info("Creating fallback test image...")
            fallback_image_bytes = bytes.fromhex(
                'FFD8FFE000104A46494600010100000100010000FFDB004300080606070605080707070909080A0C140D0C0B0B0C1912130F141D1A1F1E1D1A1C1C20242E2720222C231C1C2837292C30313434341F27393D38323C2E333432FFDB0043010909090C0B0C180D0D1832211C213232323232323232323232323232323232323232323232323232323232323232323232323232323232323232323232323232FFC00011080001000103012200021101031101FFC4001F0000010501010101010100000000000000000102030405060708090A0BFFC400B5100002010303020403050504040000017D01020300041105122131410613516107227114328191A1082342B1C11552D1F02433627282090A161718191A25262728292A3435363738393A434445464748494A535455565758595A636465666768696A737475767778797A838485868788898A92939495969798999AA2A3A4A5A6A7A8A9AAB2B3B4B5B6B7B8B9BAC2C3C4C5C6C7C8C9CAD2D3D4D5D6D7D8D9DAE1E2E3E4E5E6E7E8E9EAF1F2F3F4F5F6F7F8F9FAFFC4001F0100030101010101010101010000000000000102030405060708090A0BFFC400B51100020102040403040705040400010277000102031104052131061241510761711322328108144291A1B1C109233352F0156272D10A162434E125F11718191A262728292A35363738393A434445464748494A535455565758595A636465666768696A737475767778797A82838485868788898A92939495969798999AA2A3A4A5A6A7A8A9AAB2B3B4B5B6B7B8B9BAC2C3C4C5C6C7C8C9CAD2D3D4D5D6D7D8D9DAE2E3E4E5E6E7E8E9EAF2F3F4F5F6F7F8F9FAFFDA000C03010002110311003F00F7FA28A2800A28A2803FFD9'
            )
            image_path.write_bytes(fallback_image_bytes)
            self.logger.info("Created fallback test image successfully")
            return image_path

        except Exception as e:
            self.logger.error(f"Failed to create fallback image: {str(e)}")
            raise

    def simulate_user(self, user_id: int) -> bool:
        try:
            # Add delay between users to prevent rate limiting
            time.sleep(random.uniform(1, 2))

            # Register new account
            username, password = self.test_init.register_new_account()
            if not username or not password:
                self.logger.error(f"User #{user_id} - Registration failed")
                return False

            self.logger.info(f"User #{user_id} - Successfully registered username: {username}")

            # Login and get token
            token = self.test_init.login(username, password)
            if not token:
                self.logger.error(f"User #{user_id} - Login failed")
                return False

            self.logger.info(f"User #{user_id} - Successfully logged in")

            # Make deposit
            headers = {
                "Authorization": f"Bearer {token}"
            }

            with open(self.image_path, "rb") as image_file:
                deposit_data = {
                    "paytype": "bank",
                    "transferType": "2",
                    "amount": random.randint(30, 2000),
                    "bankId": 9,
                    "optionCode": "10DSRB",
                }
                files = {
                    "attachment": (CREDENTIALS["image_path"], image_file, "image/jpeg")
                }

                try:
                    response = http.post(
                        f"{CREDENTIALS['BO_base_url']}/api/recharge", headers=headers, data=deposit_data, files=files,
                        timeout=60
                    )
                    response.raise_for_status()
                    result = response.json()

                    if result.get("code") == 200:
                        self.logger.info(f"User #{user_id} - Deposit successful")
                        return True
                    else:
                        self.logger.error(f"User #{user_id} - Deposit failed: {result.get('message')}")
                        return False

                except Exception as e:
                    self.logger.error(f"User #{user_id} - Deposit failed: {str(e)}")
                    return False

        except Exception as e:
            self.logger.error(f"User #{user_id} - Operation failed: {str(e)}")
            return False

    def test_spam_deposit(self):
        self.logger.info(f"Starting spam deposit test with {self.USER_COUNT} users")
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.MAX_WORKERS) as executor:
                futures = []
                for user_id in range(1, self.USER_COUNT + 1):
                    futures.append(executor.submit(self.simulate_user, user_id))

                results = [future.result() for future in concurrent.futures.as_completed(futures)]
                success_count = sum(1 for result in results if result)

                self.logger.info(f"Test completed. Successful operations: {success_count}/{self.USER_COUNT}")
                self.assertTrue(success_count > 0, "No user operations were successful")

        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            raise


if __name__ == "__main__":
    unittest.main()
