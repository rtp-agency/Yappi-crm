# Инструкция по запуску TG-Bot-Yuppy

## Что нужно передать для запуска

### 1. Файлы проекта
Весь репозиторий: https://github.com/rtp-agency/Yappi-crm

### 2. Google API credentials (credentials.json)
Файл с ключами доступа к Google Sheets API. **Этот файл нужно получить отдельно!**

### 3. Telegram Bot Token
Токен бота от @BotFather

### 4. ID таблицы Google Sheets
ID из URL таблицы: `https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit`

---

## Пошаговая установка

### Шаг 1: Клонировать репозиторий
```bash
git clone https://github.com/rtp-agency/Yappi-crm.git
cd Yappi-crm
```

### Шаг 2: Создать виртуальное окружение
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### Шаг 3: Установить зависимости
```bash
pip install -r requirements.txt
```

### Шаг 4: Настроить Google API (credentials.json)

1. Перейти в [Google Cloud Console](https://console.cloud.google.com/)
2. Создать проект или выбрать существующий
3. Включить **Google Sheets API**:
   - APIs & Services → Enable APIs → найти "Google Sheets API" → Enable
4. Создать Service Account:
   - APIs & Services → Credentials → Create Credentials → Service Account
   - Дать имя (например: "yuppy-bot")
   - Нажать Create → Done
5. Создать ключ:
   - Нажать на созданный Service Account
   - Keys → Add Key → Create new key → JSON
   - Скачать файл и переименовать в `credentials.json`
6. Положить `credentials.json` в корень проекта
7. **ВАЖНО:** Скопировать email Service Account (вида `xxx@project.iam.gserviceaccount.com`)
8. Открыть Google таблицу → Поделиться → добавить этот email с правами "Редактор"

### Шаг 5: Создать файл .env
Скопировать `.env.example` в `.env` и заполнить:

```bash
cp .env.example .env
```

Содержимое `.env`:
```env
# Токен бота (получить у @BotFather в Telegram)
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz

# ID пользователей с доступом к боту (через запятую)
ADMIN_IDS=906038550

# ID Google таблицы (из URL)
SPREADSHEET_ID=1ABC...xyz

# Путь к файлу credentials.json
CREDENTIALS_FILE=credentials.json

# Настройки кэша (можно оставить по умолчанию)
CACHE_DB_PATH=data/cache.db
CACHE_SYNC_INTERVAL=300
```

### Шаг 6: Создать папку для данных
```bash
mkdir data
```

### Шаг 7: Запустить бота
```bash
python -m src.main
```

---

## Структура Google таблицы

Бот работает с таблицей определённой структуры. Листы:

| Лист | Назначение |
|------|------------|
| GENERAL | Основной лист с данными и формулами |
| DESIGNERS | Список дизайнеров |
| CLIENTS | Список заказчиков |
| EXPENSES | Расходы |
| WHITELIST | Белый список заказчиков |
| BLACKLIST | Чёрный список заказчиков |

---

## Команды для управления

### Запуск бота
```bash
# Windows PowerShell
cd C:\path\to\Yappi-crm
venv\Scripts\activate
python -m src.main

# Linux/Mac
cd /path/to/Yappi-crm
source venv/bin/activate
python -m src.main
```

### Остановка бота
`Ctrl+C` в терминале

### Запуск в фоне (Linux)
```bash
nohup python -m src.main > bot.log 2>&1 &
```

### Просмотр логов (Linux)
```bash
tail -f bot.log
```

---

## Чек-лист перед запуском

- [ ] Python 3.10+ установлен
- [ ] Виртуальное окружение создано и активировано
- [ ] Зависимости установлены (`pip install -r requirements.txt`)
- [ ] Файл `credentials.json` в корне проекта
- [ ] Email Service Account добавлен в таблицу как "Редактор"
- [ ] Файл `.env` создан и заполнен
- [ ] Папка `data/` существует
- [ ] Google Sheets API включён в проекте

---

## Возможные ошибки

### "Invalid token"
Неверный BOT_TOKEN в `.env`. Проверь токен у @BotFather.

### "The caller does not have permission"
Email Service Account не добавлен в Google таблицу. Открой таблицу → Поделиться → добавь email.

### "credentials.json not found"
Файл `credentials.json` отсутствует или путь в `.env` неверный.

### "User not in whitelist"
Telegram ID пользователя не добавлен в ADMIN_IDS в `.env`.

---

## Контакты

Репозиторий: https://github.com/rtp-agency/Yappi-crm
