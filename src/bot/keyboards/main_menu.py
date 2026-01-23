"""
Main menu keyboards.
"""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder


def get_main_menu() -> ReplyKeyboardMarkup:
    """
    Main menu keyboard (reply keyboard).

    Structure from TZ:
    - Панель агентства
    - Добавить данные
    - Заказчики / Дизайнеры
    - Расходы / Долги/Листы
    - Аналитика / Настройки
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="📊 Панель агентства")
    )
    builder.row(
        KeyboardButton(text="➕ Добавить данные")
    )
    builder.row(
        KeyboardButton(text="👤 Заказчики"),
        KeyboardButton(text="🎨 Дизайнеры")
    )
    builder.row(
        KeyboardButton(text="💸 Расходы"),
        KeyboardButton(text="⚠️ Долги/Листы")
    )

    return builder.as_markup(resize_keyboard=True)


def get_add_data_menu() -> InlineKeyboardMarkup:
    """
    'Add data' submenu (inline keyboard).

    Structure from TZ:
    - Новый заказ
    - Чистый доход
    - Оплата от заказчика
    - Добавить заказчика/дизайнера/расход
    - ЗП дизайнеру
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="🧾 Новый заказ", callback_data="add:order")
    )
    builder.row(
        InlineKeyboardButton(text="💎 Чистый доход", callback_data="add:pure_income")
    )
    builder.row(
        InlineKeyboardButton(text="💰 Оплата от заказчика", callback_data="add:payment")
    )
    builder.row(
        InlineKeyboardButton(text="💵 ЗП дизайнеру", callback_data="add:designer_salary")
    )
    builder.row(
        InlineKeyboardButton(text="👤 Добавить заказчика", callback_data="add:client"),
        InlineKeyboardButton(text="🎨 Добавить дизайнера", callback_data="add:designer")
    )
    builder.row(
        InlineKeyboardButton(text="💸 Добавить расход", callback_data="add:expense")
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:back")
    )

    return builder.as_markup()


def get_order_type_menu() -> InlineKeyboardMarkup:
    """Order type selection menu."""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="🎨 Дизайнерский заказ", callback_data="order:designer")
    )
    builder.row(
        InlineKeyboardButton(text="💎 Чистый заказ агентства", callback_data="order:pure")
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:add_data")
    )

    return builder.as_markup()


def get_model_menu() -> InlineKeyboardMarkup:
    """Designer order model selection (percent/salary)."""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="📊 Процентная модель (%)", callback_data="model:percent")
    )
    builder.row(
        InlineKeyboardButton(text="💼 Окладная модель", callback_data="model:salary")
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="order:back")
    )

    return builder.as_markup()


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Cancel button for FSM states."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
    )
    return builder.as_markup()


def get_confirm_keyboard() -> InlineKeyboardMarkup:
    """Confirm/Cancel keyboard."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
    )
    return builder.as_markup()


def get_test_confirm_keyboard() -> InlineKeyboardMarkup:
    """Test mode confirmation keyboard - keep or delete data."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Оставить данные", callback_data="test:keep"),
        InlineKeyboardButton(text="🗑 Удалить данные", callback_data="test:delete")
    )
    return builder.as_markup()


