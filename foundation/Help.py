import json
import os
from discord.ext import commands

def setup_help_commands(bot):
    @bot.command()
    async def Help(ctx):
        with open(os.path.join(os.path.dirname(__file__), "help.json"), "r", encoding="utf-8") as f:     # 確保使用正確的編碼讀取 JSON 檔案
            data = json.load(f)                                 # 讀取 JSON 檔案
        help_lines = data["help"]                               # 取得 help 部分的內容
        help_message = "可用指令：\n" + "\n".join(help_lines)    # 將每一行指令加入到訊息中

        await ctx.send(help_message)


# 如果要新增內容直接在 .json 檔案中新增即可, 這裡不需要修改Code