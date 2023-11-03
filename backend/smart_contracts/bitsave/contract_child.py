
from typing import Final
from pyteal import (
    Seq, Subroutine, Concat, Bytes, TealType, Expr, \
    abi, TxnType, InnerTxnBuilder, TxnField, \
    Global, Int, Addr, If
)
import beaker
from beaker import (
    ReservedGlobalStateValue, Authorize
)
from smart_contracts.utils import send_token
from smart_contracts.constants import (
    BITSAVE_ADDRESS,
    CS_TOKEN
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


@bitsave_child_app.external(authorize=Authorize.only_creator())
def create_savings(
        name: abi.String,
        end_time: abi.Uint64,
        principal: abi.Uint64,
        # percentage: abi.Uint64,
        interest: abi.Uint64,
        asset: abi.Asset,
        penalty: abi.Uint64,
        *,
        output: abi.Uint64
) -> Expr:
    # principal transaction from parent as principal value stored
    return Seq(
        bitsave_child_app.state.names[name.get()].set(name.get()),
        # set start_time from current timestamp
        bitsave_child_app.state.start_times[name.get()].set(Global.latest_timestamp()),
        bitsave_child_app.state.end_times[name.get()].set(end_time.get()),
        bitsave_child_app.state.penalties[name.get()].set(penalty.get()),
        bitsave_child_app.state.asset_ids[name.get()].set(asset.asset_id()),
        bitsave_child_app.state.interests[name.get()].set(interest.get()),
        # for percentage, we convert percentage to amount value
        # (interest := scratchvar()).store(self.calc_interest(principal, percentage)),
        bitsave_child_app.state.amounts[name.get()].set(principal.get()),
        output.set(int(1))
    )


@bitsave_child_app.external(authorize=Authorize.only_creator())
def add_savings(
        name: abi.String,
        principal: abi.Uint64,
        interest: abi.Uint64,
        *,
        output: abi.Uint64) -> Expr:
    bs_child_state = bitsave_child_app.state
    # add to savings
    return Seq(
        # (interest_to_add := ScratchVar(TealType.uint64)).store(self.calc_interest(principal, percentage)),
        bs_child_state.interests[name.get()].set(
            bs_child_state.interests[name.get()].get() + interest.get()
        ),
        bs_child_state.amounts[name.get()].set(
            principal.get() + bs_child_state.amounts[name.get()].get()
        ),
        output.set(bs_child_state.amounts[name.get()])
    )


@bitsave_child_app.external(authorize=Authorize.only_creator())
def close_savings(name: abi.String, owner: abi.Address, *, output: abi.String) -> Expr:
    bs_child_state = bitsave_child_app.state
    return Seq(
        # get asset id and amount
        (asset_id := abi.Uint64()).set(bs_child_state.asset_ids[name.get()].get()),
        (amount := abi.Uint64()).set(bs_child_state.amounts[name.get()].get()),
        # check if the savings has ended
        (end_time := abi.Uint64()).set(bs_child_state.end_times[name.get()].get()),

        # if savings has not ended, get penalty percentage and send to parent / bitsave contract
        # atomic transfer to send user's savings and send penalty to bitsave
        InnerTxnBuilder.Begin(),
        If(Global.latest_timestamp() < end_time.get())
        .Then(
            # remove penalty and send to cs
            Seq(
                (penalty_perc := abi.Uint64()).set(bs_child_state.penalties[name.get()].get()),
                (penalty_value := abi.Uint64()).set(penalty_perc.get() * amount.get() / Int(100)),
                amount.set(amount.get() - penalty_value.get()),
                send_token(
                    asset_id=asset_id,
                    amount=penalty_value,
                    receiver=Addr(BITSAVE_ADDRESS)
                ),
                InnerTxnBuilder.Next()
            )
        ).Else(
            # send interest as well since user fulfilled savings
            Seq(
                (retrieved_interest := abi.Uint64()).set(bs_child_state.interests[name.get()].get()),
                (ABI_CS_TOKEN := abi.Uint64()).set(CS_TOKEN),
                send_token(
                    asset_id=ABI_CS_TOKEN,
                    amount=retrieved_interest,
                    receiver=owner.get()
                )
            )
        ),
        send_token(
            asset_id=asset_id,
            amount=amount,
            receiver=owner.get()
        ),
        InnerTxnBuilder.Submit(),

        # delete savings from contract
        bs_child_state.amounts[name.get()].delete(),
        bs_child_state.asset_ids[name.get()].delete(),
        bs_child_state.penalties[name.get()].delete(),
        bs_child_state.interests[name.get()].delete(),
        bs_child_state.start_times[name.get()].delete(),
        bs_child_state.end_times[name.get()].delete(),
        bs_child_state.names[name.get()].delete(),
        output.set("Savings data cleared!")
    )


