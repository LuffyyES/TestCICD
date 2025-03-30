import unittest
import random
import string
import requests
import logging
import os
import pandas as pd
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from config.constant import LANGUAGE_SETTINGS, CREDENTIALS
from tests.authentication_test.base_test import BaseTest


class TestInit(BaseTest):

    @classmethod
    def setUpClass(cls):
        cls.logger = logging.getLogger(cls.__name__)
        cls.logger.setLevel(logging.DEBUG)

    def __init__(self, methodName="runTest", language=None, browser=None):
        super().__init__(methodName, language, browser)

    def download_image(self):
        try:
            image_url = CREDENTIALS["image_url"]
            image_path = CREDENTIALS["image_path"]

            response = requests.get(image_url, timeout=30)
            if response.status_code == 200:
                with open(image_path, "wb") as f:
                    f.write(response.content)
                self.logger.info(f"Successfully downloaded image to {image_path}")
                return image_path

            self.logger.info("Download failed, creating fallback image")
            with open(image_path, "wb") as f:
                f.write(
                    bytes.fromhex(
                        'FFD8FFE000104A46494600010100000100010000FFDB004300080606070605080707070909080A0C140D0C0B0B0C1912130F141D1A1F1E1D1A1C1C20242E2720222C231C1C2837292C30313434341F27393D38323C2E333432FFDB0043010909090C0B0C180D0D1832211C213232323232323232323232323232323232323232323232323232323232323232323232323232323232323232323232323232FFC00011080001000103012200021101031101FFC4001F0000010501010101010100000000000000000102030405060708090A0BFFC400B51000020102040403040705040400010277000102031104052131061241510761711322328108144291A1B1C109233352F0156272D10A162434E125F11718191A262728292A35363738393A434445464748494A535455565758595A636465666768696A737475767778797A82838485868788898A92939495969798999AA2A3A4A5A6A7A8A9AAB2B3B4B5B6B7B8B9BAC2C3C4C5C6C7C8C9CAD2D3D4D5D6D7D8D9DAE1E2E3E4E5E6E7E8E9EAF1F2F3F4F5F6F7F8F9FAFFC4001F0100030101010101010101010000000000000102030405060708090A0BFFC400B51100020102040403040705040400010277000102031104052131061241510761711322328108144291A1B1C109233352F0156272D10A162434E125F11718191A262728292A35363738393A434445464748494A535455565758595A636465666768696A737475767778797A82838485868788898A92939495969798999AA2A3A4A5A6A7A8A9AAB2B3B4B5B6B7B8B9BAC2C3C4C5C6C7C8C9CAD2D3D4D5D6D7D8D9DAE2E3E4E5E6E7E8E9EAF2F3F4F5F6F7F8F9FAFFDA000C03010002110311003F00F7FA28A2800A28A2803FFD9'
                    )
                )
            return image_path

        except Exception as e:
            self.logger.error(f"Error downloading/creating image: {str(e)}")
            raise

    def submit_deposit_api(
        self, amount=None, paytype="bank", transferType="2", bankId=9, promoCode=None, username=None, password=None,
        check_history_amount=False
    ):
        try:
            token = self.login(username, password)
            if not token:
                self.logger.error("Failed to get token")
                return False

            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json"
            }

            deposit_info_response = requests.get(f"{CREDENTIALS['BO_base_url']}/api/depositInfo", headers=headers)
            if deposit_info_response.status_code != 200:
                self.logger.error(f"Failed to get deposit info: {deposit_info_response.text}")
                return False

            if amount is None:
                amount = random.randint(50, 2000)

            deposit_data = {
                "paytype": paytype,
                "transferType": transferType,
                "amount": amount,
                "bankId": bankId,
                "promoCode": promoCode
            }

            image_path = self.download_image()

            with open(image_path, "rb") as image_file:
                files = {
                    "attachment": (image_path, image_file, "image/jpeg")
                }

                deposit_response = requests.post(
                    f"{CREDENTIALS['BO_base_url']}/api/recharge", headers=headers, data=deposit_data, files=files
                )

            if os.path.exists(image_path):
                os.remove(image_path)

            self.logger.info(f"Deposit response status: {deposit_response.status_code}")

            if deposit_response.status_code == 200:
                result = deposit_response.json()
                if result.get("code") == 200:
                    self.logger.info(f"Deposit successful: {result}")
                    if check_history_amount:
                        return True, amount
                    else:
                        return True
                else:
                    self.logger.error(f"Deposit failed: {result.get('message')}")
                    return False
            else:
                self.logger.error(f"Deposit request failed: {deposit_response.text}")
                return False

        except Exception as e:
            self.logger.error(f"Error submitting deposit: {str(e)}")
            return False

    def register_new_account(self):
        try:
            letters = ''.join(random.choices(string.ascii_letters, k=2))
            numbers = ''.join(random.choices(string.digits, k=2))
            random_string = f"{letters}{numbers}"

            username = f"Test{random_string}"
            password = f"Test{random_string}"
            phone = f"601{random.randint(10000000, 99999999)}"

            self.logger.info(f"Starting registration process for username: {username}")
            self.logger.info(f"Starting registration process for password: {password}")

            register_data = {
                "username": username,
                "realname": username,
                "password": password,
                "password_confirmation": password,
                "phone": phone,
            }

            register_response = requests.post(f"{CREDENTIALS['BO_base_url']}/api/v3/register", json=register_data)
            self.logger.info(f"Register response status: {register_response.status_code}")

            register_response.raise_for_status()
            data = register_response.json()
            if data.get("code") == 200:
                self.logger.info(f"Registration successful for username: {username}")
                self.logger.info(f"Username: {username}, Password: {password}")
                return username, password
            else:
                self.logger.error(f"Registration failed: {data.get('message')}")
                return None, None

        except Exception as e:
            self.logger.error(f"Error in registration: {str(e)}")
            return None, None

    def register_and_deposit_with_promo(self, with_additional_deposit=False):
        try:
            # Register new account
            username, password = self.register_new_account()
            self.logger.info(f"Username: {username}, Password: {password}")

            if username and password:
                # First deposit with promo
                deposit_success = self.submit_deposit_api(promoCode="10DSRB", username=username, password=password)

                if deposit_success and with_additional_deposit:
                    # Additional deposit without promo if requested
                    deposit_success = self.submit_deposit_api(username=username, password=password)

                if deposit_success:
                    self.logger.info("Deposit(s) successful")
                    return username, password
                else:
                    self.logger.error("Deposit failed")
                    return None, None
            else:
                self.logger.error("Registration failed")
                return None, None

        except Exception as e:
            self.logger.error(f"Error in register_and_deposit_with_promo: {str(e)}")
            return None, None

    def withdraw_api(self, amount=None, username=None, password=None):
        try:
            token = self.login(username, password)
            if not token:
                self.logger.error("Failed to get token")
                return False

            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json"
            }

            withdraw_data = {
                "amount": amount,
                "bank": 524,
            }

            withdraw_response = requests.post(
                f"{CREDENTIALS['BO_base_url']}/api/withdraw", headers=headers, json=withdraw_data
            )
            self.logger.info(f"Withdraw response status: {withdraw_response.status_code}")

            if withdraw_response.status_code == 200:
                result = withdraw_response.json()
                if result.get("code") == 200:
                    self.logger.info(f"Withdraw successful: {result}")
                    return True
                else:
                    self.logger.error(f"Withdraw failed: {result.get('message')}")
                    return False
            else:
                self.logger.error(f"Withdraw request failed: {withdraw_response.text}")
                return False

        except Exception as e:
            self.logger.error(f"Error in withdraw_api: {str(e)}")
            return False

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

    def make_transfer(self, headers, source_id, target_id, amount):
        payload = {
            "source_id": source_id,
            "target_id": target_id,
            "amount": amount
        }
        response = requests.post(f"{CREDENTIALS['BO_base_url']}/api/transfers", json=payload, headers=headers)
        return response

    def get_promo_codes(self, username, password):
        token = self.login(username, password)
        if not token:
            self.logger.error("Failed to get token")
            return []

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "language": self.language
        }

        deposit_info_response = requests.get(f"{CREDENTIALS['BO_base_url']}/api/depositInfo", headers=headers)
        if deposit_info_response.status_code != 200:
            self.logger.error(f"Failed to get deposit info: {deposit_info_response.text}")
            return []

        deposit_info = deposit_info_response.json()
        promo_data = deposit_info.get('data', {}).get('popoPromo', [])

        promo_codes = []
        for promo in promo_data:
            promo_codes.append({
                "optionCode": promo.get("optionCode"),
                "optionName": promo.get("optionName"),
                "optionValue": promo.get("optionValue"),
            })

        self.logger.info(f"Found {len(promo_codes)} promo codes: {promo_codes}")
        return promo_codes


if __name__ == "__main__":
    unittest.main()
