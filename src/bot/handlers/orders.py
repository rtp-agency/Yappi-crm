"""
Order creation handlers.
Handlers for designer orders, pure orders, payments, expenses, pure income.
"""
import uuid
from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from loguru import logger

from src.bot.states.order_states import (
    DesignerOrderStates,
    PureOrderStates,
    PaymentStates,
    ExpenseStates,
    PureIncomeStates,
    AddClientStates,
    AddDesignerStates
)
from src.bot.keyboards.main_menu import (
    get_order_type_menu,
    get_model_menu,
    get_cancel_keyboard,
    get_confirm_keyboard,
    get_wallet_keyboard,
    get_main_menu,
    get_clients_keyboard,
    get_designers_keyboard
)
from src.services.sheets.client import get_sheets_client

router = Router()


# ============================================================================
# ORDER FLOW START
# ============================================================================

@router.callback_query(F.data == "add:order")
async def start_order(callback: CallbackQuery):
    """Start order creation - show order type menu."""
    await callback.message.edit_text(
        "🧾 <b>Новый заказ</b>\n\n"
        "Выберите тип заказа:",
        reply_markup=get_order_type_menu(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "order:designer")
async def start_designer_order(callback: CallbackQuery, state: FSMContext):
    """Start designer order - ask for model."""
    await callback.message.edit_text(
        "🎨 <b>Дизайнерский заказ</b>\n\n"
        "Выберите модель сотрудничества:",
        reply_markup=get_model_menu(),
        parse_mode="HTML"
    )
    await state.set_state(DesignerOrderStates.waiting_for_model)
    await callback.answer()


@router.callback_query(F.data == "order:back")
async def back_to_order_type(callback: CallbackQuery, state: FSMContext):
    """Go back to order type selection."""
    await state.clear()
    await callback.message.edit_text(
        "🧾 <b>Новый заказ</b>\n\n"
        "Выберите тип заказа:",
        reply_markup=get_order_type_menu(),
        parse_mode="HTML"
    )
    await callback.answer()


# ============================================================================
# DESIGNER ORDER FLOW
# ============================================================================

@router.callback_query(F.data.startswith("model:"), DesignerOrderStates.waiting_for_model)
async def select_model(callback: CallbackQuery, state: FSMContext):
    """Model selected - show designer selection."""
    model = callback.data.split(":")[1]  # "percent" or "salary"

    await state.update_data(model=model)

    await callback.message.edit_text(
        f"🎨 <b>Дизайнерский заказ</b>\n"
        f"Модель: {'Процентная (%)' if model == 'percent' else 'Окладная'}\n\n"
        "⏳ Загрузка списка дизайнеров...",
        parse_mode="HTML"
    )

    try:
        sheets = get_sheets_client()
        await sheets.initialize()
        designers = await sheets.get_all_designers()

        if designers:
            await callback.message.edit_text(
                f"🎨 <b>Дизайнерский заказ</b>\n"
                f"Модель: {'Процентная (%)' if model == 'percent' else 'Окладная'}\n\n"
                "Выберите <b>дизайнера</b> из списка:",
                reply_markup=get_designers_keyboard(designers),
                parse_mode="HTML"
            )
        else:
            await callback.message.edit_text(
                f"🎨 <b>Дизайнерский заказ</b>\n"
                f"Модель: {'Процентная (%)' if model == 'percent' else 'Окладная'}\n\n"
                "Дизайнеры не найдены. Введите <b>имя дизайнера</b>:",
                reply_markup=get_cancel_keyboard(),
                parse_mode="HTML"
            )
            await state.set_state(DesignerOrderStates.waiting_for_designer)
            await callback.answer()
            return

    except Exception as e:
        logger.error(f"Error loading designers: {e}")
        await callback.message.edit_text(
            f"🎨 <b>Дизайнерский заказ</b>\n"
            f"Модель: {'Процентная (%)' if model == 'percent' else 'Окладная'}\n\n"
            "Не удалось загрузить список. Введите <b>имя дизайнера</b>:",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML"
        )
        await state.set_state(DesignerOrderStates.waiting_for_designer)

    await callback.answer()


@router.callback_query(F.data.startswith("select_designer:"))
async def designer_selected_from_list(callback: CallbackQuery, state: FSMContext):
    """Designer selected from list - show client selection."""
    designer = callback.data.split(":", 1)[1]
    await state.update_data(designer=designer)

    await callback.message.edit_text(
        f"✅ Дизайнер: <b>{designer}</b>\n\n"
        "⏳ Загрузка списка заказчиков...",
        parse_mode="HTML"
    )

    try:
        sheets = get_sheets_client()
        await sheets.initialize()
        clients = await sheets.get_all_clients()

        if clients:
            await callback.message.edit_text(
                f"✅ Дизайнер: <b>{designer}</b>\n\n"
                "Выберите <b>заказчика</b> из списка:",
                reply_markup=get_clients_keyboard(clients),
                parse_mode="HTML"
            )
        else:
            await callback.message.edit_text(
                f"✅ Дизайнер: <b>{designer}</b>\n\n"
                "Заказчики не найдены. Введите <b>имя заказчика</b>:",
                reply_markup=get_cancel_keyboard(),
                parse_mode="HTML"
            )
            await state.set_state(DesignerOrderStates.waiting_for_client)

    except Exception as e:
        logger.error(f"Error loading clients: {e}")
        await callback.message.edit_text(
            f"✅ Дизайнер: <b>{designer}</b>\n\n"
            "Не удалось загрузить список. Введите <b>имя заказчика</b>:",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML"
        )
        await state.set_state(DesignerOrderStates.waiting_for_client)

    await callback.answer()


@router.callback_query(F.data == "designer:manual")
async def designer_manual_entry(callback: CallbackQuery, state: FSMContext):
    """User wants to enter designer name manually."""
    data = await state.get_data()
    model = data.get("model", "percent")

    await callback.message.edit_text(
        f"🎨 <b>Дизайнерский заказ</b>\n"
        f"Модель: {'Процентная (%)' if model == 'percent' else 'Окладная'}\n\n"
        "Введите <b>имя нового дизайнера</b>:\n"
        "<i>(будет автоматически добавлен в базу)</i>",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(DesignerOrderStates.waiting_for_designer)
    await callback.answer()


@router.message(DesignerOrderStates.waiting_for_designer)
async def enter_designer(message: Message, state: FSMContext):
    """Designer name entered manually - add to Categories and show client selection."""
    designer = message.text.strip()

    if not designer:
        await message.answer("❌ Введите имя дизайнера:")
        return

    await state.update_data(designer=designer)

    # Add new designer to Categories sheet
    try:
        sheets = get_sheets_client()
        await sheets.initialize()
        added = await sheets.add_new_designer(designer)
        if added:
            logger.info(f"New designer '{designer}' added to Categories")
    except Exception as e:
        logger.error(f"Error adding designer to categories: {e}")

    # Show client selection
    await message.answer(
        f"✅ Дизайнер: <b>{designer}</b>\n"
        "<i>(добавлен в базу)</i>\n\n"
        "⏳ Загрузка списка заказчиков...",
        parse_mode="HTML"
    )

    try:
        clients = await sheets.get_all_clients()

        if clients:
            await message.answer(
                f"✅ Дизайнер: <b>{designer}</b>\n\n"
                "Выберите <b>заказчика</b> из списка:",
                reply_markup=get_clients_keyboard(clients),
                parse_mode="HTML"
            )
        else:
            await message.answer(
                f"✅ Дизайнер: <b>{designer}</b>\n\n"
                "Заказчики не найдены. Введите <b>имя заказчика</b>:",
                reply_markup=get_cancel_keyboard(),
                parse_mode="HTML"
            )
            await state.set_state(DesignerOrderStates.waiting_for_client)

    except Exception as e:
        logger.error(f"Error loading clients: {e}")
        await message.answer(
            f"✅ Дизайнер: <b>{designer}</b>\n\n"
            "Введите <b>имя заказчика</b>:",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML"
        )
        await state.set_state(DesignerOrderStates.waiting_for_client)


@router.callback_query(F.data.startswith("select_client:"))
async def client_selected_from_list(callback: CallbackQuery, state: FSMContext):
    """Client selected from list - check context and handle accordingly."""
    client_name = callback.data.split(":", 1)[1]
    data = await state.get_data()

    # Check if we're in designer order flow (model is set)
    if "model" in data:
        # Designer order flow - ask for amount
        await state.update_data(client=client_name)
        await callback.message.edit_text(
            f"✅ Дизайнер: <b>{data.get('designer', '?')}</b>\n"
            f"✅ Заказчик: <b>{client_name}</b>\n\n"
            "Введите <b>сумму заказа</b> (в $):",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML"
        )
        await state.set_state(DesignerOrderStates.waiting_for_amount)
        await callback.answer()
    elif data.get("is_pure_order"):
        # Pure order flow - ask for amount
        await state.update_data(client=client_name)
        await callback.message.edit_text(
            f"💎 <b>Чистый заказ агентства</b>\n\n"
            f"✅ Заказчик: <b>{client_name}</b>\n\n"
            "Введите <b>сумму заказа</b> (в $):",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML"
        )
        await state.set_state(PureOrderStates.waiting_for_amount)
        await callback.answer()
    else:
        # Payment flow - show orders with debt
        await process_client_selection(callback.message, state, client_name, is_callback=True)
        await callback.answer()


@router.callback_query(F.data == "client:manual")
async def client_manual_entry(callback: CallbackQuery, state: FSMContext):
    """User wants to enter client name manually - check context."""
    data = await state.get_data()

    if "model" in data:
        # Designer order flow
        await callback.message.edit_text(
            f"✅ Дизайнер: <b>{data.get('designer', '?')}</b>\n\n"
            "Введите <b>имя нового заказчика</b>:\n"
            "<i>(будет автоматически добавлен в базу)</i>",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML"
        )
        await state.set_state(DesignerOrderStates.waiting_for_client)
    elif data.get("is_pure_order"):
        # Pure order flow
        await callback.message.edit_text(
            "💎 <b>Чистый заказ агентства</b>\n\n"
            "Введите <b>имя нового заказчика</b>:\n"
            "<i>(будет автоматически добавлен в базу)</i>",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML"
        )
        await state.set_state(PureOrderStates.waiting_for_client)
    else:
        # Payment flow
        await callback.message.edit_text(
            "💰 <b>Оплата от заказчика</b>\n\n"
            "Введите <b>имя заказчика</b>:",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML"
        )
        await state.set_state(PaymentStates.waiting_for_client)

    await callback.answer()


@router.message(DesignerOrderStates.waiting_for_client)
async def enter_client(message: Message, state: FSMContext):
    """Client name entered manually - add to Categories and ask for amount."""
    client = message.text.strip()

    if not client:
        await message.answer("❌ Введите имя заказчика:")
        return

    await state.update_data(client=client)

    # Add new client to Categories sheet
    try:
        sheets = get_sheets_client()
        await sheets.initialize()
        added = await sheets.add_new_client(client)
        if added:
            logger.info(f"New client '{client}' added to Categories")
    except Exception as e:
        logger.error(f"Error adding client to categories: {e}")

    data = await state.get_data()
    await message.answer(
        f"✅ Дизайнер: <b>{data.get('designer', '?')}</b>\n"
        f"✅ Заказчик: <b>{client}</b>\n"
        "<i>(добавлен в базу)</i>\n\n"
        "Введите <b>сумму заказа</b> (в $):",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(DesignerOrderStates.waiting_for_amount)


@router.message(DesignerOrderStates.waiting_for_amount)
async def enter_amount(message: Message, state: FSMContext):
    """Amount entered - ask for percent or salary."""
    try:
        amount = float(message.text.strip().replace(",", ".").replace("$", ""))
        if amount <= 0:
            raise ValueError("Amount must be positive")
    except ValueError:
        await message.answer("❌ Введите корректную сумму (число):")
        return

    await state.update_data(amount=amount)
    data = await state.get_data()

    if data["model"] == "percent":
        await message.answer(
            f"✅ Сумма заказа: <b>${amount:.2f}</b>\n\n"
            "Введите <b>процент дизайнеру</b> (например: 40):",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML"
        )
        await state.set_state(DesignerOrderStates.waiting_for_percent)
    else:
        await message.answer(
            f"✅ Сумма заказа: <b>${amount:.2f}</b>\n\n"
            "Введите <b>оклад дизайнеру</b> (в $):",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML"
        )
        await state.set_state(DesignerOrderStates.waiting_for_salary)


@router.message(DesignerOrderStates.waiting_for_percent)
async def enter_percent(message: Message, state: FSMContext):
    """Percent entered - ask for actual payment."""
    try:
        percent = float(message.text.strip().replace("%", "").replace(",", "."))
        if percent < 0 or percent > 100:
            raise ValueError("Percent must be 0-100")
    except ValueError:
        await message.answer("❌ Введите корректный процент (0-100):")
        return

    await state.update_data(percent=percent)
    data = await state.get_data()

    # Calculate values
    designer_salary = data["amount"] * (percent / 100)
    agency_income = data["amount"] - designer_salary

    await state.update_data(
        designer_salary=designer_salary,
        agency_income=agency_income
    )

    # Ask for actual payment
    await message.answer(
        f"✅ Процент дизайнеру: <b>{percent}%</b>\n"
        f"💵 ЗП дизайнеру: <b>${designer_salary:.2f}</b>\n"
        f"💼 Доход агентства: <b>${agency_income:.2f}</b>\n\n"
        f"Введите <b>фактическую оплату</b> от заказчика (в $):\n"
        f"<i>(или 0 если оплаты ещё не было)</i>",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(DesignerOrderStates.waiting_for_actual_payment)


@router.message(DesignerOrderStates.waiting_for_salary)
async def enter_salary(message: Message, state: FSMContext):
    """Salary entered - ask for actual payment."""
    try:
        salary = float(message.text.strip().replace(",", ".").replace("$", ""))
        if salary < 0:
            raise ValueError("Salary must be positive")
    except ValueError:
        await message.answer("❌ Введите корректную сумму оклада:")
        return

    data = await state.get_data()

    if salary > data["amount"]:
        await message.answer(f"❌ Оклад не может быть больше суммы заказа (${data['amount']:.2f}):")
        return

    agency_income = data["amount"] - salary

    await state.update_data(
        designer_salary=salary,
        agency_income=agency_income,
        percent=0  # Not applicable for salary model
    )

    # Ask for actual payment
    await message.answer(
        f"✅ ЗП дизайнеру: <b>${salary:.2f}</b>\n"
        f"💼 Доход агентства: <b>${agency_income:.2f}</b>\n\n"
        f"Введите <b>фактическую оплату</b> от заказчика (в $):\n"
        f"<i>(или 0 если оплаты ещё не было)</i>",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(DesignerOrderStates.waiting_for_actual_payment)


@router.message(DesignerOrderStates.waiting_for_actual_payment)
async def enter_actual_payment(message: Message, state: FSMContext):
    """Actual payment entered - show confirmation."""
    try:
        actual_payment = float(message.text.strip().replace(",", ".").replace("$", ""))
        if actual_payment < 0:
            raise ValueError("Payment must be non-negative")
    except ValueError:
        await message.answer("❌ Введите корректную сумму (0 или больше):")
        return

    await state.update_data(actual_payment=actual_payment)
    data = await state.get_data()

    # Calculate debt
    debt = data["amount"] - actual_payment

    model_name = "Процентная" if data["model"] == "percent" else "Окладная"
    percent_text = f"\n📈 Процент дизайнеру: <b>{data.get('percent', 0)}%</b>" if data["model"] == "percent" else ""

    debt_text = ""
    if debt > 0:
        debt_text = f"\n🔴 Долг заказчика: <b>${debt:.2f}</b>"
    elif debt < 0:
        debt_text = f"\n🟢 Переплата: <b>${abs(debt):.2f}</b>"

    # Show confirmation
    await message.answer(
        "📋 <b>ПОДТВЕРЖДЕНИЕ ЗАКАЗА</b>\n\n"
        f"🎨 Дизайнер: <b>{data['designer']}</b>\n"
        f"👤 Заказчик: <b>{data['client']}</b>\n"
        f"📊 Модель: <b>{model_name}</b>\n"
        f"💰 Сумма заказа: <b>${data['amount']:.2f}</b>\n"
        f"💵 Фактическая оплата: <b>${actual_payment:.2f}</b>{percent_text}\n\n"
        f"💵 ЗП дизайнеру: <b>${data['designer_salary']:.2f}</b>\n"
        f"💼 Доход агентства: <b>${data['agency_income']:.2f}</b>{debt_text}\n\n"
        "Подтвердить заказ?",
        reply_markup=get_confirm_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(DesignerOrderStates.waiting_for_confirmation)


# ============================================================================
# CONFIRMATION / CANCEL
# ============================================================================

@router.callback_query(F.data == "confirm", DesignerOrderStates.waiting_for_confirmation)
async def confirm_order(callback: CallbackQuery, state: FSMContext):
    """Confirm and save order to Google Sheets."""
    data = await state.get_data()

    # Generate operation_id
    operation_id = str(uuid.uuid4())
    date_str = datetime.now().strftime("%d.%m.%Y")

    actual_payment = data.get("actual_payment", 0)
    debt = data["amount"] - actual_payment

    # Prepare data for Designer DATA sheet
    # K column: 0 for percent model, salary for salary model
    is_percent_model = data.get("model") == "percent"
    salary_value = 0 if is_percent_model else data.get("designer_salary", 0)

    order_data = [
        date_str,                              # F: Дата заполнения
        data["designer"],                      # G: Ник дизайнера
        data["client"],                        # H: Ник заказчика
        data["amount"],                        # I: Стоимость заказа
        data.get("percent", 0),               # J: % дизайнера
        salary_value,                         # K: Оклад (0 для % модели)
    ]

    await callback.message.edit_text(
        "⏳ Сохранение заказа...",
        parse_mode="HTML"
    )

    try:
        client = get_sheets_client()
        await client.initialize()

        # 1. Write to Designer DATA sheet
        row_num = await client.write_row(
            sheet_key="designer_data",
            operation_id=operation_id,
            data=order_data
        )

        logger.info(f"Order saved to Designer DATA: row={row_num}, operation_id={operation_id}")

        # Update F4 formula to include new row: =СУММ(I15:I{row_num})
        await client.update_sum_formula(
            sheet_name="Дизайнер DATA",
            formula_cell="F4",
            sum_column="I",
            start_row=15,
            end_row=row_num
        )

        # 2. Write to Заказчики DATA sheet (column J = actual payment)
        # H column: "Black List" if debt > 0, "White List" if no debt
        client_status = "Black List" if debt > 0 else "White List"
        clients_data = [
            date_str,                          # F: Дата заполнения
            data["client"],                    # G: Заказчик
            client_status,                     # H: White List / Black List
            data["amount"],                    # I: Сумма заказа
            actual_payment,                    # J: Фактическая оплата
            debt if debt > 0 else 0,           # K: Долг
        ]
        await client.write_row(
            sheet_key="clients_data",
            operation_id=operation_id,
            data=clients_data
        )
        logger.info(f"Written to Заказчики DATA: client={data['client']}, payment={actual_payment}")

        # 3. Write to Чистый доход sheet (columns I, J, K for designer orders)
        pure_income_row = await client.write_designer_to_pure_income(
            operation_id=operation_id,
            designer=data["designer"],
            order_amount=data["amount"],
            agency_income=data.get("agency_income", 0)
        )
        logger.info(f"Written to Чистый доход row {pure_income_row}")

        # 4. Write to GENERAL sheet
        general_row = await client.write_to_general(
            operation_id=operation_id,
            date=date_str,
            operation_type="designer_order",
            designer=data["designer"],
            client=data["client"],
            order_amount=data["amount"],
            actual_payment=actual_payment,
            designer_percent=data.get("percent", 0),
            designer_salary=data.get("designer_salary", 0),
            agency_income=data.get("agency_income", 0),
            wallet_operational=data.get("agency_income", 0)
        )
        logger.info(f"Written to GENERAL row {general_row}")

        debt_text = ""
        if debt > 0:
            debt_text = f"\n🔴 Долг заказчика: ${debt:.2f}"

        await state.clear()
        await callback.message.edit_text(
            "✅ <b>ЗАКАЗ СОХРАНЁН!</b>\n\n"
            f"🎨 Дизайнер: {data['designer']}\n"
            f"👤 Заказчик: {data['client']}\n"
            f"💰 Сумма: ${data['amount']:.2f}\n"
            f"💵 Фактическая оплата: ${actual_payment:.2f}{debt_text}\n"
            f"💵 ЗП дизайнеру: ${data['designer_salary']:.2f}\n"
            f"💼 Доход агентства: ${data['agency_income']:.2f}",
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Error saving order: {e}")
        await callback.message.edit_text(
            f"❌ <b>Ошибка сохранения!</b>\n\n{str(e)}",
            parse_mode="HTML"
        )
        await state.clear()

    await callback.answer("Заказ сохранён!")


@router.callback_query(F.data == "cancel")
async def cancel_order(callback: CallbackQuery, state: FSMContext):
    """Cancel order creation."""
    await state.clear()
    await callback.message.edit_text(
        "❌ Операция отменена.",
        reply_markup=get_main_menu(),
        parse_mode="HTML"
    )
    await callback.answer()


# ============================================================================
# PURE INCOME / PAYMENT / OTHER OPERATIONS
# ============================================================================

@router.callback_query(F.data == "add:pure_income")
async def add_pure_income(callback: CallbackQuery, state: FSMContext):
    """Start pure income flow - ask for category/name."""
    await callback.message.edit_text(
        "💎 <b>Чистый доход (не заказ)</b>\n\n"
        "Доход, который <b>не связан с дизайнерами</b> и не имеет заказчика.\n\n"
        "Введите <b>название дохода</b>:",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(PureIncomeStates.waiting_for_category)
    await callback.answer()


@router.callback_query(F.data == "add:payment")
async def add_payment(callback: CallbackQuery, state: FSMContext):
    """Start payment flow - show client selection."""
    await callback.message.edit_text(
        "💰 <b>Оплата от заказчика</b>\n\n"
        "⏳ Загрузка списка заказчиков...",
        parse_mode="HTML"
    )

    try:
        sheets = get_sheets_client()
        await sheets.initialize()
        clients = await sheets.get_unique_clients()

        if clients:
            await callback.message.edit_text(
                "💰 <b>Оплата от заказчика</b>\n\n"
                "Выберите заказчика из списка:",
                reply_markup=get_clients_keyboard(clients),
                parse_mode="HTML"
            )
        else:
            await callback.message.edit_text(
                "💰 <b>Оплата от заказчика</b>\n\n"
                "Заказчики не найдены. Введите имя вручную:",
                reply_markup=get_cancel_keyboard(),
                parse_mode="HTML"
            )
            await state.set_state(PaymentStates.waiting_for_client)

    except Exception as e:
        logger.error(f"Error loading clients: {e}")
        await callback.message.edit_text(
            "💰 <b>Оплата от заказчика</b>\n\n"
            "Не удалось загрузить список. Введите имя вручную:",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML"
        )
        await state.set_state(PaymentStates.waiting_for_client)

    await callback.answer()


@router.callback_query(F.data == "add:expense")
async def add_expense(callback: CallbackQuery, state: FSMContext):
    """Start expense flow - ask for category."""
    await callback.message.edit_text(
        "💸 <b>Добавить расход</b>\n\n"
        "Введите <b>категорию расхода</b>:\n"
        "(например: Подписка Клинк, Бонусы, Реклама, Вакансии)",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(ExpenseStates.waiting_for_category)
    await callback.answer()


@router.callback_query(F.data == "order:pure")
async def start_pure_order(callback: CallbackQuery, state: FSMContext):
    """Start pure agency order - show client selection."""
    # Mark that this is a pure order flow
    await state.update_data(is_pure_order=True)

    await callback.message.edit_text(
        "💎 <b>Чистый заказ агентства</b>\n\n"
        "Это заказ без дизайнера. 100% суммы идёт агентству.\n\n"
        "⏳ Загрузка списка заказчиков...",
        parse_mode="HTML"
    )

    try:
        sheets = get_sheets_client()
        await sheets.initialize()
        clients = await sheets.get_all_clients()

        if clients:
            await callback.message.edit_text(
                "💎 <b>Чистый заказ агентства</b>\n\n"
                "Это заказ без дизайнера. 100% суммы идёт агентству.\n\n"
                "Выберите <b>заказчика</b> из списка:",
                reply_markup=get_clients_keyboard(clients),
                parse_mode="HTML"
            )
        else:
            await callback.message.edit_text(
                "💎 <b>Чистый заказ агентства</b>\n\n"
                "Это заказ без дизайнера. 100% суммы идёт агентству.\n\n"
                "Заказчики не найдены. Введите <b>имя заказчика</b>:",
                reply_markup=get_cancel_keyboard(),
                parse_mode="HTML"
            )
            await state.set_state(PureOrderStates.waiting_for_client)

    except Exception as e:
        logger.error(f"Error loading clients for pure order: {e}")
        await callback.message.edit_text(
            "💎 <b>Чистый заказ агентства</b>\n\n"
            "Это заказ без дизайнера. 100% суммы идёт агентству.\n\n"
            "Введите <b>имя заказчика</b>:",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML"
        )
        await state.set_state(PureOrderStates.waiting_for_client)

    await callback.answer()


# ============================================================================
# PURE ORDER FLOW
# ============================================================================

@router.message(PureOrderStates.waiting_for_client)
async def pure_order_client(message: Message, state: FSMContext):
    """Client name entered manually - add to Categories and ask for amount."""
    client = message.text.strip()

    if not client:
        await message.answer("❌ Введите имя заказчика:")
        return

    await state.update_data(client=client)

    # Add new client to Categories sheet
    try:
        sheets = get_sheets_client()
        await sheets.initialize()
        added = await sheets.add_new_client(client)
        if added:
            logger.info(f"New client '{client}' added to Categories (pure order)")
    except Exception as e:
        logger.error(f"Error adding client to categories: {e}")

    await message.answer(
        f"💎 <b>Чистый заказ агентства</b>\n\n"
        f"✅ Заказчик: <b>{client}</b>\n"
        "<i>(добавлен в базу)</i>\n\n"
        "Введите <b>сумму заказа</b> (в $):",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(PureOrderStates.waiting_for_amount)


@router.message(PureOrderStates.waiting_for_amount)
async def pure_order_amount(message: Message, state: FSMContext):
    """Amount entered - ask for actual payment."""
    try:
        amount = float(message.text.strip().replace(",", ".").replace("$", ""))
        if amount <= 0:
            raise ValueError("Amount must be positive")
    except ValueError:
        await message.answer("❌ Введите корректную сумму (число):")
        return

    await state.update_data(amount=amount)

    await message.answer(
        f"✅ Сумма заказа: <b>${amount:.2f}</b>\n\n"
        f"Введите <b>фактическую оплату</b> от заказчика (в $):\n"
        f"<i>(или 0 если оплаты ещё не было)</i>",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(PureOrderStates.waiting_for_actual_payment)


@router.message(PureOrderStates.waiting_for_actual_payment)
async def pure_order_actual_payment(message: Message, state: FSMContext):
    """Actual payment entered - ask for wallet."""
    try:
        actual_payment = float(message.text.strip().replace(",", ".").replace("$", ""))
        if actual_payment < 0:
            raise ValueError("Payment must be non-negative")
    except ValueError:
        await message.answer("❌ Введите корректную сумму (0 или больше):")
        return

    await state.update_data(actual_payment=actual_payment)

    data = await state.get_data()
    debt = data["amount"] - actual_payment

    debt_text = ""
    if debt > 0:
        debt_text = f"\n🔴 Долг: ${debt:.2f}"
    elif debt < 0:
        debt_text = f"\n🟢 Переплата: ${abs(debt):.2f}"

    await message.answer(
        f"✅ Фактическая оплата: <b>${actual_payment:.2f}</b>{debt_text}\n\n"
        "Выберите <b>кошелёк</b> для распределения дохода:",
        reply_markup=get_wallet_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(PureOrderStates.waiting_for_wallet)


@router.callback_query(F.data.startswith("wallet:"), PureOrderStates.waiting_for_wallet)
async def pure_order_wallet(callback: CallbackQuery, state: FSMContext):
    """Wallet selected - show confirmation."""
    wallet = callback.data.split(":")[1]
    data = await state.get_data()
    amount = data["amount"]
    actual_payment = data.get("actual_payment", 0)
    debt = amount - actual_payment

    if wallet == "operational":
        wallet_operational = amount
        wallet_reserve = 0
        wallet_name = "Операционный"
    elif wallet == "reserve":
        wallet_operational = 0
        wallet_reserve = amount
        wallet_name = "Резервный"
    else:
        wallet_operational = amount / 2
        wallet_reserve = amount / 2
        wallet_name = "50/50"

    await state.update_data(
        wallet=wallet,
        wallet_name=wallet_name,
        wallet_operational=wallet_operational,
        wallet_reserve=wallet_reserve
    )

    debt_text = ""
    if debt > 0:
        debt_text = f"\n🔴 Долг заказчика: <b>${debt:.2f}</b>"
    elif debt < 0:
        debt_text = f"\n🟢 Переплата: <b>${abs(debt):.2f}</b>"

    await callback.message.edit_text(
        "📋 <b>ПОДТВЕРЖДЕНИЕ ЗАКАЗА</b>\n\n"
        f"👤 Заказчик: <b>{data['client']}</b>\n"
        f"📊 Тип: <b>Чистый заказ агентства</b>\n"
        f"💰 Сумма: <b>${amount:.2f}</b>\n"
        f"💵 Фактическая оплата: <b>${actual_payment:.2f}</b>{debt_text}\n"
        f"💼 Кошелёк: <b>{wallet_name}</b>\n\n"
        f"💵 Операционный: <b>${wallet_operational:.2f}</b>\n"
        f"🏦 Резервный: <b>${wallet_reserve:.2f}</b>\n\n"
        "Подтвердить заказ?",
        reply_markup=get_confirm_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(PureOrderStates.waiting_for_confirmation)
    await callback.answer()


@router.callback_query(F.data == "confirm", PureOrderStates.waiting_for_confirmation)
async def confirm_pure_order(callback: CallbackQuery, state: FSMContext):
    """Confirm and save pure order to Google Sheets."""
    data = await state.get_data()

    operation_id = str(uuid.uuid4())
    date_str = datetime.now().strftime("%d.%m.%Y")

    actual_payment = data.get("actual_payment", 0)
    debt = data["amount"] - actual_payment

    await callback.message.edit_text(
        "⏳ Сохранение заказа...",
        parse_mode="HTML"
    )

    try:
        client = get_sheets_client()
        await client.initialize()

        category = f"Чистый заказ: {data['client']}"

        row_num = await client.write_pure_income(
            operation_id=operation_id,
            date=date_str,
            category=category,
            amount=data["amount"]
        )

        logger.info(f"Pure order saved: row={row_num}, client={data['client']}, amount={data['amount']}")

        # Write to Заказчики DATA sheet (column J = actual payment)
        # H column: "Black List" if debt > 0, "White List" if no debt
        client_status = "Black List" if debt > 0 else "White List"
        clients_data = [
            date_str,                          # F: Дата заполнения
            data["client"],                    # G: Заказчик
            client_status,                     # H: White List / Black List
            data["amount"],                    # I: Сумма заказа
            actual_payment,                    # J: Фактическая оплата
            debt if debt > 0 else 0,           # K: Долг
        ]
        await client.write_row(
            sheet_key="clients_data",
            operation_id=operation_id,
            data=clients_data
        )
        logger.info(f"Written to Заказчики DATA: client={data['client']}, payment={actual_payment}")

        wallet_operational = data.get("wallet_operational", 0)
        wallet_reserve = data.get("wallet_reserve", 0)

        general_row = await client.write_to_general(
            operation_id=operation_id,
            date=date_str,
            operation_type="pure_order",
            client=data["client"],
            order_amount=data["amount"],
            actual_payment=actual_payment,
            pure_income_category=category,
            pure_income_amount=data["amount"],
            wallet_operational=wallet_operational,
            wallet_reserve=wallet_reserve
        )
        logger.info(f"Written to GENERAL row {general_row}")

        debt_text = ""
        if debt > 0:
            debt_text = f"\n🔴 Долг заказчика: ${debt:.2f}"

        await state.clear()
        await callback.message.edit_text(
            "✅ <b>ЧИСТЫЙ ЗАКАЗ СОХРАНЁН!</b>\n\n"
            f"👤 Заказчик: {data['client']}\n"
            f"💰 Сумма: ${data['amount']:.2f}\n"
            f"💵 Фактическая оплата: ${actual_payment:.2f}{debt_text}\n"
            f"📅 Дата: {date_str}",
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Error saving pure order: {e}")
        await callback.message.edit_text(
            f"❌ <b>Ошибка сохранения!</b>\n\n{str(e)}",
            parse_mode="HTML"
        )
        await state.clear()

    await callback.answer("Заказ создан!")


# ============================================================================
# PAYMENT FLOW
# ============================================================================

async def process_client_selection(message, state: FSMContext, client: str, is_callback: bool = False):
    """Process client selection - show orders with debt."""
    if is_callback:
        await message.edit_text("⏳ Загрузка заказов...", parse_mode="HTML")
    else:
        await message.answer("⏳ Загрузка заказов...")

    try:
        sheets = get_sheets_client()
        await sheets.initialize()

        orders = await sheets.get_client_orders_with_debt(client)

        if not orders:
            text = (
                f"❌ Заказчик <b>{client}</b> не найден.\n\n"
                "Проверьте правильность имени и попробуйте снова:"
            )
            if is_callback:
                await message.edit_text(text, reply_markup=get_cancel_keyboard(), parse_mode="HTML")
            else:
                await message.answer(text, reply_markup=get_cancel_keyboard(), parse_mode="HTML")
            return

        total_amount = sum(o["amount"] for o in orders)
        total_paid = sum(o["paid"] for o in orders)
        total_debt = sum(o["debt"] for o in orders)
        orders_with_debt = [o for o in orders if o["debt"] > 0]

        await state.update_data(
            client=client,
            orders=orders,
            total_debt=total_debt
        )

        orders_text = ""
        for i, order in enumerate(orders, 1):
            debt_marker = "⚠️" if order["debt"] > 0 else "✅"
            orders_text += (
                f"{debt_marker} <b>Заказ {i}</b> (строка {order['row']})\n"
                f"   📅 {order['date']}\n"
                f"   💰 Сумма: ${order['amount']:.2f}\n"
                f"   💵 Оплачено: ${order['paid']:.2f}\n"
                f"   {'🔴 Долг' if order['debt'] > 0 else '🟢 Переплата'}: "
                f"${abs(order['debt']):.2f}\n\n"
            )

        if total_debt <= 0:
            text = (
                f"💰 <b>Заказчик: {client}</b>\n\n"
                f"{orders_text}"
                f"📊 <b>Итого:</b>\n"
                f"   Сумма заказов: ${total_amount:.2f}\n"
                f"   Оплачено: ${total_paid:.2f}\n"
                f"   🟢 Переплата: ${abs(total_debt):.2f}\n\n"
                "✅ У этого заказчика нет долга!"
            )
            if is_callback:
                await message.edit_text(text, reply_markup=get_cancel_keyboard(), parse_mode="HTML")
            else:
                await message.answer(text, reply_markup=get_cancel_keyboard(), parse_mode="HTML")
            await state.clear()
            return

        text = (
            f"💰 <b>Заказчик: {client}</b>\n\n"
            f"{orders_text}"
            f"📊 <b>Итого:</b>\n"
            f"   Сумма заказов: ${total_amount:.2f}\n"
            f"   Оплачено: ${total_paid:.2f}\n"
            f"   🔴 Долг: ${total_debt:.2f}\n\n"
            f"💡 Заказов с долгом: {len(orders_with_debt)}\n"
            f"Оплата будет распределена по FIFO (начиная с самого старого заказа).\n\n"
            "Введите <b>сумму оплаты</b> (в $):"
        )
        if is_callback:
            await message.edit_text(text, reply_markup=get_cancel_keyboard(), parse_mode="HTML")
        else:
            await message.answer(text, reply_markup=get_cancel_keyboard(), parse_mode="HTML")
        await state.set_state(PaymentStates.waiting_for_amount)

    except Exception as e:
        logger.error(f"Error loading client orders: {e}")
        text = f"❌ <b>Ошибка загрузки!</b>\n\n{str(e)}"
        if is_callback:
            await message.edit_text(text, reply_markup=get_cancel_keyboard(), parse_mode="HTML")
        else:
            await message.answer(text, reply_markup=get_cancel_keyboard(), parse_mode="HTML")


@router.message(PaymentStates.waiting_for_client)
async def payment_enter_client(message: Message, state: FSMContext):
    """Client name entered manually - show orders with debt."""
    client = message.text.strip()

    if not client:
        await message.answer("❌ Введите имя заказчика:")
        return

    await process_client_selection(message, state, client, is_callback=False)


@router.message(PaymentStates.waiting_for_amount)
async def payment_enter_amount(message: Message, state: FSMContext):
    """Payment amount entered - show distribution preview and confirm."""
    try:
        amount = float(message.text.strip().replace(",", ".").replace("$", ""))
        if amount <= 0:
            raise ValueError("Amount must be positive")
    except ValueError:
        await message.answer("❌ Введите корректную сумму (число):")
        return

    data = await state.get_data()
    client = data["client"]
    orders = data["orders"]
    total_debt = data["total_debt"]

    remaining = amount
    distribution = []

    orders_with_debt = [o for o in orders if o["debt"] > 0]
    for order in orders_with_debt:
        if remaining <= 0:
            break

        debt = order["debt"]
        to_apply = min(remaining, debt)

        distribution.append({
            "row": order["row"],
            "date": order["date"],
            "amount": order["amount"],
            "old_paid": order["paid"],
            "new_paid": order["paid"] + to_apply,
            "applied": to_apply,
            "remaining_debt": debt - to_apply
        })

        remaining -= to_apply

    await state.update_data(
        payment_amount=amount,
        distribution=distribution,
        remaining_after=remaining
    )

    dist_text = ""
    for d in distribution:
        dist_text += (
            f"📍 Строка {d['row']} ({d['date']})\n"
            f"   Заказ: ${d['amount']:.2f}\n"
            f"   Было: ${d['old_paid']:.2f} → Станет: ${d['new_paid']:.2f}\n"
            f"   Применено: +${d['applied']:.2f}\n"
            f"   Остаток долга: ${d['remaining_debt']:.2f}\n\n"
        )

    extra_text = ""
    if remaining > 0:
        extra_text = f"\n⚠️ <b>Остаток после распределения: ${remaining:.2f}</b>\n(будет переплатой)"

    await message.answer(
        f"📋 <b>ПОДТВЕРЖДЕНИЕ ОПЛАТЫ</b>\n\n"
        f"👤 Заказчик: <b>{client}</b>\n"
        f"💰 Сумма оплаты: <b>${amount:.2f}</b>\n"
        f"🔴 Общий долг: ${total_debt:.2f}\n\n"
        f"<b>Распределение (FIFO):</b>\n\n"
        f"{dist_text}"
        f"{extra_text}\n"
        "Подтвердить оплату?",
        reply_markup=get_confirm_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(PaymentStates.waiting_for_confirmation)


@router.callback_query(F.data == "confirm", PaymentStates.waiting_for_confirmation)
async def payment_confirm(callback: CallbackQuery, state: FSMContext):
    """Confirm and apply payment to Google Sheets."""
    data = await state.get_data()
    client_name = data["client"]
    payment_amount = data["payment_amount"]

    await callback.message.edit_text(
        "⏳ Применение оплаты...",
        parse_mode="HTML"
    )

    try:
        sheets = get_sheets_client()
        await sheets.initialize()

        updates = await sheets.distribute_payment_fifo(client_name, payment_amount)

        if not updates:
            await callback.message.edit_text(
                "⚠️ Не удалось применить оплату.\n"
                "Возможно, долги уже были погашены.",
                reply_markup=get_main_menu(),
                parse_mode="HTML"
            )
            await state.clear()
            await callback.answer()
            return

        total_applied = sum(u["applied"] for u in updates)
        result_text = ""
        for u in updates:
            result_text += (
                f"✅ Строка {u['row']}: +${u['applied']:.2f} "
                f"(${u['old_paid']:.2f} → ${u['new_paid']:.2f})\n"
            )

        remaining = payment_amount - total_applied
        extra = ""
        if remaining > 0:
            extra = f"\n💡 Остаток (переплата): ${remaining:.2f}"

        await callback.message.edit_text(
            "✅ <b>ОПЛАТА ПРИМЕНЕНА!</b>\n\n"
            f"👤 Заказчик: {client_name}\n"
            f"💰 Сумма: ${payment_amount:.2f}\n"
            f"📝 Применено: ${total_applied:.2f}\n\n"
            f"<b>Обновлённые строки:</b>\n{result_text}"
            f"{extra}",
            reply_markup=get_main_menu(),
            parse_mode="HTML"
        )

        logger.info(f"Payment applied: client={client_name}, amount={payment_amount}, rows={len(updates)}")

    except Exception as e:
        logger.error(f"Error applying payment: {e}")
        await callback.message.edit_text(
            f"❌ <b>Ошибка применения оплаты!</b>\n\n{str(e)}",
            parse_mode="HTML"
        )

    await state.clear()
    await callback.answer("Оплата применена!")


# ============================================================================
# EXPENSE FLOW
# ============================================================================

@router.message(ExpenseStates.waiting_for_category)
async def expense_enter_category(message: Message, state: FSMContext):
    """Category entered - ask for amount."""
    category = message.text.strip()

    if not category:
        await message.answer("❌ Введите категорию расхода:")
        return

    await state.update_data(category=category)

    await message.answer(
        f"✅ Категория: <b>{category}</b>\n\n"
        "Введите <b>сумму расхода</b> (в $):",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(ExpenseStates.waiting_for_amount)


@router.message(ExpenseStates.waiting_for_amount)
async def expense_enter_amount(message: Message, state: FSMContext):
    """Amount entered - show confirmation."""
    try:
        amount = float(message.text.strip().replace(",", ".").replace("$", ""))
        if amount <= 0:
            raise ValueError("Amount must be positive")
    except ValueError:
        await message.answer("❌ Введите корректную сумму (число):")
        return

    data = await state.get_data()
    await state.update_data(amount=amount)

    await message.answer(
        "📋 <b>ПОДТВЕРЖДЕНИЕ РАСХОДА</b>\n\n"
        f"📁 Категория: <b>{data['category']}</b>\n"
        f"💰 Сумма: <b>${amount:.2f}</b>\n"
        f"📅 Дата: <b>{datetime.now().strftime('%d.%m.%Y')}</b>\n\n"
        "Подтвердить расход?",
        reply_markup=get_confirm_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(ExpenseStates.waiting_for_confirmation)


@router.callback_query(F.data == "confirm", ExpenseStates.waiting_for_confirmation)
async def expense_confirm(callback: CallbackQuery, state: FSMContext):
    """Confirm and save expense to Google Sheets."""
    data = await state.get_data()

    operation_id = str(uuid.uuid4())
    date_str = datetime.now().strftime("%d.%m.%Y")

    # Expense data for columns F-K:
    # F=date, G=category, H=amount, I=designer(empty), J=designer_amount(empty), K=total(formula)
    expense_data = [
        date_str,           # F - дата
        data["category"],   # G - категория
        data["amount"],     # H - сумма
        "",                 # I - ник дизайнера (пусто для обычных расходов)
        "",                 # J - сумма дизайнеру (пусто)
        "",                 # K - итоговый расход (формула, не трогаем)
    ]

    await callback.message.edit_text(
        "⏳ Сохранение расхода...",
        parse_mode="HTML"
    )

    try:
        client = get_sheets_client()
        await client.initialize()

        row_num = await client.write_row_expanding_table(
            sheet_key="expenses",
            operation_id=operation_id,
            data=expense_data
        )

        logger.info(f"Expense saved: row={row_num}, category={data['category']}, amount={data['amount']}")

        # NOTE: Расходы НЕ записываются в GENERAL - только в лист "Расходы"
        # Это сделано чтобы не ломать визуальную структуру таблицы GENERAL

        await state.clear()
        await callback.message.edit_text(
            "✅ <b>РАСХОД СОХРАНЁН!</b>\n\n"
            f"📁 Категория: {data['category']}\n"
            f"💰 Сумма: ${data['amount']:.2f}\n"
            f"📅 Дата: {date_str}",
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Error saving expense: {e}")
        await callback.message.edit_text(
            f"❌ <b>Ошибка сохранения!</b>\n\n{str(e)}",
            parse_mode="HTML"
        )
        await state.clear()

    await callback.answer("Расход сохранён!")


# ============================================================================
# PURE INCOME FLOW
# ============================================================================

@router.message(PureIncomeStates.waiting_for_category)
async def pure_income_enter_category(message: Message, state: FSMContext):
    """Category/name entered - ask for amount."""
    category = message.text.strip()

    if not category:
        await message.answer("❌ Введите название дохода:")
        return

    await state.update_data(category=category)

    await message.answer(
        f"✅ Название: <b>{category}</b>\n\n"
        "Введите <b>сумму дохода</b> (в $):",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(PureIncomeStates.waiting_for_amount)


@router.message(PureIncomeStates.waiting_for_amount)
async def pure_income_enter_amount(message: Message, state: FSMContext):
    """Amount entered - show confirmation."""
    try:
        amount = float(message.text.strip().replace(",", ".").replace("$", ""))
        if amount <= 0:
            raise ValueError("Amount must be positive")
    except ValueError:
        await message.answer("❌ Введите корректную сумму (число):")
        return

    data = await state.get_data()
    await state.update_data(amount=amount)

    await message.answer(
        "📋 <b>ПОДТВЕРЖДЕНИЕ ЧИСТОГО ДОХОДА</b>\n\n"
        f"📁 Название: <b>{data['category']}</b>\n"
        f"💰 Сумма: <b>${amount:.2f}</b>\n"
        f"📅 Дата: <b>{datetime.now().strftime('%d.%m.%Y')}</b>\n\n"
        "Подтвердить?",
        reply_markup=get_confirm_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(PureIncomeStates.waiting_for_confirmation)


@router.callback_query(F.data == "confirm", PureIncomeStates.waiting_for_confirmation)
async def pure_income_confirm(callback: CallbackQuery, state: FSMContext):
    """Confirm and save pure income to Google Sheets."""
    data = await state.get_data()

    operation_id = str(uuid.uuid4())
    date_str = datetime.now().strftime("%d.%m.%Y")

    await callback.message.edit_text(
        "⏳ Сохранение дохода...",
        parse_mode="HTML"
    )

    try:
        client = get_sheets_client()
        await client.initialize()

        row_num = await client.write_pure_income(
            operation_id=operation_id,
            date=date_str,
            category=data["category"],
            amount=data["amount"]
        )

        logger.info(f"Pure income saved: row={row_num}, category={data['category']}, amount={data['amount']}")

        general_row = await client.write_to_general(
            operation_id=operation_id,
            date=date_str,
            operation_type="pure_income",
            pure_income_category=data["category"],
            pure_income_amount=data["amount"],
            wallet_reserve=data["amount"]
        )
        logger.info(f"Written to GENERAL row {general_row}")

        await state.clear()
        await callback.message.edit_text(
            "✅ <b>ЧИСТЫЙ ДОХОД СОХРАНЁН!</b>\n\n"
            f"📁 Название: {data['category']}\n"
            f"💰 Сумма: ${data['amount']:.2f}\n"
            f"📅 Дата: {date_str}",
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Error saving pure income: {e}")
        await callback.message.edit_text(
            f"❌ <b>Ошибка сохранения!</b>\n\n{str(e)}",
            parse_mode="HTML"
        )
        await state.clear()

    await callback.answer("Доход сохранён!")


# ============================================================================
# ADD CLIENT FLOW
# ============================================================================

@router.callback_query(F.data == "add:client")
async def add_client_start(callback: CallbackQuery, state: FSMContext):
    """Start add client flow - ask for name."""
    await callback.message.edit_text(
        "👤 <b>Добавить заказчика</b>\n\n"
        "Введите <b>имя/ник заказчика</b>:",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(AddClientStates.waiting_for_name)
    await callback.answer()


@router.message(AddClientStates.waiting_for_name)
async def add_client_enter_name(message: Message, state: FSMContext):
    """Client name entered - show confirmation."""
    name = message.text.strip()

    if not name:
        await message.answer("❌ Введите имя заказчика:")
        return

    if len(name) < 2:
        await message.answer("❌ Имя должно быть не менее 2 символов:")
        return

    await state.update_data(name=name)

    await message.answer(
        "📋 <b>ПОДТВЕРЖДЕНИЕ</b>\n\n"
        f"👤 Заказчик: <b>{name}</b>\n\n"
        "Добавить заказчика?",
        reply_markup=get_confirm_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(AddClientStates.waiting_for_confirmation)


@router.callback_query(F.data == "confirm", AddClientStates.waiting_for_confirmation)
async def add_client_confirm(callback: CallbackQuery, state: FSMContext):
    """Confirm and save new client."""
    data = await state.get_data()
    name = data["name"]

    await callback.message.edit_text(
        "⏳ Добавление заказчика...",
        parse_mode="HTML"
    )

    try:
        client = get_sheets_client()
        await client.initialize()

        success = await client.add_new_client(name)

        if success:
            logger.info(f"New client added: {name}")
            await callback.message.edit_text(
                "✅ <b>ЗАКАЗЧИК ДОБАВЛЕН!</b>\n\n"
                f"👤 <b>{name}</b>\n\n"
                "Теперь можно создавать заказы с этим заказчиком.",
                reply_markup=get_main_menu(),
                parse_mode="HTML"
            )
        else:
            await callback.message.edit_text(
                "⚠️ <b>Заказчик уже существует!</b>\n\n"
                f"👤 <b>{name}</b> уже есть в базе.",
                reply_markup=get_main_menu(),
                parse_mode="HTML"
            )

    except Exception as e:
        logger.error(f"Error adding client: {e}")
        await callback.message.edit_text(
            f"❌ <b>Ошибка!</b>\n\n{str(e)}",
            parse_mode="HTML"
        )

    await state.clear()
    await callback.answer()


# ============================================================================
# ADD DESIGNER FLOW
# ============================================================================

@router.callback_query(F.data == "add:designer")
async def add_designer_start(callback: CallbackQuery, state: FSMContext):
    """Start add designer flow - ask for name."""
    await callback.message.edit_text(
        "🎨 <b>Добавить дизайнера</b>\n\n"
        "Введите <b>имя/ник дизайнера</b>:",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(AddDesignerStates.waiting_for_name)
    await callback.answer()


@router.message(AddDesignerStates.waiting_for_name)
async def add_designer_enter_name(message: Message, state: FSMContext):
    """Designer name entered - show confirmation."""
    name = message.text.strip()

    if not name:
        await message.answer("❌ Введите имя дизайнера:")
        return

    if len(name) < 2:
        await message.answer("❌ Имя должно быть не менее 2 символов:")
        return

    await state.update_data(name=name)

    await message.answer(
        "📋 <b>ПОДТВЕРЖДЕНИЕ</b>\n\n"
        f"🎨 Дизайнер: <b>{name}</b>\n\n"
        "Добавить дизайнера?",
        reply_markup=get_confirm_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(AddDesignerStates.waiting_for_confirmation)


@router.callback_query(F.data == "confirm", AddDesignerStates.waiting_for_confirmation)
async def add_designer_confirm(callback: CallbackQuery, state: FSMContext):
    """Confirm and save new designer."""
    data = await state.get_data()
    name = data["name"]

    await callback.message.edit_text(
        "⏳ Добавление дизайнера...",
        parse_mode="HTML"
    )

    try:
        client = get_sheets_client()
        await client.initialize()

        success = await client.add_new_designer(name)

        if success:
            logger.info(f"New designer added: {name}")
            await callback.message.edit_text(
                "✅ <b>ДИЗАЙНЕР ДОБАВЛЕН!</b>\n\n"
                f"🎨 <b>{name}</b>\n\n"
                "Теперь можно создавать заказы с этим дизайнером.",
                reply_markup=get_main_menu(),
                parse_mode="HTML"
            )
        else:
            await callback.message.edit_text(
                "⚠️ <b>Дизайнер уже существует!</b>\n\n"
                f"🎨 <b>{name}</b> уже есть в базе.",
                reply_markup=get_main_menu(),
                parse_mode="HTML"
            )

    except Exception as e:
        logger.error(f"Error adding designer: {e}")
        await callback.message.edit_text(
            f"❌ <b>Ошибка!</b>\n\n{str(e)}",
            parse_mode="HTML"
        )

    await state.clear()
    await callback.answer()
