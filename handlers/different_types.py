import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from database import get_all_candidates, get_candidate, update_candidate_status, search_candidates, get_statistics, match_candidates_to_vacancy, create_vacancy, get_applications_by_vacancy

logger = logging.getLogger(__name__)

# Router for handling different types of commands
router = Router()

# Manager commands
@router.message(F.text == "/view_candidates")
async def view_candidates(message: Message):
    """View all candidates."""
    candidates = get_all_candidates()
    
    if not candidates:
        await message.answer("Нет кандидатов в базе.")
        return
    
    # Format candidates list
    candidates_text = "📋 Все кандидаты:\n\n"
    for i, candidate in enumerate(candidates[:10], 1):  # Show first 10
        candidates_text += f"{i}. {candidate['first_name']} {candidate['last_name']}\n"
        candidates_text += f"   Направление: {candidate['direction']}\n"
        candidates_text += f"   Статус: {candidate['status']}\n"
        candidates_text += f"   Балл: {candidate['score']}\n\n"
    
    if len(candidates) > 10:
        candidates_text += f"... и ещё {len(candidates) - 10} кандидатов"
    
    await message.answer(candidates_text)

@router.message(F.text == "/search_candidates")
async def search_candidates_command(message: Message):
    """Search candidates by keyword."""
    await message.answer("Введите ключевое слово для поиска кандидатов:")

@router.message(F.text.contains(" "))
async def process_search(message: Message):
    """Process search command."""
    # Check if this is a search command (contains space and starts with common search terms)
    text = message.text.strip().lower()
    if ' ' in text and any(keyword in text for keyword in ['search', 'найти', 'поиск']):
        query = message.text.split(' ', 1)[1]  # Get everything after the first word
        candidates = search_candidates(query)
        
        if not candidates:
            await message.answer("Кандидаты не найдены.")
            return
        
        # Format search results
        results_text = f"🔍 Результаты поиска по '{query}':\n\n"
        for i, candidate in enumerate(candidates[:5], 1):  # Show first 5
            results_text += f"{i}. {candidate['first_name']} {candidate['last_name']}\n"
            results_text += f"   Направление: {candidate['direction']}\n"
            results_text += f"   Статус: {candidate['status']}\n"
            results_text += f"   Балл: {candidate['score']}\n\n"
        
        if len(candidates) > 5:
            results_text += f"... и ещё {len(candidates) - 5} кандидатов"
        
        await message.answer(results_text)

@router.message(F.text == "/view_stats")
async def view_statistics(message: Message):
    """View system statistics."""
    stats = get_statistics()
    
    stats_text = "📊 Статистика:\n\n"
    stats_text += f"Всего кандидатов: {stats['total_candidates']}\n"
    stats_text += f"Активных вакансий: {stats['active_vacancies']}\n"
    stats_text += f"Всего заявок: {stats['total_applications']}\n\n"
    
    stats_text += "Кандидаты по статусам:\n"
    for status, count in stats['by_status'].items():
        stats_text += f"  {status}: {count}\n"
    
    stats_text += "\nКандидаты по направлениям:\n"
    for direction, count in stats['by_direction'].items():
        stats_text += f"  {direction}: {count}\n"
    
    await message.answer(stats_text)

@router.message(F.text.startswith("/view_"))
async def view_candidate_details(message: Message):
    """View candidate details by ID."""
    try:
        candidate_id = int(message.text[6:])  # Remove "/view_" prefix
        candidate = get_candidate(candidate_id)
        
        if not candidate:
            await message.answer("Кандидат с таким ID не найден.")
            return
        
        details_text = f"👤 Детали кандидата #{candidate_id}:\n\n"
        details_text += f"Имя: {candidate['first_name']} {candidate['last_name']}\n"
        details_text += f"Возраст: {candidate['age']}\n"
        details_text += f"Город: {candidate['city']}\n"
        details_text += f"Образование: {candidate['education']}\n"
        details_text += f"Направление: {candidate['direction']}\n"
        details_text += f"Опыт: {candidate['experience']}\n"
        details_text += f"Навыки: {candidate['skills']}\n"
        details_text += f"Балл: {candidate['score']}\n"
        details_text += f"Теги: {candidate['tags']}\n"
        details_text += f"Уровень: {candidate['level']}\n"
        details_text += f"Статус: {candidate['status']}\n"
        details_text += f"Контакты: {candidate['contacts']}\n"
        details_text += f"Резюме/ссылки: {candidate['resume']}\n"
        
        await message.answer(details_text)
    except ValueError:
        await message.answer("Пожалуйста, укажите корректный ID кандидата.")

