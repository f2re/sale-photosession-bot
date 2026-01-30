from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest

from app.database import get_db
from app.database.crud import (
    get_statistics, get_open_tickets, resolve_ticket,
    get_or_create_user, get_user_balance, get_ticket_by_id,
    add_support_message, get_utm_statistics, get_conversion_funnel,
    get_utm_events_summary, get_utm_sync_status,
    get_all_orders, get_order_by_id, cancel_order, refund_order,
    get_orders_count, mark_order_paid, get_full_user_statistics
)
from app.services.notification_service import NotificationService
from app.services.yandex_metrika import metrika_service
from app.keyboards.admin_kb import (
    get_admin_menu, get_ticket_actions, get_admin_back, get_admin_cancel, get_admin_utm_menu,
    get_orders_filter_menu, get_orders_list_keyboard, get_order_detail_keyboard,
    get_refund_keyboard, get_refund_confirm_keyboard, get_ticket_list_keyboard
)
from app.utils.decorators import admin_only
from app.utils.message_helpers import safe_edit_text

router = Router()


class AdminStates(StatesGroup):
    waiting_for_ticket_reply = State()
    waiting_for_user_id = State()
    waiting_for_images_count = State()
    waiting_for_refund_order_id = State()
    waiting_for_message_user_id = State()
    waiting_for_message_text = State()
    waiting_for_stats_user_id = State()


@router.message(Command("admin"))
@admin_only
async def admin_panel(message: Message):
    """Show admin panel"""
    db = get_db()
    async with db.get_session() as session:
        stats = await get_statistics(session)

    text = (
        "🔐 <b>Админ-панель</b>\n\n"
        "📊 <b>Статистика бота:</b>\n\n"
        f"👥 Всего пользователей: {stats['total_users']}\n"
        f"📸 Обработано изображений: {stats['total_processed']}\n"
        f"   🎁 Бесплатных: {stats['free_images_processed']}\n"
        f"   💎 Платных: {stats['paid_images_processed']}\n"
        f"💰 Выручка: {stats['revenue']:.2f}₽ ({stats['paid_orders']} заказов)\n"
        f"📦 Активных заказов: {stats['active_orders']}\n"
        f"💬 Открытых обращений: {stats['open_tickets']}"
    )

    await message.answer(text, parse_mode="HTML", reply_markup=get_admin_menu())


@router.callback_query(F.data == "admin_refresh")
@admin_only
async def admin_refresh(callback: CallbackQuery):
    """Refresh admin panel"""
    db = get_db()
    async with db.get_session() as session:
        stats = await get_statistics(session)

    text = (
        "🔐 <b>Админ-панель</b>\n\n"
        "📊 <b>Статистика бота:</b>\n\n"
        f"👥 Всего пользователей: {stats['total_users']}\n"
        f"📸 Обработано изображений: {stats['total_processed']}\n"
        f"   🎁 Бесплатных: {stats['free_images_processed']}\n"
        f"   💎 Платных: {stats['paid_images_processed']}\n"
        f"💰 Выручка: {stats['revenue']:.2f}₽ ({stats['paid_orders']} заказов)\n"
        f"📦 Активных заказов: {stats['active_orders']}\n"
        f"💬 Открытых обращений: {stats['open_tickets']}"
    )

    was_modified = await safe_edit_text(callback.message, text, parse_mode="HTML", reply_markup=get_admin_menu())
    if was_modified:
        await callback.answer("✅ Обновлено")
    else:
        await callback.answer("✅ Данные актуальны")


@router.callback_query(F.data == "admin_stats")
@admin_only
async def admin_stats(callback: CallbackQuery):
    """Show detailed statistics"""
    db = get_db()
    async with db.get_session() as session:
        stats = await get_statistics(session)

    text = (
        "📊 <b>Детальная статистика</b>\n\n"
        f"👥 Всего пользователей: {stats['total_users']}\n\n"
        f"📸 Обработано изображений: {stats['total_processed']}\n"
        f"   🎁 Бесплатных: {stats['free_images_processed']}\n"
        f"   💎 Платных: {stats['paid_images_processed']}\n\n"
        f"💰 Выручка: {stats['revenue']:.2f}₽\n"
        f"   📦 Оплаченных заказов: {stats['paid_orders']}\n"
        f"   ⏳ Активных заказов: {stats['active_orders']}\n\n"
        f"💬 Открытых обращений: {stats['open_tickets']}\n\n"
        "Используйте другие команды для более детального просмотра."
    )

    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_admin_back())
    await callback.answer()


@router.callback_query(F.data == "admin_user_stats_search")
@admin_only
async def admin_user_stats_search(callback: CallbackQuery, state: FSMContext):
    """Start user stats search"""
    await state.set_state(AdminStates.waiting_for_stats_user_id)
    await callback.message.edit_text(
        "👤 <b>Статистика пользователя</b>\n\n"
        "Введите Telegram ID пользователя для просмотра статистики:",
        parse_mode="HTML",
        reply_markup=get_admin_cancel()
    )
    await callback.answer()


@router.message(AdminStates.waiting_for_stats_user_id, F.text)
@admin_only
async def admin_user_stats_view(message: Message, state: FSMContext):
    """Show user statistics by ID"""
    try:
        user_id = int(message.text)
    except ValueError:
        await message.answer("❌ Неверный формат ID. Введите число.")
        return

    db = get_db()
    async with db.get_session() as session:
        stats = await get_full_user_statistics(session, user_id)

    if not stats:
        await message.answer(
            f"❌ Пользователь с ID {user_id} не найден",
            reply_markup=get_admin_cancel()
        )
        return

    user = stats['user']
    
    # Format text
    text = (
        f"👤 <b>Статистика пользователя</b>\n"
        f"ID: <code>{user.telegram_id}</code>\n"
        f"Username: @{user.username or 'N/A'}\n"
        f"Имя: {user.first_name or ''} {user.last_name or ''}\n\n"
        
        f"📅 <b>Дата регистрации:</b> {user.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
        
        f"📸 <b>Генерации:</b>\n"
        f"• Всего: {stats['total_used']}\n"
        f"• Бесплатных: {stats['free_used']}\n"
        f"• Платных: {stats['paid_used']}\n\n"
        
        f"💰 <b>Баланс:</b> {user.images_remaining} фотосессий\n\n"
    )

    # Purchases
    if stats['orders']:
        text += "🛒 <b>История покупок:</b>\n"
        for order in stats['orders'][:5]: # Show last 5
            date = order.paid_at.strftime('%d.%m.%Y')
            text += f"• {date}: {order.package.name} ({order.amount}₽)\n"
        if len(stats['orders']) > 5:
            text += f"...и еще {len(stats['orders']) - 5}\n"
        text += "\n"
    else:
        text += "🛒 <b>Покупок не было</b>\n\n"

    # Manual Accruals
    if stats['manual_accruals']:
        text += "🎁 <b>Ручные начисления:</b>\n"
        for order in stats['manual_accruals'][:5]:
            date = order.paid_at.strftime('%d.%m.%Y')
            count = order.package.photoshoots_count
            text += f"• {date}: +{count} фотосессий\n"
        if len(stats['manual_accruals']) > 5:
            text += f"...и еще {len(stats['manual_accruals']) - 5}\n"
        text += "\n"

    # Add UTM info if available
    if user.utm_source:
        text += (
            f"🏷 <b>UTM Метки:</b>\n"
            f"Source: {user.utm_source}\n"
            f"Medium: {user.utm_medium or '-'}\n"
            f"Campaign: {user.utm_campaign or '-'}\n"
        )

    await state.clear()
    await message.answer(text, parse_mode="HTML", reply_markup=get_admin_back())


