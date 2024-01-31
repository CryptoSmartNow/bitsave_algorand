from pathlib import Path

import pytest
from algokit_utils import (
    get_algod_client,
    is_localnet,
    ApplicationSpecification,
    ApplicationClient,
    get_localnet_default_account,
    
)
from algosdk.v2client.algod import AlgodClient
from dotenv import load_dotenv
from beaker import localnet, consts, client

from smart_contracts.bitsave import contract as bitsave_contract
from algosdk.atomic_transaction_composer import (
    AtomicTransactionComposer,
    TransactionWithSigner,
)
from algosdk import transaction

from tests.constants import funded_acct


@pytest.fixture(scope="session")
def bitsave_app_spec(algod_client: AlgodClient) -> ApplicationSpecification:
    return bitsave_contract.app.build(algod_client)


@pytest.fixture(autouse=True, scope="session")
def environment_fixture() -> None:
    env_path = Path(__file__).parent.parent / ".env.localnet"
    load_dotenv(env_path)


@pytest.fixture(scope="session")
def algod_client() -> AlgodClient:
    client = get_algod_client()

    # you can remove this assertion to test on other networks,
    # included here to prevent accidentally running against other networks
    assert is_localnet(client)
    return client


@pytest.fixture(scope="session")
def childId(bitsave_client: ApplicationClient, algod_client: AlgodClient):
    atc = AtomicTransactionComposer()
    sp = algod_client.suggested_params()
    ptxn = transaction.PaymentTxn(
        sender=funded_acct.address,
        amt=3_000_000,
        sp=sp,
        receiver=bitsave_client.app_address,
    )
    join = transaction.ApplicationOptInTxn(
        sender=funded_acct.address,
        sp=sp,
        index=bitsave_client.app_id,
        accounts=[funded_acct.address],
        app_args=[],
        foreign_apps=[0],
    )
    ptxn_w_signer = TransactionWithSigner(ptxn, funded_acct.signer)
    jtxn_w_signer = TransactionWithSigner(join, funded_acct.signer)
    atc.add_transaction(ptxn_w_signer)
    atc.add_transaction(jtxn_w_signer)
    atc.build_group()
    response = bitsave_client.execute_atc(atc)
    print(response)

    result = bitsave_client.call("get_child_id")
    print(result.return_value)
    return result.return_value

@pytest.fixture(scope="session")
def bitsave_client(
    algod_client: AlgodClient, bitsave_app_spec: ApplicationSpecification
) -> ApplicationClient:
    bclient = ApplicationClient(
        algod_client,
        app_spec=bitsave_app_spec,
        signer=get_localnet_default_account(algod_client),
    )
    bclient.create()
    print("AppId: ", bclient.app_id)
    client.ApplicationClient(
        client=algod_client, app=bitsave_app_spec, app_id=bclient.app_id,
        signer=get_localnet_default_account(algod_client)
    ).fund(2 * consts.algo)

    print(bclient.app_id)
    return bclient
