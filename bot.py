import discord
from discord.ext import commands, tasks
import requests
import time
import asyncio
from datetime import datetime

# ==========================================
# 1. CONFIGURATION
# ==========================================
DISCORD_TOKEN = ""  # Replace with your NEW token after resetting
GEMINI_API_KEY = ""  # Replace with your full key from aistudio.google.com
API_BASE_URL = "http://127.0.0.1:8000/api"
ALERT_CHANNEL_ID = 1522662195870175416

# ==========================================
# 2. AUTO-DETECT WORKING GEMINI MODELS
# ==========================================
gemini_client = None

CANDIDATE_MODELS = [
    'gemini-flash-latest',
    'gemini-2.5-flash',
    'gemini-2.5-flash-lite',
    'gemini-2.0-flash',
    'gemini-2.0-flash-001',
    'gemini-flash-lite-latest',
    'gemini-2.0-flash-lite',
    'gemini-3-flash-preview',
    'gemini-3.1-flash-lite',
    'gemini-pro-latest',
    'gemini-2.5-pro',
]

GEMINI_MODELS = CANDIDATE_MODELS


def detect_working_models(client, candidate_models):
    """Test each candidate model. Returns only ones that work."""
    working = []
    print("\n🔍 Detecting working Gemini models...")
    for model_name in candidate_models:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents="Say 'ok' in one word."
            )
            if response and response.text:
                working.append(model_name)
                print(f"   ✅ {model_name}")
        except Exception as e:
            error_str = str(e)
            if '429' in error_str or 'RESOURCE_EXHAUSTED' in error_str:
                working.append(model_name)
                print(f"   ⚠️  {model_name} (rate limited, keeping)")
            else:
                short_err = error_str[:60].replace('\n', ' ')
                print(f"   ❌ {model_name} ({short_err}...)")
    print(f"\n✅ Detected {len(working)} working models\n")
    return working if working else candidate_models


try:
    from google import genai
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    print("✅ Gemini AI client initialized successfully")
    GEMINI_MODELS = detect_working_models(gemini_client, CANDIDATE_MODELS)
except Exception as e:
    print(f"⚠️  Gemini client failed: {e}")
    print("⚠️  Bot will run WITHOUT AI - all commands still work!")

# ==========================================
# 3. BOT SETUP
# ==========================================
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

sent_alerts = set()

# LLM response cache to reduce API calls (5 min TTL)
llm_cache = {}
CACHE_DURATION_SECONDS = 300

# Timeout for Gemini calls (prevents blocking too long)
GEMINI_TIMEOUT_SECONDS = 15

# ==========================================
# 4. HELPER FUNCTIONS
# ==========================================
def check_api_connection():
    """Test if the backend API is reachable."""
    try:
        response = requests.get("http://127.0.0.1:8000/", timeout=5)
        return response.status_code == 200
    except Exception:
        return False


def fetch_from_api(endpoint):
    """Safe API fetcher. Returns (data, error) tuple."""
    try:
        url = f"{API_BASE_URL}/{endpoint}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json(), None
        return None, f"API returned status code {response.status_code}"
    except requests.exceptions.ConnectionError:
        return None, (
            "❌ Cannot connect to the office backend!\n"
            "Make sure `main.py` is running first.\n"
            f"Expected at: `http://127.0.0.1:8000`"
        )
    except requests.exceptions.Timeout:
        return None, "❌ Request timed out. The backend might be overloaded."
    except Exception as e:
        return None, f"❌ Unexpected error: {str(e)}"


def _call_gemini_sync(model_name, prompt):
    """
    Synchronous Gemini call - runs in a thread pool.
    This function BLOCKS - never call it directly from async code!
    """
    response = gemini_client.models.generate_content(
        model=model_name,
        contents=prompt
    )
    return response.text


