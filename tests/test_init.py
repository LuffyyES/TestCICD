import unittest
import random
import string
import requests
import logging
import os
import time
import pandas as pd
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from config.constant import LANGUAGE_SETTINGS, CREDENTIALS
from tests.authentication_test.base_test import BaseTest
from decimal import Decimal, ROUND_HALF_UP


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
                self.fail("Approve withdraw failed")

    def make_transfer(self, headers, source_id, target_id, amount):
        self.logger.info(f"Making transfer from {source_id} to {target_id} with amount {amount}")
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

    def transfer_to_random_game(self, amount=None, username=None, password=None, provider_id=None):
        token = self.login(username, password)
        self.logger.info(f"Token: {token}")
        if not token:
            self.logger.error("Failed to get authentication token")
            raise Exception("Authentication failed")

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "language": self.language
        }

        all_games = sorted(self.get_game_ids(headers), key=lambda x: x["id"])
        valid_providers = [game for game in all_games if game.get("id", 0) > 0]
        if not valid_providers:
            self.logger.error("No valid game providers found")
            raise Exception("No valid game providers found")

        if provider_id:
            valid_providers = [game for game in all_games if game.get("id") == provider_id and game.get("id", 0) > 0]
            self.logger.info(f"Found provider with ID {provider_id}")
            self.logger.info(f"Valid providers: {valid_providers}")

        while valid_providers:
            selected_game = random.choice(valid_providers)
            game_id = selected_game.get("id")
            game_name = selected_game.get("name")
            self.logger.info(f"Attempting transfer to game provider: {game_name} (ID: {game_id})")

            response = self.make_transfer(headers, source_id=0, target_id=game_id, amount=amount)
            current_time = datetime.now().strftime("%d/%m/%Y %I:%M %p")

            if response.status_code == 200:
                self.logger.info(f"Transfer successful to game provider: {game_name}")
                transfer_details = {
                    "source_id": 0,
                    "source_name": "Main Wallet",
                    "target_id": game_id,
                    "target_name": game_name,
                    "amount": amount,
                    "timestamp": current_time
                }
                return transfer_details, True
            else:
                if provider_id:
                    return None, False
                self.logger.warning(f"Transfer failed to game provider: {game_name}. Error: {response.text}")
                valid_providers = [p for p in valid_providers if p.get("id") != game_id]
                self.logger.info(
                    f"Removed {game_name} from valid providers. {len(valid_providers)} providers remaining."
                )

    def create_downline_rebate(
        self, tier_1_userID=None, username=None, password=None, check_filter_month=False, valid_downline=False,
        valid_turnover=False, create_one_for_each_tier=False
    ):
        try:
            self.logger.info("Starting test_rebate_turnover_calculation")

            rebate_info_list = []
            downline_structure = {
                'valid_downline': {
                    't2': 5,
                    't3': 1
                },
                'create_one_for_each_tier': {
                    't2': 1,
                    't3': 1
                },
                'default': {
                    't2': 2,
                    't3': 2
                }
            }

            match (valid_downline, create_one_for_each_tier):
                case (True, _):
                    structure = downline_structure['valid_downline']
                case (_, True):
                    self.logger.info("Creating one for each tier")
                    structure = downline_structure['create_one_for_each_tier']
                case _:
                    structure = downline_structure['default']

            create_downline_api = CREDENTIALS['CreateDownline'].format(
                userID=tier_1_userID, number_of_t2=structure['t2'], number_of_t3=structure['t3']
            )
            max_retries = 3
            retry_count = 0
            response = None

            while retry_count < max_retries:
                try:
                    response = requests.get(create_downline_api)
                    if response.status_code == 200:
                        self.logger.info("Downline created successfully")
                        break
                    else:
                        self.logger.warning(f"Attempt {retry_count + 1} failed. Status code: {response.status_code}")
                except Exception as e:
                    self.logger.warning(f"Attempt {retry_count + 1} failed with error: {str(e)}")

                retry_count += 1
                time.sleep(1)

            if response is None or response.status_code != 200:
                self.fail(f"Failed to create downline: {response.status_code if response else 'No response'}")
            else:
                response_data = response.json()
                downline_users = {
                    "t2_users": response_data.get("data", {}).get("t2_users", []),
                    "t3_users": response_data.get("data", {}).get("t3_users", [])
                }
                self.logger.info(f"Downline Users: {downline_users}")
                downline_users['t1_users'] = [{
                    'id': tier_1_userID,
                    'username': username,
                    'password': password
                }]
                self.logger.info(f"Downline Users: {downline_users}")

                for user_tier in downline_users:
                    for tier_user in downline_users[user_tier]:
                        self.logger.info(f"Processing Tier User: {tier_user['id']}")
                        if valid_turnover:
                            deposit_result = self.submit_deposit_api(
                                username=tier_user['username'], password=tier_user['password'],
                                check_history_amount=True, amount=random.randint(4000, 10000)
                            )
                        else:
                            deposit_result = self.submit_deposit_api(
                                username=tier_user['username'], password=tier_user['password'],
                                check_history_amount=True, amount=random.randint(1000, 2000)
                            )

                        if isinstance(deposit_result, tuple) and len(deposit_result) == 2:
                            _, user_amount = deposit_result
                            self.logger.info(f"Deposit Amount: {user_amount}")
                        else:
                            self.logger.warning(
                                f"submit_deposit_api returned {deposit_result} instead of expected tuple. Using default amount."
                            )
                            user_amount = 4000
                            if deposit_result is False:
                                self.logger.error("Deposit failed, but continuing with default amount")

                        self.logger.info(f"Deposit Amount: {user_amount}")
                        self.handleDeposit(tier_user['id'])
                        rebate_percentage = 0

                        check_rebate_percentage = CREDENTIALS['CheckRebatePercentage']
                        response = requests.get(check_rebate_percentage)
                        if response.status_code != 200:
                            self.fail(f"Failed to check rebate percentage: {response.status_code}")

                        rebate_data = response.json()
                        match user_tier:
                            case "t1_users":
                                tier_level = "1"
                            case "t2_users":
                                tier_level = "2"
                            case "t3_users":
                                tier_level = "3"

                        eligible_providers = []
                        for provider in rebate_data.get("data", []):
                            provider_id = provider.get("provider_id")
                            rebate_percentage = provider.get("rebate_percentage", {}).get(tier_level, 0)
                            if rebate_percentage > 0:
                                eligible_providers.append({
                                    "provider_id": provider_id,
                                    "rebate_percentage": rebate_percentage
                                })

                        if eligible_providers:
                            remaining_providers = eligible_providers.copy()
                            transfer_success = False
                            #red tiger remove
                            remaining_providers = [p for p in remaining_providers if p["provider_id"] != 32]

                            while remaining_providers and not transfer_success:

                                chosen_provider = random.choice(remaining_providers)

                                provider_id = chosen_provider["provider_id"]
                                rebate_percentage = chosen_provider["rebate_percentage"]
                                self.logger.info(f"Chosen Provider: {chosen_provider}")
                                self.logger.info(f"Provider ID: {provider_id}")
                                self.logger.info(f"Rebate Percentage: {rebate_percentage}")

                                transfer_details, proceed = self.transfer_to_random_game(
                                    amount=user_amount, username=tier_user['username'], password=tier_user['password'],
                                    provider_id=provider_id
                                )
                                if proceed:
                                    transfer_success = True
                                    self.logger.info(f"Transfer successful to provider ID {provider_id}")
                                    self.logger.info(f"Transfer Details: {transfer_details}")
                                    self.logger.info(
                                        f"Using provider ID {provider_id} with rebate percentage {rebate_percentage}% for tier {tier_level}"
                                    )
                                else:
                                    remaining_providers = [
                                        p for p in remaining_providers if p["provider_id"] != provider_id
                                    ]
                                    self.logger.warning(
                                        f"Transfer failed for provider ID {provider_id}. Removing from eligible providers."
                                    )
                                    self.logger.info(f"Remaining providers: {len(remaining_providers)}")

                            if not transfer_success:
                                self.logger.warning(
                                    "All eligible providers failed. Trying without specifying a provider."
                                )
                                transfer_details, proceed = self.transfer_to_random_game(
                                    amount=user_amount, username=tier_user['username'], password=tier_user['password']
                                )
                                if not proceed:
                                    self.logger.error(
                                        f"Transfer failed for user {tier_user['username']} even without specifying provider. Skipping this user."
                                    )
                                    continue
                        else:
                            self.logger.warning(
                                f"No providers found with non-zero rebate percentage for tier {tier_level}"
                            )
                            transfer_details, proceed = self.transfer_to_random_game(
                                amount=user_amount, username=tier_user['username'], password=tier_user['password']
                            )

                            if not proceed:
                                self.logger.error(
                                    f"Transfer failed for user {tier_user['username']}. Skipping this user."
                                )
                                continue

                        current_time = datetime.now().strftime("%d/%m/%Y %I:%M %p")
                        current_date = datetime.now().strftime("%Y-%m-%d")
                        current_month = datetime.now().strftime("%Y-%m")

                        user_rebate_info = {
                            "user_id": tier_user['id'],
                            "username": tier_user['username'],
                            "tier_level": tier_level,
                            "rebate_percentage": rebate_percentage,
                            "provider_name": transfer_details["target_name"],
                            "provider_id": transfer_details["target_id"],
                            "bet_amount": user_amount,
                            "timestamp": current_time,
                            "bonus_amount": user_amount
                        }

                        rebate_info_list.append(user_rebate_info)
                        self.logger.info(f"Added rebate info for user {tier_user['username']}: {user_rebate_info}")

                        # Place bet to generate rebate
                        place_bet_url = f"{CREDENTIALS['PlaceBet'].format(userID=tier_user['id'], transfer_amount=user_amount, type=1, game_id=transfer_details['target_id'], game_record_date=current_date)}"
                        response = requests.get(place_bet_url)
                        self.logger.info(f"userid: {tier_user['id']}")
                        self.logger.info(f"Response: {response.status_code}")
                        if response.status_code != 200:
                            self.fail(f"Failed to place bet: {response.status_code}")
                        else:
                            self.logger.info("Bet placed successfully")

            self.logger.info(f"Collected rebate info for {len(rebate_info_list)} users")
            current_month = datetime.now().strftime("%Y-%m")
            self.logger.info(f"Current user: {tier_1_userID}")
            self.logger.info(f"Current month: {current_month}")
            rebate_simulation_url = f"{CREDENTIALS['CreateRebate'].format(userID=tier_1_userID, current_month=current_month)}"
            tier_2_users = [user for user in rebate_info_list if user['tier_level'] == '2']
            tier_3_users = [user for user in rebate_info_list if user['tier_level'] == '3']
            tier_1_users = [user for user in rebate_info_list if user['tier_level'] == '1']
            self.logger.info(f"Tier 2 users: {tier_2_users}")
            self.logger.info(f"Tier 3 users: {tier_3_users}")
            self.logger.info(f"Tier 1 users: {tier_1_users}")
            self.logger.info(f"Downline rebate info: {rebate_info_list}")
            self.logger.info(rebate_info_list[0])
            response = requests.get(rebate_simulation_url)
            if response.status_code != 200:
                self.fail(f"Failed to create rebate: {response.status_code}")
            else:
                self.logger.info("Rebate created successfully")

            total_bet_per_tier = {}
            total_rebate_per_tier = {}

            for user in rebate_info_list:
                tier = user['tier_level']
                self.logger.info(f"Tier: {tier}")
                bet_amount = user['bet_amount']

                self.logger.info(f"Bet Amount: {bet_amount}")
                rebate_amount = Decimal(bet_amount) * (Decimal(user['rebate_percentage']) / Decimal(100))

                rebate_amount = rebate_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

                self.logger.info(f"Rebate Amount: {rebate_amount}")

                if tier not in total_bet_per_tier:
                    total_bet_per_tier[tier] = 0
                total_bet_per_tier[tier] += bet_amount
                self.logger.info(f"Total Bet Amount per Tier: {total_bet_per_tier[tier]}")

                if tier not in total_rebate_per_tier:
                    total_rebate_per_tier[tier] = 0
                total_rebate_per_tier[tier] += rebate_amount
                self.logger.info(f"Total Rebate Amount per Tier: {total_rebate_per_tier[tier]}")

            current_month = datetime.now().strftime("%Y-%m")
            self.logger.info(f"Total Bet Amount per Tier: {total_bet_per_tier}")
            self.logger.info(f"Total Rebate Amount per Tier: {total_rebate_per_tier}")
            self.logger.info(f"Rebate for tier 1: {total_rebate_per_tier['1']}")
            self.logger.info(f"Rebate for tier 2: {total_rebate_per_tier['2']}")
            self.logger.info(f"Rebate for tier 3: {total_rebate_per_tier['3']}")
            total_bet_amount = sum(total_bet_per_tier.values())
            total_rebate_amount = sum(total_rebate_per_tier.values())
            self.logger.info(f"Total Bet Amount: {total_bet_amount}")
            self.logger.info(f"Total Rebate Amount: {total_rebate_amount}")

            if check_filter_month:
                return total_bet_per_tier, total_rebate_per_tier, total_bet_amount, total_rebate_amount, current_month, tier_2_users, tier_3_users
            else:
                return total_bet_per_tier, total_rebate_per_tier, total_bet_amount, total_rebate_amount, tier_2_users, tier_3_users, tier_1_users

        except Exception as e:
            self.logger.error(f"Error in test_rebate_turnover_calculation: {str(e)}")
            self.fail(f"Test failed: {str(e)}")

    def clean_monetary_value(self, value):
        return float(value.replace("MYR ", "").replace(",", ""))


if __name__ == "__main__":
    unittest.main()
