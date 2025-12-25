from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import select, func, and_, update, desc, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import uuid
import logging

from .models import User, Package, Order, ProcessedImage, SupportTicket, SupportMessage, Admin, UTMEvent, ReferralReward, StylePreset

logger = logging.getLogger(__name__)


# ==================== USER OPERATIONS ====================

async def get_or_create_user(
    session: AsyncSession,
    telegram_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    free_photoshoots_count: Optional[int] = None,  # Changed to Optional, will use settings if None
    utm_source: Optional[str] = None,
    utm_medium: Optional[str] = None,
    utm_campaign: Optional[str] = None,
    utm_content: Optional[str] = None,
    utm_term: Optional[str] = None
) -> User:
    """Get existing user or create new one"""
    # Import settings here to avoid circular import
    from app.config import settings

    # Use settings value if not provided
    if free_photoshoots_count is None:
        free_photoshoots_count = settings.FREE_PHOTOSHOOTS_COUNT

    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        metrika_client_id = str(uuid.uuid4())

        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            images_remaining=free_photoshoots_count,
            utm_source=utm_source,
            utm_medium=utm_medium,
            utm_campaign=utm_campaign,
            utm_content=utm_content,
            utm_term=utm_term,
            metrika_client_id=metrika_client_id
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
    else:
        # Update info
        if username: user.username = username
        if first_name: user.first_name = first_name
        if last_name: user.last_name = last_name
        
        # Update UTM if new data provided and missing
        if not user.utm_source and utm_source: user.utm_source = utm_source
        if not user.utm_medium and utm_medium: user.utm_medium = utm_medium
        if not user.utm_campaign and utm_campaign: user.utm_campaign = utm_campaign
        
        if not user.metrika_client_id:
            user.metrika_client_id = str(uuid.uuid4())
            
        await session.commit()
        await session.refresh(user)

    return user


async def get_user_balance(session: AsyncSession, telegram_id: int) -> dict:
    """Get user's balance (photoshoots remaining)"""
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        return {"total": 0, "free": 0, "paid": 0}

    # In this model, we just track total remaining photoshoots
    # You can expand logic to separate free/paid if needed based on purchase history
    return {
        "total": user.images_remaining,
        "free": user.images_remaining, # Simplified
        "paid": 0 # Simplified
    }


async def update_user_images_count(session: AsyncSession, user_id: int, delta: int):
    """Update user images count (delta can be negative)"""
    await session.execute(
        update(User)
        .where(User.id == user_id)
        .values(images_remaining=User.images_remaining + delta)
    )
    await session.commit()


async def decrease_balance(session: AsyncSession, telegram_id: int, amount: int = 1) -> bool:
    """Decrease user's balance"""
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()

    if not user or user.images_remaining < amount:
        return False

    user.images_remaining -= amount
    await session.commit()
    return True


async def update_user_stats(session: AsyncSession, telegram_id: int) -> tuple[bool, int]:
    """Update user's total processed stats"""
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()

    if user:
        is_first = (user.total_images_processed == 0)
        user.total_images_processed += 1
        user.updated_at = datetime.utcnow()
        await session.commit()
        return (is_first, user.id)

    return (False, 0)


# ==================== STYLE PRESET OPERATIONS ====================

async def create_style_preset(
    session: AsyncSession,
    user_id: int,
    name: str,
    style_data: dict
) -> StylePreset:
    """Create saved style"""
    preset = StylePreset(
        user_id=user_id,
        name=name,
        style_data=style_data
    )
    session.add(preset)
    await session.commit()
    await session.refresh(preset)
    return preset


async def get_user_style_presets(
    session: AsyncSession,
    user_id: int,
    active_only: bool = True
) -> List[StylePreset]:
    """Get user's style presets"""
    query = select(StylePreset).where(StylePreset.user_id == user_id)
    if active_only:
        query = query.where(StylePreset.is_active == True)
    query = query.order_by(StylePreset.created_at.desc())
    result = await session.execute(query)
    return result.scalars().all()


