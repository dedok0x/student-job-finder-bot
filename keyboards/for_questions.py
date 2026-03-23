from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton

def get_who_are_you_keyboard() -> InlineKeyboardMarkup:
    """Return keyboard for 'Who are you' question."""
    buttons = [
        [InlineKeyboardButton(text="студент", callback_data="who_student")],
        [InlineKeyboardButton(text="выпускник", callback_data="who_graduate")],
        [InlineKeyboardButton(text="начинающий специалист", callback_data="who_beginner_specialist")],
        [InlineKeyboardButton(text="меняю профессию", callback_data="who_change_profession")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_what_are_you_looking_for_keyboard() -> InlineKeyboardMarkup:
    """Return keyboard for 'What are you looking for' question."""
    buttons = [
        [InlineKeyboardButton(text="стажировка", callback_data="looking_internship")],
        [InlineKeyboardButton(text="частичная занятость", callback_data="looking_part_time")],
        [InlineKeyboardButton(text="полная занятость", callback_data="looking_full_time")],
        [InlineKeyboardButton(text="проектная работа", callback_data="looking_project")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_direction_keyboard() -> InlineKeyboardMarkup:
    """Return keyboard for direction selection."""
    buttons = [
        [InlineKeyboardButton(text="информационные технологии", callback_data="direction_information_technology")],
        [InlineKeyboardButton(text="маркетинг", callback_data="direction_marketing")],
        [InlineKeyboardButton(text="дизайн", callback_data="direction_design")],
        [InlineKeyboardButton(text="аналитика", callback_data="direction_analytics")],
        [InlineKeyboardButton(text="продажи", callback_data="direction_sales")],
        [InlineKeyboardButton(text="клиентская поддержка", callback_data="direction_customer_support")],
        [InlineKeyboardButton(text="ассистент", callback_data="direction_assistant")],
        [InlineKeyboardButton(text="операционная деятельность", callback_data="direction_operations")],
        [InlineKeyboardButton(text="подбор персонала", callback_data="direction_recruitment")],
        [InlineKeyboardButton(text="не знаю, помогите определить", callback_data="direction_help_determine")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_experience_keyboard() -> InlineKeyboardMarkup:
    """Return keyboard for experience selection."""
    buttons = [
        [InlineKeyboardButton(text="нет опыта", callback_data="exp_no_experience")],
        [InlineKeyboardButton(text="стажировка", callback_data="exp_internship")],
        [InlineKeyboardButton(text="курсы", callback_data="exp_courses")],
        [InlineKeyboardButton(text="учебные проекты", callback_data="exp_educational_projects")],
        [InlineKeyboardButton(text="фриланс", callback_data="exp_freelance")],
        [InlineKeyboardButton(text="коммерческий опыт до 1 года", callback_data="exp_commercial_up_to_1_year")],
        [InlineKeyboardButton(text="1-2 года", callback_data="exp_1_2_years")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_skills_keyboard(direction: str) -> InlineKeyboardMarkup:
    """Return keyboard for skills selection based on direction."""
    # Define skills by direction
    skills_by_direction = {
        "информационные технологии": [
            "Python", "JavaScript", "HTML", "CSS", "SQL", "Git", "API", "тестирование", "Figma", "Postman"
        ],
        "маркетинг": [
            "ведение социальных сетей", "таргетированная реклама", "контент", "тексты", "Canva",
            "Google Analytics", "Яндекс Метрика", "рекламный кабинет", "рассылки", "Tilda"
        ],
        "дизайн": [
            "Figma", "Photoshop", "Illustrator", "Canva", "дизайн интерфейсов", "пользовательский опыт",
            "баннеры", "презентации", "прототипирование"
        ],
        "аналитика": [
            "Excel", "Google Sheets", "SQL", "Power BI", "Tableau", "Python", "визуализация данных", "отчеты"
        ],
        "продажи": [
            "CRM", "работа с заявками", "переговоры", "обработка обращений", "холодные сообщения",
            "сопровождение клиентов", "работа с возражениями"
        ],
        "клиентская поддержка": [
            "общение с клиентами", "обработка обращений", "ответы в чатах", "ответы по почте", "CRM",
            "решение типовых вопросов", "работа с жалобами", "сбор обратной связи", "Notion", "Google Docs"
        ],
        "ассистент": [
            "ведение календаря", "поиск информации", "организация встреч", "напоминания", "работа с документами",
            "таблицы", "презентации", "Google Docs", "Google Sheets", "Notion", "координация задач", "переписка"
        ],
        "операционная деятельность": [
            "таблицы", "отчеты", "контроль сроков", "координация команды", "постановка задач", "контроль выполнения",
            "работа с CRM", "документооборот", "описание процессов", "оптимизация процессов", "сбор данных"
        ],
        "подбор персонала": [
            "поиск кандидатов", "разбор резюме", "проведение первичного интервью", "оценка кандидатов", "ведение базы",
            "переписка с кандидатами", "публикация вакансий", "работа с HH", "LinkedIn", "Google Sheets", "Notion", "CRM"
        ]
    }
    
    # Get skills for the selected direction
    skills = skills_by_direction.get(direction, [])
    
    # Create buttons for skills
    buttons = []
    for skill in skills:
        # Преобразуем название навыка в безопасный callback_data
        safe_skill = skill.lower().replace(' ', '_').replace('/', '_').replace('-', '_')
        buttons.append([InlineKeyboardButton(text=skill, callback_data=f"skill_{safe_skill}")])
    
    # Add "Готово" button to finish skill selection
    buttons.append([InlineKeyboardButton(text="Готово", callback_data="skill_done")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_test_questions_keyboard() -> InlineKeyboardMarkup:
    """Return keyboard for test questions."""
    buttons = [
        [InlineKeyboardButton(text="Пройти тест", callback_data="test_start")],
        [InlineKeyboardButton(text="Пропустить", callback_data="test_skip")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_work_style_keyboard() -> InlineKeyboardMarkup:
    """Return keyboard for work style selection."""
    buttons = [
        [InlineKeyboardButton(text="сразу уточняю у руководителя", callback_data="style_ask_manager_immediately")],
        [InlineKeyboardButton(text="сначала сам разбираюсь, потом задаю вопросы", callback_data="style_try_myself_first")],
        [InlineKeyboardButton(text="откладываю и жду дополнительных пояснений", callback_data="style_wait_for_clarification")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_confirmation_keyboard() -> InlineKeyboardMarkup:
    """Return keyboard for confirmation."""
    buttons = [
        [InlineKeyboardButton(text="обновить анкету", callback_data="update_profile")],
        [InlineKeyboardButton(text="загрузить новое резюме", callback_data="upload_resume")],
        [InlineKeyboardButton(text="связаться с менеджером", callback_data="contact_manager")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_yes_no_keyboard(prefix: str = "yn") -> InlineKeyboardMarkup:
    """Return yes/no keyboard with configurable callback prefix."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="да", callback_data=f"{prefix}_yes")],
            [InlineKeyboardButton(text="нет", callback_data=f"{prefix}_no")],
        ]
    )


def get_short_assessment_keyboard(options: list[tuple[str, str]], prefix: str) -> InlineKeyboardMarkup:
    """Inline keyboard for short assessment questions."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=text, callback_data=f"{prefix}_{key}")]
            for key, text in options
        ]
    )


def get_contact_request_keyboard() -> ReplyKeyboardMarkup:
    """Return keyboard with built-in Telegram contact sharing button."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Отправить контакт", request_contact=True)],
            [KeyboardButton(text="Пропустить и ввести вручную")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def get_manager_panel_keyboard() -> ReplyKeyboardMarkup:
    """Return manager panel keyboard."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👥 Последние кандидаты")],
            [KeyboardButton(text="📊 Общая статистика")],
            [KeyboardButton(text="🔎 Поиск по имени")],
            [KeyboardButton(text="📤 Экспорт CSV")],
            [KeyboardButton(text="✉️ Отправить сообщение")],
            [KeyboardButton(text="📄 Открыть Google таблицу")],
            [KeyboardButton(text="🚪 Выйти из панели менеджера")],
        ],
        resize_keyboard=True,
    )
