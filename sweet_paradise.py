# sweet_paradise.py
# Sweet Paradise Tiktok Live — v1.9.3 (animation-only)
# - เหลือ action เดียว: animation (มีดรอปดาวน์ท่า + วินาที)
# - ปุ่มเพิ่มกฎ → เด้งไดอะล็อก (gift/like/comment)
# - บันทึกกฎอัตโนมัติทุกการเปลี่ยน
# - ตั้งค่า "ท่านอน default (sleep)" และแจ้งเกมทันที
# - เชื่อม / ยกเลิกเชื่อม Roblox + สถานะจริงอัปเดต
# - History + CSV
# - API: /events, /confirm_link, /unlink_confirm

import os, sys, json, time, threading, asyncio, csv
from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List, Optional, Tuple, Deque
from collections import deque

from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import Qt, Signal, Slot

from fastapi import FastAPI, Body
from fastapi.responses import JSONResponse
import uvicorn

# TikTok
from TikTokLive import TikTokLiveClient
from TikTokLive.events import ConnectEvent, DisconnectEvent, CommentEvent, LikeEvent, GiftEvent

APP_NAME    = "Sweet Paradise Tiktok Live"
APP_VERSION = "1.9.3"

# ---------- Paths ----------
def config_dir() -> str:
    if sys.platform.startswith("win"):
        base = os.getenv("APPDATA", os.path.expanduser("~\\AppData\\Roaming"))
    elif sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.path.expanduser("~/.config")
    path = os.path.join(base, "SweetParadise")
    os.makedirs(path, exist_ok=True)
    return path

CONFIG_PATH = os.path.join(config_dir(), "config_simple.json")
LOG_PATH    = os.path.join(config_dir(), "sweetparadise.log")

def now_ms() -> int: return int(time.time()*1000)

def write_log(line: str):
    try:
        ts = time.strftime("[%Y-%m-%d %H:%M:%S]")
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"{ts} {line}\n")
    except Exception:
        pass

# ---------- Emotes for dropdown ----------
EMOTES_UI = [
    {"name":"Fishing03","id":"rbxassetid://95341434973902"},
    {"name":"Sit 1","id":"rbxassetid://94635953990635"},
    {"name":"Sit 2","id":"rbxassetid://107194672020448"},
    {"name":"Sit 3","id":"rbxassetid://94595259463668"},
    {"name":"sleep","id":"rbxassetid://116338609736417"},
    {"name":"Sleep Lie","id":"rbxassetid://111356976229207"},
    {"name":"Click","id":"rbxassetid://136587988124131"},
    {"name":"Automatic Save","id":"rbxassetid://135747331016183"},
    {"name":"Boneless","id":"rbxassetid://112754308583273"},
    {"name":"Boogie Bomb","id":"rbxassetid://99864758130280"},
    {"name":"Breakdown","id":"rbxassetid://97751957358196"},
    {"name":"Calamity","id":"rbxassetid://108432638264656"},
    {"name":"Crackdown","id":"rbxassetid://82684911114489"},
    {"name":"Crazy Feet","id":"rbxassetid://139640342905320"},
    {"name":"Dab","id":"rbxassetid://72001529926172"},
    {"name":"Default Dance","id":"rbxassetid://85631943971914"},
    {"name":"Eagle","id":"rbxassetid://78931097884233"},
    {"name":"Electro Shuffle","id":"rbxassetid://112494314483253"},
    {"name":"Electro Swing","id":"rbxassetid://95253735026627"},
    {"name":"Fancy Feet","id":"rbxassetid://101542157688852"},
    {"name":"Flapper","id":"rbxassetid://113443664834434"},
    {"name":"Flippin Incredible","id":"rbxassetid://91261227571111"},
    {"name":"Floss","id":"rbxassetid://102031631037753"},
    {"name":"Free Flow","id":"rbxassetid://108293696820192"},
    {"name":"Fresh","id":"rbxassetid://101021471383215"},
    {"name":"Guitar","id":"rbxassetid://112263437603669"},
    {"name":"HeadBanger","id":"rbxassetid://101207718200998"},
    {"name":"Hot Marat","id":"rbxassetid://95148378228160"},
    {"name":"Hotline Bling","id":"rbxassetid://121669269765108"},
    {"name":"Hype","id":"rbxassetid://84748996123819"},
    {"name":"Inf Dab","id":"rbxassetid://106779169358019"},
    {"name":"Kazotsky Kick","id":"rbxassetid://101542157688852"},
    {"name":"Macarena","id":"rbxassetid://89742305277035"},
    {"name":"Orange Justice","id":"rbxassetid://124602853169062"},
    {"name":"Pon Pon","id":"rbxassetid://112260504121435"},
    {"name":"Pop Lock","id":"rbxassetid://74020287597630"},
    {"name":"Pumpernickel","id":"rbxassetid://131641226256419"},
    {"name":"Reanimated","id":"rbxassetid://89742305277035"},
    {"name":"Ride The Pony","id":"rbxassetid://138595948396362"},
    {"name":"Running Man","id":"rbxassetid://73237414260412"},
    {"name":"Showstopper","id":"rbxassetid://78535458178916"},
    {"name":"Slitherin","id":"rbxassetid://106779169358019"},
    {"name":"Smooth Moves","id":"rbxassetid://74091469004143"},
    {"name":"Sprinkler","id":"rbxassetid://88709760340603"},
    {"name":"Take The L","id":"rbxassetid://99614239174320"},
    {"name":"The Robot","id":"rbxassetid://128195974761844"},
    {"name":"Twist","id":"rbxassetid://99200033054052"},
    {"name":"Worm","id":"rbxassetid://91954558839902"},
    {"name":"Yeet","id":"rbxassetid://134506091972713"},
    {"name":"Zany","id":"rbxassetid://138197066440650"},
    {"name":"jubilation","id":"rbxassetid://75804303882896"},
]