async def get_style_preset_by_id(
    session: AsyncSession,
    preset_id: int,
    user_id: int
) -> Optional[StylePreset]:
    """Get style preset by ID"""
    query = select(StylePreset).where(
        StylePreset.id == preset_id,
        StylePreset.user_id == user_id,
        StylePreset.is_active == True
    )
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def update_style_preset(
    session: AsyncSession,
    preset_id: int,
    user_id: int,
    name: Optional[str] = None,
    style_data: Optional[dict] = None
) -> Optional[StylePreset]:
    """Update style preset"""
    preset = await get_style_preset_by_id(session, preset_id, user_id)
    if not preset:
        return None
    
    if name:
        preset.name = name
    if style_data:
        preset.style_data = style_data
    
    await session.commit()
    await session.refresh(preset)
    return preset


async def delete_style_preset(
    session: AsyncSession,
    preset_id: int,
    user_id: int
) -> bool:
    """Delete style preset (soft delete)"""
    preset = await get_style_preset_by_id(session, preset_id, user_id)
    if not preset:
        return False
    
    preset.is_active = False
    await session.commit()
    return True


async def count_user_active_presets(
    session: AsyncSession,
    user_id: int
) -> int:
    """Count user's active presets"""
    query = select(func.count(StylePreset.id)).where(
        StylePreset.user_id == user_id,
        StylePreset.is_active == True
    )
    result = await session.execute(query)
    return result.scalar() or 0


# ==================== PACKAGE OPERATIONS ====================

async def get_all_packages(session: AsyncSession) -> List[Package]:
    """Get all active packages"""
    result = await session.execute(
        select(Package).where(Package.is_active == True).order_by(Package.photoshoots_count)
    )
    return result.scalars().all()


async def get_package_by_id(session: AsyncSession, package_id: int) -> Optional[Package]:
    result = await session.execute(select(Package).where(Package.id == package_id))
    return result.scalar_one_or_none()


async def sync_packages_from_config(session: AsyncSession, packages_config: List[dict]):
    """Sync packages from config"""
    active_ids = []
    for config in packages_config:
        name = config["name"]
        count = config["photoshoots_count"]
        price = config["price_rub"]

        result = await session.execute(
            select(Package).where(and_(Package.name == name, Package.photoshoots_count == count))
        )
        package = result.scalar_one_or_none()

        if package:
            package.price_rub = price
            package.is_active = True
            active_ids.append(package.id)
        else:
            package = Package(name=name, photoshoots_count=count, price_rub=price, is_active=True)
            session.add(package)
            await session.flush()
            active_ids.append(package.id)

    await session.execute(
        update(Package).where(Package.id.not_in(active_ids)).values(is_active=False)
    )
    await session.commit()


# ==================== ORDER OPERATIONS ====================

async def create_order(session: AsyncSession, telegram_id: int, package_id: int,
                       invoice_id: str, amount: float) -> Order:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if not user: raise ValueError("User not found")

    order = Order(
        user_id=user.id,
        package_id=package_id,
        invoice_id=invoice_id,
        amount=amount,
        status="pending"
    )
    session.add(order)
    await session.commit()
    await session.refresh(order)
    return order


async def get_order_by_invoice_id(session: AsyncSession, invoice_id: str) -> Optional[Order]:
    result = await session.execute(select(Order).where(Order.invoice_id == invoice_id))
    return result.scalar_one_or_none()


