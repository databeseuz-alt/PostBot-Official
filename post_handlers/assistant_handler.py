import asyncio
import re

from aiogram import F, Router, types, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import StateFilter
from aiogram.utils.keyboard import InlineKeyboardBuilder

from post_handlers.post_handler import PostCreation
from post_handlers.xreply_keyboard import get_main_menu
from post_handlers.localize_filter import LocalizedText
from xdata_handlers.database import get_user_language, save_prompt, get_user_prompts, delete_prompt, get_prompt_by_id
from xdata_handlers.translator import get_text
from xdata_handlers import config

ai_assistant_router = Router()

def markdown_to_html(text: str) -> str:
    """Markdown matnni HTML formatiga o'girish."""
    if not text:
        return text

    text = re.sub(r'```([\s\S]*?)```', r'<pre>\1</pre>', text)

    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)

    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)

    text = re.sub(r'__(.*?)__', r'<b>\1</b>', text)

    text = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'<i>\1</i>', text)

    text = re.sub(r'(?<!_)_([^_]+)_(?!_)', r'<i>\1</i>', text)

    text = re.sub(r'~~(.*?)~~', r'<s>\1</s>', text)

    text = re.sub(r'^####\s+(.*)$', r'<b>\1</b>', text, flags=re.MULTILINE)
    text = re.sub(r'^###\s+(.*)$', r'<b>\1</b>', text, flags=re.MULTILINE)
    text = re.sub(r'^##\s+(.*)$', r'<b>\1</b>', text, flags=re.MULTILINE)
    text = re.sub(r'^#\s+(.*)$', r'<b>\1</b>', text, flags=re.MULTILINE)

    text = re.sub(r'^>\s+(.*)$', r'<blockquote>\1</blockquote>', text, flags=re.MULTILINE)

    text = re.sub(r'^-\s+(.*)$', r'• \1', text, flags=re.MULTILINE)

    text = re.sub(r'^(\d+)\.\s+(.*)$', r'\1. \2', text, flags=re.MULTILINE)

    text = re.sub(r'^---$', '───────────────', text, flags=re.MULTILINE)
    text = re.sub(r'^\*\*\*$', '───────────────', text, flags=re.MULTILINE)

    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)

    text = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', r'\1 (\2)', text)

    lines = text.split('\n')
    result_lines = []
    in_pre = False
    for line in lines:
        if '<pre>' in line:
            in_pre = True
        if '</pre>' in line:
            in_pre = False
        result_lines.append(line)
    text = '\n'.join(result_lines)

    return text

def get_ai_assistant_keyboard(lang: str = 'uzl'):
    """AI-assistent uchun inline klaviatura."""
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text('back_btn', lang), callback_data="ai_assistant_back")
    builder.adjust(1)
    return builder.as_markup()

def get_ai_assistant_reply_keyboard(lang: str = 'uzl'):
    """AI-assistent uchun reply klaviatura."""
    from aiogram.utils.keyboard import ReplyKeyboardBuilder
    from aiogram.types import KeyboardButton

    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text=get_text('back_btn', lang)))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)

def get_saved_prompts_keyboard(prompts: list[dict], lang: str = 'uzl'):
    """Saqlangan promptlar uchun inline klaviatura."""
    builder = InlineKeyboardBuilder()

    if prompts:
        for prompt in prompts:
            prompt_preview = prompt['prompt_text'][:30] + "..." if len(prompt['prompt_text']) > 30 else prompt['prompt_text']
            builder.button(
                text=prompt_preview,
                callback_data=f"use_prompt:{prompt['id']}"
            )
        builder.adjust(1)

    builder.button(text="🗑 O'chirish", callback_data="delete_prompt_mode")
    builder.button(text=get_text('back_btn', lang), callback_data="ai_assistant_back")
    builder.adjust(2)
    return builder.as_markup()