def get_wallet_keyboard() -> InlineKeyboardMarkup:
    """Wallet selection for income distribution."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💼 Операционный", callback_data="wallet:operational")
    )
    builder.row(
        InlineKeyboardButton(text="🏦 Резервный", callback_data="wallet:reserve")
    )
    builder.row(
        InlineKeyboardButton(text="⚖️ 50/50", callback_data="wallet:split")
    )
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
    )
    return builder.as_markup()


def get_clients_keyboard(clients: list[str]) -> InlineKeyboardMarkup:
    """
    Keyboard with list of clients to select from.

    Args:
        clients: List of unique client names
    """
    builder = InlineKeyboardBuilder()

    for client in clients[:20]:  # Limit to 20 clients
        builder.row(
            InlineKeyboardButton(
                text=f"👤 {client}",
                callback_data=f"select_client:{client[:50]}"  # Limit callback data length
            )
        )

    builder.row(
        InlineKeyboardButton(text="✏️ Ввести вручную", callback_data="client:manual")
    )
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
    )

    return builder.as_markup()


def get_designers_keyboard(designers: list[str]) -> InlineKeyboardMarkup:
    """
    Keyboard with list of designers to select from.

    Args:
        designers: List of unique designer names
    """
    builder = InlineKeyboardBuilder()

    for designer in designers[:20]:  # Limit to 20
        builder.row(
            InlineKeyboardButton(
                text=f"🎨 {designer}",
                callback_data=f"select_designer:{designer[:50]}"
            )
        )

    builder.row(
        InlineKeyboardButton(text="✏️ Ввести вручную", callback_data="designer:manual")
    )
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
    )

    return builder.as_markup()


def get_designer_info_keyboard(designers: list[str], period_label: str = None) -> InlineKeyboardMarkup:
    """
    Keyboard with list of designers for viewing analytics.

    Args:
        designers: List of designer names
        period_label: Optional label for current filter period
    """
    builder = InlineKeyboardBuilder()

    for designer in designers[:20]:  # Limit to 20
        builder.row(
            InlineKeyboardButton(
                text=f"🎨 {designer}",
                callback_data=f"designer_info:{designer[:40]}"
            )
        )

    # Filter button
    filter_text = f"📅 Фильтр: {period_label}" if period_label else "📅 Фильтр по датам"
    builder.row(
        InlineKeyboardButton(text=filter_text, callback_data="filter:designers")
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Главное меню", callback_data="menu:back")
    )

    return builder.as_markup()


def get_client_info_keyboard(clients: list[str], period_label: str = None) -> InlineKeyboardMarkup:
    """
    Keyboard with list of clients for viewing analytics.

    Args:
        clients: List of client names
        period_label: Optional label for current filter period
    """
    builder = InlineKeyboardBuilder()

    for client in clients[:20]:  # Limit to 20
        builder.row(
            InlineKeyboardButton(
                text=f"👤 {client}",
                callback_data=f"client_info:{client[:40]}"
            )
        )

    # Filter button
    filter_text = f"📅 Фильтр: {period_label}" if period_label else "📅 Фильтр по датам"
    builder.row(
        InlineKeyboardButton(text=filter_text, callback_data="filter:clients")
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Главное меню", callback_data="menu:back")
    )

    return builder.as_markup()


def get_back_keyboard(callback_data: str = "menu:back") -> InlineKeyboardMarkup:
    """Simple back button keyboard."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data=callback_data)
    )
    return builder.as_markup()


def get_lists_menu() -> InlineKeyboardMarkup:
    """
    Lists management menu (White/Black list).
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="🟢 White list", callback_data="lists:whitelist"),
        InlineKeyboardButton(text="🔴 Black list", callback_data="lists:blacklist")
    )
    builder.row(
        InlineKeyboardButton(text="➕ Добавить в White list", callback_data="lists:add_white")
    )
    builder.row(
        InlineKeyboardButton(text="➕ Добавить в Black list", callback_data="lists:add_black")
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:back")
    )

    return builder.as_markup()


def get_list_clients_keyboard(
    clients: list[str],
    action: str  # "to_white", "to_black", "remove"
) -> InlineKeyboardMarkup:
    """
    Keyboard with list of clients for list management.

    Args:
        clients: List of client names
        action: Action to perform (to_white, to_black, remove)
    """
    builder = InlineKeyboardBuilder()

    for client in clients[:15]:  # Limit to 15
        # Truncate client name for callback_data (max ~64 bytes)
        callback = f"list_action:{action}:{client[:40]}"
        builder.row(
            InlineKeyboardButton(text=f"👤 {client}", callback_data=callback)
        )

    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="lists:back")
    )

    return builder.as_markup()


def get_analytics_menu() -> InlineKeyboardMarkup:
    """
    Analytics submenu with drill-down options.
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="🎨 Прибыль по дизайнерам", callback_data="analytics:designers")
    )
    builder.row(
        InlineKeyboardButton(text="👤 Прибыль по заказчикам", callback_data="analytics:clients")
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:back")
    )

    return builder.as_markup()


