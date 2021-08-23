import json
import os
from os import path
from typing import Callable

import aiofiles
import aiohttp
import ffmpeg
import requests
import wget
from PIL import Image, ImageDraw, ImageFont
from pyrogram import Client, filters
from pyrogram.types import Voice
from pyrogram.errors import UserAlreadyParticipant
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from Python_ARQ import ARQ
from youtube_search import YoutubeSearch

from VCsMusicBot.config import ARQ_API_KEY
from VCsMusicBot.config import BOT_NAME as bn
from VCsMusicBot.config import DURATION_LIMIT
from VCsMusicBot.config import UPDATES_CHANNEL as updateschannel
from VCsMusicBot.config import que
from VCsMusicBot.function.admins import admins as a
from VCsMusicBot.helpers.admins import get_administrators
from VCsMusicBot.helpers.channelmusic import get_chat_id
from VCsMusicBot.helpers.errors import DurationLimitError
from VCsMusicBot.helpers.decorators import errors
from VCsMusicBot.helpers.decorators import authorized_users_only
from VCsMusicBot.helpers.filters import command, other_filters
from VCsMusicBot.helpers.gets import get_file_name
from VCsMusicBot.services.callsmusic import callsmusic
from VCsMusicBot.services.callsmusic.callsmusic import client as USER
from VCsMusicBot.services.converter.converter import convert
from VCsMusicBot.services.downloaders import youtube
from VCsMusicBot.services.queues import queues

aiohttpsession = aiohttp.ClientSession()
chat_id = None
arq = ARQ("https://thearq.tech", ARQ_API_KEY, aiohttpsession)
DISABLED_GROUPS = []
useer ="NaN"
def cb_admin_check(func: Callable) -> Callable:
    async def decorator(client, cb):
        admemes = a.get(cb.message.chat.id)
        if cb.from_user.id in admemes:
            return await func(client, cb)
        else:
            await cb.answer("You ain't allowed!", show_alert=True)
            return

    return decorator


def transcode(filename):
    ffmpeg.input(filename).output(
        "input.raw", format="s16le", acodec="pcm_s16le", ac=2, ar="48k"
    ).overwrite_output().run()
    os.remove(filename)


# Convert seconds to mm:ss
def convert_seconds(seconds):
    seconds = seconds % (24 * 3600)
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60
    return "%02d:%02d" % (minutes, seconds)


# Convert hh:mm:ss to seconds
def time_to_seconds(time):
    stringt = str(time)
    return sum(int(x) * 60 ** i for i, x in enumerate(reversed(stringt.split(":"))))


# Change image size
def changeImageSize(maxWidth, maxHeight, image):
    widthRatio = maxWidth / image.size[0]
    heightRatio = maxHeight / image.size[1]
    newWidth = int(widthRatio * image.size[0])
    newHeight = int(heightRatio * image.size[1])
    newImage = image.resize((newWidth, newHeight))
    return newImage


async def generate_cover(requested_by, title, views, duration, thumbnail):
    async with aiohttp.ClientSession() as session:
        async with session.get(thumbnail) as resp:
            if resp.status == 200:
                f = await aiofiles.open("background.png", mode="wb")
                await f.write(await resp.read())
                await f.close()

    image1 = Image.open("./background.png")
    image2 = Image.open("./etc/foreground.png")
    image3 = changeImageSize(1280, 720, image1)
    image4 = changeImageSize(1280, 720, image2)
    image5 = image3.convert("RGBA")
    image6 = image4.convert("RGBA")
    Image.alpha_composite(image5, image6).save("temp.png")
    img = Image.open("temp.png")
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype("etc/font.otf", 32)
    draw.text((205, 550), f"Title: {title}", (51, 215, 255), font=font)
    draw.text((205, 590), f"Duration: {duration}", (255, 255, 255), font=font)
    draw.text((205, 630), f"Views: {views}", (255, 255, 255), font=font)
    draw.text(
        (205, 670),
        f"Added By: {requested_by}",
        (255, 255, 255),
        font=font,
    )
    img.save("final.png")
    os.remove("temp.png")
    os.remove("background.png")


@Client.on_message(filters.command("oynatmalistesi") & filters.group & ~filters.edited)
async def playlist(client, message):
    global que
    if message.chat.id in DISABLED_GROUPS:
        return    
    queue = que.get(message.chat.id)
    if not queue:
        await message.reply_text("Oynatılacaklar")
    temp = []
    for t in queue:
        temp.append(t)
    now_playing = temp[0][0]
    by = temp[0][1].mention(style="md")
    msg = "**Şimdi Oynatılan** in {}".format(message.chat.title)
    msg += "\n- " + now_playing
    msg += "\n- Oynatan " + by
    temp.pop(0)
    if temp:
        msg += "\n\n"
        msg += "**Sırada**"
        for song in temp:
            name = song[0]
            usr = song[1].mention(style="md")
            msg += f"\n- {name}"
            msg += f"\n- İsteyen {usr}\n"
    await message.reply_text(msg)


# ============================= Ayarlar =========================================


def updated_stats(chat, queue, vol=100):
    if chat.id in callsmusic.active_chats:
        # if chat.id in active_chats:
        stats = "Ayarlar **{}**".format(chat.title)
        if len(que) > 0:
            stats += "\n\n"
            stats += "Ses Düzeyi : {}%\n".format(vol)
            stats += "Şarkı Sırası : `{}`\n".format(len(que))
            stats += "Şimdi  Oynatılan : **{}**\n".format(queue[0][0])
            stats += "İsteyen : {}".format(queue[0][1].mention)
    else:
        stats = None
    return stats


