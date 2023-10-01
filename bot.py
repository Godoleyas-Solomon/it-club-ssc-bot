from telegram import KeyboardButton, ReplyKeyboardMarkup, Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from telegram.ext import CallbackContext, CallbackQueryHandler, CommandHandler, ConversationHandler, Filters, \
    MessageHandler, Updater
import mysql.connector
from mysql.connector import Error
import re
import datetime
import config


PHONE_NUMBER, FULL_NAME, GRADE, EMAIL_ADDRESS, INTEREST, EXPERIENCE, AVAILABILITY, ACHIEVEMENT = range(8)


def create_connection():
    try:
        connection = mysql.connector.connect(
            host=config.host,
            database=config.database,
            port=config.port,
            user=config.user,
            password=config.password
        )
        return connection
    except Error as e:
        print(f'Error connecting to a database {e}')
        return None


def is_valid_email(email: str) -> bool:
    email_regex = r'^[\w\.-]+@[\w\.-]+\.\w{2,}$'
    return re.match(email_regex, email) is not None


def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    connection = create_connection()

    if connection is None:
        update.message.reply_text('Error connecting to the database.')
        return ConversationHandler.END

    try:
        cursor = connection.cursor()
        query = "SELECT * FROM members WHERE telegram_id = %s"
        cursor.execute(query, (user_id,))
        result = cursor.fetchone()

        if result:
            update.message.reply_text('Your account has already been registered.')
            update.message.reply_text('If you want to withdraw your application and delete your data, please send /withdraw.')

            return ConversationHandler.END

    except Error as e:
        print(f'Error checking user registration status: {e}')
        update.message.reply_text('An error occurred while checking user registration status.')
        return ConversationHandler.END

    finally:
        cursor.close()
        connection.close()

    keyboard = [[KeyboardButton("Share Contact", request_contact=True)]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    update.message.reply_text('Please click the "Share Contact" button to share your phone number.', reply_markup=reply_markup)
    return PHONE_NUMBER


def withdraw(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    connection = create_connection()

    if connection is None:
        update.message.reply_text('Error connecting to the database.')
        return

    try:
        cursor = connection.cursor()
        query = "SELECT * FROM members WHERE telegram_id = %s"
        cursor.execute(query, (user_id,))
        result = cursor.fetchone()

        if result:
            query = "DELETE FROM members WHERE telegram_id = %s"
            cursor.execute(query, (user_id,))
            connection.commit()

            update.message.reply_text('Your application has been withdrawn. Your data has been deleted from our records.')
        else:
            update.message.reply_text('You have not registered yet. No action was taken.')

    except Error as e:
        print(f'Error withdrawing application: {e}')
        update.message.reply_text('An error occurred while withdrawing your application.')

    finally:
        cursor.close()
        connection.close()




def collect_phone_number(update: Update, context: CallbackContext):
    context.user_data['user_info'] = []
    phone_number = update.message.contact.phone_number
    context.user_data['user_info'].append(phone_number)
    
    connection = create_connection()
    
    if connection is None:
        update.message.reply_text('Error connecting to the database.')
        return ConversationHandler.END
    
    try:
        cursor = connection.cursor()
        query = "SELECT * FROM members WHERE phone_number = %s"
        cursor.execute(query, (phone_number,))
        result = cursor.fetchone()

        if result:
            update.message.reply_text('Your phone number has already been registered.', reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END

    except Error as e:
        update.message.reply_text('Error checking phone number registration status.')
        return ConversationHandler.END

    finally:
        cursor.close()
        connection.close()
    update.message.reply_text('Please enter your full name.\nPress /cancel to cancel the registration', reply_markup=ReplyKeyboardRemove())
    return FULL_NAME

def collect_full_name(update: Update, context: CallbackContext):
    full_name = update.message.text
    context.user_data['user_info'].append(full_name)
    question = "What grade are you?"
    keyboard = [
        [InlineKeyboardButton("9", callback_data='9')],
        [InlineKeyboardButton("10", callback_data='10')],
        [InlineKeyboardButton("11", callback_data='11')],
        [InlineKeyboardButton("12", callback_data='12')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(question, reply_markup=reply_markup)
    return GRADE


def collect_grade(update: Update, context: CallbackContext):
    grade = update.callback_query.data
    context.user_data['user_info'].append(grade)
    update.callback_query.answer()
    update.callback_query.edit_message_text('Please enter your email address.')
    return EMAIL_ADDRESS


def collect_email_address(update: Update, context: CallbackContext):
    email_address = update.message.text
    if not is_valid_email(email_address):
        update.message.reply_text("Invalid email address format. Please enter a valid email address.")
        return EMAIL_ADDRESS
    else:
        context.user_data['user_info'].append(email_address)
        update.message.reply_text('Why are you interested in joining the IT club?')
        return INTEREST


def collect_interest(update: Update, context: CallbackContext):
    interest = update.message.text
    context.user_data['user_info'].append(interest)
    update.message.reply_text('Please list any previous experience or skills related to IT.')
    return EXPERIENCE


def collect_experience(update: Update, context: CallbackContext):
    experience = update.message.text
    context.user_data['user_info'].append(experience)
    question = "Will you be available to attend the meetings regularly?"
    keyboard = [
        [InlineKeyboardButton("Yes", callback_data=1)],
        [InlineKeyboardButton("No", callback_data=0)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(question, reply_markup=reply_markup)
    return AVAILABILITY


def collect_availability(update: Update, context: CallbackContext):
    availability = update.callback_query.data
    context.user_data['user_info'].append(availability)
    update.callback_query.answer()
    update.callback_query.edit_message_text('What do you think you will achieve at the end of the year?')
    return ACHIEVEMENT


def collect_achievement(update: Update, context: CallbackContext):
    achievement = update.message.text
    context.user_data['user_info'].append(achievement)
    
    user_info = context.user_data['user_info']
    telegram_id = update.effective_user.id
    full_name = user_info[1]
    phone_number = user_info[0]
    grade = int(user_info[2])
    email = user_info[3]
    interest = user_info[4]
    experience = user_info[5]
    availability = int(user_info[6])
    timestamp = datetime.datetime.now()
    
    connection = create_connection()
    
    if connection is None:
        update.message.reply_text('Error connecting to the database.')
        return ConversationHandler.END
    
    try:
        cursor = connection.cursor()
        query = "INSERT INTO members (telegram_id, full_name, phone_number, grade, email, interest, experience, availability, achievement, timestamp) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        values = (telegram_id, full_name, phone_number, grade, email, interest, experience, availability, achievement, timestamp)
        cursor.execute(query, values)
        connection.commit()

        update.message.reply_text('Thank you for registering. Your information has been saved.')

    except Error as e:
        update.message.reply_text(f'Error saving user registration information. {e}')
        return ConversationHandler.END

    finally:
        cursor.close()
        connection.close()
    
    return ConversationHandler.END


def cancel_registration(update: Update, context: CallbackContext):
    update.message.reply_text('Registration canceled.')
    return ConversationHandler.END


def main():
    updater = Updater(config.token)
    dispatcher = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            PHONE_NUMBER: [MessageHandler(Filters.contact, collect_phone_number)],
            FULL_NAME: [MessageHandler(Filters.text & ~Filters.command, collect_full_name)],
            GRADE: [CallbackQueryHandler(collect_grade)],
            EMAIL_ADDRESS: [MessageHandler(Filters.text & ~Filters.command, collect_email_address)],
            INTEREST: [MessageHandler(Filters.text & ~Filters.command, collect_interest)],
            EXPERIENCE: [MessageHandler(Filters.text & ~Filters.command, collect_experience)],
            AVAILABILITY: [CallbackQueryHandler(collect_availability)],
            ACHIEVEMENT: [MessageHandler(Filters.text & ~Filters.command, collect_achievement)]
        },
        fallbacks=[CommandHandler('cancel', cancel_registration)],
    )

    dispatcher.add_handler(conv_handler)
    withdraw_handler = CommandHandler('withdraw', withdraw)
    dispatcher.add_handler(withdraw_handler)

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
