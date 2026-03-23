import asyncio
import os
from datetime import datetime

import pandas as pd
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup, Message, ReplyKeyboardRemove

from database import (
    get_all_candidates,
    get_applications_by_vacancy,
    get_candidate,
    get_recent_candidates,
    get_statistics,
    match_candidates_to_vacancy,
    search_candidates,
    search_candidates_fuzzy,
    update_candidate_status,
)
from keyboards.for_questions import get_manager_panel_keyboard
from sheets_sync import GOOGLE_SHEETS_URL, apply_candidates_sheet_formatting, get_last_sheets_error, sync_candidates_to_sheets

router = Router()

MANAGER_AUTH_CODE = os.getenv("MANAGER_AUTH_CODE")
AUTHORIZED_MANAGERS: set[int] = set()


class ManagerPanelState(StatesGroup):
    wait_search_query = State()
    wait_message_target = State()
    wait_message_text = State()


def is_manager(message: Message) -> bool:
    return bool(message.from_user and message.from_user.id in AUTHORIZED_MANAGERS)


async def send_manager_panel(message: Message) -> None:
    await message.answer("🧑‍💼 Панель менеджера активна", reply_markup=get_manager_panel_keyboard())


def format_candidate_short(candidate: dict) -> str:
    display_name = candidate.get("candidate_name") or f"{candidate.get('first_name', '')} {candidate.get('last_name', '')}".strip()
    return (
        f"ID: {candidate.get('id')} | {display_name}\n"
        f"Направление: {candidate.get('direction', '')}\n"
        f"Опыт: {candidate.get('experience', '')}\n"
        f"Статус: {candidate.get('status', '')}\n"
        f"Балл: {candidate.get('score', 0)}"
    )


def format_candidate_with_tg(candidate: dict) -> str:
    username = (candidate.get("username") or "").strip()
    tg_user_id = candidate.get("tg_user_id")
    tg_link = f"https://t.me/{username}" if username else (f"tg://user?id={tg_user_id}" if tg_user_id else "не указана")
    base = format_candidate_short(candidate)
    return f"{base}\nTelegram: {tg_link}"


async def send_message_to_candidate(message: Message, candidate: dict, text: str) -> bool:
    tg_user_id = candidate.get("tg_user_id")
    if not tg_user_id:
        return False
    try:
        await message.bot.send_message(chat_id=int(tg_user_id), text=text)
        return True
    except Exception:
        return False


@router.message(Command("auth"))
async def auth_manager(message: Message, state: FSMContext):
    parts = (message.text or "").split(maxsplit=1)
    code = parts[1].strip() if len(parts) > 1 else ""
    if code == MANAGER_AUTH_CODE:
        AUTHORIZED_MANAGERS.add(message.from_user.id)
        await state.clear()
        await send_manager_panel(message)
        return
    await message.answer("Неверный код авторизации.")


@router.message(F.text.casefold() == "quit")
async def quit_manager_panel(message: Message, state: FSMContext):
    if not is_manager(message):
        return
    AUTHORIZED_MANAGERS.discard(message.from_user.id)
    await state.clear()
    await message.answer("Вы вышли из панели менеджера. Для продолжения напишите /start", reply_markup=ReplyKeyboardRemove())


@router.message(Command("quit"))
async def quit_manager_panel_command(message: Message, state: FSMContext):
    if not is_manager(message):
        return
    AUTHORIZED_MANAGERS.discard(message.from_user.id)
    await state.clear()
    await message.answer("Вы вышли из панели менеджера. Для продолжения напишите /start", reply_markup=ReplyKeyboardRemove())


@router.message(F.text == "🚪 Выйти из панели менеджера")
async def quit_manager_panel_button(message: Message, state: FSMContext):
    if not is_manager(message):
        return
    AUTHORIZED_MANAGERS.discard(message.from_user.id)
    await state.clear()
    await message.answer("Вы вышли из панели менеджера. Для продолжения напишите /start", reply_markup=ReplyKeyboardRemove())


@router.message(F.text == "👥 Последние кандидаты")
async def manager_recent_candidates(message: Message):
    if not is_manager(message):
        return

    candidates = get_recent_candidates(10)
    if not candidates:
        await message.answer("Кандидаты не найдены.")
        return

    response = "\n\n".join([format_candidate_short(c) for c in candidates])
    await message.answer(f"📋 Последние кандидаты:\n\n{response}")


