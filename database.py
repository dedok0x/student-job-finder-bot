import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Any

from rapidfuzz import fuzz

DB_NAME = 'hr_bot.db'


def _sync_snapshot_to_sheets(conn: sqlite3.Connection) -> None:
    """Push current candidates snapshot to Google Sheets (best effort)."""
    try:
        from sheets_sync import enqueue_candidates_sync

        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM candidates ORDER BY id DESC')
        rows = cursor.fetchall()
        enqueue_candidates_sync([dict(row) for row in rows])
    except Exception:
        # sync is optional and should never break core DB writes
        pass


def _ensure_column(cursor: sqlite3.Cursor, table: str, column: str, definition: str) -> None:
    """Add a column to table if it does not exist."""
    cursor.execute(f"PRAGMA table_info({table})")
    existing_columns = {row[1] for row in cursor.fetchall()}
    if column not in existing_columns:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

def init_db():
    """Initialize database with all required tables."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Candidates table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tg_user_id INTEGER,
            tg_chat_id INTEGER,
            timestamp TEXT,
            username TEXT,
            candidate_name TEXT,
            first_name TEXT,
            last_name TEXT,
            age INTEGER,
            who_are_you TEXT,
            what_are_you_looking_for TEXT,
            direction TEXT,
            experience TEXT,
            skills TEXT,
            resume_links TEXT,
            resume_file_id TEXT,
            resume_message_link TEXT,
            test_answers TEXT,
            work_style TEXT,
            multi_task_style TEXT,
            unknown_task_action TEXT,
            work_preference TEXT,
            work_start_priority TEXT,
            contacts TEXT,
            score INTEGER DEFAULT 0,
            tags TEXT,
            level TEXT,
            status TEXT DEFAULT 'новая анкета',
            clarifying_answers TEXT,
            salary_expectations TEXT,
            additional_info TEXT,
            availability_date TEXT,
            manager_notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Vacancies table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vacancies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            direction TEXT,
            required_skills TEXT,
            experience_level TEXT,
            status TEXT DEFAULT 'активная',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Applications table (candidate-vacancy matching)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER,
            vacancy_id INTEGER,
            status TEXT DEFAULT 'отправлен работодателю',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (candidate_id) REFERENCES candidates (id),
            FOREIGN KEY (vacancy_id) REFERENCES vacancies (id)
        )
    ''')

    
    _ensure_column(cursor, 'candidates', 'tg_user_id', 'INTEGER')
    _ensure_column(cursor, 'candidates', 'tg_chat_id', 'INTEGER')
    _ensure_column(cursor, 'candidates', 'candidate_name', 'TEXT')
    _ensure_column(cursor, 'candidates', 'age', 'INTEGER')
    _ensure_column(cursor, 'candidates', 'resume_file_id', 'TEXT')
    _ensure_column(cursor, 'candidates', 'resume_message_link', 'TEXT')
    _ensure_column(cursor, 'candidates', 'additional_info', 'TEXT')
    _ensure_column(cursor, 'candidates', 'multi_task_style', 'TEXT')
    _ensure_column(cursor, 'candidates', 'unknown_task_action', 'TEXT')
    _ensure_column(cursor, 'candidates', 'work_preference', 'TEXT')
    _ensure_column(cursor, 'candidates', 'work_start_priority', 'TEXT')

    conn.commit()
    conn.close()

def save_candidate(data: Dict[str, Any]) -> int:
    """Save candidate data and return candidate ID.

    One Telegram user/chat pair keeps a single candidate row.
    Re-submitting анкета updates existing row and updated_at.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    tg_user_id = data.get('tg_user_id')
    tg_chat_id = data.get('tg_chat_id')

    candidate_id: int | None = None
    if tg_user_id and tg_chat_id:
        cursor.execute(
            '''
            SELECT id
            FROM candidates
            WHERE tg_user_id = ? AND tg_chat_id = ?
            ORDER BY id DESC
            LIMIT 1
            ''',
            (tg_user_id, tg_chat_id),
        )
        existing = cursor.fetchone()
        if existing:
            candidate_id = int(existing[0])

    if candidate_id is not None:
        cursor.execute('''
            UPDATE candidates
            SET timestamp = ?,
                username = ?,
                candidate_name = ?,
                first_name = ?,
                last_name = ?,
                age = ?,
                who_are_you = ?,
                what_are_you_looking_for = ?,
                direction = ?,
                experience = ?,
                skills = ?,
                resume_links = ?,
                resume_file_id = ?,
                resume_message_link = ?,
                test_answers = ?,
                work_style = ?,
                multi_task_style = ?,
                unknown_task_action = ?,
                work_preference = ?,
                work_start_priority = ?,
                contacts = ?,
                clarifying_answers = ?,
                salary_expectations = ?,
                additional_info = ?,
                status = ?,
                score = ?,
                tags = ?,
                level = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (
            data.get('timestamp'),
            data.get('username', ''),
            data.get('candidate_name', ''),
            data.get('first_name', ''),
            data.get('last_name', ''),
            data.get('age'),
            data.get('who_are_you', ''),
            data.get('what_are_you_looking_for', ''),
            data.get('direction', ''),
            data.get('experience', ''),
            data.get('skills', ''),
            data.get('resume_links', ''),
            data.get('resume_file_id', ''),
            data.get('resume_message_link', ''),
            data.get('test_answers', ''),
            data.get('work_style', ''),
            data.get('multi_task_style', ''),
            data.get('unknown_task_action', ''),
            data.get('work_preference', ''),
            data.get('work_start_priority', ''),
            data.get('contacts', ''),
            data.get('clarifying_answers', ''),
            data.get('salary_expectations', ''),
            data.get('additional_info', ''),
            data.get('status', 'новая анкета'),
            data.get('score', 0),
            data.get('tags', ''),
            data.get('level', ''),
            candidate_id,
        ))

        # keep only one row per Telegram user/chat
        cursor.execute(
            '''
            DELETE FROM candidates
            WHERE tg_user_id = ? AND tg_chat_id = ? AND id <> ?
            ''',
            (tg_user_id, tg_chat_id, candidate_id),
        )
    else:
        cursor.execute('''
            INSERT INTO candidates (
                tg_user_id, tg_chat_id, timestamp, username, candidate_name, first_name, last_name, age,
                who_are_you, what_are_you_looking_for, direction, experience, skills, resume_links,
                resume_file_id, resume_message_link, test_answers, work_style,
                multi_task_style, unknown_task_action, work_preference, work_start_priority,
                contacts,
                clarifying_answers, salary_expectations, additional_info, status, score, tags, level
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('tg_user_id'),
            data.get('tg_chat_id'),
            data.get('timestamp'),
            data.get('username', ''),
            data.get('candidate_name', ''),
            data.get('first_name', ''),
            data.get('last_name', ''),
            data.get('age'),
            data.get('who_are_you', ''),
            data.get('what_are_you_looking_for', ''),
            data.get('direction', ''),
            data.get('experience', ''),
            data.get('skills', ''),
            data.get('resume_links', ''),
            data.get('resume_file_id', ''),
            data.get('resume_message_link', ''),
            data.get('test_answers', ''),
            data.get('work_style', ''),
            data.get('multi_task_style', ''),
            data.get('unknown_task_action', ''),
            data.get('work_preference', ''),
            data.get('work_start_priority', ''),
            data.get('contacts', ''),
            data.get('clarifying_answers', ''),
            data.get('salary_expectations', ''),
            data.get('additional_info', ''),
            data.get('status', 'новая анкета'),
            data.get('score', 0),
            data.get('tags', ''),
            data.get('level', '')
        ))

        candidate_id = int(cursor.lastrowid)

    conn.commit()
    _sync_snapshot_to_sheets(conn)
    conn.close()
    return int(candidate_id)

