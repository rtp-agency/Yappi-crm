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
    start_row=19,  # Данные начинаются с 19 строки
    protected_columns=["B", "C", "D", "E"],  # Charts area
    skip_rows=[20],  # Пропускать строку 20
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
    data_columns="F:L",  # F-I are formulas, J is manual payment, K-L are formula results
    start_row=13,  # Rows 9-12 have existing data, bot writes from row 13
    protected_columns=["B", "C", "D", "E"],  # Info area (ЯНВАРЬ, ИНФО, dates, currency)
    columns=[
        # Note: This sheet uses formulas to pull data from "Дизайнер DATA"
        # F = date (formula)
        # G = client name (formula)
        # H = client status (formula: white/black list)
        # I = order amount (formula)
        # J = actual payment (MANUAL INPUT - only column bot writes to)
        # K = debt (formula: I - J)
        # L = overpayment (formula)
        "date",          # F - formula from Дизайнер DATA
        "client",        # G - formula from Дизайнер DATA
        "status",        # H - formula (white/black list)
        "amount",        # I - formula from Дизайнер DATA
        "paid",          # J - MANUAL INPUT (фактическая оплата)
        "debt",          # K - formula (I - J, долг)
        "overpaid",      # L - formula (переплата)
    ]
)

EXPENSES = SheetConfig(
    name="Расходы",
    id_column="A",
    data_columns="F:H",  # F-H are manual input, I-K are formulas
    start_row=12,  # Row 11 = headers, data starts from row 12
    protected_columns=["B", "C", "D", "E"],  # Don't touch these
    columns=[
        # A = operation_id
        # B-E = protected (charts/info area)
        # F = Дата заполнения (manual)
        # G = Категория текущих расходов (manual)
        # H = Сумма текущих расходов (manual)
        # I = Ник дизайнера (formula from Дизайнер DATA)
        # J = Сумма оплаты дизайнерам (formula)
        # K = Итоговые расходы (formula: J+H)
        "date",          # F - manual
        "category",      # G - manual
        "amount",        # H - manual
    ]
)

PURE_INCOME = SheetConfig(
    name="Чистый доход",
    id_column="A",
    data_columns="F:H",  # Bot writes F (date), G (category), H (amount)
    start_row=14,  # Rows 10-13 have existing data, bot writes from row 14
    protected_columns=["B", "C", "D", "E"],  # Info area (ЯНВАРЬ, ИНФО, etc.)
    columns=[
        # A = operation_id
        # B-E = protected (info area)
        # F = Дата заполнения (manual)
        # G = Категория доп дохода (manual)
        # H = Выручка с доп дохода (manual)
        # I = Ник дизайнера (formula from Дизайнер DATA)
        # J = Выручка с дизайнеров (formula)
        # K = Итоговая выручка (formula: J+H)
        "date",          # F - manual
        "category",      # G - manual
        "amount",        # H - manual
    ]
)

GENERAL = SheetConfig(
    name="GENERAL",
    id_column="A",  # operation_id in hidden column A
    data_columns="G:U",  # Итоговая таблица
    start_row=13,  # Rows 9-12 = formulas, bot writes from row 13+
    protected_columns=["B", "C", "D", "E"],  # P&L area (don't touch)
    skip_rows=[9, 10, 11, 12],  # Формулы - не трогать!
    columns=[
        # GENERAL лист заполняется ФОРМУЛАМИ из других листов
        # Бот НЕ пишет сюда напрямую, только читает для аналитики
        #
        # Summary cells (строка 4):
        # G4 = Выручка (revenue)
        # I4 = Затраты (expenses)
        # K4 = Прибыль (profit)
        # M4 = Маржинальность (margin %)
        #
        # Columns G-U (Итоговая таблица):
        "date",              # G - ='Дизайнер DATA'!F (дата)
        "designer",          # H - ='Дизайнер DATA'!G (дизайнер)
        "client",            # I - ='Дизайнер DATA'!H (заказчик)
        "order_amount",      # J - ='Дизайнер DATA'!I (стоимость заказа)
        "paid",              # K - ='Заказчики DATA'!J (фактическая оплата)
        "debt",              # L - ='Заказчики DATA'!K (долг)
        "overpaid",          # M - ='Заказчики DATA'!L (переплата)
        "designer_percent",  # N - формула: % дизайнера
        "designer_salary",   # O - оклад дизайнера
        "pure_category",     # P - ='Чистый доход'!G (категория)
        "pure_amount",       # Q - ='Чистый доход'!H (сумма)
        "expense_category",  # R - ='Расходы'!G (категория расхода)
        "expense_amount",    # S - ='Расходы'!H (сумма расхода)
        "balance_1",         # T - формула: остаток на 1 счете
        "balance_2",         # U - остаток на 2 счете
    ]
)

PAYMENTS = SheetConfig(
    name="Оплаты",
    id_column="A",
    data_columns="B:F",
    start_row=2,
    columns=[
        "operation_id",  # A
        "date",          # B
        "client",        # C
        "order_id",      # D
        "payment_type",  # E
        "amount",        # F
    ]
)

CATEGORIES = SheetConfig(
    name="Категории",
    id_column="A",
    data_columns="B:E",
    start_row=2,
    columns=[
        "operation_id",  # A
        "type",          # B - "designer" / "client" / "expense" / "income"
        "name",          # C
        "status",        # D - "active" / "whitelist" / "blacklist"
        "created_at",    # E
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
    "general": GENERAL,
    "payments": PAYMENTS,
    "categories": CATEGORIES,
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