@router.callback_query(F.data == "admin_support")
@admin_only
async def admin_support_tickets(callback: CallbackQuery):
    """Show support tickets with inline actions"""
    db = get_db()
    async with db.get_session() as session:
        tickets = await get_open_tickets(session)

    if not tickets:
        text = "💬 <b>Обращения в поддержку</b>\n\n❌ Нет открытых обращений"
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_admin_back())
        await callback.answer()
        return

    text = (
        "💬 <b>Обращения в поддержку</b>\n\n"
        f"Всего открытых: {len(tickets)}\n\n"
        "Выберите обращение для просмотра:"
    )

    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_ticket_list_keyboard(tickets, page=0))
    await callback.answer()


@router.callback_query(F.data.startswith("admin_support_page:"))
@admin_only
async def admin_support_page(callback: CallbackQuery):
    """Navigate support tickets pages"""
    page = int(callback.data.split(":")[1])

    db = get_db()
    async with db.get_session() as session:
        tickets = await get_open_tickets(session)

    text = (
        "💬 <b>Обращения в поддержку</b>\n\n"
        f"Всего открытых: {len(tickets)}\n\n"
        "Выберите обращение для просмотра:"
    )

    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_ticket_list_keyboard(tickets, page=page))
    await callback.answer()


@router.callback_query(F.data.startswith("admin_ticket_detail:"))
@admin_only
async def admin_ticket_detail(callback: CallbackQuery):
    """View ticket detail"""
    ticket_id = int(callback.data.split(":")[1])

    db = get_db()
    async with db.get_session() as session:
        ticket = await get_ticket_by_id(session, ticket_id)

        if not ticket:
            await callback.answer("❌ Обращение не найдено", show_alert=True)
            return

        text = (
            f"📝 <b>Обращение #{ticket.id}</b>\n\n"
            f"👤 От: @{ticket.user.username or 'Unknown'} ({ticket.user.telegram_id})\n"
            f"📅 Создано: {ticket.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            f"📊 Статус: {ticket.status}\n\n"
            f"💬 <b>Сообщение:</b>\n{ticket.message}"
        )

        if ticket.admin_response:
            text += f"\n\n✅ <b>Ваш ответ:</b>\n{ticket.admin_response}"

        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_ticket_actions(ticket.id))
        await callback.answer()


@router.message(Command("ticket"))
@admin_only
async def view_ticket(message: Message):
    """View specific ticket"""
    try:
        ticket_id = int(message.text.split()[1])
    except (IndexError, ValueError):
        await message.answer("❌ Использование: /ticket <ID>")
        return

    db = get_db()
    async with db.get_session() as session:
        from app.database.models import SupportTicket
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        result = await session.execute(
            select(SupportTicket)
            .where(SupportTicket.id == ticket_id)
            .options(selectinload(SupportTicket.user))
        )
        ticket = result.scalar_one_or_none()

        if not ticket:
            await message.answer("❌ Обращение не найдено")
            return

        text = (
            f"📝 <b>Обращение #{ticket.id}</b>\n\n"
            f"👤 От: @{ticket.user.username or 'Unknown'} ({ticket.user.telegram_id})\n"
            f"📅 Создано: {ticket.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            f"📊 Статус: {ticket.status}\n\n"
            f"💬 <b>Сообщение:</b>\n{ticket.message}"
        )

        if ticket.admin_response:
            text += f"\n\n✅ <b>Ваш ответ:</b>\n{ticket.admin_response}"

        await message.answer(text, parse_mode="HTML", reply_markup=get_ticket_actions(ticket.id))


@router.callback_query(F.data.startswith("admin_reply_ticket:"))
@admin_only
async def admin_reply_ticket(callback: CallbackQuery, state: FSMContext):
    """Start replying to ticket"""
    ticket_id = int(callback.data.split(":")[1])

    await state.update_data(ticket_id=ticket_id)
    await state.set_state(AdminStates.waiting_for_ticket_reply)

    await callback.message.edit_text(
        f"✉️ Ответ на обращение #{ticket_id}\n\n"
        "Напишите ваш ответ пользователю:",
        reply_markup=get_admin_cancel()
    )
    await callback.answer()


@router.message(AdminStates.waiting_for_ticket_reply, F.text)
@admin_only
async def process_ticket_reply(message: Message, state: FSMContext):
    """Process ticket reply"""
    data = await state.get_data()
    ticket_id = data.get('ticket_id')

    if not ticket_id:
        await message.answer("❌ Ошибка: ID обращения не найден")
        return

    db = get_db()
    async with db.get_session() as session:
        ticket = await get_ticket_by_id(session, ticket_id)

        if not ticket:
            await message.answer("❌ Обращение не найдено")
            return

        # Add message to conversation
        await add_support_message(
            session,
            ticket_id=ticket_id,
            sender_telegram_id=message.from_user.id,
            message=message.text,
            is_admin=True
        )

        # Also update the admin_response field and resolve
        await resolve_ticket(session, ticket_id, message.from_user.id, message.text)

        # Send notification to user using NotificationService
        await NotificationService.notify_user_support_reply(
            bot=message.bot,
            telegram_id=ticket.user.telegram_id,
            ticket_id=ticket_id,
            admin_username=message.from_user.username,
            message=message.text
        )

        await message.answer(f"✅ Ответ отправлен пользователю (ID: {ticket.user.telegram_id})")

    await state.clear()


