import discord
from discord.ext import commands

from foundation.setup import setup_join_stop_commands
from music import setup_music_commands
from TTS.tts_module import setup_tts_commands
from foundation.Help import setup_help_commands
from mockery.Mockery import setup_mockery_commands
from record import record_setup_commands, on_voice_state_update

# Intents 設定
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="Y!", intents=intents)     # 設定指令前綴

# 模組化導入各子檔案
setup_join_stop_commands(bot)           # 加入/離開語音頻道指令
setup_music_commands(bot)               # 音樂播放指令
setup_tts_commands(bot)                 # TTS 語音指令
setup_help_commands(bot)                # 幫助指令
setup_mockery_commands(bot)             # 嘲諷指令
record_setup_commands(bot)              # 語音紀錄指令
bot.add_listener(on_voice_state_update) # 語音狀態更新事件

# 當 Bot 啟動完成後顯示訊息
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")
    print("-# \"幽月YuYue\" 保有所有權利")

# 啟動機器人
bot.run("請替換為你的Token")