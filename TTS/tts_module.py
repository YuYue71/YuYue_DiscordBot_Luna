import asyncio
import discord
import os
import edge_tts
import uuid

from discord.ext import commands
from langdetect import detect
from ffmpeg_mode import FFMPEG_PATH

# TTS 全域變數
tts_settings = {}   # 每個 guild.id 各自儲存
voice_queues = {}   # 語音佇列字典，儲存每個頻道的播放佇列

# 設定 TTS 語言語音
def setup_tts_commands(bot):
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
                return "zh-tw"     # 預設中文
        except:
            return "zh-tw"  # 若無法偵測，回傳英文
        




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





    # 當有訊息時觸發事件
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





    # 播放佇列中的下一段語音
    async def play_next(guild):
        queue = voice_queues[guild.id]
        vc = guild.voice_client

        if not vc or queue.empty():
            return

        text, lang_code = await queue.get()

        # 建立語音檔路徑（唯一名稱避免衝突）
        filename = f"TTS/{uuid.uuid4()}.mp3"

        # 使用少女音語音包（依語言切換）
        voice_map = {
            "zh-tw": "zh-TW-HsiaoChenNeural",
            "zh-cn": "zh-CN-XiaoChenNeural",
            "ja": "ja-JP-NanamiNeural",
            "en": "en-US-AriaNeural"
        }
        voice = voice_map.get(lang_code, "zh-TW-HsiaoChenNeural")

        try:
            communicate = edge_tts.Communicate(text=text, voice=voice)
            await communicate.save(filename)
            print(f"✅ edge-tts 語音已儲存：{filename}")
        except Exception as e:
            print(f"🔴 語音合成失敗：{e}")
            return

        try:
            audio = discord.FFmpegPCMAudio(
                filename,
                executable=FFMPEG_PATH
            )

            loop = asyncio.get_running_loop()

            def after_play(error):
                try:
                    fut = asyncio.run_coroutine_threadsafe(play_next(guild), loop)
                    fut.result()
                    if os.path.exists(filename):
                        os.remove(filename)
                except Exception as e:
                    print(f"🔁 after 播放失敗：{e}")

            vc.play(discord.PCMVolumeTransformer(audio, volume=0.5), after=after_play)
            print(f"▶️ 撥放語音：「{text[:10]}...」，語音包：{voice}")

        except Exception as e:
            print(f"🔴 播放失敗：{e}")