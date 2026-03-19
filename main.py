import asyncio
import logging
from datetime import datetime
import os
from typing import Dict

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
API_TOKEN = os.getenv("BOT_TOKEN")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# Import handlers
from handlers.questions import router as questions_router
from handlers.different_types import router as different_types_router
from database import init_db

# Include routers
dp.include_router(questions_router)
dp.include_router(different_types_router)

# Initialize database
init_db()

# ------------------------------
# Entry point
# ------------------------------

async def main():
    """Start the bot."""
    logger.info("Bot started polling")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())