def r_ply(type_):
    if type_ == "Oynat":
        pass
    else:
        pass
    mar = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("⏹", "Bitir"),
                InlineKeyboardButton("⏸", "Durdur"),
                InlineKeyboardButton("▶️", "Devam"),
                InlineKeyboardButton("⏭", "Atla"),
            ],
            [
                InlineKeyboardButton("Oynatma Listesi 📖", "playlist"),
            ],
            [InlineKeyboardButton("❌ Kapat", "cls")],
        ]
    )
    return mar


@Client.on_message(filters.command("mevcutşarkı") & filters.group & ~filters.edited)
async def ee(client, message):
    if message.chat.id in DISABLED_GROUPS:
        return
    queue = que.get(message.chat.id)
    stats = updated_stats(message.chat, queue)
    if stats:
        await message.reply(stats)
    else:
        await message.reply("Bot Şuan Şarkı Oynatmıyor")


@Client.on_message(filters.command("oynatıcı") & filters.group & ~filters.edited)
@authorized_users_only
async def settings(client, message):
    if message.chat.id in DISABLED_GROUPS:
        await message.reply("Müzik Botu Devre Dışı")
        return    
    playing = None
    chat_id = get_chat_id(message.chat)
    if chat_id in callsmusic.active_chats:
        playing = True
    queue = que.get(chat_id)
    stats = updated_stats(message.chat, queue)
    if stats:
        if playing:
            await message.reply(stats, reply_markup=r_ply("Durdur")) 
        else:
            await message.reply(stats, reply_markup=r_ply("Oynat"))
    else:
        await message.reply("Bot Şuan Şarkı Oynatmıyor")


@Client.on_message(
    filters.command("müzikoynatıcı") & ~filters.edited & ~filters.bot & ~filters.private
)
@authorized_users_only
async def hfmm(_, message):
    global DISABLED_GROUPS
    try:
        user_id = message.from_user.id
    except:
        return
    if len(message.command) != 2:
        await message.reply_text(
            "Sadece `/müzikoynatıcı açık` veya /müzikoynatıcı `kapalı ` Yazın"
        )
        return
    status = message.text.split(None, 1)[1]
    message.chat.id
    if status == "AÇIK" or status == "açık" or status == "Açık":
        lel = await message.reply("`İşleniyor...`")
        if not message.chat.id in DISABLED_GROUPS:
            await lel.edit("Müzik Botu Zaten Aktif")
            return
        DISABLED_GROUPS.remove(message.chat.id)
        await lel.edit(
            f"Müzik Botu Aktifleştirildi {message.chat.id}"
        )

    elif status == "KAPALI" or status == "kapalı" or status == "Kapalı":
        lel = await message.reply("`İşleniyor...`")
        
        if message.chat.id in DISABLED_GROUPS:
            await lel.edit("Müzik Botu Zaten Devredışı")
            return
        DISABLED_GROUPS.append(message.chat.id)
        await lel.edit(
            f"Müzik Botu Devredışı Bırakıldı {message.chat.id}"
        )
    else:
        await message.reply_text(
            "Sadece `/müzikoynatıcı açık` veya /müzikoynatıcı `kapalı ` Yazın"
        )    
        

@Client.on_callback_query(filters.regex(pattern=r"^(oynatmalistesi)$"))
async def p_cb(b, cb):
    global que
    que.get(cb.message.chat.id)
    type_ = cb.matches[0].group(1)
    cb.message.chat.id
    cb.message.chat
    cb.message.reply_markup.inline_keyboard[1][0].callback_data
    if type_ == "playlist":
        queue = que.get(cb.message.chat.id)
        if not queue:
            await cb.message.edit("Oynatma Listesi Boş")
        temp = []
        for t in queue:
            temp.append(t)
        now_playing = temp[0][0]
        by = temp[0][1].mention(style="md")
        msg = "<b>Şimdi Oynatılan</b> in {}".format(cb.message.chat.title)
        msg += "\n- " + now_playing
        msg += "\n- İsteyen " + by
        temp.pop(0)
        if temp:
            msg += "\n\n"
            msg += "**Sıradaki**"
            for song in temp:
                name = song[0]
                usr = song[1].mention(style="md")
                msg += f"\n- {name}"
                msg += f"\n- İsteyen {usr}\n"
        await cb.message.edit(msg)


