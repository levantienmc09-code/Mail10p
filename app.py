import os
import threading
import telebot
import requests
import random
import json
import time
import re
from flask import Flask, render_template_string
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

app = Flask(__name__)

# Token bot của bạn (đã được cung cấp)
BOT_TOKEN = '8239205483:AAGW5QYjvQ0sajAlvbFY0idiPWo5Z6GX_Ko'
bot = telebot.TeleBot(BOT_TOKEN)

# Lưu trữ session ID của user
user_sessions = {}

class EmailSession:
    def __init__(self):
        self.session_id = None
        self.email = None
        self.domain = None
        self.mail_list = []
        
    def generate_session_id(self):
        """Tạo session ID ngẫu nhiên"""
        timestamp = int(time.time() * 1000)
        random_num = random.randint(100000, 999999)
        return f"{timestamp}{random_num}"

    def create_email(self, domain_choice=None):
        """Tạo email mới với domain cụ thể nếu được chọn"""
        max_attempts = 50  # Số lần thử tối đa
        attempts = 0
        
        while attempts < max_attempts:
            attempts += 1
            
            # Tạo session ID mới mỗi lần
            self.session_id = self.generate_session_id()
            
            # Gọi API tạo email
            api_url = f"https://10minutemail.net/address.api.php?sessionid={self.session_id}"
            
            try:
                response = requests.get(api_url, timeout=10)
                data = response.json()
                
                if "mail_get_mail" in data:
                    self.email = data["mail_get_mail"]
                    self.domain = data["mail_get_host"]
                    self.mail_list = data.get("mail_list", [])
                    
                    # Nếu không chọn domain hoặc domain khớp
                    if not domain_choice or domain_choice.lower() in self.domain.lower():
                        return {
                            "success": True,
                            "email": self.email,
                            "domain": self.domain,
                            "mail_list": self.mail_list,
                            "session_id": self.session_id
                        }
                    else:
                        # Nếu domain không khớp, tiếp tục thử
                        time.sleep(0.1)
                        continue
                        
            except Exception as e:
                print(f"Error creating email: {e}")
                continue
        
        # Nếu sau max_attempts vẫn không được domain mong muốn
        if self.email:
            return {
                "success": True,
                "email": self.email,
                "domain": self.domain,
                "mail_list": self.mail_list,
                "session_id": self.session_id,
                "note": f"Không tìm được domain '{domain_choice}' sau {max_attempts} lần thử. Đã tạo email với domain: {self.domain}"
            }
        else:
            return {"success": False, "error": "Không thể tạo email"}

    def get_inbox(self):
        """Lấy danh sách email trong inbox và trích xuất số từ subject"""
        if not self.session_id:
            return {"success": False, "error": "Chưa có session"}
        
        api_url = f"https://10minutemail.net/address.api.php?sessionid={self.session_id}"
        
        try:
            response = requests.get(api_url, timeout=10)
            data = response.json()
            self.mail_list = data.get("mail_list", [])
            
            # Trích xuất số từ subject của mỗi email
            emails_with_numbers = []
            for mail in self.mail_list:
                subject = mail.get("subject", "")
                # Tìm tất cả số trong subject
                numbers = re.findall(r'\b\d+\b', subject)
                if numbers:  # CHỈ lấy email có số
                    emails_with_numbers.append({
                        "mail_id": mail.get("mail_id", ""),
                        "subject": subject,
                        "numbers": numbers,
                        "first_number": numbers[0] if numbers else None,
                        "from": mail.get("from", ""),
                        "datetime2": mail.get("datetime2", ""),
                        "isread": mail.get("isread", False)
                    })
            
            return {
                "success": True,
                "all_mails": self.mail_list,
                "emails_with_numbers": emails_with_numbers,
                "email": self.email
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

def create_main_keyboard():
    """Tạo bàn phím chính với các nút"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    
    buttons = [
        InlineKeyboardButton("🎛️ Tạo Random", callback_data="create_mail"),
        InlineKeyboardButton("✉️ Inbox", callback_data="check_inbox"),
        InlineKeyboardButton("Tạo Mail Laoia", callback_data="create_laoia"),
        InlineKeyboardButton("Tạo Mail Toaik", callback_data="create_toaik")
    ]
    
    keyboard.add(buttons[0], buttons[1])
    keyboard.add(buttons[2], buttons[3])
    
    return keyboard

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    """Xử lý lệnh /start và /help"""
    welcome_text = """
👋 Chào mừng đến với Bot Tạo Email 10 Phút!

📧 **Các tính năng:**
• Tạo email 10 phút tự động
• Kiểm tra hộp thư đến
• Chọn domain Laoia hoặc Toaik

🛠 **Sử dụng:**
Nhấn vào các nút bên dưới để thao tác
    """
    
    bot.send_message(
        message.chat.id,
        welcome_text,
        parse_mode='Markdown',
        reply_markup=create_main_keyboard()
    )

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    """Xử lý tất cả callback từ nút"""
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    
    # Khởi tạo session nếu chưa có
    if user_id not in user_sessions:
        user_sessions[user_id] = EmailSession()
    
    session = user_sessions[user_id]
    
    if call.data == "create_mail":
        # Tạo email ngẫu nhiên
        bot.answer_callback_query(call.id, "Đang tạo email...")
        result = session.create_email()
        
        if result["success"]:
            response_text = f"""
📧 **Mail bạn vừa tạo:**
`{result['email']}`

📊 **Thông tin:**
• Domain: `{result['domain']}`
• Session ID: `{result['session_id']}`
• Thời gian: 10 phút
            """
            
            if "note" in result:
                response_text += f"\n📝 *Lưu ý:* {result['note']}"
        else:
            response_text = "❌ Không thể tạo email. Vui lòng thử lại!"
        
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text=response_text,
            parse_mode='Markdown',
            reply_markup=create_main_keyboard()
        )
    
    elif call.data == "create_laoia":
        # Tạo email với domain Laoia
        bot.answer_callback_query(call.id, "Đang tạo email Laoia...")
        result = session.create_email("laoia")
        
        if result["success"]:
            response_text = f"""
📧 **Mail bạn vừa tạo:**
`{result['email']}`

📊 **Thông tin:**
• Domain: `{result['domain']}`
• Session ID: `{result['session_id']}`
• Thời gian: 10 phút

✅ Đã tạo thành công với domain Laoia!
            """
            
            if "note" in result:
                response_text += f"\n📝 *Lưu ý:* {result['note']}"
        else:
            response_text = "❌ Không thể tạo email. Vui lòng thử lại!"
        
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text=response_text,
            parse_mode='Markdown',
            reply_markup=create_main_keyboard()
        )
    
    elif call.data == "create_toaik":
        # Tạo email với domain Toaik
        bot.answer_callback_query(call.id, "Đang tạo email Toaik...")
        result = session.create_email("toaik")
        
        if result["success"]:
            response_text = f"""
📧 **Mail bạn vừa tạo:**
`{result['email']}`

📊 **Thông tin:**
• Domain: `{result['domain']}`
• Session ID: `{result['session_id']}`
• Thời gian: 10 phút

✅ Đã tạo thành công với domain Toaik!
            """
            
            if "note" in result:
                response_text += f"\n📝 *Lưu ý:* {result['note']}"
        else:
            response_text = "❌ Không thể tạo email. Vui lòng thử lại!"
        
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text=response_text,
            parse_mode='Markdown',
            reply_markup=create_main_keyboard()
        )
    
    elif call.data == "check_inbox":
        # Kiểm tra inbox và trích xuất số
        bot.answer_callback_query(call.id, "Đang kiểm tra hộp thư...")
        result = session.get_inbox()
        
        if result["success"]:
            if not result["all_mails"]:
                response_text = f"""
📭 *Hộp thư trống*
Email: `{result['email']}`
                """
            else:
                total_emails = len(result["all_mails"])
                emails_with_numbers = result["emails_with_numbers"]
                
                if not emails_with_numbers:
                    response_text = f"""
📬 Hộp thư của: `{result['email']}`
📊 Tổng số email: {total_emails}

❌ Không có email nào chứa mã số trong tiêu đề
                    """
                else:
                    response_text = f"""
📬 Hộp thư của: `{result['email']}`
📊 Tổng số email: {total_emails}

📋 Inbox Mail:  
                    """
                    
                    for i, mail in enumerate(emails_with_numbers, 1):
                        # Hiển thị full from email
                        from_email = mail['from'].replace('<', '').replace('>', '')
                        
                        response_text += f"""
{i}. `{from_email}`
   └ Mã Của Bạn Là: `{mail['first_number']}`
   └ Tiêu đề: {mail['subject'][:50]}{'...' if len(mail['subject']) > 50 else ''}
                        """
                    
                    # Hiển thị thông báo nếu có email không có số
                    emails_without_numbers = total_emails - len(emails_with_numbers)
                    if emails_without_numbers > 0:
                        response_text += f"\n⚠️ Đã bỏ qua {emails_without_numbers} email không có mã số"
                    
        else:
            response_text = f"❌ Lỗi: {result.get('error', 'Không thể kiểm tra hộp thư')}"
        
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text=response_text,
            parse_mode='Markdown',
            reply_markup=create_main_keyboard()
        )

@bot.message_handler(commands=['extract'])
def extract_command(message):
    """Lệnh để trích xuất số từ chuỗi"""
    try:
        text = message.text.replace('/extract', '').strip()
        if not text:
            bot.reply_to(message, "Vui lòng nhập văn bản sau /extract\nVí dụ: `/extract hello 8268 heiwv`", parse_mode='Markdown')
            return
        
        # Tìm tất cả số trong văn bản
        numbers = re.findall(r'\b\d+\b', text)
        
        if numbers:
            response = f"📊 **Trích xuất từ:** `{text}`\n\n"
            response += f"🔢 **Mã số tìm được:**\n"
            for i, num in enumerate(numbers, 1):
                response += f"{i}. `{num}`\n"
            
            response += f"\n✅ **Mã chính:** `{numbers[0]}`"
        else:
            response = f"❌ Không tìm thấy mã số nào trong: `{text}`"
        
        bot.reply_to(message, response, parse_mode='Markdown')
        
    except Exception as e:
        bot.reply_to(message, f"❌ Lỗi: {str(e)}")

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    """Xử lý tất cả tin nhắn khác"""
    if message.text.startswith('/'):
        return
    
    # Kiểm tra nếu tin nhắn chứa số
    numbers = re.findall(r'\b\d+\b', message.text)
    if numbers:
        response = f"🔍 Tìm thấy {len(numbers)} mã số:\n"
        for i, num in enumerate(numbers, 1):
            response += f"{i}. `{num}`\n"
        response += "\n👉 Sử dụng các nút bên dưới để tạo email và kiểm tra inbox!"
    else:
        response = "👉 Sử dụng các nút bên dưới để thao tác:"
    
    bot.send_message(
        message.chat.id,
        response,
        reply_markup=create_main_keyboard()
    )

def run_bot():
    """Chạy bot Telegram trong thread riêng"""
    print("🤖 Bot Telegram đang chạy...")
    print("📧 Bot tạo email 10 phút với trích xuất mã số")
    print(f"🔑 Token: {BOT_TOKEN[:10]}...")
    
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        print(f"Lỗi Telegram bot: {e}")

@app.route('/')
def home():
    """Trang chủ hiển thị trạng thái bot"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Telegram Bot - Email 10 Phút</title>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                margin: 0;
                padding: 20px;
            }
            .container {
                background: white;
                border-radius: 20px;
                padding: 40px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                max-width: 800px;
                width: 100%;
                text-align: center;
            }
            h1 {
                color: #333;
                margin-bottom: 10px;
                font-size: 2.5em;
            }
            .status {
                background: #4CAF50;
                color: white;
                padding: 10px 20px;
                border-radius: 50px;
                display: inline-block;
                margin: 20px 0;
                font-weight: bold;
                animation: pulse 2s infinite;
            }
            @keyframes pulse {
                0% { transform: scale(1); }
                50% { transform: scale(1.05); }
                100% { transform: scale(1); }
            }
            .bot-info {
                background: #f5f5f5;
                border-radius: 10px;
                padding: 20px;
                margin: 20px 0;
                text-align: left;
            }
            .feature-list {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin: 30px 0;
            }
            .feature {
                background: linear-gradient(45deg, #f3f4f6, #e5e7eb);
                padding: 20px;
                border-radius: 10px;
                text-align: left;
            }
            .telegram-link {
                display: inline-block;
                background: #0088cc;
                color: white;
                padding: 15px 30px;
                border-radius: 10px;
                text-decoration: none;
                font-weight: bold;
                font-size: 1.2em;
                margin-top: 20px;
                transition: transform 0.3s;
            }
            .telegram-link:hover {
                transform: translateY(-5px);
                background: #006699;
            }
            .instruction {
                background: #fff3cd;
                border-left: 4px solid #ffc107;
                padding: 15px;
                margin: 20px 0;
                border-radius: 5px;
                text-align: left;
            }
            .footer {
                margin-top: 30px;
                color: #666;
                font-size: 0.9em;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 Telegram Bot</h1>
            <h2>Email 10 Phút</h2>
            
            <div class="status">🟢 Bot đang hoạt động</div>
            
            <div class="bot-info">
                <h3>📋 Thông tin Bot</h3>
                <p><strong>Tên:</strong> 𝗕𝗢𝗧 𝟭𝟬𝗣 </p>
                <p><strong>Token:</strong> {{BOT_TOKEN}}</p>
                <p><strong>Triển khai:</strong> Render.com</p>
                <p><strong>Thời gian chạy:</strong> 24/7</p>
            </div>
            
            <div class="instruction">
                <h4>📝 Hướng dẫn sử dụng:</h4>
                <p>1. Mở Telegram và tìm bot: <strong>@Email10PBot</strong></p>
                <p>2. Gửi lệnh <code>/start</code> để bắt đầu</p>
                <p>3. Sử dụng các nút chức năng để tạo email và kiểm tra hộp thư</p>
            </div>
            
            <div class="feature-list">
                <div class="feature">
                    <h4>📧 Tạo Email</h4>
                    <p>Tạo email 10 phút tự động với nhiều domain</p>
                </div>
                <div class="feature">
                    <h4>📬 Kiểm Tra Inbox</h4>
                    <p>Xem email và trích xuất mã số tự động</p>
                </div>
                <div class="feature">
                    <h4>🔢 Trích Xuất Số</h4>
                    <p>Tự động tìm và trích xuất số từ tin nhắn</p>
                </div>
            </div>
            
            <a href="https://t.me/Email10PBot" class="telegram-link" target="_blank">
                🚀 Bắt đầu với Bot trên Telegram
            </a>
            
            <div class="footer">
                <p>Bot được triển khai trên Render.com | Luôn hoạt động 24/7</p>
                <p>© 2024 Email 10 Phút Bot</p>
            </div>
        </div>
        
        <script>
            // Cập nhật thời gian hoạt động
            function updateUptime() {
                const startTime = Date.now();
                setInterval(() => {
                    const uptime = Date.now() - startTime;
                    const hours = Math.floor(uptime / (1000 * 60 * 60));
                    const minutes = Math.floor((uptime % (1000 * 60 * 60)) / (1000 * 60));
                    document.getElementById('uptime').textContent = 
                        `${hours} giờ ${minutes} phút`;
                }, 60000);
            }
            
            document.addEventListener('DOMContentLoaded', updateUptime);
        </script>
    </body>
    </html>
    """
    
    # Ẩn phần token
    masked_token = f"{BOT_TOKEN[:10]}...{BOT_TOKEN[-4:]}" if len(BOT_TOKEN) > 14 else "***"
    
    return render_template_string(html_content.replace("{{BOT_TOKEN}}", masked_token))

@app.route('/health')
def health_check():
    """Endpoint kiểm tra sức khỏe cho Render"""
    return {"status": "healthy", "service": "telegram-bot", "bot": "Email10Phut"}

def start_app():
    """Khởi động web server và bot"""
    # Chạy bot Telegram trong thread riêng
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Chạy web server
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

if __name__ == '__main__':
    start_app()
