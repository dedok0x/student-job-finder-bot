import asyncio
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from keyboards.for_questions import *

from database import save_candidate, update_candidate_score, update_candidate_status

logger = logging.getLogger(__name__)

# Define states for the questionnaire
class Questionnaire(StatesGroup):
    who_are_you = State()
    what_are_you_looking_for = State()
    direction = State()
    clarifying_questions = State()
    experience = State()
    skills = State()
    resume_links = State()
    test_questions = State()
    work_style = State()
    contacts = State()
    confirmation = State()

# Router for handling questions
router = Router()

WHO_ARE_YOU_MAP = {
    "student": "студент",
    "graduate": "выпускник",
    "beginner_specialist": "начинающий специалист",
    "change_profession": "меняю профессию",
}

LOOKING_FOR_MAP = {
    "internship": "стажировка",
    "part_time": "частичная занятость",
    "full_time": "полная занятость",
    "project": "проектная работа",
}

DIRECTION_MAP = {
    "it_product": "IT / Продукт",
    "digital_marketing_design": "Digital / маркетинг / дизайн",
    "business_operations": "Бизнес / операции",
    "help_determine": "не знаю, помогите определить",
}

EXPERIENCE_MAP = {
    "no_experience": "нет опыта",
    "internship": "стажировка",
    "courses": "курсы",
    "educational_projects": "учебные проекты",
    "freelance": "фриланс",
    "commercial_up_to_1_year": "коммерческий опыт до 1 года",
    "1_2_years": "1-2 года",
}

WORK_STYLE_MAP = {
    "ask_manager_immediately": "сразу уточняю у руководителя",
    "try_myself_first": "сначала сам разбираюсь, потом задаю вопросы",
    "wait_for_clarification": "откладываю и жду дополнительных пояснений",
}

TEST_QUESTIONS_BY_DIRECTION = {
    "IT / Продукт": [
        "Что такое HTML / CSS / SQL / API на базовом уровне?",
        "Чем отличаются интерфейс и серверная часть?",
        "Для чего нужен Git?",
    ],
    "Digital / маркетинг / дизайн": [
        "Чем отличается охват от вовлеченности?",
        "Что такое целевая аудитория?",
        "Как понять, что реклама работает?",
    ],
    "Бизнес / операции": [
        "Что такое воронка продаж?",
        "Как действовать, если клиент сомневается?",
        "Зачем фиксировать информацию в CRM?",
    ],
}

EMAIL_REGEX = re.compile(r"(?i)^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$")
PHONE_REGEX = re.compile(r"^(?:\+7|7|8)?[\s\-()]*\d(?:[\s\-()]*\d){9,10}$")
TG_REGEX = re.compile(r"^(?:@|https?://t\.me/)([A-Za-z0-9_]{5,32})$")

# Helper function to get direction options
def get_direction_options() -> List[InlineKeyboardButton]:
    """Return inline keyboard buttons for direction selection."""
    directions = [
        "IT / Продукт",
        "Digital / маркетинг / дизайн", 
        "Бизнес / операции",
        "не знаю, помогите определить"
    ]
    return [InlineKeyboardButton(text=direction, callback_data=f"direction_{direction.lower().replace(' ', '_').replace('/', '_').replace('-', '_')}") for direction in directions]

# Helper function to get experience options
def get_experience_options() -> List[InlineKeyboardButton]:
    """Return inline keyboard buttons for experience selection."""
    experiences = [
        "нет опыта",
        "стажировка", 
        "курсы",
        "учебные проекты",
        "фриланс",
        "коммерческий опыт до 1 года",
        "1-2 года"
    ]
    return [InlineKeyboardButton(text=exp, callback_data=f"exp_{exp}") for exp in experiences]

# Helper function to get work style options
def get_work_style_options() -> List[InlineKeyboardButton]:
    """Return inline keyboard buttons for work style selection."""
    styles = [
        "сразу уточняю у руководителя",
        "сначала сам разбираюсь, потом задаю вопросы",
        "откладываю и жду дополнительных пояснений"
    ]
    return [InlineKeyboardButton(text=style, callback_data=f"style_{style}") for style in styles]

# Helper function to get contact options
def get_contact_options() -> List[InlineKeyboardButton]:
    """Return inline keyboard buttons for contact preferences."""
    contacts = [
        "Telegram",
        "Email",
        "Phone"
    ]
    return [InlineKeyboardButton(text=contact, callback_data=f"contact_{contact}") for contact in contacts]

