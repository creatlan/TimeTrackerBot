import logging
import random
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
import datetime
import sqlite3


TOKEN = "TOKEN"

bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# Initializing the logger
logging.basicConfig(level=logging.INFO)

connect = sqlite3.connect('TimeTracker.db')


def base_db(user_id: int, user_name: str):
    conn = sqlite3.connect('TimeTracker.db', timeout=7)
    cursor = conn.cursor()
    cursor.execute(f"SELECT user_id FROM test WHERE user_id = {user_id}")
    data = cursor.fetchone()
    if data is None:
        cursor.execute("""INSERT INTO test (
            user_id,
            user_name
        ) VALUES (?, ?)""", (user_id, user_name))
        conn.commit()
        conn.close()


# START

# Describing user states
class Activity(StatesGroup):
    start = State()
    time = State()
    activity = State()


@dp.message_handler(commands='start')
async def start_command(message: types.Message):
    user_id = message.from_user.id
    user_full_name = message.from_user.full_name
    base_db(user_id=user_id, user_name=user_full_name)
    await message.reply(f"Привет, {user_full_name}! Я бот, который поможет вам отслеживать время и отказаться от прокрастинации!👾")
    await activity_button(message)


@dp.message_handler(state=Activity.start)
async def activity_button(message: types.Message):
    keyboard_activity = types.ReplyKeyboardMarkup(
        resize_keyboard=True,
        one_time_keyboard=True)
    activity_button1 = types.KeyboardButton(text="Study")
    activity_button2 = types.KeyboardButton(text="Work")
    activity_button3 = types.KeyboardButton(text="Rest")
    activity_button4 = types.KeyboardButton(text="Another")
    keyboard_activity.add(activity_button1, activity_button2, activity_button3, activity_button4)

    await message.answer("Выберите активность, которой хотите заняться:", reply_markup=keyboard_activity)

    # Changing the user's state to Activity.time
    await Activity.time.set()


def add_activity(activity: str, user_id: int):
    conn = sqlite3.connect('TimeTracker.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE test SET activity = ? WHERE user_id = ?', (f"{activity}", user_id))
    conn.commit()
    conn.close()


def from_activity(user_id: int):
    conn = sqlite3.connect('TimeTracker.db')
    cursor = conn.cursor()
    activity = str(cursor.execute(f"SELECT activity FROM test WHERE user_id={user_id}").fetchone()[0])
    conn.close()
    return activity


def add_time(activity: str, time: int, user_id: int):
    conn = sqlite3.connect('TimeTracker.db')
    cursor = conn.cursor()
    result = cursor.execute(f"SELECT time_{activity} FROM test WHERE user_id = {user_id}").fetchone()
    if result[0] is not None:
        time += int(result[0])
    cursor.execute(f'Update test set time_{activity} = ? where user_id = ?', (time, user_id))
    conn.commit()
    conn.close()


def from_time(activity: str, user_id: int):
    conn = sqlite3.connect('TimeTracker.db')
    cursor = conn.cursor()
    result = cursor.execute(f"SELECT time_{activity} FROM test WHERE user_id = {user_id}").fetchone()
    if result[0] is not None:
        time_activity = int(result[0])
    else:
        time_activity = int(0)
    conn.close()
    return time_activity


@dp.message_handler(state=Activity.time)
async def activity_command(message: types.Message):
    activity = message.text.lower()
    add_activity(activity, int(message.from_user.id))
    from_activ = from_activity(user_id=message.from_user.id)

    if from_activ != 'study' and from_activ != 'work' and from_activ != 'rest' and from_activ != 'another':
        await message.answer("Простите, я вас не понимаю😔\nПожалуйста, воспользуйтесь кнопками ниже⬇️")
        await activity_button(message)
    else:
        await time_button(message)


@dp.message_handler(state=Activity.time)
async def time_button(message: types.Message):
    keyboard_time = types.ReplyKeyboardMarkup(
        resize_keyboard=True,
        one_time_keyboard=True)
    time_button1 = types.KeyboardButton(text="10 мин")
    time_button2 = types.KeyboardButton(text="20 мин")
    time_button3 = types.KeyboardButton(text="30 мин")
    time_button4 = types.KeyboardButton(text="60 мин")
    keyboard_time.add(time_button1, time_button2, time_button3, time_button4)

    await message.answer("Выберите время, которое хотите этому уделить:", reply_markup=keyboard_time)
    await Activity.activity.set()


