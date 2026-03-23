import logging
import os
from typing import Any, Dict, List, Tuple

import gspread
from google.oauth2 import service_account


logger = logging.getLogger(__name__)
_LAST_SHEETS_ERROR = ""

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


def _candidate_to_row(candidate: Dict[str, Any]) -> List[str]:
    keys = [
        "id",
        "created_at",
        "updated_at",
        "candidate_name",
        "first_name",
        "last_name",
        "age",
        "username",
        "tg_user_id",
        "tg_chat_id",
        "who_are_you",
        "what_are_you_looking_for",
        "direction",
        "experience",
        "skills",
        "salary_expectations",
        "work_style",
        "multi_task_style",
        "unknown_task_action",
        "work_preference",
        "work_start_priority",
        "contacts",
        "resume_links",
        "status",
        "score",
        "tags",
        "level",
        "test_answers",
        "additional_info",
    ]
    return [str(candidate.get(key, "")) for key in keys]


def _header_row() -> List[str]:
    return [
        "id",
        "created_at",
        "updated_at",
        "candidate_name",
        "first_name",
        "last_name",
        "age",
        "username",
        "tg_user_id",
        "tg_chat_id",
        "who_are_you",
        "what_are_you_looking_for",
        "direction",
        "experience",
        "skills",
        "salary_expectations",
        "work_style",
        "multi_task_style",
        "unknown_task_action",
        "work_preference",
        "work_start_priority",
        "contacts",
        "resume_links",
        "status",
        "score",
        "tags",
        "level",
        "test_answers",
        "additional_info",
    ]


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


def ensure_google_spreadsheet() -> Tuple[str, str, bool]:
    """
    Проверяет доступ к фиксированной таблице.

    Возвращает: (spreadsheet_id, spreadsheet_url, created_now)
    created_now всегда False, т.к. таблица фиксирована и уже предоставлена.
    """
    client = _get_gspread_client()
    if not client:
        return "", "", False

    try:
        spreadsheet = client.open_by_key(GOOGLE_SHEETS_ID)
    except Exception as exc:
        _set_last_error(f"Spreadsheet access failed: {exc}")
        logger.warning("Spreadsheet access failed: %s", exc)
        return "", "", False

    worksheet = _get_or_create_worksheet(spreadsheet)
    if not worksheet:
        return "", "", False

    return spreadsheet.id, GOOGLE_SHEETS_URL, False


def sync_candidates_to_sheets(candidates: List[Dict[str, Any]]) -> bool:
    client = _get_gspread_client()
    if not client:
        return False

    try:
        spreadsheet = client.open_by_key(GOOGLE_SHEETS_ID)
        worksheet = _get_or_create_worksheet(spreadsheet)
        if not worksheet:
            return False

        values = [_header_row()] + [_candidate_to_row(candidate) for candidate in candidates]
        worksheet.clear()
        worksheet.update(values=values, range_name="A1")
        return True
    except Exception as exc:
        _set_last_error(f"Spreadsheet sync failed: {exc}")
        logger.warning("Google Sheets sync failed: %s", exc)
        return False
