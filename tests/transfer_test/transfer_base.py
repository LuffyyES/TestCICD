from tests.authentication_test.base_test import BaseTest
from tests.test_init import TestInit
import requests
from config.constant import CREDENTIALS
import random
import pandas as pd
from datetime import datetime
import json
import math


class TransferBase(BaseTest):

    def __init__(self, methodName="runTest", language=None, browser=None):
        super().__init__(methodName, language, browser)
        self.test_init = TestInit(methodName="runTest", language=language, browser=browser)
        self.TRANSFER_AMOUNT = float(CREDENTIALS['transfer_amount']['amount'])

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

    def get_id_api(self, headers):
        response = requests.get(f"{CREDENTIALS['BO_base_url']}/api/user", headers=headers)
        return response.json().get("data")["id"]

    def transfer_to_all_providers(self, headers, initial_balance=None, provider_count=None, revert_mode=False, part=1):

        all_games = sorted(self.get_game_ids(headers), key=lambda x: x["id"])

        providers = [game for game in all_games if game["id"] > 0]
        total_providers = len(providers)
        self.logger.info(f"Total providers available: {total_providers}")

        batch_size = int(CREDENTIALS['revert_batch_size']['batch_size'])
        num_parts = math.ceil(total_providers / batch_size)

        if not hasattr(self, 'processed_providers'):
            self.processed_providers = set()

        if revert_mode:
            start_idx = (part - 1) * batch_size
            if part < num_parts:

                end_idx = start_idx + batch_size
                selected_providers = providers[start_idx:end_idx]
            else:
                selected_providers = providers[start_idx:]

            print(f"Total parts needed: {num_parts}")
            print(
                f"Part {part} of {num_parts}: Processing providers {start_idx + 1} to {start_idx + len(selected_providers)}"
            )
            print(f"Selected {len(selected_providers)} providers for this batch")

            initial_game_data = [
                provider for provider in selected_providers if str(provider['id']) not in self.processed_providers
            ]

            print(f"Using part {part} of {num_parts} with {len(initial_game_data)} unprocessed providers")
        else:
            if provider_count:
                self.provider_count = provider_count
            else:
                self.provider_count = len(providers)
            initial_game_data = random.sample(providers, min(self.provider_count, len(providers)))
            self.logger.info(f"Randomly selected {len(initial_game_data)} providers")

        provider_count = len(initial_game_data)
        print(f"Selected {provider_count} providers from {len(providers)} total providers")
        print(f"Initial main wallet balance: RM {initial_balance}")

        successful_transfers = []
        failed_transfers = []
        failed_game_ids = []
        test_results = []
        total_expected_credit = 0

        current = 0
        for game in initial_game_data:
            game_id = game.get("id")
            if game_id < 1:
                continue

            current += 1
            print(f"\rProcessing provider {current}/{provider_count}: {game.get('name')}", end="")

            self.processed_providers.add(str(game_id))

            initial_credit = float(game.get("credit"))
            response = self.make_transfer(headers, source_id=0, target_id=game_id, amount=self.TRANSFER_AMOUNT)

            updated_game_data = self.get_game_ids(headers)
            updated_game = next((g for g in updated_game_data if g["id"] == game_id), None)
            final_credit = float(updated_game.get("credit", 0)) if updated_game else 0

            if response.status_code == 200:
                total_expected_credit += self.TRANSFER_AMOUNT

            result = {
                "Game ID": game_id,
                "Game Name": game.get("name"),
                "Initial Balance": initial_credit,
                "Transfer Amount": self.TRANSFER_AMOUNT,
                "Expected Balance": initial_credit +
                self.TRANSFER_AMOUNT if response.status_code == 200 else initial_credit,
                "Final Balance": final_credit,
                "Status": "Success" if response.status_code == 200 else "Failed",
                "Response Code": response.status_code,
                "Error Message": response.json().get("message") if response.status_code != 200 else ""
            }
            test_results.append(result)

            if response.status_code == 200:
                successful_transfers.append(game_id)
            else:
                error_msg = response.json().get("message")
                failed_transfers.append(f"{game_id}: {game.get('name')} failing with reason: {error_msg}")
                failed_game_ids.append(game_id)

        final_balance = self.get_main_account_balance(headers)
        return {
            'initial_balance': initial_balance,
            'final_balance': final_balance,
            'successful_transfers': successful_transfers,
            'failed_transfers': failed_transfers,
            'failed_game_ids': failed_game_ids,
            'test_results': test_results,
            'total_expected_credit': total_expected_credit
        }

    def setup_deposit_transfer(self, provider_count=None, revert_mode=False, part=1):
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
        self.test_init.submit_deposit_api(username=username, password=password, amount=random.randint(5001, 10000))
        self.test_init.handleDeposit(userID)

        initial_balance = self.get_main_account_balance(headers)

        print("\n3. Transferring to all providers...")
        transfer_results = self.transfer_to_all_providers(
            headers, initial_balance, provider_count, revert_mode=revert_mode, part=part
        )

        game_details = []
        for game_id in transfer_results['successful_transfers']:
            game_data = next((g for g in self.get_game_ids(headers) if g["id"] == game_id), None)
            if game_data:
                game_details.append({
                    'id': game_id,
                    'name': game_data.get('name'),
                    'credit': game_data.get('credit')
                })

        print("\n6. Generating report...")
        total_transferred = len(transfer_results['successful_transfers']) * self.TRANSFER_AMOUNT
        df = pd.DataFrame(transfer_results['test_results'])
        df = df[[
            "Game ID", "Game Name", "Initial Balance", "Transfer Amount", "Expected Balance", "Final Balance", "Status",
            "Response Code", "Error Message"
        ]]

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        excel_path = f"test_results/main_provider_transfer_test_{timestamp}.xlsx"

        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            success_count = len(transfer_results['successful_transfers'])
            unique_errors = set(r["Error Message"] for r in transfer_results['test_results'] if r["Status"] == "Failed")

            summary_data = {
                "Metric": [
                    "Total Providers Tested", "Successful Transfers", "Failed Transfers", "Success Rate (%)",
                    "Initial Main Balance", "Final Main Balance", "Total Amount Transferred", "Unique Error Messages"
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

        return {
            'username': username,
            'password': password,
            'game_details': game_details,
            'transfer_results': transfer_results,
            'total_expected_credit': transfer_results['total_expected_credit']
        }