@Client.on_callback_query(
    filters.regex(pattern=r"^(oynat|durdur|atla|bitir|durdur|devam|menu|cls)$")
)
@cb_admin_check
async def m_cb(b, cb):
    global que
    if (
        cb.message.chat.title.startswith("Kanal Müzik: ")
        and chat.title[14:].isnumeric()
    ):
        chet_id = int(chat.title[13:])
    else:
        chet_id = cb.message.chat.id
    qeue = que.get(chet_id)
    type_ = cb.matches[0].group(1)
    cb.message.chat.id
    m_chat = cb.message.chat

    the_data = cb.message.reply_markup.inline_keyboard[1][0].callback_data
    if type_ == "durdur":
        if (chet_id not in callsmusic.active_chats) or (
            callsmusic.active_chats[chet_id] == "durduruldu"
        ):
            await cb.answer("Chat Bağlı Değil!", show_alert=True)
        else:
            callsmusic.pause(chet_id)
            await cb.answer("Müzik Durduruldu!")
            await cb.message.edit(
                updated_stats(m_chat, qeue), reply_markup=r_ply("oynat")
            )

    elif type_ == "oynat":
        if (chet_id not in callsmusic.active_chats) or (
            callsmusic.active_chats[chet_id] == "oynatılıyor"
        ):
            await cb.answer("Chat Bağlı Değil!", show_alert=True)
        else:
            callsmusic.resume(chet_id)
            await cb.answer("Müzik Devam Ediyor!")
            await cb.message.edit(
                updated_stats(m_chat, qeue), reply_markup=r_ply("durdur")
            )

    elif type_ == "oynatmalistesi":
        queue = que.get(cb.message.chat.id)
        if not queue:
            await cb.message.edit("Oynatma Listesi Boş")
        temp = []
        for t in queue:
            temp.append(t)
        now_playing = temp[0][0]
        by = temp[0][1].mention(style="md")
        msg = "**Now Playing** in {}".format(cb.message.chat.title)
        msg += "\n- " + now_playing
        msg += "\n- İsteyen " + by
        temp.pop(0)
        if temp:
            msg += "\n\n"
            msg += "**Sıradaki**"
            for song in temp:
                name = song[0]
                usr = song[1].mention(style="md")
                msg += f"\n- {name}"
                msg += f"\n- İsteyen {usr}\n"
        await cb.message.edit(msg)

    elif type_ == "devam":
        if (chet_id not in callsmusic.active_chats) or (
            callsmusic.active_chats[chet_id] == "oynatılıyor"
        ):
            await cb.answer("Chat Bağlı Değil Veya Zaten Oynatılıyor", show_alert=True)
        else:
            callsmusic.resume(chet_id)
            await cb.answer("Müzik Devam Ediyor!")
    elif type_ == "puse":
        if (chet_id not in callsmusic.active_chats) or (
            callsmusic.active_chats[chet_id] == "durduruldu"
        ):
            await cb.answer("Chat Bağlı Değil Veya Zaten Durduruldu", show_alert=True)
        else:
            callsmusic.pause(chet_id)
            await cb.answer("Müzik Durduruldu!")
    elif type_ == "cls":
        await cb.answer("Menü Kapatıldı")
        await cb.message.delete()

    elif type_ == "menu":
        stats = updated_stats(cb.message.chat, qeue)
        await cb.answer("Menü Açıldı")
        marr = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("⏹", "bitir"),
                    InlineKeyboardButton("⏸", "durdur"),
                    InlineKeyboardButton("▶️", "devam"),
                    InlineKeyboardButton("⏭", "atla"),
                ],
                [
                    InlineKeyboardButton("Oynatma Listesi 📖", "playlist"),
                ],
                [InlineKeyboardButton("❌ Kapat", "cls")],
            ]
        )
        await cb.message.edit(stats, reply_markup=marr)
    elif type_ == "atla":
        if qeue:
            qeue.pop(0)
        if chet_id not in callsmusic.active_chats:
            await cb.answer("Chat Bağlı Değil!", show_alert=True)
        else:
            queues.task_done(chet_id)
            if queues.is_empty(chet_id):
                callsmusic.stop(chet_id)
                await cb.message.edit("- Başka Oynatılacak Bir Şey Yok..\n- Müzil Bitirildi!")
            else:
                await callsmusic.set_stream(
                    chet_id, queues.get(chet_id)["file"]
                )
                await cb.answer.reply_text("✅ <b>Atlandı</b>")
                await cb.message.edit((m_chat, qeue), reply_markup=r_ply(the_data))
                await cb.message.reply_text(
                    f"- Atlandı\n- Şimdi Oynatılan **{qeue[0][0]}**"
                )

    else:
        if chet_id in callsmusic.active_chats:
            try:
               queues.clear(chet_id)
            except QueueEmpty:
                pass

            await callsmusic.stop(chet_id)
            await cb.message.edit("Chatten Başarıyla Ayrıldı!")
        else:
            await cb.answer("Chat Bağlı Değil!", show_alert=True)


