import logging
import os
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from typing import Any, Dict, List, Tuple

import gspread
from google.oauth2 import service_account


logger = logging.getLogger(__name__)
_LAST_SHEETS_ERROR = ""
_SYNC_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="sheets-sync")
_SYNC_LOCK = Lock()
_PENDING_SYNC_SNAPSHOT: List[Dict[str, Any]] | None = None

GOOGLE_SHEETS_URL = "https://docs.google.com/spreadsheets/d/1EuD_34vuRdM5I-qHvb9KtEQEhNUtKV5S2KQlxpUwQ1g/edit?usp=sharing"
GOOGLE_SHEETS_ID = "1EuD_34vuRdM5I-qHvb9KtEQEhNUtKV5S2KQlxpUwQ1g"
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def _set_last_error(message: str) -> None:
    global _LAST_SHEETS_ERROR
    _LAST_SHEETS_ERROR = message


def get_last_sheets_error() -> str:
    return _LAST_SHEETS_ERROR


DISPLAY_COLUMNS: List[tuple[str, str]] = [
    ("updated_at", "Обновлено"),
    ("candidate_name", "Кандидат"),
    ("username_link", "Telegram"),
    ("age", "Возраст"),
    ("who_are_you", "Кто кандидат"),
    ("what_are_you_looking_for", "Ищет"),
    ("direction", "Направление"),
    ("experience", "Опыт"),
    ("skills", "Навыки"),
    ("salary_expectations", "Зарплатные ожидания"),
    ("work_style", "Рабочий стиль"),
    ("multi_task_style", "Многозадачность"),
    ("work_behavior_summary", "Формат работы (кейс)"),
    ("contacts", "Контакты"),
    ("resume_links", "Резюме / Портфолио"),
    ("status", "Статус"),
    ("score", "Скор"),
    ("tags", "Теги"),
    ("level", "Уровень"),
    ("test_answers", "Ответы мини-теста"),
    ("additional_info", "Дополнительно"),
    ("created_at", "Создано"),
]


def _build_telegram_link_cell(candidate: Dict[str, Any]) -> str:
    username = (candidate.get("username") or "").strip()
    if username:
        return f'https://t.me/{username}'

    tg_user_id = candidate.get("tg_user_id")
    if tg_user_id:
        return f'tg://user?id={tg_user_id}'

    return ""


def _format_work_behavior_summary(candidate: Dict[str, Any]) -> str:
    unknown_task_action = str(candidate.get("unknown_task_action", "") or "").strip()
    work_preference = str(candidate.get("work_preference", "") or "").strip()
    work_start_priority = str(candidate.get("work_start_priority", "") or "").strip()

    parts = []
    if unknown_task_action:
        parts.append(f"1. Если задача непонятна: {unknown_task_action}")
    if work_preference:
        parts.append(f"2. Предпочтения в работе: {work_preference}")
    if work_start_priority:
        parts.append(f"3. Приоритет в начале работы: {work_start_priority}")

    return "\n".join(parts)


def _format_test_answers(candidate: Dict[str, Any]) -> str:
    raw = str(candidate.get("test_answers", "") or "").strip()
    normalized = raw.lower()

    if normalized in {"", "пропущено", "пропустить", "skip", "-"}:
        return "тест пропущен"

    return raw


def _candidate_to_row(candidate: Dict[str, Any]) -> List[str]:
    row: List[str] = []
    for key, _ in DISPLAY_COLUMNS:
        if key == "username_link":
            row.append(_build_telegram_link_cell(candidate))
        elif key == "work_behavior_summary":
            row.append(_format_work_behavior_summary(candidate))
        elif key == "test_answers":
            row.append(_format_test_answers(candidate))
        else:
            row.append(str(candidate.get(key, "")))
    return row


def _header_row() -> List[str]:
    return [header for _, header in DISPLAY_COLUMNS]


def _get_gspread_client() -> gspread.Client | None:
    _set_last_error("")
    creds_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "creds.json")
    if not os.path.exists(creds_file):
        _set_last_error(f"Credentials file not found: {creds_file}")
        return None

    try:
        credentials = service_account.Credentials.from_service_account_file(
            creds_file,
            scopes=GOOGLE_SCOPES,
        )
        return gspread.authorize(credentials)
    except Exception as exc:
        _set_last_error(f"Credentials auth failed: {exc}")
        logger.warning("Google auth failed: %s", exc)
        return None