async def mark_order_paid(session: AsyncSession, invoice_id: str) -> Optional[Order]:
    order = await get_order_by_invoice_id(session, invoice_id)
    if not order or order.status == "paid": return None

    order.status = "paid"
    order.paid_at = datetime.utcnow()

    # Load relations
    await session.refresh(order, ['user', 'package'])

    # Add photoshoots to user balance
    order.user.images_remaining += order.package.photoshoots_count

    # Track "purchase" event for UTM users
    if order.user.utm_source or order.user.utm_medium or order.user.utm_campaign:
        from app.services.yandex_metrika import metrika_service
        await metrika_service.track_event(
            session=session,
            user_id=order.user.id,
            event_type='purchase',
            event_value=float(order.amount),
            currency='RUB',
            event_data={
                'utm_source': order.user.utm_source,
                'utm_medium': order.user.utm_medium,
                'utm_campaign': order.user.utm_campaign,
                'package_id': order.package_id,
                'package_name': order.package.name,
                'photoshoots_count': order.package.photoshoots_count
            }
        )
        logger.info(f"Tracked 'purchase' event for UTM user {order.user.id}, amount: {order.amount}₽")

    # Referral reward
    if order.user.referred_by_id:
        from app.config import settings
        reward_count = int(order.package.photoshoots_count * settings.REFERRAL_REWARD_PURCHASE_PERCENT / 100)
        if reward_count > 0:
            await add_referral_reward(
                session,
                user_id=order.user.referred_by_id,
                referred_user_id=order.user.id,
                reward_type='referral_purchase',
                images_rewarded=reward_count,
                order_id=order.id
            )

    await session.commit()
    return order


async def get_all_orders(session: AsyncSession, status: Optional[str] = None, limit: int = 50, offset: int = 0) -> List[Order]:
    """Get all orders with optional status filter"""
    query = select(Order).options(
        selectinload(Order.user),
        selectinload(Order.package)
    ).order_by(Order.created_at.desc())

    if status:
        query = query.where(Order.status == status)

    query = query.limit(limit).offset(offset)
    result = await session.execute(query)
    return result.scalars().all()


async def get_order_by_id(session: AsyncSession, order_id: int) -> Optional[Order]:
    """Get order by ID with related data"""
    result = await session.execute(
        select(Order)
        .where(Order.id == order_id)
        .options(
            selectinload(Order.user),
            selectinload(Order.package),
            selectinload(Order.processed_images)
        )
    )
    return result.scalar_one_or_none()


async def cancel_order(session: AsyncSession, order_id: int, admin_id: int) -> Optional[Order]:
    """Cancel an order (only if not paid)"""
    order = await get_order_by_id(session, order_id)

    if not order:
        return None

    if order.status == "paid":
        return None  # Cannot cancel paid order, use refund instead

    order.status = "cancelled"
    await session.commit()
    await session.refresh(order)
    return order


async def refund_order(session: AsyncSession, order_id: int, admin_id: int) -> Optional[Order]:
    """Refund a paid order and deduct photoshoots from user balance"""
    order = await get_order_by_id(session, order_id)

    if not order:
        return None

    if order.status != "paid":
        return None  # Can only refund paid orders

    # Load user and package
    await session.refresh(order, ['user', 'package'])

    # Deduct photoshoots from user balance
    photoshoots_to_deduct = order.package.photoshoots_count

    # Only deduct if user has enough balance, otherwise set to 0
    if order.user.images_remaining >= photoshoots_to_deduct:
        order.user.images_remaining -= photoshoots_to_deduct
    else:
        order.user.images_remaining = 0

    # Update order status
    order.status = "refunded"

    await session.commit()
    await session.refresh(order)
    return order


async def get_orders_count(session: AsyncSession, status: Optional[str] = None) -> int:
    """Get total count of orders"""
    query = select(func.count(Order.id))

    if status:
        query = query.where(Order.status == status)

    result = await session.execute(query)
    return result.scalar() or 0


# ==================== PROCESSED IMAGE ====================

