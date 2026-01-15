import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, WebAppInfo, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import sqlite3
import os
from aiohttp import web
import json

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Токен бота (получите у @BotFather)
BOT_TOKEN = os.getenv('BOT_TOKEN', '8445717764:AAGSqqm_DVuhgqkI-rbiSxH2caeC_on3KhQ')

# ID администраторов (укажите свои ID через запятую)
# Чтобы узнать свой ID, напишите боту @userinfobot
ADMIN_IDS = [int(x) for x in os.getenv('ADMIN_IDS', '1226518807').split(',') if x.strip()]

# Реферальная ссылка казино (замените на свою)
# Формат Telegram Mini App: https://t.me/bot_name/app?startapp=PARAMS
# Можно использовать {user_id} для подстановки ID пользователя
# По умолчанию используется ссылка из базы данных или переменной окружения
DEFAULT_CASINO_REF_LINK = os.getenv('CASINO_REF_LINK', 'https://t.me/LB_Chainreak_bot/app?startapp=bXN0PTB4NDkxYjMxMTcmbT1zdG9wa2EmYz1Ic2pzag')

# Канал для подписки
CHANNEL_USERNAME = 'maksoncikaz'  # Без @ для проверки через API
CHANNEL_LINK = 'https://t.me/maksoncikaz'
CHANNEL_ID = None  # Можно указать chat_id канала напрямую (например: -1001234567890)

# Ссылка на веб-приложение
WEB_APP_LINK = 'https://tower-b0t-web.vercel.app/'

# Пути к фотографиям (можно использовать локальные файлы или URL)
# Примеры:
# WELCOME_PHOTO = "images/welcome.jpg"  # Локальный файл
# WELCOME_PHOTO = "https://example.com/image.jpg"  # URL из интернета
# WELCOME_PHOTO = None  # Без фото

# Используем абсолютные пути к фото
BASE_IMAGES_DIR = os.path.join(os.path.dirname(__file__), "images")

# Фото для приветствия
WELCOME_PHOTO_PATH = os.path.join(BASE_IMAGES_DIR, "welcome.webp")
WELCOME_PHOTO = WELCOME_PHOTO_PATH if os.path.exists(WELCOME_PHOTO_PATH) else None
if not WELCOME_PHOTO:
    logger.info("Фото приветствия не найдено, будет использоваться текстовое сообщение")

# Фото для главного меню (приоритет: main_menu.webp > wiasa.webp)
MAIN_MENU_PHOTO_PATH = os.path.join(BASE_IMAGES_DIR, "main_menu.webp")
if not os.path.exists(MAIN_MENU_PHOTO_PATH):
    MAIN_MENU_PHOTO_PATH = os.path.join(BASE_IMAGES_DIR, "wiasa.webp")
MAIN_MENU_PHOTO = MAIN_MENU_PHOTO_PATH if os.path.exists(MAIN_MENU_PHOTO_PATH) else None
if not MAIN_MENU_PHOTO:
    logger.info("Фото главного меню не найдено, будет использоваться текстовое сообщение")

# Фото для экрана подписки
SUBSCRIPTION_PHOTO_PATH = os.path.join(BASE_IMAGES_DIR, "subscription.webp")
SUBSCRIPTION_PHOTO = SUBSCRIPTION_PHOTO_PATH if os.path.exists(SUBSCRIPTION_PHOTO_PATH) else None

# Фото для экрана депозита
DEPOSIT_PHOTO_PATH = os.path.join(BASE_IMAGES_DIR, "deposit.webp")
DEPOSIT_PHOTO = DEPOSIT_PHOTO_PATH if os.path.exists(DEPOSIT_PHOTO_PATH) else None

# Фото для успешного подтверждения
SUCCESS_PHOTO_PATH = os.path.join(BASE_IMAGES_DIR, "success.webp")
SUCCESS_PHOTO = SUCCESS_PHOTO_PATH if os.path.exists(SUCCESS_PHOTO_PATH) else None

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Middleware для логирования всех входящих сообщений и команд
@dp.update.outer_middleware()
async def logging_middleware(handler, event, data):
    """Логирование всех входящих обновлений для диагностики"""
    try:
        if hasattr(event, 'message') and event.message:
            msg = event.message
            if msg.text:
                if msg.text.startswith('/'):
                    logger.info(f"📨 Получена команда: {msg.text} от пользователя {msg.from_user.id}")
                else:
                    logger.debug(f"📨 Получено сообщение: {msg.text[:50]}... от пользователя {msg.from_user.id}")
        elif hasattr(event, 'callback_query') and event.callback_query:
            logger.debug(f"📨 Получен callback: {event.callback_query.data} от пользователя {event.callback_query.from_user.id}")
    except Exception as e:
        logger.debug(f"Ошибка в logging middleware: {e}")
    
    return await handler(event, data)

def is_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь администратором"""
    return user_id in ADMIN_IDS if ADMIN_IDS else False

# Состояния для FSM
class DepositStates(StatesGroup):
    waiting_for_amount = State()
    waiting_for_proof = State()

# База данных
DB_NAME = 'tower_bot.db'

def init_db():
    """Инициализация базы данных"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            has_deposit INTEGER DEFAULT 0,
            deposit_amount REAL DEFAULT 0,
            deposit_proof TEXT,
            deposit_date TIMESTAMP,
            referral_link_used INTEGER DEFAULT 0,
            casino_account TEXT,
            deposit_verified INTEGER DEFAULT 0,
            subscribed_to_channel INTEGER DEFAULT 0,
            start_used INTEGER DEFAULT 0
        )
    ''')
    
    # Добавляем недостающие колонки, если таблица уже существует
    try:
        cursor.execute('ALTER TABLE users ADD COLUMN subscribed_to_channel INTEGER DEFAULT 0')
    except sqlite3.OperationalError:
        pass  # Колонка уже существует
    
    try:
        cursor.execute('ALTER TABLE users ADD COLUMN start_used INTEGER DEFAULT 0')
    except sqlite3.OperationalError:
        pass  # Колонка уже существует
    
    # Таблица настроек (для хранения реферальной ссылки)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Инициализируем реферальную ссылку, если её нет
    cursor.execute('SELECT value FROM settings WHERE key = ?', ('referral_link',))
    if not cursor.fetchone():
        cursor.execute('''
            INSERT INTO settings (key, value) 
            VALUES (?, ?)
        ''', ('referral_link', DEFAULT_CASINO_REF_LINK))
    
    conn.commit()
    conn.close()
    logger.info("База данных инициализирована")

def get_user(user_id: int):
    """Получить информацию о пользователе"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def register_user(user_id: int, username: str = None, first_name: str = None):
    """Регистрация нового пользователя"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR IGNORE INTO users (user_id, username, first_name)
        VALUES (?, ?, ?)
    ''', (user_id, username, first_name))
    conn.commit()
    conn.close()

def update_deposit(user_id: int, amount: float, proof: str = None):
    """Обновить информацию о депозите"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE users 
        SET has_deposit = 1, deposit_amount = ?, deposit_proof = ?, deposit_date = CURRENT_TIMESTAMP
        WHERE user_id = ?
    ''', (amount, proof, user_id))
    conn.commit()
    conn.close()

def check_deposit(user_id: int) -> bool:
    """Проверить, есть ли у пользователя депозит"""
    user = get_user(user_id)
    if user:
        return bool(user[4])  # has_deposit
    return False

def get_referral_link(user_id: int) -> str:
    """Получить реферальную ссылку для пользователя"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM settings WHERE key = ?', ('referral_link',))
    result = cursor.fetchone()
    conn.close()
    
    # Используем ссылку из базы или дефолтную
    link_template = result[0] if result else DEFAULT_CASINO_REF_LINK
    
    # Если в ссылке есть {user_id}, заменяем его
    if '{user_id}' in link_template:
        return link_template.format(user_id=user_id)
    return link_template

def set_referral_link(link: str) -> bool:
    """Обновить реферальную ссылку"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO settings (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        ''', ('referral_link', link))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Ошибка обновления реферальной ссылки: {e}")
        return False

def mark_referral_used(user_id: int):
    """Отметить, что пользователь использовал реферальную ссылку"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE users 
        SET referral_link_used = 1
        WHERE user_id = ?
    ''', (user_id,))
    conn.commit()
    conn.close()

def check_referral_used(user_id: int) -> bool:
    """Проверить, использовал ли пользователь реферальную ссылку"""
    user = get_user(user_id)
    if user:
        return bool(user[8])  # referral_link_used
    return False

def update_casino_account(user_id: int, account: str):
    """Обновить информацию об аккаунте в казино"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE users 
        SET casino_account = ?
        WHERE user_id = ?
    ''', (account, user_id))
    conn.commit()
    conn.close()

