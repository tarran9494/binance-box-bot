import asyncio
import html
import json
import logging
import os
import random
import re
from datetime import datetime, timedelta

import feedparser
import telebot

# ====================== НАСТРОЙКИ ======================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_IDS = [int(x.strip()) for x in os.getenv("CHAT_ID", "").split(",") if x.strip()]
MAX_DAYS_OLD = float(os.getenv("MAX_DAYS_OLD", "0.25"))  # по умолчанию 6 часов

RSS_FEEDS = [
    "https://rss.app/feeds/2loSnhs0CZTT1d3I.xml",
    "https://rss.app/feeds/UAguyKs3QpIvpbDc.xml",
    "https://rss.app/feeds/8LlBqcdt6hafdWYS.xml",
    "https://rss.app/feeds/6ZWcPSn2cnrrZACj.xml",
    "https://rss.app/feeds/ufpnwv2TxtHmPMvE.xml",
    "https://rss.app/feeds/5zoykzMHaxvd7BOp.xml",
    "https://rss.app/feeds/V3pGmTlqEOGGF0bM.xml",
    "https://rss.app/feeds/KuzvCigiUbmGr8e0.xml",
]

# Расширенные ключевые слова (русские, английские, китайские)
KEYWORDS = [
    "box",
    "бокс",
    "crypto box",
    "mystery box",
    "lucky bag",
    "red packet",
    "红包",
    "口令",
    "раздача",
    "загадка",
    "riddle",
    "puzzle",
    "code",
    "код",
    "redeem",
    "gift",
    "big gift",
    "special",
    "giveaway",
    "розыгрыш",
    # Китайские
    "宝箱",
    "谜语",
    "福利",
    "活动",
    "抽奖",
    "赠送",
    "盲盒",
    "礼包",
    "现金",
    "奖励",
    "红包封面",
    "优惠券",
    "代金券",
    "福袋",
    "惊喜",
    "限量",
    "专属",
    "邀请码",
]

# ====================== ЛОГИРОВАНИЕ ======================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Путь для сохранения GUID (Volume должен быть примонтирован в /app/data)
DATA_DIR = "/app/data"
if os.path.exists(DATA_DIR):
    LAST_GUIDS_FILE = os.path.join(DATA_DIR, "last_guids.json")
else:
    LAST_GUIDS_FILE = "last_guids.json"  # fallback (не рекомендуется без Volume)

# Загружаем обработанные GUID (глобально, чтобы избежать дублей между фидами)
if os.path.exists(LAST_GUIDS_FILE):
    with open(LAST_GUIDS_FILE, "r", encoding="utf-8") as f:
        PROCESSED_GUIDS = set(json.load(f))
else:
    PROCESSED_GUIDS = set()


def save_processed_guids():
    with open(LAST_GUIDS_FILE, "w", encoding="utf-8") as f:
        json.dump(list(PROCESSED_GUIDS), f, ensure_ascii=False, indent=2)


def extract_codes(text: str):
    """Ищет коды: 4-20 заглавных букв/цифр, а также короткие цифровые коды."""
    codes = re.findall(r"\b[A-Z0-9]{4,20}\b", text.upper())
    codes += re.findall(r"\b\d{4,}\b", text)
    return list(set(codes))


def extract_username(feed):
    title = feed.feed.get("title", "")
    if "@" in title:
        return title.split("@")[-1].strip()
    return "Unknown"


async def send_telegram_message(
    text, parse_mode: str = "HTML", disable_web_page_preview: bool = True
):
    """Отправка сообщения во все указанные чаты."""
    for chat_id in CHAT_IDS:
        try:
            if len(text) > 4096:
                text = text[:4093] + "..."
            await asyncio.to_thread(
                bot.send_message,
                chat_id,
                text,
                parse_mode=parse_mode,
                disable_web_page_preview=disable_web_page_preview,
            )
        except Exception as e:
            logger.error(f"❌ Не удалось отправить сообщение в чат {chat_id}: {e}")


