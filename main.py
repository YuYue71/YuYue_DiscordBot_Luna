import discord
from openai import OpenAI
from discord.ext import commands
import asyncio
import json

from AI import setup_chatgpt_commands
from foundation.setup import setup_join_stop_commands
from music import setup_music_commands
from TTS.tts_module import setup_tts_commands
from foundation.Help import setup_help_commands
from mockery.Mockery import setup_mockery_commands
from record import record_setup_commands, on_voice_state_update
from backend_mas.massage import setup_massage_commands

# Intents 設定
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

# 讀取 config.json 檔案中 Token
with open('config.json', 'r') as config_file:
    config = json.load(config_file)
    DISCORD_TOKEN = config.get('DC_token')  # 從 config.json 讀取 DC token
    ChatGPT_TOKEN = config.get('GPT_token')  # 從 config.json 讀取 GPT token
    GEMINI_API_KEY = config.get('GEMINI_API_KEY')  # 從 config.json 讀取 GEMINI_API_KEY

bot = commands.Bot(command_prefix="Y!", intents=intents)     # 設定指令前綴

# 模組化導入各子檔案
setup_join_stop_commands(bot)               # 加入/離開語音頻道指令
setup_music_commands(bot)                   # 音樂播放指令
setup_tts_commands(bot)                     # TTS 語音指令
setup_help_commands(bot)                    # 幫助指令
setup_mockery_commands(bot)                 # 嘲諷指令
record_setup_commands(bot)                  # 語音紀錄指令
bot.add_listener(on_voice_state_update)     # 語音狀態更新事件
setup_chatgpt_commands(bot, ChatGPT_TOKEN)  # AI !
setup_massage_commands(bot)                 # 從 mas.json 發送訊息

# 當 Bot 啟動完成後顯示訊息
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")
    print("-# \"幽月YuYue\" 保有所有權利")

# 啟動機器人
bot.run(DISCORD_TOKEN)
