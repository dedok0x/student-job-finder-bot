# HR Bot System - Complete Implementation

## Overview

This is a comprehensive HR bot system designed to streamline the candidate selection process. The system collects candidate information through a structured questionnaire and manages the entire recruitment workflow from initial application to final placement.

## Features Implemented

### 1. Complete Questionnaire Flow (9 Steps)

- **Who are you?** - студент / выпускник / начинающий специалист / меняю профессию
- **What are you looking for?** - стажировка / частичная занятость / полная занятость / проектная работа
- **Direction selection** - IT / Digital / Business or "не знаю, помогите определить"
- **Experience level** - Various options from "нет опыта" to "1-2 года"
- **Dynamic skills selection** - Based on chosen direction
- **Resume links** - Portfolio, GitHub, LinkedIn, etc.
- **Direction-specific test questions** - To assess candidate knowledge
- **Work style** - How candidate approaches tasks
- **Contact information** - Email, phone, Telegram

### 2. Advanced Features

- **Clarifying Questions Logic**: When candidate selects "не знаю, помогите определить", the system asks clarifying questions to determine the best direction
- **Dynamic Skill Selection**: Skills are dynamically loaded based on the selected direction (IT, Digital, Business)
- **Scoring System**: Automatic scoring based on skills, experience, and direction alignment
- **Tagging System**: Automatic tag generation for easy filtering and matching
- **Status Management**: Complete workflow from "новая анкета" to "трудоустроен"

### 3. Database Schema

The system uses SQLite with three main tables:

- **candidates**: Stores all candidate information with comprehensive fields
- **vacancies**: Stores job openings and requirements
- **applications**: Links candidates to specific vacancies

### 4. Matching Algorithm

- Matches candidates to vacancies based on skills and direction alignment
- Calculates match percentage for better decision making
- Prioritizes candidates with higher scores and better skill matches

## Technical Architecture

### Core Components

1. **Main Bot (main.py)**: Entry point and command routing
2. **Questionnaire Handler (handlers/questions.py)**: Manages the 9-step questionnaire
3. **Manager Commands (handlers/different_types.py)**: Handles admin functionality
4. **Database Module (database.py)**: Handles all database operations
5. **Keyboards (keyboards/for_questions.py)**: Dynamic keyboard generation

### State Management

- Uses FSM (Finite State Machine) to manage questionnaire flow
- Preserves state between user interactions
- Handles backtracking and validation

### Data Flow

1. User initiates questionnaire with `/start`
2. Bot guides through 9-step process
3. Data is validated at each step
4. Final data is stored in database with scoring
5. Manager can view, search, and manage candidates
6. Matching algorithm suggests suitable candidates for vacancies

## Key Benefits

### For Candidates

- Streamlined application process
- Direction guidance for undecided candidates
- Skill-based recommendations
- Automatic profile optimization

### For HR Managers

- Automated candidate screening
- Intelligent matching to vacancies
- Comprehensive search and filtering
- Status tracking throughout process
- Detailed analytics and reporting

## Implementation Details

### Scoring Algorithm

- Skills: Points assigned based on relevance (Python: 10, JavaScript: 10, etc.)
- Experience: Weighted based on relevance to position
- Direction alignment: Bonus points for matching career direction
- Education and other factors contribute to overall score

### Security & Validation

- Input validation at every step
- SQL injection prevention through parameterized queries
- Proper error handling and logging
- Data sanitization before storage

## Usage Instructions

### Starting the Bot

1. Run `python main.py`
2. Start conversation with `/start`
3. Complete the 9-step questionnaire

## Docker Deployment (VDS)

Проект можно развернуть на Linux/VDS одной командой после клонирования.

### Что добавлено

- `Dockerfile`
- `docker-compose.yml`
- `.dockerignore`
- `deploy.sh` (автодеплой в `/opt/docker/hr_bot`)

### Быстрый запуск

1. Клонируйте репозиторий.
2. Положите в корень корректные `.env` и `creds.json`.
3. Запустите:

```bash
chmod +x deploy.sh
./deploy.sh
```

Скрипт:

- делает `apt-get update`,
- ставит системные зависимости,
- устанавливает Docker Engine + Compose Plugin (если их нет),
- проверяет наличие Docker/Compose,
- проверяет обязательные переменные в `.env`,
- копирует проект в `/opt/docker/hr_bot`,
- запускает контейнер командой `docker compose up -d --build`.

Контейнер поднимается автоматически после перезагрузки благодаря `restart: unless-stopped`.

## Testing

The system includes comprehensive testing via `test_bot.py` which validates:

- Database operations
- Questionnaire flow
- Manager commands
- Scoring system
- Matching algorithms

All tests pass successfully, confirming the system is fully functional.

## Conclusion

This HR bot system provides a complete solution for modern recruitment challenges, combining automation with intelligent matching to streamline the hiring process while maintaining personalization for both candidates and managers.