def get_analytics_back_keyboard() -> InlineKeyboardMarkup:
    """Back button for analytics drill-down views."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⬅️ К аналитике", callback_data="analytics:back")
    )
    return builder.as_markup()


def get_client_in_list_keyboard(client_name: str, current_list: str) -> InlineKeyboardMarkup:
    """
    Keyboard for managing a client in a list.

    Args:
        client_name: Client name
        current_list: Current list (whitelist/blacklist)
    """
    builder = InlineKeyboardBuilder()

    # Truncate for callback
    client_short = client_name[:40]

    if current_list == "whitelist":
        builder.row(
            InlineKeyboardButton(
                text="🔴 Перенести в Black list",
                callback_data=f"list_action:to_black:{client_short}"
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="❌ Убрать из листа",
                callback_data=f"list_action:remove:{client_short}"
            )
        )
    elif current_list == "blacklist":
        builder.row(
            InlineKeyboardButton(
                text="🟢 Перенести в White list",
                callback_data=f"list_action:to_white:{client_short}"
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="❌ Убрать из листа",
                callback_data=f"list_action:remove:{client_short}"
            )
        )

    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="lists:back")
    )

    return builder.as_markup()


def get_period_keyboard(context: str = "dashboard") -> InlineKeyboardMarkup:
    """
    Period selection keyboard for date filtering.

    Args:
        context: The context where filter is used (dashboard, designers, clients, expenses)
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="📅 Сегодня", callback_data=f"period:{context}:today"),
        InlineKeyboardButton(text="📅 Эта неделя", callback_data=f"period:{context}:week")
    )
    builder.row(
        InlineKeyboardButton(text="📅 Этот месяц", callback_data=f"period:{context}:month"),
        InlineKeyboardButton(text="📅 Весь период", callback_data=f"period:{context}:all")
    )
    builder.row(
        InlineKeyboardButton(text="✏️ Выбрать даты", callback_data=f"period:{context}:custom")
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:back")
    )

    return builder.as_markup()


def get_period_back_keyboard(context: str = "dashboard") -> InlineKeyboardMarkup:
    """Back button to return to period selection."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📅 Изменить период", callback_data=f"filter:{context}"),
        InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:back")
    )
    return builder.as_markup()


def get_dashboard_keyboard(period_label: str = None) -> InlineKeyboardMarkup:
    """Dashboard keyboard with filter button."""
    builder = InlineKeyboardBuilder()

    filter_text = f"📅 Фильтр: {period_label}" if period_label else "📅 Фильтр по датам"
    builder.row(
        InlineKeyboardButton(text=filter_text, callback_data="filter:dashboard")
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Главное меню", callback_data="menu:back")
    )

    return builder.as_markup()


def get_expenses_keyboard(period_label: str = None) -> InlineKeyboardMarkup:
    """Expenses keyboard with filter button."""
    builder = InlineKeyboardBuilder()

    filter_text = f"📅 Фильтр: {period_label}" if period_label else "📅 Фильтр по датам"
    builder.row(
        InlineKeyboardButton(text=filter_text, callback_data="filter:expenses")
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Главное меню", callback_data="menu:back")
    )

    return builder.as_markup()


def get_debts_keyboard(period_label: str = None) -> InlineKeyboardMarkup:
    """Debts/Lists keyboard with filter button."""
    builder = InlineKeyboardBuilder()

    filter_text = f"📅 Фильтр: {period_label}" if period_label else "📅 Фильтр по датам"
    builder.row(
        InlineKeyboardButton(text=filter_text, callback_data="filter:debts")
    )
    builder.row(
        InlineKeyboardButton(text="⚠️ White/Black списки", callback_data="lists:menu")
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Главное меню", callback_data="menu:back")
    )

    return builder.as_markup()
