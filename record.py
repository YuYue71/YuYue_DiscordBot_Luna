import discord
from discord.ext import commands

# 儲存每個伺服器的紀錄頻道設定
voice_log_channels = {}

def record_setup_commands(bot):
    @bot.command()
    async def record(ctx, mode: str, channel: discord.TextChannel = None):
        """啟用語音紀錄功能"""
        guild_id = ctx.guild.id     # 取得伺服器 ID

        if mode.lower() == "on":    # 啟用語音紀錄

            if channel is None:     # 如果沒有指定頻道，則使用當前頻道
                channel = ctx.channel

            voice_log_channels[guild_id] = channel.id   # 儲存頻道 ID 到字典中
            await ctx.send(f"語音紀錄已啟用，將輸出到頻道：{channel.mention}")

        elif mode.lower() == "off": # 關閉語音紀錄
            # 檢查是否已經啟用語音紀錄
            if guild_id in voice_log_channels:      
                del voice_log_channels[guild_id]    # 刪除伺服器的紀錄設定
                await ctx.send("已關閉語音紀錄功能")
            else:
                await ctx.send("此伺服器尚未啟用語音紀錄")
        else:
            await ctx.send("請使用 `Y!record on [#頻道]` 或 `Y!record off`") 



@commands.Cog.listener()
async def on_voice_state_update(member, before, after):
    guild_id = member.guild.id      # 取得伺服器 ID
    if guild_id not in voice_log_channels:  # 檢查是否有啟用語音紀錄
        return  # 沒有啟用紀錄
    channel_id = voice_log_channels[guild_id]   # 取得紀錄頻道 ID
    log_channel = member.guild.get_channel(channel_id)  # 獲取紀錄頻道對象
    if log_channel is None:     # 如果紀錄頻道不存在，則不處理
        return
    if before.channel is None and after.channel is not None:        # 成員加入語音頻道
        await log_channel.send(f"`{member.display_name}` 加入了語音頻道 `{after.channel.name}`")
    elif before.channel is not None and after.channel is None:      # 成員離開語音頻道
        await log_channel.send(f"`{member.display_name}` 離開了語音頻道 `{before.channel.name}`")
    elif before.channel != after.channel:                           # 成員移動語音頻道
        await log_channel.send(f"`{member.display_name}` 從 `{before.channel.name}` 移動到 `{after.channel.name}`")