@Client.on_message(command("oynat") & other_filters)
async def play(_, message: Message):
    global que
    global useer
    if message.chat.id in DISABLED_GROUPS:
        return    
    lel = await message.reply("🔄 <b>İşleniyor</b>")
    administrators = await get_administrators(message.chat)
    chid = message.chat.id

    try:
        user = await USER.get_me()
    except:
        user.first_name = "@zencilermuzikasistani"
    usar = user
    wew = usar.id
    try:
        # chatdetails = await USER.get_chat(chid)
        await _.get_chat_member(chid, wew)
    except:
        for administrator in administrators:
            if administrator == message.from_user.id:
                if message.chat.title.startswith("Müzik Kanalı: "):
                    await lel.edit(
                        "<b>Asistanı Kanala Almayı Unutma</b>",
                    )
                    pass
                try:
                    invitelink = await _.export_chat_invite_link(chid)
                except:
                    await lel.edit(
                        "<b>Öncelikle Beni Grupta Admin Yap</b>",
                    )
                    return

                try:
                    await USER.join_chat(invitelink)
                    await USER.send_message(
                        message.chat.id, "Müzik Oynatmak İçin Gruba Girdim"
                    )
                    await lel.edit(
                        "<b>Asistan Gruba Katıldı</b>",
                    )

                except UserAlreadyParticipant:
                    pass
                except Exception:
                    # print(e)
                    await lel.edit(
                        f"<b>🔴 Zaman Aşımı Hatası 🔴 \n {user.first_name} Asistan için yoğun katılma istekleri nedeniyle grubunuza katılamadı! Asistanın grupta yasaklanmadığından emin olun."
                        "\n\nVeya @zencilermuzikasistani Hesabını Gruba Kendin Ekle</b>",
                    )
    try:
        await USER.get_chat(chid)
        # lmoa = await client.get_chat_member(chid,wew)
    except:
        await lel.edit(
            f"<i> {user.first_name} Asistan Chatte Değil, /oynat komutunu kullan veya {user.first_name} asistanı kendin ekle</i>"
        )
        return
    text_links=None
    await lel.edit("🔎 <b>Aranıyor</b>")
    if message.reply_to_message:
        if message.reply_to_message.audio:
            pass
        entities = []
        toxt = message.reply_to_message.text \
              or message.reply_to_message.caption
        if message.reply_to_message.entities:
            entities = message.reply_to_message.entities + entities
        elif message.reply_to_message.caption_entities:
            entities = message.reply_to_message.entities + entities
        urls = [entity for entity in entities if entity.type == 'url']
        text_links = [
            entity for entity in entities if entity.type == 'text_link'
        ]
    else:
        urls=None
    if text_links:
        urls = True
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    rpk = "[" + user_name + "](tg://user?id=" + str(user_id) + ")"
    audio = (
        (message.reply_to_message.audio or message.reply_to_message.voice)
        if message.reply_to_message
        else None
    )
    if audio:
        if round(audio.duration / 60) > DURATION_LIMIT:
            await lel.edit(
                f"❌ Müzik {DURATION_LIMIT} dakikadan uzun, bunu oynatamam!"
            )
            return
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("📖 Oynatma Listesi", callback_data="playlist"),
                    InlineKeyboardButton("Menü ⏯ ", callback_data="menu"),
                ],
                [InlineKeyboardButton(text="❌ Kapat", callback_data="cls")],
            ]
        )
        file_name = get_file_name(audio)
        title = file_name
        thumb_name = "https://telegra.ph/file/cddcda16e60d4696c725f.jpg"
        thumbnail = thumb_name
        duration = round(audio.duration / 60)
        views = "Locale Eklendi"
        requested_by = message.from_user.first_name
        await generate_cover(requested_by, title, views, duration, thumbnail)
        file_path = await convert(
            (await message.reply_to_message.download(file_name))
            if not path.isfile(path.join("downloads", file_name))
            else file_name
        )
    elif urls:
        query = toxt
        await lel.edit("🎵 <b>İşleniyor</b>")
        ydl_opts = {"format": "bestaudio[ext=m4a]"}
        try:
            results = YoutubeSearch(query, max_results=1).to_dict()
            url = f"https://youtube.com{results[0]['url_suffix']}"
            # print(results)
            title = results[0]["title"][:40]
            thumbnail = results[0]["thumbnails"][0]
            thumb_name = f"thumb{title}.jpg"
            thumb = requests.get(thumbnail, allow_redirects=True)
            open(thumb_name, "wb").write(thumb.content)
            duration = results[0]["duration"]
            results[0]["url_suffix"]
            views = results[0]["views"]

        except Exception as e:
            await lel.edit(
                "Şarkı Bulunamadı Belki Başka Kelimelerle Arayarak Bulabilirsin."
            )
            print(str(e))
            return
        try:    
            secmul, dur, dur_arr = 1, 0, duration.split(':')
            for i in range(len(dur_arr)-1, -1, -1):
                dur += (int(dur_arr[i]) * secmul)
                secmul *= 60
            if (dur / 60) > DURATION_LIMIT:
                 await lel.edit(f"❌ Müzik {DURATION_LIMIT}  dakikadan uzun, bunu oynatamam!")
                 return
        except:
            pass        
        dlurl=url
        dlurl=dlurl.replace("youtube","youtubepp")
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("📖 Oynatma Listesi", callback_data="playlist"),
                    InlineKeyboardButton("Menü ⏯ ", callback_data="menu"),
                ],
                [
                    InlineKeyboardButton(text="🎬 YouTube", url=f"{url}"),
                    InlineKeyboardButton(text="İndir 📥", url=f"{dlurl}"),
                ],
                [InlineKeyboardButton(text="❌ Kapat", callback_data="cls")],
            ]
        )
        requested_by = message.from_user.first_name
        await generate_cover(requested_by, title, views, duration, thumbnail)
        file_path = await convert(youtube.download(url))        
    else:
        query = ""
        for i in message.command[1:]:
            query += " " + str(i)
        print(query)
        await lel.edit("🎵 **İşleniyor**")
        ydl_opts = {"format": "bestaudio[ext=m4a]"}
        
        try:
          results = YoutubeSearch(query, max_results=5).to_dict()
        except:
          await lel.edit("Bana Oynatacak Bir Şeyler Ver")
        # Cehenneme Bakıyorsun. Farkında Değil misin?? SİKTİR GİT
        try:
            toxxt = "**Hangisini Oynatmak İstediğini Seç**\n\n"
            j = 0
            useer=user_name
            emojilist = ["1️⃣","2️⃣","3️⃣","4️⃣","5️⃣",]

            while j < 5:
                toxxt += f"{emojilist[j]} <b>Başlık - [{results[j]['title']}](https://youtube.com{results[j]['url_suffix']})</b>\n"
                toxxt += f" ╚ <b>Süre</b> - {results[j]['duration']}\n"
                toxxt += f" ╚ <b>Görüntülenme</b> - {results[j]['views']}\n"
                toxxt += f" ╚ <b>Kanal</b> - {results[j]['channel']}\n\n"

                j += 1            
            koyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("1️⃣", callback_data=f'plll 0|{query}|{user_id}'),
                        InlineKeyboardButton("2️⃣", callback_data=f'plll 1|{query}|{user_id}'),
                        InlineKeyboardButton("3️⃣", callback_data=f'plll 2|{query}|{user_id}'),
                    ],
                    [
                        InlineKeyboardButton("4️⃣", callback_data=f'plll 3|{query}|{user_id}'),
                        InlineKeyboardButton("5️⃣", callback_data=f'plll 4|{query}|{user_id}'),
                    ],
                    [InlineKeyboardButton(text="❌", callback_data="cls")],
                ]
            )       
            await lel.edit(toxxt,reply_markup=koyboard,disable_web_page_preview=True)
            # Elim Koptu Mk Sikerim ??
            return
            # Ananın Amına Dön Yeter
        except:
            await lel.edit("Seçecek Bir Şey Yok.. Direk Oynatıyorum..")
                        
            # print(results)
            try:
                url = f"https://youtube.com{results[0]['url_suffix']}"
                title = results[0]["title"][:40]
                thumbnail = results[0]["thumbnails"][0]
                thumb_name = f"thumb{title}.jpg"
                thumb = requests.get(thumbnail, allow_redirects=True)
                open(thumb_name, "wb").write(thumb.content)
                duration = results[0]["duration"]
                results[0]["url_suffix"]
                views = results[0]["views"]

            except Exception as e:
                await lel.edit(
                    "Şarkı Bulunamadı Belki Başka Kelimelerle Arayarak Bulabilirsin."
                )
                print(str(e))
                return
            try:    
                secmul, dur, dur_arr = 1, 0, duration.split(':')
                for i in range(len(dur_arr)-1, -1, -1):
                    dur += (int(dur_arr[i]) * secmul)
                    secmul *= 60
                if (dur / 60) > DURATION_LIMIT:
                     await lel.edit(f"❌ Müzik {DURATION_LIMIT} dakikadan uzun, bunu oynatamam!")
                     return
            except:
                pass
            dlurl=url
            dlurl=dlurl.replace("youtube","youtubepp")
            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("📖 Oynatma Listesi", callback_data="playlist"),
                        InlineKeyboardButton("Menü ⏯ ", callback_data="menu"),
                    ],
                    [
                        InlineKeyboardButton(text="🎬 YouTube", url=f"{url}"),
                        InlineKeyboardButton(text="İndir 📥", url=f"{dlurl}"),
                    ],
                    [InlineKeyboardButton(text="❌ Kapaat", callback_data="cls")],
                ]
            )
            requested_by = message.from_user.first_name
            await generate_cover(requested_by, title, views, duration, thumbnail)
            file_path = await convert(youtube.download(url))   
    chat_id = get_chat_id(message.chat)
    if chat_id in callsmusic.active_chats:
        position = await queues.put(chat_id, file=file_path)
        qeue = que.get(chat_id)
        s_name = title
        r_by = message.from_user
        loc = file_path
        appendable = [s_name, r_by, loc]
        qeue.append(appendable)
        await message.reply_photo(
            photo="final.png",
            caption=f"#⃣ İstediğin Şarkı <b>Sırada</b> Sırası {position}!",
            reply_markup=keyboard,
        )
        os.remove("final.png")
        return await lel.delete()
    else:
        chat_id = get_chat_id(message.chat)
        que[chat_id] = []
        qeue = que.get(chat_id)
        s_name = title
        r_by = message.from_user
        loc = file_path
        appendable = [s_name, r_by, loc]
        qeue.append(appendable)
        try:
            await callsmusic.set_stream(chat_id, file_path)
        except:
            message.reply("Sesli Sohbete Bağlanamadım Veya Giremiyorum")
            return
        await message.reply_photo(
            photo="final.png",
            reply_markup=keyboard,
            caption="▶️ <b>Oynatılıyor</b> İstenilen Şarkı, İsteyen by {} Üzerinden YouTube Music".format(
                message.from_user.mention()
            ),
        )
        os.remove("final.png")
        return await lel.delete()


