"""
FSM States for order creation flow.
"""
from aiogram.fsm.state import State, StatesGroup


class DesignerOrderStates(StatesGroup):
    """States for creating a designer order."""

    # Step 1: Select order type (designer/pure) - handled by menu
    # Step 2: Select model (percent/salary)
    waiting_for_model = State()

    # Step 3: Enter designer name
    waiting_for_designer = State()

    # Step 4: Enter client name
    waiting_for_client = State()

    # Step 5: Enter order amount
    waiting_for_amount = State()

    # Step 6: Enter designer percentage (for percent model)
    waiting_for_percent = State()

    # Step 6 alt: Enter designer salary (for salary model)
    waiting_for_salary = State()

    # Step 7: Enter actual payment from client
    waiting_for_actual_payment = State()

    # Step 8: Select wallet (operational/reserve/split)
    waiting_for_wallet = State()

    # Step 9: Confirm order
    waiting_for_confirmation = State()


class PureOrderStates(StatesGroup):
    """States for creating a pure agency order (no designer)."""

    # Step 1: Enter client name
    waiting_for_client = State()

    # Step 2: Enter order amount
    waiting_for_amount = State()

    # Step 3: Enter actual payment from client
    waiting_for_actual_payment = State()

    # Step 4: Select wallet
    waiting_for_wallet = State()

    # Step 5: Confirm
    waiting_for_confirmation = State()


class PureIncomeStates(StatesGroup):
    """States for adding pure income (not an order)."""

    # Step 1: Enter category (e.g., "Аренда продуктов", "Подписка")
    waiting_for_category = State()

    # Step 2: Enter amount
    waiting_for_amount = State()

    # Step 3: Select wallet
    waiting_for_wallet = State()

    # Step 4: Confirm
    waiting_for_confirmation = State()


class PaymentStates(StatesGroup):
    """States for adding payment from client."""

    # Step 1: Enter client name
    waiting_for_client = State()

    # Step 2: Show orders with debt, wait for payment amount
    waiting_for_amount = State()

    # Step 3: Confirm payment distribution
    waiting_for_confirmation = State()


class ExpenseStates(StatesGroup):
    """States for adding expense."""

    # Step 1: Enter category
    waiting_for_category = State()

    # Step 2: Enter amount
    waiting_for_amount = State()

    # Step 3: Confirm
    waiting_for_confirmation = State()


class AddClientStates(StatesGroup):
    """States for adding a new client."""

    # Step 1: Enter client name
    waiting_for_name = State()

    # Step 2: Confirm
    waiting_for_confirmation = State()


class AddDesignerStates(StatesGroup):
    """States for adding a new designer."""

    # Step 1: Enter designer name
    waiting_for_name = State()

    # Step 2: Confirm
    waiting_for_confirmation = State()


class DateFilterStates(StatesGroup):
    """States for custom date range input."""

    # Step 1: Enter start date (DD.MM.YYYY)
    waiting_for_start_date = State()

    # Step 2: Enter end date (DD.MM.YYYY)
    waiting_for_end_date = State()
