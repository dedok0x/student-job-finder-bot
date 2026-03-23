import re
import os
from datetime import datetime
from typing import Any, Dict, List

from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from database import (
    has_completed_questionnaire,
    save_candidate,
    update_candidate_score,
    update_candidate_status,
    update_latest_candidate_resume,
)
from keyboards.for_questions import (
    get_confirmation_keyboard,
    get_contact_request_keyboard,
    get_direction_keyboard,
    get_experience_keyboard,
    get_short_assessment_keyboard,
    get_skills_keyboard,
    get_test_questions_keyboard,
    get_who_are_you_keyboard,
    get_work_style_keyboard,
    get_what_are_you_looking_for_keyboard,
    get_yes_no_keyboard,
)

router = Router()


class Questionnaire(StatesGroup):
    candidate_name = State()
    age = State()
    who_are_you = State()
    what_are_you_looking_for = State()
    direction = State()
    clarifying_questions = State()
    salary_expectations = State()
    experience = State()
    skills = State()
    resume_links = State()
    add_more_decision = State()
    add_more_text = State()
    test_questions = State()
    work_style = State()
    short_assessment = State()
    contacts = State()
    menu_upload_resume = State()


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
    "information_technology": "информационные технологии",
    "marketing": "маркетинг",
    "design": "дизайн",
    "analytics": "аналитика",
    "sales": "продажи",
    "customer_support": "клиентская поддержка",
    "assistant": "ассистент",
    "operations": "операционная деятельность",
    "recruitment": "подбор персонала",
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

SHORT_ASSESSMENT = [
    {
        "key": "multi_task_style",
        "question": "Если у тебя много мелких задач одновременно, как ты обычно действуешь?",
        "options": [
            ("prioritize_record", "записываю и расставляю по приоритету"),
            ("urgent_first", "делаю по очереди то, что срочнее"),
            ("easy_first", "беру то, что кажется проще"),
            ("confused_no_list", "могу запутаться без четкого списка"),
        ],
    },
    {
        "key": "unknown_task_action",
        "question": "Если ты не знаешь, как сделать задачу, что ты делаешь?",
        "options": [
            ("search_self", "ищу информацию сам"),
            ("ask_colleague", "спрашиваю коллегу или руководителя"),
            ("try_variants", "пробую несколько вариантов"),
            ("wait_instruction", "жду более подробную инструкцию"),
        ],
    },
    {
        "key": "work_preference",
        "question": "Что тебе ближе в работе?",
        "options": [
            ("clear_tasks", "четкие задачи и понятный порядок"),
            ("switch_tasks", "разные задачи и переключение"),
            ("communication", "общение с людьми"),
            ("data_text_tables", "работа с данными, текстами или таблицами"),
        ],
    },
    {
        "key": "work_start_priority",
        "question": "Что для тебя важнее в начале работы?",
        "options": [
            ("speed", "сделать быстро"),
            ("accuracy", "сделать аккуратно"),
            ("clarify_first", "сначала все уточнить"),
            ("example_first", "сначала посмотреть пример"),
        ],
    },
]

