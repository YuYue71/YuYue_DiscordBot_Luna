from music import looping
import discord
from TTS.tts_module import tts_settings, voice_queues
from music import playlist_queues, now_playing_index, is_playing, FFMPEG_PATH, looping
from record import voice_log_channels

def setup_join_stop_commands(bot):

    # 指令：!join，讓機器人加入使用者的語音頻道
    @bot.command()
    async def join(ctx):
        try:
            if ctx.author.voice:
                channel = ctx.author.voice.channel                          # 取得使用者所在的語音頻道
                await channel.connect(self_mute=False, self_deaf=False)     # 連線到使用者所在的語音頻道,並且不靜音
                await ctx.send("我進來嚕～")
            else:
                await ctx.send("語音頻道沒有人呢……")
        except discord.ClientException:
            await ctx.send("我已經在語音頻道裡了～")




    # 指令：!stop，讓機器人離開語音頻道
    @bot.command()
    async def stop(ctx):
        guild_id = ctx.guild.id     # 取得伺服器 ID
        if ctx.voice_client:        # 檢查是否有語音連線
            await ctx.voice_client.disconnect() # 斷開語音連線
            await ctx.send("先走一步了～")

        # 移除所有伺服器狀態資料
        tts_settings.pop(guild_id, None)    # 移除 TTS 設定
        voice_queues.pop(guild_id, None)    # 移除語音佇列
        playlist_queues.pop(guild_id, None) # 移除播放清單佇列
        now_playing_index.pop(guild_id, None)   # 移除當前播放索引
        is_playing.pop(guild_id, None)      # 移除播放狀態
        voice_log_channels.pop(guild_id, None)  # 移除語音紀錄頻道設定
        looping.pop(guild_id, None)         # 移除循環播放設定

        await ctx.send("已終止一切狀態")