# import pytest
# from algokit_utils import (
#     ApplicationClient,
#     ApplicationSpecification,
#     get_localnet_default_account,
# )
# from algosdk.v2client.algod import AlgodClient
# from beaker import localnet

# from smart_contracts.bitsave import contract as bitsave_contract
# from algosdk.atomic_transaction_composer import (
#     AtomicTransactionComposer,
#     TransactionWithSigner,
# )
# from algosdk import transaction
# from tests.constants import funded_acct
# import time


# def makePaymentTxn(receiver, amount: int, sp):
#     pay_txn = transaction.PaymentTxn(
#         sender=funded_acct.address, receiver=receiver, amt=amount, sp=sp
#     )
#     return TransactionWithSigner(pay_txn, funded_acct.signer)


# name_savings = "school"


# def test_create_savings(
#     bitsave_client: ApplicationClient, algod_client: AlgodClient, childId
# ) -> None:
#     atc = AtomicTransactionComposer()
#     sp = algod_client.suggested_params()
#     ptxn = makePaymentTxn(bitsave_client.app_address, 2_000_000)
#     atc.add_method_call(
#         app_id=bitsave_client.app_id,
#         method=bitsave_contract.create_savings.method_signature(),
#         sender=funded_acct.address,
#         signer=funded_acct.signer,
#         sp=sp,
#         method_args=[
#             ptxn,
#             name_savings,
#             (round(time()) + 1_000_000),
#             2,
#             1,
#             0,
#             1,
#             30_000,
#         ],
#         foreign_apps=[childId],
#         # accounts=[BITSAVE_ADDRESS],
#     )
#     result = atc.execute(bitsave_client, 2)
#     for res in result.abi_results:
#         print(res.return_value)