def get_candidate(candidate_id: int) -> Optional[Dict]:
    """Get candidate by ID."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM candidates WHERE id = ?', (candidate_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return None


def get_latest_candidate_by_telegram(tg_user_id: int, tg_chat_id: int) -> Optional[Dict]:
    """Get latest candidate by Telegram user/chat IDs."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        '''
        SELECT *
        FROM candidates
        WHERE tg_user_id = ? AND tg_chat_id = ?
        ORDER BY id DESC
        LIMIT 1
        ''',
        (tg_user_id, tg_chat_id),
    )
    row = cursor.fetchone()
    conn.close()

    if row:
        return dict(row)
    return None


def has_completed_questionnaire(tg_user_id: int, tg_chat_id: int) -> bool:
    """Check if user already has a completed questionnaire."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        '''
        SELECT 1
        FROM candidates
        WHERE tg_user_id = ? AND tg_chat_id = ?
          AND status IN ('анкета заполнена', 'готовая анкета', 'подходит', 'требует проверки')
        ORDER BY id DESC
        LIMIT 1
        ''',
        (tg_user_id, tg_chat_id),
    )
    row = cursor.fetchone()
    conn.close()
    return row is not None


def update_latest_candidate_resume(
    tg_user_id: int,
    tg_chat_id: int,
    resume_links: str,
    resume_file_id: str,
    resume_message_link: str,
) -> bool:
    """Update resume fields for latest candidate of a Telegram user."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        '''
        UPDATE candidates
        SET resume_links = ?,
            resume_file_id = ?,
            resume_message_link = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = (
            SELECT id
            FROM candidates
            WHERE tg_user_id = ? AND tg_chat_id = ?
            ORDER BY id DESC
            LIMIT 1
        )
        ''',
        (resume_links, resume_file_id, resume_message_link, tg_user_id, tg_chat_id),
    )
    conn.commit()
    _sync_snapshot_to_sheets(conn)
    updated = cursor.rowcount > 0
    conn.close()
    return updated

def get_all_candidates(filters: Optional[Dict] = None) -> List[Dict]:
    """Get all candidates with optional filters."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    query = 'SELECT * FROM candidates'
    params = []
    
    if filters:
        conditions = []
        for key, value in filters.items():
            if value:
                conditions.append(f"{key} LIKE ?")
                params.append(f"%{value}%")
        if conditions:
            query += ' WHERE ' + ' AND '.join(conditions)
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def get_recent_candidates(limit: int = 10) -> List[Dict]:
    """Get latest candidates ordered by creation time (id desc)."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM candidates ORDER BY id DESC LIMIT ?', (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def search_candidates_fuzzy(query: str, limit: int = 10) -> List[Dict]:
    """Fuzzy search by candidate_name/first_name/last_name using RapidFuzz."""
    normalized_query = (query or '').strip().lower()
    if not normalized_query:
        return []

    candidates = get_all_candidates()
    scored: List[tuple[int, Dict[str, Any]]] = []

    for candidate in candidates:
        candidate_name = (candidate.get('candidate_name') or '').strip().lower()
        first_name = (candidate.get('first_name') or '').strip().lower()
        last_name = (candidate.get('last_name') or '').strip().lower()
        full_name = f"{first_name} {last_name}".strip()

        scores = [
            fuzz.ratio(normalized_query, candidate_name),
            fuzz.partial_ratio(normalized_query, candidate_name),
            fuzz.ratio(normalized_query, first_name),
            fuzz.ratio(normalized_query, last_name),
            fuzz.partial_ratio(normalized_query, full_name),
        ]
        best = int(max(scores))
        if best >= 55:
            scored.append((best, candidate))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [item[1] for item in scored[:limit]]

def update_candidate_status(candidate_id: int, new_status: str, notes: str = '') -> bool:
    """Update candidate status."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE candidates 
        SET status = ?, manager_notes = ?, updated_at = CURRENT_TIMESTAMP 
        WHERE id = ?
    ''', (new_status, notes, candidate_id))
    
    conn.commit()
    _sync_snapshot_to_sheets(conn)
    updated = cursor.rowcount > 0
    conn.close()
    return updated

