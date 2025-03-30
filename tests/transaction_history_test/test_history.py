import unittest
import time
import logging
import random
import requests
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from config.constant import LANGUAGE_SETTINGS, CREDENTIALS
from tests.authentication_test.base_test import BaseTest
from tests.test_init import TestInit


class TestHistory(BaseTest):

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
        self.navigate_to_history()

    def tearDown(self):
        if hasattr(self, "driver"):
            self.driver.quit()

    def navigate_to_history(self):
        driver = self.driver
        history_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "home-history-button")))
        history_button.click()

    def choose_date(self, picker_id, return_date=None):
        driver = self.driver
        date_picker = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, picker_id)))
        date_picker.click()
        time.sleep(2)

        WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.CLASS_NAME, "MuiDayCalendar-root")))

        active_dates = driver.find_elements(By.XPATH, "//button[@role='gridcell' and not(@disabled)]")

        random_date = random.choice(active_dates)
        random_date.click()

        ok_button = driver.find_element(By.XPATH, "//button[text()='OK']")
        ok_button.click()
        time.sleep(2)

        date_picker = driver.find_element(By.ID, picker_id)
        date_str = date_picker.get_attribute("value")
        if return_date:
            return date_str

    def clear_selection(self):
        clear_button = WebDriverWait(self.driver,
                                     10).until(EC.element_to_be_clickable((By.ID, "clear-selection-button")))
        clear_button.click()

    def select_random_options(self, index):
        try:
            self.open_dropdown(index)
            options = WebDriverWait(self.driver, 3).until(
                EC.visibility_of_all_elements_located((By.CSS_SELECTOR, "li.MuiMenuItem-root"))
            )
            self.logger.info(f"Found {len(options)} options")
            random_option = random.choice(options)
            random_option_text = random_option.text
            self.logger.info(f"Randomly selecting option: {random_option_text}")
            WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable(random_option)).click()

        except Exception as e:
            self.fail(f"Failed to select random options: {str(e)}")

    def choose_date_range_with_current_time(self, current_time, isoutofrange=False):
        driver = self.driver

        current_datetime = datetime.strptime(current_time.split(' ')[0], "%d/%m/%Y")
        self.logger.info(f"Current datetime: {current_datetime}")
        self.logger.info(f"Current datetime for comparison: {current_datetime.strftime('%d/%m/%Y')}")

        time.sleep(1)

        start_picker = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "start-date-picker")))
        start_picker.click()
        time.sleep(1)

        WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.CLASS_NAME, "MuiDayCalendar-root")))

        active_dates = driver.find_elements(By.XPATH, "//button[@role='gridcell' and not(@disabled)]")
        valid_start_dates = []

        for date_elem in active_dates:
            try:
                date_text = date_elem.get_attribute("aria-label")
                if not date_text:
                    timestamp = date_elem.get_attribute("data-timestamp")
                    if timestamp:
                        date_obj = datetime.fromtimestamp(int(timestamp) / 1000)
                        if date_obj < current_datetime:
                            valid_start_dates.append(date_elem)
                            self.logger.info(f"Found valid start date: {date_obj.strftime('%d/%m/%Y')}")
                else:
                    date_obj = datetime.strptime(date_text, "%d %B %Y")
                    if date_obj < current_datetime:
                        valid_start_dates.append(date_elem)
                        self.logger.info(f"Found valid start date: {date_obj.strftime('%d/%m/%Y')}")
            except (ValueError, TypeError) as e:
                self.logger.warning(f"Error parsing date: {e}")
                continue

        if not valid_start_dates:
            self.logger.warning("No valid start dates found, using all active dates")
            valid_start_dates = active_dates

        if isoutofrange:
            date_elements_with_dates = []
            for date_elem in valid_start_dates:
                try:
                    date_text = date_elem.get_attribute("aria-label")
                    if date_text:
                        date_obj = datetime.strptime(date_text, "%d %B %Y")
                        date_elements_with_dates.append((date_elem, date_obj))
                    else:
                        timestamp = date_elem.get_attribute("data-timestamp")
                        if timestamp:
                            date_obj = datetime.fromtimestamp(int(timestamp) / 1000)
                            date_elements_with_dates.append((date_elem, date_obj))
                except (ValueError, TypeError) as e:
                    self.logger.warning(f"Skipping date element due to parsing error: {e}")
                    continue

            date_elements_with_dates.sort(key=lambda x: x[1])

            if not date_elements_with_dates:
                self.logger.warning("No valid date elements found with parseable dates")
                random_start_date = random.choice(valid_start_dates)
                random_start_date.click()
            else:
                start_date_pair = random.choice(date_elements_with_dates)
                start_date_elem = start_date_pair[0]
                start_date_obj = start_date_pair[1]

                self.logger.info(f"Selected random start date: {start_date_obj.strftime('%d/%m/%Y')}")
                start_date_elem.click()

            driver.find_element(By.XPATH, "//button[text()='OK']").click()
            time.sleep(1)

            start_picker = driver.find_element(By.ID, "start-date-picker")
            start_date_str = start_picker.get_attribute("value")
            start_date = datetime.strptime(start_date_str, "%m/%d/%Y")
            self.logger.info(f"Start date value: {start_date_str}, parsed: {start_date}")

            end_picker = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "end-date-picker")))
            end_picker.click()
            time.sleep(1)

            WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.CLASS_NAME, "MuiDayCalendar-root")))

            active_end_dates = driver.find_elements(By.XPATH, "//button[@role='gridcell' and not(@disabled)]")
            end_date_elements_with_dates = []

            for date_elem in active_end_dates:
                try:
                    date_text = date_elem.get_attribute("aria-label")
                    if date_text:
                        date_obj = datetime.strptime(date_text, "%d %B %Y")
                        # Only include if after start date and before current
                        if start_date < date_obj < current_datetime:
                            end_date_elements_with_dates.append((date_elem, date_obj))
                    else:
                        timestamp = date_elem.get_attribute("data-timestamp")
                        if timestamp:
                            date_obj = datetime.fromtimestamp(int(timestamp) / 1000)
                            if start_date < date_obj < current_datetime:
                                end_date_elements_with_dates.append((date_elem, date_obj))
                except (ValueError, TypeError) as e:
                    self.logger.warning(f"Skipping end date element due to parsing error: {e}")
                    continue

            if end_date_elements_with_dates:
                end_date_pair = random.choice(end_date_elements_with_dates)
                end_date_elem = end_date_pair[0]
                end_date_obj = end_date_pair[1]

                self.logger.info(f"Selected random end date: {end_date_obj.strftime('%d/%m/%Y')}")
                end_date_elem.click()
            else:
                self.logger.warning("No valid end dates found. Selecting last available date.")
                last_date = active_end_dates[-1]
                last_date.click()

            driver.find_element(By.XPATH, "//button[text()='OK']").click()
            time.sleep(1)

            # Log the selected date range
            end_picker = driver.find_element(By.ID, "end-date-picker")
            end_date_str = end_picker.get_attribute("value")
            self.logger.info(f"Selected date range: {start_date_str} to {end_date_str}")

            return

        random_start_date = random.choice(valid_start_dates)
        random_start_date.click()
        self.logger.info(f"Selected start date element: {random_start_date.text}")

        driver.find_element(By.XPATH, "//button[text()='OK']").click()
        time.sleep(1)

        start_picker = driver.find_element(By.ID, "start-date-picker")
        start_date_str = start_picker.get_attribute("value")
        self.logger.info(f"Selected start date element: {start_date_str}")
        start_date = datetime.strptime(start_date_str, "%m/%d/%Y")
        self.logger.info(f"Selected start date: {start_date}")
        self.logger.info(f"Current datetime: {current_datetime}")

        end_picker = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "end-date-picker")))
        end_picker.click()
        time.sleep(1)

        WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.CLASS_NAME, "MuiDayCalendar-root")))

        try:
            today_button = driver.find_element(By.XPATH, "//button[contains(@class, 'MuiPickersDay-today')]")
            self.logger.info(f"Found today button: {today_button.text}")
            today_button.click()
        except NoSuchElementException:
            active_dates = driver.find_elements(By.XPATH, "//button[@role='gridcell' and not(@disabled)]")
            random_end_date = active_dates[-1]
            random_end_date.click()
            self.logger.info(f"Selected last available date as end date: {random_end_date.text}")

        driver.find_element(By.XPATH, "//button[text()='OK']").click()
        time.sleep(1)

        end_picker = driver.find_element(By.ID, "end-date-picker")
        end_date_str = end_picker.get_attribute("value")
        self.logger.info(f"Selected end date: {end_date_str}")
        end_date = datetime.strptime(end_date_str, "%m/%d/%Y")
        self.logger.info(f"Selected end date: {end_date}")

        if start_date <= current_datetime <= end_date:
            self.logger.info(f"✓ Current time {current_time} is within the selected date range")
        else:
            self.logger.warning(f"✗ Current time {current_time} is NOT within the selected date range")
            self.logger.warning(
                f"Start date: {start_date.strftime('%d/%m/%Y')}, "
                f"Current date: {current_datetime.strftime('%d/%m/%Y')}, "
                f"End date: {end_date.strftime('%d/%m/%Y')}"
            )

    def choose_specific_record_type(self, record_type):
        record_type_options = WebDriverWait(self.driver, 10).until(
            EC.visibility_of_all_elements_located((By.CSS_SELECTOR, "li[id^='history-type-option-']"))
        )
        for i in record_type_options:
            option_id = i.get_attribute("id")
            if option_id == f"history-type-option-{record_type}":
                record_type_value = option_id.split("-")[-1]
                self.logger.info(f"Record type value extracted from ID: {record_type_value}")
                time.sleep(2)
                self.logger.info(f"Selecting record type: {i.text}")
                i.click()
                return record_type_value

    def check_date_record(self, index):
        self.open_dropdown(index)
        time.sleep(2)
        date_options = WebDriverWait(self.driver, 10).until(
            EC.visibility_of_all_elements_located((By.CSS_SELECTOR, "li[id^='date-type-option-']"))
        )
        record_types = []

        for option in date_options:
            option_id = option.get_attribute("id")
            option_text = option.text
            record_types.append((option_id, option_text))
            self.logger.info(f"Found record type: {option_text} with ID: {option_id}")

        return record_types

    def verify_record_history(
        self, record_type_id=None, record_type_text=None, current_time=None, amount=None, date_range=False,
        record_type_value=None, wallet_from=None, wallet_to=None, activity=None, expected_reward_counts=None,
        game_win=None, provider_name=None, rebate_info=None
    ):
        self.logger.info(f"Verifying {record_type_text} records")
        self.logger.info(f"Record type ID: {record_type_id}")

        current_date = datetime.now()
        current_date_str = current_date.strftime("%d/%m/%Y")
        self.logger.info(f"Current date: {current_date_str}")

        if rebate_info:
            try:
                date_option_id = record_type_id.split("-")[-1]
                index = int(date_option_id) - 1

                if isinstance(rebate_info, list):
                    if 0 <= index < len(rebate_info):
                        current_time = rebate_info[index]['timestamp']
                        amount = rebate_info[index]['bet_amount']
                        self.logger.info(f"Current rebate: {rebate_info}")
                        self.logger.info(f"Current time: {current_time}")
                        self.logger.info(f"Amount: {amount}")
                    else:
                        self.logger.warning(
                            f"Index {index} out of range for rebate_info list (length: {len(rebate_info)})"
                        )
                        if len(rebate_info) > 0:
                            current_rebate = rebate_info[0]
                            current_time = current_rebate['timestamp']
                            amount = current_rebate['bet_amount']
                else:
                    current_time = rebate_info[index]['timestamp']
                    amount = rebate_info[index]['bet_amount']
            except (IndexError, ValueError) as e:
                self.logger.error(f"Error processing rebate info: {e}")

        if current_time:
            current_time_str = current_time.split(' ')[0]
            self.logger.info(f"Current date passed to function: {current_time_str}")
            self.logger.info(f"Current time: {current_time}")
        else:
            self.logger.warning("No current_time provided")
            current_time_str = current_date_str

        date_in_range = False
        date_option_id = None

        if not date_range:
            record_option = WebDriverWait(self.driver,
                                          10).until(EC.visibility_of_element_located((By.ID, record_type_id)))
            record_option.click()
            time.sleep(2)

            date_option_id = record_type_id.split("-")[-1]
            self.logger.info(f"Extracted date option ID: {date_option_id}")

            try:
                date_option_index = int(date_option_id)
                match date_option_index:
                    case 1:
                        date_in_range = current_date_str == current_time_str

                        self.logger.info(f"Today option selected, date in range: {date_in_range}")

                    case 2:
                        yesterday = current_date - timedelta(days=1)
                        yesterday_str = yesterday.strftime("%d/%m/%Y")
                        self.logger.info(f"Yesterday date: {yesterday_str}")
                        self.logger.info(f"Current time: {current_time_str}")
                        date_in_range = current_time_str == yesterday_str
                        self.logger.info(f"Yesterday option selected, date in range: {date_in_range}")

                    case 3:
                        for i in range(7):
                            check_date = current_date - timedelta(days=i)
                            if check_date.strftime("%d/%m/%Y") == current_time_str:
                                date_in_range = True
                                break
                        self.logger.info(f"Last week option selected, date in range: {date_in_range}")

                    case 4:
                        date_in_range = current_date.strftime("%m") == datetime.strptime(current_time_str,
                                                                                         "%d/%m/%Y").strftime("%m")
                        self.logger.info(f"Current month option selected, date in range: {date_in_range}")

                    case 5:
                        transaction_date = datetime.strptime(current_time_str, "%d/%m/%Y")
                        transaction_month = int(transaction_date.strftime("%m"))
                        current_month = int(current_date.strftime("%m"))

                        for i in range(3):
                            check_month = (current_month - i) if (current_month - i) > 0 else (current_month - i + 12)
                            if transaction_month == check_month:
                                date_in_range = True
                                break
                        self.logger.info(f"Last 3 months option selected, date in range: {date_in_range}")
            except (ValueError, TypeError):
                self.logger.warning(f"Could not determine if date is in range for option ID: {date_option_id}")
        else:
            start_date_picker = WebDriverWait(self.driver,
                                              10).until(EC.visibility_of_element_located((By.ID, "start-date-picker")))
            end_date_picker = WebDriverWait(self.driver,
                                            10).until(EC.visibility_of_element_located((By.ID, "end-date-picker")))
            start_date = start_date_picker.get_attribute("value")
            end_date = end_date_picker.get_attribute("value")
            self.logger.info(f"Start date: {start_date}")
            self.logger.info(f"End date: {end_date}")

            if start_date and end_date:
                start_date_obj = datetime.strptime(start_date, "%m/%d/%Y")
                self.logger.info(f"Start date object: {start_date_obj}")
                end_date_obj = datetime.strptime(end_date, "%m/%d/%Y")
                self.logger.info(f"End date object: {end_date_obj}")
                transaction_date = datetime.strptime(current_time.split(' ')[0], "%d/%m/%Y")
                self.logger.info(f"Transaction date: {transaction_date}")

                date_in_range = start_date_obj <= transaction_date <= end_date_obj
                self.logger.info(f"Custom date range, date in range: {date_in_range}")

        try:
            table = WebDriverWait(self.driver,
                                  5).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "table.MuiTable-root")))

            rows = table.find_elements(By.CSS_SELECTOR, "tbody.MuiTableBody-root tr")
            self.logger.info(f"Found {len(rows)} rows")

            if len(rows) > 0:
                self.logger.info(f"Found {len(rows)} {record_type_text} records")

                token = self.login(self.username, self.password)
                if not token:
                    self.logger.error("Failed to get token")
                    return False

                headers = {
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                    "language": self.language
                }
                if date_range:
                    api_url = f"{CREDENTIALS['SpecifyDateHistory'].format(BO_base_url = CREDENTIALS["BO_base_url"], record_type_value=record_type_value, start_date=start_date, end_date=end_date)}"
                else:
                    api_url = f"{CREDENTIALS['DateHistory'].format(BO_base_url = CREDENTIALS["BO_base_url"], record_type_value=record_type_value, date_option_id=date_option_id)}"

                self.logger.info(f"API URL: {api_url}")

                deposit_info_response = requests.get(api_url, headers=headers)
                if deposit_info_response.status_code != 200:
                    self.logger.error(f"Failed to get deposit info: {deposit_info_response.text}")
                    return False

                deposit_info = deposit_info_response.json()
                self.logger.info(f"API Response: {deposit_info}")

                api_records = deposit_info.get('data', {}).get('data', [])
                self.logger.info(f"API returned {len(api_records)} records")

                first_row = rows[0]
                cells = first_row.find_elements(By.CSS_SELECTOR, "td.MuiTableCell-body")

                if date_in_range and api_records:
                    time_recorded = False
                    amount_recorded = False
                    status_recorded = False
                    promo_recorded = False
                    target_recorded = False
                    win_loss_recorded = False

                    self.logger.info(f"Record type ID: {record_type_value}")
                    match record_type_value:
                        case "bet":
                            for i, cell in enumerate(cells):
                                cell_text = cell.text

                                match i:
                                    case 0:
                                        self.logger.info(f"Current time: {current_time}")
                                        self.logger.info(f"Cell text: {cell_text}")
                                        if current_time in cell_text:
                                            self.logger.info(f"✓ Date cell has value: {cell_text}")
                                            time_recorded = True
                                        else:
                                            self.fail(f"✗ Date/Time cell is incorrect")

                                    case 1:
                                        if provider_name:
                                            if provider_name.lower() in cell_text.lower():
                                                self.logger.info(f"✓ Provider ID cell has value: {cell_text}")
                                                provider_name_recorded = True
                                            else:
                                                self.fail(f"✗ Provider ID cell is incorrect")
                                    case 3:
                                        # Convert Unicode Minus to ASCII Hyphen
                                        normalized_text = cell.text.replace("\u2212", "-")
                                        if game_win:
                                            if not normalized_text.strip().startswith("-"):
                                                self.logger.info(f"✓ Win/Loss cell has value: {cell_text}")
                                                win_loss_recorded = True
                                            else:
                                                self.fail(f"✗ Win/Loss cell is incorrect")
                                        else:
                                            self.logger.info(f"Loss: {cell.text}")
                                            if normalized_text.strip().startswith("-"):
                                                self.logger.info(f"✓ Win/Loss cell has value: {cell_text}")
                                                win_loss_recorded = True
                                            else:
                                                self.fail(f"✗ Win/Loss cell is incorrect")

                            if time_recorded and provider_name_recorded and win_loss_recorded:
                                return True
                            else:
                                return False

                        case "deposit" | "withdraw":

                            for i, cell in enumerate(cells):
                                cell_text = cell.text

                                match i:
                                    case 0:
                                        if current_time in cell_text:
                                            self.logger.info(f"✓ Date cell has value: {cell_text}")
                                            time_recorded = True
                                        else:
                                            self.fail(f"✗ Date/Time cell is incorrect")

                                    case 1:
                                        self.logger.info(f"Amount: {amount}")
                                        amount_str = str(f"{amount:,.2f}")
                                        if amount_str in cell_text:
                                            self.logger.info(
                                                f"✓ Amount verification passed: {cell_text} contains {amount_str}"
                                            )
                                            amount_recorded = True
                                        else:
                                            self.fail(f"✗ Amount cell is incorrect")

                                    case 3:
                                        if api_records:
                                            api_status = api_records[0].get('status')
                                            self.logger.info(f"API status: {api_status}")
                                            if api_status.lower() in cell_text.lower():
                                                self.logger.info(f"✓ Amount matches API data: {api_status}")
                                                status_recorded = True
                                            else:
                                                self.fail(
                                                    f"✗ Amount verification failed against both expected and API data"
                                                )

                            if time_recorded and amount_recorded and status_recorded:
                                return True
                            else:
                                return False
                        case "transfer":
                            cell_mapping = {
                                0: "Date/Time",
                                1: "Transfer Type",
                                2: "Wallet",
                                3: "Amount",
                                4: "Status"
                            }

                            if len(rows) > 1 and len(api_records) > 1:
                                row_params = [{
                                    "row": rows[0],
                                    "api_record": api_records[0],
                                    "wallet_name": wallet_from,
                                    "row_name": "Source wallet (money out)"
                                }, {
                                    "row": rows[1],
                                    "api_record": api_records[1],
                                    "wallet_name": wallet_to,
                                    "row_name": "Destination wallet (money in)"
                                }]

                                all_verified = True

                                for params in row_params:
                                    row_verified = self.verify_transfer_row(
                                        row=params["row"], api_record=params["api_record"],
                                        wallet_name=params["wallet_name"], current_time=current_time, amount=amount,
                                        cell_mapping=cell_mapping, row_name=params["row_name"]
                                    )
                                    if not row_verified:
                                        all_verified = False

                                if all_verified:
                                    self.logger.info("✓ Both transfer rows verified successfully")
                                    return True
                                else:
                                    self.logger.error("✗ Some transfer record details are incorrect")
                                    return False
                            else:
                                self.logger.error("✗ Transfer should have two rows (source and destination)")
                                return False
                        case "promo":

                            for i, cell in enumerate(cells):
                                cell_text = cell.text
                                match i:
                                    case 0:
                                        if current_time in cell_text:
                                            self.logger.info(f"✓ Date cell has value: {cell_text}")
                                            time_recorded = True
                                        else:
                                            self.fail(f"✗ Date/Time cell is incorrect")

                                    case 1:
                                        promo_used = activity.split("(")[0].strip()
                                        self.logger.info(f"Promo used: {promo_used}")
                                        if promo_used in cell_text:
                                            self.logger.info(
                                                f"✓ Amount verification passed: {cell_text} contains {promo_used}"
                                            )
                                            promo_recorded = True
                                        else:
                                            self.fail(f"✗ Amount cell is incorrect")
                                    case 6:
                                        if api_records:
                                            try:
                                                target = (
                                                    float(api_records[0].get('bonus_amount')) +
                                                    float(api_records[0].get('deposit_amount'))
                                                ) * float(api_records[0].get('turnover_multiply'))
                                                target_str = str(f"{target:,.2f}")
                                                self.logger.info(f"Target: {target_str}")
                                                if target_str in cell_text:
                                                    self.logger.info(f"✓ Target cell has value: {cell_text}")
                                                    target_recorded = True
                                                else:
                                                    self.fail(f"✗ Target cell is incorrect")
                                            except (TypeError, ValueError) as e:
                                                self.logger.error(f"Error calculating target: {e}")
                                                self.fail(f"✗ Target calculation failed: {e}")
                                    case 7:
                                        if api_records:
                                            api_status = api_records[0].get('status')
                                            self.logger.info(f"API status: {api_status}")
                                            if api_status.lower() in cell_text.lower():
                                                self.logger.info(f"✓ Amount matches API data: {api_status}")
                                                status_recorded = True
                                            else:
                                                self.fail(
                                                    f"✗ Amount verification failed against both expected and API data"
                                                )

                            if time_recorded and promo_recorded and target_recorded and status_recorded:
                                return True
                            else:
                                return False
                        case "reward":
                            self.logger.info(f"Found {len(rows)} reward rows to check")

                            found_reward_types = {
                                reward_type: False for reward_type in expected_reward_counts.keys()
                            }

                            for row_index, row in enumerate(rows):
                                self.logger.info(f"Checking row {row_index + 1}")
                                row_time_recorded = False
                                row_reward_type_recorded = False
                                row_amount_recorded = False
                                current_reward_type = None

                                cells = row.find_elements(By.CSS_SELECTOR, "td.MuiTableCell-body")
                                for i, cell in enumerate(cells):
                                    cell_text = cell.text

                                    match i:
                                        case 0:
                                            if current_time in cell_text:
                                                self.logger.info(f"✓ Date cell has value: {cell_text}")
                                                row_time_recorded = True
                                            else:
                                                self.logger.info(
                                                    f"✗ Date/Time cell doesn't match current transaction: {cell_text}"
                                                )

                                        case 2:
                                            for reward_type in expected_reward_counts.keys():
                                                if reward_type in cell_text.lower():
                                                    self.logger.info(
                                                        f"✓ Found reward type: {reward_type} in cell: {cell_text}"
                                                    )
                                                    row_reward_type_recorded = True
                                                    current_reward_type = reward_type
                                                    found_reward_types[reward_type] = True
                                                    break

                                            if not row_reward_type_recorded:
                                                self.logger.info(
                                                    f"✗ No expected reward type found in cell: {cell_text}"
                                                )

                                        case 3:
                                            if current_reward_type:
                                                expected_value = expected_reward_counts[current_reward_type]
                                                if str(expected_value) in cell_text:
                                                    self.logger.info(
                                                        f"✓ Amount verification passed: {cell_text} contains {expected_value}"
                                                    )
                                                    row_amount_recorded = True
                                                else:
                                                    self.logger.info(
                                                        f"✗ Amount verification failed: {cell_text} doesn't contain {expected_value}"
                                                    )

                                self.logger.info(
                                    f"Done checking row {row_index + 1}, results: Time={row_time_recorded}, Type={row_reward_type_recorded}, Amount={row_amount_recorded}"
                                )
                            all_types_found = all(found_reward_types.values())
                            if all_types_found and row_amount_recorded and row_time_recorded and row_reward_type_recorded:
                                self.logger.info(f"✓ All reward types were found: {list(found_reward_types.keys())}")
                                return True
                            else:
                                missing = [k for k, v in found_reward_types.items() if not v]
                                self.logger.error(f"✗ Some reward types were not found: {missing}")
                                return False
                        case "rebate":
                            if len(rows) > 1 and len(api_records) > 1:
                                row_params = [{
                                    "row": rows[0],
                                    "api_record": api_records[0],
                                    "rebate_info": rebate_info[0]
                                }, {
                                    "row": rows[1],
                                    "api_record": api_records[1],
                                    "rebate_info": rebate_info[1]
                                }]
                                all_verified = True

                                for params in row_params:
                                    row_verified = self.verify_rebate_rows(
                                        row=params["row"], api_record=params["api_record"],
                                        rebate_info=params["rebate_info"]
                                    )
                                    if not row_verified:
                                        all_verified = False

                                if all_verified:
                                    self.logger.info("✓ Both transfer rows verified successfully")
                                    return True
                                else:
                                    self.logger.error("✗ Some transfer record details are incorrect")
                                    return False
                            else:
                                self.logger.error("✗ Transfer should have two rows (source and destination)")
                                return False
                else:
                    if cells[0].text == LANGUAGE_SETTINGS[self.language]["history"]["no_record"]:
                        self.logger.info(f"No {record_type_text} records found in UI as expected (date out of range)")
                        return True
                    elif not date_in_range:
                        self.logger.warning(f"Found records but date is out of range: {current_time}")
                        return False
                    else:
                        self.logger.warning("No API records but records shown in UI")
                        return False

            else:
                self.fail("No table found")

        except TimeoutException:
            self.logger.info(f"No table found for {record_type_text} records")

            if not date_in_range:
                self.logger.info("No table found as expected (date out of range)")
                return True

            return False

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

            response = self.test_init.make_transfer(headers, source_id=0, target_id=game_id, amount=amount)
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

    def verify_transfer_row(self, row, api_record, wallet_name, current_time, amount, cell_mapping, row_name):
        self.logger.info(f"Checking {row_name}:")
        row_cells = row.find_elements(By.CSS_SELECTOR, "td.MuiTableCell-body")

        verifications = {
            "time": False,
            "transfer_type": False,
            "wallet": False,
            "amount": False,
            "status": False
        }

        for i, cell in enumerate(row_cells):
            cell_text = cell.text
            self.logger.info(f"Cell {i} ({cell_mapping.get(i, 'Unknown')}): {cell_text}")

            match i:
                case 0:
                    if current_time in cell_text:
                        self.logger.info(f"✓ Date cell has value: {cell_text}")
                        verifications["time"] = True
                    else:
                        self.logger.error(f"✗ Date/Time cell is incorrect")

                case 1:
                    api_transfer_type = api_record.get('from')
                    self.logger.info(f"API transfer type: {api_transfer_type}")
                    if api_transfer_type in cell_text:
                        self.logger.info(f"✓ Transfer Type cell has value: {cell_text}")
                        verifications["transfer_type"] = True
                    else:
                        self.logger.error(f"✗ Transfer Type cell is incorrect")

                case 2:
                    self.logger.info(f"Wallet name: {wallet_name}")
                    wallet_name = wallet_name.split()[0].lower()
                    if wallet_name in cell_text.lower():
                        self.logger.info(f"✓ Wallet cell has value: {cell_text}")
                        verifications["wallet"] = True
                    else:
                        self.logger.error(f"✗ Wallet cell is incorrect")

                case 3:
                    amount_str = str(f"{amount:,.2f}")
                    if amount_str in cell_text:
                        self.logger.info(f"✓ Amount cell has value: {cell_text}")
                        verifications["amount"] = True
                    else:
                        self.logger.error(f"✗ Amount cell is incorrect")

                case 4:
                    api_status = api_record.get('status')
                    if api_status.lower() in cell_text.lower():
                        self.logger.info(f"✓ Status cell has value: {cell_text}")
                        verifications["status"] = True
                    else:
                        self.logger.error(f"✗ Status cell is incorrect")

        all_passed = all(verifications.values())
        if all_passed:
            self.logger.info(f"✓ All verifications passed")
        else:
            failed = [k for k, v in verifications.items() if not v]
            self.logger.error(f"✗ Failed verifications for {row_name}: {', '.join(failed)}")

        return all_passed

    def setup_for_bet_test(self, use_yesterday=False):

        _, amount = self.test_init.submit_deposit_api(
            username=self.username, password=self.password, check_history_amount=True
        )
        transfer_amount = random.randint(1, amount)

        self.handleDeposit(self.userID)
        if not use_yesterday:
            self.clear_selection()
        transfer_details, _ = self.transfer_to_random_game(transfer_amount, self.username, self.password)
        token = self.login(self.username, self.password)
        if not token:
            self.logger.error("Failed to get token")
            return False

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "language": self.language
        }
        game_win = random.choice([True, False])
        if game_win:
            type = 1
        else:
            type = 0
        game_id = transfer_details['target_id']
        self.logger.info(f"Win: {game_win}")

        if use_yesterday:
            yesterday = datetime.now() - timedelta(days=1)
            current_time = yesterday.strftime("%d/%m/%Y %I:%M %p")
            self.logger.info(f"filter {current_time}")
            current_date = yesterday.strftime("%Y-%m-%d")
        else:
            current_date = datetime.now().strftime("%Y-%m-%d")
            current_time = datetime.now().strftime("%d/%m/%Y %I:%M %p")

        self.logger.info(f"Current date: {current_date}")
        if not use_yesterday:
            self.logger.info(f"Current time: {current_time}")

        # Place bet
        place_bet_url = f"{CREDENTIALS['PlaceBet'].format(BO_base_url = CREDENTIALS["BO_base_url"], userID=self.userID, transfer_amount=transfer_amount, type=type, game_id=game_id, game_record_date=current_date)}"

        response = requests.get(place_bet_url, headers=headers)
        if response.status_code != 200:
            self.fail(f"Failed to place bet: {response.status_code}")
        else:
            self.logger.info("Bet placed successfully")

        return transfer_details, current_time, game_win

    def verify_rebate_rows(self, row, api_record, rebate_info):
        row_cells = row.find_elements(By.CSS_SELECTOR, "td.MuiTableCell-body")

        verifications = {
            "time": False,
            "rebate_amount": False,
            "username": False,
            "tier_level": False,
            "status": False
        }

        for i, cell in enumerate(row_cells):
            cell_text = cell.text

            match i:
                case 0:
                    self.logger.info(f"Date cell: {cell_text}")
                    self.logger.info(f"Rebate info timestamp: {rebate_info['timestamp']}")

                    cell_dt = datetime.strptime(cell_text, "%d/%m/%Y %I:%M %p")
                    rebate_dt = datetime.strptime(rebate_info['timestamp'], "%d/%m/%Y %I:%M %p")

                    time_diff = abs((cell_dt - rebate_dt).total_seconds() / 60)

                    if time_diff <= 3:
                        self.logger.info(f"✓ Date cell has value: {cell_text}")
                        verifications["time"] = True
                    else:
                        self.fail(f"✗ Date/Time cell is incorrect")

                case 1:
                    self.logger.info(f"Rebate info bet_amount: {rebate_info['bet_amount']}")
                    self.logger.info(f"Rebate info rebate_percentage: {rebate_info['rebate_percentage']}")
                    self.logger.info(f"Date cell: {cell_text}")
                    rebate_amount = (
                        Decimal(rebate_info['bet_amount']) * (Decimal(rebate_info['rebate_percentage']) / Decimal(100))
                    )

                    rebate_amount = rebate_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

                    cell_amount = Decimal(cell_text.replace("RM", "").replace(",", "")).quantize(Decimal("0.01"))

                    self.logger.info(f"Rebate amount: {rebate_amount}")

                    if abs(rebate_amount - cell_amount) <= Decimal("0.02"):
                        self.logger.info(f"✓ Rebate amount is within acceptable range: {cell_text}")
                        verifications["rebate_amount"] = True
                    else:
                        self.logger.error(
                            f"✗ Rebate amount is incorrect! Expected: {rebate_amount}, Found: {cell_text}"
                        )
                        verifications["rebate_amount"] = True

                case 2:
                    self.logger.info(f"Rebate info username: {rebate_info['username']}")
                    self.logger.info(f"Username cell: {cell_text}")
                    if rebate_info['username'] in cell_text.lower():
                        self.logger.info(f"✓ Wallet cell has value: {cell_text}")
                        verifications["username"] = True
                    else:
                        self.logger.error(f"✗ Username cell is incorrect.")

                case 3:
                    self.logger.info(f"Rebate info tier_level: {rebate_info['tier_level']}")
                    self.logger.info(f"Tier level cell: {cell_text}")
                    if rebate_info['tier_level'] in cell_text:
                        self.logger.info(f"✓ Tier level cell has value: {cell_text}")
                        verifications["tier_level"] = True
                    else:
                        self.logger.error(f"✗ Tier level cell is incorrect.")

                case 4:
                    self.logger.info(f"Status cell: {cell_text}")
                    self.logger.info(f"Rebate info status: {api_record.get('status')}")
                    api_status = api_record.get('status')
                    if api_status.lower() in cell_text.lower():
                        self.logger.info(f"✓ Status cell has value: {cell_text}")
                        verifications["status"] = True
                    else:
                        self.logger.error(f"✗ Status cell is incorrect.")

        all_passed = all(verifications.values())
        if all_passed:
            self.logger.info(f"✓ All verifications passed")
        else:
            failed = [k for k, v in verifications.items() if not v]
            self.logger.error(f"✗ Failed verifications: {', '.join(failed)}")

        return all_passed

    def test_01_ChooseRecordType(self):
        try:
            self.driver
            time.sleep(1)
            self.select_dropdown_option(expand_icon_index=0, item_css_selector="li.MuiMenuItem-root")
        except Exception as e:
            self.fail(f"Test failed {str(e)}")

    def test_02_ChooseDate(self):
        try:
            self.driver
            time.sleep(1)
            self.select_dropdown_option(
                expand_icon_index=1, item_css_selector="li.MuiMenuItem-root", check_start_end_disable=True
            )
        except Exception as e:
            self.fail(f"Test failed {str(e)}")

    def test_03_ChooseStartEnd(self):
        try:
            self.clear_selection()
            start_date = self.choose_date("start-date-picker", return_date=True)
            time.sleep(2)
            self.logger.info(f"Start Date: {start_date}")
            end_date = self.choose_date("end-date-picker", return_date=True)
            time.sleep(2)
            self.logger.info(f"End Date: {end_date}")
            try:
                date_type_button = self.driver.find_element(By.ID, "date-type-button")
                date_disabled = not date_type_button.is_enabled()
                self.assertTrue(date_disabled, "Date Type Button should be disabled")
            except Exception as e:
                self.fail(f"Failed to click date type button: {str(e)}")
        except Exception as e:
            self.fail(f"Test failed {str(e)}")

    def test_04_ClearSelection(self):
        driver = self.driver
        self.clear_selection()

        initial_record_type = self.get_all_button_texts(history=True)[0]
        self.logger.info(f"Initial record type button text: {initial_record_type}")
        initial_date = self.get_all_button_texts(history=True)[1]
        self.logger.info(f"Initial date button text: {initial_date}")

        if random.choice([True, False]):
            self.select_random_options(0)
            self.select_random_options(1)
        else:
            self.clear_selection()
            self.select_random_options(0)
            self.choose_date(0)
            self.choose_date(1)
        time.sleep(2)
        try:
            self.clear_selection()
            time.sleep(2)

            try:
                date_inputs = WebDriverWait(driver, 10).until(
                    EC.visibility_of_all_elements_located((By.CSS_SELECTOR, "input[aria-label^='Choose date']"))
                )
                if (
                    initial_record_type == self.get_all_button_texts(history=True)[0]
                    and initial_date == self.get_all_button_texts(history=True)[1]
                    and date_inputs[0].get_attribute("value") == "" and date_inputs[1].get_attribute("value") == ""
                ):
                    self.logger.info("All field is cleared as expected.")
                else:
                    self.logger.error("field is not cleared")
                    self.fail("The field was not cleared correctly.")
            except Exception as e:
                self.fail(f"Failed to verify clear button functionality: {str(e)}")

        except Exception as e:
            self.fail(f"Test failed: {str(e)}")

    def test_05_CheckDepositHistory_Date(self):
        try:
            _, amount = self.test_init.submit_deposit_api(
                username=self.username, password=self.password, check_history_amount=True
            )
            current_time = datetime.now().strftime("%d/%m/%Y %I:%M %p")
            self.logger.info(f"Current time: {current_time}")

            self.handleDeposit(self.userID)

            self.driver.refresh()
            time.sleep(2)
            self.open_dropdown(0)
            record_type_value = self.choose_specific_record_type("deposit")
            time.sleep(2)

            record_types = self.check_date_record(1)
            self.logger.info(f"Found {len(record_types)} record types")
            self.logger.info(f"Record types: {record_types}")

            for record_type_id, record_type_text in record_types:
                self.logger.info(f"Testing record type: {record_type_text}")
                has_records = self.verify_record_history(
                    record_type_id=record_type_id, record_type_text=record_type_text, current_time=current_time,
                    amount=amount, record_type_value=record_type_value
                )

                try:
                    self.assertTrue(has_records, f"Expected to find deposit records but none were found")
                except AssertionError as e:
                    self.fail(f"Test failed: {str(e)}")

                self.open_dropdown(1)
            time.sleep(1)

        except Exception as e:
            self.fail(f"Test failed: {str(e)}")

    def test_06_CheckDepositHistory_DateRange(self):
        try:
            _, amount = self.test_init.submit_deposit_api(
                username=self.username, password=self.password, check_history_amount=True
            )
            current_time = datetime.now().strftime("%d/%m/%Y %I:%M %p")
            self.logger.info(f"Current time: {current_time}")

            self.handleDeposit(self.userID)
            self.clear_selection()
            time.sleep(2)

            self.open_dropdown(0)
            record_type_value = self.choose_specific_record_type("deposit")
            time.sleep(2)

            self.choose_date_range_with_current_time(current_time)
            has_records = self.verify_record_history(
                current_time=current_time, amount=amount, date_range=True, record_type_value=record_type_value
            )

            try:
                self.assertTrue(has_records, f"Expected to find deposit records but none were found")
            except AssertionError as e:
                self.fail(f"Test failed: {str(e)}")

        except Exception as e:
            self.fail(f"Test failed: {str(e)}")

    def test_07_CheckWithdrawHistory_Date(self):
        try:
            _, amount = self.test_init.submit_deposit_api(
                username=self.username, password=self.password, check_history_amount=True
            )
            self.logger.info(f"Deposit Amount: {amount}")
            self.handleDeposit(self.userID)
            turnoverIDs = self.get_turnover_ids(self.userID, self.language)
            if not turnoverIDs:
                self.fail("No turnoverIDs found")

            turnoverIncomplete, turnoverList = self.checkIncompleteTurnover(
                self.userID, checkIncomplete=True, language=self.language, transfer_check=True
            )
            self.logger.info(
                f"Turnover status before unlock - Incomplete: {turnoverIncomplete}, Locked: {turnoverList}"
            )

            complete_success = self.modify_turnover_status(self.userID, turnoverIDs, action_type="success")
            if not complete_success:
                self.fail("Failed to complete turnover")

            withdraw_amount = random.randint(50, amount)
            withdraw_success = self.test_init.withdraw_api(
                amount=withdraw_amount, username=self.username, password=self.password
            )
            self.logger.info(f"Withdraw Amount: {withdraw_amount}")
            if not withdraw_success:
                self.fail("Failed to withdraw")

            self.test_init.handleWithdrawRequest(self.userID)
            current_time = datetime.now().strftime("%d/%m/%Y %I:%M %p")
            self.open_dropdown(0)
            record_type_value = self.choose_specific_record_type("withdraw")
            time.sleep(2)
            record_types = self.check_date_record(1)
            self.logger.info(f"Found {len(record_types)} record types")
            self.logger.info(f"Record types: {record_types}")

            for record_type_id, record_type_text in record_types:
                self.logger.info(f"Testing record type: {record_type_text}")
                has_records = self.verify_record_history(
                    record_type_id=record_type_id, record_type_text=record_type_text, current_time=current_time,
                    amount=withdraw_amount, record_type_value=record_type_value
                )

                try:
                    self.assertTrue(has_records, f"Expected to find withdraw records but none were found")
                except AssertionError as e:
                    self.fail(f"Test failed: {str(e)}")

                self.open_dropdown(1)

        except Exception as e:
            self.fail(f"Test failed: {str(e)}")

    def test_08_CheckTransferHistory_Date(self):
        try:
            _, amount = self.test_init.submit_deposit_api(
                username=self.username, password=self.password, check_history_amount=True
            )
            self.logger.info(f"Deposit Amount: {amount}")
            self.handleDeposit(self.userID)
            transfer_amount = random.randint(1, amount)
            self.logger.info(f"Transfer Amount: {transfer_amount}")
            transfer_details, _ = self.transfer_to_random_game(transfer_amount, self.username, self.password)
            self.clear_selection()
            time.sleep(2)

            self.open_dropdown(0)
            record_type_value = self.choose_specific_record_type("transfer")
            time.sleep(2)

            record_types = self.check_date_record(1)
            self.logger.info(f"Found {len(record_types)} record types")
            self.logger.info(f"Record types: {record_types}")

            for record_type_id, record_type_text in record_types:
                self.logger.info(f"Testing record type: {record_type_text}")
                has_records = self.verify_record_history(
                    record_type_id=record_type_id, record_type_text=record_type_text,
                    current_time=transfer_details["timestamp"], amount=transfer_amount,
                    record_type_value=record_type_value, wallet_from=transfer_details["source_name"],
                    wallet_to=transfer_details["target_name"]
                )

                try:
                    self.assertTrue(has_records, f"Expected to find transfer records but none were found")
                except AssertionError as e:
                    self.fail(f"Test failed: {str(e)}")

                self.open_dropdown(1)
        except Exception as e:
            self.fail(f"Test failed: {str(e)}")

    def test_09_CheckPaticipateActivityHistory_Date(self):
        try:
            driver = self.driver
            promo_codes = self.test_init.get_promo_codes(self.username, self.password)
            if not promo_codes:
                self.fail("No promo codes found")

            promo_code = random.choice(promo_codes)
            self.logger.info(f"Selected Promo Code: {promo_code}")

            _, amount = self.test_init.submit_deposit_api(
                username=self.username, password=self.password, check_history_amount=True,
                promoCode=promo_code["optionCode"]
            )
            current_time = datetime.now().strftime("%d/%m/%Y %I:%M %p")
            self.logger.info(f"Current time: {current_time}")
            self.logger.info(f"Deposit Amount: {amount}")
            self.handleDeposit(self.userID)
            self.clear_selection()
            time.sleep(2)
            self.open_dropdown(0)
            record_type_value = self.choose_specific_record_type("promo")
            time.sleep(2)

            record_types = self.check_date_record(1)
            self.logger.info(f"Found {len(record_types)} record types")
            self.logger.info(f"Record types: {record_types}")

            for record_type_id, record_type_text in record_types:
                self.logger.info(f"Testing record type: {record_type_text}")
                has_records = self.verify_record_history(
                    record_type_id=record_type_id, record_type_text=record_type_text, current_time=current_time,
                    amount=amount, record_type_value=record_type_value, activity=promo_code["optionValue"]
                )

                try:
                    self.assertTrue(has_records, f"Expected to find transfer records but none were found")
                except AssertionError as e:
                    self.fail(f"Test failed: {str(e)}")

                self.open_dropdown(1)

        except Exception as e:
            self.fail(f"Test failed {str(e)}")

    def test_10_CheckRerwardHistory_DateRange(self):
        try:
            _, amount = self.test_init.submit_deposit_api(
                username=self.username, password=self.password, check_history_amount=True
            )
            current_time = datetime.now().strftime("%d/%m/%Y %I:%M %p")

            expected_reward_counts = {
                "spin": int(float(amount) / 50),
                "ticket": int(float(amount) / 150)
            }
            self.logger.info(f"Expected reward counts: {expected_reward_counts}")
            self.handleDeposit(self.userID)
            self.clear_selection()
            time.sleep(2)
            self.open_dropdown(0)
            record_type_value = self.choose_specific_record_type("reward")
            time.sleep(2)

            record_types = self.check_date_record(1)
            self.logger.info(f"Found {len(record_types)} record types")
            self.logger.info(f"Record types: {record_types}")

            for record_type_id, record_type_text in record_types:
                self.logger.info(f"Testing record type: {record_type_text}")
                has_records = self.verify_record_history(
                    record_type_id=record_type_id, record_type_text=record_type_text, current_time=current_time,
                    amount=amount, record_type_value=record_type_value, expected_reward_counts=expected_reward_counts
                )

                try:
                    self.assertTrue(has_records, f"Expected to find reward records but none were found")
                except AssertionError as e:
                    self.fail(f"Test failed: {str(e)}")

                self.open_dropdown(1)

        except Exception as e:
            self.fail(f"Test failed: {str(e)}")

    def test_11_CheckBetHistory_Date(self):
        try:
            self.driver
            transfer_details, current_time, game_win = self.setup_for_bet_test()

            self.clear_selection()
            time.sleep(2)
            self.open_dropdown(0)
            record_type_value = self.choose_specific_record_type("bet")
            time.sleep(2)

            record_types = self.check_date_record(1)
            self.logger.info(f"Found {len(record_types)} record types")
            self.logger.info(f"Record types: {record_types}")

            for record_type_id, record_type_text in record_types:
                self.logger.info(f"Testing record type: {record_type_text}")
                has_records = self.verify_record_history(
                    record_type_id=record_type_id, record_type_text=record_type_text, current_time=current_time,
                    record_type_value=record_type_value, game_win=game_win,
                    provider_name=transfer_details['target_name']
                )

                try:
                    self.assertTrue(has_records, f"Expected to find reward records but none were found")
                except AssertionError as e:
                    self.fail(f"Test failed: {str(e)}")

                self.open_dropdown(1)

        except Exception as e:
            self.fail(f"Test failed: {str(e)}")

    def test_12_CheckYesterdayBetHistory(self):
        try:
            transfer_details, current_time, game_win = self.setup_for_bet_test(use_yesterday=True)

            self.clear_selection()
            time.sleep(2)

            self.open_dropdown(0)
            record_type_value = self.choose_specific_record_type("bet")
            time.sleep(2)

            record_types = self.check_date_record(1)
            self.logger.info(f"Found {len(record_types)} record types")
            self.logger.info(f"Record types: {record_types}")
            self.logger.info(f"current_time: {current_time}")
            today_records = self.verify_record_history(
                record_type_id="date-type-option-1", current_time=current_time, record_type_value=record_type_value,
                game_win=game_win, provider_name=transfer_details['target_name']
            )
            self.open_dropdown(1)
            yesterday_records = self.verify_record_history(
                record_type_id="date-type-option-2", current_time=current_time, record_type_value=record_type_value,
                game_win=game_win, provider_name=transfer_details['target_name']
            )
            try:
                self.assertTrue(today_records, f"Expected to find today records but none were found")
                self.assertTrue(yesterday_records, f"Expected to find yesterday records but none were found")
            except AssertionError as e:
                self.fail(f"Test failed: {str(e)}")

        except Exception as e:
            self.fail(f"Test failed: {str(e)}")

    def test_13_CheckRebateHistory_Date(self):
        try:
            _, amount = self.test_init.submit_deposit_api(
                username=self.username, password=self.password, check_history_amount=True
            )
            self.logger.info(f"Deposit Amount: {amount}")
            self.handleDeposit(self.userID)
            self.logger.info(f"Current user: {self.userID}")

            rebate_info_list = []

            create_downline_api = CREDENTIALS['CreateDownline'].format(BO_base_url = CREDENTIALS["BO_base_url"], userID=self.userID)
            response = requests.get(create_downline_api)
            if response.status_code != 200:
                self.fail(f"Failed to create downline: {response.status_code}")
            else:
                self.logger.info("Downline created successfully")
                response_data = response.json()
                downline_users = {
                    "t2_users": response_data.get("data", {}).get("t2_users", []),
                    "t3_users": response_data.get("data", {}).get("t3_users", [])
                }
                self.logger.info(f"Downline Users: {downline_users}")

                # Process each user tier
                for user_tier in downline_users:
                    for tier_user in downline_users[user_tier]:
                        self.logger.info(f"Processing Tier User: {tier_user['id']}")
                        deposit_result = self.test_init.submit_deposit_api(
                            username=tier_user['username'], password=tier_user['password'], check_history_amount=True,
                            amount=random.randint(250, 2000)
                        )

                        if isinstance(deposit_result, tuple) and len(deposit_result) == 2:
                            _, user_amount = deposit_result
                        else:
                            self.logger.warning(
                                f"submit_deposit_api returned {deposit_result} instead of expected tuple. Using default amount."
                            )
                            user_amount = 500
                            if deposit_result is False:
                                self.logger.error("Deposit failed, but continuing with default amount")

                        self.logger.info(f"Deposit Amount: {user_amount}")
                        self.handleDeposit(tier_user['id'])
                        rebate_percentage = 0

                        check_rebate_percentage = CREDENTIALS['CheckRebatePercentage'].format(BO_base_url = CREDENTIALS["BO_base_url"])
                        response = requests.get(check_rebate_percentage)
                        if response.status_code != 200:
                            self.fail(f"Failed to check rebate percentage: {response.status_code}")

                        rebate_data = response.json()
                        tier_level = "2" if user_tier == "t2_users" else "3"

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
                            remaining_providers = [p for p in remaining_providers if p["provider_id"] != 32]

                            while remaining_providers and not transfer_success:

                                chosen_provider = random.choice(remaining_providers)

                                provider_id = chosen_provider["provider_id"]
                                rebate_percentage = chosen_provider["rebate_percentage"]
                                self.logger.info(f"Chosen Provider: {chosen_provider}")
                                self.logger.info(f"Provider ID: {provider_id}")
                                self.logger.info(f"Rebate Percentage: {rebate_percentage}")

                                transfer_details, proceed = self.transfer_to_random_game(
                                    amount=random.randint(250, 2000), username=tier_user['username'],
                                    password=tier_user['password'], provider_id=provider_id
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
                                    amount=random.randint(250, 2000), username=tier_user['username'],
                                    password=tier_user['password']
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
                                amount=250, username=tier_user['username'], password=tier_user['password']
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
                        place_bet_url = f"{CREDENTIALS['PlaceBet'].format(BO_base_url = CREDENTIALS["BO_base_url"], userID=tier_user['id'], transfer_amount=user_amount, type=1, game_id=transfer_details['target_id'], game_record_date=current_date)}"
                        response = requests.get(place_bet_url)
                        self.logger.info(f"userid: {tier_user['id']}")
                        self.logger.info(f"Response: {response.status_code}")
                        if response.status_code != 200:
                            self.fail(f"Failed to place bet: {response.status_code}")
                        else:
                            self.logger.info("Bet placed successfully")

            self.logger.info(f"Collected rebate info for {len(rebate_info_list)} users")
            current_month = datetime.now().strftime("%Y-%m")
            self.logger.info(f"Current user: {self.userID}")
            self.logger.info(f"Current month: {current_month}")
            rebate_simulation_url = f"{CREDENTIALS['CreateRebate'].format(BO_base_url = CREDENTIALS["BO_base_url"], userID=self.userID, current_month=current_month)}"
            response = requests.get(rebate_simulation_url)
            if response.status_code != 200:
                self.fail(f"Failed to create rebate: {response.status_code}")
            else:
                self.logger.info("Rebate created successfully")

            self.clear_selection()
            time.sleep(2)
            self.open_dropdown(0)
            record_type_value = self.choose_specific_record_type("rebate")
            time.sleep(2)

            record_types = self.check_date_record(1)
            self.logger.info(f"Found {len(record_types)} record types")

            if len(rebate_info_list) > 0:
                self.logger.info(f"First rebate info: {rebate_info_list[0]}")
                if len(rebate_info_list) > 1:
                    self.logger.info(f"Second rebate info: {rebate_info_list[1]}")

            for record_type_id, record_type_text in record_types:
                self.logger.info(f"Testing record type: {record_type_text}")

                has_records = self.verify_record_history(
                    record_type_id=record_type_id, record_type_text=record_type_text,
                    record_type_value=record_type_value, rebate_info=rebate_info_list
                )

                try:
                    self.assertTrue(has_records, f"Expected to find rebate records but none were found")
                except AssertionError as e:
                    self.fail(f"Test failed: {str(e)}")

                self.open_dropdown(1)

        except Exception as e:
            self.logger.error(f"Error in test_14_CheckRebateHistory_Date: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            self.fail(f"Test failed: {str(e)}")

    def test_14_OutofDateRange(self):
        try:
            self.test_init.submit_deposit_api(username=self.username, password=self.password, check_history_amount=True)
            current_time = datetime.now().strftime("%d/%m/%Y %I:%M %p")
            self.logger.info(f"Current time: {current_time}")

            self.handleDeposit(self.userID)
            self.clear_selection()
            time.sleep(2)

            self.open_dropdown(0)
            self.choose_specific_record_type("deposit")
            time.sleep(2)

            self.choose_date_range_with_current_time(current_time, isoutofrange=True)

            try:
                table = WebDriverWait(self.driver, 5).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, "table.MuiTable-root"))
                )
                rows = table.find_elements(By.CSS_SELECTOR, "tbody.MuiTableBody-root tr")
                if len(rows) > 0:
                    first_row = rows[0]
                    cells = first_row.find_elements(By.CSS_SELECTOR, "td.MuiTableCell-body")

                    no_record_message = LANGUAGE_SETTINGS[self.language]["history"]["no_record"]
                    self.logger.info(f"Expected 'no record' message: {no_record_message}")
                    self.logger.info(f"Actual message: {cells[0].text}")

                    if cells[0].text == no_record_message:
                        self.logger.info("✓ 'No record' message displayed correctly for out-of-range dates")
                    else:
                        self.fail(f"✗ Expected 'no record' message but found: {cells[0].text}")
                else:
                    self.fail("✗ Table rows not found")
            except TimeoutException:
                self.fail("✗ Table not found after setting out-of-range dates")

        except Exception as e:
            self.logger.error(f"Error in test_14_OutofDateRange: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            self.fail(f"Test failed: {str(e)}")


if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)
    unittest.main()
