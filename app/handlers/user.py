"User Handlers"
import logging
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
from app.keyboards.user_kb import get_packages_keyboard
from app.keyboards.reply import get_main_menu
from app.services.prompt_generator import PromptGenerator
from app.services.image_processor import ImageProcessor
from app.services.style_manager import StyleManager
from app.database.crud import (
    get_or_create_user,
    update_user_images_count,
    create_processed_image,
    get_user_balance,
    get_all_packages
)
from app.config import settings

logger = logging.getLogger(__name__)
router = Router()

prompt_generator = PromptGenerator()
image_processor = ImageProcessor()

@router.message(Command("start"))
async def cmd_start(message: Message, session: AsyncSession, state: FSMContext):
    user = await get_or_create_user(
        session=session,
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name
    )
    
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

@router.message(F.text == "📸 Создать фотосессию")
async def create_photoshoot_msg(message: Message):
    await message.answer("📸 Отправьте фото вашего товара (как фото или файл).")

@router.message(F.text == "📊 Баланс")
async def balance_handler(message: Message, session: AsyncSession):
    balance = await get_user_balance(session, message.from_user.id)
    await message.answer(
        f"📊 <b>Ваш баланс:</b>\n\n"
        f"📸 Фотосессий: <b>{balance['total']}</b>\n"
        f"(1 фотосессия = 4 изображения)\n\n"
        f"{'💎 Купите пакет для пополнения!' if balance['total'] == 0 else '✅ Можно творить!'}",
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
        reply_markup=get_style_preview_keyboard(True), parse_mode="HTML"
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
        f"🎲 <b>Случайные стили:</b>\n\n{text}",
        reply_markup=get_style_preview_keyboard(True), parse_mode="HTML"
    )
    await state.set_state(PhotoshootStates.reviewing_suggested_styles)

@router.callback_query(F.data == "styles:saved")
async def show_saved(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    styles = await StyleManager.get_user_styles(session, callback.from_user.id)
    if not styles:
        await callback.answer("Нет сохраненных стилей", show_alert=True)
        return
    
    text = "\n".join([f"{i+1}. {s['name']} ({s['aspect_ratio']})" for i, s in enumerate(styles)])
    await callback.message.edit_text(
        f"📁 <b>Сохраненные стили:</b>\n\n{text}",
        reply_markup=get_saved_styles_keyboard(styles), parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("apply_style:"))
async def apply_style(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    pid = int(callback.data.split(":")[1])
    style = await StyleManager.apply_style(session, callback.from_user.id, pid)
    if not style:
        await callback.answer("Ошибка", show_alert=True)
        return
        
    await state.update_data(product_name=style["product_name"], aspect_ratio=style["aspect_ratio"], styles=style["styles"])
    text = _format_styles_preview(style["styles"])
    await callback.message.edit_text(
        f"✅ <b>Стиль применен:</b>\n\n{text}",
        reply_markup=get_style_preview_keyboard(False), parse_mode="HTML"
    )
    await state.set_state(PhotoshootStates.reviewing_suggested_styles)

@router.callback_query(F.data == "confirm_generation")
async def confirm_gen(callback: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot):
    try:
        user = await get_or_create_user(session, callback.from_user.id)
        if user.images_remaining < 1:
            await callback.message.edit_text("❌ Недостаточно средств!", reply_markup=get_buy_packages_keyboard())
            return

        msg = await callback.message.edit_text("🎨 Генерирую фотосессию (4 фото)... ⏳ ~1 мин")
        data = await state.get_data()

        res = await image_processor.generate_photoshoot(
            data["product_image_bytes"], data["styles"], data["aspect_ratio"], bot, user
        )

        if not res["success"]:
            await msg.edit_text(f"❌ Ошибка: {res.get('error', 'Неизвестная ошибка')}")
            return

        # Deduct balance only if generation was successful
        await update_user_images_count(session, user.id, -1)

        media = []
        successful_count = 0
        failed_count = 0

        for i, img in enumerate(res["images"]):
            if img.get("success"):
                try:
                    # Wrap bytes in BufferedInputFile for aiogram
                    input_file = BufferedInputFile(
                        img["image_bytes"],
                        filename=f"photoshoot_{i}_{img['style_name']}.png"
                    )
                    media.append(InputMediaPhoto(
                        media=input_file,
                        caption=f"Style: {img['style_name']}" if i==0 else None
                    ))
                    await create_processed_image(session, user.id, None, img["style_name"], img["prompt"], data["aspect_ratio"])
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

                # Create summary message
                summary = "✅ Готово!"
                if failed_count > 0:
                    summary += f"\n⚠️ {failed_count} из {successful_count + failed_count} изображений не удалось сгенерировать"

                await callback.message.answer(
                    summary,
                    reply_markup=get_post_generation_keyboard(user.images_remaining > 0)
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
    await callback.message.answer("Введите название для сохранения стиля:")
    await state.set_state(PhotoshootStates.saving_style_name)

@router.message(StateFilter(PhotoshootStates.saving_style_name))
async def save_style_name(message: Message, state: FSMContext, session: AsyncSession):
    name = message.text
    data = await state.get_data()
    res = await StyleManager.save_style(
        session, message.from_user.id, name, data["product_name"], data["aspect_ratio"], data["styles"]
    )
    if res["success"]:
        await message.answer("✅ Стиль сохранен!", reply_markup=get_post_generation_keyboard(True))
    else:
        await message.answer(f"❌ Ошибка: {res['error']}")
    await state.clear() # Or go back to generated state? Clear is safer.

def _format_styles_preview(styles):
    return "\n\n".join([f"{i+1}. <b>{s['style_name']}</b>" for i, s in enumerate(styles)])

@router.callback_query(F.data == "back_to_ratio")
async def back_ratio(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Выберите пропорции:", reply_markup=get_aspect_ratio_keyboard())
    await state.set_state(PhotoshootStates.selecting_aspect_ratio)

@router.callback_query(F.data == "back_to_style_selection")
async def back_styles(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await callback.message.edit_text(f"✅ Пропорции: {data['aspect_ratio']}\nВыберите метод:", reply_markup=get_style_selection_keyboard())
    await state.set_state(PhotoshootStates.selecting_styles_method)

@router.callback_query(F.data == "new_photoshoot")
async def new_photoshoot(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("📸 Отправьте фото товара.")
    await state.clear()
    await state.set_state(PhotoshootStates.waiting_for_product_photo)

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
                'images_count': p.images_count,
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
    """Show user profile"""
    try:
        user = await get_or_create_user(session, callback.from_user.id)
        balance = await get_user_balance(session, callback.from_user.id)

        text = (
            f"👤 <b>Ваш профиль</b>\n\n"
            f"ID: <code>{user.telegram_id}</code>\n"
            f"Имя: {callback.from_user.full_name}\n"
            f"Username: @{callback.from_user.username or 'не указан'}\n\n"
            f"📊 <b>Баланс:</b>\n"
            f"💎 Доступно фотосессий: <b>{balance['total']}</b>\n"
            f"🆓 Бесплатных: {balance['free']}\n"
            f"💰 Купленных: {balance['paid']}\n\n"
            f"📈 <b>Статистика:</b>\n"
            f"✅ Обработано изображений: {user.images_processed}\n"
        )

        await callback.message.edit_text(text, parse_mode="HTML")
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