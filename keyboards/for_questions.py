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
        [InlineKeyboardButton(text="IT / Продукт", callback_data="direction_it_product")],
        [InlineKeyboardButton(text="Digital / маркетинг / дизайн", callback_data="direction_digital_marketing_design")],
        [InlineKeyboardButton(text="Бизнес / операции", callback_data="direction_business_operations")],
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
        "IT / Продукт": [
            "Python", "JavaScript", "HTML", "CSS", "SQL", "Git", "API", "тестирование", "Figma", "Postman"
        ],
        "Digital / маркетинг / дизайн": [
            "ведение социальных сетей", "таргетированная реклама", "контент", "тексты", "Canva",
            "Google Analytics", "Яндекс Метрика", "рекламный кабинет", "рассылки", "Tilda"
        ],
        "Бизнес / операции": [
            "CRM", "работа с заявками", "переговоры", "обработка обращений", "холодные сообщения",
            "сопровождение клиентов", "работа с возражениями"
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
        [InlineKeyboardButton(text="изменить направление", callback_data="change_direction")],
        [InlineKeyboardButton(text="загрузить новое резюме", callback_data="upload_resume")],
        [InlineKeyboardButton(text="связаться с менеджером", callback_data="contact_manager")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
