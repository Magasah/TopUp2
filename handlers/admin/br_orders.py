from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from database import queries as db

router = Router()


def _fmt_rub(v: float) -> str:
    return f"{int(v)} ₽" if float(v).is_integer() else f"{v:g} ₽"


@router.callback_query(F.data.startswith("br_accept_"))
async def br_accept(callback: CallbackQuery, bot, t) -> None:
    await callback.answer()
    order_id = int(callback.data.split("_")[2])
    order = await db.get_br_order(order_id)
    if not order:
        return
    await db.update_br_order_status(order_id, "accepted")
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await callback.message.answer(f"✅ Заказ #{order_id} принят!")
    await bot.send_message(
        int(order["user_tg_id"]),
        f"🎉 Заказ #{order_id} выполнен!\n"
        f"🚗 Black Russia | {order['server_name']}\n"
        f"💰 {_fmt_rub(float(order['amount']))}\n"
        "Зайдите в игру и проверьте.",
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("br_reject_"))
async def br_reject(callback: CallbackQuery, bot) -> None:
    await callback.answer()
    order_id = int(callback.data.split("_")[2])
    order = await db.get_br_order(order_id)
    if not order:
        return
    await db.update_br_order_status(order_id, "rejected")
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await callback.message.answer(f"❌ Заказ #{order_id} отклонён.")
    await bot.send_message(
        int(order["user_tg_id"]),
        f"❌ Заказ #{order_id} отклонён.\n"
        "Если это ошибка — напишите в поддержку.",
    )


@router.callback_query(F.data.startswith("br_delete_"))
async def br_delete(callback: CallbackQuery) -> None:
    await callback.answer()
    order_id = int(callback.data.split("_")[2])
    await db.delete_br_order(order_id)
    await callback.message.answer(f"🗑 Заказ #{order_id} удалён.")


@router.callback_query(F.data == "adm_br_orders")
async def br_orders_menu(callback: CallbackQuery, t) -> None:
    await callback.answer()
    rows = await db.get_br_orders_by_status("pending")
    if not rows:
        await callback.message.answer(t("orders_empty"))
        return
    kb_rows = []
    for r in rows:
        kb_rows.append([InlineKeyboardButton(text=f"🚗 #{r['id']} | {r['server_name']}", callback_data=f"br_show_{r['id']}")])
    await callback.message.answer("🚗 Black Russia заказы:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows))


@router.callback_query(F.data.startswith("br_show_"))
async def br_show(callback: CallbackQuery) -> None:
    await callback.answer()
    order_id = int(callback.data.split("_")[2])
    order = await db.get_br_order(order_id)
    if not order:
        return
    cap = (
        f"🚗 BLACK RUSSIA #{order_id}\n"
        f"👤 @{order.get('username') or order.get('user_tg_id')}\n"
        f"🖥 {order['server_name']}\n"
        f"👾 {order['nickname']}\n"
        f"💰 {_fmt_rub(float(order['amount']))}\n"
        f"💳 {order['payment_method']}"
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Принять", callback_data=f"br_accept_{order_id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"br_reject_{order_id}"),
            ],
            [InlineKeyboardButton(text="💬 Написать покупателю", url=f"tg://user?id={order['user_tg_id']}")],
            [InlineKeyboardButton(text="🗑 Удалить заказ", callback_data=f"br_delete_{order_id}")],
        ]
    )
    if order.get("receipt_file_id"):
        await callback.message.answer_photo(order["receipt_file_id"], caption=cap, reply_markup=kb)
    else:
        await callback.message.answer(cap, reply_markup=kb)

# ✅ ГОТОВО: handlers/admin/br_orders.py