# ---------- Config ----------
@dataclass
class MappingRule:
    enabled: bool = True
    trigger_type: str = "gift"    # 'gift'|'like'|'comment'|'any'
    pattern: str = ""             # gift/comment filter
    min_count: int = 0            # like threshold
    streak_end_only: bool = False # gift combo end
    action: str = "animation"     # animation only
    param: str = ""               # "rbxassetid://...|secs"
    cooldown_sec: float = 0.0     # per-user cooldown (s)

    def to_dict(self): return asdict(self)
    @staticmethod
    def from_dict(d: Dict[str,Any]):
        x = MappingRule()
        for k,v in d.items():
            if hasattr(x,k): setattr(x,k,v)
        # force to animation for any legacy actions
        x.action = "animation"
        return x

@dataclass
class AppConfig:
    tiktok_username: str = ""
    port: int = 3000
    max_queue: int = 4000
    auto_start: bool = False

    enable_gifts: bool = True
    enable_likes: bool = True
    enable_comments: bool = True

    # default pose (sleep)
    default_pose_enabled: bool = True
    default_pose_id: str = "rbxassetid://116338609736417"

    # last linked owner (for UI)
    owner_roblox_user_id: Optional[int] = None
    owner_roblox_username: str = ""

    mappings: List[MappingRule] = field(default_factory=lambda: [
        # ตัวอย่าง rule เริ่มต้น
        MappingRule(True, "like", "", 10, False, "animation", "rbxassetid://85631943971914|5", 1.0),
    ])

    def to_dict(self):
        d = asdict(self); d["mappings"] = [m.to_dict() for m in self.mappings]
        return d
    @staticmethod
    def from_dict(d: Dict[str,Any]):
        cfg = AppConfig()
        for k,v in d.items():
            if k=="mappings" and isinstance(v, list):
                cfg.mappings = [MappingRule.from_dict(i) for i in v]
            elif hasattr(cfg,k):
                setattr(cfg,k,v)
        # migrate legacy actions to animation
        for m in cfg.mappings:
            m.action = "animation"
        return cfg

def load_config() -> AppConfig:
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return AppConfig.from_dict(json.load(f))
        except Exception as e:
            write_log(f"load_config error: {e}")
    return AppConfig()

def save_config(cfg: AppConfig):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg.to_dict(), f, ensure_ascii=False, indent=2)
    except Exception as e:
        write_log(f"save_config error: {e}")

# ---------- Event Queue ----------
class EventQueue:
    def __init__(self, maxlen=4000):
        self.q: Deque[Dict[str,Any]] = deque(maxlen=maxlen)
        self.lock = threading.Lock()
        self.seq = 0
    def push(self, ev: Dict[str,Any]):
        with self.lock:
            self.seq += 1
            ev.setdefault("seq", self.seq)
            ev.setdefault("ts", now_ms())
            self.q.append(ev)
    def drain(self, n: int) -> List[Dict[str,Any]]:
        out = []
        with self.lock:
            while self.q and len(out) < n:
                out.append(self.q.popleft())
        return out
    def size(self) -> int:
        with self.lock: return len(self.q)

# ---------- Mapper ----------
class Mapper:
    def __init__(self, cfg: AppConfig):
        self.cfg = cfg
        self.cool: Dict[Tuple[str,int], float] = {}
    def update(self, cfg: AppConfig): self.cfg = cfg; self.cool.clear()
    def _rule_key(self, r: MappingRule): return f"{r.trigger_type}|{r.pattern}|{r.min_count}|{r.streak_end_only}|{r.action}|{r.param}"
    def _is_cd(self, r: MappingRule, uid: Optional[str]) -> bool:
        if not r.cooldown_sec or not uid: return False
        key = (self._rule_key(r), hash(uid)); return self.cool.get(key, 0.0) > time.time()
    def _mark_cd(self, r: MappingRule, uid: Optional[str]):
        if not r.cooldown_sec or not uid: return
        key = (self._rule_key(r), hash(uid)); self.cool[key] = time.time() + r.cooldown_sec

    def _parse_anim(self, param: str) -> Tuple[str, Optional[int]]:
        s = (param or "").strip()
        if "|" in s:
            p, t = s.split("|", 1)
            try: secs = int(float(t))
            except: secs = None
            return p.strip(), secs
        return s, None

    def match(self, ev: Dict[str,Any]) -> Optional[Dict[str,Any]]:
        t = ev.get("type"); txt=""; count=0; streak_done=True
        if t=="gift":
            txt = (ev.get("gift_name") or "").lower()
            count = int(ev.get("repeat_count") or 0)
            streakable = ev.get("streakable"); streaking = ev.get("streaking")
            streak_done = (streakable and (streaking is False)) or (streakable is None)
        elif t=="like":
            try: count = int(ev.get("like_count") or 1)
            except: count = 1
        elif t=="comment":
            txt = (ev.get("comment") or "").lower()

        for r in self.cfg.mappings:
            if not r.enabled: continue
            if r.trigger_type!="any" and r.trigger_type!=t: continue
            if r.pattern and r.pattern.lower() not in txt: continue
            if r.min_count and count < r.min_count: continue
            if r.streak_end_only and t=="gift" and not streak_done: continue
            if self._is_cd(r, ev.get("user_id")): continue
            self._mark_cd(r, ev.get("user_id"))

            # animation only
            anim_id, secs = self._parse_anim(r.param)
            act = {"name":"animation","param":anim_id}
            if secs: act["duration"] = secs
            return act
        return None

