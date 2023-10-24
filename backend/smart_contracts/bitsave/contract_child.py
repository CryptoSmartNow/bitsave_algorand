
from typing import Final
from pyteal import (
    Seq, Subroutine, Concat, Bytes, TealType, Expr, \
    abi, TxnType, InnerTxnBuilder, InnerTxn, TxnField, \
    Global, Int
)
import beaker
from beaker import (
    ReservedGlobalStateValue, Authorize
)


# Subroutines
@Subroutine(TealType.bytes)
def generate_name(key_seed: Expr) -> Expr:
    return Concat(Bytes("name"), key_seed)


@Subroutine(TealType.bytes)
def generate_amount(key_seed: Expr) -> Expr:
    return Concat(Bytes("amount"), key_seed)


@Subroutine(TealType.bytes)
def generate_start_time(key_seed: Expr) -> Expr:
    return Concat(Bytes("start_time"), key_seed)


@Subroutine(TealType.bytes)
def generate_end_time(key_seed: Expr) -> Expr:
    return Concat(Bytes("end_time"), key_seed)


@Subroutine(TealType.bytes)
def generate_interest(key_seed: Expr) -> Expr:
    return Concat(Bytes("interest"), key_seed)


@Subroutine(TealType.bytes)
def generate_penalty(key_seed: Expr) -> Expr:
    return Concat(Bytes("penalty"), key_seed)


@Subroutine(TealType.bytes)
def generate_asset_id(key_seed: Expr) -> Expr:
    return Concat(Bytes("asset_id"), key_seed)




class BitsaveChildState:
    # pass all states here
    # names of savings
    names: Final[ReservedGlobalStateValue] = ReservedGlobalStateValue(
        stack_type=TealType.bytes, max_keys=9,
        descr="All savings names will be stored here!",
        key_gen=generate_name
    )

    # amount of savings
    amounts: Final[ReservedGlobalStateValue] = ReservedGlobalStateValue(
        stack_type=TealType.uint64, max_keys=9, key_gen=generate_amount,
        descr="Amounts of savings will be stored here:)"
    )

    # the time the savings started
    # todo: check if it's possible to extract this value from metadata instead
    start_times: Final[ReservedGlobalStateValue] = ReservedGlobalStateValue(
        stack_type=TealType.uint64, max_keys=9, key_gen=generate_start_time,
        descr="Start time integer in milliseconds will be stored here"
    )

    # end_times
    end_times: Final[ReservedGlobalStateValue] = ReservedGlobalStateValue(
        stack_type=TealType.uint64, max_keys=9, key_gen=generate_end_time,
        descr="End time integer will be stored here"
    )

    # penalties
    penalties: Final[ReservedGlobalStateValue] = ReservedGlobalStateValue(
        stack_type=TealType.uint64, max_keys=9, key_gen=generate_penalty,
        descr="Penalty for each saving"
    )

    # interests
    interests: Final[ReservedGlobalStateValue] = ReservedGlobalStateValue(
        stack_type=TealType.uint64, max_keys=9, key_gen=generate_interest,
        descr="Interest for each saving"
    )

    # assetIds
    asset_ids: Final[ReservedGlobalStateValue] = ReservedGlobalStateValue(
        stack_type=TealType.uint64, max_keys=9, key_gen=generate_asset_id,
        descr="The asset ids to know what currency saving is in. 0 will be for algo"
    )


bitsave_child_app = (
    beaker.Application(
        "BitsaveChild",
        state=BitsaveChildState()
    )
)



# add (bare=True)
@bitsave_child_app.create(bare=True)
def create() -> Expr:
    return bitsave_child_app.initialize_global_state()


def calc_interest(principal: abi.Uint64, percentage: abi.Uint64) -> Expr:
    return principal.get() * percentage.get() / Int(100)


@bitsave_child_app.external(authorize=Authorize.only_creator())
def opt_contract_to_token(token_id: abi.Asset, *, output: abi.Uint64) -> Expr:
    return Seq(
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields(
            {
                TxnField.type_enum: TxnType.AssetTransfer,
                TxnField.asset_receiver: Global.current_application_address(),
                TxnField.asset_amount: Int(0),
                TxnField.xfer_asset: token_id.asset_id()
            }
        ),
        InnerTxnBuilder.Submit(),
        output.set(Int(1))
    )



