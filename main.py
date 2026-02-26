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
CHAT_ID = int(os.getenv("CHAT_ID"))

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

KEYWORDS = [
    "box",
    "бокс",
    "crypto box",
    "mystery box",
    "福袋",
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
]

MAX_DAYS_OLD = 7  # не отправлять посты старше этого количества дней
# ========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.FileHandler("bot.log", encoding="utf-8"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(TELEGRAM_TOKEN)

LAST_GUIDS_FILE = "last_guids.json"
if os.path.exists(LAST_GUIDS_FILE):
    with open(LAST_GUIDS_FILE, "r", encoding="utf-8") as f:
        LAST_GUIDS = json.load(f)
else:
    LAST_GUIDS = {}


def save_last_guids():
    with open(LAST_GUIDS_FILE, "w", encoding="utf-8") as f:
        json.dump(LAST_GUIDS, f, ensure_ascii=False, indent=2)


def extract_codes(text: str):
    # Ищет все возможные коды (6–20 символов A-Z0-9)
    return re.findall(r"\b[A-Z0-9]{6,20}\b", text.upper())


def extract_username(feed):
    """Извлекает username из title фида (если есть @) или возвращает 'Unknown'."""
    title = feed.feed.get("title", "")
    if "@" in title:
        return title.split("@")[-1].strip()
    return "Unknown"


async def send_telegram_message(
    text, parse_mode: str = "HTML", disable_web_page_preview: bool = True
):
    """Отправка сообщения в отдельном потоке, чтобы не блокировать asyncio."""
    return await asyncio.to_thread(
        bot.send_message,
        CHAT_ID,
        text,
        parse_mode=parse_mode,
        disable_web_page_preview=disable_web_page_preview,
    )


async def send_telegram_media(media_type: str, url: str, reply_to_message_id: int):
    """Отправка фото или видео в отдельном потоке."""
    try:
        if media_type == "photo":
            await asyncio.to_thread(
                bot.send_photo, CHAT_ID, url, reply_to_message_id=reply_to_message_id
            )
        elif media_type == "video":
            await asyncio.to_thread(
                bot.send_video, CHAT_ID, url, reply_to_message_id=reply_to_message_id
            )
    except Exception as e:
        logger.warning(f"Не удалось отправить медиа {url}: {e}")


async def process_feed(rss_url: str) -> int:
    """Обрабатывает один RSS-канал, возвращает количество отправленных постов."""
    try:
        feed = feedparser.parse(rss_url)
        username = extract_username(feed)
        last_guid = LAST_GUIDS.get(rss_url, "")
        sent_count = 0

        # Порог даты – не старше MAX_DAYS_OLD
        cutoff_date = datetime.now() - timedelta(days=MAX_DAYS_OLD)

        # Идём с конца, чтобы новые были в начале (feedparser выдаёт от старых к новым)
        for entry in reversed(feed.entries):
            guid = entry.get("id") or entry.link

            # Пропускаем уже обработанные
            if guid == last_guid:
                break

            # Проверка даты (если есть)
            published = entry.get("published_parsed") or entry.get("updated_parsed")
            if published:
                pub_date = datetime(*published[:6])
                if pub_date < cutoff_date:
                    continue

            title = entry.get("title", "")
            description = entry.get("description", "") or entry.get("summary", "")
            full_text = f"{title}\n\n{description}".strip()
            text_lower = full_text.lower()

            if any(kw in text_lower for kw in KEYWORDS):
                codes = extract_codes(full_text)
                codes_str = ""
                if codes:
                    codes_str = (
                        "\n\n🧧 <b>КОДЫ В ПОСТЕ:</b>\n"
                        + "\n".join([f"<code>{c}</code>" for c in codes])
                    )

                # Экранируем HTML, но оставляем наши <code> и <b> (они добавляются после экранирования)
                safe_text = html.escape(full_text)
                message = f"""
🔥 <b>НОВАЯ РАЗДАЧА / БОКС / ЗАГАДКА</b> от @{username}

{safe_text}

{codes_str}
🕒 {entry.get('published', datetime.now().strftime('%d.%m %H:%M'))}
🔗 {entry.link}
                """.strip()

                # Отправляем текст
                sent_msg = await send_telegram_message(message)

                # Отправляем медиа (enclosures и media_content)
                media_urls: list[tuple[str, str]] = []
                # 1) Стандартные enclosures
                for link in entry.get("links", []):
                    if link.get("rel") == "enclosure" and link.get(
                        "type", ""
                    ).startswith(("image/", "video/")):
                        media_urls.append(
                            (link["type"].split("/")[0], link["href"])
                        )  # ('image', url)
                # 2) Нестандартное поле media_content
                if hasattr(entry, "media_content") and entry.media_content:
                    for media in entry.media_content:
                        if media.get("url"):
                            mtype = media.get("type", "").split("/")[0]
                            if mtype in ("image", "video"):
                                media_urls.append((mtype, media["url"]))

                for mtype, url in media_urls[:4]:  # не более 4 вложений
                    await send_telegram_media(mtype, url, sent_msg.message_id)

                logger.info(f"✅ Отправлено от @{username} | кодов: {len(codes)}")
                sent_count += 1

            LAST_GUIDS[rss_url] = guid

        return sent_count

    except Exception as e:
        logger.error(f"Ошибка при обработке {rss_url}: {e}")
        return 0


async def main():
    logger.info("🔥 VIP Binance Box & Riddle Bot ЗАПУЩЕН")

    while True:
        total_sent = 0
        for rss_url in RSS_FEEDS:
            total_sent += await process_feed(rss_url)

        if total_sent > 0:
            save_last_guids()
            logger.info(
                f"✅ Цикл завершён, отправлено {total_sent} постов, GUID сохранены"
            )
        else:
            logger.info("⏳ Новых постов нет")

        # Случайная пауза 5–12 минут
        delay = random.uniform(300, 720)
        logger.info(f"💤 Следующая проверка через {delay:.0f} секунд")
        await asyncio.sleep(delay)


if __name__ == "__main__":
    asyncio.run(main())
