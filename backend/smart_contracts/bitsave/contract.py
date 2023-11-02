import beaker
from typing import Final
import pyteal as pt
from pyteal import (
    abi,
    App,
    AppParam,
    Addr,
    TealType,
    Log,
    Global,
    Expr,
    Approve,
    Seq,
    Concat,
    Bytes,
    InnerTxnBuilder,
    InnerTxn,
    TxnType,
    TxnField,
    Txn,
    Int,
    Not,
    Itob,
    ScratchVar,
    If,
    Assert,
    Gtxn,
    Subroutine,
)

### Child contract
from smart_contracts.bitsave.contract_child import bitsave_child_app
from smart_contracts.utils import send_token
from algosdk.encoding import decode_address
from smart_contracts.constants import BITSAVE_ADDRESS


# Define constants else where please
OPT_FEE = 2_400_000


# State class
class BitsaveMainState:
    user_child_contract_id: Final[beaker.LocalStateValue] = beaker.LocalStateValue(
        stack_type=pt.TealType.uint64, descr="The app id of the user's child contract"
    )


bitsave = beaker.Application(
    "bitsave",
    state=BitsaveMainState(),
    descr="This is the bitsave parent protocol v2.0",
)


# @bitsave.external
# def hello(name: pt.abi.String, *, output: pt.abi.String) -> pt.Expr:
#     return output.set(pt.Concat(pt.Bytes("Hello, "), name.get()))


@bitsave.create
def create():
    return pt.Seq(bitsave.initialize_global_state())


@bitsave.update(authorize=beaker.Authorize.only_creator())
def update():
    return pt.Approve()


@bitsave.delete(authorize=beaker.Authorize.only_creator())
def delete():
    return pt.Approve()


# -------------> Opt a new user into bitsave
@bitsave.opt_in  # TODO: bare = True
def opt_in(*, output: pt.abi.Uint64):
    """
    Opt in does a bit of operations
    1. Creates a child contract for the user and gets the id
    2. Stores the child contract id in the user's local storage
    3. In subsequent calls, it fetches the id from the storage
    :return:
    app_id of the child contact
    """
    child_contract_pc = beaker.precompiled(bitsave_child_app)  # TODO: child contract
    return pt.Seq(
        (pay := pt.ScratchVar()).store(pt.Gtxn[0].amount()),
        pt.Assert(pay.load() > pt.Int(OPT_FEE)),
        bitsave.initialize_local_state(),
        pt.InnerTxnBuilder.Execute(
            {
                **child_contract_pc.get_create_config(),  # TODO: confirm if still follows
            }
        ),
        (child_id := pt.abi.Uint64()).set(pt.InnerTxn.created_application_id()),
        (child_addr_maybe := pt.AppParam.address(child_id.get())),
        pt.Assert(child_addr_maybe.hasValue()),
        (child_addr := pt.ScratchVar()).store(child_addr_maybe.value()),
        # Fund child contract
        pt.InnerTxnBuilder.Execute(
            {
                pt.TxnField.type_enum: pt.TxnType.Payment,
                pt.TxnField.amount: pt.Int(OPT_FEE - 1_000_000),
                pt.TxnField.receiver: child_addr.load(),
            }
        ),
        # store the child app id in user's local storage
        bitsave.state.user_child_contract_id[pt.Txn.sender()].set(child_id.get()),
        # return the child app id
        output.set(child_id.get()),
    )


