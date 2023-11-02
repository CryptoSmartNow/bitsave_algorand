from pyteal import (
    abi, Expr, Int, Seq, TxnField, TxnType, InnerTxnBuilder, If
)


def send_token(asset_id: abi.Uint64, amount: abi.Uint64, receiver: Expr) -> Expr:
    return Seq(
        If(asset_id.get() == Int(0))
        .Then(
            InnerTxnBuilder.SetFields(
                {
                    TxnField.type_enum: TxnType.Payment,
                    TxnField.amount: amount.get(),
                    TxnField.receiver: receiver,
                }
            ),
        ).Else(
            InnerTxnBuilder.SetFields(
                {
                    TxnField.type_enum: TxnType.AssetTransfer,
                    TxnField.asset_receiver: receiver,
                    TxnField.asset_amount: amount.get(),
                    TxnField.xfer_asset: asset_id.get()
                }
            ),
        )
    )