@Client.on_message(filters.command("ytoynat") & filters.group & ~filters.edited)
async def ytplay(_, message: Message):
    global que
    if message.chat.id in DISABLED_GROUPS:
        return
    lel = await message.reply("🔄 <b>İşleniyor</b>")
    administrators = await get_administrators(message.chat)
    chid = message.chat.id

    try:
        user = await USER.get_me()
    except:
        user.first_name = "@zencilermuzikasistani"
    usar = user
    wew = usar.id
    try:
        # chatdetails = await USER.get_chat(chid)
        await _.get_chat_member(chid, wew)
    except:
        for administrator in administrators:
            if administrator == message.from_user.id:
                if message.chat.title.startswith("Müzik Kanalı: "):
                    await lel.edit(
                        "<b>Asistanı Gruba Eklemeyi Unutmayın</b>",
                    )
                    pass
                try:
                    invitelink = await _.export_chat_invite_link(chid)
                except:
                    await lel.edit(
                        "<b>Öncelikle Beni Grupta Admin Yapın</b>",
                    )
                    return

                try:
                    await USER.join_chat(invitelink)
                    await USER.send_message(
                        message.chat.id, "Gruba Müzik Oynatmak İçin Girdim"
                    )
                    await lel.edit(
                        "<b>Asistan Gruba Geldi</b>",
                    )

                except UserAlreadyParticipant:
                    pass
                except Exception:
                    # print(e)
                    await lel.edit(
                        f"<b>🔴 Zaman Aşımı Hatası 🔴 \n {user.first_name} Asistan için yoğun katılma istekleri nedeniyle grubunuza katılamadı! Asistanın grupta yasaklanmadığından emin olun."
                        "\n\nVeya @zencilermuzikasistani Hesabını Gruba Kendin Ekle</b>",
                    )
    try:
        await USER.get_chat(chid)
        # lmoa = await client.get_chat_member(chid,wew)
    except:
        await lel.edit(
            f"<i> {user.first_name} Asistan Chatte Değil, /oynat komutunu kullan veya {user.first_name} asistanı kendin ekle</i>"
        )
        return
    await lel.edit("🔎 <b>Aranıyor</b>")
    user_id = message.from_user.id
    user_name = message.from_user.first_name
     

    query = ""
    for i in message.command[1:]:
        query += " " + str(i)
    print(query)
    await lel.edit("🎵 <b>İşleniyor</b>")
    ydl_opts = {"format": "bestaudio[ext=m4a]"}
    try:
        results = YoutubeSearch(query, max_results=1).to_dict()
        url = f"https://youtube.com{results[0]['url_suffix']}"
        # print(results)
        title = results[0]["title"][:40]
        thumbnail = results[0]["thumbnails"][0]
        thumb_name = f"thumb{title}.jpg"
        thumb = requests.get(thumbnail, allow_redirects=True)
        open(thumb_name, "wb").write(thumb.content)
        duration = results[0]["duration"]
        results[0]["url_suffix"]
        views = results[0]["views"]

    except Exception as e:
        await lel.edit(
            "Şarkı Bulunamadı Belki Başka Kelimelerle Arayarak Bulabilirsin."
        )
        print(str(e))
        return
    try:    
        secmul, dur, dur_arr = 1, 0, duration.split(':')
        for i in range(len(dur_arr)-1, -1, -1):
            dur += (int(dur_arr[i]) * secmul)
            secmul *= 60
        if (dur / 60) > DURATION_LIMIT:
             await lel.edit(f"❌ Müzik {DURATION_LIMIT} dakikadan uzun, bunu oynatamam!")
             return
    except:
        pass    
    dlurl=url
    dlurl=dlurl.replace("youtube","youtubepp")
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("📖 Oynatma Listesi", callback_data="playlist"),
                InlineKeyboardButton("Menü ⏯ ", callback_data="menu"),
            ],
            [
                InlineKeyboardButton(text="🎬 YouTube", url=f"{url}"),
                InlineKeyboardButton(text="İndir 📥", url=f"{dlurl}"),
            ],
            [InlineKeyboardButton(text="❌ Kapat", callback_data="cls")],
        ]
    )
    requested_by = message.from_user.first_name
    await generate_cover(requested_by, title, views, duration, thumbnail)
    file_path = await convert(youtube.download(url))
    chat_id = get_chat_id(message.chat)
    if chat_id in callsmusic.active_chats:
        position = await queues.put(chat_id, file=file_path)
        qeue = que.get(chat_id)
        s_name = title
        r_by = message.from_user
        loc = file_path
        appendable = [s_name, r_by, loc]
        qeue.append(appendable)
        await message.reply_photo(
            photo="final.png",
            caption=f"#▶️ İstediğin Şarkı <b>Sıraya Alındı</b> Sırası {position}!",
            reply_markup=keyboard,
        )
        os.remove("final.png")
        return await lel.delete()
    else:
        chat_id = get_chat_id(message.chat)
        que[chat_id] = []
        qeue = que.get(chat_id)
        s_name = title
        r_by = message.from_user
        loc = file_path
        appendable = [s_name, r_by, loc]
        qeue.append(appendable)
        try:
           await callsmusic.set_stream(chat_id, file_path)
        except:
            message.reply("Sesli Sohbete Bağlanamıyorum Veya Giremiyorum")
            return
        await message.reply_photo(
            photo="final.png",
            reply_markup=keyboard,
            caption="▶️ <b>Oynatılıyor</b> İstediğin Şarkı İsteyen by {} Üzerinden YouTube Music".format(
                message.from_user.mention()
            ),
        )
        os.remove("final.png")
        return await lel.delete()
    
