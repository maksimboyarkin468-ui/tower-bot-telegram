"""
Генератор изображений для Tower Bot AI
Создает баннеры, иконки и графические элементы для бота и веб-приложения
"""

from PIL import Image, ImageDraw, ImageFont
import os

# Цветовая схема из style.css веб-приложения
COLORS = {
    'gradient_start': (74, 144, 226),      # #4a90e2
    'gradient_mid1': (107, 179, 255),      # #6bb3ff
    'gradient_mid2': (255, 140, 66),       # #ff8c42
    'gradient_end': (255, 107, 53),         # #ff6b35
    'background': (10, 10, 10),             # #0a0a0a
    'card': (42, 42, 42),                   # #2a2a2a
    'text': (255, 255, 255),                # #ffffff
    'text_secondary': (204, 204, 204),      # #cccccc
}

def create_gradient_background(width, height, colors):
    """Создает градиентный фон"""
    img = Image.new('RGB', (width, height), colors[0])
    draw = ImageDraw.Draw(img)
    
    for i in range(height):
        # Вычисляем цвет для текущей строки
        ratio = i / height
        if ratio < 0.3:
            # От start к mid1
            r = int(colors[0][0] + (colors[1][0] - colors[0][0]) * (ratio / 0.3))
            g = int(colors[0][1] + (colors[1][1] - colors[0][1]) * (ratio / 0.3))
            b = int(colors[0][2] + (colors[1][2] - colors[0][2]) * (ratio / 0.3))
        elif ratio < 0.7:
            # От mid1 к mid2
            r = int(colors[1][0] + (colors[2][0] - colors[1][0]) * ((ratio - 0.3) / 0.4))
            g = int(colors[1][1] + (colors[2][1] - colors[1][1]) * ((ratio - 0.3) / 0.4))
            b = int(colors[1][2] + (colors[2][2] - colors[1][2]) * ((ratio - 0.3) / 0.4))
        else:
            # От mid2 к end
            r = int(colors[2][0] + (colors[3][0] - colors[2][0]) * ((ratio - 0.7) / 0.3))
            g = int(colors[2][1] + (colors[3][1] - colors[2][1]) * ((ratio - 0.7) / 0.3))
            b = int(colors[2][2] + (colors[3][2] - colors[2][2]) * ((ratio - 0.7) / 0.3))
        
        draw.rectangle([(0, i), (width, i + 1)], fill=(r, g, b))
    
    return img

def create_main_menu_banner():
    """Создает баннер для главного меню бота"""
    width, height = 1200, 600
    
    # Создаем градиентный фон
    img = create_gradient_background(width, height, [
        COLORS['gradient_start'],
        COLORS['gradient_mid1'],
        COLORS['gradient_mid2'],
        COLORS['gradient_end']
    ])
    
    draw = ImageDraw.Draw(img)
    
    # Пытаемся загрузить шрифт, если не получается - используем стандартный
    try:
        # Пробуем разные шрифты
        font_large = ImageFont.truetype("arial.ttf", 80)
        font_medium = ImageFont.truetype("arial.ttf", 50)
        font_small = ImageFont.truetype("arial.ttf", 35)
    except:
        try:
            font_large = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 80)
            font_medium = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 50)
            font_small = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 35)
        except:
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_small = ImageFont.load_default()
    
    # Заголовок
    title = "TOWER BOT AI"
    title_bbox = draw.textbbox((0, 0), title, font=font_large)
    title_width = title_bbox[2] - title_bbox[0]
    title_height = title_bbox[3] - title_bbox[1]
    title_x = (width - title_width) // 2
    title_y = height // 4
    
    # Рисуем текст с тенью
    draw.text((title_x + 3, title_y + 3), title, fill=(0, 0, 0, 128), font=font_large)
    draw.text((title_x, title_y), title, fill=COLORS['text'], font=font_large)
    
    # Подзаголовок
    subtitle = "🏠 Сигнальный бот для игры Tower Rush"
    subtitle_bbox = draw.textbbox((0, 0), subtitle, font=font_medium)
    subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]
    subtitle_x = (width - subtitle_width) // 2
    subtitle_y = title_y + title_height + 30
    
    draw.text((subtitle_x + 2, subtitle_y + 2), subtitle, fill=(0, 0, 0, 128), font=font_medium)
    draw.text((subtitle_x, subtitle_y), subtitle, fill=COLORS['text'], font=font_medium)
    
    # Описание
    description = "Точные сигналы с помощью Искусственного Интеллекта"
    desc_bbox = draw.textbbox((0, 0), description, font=font_small)
    desc_width = desc_bbox[2] - desc_bbox[0]
    desc_x = (width - desc_width) // 2
    desc_y = subtitle_y + 80
    
    draw.text((desc_x + 1, desc_y + 1), description, fill=(0, 0, 0, 100), font=font_small)
    draw.text((desc_x, desc_y), description, fill=COLORS['text_secondary'], font=font_small)
    
    # Рисуем рамку
    border_width = 8
    draw.rectangle(
        [(border_width, border_width), (width - border_width, height - border_width)],
        outline=COLORS['text'],
        width=border_width
    )
    
    return img