async def send_telegram_media(media_type, url, reply_to_message_id):
    """Отправка фото или видео во все чаты."""
    for chat_id in CHAT_IDS:
        try:
            if media_type == "photo":
                await asyncio.to_thread(
                    bot.send_photo, chat_id, url, reply_to_message_id=reply_to_message_id
                )
            elif media_type == "video":
                await asyncio.to_thread(
                    bot.send_video, chat_id, url, reply_to_message_id=reply_to_message_id
                )
        except Exception as e:
            logger.warning(f"⚠️ Медиа {url} не отправлено в чат {chat_id}: {e}")


async def process_feed(rss_url):
    """Обрабатывает один RSS-канал, возвращает список GUID отправленных постов."""
    try:
        feed = feedparser.parse(rss_url)
        username = extract_username(feed)
        cutoff_date = datetime.now() - timedelta(days=MAX_DAYS_OLD)
        sent_guids = []

        for entry in feed.entries:
            guid = entry.get("id") or entry.link
            if guid in PROCESSED_GUIDS:
                continue

            # Проверка даты (если нет даты — пропускаем)
            published = entry.get("published_parsed") or entry.get("updated_parsed")
            if not published:
                logger.debug(f"⏭️ Пост без даты пропущен: {guid}")
                continue

            pub_date = datetime(*published[:6])
            if pub_date < cutoff_date:
                continue

            title = entry.get("title", "")
            description = entry.get("description", "") or entry.get("summary", "")
            full_text = f"{title}\n\n{description}".strip()
            text_lower = full_text.lower()

            # Проверка ключевых слов
            if not any(kw in text_lower for kw in KEYWORDS):
                continue

            codes = extract_codes(full_text)
            codes_str = ""
            if codes:
                codes_str = (
                    "\n\n🧧 <b>КОДЫ В ПОСТЕ:</b>\n"
                    + "\n".join([f"<code>{c}</code>" for c in codes])
                )

            safe_text = html.escape(full_text)
            message = f"""
🔥 <b>НОВАЯ РАЗДАЧА / БОКС / ЗАГАДКА</b> от @{username}

{safe_text}

{codes_str}
🕒 {entry.get('published', pub_date.strftime('%d.%m %H:%M'))}
🔗 {entry.link}
            """.strip()

            # Отправляем текст
            sent_msg = await send_telegram_message(message)

            # Отправляем медиа
            media_urls = []
            for link in entry.get("links", []):
                if link.get("rel") == "enclosure" and link.get("type", "").startswith(
                    ("image/", "video/")
                ):
                    media_urls.append((link["type"].split("/")[0], link["href"]))
            if hasattr(entry, "media_content") and entry.media_content:
                for media in entry.media_content:
                    if media.get("url"):
                        mtype = media.get("type", "").split("/")[0]
                        if mtype in ("image", "video"):
                            media_urls.append((mtype, media["url"]))

            for mtype, url in media_urls[:4]:
                await send_telegram_media(mtype, url, sent_msg.message_id if sent_msg else None)

            logger.info(f"✅ Отправлено от @{username} | кодов: {len(codes)}")
            PROCESSED_GUIDS.add(guid)
            sent_guids.append(guid)

        return sent_guids

    except Exception as e:
        logger.error(f"🔥 Ошибка при обработке {rss_url}: {e}")
        return []


async def main():
    logger.info("🔥 VIP Binance Box & Riddle Bot (MAX версия) ЗАПУЩЕН")
    logger.info(f"📢 Получатели: {CHAT_IDS}")
    logger.info(f"⏱️ Макс. возраст поста: {MAX_DAYS_OLD} дней")
    logger.info(f"💾 Файл GUID: {LAST_GUIDS_FILE}")

    while True:
        start_time = datetime.now()
        tasks = [process_feed(url) for url in RSS_FEEDS]
        results = await asyncio.gather(*tasks)
        all_sent = [guid for sublist in results for guid in sublist]

        if all_sent:
            save_processed_guids()
            logger.info(f"✅ Цикл завершён, отправлено {len(all_sent)} новых постов")
        else:
            logger.info("⏳ Новых постов нет")

        save_processed_guids()  # сохраняем даже если ничего не отправили (на случай, если GUID добавились)

        elapsed = (datetime.now() - start_time).total_seconds()
        delay = random.uniform(300, 720)  # 5-12 минут
        logger.info(f"💤 Цикл выполнен за {elapsed:.1f}с, следующий через {delay:.0f}с")
        await asyncio.sleep(delay)


if __name__ == "__main__":
    asyncio.run(main())