@dp.message_handler(state=Activity.activity)
async def time_activity(message: types.Message, state: FSMContext):
    time = message.text

    if time != '10 мин' and time != '20 мин' and time != '30 мин' and time != '60 мин':
        await message.answer("Простите, я вас не понимаю😔\nПожалуйста, воспользуйтесь кнопками ниже⬇️")
        await time_button(message)
    else:
        user_id = message.from_user.id
        time = int(message.text.split()[0])
        activity = from_activity(user_id=user_id)
        add_time(activity, time, user_id)

        end_time = datetime.datetime.now() + datetime.timedelta(minutes=time)

        await message.answer(
            f"Вы начали отслеживать {activity}\n\nНачало: {datetime.datetime.now().strftime('%H:%M')}\nОкончание: {end_time.strftime('%H:%M')}")

        # Returning to the initial state
        await state.finish()


def conversation_to_hours(time_activity: int):
    if time_activity > 60 and time_activity % 60 != 0:
        hours = str(time_activity//60)
        minutes = str(time_activity % 60)
        flag = hours + ' ч ' + minutes + ' мин'
    elif time_activity % 60 == 0:
        hours = str(time_activity//60)
        flag = hours + ' ч'
    else:
        minutes = str(time_activity)
        flag = minutes + ' мин'
    return flag


# GET_TIME to output the total time spent

@dp.message_handler(commands='get_time')
async def start_get_time(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    time_study = from_time(activity='study', user_id=user_id)
    time_work = from_time(activity='work', user_id=user_id)
    time_rest = from_time(activity='rest', user_id=user_id)
    time_another = from_time(activity='another', user_id=user_id)
    await message.answer(f"⏱Всего вы занимались:\n\nStudy = {conversation_to_hours(time_study)}\nWork = {conversation_to_hours(time_work)}\nRest = {conversation_to_hours(time_rest)}\nAnother = {conversation_to_hours(time_another)}")
    await state.finish()


# MOTIVATION to motivate users

class Motivation(StatesGroup):
    reply = State()


@dp.message_handler(commands='motivation')
async def motivation(message: types.Message):
    keyboard_motivation = types.ReplyKeyboardMarkup(
        resize_keyboard=True,
        one_time_keyboard=True)
    motivation_button1 = types.KeyboardButton(text="Советы👾")
    motivation_button2 = types.KeyboardButton(text="Мотивация🦾")
    motivation_button3 = types.KeyboardButton(text="Поддержка💜")
    keyboard_motivation.add(motivation_button1, motivation_button2, motivation_button3)

    await message.answer("Выберите мотивацию, которая вам сейчас необходима:", reply_markup=keyboard_motivation)
    await Motivation.reply.set()


@dp.message_handler(state=Motivation.reply)
async def reply_command(message: types.Message, state: FSMContext):
    motivation_but = message.text

    if motivation_but != 'Советы👾' and motivation_but != 'Мотивация🦾' and motivation_but != 'Поддержка💜':
        await message.answer("Простите, я вас не понимаю😔\nПожалуйста, воспользуйтесь кнопками ниже⬇️")
        await motivation(message)
    elif motivation_but == 'Советы👾':
        await motivation_but1(message)
    elif motivation_but == 'Мотивация🦾':
        await motivation_but2(message)
    elif motivation_but == 'Поддержка💜':
        await motivation_but3(message)
    await state.finish()


ADVICE = [
    "⏱ Напомните себе, почему вы начали эту работу. Возможно, у вас были конкретные цели, которые вы хотели достичь, или вы мечтали о карьерном росте. Помните, что эти цели все еще актуальны и достижимы, если вы продолжите работать.",
    "⏱ Установите маленькие цели. Вместо того чтобы думать о большой конечной цели, поставьте себе маленькие цели на каждый день или неделю. Это поможет вам чувствовать, что вы движетесь вперед и что ваша работа имеет смысл.",
    "⏱ Отдохните. Если вы чувствуете, что у вас заканчиваются силы, возьмите короткий перерыв. Отдохните, чтобы зарядиться энергией и снова начать работать.",
    "⏱ Общайтесь с коллегами. Общение с коллегами может помочь вам оставаться мотивированным. Попробуйте пообщаться с ними, чтобы поделиться своими мыслями и идеями, или чтобы получить от них поддержку.",
    "⏱ Визуализируйте успех. Представьте, какой результат вы получите, если продолжите работать. Это может быть достижение личной цели, новое умение или просто удовлетворение от выполненной работы.",
    "⏱ Следите за своим прогрессом. Ведите журнал или используйте приложения, которые помогут отслеживать прогресс в достижении ваших целей. Это даст вам четкое представление о том, как далеко вы продвинулись и что вам еще нужно сделать.",
    "⏱ Не позволяйте сомнениям и страхам взять верх. Иногда мы сами себе ставим преграды и боимся неудачи. Но не забывайте, что ошибки и неудачи – это не конец, а всего лишь шаг на пути к успеху. Будьте готовы к тому, что мотивация может не всегда оставаться на высоком уровне, но не позволяйте сомнениям взять верх."
]


@dp.message_handler(state=Motivation.reply)
async def motivation_but1(message: types.Message):
    advice = random.choice(ADVICE)
    await message.reply(advice)


QUOTES = [
    "✨ Жизнь - это не о том, чтобы найти себя. Жизнь - это о том, чтобы создать себя.",
    "✨ Успех - это не результат одного дня или недели. Успех - это результат постоянных усилий, упорства и труда.",
    "✨ Будьте сильны и верьте в себя. Если вы верите в свои возможности, то можете добиться любых целей, которые вы поставите перед собой.",
    "✨ Не бойтесь своих ошибок, они помогут вам учиться и расти. Лучшие уроки жизни мы получаем из своих неудач и ошибок.",
    "✨ Не сравнивайте себя с другими. Каждый человек уникален и имеет свои таланты и достоинства. Найдите свою уникальность и используйте ее, чтобы достичь своих целей.",
    "✨ Самое важное в жизни - это не бояться рисковать и принимать вызовы. Не бойтесь выходить за границы своей зоны комфорта и искать новые возможности.",
    "✨ Доверься своей интуиции и слушай своё сердце. Иногда лучшие решения приходят, когда мы даем себе возможность послушать свои чувства.",
    "✨ Даже самый долгий путь начинается с первого шага.",
    "✨ Все что нам нужно – это мечта, вера и немного труда.",
    "✨ Успех – это способность идти от одной неудачи к другой не теряя энтузиазма.",
    "✨ Лучший способ спрятать свою лень – заняться делом.",
    "✨ Трудности формируют наши характеры.",
    "✨ Каждый день – новый шанс стать лучше."
]


@dp.message_handler(state=Motivation.reply)
async def motivation_but2(message: types.Message):
    quote = random.choice(QUOTES)
    await message.reply(quote)


SUPPORT = [
    "Время лечит все раны, и это тоже пройдет💜",
    "Важно помнить, что все трудности временные, и вы пройдете через них💜",
    "У вас есть сила и ресурсы, чтобы преодолеть это. Просто держитесь и продолжайте идти вперед💜",
    "Никогда не забывайте, что вы уже преодолели много трудностей в своей жизни и сможете преодолеть и эту💜",
    "Я понимаю, что сейчас трудно, но я верю в вас и знаю, что вы сможете преодолеть это💜",
    "Вы не одиноки в своей борьбе. Я всегда здесь, чтобы поддержать вас💜",
    "Маленькие шаги могут привести к большим результатам. Давайте начнем с простых задач и постепенно двигаться дальше💜",
    "Не слишком сильно судите себя за прошлые ошибки. Вместо этого, давайте сфокусируемся на настоящем и будущем, чтобы достигнуть успеха💜",
    "Вы очень сильны, и я уверен, что вы можете справиться с этой ситуацией. Давайте работать вместе, чтобы достичь успеха💜",
    "Я знаю, что сейчас может быть сложно увидеть свет в конце тоннеля, но мы сможем найти его вместе и выйти из этой ситуации сильнее и мудрее💜"
]


@dp.message_handler(state=Motivation.reply)
async def motivation_but3(message: types.Message):
    support = random.choice(SUPPORT)
    await message.reply(support)


@dp.message_handler(commands='help')
async def help_command(message: types.Message, state: FSMContext):
    user_full_name = message.from_user.full_name
    await message.answer(f"Привет, {user_full_name}! Пожалуйста, используйте эти команды:\n\n"
                         f"/start - для выбора типа работы и времени\n"
                         f"/get_time - для вывода всего затраченного времени\n"
                         f"/motivation - для получения совета и мотивации к работе")
    await state.finish()


# Handler for user activity input
if __name__ == '__main__':
    # Launching long-polling
    executor.start_polling(dp)
