import sqlite3
import os

DB_NAME = 'tower_bot.db'

print("Проверка и исправление базы данных...")

conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()

# Получаем список всех колонок
cursor.execute('PRAGMA table_info(users)')
existing_columns = [col[1] for col in cursor.fetchall()]

print(f"\nСуществующие колонки: {existing_columns}")

# Список необходимых колонок
required_columns = {
    'subscribed_to_channel': 'INTEGER DEFAULT 0',
    'start_used': 'INTEGER DEFAULT 0'
}

# Добавляем недостающие колонки
for col_name, col_type in required_columns.items():
    if col_name not in existing_columns:
        try:
            print(f"\nДобавляю колонку: {col_name}")
            cursor.execute(f'ALTER TABLE users ADD COLUMN {col_name} {col_type}')
            print(f"✅ Колонка {col_name} добавлена")
        except sqlite3.OperationalError as e:
            print(f"❌ Ошибка при добавлении {col_name}: {e}")
    else:
        print(f"✅ Колонка {col_name} уже существует")

conn.commit()

# Проверяем результат
cursor.execute('PRAGMA table_info(users)')
final_columns = [col[1] for col in cursor.fetchall()]
print(f"\nФинальные колонки: {final_columns}")

conn.close()

print("\n✅ База данных исправлена!")
input("\nНажмите Enter для выхода...")