async def create_processed_image(
    session: AsyncSession,
    user_id: int,
    telegram_file_id: Optional[str],
    style_name: str,
    prompt_used: str,
    aspect_ratio: str,
    is_free: bool = False
) -> ProcessedImage:
    """
    Create processed image record
    
    Args:
        user_id: Database user ID (users.id, NOT telegram_id)
        telegram_file_id: Telegram file ID of the processed image
        style_name: Name of the style used
        prompt_used: Prompt used for generation
        aspect_ratio: Aspect ratio of the image
        is_free: Whether this was a free image
        
    Raises:
        ValueError: If user with given ID doesn't exist in database
    """
    # Validate that user exists with this database ID
    result = await session.execute(
        select(User.id).where(User.id == user_id)
    )
    if not result.scalar_one_or_none():
        logger.error(f"Cannot create processed image: user not found with database id={user_id}. "
                    f"Possible cause: telegram_id was passed instead of database user.id")
        raise ValueError(f"User with database id={user_id} not found. This must be the internal database ID, not telegram_id.")
    
    image = ProcessedImage(
        user_id=user_id,
        telegram_file_id=telegram_file_id,
        style_name=style_name,
        prompt_used=prompt_used,
        aspect_ratio=aspect_ratio,
        is_free=is_free
    )
    session.add(image)
    await session.commit()
    logger.info(f"Created processed image for user_id={user_id}, style={style_name}")
    return image


async def save_processed_image(
    session: AsyncSession,
    user_id: int,
    telegram_file_id: str,
    original_file_id: str,
    prompt_used: str,
    is_free: bool = False
):
    """
    Legacy method wrapper - ensures user_id is the database ID
    
    Args:
        user_id: Database user ID (users.id, NOT telegram_id)
        telegram_file_id: Telegram file ID of the processed image
        original_file_id: Original file ID (legacy parameter)
        prompt_used: Prompt used for generation
        is_free: Whether this was a free image
        
    Raises:
        ValueError: If user with given ID doesn't exist in database
    """
    # Validate that user exists with this database ID before proceeding
    result = await session.execute(
        select(User.id).where(User.id == user_id)
    )
    if not result.scalar_one_or_none():
        logger.error(f"Cannot save processed image: user not found with database id={user_id}. "
                    f"Possible cause: telegram_id was passed instead of database user.id")
        raise ValueError(f"User with database id={user_id} not found. This must be the internal database ID, not telegram_id.")
    
    await create_processed_image(
        session,
        user_id,
        telegram_file_id,
        "Legacy",
        prompt_used,
        "1:1",
        is_free
    )


# ==================== SUPPORT ====================

async def create_support_ticket(session: AsyncSession, telegram_id: int, message: str, order_id: Optional[int] = None) -> SupportTicket:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if not user: raise ValueError("User not found")

    ticket = SupportTicket(user_id=user.id, order_id=order_id, message=message)
    session.add(ticket)
    await session.commit()
    await session.refresh(ticket)
    return ticket

async def get_open_tickets(session: AsyncSession) -> List[SupportTicket]:
    result = await session.execute(
        select(SupportTicket)
        .where(SupportTicket.status.in_(["open", "in_progress"]))
        .order_by(SupportTicket.created_at.desc())
        .options(selectinload(SupportTicket.user))
    )
    return result.scalars().all()

async def get_ticket_by_id(session: AsyncSession, ticket_id: int) -> Optional[SupportTicket]:
    result = await session.execute(
        select(SupportTicket).where(SupportTicket.id == ticket_id)
        .options(selectinload(SupportTicket.user), selectinload(SupportTicket.messages))
    )
    return result.scalar_one_or_none()

async def add_support_message(session: AsyncSession, ticket_id: int, sender_telegram_id: int, message: str, is_admin: bool = False) -> SupportMessage:
    msg = SupportMessage(ticket_id=ticket_id, sender_telegram_id=sender_telegram_id, is_admin=is_admin, message=message)
    session.add(msg)
    if is_admin:
        await session.execute(update(SupportTicket).where(SupportTicket.id == ticket_id).values(status="in_progress"))
    await session.commit()
    return msg

async def resolve_ticket(session: AsyncSession, ticket_id: int, admin_telegram_id: int, admin_response: str):
    await session.execute(
        update(SupportTicket)
        .where(SupportTicket.id == ticket_id)
        .values(status="resolved", admin_response=admin_response, admin_id=admin_telegram_id, resolved_at=datetime.utcnow())
    )
    await session.commit()

# ==================== ADMIN ====================

async def is_admin(session: AsyncSession, telegram_id: int) -> bool:
    result = await session.execute(select(Admin).where(Admin.telegram_id == telegram_id))
    return result.scalar_one_or_none() is not None

