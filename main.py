import os
import re
import logging
from telethon import TelegramClient, events
from telethon.errors import ChannelPrivateError, UsernameNotOccupiedError, InviteHashExpiredError
from telethon.tl.functions.messages import ImportChatInviteRequest
from config import API_ID, API_HASH, ALLOWED_USER_ID  # Импортируем конфигурацию

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Имя файла сессии (будет создан в текущей папке)
session_name = 'my_session'

# Папка для скачивания медиа
download_folder = 'downloaded_media'
if not os.path.exists(download_folder):
    os.makedirs(download_folder)

# Создаем клиент с использованием файла сессии
client = TelegramClient(session_name, API_ID, API_HASH)

# Регулярные выражения для парсинга ссылок
INVITE_LINK_PATTERN = re.compile(r"https://t\.me/\+([\w-]+)")  # Пригласительная ссылка (например, https://t.me/+PbLTg54-mVhkNjUx)
GROUP_LINK_PATTERN = re.compile(r"https://t\.me/([^/]+)$")  # Ссылка на группу (например, https://t.me/groupname)
MESSAGE_LINK_PATTERN = re.compile(r"https://t\.me/c/(\d+)/(\d+)")  # Ссылка на сообщение (например, https://t.me/c/1234567890/75)

# Обработчик команды /start
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    # Проверяем, что сообщение от разрешённого пользователя
    if event.sender_id == ALLOWED_USER_ID:
        await event.respond("Привет! Отправь мне ссылку на группу или сообщение, чтобы я скачал медиафайлы.")
        logger.info(f"Пользователь {event.sender_id} запустил бота.")
    else:
        await event.respond("У вас нет доступа к этому боту.")
        logger.warning(f"Пользователь {event.sender_id} попытался получить доступ к боту.")

# Обработчик сообщений с ссылкой
@client.on(events.NewMessage)
async def handle_message(event):
    # Проверяем, что сообщение от разрешённого пользователя
    if event.sender_id != ALLOWED_USER_ID:
        return

    # Проверяем, является ли ссылка пригласительной
    invite_match = INVITE_LINK_PATTERN.search(event.text)
    if invite_match:
        try:
            await event.respond("Обнаружена пригласительная ссылка. Присоединяюсь к группе...")
            # Извлекаем хэш приглашения
            invite_hash = invite_match.group(1)
            # Присоединяемся к группе по пригласительной ссылке
            group_entity = await client(ImportChatInviteRequest(invite_hash))
            await event.respond("Успешно присоединился к группе. Начинаю скачивание медиафайлов...")
            # Скачиваем все медиафайлы из группы
            await download_all_media(event, group_entity)
        except InviteHashExpiredError:
            await event.respond("Пригласительная ссылка недействительна или истекла.")
            logger.error("Пригласительная ссылка недействительна или истекла.")
        except ChannelPrivateError:
            await event.respond("У вас нет доступа к этой группе или каналу.")
            logger.error("У пользователя нет доступа к группе или каналу.")
        except Exception as e:
            await event.respond(f"Ошибка: {e}")
            logger.error(f"Ошибка: {e}")
        return

    # Проверяем, является ли ссылка ссылкой на группу
    group_match = GROUP_LINK_PATTERN.search(event.text)
    if group_match:
        try:
            await event.respond("Начинаю скачивание медиафайлов из группы...")
            # Извлекаем username группы
            group_username = group_match.group(1)
            # Получаем сущность группы
            group_entity = await client.get_entity(group_username)
            # Скачиваем все медиафайлы из группы
            await download_all_media(event, group_entity)
        except UsernameNotOccupiedError:
            await event.respond("Группа или канал с таким username не найдены.")
            logger.error("Группа или канал с таким username не найдены.")
        except ChannelPrivateError:
            await event.respond("У вас нет доступа к этой группе или каналу.")
            logger.error("У пользователя нет доступа к группе или каналу.")
        except Exception as e:
            await event.respond(f"Ошибка: {e}")
            logger.error(f"Ошибка: {e}")
        return

    # Проверяем, является ли ссылка ссылкой на сообщение
    message_match = MESSAGE_LINK_PATTERN.search(event.text)
    if message_match:
        try:
            await event.respond("Скачиваю содержимое сообщения...")
            # Извлекаем ID чата и ID сообщения
            chat_id = int(message_match.group(1))
            message_id = int(message_match.group(2))

            # Преобразуем ID чата в отрицательное число (если необходимо)
            if chat_id > 0:
                chat_id = int(f"-100{chat_id}")

            # Получаем сущность чата
            chat_entity = await client.get_entity(chat_id)
            # Получаем сообщение по ID
            message = await client.get_messages(chat_entity, ids=message_id)

            # Проверяем, есть ли медиа в сообщении
            if message.media:
                await event.respond("Найдено медиа. Скачиваю...")
                # Скачиваем медиа в указанную папку
                file_path = await client.download_media(message, file=download_folder)
                await event.respond(f"Медиа скачано и сохранено: {file_path}")
            else:
                await event.respond("В этом сообщении нет медиафайлов.")
        except ChannelPrivateError:
            await event.respond("У вас нет доступа к этому чату или группа является приватной.")
            logger.error("У пользователя нет доступа к чату или группа является приватной.")
        except ValueError:
            await event.respond("Некорректный ID чата или сообщения.")
            logger.error("Некорректный ID чата или сообщения.")
        except Exception as e:
            await event.respond(f"Ошибка: {e}")
            logger.error(f"Ошибка: {e}")
        return

    # Если ссылка не распознана
    await event.respond("Это не похоже на ссылку на группу или сообщение. Попробуй еще раз.")
    logger.warning("Получена нераспознанная ссылка.")

async def download_all_media(event, group_entity, limit=100):
    """
    Скачивает все медиафайлы из группы или канала.
    """
    await event.respond(f"Скачиваю последние {limit} медиафайлов из группы...")
    # Получаем историю сообщений с пагинацией
    offset_id = 0
    total_count_limit = limit
    downloaded_files = []

    while True:
        messages = await client.get_messages(group_entity, limit=100, offset_id=offset_id)
        if not messages:
            break

        for message in messages:
            if message.media:
                try:
                    file_path = await client.download_media(message, file=download_folder)
                    downloaded_files.append(file_path)
                    await event.respond(f"Скачано: {file_path}")
                except Exception as e:
                    await event.respond(f"Ошибка при скачивании медиа: {e}")
                    logger.error(f"Ошибка при скачивании медиа: {e}")

            offset_id = messages[-1].id
            if len(downloaded_files) >= total_count_limit:
                break

        if len(downloaded_files) >= total_count_limit:
            break

    if downloaded_files:
        await event.respond(f"Всего скачано {len(downloaded_files)} медиафайлов.")
    else:
        await event.respond("В этой группе не найдено медиафайлов.")

# Удаление файла сессии после завершения работы
def cleanup_session():
    session_file = f"{session_name}.session"
    if os.path.exists(session_file):
        os.remove(session_file)
        logger.info("Файл сессии удалён.")

# Запуск бота
logger.info("Бот запущен...")
try:
    with client:
        client.run_until_disconnected()
finally:
    # Удаляем файл сессии после завершения работы
    cleanup_session()