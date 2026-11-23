import json, urllib.request, urllib.parse, os, time, threading

TOKEN = os.environ.get("BOT7_TOKEN", "").strip()
if not TOKEN:
    raise SystemExit("Set BOT7_TOKEN before starting the bot")
ADMINS = {8713521600, 5616024926, 7327528541}
GAP = 2
BACKUP_PROMO = """🚨 𝐈𝐌𝐏𝐎𝐑𝐓𝐀𝐍𝐓 𝐍𝐎𝐓𝐈𝐂𝐄 🚨

⚠️ कभी भी हमारा Main Channel बंद हो सकता है या उसमें कोई Problem आ सकती है! 😶‍🌫️

इसलिए अभी हमारा 𝐁𝐀𝐂𝐊𝐔𝐏 𝐂𝐇𝐀𝐍𝐍𝐄𝐋 जॉइन कर लो। ❤️‍🔥

✅ सभी जरूरी Updates सबसे पहले
🔥 नए पोस्ट और डेमो की जानकारी
🛡️ Main Channel में कोई दिक्कत हुई, तो Backup Channel काम आएगा!

❌ बाद में लिंक ढूँढते मत रहना!

👇 𝐀𝐁𝐇𝐈 𝐉𝐎𝐈𝐍 𝐊𝐀𝐑𝐎 👇

🔗  Backup Channel: https://t.me/+qAndW0JOuMM4ZGNl

❤️‍🔥 𝐒𝐀𝐅𝐄 𝐑𝐀𝐇𝐎, 𝐂𝐎𝐍𝐍𝐄𝐂𝐓𝐄𝐃 𝐑𝐀𝐇𝐎!"""
STATE_F = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tadka_state.json")

def load():
    try: return json.load(open(STATE_F))
    except Exception: return {"channels": [], "offset": 0, "queue": []}
st = load()
if "queue" not in st: st["queue"] = []
if "channels" not in st or not st["channels"]: st["channels"] = []
if "offset" not in st: st["offset"] = 0
# Number-wise saving: har naye post ko ek permanent number mile (delete/view button ke liye)
if "post_counter" not in st:
    _max = 0
    for _lst in (st.get("all_posts") or [], st.get("queue") or []):
        for _x in _lst:
            _max = max(_max, _x.get("num", 0) or 0)
    st["post_counter"] = _max
for _x in (st.get("queue") or []):
    if not _x.get("num"):
        st["post_counter"] += 1
        _x["num"] = st["post_counter"]
for _x in (st.get("all_posts") or []):
    if not _x.get("num"):
        st["post_counter"] += 1
        _x["num"] = st["post_counter"]

def api(meth, **p):
    for k in list(p):
        if isinstance(p[k], (dict, list)): p[k] = json.dumps(p[k])
    data = urllib.parse.urlencode(p).encode()
    # Send/copy dobara mat bhejo: connection tutne par bhi message ja chuka
    # ho sakta hai, retry se wahi post 2-3 baar chala jata hai.
    _attempts = 1 if meth in ("copyMessage", "sendMessage") else 3
    _last_err = None
    for _attempt in range(_attempts):
        try:
            return json.load(urllib.request.urlopen(f"https://api.telegram.org/bot{TOKEN}/{meth}", data, timeout=25))
        except Exception as e:
            _last_err = e
            time.sleep(1)
    raise _last_err

def save():
    json.dump(st, open(STATE_F, "w"))

# Backup promo sirf tadka bot par rahega - baki bots se hataya gaya
def backup_promo_due(regular_count, queue_remaining):
    return False

def send_pending_backup_promo():
    if not st.get("backup_promo_pending"):
        return
    sent_to = set(st.get("backup_promo_sent_to", []))
    for promo_cid in st["channels"]:
        if promo_cid in sent_to:
            continue
        try:
            result = api("sendMessage", chat_id=promo_cid, text=BACKUP_PROMO)
            if result.get("ok"):
                sent_to.add(promo_cid)
                st["backup_promo_sent_to"] = list(sent_to)
                save()
        except Exception as e:
            print("promo err:", e, flush=True)
    if all(cid in sent_to for cid in st["channels"]):
        st.pop("backup_promo_pending", None)
        st.pop("backup_promo_sent_to", None)
        save()

