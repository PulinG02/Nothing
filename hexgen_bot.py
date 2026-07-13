# hexgen_bot.py
# pip install pyTelegramBotAPI

import telebot
import io
from pathlib import Path
from datetime import datetime

BOT_TOKEN = "8969703979:AAHvyshluyE3ULR9p8Vyt82NasuhXW2F6JM"

bot = telebot.TeleBot(BOT_TOKEN)

# ================= Core =================
def generate_guard(name: str) -> str:
    return name.upper().replace(".", "_").replace("-", "_")

def img_to_header(data: bytes, array_name: str, guard_name: str, bytes_per_line: int) -> str:
    lines = []
    lines.append("// -----------------------------------")
    lines.append("// Auto-generated header")
    lines.append("// Author: Lyc4nLD")
    lines.append("// -----------------------------------\n")
    lines.append(f"#ifndef {guard_name}")
    lines.append(f"#define {guard_name}\n")
    lines.append(f"static const unsigned char {array_name}[] = {{")

    for i in range(0, len(data), bytes_per_line):
        chunk = data[i:i + bytes_per_line]
        hex_line = ", ".join(f"0x{b:02X}" for b in chunk)
        lines.append(f"    {hex_line},")

    lines.append("};")
    lines.append(f"\nstatic const unsigned int {array_name}_len = sizeof({array_name});\n")
    lines.append(f"#endif // {guard_name}")

    return "\n".join(lines)

def human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.2f} {unit}"
        n /= 1024
    return f"{n:.2f} TB"

# ================= Bot Handlers =================
@bot.message_handler(commands=['start', 'help'])
def send_welcome(msg):
    bot.reply_to(msg,
        "⚡ HexGen Bot\n\n"
        "Send any image or binary file and I'll convert it to a C/C++ header (.h)\n\n"
        "Commands:\n"
        "/start - Help\n"
        "/setname [name] - Set array name (default: Logo_data)\n"
        "/setbpl [number] - Set bytes per line (default: 16)")

# Store per-user settings
user_settings = {}

def get_settings(user_id):
    return user_settings.get(user_id, {
        'array_name': 'Logo_data',
        'bytes_per_line': 16
    })

@bot.message_handler(commands=['setname'])
def set_name(msg):
    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(msg, "❌ Usage: /setname MyArray")
        return
    name = parts[1].strip()
    settings = get_settings(msg.from_user.id)
    settings['array_name'] = name
    user_settings[msg.from_user.id] = settings
    bot.reply_to(msg, f"✅ Array name set to: {name}")

@bot.message_handler(commands=['setbpl'])
def set_bpl(msg):
    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip().isdigit():
        bot.reply_to(msg, "❌ Usage: /setbpl 16")
        return
    bpl = int(parts[1].strip())
    if bpl < 1 or bpl > 64:
        bot.reply_to(msg, "❌ Bytes per line must be 1-64.")
        return
    settings = get_settings(msg.from_user.id)
    settings['bytes_per_line'] = bpl
    user_settings[msg.from_user.id] = settings
    bot.reply_to(msg, f"✅ Bytes per line set to: {bpl}")

@bot.message_handler(content_types=['document', 'photo'])
def handle_file(message):
    chat_id = message.chat.id
    settings = get_settings(message.from_user.id)

    # Get file info
    if message.content_type == 'photo':
        file_obj = message.photo[-1]  # highest resolution
        filename = "image.jpg"
    else:
        file_obj = message.document
        filename = file_obj.file_name or "file.bin"

    file_size_mb = (file_obj.file_size or 0) / (1024 * 1024)
    if file_size_mb > 20:
        bot.reply_to(message, f"❌ File too large ({file_size_mb:.1f}MB). Max 20MB lang.")
        return

    bot.send_message(chat_id, f"⏳ Converting {filename}...")

    # Download
    file_info = bot.get_file(file_obj.file_id)
    file_bytes = bot.download_file(file_info.file_path)

    array_name = settings['array_name']
    bytes_per_line = settings['bytes_per_line']
    guard_name = generate_guard(Path(filename).stem + "_h")

    # Convert
    header_content = img_to_header(file_bytes, array_name, guard_name, bytes_per_line)

    # Send as .h file
    output_name = Path(filename).stem + ".h"
    header_bytes = io.BytesIO(header_content.encode('utf-8'))
    header_bytes.name = output_name

    summary = (
        f"✅ Done!\n\n"
        f"📄 File: {filename}\n"
        f"📦 Size: {human_size(len(file_bytes))}\n"
        f"🔢 Bytes: {len(file_bytes)}\n"
        f"📝 Array: {array_name}[]\n"
        f"🛡 Guard: {guard_name}\n"
        f"📏 Bytes/line: {bytes_per_line}"
    )
    bot.send_message(chat_id, summary)
    bot.send_document(chat_id, header_bytes)

if __name__ == "__main__":
    print("HexGen Bot started...")
    bot.infinity_polling()
