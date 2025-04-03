import unittest
import time
import logging
import random
import requests
import re
import json
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from selenium.webdriver.support import expected_conditions as EC
from config.constant import CREDENTIALS, LANGUAGE_SETTINGS, LIVE_AGENT_URL
from tests.authentication_test.base_test import BaseTest
from tests.test_init import TestInit
from tests.test_live_agent import TestLiveAgent
from tests.transaction_history_test.test_history import TestHistory


class TestLeaderboard(BaseTest):

    def __init__(self, methodName="runTest", language=None, browser=None):
        super().__init__(methodName, language, browser)
        self.test_init = TestInit(methodName="runTest", language=language, browser=browser)
        self.test_live_agent = TestLiveAgent(methodName="runTest", language=language, browser=browser)
        self.test_history = TestHistory(methodName="runTest", language=language, browser=browser)

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
        self.click_navigation_bar("footer-profile-button")

    def tearDown(self):
        if hasattr(self, "driver"):
            self.driver.quit()

    def find_element_by_id(self, element_id, wait_time=10):
        try:
            return WebDriverWait(self.driver, wait_time).until(EC.presence_of_element_located((By.ID, element_id)))
        except Exception as e:
            self.logger.error(f"Could not find element with ID '{element_id}': {str(e)}")
            raise

    def extract_numeric_value(self, element_text, position=-1):
        try:
            cleaned_text = element_text.replace("RM", "").replace(",", "").strip()
            parts = cleaned_text.split(" ")
            if 0 <= position < len(parts) or (position < 0 and abs(position) <= len(parts)):
                numeric_text = parts[position]
                return int(numeric_text)
            else:
                self.logger.warning(f"Position {position} out of range for text: '{element_text}'")
                return 0
        except ValueError as e:
            self.logger.error(f"Failed to convert to number: '{element_text}' - {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Error extracting numeric value: {str(e)}")
            raise

    def navigate_to_leaderboard(self):
        try:
            leaderboard_button = self.find_element_by_id("reward-button")
            leaderboard_button.click()
            time.sleep(2)
            self.logger.info("Successfully navigated to leaderboard page")
        except Exception as e:
            self.logger.error(f"Failed to navigate to leaderboard: {str(e)}")
            raise

    def get_turnover_value(self, tier_element_id):
        element = self.find_element_by_id(tier_element_id)
        value = self.extract_numeric_value(element.text)
        self.logger.info(f"Turnover value for {tier_element_id}: {value}")
        return value

    def check_milestone_progress(self, valid=False):
        try:
            milestone_point = WebDriverWait(self.driver,
                                            10).until(EC.presence_of_element_located((By.ID, "milestone-point-0")))
            self.logger.info("Found milestone-point-0 element")

            milestone_check_present = True
            try:
                milestone_check = milestone_point.find_element(By.ID, "milestone-check-0")
                is_displayed = milestone_check.is_displayed()
                self.logger.info(f"Found milestone-check-0 element, displayed: {is_displayed}")
            except NoSuchElementException:
                milestone_check_present = False
                is_displayed = False
                self.logger.info("milestone-check-0 not found inside milestone-point-0")

            if valid:
                if not milestone_check_present:
                    self.fail("Expected milestone check icon to be present, but it was not found")
                self.assertTrue(is_displayed, "Expected milestone check icon to be displayed, but it was not")
                self.logger.info("✓ Milestone check icon is present and displayed as expected")
            else:
                if milestone_check_present and is_displayed:
                    self.fail("Expected milestone check icon to NOT be displayed, but it was visible")
                self.logger.info("✓ Milestone check icon is correctly not displayed/not present as expected")

        except Exception as e:
            self.logger.error(f"Error verifying milestone progress: {str(e)}")
            self.fail(f"Failed to verify milestone progress: {str(e)}")

    def normalize_text(self, text):
        text = text.lower()
        text = re.sub(r'[^\w\s]', '', text)
        text = re.sub(r'\s+', '', text)
        return text

    def collect_leaderboard_rankings(self):
        try:
            self.logger.info("Collecting comprehensive leaderboard ranking information")

            all_rankings = []

            overall_position = 1

            for i in range(3):
                ranking_info = {}
                ranking_info["ranking_type"] = "top"

                try:
                    name_id = f"reward-name-top-3-{i}"
                    name_element = self.driver.find_element(By.ID, name_id)
                    ranking_info["name"] = name_element.text.strip()

                    turnover_id = f"reward-turnover-top-3-{i}"
                    turnover_element = self.driver.find_element(By.ID, turnover_id)
                    turnover_text = turnover_element.text.strip()

                    clean_turnover = turnover_text.replace("RM", "").replace(",", "").strip()
                    ranking_info["turnover_raw"] = turnover_text

                    try:
                        ranking_info["turnover"] = float(clean_turnover)
                    except ValueError:
                        ranking_info["turnover"] = 0
                        self.logger.warning(f"Could not convert turnover value '{clean_turnover}' to float")

                    member_id = f"reward-effective-new-add-top-3-{i}"
                    member_element = self.driver.find_element(By.ID, member_id)
                    member_text = member_element.text.strip()

                    member_count_match = re.search(r'Member:\s*(\d+)', member_text)
                    if member_count_match:
                        ranking_info["member_count"] = int(member_count_match.group(1))
                    else:
                        ranking_info["member_count"] = 0
                        ranking_info["member_raw"] = member_text

                    ranking_info["position"] = overall_position

                    all_rankings.append(ranking_info)
                    self.logger.info(f"Collected ranking {overall_position}: {ranking_info}")
                    overall_position += 1

                except NoSuchElementException:
                    self.logger.warning(f"Could not find all elements for top position {i+1}")
                    continue

            rank_index = 0
            while True:
                try:
                    ranking_info = {}
                    ranking_info["ranking_type"] = "regular"

                    name_id = f"reward-name-ranking-{rank_index}"
                    name_element = self.driver.find_element(By.ID, name_id)
                    ranking_info["name"] = name_element.text.strip()

                    turnover_id = f"reward-turnover-ranking-{rank_index}"
                    turnover_element = self.driver.find_element(By.ID, turnover_id)
                    turnover_text = turnover_element.text.strip()

                    turnover_match = re.search(r'Turnover:\s*RM\s*([\d,.]+)', turnover_text)
                    if turnover_match:
                        clean_turnover = turnover_match.group(1).replace(",", "")
                        ranking_info["turnover_raw"] = turnover_text

                        try:
                            ranking_info["turnover"] = float(clean_turnover)
                        except ValueError:
                            ranking_info["turnover"] = 0
                            self.logger.warning(f"Could not convert turnover value '{clean_turnover}' to float")
                    else:
                        ranking_info["turnover"] = 0
                        ranking_info["turnover_raw"] = turnover_text

                    member_id = f"reward-effective-new-add-ranking-{rank_index}"
                    member_element = self.driver.find_element(By.ID, member_id)
                    member_text = member_element.text.strip()

                    member_count_match = re.search(r'Member:\s*(\d+)', member_text)
                    if member_count_match:
                        ranking_info["member_count"] = int(member_count_match.group(1))
                    else:
                        ranking_info["member_count"] = 0
                        ranking_info["member_raw"] = member_text

                    ranking_info["position"] = overall_position

                    all_rankings.append(ranking_info)
                    self.logger.info(f"Collected ranking {overall_position}: {ranking_info}")
                    overall_position += 1

                    rank_index += 1

                except NoSuchElementException:
                    # No more rankings found, exit loop
                    self.logger.info(f"Found {len(all_rankings)} rankings in total")
                    break

            self.logger.info(f"Successfully collected {len(all_rankings)} rankings")
            return all_rankings

        except Exception as e:
            self.logger.error(f"Error collecting leaderboard rankings: {str(e)}")
            return []

    def get_profile_avatar_url(self):
        try:
            avatar_img = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "img[alt='profile_avatar']"))
            )
            src_url = avatar_img.get_attribute("src")
            if "/_next/image?url=" in src_url:
                from urllib.parse import unquote
                encoded_url = src_url.split("url=")[1].split("&")[0]
                original_url = unquote(encoded_url)
                self.logger.info(f"Extracted avatar URL: {original_url}")
                return original_url
            return src_url
        except Exception as e:
            self.logger.error(f"Error getting profile avatar URL: {str(e)}")
            return None

    def test_01_VerifyRebateBalance_ProfilePage(self):
        try:
            total_bet_per_tier, total_rebate_per_tier, total_bet_amount, total_rebate_amount, tier_2_users, _, _ = self.test_init.create_downline_rebate(
                tier_1_userID=self.userID, username=self.username, password=self.password
            )
            self.logger.info(f"Total Rebate Amount: {total_rebate_amount}")
            self.logger.info(f"Total Bet Amount: {total_bet_amount}")
            self.logger.info(f"Total Rebate Per Tier: {total_rebate_per_tier}")
            self.logger.info(f"Total Bet Per Tier: {total_bet_per_tier}")
            self.driver.refresh()

            total_turnover = WebDriverWait(self.driver,
                                           10).until(EC.presence_of_element_located((By.ID, "turnover-amount")))
            total_turnover_text = total_turnover.text
            self.logger.info(f"Total Turnover: {total_turnover_text}")

            formatted_total_turnover = str(
                Decimal(total_turnover_text.replace("MYR", "").replace(",", "").strip()
                        ).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)
            )
            self.logger.info(f"Formatted Total Turnover: {formatted_total_turnover}")

            # Format total_bet_amount consistently
            formatted_total_bet_amount = str(
                Decimal(str(total_bet_amount)).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)
            )
            self.logger.info(f"Formatted Total Bet Amount: {formatted_total_bet_amount}")

            number_of_downline_users = len(tier_2_users)
            new_member_display = WebDriverWait(self.driver,
                                               10).until(EC.presence_of_element_located((By.ID, "effective-amount")))
            new_member_display_text = int(''.join(filter(str.isdigit, new_member_display.text)))
            self.logger.info(f"New Member Display: {new_member_display_text}")

            # Compare the string representations with consistent decimal places
            self.assertEqual(
                formatted_total_turnover, formatted_total_bet_amount,
                f"Total turnover is displayed incorrectly. Expected {formatted_total_bet_amount}, got {formatted_total_turnover}"
            )
            self.assertEqual(
                new_member_display_text, number_of_downline_users,
                f"New member display is displayed incorrectly. Expected {number_of_downline_users}, got {new_member_display_text}"
            )
        except Exception as e:
            self.logger.error(f"Error in test_01_VerifyRebateBalance_ProfilePage: {str(e)}")
            self.fail(f"Test failed: {str(e)}")

    def test_02_VerifyRebateDetail_LeaderboardPage(self):
        try:
            total_bet_per_tier, _, total_bet_amount, _, tier_2_users, _, _ = self.test_init.create_downline_rebate(
                tier_1_userID=self.userID, username=self.username, password=self.password
            )
            self.logger.info(f"Expected values - Total Bet Amount: {total_bet_amount}")
            self.logger.info(
                f"Expected Tier Bets: T1={total_bet_per_tier['1']}, T2={total_bet_per_tier['2']}, T3={total_bet_per_tier['3']}"
            )

            self.navigate_to_leaderboard()

            number_of_downline_users = len(tier_2_users)
            self.logger.info(f"Expected downline users: {number_of_downline_users}")

            # Wait for the element and get its text
            new_member_element = WebDriverWait(self.driver,
                                               10).until(EC.presence_of_element_located((By.ID, "effective_new_add")))
            new_member_text = new_member_element.text
            self.logger.info(f"Raw new member text: {new_member_text}")

            # Try to extract the number using regex first
            number_match = re.search(r'(\d+)', new_member_text)
            if number_match:
                new_member_display_text = int(number_match.group(1))
            else:
                # Fallback to the extract_numeric_value method
                new_member_display_text = self.extract_numeric_value(new_member_text)

            self.logger.info(f"Displayed new member count: {new_member_display_text}")

            self.assertEqual(
                number_of_downline_users, new_member_display_text,
                f"New member display mismatch. Expected: {number_of_downline_users}, Got: {new_member_display_text}"
            )

            t1_turnover = self.get_turnover_value("tier_item_0_amount")
            t2_turnover = self.get_turnover_value("tier_item_1_amount")
            t3_turnover = self.get_turnover_value("tier_item_2_amount")
            total_turnover = self.get_turnover_value("turnover_amount")

            self.assertEqual(
                t1_turnover, total_bet_per_tier['1'],
                f"T1 Turnover Value mismatch. Expected: {total_bet_per_tier['1']}, Got: {t1_turnover}"
            )
            self.assertEqual(
                t2_turnover, total_bet_per_tier['2'],
                f"T2 Turnover Value mismatch. Expected: {total_bet_per_tier['2']}, Got: {t2_turnover}"
            )
            self.assertEqual(
                t3_turnover, total_bet_per_tier['3'],
                f"T3 Turnover Value mismatch. Expected: {total_bet_per_tier['3']}, Got: {t3_turnover}"
            )
            self.assertEqual(
                total_turnover, total_bet_amount,
                f"Total Turnover Value mismatch. Expected: {total_bet_amount}, Got: {total_turnover}"
            )

            self.logger.info("Rebate leaderboard verification completed successfully")

        except Exception as e:
            self.logger.error(f"Error in test_02_VerifyRebateDetail_LeaderboardPage: {str(e)}")
            self.fail(f"Test failed: {str(e)}")

    def test_03_ContactCustomerService(self):
        try:
            self.navigate_to_leaderboard()
            contact_cs_button = self.find_element_by_id("contact_cs_button")
            contact_cs_button.click()
            self.logger.info("Successfully clicked on contact customer service button")
            self.check_contact_us("AI Whatsapp")

        except Exception as e:
            self.logger.error(f"Error in test_03_ContactCustomerService: {str(e)}")
            self.fail(f"Test failed: {str(e)}")

    def test_04_VerifyLeaderboardProgress_Valid(self):
        try:
            self.navigate_to_leaderboard()
            total_bet_per_tier, total_rebate_per_tier, total_bet_amount, total_rebate_amount, _, _, _ = self.test_init.create_downline_rebate(
                tier_1_userID=self.userID, username=self.username, password=self.password, valid_downline=True,
                valid_turnover=True
            )
            self.logger.info(f"Total Rebate Amount: {total_rebate_amount}")
            self.logger.info(f"Total Bet Amount: {total_bet_amount}")
            self.logger.info(f"Total Rebate Per Tier: {total_rebate_per_tier}")
            self.logger.info(f"Total Bet Per Tier: {total_bet_per_tier}")
            self.driver.refresh()
            self.check_milestone_progress(valid=True)
            self.click_navigation_bar("footer-profile-button")
            self.check_milestone_progress(valid=True)

        except Exception as e:
            self.logger.error(f"Error in test_04_VerifyLeaderboardProgress: {str(e)}")
            self.fail(f"Test failed: {str(e)}")

    def test_05_VerifyLeaderboardProgress_InvalidDownlineCount(self):
        try:
            self.navigate_to_leaderboard()
            total_bet_per_tier, total_rebate_per_tier, total_bet_amount, total_rebate_amount, _, _, _ = self.test_init.create_downline_rebate(
                tier_1_userID=self.userID, username=self.username, password=self.password, valid_downline=False,
                valid_turnover=True
            )
            self.logger.info(f"Total Rebate Amount: {total_rebate_amount}")
            self.logger.info(f"Total Bet Amount: {total_bet_amount}")
            self.logger.info(f"Total Rebate Per Tier: {total_rebate_per_tier}")
            self.logger.info(f"Total Bet Per Tier: {total_bet_per_tier}")
            self.driver.refresh()
            self.check_milestone_progress(valid=False)
            self.click_navigation_bar("footer-profile-button")
            self.check_milestone_progress(valid=False)

        except Exception as e:
            self.logger.error(f"Error in test_05_VerifyLeaderboardProgress_Invalid: {str(e)}")
            self.fail(f"Test failed: {str(e)}")

    def test_06_VerifyLeaderboardProgress_InvalidTotalTurnover(self):
        try:
            self.navigate_to_leaderboard()
            total_bet_per_tier, total_rebate_per_tier, total_bet_amount, total_rebate_amount, _, _, _ = self.test_init.create_downline_rebate(
                tier_1_userID=self.userID, username=self.username, password=self.password, valid_downline=True,
                valid_turnover=False
            )
            self.logger.info(f"Total Rebate Amount: {total_rebate_amount}")
            self.logger.info(f"Total Bet Amount: {total_bet_amount}")
            self.logger.info(f"Total Rebate Per Tier: {total_rebate_per_tier}")
            self.logger.info(f"Total Bet Per Tier: {total_bet_per_tier}")
            self.driver.refresh()
            self.check_milestone_progress(valid=False)
            self.click_navigation_bar("footer-profile-button")
            self.check_milestone_progress(valid=False)

        except Exception as e:
            self.logger.error(f"Error in test_06_VerifyLeaderboardProgress_InvalidTotalTurnover: {str(e)}")
            self.fail(f"Test failed: {str(e)}")

    def test_07_LeaderBoardTnc(self):
        try:
            self.navigate_to_leaderboard()
            tnc_button = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.ID, "reward-info-button")))
            tnc_button.click()

            leaderboard_tnc_api = CREDENTIALS.get("LeaderBoardTnc")
            if not leaderboard_tnc_api:
                self.fail("LeaderBoardTnc API URL is missing in CREDENTIALS")

            self.logger.info(f"Making request to LeaderBoardTnc API: {leaderboard_tnc_api}")

            headers = {
                "Language": self.language
            }
            try:
                response = requests.get(leaderboard_tnc_api, headers=headers)
                response.raise_for_status()
            except requests.RequestException as e:
                self.fail(f"Failed to fetch contact information: {str(e)}")

            # Parse JSON response
            try:
                leaderboard_tnc_data = response.json()
                self.logger.info(f"Raw API response: {leaderboard_tnc_data}")
            except json.JSONDecodeError:
                self.fail("Failed to parse contact information response as JSON")

            # Extract TnC content from API
            value_data = leaderboard_tnc_data.get("data", {}).get("tnc", "")

            # Process API data (if it's a string, split into numbered items)
            api_tnc_items = []
            if isinstance(value_data, str):
                self.logger.info("TnC data is a string, parsing by newlines...")

                # Extract numbered sections
                numbered_items = re.split(r'(\d+\.\s+)', value_data)
                current_item = ""
                for i, part in enumerate(numbered_items):
                    if re.match(r'^\d+\.\s+$', part):
                        if current_item.strip():
                            api_tnc_items.append(current_item.strip())
                        current_item = part
                    else:
                        current_item += part
                if current_item.strip():
                    api_tnc_items.append(current_item.strip())

                if not api_tnc_items:
                    self.logger.info("Falling back to simple newline splitting...")
                    clean_tnc = re.sub(r'\s*\n\s*\n\s*', '\n\n', value_data)
                    api_tnc_items = [item.strip() for item in clean_tnc.split('\n\n') if item.strip()]

            elif isinstance(value_data, list):
                api_tnc_items = value_data
                self.logger.info(f"TnC data is already a list with {len(api_tnc_items)} items")

            for i, item in enumerate(api_tnc_items):
                self.logger.info(f"API TnC item {i+1}: {item}")

            tnc_list = WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "ul.MuiList-padding"))
            )
            ui_tnc_items = tnc_list.find_elements(By.CSS_SELECTOR, "li.MuiListItem-root")
            self.logger.info(f"Found {len(ui_tnc_items)} TnC items in UI")

            ui_tnc_texts = []
            for li in ui_tnc_items:
                p_element = li.find_element(By.CSS_SELECTOR, "p.MuiTypography-body1")
                text = p_element.text.strip()
                ui_tnc_texts.append(text)
                self.logger.info(f"UI TnC item: {text}")

            api_combined_text = " ".join(api_tnc_items)
            ui_combined_text = " ".join(ui_tnc_texts)

            api_normalized = self.normalize_text(api_combined_text)
            ui_normalized = self.normalize_text(ui_combined_text)

            self.logger.info(f"Normalized API text: {api_normalized}")
            self.logger.info(f"Normalized UI text: {ui_normalized}")

            self.assertEqual(api_normalized, ui_normalized, "TnC content does not match exactly.")
            self.logger.info("API and UI TnC content match EXACTLY - PASS")

        except Exception as e:
            self.logger.error(f"Error in test_07_LeaderBoardTnc: {str(e)}")
            self.fail(f"Test failed: {str(e)}")

    def test_08_CheckRanking(self):
        try:
            self.navigate_to_leaderboard()
            self.logger.info("Step 1: Navigating to leaderboard to check ranking")

            expected_avatar_url = self.get_profile_avatar_url()
            if not expected_avatar_url:
                self.fail("Could not get profile avatar URL")
            self.logger.info(f"Expected avatar URL: {expected_avatar_url}")

            rankings = self.collect_leaderboard_rankings()
            if not rankings:
                self.fail("No rankings found on leaderboard")

            self.logger.info(f"Step 2: Collected {len(rankings)} rankings from leaderboard")

            _, _, total_bet_amount, _, tier_2_users, _, _ = self.test_init.create_downline_rebate(
                tier_1_userID=self.userID, username=self.username, password=self.password, valid_downline=True,
                valid_turnover=True
            )
            self.logger.info(f"Step 3: User's total bet amount: {total_bet_amount}")

            total_bet_amount_float = float(total_bet_amount)

            turnover_values = []
            for rank in rankings:
                turnover_values.append(rank["turnover"])
                self.logger.info(f"Position {rank['position']}: {rank['name']} has turnover {rank['turnover']}")

            sorted_turnovers = sorted(turnover_values, reverse=True)
            self.logger.info(f"Sorted turnover values (descending): {sorted_turnovers}")

            # Determine ranking position
            user_ranking = None
            for idx, turnover in enumerate(sorted_turnovers, start=1):
                if total_bet_amount_float >= turnover:
                    user_ranking = idx
                    break

            # If user's turnover is lower than all rankings, they would be last
            if user_ranking is None:
                user_ranking = len(sorted_turnovers) + 1

            self.logger.info(f"User should be ranked: {user_ranking}")

            self.logger.info("Checking if user's turnover matches any existing ranking:")

            time.sleep(10)
            check_ranking_api = CREDENTIALS['CheckRanking']
            response = requests.get(check_ranking_api)
            if response.status_code != 200:
                self.fail(f"Failed to check ranking: {response.status_code}")
            else:
                self.logger.info("Ranking checked successfully")
                response_data = response.json()
                updated_rankings = response_data.get("data", {}).get("leaderboard", [])
                self.logger.info(f"Updated rankings: {updated_rankings}")

            if not updated_rankings:
                self.fail("No rankings found on leaderboard after refresh")

            exact_match_found = False
            if updated_rankings:
                user_rank = updated_rankings[user_ranking - 1]
                if (
                    user_rank["name"] == self.username and user_rank["valid_members"] == len(tier_2_users)
                    and user_rank["total_valid_turnover"] == total_bet_amount_float
                    and user_rank["avatar"] == expected_avatar_url
                ):
                    exact_match_found = True
                    self.logger.info("MATCH FOUND!!")
                    self.logger.info(f"Avatar URL matches: {user_rank['avatar']}")
                else:
                    self.logger.error(f"Match failed:")
                    self.logger.error(f"Expected username: {self.username}, got: {user_rank['name']}")
                    self.logger.error(f"Expected valid members: {len(tier_2_users)}, got: {user_rank['valid_members']}")
                    self.logger.error(
                        f"Expected turnover: {total_bet_amount_float}, got: {user_rank['total_valid_turnover']}"
                    )
                    self.logger.error(f"Expected avatar: {expected_avatar_url}, got: {user_rank['avatar']}")

            self.assertTrue(
                exact_match_found,
                "User's ranking details (name, members, turnover, or avatar) do not match expected values"
            )

        except Exception as e:
            self.logger.error(f"Error in test_08_CheckRanking: {str(e)}")
            self.fail(f"Test failed: {str(e)}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    unittest.main()