@router.message(Command("support_reply"))
@admin_only
async def support_reply_command(message: Message):
    """Reply to support ticket using command: /support_reply <ticket_id> <message>"""
    try:
        parts = message.text.split(maxsplit=2)
        if len(parts) < 3:
            await message.answer(
                "❌ <b>Использование:</b>\n"
                "/support_reply &lt;ticket_id&gt; &lt;message&gt;\n\n"
                "<b>Пример:</b>\n"
                "/support_reply 123 Ваш вопрос принят, мы работаем над решением",
                parse_mode="HTML"
            )
            return

        ticket_id = int(parts[1])
        reply_message = parts[2]

    except (IndexError, ValueError):
        await message.answer(
            "❌ <b>Ошибка формата</b>\n\n"
            "Используйте: /support_reply &lt;ticket_id&gt; &lt;message&gt;",
            parse_mode="HTML"
        )
        return

    db = get_db()
    async with db.get_session() as session:
        ticket = await get_ticket_by_id(session, ticket_id)

        if not ticket:
            await message.answer(f"❌ Обращение #{ticket_id} не найдено")
            return

        # Add message to conversation
        await add_support_message(
            session,
            ticket_id=ticket_id,
            sender_telegram_id=message.from_user.id,
            message=reply_message,
            is_admin=True
        )

        # Also update the admin_response field
        await resolve_ticket(session, ticket_id, message.from_user.id, reply_message)

        # Send notification to user
        await NotificationService.notify_user_support_reply(
            bot=message.bot,
            telegram_id=ticket.user.telegram_id,
            ticket_id=ticket_id,
            admin_username=message.from_user.username,
            message=reply_message
        )

        await message.answer(
            f"✅ Ответ отправлен!\n\n"
            f"📝 Тикет: #{ticket_id}\n"
            f"👤 Пользователь: {ticket.user.telegram_id}\n"
            f"💬 Ваш ответ: {reply_message[:100]}{'...' if len(reply_message) > 100 else ''}",
            parse_mode="HTML"
        )


@router.callback_query(F.data.startswith("admin_close_ticket:"))
@admin_only
async def admin_close_ticket(callback: CallbackQuery):
    """Close ticket without reply"""
    ticket_id = int(callback.data.split(":")[1])

    db = get_db()
    async with db.get_session() as session:
        await resolve_ticket(session, ticket_id, callback.from_user.id, "Закрыто администратором")

    await callback.message.edit_text(
        f"✅ Обращение #{ticket_id} закрыто",
        reply_markup=get_admin_back()
    )
    await callback.answer()


# ==================== ORDERS MANAGEMENT ====================

@router.callback_query(F.data == "admin_orders")
@admin_only
async def admin_orders_menu(callback: CallbackQuery):
    """Show orders filter menu"""
    text = (
        "📦 <b>Управление заказами</b>\n\n"
        "Выберите фильтр для просмотра заказов:"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_orders_filter_menu())
    await callback.answer()


@router.callback_query(F.data.startswith("admin_orders_filter:"))
@admin_only
async def admin_orders_filter(callback: CallbackQuery):
    """Show filtered orders list"""
    status_filter = callback.data.split(":")[1]

    db = get_db()
    async with db.get_session() as session:
        if status_filter == "all":
            orders = await get_all_orders(session, status=None, limit=100)
            filter_name = "Все заказы"
        else:
            orders = await get_all_orders(session, status=status_filter, limit=100)
            filter_name = {
                "paid": "Оплаченные",
                "pending": "Ожидают оплаты",
                "cancelled": "Отмененные",
                "refunded": "Возвращенные"
            }.get(status_filter, "Заказы")

    if not orders:
        text = f"📦 <b>{filter_name}</b>\n\n❌ Заказов не найдено"
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_admin_back())
        await callback.answer()
        return

    text = (
        f"📦 <b>{filter_name}</b>\n\n"
        f"Всего: {len(orders)}\n\n"
        "Выберите заказ для просмотра:"
    )

    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_orders_list_keyboard(orders, page=0, status_filter=status_filter)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_orders_page:"))
@admin_only
async def admin_orders_page(callback: CallbackQuery):
    """Navigate orders pages"""
    parts = callback.data.split(":")
    status_filter = parts[1]
    page = int(parts[2])

    db = get_db()
    async with db.get_session() as session:
        if status_filter == "all":
            orders = await get_all_orders(session, status=None, limit=100)
            filter_name = "Все заказы"
        else:
            orders = await get_all_orders(session, status=status_filter, limit=100)
            filter_name = {
                "paid": "Оплаченные",
                "pending": "Ожидают оплаты",
                "cancelled": "Отмененные",
                "refunded": "Возвращенные"
            }.get(status_filter, "Заказы")

    text = (
        f"📦 <b>{filter_name}</b>\n\n"
        f"Всего: {len(orders)}\n\n"
        "Выберите заказ для просмотра:"
    )

    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_orders_list_keyboard(orders, page=page, status_filter=status_filter)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_order_detail:"))
@admin_only
async def admin_order_detail(callback: CallbackQuery):
    """Show order details"""
    order_id = int(callback.data.split(":")[1])

    db = get_db()
    async with db.get_session() as session:
        order = await get_order_by_id(session, order_id)

        if not order:
            await callback.answer("❌ Заказ не найден", show_alert=True)
            return

        status_emoji = {
            "pending": "⏳",
            "paid": "✅",
            "cancelled": "❌",
            "refunded": "💸"
        }.get(order.status, "❓")

        text = (
            f"📦 <b>Заказ #{order.id}</b>\n\n"
            f"📊 Статус: {status_emoji} {order.status}\n"
            f"👤 Пользователь: {order.user.telegram_id}\n"
            f"   @{order.user.username or 'Unknown'}\n\n"
            f"📦 Пакет: {order.package.name}\n"
            f"   Фотосессий: {order.package.photoshoots_count}\n"
            f"💰 Сумма: {order.amount}₽\n\n"
            f"📅 Создан: {order.created_at.strftime('%d.%m.%Y %H:%M')}\n"
        )

        if order.paid_at:
            text += f"✅ Оплачен: {order.paid_at.strftime('%d.%m.%Y %H:%M')}\n"

        if order.invoice_id:
            text += f"\n🔑 Invoice ID: <code>{order.invoice_id}</code>"

        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=get_order_detail_keyboard(order.id, order.status)
        )
        await callback.answer()


@router.callback_query(F.data.startswith("admin_confirm_order:"))
@admin_only
async def admin_confirm_order(callback: CallbackQuery):
    """Manually confirm order payment"""
    order_id = int(callback.data.split(":")[1])

    db = get_db()
    async with db.get_session() as session:
        order = await get_order_by_id(session, order_id)

        if not order:
            await callback.answer("❌ Заказ не найден", show_alert=True)
            return

        if order.status == "paid":
            await callback.answer("✅ Заказ уже оплачен", show_alert=True)
            return

        # Mark as paid using invoice_id
        await mark_order_paid(session, order.invoice_id)

    await callback.answer("✅ Заказ помечен как оплаченный")
    # Refresh order view
    await admin_order_detail(callback)