# Start the questionnaire
@router.message(Command(commands=['start', 'help']))
async def start_questionnaire(message: Message, state: FSMContext):
    """Start the questionnaire."""
    await state.clear()
    
    welcome_text = (
        "👋 Привет! Я помогу собрать информацию для быстрого отбора.\n\n"
        "Ответь на несколько простых вопросов, и мы сразу перейдём к следующему этапу.\n"
        "Все ответы сохранятся в нашу базу.\n"
        "\n"
        "Начнём с первого вопроса:"
    )
    
    await message.answer(welcome_text, reply_markup=ReplyKeyboardRemove())
    
    # Move to the first question
    await state.set_state(Questionnaire.who_are_you)
    await message.answer("1️⃣ Кто ты?\n"
                        "студент / выпускник / начинающий специалист / меняю профессию",
                        reply_markup=get_who_are_you_keyboard())

# Process "Who are you" question
@router.callback_query(Questionnaire.who_are_you)
async def process_who_are_you(callback: CallbackQuery, state: FSMContext):
    """Process who are you question."""
    user_choice = callback.data
    
    # Extract the actual choice from callback data
    if user_choice.startswith("who_"):
        choice_key = user_choice[4:]  # Remove "who_" prefix
        choice = WHO_ARE_YOU_MAP.get(choice_key, choice_key)
        await state.update_data(who_are_you=choice)
        
        # Move to next question
        await state.set_state(Questionnaire.what_are_you_looking_for)
        await callback.message.answer("2️⃣ Что ищешь?\n"
                                    "стажировка / частичная занятость / полная занятость / проектная работа",
                                    reply_markup=get_what_are_you_looking_for_keyboard())
    else:
        await callback.answer("Пожалуйста, выберите один из вариантов.", show_alert=True)

# Process "What are you looking for" question
@router.callback_query(Questionnaire.what_are_you_looking_for)
async def process_what_are_you_looking_for(callback: CallbackQuery, state: FSMContext):
    """Process what are you looking for question."""
    user_choice = callback.data
    
    if user_choice.startswith("looking_"):
        choice_key = user_choice[8:]  # Remove "looking_" prefix
        choice = LOOKING_FOR_MAP.get(choice_key, choice_key)
        await state.update_data(what_are_you_looking_for=choice)
        
        # Move to direction selection
        await state.set_state(Questionnaire.direction)
        await callback.message.answer("3️⃣ Какое направление тебе ближе?\n"
                                    "Выбери одно из направлений:",
                                    reply_markup=get_direction_keyboard())
    else:
        await callback.answer("Пожалуйста, выберите один из вариантов.", show_alert=True)

# Process direction selection
@router.callback_query(Questionnaire.direction)
async def process_direction(callback: CallbackQuery, state: FSMContext):
    """Process direction selection."""
    user_choice = callback.data
    
    if user_choice.startswith("direction_"):
        choice_key = user_choice[10:]  # Remove "direction_" prefix
        choice = DIRECTION_MAP.get(choice_key, choice_key)
        await state.update_data(direction=choice)
        
        # Check if user selected "не знаю, помогите определить"
        if choice_key == "help_determine":
            # Ask clarifying questions
            await state.set_state(Questionnaire.clarifying_questions)
            await callback.message.answer("Хорошо, давай определим направление вместе!\n"
                                        "Ответь на несколько вопросов:")
            await ask_clarifying_question(callback.message, state, 0)
        else:
            # Continue with experience question
            await state.set_state(Questionnaire.experience)
            await callback.message.answer("4️⃣ Базовый опыт\n"
                                        "Выбери подходящий вариант:",
                                        reply_markup=get_experience_keyboard())
    else:
        await callback.answer("Пожалуйста, выберите одно из направлений.", show_alert=True)

# Clarifying questions logic
async def ask_clarifying_question(message: Message, state: FSMContext, question_index: int):
    """Ask clarifying questions to determine direction."""
    clarifying_questions = [
        "1. Тебе ближе работать с людьми, цифрами, текстами, визуалом или системами?",
        "2. Нравится больше анализировать, организовывать, продавать, создавать или поддерживать процессы?",
        "3. Тебе ближе креатив или структура?",
        "4. Комфортно ли тебе общаться с клиентами или командой?",
        "5. Интересно ли тебе работать с таблицами, данными, задачами, контентом, интерфейсами?"
    ]
    
    if question_index < len(clarifying_questions):
        await message.answer(clarifying_questions[question_index])
        # Store the question index to continue later
        await state.update_data(current_question_index=question_index)
    else:
        # Determine direction based on answers
        # For simplicity, we'll just assign a default direction here
        # In a real implementation, you'd analyze the answers
        await state.update_data(direction="IT / Продукт")
        await state.set_state(Questionnaire.experience)
        await message.answer("4️⃣ Базовый опыт\n"
                            "Выбери подходящий вариант:",
                            reply_markup=get_experience_keyboard())

