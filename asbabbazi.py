import telebot
from telebot import types
from datetime import datetime, timedelta
import time
import threading
import math

BOT_TOKEN = "8920224632:AAF5jjjrgdC3rISf-JlhYLbbx4WScATaKR0"
ADMIN_ID = 8447611962

bot = telebot.TeleBot(BOT_TOKEN)

VOUCHERS = {}
USERS = {}
TEMP_DATA = {}

VIRTUAL_ACCOUNTS = [
    {"id": 1, "country": "🇺🇸 (US-EAST)", "num": "+1 202 555 ****", "status": "Active"},
    {"id": 2, "country": "🇨🇭 (CH-ZRH)", "num": "+41 79 123 ****", "status": "Active"},
    {"id": 3, "country": "🇬🇧 (UK-LON)", "num": "+44 7700 90 ****", "status": "Active"},
    {"id": 4, "country": "🇩🇪 (DE-FRA)", "num": "+49 151 234 ****", "status": "Active"},
    {"id": 5, "country": "🇫🇷 (FR-PAR)", "num": "+33 6 12 34 ****", "status": "Active"},
]

# ── زمان‌بندی انیمیشن: هر 10 ریپورت = 2 دقیقه (120 ثانیه) ──
SECONDS_PER_10_REPORTS = 120

def calc_duration(rep_count: int) -> int:
    """کل زمان عملیات به ثانیه، حداقل 4 ثانیه."""
    return max(4, math.ceil(rep_count / 10) * SECONDS_PER_10_REPORTS)

def fmt_duration(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds}s"
    m, s = divmod(seconds, 60)
    return f"{m}m {s:02d}s" if s else f"{m}m"

# ────────────────────────── Keyboards ──────────────────────────

def get_main_menu():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("▶️ Start Report", callback_data="start_op"))
    markup.add(types.InlineKeyboardButton("🖥 Network Accounts", callback_data="acc_count"))
    return markup

def get_op_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📢 Channel / Group", callback_data="rep_channel"),
        types.InlineKeyboardButton("🤖 Bot", callback_data="rep_bot"),
        types.InlineKeyboardButton("👤 Personal Account", callback_data="rep_account")
    )
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="back_main"))
    return markup

def get_reasons_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🚫 Spam", callback_data="rsn_Spam"),
        types.InlineKeyboardButton("⚠️ Violence", callback_data="rsn_Violence"),
        types.InlineKeyboardButton("🔞 Pornography", callback_data="rsn_Pornography"),
        types.InlineKeyboardButton("💸 Fraud / Scam", callback_data="rsn_Fraud"),
        types.InlineKeyboardButton("🎭 Fake Account", callback_data="rsn_Fake"),
        types.InlineKeyboardButton("🚨 Child Abuse", callback_data="rsn_ChildAbuse")
    )
    markup.add(types.InlineKeyboardButton("❌ Cancel Operation", callback_data="cancel_op"))
    return markup

def get_confirm_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ Confirm", callback_data="confirm_yes"),
        types.InlineKeyboardButton("❌ Cancel", callback_data="cancel_op")
    )
    return markup

def get_back_menu():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_main"))
    return markup

def get_admin_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("🎟 Generate License", callback_data="admin_gen_voucher"))
    markup.add(
        types.InlineKeyboardButton("➕ Add Account", callback_data="admin_add_acc"),
        types.InlineKeyboardButton("➖ Delete Account", callback_data="admin_del_acc")
    )
    return markup

# ────────────────────────── Global error handler ──────────────────────────

@bot.middleware_handler(update_types=['message', 'callback_query'])
def global_error_middleware(bot_instance, update):
    pass  # placeholder — real catching below via exception_handler

def safe_edit(chat_id, msg_id, text, **kwargs):
    try:
        bot.edit_message_text(text, chat_id, msg_id, **kwargs)
    except Exception:
        pass

# ────────────────────────── Admin handlers ──────────────────────────