async def humanize_data(prompt_context, instruction="Give a quick, natural, friendly office assistant response (1-3 sentences max)."):
    """
    ASYNC version - runs Gemini calls in a background thread to avoid blocking Discord.
    Features: caching, multi-model fallback, timeout, async-safe.
    """
    if gemini_client is None:
        return format_data_without_ai(prompt_context)

    # 1️⃣ Check cache first (instant)
    cache_key = (str(prompt_context)[:150] + instruction[:80]).lower()
    if cache_key in llm_cache:
        cached_time, cached_response = llm_cache[cache_key]
        if time.time() - cached_time < CACHE_DURATION_SECONDS:
            print("[LLM] 💾 Using cached response")
            return cached_response

    # 2️⃣ Build prompt
    system_prompt = (
        "You are a friendly, slightly witty office assistant bot in Discord. "
        f"{instruction} "
        "Do not use markdown formatting. "
        "Keep it under 3 sentences. "
        "Here is the data/context: "
    )
    full_prompt = system_prompt + str(prompt_context)

    # 3️⃣ Try each model with proper async handling
    for model_name in GEMINI_MODELS:
        for attempt in range(2):
            try:
                # 🎯 KEY FIX: Run blocking Gemini call in a background thread
                # This prevents Discord's heartbeat from being blocked
                response_text = await asyncio.wait_for(
                    asyncio.to_thread(_call_gemini_sync, model_name, full_prompt),
                    timeout=GEMINI_TIMEOUT_SECONDS
                )

                if attempt > 0 or model_name != GEMINI_MODELS[0]:
                    print(f"[LLM] ✅ Success with '{model_name}' (attempt {attempt + 1})")
                
                llm_cache[cache_key] = (time.time(), response_text)
                return response_text

            except asyncio.TimeoutError:
                print(f"[LLM] ⏱️  '{model_name}' timed out after {GEMINI_TIMEOUT_SECONDS}s, next model...")
                break  # Skip to next model on timeout

            except Exception as e:
                error_str = str(e)
                
                if '503' in error_str or 'UNAVAILABLE' in error_str or 'overloaded' in error_str.lower():
                    # Use asyncio.sleep (non-blocking) instead of time.sleep!
                    wait_time = 1 + attempt  # 1s, 2s
                    print(f"[LLM] ⏳ '{model_name}' overloaded, retry in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue
                
                if '429' in error_str or 'RESOURCE_EXHAUSTED' in error_str:
                    print(f"[LLM] 🚫 Rate limit on '{model_name}', next model...")
                    break
                
                if '403' in error_str or '401' in error_str:
                    print(f"[LLM] 🔑 Auth error: {error_str[:100]}")
                    return format_data_without_ai(prompt_context)
                
                print(f"[LLM] ❌ Error with '{model_name}': {error_str[:100]}")
                break

    # 4️⃣ All models failed - use offline formatter
    print("[LLM] ⚠️  All Gemini models failed, using offline formatter")
    return format_data_without_ai(prompt_context)


def format_data_without_ai(data):
    """Fallback formatter when AI is unavailable."""
    try:
        if isinstance(data, dict):
            if "devices" in data:
                devices = data["devices"]
                on_devices = [d for d in devices if d["status"] == "on"]
                off_devices = [d for d in devices if d["status"] == "off"]
                return (
                    f"Office Status: {len(on_devices)} devices ON, "
                    f"{len(off_devices)} devices OFF out of {len(devices)} total."
                )
            elif "total_power_watts" in data:
                return (
                    f"Total Power: {data['total_power_watts']}W | "
                    f"Est. Daily: {data.get('estimated_daily_kwh', 'N/A')} kWh"
                )
            elif "current_total_watts" in data:
                return (
                    f"Total: {data['current_total_watts']}W | "
                    f"Daily Est: {data.get('estimated_daily_kwh', 'N/A')} kWh | "
                    f"Cost: ₹{data.get('estimated_daily_cost_rupees', 'N/A')}"
                )
        elif isinstance(data, list):
            on_count = sum(1 for d in data if d.get("status") == "on")
            return f"Room Status: {on_count} out of {len(data)} devices are currently ON."
        elif isinstance(data, str):
            return f"Heads up! {data}"
        return str(data)[:300]
    except Exception:
        return str(data)[:300]

# ==========================================
# 5. PROACTIVE ALERTS TASK
# ==========================================
@tasks.loop(minutes=1)
async def proactive_alert_checker():
    """Polls backend every minute and posts new alerts to Discord."""
    channel = bot.get_channel(ALERT_CHANNEL_ID)
    if not channel:
        print(f"[ALERT CHECKER] ⚠️  Could not find channel ID: {ALERT_CHANNEL_ID}")
        return

    # Fetch alerts in a thread to avoid blocking
    data, error = await asyncio.to_thread(fetch_from_api, "alerts")
    
    if error:
        print(f"[ALERT CHECKER] API Error: {error}")
        return

    alerts = data.get('alerts', [])
    for alert in alerts:
        alert_id = f"{alert.get('room', alert['message'][:30])}-{alert['level']}-{datetime.now().hour}"
        if alert_id not in sent_alerts:
            sent_alerts.add(alert_id)
            
            # 🎯 KEY FIX: await the async humanize_data
            humanized_alert = await humanize_data(
                alert['message'],
                instruction=(
                    "You are alerting the boss to an office anomaly. "
                    "Sound helpful but urgent. Start with 'Hey Boss!' "
                    "Keep it to 2 sentences max."
                )
            )
            
            prefix = "🚨 **CRITICAL ALERT** 🚨" if alert['level'] == 'critical' else "⚠️ **WARNING ALERT** ⚠️"
            try:
                await channel.send(f"{prefix}\n{humanized_alert}")
                print(f"[ALERT CHECKER] ✅ Sent alert: {alert['message'][:60]}...")
            except Exception as e:
                print(f"[ALERT CHECKER] ❌ Failed to send: {e}")


@proactive_alert_checker.before_loop
async def before_alert_checker():
    await bot.wait_until_ready()

# ==========================================
# 6. BOT EVENTS
# ==========================================
@bot.event
async def on_ready():
    print(f"\n{'='*50}")
    print(f"✅ Bot logged in as: {bot.user.name} (ID: {bot.user.id})")
    print(f"{'='*50}")
    if check_api_connection():
        print("✅ Backend API connection: SUCCESSFUL")
    else:
        print("❌ Backend API connection: FAILED")
        print("   → Start the backend first: python main.py")
    print(f"{'='*50}")
    print(f"🔔 Starting proactive alert monitor (every 1 min)...")
    print(f"🧠 Active Gemini models: {len(GEMINI_MODELS)} available")
    print(f"   Primary: {GEMINI_MODELS[0] if GEMINI_MODELS else 'None'}")
    print(f"⏱️  Gemini timeout: {GEMINI_TIMEOUT_SECONDS}s")
    print(f"💾 LLM cache TTL: {CACHE_DURATION_SECONDS}s")
    if not proactive_alert_checker.is_running():
        proactive_alert_checker.start()
    print("✅ Bot is fully ready! Type !help_office in Discord.")
    print(f"{'='*50}\n")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send(
            "❓ Unknown command! Try:\n"
            "`!ping` `!status` `!room <name>` `!usage` `!alerts` `!help_office`"
        )
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("⚠️ Missing argument!\nUsage: `!room <room name>`\nExample: `!room Drawing Room`")
    else:
        print(f"[COMMAND ERROR] {error}")
        try:
            await ctx.send(f"❌ An error occurred: {str(error)[:200]}")
        except Exception:
            pass

# ==========================================
# 7. BOT COMMANDS
# ==========================================
@bot.command(name="ping")
async def ping(ctx):
    bot_latency = round(bot.latency * 1000)
    api_online = check_api_connection()
    api_status = "✅ Online" if api_online else "❌ Offline"
    ai_status = f"✅ {len(GEMINI_MODELS)} models" if gemini_client else "❌ Offline"
    primary_model = GEMINI_MODELS[0] if GEMINI_MODELS and gemini_client else "N/A"
    await ctx.send(
        f"🏓 **System Health Check**\n"
        f"```\n"
        f"Bot Latency  : {bot_latency}ms\n"
        f"Backend API  : {api_status}\n"
        f"Gemini AI    : {ai_status}\n"
        f"Primary Model: {primary_model}\n"
        f"LLM Cache    : {len(llm_cache)} entries\n"
        f"```"
    )


@bot.command(name="status")
async def check_status(ctx):
    async with ctx.typing():
        data, error = await asyncio.to_thread(fetch_from_api, "devices")
        if error:
            await ctx.send(error)
            return
        devices = data["devices"]
        rooms_summary = {}
        for device in devices:
            room = device["room"]
            if room not in rooms_summary:
                rooms_summary[room] = {"on": 0, "off": 0}
            rooms_summary[room][device["status"]] += 1
        room_lines = ""
        for room, counts in rooms_summary.items():
            status_emoji = "🟢" if counts["on"] > 0 else "⚫"
            room_lines += f"{status_emoji} **{room}**: {counts['on']} ON, {counts['off']} OFF\n"
        
        # await the async version
        friendly_message = await humanize_data(
            data,
            "Summarize which rooms have devices ON vs OFF. Mention totals. Be concise."
        )
        
        total_on = sum(1 for d in devices if d["status"] == "on")
        await ctx.send(
            f"🏢 **Office Device Status** ({total_on}/{len(devices)} devices ON)\n"
            f"{room_lines}\n"
            f"💬 {friendly_message}"
        )


@bot.command(name="room")
async def check_room(ctx, *, room_name: str):
    async with ctx.typing():
        data, error = await asyncio.to_thread(fetch_from_api, "devices")
        if error:
            await ctx.send(error)
            return
        room_devices = [d for d in data['devices'] if d['room'].lower() == room_name.lower()]
        if not room_devices:
            available = list(set(d['room'] for d in data['devices']))
            rooms_list = "\n".join(f"• `{r}`" for r in available)
            await ctx.send(f"❓ Room not found: **'{room_name}'**\n\nAvailable:\n{rooms_list}")
            return
        device_lines = ""
        for device in room_devices:
            emoji = "💡" if device["type"] == "light" else "🌀"
            status_icon = "🟢 ON " if device["status"] == "on" else "⚫ OFF"
            device_lines += f"{emoji} {device['name']}: {status_icon}\n"
        actual_room_name = room_devices[0]['room']
        on_count = sum(1 for d in room_devices if d["status"] == "on")
        
        friendly_message = await humanize_data(
            room_devices,
            f"Briefly summarize device status in {actual_room_name}."
        )
        
        await ctx.send(
            f"🚪 **{actual_room_name}** ({on_count}/{len(room_devices)} devices ON)\n"
            f"{device_lines}\n"
            f"💬 {friendly_message}"
        )


@bot.command(name="usage")
async def check_usage(ctx):
    async with ctx.typing():
        data, error = await asyncio.to_thread(fetch_from_api, "power")
        if error:
            await ctx.send(error)
            return
        current_watts = data['total_power_watts']
        estimated_kwh = round((current_watts * 8) / 1000, 2)
        estimated_cost = round(estimated_kwh * 8, 2)
        room_lines = ""
        for room, watts in data['room_breakdown'].items():
            bar = "█" * (watts // 20) if watts > 0 else "░"
            room_lines += f"  {room}: {watts}W {bar}\n"
        context_data = {
            "current_total_watts": current_watts,
            "estimated_daily_kwh": estimated_kwh,
            "estimated_daily_cost_rupees": estimated_cost,
            "room_breakdown": data['room_breakdown']
        }
        
        friendly_message = await humanize_data(
            context_data,
            "Report total power and daily kWh. Comment briefly on efficiency."
        )
        
        await ctx.send(
            f"⚡ **Power Consumption Report**\n"
            f"```\n"
            f"Current Draw   : {current_watts}W\n"
            f"Est. Daily Use : {estimated_kwh} kWh\n"
            f"Est. Daily Cost: ₹{estimated_cost}\n"
            f"\nRoom Breakdown:\n{room_lines}"
            f"```\n"
            f"💬 {friendly_message}"
        )


@bot.command(name="alerts")
async def check_alerts(ctx):
    async with ctx.typing():
        data, error = await asyncio.to_thread(fetch_from_api, "alerts")
        if error:
            await ctx.send(error)
            return
        alerts = data.get("alerts", [])
        if not alerts:
            await ctx.send(
                "✅ **No Active Alerts!**\n"
                "Everything looks good in the office. 👍\n"
                "*(Alerts trigger after-hours or after 2hrs continuous use)*"
            )
            return
        alert_text = f"🚨 **{len(alerts)} Active Alert(s):**\n\n"
        for i, alert in enumerate(alerts, 1):
            level_emoji = "🔴" if alert['level'] == 'critical' else "🟡"
            time_str = datetime.fromisoformat(alert['timestamp']).strftime("%H:%M:%S")
            alert_text += f"{level_emoji} **Alert {i}** `[{time_str}]`\n{alert['message']}\n\n"
        await ctx.send(alert_text)


@bot.command(name="models")
async def list_models(ctx):
    """Show all currently working Gemini models."""
    if not gemini_client:
        await ctx.send("❌ Gemini AI not initialized")
        return
    model_list = "\n".join(f"  {i+1}. {m}" for i, m in enumerate(GEMINI_MODELS))
    await ctx.send(f"🧠 **Active Gemini Models** ({len(GEMINI_MODELS)}):\n```\n{model_list}\n```")


@bot.command(name="clear_cache")
async def clear_cache(ctx):
    count = len(llm_cache)
    llm_cache.clear()
    await ctx.send(f"🗑️ Cleared {count} cached LLM responses.")


@bot.command(name="help_office")
async def help_office(ctx):
    await ctx.send(
        "🤖 **Office Monitor Bot — Commands**\n"
        "```\n"
        "!ping          Check bot, API & AI health\n"
        "!status        All rooms & devices overview\n"
        "!room <name>   Specific room status\n"
        "!usage         Power consumption & cost\n"
        "!alerts        Check for active alerts\n"
        "!models        List active AI models\n"
        "!clear_cache   Clear AI response cache\n"
        "!help_office   Show this message\n"
        "```\n"
        "**Rooms:** `Drawing Room` | `Work Room 1` | `Work Room 2`\n\n"
        "🔔 I also send **automatic alerts** every minute!"
    )

# ==========================================
# 8. RUN THE BOT
# ==========================================
if __name__ == "__main__":
    print("\n" + "="*50)
    print("🚀 Starting Office Monitor Bot...")
    print("="*50)
    if not DISCORD_TOKEN or len(DISCORD_TOKEN) < 50:
        print("❌ ERROR: DISCORD_TOKEN looks invalid!")
        exit(1)
    if not GEMINI_API_KEY:
        print("⚠️  WARNING: Gemini API key not set. AI disabled.")
    print(f"📡 Backend URL  : {API_BASE_URL}")
    print(f"🔔 Alert Channel: {ALERT_CHANNEL_ID}")
    print("="*50 + "\n")
    bot.run(DISCORD_TOKEN)
