import logging
from telethon import TelegramClient, events

# --- ВСТАВЬ СВОИ ДАННЫЕ СЮДА ---
API_ID =32921602
API_HASH ='36a890210f2bc2ad5796a87f21f407a1'  # Твой API HASH (в кавычках)

# Смешанные триггеры (USDT запад + СНГ)
# --- ОБНОВЛЕННЫЕ НАСТРОЙКИ ---
# Ищем только конкретные запросы на наем
# Ищем только "голодных" заказчиков
KEYWORDS = [
    'hiring', 'looking for', 'need a dev', 'budget', 'urgent', 
    'ищу', 'нужен разработчик', 'заказ', 'требуется', 'кто сделает', 'бюджет'
]

# Безжалостно фильтруем других кодеров и спам-сервисы
EXCLUDE = [
    'услуги', 'команда', 'portfolio', 'рассылка', 'продам', 'sell', 
    'разработка под ключ', 'scarface', 'ww code', 'i am a dev', 'hire me', 
    'наш стек', 'предлагаю', 'ready to work'
]

client = TelegramClient('hunter_session', API_ID, API_HASH)

@client.on(events.NewMessage)
async def handler(event):
    try:
        text = event.raw_text.lower()
        
        # Проверяем слова
        if any(word in text for word in KEYWORDS) and not any(ex in text for ex in EXCLUDE):
            chat = await event.get_chat()
            chat_title = chat.title if hasattr(chat, 'title') else "Группа"
            
            print(f"🎯 Нашел заказ в: {chat_title}")
            
            # Отправляем тебе в Избранное
            alert = (
                f"🎯 **НОВЫЙ ЗАКАЗ!**\n\n"
                f"📍 **Где:** {chat_title}\n"
                f"📝 **Текст:** {event.raw_text[:300]}...\n\n"
                f"🔗 [ПЕРЕЙТИ К ПОСТУ](https://t.me/c/{event.chat_id}/{event.id})"
            )
            await client.send_message('me', alert, parse_mode='md')
            
    except Exception as e:
        print(f"Ошибка чтения: {e}")

async def main():
    print("🚀 Охотник запущен! Слушаю твои группы (Web3 и Python)...")
    await client.start()
    await client.run_until_disconnected()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