def _definite_not_delivered(e):
    # Pakka reject: request deliver hi nahi hua, agle batch me dobara try safe hai (duplicate nahi hoga).
    # HTTP 400/403/404/429 = server ne reject kiya; Tunnel/Connection refused/DNS = Telegram tak pahuncha hi nahi.
    # Connection tutne (Remote end closed, timeout) par pata nahi chalta - wo ambiguous hai, retry nahi karte.
    import urllib.error
    if isinstance(e, urllib.error.HTTPError):
        return e.code in (400, 403, 404, 429)
    _s = str(e)
    return ("Tunnel connection failed" in _s or "Connection refused" in _s
            or "Name or service not known" in _s or "Temporary failure in name resolution" in _s)

def scheduler():
    while True:
        try:
            lp = st.get("last_post", 0)
            wait = 1800 - (time.time() - lp)
            if wait > 0:
                time.sleep(wait)
                continue
            q = st.get("queue") or []
            if not q or not st["channels"]:
                time.sleep(10); continue
            import datetime
            now = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
            today = now.strftime("%Y-%m-%d")
            ap = st.get("all_posts") or []
            if ap and st.get("last_refill") != today and now.hour == 12 and not q:
                st["queue"] = list(ap)
                st["last_refill"] = today
                save()
                q = st["queue"]
            # Checker: jo post pehle ja chuka hai, use dobara mat bhejo
            _posted = set(st.get("posted", []))
            _seen = set()
            _clean = []
            for _it in q:
                _m = _it.get("mid")
                if _m in _posted or _m in _seen:
                    continue
                _seen.add(_m)
                _clean.append(_it)
            if len(_clean) != len(q):
                st["queue"] = _clean
                q = _clean
                save()
            batch = q[:10]
            for index, item in enumerate(batch):
                _tried = 0
                _definite_fail = False
                _any_ok_or_ambiguous = False
                for cid in st["channels"]:
                    # Naye channel ko wo post dobara mat bhejo jo catch-up me ja chuka hai
                    if cid == -1004401601760 and item["mid"] in st.get("sent_to_save_all", []):
                        continue
                    _tried += 1
                    try:
                        api("copyMessage", chat_id=cid, from_chat_id=item["chat"], message_id=item["mid"])
                        _any_ok_or_ambiguous = True
                    except Exception as e:
                        print("sched err:", e, flush=True)
                        if _definite_not_delivered(e):
                            _definite_fail = True
                        else:
                            # Connection tuta ho sakta hai, message ja chuka ho - duplicate se bachne ke liye posted mano
                            _any_ok_or_ambiguous = True
                    time.sleep(0.5)
                if _tried and _definite_fail and not _any_ok_or_ambiguous:
                    # Pakka reject hua - deliver nahi hua, queue me rehne do, agle batch me dobara try hoga
                    print("retry next batch:", item.get("num"), flush=True)
                    save()
                    continue
                st["queue"] = [x for x in (st.get("queue") or []) if x.get("mid") != item["mid"]]
                posted = st.setdefault("posted", [])
                posted.append(item["mid"])
                st["posted"] = posted[-500:]
                st["backup_promo_regular_count"] = st.get("backup_promo_regular_count", 0) + 1
                regular_count = st["backup_promo_regular_count"]
                promo_due = backup_promo_due(regular_count, len(st["queue"]))
                if promo_due and st.get("backup_promo_last_trigger_count") != regular_count:
                    st["backup_promo_last_trigger_count"] = regular_count
                    st["backup_promo_pending"] = True
                    st["backup_promo_sent_to"] = []
                save()
                send_pending_backup_promo()
            st["last_post"] = time.time()
            save()
        except Exception as e:
            print("sched loop err:", e, flush=True)

def _notify_async(cid, text, delay=10):
    # Confirmation background me bhejo, taaki main loop agle post ko turant save kar sake
    def f():
        try:
            r = api("sendMessage", chat_id=cid, text=text)
            _del(cid, r["result"]["message_id"], delay)
        except Exception:
            pass
    threading.Thread(target=f, daemon=True).start()

def _del(cid, mid, delay=10):
    def f():
        time.sleep(delay)
        try: api("deleteMessage", chat_id=cid, message_id=mid)
        except Exception: pass
    threading.Thread(target=f, daemon=True).start()