@router.message(F.text == "📊 Общая статистика")
async def manager_recent_stats(message: Message):
    if not is_manager(message):
        return

    all_candidates = get_all_candidates()
    by_direction: dict[str, int] = {}
    for candidate in all_candidates:
        direction = candidate.get("direction", "не указано") or "не указано"
        by_direction[direction] = by_direction.get(direction, 0) + 1

    stats = get_statistics()
    text = (
        "📊 Общая статистика\n\n"
        f"Всего кандидатов: {stats.get('total_candidates', 0)}\n"
        f"Активных вакансий: {stats.get('active_vacancies', 0)}\n"
        f"Всего заявок: {stats.get('total_applications', 0)}\n"
    )

    if stats.get("by_status"):
        text += "\nПо статусам:\n"
        for status, count in stats["by_status"].items():
            text += f"- {status}: {count}\n"

    if by_direction:
        text += "\nПо направлениям:\n"
        for direction, count in sorted(by_direction.items(), key=lambda x: x[1], reverse=True):
            text += f"- {direction}: {count}\n"
    await message.answer(text)


@router.message(F.text.contains("Поиск по имени"))
async def manager_start_name_search(message: Message, state: FSMContext):
    if not is_manager(message):
        return
    await state.set_state(ManagerPanelState.wait_search_query)
    await message.answer("Введи имя или фамилию для поиска (поддерживается неточное совпадение).")


@router.message(ManagerPanelState.wait_search_query)
async def manager_process_name_search(message: Message, state: FSMContext):
    if not is_manager(message):
        return

    query = (message.text or "").strip()
    results = search_candidates_fuzzy(query=query, limit=10)
    await state.clear()

    if not results:
        await message.answer("Ничего не найдено.", reply_markup=get_manager_panel_keyboard())
        return

    response = "\n\n".join([format_candidate_short(c) for c in results])
    await message.answer(f"🔎 Результаты поиска:\n\n{response}", reply_markup=get_manager_panel_keyboard())

    for candidate in results[:5]:
        candidate_id = candidate.get("id")
        if not candidate_id:
            continue
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="✉️ Написать через бота", callback_data=f"msg_candidate_{candidate_id}")]
            ]
        )
        await message.answer(format_candidate_with_tg(candidate), reply_markup=kb)


@router.callback_query(F.data.startswith("msg_candidate_"))
async def manager_message_from_search(callback: CallbackQuery, state: FSMContext):
    if not callback.message or not callback.from_user or callback.from_user.id not in AUTHORIZED_MANAGERS:
        await callback.answer("Недостаточно прав", show_alert=True)
        return

    try:
        candidate_id = int((callback.data or "").replace("msg_candidate_", ""))
    except ValueError:
        await callback.answer("Некорректный кандидат", show_alert=True)
        return

    await state.update_data(target_candidate_id=candidate_id)
    await state.set_state(ManagerPanelState.wait_message_text)
    await callback.message.answer(f"Введи сообщение для кандидата ID {candidate_id}.")
    await callback.answer()


@router.message(F.text == "📤 Экспорт CSV")
async def manager_export_csv(message: Message):
    if not is_manager(message):
        return

    candidates = get_all_candidates()
    if not candidates:
        await message.answer("Нет данных для экспорта.")
        return

    df = pd.DataFrame(candidates)
    os.makedirs("exports", exist_ok=True)
    file_name = f"candidates_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    file_path = os.path.join("exports", file_name)
    df.to_csv(file_path, index=False, encoding="utf-8-sig")

    await message.answer_document(FSInputFile(file_path), caption="Готово: экспорт всех данных кандидатов")


@router.message(F.text == "✉️ Отправить сообщение")
async def manager_start_send_message(message: Message, state: FSMContext):
    if not is_manager(message):
        return
    await state.set_state(ManagerPanelState.wait_message_target)
    await message.answer("Введи ID кандидата, которому нужно отправить сообщение.")