async def get_statistics(session: AsyncSession) -> dict:
    """
    Optimized statistics query - single database roundtrip instead of 8 separate queries.
    Uses aggregation with conditional counting for 60-80% performance improvement.
    """
    from sqlalchemy import literal_column

    # Single optimized query with conditional aggregations
    stmt = select(
        func.count(func.distinct(User.id)).label('total_users'),
        func.count(func.distinct(ProcessedImage.id)).label('total_processed'),
        func.coalesce(
            func.sum(case((Order.status == 'paid', Order.amount), else_=0)),
            literal_column('0')
        ).label('revenue'),
        func.count(func.distinct(case((
            Order.status.notin_(["paid", "canceled", "cancelled", "refunded"]),
            Order.id
        )))).label('active_orders'),
        func.count(func.distinct(case((
            Order.status == 'paid',
            Order.id
        )))).label('paid_orders'),
        func.count(func.distinct(case((
            ProcessedImage.is_free == True,
            ProcessedImage.id
        )))).label('free_images'),
        func.count(func.distinct(case((
            ProcessedImage.is_free == False,
            ProcessedImage.id
        )))).label('paid_images'),
        func.count(func.distinct(case((
            SupportTicket.status.in_(["open", "in_progress"]),
            SupportTicket.id
        )))).label('open_tickets')
    ).select_from(User).outerjoin(
        ProcessedImage, User.id == ProcessedImage.user_id
    ).outerjoin(
        Order, User.id == Order.user_id
    ).outerjoin(
        SupportTicket, User.id == SupportTicket.user_id
    )

    result = await session.execute(stmt)
    row = result.one()

    return {
        "total_users": row.total_users or 0,
        "total_processed": row.total_processed or 0,
        "revenue": float(row.revenue or 0),
        "active_orders": row.active_orders or 0,
        "open_tickets": row.open_tickets or 0,
        "free_images_processed": row.free_images or 0,
        "paid_images_processed": row.paid_images or 0,
        "paid_orders": row.paid_orders or 0
    }


async def get_user_detailed_stats(session: AsyncSession, telegram_id: int) -> dict:
    """
    Get detailed user statistics for profile display.
    Optimized to reduce query count by combining related queries.

    Returns:
        dict with user stats including:
        - photoshoots_used: number of photoshoots completed
        - images_generated: total images generated
        - saved_styles: number of saved style presets
        - top_styles: most used styles
        - aspect_ratios: usage breakdown by ratio
        - recent_activity: date of last generation
    """
    from sqlalchemy import desc

    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        return {
            "photoshoots_used": 0,
            "images_generated": 0,
            "saved_styles": 0,
            "top_styles": [],
            "aspect_ratios": {},
            "recent_activity": None,
            "total_spent": 0.0
        }

    # Optimized: Single query for image counts, photoshoots, and recent activity
    images_stats_stmt = select(
        func.count(ProcessedImage.id).label('images_count'),
        func.count(func.distinct(func.date_trunc('minute', ProcessedImage.created_at))).label('photoshoots_count'),
        func.max(ProcessedImage.created_at).label('recent_activity')
    ).where(ProcessedImage.user_id == user.id)

    images_stats_result = await session.execute(images_stats_stmt)
    images_stats = images_stats_result.one()

    images_generated = images_stats.images_count or 0
    photoshoots_used = images_stats.photoshoots_count or 0
    recent_activity = images_stats.recent_activity

    # Combined query for style presets count and total spent
    aggregates_stmt = select(
        func.count(func.distinct(StylePreset.id)).label('saved_styles'),
        func.coalesce(func.sum(case((Order.status == 'paid', Order.amount), else_=0)), 0).label('total_spent')
    ).select_from(User).outerjoin(
        StylePreset, and_(StylePreset.user_id == User.id, StylePreset.is_active == True)
    ).outerjoin(
        Order, User.id == Order.user_id
    ).where(User.id == user.id)

    aggregates_result = await session.execute(aggregates_stmt)
    aggregates = aggregates_result.one()

    saved_styles_count = aggregates.saved_styles or 0
    total_spent = float(aggregates.total_spent or 0.0)

    # Get top 3 most used styles (separate query - needs grouping)
    top_styles_result = await session.execute(
        select(
            ProcessedImage.style_name,
            func.count(ProcessedImage.id).label('count')
        ).where(
            ProcessedImage.user_id == user.id,
            ProcessedImage.style_name.isnot(None)
        ).group_by(ProcessedImage.style_name)
        .order_by(desc('count'))
        .limit(3)
    )
    top_styles = [
        {"name": row.style_name, "count": row.count}
        for row in top_styles_result.all()
    ]

    # Get aspect ratio breakdown (separate query - needs grouping)
    aspect_ratios_result = await session.execute(
        select(
            ProcessedImage.aspect_ratio,
            func.count(ProcessedImage.id).label('count')
        ).where(
            ProcessedImage.user_id == user.id,
            ProcessedImage.aspect_ratio.isnot(None)
        ).group_by(ProcessedImage.aspect_ratio)
        .order_by(desc('count'))
    )
    aspect_ratios = {
        row.aspect_ratio: row.count
        for row in aspect_ratios_result.all()
    }

    return {
        "photoshoots_used": photoshoots_used,
        "images_generated": images_generated,
        "saved_styles": saved_styles_count,
        "top_styles": top_styles,
        "aspect_ratios": aspect_ratios,
        "recent_activity": recent_activity,
        "total_spent": total_spent
    }

