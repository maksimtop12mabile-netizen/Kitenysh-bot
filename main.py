import telebot
import sqlite3
import os
from telebot import types

TOKEN = '8784588745:AAEvqy4hd3y6s4OEyuctfcLr1bvIgL7ql4Y'
bot = telebot.TeleBot(TOKEN)

ADMIN_IDS = [8928500376, 8225646133]

user_data = {}
chat_sessions = {}
adding_product = set()

E = {
    'box': '📦',
    'money': '💰',
    'desc': '📝',
    'name': '🏷️',
    'photo': '🖼️',
    'check': '✅',
    'cross': '❌',
    'star': '⭐',
    'cart': '🛒',
    'seller': '👤',
    'chat': '💬',
}

def init_db():
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            description TEXT,
            price REAL,
            photo_ids TEXT,
            sold INTEGER DEFAULT 0
        )
    ''')
    try:
        cursor.execute('ALTER TABLE products ADD COLUMN sold INTEGER DEFAULT 0')
    except:
        pass
    try:
        cursor.execute('ALTER TABLE products ADD COLUMN photo_ids TEXT')
    except:
        pass
    conn.commit()
    conn.close()

def format_price(price):
    if price >= 1000:
        return f"{price:,.0f} ₽".replace(',', ' ')
    return f"{int(price)} ₽" if price == int(price) else f"{price} ₽"

def escape_md(text):
    chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in chars:
        text = text.replace(char, f'\\{char}')
    return text

def create_product_caption(name, desc, price, index=0, total=0):
    caption = (
        f"{E['name']} *{escape_md(name)}*\n"
        f"{E['desc']} _{escape_md(desc)}_\n"
        f"{E['money']} *{format_price(price)}*"
    )
    
    if total > 1:
        caption += f"\n{E['photo']} Фото {index+1}/{total}"
    
    return caption

@bot.message_handler(commands=['start'])
def start(message):
    welcome = (
        f"{E['star']} *ДОБРО ПОЖАЛОВАТЬ!*\n\n"
        f"{E['cart']} *Команды:*\n"
        f"/market — товары\n"
        f"/help — помощь\n\n"
        f"Ваш ID: `{message.from_user.id}`"
    )
    bot.send_message(message.chat.id, welcome, parse_mode="Markdown")

@bot.message_handler(commands=['help'])
def help_command(message):
    help_text = (
        f"{E['star']} *ПОМОЩЬ*\n\n"
        f"{E['cart']} *Как купить:*\n"
        f"1. /market\n"
        f"2. Выберите товар\n"
        f"3. «Чат с продавцом»\n"
        f"4. Договоритесь\n\n"
        f"/exit — выйти из чата"
    )
    bot.send_message(message.chat.id, help_text, parse_mode="Markdown")

@bot.message_handler(commands=['market'])
def market(message):
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM products WHERE sold = 0 ORDER BY id DESC')
    products = cursor.fetchall()
    conn.close()
    
    if not products:
        bot.send_message(message.chat.id, f"{E['cross']} Товаров пока нет")
        return
    
    bot.send_message(
        message.chat.id,
        f"{E['cart']} *МАРКЕТ*\nДоступно: *{len(products)}*",
        parse_mode="Markdown"
    )
    
    for product in products:
        product_id, name, desc, price, photo_ids, sold = product
        
        caption = create_product_caption(name, desc, price)
        
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        
        if photo_ids:
            photos = photo_ids.split(',')
            if len(photos) > 1:
                keyboard.add(
                    types.InlineKeyboardButton("⬅️", callback_data=f"gal_{product_id}_0_prev"),
                    types.InlineKeyboardButton("➡️", callback_data=f"gal_{product_id}_0_next")
                )
        
        keyboard.add(types.InlineKeyboardButton(
            f"{E['chat']} Связаться с продавцом",
            callback_data=f"chat_{product_id}"
        ))
        
        first_photo = photo_ids.split(',')[0] if photo_ids else None
        
        if first_photo:
            try:
                bot.send_photo(
                    message.chat.id, 
                    first_photo, 
                    caption=caption + f"\n{E['photo']} Фото 1/{len(photos) if photo_ids else 1}",
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
            except:
                bot.send_message(message.chat.id, caption, reply_markup=keyboard, parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, caption, reply_markup=keyboard, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith('gal_'))
def gallery_navigation(call):
    parts = call.data.split('_')
    product_id = parts[1]
    current_index = int(parts[2])
    direction = parts[3]
    
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    cursor.execute('SELECT name, description, price, photo_ids FROM products WHERE id = ?', (product_id,))
    product = cursor.fetchone()
    conn.close()
    
    if not product:
        bot.answer_callback_query(call.id, "Товар не найден")
        return
    
    name, desc, price, photo_ids = product
    photos = photo_ids.split(',')
    total = len(photos)
    
    if direction == 'prev':
        new_index = (current_index - 1) % total
    else:
        new_index = (current_index + 1) % total
    
    caption = create_product_caption(name, desc, price, new_index, total)
    
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("⬅️", callback_data=f"gal_{product_id}_{new_index}_prev"),
        types.InlineKeyboardButton("➡️", callback_data=f"gal_{product_id}_{new_index}_next")
    )
    keyboard.add(types.InlineKeyboardButton(
        f"{E['chat']} Связаться с продавцом",
        callback_data=f"chat_{product_id}"
    ))
    
    try:
        bot.edit_message_media(
            media=types.InputMediaPhoto(photos[new_index], caption=caption, parse_mode="Markdown"),
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboard
        )
    except:
        bot.answer_callback_query(call.id, f"Фото {new_index+1}/{total}")
    
    bot.answer_callback_query(call.id)

@bot.message_handler(commands=['add'])
def add_product(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.send_message(message.chat.id, f"{E['cross']} Нет доступа!")
        return
    
    adding_product.add(message.chat.id)
    user_data[message.chat.id] = {'photos': []}
    
    bot.send_message(
        message.chat.id,
        f"{E['photo']} *ДОБАВЛЕНИЕ ТОВАРА*\n\n"
        f"Отправьте фото (можно несколько)\n"
        f"Когда закончите — /done",
        parse_mode="Markdown"
    )

@bot.message_handler(commands=['done'])
def done_photos(message):
    if message.chat.id not in adding_product:
        return
    
    if not user_data[message.chat.id].get('photos'):
        bot.send_message(message.chat.id, f"{E['cross']} Отправьте хотя бы одно фото!")
        return
    
    msg = bot.send_message(
        message.chat.id,
        f"{E['check']} Фото: {len(user_data[message.chat.id]['photos'])} шт.\n\n"
        f"{E['name']} Введите *название*:",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, get_name)

@bot.message_handler(content_types=['photo'])
def handle_photos(message):
    if message.chat.id not in adding_product:
        return
    
    if 'photos' not in user_data[message.chat.id]:
        user_data[message.chat.id]['photos'] = []
    
    user_data[message.chat.id]['photos'].append(message.photo[-1].file_id)
    
    count = len(user_data[message.chat.id]['photos'])
    bot.send_message(
        message.chat.id,
        f"{E['photo']} Фото {count} добавлено!\nЕщё или /done"
    )

def get_name(message):
    if message.chat.id not in adding_product:
        return
    
    user_data[message.chat.id]['name'] = message.text
    
    msg = bot.send_message(message.chat.id, f"{E['desc']} Введите *описание*:", parse_mode="Markdown")
    bot.register_next_step_handler(msg, get_desc)

def get_desc(message):
    if message.chat.id not in adding_product:
        return
    
    user_data[message.chat.id]['description'] = message.text
    
    msg = bot.send_message(message.chat.id, f"{E['money']} Введите *цену*:", parse_mode="Markdown")
    bot.register_next_step_handler(msg, get_price)

def get_price(message):
    if message.chat.id not in adding_product:
        return
    
    try:
        price = float(message.text)
        if price <= 0:
            raise ValueError
        
        data = user_data[message.chat.id]
        photo_ids = ','.join(data['photos'])
        
        conn = sqlite3.connect('shop.db')
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO products (name, description, price, photo_ids) VALUES (?, ?, ?, ?)',
            (data['name'], data['description'], price, photo_ids)
        )
        conn.commit()
        conn.close()
        
        preview = create_product_caption(data['name'], data['description'], price, 0, len(data['photos']))
        
        adding_product.remove(message.chat.id)
        del user_data[message.chat.id]
        
        bot.send_message(message.chat.id, f"{E['check']} *ТОВАР ДОБАВЛЕН!*", parse_mode="Markdown")
        
        if data['photos']:
            try:
                bot.send_photo(
                    message.chat.id,
                    data['photos'][0],
                    caption=preview + f"\n{E['photo']} Фото 1/{len(data['photos'])}",
                    parse_mode="Markdown"
                )
            except:
                bot.send_message(message.chat.id, preview, parse_mode="Markdown")
        
    except ValueError:
        msg = bot.send_message(message.chat.id, f"{E['cross']} Введите число:")
        bot.register_next_step_handler(msg, get_price)

@bot.message_handler(commands=['sell'])
def sell_product(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.send_message(message.chat.id, f"{E['cross']} Нет доступа!")
        return
    
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, price FROM products WHERE sold = 0')
    products = cursor.fetchall()
    conn.close()
    
    if not products:
        bot.send_message(message.chat.id, f"{E['cross']} Нет активных товаров")
        return
    
    text = f"{E['star']} *ВЫБЕРИТЕ ТОВАР:*\n\n"
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    
    for product in products:
        pid, name, price = product
        text += f"🆔 {pid} | {name} | {format_price(price)}\n"
        keyboard.add(types.InlineKeyboardButton(
            f"✅ {name} — ПРОДАНО",
            callback_data=f"sell_{pid}"
        ))
    
    keyboard.add(types.InlineKeyboardButton("❌ Отмена", callback_data="cancel_sell"))
    
    bot.send_message(message.chat.id, text, reply_markup=keyboard, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith('sell_'))
def confirm_sell(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    product_id = call.data.split('_')[1]
    
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE products SET sold = 1 WHERE id = ?', (product_id,))
    cursor.execute('SELECT name, price FROM products WHERE id = ?', (product_id,))
    product = cursor.fetchone()
    conn.commit()
    conn.close()
    
    if product:
        name, price = product
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        
        bot.send_message(
            call.message.chat.id,
            f"{E['check']} *ПРОДАНО!*\n{E['name']} *{escape_md(name)}*\n{E['money']} *{format_price(price)}*",
            parse_mode="Markdown"
        )

@bot.callback_query_handler(func=lambda call: call.data == "cancel_sell")
def cancel_sell(call):
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass

@bot.callback_query_handler(func=lambda call: call.data.startswith('chat_'))
def start_chat(call):
    product_id = call.data.split('_')[1]
    
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    cursor.execute('SELECT name, price, sold FROM products WHERE id = ?', (product_id,))
    product = cursor.fetchone()
    conn.close()
    
    if not product:
        bot.answer_callback_query(call.id, "Товар не найден")
        return
    
    name, price, sold = product
    
    if sold:
        bot.answer_callback_query(call.id, "Товар уже продан!")
        return
    
    buyer_id = call.from_user.id
    buyer_name = call.from_user.first_name
    buyer_username = f"@{call.from_user.username}" if call.from_user.username else "скрыт"
    
    chat_sessions[buyer_id] = {
        'product_name': name,
        'price': price,
        'buyer_name': buyer_name
    }
    
    bot.send_message(
        call.message.chat.id,
        f"{E['chat']} *ЧАТ ОТКРЫТ!*\n{E['name']} *{escape_md(name)}*\n{E['money']} *{format_price(price)}*\n\n"
        f"Пишите сюда — сообщения уйдут продавцам\n/exit — выход",
        parse_mode="Markdown"
    )
    
    for admin_id in ADMIN_IDS:
        try:
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton("✍️ Ответить", callback_data=f"reply_{buyer_id}"))
            
            bot.send_message(
                admin_id,
                f"🔔 *НОВЫЙ ЧАТ!*\n👤 *{buyer_name}* ({buyer_username})\n{E['name']} *{escape_md(name)}*\n{E['money']} *{format_price(price)}*",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        except:
            pass

@bot.callback_query_handler(func=lambda call: call.data.startswith('reply_'))
def admin_reply(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    buyer_id = int(call.data.split('_')[1])
    
    if buyer_id not in chat_sessions:
        bot.send_message(call.message.chat.id, "Чат закрыт")
        return
    
    chat_sessions[call.from_user.id] = {
        'reply_to': buyer_id,
        'buyer_name': chat_sessions[buyer_id]['buyer_name']
    }
    
    bot.send_message(call.message.chat.id, f"✍️ Ответ для *{chat_sessions[buyer_id]['buyer_name']}*:", parse_mode="Markdown")

@bot.message_handler(commands=['exit'])
def exit_chat(message):
    if message.from_user.id in chat_sessions and 'product_name' in chat_sessions[message.from_user.id]:
        session = chat_sessions[message.from_user.id]
        for admin_id in ADMIN_IDS:
            try:
                bot.send_message(admin_id, f"❌ {session['buyer_name']} вышел из чата")
            except:
                pass
        del chat_sessions[message.from_user.id]
        bot.send_message(message.chat.id, "✅ Вы вышли из чата")
    else:
        bot.send_message(message.chat.id, "❌ Вы не в чате")

@bot.message_handler(content_types=['text'])
def handle_text(message):
    if message.text.startswith('/'):
        return
    
    user_id = message.from_user.id
    text = message.text
    
    if user_id in adding_product:
        return
    
    if user_id in chat_sessions and 'reply_to' in chat_sessions[user_id]:
        buyer_id = chat_sessions[user_id]['reply_to']
        if buyer_id in chat_sessions:
            try:
                bot.send_message(buyer_id, f"💬 *Продавец:*\n{text}", parse_mode="Markdown")
                bot.send_message(user_id, "✅ Отправлено!")
            except:
                bot.send_message(user_id, "❌ Не отправлено")
        else:
            bot.send_message(user_id, "Чат закрыт")
        del chat_sessions[user_id]
    
    elif user_id in chat_sessions and 'product_name' in chat_sessions[user_id]:
        session = chat_sessions[user_id]
        for admin_id in ADMIN_IDS:
            try:
                keyboard = types.InlineKeyboardMarkup()
                keyboard.add(types.InlineKeyboardButton("✍️ Ответить", callback_data=f"reply_{user_id}"))
                bot.send_message(
                    admin_id,
                    f"💬 *{session['buyer_name']}*:\n{E['name']} {session['product_name']}\n📩 {text}",
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
            except:
                pass
        bot.send_message(user_id, "✅ Отправлено!")

if __name__ == '__main__':
    init_db()
    print("✅ Бот запущен!")
    bot.remove_webhook()
    bot.infinity_polling()