# ---------- TikTok Worker ----------
class TikTokWorker(QtCore.QObject):
    event_signal  = Signal(dict)
    status_signal = Signal(str)
    def __init__(self, events: EventQueue, mapper: Mapper):
        super().__init__()
        self.events = events
        self.mapper = mapper
        self._username = ""
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._client: Optional[TikTokLiveClient] = None
        self.enable_gifts = True
        self.enable_likes = True
        self.enable_comments = True

    def set_username(self, u: str): self._username = u.strip()
    def set_filters(self, gifts: bool, likes: bool, comments: bool):
        self.enable_gifts = bool(gifts); self.enable_likes = bool(likes); self.enable_comments = bool(comments)

    def is_running(self) -> bool: return self._thread and self._thread.is_alive()
    def start(self):
        if self.is_running(): return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True); self._thread.start()
    def stop(self): self._stop.set()
    def _run(self): asyncio.run(self._amain())

    async def _amain(self):
        if not self._username:
            self.status_signal.emit("กรุณาใส่ชื่อ TikTok ก่อนเริ่ม")
            return

        self.status_signal.emit(f"กำลังเชื่อมต่อ @{self._username} …")
        client = TikTokLiveClient(unique_id=self._username)
        self._client = client

        @client.on(ConnectEvent)
        async def _on_connect(_: ConnectEvent):
            self.status_signal.emit("เชื่อมต่อ TikTok แล้ว")
            ev = {"type": "status", "status": "connected"}
            self.events.push(ev); self.event_signal.emit(ev)

        @client.on(DisconnectEvent)
        async def _on_disconnect(_: DisconnectEvent):
            self.status_signal.emit("ตัดการเชื่อมต่อจาก TikTok")
            ev = {"type": "status", "status": "disconnected"}
            self.events.push(ev); self.event_signal.emit(ev)

        @client.on(CommentEvent)
        async def _on_comment(ev: CommentEvent):
            if not self.enable_comments: return
            out = {"type":"comment","user_id":ev.user.unique_id,"nickname":ev.user.nickname,"comment":ev.comment}
            act = self.mapper.match(out)
            if act:
                out["action"] = act
                self.events.push({"type":"action","scope":"owner","action":act})
            self.events.push(out); self.event_signal.emit(out)

        @client.on(LikeEvent)
        async def _on_like(ev: LikeEvent):
            if not self.enable_likes: return
            raw_like = getattr(ev, "like_count", None) or getattr(ev, "likeCount", None) or 1
            try: like_count = int(raw_like)
            except: like_count = 1
            out = {"type":"like","user_id":ev.user.unique_id,"nickname":ev.user.nickname,"like_count":like_count}
            act = self.mapper.match(out)
            if act:
                out["action"] = act
                self.events.push({"type":"action","scope":"owner","action":act})
            self.events.push(out); self.event_signal.emit(out)

        @client.on(GiftEvent)
        async def _on_gift(ev: GiftEvent):
            if not self.enable_gifts: return
            gift_name = getattr(ev.gift, "name", None) or getattr(getattr(ev.gift, "extended_gift", None), "name", None)
            diamond = getattr(ev.gift, "diamond_count", None) or getattr(ev.gift, "diamond_value", None)
            out = {
                "type":"gift","user_id":ev.user.unique_id,"nickname":ev.user.nickname,
                "gift_id":getattr(ev.gift, "id", None),"gift_name":gift_name,
                "repeat_count":getattr(ev, "repeat_count", None),
                "streaking":getattr(ev, "streaking", None),
                "streakable":getattr(ev.gift, "streakable", None),
                "diamonds": diamond
            }
            act = self.mapper.match(out)
            if act:
                out["action"] = act
                self.events.push({"type":"action","scope":"owner","action":act})
            self.events.push(out); self.event_signal.emit(out)

        try:
            await client.start(fetch_gift_info=True, fetch_room_info=True)
            while not self._stop.is_set():
                await asyncio.sleep(0.2)
        except Exception as e:
            self.status_signal.emit(f"เกิดข้อผิดพลาด TikTok: {e}")
            write_log(f"TikTok error: {e}")
        finally:
            try:
                if client and client.connected:
                    await client.disconnect()
            except Exception:
                pass
            self.status_signal.emit("หยุดเชื่อมต่อ TikTok แล้ว")

# ---------- API Server ----------
class ApiServer(QtCore.QObject):
    status_signal = Signal(str)
    event_signal  = Signal(dict)
    def __init__(self, events: EventQueue, cfg: AppConfig):
        super().__init__()
        self.events = events
        self.cfg = cfg
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()

    def is_running(self) -> bool: return self._thread and self._thread.is_alive()
    def apply_config(self, cfg: AppConfig): self.cfg = cfg
    def start(self):
        if self.is_running(): return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True); self._thread.start()
    def stop(self):
        self._stop.set()

    def _run(self):
        app = FastAPI(title=f"{APP_NAME} API")

        @app.get("/events")
        async def _events(max:int=100):
            items = self.events.drain(max if max and max>0 else 100)
            return JSONResponse({"events": items, "remaining": self.events.size()})

        @app.post("/confirm_link")
        async def _confirm(payload: Dict[str,Any] = Body(...)):
            ev = {
                "type":"link_confirmed",
                "tiktok_user_id": payload.get("user_id"),
                "nickname": payload.get("nickname"),
                "roblox_user_id": payload.get("roblox_user_id"),
                "roblox_username": payload.get("roblox_username")
            }
            self.events.push(ev); self.event_signal.emit(ev)
            self.status_signal.emit(
                f"เชื่อมแล้ว ✓ @{ev.get('nickname') or ev.get('tiktok_user_id')} ↔ "
                f"{ev.get('roblox_username')} ({ev.get('roblox_user_id')})"
            )
            return {"ok": True}

        @app.post("/unlink_confirm")
        async def _unlink_confirm(payload: Dict[str,Any] = Body(None)):
            ev = {"type":"unlink_confirm"}
            self.events.push(ev); self.event_signal.emit(ev)
            self.status_signal.emit("ยืนยันยกเลิกเชื่อมจากเกมแล้ว")
            return {"ok": True}

        config = uvicorn.Config(app, host="127.0.0.1", port=self.cfg.port, log_level="info")
        server = uvicorn.Server(config)
        self.status_signal.emit(f"HTTP พร้อมใช้ที่ http://127.0.0.1:{self.cfg.port}")

        try:
            def watcher():
                while not self._stop.is_set():
                    time.sleep(0.2)
                server.should_exit = True
            threading.Thread(target=watcher, daemon=True).start()
            server.run()
        except Exception as e:
            self.status_signal.emit(f"HTTP มีปัญหา: {e}")
            write_log(f"HTTP error: {e}")
        finally:
            self.status_signal.emit("HTTP หยุดทำงานแล้ว")

