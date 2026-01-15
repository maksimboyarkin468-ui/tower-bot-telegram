# Деплой бота на PythonAnywhere

## Шаг 1: Регистрация
1. Перейдите на https://www.pythonanywhere.com
2. Нажмите "Pricing" → выберите "Beginner" (бесплатный)
3. Зарегистрируйтесь через email или GitHub

## Шаг 2: Настройка
1. После входа откройте "Tasks" (вкладка вверху)
2. Нажмите "Create a new task"
3. Заполните:
   - Command: `cd /home/ваш_username/tower-bot-telegram && python3 bot.py`
   - Hour: выберите "Always-on"
   - Enabled: ✅ (галочка)

## Шаг 3: Загрузка кода
1. Откройте "Files" → "Upload a file"
2. Или используйте "Bash console" для клонирования из GitHub:
   ```bash
   git clone https://github.com/maksimboyarkin468-ui/tower-bot-telegram.git
   ```

## Шаг 4: Установка зависимостей
В Bash console:
```bash
cd tower-bot-telegram
pip3.10 install --user -r requirements.txt
```

## Шаг 5: Настройка переменных окружения
В Bash console:
```bash
nano ~/.bashrc
```
Добавьте в конец файла:
```bash
export BOT_TOKEN="ваш_токен"
export ADMIN_IDS="1226518807"
export CASINO_REF_LINK="ваша_ссылка"
```
Сохраните (Ctrl+O, Enter, Ctrl+X)

## Шаг 6: Запуск
В разделе "Tasks" запустите задачу