@Client.on_message(filters.command("doynat") & filters.group & ~filters.edited)
async def deezer(client: Client, message_: Message):
    if message_.chat.id in DISABLED_GROUPS:
        return
    global que
    lel = await message_.reply("🔄 <b>İşleniyor</b>")
    administrators = await get_administrators(message_.chat)
    chid = message_.chat.id
    try:
        user = await USER.get_me()
    except:
        user.first_name = "@zencilermuzikasistani"
    usar = user
    wew = usar.id
    try:
        # chatdetails = await USER.get_chat(chid)
        await client.get_chat_member(chid, wew)
    except:
        for administrator in administrators:
            if administrator == message_.from_user.id:
                if message_.chat.title.startswith("Müzik Kanalı: "):
                    await lel.edit(
                        "<b>Asistanı Gruba Eklemeyi Unutma</b>",
                    )
                    pass
                try:
                    invitelink = await client.export_chat_invite_link(chid)
                except:
                    await lel.edit(
                        "<b>Öncelikle Beni Grupta Admin Yap</b>",
                    )
                    return

                try:
                    await USER.join_chat(invitelink)
                    await USER.send_message(
                        message_.chat.id, "Gruba Müzik Oynatmak İçin Geldim"
                    )
                    await lel.edit(
                        "<b>Asistan Gruba Geldi</b>",
                    )

                except UserAlreadyParticipant:
                    pass
                except Exception:
                    # print(e)
                    await lel.edit(
                        f"<b>🔴 Zaman Aşımı Hatası 🔴 \n {user.first_name} Asistan için yoğun katılma istekleri nedeniyle grubunuza katılamadı! Asistanın grupta yasaklanmadığından emin olun."
                        "\n\nVeya @zencilermuzikasistani Hesabını Gruba Kendin Ekle</b>",
                    )
    try:
        await USER.get_chat(chid)
        # lmoa = await client.get_chat_member(chid,wew)
    except:
        await lel.edit(
            f"<i> {user.first_name} Asistan Chatte Değil, /oynat komutunu kullan veya {user.first_name} asistanı kendin ekle</i>"
        )
        return
    requested_by = message_.from_user.first_name

    text = message_.text.split(" ", 1)
    queryy = text[1]
    query = queryy
    res = lel
    await res.edit(f"Aranıyor 🔍 Üzerinden `{queryy}` Deezer")
    try:
        songs = await arq.deezer(query,1)
        if not songs.ok:
            await message_.reply_text(songs.result)
            return
        title = songs.result[0].title
        url = songs.result[0].url
        artist = songs.result[0].artist
        duration = songs.result[0].duration
        thumbnail = "https://telegra.ph/file/cddcda16e60d4696c725f.jpg"

    except:
        await res.edit("Kütüphanede Bulunamadı, İngilizce Kullanmanı Öneririm!")
        return
    try:    
        duuration= round(duration / 60)
        if duuration > DURATION_LIMIT:
            await cb.message.edit(f"Müzik {DURATION_LIMIT} dakikadan uzun, bunu oynatamam!")
            return
    except:
        pass    
    
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("📖 Oynatma Listesi", callback_data="playlist"),
                InlineKeyboardButton("Menü ⏯ ", callback_data="menu"),
            ],
            [InlineKeyboardButton(text="Deezer'dan Dinle 🎬", url=f"{url}")],
            [InlineKeyboardButton(text="❌ Kapat", callback_data="cls")],
        ]
    )
    file_path = await convert(wget.download(url))
    await res.edit("Küçük Resim Yükleniyor")
    await generate_cover(requested_by, title, artist, duration, thumbnail)
    chat_id = get_chat_id(message_.chat)
    if chat_id in callsmusic.active_chats:
        await res.edit("adding in queue")
        position = await queues.put(chat_id, file=file_path)
        qeue = que.get(chat_id)
        s_name = title
        r_by = message_.from_user
        loc = file_path
        appendable = [s_name, r_by, loc]
        qeue.append(appendable)
        await res.edit_text(f"✯{bn}✯= #️⃣ Sıraya Alındı, Sırası {position}")
    else:
        await res.edit_text(f"✯{bn}✯=▶️ Oynatılıyor.....")

        que[chat_id] = []
        qeue = que.get(chat_id)
        s_name = title
        r_by = message_.from_user
        loc = file_path
        appendable = [s_name, r_by, loc]
        qeue.append(appendable)
        try:
            await callsmusic.set_stream(chat_id, file_path)
        except:
            res.edit("Sesli Sohbete Bağlanamadım Veya Giremiyorum")
            return

    await res.delete()

    m = await client.send_photo(
        chat_id=message_.chat.id,
        reply_markup=keyboard,
        photo="final.png",
        caption=f"Oynatılıyor [{title}]({url}) Deezer Üzerinden",
    )
    os.remove("final.png")