# ---------- UI ----------
DARK_QSS = """
* { font-family: 'Segoe UI','Inter','Noto Sans',sans-serif; }
QMainWindow { background: #0f1115; }
QTabWidget::pane { border: 1px solid #232633; border-radius: 8px; }
QTabBar::tab { background: #161923; color: #cfd3dc; padding: 8px 14px; border-top-left-radius: 8px; border-top-right-radius: 8px; }
QTabBar::tab:selected { background: #212635; color: #ffffff; }
QPushButton { background: #2a3042; color: #e6e9ef; padding: 8px 14px; border-radius: 10px; }
QPushButton:hover { background: #343b55; }
QLineEdit, QSpinBox, QComboBox, QPlainTextEdit, QDoubleSpinBox { background: #161923; color: #e6e9ef; border: 1px solid #2b2f3a; border-radius: 8px; padding: 6px; }
QLabel, QCheckBox { color: #cfd3dc; }
"""

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.resize(1150, 760)
        self.setStyleSheet(DARK_QSS)

        self.cfg: AppConfig = load_config()
        self.events = EventQueue(maxlen=self.cfg.max_queue)
        self.mapper = Mapper(self.cfg)

        self.tk  = TikTokWorker(self.events, self.mapper)
        self.api = ApiServer(self.events, self.cfg)
        self.tk.status_signal.connect(self._on_status)
        self.tk.event_signal.connect(self._on_event)
        self.api.status_signal.connect(self._on_status)
        self.api.event_signal.connect(self._on_event)

        # history
        self.history: List[Dict[str,Any]] = []
        self.total_gifts = 0
        self.total_likes = 0
        self.total_comments = 0

        self._building_rules = False  # guard while populating table

        self._build_ui()
        self._load_cfg_to_ui()

        if self.cfg.auto_start:
            self.handle_start()

    # ----- build -----
    def _build_ui(self):
        central = QtWidgets.QWidget(); self.setCentralWidget(central)
        root = QtWidgets.QVBoxLayout(central)

        # แถวบน
        row1 = QtWidgets.QHBoxLayout(); root.addLayout(row1)
        self.ed_user = QtWidgets.QLineEdit(); self.ed_user.setPlaceholderText("ชื่อ TikTok (ไม่ต้องใส่ @)")
        self.sp_port = QtWidgets.QSpinBox(); self.sp_port.setRange(1000,65535)
        self.btn_start = QtWidgets.QPushButton("เริ่มใช้งาน")
        self.btn_stop  = QtWidgets.QPushButton("หยุด"); self.btn_stop.setEnabled(False)
        self.lbl_link_status = QtWidgets.QLabel("ยังไม่เชื่อม Roblox")
        for w in [QtWidgets.QLabel("TikTok:"), self.ed_user,
                  QtWidgets.QLabel("พอร์ต:"), self.sp_port,
                  self.btn_start, self.btn_stop,
                  QtWidgets.QLabel("สถานะเชื่อม:"), self.lbl_link_status]:
            row1.addWidget(w)
        self.btn_start.clicked.connect(self.handle_start); self.btn_stop.clicked.connect(self.handle_stop)

        # แถวสอง: link/unlink
        row2 = QtWidgets.QHBoxLayout(); root.addLayout(row2)
        self.ed_code = QtWidgets.QLineEdit(); self.ed_code.setPlaceholderText("รหัส 6 หลักจากในเกม")
        self.btn_link = QtWidgets.QPushButton("เชื่อม Roblox")
        self.btn_unlink = QtWidgets.QPushButton("ยกเลิกเชื่อม Roblox")
        row2.addWidget(self.ed_code, 2); row2.addWidget(self.btn_link, 1); row2.addWidget(self.btn_unlink, 1)
        self.btn_link.clicked.connect(self._link_with_code); self.ed_code.returnPressed.connect(self._link_with_code)
        self.btn_unlink.clicked.connect(self._manual_unlink)

        # Tabs
        self.tabs = QtWidgets.QTabWidget(); root.addWidget(self.tabs, 1)

        # หน้าหลัก
        home = QtWidgets.QWidget(); self.tabs.addTab(home, "หน้าหลัก")
        vh = QtWidgets.QVBoxLayout(home)
        self.txt_log = QtWidgets.QPlainTextEdit(); self.txt_log.setReadOnly(True)
        vh.addWidget(self.txt_log, 1)

        # ตั้งค่า
        st = QtWidgets.QWidget(); self.tabs.addTab(st, "ตั้งค่า")
        self._build_settings_tab(st)

        # ทดสอบ (animation only)
        test = QtWidgets.QWidget(); self.tabs.addTab(test, "ทดสอบ")
        ft = QtWidgets.QFormLayout(test)
        self.cb_emote  = QtWidgets.QComboBox(); self.cb_emote.setEditable(True); self.cb_emote.lineEdit().setPlaceholderText("พิมพ์ AnimationId หรือเลือกจากรายการ")
        for e in EMOTES_UI: self.cb_emote.addItem(f"{e.get('name','')}  ({e.get('id','')})", userData=e.get("id",""))
        self.sp_anim_secs = QtWidgets.QSpinBox(); self.sp_anim_secs.setRange(1,120); self.sp_anim_secs.setValue(5)
        self.btn_push  = QtWidgets.QPushButton("ส่งคำสั่งทดสอบ (animation)")
        ft.addRow("ท่าเต้น / รหัสท่า:", self.cb_emote)
        ft.addRow("ระยะเวลา (วิ):", self.sp_anim_secs)
        ft.addRow(self.btn_push)
        self.btn_push.clicked.connect(self._push_action)

        # ประวัติ
        hist = QtWidgets.QWidget(); self.tabs.addTab(hist, "ประวัติ")
        vh2 = QtWidgets.QVBoxLayout(hist)
        self.lbl_hist_summary = QtWidgets.QLabel("ของขวัญ: 0 | หัวใจ: 0 | คอมเมนต์: 0")
        vh2.addWidget(self.lbl_hist_summary)
        self.tbl_hist = QtWidgets.QTableWidget(0,7)
        self.tbl_hist.setHorizontalHeaderLabels(["เวลา","ประเภท","ชื่อ","รายละเอียด","จำนวน","เพชร","Action ที่แมตช์"])
        self.tbl_hist.horizontalHeader().setStretchLastSection(True)
        self.tbl_hist.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        vh2.addWidget(self.tbl_hist, 1)
        hb = QtWidgets.QHBoxLayout(); vh2.addLayout(hb)
        self.btn_hist_clear = QtWidgets.QPushButton("ล้างประวัติ")
        self.btn_hist_export = QtWidgets.QPushButton("ส่งออก CSV")
        hb.addWidget(self.btn_hist_clear); hb.addWidget(self.btn_hist_export); hb.addStretch(1)
        self.btn_hist_clear.clicked.connect(self._clear_history)
        self.btn_hist_export.clicked.connect(self._export_history_csv)

        self.statusBar().showMessage("พร้อมใช้งาน")

    def _build_settings_tab(self, st_widget: QtWidgets.QWidget):
        fs = QtWidgets.QFormLayout(st_widget)
        self.chk_auto = QtWidgets.QCheckBox("เปิดใช้งานเองทันทีเมื่อเปิดโปรแกรม")
        self.sp_queue = QtWidgets.QSpinBox(); self.sp_queue.setRange(100,100000)
        fs.addRow(self.chk_auto); fs.addRow("คิวสูงสุด:", self.sp_queue)

        fs.addRow(QtWidgets.QLabel("รับอีเวนต์จาก TikTok:"))
        self.chk_ev_gifts = QtWidgets.QCheckBox("รับของขวัญ")
        self.chk_ev_likes = QtWidgets.QCheckBox("รับหัวใจ (ไลก์)")
        self.chk_ev_comments = QtWidgets.QCheckBox("รับคอมเมนต์")
        for w in [self.chk_ev_gifts, self.chk_ev_likes, self.chk_ev_comments]:
            w.stateChanged.connect(self._settings_changed)
        fs.addRow(self.chk_ev_gifts); fs.addRow(self.chk_ev_likes); fs.addRow(self.chk_ev_comments)

        self.chk_default_pose = QtWidgets.QCheckBox("ตั้งท่านอนเป็นค่าเริ่มต้น (sleep)")
        self.chk_default_pose.stateChanged.connect(self._default_pose_toggled)
        fs.addRow(self.chk_default_pose)

        box = QtWidgets.QGroupBox("กฎอัตโนมัติ: ได้อะไร → ให้ทำอะไร (บันทึกอัตโนมัติ)")
        fs.addRow(box)
        vb = QtWidgets.QVBoxLayout(box)
        self.tbl_rules = QtWidgets.QTableWidget(0,8)
        self.tbl_rules.setHorizontalHeaderLabels(["เปิดใช้","เมื่อ","คำค้น/รายละเอียด","ขั้นต่ำ","คอมโบจบ","ทำ","พารามิเตอร์","คูลดาวน์(วิ)"])
        self.tbl_rules.horizontalHeader().setStretchLastSection(True)
        vb.addWidget(self.tbl_rules,1)
        hb = QtWidgets.QHBoxLayout(); vb.addLayout(hb)
        self.btn_add_gift = QtWidgets.QPushButton("เพิ่ม: ของขวัญ")
        self.btn_add_like = QtWidgets.QPushButton("เพิ่ม: หัวใจ")
        self.btn_add_cmt  = QtWidgets.QPushButton("เพิ่ม: คอมเมนต์")
        self.btn_dup      = QtWidgets.QPushButton("คัดลอก")
        self.btn_del      = QtWidgets.QPushButton("ลบ")
        for b in [self.btn_add_gift,self.btn_add_like,self.btn_add_cmt,self.btn_dup,self.btn_del]:
            hb.addWidget(b)
        hb.addStretch(1)
        self.btn_add_gift.clicked.connect(lambda: self._add_rule_via_dialog("gift"))
        self.btn_add_like.clicked.connect(lambda: self._add_rule_via_dialog("like"))
        self.btn_add_cmt.clicked.connect(lambda: self._add_rule_via_dialog("comment"))
        self.btn_dup.clicked.connect(self._duplicate_rule)
        self.btn_del.clicked.connect(self._delete_rule)

        self.tbl_rules.itemChanged.connect(self._table_edit_autosave)
        self._rules_to_table()

    # ----- rules helpers -----
    def _rules_to_table(self):
        self._building_rules = True
        self.tbl_rules.setRowCount(0)
        for r in self.cfg.mappings: self._append_rule_row(r)
        self._building_rules = False

    def _append_rule_row(self, r: MappingRule):
        # บังคับ action เป็น animation เสมอ
        r.action = "animation"
        row = self.tbl_rules.rowCount(); self.tbl_rules.insertRow(row)
        chk = QtWidgets.QTableWidgetItem(); chk.setFlags(chk.flags() | Qt.ItemIsUserCheckable)
        chk.setCheckState(Qt.Checked if r.enabled else Qt.Unchecked)
        self.tbl_rules.setItem(row,0, chk)
        self.tbl_rules.setItem(row,1, QtWidgets.QTableWidgetItem(r.trigger_type))
        self.tbl_rules.setItem(row,2, QtWidgets.QTableWidgetItem(r.pattern))
        self.tbl_rules.setItem(row,3, QtWidgets.QTableWidgetItem(str(r.min_count)))
        self.tbl_rules.setItem(row,4, QtWidgets.QTableWidgetItem("✓" if r.streak_end_only else ""))
        self.tbl_rules.setItem(row,5, QtWidgets.QTableWidgetItem("animation"))
        self.tbl_rules.setItem(row,6, QtWidgets.QTableWidgetItem(r.param))
        self.tbl_rules.setItem(row,7, QtWidgets.QTableWidgetItem(str(r.cooldown_sec)))

    def _table_to_rules(self) -> List[MappingRule]:
        rules: List[MappingRule] = []
        for r in range(self.tbl_rules.rowCount()):
            enabled = self.tbl_rules.item(r,0).checkState() == Qt.Checked if self.tbl_rules.item(r,0) else True
            tr = (self.tbl_rules.item(r,1).text() if self.tbl_rules.item(r,1) else "").strip()
            pattern = (self.tbl_rules.item(r,2).text() if self.tbl_rules.item(r,2) else "").strip()
            try: min_count = int(self.tbl_rules.item(r,3).text()) if self.tbl_rules.item(r,3) else 0
            except: min_count = 0
            streak = (self.tbl_rules.item(r,4).text().strip() == "✓") if self.tbl_rules.item(r,4) else False
            # action บังคับเป็น animation
            action = "animation"
            param  = (self.tbl_rules.item(r,6).text() if self.tbl_rules.item(r,6) else "").strip()
            try: cd = float(self.tbl_rules.item(r,7).text()) if self.tbl_rules.item(r,7) else 0.0
            except: cd = 0.0
            rules.append(MappingRule(enabled, tr or "gift", pattern, min_count, streak, action, param, cd))
        return rules

    def _add_rule_via_dialog(self, trig: str):
        dlg = RuleDialog(self, trig)
        if dlg.exec() == QtWidgets.QDialog.Accepted:
            r = dlg.result_rule()
            self._append_rule_row(r)
            self._autosave_rules("เพิ่มกฎแล้วและบันทึกอัตโนมัติ")
        else:
            self._on_status("ยกเลิกการเพิ่มกฎ")

    def _delete_rule(self):
        r = self.tbl_rules.currentRow()
        if r >= 0:
            self.tbl_rules.removeRow(r)
            self._autosave_rules("ลบกฎแล้ว (บันทึกอัตโนมัติ)")
        else:
            self._on_status("เลือกกฎก่อนลบ")

    def _duplicate_rule(self):
        r = self.tbl_rules.currentRow()
        if r < 0:
            self._on_status("เลือกกฎก่อนคัดลอก"); return
        allr = self._table_to_rules()
        if r < len(allr):
            self._append_rule_row(allr[r])
            self._autosave_rules("คัดลอกกฎแล้ว (บันทึกอัตโนมัติ)")

    def _table_edit_autosave(self, *_):
        if self._building_rules: return
        self._autosave_rules("บันทึกกฎอัตโนมัติแล้ว")

    def _autosave_rules(self, msg: str):
        self.cfg.mappings = self._table_to_rules()
        # ensure migrate
        for m in self.cfg.mappings:
            m.action = "animation"
        save_config(self.cfg)
        self.mapper.update(self.cfg)
        self._on_status(msg)

    # ----- state/load/save -----
    def _load_cfg_to_ui(self):
        self.ed_user.setText(self.cfg.tiktok_username)
        self.sp_port.setValue(self.cfg.port)
        self.chk_auto.setChecked(self.cfg.auto_start)
        self.sp_queue.setValue(self.cfg.max_queue)
        self.chk_ev_gifts.setChecked(self.cfg.enable_gifts)
        self.chk_ev_likes.setChecked(self.cfg.enable_likes)
        self.chk_ev_comments.setChecked(self.cfg.enable_comments)
        self.chk_default_pose.setChecked(self.cfg.default_pose_enabled)
        self._refresh_link_label()

    def _collect_cfg(self) -> AppConfig:
        return AppConfig(
            tiktok_username=self.ed_user.text().strip(),
            port=int(self.sp_port.value()),
            max_queue=int(self.sp_queue.value()),
            auto_start=self.chk_auto.isChecked(),
            enable_gifts=self.chk_ev_gifts.isChecked(),
            enable_likes=self.chk_ev_likes.isChecked(),
            enable_comments=self.chk_ev_comments.isChecked(),
            default_pose_enabled=self.chk_default_pose.isChecked(),
            default_pose_id=self.cfg.default_pose_id,
            owner_roblox_user_id=self.cfg.owner_roblox_user_id,
            owner_roblox_username=self.cfg.owner_roblox_username,
            mappings=self._table_to_rules()
        )

    def _refresh_link_label(self):
        if self.cfg.owner_roblox_user_id and self.cfg.owner_roblox_username:
            self.lbl_link_status.setText(f"เชื่อมกับ: {self.cfg.owner_roblox_username} ({self.cfg.owner_roblox_user_id})")
        else:
            self.lbl_link_status.setText("ยังไม่เชื่อม Roblox")

    # ----- control -----
    def handle_start(self):
        self.cfg = self._collect_cfg(); save_config(self.cfg)
        self.mapper.update(self.cfg)
        self.events = EventQueue(maxlen=self.cfg.max_queue)
        self.tk.events = self.events; self.api.events = self.events
        self.tk.set_username(self.cfg.tiktok_username)
        self.tk.set_filters(self.cfg.enable_gifts, self.cfg.enable_likes, self.cfg.enable_comments)
        self.api.apply_config(self.cfg)
        self.tk.start(); self.api.start()
        self._send_default_pose_event(self.cfg.default_pose_enabled)
        self.btn_start.setEnabled(False); self.btn_stop.setEnabled(True)
        self._on_status("เริ่มทำงานแล้ว")

    def handle_stop(self):
        self.events.push({"type":"unlink"})
        self.tk.stop(); self.api.stop()
        self.btn_start.setEnabled(True); self.btn_stop.setEnabled(False)
        self.cfg.owner_roblox_user_id = None
        self.cfg.owner_roblox_username = ""
        save_config(self.cfg)
        self._refresh_link_label()
        self._on_status("หยุดทำงานแล้ว และสั่งยกเลิกเชื่อม")

    # ----- link code flow -----
    def _link_with_code(self):
        code = self.ed_code.text().strip()
        if not code.isdigit() or len(code)!=6:
            self._on_status("รหัสต้องเป็นตัวเลข 6 หลัก"); return
        owner_uid = self.ed_user.text().strip() or "me"
        self.events.push({"type":"link_code","code":code,"user_id":owner_uid,"nickname":owner_uid})
        self._on_status(f"ส่งคำขอลิงก์แล้ว → @{owner_uid} (โค้ด {code})  — รอยืนยันจากเกม…")
        self.ed_code.clear()

    def _manual_unlink(self):
        self.events.push({"type":"unlink"})
        self._on_status("สั่งยกเลิกเชื่อมไปยังเกมแล้ว…")

    # ----- default pose -----
    def _send_default_pose_event(self, enabled: bool):
        self.events.push({"type":"default_pose","enabled":bool(enabled),"emote_id": self.cfg.default_pose_id})

    def _default_pose_toggled(self, *_):
        self.cfg.default_pose_enabled = self.chk_default_pose.isChecked()
        save_config(self.cfg)
        self._send_default_pose_event(self.cfg.default_pose_enabled)
        self._on_status("อัปเดตค่า default pose แล้ว")

    # ----- test (animation only) -----
    def _push_action(self):
        pick = self.cb_emote.currentData()
        raw = self.cb_emote.currentText().strip()
        anim_id = pick or raw
        secs = int(self.sp_anim_secs.value())
        self.events.push({"type":"action","scope":"owner","action":{"name":"animation","param":anim_id, "duration": secs}})
        self._on_status(f"ส่งคำสั่งทดสอบ → animation({anim_id}|{secs}s)")

    # ----- history -----
    def _add_history_row(self, ev: Dict[str,Any]):
        t = time.strftime("%H:%M:%S")
        row = self.tbl_hist.rowCount(); self.tbl_hist.insertRow(row)

        typ = ev.get("type","")
        name = ev.get("nickname") or ev.get("user_id") or ""
        detail = ""
        qty = ""
        dia = ""
        act = ""
        if typ == "gift":
            detail = ev.get("gift_name") or ""
            qty = str(ev.get("repeat_count") or "")
            dia = str(ev.get("diamonds") or "")
        elif typ == "like":
            qty = str(ev.get("like_count") or 1)
        elif typ == "comment":
            detail = ev.get("comment") or ""
        a = ev.get("action")
        if a:
            p = a.get('param') or ''
            dur = a.get('duration')
            act = f"animation({p}|{dur}s)" if dur else f"animation({p})"

        for col,val in enumerate([t, typ, name, detail, qty, dia, act]):
            self.tbl_hist.setItem(row, col, QtWidgets.QTableWidgetItem(val))
        self.tbl_hist.scrollToBottom()

    def _update_hist_summary(self):
        self.lbl_hist_summary.setText(f"ของขวัญ: {self.total_gifts} | หัวใจ: {self.total_likes} | คอมเมนต์: {self.total_comments}")

    def _clear_history(self):
        self.history.clear()
        self.total_gifts = self.total_likes = self.total_comments = 0
        self.tbl_hist.setRowCount(0)
        self._update_hist_summary()
        self._on_status("ล้างประวัติแล้ว")

    def _export_history_csv(self):
        if not self.history:
            self._on_status("ยังไม่มีประวัติให้ส่งออก")
            return
        fn = os.path.join(config_dir(), f"history_{int(time.time())}.csv")
        try:
            with open(fn, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f)
                w.writerow(["ts","type","nickname","detail","count","diamonds","matched_action"])
                for ev in self.history:
                    typ = ev.get("type","")
                    nick = ev.get("nickname") or ev.get("user_id") or ""
                    detail = ""
                    count = ""
                    dia = ""
                    if typ=="gift":
                        detail = ev.get("gift_name") or ""
                        count = str(ev.get("repeat_count") or "")
                        dia = str(ev.get("diamonds") or "")
                    elif typ=="like":
                        count = str(ev.get("like_count") or "")
                    elif typ=="comment":
                        detail = ev.get("comment") or ""
                    act = ev.get("action")
                    if act:
                        p = act.get('param') or ''
                        dur = act.get('duration')
                        act_s = f"animation({p}|{dur}s)" if dur else f"animation({p})"
                    else:
                        act_s = ""
                    w.writerow([ev.get("ts"), typ, nick, detail, count, dia, act_s])
            self._on_status(f"ส่งออกแล้ว → {fn}")
        except Exception as e:
            self._on_status(f"ส่งออกไม่สำเร็จ: {e}")

    # ----- misc -----
    def _settings_changed(self, *args):
        self.cfg.auto_start = self.chk_auto.isChecked()
        self.cfg.max_queue = int(self.sp_queue.value())
        self.cfg.enable_gifts = self.chk_ev_gifts.isChecked()
        self.cfg.enable_likes = self.chk_ev_likes.isChecked()
        self.cfg.enable_comments = self.chk_ev_comments.isChecked()
        save_config(self.cfg)
        if self.tk: self.tk.set_filters(self.cfg.enable_gifts, self.cfg.enable_likes, self.cfg.enable_comments)
        self._on_status("บันทึกการตั้งค่าแล้ว")

    # ----- signals -----
    @Slot(str)
    def _on_status(self, msg: str):
        self.statusBar().showMessage(msg)
        self.txt_log.appendPlainText(msg)
        write_log(msg)

    @Slot(dict)
    def _on_event(self, ev: Dict[str,Any]):
        t = ev.get("type")

        if t == "link_confirmed":
            rid = ev.get("roblox_user_id")
            rname = ev.get("roblox_username") or ""
            if rid:
                self.cfg.owner_roblox_user_id = int(rid)
                self.cfg.owner_roblox_username = rname
                save_config(self.cfg)
                self._refresh_link_label()
            self._on_status(f"เชื่อมแล้ว ✓ @{ev.get('nickname') or ev.get('tiktok_user_id')} ↔ {rname} ({rid})")
            return

        if t == "unlink_confirm":
            self.cfg.owner_roblox_user_id = None
            self.cfg.owner_roblox_username = ""
            save_config(self.cfg); self._refresh_link_label()
            self._on_status("สถานะ: ยกเลิกเชื่อมเรียบร้อย (ยืนยันจากเกม)")
            return

        if t in ("gift","like","comment"):
            self.history.append(ev)
            if t=="gift":
                self.total_gifts += int(ev.get("repeat_count") or 1)
            elif t=="like":
                self.total_likes += int(ev.get("like_count") or 1)
            elif t=="comment":
                self.total_comments += 1
            self._add_history_row(ev)
            self._update_hist_summary()

            who = ev.get("nickname") or ev.get("user_id") or ""
            extra = ""
            if t=="gift": extra = f"{ev.get('gift_name')} x{ev.get('repeat_count')}"
            if t=="like": extra = f"+{ev.get('like_count') or 1} likes"
            if t=="comment": extra = ev.get("comment") or ""
            act = ev.get("action")
            if act:
                p = act.get('param','')
                if act.get('duration'):
                    extra += f" → action: animation({p}|{act.get('duration')}s)"
                else:
                    extra += f" → action: animation({p})"
            self._on_status(f"{t}: {who} {extra}")

        elif t=="action":
            a = ev.get("action",{})
            self._on_status(f"action(scope=owner): animation({a.get('param')})")

