# Умный суммаризатор тендерной документации

Сервис для автоматического извлечения ключевых параметров из тендерной документации (контрактов) с использованием локальной LLM.

## Краткое описание

Приложение загружает PDF-файлы тендерной документации, извлекает из них текст и с помощью локальной языковой модели (Ollama) определяет:

- **Сумму контракта** — общая стоимость в рублях;
- **Сроки** — дата начала и дата окончания работ;
- **Требования** — ключевые требования к исполнителю;
- **Штрафы** — условия штрафов и неустоек.

Результаты сохраняются в базу данных PostgreSQL и доступны через REST API.

## Логика решения

Система построена по асинхронному микросервисному паттерну и состоит из двух основных компонентов:

| Компонент | Роль |
|---|---|
| **API-бэкенд** (`app/main.py`) | FastAPI-сервис, принимает файлы, возвращает результаты |
| **Consumer** (`app/consumer_rabbit.py`) | Асинхронный воркер, читает задачи из RabbitMQ, обрабатывает документы |

**Инфраструктура:**

| Сервис | Назначение |
|---|---|
| PostgreSQL | Хранение извлечённых данных контрактов |
| RabbitMQ | Очередь задач между бэкендом и consumer |
| Redis | Кэш / дополнительные данные |
| Ollama | Локальная LLM для анализа текста |

> DI-контейнер — **Dishka**. Все зависимости (сессии БД, брокер, настройки) инжектируются автоматически.

## Алгоритм

### 1. Загрузка файла (POST `/api/v1/tender-contracts`)

```
Клиент → POST /tender-contracts (PDF-файл)
```

1. Файл сохраняется во временное хранилище (`/tmp/{request_id}.pdf`).
2. Вычисляется SHA-256 хеш содержимого файла.
3. Выполняется поиск записи в БД по хешу:
   - **Найдена** → возвращается существующий `id` контракта (дубликаты не обрабатываются повторно).
   - **Не найдена** → в очередь RabbitMQ публикуется сообщение с `id`, `file_hash`, `file_name`, `file_path`.
4. Клиенту возвращается `id` (UUID) контракта.

### 2. Обработка файла (Consumer)

```
RabbitMQ → tender_contract_new_handler
```

1. **Получение сообщения** из очереди `tender_contracts.new`.
2. **Извлечение текста** из PDF через библиотеку `pypdfium2` (посимвольное чтение по страницам).
3. **Запрос к LLM** (Ollama):
   - Формируется промпт из настроек + текст документа.
   - Модель возвращает JSON с полями: `amount`, `start_date`, `end_date`, `requirements`, `penalties`.
4. **Парсинг и валидация**:
   - JSON-ответ парсится через Pydantic-схему (`TenderContractSchema`).
   - Типы приводятся к `Decimal`, `date`, `list[str]`.
5. **Сохранение в БД**:
   - Если запись по `file_hash` уже существует — обновляются поля, ставится `processed_at`.
   - Если записи нет — создаётся новая запись `Contract`.
6. **Очистка**: временный PDF-файл удаляется.

### 3. Получение результата (GET `/api/v1/tender-contracts/{entity_id}`)

```
Клиент → GET /tender-contracts/{id}
```

1. Запрос к БД по `id` (или `file_hash`).
2. Возвращается JSON с полями контракта: сумма, даты, требования, штрафы.

## Установка

Процесс установки описан для операционной системы `Linux` и предполагает использование следующих каталогов:
- `/opt/tender-documentation-summarizer` - каталог с исходным кодом проекта
- `/opt/tender-documentation-summarizer-data` - каталог для хранения данных проекта (PostgreSQL, Redis, RabbitMQ)

В файле `.env.sample` значение каталога для хранения данных указано в переменной `PROJECT_DATA_DIR=/opt/tender-documentation-summarizer-data`. 
Для изменения каталога хранения данных необходимо изменить значение переменной `PROJECT_DATA_DIR`.
Значения остальные переменных с каталогами указаны относительно значения переменной `PROJECT_DATA_DIR`.

1. **Создайте каталоги для данных:**

   ```bash
   cd /opt
   sudo mkdir -p /opt/tender-documentation-summarizer-data/{backups,db,files,rabbitmq,redis}
   sudo chown -R {user}:{group} tender-documentation-summarizer-data
   ```

2. **Клонируйте репозиторий:**

   ```bash
   cd /opt
   sudo git clone https://github.com/serker72/tender-documentation-summarizer.git
   sudo chown -R {user}:{group} tender-documentation-summarizer
   ```

3. **Настройте переменные окружения:**

   ```bash
   cd /opt/tender-documentation-summarizer
   cp .env.example .env
   ```

4. **Примените миграции БД:**

   ```bash
   cd /opt/tender-documentation-summarizer
   docker compose -f docker-compose.db-update.yml up
   ```

## Запуск

```bash
# Заполнить переменные в .env
cd /opt/tender-documentation-summarizer
docker compose up -d --build
```

## Останов

```bash
cd /opt/tender-documentation-summarizer
docker compose down
```

## REST API

| Метод | Endpoint | Описание |
|---|---|---|
| `POST` | `/api/v1/tender-contracts` | Загрузка PDF-файла контракта |
| `GET` | `/api/v1/tender-contracts/{id}` | Получение извлечённых данных |
| `GET` | `/api/v1/healthcheck` | Проверка работоспособности |

### Пример: загрузка файла

```bash
curl -X POST "http://localhost:8000/api/v1/tender-contracts" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -F "file=@08-1418-2026.pdf"
```

### Пример: получение результата

```bash
curl "http://localhost:8000/api/v1/tender-contracts/{contract_id}" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### Ответ

```json
{
  "amount": 1500000.00,
  "start_date": "2026-09-01",
  "end_date": "2026-12-31",
  "requirements": [
    "Наличие лицензии...",
    "Опыт работы от 3 лет"
  ],
  "penalties": [
    "Штраф 0.1% за каждый день просрочки"
  ]
}
```

## Структура проекта

```
app/
├── main.py                  # FastAPI-бэкенд
├── consumer_rabbit.py       # Воркер обработки файлов
├── schemas.py               # Pydantic-схемы
├── models.py                # SQLAlchemy-модели
├── providers.py             # DI-провайдеры (Dishka)
├── settings.py              # Настройки из .env
├── middlewares/             # Мидлвары (API-ключ, тайминги)
└── helpers/                 # Утилиты
```

## Безопасность

- Запросы к API требуют ключ авторизации в заголовке.
- Ключ настраивается через переменные `BACKEND_AUTHENTICATION_HEADER_KEY` и `BACKEND_AUTHENTICATION_HEADER_VALUE`.
- Без аутентификации доступны только: `/`, `/docs`, `/redoc`, `/openapi.json`, `/healthcheck`.