@router.callback_query(F.data.startswith("admin_cancel_order:"))
@admin_only
async def admin_cancel_order_handler(callback: CallbackQuery):
    """Cancel an order"""
    order_id = int(callback.data.split(":")[1])

    db = get_db()
    async with db.get_session() as session:
        order = await cancel_order(session, order_id, callback.from_user.id)

        if not order:
            await callback.answer("❌ Не удалось отменить заказ. Возможно, он уже оплачен.", show_alert=True)
            return

    await callback.answer("✅ Заказ отменен")
    # Refresh order view
    await admin_order_detail(callback)


# ==================== REFUND MANAGEMENT ====================

@router.callback_query(F.data == "admin_refund")
@admin_only
async def admin_refund_menu(callback: CallbackQuery):
    """Show refund menu"""
    text = (
        "💸 <b>Оформление возврата</b>\n\n"
        "Выберите оплаченный заказ для возврата средств.\n\n"
        "⚠️ При возврате:\n"
        "• Статус заказа изменится на 'refunded'\n"
        "• Фотосессии будут вычтены из баланса пользователя\n"
        "• Необходимо вернуть деньги пользователю вручную через платежную систему"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_refund_keyboard())
    await callback.answer()


@router.callback_query(F.data == "admin_refund_select")
@admin_only
async def admin_refund_select(callback: CallbackQuery):
    """Show paid orders for refund selection"""
    db = get_db()
    async with db.get_session() as session:
        paid_orders = await get_all_orders(session, status="paid", limit=100)

    if not paid_orders:
        text = "💸 <b>Оформление возврата</b>\n\n❌ Нет оплаченных заказов для возврата"
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_admin_back())
        await callback.answer()
        return

    text = (
        "💸 <b>Выберите заказ для возврата</b>\n\n"
        f"Всего оплаченных заказов: {len(paid_orders)}\n\n"
        "Выберите заказ:"
    )

    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_orders_list_keyboard(paid_orders, page=0, status_filter="paid")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_refund_confirm:"))
@admin_only
async def admin_refund_confirm(callback: CallbackQuery):
    """Confirm refund action"""
    order_id = int(callback.data.split(":")[1])

    db = get_db()
    async with db.get_session() as session:
        order = await get_order_by_id(session, order_id)

        if not order:
            await callback.answer("❌ Заказ не найден", show_alert=True)
            return

        if order.status != "paid":
            await callback.answer("❌ Можно вернуть только оплаченные заказы", show_alert=True)
            return

        text = (
            f"💸 <b>Подтверждение возврата</b>\n\n"
            f"📦 Заказ: #{order.id}\n"
            f"👤 Пользователь: {order.user.telegram_id} (@{order.user.username or 'Unknown'})\n"
            f"💰 Сумма: {order.amount}₽\n"
            f"📦 Фотосессий: {order.package.photoshoots_count}\n\n"
            f"⚠️ <b>ВНИМАНИЕ:</b>\n"
            f"• Будет вычтано {order.package.photoshoots_count} фотосессий из баланса пользователя\n"
            f"• Текущий баланс: {order.user.images_remaining} фотосессий\n"
            f"• После возврата: {max(0, order.user.images_remaining - order.package.photoshoots_count)} фотосессий\n\n"
            f"❗️ Не забудьте вернуть {order.amount}₽ через платежную систему!"
        )

        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=get_refund_confirm_keyboard(order.id)
        )
        await callback.answer()


@router.callback_query(F.data.startswith("admin_refund_process:"))
@admin_only
async def admin_refund_process(callback: CallbackQuery):
    """Process refund"""
    order_id = int(callback.data.split(":")[1])

    db = get_db()
    async with db.get_session() as session:
        order = await refund_order(session, order_id, callback.from_user.id)

        if not order:
            await callback.answer("❌ Не удалось оформить возврат. Проверьте статус заказа.", show_alert=True)
            return

        # Refresh order data
        await session.refresh(order, ['user', 'package'])

        text = (
            f"✅ <b>Возврат оформлен!</b>\n\n"
            f"📦 Заказ #{order.id} помечен как возвращенный\n"
            f"👤 Пользователь: {order.user.telegram_id}\n"
            f"💰 Сумма: {order.amount}₽\n"
            f"📦 Вычтено фотосессий: {order.package.photoshoots_count}\n"
            f"💳 Текущий баланс пользователя: {order.user.images_remaining}\n\n"
            f"❗️ <b>Важно:</b> Верните {order.amount}₽ пользователю через платежную систему!"
        )

        # Notify user
        try:
            await NotificationService.notify_user_refund(
                bot=callback.bot,
                telegram_id=order.user.telegram_id,
                order_id=order.id,
                amount=float(order.amount)
            )
        except Exception as e:
            text += f"\n\n⚠️ Не удалось отправить уведомление пользователю"

        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_admin_back())
        await callback.answer("✅ Возврат оформлен")


@router.callback_query(F.data == "admin_add_images")
@admin_only
async def admin_add_images_start(callback: CallbackQuery, state: FSMContext):
    """Start adding images to user"""
    await state.set_state(AdminStates.waiting_for_user_id)

    await callback.message.edit_text(
        "➕ <b>Добавить изображения пользователю</b>\n\n"
        "Введите Telegram ID пользователя:",
        parse_mode="HTML",
        reply_markup=get_admin_cancel()
    )
    await callback.answer()


@router.message(AdminStates.waiting_for_user_id, F.text)
@admin_only
async def admin_add_images_user_id(message: Message, state: FSMContext):
    """Process user ID for adding images"""
    try:
        user_id = int(message.text)
    except ValueError:
        await message.answer("❌ Неверный формат ID. Введите числовое значение.")
        return

    # Check if user exists
    db = get_db()
    async with db.get_session() as session:
        user = await get_or_create_user(session, user_id)

    await state.update_data(target_user_id=user_id)
    await state.set_state(AdminStates.waiting_for_images_count)

    await message.answer(
        f"👤 Пользователь: {user.telegram_id}\n\n"
        "Введите количество изображений для добавления:"
    )


