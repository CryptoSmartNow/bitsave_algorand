import pytest
from algokit_utils import (
    ApplicationClient,
    ApplicationSpecification,
    get_localnet_default_account,
)
from algosdk.v2client.algod import AlgodClient
from beaker import localnet

from smart_contracts.bitsave import contract as bitsave_contract
from algosdk.atomic_transaction_composer import AtomicTransactionComposer, TransactionWithSigner
from algosdk import transaction


accts = localnet.get_accounts()
print(accts)
acct1 = accts.pop()
acct2 = accts.pop()
acct3 = accts.pop()

funded_acct = localnet.LocalAccount(address="F6WXY5ZY5FWWAQYXPR2QBRX36EH2OCEA6R6MQV66ULIKXLULCGVJFQJA6I", private_key="D/XZYezjUtPI38IdWYgqP4poIkfQKEYp62nAvSQq4PMvrXx3OOltYEMXfHUAxvvxD6cIgPR8yFfeotCrrosRqg==")

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
        signer=get_localnet_default_account(algod_client),
    )
    client.create()
    return client


# def test_says_hello(bitsave_client: ApplicationClient) -> None:
#     result = bitsave_client.call(bitsave_contract.hello, name="World")

#     print(result.return_value)

#     assert result.return_value == "Hello, World"


def test_opt_in(bitsave_client: ApplicationClient, algod_client: AlgodClient) -> None:
    atc = AtomicTransactionComposer()
    sp = algod_client.suggested_params()
    print(sp)
    ptxn = transaction.PaymentTxn(
            sender=funded_acct.address,
            amt=3_000_000,
            sp=sp,
            receiver=bitsave_client.app_address
        )
    join = transaction.ApplicationOptInTxn(
        sender=funded_acct.address,
        sp=sp,
        index=bitsave_client.app_id,
        accounts=[funded_acct.address],
        app_args=[],
        foreign_apps=[0]
    )

    ptxn_w_signer = TransactionWithSigner(ptxn, funded_acct.signer)
    jtxn_w_signer = TransactionWithSigner(join, funded_acct.signer)
    atc.add_transaction(ptxn_w_signer)
    atc.add_transaction(jtxn_w_signer)
    atc.build_group()
    response = bitsave_client.execute_atc(atc)
    print(response.tx_ids)
