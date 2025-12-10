"User Handlers"
import logging
import asyncio
from aiogram import Router, F, Bot
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, CallbackQuery, InputMediaPhoto, BufferedInputFile
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.states import PhotoshootStates
from app.keyboards.inline import (
    get_aspect_ratio_keyboard,
    get_style_selection_keyboard,
    get_style_preview_keyboard,
    get_saved_styles_keyboard,
    get_post_generation_keyboard,
    get_confirm_save_style_keyboard,
    get_buy_packages_keyboard
)
from app.keyboards.user_kb import get_packages_keyboard, get_referral_menu, get_cancel_keyboard, get_main_menu
from app.services.prompt_generator import PromptGenerator
from app.services.image_processor import ImageProcessor
from app.services.style_manager import StyleManager
from app.database.crud import (
    get_or_create_user,
    update_user_images_count,
    create_processed_image,
    get_user_balance,
    get_all_packages,
    get_user_detailed_stats
)
from app.utils.message_helpers import safe_edit_text
from app.config import settings

logger = logging.getLogger(__name__)
router = Router()

prompt_generator = PromptGenerator()
image_processor = ImageProcessor()

@router.message(Command("start"))
async def cmd_start(message: Message, session: AsyncSession, state: FSMContext, command: Command = None):
    # Parse referral code if present
    referral_code = None
    if command and command.args and command.args.startswith("ref_"):
        referral_code = command.args.replace("ref_", "")

    # Create user (passing referral code logic to CRUD or handling it here)
    # We'll handle it here for simplicity: check if new user, if so, link to referrer
    
    # Check if user exists first to know if it's a new registration
    # (Simplified: get_or_create checks, but we need to pass referrer if new)
    
    # We can pass referral_code to get_or_create_user if we update it, 
    # or just let get_or_create return the user and 'created' flag.
    # Since we can't easily change get_or_create signature safely without checking usages,
    # let's assume get_or_create just gets/creates.
    
    user = await get_or_create_user(
        session=session,
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name
    )
    
    # If user was just created (or has no referrer) and we have a code
    if referral_code and not user.referred_by_id and str(user.telegram_id) != referral_code:
        # Find referrer
        from sqlalchemy import select
        from app.database.models import User
        
        result = await session.execute(select(User).where(User.referral_code == referral_code))
        referrer = result.scalar_one_or_none()
        
        if not referrer:
             # Try matching by telegram_id if code didn't match
             result = await session.execute(select(User).where(User.telegram_id == int(referral_code) if referral_code.isdigit() else 0))
             referrer = result.scalar_one_or_none()
             
        if referrer:
            user.referred_by_id = referrer.id
            referrer.total_referrals += 1
            # Give reward to referrer?
            referrer.images_remaining += settings.REFERRAL_REWARD_START
            await session.commit()
            
            try:
                await message.bot.send_message(
                    referrer.telegram_id,
                    f"🎉 <b>Новый реферал!</b>\n\n"
                    f"Пользователь {message.from_user.full_name} зарегистрировался по вашей ссылке.\n"
                    f"Вам начислено +{settings.REFERRAL_REWARD_START} фотосессия!"
                )
            except:
                pass

    welcome_text = f"""
🎨 <b>Добро пожаловать в Product Photoshoot Bot!</b>

Я помогу создать профессиональную фотосессию вашего товара в разных стилях! 📸

<b>Как это работает:</b>
1️⃣ Загрузите фото товара
2️⃣ Выберите пропорции
3️⃣ Выберите или сгенерируйте стили
4️⃣ Получите 4 профессиональных фото

У вас есть <b>{user.images_remaining} бесплатных фотосессий</b>! 🎁

Просто отправьте фото товара, чтобы начать! 📷
"""
    await message.answer(welcome_text, parse_mode="HTML", reply_markup=get_main_menu())

@router.message(F.text == "📸 Создать фотосессию товара")
async def create_photoshoot_msg(message: Message, state: FSMContext):
    await message.answer("📸 Отправьте фото вашего товара (как фото или файл).")
    await state.set_state(PhotoshootStates.waiting_for_product_photo)

