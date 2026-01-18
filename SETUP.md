# Запуск бота Yuppy CRM

## Вам переданы файлы:
- `credentials.json` - ключ доступа к Google Sheets
- `.env` - настройки бота

---

## Установка

### 1. Установить Python
Скачать и установить Python 3.10+: https://www.python.org/downloads/

При установке поставить галочку **"Add Python to PATH"**

### 2. Скачать проект
```bash
git clone https://github.com/rtp-agency/Yappi-crm.git
cd Yappi-crm
```

### 3. Установить зависимости
```bash
pip install -r requirements.txt
```

### 4. Положить файлы в папку проекта
Скопировать полученные файлы `credentials.json` и `.env` в папку `Yappi-crm`

### 5. Создать папку data
```bash
mkdir data
```

### 6. Запустить бота
```bash
python -m src.main
```

Если всё правильно - увидите в консоли:
```
INFO | Bot starting...
INFO | Google Sheets client ready
```

---

## Управление

| Действие | Команда |
|----------|---------|
| Запустить | `python -m src.main` |
| Остановить | `Ctrl+C` |

---

## Добавить нового пользователя

1. Пользователь пишет боту [@userinfobot](https://t.me/userinfobot) в Telegram
2. Получает свой ID (число, например: `123456789`)
3. Открыть файл `.env`, найти строку `ADMIN_IDS=...`
4. Добавить новый ID через запятую:
   ```
   ADMIN_IDS=906038550,123456789
   ```
5. Перезапустить бота (`Ctrl+C`, потом `python -m src.main`)

---

## Ошибки

| Ошибка | Решение |
|--------|---------|
| `User not in whitelist` | Добавьте Telegram ID в ADMIN_IDS (см. выше) |
| `credentials.json not found` | Файл не в папке проекта |
| `No module named...` | Выполните `pip install -r requirements.txt` |
