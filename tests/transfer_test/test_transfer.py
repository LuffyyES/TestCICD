import unittest
import time
import random
import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from config.constant import LANGUAGE_SETTINGS, CREDENTIALS
from tests.authentication_test.base_test import BaseTest
from tests.test_init import TestInit
from datetime import datetime


class TestTransfer(BaseTest):

    def __init__(self, methodName="runTest", language=None, browser=None):
        super().__init__(methodName, language, browser)
        self.test_init = TestInit(methodName="runTest", language=language, browser=browser)

    def setUp(self):
        super().setUp()
        self.navigate_to_login_page()
        self.perform_login(CREDENTIALS["duplicated_user"]["username"], CREDENTIALS["duplicated_user"]["password"])
        self.username = CREDENTIALS["duplicated_user"]["username"]
        self.password = CREDENTIALS["duplicated_user"]["password"]
        self.navigate_to_transfer()

    def tearDown(self):
        if hasattr(self, "driver"):
            self.driver.quit()

    def switchToCompleteTurnoverAcc(self):
        self.logout()
        self.perform_login(CREDENTIALS["complete_turnover"]["username"], CREDENTIALS["complete_turnover"]["password"])
        self.navigate_to_transfer()

    def switchToIncompleteTurnoverAcc(self):
        self.logout()
        self.perform_login(
            CREDENTIALS["incomplete_turnover"]["username"], CREDENTIALS["incomplete_turnover"]["password"]
        )
        self.navigate_to_transfer()

    def enter_amount(self, amount):
        amount_field = WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located((By.ID, "amount-input")))
        amount_field.clear()
        amount_field.send_keys(amount)

    def parse_provider_ids(self, providers_list):
        try:
            provider_ids = set()
            for pid in providers_list:
                if pid is None:
                    continue
                if isinstance(pid, str) and pid.startswith('['):
                    try:
                        ids = eval(pid)
                        if isinstance(ids, list):
                            provider_ids.update(str(id) for id in ids)
                    except:
                        self.logger.warning(f"Could not parse provider_ids: {pid}")
                else:
                    provider_ids.add(str(pid))

            self.logger.info(f"Parsed provider IDs: {provider_ids}")
            return provider_ids

        except Exception as e:
            self.logger.error(f"Error parsing provider IDs: {str(e)}")
            return set()

    def selectWalletByAmount(
        self, index, mode=None, gameID=None, username=None, password=None, target_gameID=None, nomain=False,
        provider_ids=None
    ):
        driver = self.driver
        try:
            if gameID is not None:
                self.logger.info(f"Entering gameID verification mode with gameID: {gameID}")
                time.sleep(6)
                self.open_dropdown(index)
                time.sleep(3)

                if str(gameID) in ['0', '-1']:
                    self.logger.info("Verification: Found main wallet or bobolive")
                    time.sleep(2)
                    credit_element = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.ID, f"provider-credit-{gameID}"))
                    )
                    credit = credit_element.text
                    self.logger.info(f"Extracted credit for main wallet {gameID}: {credit}")
                    return credit

                self.logger.info("Verification: Found game")
                providers = WebDriverWait(driver, 20).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div[id^='provider-button-']"))
                )

                for provider in providers:
                    try:
                        expand_icon = provider.find_elements(By.CSS_SELECTOR, "[id^='expand-icon-']")
                        if expand_icon:
                            provider.click()
                            time.sleep(3)
                            try:
                                time.sleep(2)
                                credit_element = WebDriverWait(self.driver, 10).until(
                                    EC.presence_of_element_located((By.ID, f"game-credit-{gameID}"))
                                )
                                self.driver.execute_script("arguments[0].scrollIntoView(true);", credit_element)
                                credit = credit_element.text
                                self.logger.info(f"Found and extracted credit for game {gameID}: {credit}")
                                return credit
                            except Exception as e:
                                self.logger.warning(f"Credit element not found: {str(e)}")
                                self.driver.execute_script("arguments[0].click();", provider)
                                time.sleep(1)
                                continue
                    except Exception as e:
                        self.logger.warning(f"Error with provider: {str(e)}")
                        continue

                raise Exception(f"Could not find credit for game ID {gameID}")

            else:
                self.logger.info("Verification: go into else")
                token = self.login(username, password)
                if not token:
                    return
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                }
                game_data = self.get_game_ids(headers)
                self.logger.info(f"Game data: {game_data}")
                userID = self.get_id_number()

                has_providers, providers_list = self.checkProviders(userID, self.language)
                if has_providers:
                    provider_ids = self.parse_provider_ids(providers_list)

                    included_provider_data = []
                    excluded_provider_data = []

                    for game in game_data:
                        game_id = str(game['id'])
                        self.logger.info(f"Checking game ID: {game_id}")

                        if game_id == '0':
                            self.logger.info(f"Found main wallet: {game}")
                            included_provider_data.append(game)
                            excluded_provider_data.append(game)
                        elif game_id in provider_ids:
                            self.logger.info(f"Found included game: {game}")
                            included_provider_data.append(game)
                            provider_ids.remove(game_id)
                        else:
                            self.logger.info(f"Found excluded game: {game}")
                            excluded_provider_data.append(game)

                    if provider_ids:
                        self.logger.warning(f"Provider IDs with no matching games: {provider_ids}")

                    self.logger.info(f"Included provider data: {included_provider_data}")
                    self.logger.info(f"Excluded provider data: {excluded_provider_data}")

                    filtered_game_data = included_provider_data

                else:
                    self.logger.info("No providers found, using all available games")
                    if provider_ids:
                        excluded_provider_data = [game for game in game_data if str(game['id']) not in provider_ids]
                        self.logger.info(f"Excluded provider data: {excluded_provider_data}")
                        included_provider_data = [game for game in game_data if str(game['id']) in provider_ids]
                        filtered_game_data = included_provider_data
                        self.logger.info(f"Included provider data: {included_provider_data}")
                    else:
                        included_provider_data = game_data
                        excluded_provider_data = game_data
                        filtered_game_data = game_data
                if not filtered_game_data or not included_provider_data or not excluded_provider_data:
                    self.logger.error("No games found")
                    self.logger.error(f"Game IDs available: {[str(g['id']) for g in game_data]}")
                    if has_providers:
                        self.logger.error(f"Provider IDs: {providers_list}")
                    raise Exception("No games found")

                self.logger.info(f"Filtered game data: {filtered_game_data}")

                valid_games = [
                    game for game in filtered_game_data if float(game.get('credit', '0').replace(',', '')) > 0
                ]
                zero_credit_games = [
                    game for game in filtered_game_data if float(game.get('credit', '0').replace(',', '')) == 0
                ]

                valid_excluded_games = [
                    game for game in excluded_provider_data if float(game.get('credit', '0').replace(',', '')) > 0
                ]
                self.logger.info(f"Valid excluded games: {valid_excluded_games}")
                zero_excluded_games = [
                    game for game in excluded_provider_data if float(game.get('credit', '0').replace(',', '')) == 0
                ]
                self.logger.info(f"Zero excluded games: {zero_excluded_games}")

                if not valid_games and mode != 'excluded_lowest':
                    selected_game = random.choice(filtered_game_data)
                else:
                    if mode == 'included_highest':
                        if nomain:
                            # Filter out game ID 0 from valid games
                            valid_games_no_main = [game for game in valid_games if str(game['id']) != '0']
                            if valid_games_no_main:
                                selected_game = max(
                                    valid_games_no_main, key=lambda x: float(x.get('credit', '0').replace(',', ''))
                                )
                                self.logger.info(
                                    f"Selected highest credit game (excluding main wallet): {selected_game}"
                                )
                            else:
                                raise Exception("No valid games with balance found excluding main wallet")
                        else:
                            selected_game = max(valid_games, key=lambda x: float(x.get('credit', '0').replace(',', '')))
                            self.logger.info(f"Selected highest credit game: {selected_game}")
                    elif mode == 'included_lowest':
                        if zero_credit_games:
                            selected_game = random.choice(zero_credit_games)
                            self.logger.info(f"Selected random zero credit game: {selected_game}")
                        else:
                            selected_game = min(valid_games, key=lambda x: float(x.get('credit', '0').replace(',', '')))
                            self.logger.info(f"Selected lowest non-zero credit game: {selected_game}")
                    elif mode == 'excluded_lowest':
                        if zero_excluded_games:
                            selected_game = random.choice(zero_excluded_games)
                            self.logger.info(f"Selected random zero credit excluded game: {selected_game}")
                        else:
                            if valid_excluded_games:
                                selected_game = min(
                                    valid_excluded_games, key=lambda x: float(x.get('credit', '0').replace(',', ''))
                                )
                                self.logger.info(f"Selected lowest non-zero credit excluded game: {selected_game}")
                            else:
                                raise Exception("No valid excluded games found")
                    elif mode == 'random':
                        selected_game = random.choice(valid_games)
                        self.logger.info(f"Selected random credit game: {selected_game}")
                    elif mode == 'specificID':
                        target_game = next((game for game in game_data if game['id'] == target_gameID), None)
                        if target_game:
                            selected_game = target_game
                            self.logger.info(f"Selected specific game with target ID: {selected_game}")
                        else:
                            raise Exception("Could not find game with ID target 16")
                    else:
                        selected_game = random.choice(valid_games)
                        self.logger.info(f"Selected random credit game: {selected_game}")

                self.open_dropdown(index)
                time.sleep(3)

                self.logger.info(f"Selected game: {selected_game}")

                if selected_game['id'] in [0, -1]:
                    wallet_selector = f"provider-button-{selected_game['id']}"
                    self.logger.info(f"Wallet selector: {wallet_selector}")

                    wallet_elements = driver.find_elements(By.ID, wallet_selector)
                    self.logger.info(f"Number of elements with ID '{wallet_selector}': {len(wallet_elements)}")

                    if len(wallet_elements) == 1:
                        wallet = wallet_elements[0]
                        self.logger.info("Only one wallet element found, selecting it.")
                    elif index == 1 and len(wallet_elements) > 1:
                        wallet = wallet_elements[1]
                        self.logger.info("Selecting the second wallet element.")
                    else:
                        wallet = wallet_elements[0]

                    try:
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", wallet)
                        time.sleep(3)

                        #credit_element = WebDriverWait(self.driver, 10).until(
                        #    EC.presence_of_element_located((By.ID, f"provider-credit-{selected_game['id']}"))
                        #)
                        #credit = credit_element.text
                        credit = selected_game['credit']
                        self.logger.info(f" API credit: {credit}")

                        WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable(wallet))
                        self.driver.execute_script("arguments[0].click();", wallet)
                        self.logger.info(f"Successfully clicked wallet using JavaScript")

                    except Exception as e:
                        self.logger.info(f"Failed to click wallet: {str(e)}")

                    time.sleep(2)
                else:
                    providers = WebDriverWait(driver, 20).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div[id^='provider-button-']"))
                    )

                    wallet = None
                    for provider in providers:
                        try:
                            expand_icon = provider.find_elements(By.CSS_SELECTOR, "[id^='expand-icon-']")
                            if expand_icon:
                                provider.click()
                                time.sleep(1)

                                try:
                                    game_selector = f"li[id='game-item-{selected_game['id']}']"
                                    self.logger.info(f"Looking for elements matching selector: {game_selector}")
                                    wallet_elements = driver.find_elements(By.CSS_SELECTOR, game_selector)

                                    if len(wallet_elements) == 1:
                                        wallet = wallet_elements[0]
                                        self.logger.info("Only one wallet element found, selecting it.")
                                    elif index == 1 and len(wallet_elements) > 1:
                                        wallet = wallet_elements[1]
                                        self.logger.info("Selecting the second wallet element.")
                                    else:
                                        wallet = wallet_elements[0]
                                    self.driver.execute_script("arguments[0].scrollIntoView(true);", wallet)
                                    time.sleep(3)
                                    #credit_element = WebDriverWait(self.driver, 3).until(
                                    #    EC.presence_of_element_located((By.ID, f"game-credit-{selected_game['id']}"))
                                    #)
                                    #credit = credit_element.text
                                    credit = selected_game['credit']
                                    self.logger.info(f"API credit: {credit}")

                                    WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable(wallet))
                                    wallet.click()
                                    self.logger.info(f"Successfully clicked wallet element")

                                    break
                                except Exception as e:
                                    self.logger.warning(f"Error clicking game item: {str(e)}")
                                    provider.click()
                                    time.sleep(5)
                                    continue

                        except Exception as e:
                            self.logger.warning(f"Error checking provider: {str(e)}")
                            continue

                    if not wallet:
                        raise Exception(f"Could not find game with ID {selected_game['id']}")

                return selected_game['id'], credit

        except Exception as e:
            self.logger.error(f"Failed to select wallet by amount: {str(e)}")
            self.fail(f"Failed to select wallet by amount: {str(e)}")

    def checkProviders(self, userID, language):

        turnoverAPI = CREDENTIALS["CheckTurnover"].format(BO_base_url = CREDENTIALS["BO_base_url"], ID=userID, language=language)
        providerslist = set()
        response = requests.get(turnoverAPI)
        if response.status_code == 200:
            self.logger.info(f"Turnover API Response: {response.json()}")
            turnoverData = response.json()
            if len(turnoverData) == 0:
                return False, list(providerslist)
            else:
                for provider in turnoverData:
                    if provider['provider_ids'] is not None:
                        if isinstance(provider['provider_ids'], str):
                            try:
                                ids = eval(provider['provider_ids'])
                                if isinstance(ids, list):
                                    providerslist.update(ids)
                            except:
                                self.logger.warning(f"Could not parse provider_ids: {provider['provider_ids']}")
                        elif isinstance(provider['provider_ids'], list):
                            providerslist.update(provider['provider_ids'])
                        else:
                            providerslist.add(provider['provider_ids'])

                self.logger.info(f"Unique provider IDs: {providerslist}")
                return True, list(providerslist) if providerslist else (False, [])
        else:
            self.logger.error(f"Failed to get providers: {response.status_code}")
            return False, list(providerslist)

    def verify_transfer_success(self, FromgameID, TogameID, transferred_amount, credit_from, credit_to):
        try:
            credit_from_after = self.selectWalletByAmount(0, gameID=FromgameID)
            self.logger.info("done checking from wallet credit1")
            self.driver.refresh()
            time.sleep(3)
            credit_to_after = self.selectWalletByAmount(0, gameID=TogameID)
            self.logger.info("done checking to wallet credit2")

            credit_from_before = float(credit_from.replace(',', ''))
            credit_to_before = float(credit_to.replace(',', ''))
            credit_from_after = float(credit_from_after.replace(',', ''))
            credit_to_after = float(credit_to_after.replace(',', ''))

            expected_credit_from_after = round(credit_from_before - transferred_amount, 2)
            actual_credit_from_after = round(credit_from_after, 2)
            self.assertAlmostEqual(
                actual_credit_from_after, expected_credit_from_after, places=2, msg=
                f"Source wallet credit mismatch: expected {expected_credit_from_after}, got {actual_credit_from_after}"
            )

            expected_credit_to_after = round(credit_to_before + transferred_amount, 2)
            actual_credit_to_after = round(credit_to_after, 2)
            self.assertAlmostEqual(
                actual_credit_to_after, expected_credit_to_after, places=2, msg=
                f"Destination wallet credit mismatch: expected {expected_credit_to_after}, got {actual_credit_to_after}"
            )

            self.logger.info("Transfer verification successful.")

        except Exception as e:
            self.logger.error(f"Transfer verification failed: {str(e)}")
            self.fail(f"Transfer verification failed: {str(e)}")

    def verify_transfer_failed(self, from_game_id, to_game_id, credit_from, credit_to, amount=None):
        try:
            credit_from_after = self.selectWalletByAmount(0, gameID=from_game_id)
            self.logger.info("done checking from wallet credit1")
            self.driver.refresh()
            time.sleep(3)
            credit_to_after = self.selectWalletByAmount(0, gameID=to_game_id)
            self.logger.info("done checking to wallet credit2")

            credit_from_before = float(credit_from.replace(',', ''))
            credit_to_before = float(credit_to.replace(',', ''))
            credit_from_after = float(credit_from_after.replace(',', ''))
            credit_to_after = float(credit_to_after.replace(',', ''))

            expected_credit_from_after = credit_from_before
            actual_credit_from_after = credit_from_after
            self.assertAlmostEqual(
                actual_credit_from_after, expected_credit_from_after, places=2, msg=
                f"Source wallet credit mismatch: expected {expected_credit_from_after}, got {actual_credit_from_after}"
            )

            expected_credit_to_after = credit_to_before
            actual_credit_to_after = credit_to_after
            self.assertAlmostEqual(
                actual_credit_to_after, expected_credit_to_after, places=2, msg=
                f"Destination wallet credit mismatch: expected {expected_credit_to_after}, got {actual_credit_to_after}"
            )

            self.logger.info("Transfer verification successful.")

        except Exception as e:
            self.logger.error(f"Transfer failed: {str(e)}")
            self.fail(f"Transfer failed: {str(e)}")

    def search_and_verify_results(self, search_term, expected_valid=True):
        try:
            driver = self.driver
            self.open_dropdown(0)
            time.sleep(2)

            searchField = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".MuiInputBase-inputTypeSearch"))
            )
            self.logger.info("Found search field")
            searchField.clear()
            searchField.send_keys(search_term)
            self.logger.info(f"Searching for: {search_term}")

            time.sleep(2)

            if expected_valid:
                providers = WebDriverWait(driver, 20).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div[id^='provider-button-']"))
                )

                found = False
                for provider in providers:
                    try:
                        expand_icon = provider.find_elements(By.CSS_SELECTOR, "[id^='expand-icon-']")
                        if expand_icon:
                            self.driver.execute_script("arguments[0].scrollIntoView(true);", provider)
                            time.sleep(0.5)
                            provider.click()
                            time.sleep(1)

                            game_names = driver.find_elements(By.CSS_SELECTOR, "div[id^='game-name-']")
                            self.logger.info(f"Found {len(game_names)} games in provider")

                            for game_name in game_names:
                                game_text = game_name.text
                                self.logger.info(f"Checking game: {game_text}")
                                if search_term.lower() in game_text.lower():
                                    self.logger.info(f"Found matching game: {game_text}")
                                    found = True
                                    break

                            if found:
                                break

                            provider.click()
                            time.sleep(0.5)

                    except Exception as e:
                        self.logger.warning(f"Error checking provider: {str(e)}")
                        continue

                try:
                    self.assertTrue(found, f"Game with name containing '{search_term}' not found in search results")
                except Exception as e:
                    self.logger.error(
                        f"Game with name containing '{search_term}' not found in search results: {str(e)}"
                    )
                    self.fail(f"Game with name containing '{search_term}' not found in search results: {str(e)}")

            else:
                try:
                    game_list = WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.ID, "game-list")))
                    game_divs = game_list.find_elements(By.TAG_NAME, "div")
                    self.assertEqual(len(game_divs), 0, "Game list should be empty for invalid search")
                    self.logger.info("No game list found as expected for invalid search")
                except:
                    self.fail("Game list should not be visible for invalid search")

        except Exception as e:
            self.logger.error(f"Test failed: {str(e)}")
            self.fail(f"Test failed: {str(e)}")

    def transfer_and_verify(self, from_game_id, to_game_id, credit_from, credit_to, amount=None):
        try:
            max_amount = float(credit_from.replace(',', ''))
            self.logger.info(f"Max amount: {max_amount}")
            if amount:
                random_amount = amount
            else:
                random_amount = round(random.uniform(1, max_amount), 2)
            self.logger.info(f"Random amount: {random_amount}")

            self.logger.info(f"Transferring amount: {random_amount}")
            self.enter_amount(random_amount)

            self.generic_submit(expected_result="success", submit="submit-transfer-button")
            try:
                self.driver.refresh()
                self.verify_transfer_success(from_game_id, to_game_id, random_amount, credit_from, credit_to)
            except Exception as e:
                self.fail("Transfer with an incorrect amount")
        except Exception as e:
            raise Exception(f"Transfer and verify failed: {str(e)}")

    def check_turnover_and_transfer(
        self, from_game_id, to_game_id, credit_from, credit_to, turnoverList=None, amount=None, out_of_whitelist=False
    ):
        try:
            userID = self.get_id_number()
            turnoverIncomplete, locked_by_list = self.checkIncompleteTurnover(
                userID, checkIncomplete=True, language=self.language, transfer_check=True
            )
            self.logger.info(f"Turnover Incomplete: {turnoverIncomplete}")
            self.logger.info(f"Locked by list: {locked_by_list}")

            max_amount = float(credit_from.replace(',', ''))
            self.logger.info(f"Max amount: {max_amount}")
            if amount:
                random_amount = amount
            else:
                random_amount = round(random.uniform(1, max_amount), 2)
            self.logger.info(f"Random amount: {random_amount}")
            self.enter_amount(random_amount)

            try:
                if turnoverIncomplete or turnoverList:
                    self.logger.info(f"Turnover incomplete: {turnoverList}")
                    self.logger.info(f"Locked by list: {locked_by_list}")
                    self.generic_submit(
                        expected_result="failure", submit="submit-transfer-button", check_general_error=True,
                        expected_error=LANGUAGE_SETTINGS[self.language]["errors"]["bonus_locked"], id="swal2-title",
                        turnoverIncomplete="True", locked_by_list=locked_by_list, transfer_check=True,
                        turnoverList=turnoverList
                    )
                else:
                    if out_of_whitelist:
                        self.logger.info("Out of whitelist")
                        try:
                            submit_button = WebDriverWait(self.driver, 10).until(
                                EC.element_to_be_clickable((By.ID, "submit-transfer-button"))
                            )
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_button)
                            time.sleep(3)
                            submit_button.click()
                            time.sleep(2)

                            error_icon = WebDriverWait(self.driver, 10).until(
                                EC.presence_of_element_located((By.CLASS_NAME, "swal2-icon-error"))
                            )
                            self.assertTrue(error_icon.is_displayed(), "Error icon not displayed")
                            self.logger.info("Error icon is displayed")
                            self.confirm_button()
                        except Exception as e:
                            self.logger.error(f"Transfer failed: {str(e)}")
                            self.fail(f"Transfer failed: {str(e)}")
                            raise
                    else:
                        self.fail("Expected turnover incomplete error was not shown")
                self.verify_transfer_failed(from_game_id, to_game_id, credit_from, credit_to, random_amount)
            except Exception as e:
                # Take screenshot on failure
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshot_name = f"turnover_transfer_fail_{timestamp}.png"
                self.driver.save_screenshot(screenshot_name)
                self.logger.error(f"Screenshot saved as {screenshot_name}")
                raise

        except Exception as e:
            self.logger.error(f"Failed to check turnover and transfer: {str(e)}")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_name = f"general_fail_{timestamp}.png"
            self.driver.save_screenshot(screenshot_name)
            self.logger.error(f"Screenshot saved as {screenshot_name}")
            raise

    def modify_turnover_status(self, userID, turnoverIDs, action_type="unlock", partial=False):

        try:
            turnover_actions = {
                "success": 1,
                "in_progress": 0,
                "unlock": -1
            }

            action = turnover_actions.get(action_type)
            if action is None:
                self.logger.error(f"Invalid action type: {action_type}")
                return False

            if partial and len(turnoverIDs) > 1:
                num_to_complete = random.randint(1, len(turnoverIDs) - 1)
                selected_ids = random.sample(turnoverIDs, num_to_complete)
                self.logger.info(f"Partially completing {num_to_complete} out of {len(turnoverIDs)} turnovers")
            else:
                selected_ids = turnoverIDs

            for turnover_id in selected_ids:
                modify_url = CREDENTIALS["ModifyTurnover"].format(BO_base_url = CREDENTIALS["BO_base_url"], userID=userID, turnover_id=turnover_id, action=action)
                self.logger.info(f"Attempting to {action_type} turnover ID: {turnover_id}")

                response = requests.get(modify_url)
                if response.status_code == 200:
                    self.logger.info(f"Successfully {action_type} turnover ID: {turnover_id}")
                else:
                    self.logger.error(
                        f"Failed to {action_type} turnover ID {turnover_id}. Status code: {response.status_code}"
                    )
                    return False

            return True

        except Exception as e:
            self.logger.error(f"Error modifying turnover: {str(e)}")
            return False

    def get_turnover_ids(self, userID, language=None):
        try:
            turnoverAPI = CREDENTIALS["CheckTurnover"].format(BO_base_url = CREDENTIALS["BO_base_url"], ID=userID, language=language)
            turnover_ids = []

            response = requests.get(turnoverAPI)
            if response.status_code == 200:
                turnoverData = response.json()
                self.logger.info(f"Turnover data: {turnoverData}")

                for item in turnoverData:
                    if 'id' in item:
                        turnover_ids.append(item['id'])

                self.logger.info(f"Found turnover IDs: {turnover_ids}")
                return turnover_ids
            else:
                self.logger.error(f"Failed to get turnover data. Status code: {response.status_code}")
                return []

        except Exception as e:
            self.logger.error(f"Error getting turnover IDs: {str(e)}")
            return []

    def check_and_transfer_to_empty_providers(self, provider_ids):

        try:
            token = self.login(self.username, self.password)
            if not token:
                self.logger.error("Failed to get token")
                return False

            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json"
            }

            game_data = self.get_game_ids(headers)

            all_zero = True
            for game in game_data:
                if str(game['id']) in provider_ids:
                    credit = float(game.get('credit', '0').replace(',', ''))
                    if credit > 0:
                        all_zero = False
                        break

            if all_zero and provider_ids:
                self.logger.info("All providers have zero credit, attempting transfer")
                target_id = random.choice(list(provider_ids))

                transfer_data = {
                    "source_id": 0,
                    "target_id": int(target_id),
                    "amount": "2"
                }

                self.logger.info(f"Attempting API transfer: {transfer_data}")
                headers["Content-Type"] = "application/json"
                response = requests.post(
                    f"{CREDENTIALS['BO_base_url']}/api/transfers", headers=headers, json=transfer_data
                )

                if response.status_code == 200:
                    result = response.json()
                    if result.get("code") == 200:
                        self.logger.info("API transfer successful")
                        return True
                    else:
                        self.logger.error(f"API transfer failed: {result.get('message')}")
                        return False
                else:
                    self.logger.error(f"API transfer request failed: {response.text}")
                    return False
            else:
                self.logger.info("Not all providers have zero credit or no providers found")
                return False

        except Exception as e:
            self.logger.error(f"Error in check_and_transfer_to_empty_providers: {str(e)}")
            return False

    def calculate_turnover_amounts_by_type(self, userID, language):
        try:
            turnoverAPI = CREDENTIALS["CheckTurnover"].format(BO_base_url = CREDENTIALS["BO_base_url"], ID=userID, language=language)
            response = requests.get(turnoverAPI)

            if response.status_code != 200:
                self.logger.error(f"Failed to get turnover data. Status code: {response.status_code}")
                return 0, 0

            turnoverData = response.json()
            provider_amount = 0
            non_provider_amount = 0

            for item in turnoverData:
                if 'provider_ids' in item and item['provider_ids'] is not None:
                    # For items with provider_ids, sum both recharge and bonus
                    recharge = float(item.get('recharge_amount', 0))
                    bonus = float(item.get('bonus_amount', 0))
                    provider_amount += recharge + bonus
                    self.logger.info(f"Provider item - Recharge: {recharge}, Bonus: {bonus}")
                else:
                    # For items without provider_ids, only sum recharge
                    recharge = float(item.get('recharge_amount', 0))
                    non_provider_amount += recharge
                    self.logger.info(f"Non-provider item - Recharge: {recharge}")

            self.logger.info(f"Total provider amount (recharge + bonus): {provider_amount}")
            self.logger.info(f"Total non-provider amount (recharge only): {non_provider_amount}")

            return provider_amount, non_provider_amount

        except Exception as e:
            self.logger.error(f"Error calculating turnover amounts: {str(e)}")
            return 0, 0

    def setup_and_get_turnover_amounts(self, with_additional_deposit=False):
        try:

            username, password = self.test_init.register_and_deposit_with_promo(with_additional_deposit)
            if not username or not password:
                self.fail("Registration or deposit failed")

            self.switchAccount(username, password)
            self.navigate_to_transfer()
            userID = self.get_id_number()
            self.handleDeposit(userID)

            turnoverIncomplete, turnoverList = self.checkIncompleteTurnover(
                userID, checkIncomplete=True, language=self.language, transfer_check=True
            )
            self.logger.info(f"Turnover status - Incomplete: {turnoverIncomplete}, Locked: {turnoverList}")
            self.driver.refresh()

            provider_amount, non_provider_amount = self.calculate_turnover_amounts_by_type(userID, self.language)
            self.logger.info(f"Provider amount: {provider_amount}, Non-provider amount: {non_provider_amount}")

            return username, password, userID, provider_amount, non_provider_amount, turnoverList

        except Exception as e:
            self.logger.error(f"Setup failed: {str(e)}")
            raise

    def submit_transfer(self):
        submit_button = WebDriverWait(self.driver,
                                      10).until(EC.element_to_be_clickable((By.ID, "submit-transfer-button")))
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_button)
        time.sleep(3)
        submit_button.click()
        time.sleep(2)

    def test_01_EmptyFields(self):
        driver = self.driver
        fields = {
            "from_wallet": LANGUAGE_SETTINGS[self.language]["errors"]["from_wallet_empty"],
            "to_wallet": LANGUAGE_SETTINGS[self.language]["errors"]["to_wallet_empty"],
            "amount": LANGUAGE_SETTINGS[self.language]["errors"]["amount_empty"]
        }
        field_actions = {
            "from_wallet": lambda: self.
            selectWalletByAmount(0, mode='random', username=self.username, password=self.password),
            "to_wallet": lambda: self.
            selectWalletByAmount(1, mode='random', username=self.username, password=self.password),
            "amount": lambda: self.enter_amount("100")
        }
        filled_fields = set()

        try:
            scenarios = [{
                "fill": None
            }, {
                "fill": "from_wallet"
            }, {
                "fill": "to_wallet"
            }]

            for scenario in scenarios:
                if scenario["fill"]:
                    field_actions[scenario["fill"]]()
                    filled_fields.add(scenario["fill"])

                self.generic_submit(submit="submit-transfer-button")

                try:
                    time.sleep(1)
                    popup = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, "swal2-title")))
                    popup_text = popup.text

                    empty_field_messages = []
                    for field_name, field_label in fields.items():
                        if field_name not in filled_fields:
                            empty_field_messages.append(field_label)

                    expected_message = " | ".join(empty_field_messages)
                    self.logger.info(f"Expected message: {expected_message}")
                    self.logger.info(f"Actual message: {popup_text}")

                    self.assertEqual(
                        expected_message, popup_text,
                        f"Error message mismatch. Expected: '{expected_message}', Got: '{popup_text}'"
                    )

                    self.confirm_button()
                    time.sleep(1)

                except Exception as e:
                    self.logger.error(f"Failed to verify error message: {str(e)}")
                    self.fail(f"Error message verification failed: {str(e)}")

        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed: {str(e)}")

    # Transfer success (to the available provider) (higher balance wallet to lower balance wallet) - display success box
    def test_02_TransferToSelectedWalletBonusLocked(self):
        try:
            FromgameID, credit_from = self.selectWalletByAmount(
                0, mode='included_highest', username=self.username, password=self.password
            )
            time.sleep(1)
            TogameID, credit_to = self.selectWalletByAmount(
                1, mode='included_lowest', username=self.username, password=self.password
            )

            self.logger.info(f"Credit from: {credit_from}")
            self.logger.info(f"Credit to: {credit_to}")
            self.logger.info(f"From game ID: {FromgameID}")
            self.logger.info(f"To game ID: {TogameID}")

            self.transfer_and_verify(FromgameID, TogameID, credit_from, credit_to)
        except Exception as e:
            self.logger.error(f"Test failed with error: {str(e)}")
            self.fail(f"Test failed: {str(e)}")

    def test_03_ExceedBalanceLimit(self):
        credit_from, _ = self.selectWalletByAmount(
            0, mode='included_highest', username=self.username, password=self.password
        )
        time.sleep(1)
        _, _ = self.selectWalletByAmount(1, mode='included_lowest', username=self.username, password=self.password)

        max_amount = float(credit_from.replace(',', ''))
        self.logger.info(f"Max amount: {max_amount}")
        exceed_amount = round(random.uniform(max_amount + 1, max_amount * 2), 2)
        self.logger.info(f"Exceed amount: {exceed_amount}")

        self.logger.info(f"Transferring amount: {exceed_amount}")
        self.enter_amount(exceed_amount)

        self.generic_submit(
            expected_result="failure", submit="submit-transfer-button", check_general_error=True,
            expected_error=LANGUAGE_SETTINGS[self.language]["errors"]["transfer_exceed_balance_limit"], id="swal2-title"
        )
        time.sleep(5)

    def test_04_ClearButton(self):
        initial_button_texts = [self.get_all_button_texts()[0], self.get_all_button_texts()[1]]
        _, _ = self.selectWalletByAmount(0, mode='included_highest', username=self.username, password=self.password)
        time.sleep(1)
        _, _ = self.selectWalletByAmount(1, mode='included_lowest', username=self.username, password=self.password)

        randomAmount = round(random.uniform(1, 9999), 2)
        AmountField = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, "amount-input")))
        self.enter_amount(randomAmount)

        self.clear_details(clearButton="clear-text")
        time.sleep(2)
        self.verify_clear_functionality(initial_button_texts, [0, 1], transferChecking=True)
        time.sleep(5)

    #Test Invalid Amount Input (eg: amount with more than 2 dp, negative value, character, special characters, 0)
    def test_05_InvalidAmount(self):
        try:
            self.selectWalletByAmount(0, mode='included_highest', username=self.username, password=self.password)
            time.sleep(1)
            self.selectWalletByAmount(1, mode='included_lowest', username=self.username, password=self.password)
            self.check_invalid_amount(
                amount_field_id="amount-input", submit_button_id="submit-transfer-button", transfer=True
            )
        except Exception as e:
            self.fail(f"Test failed: {str(e)}")

    #Transfer Same Wallet - display error message of "You cannot transfer between the same wallet."
    def test_06_TransferSameWallet(self):
        self.selectWalletByAmount(0, mode='included_highest', username=self.username, password=self.password)
        time.sleep(1)
        self.selectWalletByAmount(1, mode='included_highest', username=self.username, password=self.password)
        randomAmount = round(random.uniform(1, 9999), 2)
        self.enter_amount(randomAmount)

        self.generic_submit(
            expected_result="failure", submit="submit-transfer-button", check_general_error=True,
            expected_error=LANGUAGE_SETTINGS[self.language]["errors"]["transfer_same_wallet"], id="swal2-title"
        )
        time.sleep(5)

    #Transfer with zero balance wallet
    def test_07_TransferFromZeroCredit(self):
        self.selectWalletByAmount(0, mode='included_lowest', username=self.username, password=self.password)
        time.sleep(1)
        self.selectWalletByAmount(1, mode='random', username=self.username, password=self.password)
        randomAmount = round(random.uniform(1, 9999), 2)
        self.enter_amount(randomAmount)

        self.generic_submit(
            expected_result="failure", submit="submit-transfer-button", check_general_error=True,
            expected_error=LANGUAGE_SETTINGS[self.language]["errors"]["transfer_exceed_balance_limit"], id="swal2-title"
        )
        time.sleep(5)

    def test_08_SearchWithValidKeyword(self):
        try:
            self.search_and_verify_results("Relax", expected_valid=True)
        except Exception as e:
            self.fail(f"Test failed: {str(e)}")

    def test_09_SearchWithInvalidKeyword(self):
        try:
            self.search_and_verify_results("Test", expected_valid=False)
        except Exception as e:
            self.fail(f"Test failed: {str(e)}")

    #wait BE fix
    def test_10_VerifyBalanceforSameWallet(self):
        try:
            self.switchToCompleteTurnoverAcc()
            complete_turnover_username = CREDENTIALS["complete_turnover"]["username"]
            complete_turnover_password = CREDENTIALS["complete_turnover"]["password"]

            from_game_id, credit_from = self.selectWalletByAmount(
                0, mode='included_highest', username=complete_turnover_username, password=complete_turnover_password
            )
            time.sleep(1)

            to_game_id, credit_to = self.selectWalletByAmount(
                1, mode='specificID', username=complete_turnover_username, password=complete_turnover_password,
                target_gameID=16
            )
            time.sleep(1)

            self.logger.info(f"From game ID: {from_game_id}")
            self.logger.info(f"To game ID: {to_game_id}")
            self.logger.info(f"Credit from: {credit_from}")
            self.logger.info(f"Credit to: {credit_to}")

            self.transfer_and_verify(from_game_id, to_game_id, credit_from, credit_to)

        except Exception as e:
            self.logger.error(f"Test failed: {str(e)}")
            self.fail(f"Test failed: {str(e)}")

    # Transfer from main to the other provider (without complete turnover)
    def test_11_TransferFromMainToOtherWalletWithoutCompleteTurnover(self):
        try:
            username, password, _, _, _, _ = self.setup_and_get_turnover_amounts(with_additional_deposit=True)
            game_id_from, credit_from = self.selectWalletByAmount(
                0, mode='specificID', username=username, password=password, target_gameID=0
            )
            time.sleep(1)
            game_id_to, credit_to = self.selectWalletByAmount(
                1, mode='excluded_lowest', username=username, password=password
            )
            time.sleep(1)

            self.check_turnover_and_transfer(game_id_from, game_id_to, credit_from, credit_to)

        except Exception as e:
            self.fail(f"Test failed: {str(e)}")

    # without complete turnover, and transfer out 30 to main wallet (Expect Fail)
    def test_12_TransferToMainWithoutCompleteTurnover(self):
        try:
            username, password, _, _, _, _ = self.setup_and_get_turnover_amounts(with_additional_deposit=True)
            game_id_from, credit_from = self.selectWalletByAmount(
                0, mode='specificID', username=username, password=password, target_gameID=0
            )
            time.sleep(1)
            game_id_to, credit_to = self.selectWalletByAmount(
                1, mode='included_lowest', username=username, password=password
            )

            self.transfer_and_verify(game_id_from, game_id_to, credit_from, credit_to)
            self.driver.refresh()

            game_id_from, credit_from = self.selectWalletByAmount(
                0, mode='specificID', username=username, password=password, target_gameID=game_id_to
            )
            time.sleep(1)
            game_id_to, credit_to = self.selectWalletByAmount(
                1, mode='specificID', username=username, password=password, target_gameID=0
            )
            time.sleep(1)

            self.check_turnover_and_transfer(game_id_from, game_id_to, credit_from, credit_to)

        except Exception as e:
            self.fail(f"Test failed: {str(e)}")

    # Transfer From Main to another wallet (without complete turnover)
    def test_13_TransferToOtherWalletWithoutCompleteTurnover(self):
        try:
            username, password, _, _, _, _ = self.setup_and_get_turnover_amounts(with_additional_deposit=True)

            game_id_from, credit_from = self.selectWalletByAmount(
                0, mode='specificID', username=username, password=password, target_gameID=0
            )
            time.sleep(1)
            game_id_to, credit_to = self.selectWalletByAmount(
                1, mode='excluded_lowest', username=username, password=password
            )
            time.sleep(5)

            self.check_turnover_and_transfer(game_id_from, game_id_to, credit_from, credit_to)

        except Exception as e:
            self.fail(f"Test failed: {str(e)}")

    # Transfer across the selected provider under same category after using a promotion
    def test_14_TransferAccrossWalletWithoutCompleteTurnover(self):
        try:
            username, password, _, _, _, _ = self.setup_and_get_turnover_amounts(with_additional_deposit=True)
            game_id_from, credit_from = self.selectWalletByAmount(
                0, mode='specificID', username=username, password=password, target_gameID=0
            )
            time.sleep(1)
            game_id_to, credit_to = self.selectWalletByAmount(
                1, mode='included_lowest', username=username, password=password
            )

            self.transfer_and_verify(game_id_from, game_id_to, credit_from, credit_to)
            self.driver.refresh()

            from_game_id, credit_from = self.selectWalletByAmount(
                0, mode='included_highest', username=username, password=password
            )
            time.sleep(1)
            to_game_id, credit_to = self.selectWalletByAmount(
                1, mode='included_lowest', username=username, password=password
            )
            time.sleep(1)

            self.transfer_and_verify(from_game_id, to_game_id, credit_from, credit_to)

        except Exception as e:
            self.fail(f"Test failed: {str(e)}")

    #check if no turnoverIDs, then lock the bonus until there is turnoverIDs
    # Unlock Promo Bonus Lock,transfer from slot to main (Expect Success)
    def test_15_TransferFromSpecificWalletToMainUnlockBonus(self):
        try:
            userID = self.get_id_number()
            turnoverIDs = self.get_turnover_ids(userID, self.language)

            if not turnoverIDs:
                self.fail("No turnoverIDs found")

            unlock_success = self.modify_turnover_status(userID, turnoverIDs, action_type="unlock")
            if not unlock_success:
                self.fail("Failed to unlock turnover")

            turnoverIncomplete, locked_by_list = self.checkIncompleteTurnover(
                userID, checkIncomplete=True, language=self.language, transfer_check=True
            )
            self.logger.info(
                f"Turnover status after unlock - Incomplete: {turnoverIncomplete}, Locked: {locked_by_list}"
            )

            game_id, credit_from = self.selectWalletByAmount(
                0, mode='included_highest', username=self.username, password=self.password, nomain=True
            )
            time.sleep(1)

            game_id_to, credit_to = self.selectWalletByAmount(
                1, mode='specificID', username=self.username, password=self.password, target_gameID=0
            )
            time.sleep(1)

            self.transfer_and_verify(game_id, game_id_to, credit_from, credit_to)

        except Exception as e:
            self.logger.error(f"Test failed: {str(e)}")
            self.fail(f"Test failed: {str(e)}")

    #check if no turnoverIDs, then lock the bonus until there is turnoverIDs
    # transfer from slot to other provider (Expect Success)
    def test_16_TransferFromSpecificWalletToOtherProviderUnlockBonus(self):
        try:
            userID = self.get_id_number()
            #lock bonus first
            has_providers, providers_list = self.checkProviders(userID, self.language)

            if has_providers:
                provider_ids = self.parse_provider_ids(providers_list)
                self.logger.info(f"Provider IDs: {provider_ids}")

            turnoverIDs = self.get_turnover_ids(userID, self.language)

            if not turnoverIDs:
                self.fail("No turnoverIDs found")

            unlock_success = self.modify_turnover_status(userID, turnoverIDs, action_type="unlock")
            if not unlock_success:
                self.fail("Failed to unlock turnover")

            turnoverIncomplete, locked_by_list = self.checkIncompleteTurnover(
                userID, checkIncomplete=True, language=self.language, transfer_check=True
            )
            self.logger.info(
                f"Turnover status after unlock - Incomplete: {turnoverIncomplete}, Locked: {locked_by_list}"
            )

            game_id, credit_from = self.selectWalletByAmount(
                0, mode='included_highest', username=self.username, password=self.password, nomain=True
            )
            time.sleep(1)

            game_id_to, credit_to = self.selectWalletByAmount(
                1, mode='excluded_lowest', username=self.username, password=self.password, provider_ids=provider_ids
            )
            time.sleep(1)

            self.transfer_and_verify(game_id, game_id_to, credit_from, credit_to)

        except Exception as e:
            self.logger.error(f"Test failed: {str(e)}")
            self.fail(f"Test failed: {str(e)}")

    # Unlock Promo Bonus Lock, transfer from main wallet to other provider (Expect Success)
    def test_17_TransferFromMainToOtherProviderUnlockBonus(self):
        try:
            userID = self.get_id_number()
            #lock bonus first
            has_providers, providers_list = self.checkProviders(userID, self.language)

            if has_providers:
                provider_ids = self.parse_provider_ids(providers_list)
                self.logger.info(f"Provider IDs: {provider_ids}")

            turnoverIDs = self.get_turnover_ids(userID, self.language)

            if not turnoverIDs:
                self.fail("No turnoverIDs found")

            unlock_success = self.modify_turnover_status(userID, turnoverIDs, action_type="unlock")
            if not unlock_success:
                self.fail("Failed to unlock turnover")

            turnoverIncomplete, locked_by_list = self.checkIncompleteTurnover(
                userID, checkIncomplete=True, language=self.language, transfer_check=True
            )
            self.logger.info(
                f"Turnover status after unlock - Incomplete: {turnoverIncomplete}, Locked: {locked_by_list}"
            )

            game_id, credit_from = self.selectWalletByAmount(
                0, mode='specificID', username=self.username, password=self.password, target_gameID=0
            )
            time.sleep(1)

            game_id_to, credit_to = self.selectWalletByAmount(
                1, mode='excluded_lowest', username=self.username, password=self.password, provider_ids=provider_ids
            )
            time.sleep(1)

            self.transfer_and_verify(game_id, game_id_to, credit_from, credit_to)

        except Exception as e:
            self.logger.error(f"Test failed: {str(e)}")
            self.fail(f"Test failed: {str(e)}")

    # Unlock Promo Bonus Lock, transfer from main wallet to slot (Expect Success)
    def test_18_TransferFromMainToSelectedProviderUnlockBonus(self):
        try:
            userID = self.get_id_number()
            #lock bonus first
            has_providers, providers_list = self.checkProviders(userID, self.language)

            if has_providers:
                provider_ids = self.parse_provider_ids(providers_list)
                self.logger.info(f"Provider IDs: {provider_ids}")

            turnoverIDs = self.get_turnover_ids(userID, self.language)

            if not turnoverIDs:
                self.fail("No turnoverIDs found")

            unlock_success = self.modify_turnover_status(userID, turnoverIDs, action_type="unlock")
            if not unlock_success:
                self.fail("Failed to unlock turnover")

            turnoverIncomplete, locked_by_list = self.checkIncompleteTurnover(
                userID, checkIncomplete=True, language=self.language, transfer_check=True
            )
            self.logger.info(
                f"Turnover status after unlock - Incomplete: {turnoverIncomplete}, Locked: {locked_by_list}"
            )

            game_id, credit_from = self.selectWalletByAmount(
                0, mode='specificID', username=self.username, password=self.password, target_gameID=0
            )
            time.sleep(1)

            game_id_to, credit_to = self.selectWalletByAmount(
                1, mode='excluded_lowest', username=self.username, password=self.password, provider_ids=provider_ids
            )
            time.sleep(1)

            self.transfer_and_verify(game_id, game_id_to, credit_from, credit_to)

        except Exception as e:
            self.logger.error(f"Test failed: {str(e)}")
            self.fail(f"Test failed: {str(e)}")

    # Complete Turnover that with Promo Bonus Lock, Transfer out 30 to other provider (Expect Fail)
    def test_19_TransferFromMainToOtherProviderCompleteTurnover(self):
        self.submit_deposit_api(promoCode="10DSRB", username=self.username, password=self.password)
        userID = self.get_id_number()
        self.handleDeposit(userID)

        has_providers, providers_list = self.checkProviders(userID, self.language)

        if has_providers:
            provider_ids = self.parse_provider_ids(providers_list)
            self.logger.info(f"Provider IDs: {provider_ids}")

            transfer_needed = self.check_and_transfer_to_empty_providers(provider_ids)
            if transfer_needed:
                time.sleep(2)

        turnoverIDs = self.get_turnover_ids(userID, self.language)
        if not turnoverIDs:
            self.fail("No turnoverIDs found")

        turnoverIncomplete, turnoverList = self.checkIncompleteTurnover(
            userID, checkIncomplete=True, language=self.language, transfer_check=True
        )
        self.logger.info(f"Turnover status before unlock - Incomplete: {turnoverIncomplete}, Locked: {turnoverList}")

        complete_success = self.modify_turnover_status(userID, turnoverIDs, action_type="success")
        if not complete_success:
            self.fail("Failed to complete turnover")

        game_id_from, credit_from = self.selectWalletByAmount(
            0, mode='included_highest', username=self.username, password=self.password, nomain=True
        )
        time.sleep(1)

        game_id_to, credit_to = self.selectWalletByAmount(
            1, mode='excluded_lowest', username=self.username, password=self.password, provider_ids=provider_ids
        )
        time.sleep(1)

        self.check_turnover_and_transfer(game_id_from, game_id_to, credit_from, credit_to, turnoverList=turnoverList)

    # Complete Turnover that with Promo Bonus Lock, Transfer out 30 to main wallet (Expect Success)
    def test_20_TransferFromSelectedProviderToMainCompleteTurnover(self):
        self.submit_deposit_api(promoCode="10DSRB", username=self.username, password=self.password)
        userID = self.get_id_number()
        self.handleDeposit(userID)

        has_providers, providers_list = self.checkProviders(userID, self.language)

        if has_providers:
            provider_ids = self.parse_provider_ids(providers_list)
            self.logger.info(f"Provider IDs: {provider_ids}")

            transfer_needed = self.check_and_transfer_to_empty_providers(provider_ids)
            if transfer_needed:
                time.sleep(2)

        turnoverIDs = self.get_turnover_ids(userID, self.language)
        if not turnoverIDs:
            self.fail("No turnoverIDs found")

        turnoverIncomplete, turnoverList = self.checkIncompleteTurnover(
            userID, checkIncomplete=True, language=self.language, transfer_check=True
        )
        self.logger.info(f"Turnover status before unlock - Incomplete: {turnoverIncomplete}, Locked: {turnoverList}")

        complete_success = self.modify_turnover_status(userID, turnoverIDs, action_type="success")
        if not complete_success:
            self.fail("Failed to complete turnover")

        game_id, credit_from = self.selectWalletByAmount(
            0, mode='included_highest', username=self.username, password=self.password, nomain=True
        )
        time.sleep(1)

        game_id_to, credit_to = self.selectWalletByAmount(
            1, mode='specificID', username=self.username, password=self.password, target_gameID=0
        )
        time.sleep(1)

        self.transfer_and_verify(game_id, game_id_to, credit_from, credit_to)

    # if havent finish turnover, transfer the provider amount from Slot back to other provider (Expected Fail)
    def test_21_ProviderAmount_ThenTransferToOtherProvider_WithoutCompleteTurnover(self):
        try:
            # Get setup and amounts
            username, password, userID, provider_amount, non_provider_amount, turnoverList = self.setup_and_get_turnover_amounts(
                with_additional_deposit=True
            )

            self.switchAccount(username, password)
            self.navigate_to_transfer()
            userID = self.get_id_number()
            self.handleDeposit(userID)

            turnoverIncomplete, turnoverList = self.checkIncompleteTurnover(
                userID, checkIncomplete=True, language=self.language, transfer_check=True
            )
            self.logger.info(
                f"Turnover status before unlock - Incomplete: {turnoverIncomplete}, Locked: {turnoverList}"
            )
            self.driver.refresh()

            #check amount for promo+bonus and additional top up
            provider_amount, non_provider_amount = self.calculate_turnover_amounts_by_type(userID, self.language)
            self.logger.info(f"Provider amount: {provider_amount}")
            self.logger.info(f"Non-provider amount: {non_provider_amount}")

            # Transfer provider amount to selected provider
            game_id_from, credit_from = self.selectWalletByAmount(
                0, mode='specificID', username=username, password=password, target_gameID=0
            )
            game_id_to, credit_to = self.selectWalletByAmount(
                1, mode='included_lowest', username=username, password=password
            )
            self.logger.info(f"Game ID from: {game_id_from}, Credit from: {credit_from}")
            self.logger.info(f"Game ID to: {game_id_to}, Credit to: {credit_to}")

            self.transfer_and_verify(game_id_from, game_id_to, credit_from, credit_to, amount=provider_amount)

            self.driver.refresh()

            # Transfer back to other provider
            game_id_from, credit_from = self.selectWalletByAmount(
                0, mode='specificID', username=username, password=password, target_gameID=game_id_to
            )
            game_id_to, credit_to = self.selectWalletByAmount(
                1, mode='excluded_lowest', username=username, password=password
            )

            self.check_turnover_and_transfer(
                game_id_from, game_id_to, credit_from, credit_to, turnoverList=turnoverList
            )

        except Exception as e:
            self.logger.error(f"Test failed: {str(e)}")
            self.fail(f"Test failed: {str(e)}")

    #if (30 + welcome) havent finish turnover, transfer the provider amount from Slot back to main wallet (Expected Fail)
    def test_22_ProviderAmount_ThenTransferToMain_WithoutCompleteTurnover(self):
        try:
            username, password, _, provider_amount, _, turnoverList = self.setup_and_get_turnover_amounts(
                with_additional_deposit=True
            )

            # Transfer provider amount to selected provider
            game_id_from, credit_from = self.selectWalletByAmount(
                0, mode='specificID', username=username, password=password, target_gameID=0
            )
            game_id_to, credit_to = self.selectWalletByAmount(
                1, mode='included_lowest', username=username, password=password
            )
            self.logger.info(f"Game ID from: {game_id_from}, Credit from: {credit_from}")
            self.logger.info(f"Game ID to: {game_id_to}, Credit to: {credit_to}")

            self.transfer_and_verify(game_id_from, game_id_to, credit_from, credit_to, amount=provider_amount)

            self.driver.refresh()

            # Transfer back to main wallet
            game_id_from, credit_from = self.selectWalletByAmount(
                0, mode='specificID', username=username, password=password, target_gameID=game_id_to
            )
            game_id_to, credit_to = self.selectWalletByAmount(
                1, mode='specificID', username=username, password=password, target_gameID=0
            )

            self.check_turnover_and_transfer(
                game_id_from, game_id_to, credit_from, credit_to, turnoverList=turnoverList
            )

        except Exception as e:
            self.logger.error(f"Test failed: {str(e)}")
            self.fail(f"Test failed: {str(e)}")

    # if havent finish turnover, transfer the provider  & non-provider amount to casino and slot (Expected Success)
    def test_23_AdditionalTopUp_TransferToSelectedProviderAndOtherProvider_WithoutCompleteTurnover(self):
        try:
            username, password, _, provider_amount, non_provider_amount, _ = self.setup_and_get_turnover_amounts(
                with_additional_deposit=True
            )

            # Transfer provider amount to selected provider
            game_id_from, credit_from = self.selectWalletByAmount(
                0, mode='specificID', username=username, password=password, target_gameID=0
            )
            game_id_to, credit_to = self.selectWalletByAmount(
                1, mode='included_lowest', username=username, password=password
            )
            self.logger.info(f"Game ID from: {game_id_from}, Credit from: {credit_from}")
            self.logger.info(f"Game ID to: {game_id_to}, Credit to: {credit_to}")

            self.transfer_and_verify(game_id_from, game_id_to, credit_from, credit_to, amount=provider_amount)

            self.driver.refresh()

            # Transfer non-provider amount to selected provider
            game_id_from, credit_from = self.selectWalletByAmount(
                0, mode='specificID', username=username, password=password, target_gameID=0
            )
            game_id_to, credit_to = self.selectWalletByAmount(
                1, mode='excluded_lowest', username=username, password=password
            )
            self.transfer_and_verify(game_id_from, game_id_to, credit_from, credit_to, amount=non_provider_amount)

        except Exception as e:
            self.logger.error(f"Test failed: {str(e)}")

    # if havent finish turnover, transfer the provider & non-provider amount from Slot back to main wallet (Expected Fail
    def test_24_AdditionalTopUp_WithdrawFromSelectedProviderToMain_WithoutCompleteTurnover(self):
        try:
            username, password, _, provider_amount, non_provider_amount, _ = self.setup_and_get_turnover_amounts(
                with_additional_deposit=True
            )

            # Transfer provider amount to selected provider
            game_id_from, credit_from = self.selectWalletByAmount(
                0, mode='specificID', username=username, password=password, target_gameID=0
            )
            game_id_to, credit_to = self.selectWalletByAmount(
                1, mode='included_lowest', username=username, password=password
            )
            self.logger.info(f"Game ID from: {game_id_from}, Credit from: {credit_from}")
            self.logger.info(f"Game ID to: {game_id_to}, Credit to: {credit_to}")

            entire_amount = provider_amount + non_provider_amount

            self.transfer_and_verify(game_id_from, game_id_to, credit_from, credit_to, amount=entire_amount)

            self.driver.refresh()

            game_id_from, credit_from = self.selectWalletByAmount(
                0, mode='specificID', username=username, password=password, target_gameID=game_id_to
            )
            game_id_to, credit_to = self.selectWalletByAmount(
                1, mode='specificID', username=username, password=password, target_gameID=0
            )

            self.check_turnover_and_transfer(game_id_from, game_id_to, credit_from, credit_to)
        except Exception as e:
            self.logger.error(f"Test failed: {str(e)}")
            self.fail(f"Test failed: {str(e)}")

    #if havent finish turnover, transfer the provider & non-provider amount from Slot back to other provider (Expected Fail)
    def test_25_AdditionalTopUp_WithdrawFromSelectedProviderToOtherProvider_WithoutCompleteTurnover(self):
        try:
            username, password, _, provider_amount, non_provider_amount, _ = self.setup_and_get_turnover_amounts(
                with_additional_deposit=True
            )

            game_id_from, credit_from = self.selectWalletByAmount(
                0, mode='specificID', username=username, password=password, target_gameID=0
            )
            game_id_to, credit_to = self.selectWalletByAmount(
                1, mode='included_lowest', username=username, password=password
            )
            self.logger.info(f"Game ID from: {game_id_from}, Credit from: {credit_from}")
            self.logger.info(f"Game ID to: {game_id_to}, Credit to: {credit_to}")

            entire_amount = provider_amount + non_provider_amount

            self.transfer_and_verify(game_id_from, game_id_to, credit_from, credit_to, amount=entire_amount)

            self.driver.refresh()

            game_id_from, credit_from = self.selectWalletByAmount(
                0, mode='specificID', username=username, password=password, target_gameID=game_id_to
            )
            game_id_to, credit_to = self.selectWalletByAmount(
                1, mode='excluded_lowest', username=username, password=password
            )

            self.check_turnover_and_transfer(game_id_from, game_id_to, credit_from, credit_to)
        except Exception as e:
            self.logger.error(f"Test failed: {str(e)}")
            self.fail(f"Test failed: {str(e)}")

    #if havent finish turnover, transfer the 100 additional amount from main wallet to other provider (Expected Success)
    def test_26_AdditionalTopUp_TransferFromMainToOtherProvider_WithoutCompleteTurnover(self):
        try:
            username, password, _, _, non_provider_amount, _ = self.setup_and_get_turnover_amounts(
                with_additional_deposit=True
            )

            game_id_from, credit_from = self.selectWalletByAmount(
                0, mode='specificID', username=username, password=password, target_gameID=0
            )
            game_id_to, credit_to = self.selectWalletByAmount(
                1, mode='excluded_lowest', username=username, password=password
            )
            self.logger.info(f"Game ID from: {game_id_from}, Credit from: {credit_from}")
            self.logger.info(f"Game ID to: {game_id_to}, Credit to: {credit_to}")

            self.transfer_and_verify(game_id_from, game_id_to, credit_from, credit_to, amount=non_provider_amount)

            self.driver.refresh()

            game_id_from, credit_from = self.selectWalletByAmount(
                0, mode='specificID', username=username, password=password, target_gameID=game_id_to
            )
            game_id_to, credit_to = self.selectWalletByAmount(1, mode='random', username=username, password=password)

            self.transfer_and_verify(game_id_from, game_id_to, credit_from, credit_to)
        except Exception as e:
            self.logger.error(f"Test failed: {str(e)}")
            self.fail(f"Test failed: {str(e)}")

    #if havent finish turnover, transfer the 100 additional amount from Casino back to main wallet (Expected Success)
    def test_27_AdditionalTopUp_TransferFromSelectedProviderToMain_CompleteTurnover(self):
        try:
            username, password, userID, _, non_provider_amount, _ = self.setup_and_get_turnover_amounts(
                with_additional_deposit=True
            )

            game_id_from, credit_from = self.selectWalletByAmount(
                0, mode='specificID', username=username, password=password, target_gameID=0
            )
            game_id_to, credit_to = self.selectWalletByAmount(
                1, mode='included_lowest', username=username, password=password
            )
            self.logger.info(f"Game ID from: {game_id_from}, Credit from: {credit_from}")
            self.logger.info(f"Game ID to: {game_id_to}, Credit to: {credit_to}")

            self.transfer_and_verify(game_id_from, game_id_to, credit_from, credit_to, amount=non_provider_amount)

            turnoverIDs = self.get_turnover_ids(userID, self.language)
            if not turnoverIDs:
                self.fail("No turnoverIDs found")

            complete_success = self.modify_turnover_status(userID, turnoverIDs, action_type="success")
            if not complete_success:
                self.fail("Failed to complete turnover")

            self.driver.refresh()

            game_id_from, credit_from = self.selectWalletByAmount(
                0, mode='specificID', username=username, password=password, target_gameID=game_id_to
            )
            game_id_to, credit_to = self.selectWalletByAmount(
                1, mode='specificID', username=username, password=password, target_gameID=0
            )

            self.transfer_and_verify(game_id_from, game_id_to, credit_from, credit_to)
        except Exception as e:
            self.logger.error(f"Test failed: {str(e)}")
            self.fail(f"Test failed: {str(e)}")

    #if complete turnover, transfer the 100 additional amount from Slot back to other provider (Expected Success)
    def test_28_AdditionalTopUp_TransferFromSelectedProviderToOtherProvider_CompleteTurnover(self):
        try:
            username, password, userID, _, non_provider_amount, _ = self.setup_and_get_turnover_amounts(
                with_additional_deposit=True
            )

            game_id_from, credit_from = self.selectWalletByAmount(
                0, mode='specificID', username=username, password=password, target_gameID=0
            )
            game_id_to, credit_to = self.selectWalletByAmount(
                1, mode='included_lowest', username=username, password=password
            )
            self.logger.info(f"Game ID from: {game_id_from}, Credit from: {credit_from}")
            self.logger.info(f"Game ID to: {game_id_to}, Credit to: {credit_to}")

            self.transfer_and_verify(game_id_from, game_id_to, credit_from, credit_to, amount=non_provider_amount)

            turnoverIDs = self.get_turnover_ids(userID, self.language)
            if not turnoverIDs:
                self.fail("No turnoverIDs found")

            complete_success = self.modify_turnover_status(userID, turnoverIDs, action_type="success")
            if not complete_success:
                self.fail("Failed to complete turnover")

            self.driver.refresh()

            game_id_from, credit_from = self.selectWalletByAmount(
                0, mode='specificID', username=username, password=password, target_gameID=game_id_to
            )
            game_id_to, credit_to = self.selectWalletByAmount(1, mode='random', username=username, password=password)

            self.transfer_and_verify(game_id_from, game_id_to, credit_from, credit_to)
        except Exception as e:
            self.logger.error(f"Test failed: {str(e)}")
            self.fail(f"Test failed: {str(e)}")

    #if after finish turnover, additional top up 100, transfer the additional amount to slot and out of slot to other provider (Expected Success)
    def test_29_AdditionalTopUp_TransferFromSelectedProviderToOtherProvider_CompleteTurnover(self):
        try:
            username, password, userID, provider_amount, non_provider_amount, _ = self.setup_and_get_turnover_amounts(
                with_additional_deposit=True
            )

            game_id_from, credit_from = self.selectWalletByAmount(
                0, mode='specificID', username=username, password=password, target_gameID=0
            )
            game_id_to, credit_to = self.selectWalletByAmount(
                1, mode='included_lowest', username=username, password=password
            )

            entire_amount = provider_amount + non_provider_amount

            self.transfer_and_verify(game_id_from, game_id_to, credit_from, credit_to, amount=entire_amount)

            turnoverIDs = self.get_turnover_ids(userID, self.language)
            if not turnoverIDs:
                self.fail("No turnoverIDs found")

            complete_success = self.modify_turnover_status(userID, turnoverIDs, action_type="success")
            if not complete_success:
                self.fail("Failed to complete turnover")

            self.test_init.submit_deposit_api(username=username, password=password)
            userID = self.get_id_number()
            self.handleDeposit(userID)
            self.driver.refresh()

            game_id_from, credit_from = self.selectWalletByAmount(
                0, mode='specificID', username=username, password=password, target_gameID=0
            )
            game_id_to, credit_to = self.selectWalletByAmount(
                1, mode='specificID', username=username, password=password, target_gameID=game_id_to
            )

            self.transfer_and_verify(game_id_from, game_id_to, credit_from, credit_to)
            self.driver.refresh()
            time.sleep(1)

            game_id_from, credit_from = self.selectWalletByAmount(
                0, mode='specificID', username=username, password=password, target_gameID=game_id_to
            )
            game_id_to, credit_to = self.selectWalletByAmount(1, mode='random', username=username, password=password)
            self.transfer_and_verify(game_id_from, game_id_to, credit_from, credit_to)
        except Exception as e:
            self.logger.error(f"Test failed: {str(e)}")
            self.fail(f"Test failed: {str(e)}")

    def test_30_TransferOutToMain_PartialCompleteTurnover(self):
        try:
            for i in range(2):
                username, password, userID, provider_amount, non_provider_amount, _ = self.setup_and_get_turnover_amounts(
                    with_additional_deposit=True
                )

            game_id_from, credit_from = self.selectWalletByAmount(
                0, mode='specificID', username=username, password=password, target_gameID=0
            )
            game_id_to, credit_to = self.selectWalletByAmount(
                1, mode='included_lowest', username=username, password=password
            )

            entire_amount = provider_amount + non_provider_amount

            self.transfer_and_verify(game_id_from, game_id_to, credit_from, credit_to, amount=entire_amount)

            turnoverIDs = self.get_turnover_ids(userID, self.language)
            if not turnoverIDs:
                self.fail("No turnoverIDs found")

            complete_success = self.modify_turnover_status(userID, turnoverIDs, action_type="success", partial=True)
            if not complete_success:
                self.fail("Failed to complete turnover")

            self.driver.refresh()

            game_id_from, credit_from = self.selectWalletByAmount(
                0, mode='specificID', username=username, password=password, target_gameID=game_id_to
            )
            game_id_to, credit_to = self.selectWalletByAmount(
                1, mode='specificID', username=username, password=password, target_gameID=0
            )

            self.check_turnover_and_transfer(game_id_from, game_id_to, credit_from, credit_to)

        except Exception as e:
            self.logger.error(f"Test failed: {str(e)}")
            self.fail(f"Test failed: {str(e)}")


if __name__ == "__main__":
    unittest.main()
