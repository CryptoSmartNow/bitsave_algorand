import pytest
from algokit_utils import (
    ApplicationClient,
    ApplicationSpecification,
    get_localnet_default_account,
)
from algosdk.v2client.algod import AlgodClient

from smart_contracts.bitsave import contract as bitsave_contract


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


def test_says_hello(bitsave_client: ApplicationClient) -> None:
    result = bitsave_client.call(bitsave_contract.hello, name="World")

    assert result.return_value == "Hello, World"