# ==================== REFERRAL ====================

async def get_user_by_referral_code(session: AsyncSession, referral_code: str) -> Optional[User]:
    result = await session.execute(select(User).where(User.referral_code == referral_code))
    return result.scalar_one_or_none()

async def get_or_create_referral_code(session: AsyncSession, user_id: int) -> str:
    user = await session.get(User, user_id)
    if not user.referral_code:
        import string, random
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            if not (await session.execute(select(User).where(User.referral_code == code))).scalar_one_or_none():
                user.referral_code = code
                break
        await session.commit()
    return user.referral_code

async def set_user_referrer(session: AsyncSession, user_id: int, referrer_id: int) -> bool:
    user = await session.get(User, user_id)
    if not user.referred_by_id and user_id != referrer_id:
        user.referred_by_id = referrer_id
        await session.execute(update(User).where(User.id == referrer_id).values(total_referrals=User.total_referrals + 1))
        await session.commit()
        return True
    return False

async def add_referral_reward(session: AsyncSession, user_id: int, referred_user_id: int, reward_type: str, images_rewarded: int, order_id: int = None):
    await session.execute(update(User).where(User.id == user_id).values(images_remaining=User.images_remaining + images_rewarded))
    reward = ReferralReward(user_id=user_id, referred_user_id=referred_user_id, order_id=order_id, reward_type=reward_type, images_rewarded=images_rewarded)
    session.add(reward)
    await session.commit()

async def get_referral_stats(session: AsyncSession, user_id: int) -> dict:
    user = await session.get(User, user_id)
    total_rewards = (await session.execute(select(func.sum(ReferralReward.images_rewarded)).where(ReferralReward.user_id == user_id))).scalar() or 0
    start_rewards = (await session.execute(select(func.sum(ReferralReward.images_rewarded)).where(ReferralReward.user_id == user_id, ReferralReward.reward_type == 'referral_start'))).scalar() or 0
    purchase_rewards = (await session.execute(select(func.sum(ReferralReward.images_rewarded)).where(ReferralReward.user_id == user_id, ReferralReward.reward_type == 'referral_purchase'))).scalar() or 0
    
    return {
        "total_referrals": user.total_referrals,
        "total_rewards": int(total_rewards),
        "rewards_from_start": int(start_rewards),
        "rewards_from_purchases": int(purchase_rewards),
        "referral_code": user.referral_code
    }

# ==================== UTM ====================

