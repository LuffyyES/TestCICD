import unittest
import time
import logging
import random
import requests
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from selenium.webdriver.support import expected_conditions as EC
from config.constant import CREDENTIALS, LANGUAGE_SETTINGS
from tests.authentication_test.base_test import BaseTest
from tests.test_init import TestInit
from tests.test_live_agent import TestLiveAgent
from tests.transaction_history_test.test_history import TestHistory


class TestRebate(BaseTest):

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

    def tearDown(self):
        if hasattr(self, "driver"):
            self.driver.quit()

    def navigate_to_rebate_record(self, tab_name):
        rebate_section = self.driver.find_element(By.ID, "home-rebate-button")
        rebate_section.click()
        if self.browser == "firefox":
            self.wait_for_page_ready()
        self.wait_for_page_ready()
        match tab_name:
            case "total_rebate":
                rebate_record_section = self.driver.find_element(By.ID, "wallet-tab-total")
                rebate_record_section.click()
            case "record_rebate":
                rebate_record_section = self.driver.find_element(By.ID, "wallet-tab-history")
                rebate_record_section.click()
            case "agent_record":
                rebate_record_section = self.driver.find_element(By.ID, "wallet-tab-agentRecord")
                rebate_record_section.click()

    def collect_rebate_ui_data(self):
        try:
            WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, "t1_paper")))

            turnover_values = {
                "tier1": self.driver.find_element(By.ID, "t1_turnover_value").text,
                "tier2": self.driver.find_element(By.ID, "t2_turnover_value").text,
                "tier3": self.driver.find_element(By.ID, "t3_turnover_value").text,
                "total": self.driver.find_element(By.ID, "total_turnover_value").text
            }

            rebate_values = {
                "tier1": self.driver.find_element(By.ID, "t1_rebate_value").text,
                "tier2": self.driver.find_element(By.ID, "t2_rebate_value").text,
                "tier3": self.driver.find_element(By.ID, "t3_rebate_value").text
            }

            try:
                total_rebate_elements = self.driver.find_elements(By.ID, "total_rebate_value")
                total_rebate_value = total_rebate_elements[-1].text
                if total_rebate_value.strip() == "MYR" and len(total_rebate_elements) > 1:
                    total_rebate_value = f"MYR {total_rebate_elements[1].text}"
            except Exception as e:
                self.logger.warning(f"Error getting total rebate value: {str(e)}")
                total_rebate_value = "MYR 0.00"

            rebate_values["total"] = total_rebate_value

            selected_month = self.driver.find_element(By.ID, "month-select").text

            clean_values = {
                "turnover": {},
                "rebate": {}
            }

            for tier, value in turnover_values.items():
                try:
                    self.logger.info(f"Turnover Value: {value}")
                    clean_values["turnover"][tier] = self.test_init.clean_monetary_value(value)
                except ValueError as e:
                    self.logger.warning(f"Could not parse turnover value for {tier}: {value}. Error: {str(e)}")
                    clean_values["turnover"][tier] = 0.0

            for tier, value in rebate_values.items():
                try:
                    self.logger.info(f"Rebate Value: {value}")
                    clean_values["rebate"][tier] = self.test_init.clean_monetary_value(value)
                except ValueError as e:
                    self.logger.warning(f"Could not parse rebate value for {tier}: {value}. Error: {str(e)}")
                    clean_values["rebate"][tier] = 0.0

            return {
                "raw_values": {
                    "turnover": turnover_values,
                    "rebate": rebate_values,
                    "month": selected_month
                },
                "clean_values": clean_values
            }

        except Exception as e:
            self.logger.error(f"Error collecting UI data: {str(e)}")
            raise e

    def verify_month_in_dropdown(
        self, current_month, total_bet_per_tier, total_rebate_per_tier, total_bet_amount, total_rebate_amount
    ):
        try:
            choose_month = self.driver.find_element(By.ID, "month-select")
            choose_month.click()
            time.sleep(1)

            date_options = self.driver.find_elements(By.XPATH, "//li[@role='option']")
            options_count = len(date_options)

            self.driver.find_element(By.TAG_NAME, "body").click()
            time.sleep(1)

            for i in range(options_count):
                choose_month = self.driver.find_element(By.ID, "month-select")
                choose_month.click()
                time.sleep(1)

                fresh_options = self.driver.find_elements(By.XPATH, "//li[@role='option']")
                current_option = fresh_options[i]

                data_value = current_option.get_attribute("data-value")
                is_current_month = current_month in data_value
                self.logger.info(f"Current month: {current_month}")
                self.logger.info(f"Option data-value: {data_value}")
                self.logger.info(f"Is current month: {is_current_month}")

                try:
                    current_option.click()
                except Exception as e:
                    self.driver.execute_script("arguments[0].click();", current_option)
                    if "ElementClickInterceptedException" in str(e):
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", current_option)
                        time.sleep(1)
                        current_option.click()
                time.sleep(3)

                ui_data = self.collect_rebate_ui_data()
                selected_month = ui_data["raw_values"]["month"]
                self.logger.info(f"Selected month: {selected_month}")

                tier_mapping = {
                    "1": "tier1",
                    "2": "tier2",
                    "3": "tier3"
                }

                if is_current_month:
                    self.logger.info(f"Verifying data for current month: {selected_month}")

                    for api_tier, ui_tier in tier_mapping.items():
                        expected_turnover = float(total_bet_per_tier[api_tier])
                        expected_rebate = float(total_rebate_per_tier[api_tier])

                        self.assertEqual(
                            expected_turnover, ui_data["clean_values"]["turnover"][ui_tier],
                            f"Turnover mismatch for tier {api_tier}: Expected {expected_turnover}, got {ui_data['clean_values']['turnover'][ui_tier]}"
                        )
                        self.assertTrue(
                            abs(round(expected_rebate, 2) - round(ui_data["clean_values"]["rebate"][ui_tier], 2)) <= 0.01,
                            f"Rebate mismatch for tier {api_tier}: Expected {expected_rebate}, got {ui_data['clean_values']['rebate'][ui_tier]}"
                        )

                    self.assertEqual(
                        float(total_bet_amount), ui_data["clean_values"]["turnover"]["total"],
                        f"Total turnover mismatch: Expected {float(total_bet_amount)}, got {ui_data['clean_values']['turnover']['total']}"
                    )

                    self.assertEqual(
                        float(total_rebate_amount), ui_data["clean_values"]["rebate"]["total"],
                        f"Total rebate mismatch: Expected {float(total_rebate_amount)}, got {ui_data['clean_values']['rebate']['total']}"
                    )

                    self.logger.info("All rebate values verified successfully for current month")
                else:
                    self.logger.info(f"Verifying zero values for non-current month: {selected_month}")

                    for _, ui_tier in tier_mapping.items():
                        self.assertEqual(
                            0, ui_data["clean_values"]["turnover"][ui_tier],
                            f"Turnover for {ui_tier} should be 0 for non-current month, got {ui_data['clean_values']['turnover'][ui_tier]}"
                        )
                        self.assertEqual(
                            0, ui_data["clean_values"]["rebate"][ui_tier],
                            f"Rebate for {ui_tier} should be 0 for non-current month, got {ui_data['clean_values']['rebate'][ui_tier]}"
                        )
                    self.assertEqual(
                        0, ui_data["clean_values"]["turnover"]["total"],
                        f"Total turnover should be 0 for non-current month, got {ui_data['clean_values']['turnover']['total']}"
                    )
                    self.assertEqual(
                        0, ui_data["clean_values"]["rebate"]["total"],
                        f"Total rebate should be 0 for non-current month, got {ui_data['clean_values']['rebate']['total']}"
                    )

                    self.logger.info("All values verified as zero for non-current month")

        except Exception as e:
            self.logger.error(f"Error in verify_month_in_dropdown: {str(e)}")
            raise e

    def get_table_data(self, users, api_url, record_type):
            try:
                self.logger.info(f"Checking {record_type} records for {len(users)} users")
                
                max_retries = 3
                retry_count = 0
                token = None
                
                while retry_count < max_retries:
                    try:
                        token = self.login(self.username, self.password)
                        if token:
                            break
                    except Exception as e:
                        retry_count += 1
                        self.logger.warning(f"Login attempt {retry_count} failed: {str(e)}")
                        if retry_count < max_retries:
                            time.sleep(2) 
                        else:
                            self.logger.error("Failed to login after maximum retries")
                            return None, None  
                
                if not token:
                    self.logger.error("Failed to get token")
                    return None, None

                headers = {
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                    "language": self.language
                }

                max_api_retries = 3
                api_retry_count = 0
                rebate_api_record = None
                
                while api_retry_count < max_api_retries:
                    try:
                        rebate_api_record_response = requests.get(api_url, headers=headers, timeout=30)
                        if rebate_api_record_response.status_code == 200:
                            rebate_api_record = rebate_api_record_response.json()
                            break
                        elif rebate_api_record_response.status_code == 524:
                            api_retry_count += 1
                            self.logger.warning(f"Server timeout (524) on attempt {api_retry_count}")
                            if api_retry_count < max_api_retries:
                                time.sleep(5)  
                            else:
                                self.logger.error("Server timeout after maximum retries")
                                return None, None
                        else:
                            self.logger.error(f"API request failed with status code: {rebate_api_record_response.status_code}")
                            return None, None
                    except Exception as e:
                        api_retry_count += 1
                        self.logger.warning(f"API request attempt {api_retry_count} failed: {str(e)}")
                        if api_retry_count < max_api_retries:
                            time.sleep(2)
                        else:
                            self.logger.error("Failed to get API records after maximum retries")
                            return None, None

                if not rebate_api_record:
                    return None, None

                self.logger.info(f"API Response: {rebate_api_record}")

                # Get data path based on record type
                data_path = 'data' if record_type == 'bet' or record_type == 'rebate' else 'list'
                api_records = rebate_api_record.get('data', {}).get(data_path, [])
                self.logger.info(f"API returned {len(api_records)} records")
                self.logger.info(f"API records: {api_records}")

                # Wait for table to load with increased timeout
                try:
                    WebDriverWait(self.driver, 20).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "table.MuiTable-root"))
                    )
                except Exception as e:
                    self.logger.error(f"Timeout waiting for table to load: {str(e)}")
                    return None, None

                # Get all rows
                all_rows = self.driver.find_elements(By.CSS_SELECTOR, "tr.MuiTableRow-root")
                if not all_rows:
                    self.logger.error("No rows found in table")
                    return None, None
                    
                header_row = all_rows[0]
                record_rows = all_rows[1:]

                self.logger.info(f"Found {len(record_rows)} data rows in the table")

                # Get headers
                header_cells = header_row.find_elements(By.CSS_SELECTOR, "th.MuiTableCell-head")
                column_headers = [cell.text.strip() for cell in header_cells]
                self.logger.info(f"Table Headers: {column_headers}")

                return api_records, record_rows

            except Exception as e:
                self.logger.error(f"Error in get_table_data: {str(e)}")
                return None, None

    def check_downline_record(self, users, api_url, outofrange=False):
        try:
            self.logger.info(f"Checking downline records for {len(users)} users")
            api_records, record_rows = self.get_table_data(users, api_url, 'downline')

            all_verified = True
            max_to_check = len(record_rows)

            self.logger.info("\n======= ROW BY ROW COMPARISON =======")

            for i in range(max_to_check):
                row = record_rows[i]
                self.logger.info("Row: " + str(row))

                try:
                    cells = row.find_elements(By.CSS_SELECTOR, "td.MuiTableCell-body")
                    self.logger.info("Cells: " + str(len(cells)))
                    
                    found_match = False
                    validations = []
                    current_match = True

                    if len(api_records) > 0:
                        row_data = {}

                        # Extract cell values first
                        for j, cell in enumerate(cells):
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", cell)
                            cell_text = cell.text.strip()

                            match j:
                                case 0:
                                    row_data["username"] = cell_text
                                    self.logger.info("Username: " + row_data['username'])
                                case 1:
                                    row_data["name"] = cell_text
                                    self.logger.info("Name: " + row_data['name'])
                                case 2:
                                    row_data["tier"] = cell_text
                                    self.logger.info("Tier: " + row_data['tier'])
                                case 8:
                                    turnover_value = float(cell_text.replace("MYR", "").strip())
                                    try:
                                        row_data["turnover"] = str(
                                            Decimal(turnover_value).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)
                                        )
                                        self.logger.info("Turnover: " + row_data['turnover'])
                                    except Exception as e:
                                        self.logger.error("Error in turnover: " + str(e))
                                        row_data["turnover"] = "0.00"
                                        self.logger.info("Turnover: " + row_data['turnover'])
                                case 9:
                                    rebate_value = float(cell_text.replace("MYR", "").strip())
                                    row_data["rebate"] = str(
                                        Decimal(rebate_value).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)
                                    )
                                    self.logger.info("Rebate: " + row_data['rebate'])

                        for user in users[:]: 
                            username = user.get("username", "")
                            user_id = user.get("user_id", "")
                            tier_level = user.get("tier_level", "")
                            rebate_percentage = user.get("rebate_percentage", 0)
                            
                            bet_amount = str(Decimal(str(user.get("bet_amount", 0))).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP))
                            rebate_amount = str(Decimal(str(user.get("rebate_amount", "0.00"))).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP))

                            self.logger.info("Username: " + username)
                            self.logger.info("User ID: " + str(user_id))
                            self.logger.info("Tier level: " + str(tier_level))
                            self.logger.info("Rebate percentage: " + str(rebate_percentage))
                            self.logger.info("Bet amount: " + bet_amount)

                            self.logger.info("\n--- Comparing User #" + str(i+1) + " to Row #" + str(i+1) + " ---")
                            self.logger.info("Expected User: " + username + " (ID: " + str(user_id) + ", Tier: " + str(tier_level) + ")")

                            if row_data.get("username") == username:
                                validations.append(("Username", True, row_data.get("username") + " = " + username))
                            else:
                                validations.append(("Username", False, row_data.get("username") + " ≠ " + username))
                                all_verified = False

                            if outofrange:
                                expected_turnover = "0.00"
                            else:
                                expected_turnover = str(Decimal(str(bet_amount)).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP))
                            actual_turnover = str(Decimal(str(row_data.get("turnover", "0.00"))).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP))

                            if Decimal(actual_turnover) == Decimal(expected_turnover):
                                validations.append(("Turnover", True, actual_turnover + " = " + expected_turnover))
                            else:
                                validations.append(("Turnover", False, actual_turnover + " ≠ " + expected_turnover))
                                all_verified = False

                            if outofrange:
                                expected_rebate = "0.00"
                            else:
                                expected_rebate = str(Decimal(str(rebate_amount)).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP))
                            actual_rebate = str(Decimal(str(row_data.get("rebate", "0.00"))).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP))

                            if abs(Decimal(actual_rebate) - Decimal(expected_rebate)) <= Decimal('0.01'):
                                validations.append(("Rebate", True, actual_rebate + " = " + expected_rebate))
                            else:
                                validations.append(("Rebate", False, actual_rebate + " ≠ " + expected_rebate))
                                all_verified = False

                            self.logger.info("Validation Results:")
                            for field, success, message in validations:
                                status = "✓" if success else "✗"
                                self.logger.info(status + " " + field + ": " + message)

                            if current_match:
                                found_match = True
                                users.remove(user)  
                                break  

                        if not found_match:
                            self.logger.warning("✗ No matching user found for row " + str(i+1))
                            all_verified = False

                    else:
                        if cells[0].text == LANGUAGE_SETTINGS[self.language]["rebate"]["no_record"]:
                            self.logger.info("No records found in UI as expected (date out of range)")
                            return True

                except Exception as e:
                    self.logger.error("Error comparing row " + str(i+1) + ": " + str(e))
                    all_verified = False

            if all_verified:
                self.logger.info("✓ All " + str(max_to_check) + " rows matched with users")
            else:
                self.logger.warning("✗ Some rows could not be matched with users")

            return all_verified

        except Exception as e:
            self.logger.error("Error in check_bet_record: " + str(e))
            return False

    def check_agent_record(self, users, api_url, outofrange=False):
        try:
            self.logger.info(f"Checking downline records for {len(users)} users")
            api_records, record_rows = self.get_table_data(users, api_url, 'agent')

            all_verified = True
            max_to_check = len(record_rows)

            self.logger.info("\n======= ROW BY ROW COMPARISON =======")

            for i in range(max_to_check):
                user = users[i]
                self.logger.info(f"User: {user}")
                row = record_rows[i]
                self.logger.info(f"Row: {row}")

                username = user.get("username", "")
                rebate_percentage = user.get("rebate_percentage", 0)
                bet_amount = "{:.2f}".format(user.get("bet_amount", 0))
                parent = user.get("parent", "")
                self.logger.info(f"Username: {username}")

                try:
                    cells = row.find_elements(By.CSS_SELECTOR, "td.MuiTableCell-body")
                                     
                    validations = []

                    if len(api_records) > 0:

                        row_data = {}

                        for j, cell in enumerate(cells):
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", cell)
                            cell_text = cell.text.strip()

                            match j:
                                case 0:
                                    row_data["username"] = cell_text
                                    self.logger.info(f"Username: {row_data['username']}")
                                case 1:
                                    row_data["parent"] = cell_text
                                    self.logger.info(f"Parent: {row_data['parent']}")
                                case 6:
                                    turnover_value = cell_text.split("MYR")[1].replace(",", "").strip()
                                    row_data["turnover"] = str(
                                        Decimal(turnover_value).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)
                                    )
                                    self.logger.info(f"Turnover: {row_data['turnover']}")
                                case 7:
                                    rebate_value = cell_text.split("MYR")[1].replace(",", "").strip()
                                    row_data["rebate"] = str(
                                        Decimal(rebate_value).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)
                                    )
                                    self.logger.info(f"Rebate: {row_data['rebate']}")

                        self.logger.info(f"Row Data: {row_data}")

                        if row_data.get("username") == username:
                            validations.append(("Username", True, f"{row_data.get('username')} = {username}"))
                        else:
                            validations.append(("Username", False, f"{row_data.get('username')} ≠ {username}"))
                            all_verified = False
                            
                        if row_data.get("parent") == parent:
                            validations.append(("Parent", True, f"{row_data.get('parent')} = {parent}"))
                        else:
                            validations.append(("Parent", False, f"{row_data.get('parent')} ≠ {parent}"))
                            all_verified = False

                        if outofrange:
                            expected_turnover = "0.00"
                        else:
                            expected_turnover = str(
                                Decimal(str(bet_amount)).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)
                            )
                        actual_turnover = row_data.get("turnover")
                        if actual_turnover == expected_turnover:
                            validations.append(("Turnover", True, f"{actual_turnover} = {expected_turnover}"))
                        else:
                            validations.append(("Turnover", False, f"{actual_turnover} ≠ {expected_turnover}"))
                            all_verified = False

                        if outofrange:
                            expected_rebate = "0.00"
                        else:
                            expected_rebate = Decimal(bet_amount) * (Decimal(rebate_percentage) / Decimal(100))
                            expected_rebate = str(expected_rebate.quantize(Decimal('0.00'), rounding=ROUND_HALF_UP))
                        actual_rebate = row_data.get("rebate")
                        if actual_rebate == expected_rebate:
                            validations.append(("Rebate", True, f"{actual_rebate} = {expected_rebate}"))
                        else:
                            validations.append(("Rebate", False, f"{actual_rebate} ≠ {expected_rebate}"))
                            all_verified = False

                        self.logger.info("Validation Results:")
                        for field, success, message in validations:
                            status = "✓" if success else "✗"
                            self.logger.info(f"{status} {field}: {message}")
                    else:
                        self.logger.info("No records")
                        if outofrange:
                            if cells[0].text == LANGUAGE_SETTINGS[self.language]["history"]["no_record"]:
                                self.logger.info(f"No records found in UI as expected (date out of range)")
                                validations.append(
                                    ("No records", True, f"No records found in UI as expected (date out of range)")
                                )

                except Exception as e:
                    self.logger.error(f"Error comparing user {username} to row {i+1}: {str(e)}")
                    all_verified = False

            if all_verified:
                self.logger.info(f"all verified: {all_verified}")
                self.logger.info(f"✓ All {max_to_check} users verified successfully against table rows")
                return True
            else:
                self.logger.warning("✗ Some verifications failed - see detailed logs above")
                return False

        except Exception as e:
            self.logger.error(f"Error in check_downline_record: {str(e)}")
            return False

    def check_bet_record(self, users, api_url):
        try:
            self.logger.info(f"Checking Bet records for {len(users)} users")
            api_records, record_rows = self.get_table_data(users, api_url, 'bet')
            all_verified = True
            max_to_check = len(record_rows)

            self.logger.info("\n======= ROW BY ROW COMPARISON =======")

            for i in range(max_to_check):
                row = record_rows[i]
                self.logger.info(f"Row: {row}")

                try:
                    cells = row.find_elements(By.CSS_SELECTOR, "td.MuiTableCell-body")
                    validations = []
                    if len(api_records) > 0:
                        row_data = {}

                        for j, cell in enumerate(cells):
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", cell)
                            cell_text = cell.text.strip()

                            match j:
                                case 2:
                                    row_data["username"] = cell_text
                                    self.logger.info(f"Username: {row_data['username']}")
                                case 4:
                                    row_data["bet_time"] = cell_text
                                    self.logger.info(f"Bet times: {row_data['bet_time']}")
                                case 5:
                                    bet_amount_value = cell_text.split("MYR")[1].replace(",", "").strip()
                                    row_data["bet_amount"] = str(
                                        Decimal(bet_amount_value).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)
                                    )
                                    self.logger.info(f"Bet amount: {row_data['bet_amount']}")

                        found_match = False
                        current_match = True
                        for user in users[:]: 
                            username = user.get("username", "")
                            bet_time = user.get("timestamp", "")
                            bet_amount = "{:.2f}".format(user.get("bet_amount", 0))

                            self.logger.info(f"\n--- Comparing Row #{i+1} with User {username} ---")

                            if row_data.get("username") == username:
                                validations.append(("Username", True, f"{row_data.get('username')} = {username}"))
                            else:
                                validations.append(("Username", False, f"{row_data.get('username')} ≠ {username}"))
                                continue  

                            expected_bet_amount = str(
                                Decimal(str(bet_amount)).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)
                            )
                            actual_bet_amount = row_data.get("bet_amount")
                            if actual_bet_amount == expected_bet_amount:
                                validations.append(("Bet Amount", True, f"{actual_bet_amount} = {expected_bet_amount}"))
                            else:
                                validations.append(
                                    ("Bet Amount", False, f"{actual_bet_amount} ≠ {expected_bet_amount}")
                                )
                                current_match = False

                            expected_bet_time = datetime.strptime(bet_time, "%d/%m/%Y %I:%M %p")
                            formatted_bet_time = expected_bet_time.strftime(
                                "%Y-%m-%d %H:%M"
                            )  
                            actual_bet_time = datetime.strptime(row_data.get("bet_time"), "%Y-%m-%d %H:%M:%S").strftime(
                                "%Y-%m-%d %H:%M"
                            )  
                            if actual_bet_time == formatted_bet_time:
                                validations.append(("Bet Time", True, f"{actual_bet_time} = {formatted_bet_time}"))
                            else:
                                validations.append(("Bet Time", False, f"{actual_bet_time} ≠ {formatted_bet_time}"))
                                current_match = False

                            self.logger.info("Validation Results:")
                            for field, success, message in validations:
                                status = "✓" if success else "✗"
                                self.logger.info(f"{status} {field}: {message}")

                            if current_match:
                                found_match = True
                                users.remove(user)  
                                break 

                        if not found_match:
                            self.logger.warning(f"✗ No matching user found for row {i+1}")
                            all_verified = False

                    else:
                        if cells[0].text == LANGUAGE_SETTINGS[self.language]["rebate"]["no_record"]:
                            self.logger.info(f"No records found in UI as expected (date out of range)")
                            return True

                except Exception as e:
                    self.logger.error(f"Error comparing row {i+1}: {str(e)}")
                    all_verified = False

            if all_verified:
                self.logger.info(f"✓ All {max_to_check} rows matched with users")
            else:
                self.logger.warning("✗ Some rows could not be matched with users")

            return all_verified

        except Exception as e:
            self.logger.error(f"Error in check_bet_record: {str(e)}")
            return False

    def check_rebate_record(self, current_time, users, api_url, outofrange=False):
        try:
            self.logger.info(f"Checking downline records for {len(users)} users")
            api_records, record_rows = self.get_table_data(users, api_url, 'rebate')
            self.logger.info(f"api_records: {api_records}")
            self.logger.info(f"length of api_records: {len(api_records)}")
            self.logger.info(f"record_rows: {record_rows}")

            all_verified = True
            max_to_check = len(record_rows)

            self.logger.info("\n======= ROW BY ROW COMPARISON =======")

            for i in range(max_to_check):
                user = users[i]
                self.logger.info(f"User: {user}")
                row = record_rows[i]
                self.logger.info(f"Row: {row}")

                username = user.get("username", "")
                user_id = user.get("user_id", "")
                tier_level = user.get("tier_level", "")
                rebate_percentage = user.get("rebate_percentage", 0)
                bet_amount = "{:.2f}".format(user.get("bet_amount", 0))
                self.logger.info(f"Username: {username}")
                self.logger.info(f"User ID: {user_id}")
                self.logger.info(f"Tier level: {tier_level}")
                self.logger.info(f"Rebate percentage: {rebate_percentage}")
                self.logger.info(f"Bet amount: {bet_amount}")

                self.logger.info(f"\n--- Comparing User #{i+1} to Row #{i+1} ---")
                self.logger.info(f"Expected User: {username} (ID: {user_id}, Tier: {tier_level})")

                try:
                    cells = row.find_elements(By.CSS_SELECTOR, "td.MuiTableCell-body")
                    validations = []
                    self.logger.info(f"length of api_records: {len(api_records)}")
                    if len(api_records) > 0:
                        self.logger.info("more than 0")

                        row_data = {}

                        for j, cell in enumerate(cells):
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", cell)
                            cell_text = cell.text.strip()
                            

                            match j:
                                case 0:
                                    row_data["date"] = cell_text
                                    self.logger.info(f"Date: {row_data['date']}")
                                case 1:
                                    row_data["from_user"] = cell_text
                                    self.logger.info(f"From User: {row_data['from_user']}")
                                case 2:
                                    row_data["tier_level"] = cell_text
                                    self.logger.info(f"Tier Level: {row_data['tier_level']}")
                                case 3:
                                    rebate_amount = cell_text.split("MYR")[1].replace(",", "").strip()
                                    row_data["rebate_amount"] = str(
                                        Decimal(rebate_amount).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)
                                    )
                                    row_data["amount"] = cell_text
                                    self.logger.info(f"Rebate amount: {row_data['rebate_amount']}")

                        self.logger.info(f"Row Data: {row_data}")

                        if row_data.get("date") == current_time:
                            validations.append(("Date", True, f"{row_data.get('date')} = {current_time}"))
                        else:
                            validations.append(("Date", False, f"{row_data.get('date')} ≠ {current_time}"))
                            all_verified = False
                            
                        if row_data.get("tier_level") == tier_level:
                            validations.append(("From User", True, f"{row_data.get("tier_level")} = {tier_level}"))
                        else:
                            validations.append(("From User", False, f"{row_data.get("tier_level")} ≠ {tier_level}"))
                            all_verified = False

                        expected_rebate = Decimal(bet_amount) * (Decimal(rebate_percentage) / Decimal(100))
                        expected_rebate = str(expected_rebate.quantize(Decimal('0.00'), rounding=ROUND_HALF_UP))
                        actual_rebate = row_data.get("rebate_amount")
                        if actual_rebate == expected_rebate:
                            validations.append(("Rebate", True, f"{actual_rebate} = {expected_rebate}"))
                        else:
                            validations.append(("Rebate", False, f"{actual_rebate} ≠ {expected_rebate}"))
                            all_verified = False
                            
                        self.logger.info("Validation Results:")
                        for field, success, message in validations:
                            status = "✓" if success else "✗"
                            self.logger.info(f"{status} {field}: {message}")
                    else:
                        self.logger.info("No Records")
                        if outofrange:
                            if cells[0].text == LANGUAGE_SETTINGS[self.language]["rebate"]["no_record"]:
                                self.logger.info(f"No records found in UI as expected (date out of range)")
                                validations.append(
                                    ("No records", True, f"No records found in UI as expected (date out of range)")
                                )

                except Exception as e:
                    self.logger.error(f"Error comparing user {username} to row {i+1}: {str(e)}")
                    all_verified = False

            if all_verified:
                self.logger.info(f"all verified: {all_verified}")
                self.logger.info(f"✓ All {max_to_check} users verified successfully against table rows")
                return True
            else:
                self.logger.warning("✗ Some verifications failed - see detailed logs above")
                return False

        except Exception as e:
            self.logger.error(f"Error in check_downline_record: {str(e)}")
            return False
        
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

    def check_rebate_percentage(self,provider_id,tier_level):

        check_rebate_percentage = CREDENTIALS['CheckRebatePercentage']
        response = requests.get(check_rebate_percentage)
        if response.status_code != 200:
            self.fail(f"Failed to check rebate percentage: {response.status_code}")

        rebate_data = response.json()
        for provider in rebate_data.get("data", []):
            if provider_id == provider.get("provider_id"):
                rebate_percentage = provider.get("rebate_percentage", {}).get(tier_level, 0)
                self.logger.info(f"rebate_percentage: {rebate_percentage}")
                return rebate_percentage
        return 0
        
    def test_01_VerifyRebateAmount_ValidMonth(self):
        try:
            self.navigate_to_rebate_record("total_rebate")
            total_bet_per_tier, total_rebate_per_tier, total_bet_amount, total_rebate_amount, current_month, _, _ = self.test_init.create_downline_rebate(
                tier_1_userID = self.userID,
                username=self.username,
                password=self.password,
                check_filter_month=True
            )

            self.driver.refresh()
            time.sleep(3)

            try:
                self.verify_month_in_dropdown(
                    current_month, total_bet_per_tier, total_rebate_per_tier, total_bet_amount, total_rebate_amount
                )
            except Exception as e:
                self.logger.error(f"Error in verify_month_in_dropdown: {str(e)}")
                self.fail(f"Test failed: {str(e)}")

        except Exception as e:
            self.logger.error(f"Error in test_01_VerifyRebateAmount: {str(e)}")
            self.fail(f"Test failed: {str(e)}")

    def test_02_ApproveRebate(self):
        try:
            driver = self.driver
            self.navigate_to_rebate_record("total_rebate")
            self.test_init.create_downline_rebate(tier_1_userID=self.userID, username=self.username, password=self.password)
            driver.refresh()
            
            initial_balance = self.extract_total_balance()
            time.sleep(1)
            
            self.scrollToSection("total_rebate_value")
            total_rebate_elements = self.driver.find_elements(By.ID, "total_rebate_value")
            total_rebate_value = total_rebate_elements[-1].text
            if total_rebate_value.strip() == "MYR" and len(total_rebate_elements) > 1:
                total_rebate_value = f"MYR {total_rebate_elements[1].text}"

            self.logger.info(f"Total Rebate Value: {total_rebate_value}")
            
            rebate_amount = float(total_rebate_value.replace("MYR", "").replace(",", "").strip())
            self.logger.info(f"Rebate amount (float): {rebate_amount}")

            approve_rebate_url = CREDENTIALS['ApproveRebate'].format(userID=self.userID)
            response = requests.get(approve_rebate_url)
            if response.status_code != 200:
                self.fail(f"Failed to approve rebate: {response.status_code}")
            else:
                self.logger.info("Rebate approved successfully")

            driver.refresh()
            time.sleep(2)
      
            final_balance = self.extract_total_balance()
            expected_balance = initial_balance + rebate_amount
            
            self.assertEqual(final_balance, expected_balance, msg=f"Balance mismatch: Expected {expected_balance:.2f}, got {final_balance:.2f}")
            
        except Exception as e:
            self.logger.error(f"Error in test_02_ApproveRebate: {str(e)}")
            self.fail(f"Test failed: {str(e)}")
 
    def test_03_NavigateToWhatsapp(self):
        try:
            self.navigate_to_rebate_record("total_rebate")
            time.sleep(5)
            self.scrollToSection("contact_customer_service_button")
            time.sleep(2)
            customer_service_button = self.driver.find_element(By.ID, "contact_customer_service_button")
            customer_service_button.click()

            self.test_live_agent.driver = self.driver
            self.test_live_agent.check_whatsapp_url()

        except Exception as e:
            self.logger.error(f"Redirection verification failed: {str(e)}")
            self.fail(f"Failed to verify redirection: {str(e)}")

    def test_04_VerifyApprovedRebateWithinValidDateRange(self):
        try:
            self.navigate_to_rebate_record("record_rebate")

            _, _, _, _, tier_2_users, tier_3_users, tier_1_users = self.test_init.create_downline_rebate(
                tier_1_userID=self.userID, username=self.username, password=self.password, create_one_for_each_tier=True
            )

            current_time = datetime.now().strftime("%d/%m/%Y %I:%M %p")

            self.test_history.driver = self.driver

            self.test_history.choose_date_range_with_current_time(current_time)
            time.sleep(2)
            start_date = WebDriverWait(self.driver,
                                               10).until(EC.presence_of_element_located((By.ID, "start-date-picker"))
                                                         ).get_attribute("value")
            end_date = WebDriverWait(self.driver,
                                             10).until(EC.presence_of_element_located((By.ID, "end-date-picker"))
                                                       ).get_attribute("value")
            formatted_start_date = datetime.strptime(start_date, "%m/%d/%Y").strftime("%Y-%m-%d")
            formatted_end_date = datetime.strptime(end_date, "%m/%d/%Y").strftime("%Y-%m-%d")
            users_to_check = tier_1_users + tier_2_users + tier_3_users
            api_url = f"{CREDENTIALS['SpecifyDateHistory'].format(record_type_value="rebate", start_date=formatted_start_date, end_date=formatted_end_date)}"
            records_verified = self.check_rebate_record(current_time, users_to_check, api_url)
            self.assertTrue(records_verified, "Failed to verify rebate records")

        except Exception as e:
            self.logger.error(f"Error in test_04_VerifyApprovedRebateWithinValidDateRange: {str(e)}")
            self.fail(f"Test failed: {str(e)}")

    def test_05_VerifyApprovedRebateWithinInValidDateRange(self):
        try:
            self.navigate_to_rebate_record("record_rebate")

            _, _, _, _, tier_2_users, tier_3_users, tier_1_users = self.test_init.create_downline_rebate(
                tier_1_userID=self.userID, username=self.username, password=self.password, create_one_for_each_tier=True
            )

            current_time = datetime.now().strftime("%d/%m/%Y %I:%M %p")

            self.test_history.driver = self.driver

            self.test_history.choose_date_range_with_current_time(current_time, isoutofrange=True)
            time.sleep(2)
            start_date = WebDriverWait(self.driver,
                                               10).until(EC.presence_of_element_located((By.ID, "start-date-picker"))
                                                         ).get_attribute("value")
            end_date = WebDriverWait(self.driver,
                                             10).until(EC.presence_of_element_located((By.ID, "end-date-picker"))
                                                       ).get_attribute("value")
            formatted_start_date = datetime.strptime(start_date, "%m/%d/%Y").strftime("%Y-%m-%d")
            formatted_end_date = datetime.strptime(end_date, "%m/%d/%Y").strftime("%Y-%m-%d")
            users_to_check = tier_1_users + tier_2_users + tier_3_users
            api_url = f"{CREDENTIALS['SpecifyDateHistory'].format(record_type_value="rebate", start_date=formatted_start_date, end_date=formatted_end_date)}"
            records_verified = self.check_rebate_record(current_time, users_to_check, api_url, outofrange=True)
            self.assertTrue(records_verified, "Failed to verify rebate records")

        except Exception as e:
            self.logger.error(f"Error in test_05_VerifyApprovedRebateWithinInValidDateRange: {str(e)}")
            self.fail(f"Test failed: {str(e)}")

    def test_06_AllRecord_AllTier_ValidDateRange(self):
        try:
            _, _, _, _, tier_2_users, tier_3_users, tier_1_users = self.test_init.create_downline_rebate(
                tier_1_userID=self.userID, username=self.username, password=self.password, create_one_for_each_tier=True
            )

            current_time = datetime.now().strftime("%d/%m/%Y %I:%M %p")

            self.navigate_to_rebate_record("agent_record")
            choose_record_type = WebDriverWait(self.driver,
                                               10).until(EC.element_to_be_clickable((By.ID, "record_type_button")))
            choose_record_type.click()
            time.sleep(1)
            all_record = self.driver.find_elements(By.ID, "record_type_menu_item")
            all_record[0].click()

            tier_positions = [0, 1, 2, 3] 
            verification_results = {}

            for tier_position in tier_positions:
                choose_tier = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.ID, "tier_button")))
                choose_tier.click()
                time.sleep(1)

                tier_items = WebDriverWait(self.driver,
                                           10).until(EC.presence_of_all_elements_located((By.ID, "tier_menu_item")))

                if tier_position < len(tier_items):
                    tier_items[tier_position].click()
                    time.sleep(1)

                    self.test_history.driver = self.driver
                    self.test_history.choose_date_range_with_current_time(current_time)
                    time.sleep(2)
                    for user in tier_2_users:
                        user["parent"] = tier_1_users[0].get("username")
                        
                    for user in tier_3_users:
                        user["parent"] = tier_2_users[0].get("username")
                        
                    for user in tier_1_users:
                        user["parent"] = "-"

                    match tier_position:
                        case 0: 
                            api_url = CREDENTIALS['RebateAllRecord']
                            users_to_check = tier_1_users + tier_2_users + tier_3_users
                            verification_results['all'] = self.check_agent_record(users_to_check, api_url)
                            self.logger.info("Finished checking all records")
                        case 1:  
                            api_url = CREDENTIALS['RebateAllRecord'] + "tier=1"
                            verification_results['tier1'] = self.check_agent_record(tier_1_users, api_url)
                            self.logger.info("Finished checking tier 1 records")
                        case 2: 
                            api_url = CREDENTIALS['RebateAllRecord'] + "tier=2"
                            verification_results['tier2'] = self.check_agent_record(tier_2_users, api_url)
                            self.logger.info("Finished checking tier 2 records")
                        case 3: 
                            api_url = CREDENTIALS['RebateAllRecord'] + "tier=3"
                            verification_results['tier3'] = self.check_agent_record(tier_3_users, api_url)
                            self.logger.info("Finished checking tier 3 records")
                else:
                    self.logger.warning(f"Tier position {tier_position} is out of range")

            self.logger.info("Results by tier:")
            for tier, result in verification_results.items():
                status = "✓" if result else "✗"
                self.logger.info(f"{status} {tier.capitalize()} verification: {'Passed' if result else 'Failed'}")

            for tier, result in verification_results.items():
                self.assertTrue(result, f"{tier.capitalize()} records verification failed")

        except Exception as e:
            self.logger.error(f"Error in test_06_AllRecord_AllTier_ValidDateRange {str(e)}")
            self.fail(f"Test failed: {str(e)}")

    
    def test_07_AllRecord_AllTier_InValidDateRange(self):
        try:
            _, _, _, _, tier_2_users, tier_3_users, tier_1_users = self.test_init.create_downline_rebate(
                tier_1_userID=self.userID, username=self.username, password=self.password, create_one_for_each_tier=True
            )

            current_time = datetime.now().strftime("%d/%m/%Y %I:%M %p")

            self.navigate_to_rebate_record("agent_record")
            choose_record_type = WebDriverWait(self.driver,
                                               10).until(EC.element_to_be_clickable((By.ID, "record_type_button")))
            choose_record_type.click()
            time.sleep(1)
            all_record = self.driver.find_elements(By.ID, "record_type_menu_item")
            all_record[0].click()

            tier_positions = [0, 1, 2, 3] 
            verification_results = {}

            for tier_position in tier_positions:
                choose_tier = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.ID, "tier_button")))
                choose_tier.click()
                time.sleep(1)

                tier_items = WebDriverWait(self.driver,
                                           10).until(EC.presence_of_all_elements_located((By.ID, "tier_menu_item")))

                if tier_position < len(tier_items):
                    tier_items[tier_position].click()
                    time.sleep(1)

                    self.test_history.driver = self.driver
                    self.test_history.choose_date_range_with_current_time(current_time, isoutofrange=True)
                    start_date = WebDriverWait(self.driver,
                                               10).until(EC.presence_of_element_located((By.ID, "start-date-picker"))
                                                         ).get_attribute("value")
                    end_date = WebDriverWait(self.driver,
                                             10).until(EC.presence_of_element_located((By.ID, "end-date-picker"))
                                                       ).get_attribute("value")
                    formatted_start_date = datetime.strptime(start_date, "%m/%d/%Y").strftime("%Y-%m-%d")
                    formatted_end_date = datetime.strptime(end_date, "%m/%d/%Y").strftime("%Y-%m-%d")
                    self.logger.info(f"start_date: {formatted_start_date}")
                    self.logger.info(f"end_date: {formatted_end_date}")
                    time.sleep(2)
                    for user in tier_2_users:
                        user["parent"] = tier_1_users[0].get("username")
                        
                    for user in tier_3_users:
                        user["parent"] = tier_2_users[0].get("username")
                        
                    for user in tier_1_users:
                        user["parent"] = "-"

                    match tier_position:
                        case 0: 
                            api_url = CREDENTIALS['RebateAllRecord'
                                                  ] + f"&start={formatted_start_date}&end={formatted_end_date}"
                            users_to_check = tier_1_users + tier_2_users + tier_3_users
                            verification_results['all'] = self.check_agent_record(
                                users_to_check, api_url, outofrange=True
                            )
                            self.logger.info("Finished checking all records")
                        case 1: 
                            api_url = CREDENTIALS[
                                'RebateAllRecord'] + "tier=1" + f"&start={formatted_start_date}&end={formatted_end_date}"
                            verification_results['tier1'] = self.check_agent_record(
                                tier_1_users, api_url, outofrange=True
                            )
                            self.logger.info("Finished checking tier 1 records")
                        case 2: 
                            api_url = CREDENTIALS[
                                'RebateAllRecord'] + "tier=2" + f"&start={formatted_start_date}&end={formatted_end_date}"
                            verification_results['tier2'] = self.check_agent_record(
                                tier_2_users, api_url, outofrange=True
                            )
                            self.logger.info("Finished checking tier 2 records")
                        case 3: 
                            api_url = CREDENTIALS[
                                'RebateAllRecord'] + "tier=3" + f"&start={formatted_start_date}&end={formatted_end_date}"
                            verification_results['tier3'] = self.check_agent_record(
                                tier_3_users, api_url, outofrange=True
                            )
                            self.logger.info("Finished checking tier 3 records")
                else:
                    self.logger.warning(f"Tier position {tier_position} is out of range")

            self.logger.info(f"verification_results: {verification_results}")
            self.logger.info("Results by tier:")
            for tier, result in verification_results.items():
                status = "✓" if result else "✗"
                self.logger.info(f"{status} {tier.capitalize()} verification: {'Passed' if result else 'Failed'}")

            for tier, result in verification_results.items():
                self.assertTrue(result, f"{tier.capitalize()} records verification failed")

        except Exception as e:
            self.logger.error(f"Error in test_06_AllRecord_AllTier_InValidDateRange {str(e)}")
            self.fail(f"Test failed: {str(e)}")

    def test_08_Downline_AllTier_ValidDateRange(self):
        try:
            _, _, _, _, tier_2_users, tier_3_users, tier_1_users = self.test_init.create_downline_rebate(
                tier_1_userID=self.userID, username=self.username, password=self.password, create_one_for_each_tier=True
            )

            current_time = datetime.now().strftime("%d/%m/%Y %I:%M %p")

            self.navigate_to_rebate_record("agent_record")
            choose_record_type = WebDriverWait(self.driver,
                                               10).until(EC.element_to_be_clickable((By.ID, "record_type_button")))
            choose_record_type.click()
            time.sleep(1)
            downline_record = self.driver.find_elements(By.ID, "record_type_menu_item")
            downline_record[1].click()

            tier_positions = [0, 1, 2, 3] 
            verification_results = {}
            for user in tier_2_users:
               
                tier2_rebate = (Decimal(str(self.check_rebate_percentage(user.get("provider_id", 0), "1"))) * Decimal(str(user.get("bet_amount", 0)))) / Decimal('100')
                tier3_rebates = sum(
                    (Decimal(str(self.check_rebate_percentage(t3_user.get("provider_id", 0), "2"))) * 
                    Decimal(str(t3_user.get("bet_amount", 0)))) / Decimal('100')
                    for t3_user in tier_3_users
                )
                self.logger.info(f"HI")
                self.logger.info(f"tier2_rebate: {tier2_rebate}")
                self.logger.info(f"tier3_rebates: {tier3_rebates}")
                user["rebate_amount"] = str((tier2_rebate + tier3_rebates).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP))
                
                total_bet = Decimal(str(user.get("bet_amount", 0))) + sum(
                    Decimal(str(t3_user.get("bet_amount", 0))) for t3_user in tier_3_users
                )
                user["bet_amount"] = total_bet.quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)

            for user in tier_3_users:
                rebate = (Decimal(str(self.check_rebate_percentage(user.get("provider_id", 0), "1"))) * 
                        Decimal(str(user.get("bet_amount", 0)))) / Decimal('100')
                user["rebate_amount"] = str(rebate.quantize(Decimal('0.00'), rounding=ROUND_HALF_UP))

            self.logger.info(f"tier_2_users: {tier_2_users}")
            self.logger.info(f"tier_3_users: {tier_3_users}")

  
            for tier_position in tier_positions:
                # Open tier dropdown
                choose_tier = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.ID, "tier_button")))
                choose_tier.click()
                time.sleep(1)

                tier_items = WebDriverWait(self.driver,
                                           10).until(EC.presence_of_all_elements_located((By.ID, "tier_menu_item")))

                if tier_position < len(tier_items):
                    tier_items[tier_position].click()
                    time.sleep(1)

                    self.test_history.driver = self.driver
                    self.test_history.choose_date_range_with_current_time(current_time)
                    time.sleep(2)

                    match tier_position:
                        case 0:  
                            api_url = CREDENTIALS['RebateDownlineRecord']
                            users_to_check = tier_2_users + tier_3_users
                            verification_results['all'] = self.check_downline_record(users_to_check, api_url)
                        case 1:  
                            api_url = CREDENTIALS['RebateDownlineRecord'] + "tier=1"
                            for user in tier_1_users:
                                user["total_bet_amount"] = user.get("bet_amount", 0)
                            verification_results['tier1'] = self.check_downline_record(tier_1_users, api_url)
                        case 2:  
                            api_url = CREDENTIALS['RebateDownlineRecord'] + "tier=2"
                            for user in tier_2_users:
                                user["total_bet_amount"] = user.get("bet_amount", 0)
                            verification_results['tier2'] = self.check_downline_record(tier_2_users, api_url)
                        case 3:  
                            api_url = CREDENTIALS['RebateDownlineRecord'] + "tier=3"
                            for user in tier_3_users:
                                user["total_bet_amount"] = user.get("bet_amount", 0)
                            verification_results['tier3'] = self.check_downline_record(tier_3_users, api_url)
             
                else:
                    self.logger.warning(f"Tier position {tier_position} is out of range")

            self.logger.info("Results by tier:")
            for tier, result in verification_results.items():
                status = "✓" if result else "✗"
                self.logger.info(f"{status} {tier.capitalize()} verification: {'Passed' if result else 'Failed'}")

            for tier, result in verification_results.items():
                self.assertTrue(result, f"{tier.capitalize()} records verification failed")

        except Exception as e:
            self.logger.error(f"Error in test_07_Downline_AllTier_ValidDateRange: {str(e)}")
            self.fail(f"Test failed: {str(e)}")

    def test_09_BetRecord_AllTier_ValidDateRange(self):
        try:
            _, _, _, _, tier_2_users, tier_3_users, tier_1_users = self.test_init.create_downline_rebate(
                tier_1_userID=self.userID, username=self.username, password=self.password, create_one_for_each_tier=True
            )

            current_time = datetime.now().strftime("%d/%m/%Y %I:%M %p")

            self.navigate_to_rebate_record("agent_record")
            choose_record_type = WebDriverWait(self.driver,
                                               10).until(EC.element_to_be_clickable((By.ID, "record_type_button")))
            choose_record_type.click()
            time.sleep(1)
            all_record = self.driver.find_elements(By.ID, "record_type_menu_item")
            all_record[2].click()

            tier_positions = [0, 1, 2, 3] 
            verification_results = {}

            for tier_position in tier_positions:
            
                choose_tier = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.ID, "tier_button")))
                choose_tier.click()
                time.sleep(1)

                tier_items = WebDriverWait(self.driver,
                                           10).until(EC.presence_of_all_elements_located((By.ID, "tier_menu_item")))

                if tier_position < len(tier_items):
                    tier_items[tier_position].click()
                    time.sleep(1)

                    self.test_history.driver = self.driver
                    self.test_history.choose_date_range_with_current_time(current_time)
                    time.sleep(2)

                    match tier_position:
                        case 0:  
                            api_url = CREDENTIALS['RebateBetRecord']
                            users_to_check = tier_2_users + tier_3_users
                            verification_results['all'] = self.check_bet_record(users_to_check, api_url)
                            self.logger.info("Finished checking all records")
                        case 1:  
                            api_url = CREDENTIALS['RebateBetRecord'] + "tier=1"
                            verification_results['tier1'] = self.check_bet_record(tier_1_users, api_url)
                            self.logger.info("Finished checking tier 1 records")
                        case 2: 
                            api_url = CREDENTIALS['RebateBetRecord'] + "tier=2"
                            verification_results['tier2'] = self.check_bet_record(tier_2_users, api_url)
                            self.logger.info("Finished checking tier 2 records")
                        case 3: 
                            api_url = CREDENTIALS['RebateBetRecord'] + "tier=3"
                            verification_results['tier3'] = self.check_bet_record(tier_3_users, api_url)
                            self.logger.info("Finished checking tier 3 records")
                else:
                    self.logger.warning(f"Tier position {tier_position} is out of range")

            self.logger.info("Results by tier:")
            for tier, result in verification_results.items():
                status = "✓" if result else "✗"
                self.logger.info(f"{status} {tier.capitalize()} verification: {'Passed' if result else 'Failed'}")

            for tier, result in verification_results.items():
                self.assertTrue(result, f"{tier.capitalize()} records verification failed")

        except Exception as e:
            self.logger.error(f"Error in test_06_AllRecord_AllTier_ValidDateRange {str(e)}")
            self.fail(f"Test failed: {str(e)}")
 
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    unittest.main()
