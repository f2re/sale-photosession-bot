from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_admin_menu() -> InlineKeyboardMarkup:
    """Get admin menu keyboard"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👥 Статистика пользователей", callback_data="admin_stats")],
            [InlineKeyboardButton(text="📦 Заказы", callback_data="admin_orders")],
            [InlineKeyboardButton(text="💬 Обращения в поддержку", callback_data="admin_support")],
            [InlineKeyboardButton(text="📊 UTM Статистика", callback_data="admin_utm_menu")],
            [InlineKeyboardButton(text="➕ Добавить генерации", callback_data="admin_add_images")],
            [InlineKeyboardButton(text="💵 Оформить возврат", callback_data="admin_refund")],
            [InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_refresh")]
        ]
    )
    return keyboard


def get_order_actions(order_id: int) -> InlineKeyboardMarkup:
    """Get order actions keyboard"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить оплату", callback_data=f"admin_confirm_order:{order_id}")],
            [InlineKeyboardButton(text="❌ Отменить заказ", callback_data=f"admin_cancel_order:{order_id}")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_orders")]
        ]
    )
    return keyboard


def get_ticket_actions(ticket_id: int) -> InlineKeyboardMarkup:
    """Get support ticket actions keyboard"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✉️ Ответить", callback_data=f"admin_reply_ticket:{ticket_id}")],
            [InlineKeyboardButton(text="✅ Закрыть обращение", callback_data=f"admin_close_ticket:{ticket_id}")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_support")]
        ]
    )
    return keyboard


def get_admin_utm_menu() -> InlineKeyboardMarkup:
    """Get admin UTM menu keyboard"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Общая статистика", callback_data="admin_utm_stats")],
            [InlineKeyboardButton(text="🎢 Воронка конверсии", callback_data="admin_utm_funnel")],
            [InlineKeyboardButton(text="📈 События UTM", callback_data="admin_utm_events")],
            [InlineKeyboardButton(text="⚙️ Статус синхронизации", callback_data="admin_utm_sync_status")],
            [InlineKeyboardButton(text="◀️ Назад в админ-панель", callback_data="admin_menu")]
        ]
    )
    return keyboard


def get_admin_back() -> InlineKeyboardMarkup:
    """Get back to admin menu keyboard"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад в админ-панель", callback_data="admin_menu")]
        ]
    )
    return keyboard


def get_admin_cancel() -> InlineKeyboardMarkup:
    """Get cancel keyboard for admin actions"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel_action")]
        ]
    )
    return keyboard


def get_orders_filter_menu() -> InlineKeyboardMarkup:
    """Get orders filter menu keyboard"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📦 Все заказы", callback_data="admin_orders_filter:all")],
            [InlineKeyboardButton(text="✅ Оплаченные", callback_data="admin_orders_filter:paid")],
            [InlineKeyboardButton(text="⏳ Ожидают оплаты", callback_data="admin_orders_filter:pending")],
            [InlineKeyboardButton(text="❌ Отмененные", callback_data="admin_orders_filter:cancelled")],
            [InlineKeyboardButton(text="💸 Возвращенные", callback_data="admin_orders_filter:refunded")],
            [InlineKeyboardButton(text="◀️ Назад в админ-панель", callback_data="admin_menu")]
        ]
    )
    return keyboard


def get_orders_list_keyboard(orders: list, page: int = 0, status_filter: str = "all") -> InlineKeyboardMarkup:
    """Get orders list keyboard with pagination"""
    buttons = []

    # Show up to 5 orders per page
    start_idx = page * 5
    end_idx = min(start_idx + 5, len(orders))

    for order in orders[start_idx:end_idx]:
        status_emoji = {
            "pending": "⏳",
            "paid": "✅",
            "cancelled": "❌",
            "refunded": "💸"
        }.get(order.status, "❓")

        button_text = f"{status_emoji} #{order.id} | {order.user.telegram_id} | {order.amount}₽"
        buttons.append([InlineKeyboardButton(
            text=button_text,
            callback_data=f"admin_order_detail:{order.id}"
        )])

    # Pagination buttons
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"admin_orders_page:{status_filter}:{page-1}"))
    if end_idx < len(orders):
        nav_buttons.append(InlineKeyboardButton(text="Вперед ▶️", callback_data=f"admin_orders_page:{status_filter}:{page+1}"))

    if nav_buttons:
        buttons.append(nav_buttons)

    # Bottom navigation
    buttons.append([InlineKeyboardButton(text="🔄 Фильтры", callback_data="admin_orders")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад в админ-панель", callback_data="admin_menu")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_order_detail_keyboard(order_id: int, order_status: str) -> InlineKeyboardMarkup:
    """Get order detail keyboard with available actions"""
    buttons = []

    if order_status == "paid":
        buttons.append([InlineKeyboardButton(text="💸 Оформить возврат", callback_data=f"admin_refund_confirm:{order_id}")])
    elif order_status == "pending":
        buttons.append([InlineKeyboardButton(text="✅ Подтвердить оплату", callback_data=f"admin_confirm_order:{order_id}")])
        buttons.append([InlineKeyboardButton(text="❌ Отменить заказ", callback_data=f"admin_cancel_order:{order_id}")])

    buttons.append([InlineKeyboardButton(text="◀️ Назад к заказам", callback_data="admin_orders")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_refund_keyboard() -> InlineKeyboardMarkup:
    """Get refund keyboard"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💸 Выбрать заказ для возврата", callback_data="admin_refund_select")],
            [InlineKeyboardButton(text="◀️ Назад в админ-панель", callback_data="admin_menu")]
        ]
    )
    return keyboard


def get_refund_confirm_keyboard(order_id: int) -> InlineKeyboardMarkup:
    """Get refund confirmation keyboard"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да, оформить возврат", callback_data=f"admin_refund_process:{order_id}")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"admin_order_detail:{order_id}")]
        ]
    )
    return keyboard


def get_ticket_list_keyboard(tickets: list, page: int = 0) -> InlineKeyboardMarkup:
    """Get support tickets list keyboard with pagination and inline actions"""
    buttons = []

    # Show up to 5 tickets per page
    start_idx = page * 5
    end_idx = min(start_idx + 5, len(tickets))

    for ticket in tickets[start_idx:end_idx]:
        status_emoji = {
            "open": "🔴",
            "in_progress": "🟡",
            "resolved": "🟢"
        }.get(ticket.status, "⚪")

        button_text = f"{status_emoji} #{ticket.id} | @{ticket.user.username or 'Unknown'}"
        buttons.append([InlineKeyboardButton(
            text=button_text,
            callback_data=f"admin_ticket_detail:{ticket.id}"
        )])

    # Pagination buttons
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"admin_support_page:{page-1}"))
    if end_idx < len(tickets):
        nav_buttons.append(InlineKeyboardButton(text="Вперед ▶️", callback_data=f"admin_support_page:{page+1}"))

    if nav_buttons:
        buttons.append(nav_buttons)

    # Bottom navigation
    buttons.append([InlineKeyboardButton(text="◀️ Назад в админ-панель", callback_data="admin_menu")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)
