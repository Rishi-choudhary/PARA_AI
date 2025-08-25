import logging
import config
import ai_handler
import notion_handler

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
)
from telegram.constants import ChatAction

# --- Basic Setup ---
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


# --- Command Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # ... (unchanged)
    user = update.effective_user
    await update.message.reply_html(
        f"Hi {user.first_name}! I'm your PARA-method assistant. "
        "Send me text, links, photos, or files to organize them in Notion."
    )

async def archive_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /archive command to move an item to the archive."""
    try:
        # The title is everything after the "/archive " command
        title_to_archive = " ".join(context.args)
        if not title_to_archive:
            await update.message.reply_text("Please provide a title to archive.\nUsage: /archive <exact page title>")
            return

        await update.message.reply_text(f"Searching for '{title_to_archive}' to archive...")
        page_data = notion_handler.search_databases(title_to_archive)

        if page_data:
            context.user_data['archive_data'] = page_data
            keyboard = [[
                InlineKeyboardButton("✅ Yes, archive it", callback_data='archive_confirm'),
                InlineKeyboardButton("❌ Cancel", callback_data='archive_cancel'),
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(f"Found page: <b>{title_to_archive}</b>\n\nAre you sure you want to move it to the archive?", reply_markup=reply_markup, parse_mode='HTML')
        else:
            await update.message.reply_text(f"Sorry, I couldn't find a page with the exact title '{title_to_archive}'.")

    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /archive <exact page title>")


# --- Message Handlers ---
async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # ... (unchanged)
    user_text = update.message.text
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    ai_result = ai_handler.process_text_with_ai(user_text)
    if not ai_result:
        await update.message.reply_text("Sorry, I had trouble understanding that.")
        return
    if ai_result.get("category") == "Projects":
        context.user_data['project_data'] = ai_result
        keyboard = [[InlineKeyboardButton("✅ Yes, break it down", callback_data='breakdown_yes'), InlineKeyboardButton("❌ No, thanks", callback_data='breakdown_no')]]
        await update.message.reply_text(f"Project identified: <b>'{ai_result['title']}'</b>.\nBreak it down into tasks?", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    else:
        notion_page_url = notion_handler.add_item_to_database(ai_result)
        if notion_page_url:
            await update.message.reply_html(f"✅ Added to <b>{ai_result.get('category')}</b>: <a href='{notion_page_url}'>{ai_result.get('title')}</a>", disable_web_page_preview=True)
        else:
            await update.message.reply_text("❌ Sorry, I couldn't add this to Notion.")

# --- Callback Query Handler ---
async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles all button presses from inline keyboards."""
    query = update.callback_query
    await query.answer()
    choice = query.data

    # --- Archive Flow ---
    if choice.startswith('archive_'):
        archive_data = context.user_data.get('archive_data')
        if not archive_data:
            await query.edit_message_text("Sorry, something went wrong. Please try the /archive command again.")
            return
        
        if choice == 'archive_confirm':
            await query.edit_message_text("Archiving page...")
            success = notion_handler.move_page_to_archive(archive_data)
            if success:
                await query.edit_message_text("✅ Successfully moved to Archive.")
            else:
                await query.edit_message_text("❌ Failed to move page to Archive.")
        elif choice == 'archive_cancel':
            await query.edit_message_text("Archive operation cancelled.")
        return

    # --- Project Breakdown Flow ---
    ai_data = context.user_data.get('project_data')
    if not ai_data:
        await query.edit_message_text("Sorry, something went wrong. Please send the project again.")
        return

    if choice == 'breakdown_yes':
        await query.edit_message_text(f"Breaking down '{ai_data['title']}'...")
        tasks = ai_handler.break_down_project(ai_data['title'])
        if tasks:
            context.user_data['project_tasks'] = tasks
            task_list_str = "\n".join([f"• {task}" for task in tasks])
            keyboard = [[InlineKeyboardButton("👍 Add them", callback_data='approve_tasks'), InlineKeyboardButton("👎 Add without tasks", callback_data='cancel_tasks')]]
            await query.edit_message_text(f"Sub-tasks for <b>'{ai_data['title']}'</b>:\n\n{task_list_str}\n\nAdd them to the page?", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        else:
            await query.edit_message_text("Couldn't break it down. Adding project without tasks.")
            notion_page_url = notion_handler.add_item_to_database(ai_data)
            if notion_page_url: await query.edit_message_text(f"✅ Project added!\n\n<a href='{notion_page_url}'>{ai_data['title']}</a>", parse_mode='HTML', disable_web_page_preview=True)
            else: await query.edit_message_text("❌ Couldn't add project.")
    
    elif choice == 'breakdown_no':
        await query.edit_message_text(f"Okay, adding '{ai_data['title']}'...")
        notion_page_url = notion_handler.add_item_to_database(ai_data)
        if notion_page_url: await query.edit_message_text(f"✅ Project added!\n\n<a href='{notion_page_url}'>{ai_data['title']}</a>", parse_mode='HTML', disable_web_page_preview=True)
        else: await query.edit_message_text("❌ Couldn't add project.")

    elif choice == 'approve_tasks':
        tasks = context.user_data.get('project_tasks')
        await query.edit_message_text("Adding project and tasks...")
        notion_page_url = notion_handler.add_project_with_tasks(ai_data, tasks)
        if notion_page_url: await query.edit_message_text(f"✅ Project and tasks added!\n\n<a href='{notion_page_url}'>{ai_data['title']}</a>", parse_mode='HTML', disable_web_page_preview=True)
        else: await query.edit_message_text("❌ Couldn't add project.")
    
    elif choice == 'cancel_tasks':
        await query.edit_message_text("Okay, adding project without sub-tasks...")
        notion_page_url = notion_handler.add_item_to_database(ai_data)
        if notion_page_url: await query.edit_message_text(f"✅ Project added!\n\n<a href='{notion_page_url}'>{ai_data['title']}</a>", parse_mode='HTML', disable_web_page_preview=True)
        else: await query.edit_message_text("❌ Couldn't add project.")

# ... (handle_link and handle_media are unchanged)
async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    url = update.message.text
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    notion_page_url = notion_handler.add_content_to_resources(title=url, content_url=url, content_type="url")
    if notion_page_url: await update.message.reply_html(f"✅ Saved link: <a href='{notion_page_url}'>{url}</a>", disable_web_page_preview=True)
    else: await update.message.reply_text("❌ Couldn't save link.")

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    media_type = "Photo" if message.photo else "File"
    caption = message.caption or f"Telegram {media_type}"
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    try:
        file_id = message.photo[-1].file_id if message.photo else message.document.file_id
        caption = caption or (message.document.file_name if message.document else caption)
        file = await context.bot.get_file(file_id)
        notion_page_url = notion_handler.add_content_to_resources(title=caption, content_url=file.file_path, content_type=media_type.lower())
        if notion_page_url: await update.message.reply_html(f"✅ Saved {media_type}: <a href='{notion_page_url}'>{caption}</a>", disable_web_page_preview=True)
        else: await update.message.reply_text(f"❌ Couldn't save {media_type}.")
    except Exception as e:
        logger.error(f"Error handling media: {e}")
        await update.message.reply_text("❌ Error processing file.")

# --- Main Bot Logic ---
def main() -> None:
    """Start the bot and register all handlers."""
    application = Application.builder().token(config.TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("archive", archive_command)) # New command
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Entity("url"), handle_text_message))
    application.add_handler(MessageHandler(filters.Entity("url") | filters.Entity("text_link"), handle_link))
    application.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, handle_media))
    application.add_handler(CallbackQueryHandler(button_callback_handler))

    logger.info("Bot is starting up...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)
    logger.info("Bot has shut down.")


if __name__ == "__main__":
    main()
