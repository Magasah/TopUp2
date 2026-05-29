from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from database.queries import get_bonus_balance

router = Router()


@router.message(Command("bonus"))
async def cmd_bonus(message: Message, t) -> None:
    bal = await get_bonus_balance(message.from_user.id)
    await message.answer(
        t("bonus_balance_cmd", balance=bal),
        parse_mode="HTML",
    )

# ✅ ГОТОВО: handlers/bonus.py
