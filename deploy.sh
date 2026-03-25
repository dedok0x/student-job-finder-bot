#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/docker/hr_bot"
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[1/7] Проверка Docker..."
if ! command -v docker >/dev/null 2>&1; then
  echo "Docker не найден. Установите Docker Engine и повторите запуск."
  exit 1
fi

if docker compose version >/dev/null 2>&1; then
  COMPOSE_CMD="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE_CMD="docker-compose"
else
  echo "Не найден docker compose. Установите Docker Compose и повторите запуск."
  exit 1
fi

echo "[2/7] Проверка обязательных файлов..."
[[ -f "$SRC_DIR/.env" ]] || { echo "Файл .env не найден в корне репозитория"; exit 1; }
[[ -f "$SRC_DIR/creds.json" ]] || { echo "Файл creds.json не найден в корне репозитория"; exit 1; }
[[ -f "$SRC_DIR/docker-compose.yml" ]] || { echo "Файл docker-compose.yml не найден"; exit 1; }
[[ -f "$SRC_DIR/Dockerfile" ]] || { echo "Файл Dockerfile не найден"; exit 1; }

echo "[3/7] Проверка обязательных переменных .env..."
grep -q '^BOT_TOKEN=' "$SRC_DIR/.env" || { echo "В .env отсутствует BOT_TOKEN"; exit 1; }
grep -q '^MANAGER_AUTH_CODE=' "$SRC_DIR/.env" || { echo "В .env отсутствует MANAGER_AUTH_CODE"; exit 1; }
grep -q '^GOOGLE_SERVICE_ACCOUNT_FILE=' "$SRC_DIR/.env" || { echo "В .env отсутствует GOOGLE_SERVICE_ACCOUNT_FILE"; exit 1; }

echo "[4/7] Подготовка директории $APP_DIR..."
sudo mkdir -p "$APP_DIR"
sudo mkdir -p "$APP_DIR/exports"

echo "[5/7] Копирование проекта в $APP_DIR..."
tar --exclude='.git' --exclude='__pycache__' --exclude='.venv' --exclude='venv' -cf - -C "$SRC_DIR" . | sudo tar -xf - -C "$APP_DIR"

echo "[6/7] Включение автозапуска Docker..."
sudo systemctl enable docker >/dev/null 2>&1 || true
sudo systemctl start docker >/dev/null 2>&1 || true

echo "[7/7] Сборка и запуск контейнера..."
cd "$APP_DIR"
sudo $COMPOSE_CMD up -d --build

echo "Готово. Контейнер hr_bot запущен и будет подниматься после reboot (restart: unless-stopped)."
