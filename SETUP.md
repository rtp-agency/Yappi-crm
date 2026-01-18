# Запуск бота Yuppy CRM

## Данные для настройки

| Что | Значение |
|-----|----------|
| Репозиторий | https://github.com/rtp-agency/Yappi-crm |
| BOT_TOKEN | *(получить от владельца)* |
| SPREADSHEET_ID | *(получить от владельца)* |
| credentials.json | *(получить от владельца)* |

---

## Установка (5 минут)

```bash
# 1. Скачать проект
git clone https://github.com/rtp-agency/Yappi-crm.git
cd Yappi-crm

# 2. Установить зависимости
pip install -r requirements.txt

# 3. Создать папку data
mkdir data

# 4. Положить credentials.json в папку проекта

# 5. Создать файл .env (содержимое ниже)

# 6. Запустить
python -m src.main
```

---

## Файл .env

Создать файл `.env` в папке проекта:

```
BOT_TOKEN=сюда_токен_бота
SPREADSHEET_ID=сюда_id_таблицы
ADMIN_IDS=сюда_telegram_id
CREDENTIALS_FILE=credentials.json
```

---

## Как дать доступ к боту

Бот работает только для пользователей из `ADMIN_IDS`.

**Узнать Telegram ID:**
1. Написать боту @userinfobot в Telegram
2. Он ответит число (например: `906038550`)

**Добавить пользователя:**
```
ADMIN_IDS=906038550,123456789,555555555
```
*(ID через запятую, без пробелов)*

После изменения - перезапустить бота (`Ctrl+C`, потом `python -m src.main`)

---

## Ошибки

| Ошибка | Что делать |
|--------|------------|
| User not in whitelist | Добавь Telegram ID в ADMIN_IDS |
| credentials.json not found | Положи файл в папку проекта |
| Invalid token | Проверь BOT_TOKEN |