@router.message(AdminStates.waiting_for_images_count, F.text)
@admin_only
async def admin_add_images_count(message: Message, state: FSMContext):
    """Process images count for adding"""
    try:
        count = int(message.text)
        if count <= 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Неверное количество. Введите положительное число.")
        return

    data = await state.get_data()
    target_user_id = data.get('target_user_id')

    # Add images by creating a manual order
    db = get_db()
    async with db.get_session() as session:
        from app.database.models import Package, Order, User
        from sqlalchemy import select

        # Get user
        result = await session.execute(
            select(User).where(User.telegram_id == target_user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            await message.answer("❌ Пользователь не найден")
            return

        # Create manual package entry
        manual_package = Package(
            name=f"Manual {count} photoshoots",
            photoshoots_count=count,  # Fixed: photoshoots_count, not images_count
            price_rub=0,
            is_active=False
        )
        session.add(manual_package)
        await session.flush()

        # Create paid order
        order = Order(
            user_id=user.id,
            package_id=manual_package.id,
            amount=0,
            status="paid",
            invoice_id=f"manual_{user.id}_{int(__import__('time').time())}"
        )
        session.add(order)
        await session.flush()

        # Manually add photoshoots to user balance
        user.images_remaining += count
        await session.commit()

    await state.clear()
    await message.answer(
        f"✅ Добавлено {count} фотосессий пользователю {target_user_id}\n\n"
        f"Теперь у пользователя доступно фотосессий: {user.images_remaining}"
    )


@router.callback_query(F.data == "admin_cancel_action")
@admin_only
async def admin_cancel_action(callback: CallbackQuery, state: FSMContext):
    """Cancel admin action"""
    await state.clear()
    await callback.message.edit_text(
        "❌ Действие отменено",
        reply_markup=get_admin_back()
    )
    await callback.answer()


@router.callback_query(F.data == "admin_menu")
@admin_only
async def admin_menu_callback(callback: CallbackQuery):
    """Return to admin menu"""
    db = get_db()
    async with db.get_session() as session:
        stats = await get_statistics(session)

    text = (
        "🔐 <b>Админ-панель</b>\n\n"
        "📊 <b>Статистика бота:</b>\n\n"
        f"👥 Всего пользователей: {stats['total_users']}\n"
        f"📸 Обработано изображений: {stats['total_processed']}\n"
        f"   🎁 Бесплатных: {stats['free_images_processed']}\n"
        f"   💎 Платных: {stats['paid_images_processed']}\n"
        f"💰 Выручка: {stats['revenue']:.2f}₽ ({stats['paid_orders']} заказов)\n"
        f"📦 Активных заказов: {stats['active_orders']}\n"
        f"💬 Открытых обращений: {stats['open_tickets']}"
    )

    await safe_edit_text(callback.message, text, parse_mode="HTML", reply_markup=get_admin_menu())
    await callback.answer()



@router.callback_query(F.data == "admin_utm_menu")
@admin_only
async def admin_utm_menu_callback(callback: CallbackQuery):
    """Show UTM statistics menu"""
    text = "📊 <b>UTM Статистика</b>\n\nВыберите раздел для просмотра:"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_admin_utm_menu())
    await callback.answer()


@router.callback_query(F.data == "admin_utm_stats")
@admin_only
async def admin_utm_stats_callback(callback: CallbackQuery):
    """Show UTM stats"""
    db = get_db()
    async with db.get_session() as session:
        stats = await get_utm_statistics(session)

    if not stats:
        await callback.message.edit_text(
            "📊 <b>UTM Статистика</b>\n\n"
            "ℹ️ Пока нет данных по UTM-меткам.\n\n"
            "Пользователи без UTM-меток не учитываются в этой статистике. "
            "Создайте ссылку с UTM-метками для отслеживания источников трафика.",
            parse_mode="HTML",
            reply_markup=get_admin_back()
        )
        await callback.answer()
        return

    text = "📊 <b>Статистика по UTM-меткам</b>\n\n"

    for stat in stats[:10]:  # Show top 10 sources
        source = stat['utm_source']
        medium = stat['utm_medium']
        campaign = stat['utm_campaign']
        total_users = stat['total_users']
        paying_users = stat['paying_users']
        conversion_rate = stat['conversion_rate']
        revenue = stat['revenue']
        arpu = stat['arpu']

        text += (
            f"🔹 <b>{source} / {medium} / {campaign}</b>\n"
            f"   👥 Пользователей: {total_users}\n"
            f"   💰 Купили: {paying_users} ({conversion_rate}%)\n"
            f"   💵 Выручка: {revenue:.2f}₽\n"
            f"   📈 ARPU: {arpu:.2f}₽\n\n"
        )

    if len(stats) > 10:
        text += f"<i>...и еще {len(stats) - 10} источников</i>"

    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_admin_back())
    await callback.answer()


@router.callback_query(F.data == "admin_utm_funnel")
@admin_only
async def admin_utm_funnel_callback(callback: CallbackQuery):
    """Show UTM funnel"""
    db = get_db()
    async with db.get_session() as session:
        funnel = await get_conversion_funnel(session)

    starts = funnel.get('starts', 0)
    first_images = funnel.get('first_images', 0)
    purchases = funnel.get('purchases', 0)
    start_to_first_image_rate = funnel.get('start_to_first_image_rate', 0)
    first_image_to_purchase_rate = funnel.get('first_image_to_purchase_rate', 0)
    overall_conversion_rate = funnel.get('overall_conversion_rate', 0)

    if starts == 0 and first_images == 0 and purchases == 0:
        text = (
            "📊 <b>Воронка конверсии (UTM пользователи)</b>\n\n"
            "ℹ️ Пока нет данных о конверсии.\n\n"
            "Данные появятся после того, как пользователи из UTM-источников "
            "начнут использовать бота и совершать покупки."
        )
    else:
        text = (
            "📊 <b>Воронка конверсии (UTM пользователи)</b>\n\n"
            f"1️⃣ <b>Запуск бота</b>: {starts} чел.\n"
            f"   ⬇️ {start_to_first_image_rate}%\n\n"
            f"2️⃣ <b>Первое фото</b>: {first_images} чел.\n"
            f"   ⬇️ {first_image_to_purchase_rate}%\n\n"
            f"3️⃣ <b>Покупка</b>: {purchases} чел.\n\n"
            f"📈 <b>Общая конверсия</b>: {overall_conversion_rate}%\n\n"
            "<i>Учитываются только пользователи из UTM-источников</i>"
        )

    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_admin_back())
    await callback.answer()


