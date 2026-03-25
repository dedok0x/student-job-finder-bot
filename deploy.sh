#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/docker/hr_bot"
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ "${EUID}" -ne 0 ]]; then
  SUDO="sudo"
else
  SUDO=""
fi

echo "[1/9] Проверка пакетного менеджера..."
if ! command -v apt-get >/dev/null 2>&1; then
  echo "Скрипт рассчитан на Debian/Ubuntu (apt-get)."
  exit 1
fi

echo "[2/9] Обновление apt и установка базовых зависимостей..."
$SUDO apt-get update -y
$SUDO apt-get install -y ca-certificates curl gnupg lsb-release

echo "[3/9] Установка Docker Engine и Compose Plugin (если не установлены)..."
if ! command -v docker >/dev/null 2>&1; then
  $SUDO install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | $SUDO gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  $SUDO chmod a+r /etc/apt/keyrings/docker.gpg

  ARCH="$(dpkg --print-architecture)"
  CODENAME="$(. /etc/os-release && echo "$VERSION_CODENAME")"
  echo "deb [arch=${ARCH} signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu ${CODENAME} stable" | $SUDO tee /etc/apt/sources.list.d/docker.list >/dev/null

  $SUDO apt-get update -y
  $SUDO apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi

if docker compose version >/dev/null 2>&1; then
  COMPOSE_CMD="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE_CMD="docker-compose"
else
  echo "Не найден docker compose."
  exit 1
fi

echo "[4/9] Проверка обязательных файлов..."
[[ -f "$SRC_DIR/.env" ]] || { echo "Файл .env не найден в корне репозитория"; exit 1; }
[[ -f "$SRC_DIR/creds.json" ]] || { echo "Файл creds.json не найден в корне репозитория"; exit 1; }
[[ -f "$SRC_DIR/docker-compose.yml" ]] || { echo "Файл docker-compose.yml не найден"; exit 1; }
[[ -f "$SRC_DIR/Dockerfile" ]] || { echo "Файл Dockerfile не найден"; exit 1; }

echo "[5/9] Проверка обязательных переменных .env..."
grep -q '^BOT_TOKEN=' "$SRC_DIR/.env" || { echo "В .env отсутствует BOT_TOKEN"; exit 1; }
grep -q '^MANAGER_AUTH_CODE=' "$SRC_DIR/.env" || { echo "В .env отсутствует MANAGER_AUTH_CODE"; exit 1; }
grep -q '^GOOGLE_SERVICE_ACCOUNT_FILE=' "$SRC_DIR/.env" || { echo "В .env отсутствует GOOGLE_SERVICE_ACCOUNT_FILE"; exit 1; }

echo "[6/9] Подготовка директории $APP_DIR..."
$SUDO mkdir -p "$APP_DIR"
$SUDO mkdir -p "$APP_DIR/exports"

echo "[7/9] Копирование проекта в $APP_DIR..."
tar --exclude='.git' --exclude='__pycache__' --exclude='.venv' --exclude='venv' -cf - -C "$SRC_DIR" . | $SUDO tar -xf - -C "$APP_DIR"

echo "[8/9] Включение автозапуска Docker..."
$SUDO systemctl enable docker >/dev/null 2>&1 || true
$SUDO systemctl start docker >/dev/null 2>&1 || true

echo "[9/9] Сборка и запуск контейнера..."
cd "$APP_DIR"
$SUDO $COMPOSE_CMD up -d --build

echo "Готово. Контейнер hr_bot запущен и будет подниматься после reboot (restart: unless-stopped)."