def get_saved_prompts_reply_keyboard(prompts: list[dict], lang: str = 'uzl'):
    """Saqlangan promptlar uchun reply klaviatura."""
    from aiogram.utils.keyboard import ReplyKeyboardBuilder
    from aiogram.types import KeyboardButton

    builder = ReplyKeyboardBuilder()

    if prompts:
        for prompt in prompts:
            prompt_preview = prompt['prompt_text'][:30] + "..." if len(prompt['prompt_text']) > 30 else prompt['prompt_text']
            builder.add(KeyboardButton(text=f"📝 {prompt_preview}"))
        builder.adjust(1)

    builder.add(KeyboardButton(text="🗑 O'chirish"))
    builder.add(KeyboardButton(text=get_text('back_btn', lang)))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def get_delete_prompt_keyboard(prompts: list[dict], lang: str = 'uzl'):
    """Promptlarni o'chirish uchun inline klaviatura."""
    builder = InlineKeyboardBuilder()

    if prompts:
        for prompt in prompts:
            prompt_preview = prompt['prompt_text'][:30] + "..." if len(prompt['prompt_text']) > 30 else prompt['prompt_text']
            builder.button(
                text=f"🗑 {prompt_preview}",
                callback_data=f"confirm_delete_prompt:{prompt['id']}"
            )
        builder.adjust(1)

    builder.button(text=get_text('back_btn', lang), callback_data="ai_prompts")
    builder.adjust(1)
    return builder.as_markup()

class AIAssistant(StatesGroup):
    waiting_for_user_message = State()
    waiting_for_prompt_to_save = State()
    waiting_for_prompt_to_delete = State()

async def call_gemini_api(history: list[dict]) -> str | None:
    """Google Gemini API orqali AI javobini olish (tarix bilan)."""
    if not config.GEMINI_API_KEY:
        return "AI API kaliti sozlanmagan. Iltimos, .env fayliga GEMINI_API_KEY qo'shing."

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=config.GEMINI_API_KEY)

        model = "gemini-2.0-flash"

        contents = []
        for msg in history:
            role = "user" if msg['role'] == 'user' else "model"
            contents.append(
                types.Content(
                    role=role,
                    parts=[
                        types.Part.from_text(text=msg['text']),
                    ],
                )
            )

        response = await asyncio.to_thread(
            client.models.generate_content,
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=config.AI_SYSTEM_INSTRUCTION
            )
        )

        if response and response.text:
            return response.text
        else:
            return "AI javob bera olmadi."
    except ImportError:
        return "AI kutubxonasi o'rnatilmagan. Iltimos, admin bilan bog'laning."
    except Exception:
        return "AI bilan bog'lanishda xatolik yuz berdi. Iltimos, keyinroq urinib ko'ring."

@ai_assistant_router.callback_query(F.data == "ai_assistant")
async def ai_assistant_start(callback: types.CallbackQuery, state: FSMContext):
    """AI-assistent tugmasi bosilganda."""
    await callback.answer("AI-assistentga o'tilmoqda...")
    lang = await get_user_language(callback.from_user.id)

    current_state = await state.get_state()
    await state.update_data(previous_state=current_state)

    await state.update_data(ai_history=[])

    await state.set_state(AIAssistant.waiting_for_user_message)

    try:
        await callback.message.answer(
            get_text('ai_assistant_msg', lang),
            reply_markup=get_ai_assistant_reply_keyboard(lang)
        )
    except Exception:
        pass

@ai_assistant_router.message(
    StateFilter(
        PostCreation.waiting_for_content,
        PostCreation.waiting_for_edit_code,
        PostCreation.configuring_post,
        PostCreation.waiting_for_button_text,
        PostCreation.waiting_for_button_url,
        PostCreation.waiting_for_post_name,
    ),
    LocalizedText('ai_assistant_btn')
)
async def ai_assistant_button_handler(message: types.Message, state: FSMContext, bot: Bot):
    """AI-assistent tugmasi bosilganda (post yaratish jarayonidan)."""
    lang = await get_user_language(message.from_user.id)
    data = await state.get_data()
    content_message_id = data.get('content_message_id')

    current_state = await state.get_state()
    await state.update_data(previous_state=current_state)

    await state.update_data(ai_history=[])

    await state.set_state(AIAssistant.waiting_for_user_message)

    await message.answer(
        get_text('ai_assistant_msg', lang),
        reply_markup=get_ai_assistant_reply_keyboard(lang)
    )

@ai_assistant_router.message(AIAssistant.waiting_for_user_message, LocalizedText('back_btn'))
async def ai_assistant_back_reply(message: types.Message, state: FSMContext, bot: Bot):
    """Reply klaviaturadagi 'Orqaga' tugmasi uchun."""

    data = await state.get_data()
    previous_state = data.get('previous_state')

    lang = await get_user_language(message.from_user.id)

    if previous_state:
        await state.set_state(previous_state)
        previous_state_str = str(previous_state)

        if 'PostCreation' in previous_state_str and 'waiting_for_content' in previous_state_str:
            from post_handlers.xreply_keyboard import get_cancel_reply_kb
            content_text = get_text('content_msg', lang)
            await message.answer(content_text, reply_markup=get_cancel_reply_kb(lang, True))  # AI assistant is enabled if user was in AI flow
        else:
            await state.clear()
            from post_handlers.start_handler import show_main_menu
            await show_main_menu(message, state, bot)

