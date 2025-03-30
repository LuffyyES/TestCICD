import unittest
import time
import requests
import json
from tests.authentication_test.base_test import BaseTest
from config.constant import LANGUAGE_SETTINGS, CREDENTIALS
import pandas as pd
from datetime import datetime
import random
from tests.transfer_test.transfer_base import TransferBase


class TestMainProvider(TransferBase):

    def __init__(self, methodName="runTest", language=None, browser=None):
        super().__init__(methodName, language, browser)
        self.TRANSFER_AMOUNT = 2.0

    def setUp(self):
        #super().setUp()
        pass

    def test_01_TransferToAllProviders(self):
        try:
            print("\n=== Main to Provider Transfer Test ===")
            print("1. Setting up test account...")
            username, password = self.register_new_account()
            token = self.login(username, password)

            if not token:
                return

            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "Content-Type": "application/json"
            }

            print("2. Making initial deposit...")
            userID = self.get_id_api(headers)
            self.submit_deposit_api(username=username, password=password, amount=10000)
            self.handleDeposit(userID)

            print("3. Getting provider list...")
            initial_balance = self.get_main_account_balance(headers)

            print("\n4. Testing transfers to each provider...")
            transfer_results = self.transfer_to_all_providers(headers, initial_balance)

            print("\n5. Main Wallet Summary:")
            print(f"Initial Balance: RM {transfer_results['initial_balance']}")
            print(f"Final Balance: RM {transfer_results['final_balance']}")
            total_transferred = len(transfer_results['successful_transfers']) * self.TRANSFER_AMOUNT
            print(f"Total Amount Transferred: RM {total_transferred}")
            print(
                f"Balance Change: RM {float(transfer_results['initial_balance']) - float(transfer_results['final_balance']):.2f}"
            )

            print("\n6. Generating report...")
            df = pd.DataFrame(transfer_results['test_results'])
            df = df[[
                "Game ID", "Game Name", "Initial Balance", "Transfer Amount", "Expected Balance", "Final Balance",
                "Status", "Response Code", "Error Message"
            ]]

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            excel_path = f"test_results/main_provider_transfer_test_{timestamp}.xlsx"

            with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                success_count = len(transfer_results['successful_transfers'])
                unique_errors = set(
                    r["Error Message"] for r in transfer_results['test_results'] if r["Status"] == "Failed"
                )

                summary_data = {
                    "Metric": [
                        "Total Providers Tested", "Successful Transfers", "Failed Transfers", "Success Rate (%)",
                        "Initial Main Balance", "Final Main Balance", "Total Amount Transferred",
                        "Unique Error Messages"
                    ],
                    "Value": [
                        len(transfer_results['test_results']), success_count,
                        len(transfer_results['test_results']) - success_count,
                        round(success_count * 100 /
                              len(transfer_results['test_results']), 2) if transfer_results['test_results'] else 0,
                        f"RM {transfer_results['initial_balance']}", f"RM {transfer_results['final_balance']}",
                        f"RM {total_transferred}", "\n".join(unique_errors)
                    ]
                }
                pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)
                df.to_excel(writer, sheet_name='Transfer Details', index=False)

            print(f"\nTest completed! Results saved to: {excel_path}")
            success_rate = round(success_count * 100 /
                                 len(transfer_results['test_results']), 2) if transfer_results['test_results'] else 0
            print(f"Success rate: {success_rate}%")
            print(f"Successful transfers: {len(transfer_results['successful_transfers'])}")
            print(f"Failed transfers: {len(transfer_results['failed_transfers'])}")

        except Exception as e:
            self.logger.error(f"Test failed: {str(e)}")
            self.fail(f"Test failed: {str(e)}")


if __name__ == "__main__":
    unittest.main()