@router.callback_query(F.data == "admin_utm_events")
@admin_only
async def admin_utm_events_callback(callback: CallbackQuery):
    """Show UTM events"""
    db = get_db()
    async with db.get_session() as session:
        events = await get_utm_events_summary(session, limit=20)

    if not events:
        await callback.message.edit_text(
            "📊 <b>События UTM</b>\n\n"
            "ℹ️ Нет событий для отображения.",
            parse_mode="HTML",
            reply_markup=get_admin_back()
        )
        await callback.answer()
        return

    text = f"📊 <b>Последние {len(events)} событий UTM</b>\n\n"

    for event in events[:20]:  # Show max 20 in message
        event_type = event['event_type']
        user_id = event['user_id']
        username = event['username'] or 'N/A'
        utm_source = event['utm_source'] or '-'
        utm_campaign = event['utm_campaign'] or '-'
        event_value = event['event_value']
        sent = "✅" if event['sent_to_metrika'] else "⏳"

        # Event emoji
        event_emoji = {
            'start': '🚀',
            'first_image': '📸',
            'purchase': '💰'
        }.get(event_type, '📌')

        text += f"{event_emoji} <code>{event_type}</code>"

        if event_value:
            text += f" ({event_value}₽)"

        text += f"\n   👤 @{username} ({user_id})\n"
        text += f"   🏷 {utm_source}/{utm_campaign} {sent}\n\n"

    if len(events) > 20:
        text += f"<i>...и еще {len(events) - 20} событий</i>\n\n"

    text += "\n<i>✅ отправлено в Метрику, ⏳ в очереди</i>"

    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_admin_back())
    await callback.answer()


@router.callback_query(F.data == "admin_utm_sync_status")
@admin_only
async def admin_utm_sync_status_callback(callback: CallbackQuery):
    """Show UTM sync status"""
    db = get_db()
    async with db.get_session() as session:
        status = await get_utm_sync_status(session)

    total = status['total_events']
    sent = status['sent_events']
    pending = status['pending_events']
    sync_rate = status['sync_rate']
    last_sent = status['last_sent_at']
    last_pending = status['last_pending_at']
    pending_breakdown = status['pending_breakdown']

    # Format last sent time
    if last_sent:
        from datetime import datetime
        try:
            last_sent_dt = datetime.fromisoformat(last_sent)
            last_sent_str = last_sent_dt.strftime("%d.%m.%Y %H:%M:%S")
        except:
            last_sent_str = last_sent
    else:
        last_sent_str = "Никогда"

    # Build text
    text = (
        "📊 <b>Статус синхронизации с Яндекс.Метрикой</b>\n\n"
        f"📈 <b>Общая статистика:</b>\n"
        f"   Всего событий: {total}\n"
        f"   ✅ Отправлено: {sent} ({sync_rate}%)\n"
        f"   ⏳ В очереди: {pending}\n\n"
    )

    if pending > 0:
        text += "📋 <b>В очереди по типам:</b>\n"
        event_names = {
            'start': '🚀 Запуски бота',
            'first_image': '📸 Первые фото',
            'purchase': '💰 Покупки'
        }
        for event_type, count in pending_breakdown.items():
            event_name = event_names.get(event_type, event_type)
            text += f"   {event_name}: {count}\n"
        text += "\n"

    text += (
        f"🕐 <b>Последняя отправка:</b> {last_sent_str}\n\n"
        f"⚙️ <b>Интервал загрузки:</b> {metrika_service.is_enabled and 'каждый час' or 'Метрика отключена'}\n\n"
    )

    if not metrika_service.is_enabled:
        text += (
            "⚠️ <b>Яндекс.Метрика отключена</b>\n"
            "События сохраняются в БД, но не отправляются в Метрику.\n"
            "Для включения установите YANDEX_METRIKA_COUNTER_ID и YANDEX_METRIKA_TOKEN в .env"
        )
    elif pending > 0:
        text += "✅ Все события отправлены в Метрику!"
    else:
        text += "✅ Все события отправлены в Метрику!"

    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_admin_back())
    await callback.answer()


# ==================== UTM TRACKING STATISTICS ====================

@router.message(Command("utm_stats"))
@admin_only
async def utm_stats_handler(message: Message):
    """
    Show UTM tracking statistics (only for admins).

    Usage: /utm_stats
    """
    db = get_db()
    async with db.get_session() as session:
        stats = await get_utm_statistics(session)

    if not stats:
        await message.answer(
            "📊 <b>UTM Статистика</b>\n\n"
            "ℹ️ Пока нет данных по UTM-меткам.\n\n"
            "Пользователи без UTM-меток не учитываются в этой статистике. "
            "Создайте ссылку с UTM-метками для отслеживания источников трафика.",
            parse_mode="HTML"
        )
        return

    text = "📊 <b>Статистика по UTM-меткам</b>\n\n"

    for stat in stats[:10]:  # Show top 10 sources
        source = stat['utm_source']
        medium = stat['utm_medium']
        campaign = stat['utm_campaign']
        total_users = stat['total_users']
        paying_users = stat['paying_users']
        conversion_rate = stat['conversion_rate']
        revenue = stat['revenue']
        arpu = stat['arpu']

        text += (
            f"🔹 <b>{source} / {medium} / {campaign}</b>\n"
            f"   👥 Пользователей: {total_users}\n"
            f"   💰 Купили: {paying_users} ({conversion_rate}%)\n"
            f"   💵 Выручка: {revenue:.2f}₽\n"
            f"   📈 ARPU: {arpu:.2f}₽\n\n"
        )

    if len(stats) > 10:
        text += f"<i>...и еще {len(stats) - 10} источников</i>\n\n"

    text += (
        "📌 <b>Команды:</b>\n"
        "• /utm_funnel — воронка конверсии\n"
        "• /utm_events — последние события"
    )

    await message.answer(text, parse_mode="HTML")


@router.message(Command("utm_funnel"))
@admin_only
async def utm_funnel_handler(message: Message):
    """
    Show UTM conversion funnel (only for admins).

    Usage: /utm_funnel
    """
    db = get_db()
    async with db.get_session() as session:
        funnel = await get_conversion_funnel(session)

    starts = funnel.get('starts', 0)
    first_images = funnel.get('first_images', 0)
    purchases = funnel.get('purchases', 0)
    start_to_first_image_rate = funnel.get('start_to_first_image_rate', 0)
    first_image_to_purchase_rate = funnel.get('first_image_to_purchase_rate', 0)
    overall_conversion_rate = funnel.get('overall_conversion_rate', 0)

    if starts == 0 and first_images == 0 and purchases == 0:
        text = (
            "📊 <b>Воронка конверсии (UTM пользователи)</b>\n\n"
            "ℹ️ Пока нет данных о конверсии.\n\n"
            "Данные появятся после того, как пользователи из UTM-источников "
            "начнут использовать бота и совершать покупки."
        )
    else:
        text = (
            "📊 <b>Воронка конверсии (UTM пользователи)</b>\n\n"
            f"1️⃣ <b>Запуск бота</b>: {starts} чел.\n"
            f"   ⬇️ {start_to_first_image_rate}%\n\n"
            f"2️⃣ <b>Первое фото</b>: {first_images} чел.\n"
            f"   ⬇️ {first_image_to_purchase_rate}%\n\n"
            f"3️⃣ <b>Покупка</b>: {purchases} чел.\n\n"
            f"📈 <b>Общая конверсия</b>: {overall_conversion_rate}%\n\n"
            "<i>Учитываются только пользователи из UTM-источников</i>"
        )

    await message.answer(text, parse_mode="HTML")