# Process clarifying question answers
@router.message(Questionnaire.clarifying_questions)
async def process_clarifying_answer(message: Message, state: FSMContext):
    """Process clarifying question answers."""
    # Get current question index
    data = await state.get_data()
    current_index = data.get('current_question_index', 0)
    
    # Store the answer
    answers = data.get('clarifying_answers', [])
    answers.append(message.text)
    await state.update_data(clarifying_answers=answers)
    
    # Ask the next question
    current_index += 1
    await ask_clarifying_question(message, state, current_index)

# Process experience selection
@router.callback_query(Questionnaire.experience)
async def process_experience(callback: CallbackQuery, state: FSMContext):
    """Process experience selection."""
    user_choice = callback.data
    
    if user_choice.startswith("exp_"):
        choice_key = user_choice[4:]  # Remove "exp_" prefix
        choice = EXPERIENCE_MAP.get(choice_key, choice_key)
        await state.update_data(experience=choice)
        
        # Move to skills selection
        await state.set_state(Questionnaire.skills)
        # Get the selected direction to show relevant skills
        data = await state.get_data()
        direction = data.get('direction', 'IT / Продукт')
        await callback.message.answer("5️⃣ Навыки / инструменты\n"
                                    "Выбери подходящие навыки (можно выбрать несколько):",
                                    reply_markup=get_skills_keyboard(direction))
    else:
        await callback.answer("Пожалуйста, выберите один из вариантов.", show_alert=True)

# Process skills selection
@router.callback_query(Questionnaire.skills)
async def process_skills(callback: CallbackQuery, state: FSMContext):
    """Process skills selection."""
    user_choice = callback.data
    
    # Get current skills from state
    data = await state.get_data()
    current_skills = data.get('skills', [])
    
    # Handle skill selection
    if user_choice.startswith("skill_") and user_choice != "skill_done":
        data = await state.get_data()
        direction = data.get('direction', 'IT / Продукт')
        skills_keyboard = get_skills_keyboard(direction)
        skill = next(
            (
                btn.text
                for row in skills_keyboard.inline_keyboard
                for btn in row
                if btn.callback_data == user_choice
            ),
            user_choice[6:]
        )
        if skill not in current_skills:
            current_skills.append(skill)
        
        # Update state with new skills
        await state.update_data(skills=current_skills)
        
        # Show updated skills list
        await callback.answer(f"Добавлен навык: {skill}")
        
        # Show the skills keyboard again for more selections
        data = await state.get_data()
        direction = data.get('direction', 'IT / Продукт')
        await callback.message.edit_reply_markup(reply_markup=get_skills_keyboard(direction))
    elif user_choice == "skill_done":
        # User finished selecting skills
        await state.set_state(Questionnaire.resume_links)
        await callback.message.answer("6️⃣ Резюме / ссылки / портфолио\n"
                                    "Пришли ссылки на резюме, GitHub, LinkedIn и т.д. (можно оставить пустым)")
    else:
        await callback.answer("Пожалуйста, выберите навыки.", show_alert=True)

# Process resume links
@router.message(Questionnaire.resume_links)
async def process_resume_links(message: Message, state: FSMContext):
    """Process resume links."""
    resume_links = message.text.strip()
    await state.update_data(resume_links=resume_links)
    
    # Move to test questions
    await state.set_state(Questionnaire.test_questions)
    data = await state.get_data()
    direction = data.get('direction', 'IT / Продукт')
    await message.answer("7️⃣ Короткий тест по выбранному направлению\n"
                        f"Направление: {direction}\n"
                        "Ответь на несколько вопросов (можно пропустить):",
                        reply_markup=get_test_questions_keyboard())