@router.message(F.text == "👥 Реферальная программа")
async def referral_handler(message: Message, session: AsyncSession, bot: Bot):
    """Handle referral program menu"""
    user = await get_or_create_user(session, message.from_user.id)
    
    # Generate referral code if not exists
    if not user.referral_code:
        # Use simple hex of ID or just ID if preferred, but let's stick to unique string
        import uuid
        user.referral_code = str(user.telegram_id) # Simple code = telegram_id
        await session.commit()
    
    # Get stats
    referrals_count = user.total_referrals
    
    bot_info = await bot.get_me()
    referral_link = f"https://t.me/{bot_info.username}?start=ref_{user.referral_code}"
    
    await message.answer(
        f"👥 <b>Реферальная программа</b>\n\n"
        f"Приглашайте друзей и получайте бонусы!\n\n"
        f"🔗 <b>Ваша статистика:</b>\n"
        f"👥 Приглашено друзей: <b>{referrals_count}</b>\n"
        f"\n"
        f"🎁 <b>Бонусы:</b>\n"
        f"• +{settings.REFERRAL_REWARD_START} фотосессия за каждого друга\n"
        f"• {settings.REFERRAL_REWARD_PURCHASE_PERCENT}% от их покупок\n\n"
        f"👇 <b>Ваша ссылка для приглашения:</b>\n"
        f"<code>{referral_link}</code>",
        parse_mode="HTML",
        reply_markup=get_referral_menu(bot_info.username, user.referral_code)
    )

@router.callback_query(F.data.startswith("copy_referral:"))
async def copy_referral_handler(callback: CallbackQuery):
    """Handle copy referral link action"""
    code = callback.data.split(":")[1]
    bot_info = await callback.bot.get_me()
    link = f"https://t.me/{bot_info.username}?start=ref_{code}"
    
    await callback.answer("Ссылка скопирована!", show_alert=False)
    # Send as text so user can copy
    await callback.message.answer(f"<code>{link}</code>", parse_mode="HTML")

@router.message(F.text == "ℹ️ Информация")
async def info_handler(message: Message):
    from app.keyboards.user_kb import get_info_menu
    await message.answer(
        "ℹ️ <b>Информация</b>\n\n"
        "Выберите интересующий раздел:",
        parse_mode="HTML",
        reply_markup=get_info_menu()
    )

@router.callback_query(F.data == "info_how_it_works")
async def info_how_it_works_handler(callback: CallbackQuery):
    """Show 'How it works' information"""
    from app.data import get_info_text
    from app.keyboards.user_kb import get_back_to_info_keyboard

    await callback.message.edit_text(
        get_info_text("how_it_works"),
        parse_mode="HTML",
        reply_markup=get_back_to_info_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "info_faq")
async def info_faq_handler(callback: CallbackQuery):
    """Show FAQ information"""
    from app.data import get_info_text
    from app.keyboards.user_kb import get_back_to_info_keyboard

    await callback.message.edit_text(
        get_info_text("faq"),
        parse_mode="HTML",
        reply_markup=get_back_to_info_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "info_offer")
async def info_offer_handler(callback: CallbackQuery):
    """Show public offer (terms of service)"""
    from app.data import get_info_text
    from app.keyboards.user_kb import get_back_to_info_keyboard

    await callback.message.edit_text(
        get_info_text("offer"),
        parse_mode="HTML",
        reply_markup=get_back_to_info_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "info_refund")
async def info_refund_handler(callback: CallbackQuery):
    """Show refund policy"""
    from app.data import get_info_text
    from app.keyboards.user_kb import get_back_to_info_keyboard

    await callback.message.edit_text(
        get_info_text("refund"),
        parse_mode="HTML",
        reply_markup=get_back_to_info_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "info_privacy")
async def info_privacy_handler(callback: CallbackQuery):
    """Show privacy policy"""
    from app.data import get_info_text
    from app.keyboards.user_kb import get_back_to_info_keyboard

    await callback.message.edit_text(
        get_info_text("privacy"),
        parse_mode="HTML",
        reply_markup=get_back_to_info_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "back_to_info")