@router.message(Command("utm_events"))
@admin_only
async def utm_events_handler(message: Message):
    """
    Show recent UTM events (only for admins).

    Usage: /utm_events [limit]
    Example: /utm_events 20
    """
    # Parse limit from command
    limit = 20
    if message.text and len(message.text.split()) > 1:
        try:
            limit = int(message.text.split()[1])
            limit = min(max(limit, 1), 100)  # Clamp between 1 and 100
        except ValueError:
            pass

    db = get_db()
    async with db.get_session() as session:
        events = await get_utm_events_summary(session, limit=limit)

    if not events:
        await message.answer(
            "📊 <b>События UTM</b>\n\n"
            "ℹ️ Нет событий для отображения.",
            parse_mode="HTML"
        )
        return

    text = f"📊 <b>Последние {len(events)} событий UTM</b>\n\n"

    for event in events[:20]:  # Show max 20 in message
        event_type = event['event_type']
        user_id = event['user_id']
        username = event['username'] or 'N/A'
        utm_source = event['utm_source'] or '-'
        utm_campaign = event['utm_campaign'] or '-'
        event_value = event['event_value']
        sent = "✅" if event['sent_to_metrika'] else "⏳"

        # Event emoji
        event_emoji = {
            'start': '🚀',
            'first_image': '📸',
            'purchase': '💰'
        }.get(event_type, '📌')

        text += f"{event_emoji} <code>{event_type}</code>"

        if event_value:
            text += f" ({event_value}₽)"

        text += f"\n   👤 @{username} ({user_id})\n"
        text += f"   🏷 {utm_source}/{utm_campaign} {sent}\n\n"

    if len(events) > 20:
        text += f"<i>...и еще {len(events) - 20} событий</i>\n\n"

    text += "\n<i>✅ отправлено в Метрику, ⏳ в очереди</i>"

    await message.answer(text, parse_mode="HTML")


@router.message(Command("utm_sync_status"))
@admin_only
async def utm_sync_status_handler(message: Message):
    """
    Show Yandex Metrika synchronization status (only for admins).

    Usage: /utm_sync_status
    """
    db = get_db()
    async with db.get_session() as session:
        status = await get_utm_sync_status(session)

    total = status['total_events']
    sent = status['sent_events']
    pending = status['pending_events']
    sync_rate = status['sync_rate']
    last_sent = status['last_sent_at']
    last_pending = status['last_pending_at']
    pending_breakdown = status['pending_breakdown']

    # Format last sent time
    if last_sent:
        from datetime import datetime
        try:
            last_sent_dt = datetime.fromisoformat(last_sent)
            last_sent_str = last_sent_dt.strftime("%d.%m.%Y %H:%M:%S")
        except:
            last_sent_str = last_sent
    else:
        last_sent_str = "Никогда"

    # Build text
    text = (
        "📊 <b>Статус синхронизации с Яндекс.Метрикой</b>\n\n"
        f"📈 <b>Общая статистика:</b>\n"
        f"   Всего событий: {total}\n"
        f"   ✅ Отправлено: {sent} ({sync_rate}%)\n"
        f"   ⏳ В очереди: {pending}\n\n"
    )

    if pending > 0:
        text += "📋 <b>В очереди по типам:</b>\n"
        event_names = {
            'start': '🚀 Запуски бота',
            'first_image': '📸 Первые фото',
            'purchase': '💰 Покупки'
        }
        for event_type, count in pending_breakdown.items():
            event_name = event_names.get(event_type, event_type)
            text += f"   {event_name}: {count}\n"
        text += "\n"

    text += (
        f"🕐 <b>Последняя отправка:</b> {last_sent_str}\n\n"
        f"⚙️ <b>Интервал загрузки:</b> {metrika_service.is_enabled and 'каждый час' or 'Метрика отключена'}\n\n"
    )

    if not metrika_service.is_enabled:
        text += (
            "⚠️ <b>Яндекс.Метрика отключена</b>\n"
            "События сохраняются в БД, но не отправляются в Метрику.\n"
            "Для включения установите YANDEX_METRIKA_COUNTER_ID и YANDEX_METRIKA_TOKEN в .env\n\n"
        )
    elif pending > 0:
        text += (
            "💡 <b>Команды:</b>\n"
            "• /utm_upload — загрузить события сейчас\n"
            "• /utm_events — посмотреть последние события"
        )
    else:
        text += "✅ Все события отправлены в Метрику!"

    await message.answer(text, parse_mode="HTML")


@router.message(Command("utm_upload"))
@admin_only
async def utm_upload_handler(message: Message):
    """
    Manually upload pending events to Yandex Metrika (only for admins).

    Usage: /utm_upload
    """
    if not metrika_service.is_enabled:
        await message.answer(
            "⚠️ <b>Яндекс.Метрика отключена</b>\n\n"
            "События не могут быть отправлены, так как Метрика не настроена.\n"
            "Для включения установите YANDEX_METRIKA_COUNTER_ID и YANDEX_METRIKA_TOKEN в .env",
            parse_mode="HTML"
        )
        return

    # Get pending count first
    db = get_db()
    async with db.get_session() as session:
        status = await get_utm_sync_status(session)
        pending = status['pending_events']

    if pending == 0:
        await message.answer(
            "✅ <b>Нет событий для отправки</b>\n\n"
            "Все события уже отправлены в Яндекс.Метрику.",
            parse_mode="HTML"
        )
        return

    # Send status message
    status_msg = await message.answer(
        f"⏳ Отправляю {pending} событий в Яндекс.Метрику...",
        parse_mode="HTML"
    )

    # Upload events
    async with db.get_session() as session:
        success = await metrika_service.upload_pending_events(session)

    if success:
        # Get updated status
        async with db.get_session() as session:
            new_status = await get_utm_sync_status(session)
            new_pending = new_status['pending_events']

        uploaded = pending - new_pending

        await status_msg.edit_text(
            f"✅ <b>Успешно отправлено!</b>\n\n"
            f"Отправлено событий: {uploaded}\n"
            f"Осталось в очереди: {new_pending}\n\n"
            f"Используйте /utm_sync_status для проверки статуса",
            parse_mode="HTML"
        )
    else:
        await status_msg.edit_text(
            "❌ <b>Ошибка при отправке</b>\n\n"
            "Не удалось отправить события в Яндекс.Метрику.\n"
            "Проверьте логи для подробностей.\n\n"
            "Возможные причины:\n"
            "• Неверный токен или счетчик\n"
            "• Офлайн-конверсии не включены в Метрике\n"
            "• Проблемы с сетью",
            parse_mode="HTML"
        )


