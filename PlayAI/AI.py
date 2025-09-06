import discord
from discord.ext import commands
import requests
import json
import time
import random
import asyncio

# 從 config.json 建立新的變數 GEMINI_API_KEY
with open('config.json', 'r', encoding='utf-8') as config_file:
    config = json.load(config_file)
    GEMINI_API_KEY = config.get('GEMINI_API_KEY')
    
# 為 AI_profile.json 建立新的變數 ai_profile
with open('PlayAI/AI_profile.json', 'r', encoding='utf-8') as profile_file:
    ai_profile = json.load(profile_file)
    SYSTEM_PROMPT = ai_profile.get('SHUUBI_SYSTEM_PROMPT') # 讀取系統提示
    
# 短期記憶,處理包含對話歷史的請求
def gemini_api_call(payload, system_prompt):
    # 設定 API 請求的 URL、標頭和載荷
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"    # API 端點
    # 免費2.5 -> https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent
    # 付費2.5 -> https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent
    headers = {
        "Content-Type": "application/json",
        "X-goog-api-key": GEMINI_API_KEY
    }
    
    if system_prompt:
        payload["system_instruction"] = {
            "parts": [{"text": system_prompt}]
        }
    
    max_retries = 5  # 最大重試次數
    base_delay = 1   # 基礎延遲時間（秒）

    # 實現指數退避重試機制
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=40) # 增加 timeout

            # 如果遇到 503 錯誤，就觸發重試
            if response.status_code == 503:
                # 如果是最後一次嘗試，就回傳錯誤訊息
                if attempt == max_retries - 1:
                    response.raise_for_status()
                # 計算下一次重試的等待時間
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                print(f"收到 503 錯誤，將在 {delay:.2f} 秒後重試... (第 {attempt + 1}/{max_retries} 次)")
                time.sleep(delay)
                continue # 進入下一次迴圈重試

            response.raise_for_status()  # 其他非 503 的錯誤直接拋出
            data = response.json()
            
            # 檢查 candidates 是否存在且不為空
            if "candidates" in data and data["candidates"]:
                content = data["candidates"][0].get("content", {})      # 取得第一個候選回覆的內容
                parts = content.get("parts", [])                        # 取得 parts 列表
                # 確保 parts 不為空且包含 text 欄位
                if parts:
                    answer_text = parts[0].get("text", "")              # 取得回覆文字
                    return answer_text if answer_text else "抱歉，我無法生成有效的回覆。"   # 返回回覆文字或預設訊息

            # 如果 API 因安全設定等原因阻止了回覆，通常會在這裡處理
            print(f"API 回應異常: {data}") 
            return "對捕幾,Luna沒有辦法回答.."
        
        except requests.exceptions.Timeout:
            print(f"錯誤：API 請求超時 (timeout=20s)。")
            return "對不起，Luna 腦袋有點熱熱的，思考超時了..." # 使用者指定的錯誤訊息
        
        except requests.exceptions.ConnectionError:
            print("錯誤：網路連線失敗。")
            return "網路連線不穩定，無法聯繫到 Luna 的大腦。"

        except requests.exceptions.HTTPError as http_err:
            status_code = http_err.response.status_code
            error_details = http_err.response.text
            print(f"API HTTP 錯誤: {status_code}\n詳情: {error_details}")

            if status_code == 429:
                return "請求太快了！Luna 需要喘口氣，請稍後再試。"
            elif status_code in [401, 403]:
                return "API 認證失敗，請檢查金鑰設定。 (聯繫開發者)"
            elif status_code == 400:
                return f"請求格式錯誤 (400)，請檢查傳送的資料。\n`{error_details}`"
            else:
                return f"發生未知的 API 錯誤 (Code: {status_code})。"
        
        except json.JSONDecodeError:
            print(f"錯誤：無法解析 API 回應的 JSON 格式。收到內容: {response.text}")
            return "API 回應格式錯誤，Luna 看不懂..."

        except Exception as e:
            print(f"gemini_api_call 發生未預期的錯誤: {e}")
            return f"發生了未知的內部錯誤: {e}"

    return "API 模型持續超載且重試失敗，請稍後再試。"