# ---------- RuleDialog (animation only) ----------
class RuleDialog(QtWidgets.QDialog):
    def __init__(self, parent, trigger_type: str):
        super().__init__(parent)
        self.setWindowTitle("เพิ่มกฎใหม่")
        self.trigger_type = trigger_type
        self.setModal(True)
        lay = QtWidgets.QFormLayout(self)

        self.ed_pattern = QtWidgets.QLineEdit()
        self.sp_min = QtWidgets.QSpinBox(); self.sp_min.setRange(0, 1_000_000); self.sp_min.setValue(10)
        self.chk_streak = QtWidgets.QCheckBox("ยิงตอนจบคอมโบ (ของขวัญ)")

        # animation param
        self.cb_anim = QtWidgets.QComboBox(); self.cb_anim.setEditable(True); self.cb_anim.lineEdit().setPlaceholderText("พิมพ์ หรือเลือกจากรายการ")
        for e in EMOTES_UI:
            self.cb_anim.addItem(f"{e['name']}  ({e['id']})", userData=e['id'])
        self.sp_anim_secs = QtWidgets.QSpinBox(); self.sp_anim_secs.setRange(1, 120); self.sp_anim_secs.setValue(5)

        self.sp_cd = QtWidgets.QDoubleSpinBox(); self.sp_cd.setRange(0, 3600); self.sp_cd.setDecimals(2); self.sp_cd.setValue(1.0)

        if trigger_type == "gift":
            lay.addRow("ชื่อของขวัญมีคำว่า:", self.ed_pattern)
            lay.addRow("", self.chk_streak)
        elif trigger_type == "like":
            lay.addRow("หัวใจครบ (ครั้ง):", self.sp_min)
        elif trigger_type == "comment":
            lay.addRow("ข้อความมีคำว่า:", self.ed_pattern)

        lay.addRow("ท่าเต้น (animation):", self.cb_anim)
        lay.addRow("เต้นกี่วิ:", self.sp_anim_secs)
        lay.addRow("คูลดาวน์รายคน (วินาที):", self.sp_cd)

        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok|QtWidgets.QDialogButtonBox.Cancel)
        lay.addRow(btns)
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject)

    def result_rule(self) -> MappingRule:
        r = MappingRule()
        r.trigger_type = self.trigger_type
        if self.trigger_type in ("gift","comment"): r.pattern = self.ed_pattern.text().strip()
        if self.trigger_type == "like": r.min_count = int(self.sp_min.value())
        if self.trigger_type == "gift": r.streak_end_only = self.chk_streak.isChecked()

        pick = self.cb_anim.currentData()
        raw = self.cb_anim.currentText().strip()
        anim_id = pick or raw
        secs = int(self.sp_anim_secs.value())
        r.action = "animation"
        r.param = f"{anim_id}|{secs}"

        r.cooldown_sec = float(self.sp_cd.value())
        return r

# ---------- Entry ----------
def main():
    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow(); w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
