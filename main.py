import logging
import config
import ai_handler
import notion_handler
from datetime import time, timezone, datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
)
from telegram.constants import ChatAction

# --- Basic Setup ---
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


# --- Daily Digest & Today's Focus Logic ---
async def send_today_dashboard(bot, chat_id: int):
    """Fetches and sends the full 'Today' dashboard."""
    logger.info(f"Running Today Dashboard for chat_id: {chat_id}")
    
    # Part 1: Today's Focus (Tasks due today)
    tasks_today = notion_handler.get_tasks_due_today()
    focus_message = "🎯 **Today's Focus**\n\n"
    if tasks_today:
        focus_message += "\n".join([f"- {task}" for task in tasks_today])
    else:
        focus_message += "No tasks due today. Great job!"
        
    await bot.send_message(chat_id=chat_id, text=focus_message, parse_mode='Markdown')

    # Part 2: Daily Digest (Summary of items added today)
    summary = notion_handler.get_daily_summary()
    digest_message = "\n\n🗓️ **Daily Digest**\n\nHere's what you've added today:\n"
    total_added = 0
    for category, count in summary.items():
        if count > 0:
            digest_message += f"\n- **{category}:** {count} new item(s)"
            total_added += count
    if total_added == 0:
        digest_message += "\nNo new items were added today."
        
    await bot.send_message(chat_id=chat_id, text=digest_message, parse_mode='Markdown')

