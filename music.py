import discord
from discord.ext import commands
from yt_dlp import YoutubeDL
import asyncio
from ffmpeg_mode import FFMPEG_PATH

# 狀態變數與清單, 用於多伺服器音樂播放清單
playlist_queues = {}     # 音樂播放清單 {guild_id: [url1, url2, ...]}
now_playing_index = {}   # 當前播放索引 {guild_id: index}
is_playing = {}          # 是否正在播放音樂 {guild_id: True/False}
looping = False          # 是否循環播放

def setup_music_commands(bot):

    # 取得影片音訊串流連結
    def get_audio_url(youtube_url):
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': False,                 # 是否靜音輸出
            'noplaylist': True              # 是否只下載單一影片，不下載播放清單
        }
        with YoutubeDL(ydl_opts) as ydl:                        # 使用 yt-dlp 取得音訊串流連結
            info = ydl.extract_info(youtube_url, download=False)
            return info['url']

    # 播放器核心函式
    async def start_playing(ctx):
        guild_id = ctx.guild.id                     # 取得當前伺服器的 ID
        queue = playlist_queues.get(guild_id, [])   # 取得當前伺服器的播放清單
        index = now_playing_index.get(guild_id, 0)  # 取得當前播放索引

        if index >= len(queue):                     # 如果索引超出清單長度，則停止播放
            if looping and len(queue) > 0:
                now_playing_index[guild_id] = 0
                index = 0
            else:
                is_playing[guild_id] = False
                return

        url = queue[index]                          # 取得當前播放的 URL
        try:
            stream_url = get_audio_url(url)         # 取得音訊串流連結
        except Exception as e:
            await ctx.send(f"❌ 取得音訊失敗：{e}")
            return

        vc = ctx.voice_client       # 取得當前語音頻道的連線

        def after_play(error):      # 播放結束後的回調函式
            if error:
                print(f"播放時錯誤：{error}")
            now_playing_index[guild_id] += 1
            asyncio.run_coroutine_threadsafe(start_playing(ctx), bot.loop)  # 播放下一首音樂

        # 播放音樂
        audio = discord.FFmpegPCMAudio(
            stream_url,                                                                         # 使用 FFmpeg 播放音訊
            executable=FFMPEG_PATH,                                                             # 指定 FFmpeg 的執行檔路徑
            before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'          # 重新連線選項
        )
        try:
            vc.play(discord.PCMVolumeTransformer(audio, volume=0.5), after=after_play)  # 播放音樂並設定回調函式
        except discord.ClientException:
            await ctx.send("音樂衝突啦,拜託回報一下怎麼做到的,因為作者找不到原因。")
            return
        await asyncio.sleep(2.0)  # 等待一小段時間確認是否成功播放
        if not vc.is_playing():
            await ctx.send("⚠️ 播放失敗，自動跳過下一首！")
            now_playing_index[guild_id] += 1
            await start_playing(ctx)
            return
        else:
            is_playing[guild_id] = True                                 # 設定當前播放狀態為 True
            await ctx.send(f"🎵 當前撥放歌曲：[[連結]]({url})")

    # 指令：!play <YouTube連結>
    @bot.command()
    async def play(ctx, url: str):
        guild_id = ctx.guild.id         # 取得當前伺服器的 ID

        # 初始化清單與狀態
        playlist_queues.setdefault(guild_id, [])    # 音樂播放清單
        now_playing_index.setdefault(guild_id, 0)   # 當前播放索引
        is_playing.setdefault(guild_id, False)      # 是否正在播放音樂

        if not ctx.author.voice:
            await ctx.send("你不在語音頻道裡喔！")
            return

        if ctx.voice_client is None:                                                    # 如果機器人不在語音頻道，則加入使用者所在的語音頻道
            await ctx.author.voice.channel.connect(self_mute=False, self_deaf=False)    # 連線到使用者所在的語音頻道
            await ctx.send("我來了喵～")

        playlist_queues[guild_id].append(url)   # 將音樂加入播放清單
        await ctx.send("✅ 音樂加入播放清單！")

        if not is_playing[guild_id]:            # 如果目前沒有播放音樂，則開始播放
            await start_playing(ctx)

    # 指令：!loop on/off    (循環功能)
    @bot.command()
    async def loop(ctx, mode: str):
        global looping
        if mode == "on":
            looping = True
            await ctx.send("🔁 循環播放模式開啟！")
        elif mode == "off":
            looping = False
            await ctx.send("⏹ 循環播放模式關閉！")
        else:
            await ctx.send("請使用 `!loop on` 或 `!loop off`")


    # 指令：!clearPlaylist  (清空播放清單)
    @bot.command()
    async def clearPlaylist(ctx):
        guild_id = ctx.guild.id                                 # 取得當前伺服器的 ID
        playlist_queues[guild_id] = []                          # 清空播放清單
        now_playing_index[guild_id] = 0                         # 重置當前播放索引
        is_playing[guild_id] = False                            # 重置播放狀態
        if ctx.voice_client and ctx.voice_client.is_playing():  # 如果有正在播放的音樂，則停止播放
            ctx.voice_client.stop()                             # 停止當前播放的音樂
        await ctx.send("播放清單已清空～")


    # 指令：!cut (跳過當前歌曲)
    @bot.command()
    async def cut(ctx):
        guild_id = ctx.guild.id                                 # 取得當前伺服器的 ID
        if ctx.voice_client and ctx.voice_client.is_playing():  # 如果有正在播放的音樂
            ctx.voice_client.stop()                             # 停止當前播放的音樂
            await ctx.send("⏭ 已跳過目前歌曲！")
        else:
            await ctx.send("沒有播放中的音樂喔～")