# Process test questions
@router.callback_query(Questionnaire.test_questions)
async def process_test_questions(callback: CallbackQuery, state: FSMContext):
    """Process test questions."""
    user_choice = callback.data
    data = await state.get_data()
    direction = data.get('direction', 'IT / Продукт')
    questions = TEST_QUESTIONS_BY_DIRECTION.get(direction, TEST_QUESTIONS_BY_DIRECTION["IT / Продукт"])

    if user_choice == "test_skip":
        await state.update_data(test_answers="пропущено")
        await state.set_state(Questionnaire.work_style)
        await callback.message.answer(
            "8️⃣ Рабочий стиль\n"
            "Если задача непонятна, что ты обычно делаешь?\n"
            "Выбери подходящий вариант:",
            reply_markup=get_work_style_keyboard()
        )
        return

    if user_choice == "test_start":
        await state.update_data(
            test_questions_pool=questions,
            test_question_index=0,
            test_answers=[]
        )
        await callback.message.answer(
            f"Вопрос 1/{len(questions)}:\n{questions[0]}\n\n"
            "Напиши ответ текстом или отправь 'пропустить'."
        )
        return

    await callback.answer("Пожалуйста, выберите: пройти тест или пропустить.", show_alert=True)


@router.message(Questionnaire.test_questions)
async def process_test_answer(message: Message, state: FSMContext):
    """Process text answers for short test questions."""
    data = await state.get_data()
    questions = data.get('test_questions_pool')
    current_index = data.get('test_question_index', 0)

    if not questions:
        await message.answer("Нажми кнопку: 'Пройти тест' или 'Пропустить'.", reply_markup=get_test_questions_keyboard())
        return

    answers = data.get('test_answers', [])
    current_question = questions[current_index]
    text = (message.text or "").strip()
    answer = "пропущено" if text.lower() in {"пропустить", "skip", "-"} else text
    answers.append({"question": current_question, "answer": answer})

    next_index = current_index + 1
    if next_index < len(questions):
        await state.update_data(test_answers=answers, test_question_index=next_index)
        await message.answer(
            f"Вопрос {next_index + 1}/{len(questions)}:\n{questions[next_index]}\n\n"
            "Напиши ответ текстом или отправь 'пропустить'."
        )
        return

    formatted_answers = "\n".join(
        [f"{i + 1}. {item['question']} -> {item['answer']}" for i, item in enumerate(answers)]
    )
    await state.update_data(test_answers=formatted_answers)
    await state.set_state(Questionnaire.work_style)
    await message.answer(
        "8️⃣ Рабочий стиль\n"
        "Если задача непонятна, что ты обычно делаешь?\n"
        "Выбери подходящий вариант:",
        reply_markup=get_work_style_keyboard()
    )

# Process work style
@router.callback_query(Questionnaire.work_style)
async def process_work_style(callback: CallbackQuery, state: FSMContext):
    """Process work style selection."""
    user_choice = callback.data
    
    if user_choice.startswith("style_"):
        choice_key = user_choice[6:]  # Remove "style_" prefix
        choice = WORK_STYLE_MAP.get(choice_key, choice_key)
        await state.update_data(work_style=choice)
        
        # Move to contacts
        await state.set_state(Questionnaire.contacts)
        await state.update_data(contact_step="email")
        await callback.message.answer("9️⃣ Контакты и доступность\n"
                                    "Шаг 1/3. Укажи email:")
    else:
        await callback.answer("Пожалуйста, выберите один из вариантов.", show_alert=True)

