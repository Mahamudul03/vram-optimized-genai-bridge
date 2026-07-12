import os
import time
import requests
import json
import base64
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# --- CONFIGURATION ---
TOKEN = " Your Token" 
SD_API_URL = "http://1ip0"
PROXY_URL = None # Set to your proxy URL if NOT using a system VPN

if PROXY_URL:
    os.environ['HTTPS_PROXY'] = PROXY_URL
    os.environ['HTTP_PROXY'] = PROXY_URL

# --- DYNAMIC TIME ENGINE ---
generation_history = [] 
DEFAULT_SEC_PER_STEP = 1.5 

def calculate_optimal_steps(target_seconds):
    if len(generation_history) == 0:
        sec_per_step = DEFAULT_SEC_PER_STEP
    else:
        total_time = sum(item[1] for item in generation_history)
        total_steps = sum(item[0] for item in generation_history)
        sec_per_step = total_time / total_steps if total_steps > 0 else DEFAULT_SEC_PER_STEP
        
    calculated_steps = int(target_seconds / sec_per_step)
    return max(15, min(calculated_steps, 45)) # Safety ceiling to protect VRAM

# --- UNIVERSAL COMMAND PARSER ---
def parse_inline_commands(text, current_settings):
    settings = current_settings.copy()
    patterns = {
        'width': r'--w\s+(\d+)',
        'height': r'--h\s+(\d+)',
        'steps': r'--steps\s+(\d+)',
        'cfg_scale': r'--cfg\s+(\d+(?:\.\d+)?)',
        'time_budget': r'--time\s+(\d+)'
    }
    
    cleaned_prompt = text
    for key, pattern in patterns.items():
        match = re.search(pattern, cleaned_prompt)
        if match:
            val = match.group(1)
            settings[key] = float(val) if key == 'cfg_scale' else int(val)
            cleaned_prompt = re.sub(pattern, '', cleaned_prompt)
            
    return cleaned_prompt.strip(), settings

