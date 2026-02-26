import re
import asyncio
from telethon import TelegramClient, events

# Подключение (используй свои старые ключи)
API_ID = 37881117  
API_HASH = 'd46e644f9d2c3bfefedcce9161be3264'  

client = TelegramClient('new_ultimate_session', API_ID, API_HASH)

# ==========================================
# 1. АБСОЛЮТНАЯ БРОНЯ ДЛЯ КОДОВ (Твоя идея!)
# ==========================================
# Формула: Строго 8-15 символов. ОБЯЗАТЕЛЬНО минимум 1 буква И минимум 1 цифра. 
# Никаких чистых ID или чистых слов. Только заглавные.
STRICT_CODE_PATTERN = r'\b(?=[A-Z0-9]*[A-Z])(?=[A-Z0-9]*[0-9])[A-Z0-9]{8,15}\b'

# Ссылки на чеки (CryptoBot, Wallet, xRocket)
LINK_PATTERN = r't\.me/(?:CryptoBot|xrocket|wallet)\?start=[a-zA-Z0-9_-]+'

# ==========================================
# 2. РАДАР НА "КИТОВ" И РАЗДАЧИ
# ==========================================
WHALE_TRIGGERS = [
    'red packet', 'prize pool', 'giveaway', 'claim usdt', 
    'airdrop pool', 'красный пакет', 'пул на'
]

# ==========================================
# 3. ПОИСК КЛИЕНТОВ НА БОТОВ (Freelance)
# ==========================================
JOB_TRIGGERS = [
    'need a dev', 'hiring python', 'build a bot', 'looking for a developer', 
    'paying in usdt', 'нужен разработчик', 'кто напишет бота', 'ищу кодера'
]

# ==========================================
# 4. АНТИ-СПАМ ФИЛЬТР
# ==========================================
IGNORE_WORDS = [
    'welcome', 'hello', 'rules', 'guidelines', 'joined', 
    'ціна', 'грн', 'scam', 'test', 'testnet'
]

@client.on(events.NewMessage)
async def ultimate_sniper(event):
    # Защита от лагов сети (Retry Logic на уровне события)
    try:
        text = event.raw_text
        if not text:
            return

        low_text = text.lower()
        
        # Если есть спам-слово — сразу выходим, не тратим ресурсы сервера
        if any(word in low_text for word in IGNORE_WORDS):
            return

        found_codes = re.findall(STRICT_CODE_PATTERN, text)
        found_links = re.findall(LINK_PATTERN, text)
        
        is_whale = any(word in low_text for word in WHALE_TRIGGERS)
        is_job = any(word in low_text for word in JOB_TRIGGERS)

        # Если сработало ХОТЬ ЧТО-ТО из наших радаров:
        if found_codes or found_links or is_whale or is_job:
            chat = await event.get_chat()
            chat_title = getattr(chat, 'title', 'Неизвестный чат')
            post_link = f"https://t.me/c/{chat.id}/{event.id}" if chat.id else "Ссылка скрыта"

            # Формируем красивый HTML-отчет
            msg = f"<b>🚨 VIBEGUARD: ПЕРЕХВАТ ЦЕЛИ</b>\n\n"
            msg += f"📍 <b>Локация:</b> {chat_title}\n\n"

            if is_job:
                msg += "👨‍💻 <b>АЛЕРТ: КТО-ТО ИЩЕТ РАЗРАБОТЧИКА! (БЕРИ ЗАКАЗ)</b>\n"
            
            if is_whale:
                msg += "🐳 <b>АЛЕРТ: КИТОВАЯ РАЗДАЧА (PRIZE POOL)!</b>\n"

            if found_codes:
                msg += f"🔑 <b>Идеальные Коды:</b> <code>{', '.join(found_codes)}</code>\n"
                
            if found_links:
                msg += f"🔗 <b>Чеки/Пакеты:</b> <code>{', '.join(found_links)}</code>\n"

            msg += f"\n📝 <b>Текст сообщения:</b>\n<i>{text[:250]}...</i>\n\n"
            msg += f"🔗 <a href='{post_link}'>ПЕРЕЙТИ К ПОСТУ (ЖМИ)</a>"

            # Отправка в Избранное
            await client.send_message('me', msg, parse_mode='html')
            print(f"🎯 ИДЕАЛЬНЫЙ ЗАХВАТ в {chat_title}")

    except Exception as e:
        print(f"⚠️ Ошибка парсинга: {e}")

async def main_loop():
    # Бесконечный цикл работы (Infinity Polling)
    while True:
        try:
            print("🚀 VibeGuard Монолит запущен! Ищу Китов, Идеальные Коды и Заказы...")
            await client.start()
            await client.run_until_disconnected()
        except ConnectionError:
            print("🔌 Обрыв связи. Переподключение через 5 сек...")
            await asyncio.sleep(5)
        except Exception as e:
            print(f"Критический сбой: {e}. Рестарт через 10 сек...")
            await asyncio.sleep(10)

if __name__ == '__main__':
    asyncio.run(main_loop())