async def back_to_info_handler(callback: CallbackQuery):
    """Go back to info menu"""
    from app.keyboards.user_kb import get_info_menu

    await callback.message.edit_text(
        "ℹ️ <b>Информация</b>\n\n"
        "Выберите интересующий раздел:",
        parse_mode="HTML",
        reply_markup=get_info_menu()
    )
    await callback.answer()

@router.message(F.text == "📊 Мой баланс")
async def balance_handler(message: Message, session: AsyncSession):
    from datetime import datetime

    user = await get_or_create_user(session, message.from_user.id)
    balance = await get_user_balance(session, message.from_user.id)
    stats = await get_user_detailed_stats(session, message.from_user.id)

    # Build balance message
    text = f"📊 <b>Ваш баланс и статистика</b>\n\n"

    # Current balance
    text += f"💎 <b>Доступно фотосессий:</b> <b>{balance['total']}</b>\n"
    text += f"<i>(1 фотосессия = 4 изображения)</i>\n\n"

    # Usage stats
    text += f"📈 <b>Ваша статистика:</b>\n"
    text += f"🎬 Проведено фотосессий: <b>{stats['photoshoots_used']}</b>\n"
    text += f"🖼️ Сгенерировано изображений: <b>{stats['images_generated']}</b>\n"
    text += f"🎨 Сохранено стилей: <b>{stats['saved_styles']}</b>\n"

    # Total spent
    if stats['total_spent'] > 0:
        text += f"💰 Всего потрачено: <b>{stats['total_spent']:.0f}₽</b>\n"

    # Top styles
    if stats['top_styles']:
        text += f"\n🏆 <b>Любимые стили:</b>\n"
        for i, style in enumerate(stats['top_styles'], 1):
            text += f"   {i}. {style['name']} ({style['count']}x)\n"

    # Aspect ratios
    if stats['aspect_ratios']:
        text += f"\n📐 <b>Используемые пропорции:</b>\n"
        for ratio, count in list(stats['aspect_ratios'].items())[:3]:
            text += f"   • {ratio} — {count} фото\n"

    # Recent activity
    if stats['recent_activity']:
        days_ago = (datetime.utcnow() - stats['recent_activity']).days
        if days_ago == 0:
            activity_text = "сегодня"
        elif days_ago == 1:
            activity_text = "вчера"
        else:
            activity_text = f"{days_ago} дн. назад"
        text += f"\n⏱️ Последняя генерация: {activity_text}\n"

    # Call to action
    if balance['total'] == 0:
        text += f"\n💎 Купите пакет для продолжения!"
    else:
        text += f"\n✅ Готовы творить!"

    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=get_buy_packages_keyboard() if balance['total'] == 0 else None
    )

@router.message(F.photo | F.document, StateFilter(None, PhotoshootStates.waiting_for_product_photo))
async def handle_product_photo(message: Message, session: AsyncSession, state: FSMContext, bot: Bot):
    user = await get_or_create_user(session, message.from_user.id)
    
    if user.images_remaining <= 0:
        await message.answer("😔 Недостаточно фотосессий! Купите пакет.", reply_markup=get_buy_packages_keyboard())
        return

    msg = await message.answer("⏳ Загружаю фото...")
    
    try:
        if message.photo:
            file_id = message.photo[-1].file_id
        else:
            file_id = message.document.file_id
            
        file = await bot.get_file(file_id)
        photo_bytes = await bot.download_file(file.file_path)
        photo_data = photo_bytes.read()
        
        await state.update_data(product_image_bytes=photo_data, product_image_file_id=file_id)
        await msg.edit_text("✅ Фото получено!\nВыберите пропорции:", reply_markup=get_aspect_ratio_keyboard())
        await state.set_state(PhotoshootStates.selecting_aspect_ratio)
        
    except Exception as e:
        logger.error(f"Error: {e}")
        await msg.edit_text("❌ Ошибка загрузки. Попробуйте снова.")

