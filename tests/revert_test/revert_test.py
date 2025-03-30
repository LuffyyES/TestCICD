import unittest
import time
import requests
import pandas as pd
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from config.constant import LANGUAGE_SETTINGS, CREDENTIALS
from tests.authentication_test.base_test import BaseTest
from tests.test_init import TestInit
from datetime import datetime
from tests.transfer_test.transfer_base import TransferBase
import math


class TestRevert(TransferBase):

    BATCH_SIZE = int(CREDENTIALS['revert_batch_size']['batch_size'])
    _test_methods_generated = False

    def __init__(self, methodName="runTest", language=None, browser=None):
        super().__init__(methodName, language, browser)
        self.TRANSFER_AMOUNT = float(CREDENTIALS['transfer_amount']['amount'])
        self.ignore_providers = ['0']

    def setUp(self):
        super().setUp()
        self.browser_closed = False
        self.current_part = None
        if self._testMethodName.startswith('test_') and '_Part' in self._testMethodName:
            try:
                self.current_part = int(self._testMethodName.split('_Part')[1])
            except (ValueError, IndexError):
                self.logger.warning(f"Could not extract part number from test name: {self._testMethodName}")

        try:
            match self._testMethodName:
                case method_name if method_name.startswith('test_') and '_RevertAll_Part' in method_name:
                    setup_data = self.setup_deposit_transfer(revert_mode=True, part=self.current_part)
                    self.username = setup_data['username']
                    self.password = setup_data['password']
                    self.successful_game_details = setup_data['game_details']
                    self.total_expected_credit = setup_data['total_expected_credit']
                    self.logger.info(f"Set up revert test part {self.current_part}")

                case 'test_02_EmptyWallet':
                    result = self.test_init.register_new_account()
                    if not result or not isinstance(result, tuple) or len(result) != 2:
                        self.logger.error(f"Registration failed. Got result: {result}")
                        raise Exception("Failed to register new account")

                    self.username, self.password = result
                    self.logger.info(f"Successfully registered account: {self.username}")

                case _:
                    self.logger.warning(f"No setup defined for test: {self._testMethodName}")

            if not hasattr(self, 'username') or not hasattr(self, 'password'):
                raise Exception("No credentials available for test")

            self.logger.info(f"Logging in with username: {self.username}")
            self.navigate_to_login_page()
            self.perform_login(self.username, self.password)
            self.navigate_to_transfer()

        except Exception as e:
            self.logger.error(f"Setup failed: {str(e)}")

    def tearDown(self):
        if not self.browser_closed:
            self.cleanup_browser()
        super().tearDown()

    def cleanup_browser(self):
        try:
            if hasattr(self, 'driver') and self.driver and not self.browser_closed:
                self.logger.info("Closing browser...")
                self.driver.quit()
                self.driver = None
                self.browser_closed = True
        except Exception as e:
            self.logger.error(f"Error closing browser: {str(e)}")

    def perform_revert_all(self):
        one_click_revert = WebDriverWait(self.driver,
                                         10).until(EC.element_to_be_clickable((By.ID, "rebate-all-button")))
        self.driver.execute_script("arguments[0].scrollIntoView(true);", one_click_revert)
        time.sleep(2)
        one_click_revert.click()

    def click_revert_button(self):
        try:
            # Wait for page load first
            self.wait_for_page_ready()

            # Wait longer and check if element exists first
            WebDriverWait(self.driver, 20).until(EC.presence_of_element_located((By.ID, "revert-button")))

            revert_button = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.ID, "revert-button")))

            # Scroll into view first
            self.driver.execute_script("arguments[0].scrollIntoView(true);", revert_button)
            time.sleep(2)

            try:
                revert_button.click()
            except:
                self.logger.warning("Normal click failed, trying JavaScript click")
                self.driver.execute_script("arguments[0].click();", revert_button)

            # Wait for click to take effect
            time.sleep(3)
            self.logger.info("Successfully clicked revert button")

        except Exception as e:
            self.logger.error(f"Failed to click revert button: {str(e)}")
            raise  # Re-raise to handle in calling method

    def check_mainwallet_credit(self):
        driver = self.driver
        try:
            main_wallet_credit = 0

            for provider_id in self.ignore_providers:
                try:
                    time.sleep(2)
                    WebDriverWait(driver, 10).until(
                        EC.visibility_of_element_located((By.CSS_SELECTOR, "ul.MuiList-root.MuiList-padding"))
                    )

                    provider_credit_elements = driver.find_elements(By.ID, f"provider-credit-{provider_id}")

                    if not provider_credit_elements:
                        self.logger.warning(f"No provider credit elements found for ID: {provider_id}")
                        continue

                    provider_credit_element = provider_credit_elements[0]

                    driver.execute_script("arguments[0].scrollIntoView(true);", provider_credit_element)
                    provider_credit = provider_credit_element.text.strip()
                    self.logger.info(f"Main wallet credit: {provider_credit}")

                    if provider_credit:
                        try:
                            credit_value = float(provider_credit.replace(',', ''))
                            main_wallet_credit = credit_value
                            self.logger.info(f"Main wallet credit value: {main_wallet_credit}")
                        except ValueError:
                            self.logger.error(f"Main wallet has invalid credit value: {provider_credit}")
                            return None
                except Exception as e:
                    self.logger.error(f"Failed to check main wallet credit: {str(e)}")
                    return None

            return main_wallet_credit

        except Exception as e:
            self.logger.error(f"Failed to get main wallet credit: {str(e)}")
            return None

    def check_credit(self, checkEmpty=False, collect_initial=False, initial_game_list=None):
        driver = self.driver
        ui_credits = {}
        try:
            if not self.wait_for_page_ready():
                self.fail("Page not ready for credit check")

            token = self.login(self.username, self.password)
            if not token:
                return {}

            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "Content-Type": "application/json"
            }

            current_games = self.get_game_ids(headers)
            self.logger.info(f"Got {len(current_games)} games from API")

            failed_transfers = {
                str(game['id']): game.get('has_failed_transfer', False) for game in current_games
            }

            all_credits_valid = True
            non_zero_credits = []

            providers = WebDriverWait(driver, 20).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div[id^='provider-button-']"))
            )
            self.logger.info(f"Found {len(providers)} providers")

            expected_credits = {}
            if not checkEmpty:
                for game in self.successful_game_details:
                    expected_credits[str(game['id'])] = float(game['credit'])
                self.logger.info(f"Expected credits: {expected_credits}")

            for provider in providers[:10]:
                try:
                    provider_id = provider.get_attribute('id').replace('provider-button-', '')
                    provider_name = provider.find_element(By.ID, f"provider-name-{provider_id}").text.strip()

                    if int(provider_id) == -1:
                        provider_credit_element = provider.find_element(By.ID, f"provider-credit-{provider_id}")
                        provider_credit = provider_credit_element.text.strip()

                        if provider_credit:
                            credit_value = float(provider_credit.replace(',', ''))
                            if checkEmpty:
                                if credit_value > 0:
                                    non_zero_credits.append({
                                        'id': provider_id,
                                        'name': provider_name,
                                        'credit': credit_value
                                    })
                                    all_credits_valid = False
                                    if initial_game_list and provider_id in initial_game_list:
                                        self.assertEqual(
                                            credit_value, initial_game_list[provider_id],
                                            f"Game {provider_id} should be empty but has balance: {credit_value}"
                                        )

                                else:
                                    self.logger.info(f"Provider {provider_id} has zero credit: {credit_value}")
                            else:
                                api_credit = next(
                                    (game['credit'] for game in current_games if str(game['id']) == provider_id), 0
                                )
                                if credit_value != float(api_credit):
                                    self.logger.info(
                                        f"Provider {provider_id} credit mismatch. Expected: {api_credit}, Got: {credit_value}"
                                    )
                                    non_zero_credits.append({
                                        'id': provider_id,
                                        'name': provider_name,
                                        'credit': credit_value,
                                        'expected': api_credit
                                    })
                                    all_credits_valid = False
                                else:
                                    self.logger.info(
                                        f"Provider {provider_id} credit matches expected value: {credit_value}"
                                    )

                    expand_icon = provider.find_elements(By.CSS_SELECTOR, "[data-testid='ExpandMoreIcon']")
                    if expand_icon:

                        self.driver.execute_script("arguments[0].scrollIntoView(true);", provider)
                        time.sleep(1)
                        try:
                            provider.click()
                        except:
                            self.driver.execute_script("arguments[0].click();", provider)
                        time.sleep(1)

                        game_credits = driver.find_elements(By.CSS_SELECTOR, f"[id^='game-credit-']")
                        for credit_element in game_credits:
                            try:
                                game_id = credit_element.get_attribute('id').replace('game-credit-', '')
                                credit = credit_element.text.strip()

                                try:
                                    game_text_element = driver.find_element(By.ID, f"game-text-{game_id}")
                                    self.driver.execute_script("arguments[0].scrollIntoView(true);", game_text_element)
                                    game_name = game_text_element.text.strip()
                                except:
                                    game_name = f"Game {game_id}"

                                if credit:
                                    credit_value = float(credit.replace(',', ''))

                                    if collect_initial:
                                        ui_credits[game_id] = credit_value

                                    if checkEmpty:
                                        if credit_value > 0:
                                            if failed_transfers.get(game_id, False):
                                                self.logger.info(f"Game {game_id} has non-zero credit: {credit_value} ")
                                                self.logger.info(f"Game {game_id} has failed transfer, checking tag...")
                                                try:
                                                    failed_tag = driver.find_element(
                                                        By.ID, f"game-tag-{game_id}_failed"
                                                    )
                                                    if credit_value > 0 or not failed_tag.is_displayed():
                                                        non_zero_credits.append({
                                                            'id': game_id,
                                                            'name': game_name,
                                                            'credit': credit_value,
                                                            'failed': "No failed tag displayed"
                                                        })

                                                    all_credits_valid = False

                                                except:
                                                    self.logger.info(f"Failed tag not found for game {game_id}")
                                        else:
                                            self.logger.info(f"Game {game_id} has zero credit: {credit_value}")
                                    else:
                                        api_credit = next(
                                            (game['credit'] for game in current_games if str(game['id']) == game_id), 0
                                        )
                                        if credit_value != float(api_credit):
                                            self.logger.info(
                                                f"Game {game_id} credit mismatch. Expected: {api_credit}, Got: {credit_value}"
                                            )
                                            all_credits_valid = False
                                        else:
                                            self.logger.info(
                                                f"Game {game_id} credit matches expected value: {credit_value}"
                                            )

                                if failed_transfers.get(game_id, False):
                                    self.logger.info(f"Game {game_id} has failed transfer, checking tag...")
                                    try:
                                        failed_tag = driver.find_element(By.ID, f"game-tag-{game_id}_failed")
                                        if not failed_tag.is_displayed():
                                            self.logger.info(
                                                f"Game {game_id} has failed transfer but tag is not displayed"
                                            )
                                            all_credits_valid = False
                                        else:
                                            self.logger.info(f"Found failed tag displayed for game {game_id}")
                                    except:
                                        self.logger.info(
                                            f"Failed tag not found for game {game_id} with failed transfer"
                                        )
                                        all_credits_valid = False
                            except Exception as e:
                                self.logger.error(f"Error checking provider {provider_id}: {str(e)}")
                                continue
                        provider.click()
                        time.sleep(1)

                except Exception as e:
                    self.logger.warning(f"Error checking provider {provider_id}: {str(e)}")
                    continue

            if non_zero_credits:
                non_zero_credits.sort(key=lambda x: int(x['id']))

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"Failed_Revert_Part{self.current_part}_{timestamp}.xlsx"
                df = pd.DataFrame(non_zero_credits)
                df.to_excel(filename, index=False)
                self.logger.error(f"Found {len(non_zero_credits)} non-zero credits. Details exported to {filename}")

            if checkEmpty:
                if not all_credits_valid:
                    self.fail("Not all credits are empty (except main wallet)")
            else:
                self.assertTrue(all_credits_valid, "Credits don't match expected values from API")

            if collect_initial:
                return ui_credits

        except Exception as e:
            self.logger.error(f"Failed to check credits: {str(e)}")
            self.fail(f"Failed to check credits: {str(e)}")
            return {}

    def wait_for_process_complete(self, initial_credit):
        try:
            WebDriverWait(self.driver, 30).until(
                lambda driver:
                (self.check_mainwallet_credit() is not None and self.check_mainwallet_credit() != initial_credit)
            )
            self.logger.info("Credit change detected - process completed")
            time.sleep(2)
        except Exception as e:
            self.logger.error(f"Timeout waiting for process to complete: {str(e)}")

    def check_specific_games(self, game_list):
        try:
            token = self.login(self.username, self.password)
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "Content-Type": "application/json"
            }

            current_games = self.get_game_ids(headers)
            self.logger.info(f"Got {len(current_games)} games from API")

            self.logger.info("=== All Game Credits from API ===")
            for game in current_games:
                try:
                    game_id = str(game['id'])
                    credit_str = str(game.get('credit', '0'))
                    credit_value = float(credit_str.replace(',', ''))
                    self.logger.info(f"Game {game_id}: {credit_value}")
                except (ValueError, TypeError) as e:
                    self.logger.warning(f"Could not convert credit for game {game['id']}: {str(e)}")

            current_credits = {}
            for game in current_games:
                try:
                    credit_str = str(game.get('credit', '0'))
                    credit_value = float(credit_str.replace(',', ''))
                    current_credits[str(game['id'])] = credit_value
                except (ValueError, TypeError) as e:
                    self.logger.warning(f"Could not convert credit for game {game['id']}: {str(e)}")
                    current_credits[str(game['id'])] = 0

            games_with_credits = []
            for game in game_list:
                game_id = str(game['id'])
                if current_credits.get(game_id, 0) > 0:
                    games_with_credits.append({
                        'id': game_id,
                        'credit': current_credits[game_id]
                    })

            if games_with_credits:
                self.logger.info(f"Found {len(games_with_credits)} games with remaining credits")
                for game in games_with_credits:
                    self.logger.info(f"Game ID: {game['id']} has non-zero credit: {game['credit']}")
                return games_with_credits

            else:
                self.logger.info("No games with remaining credits")
                return []

        except Exception as e:
            self.logger.error(f"Failed to check specific games: {str(e)}")
            return []

    def wait_for_page_ready(self, timeout=30):
        try:
            start_time = time.time()

            loading_wait = WebDriverWait(self.driver, timeout)
            try:
                loading_wait.until(
                    lambda d: not d.find_elements(By.CLASS_NAME, "MuiCircularProgress-root") and not d.
                    find_elements(By.XPATH, "//*[@role='progressbar']") and not d.find_elements(By.ID, "nprogress")
                )
                self.logger.info("All loading indicators disappeared")
            except Exception as e:
                self.logger.warning(f"Some loading indicators might still be present: {str(e)}")

            ready_wait = WebDriverWait(self.driver, timeout)
            ready_wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
            self.logger.info("Document ready state is complete")

            ajax_complete = self.driver.execute_script(
                "return (typeof jQuery === 'undefined') || (jQuery.active === 0);"
            )
            if not ajax_complete:
                self.logger.warning("AJAX requests might still be ongoing")

            time.sleep(3)

            elapsed = time.time() - start_time
            self.logger.info(f"Page ready check completed in {elapsed:.2f} seconds")
            return True

        except Exception as e:
            self.logger.error(f"Page not ready after {timeout} seconds: {str(e)}")
            return False

    def check_wallet_credits(self, initial_credit, max_retries=3):
        for attempt in range(max_retries):
            try:
                final_credit = self.check_mainwallet_credit()
                self.logger.info(f"Final main wallet credit: {final_credit}")
                self.logger.info(f"Total expected credit: {self.total_expected_credit}")
                self.logger.info(f"Initial main wallet credit: {initial_credit}")

                if initial_credit and final_credit:
                    expected_final = initial_credit + float(self.total_expected_credit)
                    self.logger.info(f"Checking main wallet credit - Expected: {expected_final}, Got: {final_credit}")

                    if expected_final == final_credit:
                        self.logger.info("Main wallet credit matches expected value")
                        return final_credit
                    else:
                        if attempt < max_retries - 1:
                            self.logger.warning(
                                f"Credit mismatch on attempt {attempt + 1}. "
                                f"Expected: {expected_final}, Got: {final_credit}. Retrying..."
                            )
                            self.driver.refresh()
                            time.sleep(6)
                            self.click_revert_button()
                            time.sleep(2)
                            continue
                        else:
                            self.logger.warning(
                                f"Main wallet credit mismatch after {max_retries} attempts. "
                                f"Expected: {expected_final}, Got: {final_credit}"
                            )

                if attempt < max_retries - 1:
                    self.logger.warning(f"Invalid credits on attempt {attempt + 1}, retrying...")
                    self.driver.refresh()
                    time.sleep(3)
                    self.click_revert_button()
                    time.sleep(2)
                else:
                    self.fail("Could not get valid credit values after all attempts")

            except Exception as e:
                if attempt < max_retries - 1:
                    self.logger.warning(f"Error on attempt {attempt + 1}: {str(e)}. Retrying...")
                    self.driver.refresh()
                    time.sleep(3)
                    self.click_revert_button()
                    time.sleep(2)
                else:
                    self.logger.error(f"Failed to check wallet credits after {max_retries} attempts: {str(e)}")

        return None

    def check_error_popup(self):
        try:
            error_icon = WebDriverWait(self.driver, 5).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "div.swal2-icon.swal2-error.swal2-icon-show"))
            )

            if error_icon.is_displayed():
                self.confirm_button()
                return True

            return False

        except Exception as e:
            self.logger.info("No error popup found")
            return False

    def revert_all(self):
        try:
            self.driver.refresh()
            time.sleep(2)
            self.click_revert_button()
            time.sleep(2)

            initial_main_wallet_credit = self.check_mainwallet_credit()
            self.logger.info(f"Initial main wallet credit: {initial_main_wallet_credit}")
            initial_credits = self.check_credit(collect_initial=True)

            max_retries = 3
            for attempt in range(max_retries):
                try:
                    self.perform_revert_all()
                    self.logger.info(f"Revert all attempt {attempt + 1} completed")
                    break
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    self.logger.warning(f"Revert attempt {attempt + 1} failed, retrying: {str(e)}")
                    time.sleep(2)

            if self.check_error_popup():
                self.logger.info("Error popup found and handled")
                if not self.wait_for_page_ready():
                    self.logger.warning("Page not ready after error popup, refreshing...")
                    self.driver.refresh()
                    time.sleep(3)

                self.logger.info("Checking credits after error popup...")
                self.click_revert_button()
                time.sleep(2)
                self.check_wallet_credits(initial_main_wallet_credit)
                self.check_credit(checkEmpty=True, initial_game_list=initial_credits)
            else:
                self.logger.info("No error popup found, proceeding with checks")
                retry_count = 0
                max_retries = 3

                while retry_count < max_retries:
                    if self.wait_for_page_ready():
                        break
                    self.logger.warning(f"Page not ready, attempt {retry_count + 1} of {max_retries}")
                    self.driver.refresh()
                    time.sleep(3)
                    retry_count += 1

                if retry_count == max_retries:
                    raise Exception("Page failed to become ready after multiple attempts")

                self.logger.info("Performing final checks...")
                self.driver.refresh()
                time.sleep(6)
                self.click_revert_button()
                time.sleep(4)

                max_check_retries = 2
                for check_attempt in range(max_check_retries):
                    try:
                        self.check_wallet_credits(initial_main_wallet_credit)
                        self.check_credit(checkEmpty=True, initial_game_list=initial_credits)
                        break
                    except Exception as e:
                        self.logger.warning(f"Check attempt {check_attempt + 1} failed, retrying: {str(e)}")
                        time.sleep(2)

        except Exception as e:
            self.logger.error(f"Revert all failed: {str(e)}")

    @classmethod
    def get_total_providers(cls, browser, language):
        temp_instance = cls(methodName="runTest", browser=browser, language=language)
        token = temp_instance.login(
            CREDENTIALS['duplicated_user']['username'], CREDENTIALS['duplicated_user']['password']
        )
        if not token:
            return 3

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        all_games = temp_instance.get_game_ids(headers)
        providers = [game for game in all_games if game["id"] > 0]
        total_providers = len(providers)
        #print(f"Total providers found: {total_providers}")
        return total_providers

    @classmethod
    def generate_test_methods(cls, browser, language):
        if cls._test_methods_generated:
            return

        total_providers = cls.get_total_providers(browser, language)
        num_parts = math.ceil(total_providers / cls.BATCH_SIZE)

        #print(f"Generating {num_parts} test parts with batch size {cls.BATCH_SIZE}")

        def create_test_method(part_num):

            def test_method(self):
                self._run_revert_for_part(part_num)

            test_method.__doc__ = f"Test revert for part {part_num}"
            return test_method

        for i in range(1, num_parts + 1):
            test_name = f'test_{i:02d}_RevertAll_Part{i}'
            setattr(cls, test_name, create_test_method(i))
            #print(f"Created test method: {test_name}")

        cls._test_methods_generated = True

    @classmethod
    def get_test_methods(cls, browser, language):
        cls.generate_test_methods(browser, language)

        return [name for name in dir(cls) if name.startswith('test_')]

    def _run_revert_for_part(self, part_num):
        self.logger.info(f"Running revert test for part {part_num}")
        try:
            self.revert_all()
        except Exception as e:
            self.logger.error(f"Test for part {part_num} failed: {str(e)}")
            self.fail(f"Test for part {part_num} failed: {str(e)}")

    def test_02_EmptyWallet(self):
        try:
            self.userID = self.get_id_number()
            self.test_init.submit_deposit_api(username=self.username, password=self.password)
            self.handleDeposit(self.userID)
            self.driver.refresh()
            self.click_revert_button()
            self.logger.info("Successfully clicked revert button")
            time.sleep(2)
            self.check_credit(checkEmpty=True)
            time.sleep(2)

            self.perform_revert_all()
            time.sleep(5)
            self.click_revert_button()
            time.sleep(5)
            self.check_credit(checkEmpty=True)

        except Exception as e:
            self.logger.error(f"Test failed: {str(e)}")
            self.fail(f"Test failed: {str(e)}")


if __name__ == "__main__":
    unittest.main()