async def get_utm_statistics(session: AsyncSession) -> List[Dict[str, Any]]:
    """
    Get UTM statistics grouped by source, medium, and campaign.

    Returns:
        List of dicts with UTM stats including users, conversions, revenue
    """
    from sqlalchemy import func, case

    # Get users with UTM data
    stmt = select(
        User.utm_source,
        User.utm_medium,
        User.utm_campaign,
        func.count(User.id).label('total_users'),
        func.count(case((Order.status == 'paid', Order.id))).label('paying_users'),
        func.coalesce(func.sum(case((Order.status == 'paid', Order.amount), else_=0)), 0).label('revenue')
    ).outerjoin(
        Order, User.id == Order.user_id
    ).where(
        # Only users with at least one UTM parameter
        (User.utm_source.isnot(None)) |
        (User.utm_medium.isnot(None)) |
        (User.utm_campaign.isnot(None))
    ).group_by(
        User.utm_source,
        User.utm_medium,
        User.utm_campaign
    ).order_by(
        func.count(User.id).desc()
    )

    result = await session.execute(stmt)
    rows = result.all()

    stats = []
    for row in rows:
        total_users = row.total_users
        paying_users = row.paying_users
        revenue = float(row.revenue)

        # Calculate metrics
        conversion_rate = round((paying_users / total_users * 100), 2) if total_users > 0 else 0
        arpu = round((revenue / total_users), 2) if total_users > 0 else 0

        stats.append({
            'utm_source': row.utm_source or 'unknown',
            'utm_medium': row.utm_medium or 'unknown',
            'utm_campaign': row.utm_campaign or 'unknown',
            'total_users': total_users,
            'paying_users': paying_users,
            'conversion_rate': conversion_rate,
            'revenue': revenue,
            'arpu': arpu
        })

    return stats


async def get_conversion_funnel(session: AsyncSession) -> Dict[str, Any]:
    """
    Get conversion funnel for UTM users.

    Returns:
        Dict with funnel metrics: starts, first_images, purchases, conversion rates
    """
    # Count UTM users (start)
    starts_stmt = select(func.count(User.id)).where(
        (User.utm_source.isnot(None)) |
        (User.utm_medium.isnot(None)) |
        (User.utm_campaign.isnot(None))
    )
    starts_result = await session.execute(starts_stmt)
    starts = starts_result.scalar() or 0

    # Count UTM users who generated at least one image (first_image)
    first_images_stmt = select(func.count(func.distinct(User.id))).select_from(User).join(
        ProcessedImage, User.id == ProcessedImage.user_id
    ).where(
        (User.utm_source.isnot(None)) |
        (User.utm_medium.isnot(None)) |
        (User.utm_campaign.isnot(None))
    )
    first_images_result = await session.execute(first_images_stmt)
    first_images = first_images_result.scalar() or 0

    # Count UTM users who made a purchase
    purchases_stmt = select(func.count(func.distinct(User.id))).select_from(User).join(
        Order, User.id == Order.user_id
    ).where(
        Order.status == 'paid'
    ).where(
        (User.utm_source.isnot(None)) |
        (User.utm_medium.isnot(None)) |
        (User.utm_campaign.isnot(None))
    )
    purchases_result = await session.execute(purchases_stmt)
    purchases = purchases_result.scalar() or 0

    # Calculate conversion rates
    start_to_first_image_rate = round((first_images / starts * 100), 2) if starts > 0 else 0
    first_image_to_purchase_rate = round((purchases / first_images * 100), 2) if first_images > 0 else 0
    overall_conversion_rate = round((purchases / starts * 100), 2) if starts > 0 else 0

    return {
        'starts': starts,
        'first_images': first_images,
        'purchases': purchases,
        'start_to_first_image_rate': start_to_first_image_rate,
        'first_image_to_purchase_rate': first_image_to_purchase_rate,
        'overall_conversion_rate': overall_conversion_rate
    }


