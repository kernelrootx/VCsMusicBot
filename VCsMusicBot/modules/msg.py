import os
from VCsMusicBot.config import SOURCE_CODE,ASSISTANT_NAME,PROJECT_NAME,SUPPORT_GROUP,UPDATES_CHANNEL
class Messages():
      START_MSG = "**Merhaba 👋 [{}](tg://user?id={})!**\n\n🤖 Zenciler Federasyonu'nun Müzik Botudur.\n\n✅ Kullanım Kılavuzu İçin /yardım yazın."
      HELP_MSG = [
        ".",
f"""
**Merhaba, Ben {PROJECT_NAME} 

⭕ Grupların Sesli Sohbetlerinde Müzik Vb. Şeyleri Oynatabilirim.

⭕ Assistanım: @{ASSISTANT_NAME}\n\nSonraki Sayfa İçin Tıkla ➡️ **
""",

f"""
**Ayarlar**

1) Beni  Admin Yap.
2) Sesli Sohbeti Başlat.
3) /oynat (Şarkı İsmi) Yaz Ve Gönder
 Asistan Otomatik Olarak Gruba Katılacaktır, Katılmazsa sen @{ASSISTANT_NAME} hesabını ekle ve yeniden dene.
 4) Yine olmazsa @{ASSISTANT_NAME} hesabının banlanmadığına emin ol.
 5) Bunları Yaptığın Halde Botta Sıkıntı Varsa {SUPPORT_GROUP} 'a Katıl Ve Yardım İste.

**Commands**

**=>> Şarkı Oynatma 🎧**

- /oynat <Şarkı İsmi>: İsmini Yazdığın Şarkıyı Ve Türevlerini Bulur, Seçtiğini Oynatır.
- /oynat <YouTube Linki>: YouTube Linki Üzerinden Oynatır.
- /ytoynat: YouTube Music Kütüphanesinden Oynatır.
- /doynat: Deezer Üzerinden Oynatır.
- /soynat: Jio Saavn Üzerinden Oynatır.

**=>> Oynatma Ayarları ⏯**

- /oynatıcı: Oynatıcı Ayarlarını Açar.
- /atla: Sonraki Parçaya Atlar.
- /durdur: Oynatmayı Durdurur.
- /devam: Oynatmayı Devam Ettirir.
- /bitir: Oynatmayı Bitirir.
- /mevcutşarkı: Oynatılan Parçayı Gösterir.
- /oynatmalistesi: Oynatma Listesihi Gösterir.

**ZENCİLER FEDERASYONU**
""",
        

f"""
**=>> Extra Ayarlar 😬**

- /müzikoynatıcı <açık/kapalı> : Müzik Botunu Aktif Veya Devredışı Yapar.
- /adminreset: Gruptaki Adminleri Yeniden Tanır.
- /asistanekle: Asistan Hesabını (@{ASSISTANT_NAME}) Gruba Davet Eder.
""",
f"""
**=>> Şarkı/Video İndirme 📥**
- /video [Şarkı İsmi]: YouTube'den Video İndirir.
- /song [Şarkı İsmi]: YouTube'den Şarkı İndirir.
- /saavn [Şarkı İsmi]: Saavn'dan Şarkı İndirir.
- /deezer [Şarkı İsmi]: Deezer'dan Şarkı İndirir.

**=>> Arama Komutarı 🔍**
- /ara [Şarkı İsmi]: YouTube'den Şarkıyı Arar.
- /şarkısözü [Şarkı İsmi]: Şarkının Sözlerini Getirir.
""",
      ]