def verify_deposit(user_id: int, amount: float = 0):
    """Подтвердить депозит пользователя"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE users 
        SET has_deposit = 1, deposit_amount = ?, deposit_verified = 1, deposit_date = CURRENT_TIMESTAMP
        WHERE user_id = ?
    ''', (amount, user_id))
    conn.commit()
    conn.close()

def check_subscription(user_id: int) -> bool:
    """Проверить, подписан ли пользователь на канал"""
    user = get_user(user_id)
    if user:
        return bool(user[11]) if len(user) > 11 else False
    return False

def mark_subscribed(user_id: int):
    """Отметить, что пользователь подписан на канал"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE users 
        SET subscribed_to_channel = 1
        WHERE user_id = ?
    ''', (user_id,))
    conn.commit()
    conn.close()

async def check_user_subscription(user_id: int) -> bool:
    """Проверить подписку пользователя на канал через API"""
    try:
        channel_username = CHANNEL_USERNAME.replace('@', '').strip()
        
        logger.info(f"🔍 Проверка подписки для пользователя {user_id} на канал {channel_username}")
        
        chat_member = None
        errors = []
        
        # Добавляем таймаут для всей операции проверки подписки (максимум 10 секунд)
        try:
            # Вариант 1: Если указан CHANNEL_ID, используем его
            if CHANNEL_ID:
                try:
                    logger.info(f"Попытка проверки через CHANNEL_ID: {CHANNEL_ID}")
                    chat_member = await asyncio.wait_for(
                        bot.get_chat_member(CHANNEL_ID, user_id),
                        timeout=5.0
                    )
                    logger.info(f"✅ Успешно через CHANNEL_ID")
                except asyncio.TimeoutError:
                    errors.append(f"CHANNEL_ID: timeout")
                    logger.warning(f"Таймаут при проверке через CHANNEL_ID")
                except Exception as e:
                    errors.append(f"CHANNEL_ID: {e}")
                    logger.warning(f"Ошибка через CHANNEL_ID: {e}")
            
            # Вариант 2: Через username без @
            if not chat_member:
                try:
                    logger.info(f"Попытка проверки через username: {channel_username}")
                    chat_member = await asyncio.wait_for(
                        bot.get_chat_member(channel_username, user_id),
                        timeout=5.0
                    )
                    logger.info(f"✅ Успешно через username")
                except asyncio.TimeoutError:
                    errors.append(f"username: timeout")
                    logger.warning(f"Таймаут при проверке через username")
                except Exception as e:
                    errors.append(f"username: {e}")
                    logger.warning(f"Ошибка через username: {e}")
            
            # Вариант 3: Через username с @
            if not chat_member:
                try:
                    logger.info(f"Попытка проверки через @{channel_username}")
                    chat_member = await asyncio.wait_for(
                        bot.get_chat_member(f'@{channel_username}', user_id),
                        timeout=5.0
                    )
                    logger.info(f"✅ Успешно через @username")
                except asyncio.TimeoutError:
                    errors.append(f"@username: timeout")
                    logger.warning(f"Таймаут при проверке через @username")
                except Exception as e:
                    errors.append(f"@username: {e}")
                    logger.warning(f"Ошибка через @username: {e}")
            
            # Вариант 4: Получаем chat и используем его ID
            if not chat_member:
                try:
                    logger.info(f"Попытка получить chat по username: {channel_username}")
                    chat = await asyncio.wait_for(
                        bot.get_chat(channel_username),
                        timeout=5.0
                    )
                    logger.info(f"Chat получен: ID={chat.id}, Type={chat.type}")
                    chat_member = await asyncio.wait_for(
                        bot.get_chat_member(chat.id, user_id),
                        timeout=5.0
                    )
                    logger.info(f"✅ Успешно через chat.id")
                except asyncio.TimeoutError:
                    errors.append(f"chat.id: timeout")
                    logger.warning(f"Таймаут при проверке через chat.id")
                except Exception as e:
                    errors.append(f"chat.id: {e}")
                    logger.warning(f"Ошибка через chat.id: {e}")
        except Exception as e:
            logger.error(f"Критическая ошибка при проверке подписки: {e}")
            return check_subscription(user_id)
        
        if chat_member:
            is_member = chat_member.status in ['member', 'administrator', 'creator']
            
            logger.info(f"✅ Результат проверки для {user_id}: статус = {chat_member.status}, подписан = {is_member}")
            
            # Обновляем статус в базе данных
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET subscribed_to_channel = ? WHERE user_id = ?', (1 if is_member else 0, user_id))
            conn.commit()
            conn.close()
            
            return is_member
        else:
            # Все варианты не сработали
            error_summary = " | ".join(errors)
            logger.error(f"❌ Все варианты проверки не сработали для {user_id}. Ошибки: {error_summary}")
            
            # Проверяем конкретные ошибки
            error_str = error_summary.lower()
            if "chat not found" in error_str or "bad request" in error_str:
                logger.error(f"Канал '{channel_username}' не найден или недоступен для бота")
            elif "not enough rights" in error_str or "forbidden" in error_str or "can't get chat member" in error_str:
                logger.error("⚠️ У бота нет прав для проверки подписки!")
                logger.error("Убедитесь, что:")
                logger.error("1. Бот добавлен в канал как администратор")
                logger.error("2. У бота есть права 'View channel members' (Просмотр участников)")
                logger.error("3. Канал публичный или бот имеет доступ")
            elif "user not found" in error_str:
                logger.error(f"Пользователь {user_id} не найден")
            
            # Возвращаем статус из базы данных как запасной вариант
            return check_subscription(user_id)
            
    except Exception as e:
        logger.error(f"❌ Критическая ошибка при проверке подписки для {user_id}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        # В случае ошибки возвращаем статус из базы данных
        return check_subscription(user_id)

def mark_start_used(user_id: int):
    """Отметить, что пользователь использовал /start"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Используем INSERT OR REPLACE чтобы гарантировать, что запись будет обновлена
    cursor.execute('''
        UPDATE users 
        SET start_used = 1
        WHERE user_id = ?
    ''', (user_id,))
    # Если запись не существует, создаем её
    if cursor.rowcount == 0:
        cursor.execute('''
            INSERT OR IGNORE INTO users (user_id, start_used)
            VALUES (?, 1)
        ''', (user_id,))
    conn.commit()
    conn.close()

def check_start_used(user_id: int) -> bool:
    """Проверить, использовал ли пользователь /start"""
    user = get_user(user_id)
    if user:
        return bool(user[12]) if len(user) > 12 else False
    return False

async def ensure_bot_connection():
    """Проверка и восстановление соединения с ботом"""
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            # Используем таймаут для проверки соединения
            await asyncio.wait_for(bot.get_me(), timeout=10)
            return True
        except asyncio.TimeoutError:
            logger.warning(f"⚠️ Таймаут при проверке соединения (попытка {attempt + 1}/{max_attempts})")
        except Exception as e:
            logger.warning(f"⚠️ Проблема с соединением (попытка {attempt + 1}/{max_attempts}): {e}")
        
        if attempt < max_attempts - 1:
            # Переподключаемся
            try:
                logger.info(f"🔄 Переподключение сессии бота (попытка {attempt + 1})...")
                await bot.session.close()
            except:
                pass
            
            try:
                from aiogram.client.session.aiohttp import AiohttpSession
                bot._session = AiohttpSession()
                await bot.session.create()
                await asyncio.sleep(2)  # Даем время на установку соединения
            except Exception as reconnect_error:
                logger.error(f"Ошибка переподключения: {reconnect_error}")
        else:
            logger.error(f"❌ Не удалось восстановить соединение после {max_attempts} попыток")
            return False
    return False

async def safe_edit_message(callback: CallbackQuery, text: str, reply_markup: InlineKeyboardMarkup = None, parse_mode: str = "HTML"):
    """Безопасное редактирование сообщения: проверяет тип сообщения и использует правильный метод"""
    try:
        # Если сообщение содержит фото, удаляем его и отправляем новое текстовое сообщение
        if callback.message.photo:
            await callback.message.delete()
            await callback.message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
        else:
            # Если сообщение текстовое, редактируем его
            await callback.message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except Exception as e:
        logger.error(f"Ошибка при редактировании сообщения: {e}")
        # Если редактирование не удалось, удаляем старое сообщение и отправляем новое
        try:
            await callback.message.delete()
        except:
            pass
        await callback.message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)

# Команда /start - ВАЖНО: должна быть ПЕРЕД другими обработчиками сообщений
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Обработка команды /start - всегда должна работать"""
    start_time = asyncio.get_event_loop().time()
    try:
        user_id = message.from_user.id
        username = message.from_user.username
        first_name = message.from_user.first_name
        
        logger.info(f"✅ Обработка команды /start от пользователя {user_id} (username: @{username or 'нет'})")
        
        # Регистрируем пользователя с таймаутом
        try:
            # Используем asyncio.to_thread для операций с БД, чтобы не блокировать event loop
            loop = asyncio.get_event_loop()
            await asyncio.wait_for(
                loop.run_in_executor(None, lambda: register_user(user_id, username, first_name)),
                timeout=2.0
            )
            await asyncio.wait_for(
                loop.run_in_executor(None, lambda: mark_start_used(user_id)),
                timeout=2.0
            )
        except asyncio.TimeoutError:
            logger.warning(f"Таймаут при регистрации пользователя {user_id}")
            # Продолжаем выполнение даже при таймауте
        except Exception as e:
            logger.error(f"Ошибка регистрации пользователя {user_id}: {e}")
            # Продолжаем выполнение даже при ошибке регистрации
        
        # Главное меню
        keyboard_buttons = [
            [InlineKeyboardButton(text="📊 Получить сигнал", callback_data="get_signal")],
            [InlineKeyboardButton(text="📞 Поддержка", url="https://t.me/nomep999")],
            [InlineKeyboardButton(text="💬 Наш ТГК", url=CHANNEL_LINK)]
        ]
        
        # Добавляем кнопку панели администратора только для админов
        try:
            if is_admin(user_id):
                keyboard_buttons.append([InlineKeyboardButton(text="⚙️ Панель администратора", callback_data="admin_panel")])
        except Exception as e:
            logger.error(f"Ошибка проверки прав администратора: {e}")
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        text = (
            "🏠 <b>Добро пожаловать в главное меню!</b>\n\n"
            "Вы находитесь в сигнальном боте <b>TOWER BOT AI</b> 🎯\n\n"
            "📊 <b>Функционал бота:</b>\n"
            "• Получение точных сигналов для игры Tower Rush\n"
            "• Анализ с помощью искусственного интеллекта\n"
            "• Прогнозирование результатов с высокой вероятностью\n"
            "• Удобный интерфейс и быстрый доступ к сигналам\n\n"
            "Выберите действие из меню ниже 👇"
        )
        
        # Отправляем текстовое сообщение с таймаутом
        try:
            await asyncio.wait_for(
                message.answer(text, reply_markup=keyboard, parse_mode="HTML"),
                timeout=10.0
            )
        except asyncio.TimeoutError:
            logger.error(f"Таймаут при отправке сообщения /start пользователю {user_id}")
            # Пытаемся отправить простое сообщение без форматирования
            try:
                await asyncio.wait_for(
                    message.answer("🏠 Добро пожаловать в главное меню! Используйте кнопки ниже.", reply_markup=keyboard),
                    timeout=5.0
                )
            except Exception as e2:
                logger.error(f"Критическая ошибка отправки сообщения: {e2}")
                raise
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения /start: {e}")
            # Пытаемся отправить простое сообщение без форматирования
            try:
                await message.answer("🏠 Добро пожаловать в главное меню! Используйте кнопки ниже.", reply_markup=keyboard)
            except Exception as e2:
                logger.error(f"Критическая ошибка отправки сообщения: {e2}")
                raise
        
        elapsed_time = asyncio.get_event_loop().time() - start_time
        logger.info(f"✅ Команда /start успешно обработана для пользователя {user_id} за {elapsed_time:.2f} сек")
        
    except Exception as e:
        error_type = type(e).__name__
        logger.error(f"❌ ОШИБКА при обработке /start: {error_type}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        try:
            await message.answer("❌ Произошла ошибка. Попробуйте еще раз через несколько секунд.")
        except Exception as e2:
            logger.error(f"Не удалось отправить сообщение об ошибке: {e2}")

# Обработка callback запросов
@dp.callback_query()
async def process_callback(callback: CallbackQuery, state: FSMContext):
    try:
        user_id = callback.from_user.id
        has_deposit = check_deposit(user_id)
    except Exception as e:
        logger.error(f"Ошибка при получении данных пользователя в callback: {e}")
        try:
            await callback.answer("❌ Произошла ошибка. Попробуйте еще раз.", show_alert=True)
        except:
            pass
        return
    
    try:
        # Проверяем подписку на канал для всех действий (кроме админских и подписки)
        if callback.data not in ["admin_approve_", "admin_reject_", "admin_panel", "admin_users", "admin_stats", "admin_give_access", "admin_set_referral", "check_subscription", "force_subscribe", "start_bot", "back_to_menu"]:
            is_subscribed = await check_user_subscription(user_id)
            
            # Если пользователь отписался - возвращаем на экран подписки
            if not is_subscribed and has_deposit:
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute('UPDATE users SET subscribed_to_channel = 0 WHERE user_id = ?', (user_id,))
                conn.commit()
                conn.close()
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📢 Подписаться на канал", url=CHANNEL_LINK)],
                    [InlineKeyboardButton(text="✅ Я подписался", callback_data="check_subscription")],
                    [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_to_menu")]
                ])
                
                text = (
                    "⚠️ <b>Доступ заблокирован!</b>\n\n"
                    "Вы отписались от нашего канала.\n\n"
                    "Для продолжения работы необходимо подписаться на канал:\n\n"
                    f"💬 <b>{CHANNEL_USERNAME}</b>\n\n"
                    "1️⃣ Нажмите кнопку \"📢 Подписаться на канал\"\n"
                    "2️⃣ Подпишитесь на канал\n"
                    "3️⃣ Вернитесь в бота и нажмите \"✅ Я подписался\"\n\n"
                    "⚠️ <b>Важно:</b> Если вы отпишетесь от канала, доступ к сигналам будет заблокирован!"
                )
                
                await safe_edit_message(callback, text, keyboard)
                await callback.answer("❌ Вы не подписаны на канал!", show_alert=True)
                return
        
        # Обработка действий администратора
        if callback.data.startswith("admin_approve_"):
            if not is_admin(user_id):
                await callback.answer("❌ У вас нет прав для этого действия!", show_alert=True)
                return
            
            target_user_id = int(callback.data.split("_")[-1])
            verify_deposit(target_user_id, 0)
            
            try:
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🌐 Открыть Web-App", web_app=WebAppInfo(url=WEB_APP_LINK))],
                    [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_to_menu")]
                ])
                
                await bot.send_message(
                    target_user_id,
                    "✅ <b>Вам открыт доступ к сигнальному боту TOWER BOT AI!</b>\n\n"
                    "🎉 Поздравляем! Ваш депозит подтвержден администратором.\n\n"
                    "Теперь вы можете:\n"
                    "• Получать точные сигналы для игры Tower Rush\n"
                    "• Использовать все возможности бота\n"
                    "• Получать прогнозы с высокой вероятностью успеха\n\n"
                    f"🌐 <b>Ссылка на этого бота в Web-App:</b>\n"
                    f"{WEB_APP_LINK}\n\n"
                    "Используйте кнопки ниже для начала работы!",
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Ошибка отправки уведомления пользователю {target_user_id}: {e}")
            
            target_user = get_user(target_user_id)
            username = target_user[1] if target_user else "неизвестно"
            
            text_approve = (
                f"✅ <b>Депозит подтвержден!</b>\n\n"
                f"👤 Пользователь: @{username or 'без username'}\n"
                f"🆔 ID: {target_user_id}\n\n"
                f"Пользователь получил уведомление и доступ к сигналам."
            )
            await safe_edit_message(callback, text_approve)
            await callback.answer("✅ Депозит подтвержден!")
            return
        
        elif callback.data.startswith("admin_reject_"):
            if not is_admin(user_id):
                await callback.answer("❌ У вас нет прав для этого действия!", show_alert=True)
                return
            
            target_user_id = int(callback.data.split("_")[-1])
            
            try:
                await bot.send_message(
                    target_user_id,
                    "❌ <b>Ваш запрос на подтверждение депозита отклонен.</b>\n\n"
                    "Пожалуйста, убедитесь, что:\n"
                    "1️⃣ Вы зарегистрировались по реферальной ссылке\n"
                    "2️⃣ Вы сделали депозит в казино\n"
                    "3️⃣ Вы отправили правильное подтверждение\n\n"
                    "Если у вас есть вопросы, свяжитесь с менеджером @nomep999",
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Ошибка отправки уведомления пользователю {target_user_id}: {e}")
            
            await safe_edit_message(callback, "❌ Запрос отклонен. Пользователь уведомлен.")
            await callback.answer("❌ Запрос отклонен")
            return
        
        elif callback.data == "start_bot":
            # Обработка кнопки "Начать работу" из приветствия
            user_id = callback.from_user.id
            username = callback.from_user.username
            first_name = callback.from_user.first_name
            
            # Регистрируем пользователя
            register_user(user_id, username, first_name)
            mark_start_used(user_id)
            
            # Главное меню
            keyboard_buttons = [
                [InlineKeyboardButton(text="📊 Получить сигнал", callback_data="get_signal")],
                [InlineKeyboardButton(text="📞 Поддержка", url="https://t.me/nomep999")],
                [InlineKeyboardButton(text="💬 Наш ТГК", url=CHANNEL_LINK)]
            ]
            
            # Добавляем кнопку панели администратора только для админов
            if is_admin(user_id):
                keyboard_buttons.append([InlineKeyboardButton(text="⚙️ Панель администратора", callback_data="admin_panel")])
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
            
            text = (
                "🏠 <b>Добро пожаловать в главное меню!</b>\n\n"
                "Вы находитесь в сигнальном боте <b>TOWER BOT AI</b> 🎯\n\n"
                "📊 <b>Функционал бота:</b>\n"
                "• Получение точных сигналов для игры Tower Rush\n"
                "• Анализ с помощью искусственного интеллекта\n"
                "• Прогнозирование результатов с высокой вероятностью\n"
                "• Удобный интерфейс и быстрый доступ к сигналам\n\n"
                "Выберите действие из меню ниже 👇"
            )
            
            await safe_edit_message(callback, text, keyboard)
            await callback.answer()
            return
        
        elif callback.data == "get_signal":
            # Проверяем подписку на канал при каждом запросе сигнала
            is_subscribed = await check_user_subscription(user_id)
            
            # Если пользователь отписался - сбрасываем подписку и возвращаем на экран подписки
            if not is_subscribed and check_subscription(user_id):
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute('UPDATE users SET subscribed_to_channel = 0 WHERE user_id = ?', (user_id,))
                conn.commit()
                conn.close()
            
            if not is_subscribed:
                # Пользователь не подписан - показываем экран подписки
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📢 Подписаться на канал", url=CHANNEL_LINK)],
                    [InlineKeyboardButton(text="✅ Я подписался", callback_data="check_subscription")],
                    [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_to_menu")]
                ])
                
                text = (
                    "📢 <b>Подписка на канал</b>\n\n"
                    "Для получения доступа к сигналам необходимо подписаться на наш канал:\n\n"
                    f"💬 <b>{CHANNEL_USERNAME}</b>\n\n"
                    "1️⃣ Нажмите кнопку \"📢 Подписаться на канал\"\n"
                    "2️⃣ Подпишитесь на канал\n"
                    "3️⃣ Вернитесь в бота и нажмите \"✅ Я подписался\"\n\n"
                    "⚠️ <b>Важно:</b> Если вы отпишетесь от канала, доступ к сигналам будет заблокирован!"
                )
                
                await safe_edit_message(callback, text, keyboard)
                await callback.answer()
                return
            
            # Пользователь подписан - проверяем депозит
            if not has_deposit:
                # Показываем информацию о депозите
                referral_link = get_referral_link(user_id)
                referral_used = check_referral_used(user_id)
                
                if not referral_used:
                    # Пользователь еще не получил реферальную ссылку
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🎰 Получить реферальную ссылку", callback_data="get_referral")],
                        [InlineKeyboardButton(text="📞 Связаться с менеджером", url="https://t.me/nomep999")],
                        [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_to_menu")]
                    ])
                    
                    text = (
                        "💰 <b>Для получения доступа к сигнальному боту необходимо внести депозит</b>\n\n"
                        "📋 <b>Инструкция:</b>\n\n"
                        "1️⃣ Получите реферальную ссылку\n"
                        "2️⃣ Зарегистрируйтесь в казино по этой ссылке\n"
                        "3️⃣ Сделайте депозит в казино\n"
                        "4️⃣ Отправьте подтверждение менеджеру\n\n"
                        "💰 После подтверждения депозита вам будет открыт доступ к сигналам!"
                    )
                else:
                    # Пользователь уже получил ссылку, но депозит не подтвержден
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🎰 Моя реферальная ссылка", callback_data="show_referral")],
                        [InlineKeyboardButton(text="✅ Я сделал депозит", callback_data="confirm_deposit")],
                        [InlineKeyboardButton(text="📞 Связаться с менеджером", url="https://t.me/nomep999")],
                        [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_to_menu")]
                    ])
                    
                    text = (
                        "💰 <b>Для получения доступа к сигнальному боту необходимо внести депозит</b>\n\n"
                        "📋 <b>Инструкция:</b>\n\n"
                        "1️⃣ Перейдите по вашей реферальной ссылке\n"
                        "2️⃣ Зарегистрируйтесь в казино\n"
                        "3️⃣ Сделайте депозит\n"
                        "4️⃣ Нажмите \"✅ Я сделал депозит\" и отправьте подтверждение\n\n"
                        "⏳ После проверки менеджером вам будет открыт доступ к сигналам!"
                    )
                
                await safe_edit_message(callback, text, keyboard)
                await callback.answer()
                return
            
            # Пользователь подписан и имеет депозит - показываем сообщение с веб-апп
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🌐 Открыть Web-App", url=WEB_APP_LINK)],
                [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_to_menu")]
            ])
            
            text = (
                "✅ <b>Вам открыт доступ к сигнальному боту TOWER BOT AI!</b>\n\n"
                "🎉 Поздравляем! Ваш депозит подтвержден администратором.\n\n"
                "Теперь вы можете:\n"
                "• Получать точные сигналы для игры Tower Rush\n"
                "• Использовать все возможности бота\n"
                "• Получать прогнозы с высокой вероятностью успеха\n\n"
                f"🌐 <b>Ссылка на этого бота в Web-App:</b>\n"
                f"{WEB_APP_LINK}\n\n"
                "Используйте кнопки ниже для начала работы!"
            )
            
            await safe_edit_message(callback, text, keyboard)
            await callback.answer()
        
        elif callback.data == "check_subscription":
            # Проверка подписки после нажатия "Я подписался"
            await callback.answer("⏳ Проверяю подписку...")
            
            is_subscribed = await check_user_subscription(user_id)
            
            if is_subscribed:
                mark_subscribed(user_id)
                # Показываем информацию о депозите
                referral_link = get_referral_link(user_id)
                referral_used = check_referral_used(user_id)
                
                if not referral_used:
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🎰 Получить реферальную ссылку", callback_data="get_referral")],
                        [InlineKeyboardButton(text="📞 Связаться с менеджером", url="https://t.me/nomep999")],
                        [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_to_menu")]
                    ])
                else:
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🎰 Моя реферальная ссылка", callback_data="show_referral")],
                        [InlineKeyboardButton(text="✅ Я сделал депозит", callback_data="confirm_deposit")],
                        [InlineKeyboardButton(text="📞 Связаться с менеджером", url="https://t.me/nomep999")],
                        [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_to_menu")]
                    ])
                
                text = (
                    "✅ <b>Спасибо за подписку!</b>\n\n"
                    "💰 <b>Для получения доступа к сигнальному боту необходимо внести депозит</b>\n\n"
                    "📋 <b>Инструкция:</b>\n\n"
                    "1️⃣ Получите реферальную ссылку\n"
                    "2️⃣ Зарегистрируйтесь в казино по этой ссылке\n"
                    "3️⃣ Сделайте депозит в казино\n"
                    "4️⃣ Отправьте подтверждение менеджеру\n\n"
                    "💰 После подтверждения депозита вам будет открыт доступ к сигналам!"
                )
                
                await safe_edit_message(callback, text, keyboard)
                await callback.answer("✅ Подписка подтверждена!")
            else:
                # Если проверка не удалась, предлагаем альтернативный способ
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📢 Подписаться на канал", url=CHANNEL_LINK)],
                    [InlineKeyboardButton(text="✅ Я точно подписан", callback_data="force_subscribe")],
                    [InlineKeyboardButton(text="📞 Написать администратору", url="https://t.me/nomep999")],
                    [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_to_menu")]
                ])
                
                text = (
                    "⚠️ <b>Не удалось проверить подписку автоматически</b>\n\n"
                    "Возможные причины:\n"
                    "• Бот не добавлен в канал как администратор\n"
                    "• Канал приватный\n"
                    "• Технические проблемы\n\n"
                    "Попробуйте:\n"
                    "1️⃣ Убедитесь, что вы подписались на канал\n"
                    "2️⃣ Нажмите \"✅ Я точно подписан\" для ручной проверки\n"
                    "3️⃣ Или свяжитесь с администратором\n\n"
                    f"Канал: {CHANNEL_LINK}"
                )
                
                await safe_edit_message(callback, text, keyboard)
                await callback.answer("⚠️ Не удалось проверить подписку автоматически", show_alert=True)
        
        elif callback.data == "force_subscribe":
            # Ручное подтверждение подписки (для случаев, когда автоматическая проверка не работает)
            mark_subscribed(user_id)
            
            referral_link = get_referral_link(user_id)
            referral_used = check_referral_used(user_id)
            
            if not referral_used:
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🎰 Получить реферальную ссылку", callback_data="get_referral")],
                    [InlineKeyboardButton(text="📞 Связаться с менеджером", url="https://t.me/nomep999")],
                    [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_to_menu")]
                ])
            else:
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🎰 Моя реферальная ссылка", callback_data="show_referral")],
                    [InlineKeyboardButton(text="✅ Я сделал депозит", callback_data="confirm_deposit")],
                    [InlineKeyboardButton(text="📞 Связаться с менеджером", url="https://t.me/nomep999")],
                    [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_to_menu")]
                ])
            
            text = (
                "✅ <b>Подписка подтверждена вручную!</b>\n\n"
                "💰 <b>Для получения доступа к сигнальному боту необходимо внести депозит</b>\n\n"
                "📋 <b>Инструкция:</b>\n\n"
                "1️⃣ Получите реферальную ссылку\n"
                "2️⃣ Зарегистрируйтесь в казино по этой ссылке\n"
                "3️⃣ Сделайте депозит в казино\n"
                "4️⃣ Отправьте подтверждение менеджеру\n\n"
                "💰 После подтверждения депозита вам будет открыт доступ к сигналам!"
            )
            
            await safe_edit_message(callback, text, keyboard)
            await callback.answer("✅ Подписка подтверждена!")
        
        elif callback.data == "get_referral":
            # Выдаем реферальную ссылку
            referral_link = get_referral_link(user_id)
            mark_referral_used(user_id)
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🎰 Перейти в казино", url=referral_link)],
                [InlineKeyboardButton(text="✅ Я сделал депозит", callback_data="confirm_deposit")],
                [InlineKeyboardButton(text="📞 Связаться с менеджером", url="https://t.me/nomep999")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
            ])
            
            text = (
                "🎰 <b>Ваша реферальная ссылка</b>\n\n"
                f"🔗 <code>{referral_link}</code>\n\n"
                "📋 <b>Инструкция:</b>\n\n"
                "1️⃣ Нажмите кнопку \"🎰 Перейти в казино\" или скопируйте ссылку выше\n"
                "2️⃣ Зарегистрируйтесь в казино по этой ссылке\n"
                "3️⃣ Сделайте депозит в казино\n"
                "4️⃣ Нажмите \"✅ Я сделал депозит\" и отправьте подтверждение\n\n"
                "⚠️ <b>Важно:</b> Используйте именно эту ссылку для регистрации!\n"
                "Только депозиты, сделанные через эту ссылку, будут засчитаны."
            )
            
            await safe_edit_message(callback, text, keyboard)
            await callback.answer("✅ Реферальная ссылка выдана!")
        
        elif callback.data == "show_referral":
            # Показываем реферальную ссылку повторно
            referral_link = get_referral_link(user_id)
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🎰 Перейти в казино", url=referral_link)],
                [InlineKeyboardButton(text="✅ Я сделал депозит", callback_data="confirm_deposit")],
                [InlineKeyboardButton(text="📞 Связаться с менеджером", url="https://t.me/nomep999")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
            ])
            
            text = (
                "🎰 <b>Ваша реферальная ссылка</b>\n\n"
                f"🔗 <code>{referral_link}</code>\n\n"
                "📋 <b>Инструкция:</b>\n\n"
                "1️⃣ Нажмите кнопку \"🎰 Перейти в казино\" или скопируйте ссылку выше\n"
                "2️⃣ Зарегистрируйтесь в казино по этой ссылке\n"
                "3️⃣ Сделайте депозит в казино\n"
                "4️⃣ Нажмите \"✅ Я сделал депозит\" и отправьте подтверждение\n\n"
                "⚠️ <b>Важно:</b> Используйте именно эту ссылку для регистрации!"
            )
            
            await safe_edit_message(callback, text, keyboard)
            await callback.answer()
        
        elif callback.data == "make_deposit":
            referral_link = get_referral_link(user_id)
            referral_used = check_referral_used(user_id)
            
            if not referral_used:
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🎰 Получить реферальную ссылку", callback_data="get_referral")],
                    [InlineKeyboardButton(text="📞 Связаться с менеджером", url="https://t.me/nomep999")],
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
                ])
                
                text = (
                    "💰 <b>Информация о депозите</b>\n\n"
                    "Для получения доступа ко всем возможностям бота необходимо:\n\n"
                    "1️⃣ Получить реферальную ссылку\n"
                    "2️⃣ Зарегистрироваться в казино по этой ссылке\n"
                    "3️⃣ Сделать депозит в казино\n"
                    "4️⃣ Отправить подтверждение менеджеру\n\n"
                    "📞 Если у вас есть вопросы, свяжитесь с менеджером @nomep999"
                )
            else:
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🎰 Моя реферальная ссылка", callback_data="show_referral")],
                    [InlineKeyboardButton(text="✅ Я сделал депозит", callback_data="confirm_deposit")],
                    [InlineKeyboardButton(text="📞 Связаться с менеджером", url="https://t.me/nomep999")],
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
                ])
                
                text = (
                    "💰 <b>Информация о депозите</b>\n\n"
                    "Вы уже получили реферальную ссылку.\n\n"
                    "📋 <b>Следующие шаги:</b>\n"
                    "1️⃣ Перейдите по вашей реферальной ссылке\n"
                    "2️⃣ Зарегистрируйтесь в казино\n"
                    "3️⃣ Сделайте депозит\n"
                    "4️⃣ Нажмите \"✅ Я сделал депозит\" и отправьте подтверждение\n\n"
                    "📞 Если у вас есть вопросы, свяжитесь с менеджером @nomep999"
                )
            
            await safe_edit_message(callback, text, keyboard)
            await callback.answer()
        
        elif callback.data == "confirm_deposit":
            referral_used = check_referral_used(user_id)
            
            if not referral_used:
                await callback.answer("❌ Сначала получите реферальную ссылку!", show_alert=True)
                return
            
            text_deposit = (
                "📤 <b>Подтверждение депозита</b>\n\n"
                "Отправьте следующую информацию:\n\n"
                "1️⃣ Скриншот или фото подтверждения депозита в казино\n"
                "2️⃣ Ваш логин/ID в казино (если есть)\n"
                "3️⃣ Сумму депозита (опционально)\n\n"
                "Менеджер проверит ваш депозит и активирует доступ.\n"
                "Обычно это занимает несколько минут."
            )
            deposit_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📞 Написать менеджеру", url="https://t.me/nomep999")],
                [InlineKeyboardButton(text="🔙 Отмена", callback_data="back_to_menu")]
            ])
            await safe_edit_message(callback, text_deposit, deposit_keyboard)
            await state.set_state(DepositStates.waiting_for_proof)
            await callback.answer()
        
        elif callback.data == "my_deposit":
            user = get_user(user_id)
            if user and user[4]:  # has_deposit
                deposit_amount = user[5] or 0
                deposit_date = user[7] or "Не указана"
                text = (
                    f"💰 <b>Информация о депозите</b>\n\n"
                    f"✅ Статус: <b>Подтвержден</b>\n"
                    f"💵 Сумма: <b>{deposit_amount}</b>\n"
                    f"📅 Дата: {deposit_date}\n\n"
                    f"Вы имеете доступ ко всем функциям бота!"
                )
            else:
                text = (
                    "💰 <b>Информация о депозите</b>\n\n"
                    "❌ Депозит не подтвержден.\n\n"
                    "Для получения доступа к сигналам необходимо сделать депозит."
                )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_to_menu")]
            ])
            
            await safe_edit_message(callback, text, keyboard)
            await callback.answer()
        
        elif callback.data == "admin_panel":
            # Панель администратора
            if not is_admin(user_id):
                await callback.answer("❌ У вас нет прав для этого действия!", show_alert=True)
                return
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="👥 Список пользователей", callback_data="admin_users")],
                [InlineKeyboardButton(text="✅ Выдать доступ", callback_data="admin_give_access")],
                [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
                [InlineKeyboardButton(text="🔗 Обновить реферальную ссылку", callback_data="admin_set_referral")],
                [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_to_menu")]
            ])
            
            text = (
                "⚙️ <b>Панель администратора</b>\n\n"
                "Выберите действие:\n\n"
                "👥 <b>Список пользователей</b> - просмотр всех пользователей\n"
                "✅ <b>Выдать доступ</b> - подтвердить депозит пользователя\n"
                "📊 <b>Статистика</b> - общая статистика бота\n"
                "🔗 <b>Обновить реферальную ссылку</b> - изменить ссылку казино"
            )
            
            await safe_edit_message(callback, text, keyboard)
            await callback.answer()
        
        elif callback.data == "admin_give_access":
            if not is_admin(user_id):
                await callback.answer("❌ У вас нет прав!", show_alert=True)
                return
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")]
            ])
            
            text = (
                "✅ <b>Выдача доступа пользователю</b>\n\n"
                "Для подтверждения депозита используйте команду:\n\n"
                "<code>/approve_deposit &lt;user_id&gt; [сумма]</code>\n\n"
                "Или ответьте на сообщение пользователя командой:\n"
                "<code>/approve [сумма]</code>\n\n"
                "Пример:\n"
                "<code>/approve_deposit 123456789 1000</code>"
            )
            
            await safe_edit_message(callback, text, keyboard)
            await callback.answer()
        
        elif callback.data == "admin_users":
            if not is_admin(user_id):
                await callback.answer("❌ У вас нет прав!", show_alert=True)
                return
            
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute('SELECT user_id, username, first_name, has_deposit FROM users ORDER BY registered_at DESC LIMIT 20')
            users = cursor.fetchall()
            conn.close()
            
            if not users:
                text = "Пользователей пока нет."
            else:
                text = "👥 <b>Последние пользователи:</b>\n\n"
                for u in users:
                    status = "✅" if u[3] else "❌"
                    username = f"@{u[1]}" if u[1] else "без username"
                    text += f"{status} <code>{u[0]}</code> - {username} ({u[2] or 'без имени'})\n"
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")]
            ])
            
            await safe_edit_message(callback, text, keyboard)
            await callback.answer()
        
        elif callback.data == "admin_stats":
            if not is_admin(user_id):
                await callback.answer("❌ У вас нет прав!", show_alert=True)
                return
            
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM users')
            total_users = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM users WHERE has_deposit = 1')
            users_with_deposit = cursor.fetchone()[0]
            
            cursor.execute('SELECT SUM(deposit_amount) FROM users WHERE has_deposit = 1')
            total_deposits = cursor.fetchone()[0] or 0
            
            cursor.execute('SELECT COUNT(*) FROM users WHERE DATE(registered_at) = DATE("now")')
            new_today = cursor.fetchone()[0]
            
            conn.close()
            
            text = (
                "📊 <b>Статистика бота</b>\n\n"
                f"👥 Всего пользователей: <b>{total_users}</b>\n"
                f"✅ С депозитом: <b>{users_with_deposit}</b>\n"
                f"❌ Без депозита: <b>{total_users - users_with_deposit}</b>\n"
                f"💰 Общая сумма депозитов: <b>{total_deposits}</b>\n"
                f"🆕 Новых сегодня: <b>{new_today}</b>"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")]
            ])
            
            await safe_edit_message(callback, text, keyboard)
            await callback.answer()
        
        elif callback.data == "admin_set_referral":
            if not is_admin(user_id):
                await callback.answer("❌ У вас нет прав!", show_alert=True)
                return
            
            current_link = get_referral_link(0)
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")]
            ])
            
            text = (
                "🔗 <b>Обновление реферальной ссылки</b>\n\n"
                f"Текущая ссылка:\n<code>{current_link}</code>\n\n"
                "Для обновления используйте команду:\n"
                "<code>/set_referral ваша_ссылка</code>\n\n"
                "Пример:\n"
                "<code>/set_referral https://t.me/LB_Chainreak_bot/app?startapp=НОВАЯ_ССЫЛКА</code>"
            )
            
            await safe_edit_message(callback, text, keyboard)
            await callback.answer()
        
        elif callback.data == "back_to_menu":
            # Возвращаемся к главному меню
            keyboard_buttons = [
                [InlineKeyboardButton(text="📊 Получить сигнал", callback_data="get_signal")],
                [InlineKeyboardButton(text="📞 Поддержка", url="https://t.me/nomep999")],
                [InlineKeyboardButton(text="💬 Наш ТГК", url=CHANNEL_LINK)]
            ]
            
            if is_admin(user_id):
                keyboard_buttons.append([InlineKeyboardButton(text="⚙️ Панель администратора", callback_data="admin_panel")])
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
            
            text = (
                "🏠 <b>Добро пожаловать в главное меню!</b>\n\n"
                "Вы находитесь в сигнальном боте <b>TOWER BOT AI</b> 🎯\n\n"
                "📊 <b>Функционал бота:</b>\n"
                "• Получение точных сигналов для игры Tower Rush\n"
                "• Анализ с помощью искусственного интеллекта\n"
                "• Прогнозирование результатов с высокой вероятностью\n"
                "• Удобный интерфейс и быстрый доступ к сигналам\n\n"
                "Выберите действие из меню ниже 👇"
            )
            
            # Отправляем текстовое сообщение
            await safe_edit_message(callback, text, keyboard)
            await callback.answer()
    except (ConnectionError, TimeoutError, asyncio.TimeoutError) as e:
        error_type = type(e).__name__
        logger.error(f"❌ Сетевая ошибка при обработке callback {callback.data if callback.data else 'unknown'}: {error_type}: {e}")
        # Пытаемся переподключиться
        try:
            await bot.session.close()
        except:
            pass
        try:
            from aiogram.client.session.aiohttp import AiohttpSession
            bot._session = AiohttpSession()
            await bot.session.create()
        except Exception as reconnect_error:
            logger.error(f"❌ Не удалось переподключиться: {reconnect_error}")
        
        try:
            await callback.answer("⚠️ Временные проблемы с соединением. Попробуйте еще раз или используйте /start", show_alert=True)
        except Exception as e2:
            logger.error(f"Не удалось отправить ответ на callback: {e2}")
    except Exception as e:
        error_type = type(e).__name__
        logger.error(f"❌ Ошибка при обработке callback {callback.data if callback.data else 'unknown'}: {error_type}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        try:
            await callback.answer("❌ Произошла ошибка. Попробуйте еще раз или используйте /start", show_alert=True)
        except Exception as e2:
            logger.error(f"Не удалось отправить ответ на callback: {e2}")

# Обработка фото для подтверждения депозита
@dp.message(DepositStates.waiting_for_proof)
async def process_deposit_proof(message: types.Message, state: FSMContext):
    try:
        user_id = message.from_user.id
        try:
            user = get_user(user_id)
            referral_link = get_referral_link(user_id)
        except Exception as e:
            logger.error(f"Ошибка получения данных пользователя {user_id}: {e}")
            await message.answer("❌ Произошла ошибка. Попробуйте еще раз или используйте /start")
            await state.clear()
            return
        
        # Сохраняем текст сообщения как подтверждение
        proof_text = message.text or "Фото подтверждения"
        
        if message.photo:
            # Отправляем уведомление администраторам
            notification_text = (
                f"🔔 <b>Новый запрос на подтверждение депозита</b>\n\n"
                f"👤 Пользователь: @{message.from_user.username or 'без username'}\n"
                f"🆔 ID: <code>{user_id}</code>\n"
                f"📛 Имя: {message.from_user.first_name}\n"
                f"🔗 Реферальная ссылка: <code>{referral_link}</code>\n\n"
                f"Для подтверждения нажмите кнопку ниже или используйте:\n"
                f"<code>/approve_deposit {user_id} [сумма]</code>\n"
                f"Или ответьте на сообщение пользователя командой /approve [сумма]"
            )
            
            # Клавиатура для быстрого подтверждения
            approve_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Подтвердить депозит", callback_data=f"admin_approve_{user_id}")],
                [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"admin_reject_{user_id}")]
            ])
            
            # Отправляем уведомление всем администраторам
            for admin_id in ADMIN_IDS:
                try:
                    # Пересылаем фото администратору
                    await bot.forward_message(admin_id, message.chat.id, message.message_id)
                    await bot.send_message(admin_id, notification_text, reply_markup=approve_keyboard, parse_mode="HTML")
                except Exception as e:
                    logger.error(f"Ошибка отправки уведомления администратору {admin_id}: {e}")
            
            text = (
                "✅ <b>Ваше подтверждение депозита получено!</b>\n\n"
                "📞 Менеджер проверит ваш депозит и активирует доступ.\n\n"
                "⏳ Обычно это занимает несколько минут.\n"
                "Вы получите уведомление, когда доступ будет активирован.\n\n"
                "Используйте /start для возврата в меню."
            )
            
            await message.answer(text, parse_mode="HTML")
            await state.clear()
        elif message.text:
            # Если отправлен текст (логин, сумма и т.д.)
            proof_text = message.text
            
            notification_text = (
                f"🔔 <b>Новый запрос на подтверждение депозита</b>\n\n"
                f"👤 Пользователь: @{message.from_user.username or 'без username'}\n"
                f"🆔 ID: <code>{user_id}</code>\n"
                f"📛 Имя: {message.from_user.first_name}\n"
                f"🔗 Реферальная ссылка: <code>{referral_link}</code>\n"
                f"📝 Информация: {proof_text}\n\n"
                f"Для подтверждения нажмите кнопку ниже или используйте:\n"
                f"<code>/approve_deposit {user_id} [сумма]</code>\n"
                f"Или ответьте на сообщение пользователя командой /approve [сумма]"
            )
            
            # Клавиатура для быстрого подтверждения
            approve_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Подтвердить депозит", callback_data=f"admin_approve_{user_id}")],
                [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"admin_reject_{user_id}")]
            ])
            
            # Отправляем уведомление всем администраторам
            for admin_id in ADMIN_IDS:
                try:
                    await bot.send_message(admin_id, notification_text, reply_markup=approve_keyboard, parse_mode="HTML")
                except Exception as e:
                    logger.error(f"Ошибка отправки уведомления администратору {admin_id}: {e}")
            
            text = (
                "✅ <b>Ваша информация получена!</b>\n\n"
                "📞 Менеджер проверит ваш депозит и активирует доступ.\n\n"
                "⏳ Обычно это занимает несколько минут.\n"
                "Вы получите уведомление, когда доступ будет активирован.\n\n"
                "💡 Вы также можете отправить скриншот подтверждения депозита.\n\n"
                "Используйте /start для возврата в меню."
            )
            
            await message.answer(text, parse_mode="HTML")
        else:
            await message.answer(
                "📤 Отправьте скриншот или фото подтверждения депозита, либо текстовую информацию.\n\n"
                "Или нажмите /start для возврата в меню."
            )
    except Exception as e:
        logger.error(f"Ошибка при обработке подтверждения депозита: {e}")
        import traceback
        logger.error(traceback.format_exc())
        try:
            await message.answer("❌ Произошла ошибка при обработке подтверждения. Попробуйте еще раз или используйте /start")
            await state.clear()
        except:
            pass

# Команда для администратора - подтверждение депозита
@dp.message(Command("approve_deposit"))
async def cmd_approve_deposit(message: types.Message):
    # Проверка прав администратора
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для выполнения этой команды.")
        return
    
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    
    if not args:
        await message.answer(
            "Использование: /approve_deposit <user_id> [amount]\n\n"
            "Пример: /approve_deposit 123456789 1000\n\n"
            "Или ответьте на сообщение пользователя командой /approve_deposit [amount]"
        )
        return
    
    try:
        user_id = int(args[0])
        amount = float(args[1]) if len(args) > 1 else 0
        
        verify_deposit(user_id, amount)
        
        # Уведомляем пользователя
        try:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🌐 Открыть Web-App", web_app=WebAppInfo(url=WEB_APP_LINK))],
                [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_to_menu")]
            ])
            
            await bot.send_message(
                user_id,
                "✅ <b>Вам открыт доступ к сигнальному боту TOWER BOT AI!</b>\n\n"
                "🎉 Поздравляем! Ваш депозит подтвержден администратором.\n\n"
                "Теперь вы можете:\n"
                "• Получать точные сигналы для игры Tower Rush\n"
                "• Использовать все возможности бота\n"
                "• Получать прогнозы с высокой вероятностью успеха\n\n"
                f"🌐 <b>Ссылка на этого бота в Web-App:</b>\n"
                f"{WEB_APP_LINK}\n\n"
                "Используйте кнопки ниже для начала работы!",
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления пользователю {user_id}: {e}")
        
        user_info = get_user(user_id)
        username = user_info[1] if user_info else "неизвестно"
        
        await message.answer(
            f"✅ Депозит пользователя подтвержден!\n\n"
            f"👤 Пользователь: @{username or 'без username'}\n"
            f"🆔 ID: {user_id}\n"
            f"💵 Сумма: {amount}\n\n"
            f"Пользователь получил уведомление и доступ к сигналам.",
            parse_mode="HTML"
        )
        
    except ValueError:
        await message.answer("❌ Неверный формат команды. Используйте: /approve_deposit <user_id> [amount]")

# Обработчик ответа на сообщение для быстрого подтверждения
@dp.message(Command("approve"))
async def cmd_approve_reply(message: types.Message):
    """Быстрое подтверждение депозита через ответ на сообщение пользователя"""
    if not is_admin(message.from_user.id):
        return
    
    if not message.reply_to_message:
        await message.answer(
            "❌ Ответьте на сообщение пользователя командой /approve [amount]\n\n"
            "Пример: Ответьте на сообщение и напишите /approve 1000"
        )
        return
    
    user_id = message.reply_to_message.from_user.id
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    amount = float(args[0]) if args else 0
    
    verify_deposit(user_id, amount)
    
    try:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🌐 Открыть Web-App", url=WEB_APP_LINK)],
            [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_to_menu")]
        ])
        
        await bot.send_message(
            user_id,
            "✅ <b>Вам открыт доступ к сигнальному боту TOWER BOT AI!</b>\n\n"
            "🎉 Поздравляем! Ваш депозит подтвержден администратором.\n\n"
            "Теперь вы можете:\n"
            "• Получать точные сигналы для игры Tower Rush\n"
            "• Использовать все возможности бота\n"
            "• Получать прогнозы с высокой вероятностью успеха\n\n"
            f"🌐 <b>Ссылка на этого бота в Web-App:</b>\n"
            f"{WEB_APP_LINK}\n\n"
            "Используйте кнопки ниже для начала работы!",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Ошибка отправки уведомления пользователю {user_id}: {e}")
    
    await message.answer(f"✅ Депозит пользователя {user_id} подтвержден!")

# Команда для администратора - обновление реферальной ссылки
@dp.message(Command("set_referral"))
async def cmd_set_referral(message: types.Message):
    # Проверка прав администратора
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для выполнения этой команды.")
        return
    
    args = message.text.split(maxsplit=1)
    
    if len(args) < 2:
        current_link = get_referral_link(0)  # Получаем текущую ссылку
        await message.answer(
            f"📝 <b>Текущая реферальная ссылка:</b>\n\n"
            f"<code>{current_link}</code>\n\n"
            f"Для обновления используйте:\n"
            f"<code>/set_referral ваша_ссылка_здесь</code>\n\n"
            f"Пример:\n"
            f"<code>/set_referral https://t.me/LB_Chainreak_bot/app?startapp=НОВАЯ_ССЫЛКА</code>",
            parse_mode="HTML"
        )
        return
    
    new_link = args[1].strip()
    
    if set_referral_link(new_link):
        await message.answer(
            f"✅ <b>Реферальная ссылка обновлена!</b>\n\n"
            f"Новая ссылка:\n"
            f"<code>{new_link}</code>\n\n"
            f"Теперь все новые пользователи будут получать эту ссылку.",
            parse_mode="HTML"
        )
        logger.info(f"Администратор {message.from_user.id} обновил реферальную ссылку")
    else:
        await message.answer("❌ Ошибка при обновлении ссылки. Проверьте логи.")

# Команда для администратора - статистика
@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    # Проверка прав администратора
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для выполнения этой команды.")
        return
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Общее количество пользователей
    cursor.execute('SELECT COUNT(*) FROM users')
    total_users = cursor.fetchone()[0]
    
    # Пользователи с депозитом
    cursor.execute('SELECT COUNT(*) FROM users WHERE has_deposit = 1')
    users_with_deposit = cursor.fetchone()[0]
    
    # Общая сумма депозитов
    cursor.execute('SELECT SUM(deposit_amount) FROM users WHERE has_deposit = 1')
    total_deposits = cursor.fetchone()[0] or 0
    
    # Новые пользователи за сегодня
    cursor.execute('SELECT COUNT(*) FROM users WHERE DATE(registered_at) = DATE("now")')
    new_today = cursor.fetchone()[0]
    
    conn.close()
    
    stats_text = (
        "📊 <b>Статистика бота</b>\n\n"
        f"👥 Всего пользователей: <b>{total_users}</b>\n"
        f"✅ С депозитом: <b>{users_with_deposit}</b>\n"
        f"❌ Без депозита: <b>{total_users - users_with_deposit}</b>\n"
        f"💰 Общая сумма депозитов: <b>{total_deposits}</b>\n"
        f"🆕 Новых сегодня: <b>{new_today}</b>"
    )
    
    await message.answer(stats_text, parse_mode="HTML")

# Приветственное сообщение для новых пользователей (до /start)
# Этот обработчик должен быть ПОСЛЕ всех командных обработчиков
# Обрабатывает все сообщения от пользователей, которые еще не использовали /start
# ВАЖНО: Используем фильтр, который исключает команды, чтобы не перехватывать /start
@dp.message(F.text)
async def welcome_message(message: types.Message):
    """Автоматическое приветствие при первом контакте с ботом"""
    try:
        # ВАЖНО: Проверяем, что это НЕ команда - команды обрабатываются отдельными обработчиками
        # Это дополнительная защита на случай, если фильтр не сработает
        if message.text and (message.text.startswith('/') or message.text.startswith('!')):
            # Логируем для диагностики, если команда попала в этот обработчик
            logger.debug(f"Команда {message.text} попала в welcome_message - пропускаем")
            return  # Пропускаем команды - они обрабатываются отдельными обработчиками
        
        user_id = message.from_user.id
        
        # Если пользователь уже использовал /start, просто игнорируем сообщение
        # Команда /start обрабатывается отдельным обработчиком выше
        try:
            if check_start_used(user_id):
                return
        except Exception as e:
            logger.error(f"Ошибка проверки start_used для {user_id}: {e}")
            # Продолжаем выполнение
        
        # Регистрируем пользователя
        try:
            register_user(user_id, message.from_user.username, message.from_user.first_name)
        except Exception as e:
            logger.error(f"Ошибка регистрации пользователя {user_id}: {e}")
            # Продолжаем выполнение
        
        # Приветственное сообщение - отправляется автоматически при первом контакте
        welcome_text = (
            "🎉 <b>Приветствую!</b>\n\n"
            "Ты попал в сигнального бота <b>TOWER BOT AI</b> 🏠\n\n"
            "Этот бот поможет тебе получать точные сигналы для игры Tower Rush.\n"
            "Мы используем искусственный интеллект для анализа и прогнозирования результатов с высокой точностью.\n\n"
            "🎯 <b>Что тебя ждет:</b>\n"
            "• Точные сигналы с вероятностью успеха 85-98%\n"
            "• Анализ на основе AI провайдера Galaxsys\n"
            "• Удобный интерфейс и быстрый доступ к сигналам\n"
            "• Поддержка 24/7 от нашей команды\n"
            "• Регулярные обновления и улучшения функционала\n\n"
            "💡 <b>Как это работает:</b>\n"
            "Наш AI анализирует тысячи игровых ситуаций и выдает наиболее вероятные результаты. "
            "Каждый сигнал проходит проверку и имеет высокую вероятность успеха.\n\n"
            "🚀 Для начала работы используй команду <b>/start</b> или нажми кнопку ниже 👇"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Начать работу", callback_data="start_bot")]
        ])
        
        # Отправляем сообщение с фото, если оно указано
        if WELCOME_PHOTO:
            try:
                # Пробуем отправить фото (может быть локальный файл или URL)
                if WELCOME_PHOTO.startswith('http'):
                    # Это URL
                    await message.answer_photo(
                        photo=WELCOME_PHOTO,
                        caption=welcome_text,
                        reply_markup=keyboard,
                        parse_mode="HTML"
                    )
                else:
                    # Это локальный файл
                    try:
                        # Используем FSInputFile для отправки локального файла
                        photo_file = FSInputFile(WELCOME_PHOTO)
                        await message.answer_photo(
                            photo=photo_file,
                            caption=welcome_text,
                            reply_markup=keyboard,
                            parse_mode="HTML"
                        )
                    except FileNotFoundError:
                        # Если файл не найден, отправляем без фото
                        await message.answer(welcome_text, reply_markup=keyboard, parse_mode="HTML")
            except Exception as e:
                logger.error(f"Ошибка отправки фото приветствия: {e}")
                # В случае ошибки отправляем без фото
                await message.answer(welcome_text, reply_markup=keyboard, parse_mode="HTML")
        else:
            # Если фото не указано, отправляем обычное текстовое сообщение
            await message.answer(welcome_text, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Ошибка при отправке приветственного сообщения: {e}")
        import traceback
        logger.error(traceback.format_exc())
        try:
            await message.answer("🎉 Привет! Используйте команду /start для начала работы.")
        except:
            pass

# Health check endpoint для Render (чтобы инстанс не "засыпал")
async def health_check(request):
    """Health check endpoint для мониторинга Render"""
    return web.json_response({'status': 'ok', 'service': 'tower-bot-telegram'})

# HTTP API для веб-приложения
async def check_user_status(request):
    """API endpoint для проверки статуса пользователя (депозит и подписка)"""
    try:
        # Получаем user_id из запроса
        data = await request.json()
        user_id = data.get('user_id')
        
        if not user_id:
            return web.json_response({'error': 'user_id is required'}, status=400)
        
        try:
            user_id = int(user_id)
        except ValueError:
            return web.json_response({'error': 'Invalid user_id'}, status=400)
        
        # Проверяем статус пользователя
        user = get_user(user_id)
        if not user:
            return web.json_response({
                'has_access': False,
                'has_deposit': False,
                'is_subscribed': False,
                'message': 'Пользователь не найден'
            })
        
        has_deposit = bool(user[4])  # has_deposit
        is_subscribed = check_subscription(user_id)
        
        # Проверяем подписку через API (асинхронно)
        try:
            is_subscribed_api = await check_user_subscription(user_id)
            is_subscribed = is_subscribed_api or is_subscribed
        except Exception as e:
            logger.error(f"Ошибка проверки подписки через API: {e}")
        
        has_access = has_deposit and is_subscribed
        
        return web.json_response({
            'has_access': has_access,
            'has_deposit': has_deposit,
            'is_subscribed': is_subscribed,
            'message': 'Доступ разрешен' if has_access else 'Необходимо внести депозит и подписаться на канал'
        })
    except Exception as e:
        logger.error(f"Ошибка в API check_user_status: {e}")
        return web.json_response({'error': 'Internal server error'}, status=500)

# Главная функция с обработкой ошибок и переподключением
async def main():
    # Инициализация базы данных
    init_db()
    
    # Создаем HTTP сервер для API
    app = web.Application()
    app.router.add_get('/', health_check)  # Health check для Render
    app.router.add_get('/health', health_check)  # Альтернативный health check
    app.router.add_post('/api/check_user', check_user_status)
    
    # Настраиваем CORS для работы с веб-приложением
    async def cors_middleware(app, handler):
        async def middleware_handler(request):
            if request.method == 'OPTIONS':
                response = web.Response()
            else:
                response = await handler(request)
            
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
            return response
        return middleware_handler
    
    app.middlewares.append(cors_middleware)
    
    # Запускаем HTTP сервер в фоне
    # Используем переменную окружения PORT для облачных платформ (Render, Heroku и т.д.)
    # Если PORT не указан, используем 8080 для локальной разработки
    port = int(os.getenv('PORT', 8080))
    host = '0.0.0.0'  # Слушаем на всех интерфейсах для облачных платформ
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    
    # Определяем URL для логирования
    if port == 8080:
        api_url = f"http://localhost:{port}"
    else:
        # Для облачных платформ URL будет известен после деплоя
        api_url = f"http://0.0.0.0:{port}"
    
    logger.info(f"HTTP API сервер запущен на {api_url}")
    
    # Запуск бота с обработкой ошибок и автоматическим переподключением
    retry_count = 0
    max_retries = 10  # Увеличиваем количество попыток
    retry_delay = 5  # секунд
    consecutive_errors = 0
    
    while True:
        try:
            logger.info("Запуск бота...")
            # Закрываем предыдущую сессию, если она была
            try:
                await bot.session.close()
            except Exception as e:
                logger.debug(f"Ошибка закрытия сессии (можно игнорировать): {e}")
            
            # Создаем новую сессию бота
            try:
                await bot.delete_webhook(drop_pending_updates=True)
            except Exception as e:
                logger.warning(f"Не удалось удалить webhook (можно игнорировать): {e}")
            
            # Проверяем, что бот работает
            try:
                bot_info = await bot.get_me()
                logger.info(f"✅ Бот подключен: @{bot_info.username} (ID: {bot_info.id})")
            except Exception as e:
                logger.error(f"❌ Ошибка подключения к Telegram API: {e}")
                raise
            
            logger.info("Бот запущен и готов к работе")
            retry_count = 0  # Сбрасываем счетчик при успешном запуске
            consecutive_errors = 0  # Сбрасываем счетчик последовательных ошибок
            
            # Переменные для отслеживания состояния polling (инициализируем здесь, чтобы были доступны в health_check)
            polling_active = {'status': True}
            # Отслеживание времени последнего обновления
            last_update_time = {'time': asyncio.get_event_loop().time()}
            # Время запуска polling для профилактического перезапуска
            polling_start_time = {'time': asyncio.get_event_loop().time()}
            # Ссылка на polling task для возможности его отмены
            polling_task_ref = {'task': None}
            
            # Middleware для отслеживания обновлений
            @dp.update.outer_middleware()
            async def update_tracker_middleware(handler, event, data):
                # Обновляем время последнего обновления при получении любого обновления
                current_time = asyncio.get_event_loop().time()
                time_since_last = current_time - last_update_time['time']
                last_update_time['time'] = current_time
                # Логируем получение обновления (только если прошло больше минуты с последнего)
                if time_since_last > 60:
                    logger.info(f"📨 Получено обновление (тип: {event.__class__.__name__}), предыдущее было {time_since_last:.0f} сек назад")
                return await handler(event, data)
            
            # Запускаем задачу для периодической проверки соединения и обновлений
            async def health_check():
                """Периодическая проверка работоспособности бота и получения обновлений"""
                consecutive_failures = 0
                max_failures = 3
                no_updates_timeout = 300  # 5 минут без обновлений = проблема (уменьшено с 10 минут)
                connection_check_interval = 300  # Проверка соединения каждые 5 минут (даже если есть обновления)
                preventive_restart_interval = 21600  # Профилактический перезапуск каждые 6 часов (для предотвращения проблем после длительного простоя)
                last_connection_check = asyncio.get_event_loop().time()
                
                while polling_active['status']:
                    try:
                        await asyncio.sleep(180)  # Проверка каждые 3 минуты
                        current_time = asyncio.get_event_loop().time()
                        
                        # Проверяем время работы polling для профилактического перезапуска
                        polling_uptime = current_time - polling_start_time['time']
                        if polling_uptime >= preventive_restart_interval:
                            logger.info(f"⏰ Polling работает уже {polling_uptime/3600:.1f} часов. Профилактический перезапуск для предотвращения проблем после длительного простоя...")
                            polling_active['status'] = False
                            if polling_task_ref['task'] and not polling_task_ref['task'].done():
                                logger.info("Отменяю polling task для профилактического перезапуска...")
                                polling_task_ref['task'].cancel()
                            raise ConnectionError(f"Preventive restart after {polling_uptime:.0f} seconds")
                        
                        # Проверяем, получает ли бот обновления
                        time_since_last_update = current_time - last_update_time['time']
                        
                        if time_since_last_update > no_updates_timeout:
                            logger.warning(f"⚠️ Нет обновлений {time_since_last_update:.0f} секунд ({time_since_last_update/60:.1f} минут). Возможно polling завис.")
                            # Пробуем проверить соединение
                            try:
                                bot_info = await asyncio.wait_for(bot.get_me(), timeout=5)
                                logger.info(f"✅ Соединение работает, но обновления не приходят. Перезапуск polling...")
                            except asyncio.TimeoutError:
                                logger.error("❌ Таймаут при проверке соединения. Перезапуск...")
                            except Exception as e:
                                logger.error(f"❌ Ошибка при проверке соединения: {e}")
                            
                            # Перезапускаем polling - устанавливаем флаг и отменяем polling task
                            polling_active['status'] = False
                            # Отменяем polling task если он существует
                            if polling_task_ref['task'] and not polling_task_ref['task'].done():
                                logger.info("Отменяю зависший polling task из health check...")
                                polling_task_ref['task'].cancel()
                            raise ConnectionError(f"No updates received for {time_since_last_update:.0f} seconds")
                        
                        # Проверяем соединение с ботом (каждые 5 минут или если нет обновлений)
                        time_since_connection_check = current_time - last_connection_check
                        should_check_connection = (time_since_connection_check >= connection_check_interval) or (time_since_last_update > 180)
                        
                        if should_check_connection:
                            logger.info(f"🔍 Проверка соединения с Telegram API...")
                            connection_ok = await ensure_bot_connection()
                            last_connection_check = current_time
                            
                            if connection_ok:
                                try:
                                    bot_info = await bot.get_me()
                                    logger.info(f"✅ Health check: бот работает, username: @{bot_info.username}, последнее обновление: {time_since_last_update:.0f} сек назад")
                                    consecutive_failures = 0  # Сбрасываем счетчик при успехе
                                except Exception as e:
                                    consecutive_failures += 1
                                    error_type = type(e).__name__
                                    logger.warning(f"⚠️ Health check failed после восстановления соединения (попытка {consecutive_failures}/{max_failures}): {error_type}: {e}")
                            else:
                                consecutive_failures += 1
                                logger.warning(f"⚠️ Health check failed - не удалось восстановить соединение (попытка {consecutive_failures}/{max_failures})")
                                
                                # Если несколько проверок подряд не удались, перезапускаем соединение
                                if consecutive_failures >= max_failures:
                                    logger.error("❌ Множественные ошибки health check. Перезапуск соединения...")
                                    polling_active['status'] = False
                                    # Прерываем polling для перезапуска
                                    raise ConnectionError("Health check failed multiple times")
                        else:
                            # Просто логируем статус без проверки соединения
                            logger.info(f"✅ Health check: последнее обновление: {time_since_last_update:.0f} сек назад")
                    except asyncio.CancelledError:
                        logger.info("Health check task cancelled")
                        break
                    except ConnectionError:
                        # Это ожидаемая ошибка для перезапуска polling
                        logger.warning("Health check обнаружил проблему - требуется перезапуск polling")
                        polling_active['status'] = False
                        raise
                    except Exception as e:
                        logger.error(f"❌ Критическая ошибка в health check: {e}")
                        consecutive_failures += 1
                        if consecutive_failures >= max_failures:
                            polling_active['status'] = False
                            raise ConnectionError(f"Health check critical error: {e}")
            
            # Запускаем health check в фоне
            health_check_task = asyncio.create_task(health_check())
            
            logger.info("🔄 Начинаю polling...")
            logger.info(f"📋 Зарегистрировано обработчиков: {len(dp.message.handlers)} сообщений, {len(dp.callback_query.handlers)} callback")
            
            # Сбрасываем время последнего обновления при запуске
            last_update_time['time'] = asyncio.get_event_loop().time()
            polling_start_time['time'] = asyncio.get_event_loop().time()
            logger.info("⏱️ Отслеживание обновлений активировано:")
            logger.info("   • Автоматический перезапуск при отсутствии обновлений более 5 минут")
            logger.info("   • Профилактический перезапуск каждые 6 часов для предотвращения проблем после длительного простоя")
            
            # Запуск polling с обработкой ошибок и таймаутами
            polling_task = None
            try:
                # Создаем задачу для polling с возможностью отмены
                polling_task = asyncio.create_task(
                    dp.start_polling(
                        bot,
                        allowed_updates=dp.resolve_used_update_types(),
                        close_bot_session=False,  # Не закрываем сессию автоматически
                        drop_pending_updates=True  # Удаляем ожидающие обновления при старте
                    )
                )
                # Сохраняем ссылку на task для health check
                polling_task_ref['task'] = polling_task
                
                # Ждем завершения polling или его отмены
                await polling_task
            except asyncio.CancelledError:
                logger.info("Polling был отменен")
                polling_active['status'] = False
                # Очищаем ссылку на polling task
                polling_task_ref['task'] = None
                # Отменяем polling task если он еще работает
                if polling_task and not polling_task.done():
                    polling_task.cancel()
                    try:
                        await polling_task
                    except asyncio.CancelledError:
                        pass
                raise
            except Exception as polling_error:
                error_type = type(polling_error).__name__
                logger.error(f"❌ Ошибка polling: {error_type}: {polling_error}")
                polling_active['status'] = False
                # Очищаем ссылку на polling task
                polling_task_ref['task'] = None
                # Отменяем polling task если он еще работает
                if polling_task and not polling_task.done():
                    logger.info("Отменяю зависший polling task...")
                    polling_task.cancel()
                    try:
                        await asyncio.wait_for(polling_task, timeout=5)
                    except (asyncio.CancelledError, asyncio.TimeoutError):
                        pass
                # Отменяем health check task
                try:
                    health_check_task.cancel()
                except:
                    pass
                raise
            
        except KeyboardInterrupt:
            logger.info("Получен сигнал остановки. Завершение работы...")
            polling_active['status'] = False
            # Отменяем health check task
            try:
                health_check_task.cancel()
                await health_check_task
            except:
                pass
            break
        except asyncio.CancelledError:
            logger.warning("Задача была отменена. Перезапуск...")
            polling_active['status'] = False
            # Отменяем health check task
            try:
                health_check_task.cancel()
            except:
                pass
            await asyncio.sleep(retry_delay)
            continue
        except (ConnectionError, TimeoutError, asyncio.TimeoutError) as e:
            retry_count += 1
            consecutive_errors += 1
            error_type = type(e).__name__
            error_msg = f"Сетевая ошибка при работе бота (попытка {retry_count}/{max_retries}): {error_type}: {e}"
            logger.error(error_msg)
            
            polling_active['status'] = False
            # Отменяем health check task
            try:
                health_check_task.cancel()
            except:
                pass
            
            # Переподключаемся используя функцию восстановления соединения
            connection_restored = await ensure_bot_connection()
            if not connection_restored:
                logger.error("Не удалось восстановить соединение после сетевой ошибки")
            
            retry_delay = min(retry_delay * 1.5, 30)  # Меньшая задержка для сетевых ошибок
            
            if retry_count >= max_retries:
                logger.error("Достигнуто максимальное количество попыток переподключения. Завершение работы.")
                break
            
            import traceback
            logger.error(traceback.format_exc())
            logger.info(f"Повторная попытка через {retry_delay:.1f} секунд...")
            await asyncio.sleep(retry_delay)
            continue
        except Exception as e:
            retry_count += 1
            consecutive_errors += 1
            error_type = type(e).__name__
            error_msg = f"Ошибка при работе бота (попытка {retry_count}/{max_retries}): {error_type}: {e}"
            logger.error(error_msg)
            
            polling_active['status'] = False
            # Отменяем health check task
            try:
                health_check_task.cancel()
            except:
                pass
            
            # Обработка конкретных типов ошибок
            if "Unauthorized" in error_type or "Forbidden" in error_type:
                logger.error("Ошибка авторизации! Проверьте токен бота.")
                break  # Критическая ошибка - останавливаем бота
            else:
                retry_delay = min(retry_delay * 2, 60)  # Экспоненциальная задержка
            
            # Если слишком много последовательных ошибок, увеличиваем задержку
            if consecutive_errors >= 3:
                retry_delay = min(retry_delay * 2, 120)
                logger.warning(f"Много последовательных ошибок. Увеличиваем задержку до {retry_delay} сек.")
            
            if retry_count >= max_retries:
                logger.error("Достигнуто максимальное количество попыток переподключения. Завершение работы.")
                break
            
            import traceback
            logger.error(traceback.format_exc())
            logger.info(f"Повторная попытка через {retry_delay:.1f} секунд...")
            await asyncio.sleep(retry_delay)
        finally:
            # Закрываем сессию при выходе из цикла
            if not polling_active['status']:
                try:
                    await bot.session.close()
                except:
                    pass

# Глобальный обработчик ошибок убран - используем встроенную обработку aiogram
# Ошибки обрабатываются в каждом обработчике индивидуально

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("ЗАПУСК БОТА TOWER BOT AI")
    logger.info("=" * 60)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        import traceback
        logger.error(traceback.format_exc())
        print("\n" + "=" * 60)
        print("ОШИБКА ПРИ ЗАПУСКЕ БОТА!")
        print("=" * 60)
        print(f"Ошибка: {e}")
        print("\nПроверьте:")
        print("1. Правильность токена бота")
        print("2. Наличие интернет-соединения")
        print("3. Установлены ли все зависимости (pip install -r requirements.txt)")
        print("=" * 60)