@ai_assistant_router.message(AIAssistant.waiting_for_user_message, F.text, ~F.text.startswith('/'))
async def ai_assistant_process_message(message: types.Message, state: FSMContext, bot: Bot):
    """Foydalanuvchi xabarini qabul qiladi va AI javobini yuboradi."""
    user_message = message.text
    lang = await get_user_language(message.from_user.id)

    await bot.send_chat_action(message.chat.id, "typing")

    data = await state.get_data()
    history = data.get('ai_history', [])

    history.append({'role': 'user', 'text': user_message})

    ai_response = await call_gemini_api(history)

    if ai_response:
        history.append({'role': 'model', 'text': ai_response})
        await state.update_data(ai_history=history)

    ai_response_html = markdown_to_html(ai_response)

    await message.answer(ai_response_html, parse_mode="HTML", reply_markup=get_ai_assistant_reply_keyboard(lang))

@ai_assistant_router.message(AIAssistant.waiting_for_user_message, ~F.text)
async def ai_assistant_non_text(message: types.Message, state: FSMContext):
    """Boshqa turdagi xabarlar kelganda (rasm, video, stiker va h.k.)."""
    lang = await get_user_language(message.from_user.id)
    await message.answer(
        "⚠️ Hozircha faqat matnli xabarlar qabul qilinadi. Iltimos, matn yuboring.",
        reply_markup=get_ai_assistant_reply_keyboard(lang)
    )