def update_candidate_score(candidate_id: int, score: int, tags: str, level: str) -> bool:
    """Update candidate score, tags and level."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE candidates 
        SET score = ?, tags = ?, level = ?, updated_at = CURRENT_TIMESTAMP 
        WHERE id = ?
    ''', (score, tags, level, candidate_id))
    
    conn.commit()
    _sync_snapshot_to_sheets(conn)
    updated = cursor.rowcount > 0
    conn.close()
    return updated

def search_candidates(query: str, direction: str = '', status: str = '') -> List[Dict]:
    """Search candidates by various criteria."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    sql = 'SELECT * FROM candidates WHERE 1=1'
    params = []
    
    if query:
        sql += ' AND (skills LIKE ? OR direction LIKE ? OR experience LIKE ? OR first_name LIKE ? OR last_name LIKE ?)'
        params.extend([f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%'])
    
    if direction:
        sql += ' AND direction = ?'
        params.append(direction)
    
    if status:
        sql += ' AND status = ?'
        params.append(status)
    
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

def create_vacancy(data: Dict[str, Any]) -> int:
    """Create a new vacancy."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO vacancies (title, direction, required_skills, experience_level, status)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        data.get('title', ''),
        data.get('direction', ''),
        data.get('required_skills', ''),
        data.get('experience_level', ''),
        data.get('status', 'активная')
    ))
    
    vacancy_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return vacancy_id

def match_candidates_to_vacancy(vacancy_id: int) -> List[Dict]:
    """Find matching candidates for a vacancy based on skills and direction."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get vacancy details
    cursor.execute('SELECT * FROM vacancies WHERE id = ?', (vacancy_id,))
    vacancy = cursor.fetchone()
    
    if not vacancy:
        conn.close()
        return []
    
    vacancy_dir = vacancy['direction']
    required_skills = set(skill.strip().lower() for skill in vacancy['required_skills'].split(',') if skill.strip())
    
    # Find candidates with matching direction and skills
    cursor.execute('''
        SELECT * FROM candidates 
        WHERE direction = ? 
        AND status IN ('подходит', 'готовая анкета', 'требует проверки')
    ''', (vacancy_dir,))
    
    candidates = cursor.fetchall()
    matches = []
    
    for candidate in candidates:
        candidate_skills = set(skill.strip().lower() for skill in candidate['skills'].split(',') if skill.strip())
        matching_skills = required_skills.intersection(candidate_skills)
        match_score = len(matching_skills) / len(required_skills) if required_skills else 0
        
        if match_score >= 0.3:  # At least 30% skill match
            candidate_dict = dict(candidate)
            candidate_dict['match_score'] = round(match_score * 100, 1)
            candidate_dict['matching_skills'] = list(matching_skills)
            matches.append(candidate_dict)
    
    conn.close()
    # Sort by match score descending
    matches.sort(key=lambda x: x['match_score'], reverse=True)
    return matches

def create_application(candidate_id: int, vacancy_id: int) -> int:
    """Create an application linking candidate to vacancy."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO applications (candidate_id, vacancy_id, status)
        VALUES (?, ?, ?)
    ''', (candidate_id, vacancy_id, 'отправлен работодателю'))
    
    app_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return app_id

def get_applications_by_vacancy(vacancy_id: int) -> List[Dict]:
    """Get all applications for a vacancy."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT a.*, c.first_name, c.last_name, c.direction, c.score, c.skills
        FROM applications a
        JOIN candidates c ON a.candidate_id = c.id
        WHERE a.vacancy_id = ?
        ORDER BY a.created_at DESC
    ''', (vacancy_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

def get_statistics() -> Dict[str, Any]:
    """Get overall statistics."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    stats = {}
    
    # Total candidates
    cursor.execute('SELECT COUNT(*) FROM candidates')
    stats['total_candidates'] = cursor.fetchone()[0]
    
    # Candidates by status
    cursor.execute('SELECT status, COUNT(*) FROM candidates GROUP BY status')
    stats['by_status'] = dict(cursor.fetchall())
    
    # Candidates by direction
    cursor.execute('SELECT direction, COUNT(*) FROM candidates GROUP BY direction')
    stats['by_direction'] = dict(cursor.fetchall())
    
    # Total vacancies
    cursor.execute('SELECT COUNT(*) FROM vacancies WHERE status = "активная"')
    stats['active_vacancies'] = cursor.fetchone()[0]
    
    # Total applications
    cursor.execute('SELECT COUNT(*) FROM applications')
    stats['total_applications'] = cursor.fetchone()[0]
    
    conn.close()
    return stats