@Client.on_message(filters.command("soynat") & filters.group & ~filters.edited)
async def jiosaavn(client: Client, message_: Message):
    global que
    if message_.chat.id in DISABLED_GROUPS:
        return    
    lel = await message_.reply("🔄 <b>İşleniyor</b>")
    administrators = await get_administrators(message_.chat)
    chid = message_.chat.id
    try:
        user = await USER.get_me()
    except:
        user.first_name = "@zencilermuzikasistani"
    usar = user
    wew = usar.id
    try:
        # chatdetails = await USER.get_chat(chid)
        await client.get_chat_member(chid, wew)
    except:
        for administrator in administrators:
            if administrator == message_.from_user.id:
                if message_.chat.title.startswith("Müzik Kanalı: "):
                    await lel.edit(
                        "<b>Asistanı Gruba Eklemeyi Unutma</b>",
                    )
                    pass
                try:
                    invitelink = await client.export_chat_invite_link(chid)
                except:
                    await lel.edit(
                        "<b>Öncelikle Beni Grupta Admin Yap</b>",
                    )
                    return

                try:
                    await USER.join_chat(invitelink)
                    await USER.send_message(
                        message_.chat.id, "Müzik Oynatmak İçin Gruba Girdim"
                    )
                    await lel.edit(
                        "<b>Asistan Gruba Girdi</b>",
                    )

                except UserAlreadyParticipant:
                    pass
                except Exception:
                    # print(e)
                    await lel.edit(
                        f"<b>🔴 🔴 Zaman Aşımı Hatası 🔴 \n {user.first_name} Asistan için yoğun katılma istekleri nedeniyle grubunuza katılamadı! Asistanın grupta yasaklanmadığından emin olun."
                        "\n\nVeya @zencilermuzikasistani Hesabını Gruba Kendin Ekle</b>",
                    )
    try:
        await USER.get_chat(chid)
        # lmoa = await client.get_chat_member(chid,wew)
    except:
        await lel.edit(
            "<i> {user.first_name} Asistan Chatte Değil, /oynat komutunu kullan veya {user.first_name} asistanı kendin ekle</i>"
        )
        return
    requested_by = message_.from_user.first_name
    chat_id = message_.chat.id
    text = message_.text.split(" ", 1)
    query = text[1]
    res = lel
    await res.edit(f"Aranıyor 🔍 `{query}` Üzerinden Jio Saavn")
    try:
        songs = await arq.saavn(query)
        if not songs.ok:
            await message_.reply_text(songs.result)
            return
        sname = songs.result[0].song
        slink = songs.result[0].media_url
        ssingers = songs.result[0].singers
        sthumb = songs.result[0].image
        sduration = int(songs.result[0].duration)
    except Exception as e:
        await res.edit("Kütüphanede Bulunamadı!, Sana İngilizce Yazmanı Öneririm.")
        print(str(e))
        return
    try:    
        duuration= round(sduration / 60)
        if duuration > DURATION_LIMIT:
            await cb.message.edit(f"Müzik {DURATION_LIMIT} dakikadan uzun, bunu oynatamam")
            return
    except:
        pass    
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("📖 Oynatma Listesi", callback_data="playlist"),
                InlineKeyboardButton("Menü ⏯ ", callback_data="menu"),
            ],
            [
                InlineKeyboardButton(
                    text="Grubumuza Katıl", url=f"https://t.me/{updateschannel}"
                )
            ],
            [InlineKeyboardButton(text="❌ Katıl", callback_data="cls")],
        ]
    )
    file_path = await convert(wget.download(slink))
    chat_id = get_chat_id(message_.chat)
    if chat_id in callsmusic.active_chats:
        position = await queues.put(chat_id, file=file_path)
        qeue = que.get(chat_id)
        s_name = sname
        r_by = message_.from_user
        loc = file_path
        appendable = [s_name, r_by, loc]
        qeue.append(appendable)
        await res.delete()
        m = await client.send_photo(
            chat_id=message_.chat.id,
            reply_markup=keyboard,
            photo="final.png",
            caption=f"✯{bn}✯=#️⃣ Sıraya Alındı, Sırası {position}",
        )

    else:
        await res.edit_text(f"{bn}=▶️ Oynatılıyor.....")
        que[chat_id] = []
        qeue = que.get(chat_id)
        s_name = sname
        r_by = message_.from_user
        loc = file_path
        appendable = [s_name, r_by, loc]
        qeue.append(appendable)
        try:
            await callsmusic.set_stream(chat_id, file_path)
        except:
            res.edit("Sesli Sohbete Bağlanamadım Veya Giremedim")
            return
    await res.edit("Küçük Resim Yükleniyor.")
    await generate_cover(requested_by, sname, ssingers, sduration, sthumb)
    await res.delete()
    m = await client.send_photo(
        chat_id=message_.chat.id,
        reply_markup=keyboard,
        photo="final.png",
        caption=f"Oynatılıyor {sname} Üzerinden Jiosaavn",
    )
    os.remove("final.png")


