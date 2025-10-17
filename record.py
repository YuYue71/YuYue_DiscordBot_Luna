import discord
import pytz

from discord import Embed, Color
from datetime import datetime
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
    tz = pytz.timezone('Asia/Taipei')  # 設定時區為台北時間
    now = datetime.now(tz)  # 取得當前時間
    guild_id = member.guild.id      # 取得伺服器 ID

    if guild_id not in voice_log_channels:  # 檢查是否有啟用語音紀錄
        return
    
    channel_id = voice_log_channels[guild_id]   # 取得紀錄頻道 ID
    log_channel = member.guild.get_channel(channel_id)  # 獲取紀錄頻道對象

    if log_channel is None:     # 如果紀錄頻道不存在，則不處理
        return
    
    now_time = now.strftime("%Y-%m-%d %H:%M:%S")

    if before.channel is None and after.channel is not None:
        # 加入語音頻道
        embed = Embed(
            title=f"--**{member.display_name}**-- 加入了: **{after.channel.name}**",
            color=Color.green()     # 綠色
        )
        embed.set_footer(text=f"[首都時間]：{now_time}")

    elif before.channel is not None and after.channel is None:
        # 離開語音頻道
        embed = Embed(
            title=f"--**{member.display_name}**-- 離開了: **{before.channel.name}**",
            color=Color.red()       # 紅色
        )
        embed.set_footer(text=f"[首都時間]：{now_time}")

    elif before.channel != after.channel:
        # 移動語音頻道
        embed = Embed(
            title=f"--**{member.display_name}**-- 從: **{before.channel.name}** -> **{after.channel.name}**",
            color=Color.yellow()    # 黃色
        )
        embed.set_footer(text=f"[首都時間]：{now_time}")
    
    # 發送訊息
    await log_channel.send(embed = embed)