# # Create savings functionality
@bitsave.external
def create_savings(
    pay_txn: abi.PaymentTransaction,
    name: abi.String,
    end_time: abi.Uint64,
    penalty: abi.Uint64,
    # percentage: abi.Uint64,  # the percentage for profit
    asset_id: abi.Asset,  # the id of the asset
    interest: abi.Uint64,  # interest in CSA of the savings
    isOpted: abi.Uint8,  # is child opted into asset, 1 for true
    charges: abi.Uint64,
    *,
    output: abi.Uint64,
):
    return Seq(
        # is name available
        confirm_name := App.globalGetEx(
            bitsave.state.user_child_contract_id[Txn.sender()],
            Concat(Bytes("name"), name.get()),
        ),
        Assert(Not(confirm_name.hasValue())),
        # asset_balance := AssetHolding.balance(self.user_child_contract_id[Txn.sender()], asset_id.asset_id()),
        # Assert(asset_balance.hasValue()),
        # take principal with type of asset
        (principal := ScratchVar()).store(
            If(
                pay_txn.get().type_enum() == TxnType.AssetTransfer,
                pay_txn.get().asset_amount() - charges.get(),
                pay_txn.get().amount() - charges.get(),
            )
        ),
        (amount := abi.Uint64()).set(principal.load()),
        (asset_uint := abi.Uint64()).set(asset_id.asset_id()),
        child_address := AppParam.address(
            bitsave.state.user_child_contract_id[Txn.sender()]
        ),
        Assert(child_address.hasValue()),
        InnerTxnBuilder.Begin(),
        # opt child to asset if not yet
        If(isOpted.get() != Int(1)).Then(
            Seq(
                InnerTxnBuilder.MethodCall(
                    app_id=bitsave.state.user_child_contract_id[Txn.sender()],
                    method_signature=bitsave_child_app.opt_contract_to_token.method_signature(),
                    args=[asset_id],
                ),
                InnerTxnBuilder.Next(),
            )
        ),
        send_token(asset_id=asset_uint, amount=amount, receiver=child_address.value()),
        InnerTxnBuilder.Next(),
        send_token(asset_id=asset_uint, amount=charges, receiver=Addr(BITSAVE_ADDRESS)),
        InnerTxnBuilder.Next(),
        InnerTxnBuilder.MethodCall(
            app_id=bitsave.state.user_child_contract_id[Txn.sender()],
            method_signature=bitsave_child_app.create_savings.method_signature(),
            args=[
                name,
                end_time,
                Itob(principal.load()),
                # percentage,
                interest,
                asset_id,
                penalty,
            ],
            extra_fields={
                TxnField.accounts: [
                    Txn.sender(),
                    Bytes(decode_address(BITSAVE_ADDRESS)),
                ]
            },
        ),
        InnerTxnBuilder.Submit(),
        output.set(Int(1)),
    )


# @bitsave.external
# def add_to_savings(
#     pay_txn: abi.PaymentTransaction,
#     name: abi.String,
#     asset_id: abi.Uint64,
#     interest: abi.Uint64,
#     *,
#     output: abi.Uint64,
# ):
#     return Seq(
#         # assert that savings name exist else reject txn
#         confirm_name := App.globalGetEx(
#             bitsave.state.user_child_contract_id[Txn.sender()],
#             Concat(Bytes("name"), name.get()),
#         ),
#         Assert(confirm_name.hasValue()),
#         (edited_principal := abi.Uint64()).set(
#             If(
#                 pay_txn.get().type_enum() == TxnType.AssetTransfer,
#                 pay_txn.get().asset_amount(),
#                 pay_txn.get().amount(),
#             )
#         ),
#         child_address := AppParam.address(
#             bitsave.state.user_child_contract_id[Txn.sender()]
#         ),
#         Assert(child_address.hasValue()),
#         InnerTxnBuilder.Begin(),
#         send_token(
#             asset_id=asset_id, amount=edited_principal, receiver=child_address.value()
#         ),
#         InnerTxnBuilder.Next(),
#         InnerTxnBuilder.MethodCall(
#             app_id=bitsave.state.user_child_contract_id[Txn.sender()],
#             method_signature=CC.add_savings.method_signature(),
#             args=[name, edited_principal, interest],
#         ),
#         InnerTxnBuilder.Submit(),
#         output.set(Int(1)),
#     )


# @bitsave.external
# def withdraw_savings(name: abi.String, *, output: abi.Uint64):
#     return Seq(
#         amount_check := App.globalGetEx(
#             bitsave.state.user_child_contract_id, join_keys(Bytes("amount"), name.get())
#         ),
#         # confirm user has the said savings, else just reject transaction
#         Assert(amount_check.hasValue()),
#         # has the savings period ended!
#         end_time_check := App.globalGetEx(
#             bitsave.state.user_child_contract_id,
#             join_keys(Bytes("end_time"), name.get()),
#         ),
#         Assert(end_time_check.hasValue()),
#         # atomic transfer to first send user's savings and then delete from child
#         InnerTxnBuilder.Begin(),
#         # delete savings state on child contract!
#         InnerTxnBuilder.MethodCall(
#             app_id=bitsave.state.user_child_contract_id,
#             method_signature=CC.close_savings.method_signature(),
#             args=[name, Txn.sender()],
#             extra_fields={
#                 TxnField.accounts: [
#                     Txn.sender(),
#                     Bytes(decode_address(BITSAVE_ADDRESS)),
#                 ]
#             },
#         ),
#         InnerTxnBuilder.Submit(),
#         output.set(Int(1)),
#     )


# @bitsave.external
# def get_child_id(*, output: abi.Uint64):
#     """Adds two num together"""
#     return output.set(bitsave.state.user_child_contract_id[Txn.sender()])


app = bitsave