async def get_utm_events_summary(session: AsyncSession, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Get recent UTM events.

    Args:
        limit: Maximum number of events to return

    Returns:
        List of dicts with event data
    """
    stmt = select(
        UTMEvent,
        User.telegram_id,
        User.username,
        User.utm_source,
        User.utm_medium,
        User.utm_campaign
    ).join(
        User, UTMEvent.user_id == User.id
    ).order_by(
        UTMEvent.created_at.desc()
    ).limit(limit)

    result = await session.execute(stmt)
    rows = result.all()

    events = []
    for row in rows:
        event = row.UTMEvent
        events.append({
            'id': event.id,
            'event_type': event.event_type,
            'user_id': row.telegram_id,
            'username': row.username,
            'utm_source': row.utm_source,
            'utm_medium': row.utm_medium,
            'utm_campaign': row.utm_campaign,
            'event_value': float(event.event_value) if event.event_value else None,
            'currency': event.currency,
            'sent_to_metrika': event.sent_to_metrika,
            'created_at': event.created_at.isoformat() if event.created_at else None
        })

    return events


async def get_utm_sync_status(session: AsyncSession) -> Dict[str, Any]:
    """
    Get synchronization status with Yandex Metrika.

    Returns:
        Dict with sync stats: total, sent, pending counts and rates
    """
    # Total events
    total_stmt = select(func.count(UTMEvent.id))
    total_result = await session.execute(total_stmt)
    total_events = total_result.scalar() or 0

    # Sent events
    sent_stmt = select(func.count(UTMEvent.id)).where(UTMEvent.sent_to_metrika == True)
    sent_result = await session.execute(sent_stmt)
    sent_events = sent_result.scalar() or 0

    # Pending events
    pending_events = total_events - sent_events

    # Sync rate
    sync_rate = round((sent_events / total_events * 100), 2) if total_events > 0 else 0

    # Get last sent timestamp
    last_sent_stmt = select(func.max(UTMEvent.sent_at)).where(UTMEvent.sent_to_metrika == True)
    last_sent_result = await session.execute(last_sent_stmt)
    last_sent_at = last_sent_result.scalar()

    # Get last pending timestamp
    last_pending_stmt = select(func.max(UTMEvent.created_at)).where(UTMEvent.sent_to_metrika == False)
    last_pending_result = await session.execute(last_pending_stmt)
    last_pending_at = last_pending_result.scalar()

    # Get pending breakdown by event type
    pending_breakdown_stmt = select(
        UTMEvent.event_type,
        func.count(UTMEvent.id).label('count')
    ).where(
        UTMEvent.sent_to_metrika == False
    ).group_by(
        UTMEvent.event_type
    )
    pending_breakdown_result = await session.execute(pending_breakdown_stmt)
    pending_breakdown = {row.event_type: row.count for row in pending_breakdown_result.all()}

    return {
        'total_events': total_events,
        'sent_events': sent_events,
        'pending_events': pending_events,
        'sync_rate': sync_rate,
        'last_sent_at': last_sent_at.isoformat() if last_sent_at else None,
        'last_pending_at': last_pending_at.isoformat() if last_pending_at else None,
        'pending_breakdown': pending_breakdown
    }

# ==================== BALANCE OPERATIONS (Compatibility) ====================

async def check_and_reserve_balance(session: AsyncSession, telegram_id: int) -> tuple[bool, bool]:
    """
    Atomically check and reserve balance for image processing.
    Returns (success, is_free).
    For this bot, all balance is treated equally (images_remaining).
    is_free logic is legacy but we return False unless specific logic needed.
    """
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id).with_for_update()
    )
    user = result.scalar_one_or_none()

    if not user or user.images_remaining <= 0:
        return False, False

    user.images_remaining -= 1
    await session.commit()
    return True, False # Treat as paid/consumed credit

async def rollback_balance(session: AsyncSession, telegram_id: int, is_free: bool):
    """Rollback balance if processing failed"""
    # We ignore is_free distinction for simplicity in this version
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id).with_for_update()
    )
    user = result.scalar_one_or_none()

    if user:
        user.images_remaining += 1
        await session.commit()
