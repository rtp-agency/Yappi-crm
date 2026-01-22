"""
Start command and main menu handlers.
"""
from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from loguru import logger

from src.bot.keyboards.main_menu import (
    get_main_menu,
    get_add_data_menu,
    get_lists_menu,
    get_list_clients_keyboard,
    get_client_in_list_keyboard,
    get_analytics_menu,
    get_analytics_back_keyboard,
    get_designer_info_keyboard,
    get_client_info_keyboard,
    get_back_keyboard,
    get_period_keyboard,
    get_period_back_keyboard,
    get_cancel_keyboard,
    get_dashboard_keyboard,
    get_expenses_keyboard,
    get_debts_keyboard
)
from src.bot.states.order_states import DateFilterStates
from src.services.sheets.client import get_sheets_client, SheetsClient

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Handle /start command."""
    # Clear any existing state
    await state.clear()

    await message.answer(
        f"👋 Привет, {message.from_user.first_name}!\n\n"
        "Это бот для учёта доходов дизайн-агентства.\n\n"
        "Выбери действие в меню:",
        reply_markup=get_main_menu()
    )


@router.message(F.text == "📊 Панель агентства")
async def show_dashboard(message: Message):
    """Show agency dashboard with data from GENERAL sheet."""
    await message.answer("⏳ Загрузка данных...")

    try:
        sheets = get_sheets_client()
        await sheets.initialize()
        data = await sheets.get_dashboard_data()

        if "error" in data:
            await message.answer(
                f"❌ <b>Ошибка загрузки данных</b>\n\n{data['error']}",
                parse_mode="HTML"
            )
            return

        # Format margin as percentage
        margin_pct = data['margin'] * 100 if data['margin'] < 1 else data['margin']

        balance_1 = data.get('balance_1', 0)
        balance_2 = data.get('balance_2', 0)
        total_balance = balance_1 + balance_2

        await message.answer(
            "📊 <b>ПАНЕЛЬ АГЕНТСТВА</b>\n\n"
            f"💰 Выручка: <b>${data['revenue']:,.2f}</b>\n"
            f"💸 Затраты: <b>${data['expenses']:,.2f}</b>\n"
            f"📈 Прибыль: <b>${data['profit']:,.2f}</b>\n"
            f"📊 Маржинальность: <b>{margin_pct:.1f}%</b>\n\n"
            f"💼 <b>Счета:</b>\n"
            f"   Операционный: <b>${balance_1:,.2f}</b>\n"
            f"   Резервный: <b>${balance_2:,.2f}</b>\n"
            f"   💰 Всего: <b>${total_balance:,.2f}</b>",
            reply_markup=get_dashboard_keyboard(),
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Error loading dashboard: {e}")
        await message.answer(
            f"❌ <b>Ошибка загрузки!</b>\n\n{str(e)}",
            parse_mode="HTML"
        )


@router.message(F.text == "➕ Добавить данные")
async def show_add_data_menu(message: Message):
    """Show add data submenu."""
    await message.answer(
        "➕ <b>Добавить данные</b>\n\n"
        "Выберите тип операции:",
        reply_markup=get_add_data_menu(),
        parse_mode="HTML"
    )


@router.message(F.text == "👤 Заказчики")
async def show_clients(message: Message):
    """Show clients list as buttons for selection."""
    await message.answer("⏳ Загрузка данных...")

    try:
        sheets = get_sheets_client()
        await sheets.initialize()
        clients = await sheets.get_clients_with_debts()

        if not clients:
            await message.answer(
                "👤 <b>Заказчики</b>\n\n"
                "Нет данных о заказчиках.",
                parse_mode="HTML"
            )
            return

        # Get list of client names
        client_names = [c["client"] for c in clients]

        # Summary stats
        total_debt = sum(c["total_debt"] for c in clients)
        total_amount = sum(c["total_amount"] for c in clients)

        await message.answer(
            f"👤 <b>ЗАКАЗЧИКИ</b>\n\n"
            f"📊 Всего заказчиков: <b>{len(clients)}</b>\n"
            f"💰 Общая сумма заказов: <b>${total_amount:,.2f}</b>\n"
            f"⚠️ Общий долг: <b>${total_debt:,.2f}</b>\n\n"
            "Выберите заказчика для просмотра аналитики:",
            reply_markup=get_client_info_keyboard(client_names),
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Error loading clients: {e}")
        await message.answer(
            f"❌ <b>Ошибка загрузки!</b>\n\n{str(e)}",
            parse_mode="HTML"
        )


@router.callback_query(F.data.startswith("client_info:"))
async def show_client_analytics(callback: CallbackQuery):
    """Show detailed analytics for a specific client."""
    client_name = callback.data.split(":", 1)[1]
    await callback.answer()

    try:
        sheets = get_sheets_client()
        await sheets.initialize()
        clients = await sheets.get_clients_with_debts()

        # Find the specific client
        client_data = None
        for c in clients:
            if c["client"] == client_name:
                client_data = c
                break

        if not client_data:
            await callback.message.edit_text(
                f"❌ Заказчик '{client_name}' не найден.",
                reply_markup=get_back_keyboard("menu:back"),
                parse_mode="HTML"
            )
            return

        # Debt icon
        debt_icon = "🔴" if client_data["total_debt"] > 0 else "🟢"

        # Build detailed analytics message
        lines = [
            f"👤 <b>АНАЛИТИКА: {client_name}</b>\n",
            "─" * 30,
            f"📦 Количество заказов: <b>{client_data['orders_count']}</b>",
            f"💰 Общая сумма заказов: <b>${client_data['total_amount']:,.2f}</b>",
            f"💳 Оплачено: <b>${client_data['total_paid']:,.2f}</b>",
            f"{debt_icon} Долг: <b>${client_data['total_debt']:,.2f}</b>",
        ]

        # Average order amount
        if client_data['orders_count'] > 0:
            avg_order = client_data['total_amount'] / client_data['orders_count']
            lines.append(f"📊 Средний заказ: <b>${avg_order:,.2f}</b>")

        # Payment percentage
        if client_data['total_amount'] > 0:
            payment_pct = (client_data['total_paid'] / client_data['total_amount']) * 100
            lines.append(f"💹 Процент оплаты: <b>{payment_pct:.1f}%</b>")

        await callback.message.edit_text(
            "\n".join(lines),
            reply_markup=get_back_keyboard("menu:back"),
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Error loading client analytics: {e}")
        await callback.message.edit_text(
            f"❌ <b>Ошибка загрузки!</b>\n\n{str(e)}",
            reply_markup=get_back_keyboard("menu:back"),
            parse_mode="HTML"
        )


@router.message(F.text == "🎨 Дизайнеры")
async def show_designers(message: Message):
    """Show designers list as buttons for selection."""
    await message.answer("⏳ Загрузка данных...")

    try:
        sheets = get_sheets_client()
        await sheets.initialize()
        designers = await sheets.get_designers_with_earnings()

        if not designers:
            await message.answer(
                "🎨 <b>Дизайнеры</b>\n\n"
                "Нет данных о дизайнерах.",
                parse_mode="HTML"
            )
            return

        # Get list of designer names
        designer_names = [d["designer"] for d in designers]

        # Summary stats
        total_earnings = sum(d["total_earnings"] for d in designers)
        total_orders = sum(d["orders_count"] for d in designers)

        await message.answer(
            f"🎨 <b>ДИЗАЙНЕРЫ</b>\n\n"
            f"📊 Всего дизайнеров: <b>{len(designers)}</b>\n"
            f"📦 Всего заказов: <b>{total_orders}</b>\n"
            f"💵 Общий заработок: <b>${total_earnings:,.2f}</b>\n\n"
            "Выберите дизайнера для просмотра аналитики:",
            reply_markup=get_designer_info_keyboard(designer_names),
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Error loading designers: {e}")
        await message.answer(
            f"❌ <b>Ошибка загрузки!</b>\n\n{str(e)}",
            parse_mode="HTML"
        )


@router.callback_query(F.data.startswith("designer_info:"))
async def show_designer_analytics(callback: CallbackQuery):
    """Show detailed analytics for a specific designer."""
    designer_name = callback.data.split(":", 1)[1]
    await callback.answer()

    try:
        sheets = get_sheets_client()
        await sheets.initialize()
        designers = await sheets.get_designers_with_earnings()

        # Find the specific designer
        designer_data = None
        for d in designers:
            if d["designer"] == designer_name:
                designer_data = d
                break

        if not designer_data:
            await callback.message.edit_text(
                f"❌ Дизайнер '{designer_name}' не найден.",
                reply_markup=get_back_keyboard("menu:back"),
                parse_mode="HTML"
            )
            return

        # Build detailed analytics message
        lines = [
            f"🎨 <b>АНАЛИТИКА: {designer_name}</b>\n",
            "─" * 30,
            f"📦 Количество заказов: <b>{designer_data['orders_count']}</b>",
            f"💰 Общая сумма заказов: <b>${designer_data['total_amount']:,.2f}</b>",
            f"💵 Заработок дизайнера: <b>${designer_data['total_earnings']:,.2f}</b>",
        ]

        # Calculate agency profit from this designer
        agency_profit = designer_data['total_amount'] - designer_data['total_earnings']
        lines.append(f"🏢 Доход агентства: <b>${agency_profit:,.2f}</b>")

        # Average order amount
        if designer_data['orders_count'] > 0:
            avg_order = designer_data['total_amount'] / designer_data['orders_count']
            lines.append(f"📊 Средний заказ: <b>${avg_order:,.2f}</b>")

        await callback.message.edit_text(
            "\n".join(lines),
            reply_markup=get_back_keyboard("menu:back"),
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Error loading designer analytics: {e}")
        await callback.message.edit_text(
            f"❌ <b>Ошибка загрузки!</b>\n\n{str(e)}",
            reply_markup=get_back_keyboard("menu:back"),
            parse_mode="HTML"
        )


@router.message(F.text == "💸 Расходы")
async def show_expenses(message: Message):
    """Show expenses by category."""
    await message.answer("⏳ Загрузка данных...")

    try:
        sheets = get_sheets_client()
        await sheets.initialize()

        # Get total from formula cell F4 in "Расходы" sheet
        total_amount = await sheets.get_total_expenses()
        expenses = await sheets.get_expenses_by_category()
        designer_payments = await sheets.get_designer_payments()

        if not expenses and total_amount == 0 and not designer_payments:
            await message.answer(
                "💸 <b>Расходы</b>\n\n"
                "Нет данных о расходах.",
                parse_mode="HTML"
            )
            return

        # Build message
        lines = ["💸 <b>РАСХОДЫ</b>\n"]

        total_designer_payments = sum(p["amount"] for p in designer_payments)
        total_manual_expenses = sum(e["total_amount"] for e in expenses) if expenses else 0

        lines.append(f"💰 <b>Итого расходов: ${total_amount:,.2f}</b>\n")

        # Designer payments section
        lines.append("🎨 <b>ОПЛАТЫ ДИЗАЙНЕРАМ</b>")
        lines.append("─" * 25)

        if designer_payments:
            lines.append(f"💵 Всего оплачено: <b>${total_designer_payments:,.2f}</b>\n")

            for payment in designer_payments:
                lines.append(
                    f"🎨 <b>{payment['designer']}</b>: ${payment['amount']:,.2f}"
                )
        else:
            lines.append("Нет оплат дизайнерам")

        # Manual expenses section
        lines.append("\n" + "─" * 25)
        lines.append("\n📁 <b>ТЕКУЩИЕ РАСХОДЫ</b>")
        lines.append("─" * 25)

        if expenses:
            total_count = sum(e["count"] for e in expenses)
            lines.append(f"📊 Категорий: <b>{len(expenses)}</b>")
            lines.append(f"💵 Сумма: <b>${total_manual_expenses:,.2f}</b>\n")

            for expense in expenses:
                lines.append(
                    f"📁 <b>{expense['category']}</b>\n"
                    f"   📦 Записей: {expense['count']}\n"
                    f"   💰 Сумма: ${expense['total_amount']:,.2f}"
                )
        else:
            lines.append("Нет текущих расходов")

        await message.answer(
            "\n".join(lines),
            reply_markup=get_expenses_keyboard(),
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Error loading expenses: {e}")
        await message.answer(
            f"❌ <b>Ошибка загрузки!</b>\n\n{str(e)}",
            parse_mode="HTML"
        )


@router.message(F.text == "⚠️ Долги/Листы")
async def show_debts(message: Message):
    """Show debtors and lists."""
    await message.answer("⏳ Загрузка данных...")

    try:
        sheets = get_sheets_client()
        await sheets.initialize()
        debtors = await sheets.get_debtors()
        whitelist = await sheets.get_whitelist_clients()
        blacklist = await sheets.get_blacklist_clients()

        # Build message
        lines = ["⚠️ <b>ДОЛГИ И ЛИСТЫ</b>\n"]

        # Debtors section
        lines.append("💸 <b>ДОЛЖНИКИ</b>")
        lines.append("─" * 25)

        if not debtors:
            lines.append("✅ Нет должников!")
        else:
            total_debt = sum(d["total_debt"] for d in debtors)
            lines.append(f"⚠️ Общий долг: <b>${total_debt:,.2f}</b>\n")

            for debtor in debtors[:10]:  # Limit to 10
                lines.append(
                    f"🔴 <b>{debtor['client']}</b>\n"
                    f"   💰 Сумма заказов: ${debtor['total_amount']:,.2f}\n"
                    f"   💳 Оплачено: ${debtor['total_paid']:,.2f}\n"
                    f"   ⚠️ Долг: <b>${debtor['total_debt']:,.2f}</b>"
                )

            if len(debtors) > 10:
                lines.append(f"\n... и ещё {len(debtors) - 10} должников")

        # White/Black list summary
        lines.append("\n" + "─" * 25)
        lines.append("\n📋 <b>ЛИСТЫ</b>")
        lines.append(f"🟢 White list: <b>{len(whitelist)}</b> заказчиков")
        lines.append(f"🔴 Black list: <b>{len(blacklist)}</b> заказчиков")

        await message.answer(
            "\n".join(lines),
            parse_mode="HTML",
            reply_markup=get_debts_keyboard()
        )

    except Exception as e:
        logger.error(f"Error loading debts: {e}")
        await message.answer(
            f"❌ <b>Ошибка загрузки!</b>\n\n{str(e)}",
            parse_mode="HTML"
        )


@router.message(F.text == "📈 Аналитика")
async def show_analytics(message: Message):
    """Show analytics main menu."""
    await message.answer("⏳ Загрузка данных...")

    try:
        sheets = get_sheets_client()
        await sheets.initialize()
        data = await sheets.get_analytics_data()

        if "error" in data:
            await message.answer(
                f"❌ <b>Ошибка загрузки данных</b>\n\n{data['error']}",
                parse_mode="HTML"
            )
            return

        # Build main analytics message
        # Data from GENERAL summary cells: G4=выручка, I4=затраты, K4=прибыль, M4=маржинальность
        lines = ["📈 <b>АНАЛИТИКА АГЕНТСТВА</b>\n"]
        lines.append("─" * 25)

        # P&L summary from GENERAL formulas
        lines.append("\n💰 <b>P&L</b>")
        lines.append(f"   📊 Выручка: <b>${data['revenue']:,.2f}</b>")
        lines.append(f"   💸 Затраты: <b>${data['expenses']:,.2f}</b>")
        lines.append(f"   📈 Прибыль: <b>${data['profit']:,.2f}</b>")

        # Format margin as percentage
        margin_pct = data['margin'] * 100 if data['margin'] < 1 else data['margin']
        lines.append(f"   📊 Маржинальность: <b>{margin_pct:.1f}%</b>")

        # Pure income
        lines.append(f"\n💎 <b>ЧИСТЫЙ ДОХОД</b>")
        lines.append(f"   💎 Чистый доход: <b>${data['pure_income']:,.2f}</b>")

        # Wallets (account balances from T and U columns)
        lines.append(f"\n💼 <b>КОШЕЛЬКИ</b>")
        lines.append(f"   💼 Счёт 1: <b>${data['balance_1']:,.2f}</b>")
        lines.append(f"   🏦 Счёт 2: <b>${data['balance_2']:,.2f}</b>")

        # Total balance
        total_balance = data['balance_1'] + data['balance_2']
        lines.append(f"\n💵 <b>ИТОГО НА КОШЕ: ${total_balance:,.2f}</b>")

        lines.append("\n" + "─" * 25)
        lines.append("\n<i>Выберите раздел для детализации:</i>")

        await message.answer(
            "\n".join(lines),
            parse_mode="HTML",
            reply_markup=get_analytics_menu()
        )

    except Exception as e:
        logger.error(f"Error loading analytics: {e}")
        await message.answer(
            f"❌ <b>Ошибка загрузки!</b>\n\n{str(e)}",
            parse_mode="HTML"
        )


@router.message(F.text == "⚙️ Настройки")
async def show_settings(message: Message):
    """Show settings."""
    await message.answer(
        "⚙️ <b>Настройки</b>\n\n"
        "🚧 В разработке...",
        parse_mode="HTML"
    )


# Callback handlers for inline menu
@router.callback_query(F.data == "menu:back")
async def callback_menu_back(callback: CallbackQuery):
    """Handle back button - return to main menu."""
    await callback.message.delete()
    await callback.message.answer(
        "🏠 <b>Главное меню</b>\n\nВыберите действие:",
        reply_markup=get_main_menu(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "menu:add_data")
async def callback_add_data(callback: CallbackQuery):
    """Show add data menu from callback."""
    await callback.message.edit_text(
        "➕ <b>Добавить данные</b>\n\n"
        "Выберите тип операции:",
        reply_markup=get_add_data_menu(),
        parse_mode="HTML"
    )
    await callback.answer()


# ============================================================================
# LIST MANAGEMENT CALLBACKS
# ============================================================================

@router.callback_query(F.data == "lists:back")
async def callback_lists_back(callback: CallbackQuery):
    """Go back to lists menu."""
    try:
        sheets = get_sheets_client()
        await sheets.initialize()
        whitelist = await sheets.get_whitelist_clients()
        blacklist = await sheets.get_blacklist_clients()

        await callback.message.edit_text(
            "📋 <b>УПРАВЛЕНИЕ ЛИСТАМИ</b>\n\n"
            f"🟢 White list: <b>{len(whitelist)}</b> заказчиков\n"
            f"🔴 Black list: <b>{len(blacklist)}</b> заказчиков",
            parse_mode="HTML",
            reply_markup=get_lists_menu()
        )
    except Exception as e:
        logger.error(f"Error in lists_back: {e}")
        await callback.message.edit_text(
            "📋 <b>УПРАВЛЕНИЕ ЛИСТАМИ</b>",
            parse_mode="HTML",
            reply_markup=get_lists_menu()
        )
    await callback.answer()


@router.callback_query(F.data == "lists:whitelist")
async def callback_show_whitelist(callback: CallbackQuery):
    """Show whitelist clients."""
    try:
        sheets = get_sheets_client()
        await sheets.initialize()
        whitelist = await sheets.get_whitelist_clients()

        if not whitelist:
            await callback.message.edit_text(
                "🟢 <b>WHITE LIST</b>\n\n"
                "Список пуст.\n\n"
                "<i>Добавьте надёжных заказчиков в белый список.</i>",
                parse_mode="HTML",
                reply_markup=get_lists_menu()
            )
        else:
            lines = ["🟢 <b>WHITE LIST</b>\n"]
            lines.append(f"Надёжных заказчиков: <b>{len(whitelist)}</b>\n")
            lines.append("─" * 25)

            for client in whitelist:
                lines.append(f"✅ {client}")

            await callback.message.edit_text(
                "\n".join(lines),
                parse_mode="HTML",
                reply_markup=get_list_clients_keyboard(whitelist, "manage_white")
            )
    except Exception as e:
        logger.error(f"Error showing whitelist: {e}")
        await callback.answer(f"Ошибка: {e}", show_alert=True)
    await callback.answer()


@router.callback_query(F.data == "lists:blacklist")
async def callback_show_blacklist(callback: CallbackQuery):
    """Show blacklist clients."""
    try:
        sheets = get_sheets_client()
        await sheets.initialize()
        blacklist = await sheets.get_blacklist_clients()

        if not blacklist:
            await callback.message.edit_text(
                "🔴 <b>BLACK LIST</b>\n\n"
                "Список пуст.\n\n"
                "<i>Добавьте проблемных заказчиков в чёрный список.</i>",
                parse_mode="HTML",
                reply_markup=get_lists_menu()
            )
        else:
            lines = ["🔴 <b>BLACK LIST</b>\n"]
            lines.append(f"Проблемных заказчиков: <b>{len(blacklist)}</b>\n")
            lines.append("─" * 25)

            for client in blacklist:
                lines.append(f"⛔ {client}")

            await callback.message.edit_text(
                "\n".join(lines),
                parse_mode="HTML",
                reply_markup=get_list_clients_keyboard(blacklist, "manage_black")
            )
    except Exception as e:
        logger.error(f"Error showing blacklist: {e}")
        await callback.answer(f"Ошибка: {e}", show_alert=True)
    await callback.answer()


@router.callback_query(F.data == "lists:add_white")
async def callback_add_to_whitelist(callback: CallbackQuery):
    """Show clients to add to whitelist."""
    try:
        sheets = get_sheets_client()
        await sheets.initialize()

        # Get all clients
        all_clients = await sheets.get_unique_clients()
        whitelist = await sheets.get_whitelist_clients()

        # Filter out clients already in whitelist
        available = [c for c in all_clients if c not in whitelist]

        if not available:
            await callback.answer("Все заказчики уже в White list!", show_alert=True)
            return

        await callback.message.edit_text(
            "🟢 <b>ДОБАВИТЬ В WHITE LIST</b>\n\n"
            "Выберите заказчика:",
            parse_mode="HTML",
            reply_markup=get_list_clients_keyboard(available, "to_white")
        )
    except Exception as e:
        logger.error(f"Error in add_to_whitelist: {e}")
        await callback.answer(f"Ошибка: {e}", show_alert=True)
    await callback.answer()


@router.callback_query(F.data == "lists:add_black")
async def callback_add_to_blacklist(callback: CallbackQuery):
    """Show clients to add to blacklist."""
    try:
        sheets = get_sheets_client()
        await sheets.initialize()

        # Get all clients
        all_clients = await sheets.get_unique_clients()
        blacklist = await sheets.get_blacklist_clients()

        # Filter out clients already in blacklist
        available = [c for c in all_clients if c not in blacklist]

        if not available:
            await callback.answer("Все заказчики уже в Black list!", show_alert=True)
            return

        await callback.message.edit_text(
            "🔴 <b>ДОБАВИТЬ В BLACK LIST</b>\n\n"
            "Выберите заказчика:",
            parse_mode="HTML",
            reply_markup=get_list_clients_keyboard(available, "to_black")
        )
    except Exception as e:
        logger.error(f"Error in add_to_blacklist: {e}")
        await callback.answer(f"Ошибка: {e}", show_alert=True)
    await callback.answer()


@router.callback_query(F.data.startswith("list_action:"))
async def callback_list_action(callback: CallbackQuery):
    """Handle list actions (to_white, to_black, remove, manage)."""
    try:
        parts = callback.data.split(":", 2)
        if len(parts) < 3:
            await callback.answer("Неверный формат данных", show_alert=True)
            return

        action = parts[1]
        client_name = parts[2]

        sheets = get_sheets_client()
        await sheets.initialize()

        if action == "to_white":
            success = await sheets.add_to_whitelist(client_name)
            if success:
                await callback.answer(f"✅ {client_name} добавлен в White list!")
                # Refresh list view
                whitelist = await sheets.get_whitelist_clients()
                blacklist = await sheets.get_blacklist_clients()

                await callback.message.edit_text(
                    "📋 <b>УПРАВЛЕНИЕ ЛИСТАМИ</b>\n\n"
                    f"🟢 White list: <b>{len(whitelist)}</b> заказчиков\n"
                    f"🔴 Black list: <b>{len(blacklist)}</b> заказчиков\n\n"
                    f"✅ <i>{client_name} добавлен в White list</i>",
                    parse_mode="HTML",
                    reply_markup=get_lists_menu()
                )
            else:
                await callback.answer("Ошибка добавления!", show_alert=True)

        elif action == "to_black":
            success = await sheets.add_to_blacklist(client_name)
            if success:
                await callback.answer(f"⛔ {client_name} добавлен в Black list!")
                # Refresh list view
                whitelist = await sheets.get_whitelist_clients()
                blacklist = await sheets.get_blacklist_clients()

                await callback.message.edit_text(
                    "📋 <b>УПРАВЛЕНИЕ ЛИСТАМИ</b>\n\n"
                    f"🟢 White list: <b>{len(whitelist)}</b> заказчиков\n"
                    f"🔴 Black list: <b>{len(blacklist)}</b> заказчиков\n\n"
                    f"⛔ <i>{client_name} добавлен в Black list</i>",
                    parse_mode="HTML",
                    reply_markup=get_lists_menu()
                )
            else:
                await callback.answer("Ошибка добавления!", show_alert=True)

        elif action == "remove":
            success = await sheets.remove_from_lists(client_name)
            if success:
                await callback.answer(f"❌ {client_name} убран из листа!")
                # Refresh list view
                whitelist = await sheets.get_whitelist_clients()
                blacklist = await sheets.get_blacklist_clients()

                await callback.message.edit_text(
                    "📋 <b>УПРАВЛЕНИЕ ЛИСТАМИ</b>\n\n"
                    f"🟢 White list: <b>{len(whitelist)}</b> заказчиков\n"
                    f"🔴 Black list: <b>{len(blacklist)}</b> заказчиков\n\n"
                    f"<i>{client_name} убран из листа</i>",
                    parse_mode="HTML",
                    reply_markup=get_lists_menu()
                )
            else:
                await callback.answer("Ошибка удаления!", show_alert=True)

        elif action == "manage_white":
            # Show management options for whitelist client
            await callback.message.edit_text(
                f"🟢 <b>ЗАКАЗЧИК В WHITE LIST</b>\n\n"
                f"👤 <b>{client_name}</b>\n\n"
                "Выберите действие:",
                parse_mode="HTML",
                reply_markup=get_client_in_list_keyboard(client_name, "whitelist")
            )

        elif action == "manage_black":
            # Show management options for blacklist client
            await callback.message.edit_text(
                f"🔴 <b>ЗАКАЗЧИК В BLACK LIST</b>\n\n"
                f"👤 <b>{client_name}</b>\n\n"
                "Выберите действие:",
                parse_mode="HTML",
                reply_markup=get_client_in_list_keyboard(client_name, "blacklist")
            )

    except Exception as e:
        logger.error(f"Error in list_action: {e}")
        await callback.answer(f"Ошибка: {e}", show_alert=True)


# ============================================================================
# ANALYTICS CALLBACKS
# ============================================================================

@router.callback_query(F.data == "analytics:back")
async def callback_analytics_back(callback: CallbackQuery):
    """Go back to analytics main view."""
    try:
        sheets = get_sheets_client()
        await sheets.initialize()
        data = await sheets.get_analytics_data()

        if "error" in data:
            await callback.message.edit_text(
                f"❌ <b>Ошибка загрузки данных</b>\n\n{data['error']}",
                parse_mode="HTML"
            )
            await callback.answer()
            return

        # Build main analytics message
        # Data from GENERAL summary cells: G4=выручка, I4=затраты, K4=прибыль, M4=маржинальность
        lines = ["📈 <b>АНАЛИТИКА АГЕНТСТВА</b>\n"]
        lines.append("─" * 25)

        # P&L summary from GENERAL formulas
        lines.append("\n💰 <b>P&L</b>")
        lines.append(f"   📊 Выручка: <b>${data['revenue']:,.2f}</b>")
        lines.append(f"   💸 Затраты: <b>${data['expenses']:,.2f}</b>")
        lines.append(f"   📈 Прибыль: <b>${data['profit']:,.2f}</b>")

        # Format margin as percentage
        margin_pct = data['margin'] * 100 if data['margin'] < 1 else data['margin']
        lines.append(f"   📊 Маржинальность: <b>{margin_pct:.1f}%</b>")

        # Pure income
        lines.append(f"\n💎 <b>ЧИСТЫЙ ДОХОД</b>")
        lines.append(f"   💎 Чистый доход: <b>${data['pure_income']:,.2f}</b>")

        # Wallets (account balances from T and U columns)
        lines.append(f"\n💼 <b>КОШЕЛЬКИ</b>")
        lines.append(f"   💼 Счёт 1: <b>${data['balance_1']:,.2f}</b>")
        lines.append(f"   🏦 Счёт 2: <b>${data['balance_2']:,.2f}</b>")

        # Total balance
        total_balance = data['balance_1'] + data['balance_2']
        lines.append(f"\n💵 <b>ИТОГО НА КОШЕ: ${total_balance:,.2f}</b>")

        lines.append("\n" + "─" * 25)
        lines.append("\n<i>Выберите раздел для детализации:</i>")

        await callback.message.edit_text(
            "\n".join(lines),
            parse_mode="HTML",
            reply_markup=get_analytics_menu()
        )

    except Exception as e:
        logger.error(f"Error in analytics_back: {e}")
        await callback.answer(f"Ошибка: {e}", show_alert=True)
    await callback.answer()


@router.callback_query(F.data == "analytics:designers")
async def callback_analytics_designers(callback: CallbackQuery):
    """Show profit by designers."""
    try:
        sheets = get_sheets_client()
        await sheets.initialize()
        data = await sheets.get_analytics_data()

        if "error" in data:
            await callback.answer(f"Ошибка: {data['error']}", show_alert=True)
            return

        by_designer = data.get("by_designer", {})

        lines = ["🎨 <b>ПРИБЫЛЬ ПО ДИЗАЙНЕРАМ</b>\n"]
        lines.append("─" * 25)

        if not by_designer:
            lines.append("\n<i>Нет данных о прибыли от дизайнеров</i>")
        else:
            total = sum(by_designer.values())
            lines.append(f"\n📊 Всего дизайнеров: <b>{len(by_designer)}</b>")
            lines.append(f"💰 Общая прибыль: <b>${total:,.2f}</b>\n")
            lines.append("─" * 25)

            for designer, income in list(by_designer.items())[:15]:
                pct = (income / total * 100) if total > 0 else 0
                lines.append(
                    f"\n🎨 <b>{designer}</b>\n"
                    f"   💵 Прибыль: <b>${income:,.2f}</b>\n"
                    f"   📊 Доля: <b>{pct:.1f}%</b>"
                )

            if len(by_designer) > 15:
                lines.append(f"\n... и ещё {len(by_designer) - 15} дизайнеров")

        await callback.message.edit_text(
            "\n".join(lines),
            parse_mode="HTML",
            reply_markup=get_analytics_back_keyboard()
        )

    except Exception as e:
        logger.error(f"Error in analytics_designers: {e}")
        await callback.answer(f"Ошибка: {e}", show_alert=True)
    await callback.answer()


@router.callback_query(F.data == "analytics:clients")
async def callback_analytics_clients(callback: CallbackQuery):
    """Show profit by clients."""
    try:
        sheets = get_sheets_client()
        await sheets.initialize()
        data = await sheets.get_analytics_data()

        if "error" in data:
            await callback.answer(f"Ошибка: {data['error']}", show_alert=True)
            return

        by_client = data.get("by_client", {})

        lines = ["👤 <b>ПРИБЫЛЬ ПО ЗАКАЗЧИКАМ</b>\n"]
        lines.append("─" * 25)

        if not by_client:
            lines.append("\n<i>Нет данных о прибыли от заказчиков</i>")
        else:
            total = sum(by_client.values())
            lines.append(f"\n📊 Всего заказчиков: <b>{len(by_client)}</b>")
            lines.append(f"💰 Общая прибыль: <b>${total:,.2f}</b>\n")
            lines.append("─" * 25)

            for client, income in list(by_client.items())[:15]:
                pct = (income / total * 100) if total > 0 else 0
                lines.append(
                    f"\n👤 <b>{client}</b>\n"
                    f"   💵 Прибыль: <b>${income:,.2f}</b>\n"
                    f"   📊 Доля: <b>{pct:.1f}%</b>"
                )

            if len(by_client) > 15:
                lines.append(f"\n... и ещё {len(by_client) - 15} заказчиков")

        await callback.message.edit_text(
            "\n".join(lines),
            parse_mode="HTML",
            reply_markup=get_analytics_back_keyboard()
        )

    except Exception as e:
        logger.error(f"Error in analytics_clients: {e}")
        await callback.answer(f"Ошибка: {e}", show_alert=True)
    await callback.answer()


# =============================================================================
# DATE FILTER HANDLERS
# =============================================================================

PERIOD_LABELS = {
    "today": "Сегодня",
    "week": "Эта неделя",
    "month": "Этот месяц",
    "all": "Весь период"
}


@router.callback_query(F.data == "filter:designers")
async def filter_designers(callback: CallbackQuery):
    """Show period selection for designers filter."""
    await callback.answer()
    await callback.message.edit_text(
        "📅 <b>Фильтр по датам</b>\n\n"
        "Выберите период для просмотра данных по дизайнерам:",
        reply_markup=get_period_keyboard("designers"),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "filter:clients")
async def filter_clients(callback: CallbackQuery):
    """Show period selection for clients filter."""
    await callback.answer()
    await callback.message.edit_text(
        "📅 <b>Фильтр по датам</b>\n\n"
        "Выберите период для просмотра данных по заказчикам:",
        reply_markup=get_period_keyboard("clients"),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("period:designers:"))
async def period_designers(callback: CallbackQuery, state: FSMContext):
    """Handle designer period selection."""
    period = callback.data.split(":")[2]
    await callback.answer()

    # Handle custom date input
    if period == "custom":
        await state.update_data(filter_context="designers")
        await callback.message.edit_text(
            "📅 <b>Введите начальную дату</b>\n\n"
            "Формат: ДД.ММ.ГГГГ (например, 01.01.2024)",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML"
        )
        await state.set_state(DateFilterStates.waiting_for_start_date)
        return

    # Get period dates
    start_date, end_date = SheetsClient.get_period_dates(period)
    period_label = PERIOD_LABELS.get(period, period)

    try:
        sheets = get_sheets_client()
        await sheets.initialize()
        designers = await sheets.get_designers_with_earnings(start_date, end_date)

        if not designers:
            await callback.message.edit_text(
                f"🎨 <b>ДИЗАЙНЕРЫ</b>\n"
                f"📅 Период: {period_label}\n\n"
                "Нет данных за выбранный период.",
                reply_markup=get_period_back_keyboard("designers"),
                parse_mode="HTML"
            )
            return

        # Get list of designer names
        designer_names = [d["designer"] for d in designers]

        # Summary stats
        total_earnings = sum(d["total_earnings"] for d in designers)
        total_orders = sum(d["orders_count"] for d in designers)

        await callback.message.edit_text(
            f"🎨 <b>ДИЗАЙНЕРЫ</b>\n"
            f"📅 Период: {period_label}\n\n"
            f"📊 Всего дизайнеров: <b>{len(designers)}</b>\n"
            f"📦 Всего заказов: <b>{total_orders}</b>\n"
            f"💵 Общий заработок: <b>${total_earnings:,.2f}</b>\n\n"
            "Выберите дизайнера для просмотра аналитики:",
            reply_markup=get_designer_info_keyboard(designer_names, period_label),
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Error filtering designers: {e}")
        await callback.message.edit_text(
            f"❌ <b>Ошибка загрузки!</b>\n\n{str(e)}",
            reply_markup=get_back_keyboard("menu:back"),
            parse_mode="HTML"
        )


@router.callback_query(F.data.startswith("period:clients:"))
async def period_clients(callback: CallbackQuery, state: FSMContext):
    """Handle client period selection."""
    period = callback.data.split(":")[2]
    await callback.answer()

    # Handle custom date input
    if period == "custom":
        await state.update_data(filter_context="clients")
        await callback.message.edit_text(
            "📅 <b>Введите начальную дату</b>\n\n"
            "Формат: ДД.ММ.ГГГГ (например, 01.01.2024)",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML"
        )
        await state.set_state(DateFilterStates.waiting_for_start_date)
        return

    # Get period dates
    start_date, end_date = SheetsClient.get_period_dates(period)
    period_label = PERIOD_LABELS.get(period, period)

    try:
        sheets = get_sheets_client()
        await sheets.initialize()
        clients = await sheets.get_clients_with_debts(start_date, end_date)

        if not clients:
            await callback.message.edit_text(
                f"👤 <b>ЗАКАЗЧИКИ</b>\n"
                f"📅 Период: {period_label}\n\n"
                "Нет данных за выбранный период.",
                reply_markup=get_period_back_keyboard("clients"),
                parse_mode="HTML"
            )
            return

        # Get list of client names
        client_names = [c["client"] for c in clients]

        # Summary stats
        total_debt = sum(c["total_debt"] for c in clients)
        total_amount = sum(c["total_amount"] for c in clients)

        await callback.message.edit_text(
            f"👤 <b>ЗАКАЗЧИКИ</b>\n"
            f"📅 Период: {period_label}\n\n"
            f"📊 Всего заказчиков: <b>{len(clients)}</b>\n"
            f"💰 Общая сумма заказов: <b>${total_amount:,.2f}</b>\n"
            f"⚠️ Общий долг: <b>${total_debt:,.2f}</b>\n\n"
            "Выберите заказчика для просмотра аналитики:",
            reply_markup=get_client_info_keyboard(client_names, period_label),
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Error filtering clients: {e}")
        await callback.message.edit_text(
            f"❌ <b>Ошибка загрузки!</b>\n\n{str(e)}",
            reply_markup=get_back_keyboard("menu:back"),
            parse_mode="HTML"
        )


@router.callback_query(F.data == "filter:dashboard")
async def filter_dashboard(callback: CallbackQuery):
    """Show period selection for dashboard filter."""
    await callback.answer()
    await callback.message.edit_text(
        "📅 <b>Фильтр по датам</b>\n\n"
        "Выберите период для просмотра панели агентства:",
        reply_markup=get_period_keyboard("dashboard"),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "filter:expenses")
async def filter_expenses(callback: CallbackQuery):
    """Show period selection for expenses filter."""
    await callback.answer()
    await callback.message.edit_text(
        "📅 <b>Фильтр по датам</b>\n\n"
        "Выберите период для просмотра расходов:",
        reply_markup=get_period_keyboard("expenses"),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "filter:debts")
async def filter_debts(callback: CallbackQuery):
    """Show period selection for debts filter."""
    await callback.answer()
    await callback.message.edit_text(
        "📅 <b>Фильтр по датам</b>\n\n"
        "Выберите период для просмотра должников:",
        reply_markup=get_period_keyboard("debts"),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "lists:menu")
async def show_lists_menu(callback: CallbackQuery):
    """Show lists management menu."""
    await callback.answer()
    await callback.message.edit_text(
        "📋 <b>Управление листами</b>\n\n"
        "Выберите действие:",
        reply_markup=get_lists_menu(),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("period:dashboard:"))
async def period_dashboard(callback: CallbackQuery, state: FSMContext):
    """Handle dashboard period selection."""
    period = callback.data.split(":")[2]
    await callback.answer()

    if period == "custom":
        await state.update_data(filter_context="dashboard")
        await callback.message.edit_text(
            "📅 <b>Введите начальную дату</b>\n\n"
            "Формат: ДД.ММ.ГГГГ (например, 01.01.2024)",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML"
        )
        await state.set_state(DateFilterStates.waiting_for_start_date)
        return

    period_label = PERIOD_LABELS.get(period, period)

    try:
        sheets = get_sheets_client()
        await sheets.initialize()
        data = await sheets.get_dashboard_data_filtered(period)

        if "error" in data:
            await callback.message.edit_text(
                f"❌ <b>Ошибка загрузки данных</b>\n\n{data['error']}",
                reply_markup=get_back_keyboard("menu:back"),
                parse_mode="HTML"
            )
            return

        margin_pct = data['margin'] * 100 if data['margin'] < 1 else data['margin']
        balance_1 = data.get('balance_1', 0)
        balance_2 = data.get('balance_2', 0)
        total_balance = balance_1 + balance_2

        await callback.message.edit_text(
            f"📊 <b>ПАНЕЛЬ АГЕНТСТВА</b>\n"
            f"📅 Период: {period_label}\n\n"
            f"💰 Выручка: <b>${data['revenue']:,.2f}</b>\n"
            f"💸 Затраты: <b>${data['expenses']:,.2f}</b>\n"
            f"📈 Прибыль: <b>${data['profit']:,.2f}</b>\n"
            f"📊 Маржинальность: <b>{margin_pct:.1f}%</b>\n\n"
            f"💼 <b>Счета:</b>\n"
            f"   Операционный: <b>${balance_1:,.2f}</b>\n"
            f"   Резервный: <b>${balance_2:,.2f}</b>\n"
            f"   💰 Всего: <b>${total_balance:,.2f}</b>",
            reply_markup=get_dashboard_keyboard(period_label),
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Error filtering dashboard: {e}")
        await callback.message.edit_text(
            f"❌ <b>Ошибка загрузки!</b>\n\n{str(e)}",
            reply_markup=get_back_keyboard("menu:back"),
            parse_mode="HTML"
        )


@router.callback_query(F.data.startswith("period:expenses:"))
async def period_expenses(callback: CallbackQuery, state: FSMContext):
    """Handle expenses period selection."""
    period = callback.data.split(":")[2]
    await callback.answer()

    if period == "custom":
        await state.update_data(filter_context="expenses")
        await callback.message.edit_text(
            "📅 <b>Введите начальную дату</b>\n\n"
            "Формат: ДД.ММ.ГГГГ (например, 01.01.2024)",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML"
        )
        await state.set_state(DateFilterStates.waiting_for_start_date)
        return

    period_label = PERIOD_LABELS.get(period, period)

    try:
        sheets = get_sheets_client()
        await sheets.initialize()

        total_amount = await sheets.get_total_expenses()
        expenses = await sheets.get_expenses_by_category()
        designer_payments = await sheets.get_designer_payments()

        lines = [f"💸 <b>РАСХОДЫ</b>\n📅 Период: {period_label}\n"]

        total_designer_payments = sum(p["amount"] for p in designer_payments)
        total_manual_expenses = sum(e["total_amount"] for e in expenses) if expenses else 0

        lines.append(f"💰 <b>Итого расходов: ${total_amount:,.2f}</b>\n")

        lines.append("🎨 <b>ОПЛАТЫ ДИЗАЙНЕРАМ</b>")
        lines.append("─" * 25)

        if designer_payments:
            lines.append(f"💵 Всего оплачено: <b>${total_designer_payments:,.2f}</b>\n")
            for payment in designer_payments[:5]:
                lines.append(f"🎨 <b>{payment['designer']}</b>: ${payment['amount']:,.2f}")
        else:
            lines.append("Нет оплат дизайнерам")

        lines.append("\n" + "─" * 25)
        lines.append("\n📁 <b>ТЕКУЩИЕ РАСХОДЫ</b>")

        if expenses:
            lines.append(f"💵 Сумма: <b>${total_manual_expenses:,.2f}</b>\n")
            for expense in expenses[:5]:
                lines.append(f"📁 <b>{expense['category']}</b>: ${expense['total_amount']:,.2f}")
        else:
            lines.append("Нет текущих расходов")

        await callback.message.edit_text(
            "\n".join(lines),
            reply_markup=get_expenses_keyboard(period_label),
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Error filtering expenses: {e}")
        await callback.message.edit_text(
            f"❌ <b>Ошибка загрузки!</b>\n\n{str(e)}",
            reply_markup=get_back_keyboard("menu:back"),
            parse_mode="HTML"
        )


@router.callback_query(F.data.startswith("period:debts:"))
async def period_debts(callback: CallbackQuery, state: FSMContext):
    """Handle debts period selection."""
    period = callback.data.split(":")[2]
    await callback.answer()

    if period == "custom":
        await state.update_data(filter_context="debts")
        await callback.message.edit_text(
            "📅 <b>Введите начальную дату</b>\n\n"
            "Формат: ДД.ММ.ГГГГ (например, 01.01.2024)",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML"
        )
        await state.set_state(DateFilterStates.waiting_for_start_date)
        return

    period_label = PERIOD_LABELS.get(period, period)

    try:
        sheets = get_sheets_client()
        await sheets.initialize()
        debtors = await sheets.get_debtors()
        whitelist = await sheets.get_whitelist_clients()
        blacklist = await sheets.get_blacklist_clients()

        lines = [f"⚠️ <b>ДОЛГИ И ЛИСТЫ</b>\n📅 Период: {period_label}\n"]

        lines.append("💸 <b>ДОЛЖНИКИ</b>")
        lines.append("─" * 25)

        if not debtors:
            lines.append("✅ Нет должников!")
        else:
            total_debt = sum(d["total_debt"] for d in debtors)
            lines.append(f"⚠️ Общий долг: <b>${total_debt:,.2f}</b>\n")

            for debtor in debtors[:7]:
                lines.append(
                    f"🔴 <b>{debtor['client']}</b>: ${debtor['total_debt']:,.2f}"
                )

            if len(debtors) > 7:
                lines.append(f"\n... и ещё {len(debtors) - 7} должников")

        lines.append("\n📋 <b>ЛИСТЫ</b>")
        lines.append(f"🟢 White: {len(whitelist)} | 🔴 Black: {len(blacklist)}")

        await callback.message.edit_text(
            "\n".join(lines),
            reply_markup=get_debts_keyboard(period_label),
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Error filtering debts: {e}")
        await callback.message.edit_text(
            f"❌ <b>Ошибка загрузки!</b>\n\n{str(e)}",
            reply_markup=get_back_keyboard("menu:back"),
            parse_mode="HTML"
        )


# =============================================================================
# CUSTOM DATE INPUT HANDLERS
# =============================================================================

@router.message(DateFilterStates.waiting_for_start_date)
async def enter_start_date(message: Message, state: FSMContext):
    """Handle start date input."""
    date_str = message.text.strip()

    # Validate date format
    parsed = SheetsClient.parse_date(date_str)
    if not parsed:
        await message.answer(
            "❌ <b>Неверный формат даты!</b>\n\n"
            "Пожалуйста, введите дату в формате ДД.ММ.ГГГГ\n"
            "Например: 01.01.2024",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML"
        )
        return

    await state.update_data(start_date=parsed, start_date_str=date_str)
    await message.answer(
        f"✅ Начальная дата: <b>{date_str}</b>\n\n"
        "📅 <b>Введите конечную дату</b>\n\n"
        "Формат: ДД.ММ.ГГГГ (например, 31.12.2024)",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(DateFilterStates.waiting_for_end_date)


@router.message(DateFilterStates.waiting_for_end_date)
async def enter_end_date(message: Message, state: FSMContext):
    """Handle end date input and show filtered results."""
    date_str = message.text.strip()

    # Validate date format
    parsed = SheetsClient.parse_date(date_str)
    if not parsed:
        await message.answer(
            "❌ <b>Неверный формат даты!</b>\n\n"
            "Пожалуйста, введите дату в формате ДД.ММ.ГГГГ\n"
            "Например: 31.12.2024",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML"
        )
        return

    data = await state.get_data()
    start_date = data.get("start_date")
    start_date_str = data.get("start_date_str")
    context = data.get("filter_context", "designers")

    # Set end date to end of day
    end_date = parsed.replace(hour=23, minute=59, second=59)
    period_label = f"{start_date_str} - {date_str}"

    await state.clear()

    try:
        sheets = get_sheets_client()
        await sheets.initialize()

        if context == "designers":
            designers = await sheets.get_designers_with_earnings(start_date, end_date)

            if not designers:
                await message.answer(
                    f"🎨 <b>ДИЗАЙНЕРЫ</b>\n"
                    f"📅 Период: {period_label}\n\n"
                    "Нет данных за выбранный период.",
                    reply_markup=get_main_menu(),
                    parse_mode="HTML"
                )
                return

            designer_names = [d["designer"] for d in designers]
            total_earnings = sum(d["total_earnings"] for d in designers)
            total_orders = sum(d["orders_count"] for d in designers)

            await message.answer(
                f"🎨 <b>ДИЗАЙНЕРЫ</b>\n"
                f"📅 Период: {period_label}\n\n"
                f"📊 Всего дизайнеров: <b>{len(designers)}</b>\n"
                f"📦 Всего заказов: <b>{total_orders}</b>\n"
                f"💵 Общий заработок: <b>${total_earnings:,.2f}</b>\n\n"
                "Выберите дизайнера для просмотра аналитики:",
                reply_markup=get_designer_info_keyboard(designer_names, period_label),
                parse_mode="HTML"
            )

        elif context == "clients":
            clients = await sheets.get_clients_with_debts(start_date, end_date)

            if not clients:
                await message.answer(
                    f"👤 <b>ЗАКАЗЧИКИ</b>\n"
                    f"📅 Период: {period_label}\n\n"
                    "Нет данных за выбранный период.",
                    reply_markup=get_main_menu(),
                    parse_mode="HTML"
                )
                return

            client_names = [c["client"] for c in clients]
            total_debt = sum(c["total_debt"] for c in clients)
            total_amount = sum(c["total_amount"] for c in clients)

            await message.answer(
                f"👤 <b>ЗАКАЗЧИКИ</b>\n"
                f"📅 Период: {period_label}\n\n"
                f"📊 Всего заказчиков: <b>{len(clients)}</b>\n"
                f"💰 Общая сумма заказов: <b>${total_amount:,.2f}</b>\n"
                f"⚠️ Общий долг: <b>${total_debt:,.2f}</b>\n\n"
                "Выберите заказчика для просмотра аналитики:",
                reply_markup=get_client_info_keyboard(client_names, period_label),
                parse_mode="HTML"
            )

        elif context == "dashboard":
            # Use filtered dashboard data with custom date range
            data = await sheets.get_dashboard_data_filtered("custom", start_date, end_date)

            if "error" in data:
                await message.answer(
                    f"❌ <b>Ошибка загрузки данных</b>\n\n{data['error']}",
                    reply_markup=get_back_keyboard("menu:back"),
                    parse_mode="HTML"
                )
                return

            margin_pct = data['margin'] * 100 if data['margin'] < 1 else data['margin']
            balance_1 = data.get('balance_1', 0)
            balance_2 = data.get('balance_2', 0)
            total_balance = balance_1 + balance_2

            await message.answer(
                f"📊 <b>ПАНЕЛЬ АГЕНТСТВА</b>\n"
                f"📅 Период: {period_label}\n\n"
                f"💰 Выручка: <b>${data['revenue']:,.2f}</b>\n"
                f"💸 Затраты: <b>${data['expenses']:,.2f}</b>\n"
                f"📈 Прибыль: <b>${data['profit']:,.2f}</b>\n"
                f"📊 Маржинальность: <b>{margin_pct:.1f}%</b>\n\n"
                f"💼 <b>Счета:</b>\n"
                f"   Операционный: <b>${balance_1:,.2f}</b>\n"
                f"   Резервный: <b>${balance_2:,.2f}</b>\n"
                f"   💰 Всего: <b>${total_balance:,.2f}</b>",
                reply_markup=get_dashboard_keyboard(period_label),
                parse_mode="HTML"
            )

        elif context == "expenses":
            # Expenses don't support date filtering currently
            total_amount = await sheets.get_total_expenses()
            expenses = await sheets.get_expenses_by_category()
            designer_payments = await sheets.get_designer_payments()

            lines = [f"💸 <b>РАСХОДЫ</b>\n📅 Период: {period_label}\n"]

            total_designer_payments = sum(p["amount"] for p in designer_payments)
            total_manual_expenses = sum(e["total_amount"] for e in expenses) if expenses else 0

            lines.append(f"💰 <b>Итого расходов: ${total_amount:,.2f}</b>\n")

            lines.append("🎨 <b>ОПЛАТЫ ДИЗАЙНЕРАМ</b>")
            lines.append("─" * 25)

            if designer_payments:
                lines.append(f"💵 Всего оплачено: <b>${total_designer_payments:,.2f}</b>\n")
                for payment in designer_payments[:5]:
                    lines.append(f"🎨 <b>{payment['designer']}</b>: ${payment['amount']:,.2f}")
            else:
                lines.append("Нет оплат дизайнерам")

            lines.append("\n" + "─" * 25)
            lines.append("\n📁 <b>ТЕКУЩИЕ РАСХОДЫ</b>")

            if expenses:
                lines.append(f"💵 Сумма: <b>${total_manual_expenses:,.2f}</b>\n")
                for expense in expenses[:5]:
                    lines.append(f"📁 <b>{expense['category']}</b>: ${expense['total_amount']:,.2f}")
            else:
                lines.append("Нет текущих расходов")

            await message.answer(
                "\n".join(lines),
                reply_markup=get_expenses_keyboard(period_label),
                parse_mode="HTML"
            )

        elif context == "debts":
            clients = await sheets.get_clients_with_debts(start_date, end_date)
            debtors = [c for c in clients if c.get("total_debt", 0) > 0]

            if not debtors:
                await message.answer(
                    f"⚠️ <b>ДОЛГИ/ЛИСТЫ</b>\n"
                    f"📅 Период: {period_label}\n\n"
                    "✅ Нет должников за выбранный период!",
                    reply_markup=get_debts_keyboard(period_label),
                    parse_mode="HTML"
                )
            else:
                total_debt = sum(c.get("total_debt", 0) for c in debtors)

                debtors_text = "\n".join(
                    f"  • {c['client']}: <b>${c['total_debt']:,.2f}</b>"
                    for c in sorted(debtors, key=lambda x: -x.get("total_debt", 0))[:10]
                )

                await message.answer(
                    f"⚠️ <b>ДОЛГИ/ЛИСТЫ</b>\n"
                    f"📅 Период: {period_label}\n\n"
                    f"💰 Общий долг: <b>${total_debt:,.2f}</b>\n"
                    f"👤 Должников: <b>{len(debtors)}</b>\n\n"
                    f"<b>Топ должников:</b>\n{debtors_text}",
                    reply_markup=get_debts_keyboard(period_label),
                    parse_mode="HTML"
                )

    except Exception as e:
        logger.error(f"Error with custom date filter: {e}")
        await message.answer(
            f"❌ <b>Ошибка загрузки!</b>\n\n{str(e)}",
            reply_markup=get_main_menu(),
            parse_mode="HTML"
        )
