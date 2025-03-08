import telebot
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, BigInteger
from sqlalchemy.orm import sessionmaker, declarative_base
import logging
from datetime import datetime

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

bot = telebot.TeleBot(TOKEN)

logging.basicConfig(filename='fuel_bot.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

engine = create_engine('sqlite:///trips.db')
Base = declarative_base()

class UserSettings(Base):
    __tablename__ = 'user_settings'
    user_id = Column(BigInteger, primary_key=True)
    base_fuel_consumption = Column(Float)
    extra_fuel_per_ton = Column(Float)

class Trip(Base):
    __tablename__ = 'trips'
    id = Column(Integer, primary_key=True)
    date = Column(Date)
    start_km = Column(Float)
    end_km = Column(Float)
    cargo_weight_kg = Column(Float)
    total_fuel = Column(Float)
    route = Column(String)
    car_number = Column(String)
    user_id = Column(BigInteger)

Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

@bot.message_handler(commands=['start'])
def start(message):
    try:
        logging.info(f"User {message.chat.id} started the bot")
        session = Session()
        user_settings = session.query(UserSettings).filter_by(user_id=message.chat.id).first()
        session.close()
        if user_settings:
            show_main_menu(message)
        else:
            bot.send_message(message.chat.id, "Похоже, что вы первый раз используете бот. Пожалуйста, введите базовый расход топлива (л/100 км).")
            add_cancel_button(message)
            bot.register_next_step_handler(message, get_base_fuel_consumption)
    except Exception as e:
        logging.error(f"Error in start command: {e}", exc_info=True)
        bot.send_message(message.chat.id, "Произошла ошибка, попробуйте позже.")

def add_cancel_button(message):
    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    cancel_button = telebot.types.KeyboardButton("Отменить")
    markup.add(cancel_button)
    bot.send_message(message.chat.id, "Вы можете отменить действие", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "Отменить")
def cancel_action(message):
    bot.send_message(message.chat.id, "Действие отменено.", reply_markup=telebot.types.ReplyKeyboardRemove())
    show_main_menu(message)

def get_base_fuel_consumption(message):
    if message.text == "Отменить":
        cancel_action(message)
        return
    try:
        base_fuel_consumption = float(message.text)
        bot.send_message(message.chat.id, "Теперь введите дополнительный расход топлива на тонну груза (л/100 км).")
        add_cancel_button(message)
        bot.register_next_step_handler(message, lambda msg: save_user_settings(msg, base_fuel_consumption))
    except ValueError:
        bot.send_message(message.chat.id, "❌ Введи число! Попробуй ещё раз.")
        add_cancel_button(message)
        bot.register_next_step_handler(message, get_base_fuel_consumption)
    except Exception as e:
        logging.error(f"Error in get_base_fuel_consumption: {e}", exc_info=True)
        bot.send_message(message.chat.id, "Произошла ошибка, попробуйте позже.")

def save_user_settings(message, base_fuel_consumption):
    if message.text == "Отменить":
        cancel_action(message)
        return
    try:
        extra_fuel_per_ton = float(message.text)
        session = Session()
        user_settings = UserSettings(
            user_id=message.chat.id,
            base_fuel_consumption=base_fuel_consumption,
            extra_fuel_per_ton=extra_fuel_per_ton
        )
        session.add(user_settings)
        session.commit()
        session.close()
        bot.send_message(message.chat.id, "Настройки сохранены.")
        show_main_menu(message)
    except ValueError:
        bot.send_message(message.chat.id, "❌ Введи число! Попробуй ещё раз.")
        add_cancel_button(message)
        bot.register_next_step_handler(message, lambda msg: save_user_settings(msg, base_fuel_consumption))
    except Exception as e:
        logging.error(f"Error in save_user_settings: {e}", exc_info=True)
        bot.send_message(message.chat.id, "Произошла ошибка, попробуйте позже.")

def show_main_menu(message):
    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    new_record_button = telebot.types.KeyboardButton("Новая запись")
    view_records_button = telebot.types.KeyboardButton("Просмотреть записи")
    delete_records_button = telebot.types.KeyboardButton("Удалить записи")
    settings_button = telebot.types.KeyboardButton("Настройки")
    markup.add(new_record_button, view_records_button, delete_records_button, settings_button)
    bot.send_message(message.chat.id, "Выберите действие:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text in ["Новая запись", "Просмотреть записи", "Удалить записи", "Настройки"])
def handle_menu(message):
    try:
        if message.text == "Новая запись":
            bot.send_message(message.chat.id, "Введи показание спидометра при выезде (км).")
            add_cancel_button(message)
            bot.register_next_step_handler(message, get_start_km)
        elif message.text == "Просмотреть записи":
            show_trips(message)
        elif message.text == "Удалить записи":
            delete_trips(message)
        elif message.text == "Настройки":
            update_settings(message)
    except Exception as e:
        logging.error(f"Error in handle_menu: {e}", exc_info=True)
        bot.send_message(message.chat.id, "Произошла ошибка, попробуйте позже.")

def get_start_km(message):
    if message.text == "Отменить":
        cancel_action(message)
        return
    try:
        start_km = float(message.text)
        bot.send_message(message.chat.id, "Теперь введи показание спидометра при приезде (км).")
        add_cancel_button(message)
        bot.register_next_step_handler(message, lambda msg: get_end_km(msg, start_km))
    except ValueError:
        bot.send_message(message.chat.id, "❌ Введи число! Попробуй ещё раз.")
        add_cancel_button(message)
        bot.register_next_step_handler(message, get_start_km)
    except Exception as e:
        logging.error(f"Error in get_start_km: {e}", exc_info=True)
        bot.send_message(message.chat.id, "Произошла ошибка, попробуйте позже.")

def get_end_km(message, start_km):
    if message.text == "Отменить":
        cancel_action(message)
        return
    try:
        end_km = float(message.text)
        if end_km < start_km:
            bot.send_message(message.chat.id, "❌ Ошибка! Приезд не может быть меньше выезда.")
            add_cancel_button(message)
            bot.register_next_step_handler(message, get_start_km)
            return
        bot.send_message(message.chat.id, "Теперь введи массу груза (кг).")
        add_cancel_button(message)
        bot.register_next_step_handler(message, lambda msg: calculate_fuel(msg, start_km, end_km))
    except ValueError:
        bot.send_message(message.chat.id, "❌ Введи число! Попробуй ещё раз.")
        add_cancel_button(message)
        bot.register_next_step_handler(message, lambda msg: get_end_km(msg, start_km))
    except Exception as e:
        logging.error(f"Error in get_end_km: {e}", exc_info=True)
        bot.send_message(message.chat.id, "Произошла ошибка, попробуйте позже.")

def calculate_fuel(message, start_km, end_km):
    if message.text == "Отменить":
        cancel_action(message)
        return
    try:
        cargo_weight_kg = float(message.text)
        session = Session()
        user_settings = session.query(UserSettings).filter_by(user_id=message.chat.id).first()
        if not user_settings:
            bot.send_message(message.chat.id, "Произошла ошибка при получении настроек пользователя.")
            return

        base_fuel_consumption = user_settings.base_fuel_consumption
        extra_fuel_per_ton = user_settings.extra_fuel_per_ton

        distance = end_km - start_km
        base_fuel = (distance / 100) * base_fuel_consumption
        extra_fuel = (distance / 100) * (cargo_weight_kg / 1000) * extra_fuel_per_ton
        total_fuel = base_fuel + extra_fuel

        trip = Trip(
            date=datetime.now().date(),
            start_km=start_km,
            end_km=end_km,
            cargo_weight_kg=cargo_weight_kg,
            total_fuel=total_fuel,
            route="Не указан",
            car_number="Не указан",
            user_id=message.chat.id
        )
        session.add(trip)
        session.commit()
        session.close()

        bot.send_message(message.chat.id, f"🚗 Пройденное расстояние: {distance:.2f} км\n"
                                          f"📦 Груз: {cargo_weight_kg / 1000:.2f} тонн\n"
                                          f"⛽ Примерный расход топлива: {total_fuel:.2f} литров.\n"
                                          f"✅ Данные сохранены.")
        show_main_menu(message)
    except ValueError:
        bot.send_message(message.chat.id, "❌ Введи число! Попробуй ещё раз.")
        add_cancel_button(message)
        bot.register_next_step_handler(message, lambda msg: calculate_fuel(msg, start_km, end_km))
    except Exception as e:
        logging.error(f"Error in calculate_fuel: {e}", exc_info=True)
        bot.send_message(message.chat.id, "Произошла ошибка, попробуйте позже.")

def show_trips(message):
    try:
        session = Session()
        trips = session.query(Trip).filter_by(user_id=message.chat.id).all()
        session.close()

        if trips:
            response = "Ваши поездки:\n"
            for trip in trips:
                response += f"Дата: {trip.date}\n"
                response += f"Расстояние: {trip.end_km - trip.start_km:.2f} км\n"
                response += f"Груз: {trip.cargo_weight_kg / 1000:.2f} тонн\n"
                response += f"Расход: {trip.total_fuel:.2f} л\n\n"
            bot.send_message(message.chat.id, response)
        else:
            bot.send_message(message.chat.id, "Нет записанных поездок.")
        show_main_menu(message)
    except Exception as e:
        logging.error(f"Error in show_trips: {e}", exc_info=True)
        bot.send_message(message.chat.id, "Произошла ошибка, попробуйте позже.")

def delete_trips(message):
    try:
        session = Session()
        trips = session.query(Trip).filter_by(user_id=message.chat.id).all()
        if trips:
            session.query(Trip).filter_by(user_id=message.chat.id).delete()
            session.commit()
            bot.send_message(message.chat.id, "Все ваши записи о поездках были удалены.")
        else:
            bot.send_message(message.chat.id, "У вас нет записей для удаления.")
        session.close()
        show_main_menu(message)
    except Exception as e:
        logging.error(f"Error in delete_trips: {e}", exc_info=True)
        bot.send_message(message.chat.id, "Произошла ошибка, попробуйте позже.")

def update_settings(message):
    try:
        session = Session()
        user_settings = session.query(UserSettings).filter_by(user_id=message.chat.id).first()
        session.close()
        if user_settings:
            bot.send_message(message.chat.id, f"Ваш текущий базовый расход топлива: {user_settings.base_fuel_consumption} л/100 км\n"
                                              f"Ваш текущий дополнительный расход топлива на тонну груза: {user_settings.extra_fuel_per_ton} л/100 км\n"
                                              f"Введите новый базовый расход топлива (л/100 км):")
            add_cancel_button(message)
            bot.register_next_step_handler(message, get_new_base_fuel_consumption)
        else:
            bot.send_message(message.chat.id, "Произошла ошибка при получении настроек пользователя.")
    except Exception as e:
        logging.error(f"Error in update_settings: {e}", exc_info=True)
        bot.send_message(message.chat.id, "Произошла ошибка, попробуйте позже.")

def get_new_base_fuel_consumption(message):
    if message.text == "Отменить":
        cancel_action(message)
        return
    try:
        base_fuel_consumption = float(message.text)
        bot.send_message(message.chat.id, "Теперь введите новый дополнительный расход топлива на тонну груза (л/100 км).")
        add_cancel_button(message)
        bot.register_next_step_handler(message, lambda msg: save_new_user_settings(msg, base_fuel_consumption))
    except ValueError:
        bot.send_message(message.chat.id, "❌ Введи число! Попробуй ещё раз.")
        add_cancel_button(message)
        bot.register_next_step_handler(message, get_new_base_fuel_consumption)
    except Exception as e:
        logging.error(f"Error in get_new_base_fuel_consumption: {e}", exc_info=True)
        bot.send_message(message.chat.id, "Произошла ошибка, попробуйте позже.")

def save_new_user_settings(message, base_fuel_consumption):
    if message.text == "Отменить":
        cancel_action(message)
        return
    try:
        extra_fuel_per_ton = float(message.text)
        session = Session()
        user_settings = session.query(UserSettings).filter_by(user_id=message.chat.id).first()
        user_settings.base_fuel_consumption = base_fuel_consumption
        user_settings.extra_fuel_per_ton = extra_fuel_per_ton
        session.commit()
        session.close()
        bot.send_message(message.chat.id, "Настройки обновлены.")
        show_main_menu(message)
    except ValueError:
        bot.send_message(message.chat.id, "❌ Введи число! Попробуй ещё раз.")
        add_cancel_button(message)
        bot.register_next_step_handler(message, lambda msg: save_new_user_settings(msg, base_fuel_consumption))
    except Exception as e:
        logging.error(f"Error in save_new_user_settings: {e}", exc_info=True)
        bot.send_message(message.chat.id, "Произошла ошибка, попробуйте позже.")

bot.polling(none_stop=True)
