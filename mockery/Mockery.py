import json
import os
from discord.ext import commands

def setup_mockery_commands(bot):
    with open(os.path.join(os.path.dirname(__file__), "Mockery.json"), "r", encoding="utf-8") as f:          # 確保使用正確的編碼讀取 JSON 檔案
        data = json.load(f)                                         # 讀取 JSON 檔案
    Mockery_lines = data["mockery_list"]                            # 取得 help 部分的內容

    # 嘲諷指令：!Mockery
    @bot.command()
    async def Mockery(ctx, MK: int):
        # 檢查數字是否在有效範圍內(從 1 開始)
        if 1 <= MK <= len(Mockery_lines):
            await ctx.send(Mockery_lines[MK - 1])  # 注意索引從 0 開始
        else:
            await ctx.send(f"目前只有 {len(Mockery_lines)} 個選項，歡迎找 @yuyue_71 新增內容喔～")


    # 嘲諷指令對照表：!MockeryList
    @bot.command()
    async def MockeryList(ctx):
        Mockery_message = "嘲諷指令對照表：\n" + "\n".join(Mockery_lines) + f"\n目前只有 {len(Mockery_lines)} 個選項，歡迎找 @yuyue_71 新增內容喔～" # 將每一行指令加入到訊息中

        await ctx.send(Mockery_message)


# 如果要新增內容直接在 .json 檔案中新增即可, 這裡不需要修改Code