# --- Job Callback for Daily Digest ---
async def daily_digest_job_callback(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Scheduled job callback. We'll just send the digest part."""
    chat_id = context.job.chat_id
    summary = notion_handler.get_daily_summary()
    digest_message = "🗓️ **Your Daily Digest**\n\nHere's what you've added today:\n"
    total_added = 0
    for category, count in summary.items():
        if count > 0:
            digest_message += f"\n- **{category}:** {count} new item(s)"
            total_added += count
    if total_added == 0:
        digest_message += "\nNo new items were added today."
    await context.bot.send_message(chat_id=chat_id, text=digest_message, parse_mode='Markdown')

# --- Command Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # ... (unchanged)
    user = update.effective_user
    chat_id = update.effective_chat.id
    if 'daily_digest_job' not in context.chat_data:
        job_time = time(hour=13, minute=30, tzinfo=timezone.utc) # 7 PM IST
        context.chat_data['daily_digest_job'] = context.job_queue.run_daily(
            daily_digest_job_callback,
            time=job_time,
            chat_id=chat_id,
            name=f"daily_digest_{chat_id}"
        )
        await update.message.reply_text("I've scheduled a daily summary for you every evening at 7 PM!")
    await update.message.reply_html(f"Hi {user.first_name}! Let's organize your thoughts.")

async def today_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manually triggers the full 'Today' dashboard."""
    await update.message.reply_text("Fetching your dashboard for today...")
    await send_today_dashboard(context.bot, update.effective_chat.id)


# ... (other command handlers are unchanged)
async def task_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    task_description = " ".join(context.args)
    if not task_description: await update.message.reply_text("Usage: /task <your task>"); return
    await update.message.reply_text("Analyzing your task...")
    task_details = ai_handler.extract_task_details(task_description)
    if task_details:
        notion_page_url = notion_handler.add_task(task_details)
        if notion_page_url: await update.message.reply_html(f"✅ Task added: <a href='{notion_page_url}'>{task_details['task_name']}</a>")
        else: await update.message.reply_text("❌ Couldn't add task.")
    else: await update.message.reply_text("Sorry, I had trouble understanding that task.")
async def archive_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        title_to_archive = " ".join(context.args)
        if not title_to_archive: await update.message.reply_text("Usage: /archive <exact page title>"); return
        await update.message.reply_text(f"Searching for '{title_to_archive}'...")
        page_data = notion_handler.search_databases_for_exact_title(title_to_archive)
        if page_data:
            context.user_data['archive_data'] = page_data
            keyboard = [[InlineKeyboardButton("✅ Yes, archive it", callback_data='archive_confirm'), InlineKeyboardButton("❌ Cancel", callback_data='archive_cancel')]]
            await update.message.reply_text(f"Found: <b>{title_to_archive}</b>\n\nMove it to the archive?", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        else: await update.message.reply_text(f"Sorry, couldn't find a page with that exact title.")
    except (IndexError, ValueError): await update.message.reply_text("Usage: /archive <exact page title>")
async def find_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        query = " ".join(context.args)
        if not query: await update.message.reply_text("Usage: /find <keyword>"); return
        await update.message.reply_text(f"Searching your workspace for '{query}'...")
        results = notion_handler.search_workspace(query)
        if results:
            message = f"🔎 Found {len(results)} page(s) matching '<b>{query}</b>':\n\n" + "\n".join([f"• <a href='{page['url']}'>{page['title']}</a>" for page in results[:10]])
            await update.message.reply_html(message, disable_web_page_preview=True)
        else: await update.message.reply_text(f"No results found for '{query}'.")
    except Exception as e:
        logger.error(f"Error in find_command: {e}")
        await update.message.reply_text("An error occurred while searching.")
async def add_to_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        full_args = " ".join(context.args)
        if '-' not in full_args: await update.message.reply_text("Invalid format. Usage: /addto <exact page title> - <your note>"); return
        parts = full_args.split('-', 1)
        title_to_find, note_to_add = parts[0].strip(), parts[1].strip()
        if not title_to_find or not note_to_add: await update.message.reply_text("Both a title and a note are required."); return
        await update.message.reply_text(f"Searching for '{title_to_find}'...")
        page_data = notion_handler.search_databases_for_exact_title(title_to_find)
        if page_data:
            success = notion_handler.add_note_to_page(page_data.get("page_id"), note_to_add)
            if success: await update.message.reply_html(f"✅ Note added to <a href='{page_data.get('url')}'>{title_to_find}</a>")
            else: await update.message.reply_text("❌ Couldn't add your note.")
        else: await update.message.reply_text(f"Sorry, couldn't find a page with the exact title '{title_to_find}'.")
    except Exception as e:
        logger.error(f"Error in add_to_command: {e}")
        await update.message.reply_text("An error occurred.")

# --- Message Handlers ---
async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # ... (unchanged)
    user_text = update.message.text
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    ai_result = ai_handler.process_text_with_ai(user_text)
    if not ai_result:
        await update.message.reply_text("Sorry, I had trouble understanding that.")
        return
    if ai_result.get("category") == "Projects" and ai_handler.is_project_complex(ai_result.get("title")):
        context.user_data['project_data'] = ai_result
        keyboard = [[InlineKeyboardButton("✅ Yes, break it down", callback_data='breakdown_yes'), InlineKeyboardButton("❌ No, thanks", callback_data='breakdown_no')]]
        await update.message.reply_text(f"Complex project detected: <b>'{ai_result['title']}'</b>.\nBreak it down?", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    else:
        notion_page_url = notion_handler.add_item_to_database(ai_result)
        if notion_page_url:
            await update.message.reply_html(f"✅ Added to <b>{ai_result.get('category')}</b>: <a href='{notion_page_url}'>{ai_result.get('title')}</a>", disable_web_page_preview=True)
        else:
            await update.message.reply_text("❌ Sorry, I couldn't add this to Notion.")

# --- Callback Query Handler ---
async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # ... (unchanged)
    query = update.callback_query
    await query.answer()
    choice = query.data
    if choice.startswith('archive_'):
        archive_data = context.user_data.get('archive_data')
        if not archive_data: await query.edit_message_text("Error. Try /archive again."); return
        if choice == 'archive_confirm':
            success = notion_handler.move_page_to_archive(archive_data)
            await query.edit_message_text("✅ Moved to Archive." if success else "❌ Failed to move page.")
        else: await query.edit_message_text("Archive cancelled.")
        return
    ai_data = context.user_data.get('project_data')
    if not ai_data: await query.edit_message_text("Error. Please send the project again."); return
    if choice == 'breakdown_yes':
        await query.edit_message_text(f"Breaking down '{ai_data['title']}'...")
        tasks = ai_handler.break_down_project(ai_data['title'])
        if tasks:
            context.user_data['project_tasks'] = tasks
            task_list_str = "\n".join([f"• {task}" for task in tasks])
            keyboard = [[InlineKeyboardButton("👍 Add them", callback_data='approve_tasks'), InlineKeyboardButton("👎 Add without tasks", callback_data='cancel_tasks')]]
            await query.edit_message_text(f"Sub-tasks for <b>'{ai_data['title']}'</b>:\n\n{task_list_str}\n\nAdd them?", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        else:
            await query.edit_message_text("Couldn't break it down. Adding project without tasks.")
            notion_page_url = notion_handler.add_item_to_database(ai_data)
            if notion_page_url: await query.edit_message_text(f"✅ Project added!\n<a href='{notion_page_url}'>{ai_data['title']}</a>", parse_mode='HTML', disable_web_page_preview=True)
            else: await query.edit_message_text("❌ Couldn't add project.")
    elif choice in ['breakdown_no', 'cancel_tasks']:
        await query.edit_message_text(f"Okay, adding '{ai_data['title']}'...")
        notion_page_url = notion_handler.add_item_to_database(ai_data)
        if notion_page_url: await query.edit_message_text(f"✅ Project added!\n<a href='{notion_page_url}'>{ai_data['title']}</a>", parse_mode='HTML', disable_web_page_preview=True)
        else: await query.edit_message_text("❌ Couldn't add project.")
    elif choice == 'approve_tasks':
        tasks = context.user_data.get('project_tasks')
        await query.edit_message_text("Adding project and tasks...")
        notion_page_url = notion_handler.add_project_with_tasks(ai_data, tasks)
        if notion_page_url: await query.edit_message_text(f"✅ Project and tasks added!\n<a href='{notion_page_url}'>{ai_data['title']}</a>", parse_mode='HTML', disable_web_page_preview=True)
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
    application.add_handler(CommandHandler("today", today_command))
    application.add_handler(CommandHandler("archive", archive_command))
    application.add_handler(CommandHandler("find", find_command))
    application.add_handler(CommandHandler("addto", add_to_command))
    application.add_handler(CommandHandler("task", task_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Entity("url"), handle_text_message))
    application.add_handler(MessageHandler(filters.Entity("url") | filters.Entity("text_link"), handle_link))
    application.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, handle_media))
    application.add_handler(CallbackQueryHandler(button_callback_handler))

    logger.info("Bot is starting up...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)
    logger.info("Bot has shut down.")


if __name__ == "__main__":
    main()
