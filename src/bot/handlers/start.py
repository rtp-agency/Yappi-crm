"""
Start command and main menu handlers.
"""
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
    get_analytics_back_keyboard
)
from src.services.sheets.client import get_sheets_client

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

        await message.answer(
            "📊 <b>ПАНЕЛЬ АГЕНТСТВА</b>\n\n"
            f"💰 Выручка: <b>${data['revenue']:,.2f}</b>\n"
            f"💸 Затраты: <b>${data['expenses']:,.2f}</b>\n"
            f"📈 Прибыль: <b>${data['profit']:,.2f}</b>\n"
            f"📊 Маржинальность: <b>{margin_pct:.1f}%</b>\n\n"
            f"💼 На счету: <b>${data['account_balance']:,.2f}</b>",
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
    """Show clients list with debts."""
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

        # Build message
        lines = ["👤 <b>ЗАКАЗЧИКИ</b>\n"]

        total_debt = sum(c["total_debt"] for c in clients)
        total_amount = sum(c["total_amount"] for c in clients)

        lines.append(f"📊 Всего заказчиков: <b>{len(clients)}</b>")
        lines.append(f"💰 Общая сумма заказов: <b>${total_amount:,.2f}</b>")
        lines.append(f"⚠️ Общий долг: <b>${total_debt:,.2f}</b>\n")

        lines.append("─" * 25)

        for client in clients[:15]:  # Limit to 15 clients
            debt_icon = "🔴" if client["total_debt"] > 0 else "🟢"
            lines.append(
                f"{debt_icon} <b>{client['client']}</b>\n"
                f"   📦 Заказов: {client['orders_count']}\n"
                f"   💵 Сумма: ${client['total_amount']:,.2f}\n"
                f"   💳 Оплачено: ${client['total_paid']:,.2f}\n"
                f"   ⚠️ Долг: ${client['total_debt']:,.2f}"
            )

        if len(clients) > 15:
            lines.append(f"\n... и ещё {len(clients) - 15} заказчиков")

        await message.answer("\n".join(lines), parse_mode="HTML")

    except Exception as e:
        logger.error(f"Error loading clients: {e}")
        await message.answer(
            f"❌ <b>Ошибка загрузки!</b>\n\n{str(e)}",
            parse_mode="HTML"
        )


@router.message(F.text == "🎨 Дизайнеры")
async def show_designers(message: Message):
    """Show designers list with earnings."""
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

        # Build message
        lines = ["🎨 <b>ДИЗАЙНЕРЫ</b>\n"]

        total_earnings = sum(d["total_earnings"] for d in designers)
        total_amount = sum(d["total_amount"] for d in designers)
        total_orders = sum(d["orders_count"] for d in designers)

        lines.append(f"📊 Всего дизайнеров: <b>{len(designers)}</b>")
        lines.append(f"📦 Всего заказов: <b>{total_orders}</b>")
        lines.append(f"💰 Общая сумма заказов: <b>${total_amount:,.2f}</b>")
        lines.append(f"💵 Общий заработок дизайнеров: <b>${total_earnings:,.2f}</b>\n")

        lines.append("─" * 25)

        for designer in designers[:15]:  # Limit to 15 designers
            lines.append(
                f"🎨 <b>{designer['designer']}</b>\n"
                f"   📦 Заказов: {designer['orders_count']}\n"
                f"   💰 Сумма заказов: ${designer['total_amount']:,.2f}\n"
                f"   💵 Заработок: ${designer['total_earnings']:,.2f}"
            )

        if len(designers) > 15:
            lines.append(f"\n... и ещё {len(designers) - 15} дизайнеров")

        await message.answer("\n".join(lines), parse_mode="HTML")

    except Exception as e:
        logger.error(f"Error loading designers: {e}")
        await message.answer(
            f"❌ <b>Ошибка загрузки!</b>\n\n{str(e)}",
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

        await message.answer("\n".join(lines), parse_mode="HTML")

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
            reply_markup=get_lists_menu()
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
    """Handle back button - delete inline menu."""
    await callback.message.delete()
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
