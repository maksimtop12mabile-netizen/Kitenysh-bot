import telebot
import sqlite3
import os
from telebot import types

TOKEN = '8784588745:AAEvqy4hd3y6s4OEyuctfcLr1bvIgL7ql4Y'
bot = telebot.TeleBot(TOKEN)

ADMIN_IDS = [8928500376]

user_data = {}
chat_sessions = {}
adding_product = set()

def init_db():
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            description TEXT,
            price REAL,
            photo_id TEXT,
            sold INTEGER DEFAULT 0
        )
    ''')
    try:
        cursor.execute('ALTER TABLE products ADD COLUMN sold INTEGER DEFAULT 0')
    except:
        pass
    conn.commit()
    conn.close()

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id,
        f"Привет! Твой ID: {message.from_user.id}\n\n"
        f"Доступные команды:\n"
        f"/market - посмотреть товары\n"
        f"/add - добавить товар (админ)\n"
        f"/sell - отметить товар как проданный (админ)"
    )

@bot.message_handler(commands=['market'])
def market(message):
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM products WHERE sold = 0')
    products = cursor.fetchall()
    conn.close()
    
    if not products:
        bot.send_message(message.chat.id, "Товаров пока нет")
        return
    
    bot.send_message(message.chat.id, f"Доступно товаров: {len(products)}")
    
    for product in products:
        product_id, name, desc, price, photo_id, sold = product
        text = f"{name}\n{desc}\n{price} руб."
        
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("Чат с продавцом", callback_data=f"chat_{product_id}"))
        
        try:
            bot.send_photo(message.chat.id, photo_id, caption=text, reply_markup=keyboard)
        except:
            bot.send_message(message.chat.id, text, reply_markup=keyboard)

@bot.message_handler(commands=['sell'])
def sell_product(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "Нет доступа!")
        return
    
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, price FROM products WHERE sold = 0')
    products = cursor.fetchall()
    conn.close()
    
    if not products:
        bot.send_message(message.chat.id, "Нет активных товаров")
        return
    
    text = "Выберите товар для продажи:\n\n"
    keyboard = types.InlineKeyboardMarkup()
    
    for product in products:
        product_id, name, price = product
        text += f"{product_id}: {name} - {price} руб.\n"
        keyboard.add(types.InlineKeyboardButton(
            f"{name} - ПРОДАНО",
            callback_data=f"sell_{product_id}"
        ))
    
    keyboard.add(types.InlineKeyboardButton("Отмена", callback_data="cancel_sell"))
    
    bot.send_message(message.chat.id, text, reply_markup=keyboard)

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
            f"Товар продан!\n{name}\n{price} руб."
        )

@bot.callback_query_handler(func=lambda call: call.data == "cancel_sell")
def cancel_sell(call):
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass

@bot.message_handler(commands=['add'])
def add_product(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "Нет доступа!")
        return
    
    adding_product.add(message.chat.id)
    user_data[message.chat.id] = {}
    
    msg = bot.send_message(message.chat.id, "Отправьте фото товара:")
    bot.register_next_step_handler(msg, get_photo)

def get_photo(message):
    if message.chat.id not in adding_product:
        return
    
    if not message.photo:
        msg = bot.send_message(message.chat.id, "Нужно фото!")
        bot.register_next_step_handler(msg, get_photo)
        return
    
    user_data[message.chat.id]['photo_id'] = message.photo[-1].file_id
    msg = bot.send_message(message.chat.id, "Название:")
    bot.register_next_step_handler(msg, get_name)

def get_name(message):
    if message.chat.id not in adding_product:
        return
    user_data[message.chat.id]['name'] = message.text
    msg = bot.send_message(message.chat.id, "Описание:")
    bot.register_next_step_handler(msg, get_desc)

def get_desc(message):
    if message.chat.id not in adding_product:
        return
    user_data[message.chat.id]['description'] = message.text
    msg = bot.send_message(message.chat.id, "Цена:")
    bot.register_next_step_handler(msg, get_price)

def get_price(message):
    if message.chat.id not in adding_product:
        return
    
    try:
        price = float(message.text)
        data = user_data[message.chat.id]
        
        conn = sqlite3.connect('shop.db')
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO products (name, description, price, photo_id) VALUES (?, ?, ?, ?)',
            (data['name'], data['description'], price, data['photo_id'])
        )
        conn.commit()
        conn.close()
        
        adding_product.remove(message.chat.id)
        del user_data[message.chat.id]
        
        bot.send_message(message.chat.id, f"Товар добавлен!\n{data['name']}\n{price} руб.")
        
    except ValueError:
        msg = bot.send_message(message.chat.id, "Введите число!")
        bot.register_next_step_handler(msg, get_price)

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
    buyer_username = f"@{call.from_user.username}" if call.from_user.username else "нет username"
    
    chat_sessions[buyer_id] = {
        'product_name': name,
        'price': price,
        'buyer_name': buyer_name
    }
    
    bot.send_message(
        call.message.chat.id,
        f"Чат открыт!\n{name}\n{price} руб.\n\nПишите сюда, сообщения уйдут продавцам.\n/exit - выход"
    )
    
    for admin_id in ADMIN_IDS:
        try:
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton("Ответить", callback_data=f"reply_{buyer_id}"))
            
            bot.send_message(
                admin_id,
                f"Новый чат!\n{buyer_name} ({buyer_username})\n{name}\n{price} руб.",
                reply_markup=keyboard
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
    
    bot.send_message(call.message.chat.id, f"Введите ответ:")

@bot.message_handler(commands=['exit'])
def exit_chat(message):
    if message.from_user.id in chat_sessions and 'product_name' in chat_sessions[message.from_user.id]:
        session = chat_sessions[message.from_user.id]
        for admin_id in ADMIN_IDS:
            try:
                bot.send_message(admin_id, f"{session['buyer_name']} вышел из чата")
            except:
                pass
        del chat_sessions[message.from_user.id]
        bot.send_message(message.chat.id, "Вы вышли из чата")
    else:
        bot.send_message(message.chat.id, "Вы не в чате")

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
                bot.send_message(buyer_id, f"Продавец: {text}")
                bot.send_message(user_id, "Отправлено!")
            except:
                bot.send_message(user_id, "Не отправлено")
        else:
            bot.send_message(user_id, "Чат закрыт")
        del chat_sessions[user_id]
    
    elif user_id in chat_sessions and 'product_name' in chat_sessions[user_id]:
        session = chat_sessions[user_id]
        for admin_id in ADMIN_IDS:
            try:
                keyboard = types.InlineKeyboardMarkup()
                keyboard.add(types.InlineKeyboardButton("Ответить", callback_data=f"reply_{user_id}"))
                bot.send_message(
                    admin_id,
                    f"{session['buyer_name']}:\n{session['product_name']}\n{text}",
                    reply_markup=keyboard
                )
            except:
                pass
        bot.send_message(user_id, "Отправлено!")

if __name__ == '__main__':
    init_db()
    print("Бот запущен!")
    bot.infinity_polling()
