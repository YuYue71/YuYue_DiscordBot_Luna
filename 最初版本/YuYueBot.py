# 匯入 Discord.py、yt_dlp 以及系統相關模組
import discord
import asyncio
from discord.ext import commands
from langdetect import detect
from gtts import gTTS
from yt_dlp import YoutubeDL
import sys
import os



# 檢查是否為 PyInstaller 打包後執行的環境
# 若是，使用內部臨時資料夾；否則使用目前所在目錄
if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
else:
    base_path = os.path.abspath(".")


# TTS 全域變數
tts_settings = {}  # 每個 guild.id 各自儲存
# 語音佇列字典，儲存每個頻道的播放佇列
voice_queues = {}

# 設定 FFmpeg 執行檔的路徑（支援打包後的相對路徑）
FFMPEG_PATH = os.path.join(base_path, "ffmpeg-master-latest-win64-gpl-shared", "bin", "ffmpeg.exe")

# 循環播放次數計數器
Frequency = 0


# 初始是否循環播放
looping = False


# 設定 Discord Bot 的 Intents（啟用訊息內容與語音狀態）
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True


# 建立 Bot 實例，設定指令前綴為 "!"
bot = commands.Bot(command_prefix="!", intents=intents)


# 使用 yt_dlp 取得影片的音訊串流網址（只取最佳音質）
def get_audio_url(youtube_url):
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': False,         # 關閉詳細輸出
        'noplaylist': True     # 禁止播放整個播放清單
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(youtube_url, download=False)
        return info['url']
    

# 當 Bot 啟動完成後顯示訊息
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")


# 指令：!join，讓機器人加入使用者的語音頻道
@bot.command()
async def join(ctx):
    if ctx.author.voice:
        channel = ctx.author.voice.channel                          # 取得使用者所在的語音頻道
        await channel.connect(self_mute=False, self_deaf=False)     # 連線到使用者所在的語音頻道,並且不靜音
        await ctx.send("我進來嚕～")
    else:
        await ctx.send("語音頻道沒有人呢……")


# 指令：!play <YouTube連結>，播放音樂
@bot.command()
async def play(ctx, url: str):
    global looping

    # 沒有在語音頻道，則取消播放
    if not ctx.author.voice:
        await ctx.send("語音房內沒人呢……")
        return

    # 如果機器人還沒加入語音頻道，就先加入
    voice_channel = ctx.author.voice.channel
    if ctx.voice_client is None:
        await voice_channel.connect(self_mute=False, self_deaf=False)   # 連線到使用者所在的語音頻道,並且不靜音
        await ctx.send("我進來嚕～")

    vc = ctx.voice_client

    # 若正在播放中，先停止
    if vc.is_playing():
        vc.stop()

    # 嘗試取得音訊串流網址
    try:
        stream_url = get_audio_url(url)     # 使用 yt_dlp 取得音訊串流網址
    except Exception as e:
        await ctx.send("無法取得音訊連結…\n錯誤訊息：" + str(e))
        return

    # 循環播放時的回呼函式（播放完畢後再次播放）
    def repeat_playback(error):
        if looping:     # 如果循環播放模式開啟
            try:
                stream_url_repeat = get_audio_url(url)  # 重新取得音訊串流網址
                audio_source = discord.PCMVolumeTransformer(
                    discord.FFmpegPCMAudio(             # 重新建立音訊來源，避免重複使用同一個來源
                        stream_url_repeat,
                        executable=FFMPEG_PATH,
                        before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
                    )
                )
                audio_source.volume = 0.5  # 設定音量為 50%
                vc.play(audio_source, after=repeat_playback)    # 再次播放音訊
                asyncio.run_coroutine_threadsafe(Ftext(ctx), bot.loop)  # 更新循環次數
            except Exception as e:
                print(f"Loop 播放錯誤：{e}")              


    async def Ftext(ctx):
        global Frequency
        Frequency += 1
        await ctx.send(f"已循環播放 [{Frequency}] 次")


    # 正常第一次播放
    audio_source = discord.PCMVolumeTransformer(
        discord.FFmpegPCMAudio(
            stream_url,
            executable=FFMPEG_PATH,
            before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
        )
    )
    audio_source.volume = 0.5  # 設定音量為 50%
    vc.play(audio_source, after=repeat_playback)

    await ctx.send("正在播放音樂囉～（循環模式：" + ("開啟" if looping else "關閉") + "）")
        

