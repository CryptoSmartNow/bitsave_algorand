import beaker
from typing import Final
import pyteal as pt

### Child contract
from smart_contracts.bitsave.contract_child import bitsave_child_app



# Define constants else where please
OPT_FEE = 2_400_000


# State class
class BitsaveMainState:
    user_child_contract_id: Final[beaker.LocalStateValue] = beaker.LocalStateValue(
        stack_type=pt.TealType.uint64,
        descr="The app id of the user's child contract"
    )


bitsave = beaker.Application(
    "bitsave",
    state=BitsaveMainState(),
    descr="This is the bitsave parent protocol v2.0"
)


# @bitsave.external
# def hello(name: pt.abi.String, *, output: pt.abi.String) -> pt.Expr:
#     return output.set(pt.Concat(pt.Bytes("Hello, "), name.get()))


@bitsave.create
def create():
    return pt.Seq(
        bitsave.initialize_global_state()
    )

@bitsave.update(authorize=beaker.Authorize.only_creator())
def update():
    return pt.Approve()

@bitsave.delete(authorize=beaker.Authorize.only_creator())
def delete():
    return pt.Approve()



# -------------> Opt a new user into bitsave
@bitsave.opt_in(bare=True) # TODO: bare = True
def opt_in():
    """
    Opt in does a bit of operations
    1. Creates a child contract for the user and gets the id
    2. Stores the child contract id in the user's local storage
    3. In subsequent calls, it fetches the id from the storage
    :return:
    app_id of the child contact
    """
    child_contract_pc = beaker.precompiled(bitsave_child_app) # TODO: child contract
    return pt.Seq(
        (pay := pt.ScratchVar()).store(pt.Gtxn[0].amount()),
        pt.Assert(pay.load() > pt.Int(OPT_FEE)),
        bitsave.initialize_local_state(),
        pt.InnerTxnBuilder.Execute(
            {
                **child_contract_pc.get_create_config(), # TODO: confirm if still follows
            }
        ),
        (child_id := pt.abi.Uint64()).set(pt.InnerTxn.created_application_id()),
        (child_addr_maybe := pt.AppParam.address(child_id.get())),
        pt.Assert(child_addr_maybe.hasValue()),
        (child_addr := pt.ScratchVar()).store(child_addr_maybe.value()),
        # Fund child contract
        # pt.InnerTxnBuilder.Execute(
        #     {
        #         pt.TxnField.type_enum: pt.TxnType.Payment,
        #         pt.TxnField.amount: pt.Int(OPT_FEE - 1_000_000),
        #         pt.TxnField.receiver: child_addr.load(),
        #     }
        # ),
        # store the child app id in user's local storage
        bitsave.state.user_child_contract_id[pt.Txn.sender()].set(child_id.get()),
        # return the child app id
        # output.set(child_id.get()),
    )

app = bitsave


