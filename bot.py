from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
)
import logging
import datetime
import os
from dotenv import load_dotenv

# بارگذاری متغیرهای محیطی از .env (برای اجرای لوکال)
load_dotenv()

# مراحل
START, BUY_SELL, CURRENCY, AMOUNT, PRICE, TRANSFER_TYPE, FINAL = range(7)

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

if not TOKEN:
    logging.error("❌ BOT_TOKEN تنظیم نشده است. متغیر محیطی BOT_TOKEN خالی است.")
if not CHANNEL_ID:
    logging.error("❌ CHANNEL_ID تنظیم نشده است. متغیر محیطی CHANNEL_ID خالی است.")

# کیبورد استارت
start_keyboard = [
    [KeyboardButton("💰 Buy - خرید دارم"), KeyboardButton("💵 Sell - فروش دارم")],
    [KeyboardButton("🔄 ثبت مجدد درخواست")],
]

# کیبورد بعد از ثبت
after_submit_keyboard = [
    [KeyboardButton("📤 ارسال به کانال")],
    [KeyboardButton("🔄 ثبت مجدد درخواست")],
]

# کیبورد ارزها
currency_keyboard = [
    [InlineKeyboardButton("💠 USDT - تتر", callback_data="USDT")],
    [InlineKeyboardButton("🇹🇷 TRY - لیر", callback_data="TRY")],
    [InlineKeyboardButton("🇺🇸 USD - دلار", callback_data="USD")],
    [InlineKeyboardButton("🇪🇺 EUR - یورو", callback_data="EUR")],
    [InlineKeyboardButton("🇬🇧 GBP - پوند", callback_data="GBP")],
]

# کیبورد نوع انتقال
transfer_keyboard = [
    [KeyboardButton("نقدی"), KeyboardButton("حسابی")],
    [KeyboardButton("🔄 ثبت مجدد درخواست")],
]


async def send_to_channel(context: ContextTypes.DEFAULT_TYPE, order_data: dict) -> bool:
    """ارسال سفارش به کانال تلگرام"""
    try:
        currency_names = {
            "USDT": "تتر",
            "TRY": "لیر",
            "USD": "دلار",
            "EUR": "یورو",
            "GBP": "پوند",
        }

        if "خرید دارم" in order_data["buy_sell"]:
            status = "خریدار"
            transfer_text = "واریز به حساب فروشنده"
        else:
            status = "فروشنده"
            transfer_text = "واریز به حساب خریدار"

        user_mention = (
            f"@{order_data['username']}" if order_data["username"] else str(order_data["user_id"])
        )

        message_text = (
            f"💰 سفارش جدید مشتری ({order_data['time']})\n\n"
            f"💱{status} : {order_data['amount']} {currency_names[order_data['currency']]} {order_data['currency']}\n"
            f"💵 با قیمت {order_data['price']} تومان\n"
        )

        if order_data["currency"] != "USDT":
            message_text += f"🏦 {transfer_text}\n"

        message_text += f"👤 ID : {user_mention}"

        # تبدیل CHANNEL_ID به int اگر به صورت رشته ذخیره شده باشد
        chat_id = int(CHANNEL_ID)

        await context.bot.send_message(chat_id=chat_id, text=message_text)

        logging.info(f"✅ ارسال به کانال: {order_data['currency']}")
        return True
    except Exception as e:
        logging.error(f"❌ خطا در ارسال به کانال: {e}")
        return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("به بازار صرافی سیمرغ خوش آمدید")

    reply_markup = ReplyKeyboardMarkup(start_keyboard, resize_keyboard=True)
    await update.message.reply_text("خرید یا فروش لطفاً انتخاب کنید:", reply_markup=reply_markup)
    return BUY_SELL


async def buy_sell_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "🔄 ثبت مجدد درخواست":
        return await start(update, context)

    user_choice = update.message.text
    context.user_data["buy_sell"] = user_choice

    keyboard = InlineKeyboardMarkup(currency_keyboard)
    await update.message.reply_text("ارز را انتخاب کنید:", reply_markup=keyboard)
    return CURRENCY