TEST_QUESTIONS_BY_DIRECTION = {
    "информационные технологии": [
        "Представь задачу: нужно получить данные из API и сохранить в таблицу. Какой план действий?",
        "Есть баг: страница открывается, но кнопка не работает. Что проверишь в первую очередь?",
        "Как объяснишь на простом языке разницу между фронтендом и бэкендом?",
    ],
    "маркетинг": [
        "Тебе дали бюджет 30 000 ₽ на запуск. Какие 3 шага сделаешь перед стартом рекламы?",
        "По рекламе высокий охват, но мало заявок. Какие гипотезы проверишь?",
        "Какие 3 метрики считаешь ключевыми для оценки эффективности кампании?",
    ],
    "дизайн": [
        "Тебе дали задачу сделать лендинг за 1 день. Как расставишь приоритеты?",
        "Как проверишь, что твой дизайн понятен пользователю без дополнительных пояснений?",
        "Какой набор артефактов ты обычно готовишь: wireframe, прототип, UI-kit — и зачем?",
    ],
    "аналитика": [
        "Тебе дали сырые данные по продажам. Какие первые шаги в анализе?",
        "Как обнаружишь аномалии в отчете и проверишь, что это не ошибка данных?",
        "Какие визуализации ты выберешь для динамики, структуры и сравнения категорий?",
    ],
    "продажи": [
        "Клиент говорит «дорого». Какой сценарий ответа используешь?",
        "Лид оставил заявку, но не отвечает. Как выстроишь цепочку касаний?",
        "Какие поля обязательно фиксируешь в CRM после звонка?",
    ],
    "клиентская поддержка": [
        "Как обработаешь обращение, если клиент пишет эмоционально и на повышенных тонах?",
        "Что сделаешь, если по одному вопросу одновременно пишет много пользователей?",
        "Как оценишь качество своей поддержки за неделю?",
    ],
    "ассистент": [
        "Руководитель просит срочно подготовить встречу через 2 часа. Твои действия по шагам?",
        "Как ведешь приоритеты, когда задач много и часть из них без дедлайна?",
        "Как организуешь хранение документов, чтобы команда быстро находила нужное?",
    ],
    "операционная деятельность": [
        "Процесс регулярно срывает сроки. Как найдешь причину и предложишь решение?",
        "Какие показатели будешь отслеживать, чтобы видеть стабильность операционных процессов?",
        "Как внедришь новый регламент так, чтобы команда реально начала его соблюдать?",
    ],
    "подбор персонала": [
        "По каким критериям быстро отсеиваешь нерелевантные резюме?",
        "Какие вопросы задашь на первичном интервью, чтобы проверить мотивацию кандидата?",
        "Как организуешь воронку подбора, чтобы не терять кандидатов между этапами?",
    ],
}

SKILL_CLARIFY_DIRECTION_HINTS = {
    "информационные технологии": ["python", "sql", "api", "git", "код", "программ"],
    "маркетинг": ["реклама", "контент", "соц", "таргет", "метрика"],
    "дизайн": ["figma", "photoshop", "ux", "ui", "баннер", "дизайн"],
    "аналитика": ["excel", "tableau", "power bi", "данн", "аналит"],
    "продажи": ["продаж", "переговор", "лид", "возраж"],
    "клиентская поддержка": ["поддержк", "чат", "жалоб", "обращени"],
    "ассистент": ["календар", "встреч", "ассист", "документ"],
    "операционная деятельность": ["операц", "процесс", "срок", "координац"],
    "подбор персонала": ["кандидат", "рекрут", "интервью", "hh", "linkedin"],
}

EMAIL_REGEX = re.compile(r"(?i)^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$")
PHONE_REGEX = re.compile(r"^(?:\+7|7|8)?[\s\-()]*\d(?:[\s\-()]*\d){9,10}$")
GREETING_WORDS = {"привет", "здарова", "здравствуйте", "добрый", "хай", "чё", "че", "как", "hello", "hi"}
MANAGER_MENU_TEXTS = {
    "👥 Последние кандидаты",
    "📊 Общая статистика",
    "🔎 Поиск по имени",
    "📤 Экспорт CSV",
    "📄 Открыть Google таблицу",
    "🚪 Выйти из панели менеджера"
}
RESUME_FORWARD_TARGET_CHAT_ID = "1038860577"


def is_greeting_or_generic(text: str) -> bool:
    normalized = (text or "").strip().lower()
    if not normalized:
        return True
    if normalized.startswith("/"):
        return False
    return any(token in normalized for token in GREETING_WORDS) or len(normalized) < 3


