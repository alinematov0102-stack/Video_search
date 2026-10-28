import os
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp

# Loglarni sozlash
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Server resurslarini tejash va qotib qolmaslik uchun Executor
executor = ThreadPoolExecutor(max_workers=4)

# /start buyrug'i
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_name = update.effective_user.first_name
    await update.message.reply_text(
        f"Salom, {user_name}! 👋\n\n"
        "Menga **Instagram** yoki **TikTok** video havolasini yuboring. "
        "Men sizga videoni va uning musiqasini (audio) professional tarzda yuklab beraman! 🚀"
    )

# Yuklab olish jarayoni (Background Thread)
def blocking_download(url, file_id):
    video_filename = f"video_{file_id}.mp4"
    audio_filename = f"audio_{file_id}.mp3"

    # Video sozlamalari
    ydl_video_opts = {
        'format': 'best',
        'outtmpl': video_filename,
        'quiet': True,
        'no_warnings': True,
        'geo_bypass': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        }
    }

    # Audio sozlamalari
    ydl_audio_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f"audio_{file_id}.%(ext)s",
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
        'no_warnings': True,
        'geo_bypass': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        }
    }

    success = False
    try:
        # Videoni tortish
        with yt_dlp.YoutubeDL(ydl_video_opts) as ydl:
            ydl.download([url])
        
        # Musiqani tortish
        with yt_dlp.YoutubeDL(ydl_audio_opts) as ydl:
            ydl.download([url])
            
        success = True
    except Exception as e:
        logger.error(f"Yuklashda xatolik: {e}")

    return success, video_filename, audio_filename

# Xabarlarni qabul qilish va qayta ishlash
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    url = update.message.text.strip()
    
    # Havolani tekshirish
    if not ("instagram.com" in url or "tiktok.com" in url):
        await update.message.reply_text("⚠️ Iltimos, faqat haqiqiy **Instagram** yoki **TikTok** havolasini yuboring!")
        return

    status_msg = await update.message.reply_text("⏳ Media qidirilmoqda va yuklab olinmoqda...")
    
    file_id = f"{update.message.from_user.id}_{update.message.message_id}"
    
    # Asinxron tarzda yuklab olishni ishga tushiramiz
    loop = asyncio.get_running_loop()
    success, video_filename, audio_filename = await loop.run_in_executor(
        executor, blocking_download, url, file_id
    )

    if not success or (not os.path.exists(video_filename) and not os.path.exists(audio_filename)):
        await status_msg.edit_text(
            "❌ **Xatolik yuz berdi!**\n\n"
            "• Havola yopiq (private) sahifaga tegishli bo'lishi mumkin.\n"
            "• Yoki video o'chirib yuborilgan."
        )
        return

    try:
        await status_msg.edit_text("📤 Telegramga yuborilmoqda...")

        # Videoni yuborish
        if os.path.exists(video_filename):
            with open(video_filename, 'rb') as v_file:
                await update.message.reply_video(
                    video=v_file,
                    caption="✅ **Video muvaffaqiyatli yuklandi!**",
                    supports_streaming=True
                )

        # Musiqani yuborish
        if os.path.exists(audio_filename):
            with open(audio_filename, 'rb') as a_file:
                await update.message.reply_audio(
                    audio=a_file,
                    caption="🎵 **Original Musiqa (Audio)**",
                    title="Instagram/TikTok Audio"
                )

        await status_msg.delete()

    except Exception as e:
        logger.error(f"Yuborishda xatolik: {e}")
        await status_msg.edit_text("❌ Faylni Telegramga yuborish vaqtida xatolik yuz berdi.")

    finally:
        # Fayllarni tozalash (Xotirani to'ldirmaslik uchun)
        for filename in [video_filename, audio_filename]:
            if os.path.exists(filename):
                try:
                    os.remove(filename)
                except:
                    pass

def main():
    BOT_TOKEN = "8858754258:AAE_iSvoBxkHn52L6lfMoxS8lNQ9qMbi9ck"

    application = Application.builder().token(BOT_TOKEN).build()

    # Handlerlar
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 Professional bot ishga tushdi va foydalanuvchilarni kutmoqda...")
    application.run_polling()

if __name__ == '__main__':
    main()