# 指令：!loop on / off，設定是否循環播放
@bot.command()
async def loop(ctx, mode: str = None):
    global looping
    global Frequency
    if mode == "on":
        looping = True
        await ctx.send("循環播放模式開啟喵～:repeat:")
    elif mode == "off":
        looping = False
        await ctx.send("循環播放模式關閉喵～⏹")
        Frequency = 0
    else:
        await ctx.send("用法：`!loop on` 或 `!loop off` ～")


# 指令：!stop，讓機器人離開語音頻道
@bot.command()
async def stop(ctx):
    global looping, Frequency
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("先走一步了～")
        tts_settings.pop(ctx.guild.id, None)  # 移除 TTS 設定
        voice_queues.pop(ctx.guild.id, None)  # 移除語音佇列
        looping = False
        Frequency = 0
    else:
        await ctx.send("我沒在語音房內～")
        

# 指令：!Help，顯示可用指令的說明
@bot.command()
async def Help(ctx):
    """顯示可用指令的說明"""
    help_message = (
        "可用指令：\n"
        "`!Help` - 顯示這個幫助訊息\n"
        "`!join` - 加入語音頻道\n"
        "`!play <YouTube連結>` - 播放音樂\n"
        "`!loop on/off` - 開啟或關閉循環播放\n"
        "`!tts on/off <頻道>` - 開啟或關閉 TTS 說話功能\n"
        "`!stop` - 停止播放並離開語音頻道\n"
        "`!Mockery <數字>` - 嘲諷\n"
        "`!MockeryList` - 查看嘲諷指令數字對照表\n"
    )
    await ctx.send(help_message)


def get_language_code(text):
    try:
        # 檢查是否包含日文字符（平假名、片假名）
        if any('\u3040' <= ch <= '\u30ff' for ch in text):
            return "ja"
        
        # 檢查是否包含中文字符（簡體或繁體）
        if any('\u4e00' <= ch <= '\u9fff' for ch in text):
            return "zh-tw"
        
        # 其他語言交由 langdetect 判斷
        lang = detect(text)
        if lang == "ja":            # 日文
            return "ja"
        elif lang == "zh-cn" or lang == "zh-tw":   # 中文（簡體或繁體）
            return "zh-tw"
        elif lang == "en":          # 英文或其他語言
            return "en"
        else:
            return "zh-tw"     # 預設英文
    except:
        return "zh-tw"  # 若無法偵測，回傳英文


# 語音佇列初始化
async def play_next(guild):
    queue = voice_queues[guild.id]
    vc = guild.voice_client

    # 如果佇列為空或未連線，則不處理
    if not vc or queue.empty():
        return

    text, lang_code = await queue.get()     # 從佇列中取出下一段要播的文字和語言

    # 儲存語音檔案路徑（單一檔案）
    path = "voice.mp3"

    # 建立語音檔案
    try:
        tts = gTTS(text=text, lang=lang_code, slow=False)
        tts.save(path)
        print(f"✅ 語音檔已儲存：{path}")
    except Exception as e:
        print(f"🔴 語音合成失敗：{e}")
        return

    # 播放語音檔
    try:
        # atempo 只支援 0.5～2.0
        audio = discord.FFmpegPCMAudio(
            path,
            executable=FFMPEG_PATH,
        )

        loop = asyncio.get_running_loop()

        def after_play(error):
            try:
                fut = asyncio.run_coroutine_threadsafe(play_next(guild), loop)
                fut.result()
            except Exception as e:
                print(f"after 播放下一段失敗：{e}")

        print(f"▶️ 正在播放語音：{text[:10]}，語言：{lang_code}")
        vc.play(discord.PCMVolumeTransformer(audio, volume=0.5), after=after_play)
    except Exception as e:
        print(f"🔴 播放失敗：{e}")