# --- SLASH COMMAND HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['settings'] = {"width": 512, "height": 768, "time_budget": 60, "sampler_name": "DPM++ SDE", "cfg_scale": 7}
    await update.message.reply_text("🚀 Bot initialized! Send a prompt to generate, or type /help to view commands.")

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("⏱️ Fast (30s)", callback_data='time_30'),
         InlineKeyboardButton("⚖️ Balanced (60s)", callback_data='time_60'),
         InlineKeyboardButton("💎 Quality (120s)", callback_data='time_120')],
        [InlineKeyboardButton("🔄 Switch AI Model", callback_data='switch_model')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if 'settings' not in context.user_data:
        context.user_data['settings'] = {"width": 512, "height": 768, "time_budget": 60, "sampler_name": "DPM++ SDE", "cfg_scale": 7}
        
    budget = context.user_data['settings'].get('time_budget', 60)
    await update.message.reply_text(
        f"⚙️ **Control Panel**\n"
        f"Active Time Budget: {budget}s\n\n"
        f"Select a quick option or swap models below:", 
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def show_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'settings' not in context.user_data:
        context.user_data['settings'] = {"width": 512, "height": 768, "time_budget": 60, "sampler_name": "DPM++ SDE", "cfg_scale": 7}
    
    s = context.user_data['settings']
    text = (
        f"📊 **Current Configuration Status:**\n"
        f"• Dimensions: `{int(s.get('width', 512))}x{int(s.get('height', 768))}`\n"
        f"• CFG Scale: `{s.get('cfg_scale', 7)}`\n"
        f"• Sampler: `{s.get('sampler_name', 'DPM++ SDE')}`\n"
        f"• Target Time Window: `{s.get('time_budget', 60)}s`"
    )
    await update.message.reply_text(text, parse_mode='Markdown')

async def set_aspect_ratio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📱 Portrait (512x768)", callback_data='aspect_portrait'),
         InlineKeyboardButton("🟩 Square (512x512)", callback_data='aspect_square'),
         InlineKeyboardButton("🌅 Landscape (768x512)", callback_data='aspect_landscape')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📐 Choose an aspect ratio preset:", reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        f"📖 **Master Command Manual**\n\n"
        f"**Commands:**\n"
        f"/menu - Open interactive configuration dashboard\n"
        f"/settings - Check active parameter baselines\n"
        f"/aspect - Swiftly switch dimension boundaries\n"
        f"/reset - Clear calculated timing statistics\n\n"
        f"**Inline Prompt Flags:**\n"
        f"Append these to any prompt to force parameters:\n"
        f"`--w [pixels]` | `--h [pixels]` | `--cfg [scale]` | `--time [seconds]` | `--steps [count]`"
    )
    await update.message.reply_text(text, parse_mode='Markdown')

async def reset_defaults(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global generation_history
    generation_history.clear()
    context.user_data['settings'] = {"width": 512, "height": 768, "time_budget": 60, "sampler_name": "DPM++ SDE", "cfg_scale": 7}
    await update.message.reply_text("🔄 Timing logs flushed. System metrics restored to baseline parameters.")

# --- INTERACTIVE BUTTON & CALLBACK ROUTER ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if 'settings' not in context.user_data:
        context.user_data['settings'] = {"width": 512, "height": 768, "time_budget": 60, "sampler_name": "DPM++ SDE", "cfg_scale": 7}

    if data.startswith('time_'):
        seconds = int(data.split('_')[1])
        context.user_data['settings']['time_budget'] = seconds
        await query.edit_message_text(f"✅ Time Budget target shifted to **{seconds}s**.", parse_mode='Markdown')

    elif data.startswith('aspect_'):
        ratio = data.split('_')[1]
        if ratio == 'portrait':
            context.user_data['settings']['width'], context.user_data['settings']['height'] = 512, 768
        elif ratio == 'square':
            context.user_data['settings']['width'], context.user_data['settings']['height'] = 512, 512
        elif ratio == 'landscape':
            context.user_data['settings']['width'], context.user_data['settings']['height'] = 768, 512
        await query.edit_message_text(f"✅ Layout updated to **{ratio.capitalize()}** shape configuration.")

    elif data == 'switch_model':
        try:
            response = requests.get(f"{SD_API_URL}/sdapi/v1/sd-models")
            keyboard = [[InlineKeyboardButton(m['title'][:30], callback_data=f"model_{m['title']}")] for m in response.json()]
            await query.edit_message_text("Select an active checkpoint:", reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception as e:
            await query.edit_message_text(f"Failed to query local models: {e}")

    elif data.startswith('model_'):
        model_name = data.replace('model_', '')
        await query.edit_message_text(f"⏳ Swapping hardware checkpoint to `{model_name}`...", parse_mode='Markdown')
        try:
            requests.post(f"{SD_API_URL}/sdapi/v1/options", json={"sd_model_checkpoint": model_name})
            await query.edit_message_text(f"✅ Active checkpoint successfully loaded!", parse_mode='Markdown')
        except Exception as e:
            await query.edit_message_text(f"Checkpoint swap failed: {e}")

# --- MAIN INFERENCE ENGINE ---
async def handle_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw_text = update.message.text
    if 'settings' not in context.user_data:
        context.user_data['settings'] = {"width": 512, "height": 768, "time_budget": 60, "sampler_name": "DPM++ SDE", "cfg_scale": 7}
        
    prompt, active_run_settings = parse_inline_commands(raw_text, context.user_data['settings'])
    
    if 'steps' in active_run_settings and active_run_settings['steps'] != context.user_data['settings'].get('steps'):
        optimal_steps = active_run_settings['steps']
        mode_desc = f"Static Override ({optimal_steps} steps)"
    else:
        target_time = active_run_settings.get('time_budget', 60)
        optimal_steps = calculate_optimal_steps(target_time)
        mode_desc = f"Dynamic Budgeting ({optimal_steps} steps allocation)"

    payload = {
        "prompt": prompt,
        "steps": optimal_steps,
        "sampler_name": active_run_settings.get('sampler_name', 'DPM++ SDE'),
        "cfg_scale": active_run_settings.get('cfg_scale', 7),
        "width": active_run_settings.get('width', 512),
        "height": active_run_settings.get('height', 768)
    }
    
    status_msg = await update.message.reply_text("🎨 Connected to WebUI... processing generation queue.")
    start_time = time.time()
    
    try:
        response = requests.post(f"{SD_API_URL}/sdapi/v1/txt2img", json=payload)
        img_base64 = response.json()['images'][0]
        time_taken = round(time.time() - start_time, 2)
        
        if 'steps' not in raw_text:
            generation_history.append((optimal_steps, time_taken))
            if len(generation_history) > 3:
                generation_history.pop(0)
                
        await update.message.reply_photo(
            photo=base64.b64decode(img_base64),
            caption=f"⚡ Render Complete: {time_taken}s\n📊 Strategy: {mode_desc}\n📐 Resolution: {payload['width']}x{payload['height']}"
        )
        await status_msg.delete()
    except Exception as e:
        await update.message.reply_text(f"❌ Execution error encountered: {e}")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Map command workflows
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('menu', menu))
    app.add_handler(CommandHandler('settings', show_settings))
    app.add_handler(CommandHandler('aspect', set_aspect_ratio))
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(CommandHandler('reset', reset_defaults))
    
    # Map input callbacks
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_prompt))
    
    print("Universal Command Bot is running...")
    app.run_polling()