# Process contacts
@router.message(Questionnaire.contacts)
async def process_contacts(message: Message, state: FSMContext):
    """Process contacts."""
    raw_value = (message.text or "").strip()
    data = await state.get_data()
    step = data.get("contact_step", "email")

    if step == "email":
        email = raw_value.lower()
        if not EMAIL_REGEX.fullmatch(email):
            await message.answer(
                "Некорректный email.\n"
                "Пример: example@mail.com\n"
                "Введи email ещё раз:"
            )
            return

        await state.update_data(contact_email=email, contact_step="phone")
        await message.answer("Шаг 2/3. Укажи телефон в формате +79991234567:")
        return

    if step == "phone":
        if not PHONE_REGEX.fullmatch(raw_value):
            await message.answer(
                "Некорректный телефон.\n"
                "Допустимые форматы: +79991234567, 89991234567, 79991234567\n"
                "Введи телефон ещё раз:"
            )
            return

        phone_digits = "".join(ch for ch in raw_value if ch.isdigit())
        if len(phone_digits) == 11 and phone_digits.startswith("8"):
            phone_digits = "7" + phone_digits[1:]
        phone = f"+{phone_digits}" if len(phone_digits) == 11 and phone_digits.startswith("7") else ""
        if not phone:
            await message.answer("Некорректный телефон. Введи в формате +79991234567:")
            return

        await state.update_data(contact_phone=phone, contact_step="telegram")
        await message.answer("Шаг 3/3. Укажи Telegram в формате @username или https://t.me/username:")
        return

    if step == "telegram":
        tg_match = TG_REGEX.fullmatch(raw_value)
        if not tg_match:
            await message.answer(
                "Некорректный Telegram username.\n"
                "Пример: @username или https://t.me/username\n"
                "Введи Telegram ещё раз:"
            )
            return

        telegram = f"@{tg_match.group(1)}"
        email = data.get("contact_email", "")
        phone = data.get("contact_phone", "")
        contacts = f"Email: {email}; Телефон: {phone}; Telegram: {telegram}"
        await state.update_data(contacts=contacts)

    else:
        await state.update_data(contact_step="email")
        await message.answer("Шаг 1/3. Укажи email:")
        return
    
    # Collect all data and save to database
    user_data = await state.get_data()
    user_data.update({
        'timestamp': datetime.now().isoformat(),
        'username': message.from_user.username or '',
        'first_name': message.from_user.first_name,
        'last_name': message.from_user.last_name,
        'status': 'новая анкета'
    })
    
    # Normalize complex fields before save to DB
    if isinstance(user_data.get('skills'), list):
        user_data['skills'] = ', '.join(user_data['skills'])
    if isinstance(user_data.get('clarifying_answers'), list):
        user_data['clarifying_answers'] = ' | '.join(user_data['clarifying_answers'])
    if isinstance(user_data.get('test_answers'), (list, dict)):
        user_data['test_answers'] = str(user_data['test_answers'])

    # Save to database
    candidate_id = save_candidate(user_data)
    
    # Calculate score and tags
    score, tags, level = calculate_score_and_tags(user_data)
    update_candidate_score(candidate_id, score, tags, level)
    
    # Update status
    update_candidate_status(candidate_id, 'анкета заполнена')
    
    # Send confirmation
    await message.answer("✅ Спасибо за заполнение анкеты!\n"
                        "Ваши данные были сохранены в нашей базе.\n\n"
                        "Если ваш опыт подойдет под актуальные вакансии, мы свяжемся с вами.\n"
                        "Также при необходимости вы сможете обновить информацию позже.",
                        reply_markup=get_confirmation_keyboard())
    
    # Clear state
    await state.clear()

def calculate_score_and_tags(data: Dict[str, Any]) -> tuple[int, str, str]:
    """Calculate candidate score, tags and level."""
    score = 0
    tags = []
    level = "без опыта"
    
    # Base score calculation
    skills = data.get('skills', [])
    if isinstance(skills, str):
        skills = [s.strip() for s in skills.split(',') if s.strip()]
    
    # Add points for skills
    skill_points = {
        'Python': 10, 'JavaScript': 10, 'HTML': 5, 'CSS': 5, 'SQL': 10,
        'Git': 8, 'API': 8, 'Figma': 8, 'Postman': 8, 'Google Analytics': 8,
        'Canva': 5, 'Яндекс Метрика': 8, 'Power BI': 10, 'Tableau': 10,
        'Excel': 5, 'Google Sheets': 5, 'CRM': 8, 'Notion': 8, 'Google Docs': 5
    }
    
    for skill in skills:
        skill = skill.lower()
        if skill in skill_points:
            score += skill_points[skill]
            tags.append(skill)
    
    # Level determination
    experience = data.get('experience', '').lower()
    if 'стажировка' in experience or 'фриланс' in experience:
        level = "стажер"
    elif 'коммерческий' in experience or '1-2' in experience:
        level = "начинающий специалист"
    
    # Add experience points
    if 'стажировка' in experience:
        score += 15
    elif 'фриланс' in experience:
        score += 20
    elif 'коммерческий' in experience or '1-2' in experience:
        score += 25
    elif 'курсы' in experience:
        score += 10
    
    # Add direction points
    direction = data.get('direction', '').lower()
    if 'it' in direction or 'продукт' in direction:
        score += 15
        tags.append('IT')
    elif 'digital' in direction or 'маркетинг' in direction or 'дизайн' in direction:
        score += 10
        tags.append('Digital')
    elif 'бизнес' in direction or 'операции' in direction:
        score += 8
        tags.append('Бизнес')
    
    return score, ','.join(tags), level
