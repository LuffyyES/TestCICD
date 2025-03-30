import unittest
import time
import requests
import json
import random
from tests.authentication_test.base_test import BaseTest
from tests.test_init import TestInit
from config.constant import LANGUAGE_SETTINGS, CREDENTIALS
import pandas as pd
from datetime import datetime


class TestProviderToProvider(BaseTest):

    def __init__(self, methodName="runTest", language=None, browser=None):
        super().__init__(methodName, language, browser)
        self.test_init = TestInit(methodName="runTest", language=language, browser=browser)

    def setUp(self):
        self.TRANSFER_AMOUNT = 2.0

    def get_main_account_balance(self, headers):
        response = requests.get(f"{CREDENTIALS['BO_base_url']}/api/balance", headers=headers)
        response.raise_for_status()
        return response.json().get("data")["balance"]

    def make_transfer(self, headers, source_id, target_id, amount):
        payload = {
            "source_id": source_id,
            "target_id": target_id,
            "amount": amount
        }
        response = requests.post(f"{CREDENTIALS['BO_base_url']}/api/transfers", json=payload, headers=headers)
        return response

    def print_game_data(self, label, game_data):
        print(f"{label}:\n")
        formatted_data = json.dumps(game_data, indent=4, ensure_ascii=False)
        print(formatted_data + "\n")

    def revert_all(self, headers):
        response = requests.post(f"{CREDENTIALS['BO_base_url']}/api/revertAll", headers=headers)
        return response

    def get_id_api(self, headers):
        response = requests.get(f"{CREDENTIALS['BO_base_url']}/api/user", headers=headers)
        return response.json().get("data")["id"]

    def test_01_RandomProviderToProviderTransfer(self):
        try:
            print("\n=== Provider to Provider Transfer Test ===")
            print("1. Setting up test account...")
            username, password = self.test_init.register_new_account()
            token = self.login(username, password)
            if not token:
                self.fail("Failed to get token")

            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "Content-Type": "application/json"
            }

            print("2. Making initial deposit...")
            userID = self.get_id_api(headers)
            self.test_init.submit_deposit_api(username=username, password=password, amount=10000)
            self.handleDeposit(userID)

            print("3. Getting provider list...")
            initial_game_data = sorted(self.get_game_ids(headers), key=lambda x: x["id"])
            provider_list = [game for game in initial_game_data if game["id"] > 0]

            print("\n4. Funding providers from main wallet...")
            print(f"Total providers to fund: {len(provider_list)}")
            funded_providers = []
            failed_providers = []

            for i, provider in enumerate(provider_list, 1):
                print(f"\rFunding provider {i}/{len(provider_list)}: {provider['name']}", end="")
                setup_response = self.make_transfer(
                    headers, source_id=0, target_id=provider["id"], amount=self.TRANSFER_AMOUNT * 2
                )
                if setup_response.status_code == 200:
                    funded_providers.append(provider)
                else:
                    error_msg = setup_response.json().get("message", "Unknown error")
                    failed_providers.append({
                        "name": provider["name"],
                        "id": provider["id"],
                        "error": error_msg
                    })
            print(f"\nSuccessfully funded: {len(funded_providers)} providers")
            print(f"Failed to fund: {len(failed_providers)} providers")

            if not funded_providers:
                self.fail("No providers were successfully funded for testing")

            print("\n5. Testing random transfers between providers...")
            updated_game_data = sorted(self.get_game_ids(headers), key=lambda x: x["id"])
            provider_list = [
                game for game in updated_game_data
                if game["id"] > 0 and any(fp["id"] == game["id"]
                                          for fp in funded_providers) and float(game["credit"]) > 0
            ]

            transfer_results = []
            total_transfers = 50
            print(f"Planning {total_transfers} random transfers")

            for i in range(total_transfers):
                print(f"\rProcessing transfer {i+1}/{total_transfers}", end="")
                source = random.choice(provider_list)
                target = random.choice([p for p in provider_list if p["id"] != source["id"]])

                response = self.make_transfer(
                    headers, source_id=source["id"], target_id=target["id"], amount=self.TRANSFER_AMOUNT
                )

                result = {
                    "Source Provider": f"{source['name']} (ID: {source['id']})",
                    "Target Provider": f"{target['name']} (ID: {target['id']})",
                    "Amount": self.TRANSFER_AMOUNT,
                    "Status": "Success" if response.status_code == 200 else "Failed",
                    "Response Code": response.status_code,
                    "Error Message": response.json().get("message") if response.status_code != 200 else ""
                }
                transfer_results.append(result)

            print("\n\n6. Generating report...")
            # Create Excel report with additional sheet for failed initial transfers
            df = pd.DataFrame(transfer_results)
            failed_df = pd.DataFrame(failed_providers)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            excel_path = f"test_results/provider_to_provider_test_{timestamp}.xlsx"

            with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                # Summary statistics
                success_count = len([r for r in transfer_results if r["Status"] == "Success"])
                unique_errors = set(r["Error Message"] for r in transfer_results if r["Status"] == "Failed")

                summary_data = {
                    "Metric": [
                        "Total Providers", "Successfully Funded Providers", "Failed Funding Providers",
                        "Total Transfers Attempted", "Successful Transfers", "Failed Transfers", "Success Rate (%)",
                        "Unique Error Messages"
                    ],
                    "Value": [
                        len(initial_game_data) - 1,  # Total providers (excluding main wallet)
                        len(funded_providers),
                        len(failed_providers),
                        len(transfer_results),  # Total transfers attempted
                        success_count,
                        len(transfer_results) - success_count,
                        round(success_count * 100 / len(transfer_results), 2) if transfer_results else 0,
                        "\n".join(unique_errors)
                    ]
                }
                pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)

                # Transfer details
                df.to_excel(writer, sheet_name='Transfer Details', index=False)

                # Failed initial transfers
                if failed_providers:
                    failed_df.to_excel(writer, sheet_name='Failed Initial Transfers', index=False)

            print(f"\nTest completed! Results saved to: {excel_path}")
            success_rate = round(success_count * 100 / len(transfer_results), 2) if transfer_results else 0
            print(f"Success rate: {success_rate}%")

        except Exception as e:
            self.logger.error(f"Test failed: {str(e)}")
            self.fail(f"Test failed: {str(e)}")


if __name__ == "__main__":
    unittest.main()
