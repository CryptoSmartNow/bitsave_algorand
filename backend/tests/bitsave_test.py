import pytest
from algokit_utils import (
    ApplicationClient,
    ApplicationSpecification,
    get_localnet_default_account,
)
from algosdk.v2client.algod import AlgodClient
from beaker import localnet, client as bClient, consts

from smart_contracts.bitsave import contract as bitsave_contract
from algosdk.atomic_transaction_composer import (
    AtomicTransactionComposer,
    TransactionWithSigner,
)
from algosdk import transaction

from tests.constants import funded_acct
from time import time


@pytest.fixture(scope="session")
def bitsave_app_spec(algod_client: AlgodClient) -> ApplicationSpecification:
    return bitsave_contract.app.build(algod_client)


@pytest.fixture(scope="session")
def bitsave_client(
    algod_client: AlgodClient, bitsave_app_spec: ApplicationSpecification
) -> ApplicationClient:
    client = ApplicationClient(
        algod_client,
        app_spec=bitsave_app_spec,
        # signer=get_localnet_default_account(algod_client),
        signer=funded_acct.signer,
    )
    client.create()
    print("AppId: ", client.app_id)
    bClient.ApplicationClient(
        client=algod_client,
        app=bitsave_app_spec,
        app_id=client.app_id,
        # signer=get_localnet_default_account(algod_client),
        signer=funded_acct.signer,
    ).fund(2 * consts.algo)

    print(client.app_id)
    return client


# def test_opt_in(bitsave_client: ApplicationClient, algod_client: AlgodClient) -> None:
#     atc = AtomicTransactionComposer()
#     sp = algod_client.suggested_params()
#     print(sp)
#     ptxn = transaction.PaymentTxn(
#         sender=funded_acct.address,
#         amt=3_000_000,
#         sp=sp,
#         receiver=bitsave_client.app_address,
#     )
#     join = transaction.ApplicationOptInTxn(
#         sender=funded_acct.address,
#         sp=sp,
#         index=bitsave_client.app_id,
#         accounts=[funded_acct.address],
#         app_args=[],
#         foreign_apps=[0],
#     )

#     ptxn_w_signer = TransactionWithSigner(ptxn, funded_acct.signer)
#     jtxn_w_signer = TransactionWithSigner(join, funded_acct.signer)
#     atc.add_transaction(ptxn_w_signer)
#     atc.add_transaction(jtxn_w_signer)
#     atc.build_group()
#     response = bitsave_client.execute_atc(atc)
#     print(response.tx_ids)


def makePaymentTxn(receiver, amount: int, sp):
    pay_txn = transaction.PaymentTxn(
        sender=funded_acct.address, receiver=receiver, amt=amount, sp=sp
    )
    return TransactionWithSigner(pay_txn, funded_acct.signer)


name_savings = "school"


def test_create_savings(
    bitsave_client: ApplicationClient, algod_client: AlgodClient, childId
) -> None:
    print("Testing create savings with ", childId)
    atc = AtomicTransactionComposer()
    sp = algod_client.suggested_params()
    ptxn = makePaymentTxn(bitsave_client.app_address, 2_000_000, sp)
    bitsave_client.add_method_call(
        atc=atc,
        abi_method=bitsave_contract.create_savings,
        parameters={
            "foreign_apps": [childId],
        },
        abi_args={
             "pay_txn": ptxn,
            "name": name_savings,
            "end_time": round(time()) + 1_000_000,
            "penalty": 2,
            "asset_id": 1,
            "interest": 0,
            "isOpted": 1,
            "charges": 30_000,
        },
        # foreign_apps=[childId],
    )
    # atc.add_method_call(
    #     app_id=bitsave_client.app_id,
    #     method=bitsave,
    #     sender=funded_acct.address,
    #     signer=funded_acct.signer,
    #     sp=sp,
    # "pay_txn": ptxn,
    #         "name": name_savings,
    #         "end_time": round(time()) + 1_000_000,
    #         "penalty": 2,
    #         "asset_id": 1,
    #         "interest": 0,
    #         "isOpted": 1,
    #         "charges": 30_000,
    #     method_args=[
    #         ptxn,
    #         name_savings,
    #         round(time()) + 1_000_000,
    #         2,
    #         1,
    #         0,
    #         1,
    #         30_000,
    #     ],
    #     foreign_apps=[childId],
    #     # accounts=[BITSAVE_ADDRESS],
    # )
    result = atc.execute(algod_client, 2)
    for res in result.abi_results:
        print(res.return_value)