# 長期記憶與短期記憶結合的 Gemini 指令
def setup_gemini_commands(bot):
    # 從設定檔讀取記憶頻道的 ID
    with open('PlayAI/AI_profile.json', 'r', encoding='utf-8') as config_file:
        config = json.load(config_file)
        MEMORY_CHANNEL_ID = config.get('MEMORY_CHANNEL_ID')
        
    bot.long_term_memory = [] # 建立一個掛在 bot 物件下的變數來儲存記憶
    user_cooldowns = {} # 用於追蹤使用者的冷卻時間
    COOLDOWN_SECONDS = 25   # 每個使用者的冷卻時間（秒）
    
    @bot.event
    async def on_message(message):
        # 基本檢查：避免 Bot 回應自己
        if message.author == bot.user:
            return

        # 觸發條件：檢查是否被提及
        if bot.user in message.mentions:
            try:
                user_id = message.author.id
                current_time = time.time()

                # 冷卻機制檢查
                if user_id in user_cooldowns:
                    time_since_last_call = current_time - user_cooldowns[user_id]
                    if time_since_last_call < COOLDOWN_SECONDS:
                        await message.channel.send(f"Luna 的大腦正在休息中... 請在 {int(COOLDOWN_SECONDS - time_since_last_call)} 秒後再試一次！")
                        return
                
                # 準備基本資料
                memory_channel = bot.get_channel(MEMORY_CHANNEL_ID)
                if not memory_channel:
                    # 這種情況通常是設定檔錯誤，直接在控制台提示
                    print(f"嚴重錯誤：在 on_message 中找不到 ID 為 {MEMORY_CHANNEL_ID} 的記憶頻道！")
                    await message.channel.send("錯誤：記憶頻道設定遺失，請聯繫開發者。")
                    return
                
                content = message.content.replace(f"<@{bot.user.id}>", "").strip()
                if not content:
                    await message.channel.send("召喚Luna有甚麼事嗎?~")
                    return
                
                # 啟動同步打字提示
                await message.channel.typing()

                final_answer = "" # 用於儲存最終要回覆的訊息
                user_cooldowns[user_id] = time.time()

                # 判斷使用者意圖
                intent_prompt = f"""
                你的任務是判斷使用者是否明確地要求你「記住」或「記下」一件事。只能用「是」或「否」來回答。
                規則：
                1.  必須包含明確的指令詞，如「記住」、「記下」、「別忘了」、「幫我記」、「你要記得」等。
                2.  單純的提問、陳述事實或聊天，都不是記憶指令。
                正面範例 - 應該回答「是」：
                使用者：「記住我最喜歡的水果是蘋果。」
                你的回答：「是」
                使用者：「幫我記下來，我明天下午三點有會議。」
                你的回答：「是」
                使用者：「這件事你可得記牢了：專案的截止日期是下周五。」
                你的回答：「是」
                反面範例 - 應該回答「否」：
                使用者：「你記得我上次跟你說過什麼嗎？」
                你的回答：「否」(這是在查詢當前頻道過去的記憶，不是要求儲存新記憶)
                使用者：「今天天氣真好。」
                你的回答：「否」(這是聊天)
                使用者：「你是誰？」
                你的回答：「否」(這是提問)
                使用者：「我想知道台北 101 有多高？」
                你的回答：「否」(這是提問)
                使用者：「我的生日是今天。」
                你的回答：「否」(這是陳述事實，沒有要求記憶)
                ---
                現在，請根據以上規則與範例，判斷以下這句話：
                使用者：「{content}」
                你的回答：
                """
                intent_payload = {"contents": [{"parts": [{"text": intent_prompt}]}]}

                intent_response = await bot.loop.run_in_executor(None, gemini_api_call, intent_payload, None)

                # 根據意圖執行對應操作
                if intent_response and "是" in intent_response.strip():
                    # 處理記憶指令
                    user_mention = f"<@{message.author.id}>" # 獲取使用者提及字串
                    reflection_prompt = f"""
                        [任務]: 將使用者的原始請求轉換為一條結構化的長期記憶。

                        [輸入資料]:
                        * 使用者ID: {user_mention}
                        * 原始請求: "{content}"

                        [處理要求]:
                        1.  **提煉核心事實**: 分析原始請求，提取最關鍵的資訊點。
                        2.  **格式化輸出**: 必須嚴格按照以下格式生成記憶字串，不要添加任何額外的解釋或聊天內容。
                            格式: `[使用者: {user_mention}] [記憶點: <提煉後的核心事實>]`

                        [範例]:
                        * 範例請求: "記住我最喜歡的水果是蘋果。"
                        * 範例輸出: `[使用者: {user_mention}] [記憶點: 最喜歡的水果是蘋果。]`

                        * 範例請求: "我討厭吃香菜，不要推薦含有香菜的食物給我。"
                        * 範例輸出: `[使用者: {user_mention}] [記憶點: 討厭香菜，不希望被推薦含香菜的食物。]`

                        [開始處理]:
                        請根據上述要求，處理輸入資料。
                        """
                    reflection_payload = {"contents": [{"parts": [{"text": reflection_prompt}]}]}   # 建立反思請求的 payload
                    refined_memory = await bot.loop.run_in_executor(None, gemini_api_call, reflection_payload, SYSTEM_PROMPT)   # 呼叫 Gemini API 進行反思

                    # 儲存記憶到頻道與本地清單
                    if refined_memory and "抱歉" not in refined_memory and "錯誤" not in refined_memory:
                        await memory_channel.send(refined_memory)
                        bot.long_term_memory.append(refined_memory)
                        final_answer = f"好的，Luna把這件事記在心裡囉！\n```ini\n{refined_memory}\n```"
                    else:
                        final_answer = "啊...這次Luna的腦袋卡住了，沒辦法好好記下來。"

                else:
                    # 處理一般對話邏輯
                    participant_ids = set() # 用於儲存所有不重複的參與者 ID
                    conversation_history = []   # 用於儲存對話歷史
                    # 抓取最近 10 則訊息作為短期記憶
                    async for msg in message.channel.history(limit=10):
                        participant_ids.add(msg.author.id)  # 蒐集參與者 ID
                        msg_content = msg.content.replace(f"<@{bot.user.id}>", "").strip()  # 移除提及
                        # 只加入有內容的訊息
                        if msg_content:
                            if msg.author == bot.user:
                                role = "model"
                                # Bot 的回覆保持原樣
                                formatted_text = msg_content
                            else:
                                role = "user"
                                # 在使用者訊息前加上顯示名稱，讓 AI 清楚看到是誰說了什麼
                                formatted_text = f"[{msg.author.display_name}]: {msg_content}"
                                
                            conversation_history.insert(0, {"role": role, "parts": [{"text": formatted_text}]})
                            
                    user_mention = f"<@{message.author.id}>"    # 使用者提及格式
                    user_display_name = message.author.display_name # 使用者顯示名稱
                    # 建立「目前發言者」的註記
                    current_speaker_context = f"[系統註記：目前發言的使用者是 {user_display_name} (ID: {user_mention})。]"
    
                    participant_list_str = ", ".join([f"<@{pid}>" for pid in participant_ids])  # 參與者 ID 列表字串
                    # 建立「近期對話參與者」的註記
                    participants_context = f"[系統註記：近期對話參與者ID列表：{participant_list_str}]"
    
                    long_term_memory_messages = bot.long_term_memory
                    
                    if long_term_memory_messages:
                        memory_string = "\n- ".join(long_term_memory_messages)  # 將長期記憶串接成字串
                        ltm_context = f"\n\n[Luna的額外記憶庫]\n- {memory_string}"  # 長期記憶內容
                    else:
                        ltm_context = ""    # 如果沒有長期記憶，則為空字串
                        
                    # 組合所有情境資訊和系統提示
                    combined_system_prompt = (
                        f"{current_speaker_context}\n"
                        f"{participants_context}\n\n"
                        f"{SYSTEM_PROMPT}{ltm_context}"
                    )
                        
                    dialogue_payload = {"contents": conversation_history}
                    final_answer = await bot.loop.run_in_executor(None, gemini_api_call, dialogue_payload, combined_system_prompt)
                        
            except discord.Forbidden as forbidden_err:
                print(f"Discord 權限錯誤：無法在頻道 {message.channel.name} 發言或讀取歷史紀錄。 {forbidden_err}")
                # Bot 可能沒有權限發送錯誤訊息到當前頻道，所以只在 console 打印
                return # 靜默失敗

            # 捕捉所有其他未預期的錯誤，避免 Bot 崩潰
            except Exception as e:
                print(f"在 on_message 處理中發生嚴重錯誤: {e}")
                # 避免暴露詳細錯誤給前端使用者
                final_answer = "嗚... Luna 的核心程式碼好像出錯了，請聯繫開發者檢查後台日誌。"
            
            # 發送最終的回應
            if final_answer:
                if len(final_answer) > 2000:
                    chunks = []
                    remaining = final_answer
                    while len(remaining) > 2000:
                        split_pos = remaining.rfind('\n', 0, 2000)
                        if split_pos == -1: split_pos = 2000
                        chunks.append(remaining[:split_pos])
                        remaining = remaining[split_pos:].lstrip()
                    chunks.append(remaining)
                    for chunk in chunks:
                        if chunk: await message.channel.send(chunk)
                else:
                    await message.channel.send(final_answer)

        await bot.process_commands(message)