def build_tg_resume_ref(message: Message) -> tuple[str, str]:
    file_id = ""
    if message.document:
        file_id = message.document.file_id
    elif message.photo:
        file_id = message.photo[-1].file_id

    chat_id = message.chat.id
    if str(chat_id).startswith("-100"):
        message_link = f"https://t.me/c/{str(chat_id)[4:]}/{message.message_id}"
    else:
        message_link = f"tg://message?chat_id={chat_id}&message_id={message.message_id}"
    return file_id, message_link


def build_resume_forward_api_link(message: Message) -> str:
    token = os.getenv("BOT_TOKEN", "")
    if not token:
        return ""

    return (
        f"https://api.telegram.org/bot{token}/forwardMessage"
        f"?chat_id={RESUME_FORWARD_TARGET_CHAT_ID}"
        f"&from_chat_id={message.chat.id}"
        f"&message_id={message.message_id}"
    )


def normalize_resume_from_message(message: Message) -> tuple[str, str, str] | None:
    if message.document:
        mime = (message.document.mime_type or "").lower()
        filename = (message.document.file_name or "").lower()
        is_pdf = mime == "application/pdf" or filename.endswith(".pdf")
        is_png = mime == "image/png" or filename.endswith(".png")
        if not (is_pdf or is_png):
            return None
        file_id, message_link = build_tg_resume_ref(message)
        forward_link = build_resume_forward_api_link(message)
        return forward_link or f"telegram_cloud:{message_link}", file_id, message_link

    if message.photo:
        file_id, message_link = build_tg_resume_ref(message)
        forward_link = build_resume_forward_api_link(message)
        return forward_link or f"telegram_cloud:{message_link}", file_id, message_link

    if message.text:
        return message.text.strip(), "", ""

    return None


