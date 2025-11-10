#!/usr/bin/env bash
set -euo pipefail

BUILD=false
LOGS=false
DOWN=false
UP=false
CLIENT=1

while [[ "$#" -gt 0 ]]; do
  case $1 in
    --build) BUILD=true ;;
    --logs) LOGS=true ;;
    --down) DOWN=true ;;
    --up) UP=true ;;
    --client)
      shift
      if [[ -z "${1:-}" || ! "$1" =~ ^[0-9]+$ ]]; then
        echo "Ошибка: --client требует число (например, --client 3)"
        exit 1
      fi
      CLIENT="$1"
      ;;
    *) echo "Неизвестный флаг: $1"; exit 1 ;;
  esac
  shift
done

if [ "$DOWN" = true ]; then
  docker compose -f docker-compose.yml down
  exit 0
fi

if [ "$BUILD" = true ]; then
  docker compose -f docker-compose.yml build
fi

if [ "$UP" = true ]; then
  docker compose -f docker-compose.yml up -d --scale client="${CLIENT}"
  docker compose -f docker-compose.yml ps
fi

if [ "$LOGS" = true ]; then
  echo "Показываю логи..."
  docker compose -f docker-compose.yml logs -f
else
  if [ "$UP" = true ]; then
    echo "Стек запущен успешно! Клиентов: ${CLIENT}"
  fi
fi