@router.message(F.text == "📄 Открыть Google таблицу")
async def manager_open_google_sheet(message: Message):
    if not is_manager(message):
        return

    progress_message = await message.answer("⏳ Готовлю и синхронизирую таблицу, это может занять до 20 секунд...")

    # Синхронизация при открытии менеджером, чтобы ссылка всегда вела на актуальные данные
    candidates = get_all_candidates()
    synced = await asyncio.to_thread(sync_candidates_to_sheets, candidates)
    formatted = await asyncio.to_thread(apply_candidates_sheet_formatting)

    if not synced:
        details = get_last_sheets_error()
        suffix = f"\nПричина: {details}" if details else ""
        await progress_message.edit_text(
            "Не удалось синхронизировать Google таблицу."
            f"{suffix}\nСсылка:\n{GOOGLE_SHEETS_URL}"
        )
        return

    formatting_text = "Формат обновлён." if formatted else "Формат не применён (данные сохранены)."
    await progress_message.edit_text(
        f"✅ Google таблица подключена.\nДанные синхронизированы.\n{formatting_text}\n"
        f"Записано строк: {len(candidates)}\n"
        f"Ссылка:\n{GOOGLE_SHEETS_URL}"
    )


@router.message(ManagerPanelState.wait_message_target)
async def manager_pick_target(message: Message, state: FSMContext):
    if not is_manager(message):
        return

    text = (message.text or "").strip()
    if not text.isdigit():
        await message.answer("ID кандидата должен быть числом.")
        return

    candidate = get_candidate(int(text))
    if not candidate:
        await message.answer("Кандидат не найден. Введи корректный ID.")
        return

    await state.update_data(target_candidate_id=int(text))
    await state.set_state(ManagerPanelState.wait_message_text)
    await message.answer("Теперь отправь текст сообщения для кандидата.")


@router.message(ManagerPanelState.wait_message_text)
async def manager_send_text(message: Message, state: FSMContext):
    if not is_manager(message):
        return

    data = await state.get_data()
    candidate_id = data.get("target_candidate_id")
    candidate = get_candidate(candidate_id) if candidate_id else None
    if not candidate:
        await state.clear()
        await message.answer("Кандидат не найден. Начни заново.", reply_markup=get_manager_panel_keyboard())
        return

    text = (message.text or "").strip()
    if len(text) < 2:
        await message.answer("Текст слишком короткий. Отправь нормальное сообщение.")
        return

    ok = await send_message_to_candidate(message, candidate, text)
    await state.clear()
    if ok:
        await message.answer("✅ Сообщение отправлено кандидату.", reply_markup=get_manager_panel_keyboard())
    else:
        await message.answer("Не удалось отправить сообщение (возможно, нет tg_user_id или диалог не начат).", reply_markup=get_manager_panel_keyboard())


@router.message(F.text == "/view_candidates")
async def view_candidates(message: Message):
    candidates = get_all_candidates()
    if not candidates:
        await message.answer("Нет кандидатов в базе.")
        return
    text = "📋 Все кандидаты:\n\n"
    for i, candidate in enumerate(candidates[:10], 1):
        text += f"{i}. {candidate.get('candidate_name') or candidate.get('first_name', '')} {candidate.get('last_name', '')}\n"
        text += f"   Направление: {candidate.get('direction', '')}\n"
        text += f"   Статус: {candidate.get('status', '')}\n"
        text += f"   Балл: {candidate.get('score', 0)}\n\n"
    if len(candidates) > 10:
        text += f"... и ещё {len(candidates) - 10} кандидатов"
    await message.answer(text)


@router.message(F.text == "/search_candidates")
async def search_candidates_command(message: Message):
    await message.answer("Введите ключевое слово для поиска кандидатов:")


@router.message(F.text.contains(" "))
async def process_search(message: Message):
    text = (message.text or "").strip().lower()
    if " " in text and any(keyword in text for keyword in ["search", "найти", "поиск"]):
        query = (message.text or "").split(" ", 1)[1]
        candidates = search_candidates(query)
        if not candidates:
            await message.answer("Кандидаты не найдены.")
            return
        result = f"🔍 Результаты поиска по '{query}':\n\n"
        for i, candidate in enumerate(candidates[:5], 1):
            result += f"{i}. {candidate.get('candidate_name') or candidate.get('first_name', '')} {candidate.get('last_name', '')}\n"
            result += f"   Направление: {candidate.get('direction', '')}\n"
            result += f"   Статус: {candidate.get('status', '')}\n"
            result += f"   Балл: {candidate.get('score', 0)}\n\n"
        await message.answer(result)