async def ask_first_question(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(Questionnaire.candidate_name)
    await message.answer(
        "👋 Привет! Я помогу быстро собрать анкету для подбора вакансий.\n"
        "1️⃣ Введи ниже своё ФИО.",
        reply_markup=ReplyKeyboardRemove(),
    )


async def show_main_menu(message: Message) -> None:
    await message.answer("📌 У тебя уже есть заполненная анкета. Выбери действие:", reply_markup=get_confirmation_keyboard())


async def start_flow_or_menu(message: Message, state: FSMContext) -> None:
    if not message.from_user:
        return

    if has_completed_questionnaire(message.from_user.id, message.chat.id):
        await state.clear()
        await show_main_menu(message)
        return

    await ask_first_question(message, state)


@router.message(Command(commands=["start", "help"]))
async def start_questionnaire(message: Message, state: FSMContext):
    await start_flow_or_menu(message, state)


@router.callback_query(lambda c: c.data == "update_profile")
async def menu_update_profile(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    if callback.message:
        await callback.message.answer("Обновляем анкету 👇")
        await ask_first_question(callback.message, state)


@router.callback_query(lambda c: c.data == "upload_resume")
async def menu_upload_resume(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(Questionnaire.menu_upload_resume)
    if callback.message:
        await callback.message.answer(
            "Пришли новое резюме в PDF/PNG, фото или ссылку.\n"
            "Также можно отправить GitHub или LinkedIn."
        )


@router.callback_query(lambda c: c.data == "contact_manager")
async def menu_contact_manager(callback: CallbackQuery):
    await callback.answer()
    if callback.message:
        await callback.message.answer("Для связи с менеджером: @SJIONIK")


@router.message(Questionnaire.menu_upload_resume)
async def process_menu_resume_upload(message: Message, state: FSMContext):
    if not message.from_user:
        return

    normalized = normalize_resume_from_message(message)
    if not normalized:
        await message.answer("Поддерживаются PDF/PNG, фото или текстовая ссылка. Отправь файл заново.")
        return

    resume_links, resume_file_id, resume_message_link = normalized
    ok = update_latest_candidate_resume(
        tg_user_id=message.from_user.id,
        tg_chat_id=message.chat.id,
        resume_links=resume_links,
        resume_file_id=resume_file_id,
        resume_message_link=resume_message_link,
    )
    await state.clear()
    if ok:
        await message.answer("✅ Новое резюме сохранено.", reply_markup=get_confirmation_keyboard())
    else:
        await message.answer("Анкета не найдена. Сначала заполни анкету.", reply_markup=get_confirmation_keyboard())


@router.message(Questionnaire.candidate_name)
async def process_candidate_name(message: Message, state: FSMContext):
    name = (message.text or "").strip()
    if len(name) < 2:
        await message.answer("Введи имя текстом (минимум 2 символа).")
        return
    await state.update_data(candidate_name=name)
    await state.set_state(Questionnaire.age)
    await message.answer("2️⃣ Сколько тебе лет?")


@router.message(Questionnaire.age)
async def process_age(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if not text.isdigit():
        await message.answer("Укажи возраст числом, например: 21")
        return
    age = int(text)
    if age < 14 or age > 80:
        await message.answer("Укажи корректный возраст (14-80).")
        return
    await state.update_data(age=age)
    await state.set_state(Questionnaire.who_are_you)
    await message.answer(
        "3️⃣ Кто ты?\n"
        "студент / выпускник / начинающий специалист / меняю профессию",
        reply_markup=get_who_are_you_keyboard(),
    )


@router.callback_query(Questionnaire.who_are_you)
async def process_who_are_you(callback: CallbackQuery, state: FSMContext):
    data = callback.data or ""
    if not data.startswith("who_"):
        await callback.answer("Выбери один из вариантов", show_alert=True)
        return
    choice_key = data[4:]
    await state.update_data(who_are_you=WHO_ARE_YOU_MAP.get(choice_key, choice_key))
    await state.set_state(Questionnaire.what_are_you_looking_for)
    await callback.message.answer(
        "4️⃣ Что ищешь?\n"
        "стажировка / частичная занятость / полная занятость / проектная работа",
        reply_markup=get_what_are_you_looking_for_keyboard(),
    )
    await callback.answer()


@router.callback_query(Questionnaire.what_are_you_looking_for)
async def process_looking_for(callback: CallbackQuery, state: FSMContext):
    data = callback.data or ""
    if not data.startswith("looking_"):
        await callback.answer("Выбери один из вариантов", show_alert=True)
        return
    choice_key = data[8:]
    await state.update_data(what_are_you_looking_for=LOOKING_FOR_MAP.get(choice_key, choice_key))
    await state.set_state(Questionnaire.direction)
    await callback.message.answer(
        "5️⃣ Какое направление тебе ближе?",
        reply_markup=get_direction_keyboard(),
    )
    await callback.answer()


async def ask_clarifying_question(message: Message, state: FSMContext, index: int) -> None:
    questions = [
        "1) Тебе ближе люди, цифры, тексты, визуал или системы?",
        "2) Что интереснее: продавать, анализировать, поддерживать клиентов, организовывать или разрабатывать?",
        "3) Что больше нравится: креативные задачи или структурные процессы?",
        "4) Комфортно ли много общаться с клиентами/кандидатами?",
        "5) Какие инструменты уже пробовал(а): таблицы, CRM, Figma, код, реклама?",
    ]
    if index < len(questions):
        await state.update_data(current_question_index=index)
        await message.answer(questions[index])
        return

    user_data = await state.get_data()
    answers = " ".join(user_data.get("clarifying_answers", [])).lower()
    picked = "операционная деятельность"
    best = -1
    for direction, hints in SKILL_CLARIFY_DIRECTION_HINTS.items():
        score = sum(1 for hint in hints if hint in answers)
        if score > best:
            best = score
            picked = direction

    await state.update_data(direction=picked)
    await state.set_state(Questionnaire.salary_expectations)
    await message.answer(f"Похоже, тебе ближе направление: {picked}")
    await message.answer("6️⃣ Какие зарплатные ожидания? (например: 60 000 ₽)")


@router.callback_query(Questionnaire.direction)
async def process_direction(callback: CallbackQuery, state: FSMContext):
    data = callback.data or ""
    if not data.startswith("direction_"):
        await callback.answer("Выбери одно из направлений", show_alert=True)
        return

    key = data[10:]
    direction = DIRECTION_MAP.get(key, key)
    await state.update_data(direction=direction)

    if key == "help_determine":
        await state.set_state(Questionnaire.clarifying_questions)
        await callback.message.answer("Помогу определить направление. Ответь на 5 коротких вопросов:")
        await ask_clarifying_question(callback.message, state, 0)
    else:
        await state.set_state(Questionnaire.salary_expectations)
        await callback.message.answer("6️⃣ Какие зарплатные ожидания? (например: 60 000 ₽)")
    await callback.answer()


@router.message(Questionnaire.clarifying_questions)
async def process_clarifying_answer(message: Message, state: FSMContext):
    data = await state.get_data()
    answers = data.get("clarifying_answers", [])
    answers.append((message.text or "").strip())
    await state.update_data(clarifying_answers=answers)
    await ask_clarifying_question(message, state, data.get("current_question_index", 0) + 1)


@router.message(Questionnaire.salary_expectations)
async def process_salary(message: Message, state: FSMContext):
    salary = (message.text or "").strip()
    if len(salary) < 2:
        await message.answer("Укажи ожидания текстом, например: 60 000 ₽")
        return
    await state.update_data(salary_expectations=salary)
    await state.set_state(Questionnaire.experience)
    await message.answer("7️⃣ Какой у тебя текущий опыт?", reply_markup=get_experience_keyboard())


@router.callback_query(Questionnaire.experience)
async def process_experience(callback: CallbackQuery, state: FSMContext):
    data = callback.data or ""
    if not data.startswith("exp_"):
        await callback.answer("Выбери один вариант", show_alert=True)
        return

    await state.update_data(experience=EXPERIENCE_MAP.get(data[4:], data[4:]))
    direction = (await state.get_data()).get("direction", "информационные технологии")
    await state.set_state(Questionnaire.skills)
    await callback.message.answer(
        "8️⃣ Отметь навыки и инструменты, с которыми уже работал(а).\n"
        "Можно выбрать несколько вариантов и нажать «Готово».",
        reply_markup=get_skills_keyboard(direction),
    )
    await callback.answer()


@router.callback_query(Questionnaire.skills)
async def process_skills(callback: CallbackQuery, state: FSMContext):
    data = callback.data or ""
    state_data = await state.get_data()
    selected = state_data.get("skills", [])

    if data.startswith("skill_") and data != "skill_done":
        direction = state_data.get("direction", "информационные технологии")
        kb = get_skills_keyboard(direction)
        skill = next((btn.text for row in kb.inline_keyboard for btn in row if btn.callback_data == data), data[6:])
        if skill not in selected:
            selected.append(skill)
            await state.update_data(skills=selected)
            await callback.answer(f"Добавлено: {skill}")
        else:
            await callback.answer("Уже выбрано")
        return

    if data == "skill_done":
        await state.set_state(Questionnaire.resume_links)
        await callback.message.answer(
            "9️⃣ Загрузка резюме\n"
            "Отправь PDF/PNG, фото или текстовую ссылку на резюме/портфолио.\n"
            "Также можно указать GitHub или LinkedIn."
        )
        await callback.answer()
        return

    await callback.answer("Выбери навык или нажми «Готово»", show_alert=True)


@router.message(Questionnaire.resume_links)
async def process_resume_links(message: Message, state: FSMContext):
    normalized = normalize_resume_from_message(message)
    if not normalized:
        await message.answer("Поддерживаются PDF/PNG, фото или текстовая ссылка. Отправь корректный формат.")
        return

    resume_links, resume_file_id, resume_message_link = normalized
    await state.update_data(
        resume_links=resume_links,
        resume_file_id=resume_file_id,
        resume_message_link=resume_message_link,
    )
    await state.set_state(Questionnaire.add_more_decision)
    await message.answer("Хочешь добавить что-то ещё к анкете?", reply_markup=get_yes_no_keyboard("add"))


@router.callback_query(Questionnaire.add_more_decision)
async def process_add_more_decision(callback: CallbackQuery, state: FSMContext):
    data = callback.data or ""
    if data == "add_yes":
        await state.set_state(Questionnaire.add_more_text)
        await callback.message.answer("Напиши дополнительную информацию одним сообщением.")
        await callback.answer()
        return

    if data == "add_no":
        await state.update_data(additional_info="")
        await state.set_state(Questionnaire.test_questions)
        direction = (await state.get_data()).get("direction", "информационные технологии")
        await callback.message.answer(
            f"🔟 Мини-тест по направлению: {direction}\n"
            "Нажми «Пройти тест» или «Пропустить».",
            reply_markup=get_test_questions_keyboard(),
        )
        await callback.answer()
        return

    await callback.answer("Выбери: да или нет", show_alert=True)


@router.message(Questionnaire.add_more_text)
async def process_add_more_text(message: Message, state: FSMContext):
    await state.update_data(additional_info=(message.text or "").strip())
    await state.set_state(Questionnaire.test_questions)
    direction = (await state.get_data()).get("direction", "информационные технологии")
    await message.answer(
        f"🔟 Мини-тест по направлению: {direction}\n"
        "Нажми «Пройти тест» или «Пропустить».",
        reply_markup=get_test_questions_keyboard(),
    )


@router.callback_query(Questionnaire.test_questions)
async def process_test_questions(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    direction = data.get("direction", "информационные технологии")
    questions = TEST_QUESTIONS_BY_DIRECTION.get(direction, TEST_QUESTIONS_BY_DIRECTION["информационные технологии"])
    choice = callback.data or ""

    if choice == "test_skip":
        await state.update_data(test_answers="пропущено")
        await state.set_state(Questionnaire.work_style)
        await callback.message.answer(
            "1️⃣1️⃣ Какой у тебя рабочий стиль?\n"
            "Если задача сформулирована не до конца, как ты обычно действуешь?",
            reply_markup=get_work_style_keyboard(),
        )
        await callback.answer()
        return

    if choice == "test_start":
        await state.update_data(test_questions_pool=questions, test_question_index=0, test_answers=[])
        await callback.message.answer(f"Вопрос 1/{len(questions)}:\n{questions[0]}\n\nОтветь текстом или напиши «пропустить».")
        await callback.answer()
        return

    await callback.answer("Выбери: пройти тест или пропустить", show_alert=True)


@router.message(Questionnaire.test_questions)
async def process_test_answer(message: Message, state: FSMContext):
    data = await state.get_data()
    questions = data.get("test_questions_pool")
    idx = data.get("test_question_index", 0)
    if not questions:
        await message.answer("Нажми кнопку: «Пройти тест» или «Пропустить».", reply_markup=get_test_questions_keyboard())
        return

    answers = data.get("test_answers", [])
    txt = (message.text or "").strip()
    answer = "пропущено" if txt.lower() in {"пропустить", "skip", "-"} else txt
    answers.append({"question": questions[idx], "answer": answer})

    next_idx = idx + 1
    if next_idx < len(questions):
        await state.update_data(test_answers=answers, test_question_index=next_idx)
        await message.answer(f"Вопрос {next_idx + 1}/{len(questions)}:\n{questions[next_idx]}\n\nОтветь текстом или напиши «пропустить».")
        return

    formatted = "\n".join([f"{i + 1}. {item['question']} -> {item['answer']}" for i, item in enumerate(answers)])
    await state.update_data(test_answers=formatted)
    await state.set_state(Questionnaire.work_style)
    await message.answer(
        "1️⃣1️⃣ Какой у тебя рабочий стиль?\n"
        "Если задача сформулирована не до конца, как ты обычно действуешь?",
        reply_markup=get_work_style_keyboard(),
    )


@router.callback_query(Questionnaire.work_style)
async def process_work_style(callback: CallbackQuery, state: FSMContext):
    data = callback.data or ""
    if not data.startswith("style_"):
        await callback.answer("Выбери вариант", show_alert=True)
        return

    await state.update_data(work_style=WORK_STYLE_MAP.get(data[6:], data[6:]))
    await state.update_data(short_assessment_index=0)
    await state.set_state(Questionnaire.short_assessment)
    first = SHORT_ASSESSMENT[0]
    await callback.message.answer(
        first["question"],
        reply_markup=get_short_assessment_keyboard(first["options"], prefix="sa0"),
    )
    await callback.answer()


@router.callback_query(Questionnaire.short_assessment)
async def process_short_assessment(callback: CallbackQuery, state: FSMContext):
    payload = callback.data or ""
    state_data = await state.get_data()
    index = int(state_data.get("short_assessment_index", 0))

    if not payload.startswith(f"sa{index}_"):
        await callback.answer("Выбери один из вариантов", show_alert=True)
        return

    selected_key = payload.replace(f"sa{index}_", "", 1)
    cfg = SHORT_ASSESSMENT[index]
    selected_text = next((text for key, text in cfg["options"] if key == selected_key), "")
    await state.update_data(**{cfg["key"]: selected_text})

    next_index = index + 1
    if next_index < len(SHORT_ASSESSMENT):
        next_cfg = SHORT_ASSESSMENT[next_index]
        await state.update_data(short_assessment_index=next_index)
        await callback.message.answer(
            next_cfg["question"],
            reply_markup=get_short_assessment_keyboard(next_cfg["options"], prefix=f"sa{next_index}"),
        )
        await callback.answer()
        return

    await state.set_state(Questionnaire.contacts)
    await state.update_data(contact_step="email")
    await callback.message.answer("1️⃣2️⃣ Контакты\nШаг 1/2: укажи email")
    await callback.answer()


@router.message(Questionnaire.contacts)
async def process_contacts(message: Message, state: FSMContext):
    data = await state.get_data()
    step = data.get("contact_step", "email")

    if step == "email":
        email = (message.text or "").strip().lower()
        if not EMAIL_REGEX.fullmatch(email):
            await message.answer("Некорректный email. Пример: example@mail.com")
            return
        await state.update_data(contact_email=email, contact_step="phone")
        await message.answer(
            "Шаг 2/2: отправь номер кнопкой ниже или введи вручную в формате +79991234567",
            reply_markup=get_contact_request_keyboard(),
        )
        return

    phone = ""
    if message.contact and message.contact.phone_number:
        digits = "".join(ch for ch in message.contact.phone_number if ch.isdigit())
        if len(digits) == 11 and digits.startswith("8"):
            digits = "7" + digits[1:]
        phone = f"+{digits}" if len(digits) == 11 and digits.startswith("7") else ""
    else:
        raw = (message.text or "").strip()
        if raw == "Пропустить и ввести вручную":
            await message.answer("Введи телефон в формате +79991234567")
            return
        if PHONE_REGEX.fullmatch(raw):
            digits = "".join(ch for ch in raw if ch.isdigit())
            if len(digits) == 11 and digits.startswith("8"):
                digits = "7" + digits[1:]
            phone = f"+{digits}" if len(digits) == 11 and digits.startswith("7") else ""

    if not phone:
        await message.answer("Некорректный телефон. Отправь контакт кнопкой или введи вручную в формате +79991234567")
        return

    contacts = f"Email: {data.get('contact_email', '')}; Телефон: {phone}"
    await state.update_data(contacts=contacts)

    user_data = await state.get_data()
    user_data.update(
        {
            "timestamp": datetime.now().isoformat(),
            "username": message.from_user.username or "",
            "first_name": message.from_user.first_name or "",
            "last_name": message.from_user.last_name or "",
            "tg_user_id": message.from_user.id,
            "tg_chat_id": message.chat.id,
            "status": "новая анкета",
        }
    )

    if isinstance(user_data.get("skills"), list):
        user_data["skills"] = ", ".join(user_data["skills"])
    if isinstance(user_data.get("clarifying_answers"), list):
        user_data["clarifying_answers"] = " | ".join(user_data["clarifying_answers"])
    if isinstance(user_data.get("test_answers"), (list, dict)):
        user_data["test_answers"] = str(user_data["test_answers"])

    candidate_id = save_candidate(user_data)
    score, tags, level = calculate_score_and_tags(user_data)
    update_candidate_score(candidate_id, score, tags, level)
    update_candidate_status(candidate_id, "анкета заполнена")

    await message.answer(
        "✅ Спасибо! Анкета сохранена.\n"
        "Если профиль подойдет под текущие вакансии, мы свяжемся с тобой.",
        reply_markup=ReplyKeyboardRemove(),
    )
    await message.answer("Доступные действия:", reply_markup=get_confirmation_keyboard())
    await state.clear()


def calculate_score_and_tags(data: Dict[str, Any]) -> tuple[int, str, str]:
    score = 0
    tags: List[str] = []
    level = "без опыта"

    skills = data.get("skills", [])
    if isinstance(skills, str):
        skills = [s.strip() for s in skills.split(",") if s.strip()]

    skill_points = {
        "python": 10,
        "javascript": 10,
        "html": 5,
        "css": 5,
        "sql": 10,
        "git": 8,
        "api": 8,
        "figma": 8,
        "postman": 8,
        "google analytics": 8,
        "canva": 5,
        "яндекс метрика": 8,
        "power bi": 10,
        "tableau": 10,
        "excel": 5,
        "google sheets": 5,
        "crm": 8,
        "notion": 8,
        "google docs": 5,
    }
    for skill in skills:
        key = skill.lower()
        if key in skill_points:
            score += skill_points[key]
            tags.append(skill)

    experience = data.get("experience", "").lower()
    if "стажировка" in experience or "фриланс" in experience:
        level = "стажер"
    elif "коммерческий" in experience or "1-2" in experience:
        level = "начинающий специалист"

    if "стажировка" in experience:
        score += 15
    elif "фриланс" in experience:
        score += 20
    elif "коммерческий" in experience or "1-2" in experience:
        score += 25
    elif "курсы" in experience:
        score += 10

    direction = data.get("direction", "").lower()
    if "информационные технологии" in direction:
        score += 15
        tags.append("IT")
    elif "маркетинг" in direction:
        score += 10
        tags.append("Маркетинг")
    elif "дизайн" in direction:
        score += 10
        tags.append("Дизайн")
    elif "аналитика" in direction:
        score += 12
        tags.append("Аналитика")
    elif "продажи" in direction:
        score += 8
        tags.append("Продажи")
    elif "клиентская поддержка" in direction:
        score += 7
        tags.append("Поддержка")
    elif "ассистент" in direction:
        score += 7
        tags.append("Ассистент")
    elif "операционная деятельность" in direction:
        score += 8
        tags.append("Операции")
    elif "подбор персонала" in direction:
        score += 8
        tags.append("HR")

    return score, ",".join(tags), level


@router.message(StateFilter(None), ~F.text.startswith("/"), lambda m: is_greeting_or_generic((m.text or "").strip()))
async def fallback_entrypoint(message: Message, state: FSMContext):
    await start_flow_or_menu(message, state)


@router.message(
    StateFilter(None),
    ~F.text.startswith("/"),
    lambda m: (m.text or "").strip() not in MANAGER_MENU_TEXTS,
    lambda m: not is_greeting_or_generic((m.text or "").strip()),
)
async def fallback_start_hint(message: Message):
    await message.answer("Для продолжения напишите /start")