def create_welcome_banner():
    """Создает баннер для приветственного сообщения"""
    width, height = 1200, 800
    
    # Темный фон
    img = Image.new('RGB', (width, height), COLORS['background'])
    draw = ImageDraw.Draw(img)
    
    # Градиентная рамка
    border_img = create_gradient_background(width, height, [
        COLORS['gradient_start'],
        COLORS['gradient_mid1'],
        COLORS['gradient_mid2'],
        COLORS['gradient_end']
    ])
    
    # Накладываем градиент как рамку
    border_width = 10
    img.paste(border_img.crop((0, 0, width, border_width)), (0, 0))
    img.paste(border_img.crop((0, height - border_width, width, height)), (0, height - border_width))
    img.paste(border_img.crop((0, 0, border_width, height)), (0, 0))
    img.paste(border_img.crop((width - border_width, 0, width, height)), (width - border_width, 0))
    
    draw = ImageDraw.Draw(img)
    
    try:
        font_large = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 90)
        font_medium = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 45)
    except:
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
    
    # Заголовок
    title = "🎉 Добро пожаловать!"
    title_bbox = draw.textbbox((0, 0), title, font=font_large)
    title_width = title_bbox[2] - title_bbox[0]
    title_x = (width - title_width) // 2
    title_y = height // 3
    
    draw.text((title_x, title_y), title, fill=COLORS['text'], font=font_large)
    
    # Описание
    desc_lines = [
        "TOWER BOT AI - Сигнальный бот",
        "для игры Tower Rush",
        "",
        "Получайте точные сигналы",
        "с помощью Искусственного Интеллекта"
    ]
    
    y_offset = title_y + 150
    for line in desc_lines:
        if line:
            line_bbox = draw.textbbox((0, 0), line, font=font_medium)
            line_width = line_bbox[2] - line_bbox[0]
            line_x = (width - line_width) // 2
            draw.text((line_x, y_offset), line, fill=COLORS['text_secondary'], font=font_medium)
        y_offset += 60
    
    return img

def create_subscription_banner():
    """Создает баннер для экрана подписки"""
    width, height = 1200, 600
    
    img = Image.new('RGB', (width, height), COLORS['card'])
    draw = ImageDraw.Draw(img)
    
    # Градиентная верхняя полоса
    gradient_bar = create_gradient_background(width, 80, [
        COLORS['gradient_start'],
        COLORS['gradient_mid1'],
        COLORS['gradient_mid2'],
        COLORS['gradient_end']
    ])
    img.paste(gradient_bar.crop((0, 0, width, 80)), (0, 0))
    
    draw = ImageDraw.Draw(img)
    
    try:
        font_large = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 70)
        font_medium = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 40)
    except:
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
    
    # Заголовок
    title = "📢 Подписка на канал"
    title_bbox = draw.textbbox((0, 0), title, font=font_large)
    title_width = title_bbox[2] - title_bbox[0]
    title_x = (width - title_width) // 2
    title_y = 120
    
    draw.text((title_x, title_y), title, fill=COLORS['text'], font=font_large)
    
    # Описание
    desc = "Для получения доступа к сигналам\nнеобходимо подписаться на наш канал"
    desc_y = title_y + 120
    
    for line in desc.split('\n'):
        line_bbox = draw.textbbox((0, 0), line, font=font_medium)
        line_width = line_bbox[2] - line_bbox[0]
        line_x = (width - line_width) // 2
        draw.text((line_x, desc_y), line, fill=COLORS['text_secondary'], font=font_medium)
        desc_y += 50
    
    return img

