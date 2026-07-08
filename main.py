import os
import re
import json
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler
import yt_dlp

# লগিং সেটআপ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- কনফিগারেশন ---
BOT_TOKEN = os.getenv('BOT_TOKEN')
# SannexT এর জন্য যদি কোনো বিশেষ API Key বা Header লাগে তবে সেখানে যোগ করুন
SANNEXT_API_BASE_URL = "https://www.sannex.com/api/video/" # উদাহরণ, সঠিক URL পরীক্ষা করে নেবেন

def get_sannex_video_info(player_id):
    """
    SannexT থেকে প্লেয়ার আইডি ব্যবহার করে ভিডিওর তথ্য এবং লিংক বের করার ফাংশন।
    """
    try:
        # API কল (এটি একটি উদাহরণ, সঠিক এন্ডপয়েট অনুযায়ী পরিবর্তন করতে হতে পারে)
        # অনেক সময় প্লেয়ার আইডি URL থেকে বের করা যায়, যেমন: sannex.com/watch/12345
        url = f"{SANNEXT_API_BASE_URL}{player_id}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json'
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            
            # JSON ডাটা থেকে ভিডিও লিংক বের করা (এটি JSON স্ট্রাকচার অনুযায়ী পরিবর্তন হতে পারে)
            # সাধারণত 'video_url', 'source', বা 'hls' কী-এ থাকে।
            # এখানে একটি ডামি লজিক দেওয়া হলো, আপনাকে আপনার ব্রাউজারের নেটওয়ার্ক ট্যাব দেখে সঠিক কী-টি খুঁজে বের করতে হবে।
            
            video_url = data.get('video_url') or data.get('hls') or data.get('source')
            title = data.get('title', 'Unknown Title')
            thumbnail = data.get('thumbnail', '')
            
            if video_url:
                return {
                    "success": True,
                    "url": video_url,
                    "title": title,
                    "thumbnail": thumbnail
                }
            else:
                return {"success": False, "error": "Video URL not found in API response"}
        else:
            return {"success": False, "error": f"API Error: {response.status_code}"}
            
    except Exception as e:
        logger.error(f"Error fetching SannexT info: {e}")
        return {"success": False, "error": str(e)}

def get_ydl_opts():
    opts = {
        'quiet': False,
        'verbose': True,
        # কুকিজ ব্যবহার করবে (যদি DRM বা লগইন প্রয়োজন হয়)
        'cookiesfrombrowser': ('chrome',), 
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': '%(title)s.%(ext)s',
    }
    return opts

# --- বট হ্যান্ডলারস ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    first_name = update.effective_user.first_name
    text = f"হাই {first_name}, আমি SannexT ডাউনলোডার বট।\n\nআপনি নিচের যেকোনো একটি পাঠান:\n1. পুরো লিংক (যেমন: sannex.com/watch/12345)\n2. শুধুমাত্র প্লেয়ার আইডি (যেমন: 12345)"
    
    keyboard = [
        [InlineKeyboardButton("সাহায্য", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(text, reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'help':
        help_msg = "কীভাবে ব্যবহার করবেন:\n\n1. SannexT ভিডিও পেজে যান।\n2. লিংকের শেষের সংখ্যাটি কপি করুন (এটাই প্লেয়ার আইডি) অথবা পুরো লিংক কপি করুন।\n3. বটে পাঠিয়ে দিন।"
        await query.edit_message_text(help_msg)

async def handle_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    
    # লিংক থেকে আইডি বের করার রিজেক্স প্যাটার্ন
    # উদাহরণ: sannex.com/watch/12345 -> 12345
    match = re.search(r'watch/(\d+)', text)
    if match:
        player_id = match.group(1)
    else:
        # যদি শুধু সংখ্যা থাকে, তবে তা আইডি ধরে নেওয়া হবে
        if text.isdigit():
            player_id = text
        else:
            await update.message.reply_text("দয়া করে সঠিক প্লেয়ার আইডি বা লিংক দিন।")
            return

    msg = await update.message.reply_text(f"প্লেয়ার আইডি: `{player_id}`\nতথ্য পাওয়া যাচ্ছে...")
    
    # API কল করে তথ্য নেওয়া
    info = get_sannex_video_info(player_id)
    
    if info['success']:
        await msg.edit_text(
            f"ভিডিও পাওয়া গেছে!\n\n"
            f"শিরোনাম: {info['title']}\n"
            f"লিংক: {info['url'][:50]}...\n\n"
            f"দয়া করে কোয়ালিটি সিলেক্ট করুন:",
            parse_mode='Markdown'
        )
        
        # ইউজারকে ডাউনলোড অপশন দেখানো
        keyboard = [
            [InlineKeyboardButton("1080p (HD)", callback_data='dl_1080')],
            [InlineKeyboardButton("720p", callback_data='dl_720')],
            [InlineKeyboardButton("Audio Only", callback_data='dl_audio')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text("কোয়ালিটি সিলেক্ট করুন:", reply_markup=reply_markup)
    else:
        await msg.edit_text(f"ত্রুটি: {info['error']}")

async def download_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # এখানে আপনি ডাউনলোড লজিক বসাবেন।
    # নোট: বাস্তবে আপনাকে `get_sannex_video_info` থেকে পাওয়া URL ব্যবহার করে yt-dlp চালানো হবে।
    # যেহেতু আমরা স্টেট মেশিন ব্যবহার করছি না, তাই এখানে একটি ডামি লজিক দেওয়া হলো।
    
    await query.edit_message_text("ডাউনলোড শুরু হচ্ছে...")
    
    # উদাহরণস্বরূপ, আগের মেসেজ থেকে ইউআরএল বের করা জটিল, তাই আমরা ধরে নিচ্ছি যে API কল করে পাওয়া URL ব্যবহার করা হবে।
    # একটি পুরো কাজ করার জন্য, আপনাকে `context.user_data` বা ডাটাবেস ব্যবহার করে URL স্টোর করতে হবে।

def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_input))

    logger.info("Bot is starting...")
    application.run_polling()

if __name__ == '__main__':
    main()