@Client.on_callback_query(filters.regex(pattern=r"plll"))
async def lol_cb(b, cb):
    global que

    cbd = cb.data.strip()
    chat_id = cb.message.chat.id
    typed_=cbd.split(None, 1)[1]
    #useer_id = cb.message.reply_to_message.from_user.id
    try:
        x,query,useer_id = typed_.split("|")      
    except:
        await cb.message.edit("Şarkı Bulunamadı")
        return
    useer_id = int(useer_id)
    if cb.from_user.id != useer_id:
        await cb.answer("Şarkıyı Oynatmak İsteyen Kişi Sen Değilsin!", show_alert=True)
        return
    await cb.message.edit("Oynatma Başlatılıyor")
    x=int(x)
    try:
        useer_name = cb.message.reply_to_message.from_user.first_name
    except:
        useer_name = cb.message.from_user.first_name
    
    results = YoutubeSearch(query, max_results=5).to_dict()
    resultss=results[x]["url_suffix"]
    title=results[x]["title"][:40]
    thumbnail=results[x]["thumbnails"][0]
    duration=results[x]["duration"]
    views=results[x]["views"]
    url = f"https://youtube.com{resultss}"
    
    try:    
        secmul, dur, dur_arr = 1, 0, duration.split(':')
        for i in range(len(dur_arr)-1, -1, -1):
            dur += (int(dur_arr[i]) * secmul)
            secmul *= 60
        if (dur / 60) > DURATION_LIMIT:
             await cb.message.edit(f"Müzik {DURATION_LIMIT} dakikadan uzun, bunu oynatamam!")
             return
    except:
        pass
    try:
        thumb_name = f"thumb{title}.jpg"
        thumb = requests.get(thumbnail, allow_redirects=True)
        open(thumb_name, "wb").write(thumb.content)
    except Exception as e:
        print(e)
        return
    dlurl=url
    dlurl=dlurl.replace("youtube","youtubepp")
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("📖 Oynatma Listesi", callback_data="playlist"),
                InlineKeyboardButton("Menü ⏯ ", callback_data="menu"),
            ],
            [
                InlineKeyboardButton(text="🎬 YouTube", url=f"{url}"),
                InlineKeyboardButton(text="İndir 📥", url=f"{dlurl}"),
            ],
            [InlineKeyboardButton(text="❌ Kapat", callback_data="cls")],
        ]
    )
    requested_by = useer_name
    await generate_cover(requested_by, title, views, duration, thumbnail)
    file_path = await convert(youtube.download(url))  
    if chat_id in callsmusic.active_chats:
        position = await queues.put(chat_id, file=file_path)
        qeue = que.get(chat_id)
        s_name = title
        try:
            r_by = cb.message.reply_to_message.from_user
        except:
            r_by = cb.message.from_user
        loc = file_path
        appendable = [s_name, r_by, loc]
        qeue.append(appendable)
        await cb.message.delete()
        await b.send_photo(chat_id,
            photo="final.png",
            caption=f"#⃣  İstediğin Şarkı by {r_by.mention} <b>Sırada</b> Sırası {position}!",
            reply_markup=keyboard,
        )
        os.remove("final.png")
        
    else:
        que[chat_id] = []
        qeue = que.get(chat_id)
        s_name = title
        try:
            r_by = cb.message.reply_to_message.from_user
        except:
            r_by = cb.message.from_user
        loc = file_path
        appendable = [s_name, r_by, loc]
        qeue.append(appendable)
    
        await callsmusic.set_stream(chat_id, file_path)
        await cb.message.delete()
        await b.send_photo(chat_id,
            photo="final.png",
            reply_markup=keyboard,
            caption=f"▶️ <b>Oynatılıyor</b> istediğin şarkı, İsteyen by {r_by.mention} Üzerinden YouTube Music",
        )
        
        os.remove("final.png")
