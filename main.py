import asyncio
import os
import json
from datetime import datetime

from twscrape import API, gather
from twscrape.logger import set_log_level
import telebot

# ====================== НАСТРОЙКИ ======================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))

USERS_TO_MONITOR = [
    "heyibinance",      # главный по боксам и загадкам
    "redpacketcodess",
    "Redpacketking",
    "BNCryptoB0X",
    "MSAirdropKing",
    "sleepfarting",
    "CoinsBoxes"
]

KEYWORDS = [
    "code", "код", "box", "бокс", "crypto box", "mystery box", "福袋",
    "red packet", "红包", "口令", "загадка", "riddle", "puzzle",
    "redeem", "gift", "lucky", "big gift", "special", "раздача", "谜语"
]

# X-аккаунты из переменных Railway (безопасно)
X_ACCOUNTS = [
    {
        "username": os.getenv("X1_USERNAME"),
        "password": os.getenv("X1_PASSWORD"),
        "email": os.getenv("X1_EMAIL"),
        "email_password": os.getenv("X1_EMAIL_PASSWORD"),
    },
    {
        "username": os.getenv("X2_USERNAME"),
        "password": os.getenv("X2_PASSWORD"),
        "email": os.getenv("X2_EMAIL"),
        "email_password": os.getenv("X2_EMAIL_PASSWORD"),
    }
]

bot = telebot.TeleBot(TELEGRAM_TOKEN)
api = API()

LAST_IDS = {}  # в памяти, при перезапуске сбросится — нормально


async def main():
    set_log_level("DEBUG")
    print(f"[{datetime.now()}] 🔥 VIP Binance Box Bot ЗАПУЩЕН!")

    # Добавляем твои 2 X-аккаунта
    for acc in X_ACCOUNTS:
        if acc["username"] and acc["password"]:
            await api.pool.add_account(
                acc["username"], acc["password"],
                acc["email"], acc["email_password"]
            )
    await api.pool.login_all()

    while True:
        for username in USERS_TO_MONITOR:
            try:
                tweets = await gather(api.user_tweets(username, limit=5))
                for tweet in tweets:
                    if LAST_IDS.get(username, 0) >= tweet.id:
                        continue

                    # Только оригинальные посты (без ответов и репостов)
                    if tweet.inReplyToStatusId or getattr(tweet, 'isRetweet', False):
                        continue

                    text_lower = tweet.rawContent.lower()
                    if any(kw.lower() in text_lower for kw in KEYWORDS):
                        message = f"""
🔥 <b>НОВАЯ РАЗДАЧА / БОКС / ЗАГАДКА!</b> @{username}

{tweet.rawContent}

🕒 {tweet.date.strftime('%d.%m.%Y %H:%M')}
🔗 https://x.com/{username}/status/{tweet.id}
                        """.strip()

                        # Отправляем текст
                        sent = bot.send_message(CHAT_ID, message, parse_mode='HTML')

                        # Отправляем фото (до 3 шт)
                        if hasattr(tweet, 'photos') and tweet.photos:
                            for photo in tweet.photos[:3]:
                                bot.send_photo(CHAT_ID, photo.url, reply_to_message_id=sent.message_id)

                        # Отправляем видео (до 1 шт)
                        if hasattr(tweet, 'videos') and tweet.videos:
                            bot.send_video(CHAT_ID, tweet.videos[0].url, reply_to_message_id=sent.message_id)

                        print(f"✅ Отправлено от @{username} — {tweet.id}")

                    LAST_IDS[username] = tweet.id

            except Exception as e:
                print(f"Ошибка у {username}: {e}")

        await asyncio.sleep(45)  # проверка каждые 45 секунд


if __name__ == "__main__":
    asyncio.run(main())