@bot.message_handler(commands=['admin'])
def cmd_admin(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        bot.reply_to(message, "⚙️ **HEX Admin Portal**\n\nSelect an operation:", reply_markup=get_admin_menu(), parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

def admin_process_ttl(message):
    try:
        TEMP_DATA[message.from_user.id] = {'ttl': int(message.text)}
        msg = bot.reply_to(message, "Max **Accounts** allowed for this license (1 to network max):", parse_mode="Markdown")
        bot.register_next_step_handler(msg, admin_process_acc)
    except ValueError:
        bot.reply_to(message, "❌ Invalid input format.")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

def admin_process_acc(message):
    try:
        TEMP_DATA[message.from_user.id]['acc'] = int(message.text)
        msg = bot.reply_to(message, "Max **Reports** per user:", parse_mode="Markdown")
        bot.register_next_step_handler(msg, admin_process_rep)
    except ValueError:
        bot.reply_to(message, "❌ Invalid input format.")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

def admin_process_rep(message):
    try:
        TEMP_DATA[message.from_user.id]['rep'] = int(message.text)
        msg = bot.reply_to(message, "Max **Users** allowed to activate this license:", parse_mode="Markdown")
        bot.register_next_step_handler(msg, admin_process_users)
    except ValueError:
        bot.reply_to(message, "❌ Invalid input format.")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

def admin_process_users(message):
    try:
        users = int(message.text)
        data = TEMP_DATA.get(message.from_user.id, {})
        code = f"HEX-{int(time.time())}"
        VOUCHERS[code] = {
            'expires': datetime.now() + timedelta(hours=data.get('ttl', 1)),
            'acc_limit': data.get('acc', 1),
            'rep_limit': data.get('rep', 1),
            'max_users': users,
            'used_by': []
        }
        bot.reply_to(message,
            f"✅ **License Generated Successfully.**\n\n"
            f"🔑 License Code: `{code}`\n"
            f"👥 Users Limit: {users}\n"
            f"📱 Accounts Limit: {data['acc']}\n"
            f"📊 Reports Quota: {data['rep']}",
            parse_mode="Markdown"
        )
        TEMP_DATA.pop(message.from_user.id, None)
    except ValueError:
        bot.reply_to(message, "❌ Invalid input format.")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

def admin_process_add_acc(message):
    try:
        parts = message.text.split('|')
        if len(parts) != 2:
            bot.reply_to(message, "❌ Invalid input format.")
            return
        country = parts[0].strip()
        num = parts[1].strip()
        new_id = max([acc['id'] for acc in VIRTUAL_ACCOUNTS], default=0) + 1
        VIRTUAL_ACCOUNTS.append({"id": new_id, "country": country, "num": num, "status": "Active"})
        bot.reply_to(message, f"✅ **New Account connected to the network.**\n\nAccount ID: {new_id}\nNumber: `{num}`", parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"❌ System error: {e}")

def admin_process_del_acc(message):
    global VIRTUAL_ACCOUNTS
    try:
        acc_id = int(message.text)
        original_len = len(VIRTUAL_ACCOUNTS)
        VIRTUAL_ACCOUNTS = [acc for acc in VIRTUAL_ACCOUNTS if acc['id'] != acc_id]
        if len(VIRTUAL_ACCOUNTS) < original_len:
            bot.reply_to(message, f"✅ Account ID **{acc_id}** disconnected successfully.", parse_mode="Markdown")
        else:
            bot.reply_to(message, "❌ Account ID not found in the network.")
    except ValueError:
        bot.reply_to(message, "❌ Please enter a valid numeric ID.")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

# ────────────────────────── User /start ──────────────────────────

@bot.message_handler(commands=['start'])
def cmd_start(message):
    try:
        user_id = message.from_user.id
        if user_id in USERS:
            if USERS[user_id]['rep_left'] <= 0:
                bot.send_message(message.chat.id, "🚫 **License Exhausted**\n\nYour report quota is empty. Please get a new license to continue.", parse_mode="Markdown")
                return
            status_text = (
                f"🛡 **HEX Processing System**\n\n"
                f"📊 Report Quota: {USERS[user_id]['rep_left']}\n"
                f"📱 Network Accounts: {USERS[user_id]['acc_limit']}\n\n"
                f"Select an option below:"
            )
            bot.send_message(message.chat.id, status_text, reply_markup=get_main_menu(), parse_mode="Markdown")
        else:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔑 Authenticate & Enter License", callback_data="enter_voucher"))
            bot.send_message(
                message.chat.id,
                "🔒 **Access Denied**\n\nWelcome to the Hex System. Please authenticate by entering a valid license code.",
                reply_markup=markup,
                parse_mode="Markdown"
            )
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ An error occurred: {e}")

# ────────────────────────── Operation animation (threaded) ──────────────────────────

def run_operation(chat_id, msg_id, req_rep, user_id):
    """اجرای انیمیشن عملیات در thread جداگانه — بدون بلاک کردن ربات."""
    try:
        total_seconds = calc_duration(req_rep)
        eta_str = fmt_duration(total_seconds)

        # فریم‌های انیمیشن با تقسیم زمان واقعی
        frames = [
            (0,   "░░░░░░░░░░", "0%",   "Establishing secure connection to network accounts..."),
            (0.2, "██░░░░░░░░", "20%",  "Validating target identity..."),
            (0.4, "████░░░░░░", "40%",  "Allocating network resources..."),
            (0.6, "██████░░░░", "60%",  "Distributing payload across accounts..."),
            (0.8, "████████░░", "80%",  "Sending reports to central core..."),
            (1.0, "██████████", "100%", "All reports successfully registered."),
        ]

        prev_ratio = 0.0
        for ratio, bar, pct, status_msg in frames:
            sleep_time = (ratio - prev_ratio) * total_seconds
            if sleep_time > 0:
                time.sleep(sleep_time)
            prev_ratio = ratio

            elapsed = int(ratio * total_seconds)
            remaining = total_seconds - elapsed

            if ratio < 1.0:
                text = (
                    f"🔄 **Processing Operation**\n\n"
                    f"[{bar}] {pct}\n"
                    f"⏱ ETA: ~{fmt_duration(remaining)}\n"
                    f"📡 {status_msg}"
                )
            else:
                text = (
                    f"✅ **Operation Complete**\n\n"
                    f"[{bar}] {pct}\n"
                    f"⏱ Total time: {eta_str}\n"
                    f"📊 {req_rep} report(s) successfully submitted."
                )
            safe_edit(chat_id, msg_id, text, parse_mode="Markdown")

        # پس از اتمام، نمایش نتیجه نهایی
        if USERS[user_id]['rep_left'] <= 0:
            bot.send_message(chat_id, "🚫 **License Exhausted**\n\nYour report quota is empty. Access to the system has been suspended.", parse_mode="Markdown")
        else:
            safe_edit(
                chat_id, msg_id,
                f"✅ **Operation finished successfully.**\n📊 Remaining Quota: {USERS[user_id]['rep_left']} Reports",
                reply_markup=get_back_menu(),
                parse_mode="Markdown"
            )
    except Exception as e:
        try:
            bot.send_message(chat_id, f"❌ Operation error: {e}")
        except Exception:
            pass

# ────────────────────────── Callback handler ──────────────────────────

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    try:
        user_id = call.from_user.id

        if call.data == "admin_gen_voucher":
            msg = bot.edit_message_text("To generate a license, enter **Validity (Hours)**:", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
            bot.register_next_step_handler(msg, admin_process_ttl)

        elif call.data == "admin_add_acc":
            text = "To configure a new account, send data in this format:\n\n`Country | Number`\n\nExample:\n`🇯🇵 (JP-TKY) | +81 90 123 ****`"
            msg = bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="Markdown")
            bot.register_next_step_handler(msg, admin_process_add_acc)

        elif call.data == "admin_del_acc":
            text = "🗄 **Network Accounts Status:**\n\n"
            if not VIRTUAL_ACCOUNTS:
                text += "The network is currently empty."
            else:
                for acc in VIRTUAL_ACCOUNTS:
                    text += f"ID: **{acc['id']}** | {acc['country']} | `{acc['num']}`\n"
            text += "\nTo disconnect an account, send its **ID**:"
            msg = bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="Markdown")
            bot.register_next_step_handler(msg, admin_process_del_acc)

        elif call.data == "enter_voucher":
            msg = bot.edit_message_text("Please enter your license code:", call.message.chat.id, call.message.message_id)
            bot.register_next_step_handler(msg, process_voucher)

        elif call.data == "back_main":
            if USERS[user_id]['rep_left'] <= 0:
                bot.edit_message_text("🚫 Your license quota is exhausted.", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
                return
            status_text = f"🛡 **HEX Processing System**\n\n📊 Current Quota: {USERS[user_id]['rep_left']} Reports\n\nSelect an option below:"
            bot.edit_message_text(status_text, call.message.chat.id, call.message.message_id, reply_markup=get_main_menu(), parse_mode="Markdown")

        elif call.data == "acc_count":
            msg = "🖥 **Network Accounts Status:**\n\n"
            if not VIRTUAL_ACCOUNTS:
                msg += "⚠️ Processing accounts are currently offline."
            else:
                for acc in VIRTUAL_ACCOUNTS:
                    msg += f"▪️ {acc['country']} | ID: {acc['id']} | `{acc['num']}` | Status: 🟢 {acc['status']}\n"
            bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, reply_markup=get_back_menu(), parse_mode="Markdown")

        elif call.data == "start_op":
            if USERS[user_id]['rep_left'] <= 0:
                bot.answer_callback_query(call.id, "❌ Your license quota is exhausted!", show_alert=True)
                return
            bot.edit_message_text("🎯 **Select the target type for the report:**", call.message.chat.id, call.message.message_id, reply_markup=get_op_menu(), parse_mode="Markdown")

        elif call.data in ["rep_channel", "rep_bot", "rep_account"]:
            op_names = {"rep_channel": "Channel / Group", "rep_bot": "Bot", "rep_account": "Personal Account"}
            op_type = op_names[call.data]
            TEMP_DATA[user_id] = {'op_type': op_type}
            msg = bot.edit_message_text(f"🔗 Please send the Target ID or Link ({op_type}):", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
            bot.clear_step_handler_by_chat_id(call.message.chat.id)
            bot.register_next_step_handler(msg, process_target)

        elif call.data.startswith("rsn_"):
            reason = call.data.split("_")[1]
            TEMP_DATA[user_id]['reason'] = reason
            data = TEMP_DATA[user_id]
            req_rep = data.get('req_rep', 0)
            total_seconds = calc_duration(req_rep)
            eta_str = fmt_duration(total_seconds)

            invoice = (
                f"📋 **Operation Invoice**\n\n"
                f"🎯 **Target:** `{data.get('target')}`\n"
                f"📱 **Accounts to use:** {data.get('req_acc')}\n"
                f"📊 **Reports to send:** {req_rep}\n"
                f"📝 **Violation Reason:** {data.get('reason')}\n"
                f"⏱ **Estimated Time:** ~{eta_str}\n\n"
                f"Confirm operation?"
            )
            bot.edit_message_text(invoice, call.message.chat.id, call.message.message_id, reply_markup=get_confirm_menu(), parse_mode="Markdown")

        elif call.data == "cancel_op":
            bot.clear_step_handler_by_chat_id(call.message.chat.id)
            TEMP_DATA.pop(user_id, None)
            bot.edit_message_text("🛑 **Operation cancelled by user.**\n\nReturning to main menu...", call.message.chat.id, call.message.message_id, reply_markup=get_main_menu(), parse_mode="Markdown")

        elif call.data == "confirm_yes":
            data = TEMP_DATA.get(user_id, {})
            req_rep = data.get('req_rep', 0)
            USERS[user_id]['rep_left'] -= req_rep
            TEMP_DATA.pop(user_id, None)

            total_seconds = calc_duration(req_rep)
            eta_str = fmt_duration(total_seconds)

            # پیام اولیه بلافاصله
            bot.edit_message_text(
                f"🔄 **Processing Operation**\n\n"
                f"[░░░░░░░░░░] 0%\n"
                f"⏱ ETA: ~{eta_str}\n"
                f"📡 Establishing secure connection to network accounts...",
                call.message.chat.id, call.message.message_id,
                parse_mode="Markdown"
            )

            # انیمیشن در thread جداگانه — بات بلاک نمیشه
            t = threading.Thread(
                target=run_operation,
                args=(call.message.chat.id, call.message.message_id, req_rep, user_id),
                daemon=True
            )
            t.start()

    except Exception as e:
        try:
            bot.answer_callback_query(call.id, f"❌ Error: {e}", show_alert=True)
        except Exception:
            pass

# ────────────────────────── Voucher & flow handlers ──────────────────────────

def process_voucher(message):
    try:
        code = message.text.strip()
        user_id = message.from_user.id
        if code in VOUCHERS:
            v = VOUCHERS[code]
            if datetime.now() > v['expires']:
                bot.reply_to(message, "❌ This license has expired.")
            elif user_id in v['used_by']:
                bot.reply_to(message, "❌ You have already used this license.")
            elif len(v['used_by']) >= v['max_users']:
                bot.reply_to(message, "❌ The activation limit for this license has been reached.")
            else:
                v['used_by'].append(user_id)
                USERS[user_id] = {
                    'voucher': code,
                    'acc_limit': v['acc_limit'],
                    'rep_left': v['rep_limit']
                }
                bot.send_message(message.chat.id, "✅ **Authentication Successful.**\n\nYour user panel is now active.", reply_markup=get_main_menu(), parse_mode="Markdown")
        else:
            bot.reply_to(message, "❌ Invalid license code.")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

def process_target(message):
    try:
        user_id = message.from_user.id
        if user_id not in TEMP_DATA:
            return
        TEMP_DATA[user_id]['target'] = message.text
        msg = bot.send_message(message.chat.id, f"🖥 Enter the number of network accounts to use (Max allowed: {USERS[user_id]['acc_limit']} | Total network: {len(VIRTUAL_ACCOUNTS)}):")
        bot.register_next_step_handler(msg, process_acc_count)
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error: {e}")

def process_acc_count(message):
    try:
        user_id = message.from_user.id
        count = int(message.text)
        max_allowed = min(USERS[user_id]['acc_limit'], len(VIRTUAL_ACCOUNTS))
        if count > max_allowed:
            msg = bot.reply_to(message, f"❌ Access Error. Your maximum allowed accounts limit is {max_allowed}. Please enter a lower number:")
            bot.register_next_step_handler(msg, process_acc_count)
            return
        TEMP_DATA[user_id]['req_acc'] = count
        msg = bot.send_message(message.chat.id, f"📊 Enter the number of reports to execute (Your quota: {USERS[user_id]['rep_left']}):")
        bot.register_next_step_handler(msg, process_rep_count)
    except ValueError:
        msg = bot.reply_to(message, "❌ Invalid format. Please send a valid integer:")
        bot.register_next_step_handler(msg, process_acc_count)
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error: {e}")

def process_rep_count(message):
    try:
        user_id = message.from_user.id
        count = int(message.text)
        if count > USERS[user_id]['rep_left']:
            msg = bot.reply_to(message, f"❌ Insufficient capacity. Your balance is {USERS[user_id]['rep_left']} reports. Please enter a lower number:")
            bot.register_next_step_handler(msg, process_rep_count)
            return
        TEMP_DATA[user_id]['req_rep'] = count
        req_rep = count
        total_seconds = calc_duration(req_rep)
        eta_str = fmt_duration(total_seconds)
        bot.send_message(
            message.chat.id,
            f"📝 **Select the violation protocol (Report Reason):**\n⏱ Estimated operation time: ~{eta_str}",
            reply_markup=get_reasons_menu(),
            parse_mode="Markdown"
        )
    except ValueError:
        msg = bot.reply_to(message, "❌ Invalid format. Please send a valid integer:")
        bot.register_next_step_handler(msg, process_rep_count)
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error: {e}")

# ────────────────────────── Run ──────────────────────────

if __name__ == "__main__":
    print("✅ HEX Bot started.")
    bot.infinity_polling()