def file_id_for(m):
    for kind in ("video", "animation", "document", "audio", "voice", "video_note", "sticker"):
        if kind in m:
            return m[kind].get("file_id", "")
    if "photo" in m and m["photo"]:
        return m["photo"][-1].get("file_id", "")
    return ""

def is_private_admin(uid, chat):
    return uid in ADMINS and chat.get("type") == "private" and chat.get("id") == uid

def is_post_message(m):
    text = (m.get("text") or "").strip()
    if text.startswith("/"):
        return False
    return any(k in m for k in ("text", "caption", "photo", "video", "animation", "document", "audio", "voice", "video_note", "sticker", "contact", "location", "venue", "poll", "dice", "game"))

def queue_has_duplicate(q, m, fid):
    if any(x.get("chat") == m["chat"]["id"] and x.get("mid") == m["message_id"] for x in q):
        return True
    return bool(fid and any(x.get("fid") == fid for x in q))

print("tadka xpress running", flush=True)
threading.Thread(target=scheduler, daemon=True).start()
while True:
    try:
        ups = api("getUpdates", offset=st["offset"], timeout=10, limit=20).get("result", [])
    except Exception as e:
        print("poll err:", e, flush=True); time.sleep(1); continue
    for u in ups:
        st["offset"] = u["update_id"] + 1
        try:
            cq = u.get("callback_query")
            if cq:
                uid = cq.get("from", {}).get("id", 0)
                msg = cq.get("message") or {}
                chat = msg.get("chat", {})
                data = cq.get("data", "")
                if is_private_admin(uid, chat):
                    if data == "save_post":
                        st["save_post_waiting"] = uid
                        save()
                        api("answerCallbackQuery", callback_query_id=cq["id"], text="Ab agla post bhejo")
                    elif data == "queue_check" or data.startswith("qc:"):
                        try: api("answerCallbackQuery", callback_query_id=cq["id"])
                        except Exception: pass
                        _page = 0
                        if data.startswith("qc:"):
                            try: _page = int(data.split(":", 1)[1])
                            except Exception: _page = 0
                        _q = st.get("queue", [])
                        _per = 40
                        _total_pages = max(1, (_q.__len__() + _per - 1) // _per)
                        _page = max(0, min(_page, _total_pages - 1))
                        _items = _q[_page * _per:(_page + 1) * _per]
                        _lines = ["📋 Queue — Page " + str(_page + 1) + "/" + str(_total_pages) + " (" + str(len(_q)) + " pending)"]
                        for _it in _items:
                            _lines.append("#" + str(_it.get("num")) + " - mid " + str(_it.get("mid")))
                        _kb_rows = []
                        for _it in _items:
                            _n = _it.get("num")
                            _kb_rows.append([{"text": "👁 #" + str(_n), "callback_data": "view:" + str(_n)}, {"text": "🗑 #" + str(_n), "callback_data": "del:" + str(_n)}])
                        _nav = []
                        if _page > 0:
                            _nav.append({"text": "⬅️ Prev", "callback_data": "qc:" + str(_page - 1)})
                        if _page + 1 < _total_pages:
                            _nav.append({"text": "Next ➡️", "callback_data": "qc:" + str(_page + 1)})
                        if _nav:
                            _kb_rows.append(_nav)
                        _kb_rows.append([{"text": "📋 Queue Check", "callback_data": "queue_check"}, {"text": "💾 Post Save", "callback_data": "save_post"}])
                        api("sendMessage", chat_id=chat["id"], text="\n".join(_lines), reply_markup={"inline_keyboard": _kb_rows})
                    elif data.startswith("view:"):
                        try: api("answerCallbackQuery", callback_query_id=cq["id"])
                        except Exception: pass
                        try: _view_num = int(data.split(":", 1)[1])
                        except Exception: continue
                        _item = next((x for x in (st.get("queue") or []) if x.get("num") == _view_num), None)
                        if not _item:
                            api("sendMessage", chat_id=chat["id"], text="⚠️ Post #" + str(_view_num) + " queue me nahi mila.")
                        else:
                            try:
                                _copied = api("copyMessage", chat_id=chat["id"], from_chat_id=_item["chat"], message_id=_item["mid"])
                                _del(chat["id"], _copied["result"]["message_id"], 20)
                                _label = api("sendMessage", chat_id=chat["id"], text="👆 Ye Post #" + str(_view_num) + " hai — ye post 20 sec me auto-delete ho jayega.")
                                _del(chat["id"], _label["result"]["message_id"], 20)
                            except Exception as e:
                                print("view err:", e, flush=True)
                                api("sendMessage", chat_id=chat["id"], text="⚠️ Post #" + str(_view_num) + " dikh nahi paya — shayad original post delete ho gaya hai.")
                    elif data.startswith("del:"):
                        try: api("answerCallbackQuery", callback_query_id=cq["id"])
                        except Exception: pass
                        try: _del_num = int(data.split(":", 1)[1])
                        except Exception: continue
                        _q_before = len(st.get("queue") or [])
                        st["queue"] = [x for x in (st.get("queue") or []) if x.get("num") != _del_num]
                        st["all_posts"] = [x for x in (st.get("all_posts") or []) if x.get("num") != _del_num]
                        save()
                        if len(st["queue"]) < _q_before:
                            api("sendMessage", chat_id=chat["id"], text="🗑 Post #" + str(_del_num) + " queue se delete ho gaya (" + str(len(st["queue"])) + " pending bache)")
                        else:
                            api("sendMessage", chat_id=chat["id"], text="⚠️ Post #" + str(_del_num) + " queue me nahi mila, shayad pehle hi post ho gaya ya delete ho gaya hai.")
                else:
                    api("answerCallbackQuery", callback_query_id=cq["id"], text="Ye button sirf admin ke private chat ke liye hai")
                continue
            mcm = u.get("my_chat_member")
            if mcm and mcm["chat"]["type"] in ("channel", "group", "supergroup"):
                cid = mcm["chat"]["id"]
                if cid not in st["channels"]:
                    st["channels"].append(cid)
                save(); continue
            if u.get("channel_post"):
                continue
            m = u.get("message")
            if not m:
                continue
            uid = m.get("from", {}).get("id", 0)
            chat = m.get("chat", {})
            cid = chat.get("id")
            text = (m.get("text") or "").strip()
            if text.startswith("/start") and is_private_admin(uid, chat):
                keyboard = {"inline_keyboard": [[{"text": "📥 Queue", "callback_data": "queue_check"}], [{"text": "💾 Save post", "callback_data": "save_post"}]]}
                api("sendMessage", chat_id=cid, text="✅ chalu hai.", reply_markup=keyboard)
                continue
            if not is_private_admin(uid, chat) or not is_post_message(m):
                continue
            waiting = st.get("save_post_waiting") == uid
            if waiting:
                st.pop("save_post_waiting", None)
                save()
            q = st.setdefault("queue", [])
            fid = file_id_for(m)
            ap = st.setdefault("all_posts", [])
            if queue_has_duplicate(q, m, fid) or (fid and any(x.get("fid") == fid for x in ap)) or m["message_id"] in st.get("posted", []):
                r = api("sendMessage", chat_id=cid, text="⚠️ ye post/file queue me already hai, double nahi jayega")
                _del(cid, r["result"]["message_id"])
                save(); continue
            if fid == "BAACAgUAAxkBAAICdmrm2fx-4YNKFqpx3B2YYBgoQl_vAAJYDAACMLVgV3YDVpQQ":
                r = api("sendMessage", chat_id=cid, text="⚠️ ye file queue me add nahi ho sakti")
                _del(cid, r["result"]["message_id"])
                save(); continue
            st["post_counter"] = st.get("post_counter", 0) + 1
            _num = st["post_counter"]
            q.append({"chat": cid, "mid": m["message_id"], "fid": fid, "num": _num, "text": text})
            if not any(x.get("chat") == cid and x.get("mid") == m["message_id"] for x in ap):
                ap.append({"chat": cid, "mid": m["message_id"], "fid": fid, "num": _num, "text": text})
            save()
            _notify_async(cid, "📥 Post #" + str(_num) + " queue me add (" + str(len(q)) + " pending)", delay=10)
        except Exception as e:
            print("err:", e, flush=True)
    save()
