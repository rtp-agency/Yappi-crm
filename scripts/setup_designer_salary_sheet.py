"""
Script to set up the "ЗП дизайнерам" sheet with beautiful formatting.
Run: python scripts/setup_designer_salary_sheet.py
"""
import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from src.config.settings import get_settings


def get_sheet_id(service, spreadsheet_id, sheet_name):
    """Get sheet ID by name."""
    spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    for sheet in spreadsheet['sheets']:
        if sheet['properties']['title'] == sheet_name:
            return sheet['properties']['sheetId']
    return None


def setup_designer_salary_sheet():
    """Set up the "ЗП дизайнерам" sheet with proper structure and formatting."""
    print("=" * 60)
    print("   НАСТРОЙКА ЛИСТА 'ЗП дизайнерам'")
    print("=" * 60)

    settings = get_settings()

    # Initialize Google Sheets API
    credentials = Credentials.from_service_account_file(
        settings.CREDENTIALS_FILE,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    service = build("sheets", "v4", credentials=credentials)

    spreadsheet_id = settings.SPREADSHEET_ID
    sheet_name = "ЗП Дизайнерам"

    # 1. Check if sheet exists, create if not
    print(f"\n1. Проверка листа '{sheet_name}'...")

    # Show all existing sheets
    spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    print("   Существующие листы:")
    for sheet in spreadsheet['sheets']:
        title = sheet['properties']['title']
        print(f"      - '{title}'")

    sheet_id = get_sheet_id(service, spreadsheet_id, sheet_name)

    if sheet_id is None:
        print(f"\n   ⚠️ Лист '{sheet_name}' не найден, создаю...")
        # Create new sheet
        create_request = {
            "requests": [{
                "addSheet": {
                    "properties": {
                        "title": sheet_name,
                        "gridProperties": {
                            "rowCount": 100,
                            "columnCount": 15
                        }
                    }
                }
            }]
        }
        response = service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=create_request
        ).execute()
        sheet_id = response['replies'][0]['addSheet']['properties']['sheetId']
        print(f"   ✅ Лист создан (ID: {sheet_id})")
    else:
        print(f"   ✅ Лист найден (ID: {sheet_id})")

    # Colors (RGB 0-1 format)
    BROWN = {"red": 0.6, "green": 0.4, "blue": 0.2}  # Коричневый как в других листах
    DARK_BROWN = {"red": 0.45, "green": 0.3, "blue": 0.15}
    LIGHT_ORANGE = {"red": 1.0, "green": 0.9, "blue": 0.8}
    WHITE = {"red": 1.0, "green": 1.0, "blue": 1.0}
    LIGHT_GRAY = {"red": 0.95, "green": 0.95, "blue": 0.95}

    # 2. Clear existing content and formatting
    print("\n2. Очистка листа...")
    service.spreadsheets().values().clear(
        spreadsheetId=spreadsheet_id,
        range=f"'{sheet_name}'!A1:Z100"
    ).execute()

    # 3. Set column widths
    print("\n3. Настройка ширины колонок...")
    requests = [
        # Column A (operation_id) - narrow, hidden
        {"updateDimensionProperties": {
            "range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 0, "endIndex": 1},
            "properties": {"pixelSize": 50, "hiddenByUser": True},
            "fields": "pixelSize,hiddenByUser"
        }},
        # Columns B-E - narrow (protected area)
        {"updateDimensionProperties": {
            "range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 1, "endIndex": 5},
            "properties": {"pixelSize": 80},
            "fields": "pixelSize"
        }},
        # Column F - Дата выплаты (medium)
        {"updateDimensionProperties": {
            "range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 5, "endIndex": 6},
            "properties": {"pixelSize": 140},
            "fields": "pixelSize"
        }},
        # Column G - Дизайнер (wide)
        {"updateDimensionProperties": {
            "range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 6, "endIndex": 7},
            "properties": {"pixelSize": 180},
            "fields": "pixelSize"
        }},
        # Column H - Сумма (medium)
        {"updateDimensionProperties": {
            "range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 7, "endIndex": 8},
            "properties": {"pixelSize": 140},
            "fields": "pixelSize"
        }},
    ]

    # 4. Set row heights
    print("\n4. Настройка высоты строк...")
    requests.extend([
        # Row 3 - title row (tall)
        {"updateDimensionProperties": {
            "range": {"sheetId": sheet_id, "dimension": "ROWS", "startIndex": 2, "endIndex": 3},
            "properties": {"pixelSize": 50},
            "fields": "pixelSize"
        }},
        # Row 5 - summary row
        {"updateDimensionProperties": {
            "range": {"sheetId": sheet_id, "dimension": "ROWS", "startIndex": 4, "endIndex": 5},
            "properties": {"pixelSize": 35},
            "fields": "pixelSize"
        }},
        # Row 8 - spacer
        {"updateDimensionProperties": {
            "range": {"sheetId": sheet_id, "dimension": "ROWS", "startIndex": 7, "endIndex": 8},
            "properties": {"pixelSize": 15},
            "fields": "pixelSize"
        }},
        # Row 9 - headers (medium)
        {"updateDimensionProperties": {
            "range": {"sheetId": sheet_id, "dimension": "ROWS", "startIndex": 8, "endIndex": 9},
            "properties": {"pixelSize": 40},
            "fields": "pixelSize"
        }},
    ])

    # 5. Title block (F3:H3) - merged, brown background
    print("\n5. Создание заголовка...")
    requests.extend([
        # Merge F3:H3 for title
        {"mergeCells": {
            "range": {"sheetId": sheet_id, "startRowIndex": 2, "endRowIndex": 3, "startColumnIndex": 5, "endColumnIndex": 8},
            "mergeType": "MERGE_ALL"
        }},
        # Format title cell
        {"repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": 2, "endRowIndex": 3, "startColumnIndex": 5, "endColumnIndex": 8},
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": BROWN,
                    "textFormat": {
                        "foregroundColor": WHITE,
                        "fontSize": 16,
                        "bold": True
                    },
                    "horizontalAlignment": "CENTER",
                    "verticalAlignment": "MIDDLE"
                }
            },
            "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment)"
        }},
    ])

    # 6. Summary row (F5:H5)
    print("\n6. Создание строки с итогами...")
    requests.extend([
        # F5 - label background
        {"repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": 4, "endRowIndex": 5, "startColumnIndex": 5, "endColumnIndex": 6},
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": LIGHT_ORANGE,
                    "textFormat": {"fontSize": 11, "bold": True},
                    "horizontalAlignment": "RIGHT",
                    "verticalAlignment": "MIDDLE"
                }
            },
            "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment)"
        }},
        # G5 - "Всего выплачено:" label
        {"repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": 4, "endRowIndex": 5, "startColumnIndex": 6, "endColumnIndex": 7},
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": LIGHT_ORANGE,
                    "textFormat": {"fontSize": 11, "bold": True},
                    "horizontalAlignment": "RIGHT",
                    "verticalAlignment": "MIDDLE"
                }
            },
            "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment)"
        }},
        # H5 - sum value
        {"repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": 4, "endRowIndex": 5, "startColumnIndex": 7, "endColumnIndex": 8},
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": LIGHT_ORANGE,
                    "textFormat": {"fontSize": 12, "bold": True},
                    "horizontalAlignment": "CENTER",
                    "verticalAlignment": "MIDDLE",
                    "numberFormat": {"type": "CURRENCY", "pattern": "$#,##0.00"}
                }
            },
            "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment,numberFormat)"
        }},
        # Border around summary
        {"updateBorders": {
            "range": {"sheetId": sheet_id, "startRowIndex": 4, "endRowIndex": 5, "startColumnIndex": 5, "endColumnIndex": 8},
            "top": {"style": "SOLID", "width": 1, "color": BROWN},
            "bottom": {"style": "SOLID", "width": 1, "color": BROWN},
            "left": {"style": "SOLID", "width": 1, "color": BROWN},
            "right": {"style": "SOLID", "width": 1, "color": BROWN},
        }},
    ])

    # 7. Headers row (F9:H9)
    print("\n7. Создание заголовков таблицы...")
    requests.extend([
        # Headers background and text
        {"repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": 8, "endRowIndex": 9, "startColumnIndex": 5, "endColumnIndex": 8},
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": DARK_BROWN,
                    "textFormat": {
                        "foregroundColor": WHITE,
                        "fontSize": 11,
                        "bold": True
                    },
                    "horizontalAlignment": "CENTER",
                    "verticalAlignment": "MIDDLE"
                }
            },
            "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment)"
        }},
        # Border around headers
        {"updateBorders": {
            "range": {"sheetId": sheet_id, "startRowIndex": 8, "endRowIndex": 9, "startColumnIndex": 5, "endColumnIndex": 8},
            "top": {"style": "SOLID", "width": 2, "color": DARK_BROWN},
            "bottom": {"style": "SOLID", "width": 2, "color": DARK_BROWN},
            "left": {"style": "SOLID", "width": 2, "color": DARK_BROWN},
            "right": {"style": "SOLID", "width": 2, "color": DARK_BROWN},
            "innerVertical": {"style": "SOLID", "width": 1, "color": WHITE},
        }},
    ])

    # 8. Data area formatting (rows 10-50)
    print("\n8. Форматирование области данных...")
    requests.extend([
        # Light background for data area
        {"repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": 9, "endRowIndex": 50, "startColumnIndex": 5, "endColumnIndex": 8},
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": LIGHT_GRAY,
                    "verticalAlignment": "MIDDLE",
                    "horizontalAlignment": "CENTER"
                }
            },
            "fields": "userEnteredFormat(backgroundColor,verticalAlignment,horizontalAlignment)"
        }},
        # Currency format for column H (amount)
        {"repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": 9, "endRowIndex": 50, "startColumnIndex": 7, "endColumnIndex": 8},
            "cell": {
                "userEnteredFormat": {
                    "numberFormat": {"type": "CURRENCY", "pattern": "$#,##0.00"}
                }
            },
            "fields": "userEnteredFormat(numberFormat)"
        }},
        # Grid lines for data area
        {"updateBorders": {
            "range": {"sheetId": sheet_id, "startRowIndex": 9, "endRowIndex": 50, "startColumnIndex": 5, "endColumnIndex": 8},
            "top": {"style": "SOLID", "width": 1, "color": BROWN},
            "bottom": {"style": "SOLID", "width": 1, "color": BROWN},
            "left": {"style": "SOLID", "width": 1, "color": BROWN},
            "right": {"style": "SOLID", "width": 1, "color": BROWN},
            "innerHorizontal": {"style": "SOLID", "width": 1, "color": {"red": 0.8, "green": 0.8, "blue": 0.8}},
            "innerVertical": {"style": "SOLID", "width": 1, "color": {"red": 0.8, "green": 0.8, "blue": 0.8}},
        }},
    ])

    # Execute all formatting requests
    print("\n9. Применение форматирования...")
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"requests": requests}
    ).execute()

    # 10. Write content
    print("\n10. Запись содержимого...")
    values = [
        # Row 3 - Title
        [],
        [],
        ["", "", "", "", "", "ЗП ДИЗАЙНЕРАМ"],  # F3
        [],
        # Row 5 - Summary
        ["", "", "", "", "", "", "Всего выплачено:", "=СУММ(H10:H1000)"],  # G5, H5
        [],
        [],
        [],
        # Row 9 - Headers
        ["", "", "", "", "", "Дата выплаты", "Дизайнер", "Сумма"],  # F9, G9, H9
    ]

    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=f"'{sheet_name}'!A1:H9",
        valueInputOption="USER_ENTERED",
        body={"values": values}
    ).execute()

    print("\n" + "=" * 60)
    print("   ✅ ГОТОВО! Лист 'ЗП дизайнерам' настроен")
    print("=" * 60)
    print("""
    Структура листа:

    ┌─────────────────────────────────────┐
    │        ЗП ДИЗАЙНЕРАМ               │  ← Строка 3 (заголовок)
    └─────────────────────────────────────┘

    │ Всего выплачено: │    $0.00        │  ← Строка 5 (итого)

    ┌──────────────┬───────────┬─────────┐
    │ Дата выплаты │ Дизайнер  │  Сумма  │  ← Строка 9 (заголовки)
    ├──────────────┼───────────┼─────────┤
    │              │           │         │  ← Строка 10+ (данные)
    │              │           │         │
    └──────────────┴───────────┴─────────┘

    Теперь можно запускать бота и использовать
    кнопку "💵 ЗП дизайнеру" для выплат!
    """)

    return True


if __name__ == "__main__":
    result = setup_designer_salary_sheet()
    sys.exit(0 if result else 1)
