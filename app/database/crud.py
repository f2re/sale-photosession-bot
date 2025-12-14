from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import select, func, and_, update, desc, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import uuid

from .models import User, Package, Order, ProcessedImage, SupportTicket, SupportMessage, Admin, UTMEvent, ReferralReward, StylePreset


# ==================== USER OPERATIONS ====================

async def get_or_create_user(
    session: AsyncSession,
    telegram_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    free_photoshoots_count: int = 2,
    utm_source: Optional[str] = None,
    utm_medium: Optional[str] = None,
    utm_campaign: Optional[str] = None,
    utm_content: Optional[str] = None,
    utm_term: Optional[str] = None
) -> User:
    """Get existing user or create new one"""
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
    aspect_ratio: str
) -> ProcessedImage:
    """Create processed image record"""
    image = ProcessedImage(
        user_id=user_id,
        telegram_file_id=telegram_file_id,
        style_name=style_name,
        prompt_used=prompt_used,
        aspect_ratio=aspect_ratio,
        is_free=False # Assuming all are "paid" with credits
    )
    session.add(image)
    await session.commit()
    return image


async def save_processed_image(session: AsyncSession, user_id: int, telegram_file_id: str, 
                               original_file_id: str, prompt_used: str, is_free: bool = False):
    """Legacy method wrapper"""
    # Adapted for compatibility if needed, but prefer create_processed_image
    await create_processed_image(session, user_id, telegram_file_id, "Legacy", prompt_used, "1:1")


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
    users = (await session.execute(select(func.count(User.id)))).scalar()
    processed = (await session.execute(select(func.count(ProcessedImage.id)))).scalar()
    revenue = (await session.execute(select(func.sum(Order.amount)).where(Order.status == "paid"))).scalar() or 0

    # Active orders = all non-canceled and non-paid orders (pending, waiting_payment, etc)
    active_orders = (await session.execute(
        select(func.count(Order.id)).where(
            Order.status.notin_(["paid", "canceled", "cancelled", "refunded"])
        )
    )).scalar()

    # Paid orders count
    paid_orders = (await session.execute(
        select(func.count(Order.id)).where(Order.status == "paid")
    )).scalar()

    # Free vs paid images
    free_images = (await session.execute(
        select(func.count(ProcessedImage.id)).where(ProcessedImage.is_free == True)
    )).scalar() or 0

    paid_images = (await session.execute(
        select(func.count(ProcessedImage.id)).where(ProcessedImage.is_free == False)
    )).scalar() or 0

    open_tickets = (await session.execute(
        select(func.count(SupportTicket.id)).where(
            SupportTicket.status.in_(["open", "in_progress"])
        )
    )).scalar()

    return {
        "total_users": users,
        "total_processed": processed,
        "revenue": float(revenue),
        "active_orders": active_orders,
        "open_tickets": open_tickets,
        "free_images_processed": free_images,
        "paid_images_processed": paid_images,
        "paid_orders": paid_orders
    }


async def get_user_detailed_stats(session: AsyncSession, telegram_id: int) -> dict:
    """
    Get detailed user statistics for profile display

    Returns:
        dict with user stats including:
        - photoshoots_used: number of photoshoots completed
        - images_generated: total images generated
        - saved_styles: number of saved style presets
        - top_styles: most used styles
        - aspect_ratios: usage breakdown by ratio
        - recent_activity: date of last generation
    """
    from sqlalchemy import desc, case, func as sql_func, extract

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

    # Count total images generated - ACCURATE COUNT from ProcessedImage table
    images_count_result = await session.execute(
        select(func.count(ProcessedImage.id)).where(
            ProcessedImage.user_id == user.id
        )
    )
    images_generated = images_count_result.scalar() or 0

    # Count photoshoots - group images by creation time (within 1 minute = same photoshoot)
    # PostgreSQL approach: Use date_trunc to group by minute
    try:
        # Try PostgreSQL date_trunc
        photoshoots_result = await session.execute(
            select(func.count(func.distinct(func.date_trunc('minute', ProcessedImage.created_at))))
            .where(ProcessedImage.user_id == user.id)
        )
        photoshoots_used = photoshoots_result.scalar() or 0
    except Exception:
        # Fallback: estimate based on 4 images per photoshoot
        photoshoots_used = max(1, images_generated // 4) if images_generated > 0 else 0

    # Count saved style presets
    saved_styles_count = (await session.execute(
        select(func.count(StylePreset.id)).where(
            StylePreset.user_id == user.id,
            StylePreset.is_active == True
        )
    )).scalar() or 0

    # Get top 3 most used styles
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

    # Get aspect ratio breakdown
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

    # Get recent activity (last generated image)
    recent_activity_result = await session.execute(
        select(ProcessedImage.created_at)
        .where(ProcessedImage.user_id == user.id)
        .order_by(desc(ProcessedImage.created_at))
        .limit(1)
    )
    recent_activity = recent_activity_result.scalar_one_or_none()

    # Calculate total spent
    total_spent_result = await session.execute(
        select(func.sum(Order.amount))
        .where(
            Order.user_id == user.id,
            Order.status == "paid"
        )
    )
    total_spent = total_spent_result.scalar() or 0.0

    return {
        "photoshoots_used": photoshoots_used,
        "images_generated": images_generated,
        "saved_styles": saved_styles_count,
        "top_styles": top_styles,
        "aspect_ratios": aspect_ratios,
        "recent_activity": recent_activity,
        "total_spent": float(total_spent)
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
# (Minimal implementation for compatibility)
async def get_utm_statistics(session: AsyncSession) -> List: return []
async def get_conversion_funnel(session: AsyncSession) -> Dict: return {}
async def get_utm_events_summary(session: AsyncSession, limit: int = 100) -> List: return []
async def get_utm_sync_status(session: AsyncSession) -> Dict: return {'total_events': 0, 'sent_events': 0, 'pending_events': 0, 'sync_rate': 0}

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