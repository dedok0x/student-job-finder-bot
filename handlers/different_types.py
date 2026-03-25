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
    get_candidate,
    get_recent_candidates,
    get_statistics,
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
    wait_broadcast_all_text = State()


def is_manager(message: Message) -> bool:
    return bool(message.from_user and message.from_user.id in AUTHORIZED_MANAGERS)


async def send_manager_panel(message: Message) -> None:
    await message.answer("🧑‍💼 Панель менеджера активна", reply_markup=get_manager_panel_keyboard())


def format_candidate_short(candidate: dict) -> str:
    display_name = candidate.get("candidate_name") or f"{candidate.get('first_name', '')} {candidate.get('last_name', '')}".strip()
    rating = candidate.get("rating", candidate.get("score", 0))
    return (
        f"ID: {candidate.get('id')} | {display_name}\n"
        f"Направление: {candidate.get('direction', '')}\n"
        f"Опыт: {candidate.get('experience', '')}\n"
        f"Статус: {candidate.get('status', '')}\n"
        f"Оценка: {rating}"
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


def _unique_candidates_by_tg(candidates: list[dict]) -> list[dict]:
    dedup: dict[int, dict] = {}
    for candidate in candidates:
        tg_user_id = candidate.get("tg_user_id")
        if not tg_user_id:
            continue
        prev = dedup.get(int(tg_user_id))
        if not prev or int(candidate.get("id", 0)) > int(prev.get("id", 0)):
            dedup[int(tg_user_id)] = candidate
    return list(dedup.values())


def _is_incomplete_status(status: str) -> bool:
    normalized = (status or "").strip().lower()
    return normalized.startswith("черновик") or normalized.startswith("недозаполнена")


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


@router.message(F.text == "📣 Напомнить недопрошедшим")
async def manager_remind_incomplete(message: Message):
    if not is_manager(message):
        return

    all_candidates = get_all_candidates()
    unique_candidates = _unique_candidates_by_tg(all_candidates)
    targets = [candidate for candidate in unique_candidates if _is_incomplete_status(candidate.get("status", ""))]

    if not targets:
        await message.answer("Нет недозаполненных анкет для напоминания.", reply_markup=get_manager_panel_keyboard())
        return

    sent = 0
    failed = 0
    reminder_text = (
        "👋 Напоминание: вы остановились на заполнении анкеты.\n"
        "Продолжите с места остановки — это повысит точность подбора вакансий.\n"
        "Или начни заново, нажми /start"
    )
    for candidate in targets:
        ok = await send_message_to_candidate(message, candidate, reminder_text)
        if ok:
            sent += 1
        else:
            failed += 1

    await message.answer(
        f"📣 Напоминания отправлены.\nУспешно: {sent}\nНе доставлено: {failed}",
        reply_markup=get_manager_panel_keyboard(),
    )


@router.message(F.text == "📢 Сообщение всем пользователям")
async def manager_start_broadcast_all(message: Message, state: FSMContext):
    if not is_manager(message):
        return
    await state.set_state(ManagerPanelState.wait_broadcast_all_text)
    await message.answer("Введи текст для отправки всем пользователям.")


@router.message(ManagerPanelState.wait_broadcast_all_text)
async def manager_send_broadcast_all(message: Message, state: FSMContext):
    if not is_manager(message):
        return

    text = (message.text or "").strip()
    if len(text) < 2:
        await message.answer("Текст слишком короткий. Введи сообщение длиннее.")
        return

    all_candidates = get_all_candidates()
    targets = _unique_candidates_by_tg(all_candidates)
    if not targets:
        await state.clear()
        await message.answer("Нет пользователей для рассылки.", reply_markup=get_manager_panel_keyboard())
        return

    sent = 0
    failed = 0
    for candidate in targets:
        ok = await send_message_to_candidate(message, candidate, text)
        if ok:
            sent += 1
        else:
            failed += 1

    await state.clear()
    await message.answer(
        f"📢 Рассылка завершена.\nУспешно: {sent}\nНе доставлено: {failed}",
        reply_markup=get_manager_panel_keyboard(),
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