def _get_or_create_worksheet(spreadsheet: gspread.Spreadsheet) -> gspread.Worksheet | None:
    try:
        worksheet = spreadsheet.get_worksheet(0)
        if worksheet:
            return worksheet
        try:
            return spreadsheet.add_worksheet(title="Sheet1", rows=1000, cols=40)
        except Exception as exc:
            _set_last_error(f"Worksheet create failed: {exc}")
            logger.warning("Worksheet create failed: %s", exc)
            return None
    except Exception as exc:
        _set_last_error(f"Worksheet access failed: {exc}")
        logger.warning("Worksheet access failed: %s", exc)
        return None


def _open_spreadsheet_and_worksheet() -> tuple[gspread.Spreadsheet, gspread.Worksheet] | None:
    client = _get_gspread_client()
    if not client:
        return None

    try:
        spreadsheet = client.open_by_key(GOOGLE_SHEETS_ID)
        worksheet = _get_or_create_worksheet(spreadsheet)
        if not worksheet:
            return None
        return spreadsheet, worksheet
    except Exception as exc:
        _set_last_error(f"Spreadsheet access failed: {exc}")
        logger.warning("Spreadsheet access failed: %s", exc)
        return None


def ensure_google_spreadsheet() -> Tuple[str, str, bool]:
    """
    Проверяет доступ к фиксированной таблице.

    Возвращает: (spreadsheet_id, spreadsheet_url, created_now)
    created_now всегда False, т.к. таблица фиксирована и уже предоставлена.
    """
    opened = _open_spreadsheet_and_worksheet()
    if not opened:
        return "", "", False

    spreadsheet, _ = opened

    return spreadsheet.id, GOOGLE_SHEETS_URL, False


def apply_candidates_sheet_formatting() -> bool:
    opened = _open_spreadsheet_and_worksheet()
    if not opened:
        return False

    try:
        spreadsheet, worksheet = opened
        requests = [
            {
                "updateSheetProperties": {
                    "properties": {
                        "sheetId": worksheet.id,
                        "gridProperties": {"frozenRowCount": 1},
                    },
                    "fields": "gridProperties.frozenRowCount",
                }
            },
            {
                "repeatCell": {
                    "range": {
                        "sheetId": worksheet.id,
                        "startRowIndex": 0,
                        "endRowIndex": 1,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": {"red": 0.89, "green": 0.95, "blue": 0.99},
                            "textFormat": {"bold": True},
                        }
                    },
                    "fields": "userEnteredFormat(backgroundColor,textFormat)",
                }
            },
            {
                "setBasicFilter": {
                    "filter": {
                        "range": {
                            "sheetId": worksheet.id,
                            "startRowIndex": 0,
                            "startColumnIndex": 0,
                            "endColumnIndex": len(_header_row()),
                        }
                    }
                }
            },
            {
                "autoResizeDimensions": {
                    "dimensions": {
                        "sheetId": worksheet.id,
                        "dimension": "COLUMNS",
                        "startIndex": 0,
                        "endIndex": len(_header_row()),
                    }
                }
            },
        ]
        spreadsheet.batch_update({"requests": requests})
        return True
    except Exception as exc:
        _set_last_error(f"Sheet formatting failed: {exc}")
        logger.warning("Sheet formatting failed: %s", exc)
        return False


def sync_candidates_to_sheets(candidates: List[Dict[str, Any]]) -> bool:
    try:
        opened = _open_spreadsheet_and_worksheet()
        if not opened:
            return False
        _, worksheet = opened

        values = [_header_row()] + [_candidate_to_row(candidate) for candidate in candidates]
        worksheet.clear()
        worksheet.update(values=values, range_name="A1")
        return True
    except Exception as exc:
        _set_last_error(f"Spreadsheet sync failed: {exc}")
        logger.warning("Google Sheets sync failed: %s", exc)
        return False


def _drain_pending_sync() -> None:
    global _PENDING_SYNC_SNAPSHOT
    while True:
        with _SYNC_LOCK:
            snapshot = _PENDING_SYNC_SNAPSHOT
            if snapshot is None:
                return
            _PENDING_SYNC_SNAPSHOT = None

        sync_candidates_to_sheets(snapshot)


def enqueue_candidates_sync(candidates: List[Dict[str, Any]]) -> None:
    global _PENDING_SYNC_SNAPSHOT
    with _SYNC_LOCK:
        _PENDING_SYNC_SNAPSHOT = candidates
    _SYNC_EXECUTOR.submit(_drain_pending_sync)