@router.message(F.text == "/view_stats")
async def view_statistics(message: Message):
    stats = get_statistics()
    text = "📊 Статистика:\n\n"
    text += f"Всего кандидатов: {stats['total_candidates']}\n"
    text += f"Активных вакансий: {stats['active_vacancies']}\n"
    text += f"Всего заявок: {stats['total_applications']}\n\n"
    text += "Кандидаты по статусам:\n"
    for status, count in stats["by_status"].items():
        text += f"  {status}: {count}\n"
    text += "\nКандидаты по направлениям:\n"
    for direction, count in stats["by_direction"].items():
        text += f"  {direction}: {count}\n"
    await message.answer(text)


@router.message(F.text.startswith("/view_"))
async def view_candidate_details(message: Message):
    try:
        candidate_id = int((message.text or "")[6:])
        candidate = get_candidate(candidate_id)
        if not candidate:
            await message.answer("Кандидат с таким ID не найден.")
            return
        details = f"👤 Детали кандидата #{candidate_id}:\n\n"
        details += f"Имя Telegram: {candidate.get('first_name', '')} {candidate.get('last_name', '')}\n"
        details += f"Имя кандидата: {candidate.get('candidate_name', '')}\n"
        details += f"Возраст: {candidate.get('age', '')}\n"
        details += f"Направление: {candidate.get('direction', '')}\n"
        details += f"Опыт: {candidate.get('experience', '')}\n"
        details += f"Навыки: {candidate.get('skills', '')}\n"
        details += f"ЗП ожидания: {candidate.get('salary_expectations', '')}\n"
        details += f"Балл: {candidate.get('score', 0)}\n"
        details += f"Теги: {candidate.get('tags', '')}\n"
        details += f"Уровень: {candidate.get('level', '')}\n"
        details += f"Статус: {candidate.get('status', '')}\n"
        details += f"Контакты: {candidate.get('contacts', '')}\n"
        details += f"Резюме/ссылки: {candidate.get('resume_links', '')}\n"
        await message.answer(details)
    except ValueError:
        await message.answer("Пожалуйста, укажите корректный ID кандидата.")


@router.message(F.text.startswith("/status_"))
async def update_candidate_status_command(message: Message):
    try:
        parts = (message.text or "")[7:].split(" ", 1)
        candidate_id = int(parts[0])
        new_status = parts[1] if len(parts) > 1 else "не подходит"
        if update_candidate_status(candidate_id, new_status):
            await message.answer(f"Статус кандидата #{candidate_id} обновлен на '{new_status}'")
        else:
            await message.answer("Ошибка при обновлении статуса кандидата.")
    except (ValueError, IndexError):
        await message.answer("Пожалуйста, укажите корректный ID кандидата и новый статус.")


@router.message(F.text.startswith("/match_"))
async def match_candidates_to_vacancy_cmd(message: Message):
    try:
        vacancy_id = int((message.text or "")[7:])
        matches = match_candidates_to_vacancy(vacancy_id)
        if not matches:
            await message.answer(f"Не найдено подходящих кандидатов для вакансии #{vacancy_id}")
            return
        text = f"✅ Найдено {len(matches)} подходящих кандидатов для вакансии #{vacancy_id}:\n\n"
        for i, match in enumerate(matches[:10], 1):
            text += f"{i}. {match.get('candidate_name') or match.get('first_name', '')} {match.get('last_name', '')}\n"
            text += f"   Направление: {match.get('direction', '')}\n"
            text += f"   Балл: {match.get('score', 0)}\n"
            text += f"   Совпадение: {match.get('match_score', 0)}%\n"
            text += f"   Навыки: {', '.join(match.get('matching_skills', []))}\n\n"
        await message.answer(text)
    except ValueError:
        await message.answer("Пожалуйста, укажите корректный ID вакансии.")


@router.message(F.text.startswith("/applications_"))
async def view_applications_for_vacancy(message: Message):
    try:
        vacancy_id = int((message.text or "")[12:])
        applications = get_applications_by_vacancy(vacancy_id)
        if not applications:
            await message.answer(f"Нет заявок для вакансии #{vacancy_id}")
            return
        text = f"📋 Заявки для вакансии #{vacancy_id}:\n\n"
        for i, app in enumerate(applications, 1):
            text += f"{i}. {app.get('first_name', '')} {app.get('last_name', '')}\n"
            text += f"   Направление: {app.get('direction', '')}\n"
            text += f"   Балл: {app.get('score', 0)}\n"
            text += f"   Статус: {app.get('status', '')}\n\n"
        await message.answer(text)
    except ValueError:
        await message.answer("Пожалуйста, укажите корректный ID вакансии.")