# TTS 說話
@bot.event
async def on_message(message):
    await bot.process_commands(message)     # 確保指令能正常處理

    # 濾掉私訊、機器人、空訊息
    if not message.guild or message.author.bot or not message.content.strip():
        return
    
    # 檢查是否啟用 TTS 並且在指定頻道
    guild_id = message.guild.id
    setting = tts_settings.get(guild_id)

    # 如果沒有設定，則不處理
    if setting and setting["enabled"] and message.channel.id == setting["channel_id"]:
        # 嘗試使用 gTTS 進行語音合成
        try:
            lang_code = get_language_code(message.content)  # 根據內容自動偵測語言
            # 初始化佇列
            if guild_id not in voice_queues:
                voice_queues[guild_id] = asyncio.Queue()

            vc = message.guild.voice_client                 # 取得當前語音頻道的連線
            # 如果沒有連線，則嘗試加入使用者的語音頻道
            if not vc:
                if message.author.voice and message.author.voice.channel:
                    vc = await message.author.voice.channel.connect(self_mute=False, self_deaf=False)   # 連線到使用者所在的語音頻道
                    await message.channel.send("我進來語音房囉～")
                else:
                    await message.channel.send("你不在語音房，我沒辦法說話>:(")
                    return
                
            # 加入佇列
            await voice_queues[guild_id].put((message.content, lang_code))

            # 若未在播放，則手動開始播第一段（觸發整個串聯）
            if not vc.is_playing():
                await play_next(message.guild)

        except Exception as e:
            print(f"TTS 播放失敗：{e}")
    

# TTS 指令：!tts on/off <頻道>
@bot.command()
async def tts(ctx, mode: str, channel: discord.TextChannel = None):
    guild_id = ctx.guild.id     # 取得伺服器 ID

    # 如果沒有指定頻道，則使用當前頻道
    if mode == "on":
        if channel is None:         # 如果沒有指定頻道，則使用當前頻道
            channel = ctx.channel
        
        # 檢查是否已經啟用 TTS
        tts_settings[guild_id] = {
            "enabled": True,
            "channel_id": channel.id,
            "rate": 1.0  # 預設播放速度
        }
        # 加入頻道的 ID 到設定中
        await ctx.send(f"✅ TTS 模式啟用，現在會朗讀頻道：{channel.mention}")
    elif mode == "off":
        if guild_id in tts_settings:                    # 如果這個伺服器有啟用過 TTS
            tts_settings[guild_id]["enabled"] = False   # 關閉 TTS 模式
            await ctx.send("🛑 TTS 模式已關閉")
        else:
            await ctx.send("TTS 沒有啟用過喔")
    else:
        await ctx.send("用法：`!tts on [#頻道]` 或 `!tts off`")


# 嘲諷指令：!Mockery
@bot.command()
async def Mockery(ctx, MK: int):
    if MK == 1:
        await ctx.send("那你很幽默喔~")
    elif MK == 2:
        await ctx.send(":place_of_worship: :place_of_worship: :place_of_worship: ")
    elif MK == 3:
        await ctx.send("666666")
    elif MK == 2147483647:
        await ctx.send("你媽")
    else :
        await ctx.send("目前只有 3 個選項,歡迎找 @yuyue_71 新增內容喔～\n")


# 嘲諷指令對照表：!MockeryList
@bot.command()
async def MockeryList(ctx):
    mockery_list = (
        "嘲諷指令對照表：\n"
        "`!Mockery 1` - 那你很幽默喔~\n"
        "`!Mockery 2` - :place_of_worship: :place_of_worship: :place_of_worship:\n"
        "`!Mockery 3` - 666666\n"
        "目前只有 3 個選項,歡迎找 @yuyue_71 新增內容喔～\n"
    )
    await ctx.send(mockery_list)

# 啟動機器人，提示輸入 TOKEN（避免寫死在程式中）
bot.run("MTE5ODg2ODI3NTE2NjE5NTcyMg.GyoFgO.J9cdXRrNGJQuWsu0qh3nMVr8VFAsQhjYwMuIAo")