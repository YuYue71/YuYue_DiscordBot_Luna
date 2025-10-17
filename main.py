import discord
from discord.ext import commands
import json

from PlayAI.AI import setup_gemini_commands
from foundation.setup import setup_join_stop_commands
from music import setup_music_commands
from TTS.tts_module import setup_tts_commands
from foundation.Help import setup_help_commands
from record import record_setup_commands, on_voice_state_update

# Intents 設定
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

# 讀取 config.json 檔案中 Token
with open('config.json', 'r') as config_file:
    config = json.load(config_file)
    DISCORD_TOKEN = config.get('DC_token')  # 從 config.json 讀取 DC token
    ChatGPT_TOKEN = config.get('GPT_token')  # 從 config.json 讀取 GPT token
with open('PlayAI/AI_profile.json', 'r', encoding='utf-8') as profile_file:
    ai_profile = json.load(profile_file)
    MEMORY_CHANNEL_ID = ai_profile.get('MEMORY_CHANNEL_ID') # 從 AI_profile.json 讀取記憶頻道 ID
    
bot = commands.Bot(command_prefix="Y!", intents=intents)     # 設定指令前綴

# 模組化導入各子檔案
setup_join_stop_commands(bot)               # 加入/離開語音頻道指令
setup_music_commands(bot)                   # 音樂播放指令
setup_tts_commands(bot)                     # TTS 語音指令
setup_help_commands(bot)                    # 幫助指令
record_setup_commands(bot)                  # 語音紀錄指令
bot.add_listener(on_voice_state_update)     # 語音狀態更新事件
setup_gemini_commands(bot)                  # AI !!

# 當 Bot 啟動完成後顯示訊息
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")
    memory_channel = bot.get_channel(MEMORY_CHANNEL_ID) # 取得記憶頻道物件
    if memory_channel:
        print("正在載入長期記憶...")
        # 清空舊的快取，以防重連時重複載入
        bot.long_term_memory.clear()
        # 從記憶頻道載入歷史訊息
        async for message in memory_channel.history(limit=100, oldest_first=True):
            bot.long_term_memory.append(message.content)    # 將訊息內容加入長期記憶清單
                    
        print(f"已載入 {len(bot.long_term_memory)} 則長期記憶。")
    else:
        print(f"錯誤：找不到 ID 為 {MEMORY_CHANNEL_ID} 的記憶頻道！")
    print(f'Logged in as {bot.user}')
    print(f'{bot.user} 的 AI 模組已啟動!!\n')
    print("-# \"幽月YuYue\" 保有所有權利")

# 啟動機器人
bot.run(DISCORD_TOKEN)