@router.message(F.text.startswith("/status_"))
async def update_candidate_status_command(message: Message):
    """Update candidate status."""
    try:
        parts = message.text[7:].split(' ', 1)  # Remove "/status_" prefix and split
        candidate_id = int(parts[0])
        new_status = parts[1] if len(parts) > 1 else "не подходит"
        
        if update_candidate_status(candidate_id, new_status):
            await message.answer(f"Статус кандидата #{candidate_id} обновлен на '{new_status}'")
        else:
            await message.answer("Ошибка при обновлении статуса кандидата.")
    except (ValueError, IndexError):
        await message.answer("Пожалуйста, укажите корректный ID кандидата и новый статус.")

@router.message(F.text == "/help")
async def help_command(message: Message):
    """Show help message."""
    help_text = (
        "🤖 Команды бота:\n\n"
        "/start - Начать анкетирование\n"
        "/view_candidates - Посмотреть всех кандидатов\n"
        "/search_candidates - Поиск кандидатов (используйте: search [запрос])\n"
        "/view_stats - Просмотр статистики\n"
        "/view_[ID] - Просмотр деталей кандидата\n"
        "/status_[ID] [статус] - Обновить статус кандидата\n"
        "/help - Показать эту справку"
    )
    await message.answer(help_text)

# Additional manager commands
@router.message(F.text.startswith("/match_"))
async def match_candidates_to_vacancy_cmd(message: Message):
    """Match candidates to a vacancy by ID."""
    try:
        vacancy_id = int(message.text[7:])  # Remove "/match_" prefix
        matches = match_candidates_to_vacancy(vacancy_id)
        
        if not matches:
            await message.answer(f"Не найдено подходящих кандидатов для вакансии #{vacancy_id}")
            return
        
        # Format matches
        matches_text = f"✅ Найдено {len(matches)} подходящих кандидатов для вакансии #{vacancy_id}:\n\n"
        for i, match in enumerate(matches[:10], 1):  # Show first 10
            matches_text += f"{i}. {match['first_name']} {match['last_name']}\n"
            matches_text += f"   Направление: {match['direction']}\n"
            matches_text += f"   Балл: {match['score']}\n"
            matches_text += f"   Совпадение: {match['match_score']}%\n"
            matches_text += f"   Навыки: {', '.join(match['matching_skills'])}\n\n"
        
        if len(matches) > 10:
            matches_text += f"... и ещё {len(matches) - 10} кандидатов"
        
        await message.answer(matches_text)
    except ValueError:
        await message.answer("Пожалуйста, укажите корректный ID вакансии.")

@router.message(F.text.startswith("/applications_"))
async def view_applications_for_vacancy(message: Message):
    """View applications for a vacancy by ID."""
    try:
        vacancy_id = int(message.text[12:])  # Remove "/applications_" prefix
        applications = get_applications_by_vacancy(vacancy_id)
        
        if not applications:
            await message.answer(f"Нет заявок для вакансии #{vacancy_id}")
            return
        
        # Format applications
        apps_text = f"📋 Заявки для вакансии #{vacancy_id}:\n\n"
        for i, app in enumerate(applications, 1):
            apps_text += f"{i}. {app['first_name']} {app['last_name']}\n"
            apps_text += f"   Направление: {app['direction']}\n"
            apps_text += f"   Балл: {app['score']}\n"
            apps_text += f"   Статус: {app['status']}\n\n"
        
        await message.answer(apps_text)
    except ValueError:
        await message.answer("Пожалуйста, укажите корректный ID вакансии.")
