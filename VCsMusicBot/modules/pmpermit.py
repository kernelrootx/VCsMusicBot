from pyrogram import Client
import asyncio
from VCsMusicBot.config import SUDO_USERS, PMPERMIT
from pyrogram import filters
from pyrogram.types import Message
from VCsMusicBot.services.callsmusic.callsmusic import client as USER

PMSET =True
pchats = []

@USER.on_message(filters.text & filters.private & ~filters.me & ~filters.bot)
async def pmPermit(client: USER, message: Message):
    if PMPERMIT == "ENABLE":
        if PMSET:
            chat_id = message.chat.id
            if chat_id in pchats:
                return
            await USER.send_message(
                message.chat.id,
                "Merhaba, Ben @Zencilermuzikbot'un Asistanıyım.\n\n ❗️ Kurallar:\n   - Bu Hesap Sohbet İçin Değil\n   - Spam Yasak \n\n 👉 **GRUP LİNKİNİ VEYA GRUP KULLANICI ADINI AT.**\n\n ⚠️ Uyarı: Attığın Her Mesajı Botun Sahibi @ex0rc1st0 Görüyor.\n    - Gizli Gruplara Girmez.\n   - Gizli Grup Linki Atmayın.\n\n**İletişim için @ex0rc1st0.\n\nGrubumuz** https://t.me/zenciler_federasyonu",
            )
            return

    

@Client.on_message(filters.command(["/pmpermit"]))
async def bye(client: Client, message: Message):
    if message.from_user.id in SUDO_USERS:
        global PMSET
        text = message.text.split(" ", 1)
        queryy = text[1]
        if queryy == "on":
            PMSET = True
            await message.reply_text("Pmpermit Açık")
            return
        if queryy == "off":
            PMSET = None
            await message.reply_text("Pmpermit Kapalı")
            return

@USER.on_message(filters.text & filters.private & filters.me)        
async def autopmPermiat(client: USER, message: Message):
    chat_id = message.chat.id
    if not chat_id in pchats:
        pchats.append(chat_id)
        await message.reply_text("PM'ye İzin Veriliyor")
        return
    message.continue_propagation()    
    
@USER.on_message(filters.command("a", [".", ""]) & filters.me & filters.private)
async def pmPermiat(client: USER, message: Message):
    chat_id = message.chat.id
    if not chat_id in pchats:
        pchats.append(chat_id)
        await message.reply_text("PM'ye İzin Verildi")
        return
    message.continue_propagation()    
    

@USER.on_message(filters.command("da", [".", ""]) & filters.me & filters.private)
async def rmpmPermiat(client: USER, message: Message):
    chat_id = message.chat.id
    if chat_id in pchats:
        pchats.remove(chat_id)
        await message.reply_text("PM'ye İzin Verilmiyor")
        return
    message.continue_propagation()