def create_deposit_banner():
    """Создает баннер для экрана депозита"""
    width, height = 1200, 600
    
    img = Image.new('RGB', (width, height), COLORS['card'])
    draw = ImageDraw.Draw(img)
    
    # Градиентная верхняя полоса
    gradient_bar = create_gradient_background(width, 80, [
        COLORS['gradient_start'],
        COLORS['gradient_mid1'],
        COLORS['gradient_mid2'],
        COLORS['gradient_end']
    ])
    img.paste(gradient_bar.crop((0, 0, width, 80)), (0, 0))
    
    draw = ImageDraw.Draw(img)
    
    try:
        font_large = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 70)
        font_medium = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 40)
    except:
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
    
    # Заголовок
    title = "💰 Депозит"
    title_bbox = draw.textbbox((0, 0), title, font=font_large)
    title_width = title_bbox[2] - title_bbox[0]
    title_x = (width - title_width) // 2
    title_y = 120
    
    draw.text((title_x, title_y), title, fill=COLORS['text'], font=font_large)
    
    # Описание
    desc = "Для получения доступа к сигналам\nнеобходимо внести депозит"
    desc_y = title_y + 120
    
    for line in desc.split('\n'):
        line_bbox = draw.textbbox((0, 0), line, font=font_medium)
        line_width = line_bbox[2] - line_bbox[0]
        line_x = (width - line_width) // 2
        draw.text((line_x, desc_y), line, fill=COLORS['text_secondary'], font=font_medium)
        desc_y += 50
    
    return img

def create_success_banner():
    """Создает баннер для успешного подтверждения"""
    width, height = 1200, 600
    
    # Градиентный фон
    img = create_gradient_background(width, height, [
        COLORS['gradient_start'],
        COLORS['gradient_mid1'],
        COLORS['gradient_mid2'],
        COLORS['gradient_end']
    ])
    
    draw = ImageDraw.Draw(img)
    
    try:
        font_large = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 80)
        font_medium = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 45)
    except:
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
    
    # Заголовок
    title = "✅ Доступ открыт!"
    title_bbox = draw.textbbox((0, 0), title, font=font_large)
    title_width = title_bbox[2] - title_bbox[0]
    title_x = (width - title_width) // 2
    title_y = height // 3
    
    draw.text((title_x + 3, title_y + 3), title, fill=(0, 0, 0, 128), font=font_large)
    draw.text((title_x, title_y), title, fill=COLORS['text'], font=font_large)
    
    # Описание
    desc = "Ваш депозит подтвержден.\nТеперь вы можете получать сигналы!"
    desc_y = title_y + 120
    
    for line in desc.split('\n'):
        line_bbox = draw.textbbox((0, 0), line, font=font_medium)
        line_width = line_bbox[2] - line_bbox[0]
        line_x = (width - line_width) // 2
        draw.text((line_x + 2, desc_y + 2), line, fill=(0, 0, 0, 100), font=font_medium)
        draw.text((line_x, desc_y), line, fill=COLORS['text'], font=font_medium)
        desc_y += 60
    
    return img

def main():
    """Генерирует все изображения"""
    import sys
    # Настраиваем кодировку для Windows
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    
    # Создаем папку для изображений если её нет
    images_dir = os.path.join(os.path.dirname(__file__), 'images')
    os.makedirs(images_dir, exist_ok=True)
    
    print("Генерация изображений для Tower Bot AI...")
    
    # Генерируем изображения
    images = {
        'main_menu': create_main_menu_banner(),
        'welcome': create_welcome_banner(),
        'subscription': create_subscription_banner(),
        'deposit': create_deposit_banner(),
        'success': create_success_banner(),
    }
    
    # Сохраняем изображения
    for name, img in images.items():
        # Сохраняем в JPG
        jpg_path = os.path.join(images_dir, f'{name}.jpg')
        img.save(jpg_path, 'JPEG', quality=95)
        print(f"[OK] Создано: {jpg_path}")
        
        # Сохраняем в WebP (для Telegram, меньший размер)
        webp_path = os.path.join(images_dir, f'{name}.webp')
        img.save(webp_path, 'WEBP', quality=90)
        print(f"[OK] Создано: {webp_path}")
    
    print("\nГенерация завершена!")
    print(f"\nИзображения сохранены в: {images_dir}")
    print("\nТеперь вы можете использовать эти изображения в боте:")
    print("   - main_menu.jpg/webp - для главного меню")
    print("   - welcome.jpg/webp - для приветствия")
    print("   - subscription.jpg/webp - для экрана подписки")
    print("   - deposit.jpg/webp - для экрана депозита")
    print("   - success.jpg/webp - для успешного подтверждения")

if __name__ == "__main__":
    main()