# ==================== DIRECT MESSAGE TO USER ====================

@router.message(Command("message"))
@admin_only
async def send_message_to_user_command(message: Message, state: FSMContext):
    """
    Send direct message to user by ID.

    Usage:
    /message <user_id> <text>

    Example:
    /message 123456789 Здравствуйте! По вашему вопросу...
    """
    try:
        parts = message.text.split(maxsplit=2)
        if len(parts) < 3:
            await message.answer(
                "📨 <b>Отправка сообщения пользователю</b>\n\n"
                "<b>Использование:</b>\n"
                "/message &lt;user_id&gt; &lt;текст сообщения&gt;\n\n"
                "<b>Пример:</b>\n"
                "/message 123456789 Здравствуйте! По вашему вопросу о возврате...\n\n"
                "<i>User ID можно найти в обращениях в поддержку или в списке заказов</i>",
                parse_mode="HTML"
            )
            return

        user_id = int(parts[1])
        message_text = parts[2]

    except (IndexError, ValueError):
        await message.answer(
            "❌ <b>Ошибка формата</b>\n\n"
            "User ID должен быть числом.\n\n"
            "Используйте: /message &lt;user_id&gt; &lt;текст&gt;",
            parse_mode="HTML"
        )
        return

    # Verify user exists
    db = get_db()
    async with db.get_session() as session:
        user = await get_or_create_user(session, user_id)

        if not user:
            await message.answer(f"❌ Пользователь с ID {user_id} не найден")
            return

        # Send message to user
        try:
            await message.bot.send_message(
                chat_id=user_id,
                text=(
                    f"💬 <b>Сообщение от администратора</b>\n\n"
                    f"{message_text}\n\n"
                    f"<i>Для ответа используйте меню 💬 Поддержка</i>"
                ),
                parse_mode="HTML"
            )

            # Confirm to admin
            await message.answer(
                f"✅ <b>Сообщение отправлено!</b>\n\n"
                f"👤 Пользователь: {user_id} (@{user.username or 'N/A'})\n"
                f"💬 Ваше сообщение:\n{message_text[:200]}{'...' if len(message_text) > 200 else ''}",
                parse_mode="HTML"
            )

        except TelegramBadRequest as e:
            await message.answer(
                f"❌ <b>Ошибка отправки</b>\n\n"
                f"Не удалось отправить сообщение пользователю {user_id}.\n\n"
                f"Возможные причины:\n"
                f"• Пользователь заблокировал бота\n"
                f"• Пользователь не запускал бота\n"
                f"• Неверный ID\n\n"
                f"Ошибка: {str(e)}",
                parse_mode="HTML"
            )


@router.callback_query(F.data == "admin_send_message")
@admin_only
async def admin_send_message_start(callback: CallbackQuery, state: FSMContext):
    """Start sending direct message to user (via admin panel)"""
    await state.set_state(AdminStates.waiting_for_message_user_id)

    await callback.message.edit_text(
        "📨 <b>Отправка сообщения пользователю</b>\n\n"
        "Введите Telegram ID пользователя:\n\n"
        "<i>ID можно найти в обращениях в поддержку или в списке заказов</i>",
        parse_mode="HTML",
        reply_markup=get_admin_cancel()
    )
    await callback.answer()


@router.message(AdminStates.waiting_for_message_user_id, F.text)
@admin_only
async def admin_send_message_get_user_id(message: Message, state: FSMContext):
    """Process user ID for sending message"""
    try:
        user_id = int(message.text)
    except ValueError:
        await message.answer("❌ Неверный формат ID. Введите числовое значение.")
        return

    # Verify user exists
    db = get_db()
    async with db.get_session() as session:
        user = await get_or_create_user(session, user_id)

    await state.update_data(message_target_user_id=user_id)
    await state.set_state(AdminStates.waiting_for_message_text)

    await message.answer(
        f"✅ <b>Пользователь найден</b>\n\n"
        f"👤 ID: {user.telegram_id}\n"
        f"📱 Username: @{user.username or 'N/A'}\n"
        f"💎 Баланс: {user.images_remaining}\n\n"
        f"Теперь введите текст сообщения:",
        parse_mode="HTML"
    )


@router.message(AdminStates.waiting_for_message_text, F.text)
@admin_only
async def admin_send_message_send(message: Message, state: FSMContext):
    """Send message to user"""
    data = await state.get_data()
    user_id = data.get('message_target_user_id')

    if not user_id:
        await message.answer("❌ Ошибка: ID пользователя не найден")
        return

    message_text = message.text

    # Validate message length
    if len(message_text) < 1:
        await message.answer("❌ Сообщение не может быть пустым")
        return

    if len(message_text) > 4096:
        await message.answer("❌ Сообщение слишком длинное (максимум 4096 символов)")
        return

    # Send message to user
    try:
        await message.bot.send_message(
            chat_id=user_id,
            text=(
                f"💬 <b>Сообщение от администратора</b>\n\n"
                f"{message_text}\n\n"
                f"<i>Для ответа используйте меню 💬 Поддержка</i>"
            ),
            parse_mode="HTML"
        )

        # Get user info for confirmation
        db = get_db()
        async with db.get_session() as session:
            user = await get_or_create_user(session, user_id)

        # Confirm to admin
        await message.answer(
            f"✅ <b>Сообщение отправлено!</b>\n\n"
            f"👤 Пользователь: {user_id} (@{user.username or 'N/A'})\n"
            f"💬 Ваше сообщение:\n{message_text[:200]}{'...' if len(message_text) > 200 else ''}",
            parse_mode="HTML"
        )

        await state.clear()

    except TelegramBadRequest as e:
        await message.answer(
            f"❌ <b>Ошибка отправки</b>\n\n"
            f"Не удалось отправить сообщение пользователю {user_id}.\n\n"
            f"Возможные причины:\n"
            f"• Пользователь заблокировал бота\n"
            f"• Пользователь не запускал бота\n"
            f"• Неверный ID\n\n"
            f"Ошибка: {str(e)}",
            parse_mode="HTML"
        )
        await state.clear()