@ai_assistant_router.callback_query(F.data == "ai_assistant_back")
async def ai_assistant_back(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    """Orqaga tugmasi bosilganda."""
    await callback.answer("Orqaga qaytmoqda...")

    data = await state.get_data()
    previous_state = data.get('previous_state')

    lang = await get_user_language(callback.from_user.id)

    try:
        await callback.message.delete()

        if previous_state:
            await state.set_state(previous_state)

            previous_state_str = str(previous_state)

            if 'PostCreation' in previous_state_str and 'waiting_for_content' in previous_state_str:
                from post_handlers.xreply_keyboard import get_cancel_reply_kb
                content_text = get_text('content_msg', lang)
                await callback.message.answer(content_text, reply_markup=get_cancel_reply_kb(lang, True))  # AI assistant is enabled if user was in AI flow
            elif 'AIAssistant' in previous_state_str and 'waiting_for_user_message' in previous_state_str:
                await callback.message.answer(
                    get_text('ai_assistant_msg', lang),
                    reply_markup=get_ai_assistant_keyboard(lang)
                )
            else:
                await state.clear()
                from post_handlers.start_handler import show_main_menu
                await show_main_menu(callback, state, bot)

    except Exception:
        pass

async def ai_assistant_prompts(callback: types.CallbackQuery, state: FSMContext):
    """Promptlar tugmasi bosilganda."""
    await callback.answer("Promptlar menyusi...")
    lang = await get_user_language(callback.from_user.id)

    current_state = await state.get_state()
    await state.update_data(previous_state=current_state)

    prompts = await get_user_prompts(callback.from_user.id)

    try:
        if prompts:
            prompts_text = "❤️ <b>Saqlangan promptlar</b>\n\n"
            prompts_text += "Bu yerda promptlarni saqlab, keyin bir marta bosish orqali ulardan foydalanishingiz mumkin.\n\n"
            prompts_text += "▫️ Promptni saqlash uchun uning matnini yuboring\n"
            prompts_text += "▫️ O'chirish uchun - «O'chirish» tugmasini bosing va ro'yxatdan promptni tanlang"

            await callback.message.delete()
            await callback.message.answer(
                prompts_text,
                parse_mode="HTML",
                reply_markup=get_saved_prompts_reply_keyboard(prompts, lang)
            )
        else:
            prompts_text = "❤️ <b>Saqlangan promptlar</b>\n\n"
            prompts_text += "Bu yerda promptlarni saqlab, keyin bir marta bosish orqali ulardan foydalanishingiz mumkin.\n\n"
            prompts_text += "▫️ Promptni saqlash uchun uning matnini yuboring\n"
            prompts_text += "▫️ O'chirish uchun - «O'chirish» tugmasini bosing va ro'yxatdan promptni tanlang\n\n"
            prompts_text += "Hozirda hech qanday prompt saqlanmagan."

            await callback.message.delete()
            await callback.message.answer(
                prompts_text,
                parse_mode="HTML",
                reply_markup=get_saved_prompts_reply_keyboard(prompts, lang)
            )

        await state.set_state(AIAssistant.waiting_for_prompt_to_save)
    except Exception:
        pass

@ai_assistant_router.message(AIAssistant.waiting_for_prompt_to_save, F.text)
async def save_prompt_handler(message: types.Message, state: FSMContext):
    """Promptni saqlash."""
    prompt_text = message.text
    lang = await get_user_language(message.from_user.id)

    if prompt_text == get_text('back_btn', lang):
        await state.set_state(AIAssistant.waiting_for_user_message)
        await message.answer(
            get_text('ai_assistant_msg', lang),
            reply_markup=get_ai_assistant_keyboard(lang)
        )
        return

    if prompt_text == "🗑 O'chirish":
        prompts = await get_user_prompts(message.from_user.id)
        if prompts:
            prompts_text = "🗑 <b>Promptni o'chirish</b>\n\n"
            prompts_text += "O'chirmoqchi bo'lgan promptni tanlang:"
            await message.answer(
                prompts_text,
                parse_mode="HTML",
                reply_markup=get_saved_prompts_reply_keyboard(prompts, lang)
            )
            await state.set_state(AIAssistant.waiting_for_prompt_to_delete)
        else:
            await message.answer("❌ O'chirish uchun hech qanday prompt yo'q.")
        return

    prompt_id = await save_prompt(message.from_user.id, prompt_text)

    if prompt_id:
        await message.answer("✅ Prompt saqlandi!")
    else:
        await message.answer("❌ Promptni saqlashda xatolik yuz berdi.")

    prompts = await get_user_prompts(message.from_user.id)

    if prompts:
        prompts_text = "❤️ <b>Saqlangan promptlar</b>\n\n"
        prompts_text += "Bu yerda promptlarni saqlab, keyin bir marta bosish orqali ulardan foydalanishingiz mumkin.\n\n"
        prompts_text += "▫️ Promptni saqlash uchun uning matnini yuboring\n"
        prompts_text += "▫️ O'chirish uchun - «O'chirish» tugmasini bosing va ro'yxatdan promptni tanlang"

        await message.answer(
            prompts_text,
            parse_mode="HTML",
            reply_markup=get_saved_prompts_reply_keyboard(prompts, lang)
        )
    else:
        prompts_text = "❤️ <b>Saqlangan promptlar</b>\n\n"
        prompts_text += "Bu yerda promptlarni saqlab, keyin bir marta bosish orqali ulardan foydalanishingiz mumkin.\n\n"
        prompts_text += "▫️ Promptni saqlash uchun uning matnini yuboring\n"
        prompts_text += "▫️ O'chirish uchun - «O'chirish» tugmasini bosing va ro'yxatdan promptni tanlang\n\n"
        prompts_text += "Hozirda hech qanday prompt saqlanmagan."

        await message.answer(
            prompts_text,
            parse_mode="HTML",
            reply_markup=get_saved_prompts_reply_keyboard(prompts, lang)
        )

@ai_assistant_router.callback_query(F.data == "delete_prompt_mode")
async def delete_prompt_mode(callback: types.CallbackQuery, state: FSMContext):
    """O'chirish rejimiga o'tish."""
    await callback.answer()
    lang = await get_user_language(callback.from_user.id)

    prompts = await get_user_prompts(callback.from_user.id)

    if prompts:
        prompts_text = "🗑 <b>Promptni o'chirish</b>\n\n"
        prompts_text += "O'chirmoqchi bo'lgan promptni tanlang:"

        await callback.message.edit_text(
            prompts_text,
            parse_mode="HTML",
            reply_markup=get_delete_prompt_keyboard(prompts, lang)
        )
    else:
        prompts_text = "❌ O'chirish uchun hech qanday prompt yo'q."

        await callback.message.edit_text(
            prompts_text,
            parse_mode="HTML",
            reply_markup=get_saved_prompts_keyboard(prompts, lang)
        )

    await state.set_state(AIAssistant.waiting_for_prompt_to_delete)

@ai_assistant_router.callback_query(F.data.startswith("confirm_delete_prompt:"))
async def confirm_delete_prompt(callback: types.CallbackQuery, state: FSMContext):
    """Promptni o'chirishni tasdiqlash."""
    await callback.answer()
    lang = await get_user_language(callback.from_user.id)

    parts = callback.data.split(":")
    prompt_id = int(parts[1]) if len(parts) > 1 else None

    success = await delete_prompt(prompt_id, callback.from_user.id)

    if success:
        await callback.answer("✅ Prompt o'chirildi!")
    else:
        await callback.answer("❌ Promptni o'chirishda xatolik yuz berdi.")

    prompts = await get_user_prompts(callback.from_user.id)

    if prompts:
        prompts_text = "❤️ <b>Saqlangan promptlar</b>\n\n"
        prompts_text += "Bu yerda promptlarni saqlab, keyin bir marta bosish orqali ulardan foydalanishingiz mumkin.\n\n"
        prompts_text += "▫️ Promptni saqlash uchun uning matnini yuboring\n"
        prompts_text += "▫️ O'chirish uchun - «O'chirish» tugmasini bosing va ro'yxatdan promptni tanlang"

        await callback.message.edit_text(
            prompts_text,
            parse_mode="HTML",
            reply_markup=get_saved_prompts_keyboard(prompts, lang)
        )
    else:
        prompts_text = "❤️ <b>Saqlangan promptlar</b>\n\n"
        prompts_text += "Bu yerda promptlarni saqlab, keyin bir marta bosish orqali ulardan foydalanishingiz mumkin.\n\n"
        prompts_text += "▫️ Promptni saqlash uchun uning matnini yuboring\n"
        prompts_text += "▫️ O'chirish uchun - «O'chirish» tugmasini bosing va ro'yxatdan promptni tanlang\n\n"
        prompts_text += "Hozirda hech qanday prompt saqlanmagan."

        await callback.message.edit_text(
            prompts_text,
            parse_mode="HTML",
            reply_markup=get_saved_prompts_keyboard(prompts, lang)
        )

    await state.set_state(AIAssistant.waiting_for_prompt_to_save)

@ai_assistant_router.callback_query(F.data.startswith("use_prompt:"))
async def use_saved_prompt(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    """Saqlangan promptdan foydalanish."""
    await callback.answer()
    lang = await get_user_language(callback.from_user.id)

    parts = callback.data.split(":")
    prompt_id = int(parts[1]) if len(parts) > 1 else None

    prompt_data = await get_prompt_by_id(prompt_id, callback.from_user.id)

    if prompt_data:
        await callback.message.edit_text(
            get_text('ai_assistant_msg', lang),
            reply_markup=get_ai_assistant_keyboard(lang)
        )

        history = [{'role': 'user', 'text': prompt_data['prompt_text']}]
        await state.update_data(ai_history=history)

        ai_response = await call_gemini_api(history)

        if ai_response:
             history.append({'role': 'model', 'text': ai_response})
             await state.update_data(ai_history=history)

        ai_response_html = markdown_to_html(ai_response)

        await callback.message.answer(ai_response_html, parse_mode="HTML", reply_markup=get_ai_assistant_reply_keyboard(lang))
    else:
        await callback.answer("❌ Prompt topilmadi.")

    await state.set_state(AIAssistant.waiting_for_user_message)

@ai_assistant_router.message(AIAssistant.waiting_for_prompt_to_save, F.text.startswith("📝"))
async def use_saved_prompt_reply(message: types.Message, state: FSMContext, bot: Bot):
    """Saqlangan promptdan foydalanish (reply keyboard orqali)."""
    lang = await get_user_language(message.from_user.id)

    prompt_text = message.text[2:].strip()

    prompts = await get_user_prompts(message.from_user.id)
    prompt_data = None

    for prompt in prompts:
        if prompt['prompt_text'][:30] + ("..." if len(prompt['prompt_text']) > 30 else "") == prompt_text:
            prompt_data = prompt
            break

    if prompt_data:
        await message.answer(
            get_text('ai_assistant_msg', lang),
            reply_markup=get_ai_assistant_keyboard(lang)
        )

        history = [{'role': 'user', 'text': prompt_data['prompt_text']}]
        await state.update_data(ai_history=history)

        ai_response = await call_gemini_api(history)

        if ai_response:
             history.append({'role': 'model', 'text': ai_response})
             await state.update_data(ai_history=history)

        ai_response_html = markdown_to_html(ai_response)

        await message.answer(ai_response_html, parse_mode="HTML", reply_markup=get_ai_assistant_reply_keyboard(lang))

        await state.set_state(AIAssistant.waiting_for_user_message)
    else:
        await message.answer("❌ Prompt topilmadi.")

@ai_assistant_router.message(AIAssistant.waiting_for_prompt_to_delete, F.text.startswith("📝"))
async def delete_saved_prompt_reply(message: types.Message, state: FSMContext):
    """Saqlangan promptni o'chirish (reply keyboard orqali)."""
    lang = await get_user_language(message.from_user.id)

    prompt_text = message.text[2:].strip()

    prompts = await get_user_prompts(message.from_user.id)
    prompt_id = None

    for prompt in prompts:
        if prompt['prompt_text'][:30] + ("..." if len(prompt['prompt_text']) > 30 else "") == prompt_text:
            prompt_id = prompt['id']
            break

    if prompt_id:
        success = await delete_prompt(prompt_id, message.from_user.id)

        if success:
            await message.answer("✅ Prompt o'chirildi!")
        else:
            await message.answer("❌ Promptni o'chirishda xatolik yuz berdi.")

        prompts = await get_user_prompts(message.from_user.id)

        if prompts:
            prompts_text = "❤️ <b>Saqlangan promptlar</b>\n\n"
            prompts_text += "Bu yerda promptlarni saqlab, keyin bir marta bosish orqali ulardan foydalanishingiz mumkin.\n\n"
            prompts_text += "▫️ Promptni saqlash uchun uning matnini yuboring\n"
            prompts_text += "▫️ O'chirish uchun - «O'chirish» tugmasini bosing va ro'yxatdan promptni tanlang"

            await message.answer(
                prompts_text,
                parse_mode="HTML",
                reply_markup=get_saved_prompts_reply_keyboard(prompts, lang)
            )
        else:
            prompts_text = "❤️ <b>Saqlangan promptlar</b>\n\n"
            prompts_text += "Bu yerda promptlarni saqlab, keyin bir marta bosish orqali ulardan foydalanishingiz mumkin.\n\n"
            prompts_text += "▫️ Promptni saqlash uchun uning matnini yuboring\n"
            prompts_text += "▫️ O'chirish uchun - «O'chirish» tugmasini bosing va ro'yxatdan promptni tanlang\n\n"
            prompts_text += "Hozirda hech qanday prompt saqlanmagan."

            await message.answer(
                prompts_text,
                parse_mode="HTML",
                reply_markup=get_saved_prompts_reply_keyboard(prompts, lang)
            )

        await state.set_state(AIAssistant.waiting_for_prompt_to_save)
    else:
        await message.answer("❌ Prompt topilmadi.")

@ai_assistant_router.message(AIAssistant.waiting_for_prompt_to_delete, LocalizedText('back_btn'))
async def delete_prompt_back(message: types.Message, state: FSMContext):
    """O'chirish rejimidan orqaga qaytish."""
    lang = await get_user_language(message.from_user.id)

    prompts = await get_user_prompts(message.from_user.id)

    if prompts:
        prompts_text = "❤️ <b>Saqlangan promptlar</b>\n\n"
        prompts_text += "Bu yerda promptlarni saqlab, keyin bir marta bosish orqali ulardan foydalanishingiz mumkin.\n\n"
        prompts_text += "▫️ Promptni saqlash uchun uning matnini yuboring\n"
        prompts_text += "▫️ O'chirish uchun - «O'chirish» tugmasini bosing va ro'yxatdan promptni tanlang"

        await message.answer(
            prompts_text,
            parse_mode="HTML",
            reply_markup=get_saved_prompts_reply_keyboard(prompts, lang)
        )
    else:
        prompts_text = "❤️ <b>Saqlangan promptlar</b>\n\n"
        prompts_text += "Bu yerda promptlarni saqlab, keyin bir marta bosish orqali ulardan foydalanishingiz mumkin.\n\n"
        prompts_text += "▫️ Promptni saqlash uchun uning matnini yuboring\n"
        prompts_text += "▫️ O'chirish uchun - «O'chirish» tugmasini bosing va ro'yxatdan promptni tanlang\n\n"
        prompts_text += "Hozirda hech qanday prompt saqlanmagan."

        await message.answer(
            prompts_text,
            parse_mode="HTML",
            reply_markup=get_saved_prompts_reply_keyboard(prompts, lang)
        )

    await state.set_state(AIAssistant.waiting_for_prompt_to_save)