async def currency_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data["currency"] = query.data

    currency_names = {
        "USDT": "تتر",
        "TRY": "لیر",
        "USD": "دلار",
        "EUR": "یورو",
        "GBP": "پوند",
    }

    await query.edit_message_text(
        f"ارز انتخاب شده: {query.data} ({currency_names[query.data]})"
    )

    if context.user_data["currency"] == "USDT":
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="مقدار یا تعداد را نوشته و ارسال کنید:",
        )
        return AMOUNT
    else:
        reply_markup = ReplyKeyboardMarkup(transfer_keyboard, resize_keyboard=True)
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="حسابی یا نقدی را انتخاب کنید:",
            reply_markup=reply_markup,
        )
        return TRANSFER_TYPE


async def transfer_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "🔄 ثبت مجدد درخواست":
        return await start(update, context)

    context.user_data["transfer_type"] = update.message.text
    await update.message.reply_text("مقدار یا تعداد را نوشته و ارسال کنید:")
    return AMOUNT


async def amount_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "🔄 ثبت مجدد درخواست":
        return await start(update, context)

    amount = update.message.text.replace(",", "")
    if not amount.isdigit():
        await update.message.reply_text("فقط عدد بنویسید. ممنون")
        return AMOUNT

    formatted_amount = "{:,}".format(int(amount))
    context.user_data["amount"] = formatted_amount

    await update.message.reply_text("قیمت به تومان نوشته و ارسال کنید:")
    return PRICE


async def price_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "🔄 ثبت مجدد درخواست":
        return await start(update, context)

    price = update.message.text.replace(",", "")
    if not price.isdigit():
        await update.message.reply_text("فقط عدد بنویسید. ممنون")
        return PRICE

    formatted_price = "{:,}".format(int(price))
    context.user_data["price"] = formatted_price

    user_id = update.message.from_user.id
    username = update.message.from_user.username
    time = datetime.datetime.now().strftime("%H%M%S")

    currency_names = {
        "USDT": "تتر",
        "TRY": "لیر",
        "USD": "دلار",
        "EUR": "یورو",
        "GBP": "پوند",
    }

    summary = (
        f"سفارش مشتری ({time})\n"
        f"{context.user_data['buy_sell']}\n"
        f"مقدار: {context.user_data['amount']} {context.user_data['currency']} ({currency_names[context.user_data['currency']]})\n"
        f"قیمت: {context.user_data['price']} تومان\n"
    )

    if context.user_data["currency"] != "USDT":
        summary += f"{context.user_data['transfer_type']}\n"

    summary += f"ID: {user_id}"

    await update.message.reply_text(summary)

    context.user_data["user_id"] = user_id
    context.user_data["username"] = username
    context.user_data["time"] = time

    reply_markup = ReplyKeyboardMarkup(after_submit_keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "ثبت شد. برای ارسال به کانال کلیک کنید", reply_markup=reply_markup
    )
    return FINAL


async def final_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "🔄 ثبت مجدد درخواست":
        return await start(update, context)

    if update.message.text == "📤 ارسال به کانال":
        success = await send_to_channel(context, context.user_data)

        if success:
            await update.message.reply_text("✅ سفارش شما به کانال ارسال شد")
        else:
            await update.message.reply_text(
                "❌ خطا در ارسال به کانال. لطفاً مجدد تلاش کنید"
            )

        reply_markup = ReplyKeyboardMarkup(start_keyboard, resize_keyboard=True)
        await update.message.reply_text("برای شروع مجدد /start", reply_markup=reply_markup)
        return START


def setup_conversation_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            BUY_SELL: [MessageHandler(filters.TEXT & ~filters.COMMAND, buy_sell_handler)],
            CURRENCY: [CallbackQueryHandler(currency_handler)],
            TRANSFER_TYPE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, transfer_handler)
            ],
            AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, amount_handler)],
            PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, price_handler)],
            FINAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, final_handler)],
        },
        fallbacks=[CommandHandler("start", start)],
    )


async def main():
    if not TOKEN:
        logging.error("❌ BOT_TOKEN وجود ندارد، ربات اجرا نمی‌شود.")
        return

    application = Application.builder().token(TOKEN).build()
    application.add_handler(setup_conversation_handler())

    logging.info("✅ ربات با قابلیت ارسال به کانال فعال شد")
    await application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())

