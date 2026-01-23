"""
Google Sheets configuration.

Each sheet has unique settings:
- name: Sheet name in Google Spreadsheet
- id_column: Column for operation_id (UUID)
- data_columns: Range of columns for bot data (e.g., "F:K")
- start_row: First row where bot can write data (1-based)
- columns: Ordered list of column names for this sheet
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class SheetConfig:
    """Configuration for a single sheet."""
    name: str
    id_column: str = "A"
    data_columns: str = "B:Z"
    start_row: int = 2
    check_column: str = None  # Column to check for empty rows (if None, uses data_start_col)
    columns: List[str] = field(default_factory=list)
    protected_columns: List[str] = field(default_factory=list)
    skip_rows: List[int] = field(default_factory=list)  # Rows to skip when writing

    @property
    def data_start_col(self) -> str:
        """Get first column of data range (e.g., 'F' from 'F:K')."""
        return self.data_columns.split(":")[0]

    @property
    def data_end_col(self) -> str:
        """Get last column of data range (e.g., 'K' from 'F:K')."""
        return self.data_columns.split(":")[1]

    @property
    def full_range(self) -> str:
        """Get full range including ID column for reading."""
        return f"{self.id_column}:{self.data_end_col}"


# ============================================================================
# SHEET CONFIGURATIONS
# ============================================================================

DESIGNER_DATA = SheetConfig(
    name="Дизайнер DATA",
    id_column="A",
    data_columns="F:K",
    start_row=15,  # Данные начинаются с 15 строки
    check_column="G",  # Проверяем по колонке G (Ник дизайнера)
    protected_columns=["B", "C", "D", "E"],  # Charts area
    skip_rows=[],  # Нет пропускаемых строк
    columns=[
        "operation_id",  # A
        # B, C, D, E - protected (charts)
        "date",          # F
        "designer",      # G
        "client",        # H
        "amount",        # I - Стоимость заказа
        "percent",       # J - % дизайнера
        "salary",        # K - Оклад дизайнера
    ]
)

CLIENTS_DATA = SheetConfig(
    name="Заказчики DATA",
    id_column="A",
    data_columns="F:L",  # F-L data columns
    start_row=9,  # Данные начинаются с 9 строки
    check_column="G",  # Проверяем по колонке G (Ник заказчика)
    protected_columns=["B", "C", "D", "E"],  # Info area (ЯНВАРЬ, ИНФО, dates, currency)
    columns=[
        "date",          # F - дата
        "client",        # G - ник заказчика
        "status",        # H - статус (white/black list)
        "amount",        # I - сумма заказа
        "paid",          # J - фактическая оплата
        "debt",          # K - долг
        "overpaid",      # L - переплата
    ]
)

EXPENSES = SheetConfig(
    name="Расходы",
    id_column="A",
    data_columns="F:K",  # F-K: F=date, G=category, H=amount, I=designer, J=designer_amount, K=total
    start_row=12,  # Данные начинаются с 12 строки
    check_column="G",  # Проверяем по колонке G (Категория расходов) - для обычных расходов
    protected_columns=["B", "C", "D", "E"],  # Don't touch these
    columns=[
        "date",             # F - дата
        "category",         # G - категория расходов (для обычных расходов)
        "amount",           # H - сумма (для обычных расходов)
        "designer",         # I - ник дизайнера (для выплат дизайнерам)
        "designer_amount",  # J - сумма оплаты дизайнерам
        "total",            # K - итоговый расход (формула)
    ]
)

PURE_INCOME = SheetConfig(
    name="Чистый доход",
    id_column="A",
    data_columns="F:H",  # Bot writes F (date), G (category), H (amount)
    start_row=10,  # Данные начинаются с 10 строки
    check_column="G",  # Проверяем по колонке G (Категория дохода)
    protected_columns=["B", "C", "D", "E"],  # Info area
    columns=[
        "date",          # F - дата
        "category",      # G - категория дохода
        "amount",        # H - сумма дохода
    ]
)

# GENERAL имеет два раздела:
# 1. P&L (B-E) - с 13 строки, проверяем по B
# 2. Data (G-U) - с 9 строки, проверяем по G

GENERAL_PL = SheetConfig(
    name="GENERAL",
    id_column="A",
    data_columns="B:E",  # P&L columns
    start_row=13,  # P&L данные начинаются с 13 строки
    check_column="B",  # Проверяем по колонке B (дата)
    protected_columns=[],
    columns=[
        "date",      # B - дата (DD.MM)
        "revenue",   # C - выручка
        "expense",   # D - расходы
        "profit",    # E - прибыль
    ]
)

GENERAL_DATA = SheetConfig(
    name="GENERAL",
    id_column="A",
    data_columns="G:U",  # Data columns
    start_row=10,  # Data данные начинаются с 10 строки (row 9 = заголовки)
    check_column="G",  # Проверяем по колонке G (дата)
    protected_columns=[],
    columns=[
        "date",              # G - дата (DD.MM)
        "designer",          # H - дизайнер
        "client",            # I - заказчик
        "order_amount",      # J - сумма заказа
        "paid",              # K - фактическая оплата
        "debt",              # L - долг
        "overpaid",          # M - переплата
        "designer_percent",  # N - % дизайнера
        "designer_salary",   # O - оклад дизайнера
        "pure_category",     # P - категория чистого дохода
        "pure_amount",       # Q - сумма чистого дохода
        "expense_category",  # R - (пусто)
        "expense_amount",    # S - сумма расхода
        "balance_1",         # T - (пусто - формула)
        "balance_2",         # U - резервный кошелёк
    ]
)

# Legacy alias for backward compatibility
GENERAL = GENERAL_DATA

CATEGORIES = SheetConfig(
    name="Категории",
    id_column="A",
    data_columns="B:E",
    start_row=2,
    check_column="B",  # Проверяем по колонке B (тип)
    columns=[
        "type",          # B - "designer" / "client" / "expense" / "income"
        "name",          # C
        "status",        # D - "active" / "whitelist" / "blacklist"
        "created_at",    # E
    ]
)

DESIGNER_SALARY = SheetConfig(
    name="ЗП Дизайнерам",
    id_column="A",
    data_columns="F:H",  # F=дата, G=дизайнер, H=сумма
    start_row=10,  # Данные начинаются с 10 строки
    check_column="G",  # Проверяем по колонке G (дизайнер)
    protected_columns=["B", "C", "D", "E"],  # Не трогаем
    columns=[
        "date",          # F - дата выплаты
        "designer",      # G - ник дизайнера
        "amount",        # H - сумма выплаты
    ]
)


# ============================================================================
# SHEETS REGISTRY
# ============================================================================

SHEETS_CONFIG: Dict[str, SheetConfig] = {
    "designer_data": DESIGNER_DATA,
    "clients_data": CLIENTS_DATA,
    "expenses": EXPENSES,
    "pure_income": PURE_INCOME,
    "general": GENERAL,  # Alias для GENERAL_DATA
    "general_pl": GENERAL_PL,  # P&L секция (B-E, start_row=13)
    "general_data": GENERAL_DATA,  # Data секция (G-U, start_row=9)
    "categories": CATEGORIES,
    "designer_salary": DESIGNER_SALARY,  # ЗП дизайнерам
}


def get_sheet_config(sheet_key: str) -> SheetConfig:
    """
    Get sheet configuration by key.

    Args:
        sheet_key: One of: designer_data, clients_data, expenses,
                   pure_income, general, payments, categories

    Returns:
        SheetConfig for the requested sheet

    Raises:
        KeyError: If sheet_key is not found
    """
    if sheet_key not in SHEETS_CONFIG:
        raise KeyError(f"Unknown sheet key: {sheet_key}. Available: {list(SHEETS_CONFIG.keys())}")
    return SHEETS_CONFIG[sheet_key]