@router.callback_query(F.data.startswith("aspect_ratio:"))
async def select_aspect_ratio(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    ratio = callback.data.split(":")[1]
    await state.update_data(aspect_ratio=ratio)
    await callback.message.edit_text(
        f"✅ Пропорции: <b>{ratio}</b>\nВыберите метод создания стилей:",
        reply_markup=get_style_selection_keyboard(), parse_mode="HTML"
    )
    await state.set_state(PhotoshootStates.selecting_styles_method)

@router.callback_query(F.data == "styles:analyze")
async def analyze_styles(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    msg = await callback.message.edit_text("🔍 Анализирую товар...")
    data = await state.get_data()
    
    res = await prompt_generator.generate_styles_from_description("product image", data["aspect_ratio"])
    
    if not res["success"]:
        await msg.edit_text("❌ Ошибка генерации стилей.", reply_markup=get_style_selection_keyboard())
        return
        
    await state.update_data(product_name=res["product_name"], styles=res["styles"])

    text = _format_styles_preview(res["styles"])
    await msg.edit_text(
        f"✨ <b>Предложенные стили:</b>\n📦 {res['product_name']}\n\n{text}",
        reply_markup=get_style_preview_keyboard(True, res["product_name"]), parse_mode="HTML"
    )
    await state.set_state(PhotoshootStates.reviewing_suggested_styles)

@router.callback_query(F.data == "styles:random")
async def random_styles(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    msg = await callback.message.edit_text("🎲 Генерирую случайные стили...")
    data = await state.get_data()
    
    res = await prompt_generator.generate_styles_from_description("product image", data["aspect_ratio"], random=True)
    
    if not res["success"]:
        await msg.edit_text("❌ Ошибка.", reply_markup=get_style_selection_keyboard())
        return
        
    await state.update_data(product_name=res["product_name"], styles=res["styles"])
    text = _format_styles_preview(res["styles"])
    await msg.edit_text(
        f"🎲 <b>Случайные стили:</b>\n📦 {res['product_name']}\n\n{text}",
        reply_markup=get_style_preview_keyboard(True, res["product_name"]), parse_mode="HTML"
    )
    await state.set_state(PhotoshootStates.reviewing_suggested_styles)

@router.callback_query(F.data == "styles:saved")
async def show_saved(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    await callback.answer()
    styles = await StyleManager.get_user_styles(session, callback.from_user.id)
    if not styles:
        await callback.message.answer("Нет сохраненных стилей", show_alert=True)
        return
    
    text = "\n".join([f"{i+1}. {s['name']} ({s['aspect_ratio']})" for i, s in enumerate(styles)])
    await callback.message.edit_text(
        f"📁 <b>Сохраненные стили:</b>\n\n{text}",
        reply_markup=get_saved_styles_keyboard(styles), parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("apply_style:"))
async def apply_style(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    await callback.answer()
    pid = int(callback.data.split(":")[1])
    style = await StyleManager.apply_style(session, callback.from_user.id, pid)
    if not style:
        await callback.message.answer("Ошибка", show_alert=True)
        return
        
    await state.update_data(product_name=style["product_name"], aspect_ratio=style["aspect_ratio"], styles=style["styles"])
    text = _format_styles_preview(style["styles"])
    await callback.message.edit_text(
        f"✅ <b>Стиль применен:</b>\n📦 {style['product_name']}\n\n{text}",
        reply_markup=get_style_preview_keyboard(False, style["product_name"]), parse_mode="HTML"
    )
    await state.set_state(PhotoshootStates.reviewing_suggested_styles)

@router.callback_query(F.data == "confirm_generation")
async def confirm_gen(callback: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot):
    await callback.answer()
    try:
        user = await get_or_create_user(session, callback.from_user.id)
        if user.images_remaining < 1:
            await callback.message.edit_text("❌ Недостаточно средств!", reply_markup=get_buy_packages_keyboard())
            return

        data = await state.get_data()
        styles = data["styles"]
        styles_count = len(styles)
        aspect_ratio = data.get("aspect_ratio", "1:1")
        product_name = data.get("product_name", "Товар")

        # Show detailed generation parameters to user
        params_text = f"🎨 <b>Параметры генерации:</b>\n\n"
        params_text += f"📦 Товар: <b>{product_name}</b>\n"
        params_text += f"📊 Пропорции: <b>{aspect_ratio}</b>\n"
        params_text += f"🖼️ Количество фото: <b>{styles_count}</b>\n\n"
        params_text += f"🎭 <b>Стили:</b>\n"
        for i, style in enumerate(styles, 1):
            params_text += f"{i}. {style['style_name']}\n"

        # Show parameters
        await callback.message.edit_text(params_text, parse_mode="HTML")
        await asyncio.sleep(2)  # Give user time to see parameters

        msg = await callback.message.edit_text(
            f"🎨 Генерирую {styles_count} фото...\n⏳ Ожидайте ~1 мин"
        )

        res = await image_processor.generate_photoshoot(
            data["product_image_bytes"], data["styles"], data["aspect_ratio"], bot, user, msg
        )

        if not res["success"]:
            await msg.edit_text(f"❌ Ошибка: {res.get('error', 'Неизвестная ошибка')}")
            return

        # Deduct balance only if generation was successful
        await update_user_images_count(session, user.id, -1)

        media = []
        successful_count = 0
        failed_count = 0

        style_names = []
        for i, img in enumerate(res["images"]):
            if img.get("success"):
                try:
                    # Wrap bytes in BufferedInputFile for aiogram
                    input_file = BufferedInputFile(
                        img["image_bytes"],
                        filename=f"photoshoot_{i}_{img['style_name']}.png"
                    )
                    media.append(InputMediaPhoto(media=input_file))
                    await create_processed_image(session, user.id, None, img["style_name"], img["prompt"], data["aspect_ratio"])
                    style_names.append(img['style_name'])
                    successful_count += 1
                except Exception as e:
                    logger.error(f"Error preparing image {i}: {e}", exc_info=True)
                    failed_count += 1
            else:
                failed_count += 1

        await msg.delete()

        if media:
            try:
                await callback.message.answer_media_group(media)

                # Create summary message with all styles
                summary = "✅ <b>Готово!</b>\n\n"
                summary += f"📊 <b>Результаты генерации:</b>\n"
                summary += f"✅ Успешно: {successful_count}\n"
                if failed_count > 0:
                    summary += f"❌ Ошибок: {failed_count}\n"
                summary += f"📐 Пропорции: {aspect_ratio}\n"

                if style_names:
                    summary += f"\n🎨 <b>Стили:</b>\n"
                    for idx, style in enumerate(style_names, 1):
                        summary += f"{idx}. {style}\n"

                await callback.message.answer(
                    summary,
                    reply_markup=get_post_generation_keyboard(user.images_remaining > 0),
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Error sending media group: {e}", exc_info=True)
                await callback.message.answer(
                    f"❌ Ошибка отправки изображений: {str(e)}\n"
                    f"Сгенерировано: {successful_count}, Ошибок: {failed_count}"
                )
        else:
            await callback.message.answer(
                "❌ К сожалению, не удалось сгенерировать ни одного изображения.\n"
                "Попробуйте еще раз или измените параметры.",
                reply_markup=get_post_generation_keyboard(user.images_remaining > 0)
            )

        await state.update_data(last_generated=True)
        await state.set_state(PhotoshootStates.generating_photoshoot)

    except Exception as e:
        logger.error(f"Critical error in confirm_gen: {e}", exc_info=True)
        try:
            await callback.message.answer(
                "❌ Произошла критическая ошибка. Пожалуйста, попробуйте снова или обратитесь в поддержку."
            )
        except:
            pass

@router.callback_query(F.data == "save_style")
async def save_style_prompt(callback: CallbackQuery, state: FSMContext):
    """
    Handler for 'Save Style' button.
    Works for both preview stage and post-generation stage.
    """
    await callback.answer()
    data = await state.get_data()
    
    # Check if we have style data to save
    if not data.get("styles") and not data.get("last_generated"):
         await callback.message.answer("Нет данных стиля для сохранения", show_alert=True)
         return

    await callback.message.answer(
        "💾 <b>Сохранение стиля</b>\n\n"
        "Введите название для этого стиля (например: 'Мой любимый неон'):",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(PhotoshootStates.saving_style_name)

@router.message(StateFilter(PhotoshootStates.saving_style_name))
async def save_style_name(message: Message, state: FSMContext, session: AsyncSession):
    logger.info(f"User {message.from_user.id} saving style name: {message.text}")
    name = message.text
    if len(name) > 30:
        await message.answer("⚠️ Название слишком длинное. Максимум 30 символов.")
        return

    data = await state.get_data()
    
    # Extract style data depending on where we are coming from
    # If post-generation, data['styles'] should hold the style used.
    # If multiple styles were generated, we might need to know which one.
    # For now, assuming single style flow or taking the first/active one.
    
    # In generate_photoshoot, we pass 'styles' list.
    styles_to_save = data.get("styles")
    
    if not styles_to_save:
        logger.error("No styles found in state during save")
        await message.answer("❌ Ошибка: данные стиля потеряны.")
        await state.clear()
        return

    res = await StyleManager.save_style(
        session, message.from_user.id, name, data.get("product_name", "Product"), data.get("aspect_ratio", "1:1"), styles_to_save
    )

    if res["success"]:
        # Check context: are we working with a photo?
        has_photo = bool(data.get("product_image_bytes"))
        has_generated = data.get("last_generated")

        if has_generated:
            # After generation - show post-generation menu
            markup = get_post_generation_keyboard(True)
            await message.answer(f"✅ Стиль '<b>{name}</b>' успешно сохранен!", parse_mode="HTML", reply_markup=markup)
            await state.set_state(PhotoshootStates.generating_photoshoot)
        elif has_photo:
            # Working with photo but haven't generated yet - return to style preview
            product_name = data.get("product_name", "Product")
            styles = data.get("styles", [])
            text = _format_styles_preview(styles)

            await message.answer(
                f"✅ Стиль '<b>{name}</b>' успешно сохранен!\n\n"
                f"✨ <b>Текущие стили:</b>\n📦 {product_name}\n\n{text}",
                parse_mode="HTML",
                reply_markup=get_style_preview_keyboard(True, product_name)
            )
            await state.set_state(PhotoshootStates.reviewing_suggested_styles)
        else:
            # No photo context - return to style selection
            markup = get_style_selection_keyboard()
            await message.answer(f"✅ Стиль '<b>{name}</b>' успешно сохранен!", parse_mode="HTML", reply_markup=markup)
            await state.set_state(PhotoshootStates.selecting_styles_method)
    else:
        logger.error(f"Failed to save style: {res['error']}")
        await message.answer(f"❌ Ошибка: {res['error']}")

@router.callback_query(F.data == "cancel_action")
async def cancel_handler(callback: CallbackQuery, state: FSMContext):
    """Handle generic cancel action"""
    await state.clear()
    await callback.message.edit_text("❌ Действие отменено.")
    await callback.answer()

def _format_styles_preview(styles):
    return "\n\n".join([f"{i+1}. <b>{s['style_name']}</b>" for i, s in enumerate(styles)])

@router.callback_query(F.data == "back_to_ratio")
async def back_ratio(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await safe_edit_text(callback.message, "Выберите пропорции:", reply_markup=get_aspect_ratio_keyboard())
    await state.set_state(PhotoshootStates.selecting_aspect_ratio)

@router.callback_query(F.data == "back_to_style_selection")
async def back_styles(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    await safe_edit_text(callback.message, f"✅ Пропорции: {data['aspect_ratio']}\nВыберите метод:", reply_markup=get_style_selection_keyboard())
    await state.set_state(PhotoshootStates.selecting_styles_method)

@router.callback_query(F.data == "new_photoshoot")
async def new_photoshoot(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer("📸 Отправьте фото товара.")
    await state.clear()
    await state.set_state(PhotoshootStates.waiting_for_product_photo)

@router.message(F.text == "💎 Купить пакет")
async def show_packages_msg(message: Message, session: AsyncSession):
    """Show available packages for purchase (message handler)"""
    try:
        packages = await get_all_packages(session)

        if not packages:
            await message.answer("Пакеты временно недоступны")
            return

        # Convert to dict format expected by keyboard
        packages_dict = [
            {
                'id': p.id,
                'name': p.name,
                'images_count': p.photoshoots_count,  # Note: photoshoots_count in DB
                'price_rub': float(p.price_rub)
            }
            for p in packages
        ]

        text = (
            "💎 <b>Доступные пакеты</b>\n\n"
            "Выберите пакет для покупки:\n"
        )

        await message.answer(
            text,
            parse_mode="HTML",
            reply_markup=get_packages_keyboard(packages_dict)
        )
    except Exception as e:
        logger.error(f"Error showing packages: {e}", exc_info=True)
        await message.answer("Ошибка загрузки пакетов")

@router.callback_query(F.data == "show_packages")
async def show_packages(callback: CallbackQuery, session: AsyncSession):
    """Show available packages for purchase"""
    try:
        packages = await get_all_packages(session)

        if not packages:
            await callback.answer("Пакеты временно недоступны", show_alert=True)
            return

        # Convert to dict format expected by keyboard
        packages_dict = [
            {
                'id': p.id,
                'name': p.name,
                'images_count': p.photoshoots_count,  # Note: photoshoots_count in DB
                'price_rub': float(p.price_rub)
            }
            for p in packages
        ]

        text = (
            "💎 <b>Доступные пакеты</b>\n\n"
            "Выберите пакет для покупки:\n"
        )

        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=get_packages_keyboard(packages_dict)
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Error showing packages: {e}", exc_info=True)
        await callback.answer("Ошибка загрузки пакетов", show_alert=True)

@router.callback_query(F.data == "buy_package")
async def buy_package_redirect(callback: CallbackQuery, session: AsyncSession):
    """Redirect to show packages (alias for show_packages)"""
    await show_packages(callback, session)

@router.callback_query(F.data == "profile")
async def show_profile(callback: CallbackQuery, session: AsyncSession):
    """Show user profile with detailed statistics"""
    try:
        from datetime import datetime

        user = await get_or_create_user(session, callback.from_user.id)
        balance = await get_user_balance(session, callback.from_user.id)
        stats = await get_user_detailed_stats(session, callback.from_user.id)

        # Build profile text
        text = f"👤 <b>Ваш профиль</b>\n\n"

        # User info
        text += f"🆔 ID: <code>{user.telegram_id}</code>\n"
        text += f"👤 Имя: {callback.from_user.full_name}\n"
        if callback.from_user.username:
            text += f"📱 Username: @{callback.from_user.username}\n"
        text += f"\n"

        # Balance
        text += f"💎 <b>Баланс:</b> <b>{balance['total']}</b> фотосессий\n"
        text += f"<i>(1 фотосессия = 4 изображения)</i>\n\n"

        # Detailed statistics
        text += f"📈 <b>Статистика:</b>\n"
        text += f"🎬 Проведено фотосессий: <b>{stats['photoshoots_used']}</b>\n"
        text += f"🖼️ Сгенерировано изображений: <b>{stats['images_generated']}</b>\n"
        text += f"🎨 Сохранено стилей: <b>{stats['saved_styles']}</b>\n"

        # Financial stats
        if stats['total_spent'] > 0:
            text += f"💰 Всего потрачено: <b>{stats['total_spent']:.0f}₽</b>\n"

        # Top styles
        if stats['top_styles']:
            text += f"\n🏆 <b>Топ-стили:</b>\n"
            for i, style in enumerate(stats['top_styles'], 1):
                text += f"{i}. {style['name']} — {style['count']} раз\n"

        # Aspect ratios
        if stats['aspect_ratios']:
            text += f"\n📐 <b>Пропорции:</b>\n"
            for ratio, count in list(stats['aspect_ratios'].items())[:3]:
                text += f"• {ratio}: {count} фото\n"

        # Activity
        if stats['recent_activity']:
            days_ago = (datetime.utcnow() - stats['recent_activity']).days
            if days_ago == 0:
                activity_text = "сегодня"
            elif days_ago == 1:
                activity_text = "вчера"
            else:
                activity_text = f"{days_ago} дней назад"
            text += f"\n⏱️ Последняя активность: {activity_text}"

        await safe_edit_text(callback.message, text, parse_mode="HTML")
        await callback.answer()
    except Exception as e:
        logger.error(f"Error showing profile: {e}", exc_info=True)
        await callback.answer("Ошибка загрузки профиля", show_alert=True)

@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext):
    """Go back to main menu"""
    await state.clear()
    await callback.message.edit_text(
        "Главное меню",
        reply_markup=None
    )
    await callback.message.answer(
        "Используйте кнопки меню для навигации",
        reply_markup=get_main_menu()
    )
    await callback.answer()