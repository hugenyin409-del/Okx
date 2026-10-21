import requests
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
import feedparser
import sqlite3
import hashlib
import hmac
import secrets
import os
import re
import time
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path
from datetime import datetime, timezone

st.set_page_config(page_title="NEXUS | 数字资产行情研究终端", page_icon="📈", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"], [data-testid="stAppViewContainer"] {font-family:Inter,"PingFang SC","Microsoft YaHei",sans-serif;}
[data-testid="stAppViewContainer"] {
  background: radial-gradient(ellipse 72% 45% at 85% 0%,rgba(32,95,167,.21),transparent 72%),
              radial-gradient(ellipse 60% 55% at 0% 80%,rgba(14,95,115,.14),transparent 72%),#070d18;
  color:#e9f0fb;
}
[data-testid="stHeader"] {background:rgba(7,13,24,.6);}
[data-testid="stSidebar"] {background:#0b1424;border-right:1px solid rgba(115,155,210,.15);}
.block-container {padding-top:2rem;max-width:1450px;}
h1,h2,h3 {letter-spacing:-.025em;color:#f0f6ff!important;}
h1 {font-weight:800!important;}
[data-testid="stMetric"] {background:linear-gradient(145deg,rgba(24,43,68,.94),rgba(13,26,45,.92));border:1px solid rgba(102,151,211,.19);border-radius:16px;padding:16px 18px;}
[data-testid="stMetricValue"] {color:#e6f6ff;font-weight:700;}
[data-testid="stExpander"] {background:rgba(13,27,47,.78);border:1px solid rgba(107,155,214,.17);border-radius:14px;overflow:hidden;}
div.stButton > button[kind="primary"],div.stFormSubmitButton > button[kind="primary"] {background:linear-gradient(110deg,#1679df,#17a5c2);color:white;border:0;border-radius:11px;font-weight:700;}
div.stButton > button,div.stFormSubmitButton > button {border-radius:11px;}
[data-testid="stForm"] {background:rgba(13,26,46,.83);border:1px solid rgba(99,154,217,.23);border-radius:20px;padding:22px;}
.nexus-kicker {color:#5dbdf8;font-size:12px;font-weight:800;letter-spacing:.24em;margin-bottom:9px;}
.nexus-hero {background:linear-gradient(110deg,rgba(17,40,69,.95),rgba(10,22,41,.85));border:1px solid rgba(95,154,224,.24);border-radius:22px;padding:25px 30px;margin:10px 0 22px;box-shadow:0 20px 55px rgba(0,0,0,.16);}
.nexus-hero h1 {margin:0;font-size:clamp(27px,3.4vw,42px);line-height:1.2;}
.nexus-hero p {color:#a8bbd5;margin:11px 0 0;font-size:14px;}
.nexus-brand {font-size:14px;font-weight:800;letter-spacing:.22em;color:#8bd7ff;}
.nexus-small {color:#8299b8;font-size:12px;}
.nexus-ticker {overflow:hidden;white-space:nowrap;border:1px solid rgba(71,166,235,.28);background:rgba(11,35,59,.86);border-radius:12px;padding:10px 0;margin:0 0 16px;}
.nexus-ticker span {display:inline-block;padding-left:100%;animation:nexus-marquee 24s linear infinite;color:#b9e7ff;font-size:13px;font-weight:600;}
@keyframes nexus-marquee {from{transform:translateX(0)}to{transform:translateX(-100%)}}
@media(prefers-reduced-motion:reduce){.nexus-ticker span{animation:none;padding-left:12px;white-space:normal}}

/* NEXUS Terminal Pro: cohesive visual system, responsive and accessible */
:root{--nx-bg:#080d15;--nx-panel:#111b2a;--nx-border:rgba(136,171,209,.16);--nx-blue:#64c6ff;--nx-muted:#94a8c0}
[data-testid="stAppViewContainer"]{background:radial-gradient(ellipse 65% 28% at 60% -7%,rgba(34,106,173,.17),transparent 80%),linear-gradient(180deg,#080f1a 0%,#080d15 70%)!important}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#0c1624,#0a111d)!important;border-right:1px solid var(--nx-border)!important}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"]{gap:.58rem}
[data-testid="stHeader"]{background:rgba(8,14,24,.76)!important;backdrop-filter:blur(16px)}
.block-container{max-width:1540px!important;padding-top:1.35rem!important;padding-bottom:3rem!important}
h1,h2,h3{font-weight:720!important;letter-spacing:-.035em!important}
h3{font-size:1.23rem!important}
[data-testid="stMetric"]{background:linear-gradient(150deg,rgba(21,35,55,.98),rgba(12,23,39,.97))!important;border:1px solid var(--nx-border)!important;border-radius:14px!important;padding:20px!important;box-shadow:0 10px 32px rgba(0,0,0,.12)}
[data-testid="stMetricLabel"]{color:var(--nx-muted)!important;letter-spacing:.025em}
[data-testid="stMetricValue"]{font-variant-numeric:tabular-nums;letter-spacing:-.04em;font-size:clamp(1.25rem,2vw,1.9rem)!important}
[data-testid="stExpander"],[data-testid="stForm"]{border:1px solid var(--nx-border)!important;border-radius:14px!important;background:rgba(16,28,45,.8)!important}
[data-testid="stExpander"]{box-shadow:none!important}
[data-testid="stForm"]{padding:20px!important}
[data-testid="stSelectbox"]>div>div,[data-testid="stNumberInput"] input,[data-testid="stTextInput"] input,[data-testid="stTextArea"] textarea{border-radius:10px!important;background:#0e1929!important;border-color:rgba(124,158,198,.21)!important}
div.stButton>button,div.stFormSubmitButton>button{min-height:40px;border-radius:10px!important;transition:transform .15s,border-color .15s,background .15s}
div.stButton>button:hover,div.stFormSubmitButton>button:hover{border-color:#58b7ed!important;transform:translateY(-1px)}
div.stButton>button[kind="primary"],div.stFormSubmitButton>button[kind="primary"]{background:linear-gradient(120deg,#1874bf,#2498c9)!important;box-shadow:0 6px 22px rgba(24,116,191,.2)}
[data-testid="stAlert"]{border-radius:11px!important;border:1px solid rgba(132,169,211,.16)!important}
hr{border-color:rgba(130,159,191,.12)!important;margin:1.15rem 0!important}
.nexus-brand{font-size:16px!important;letter-spacing:.19em!important;color:#c0ebff!important;padding-top:6px}
.nexus-kicker{font-size:11px!important;letter-spacing:.25em!important;color:#78bfe7!important}
.nexus-hero{position:relative;overflow:hidden;background:linear-gradient(115deg,rgba(19,42,67,.98),rgba(10,24,40,.97))!important;border:1px solid rgba(105,164,218,.2)!important;border-radius:18px!important;padding:29px 34px!important;box-shadow:0 18px 45px rgba(0,0,0,.14)!important}
.nexus-hero:after{content:"";position:absolute;right:-65px;top:-125px;width:310px;height:310px;border-radius:50%;border:1px solid rgba(105,190,246,.12);box-shadow:0 0 0 42px rgba(81,161,219,.025),0 0 0 85px rgba(81,161,219,.018);pointer-events:none}
.nexus-hero h1{font-size:clamp(26px,3vw,38px)!important;font-weight:750!important}
.nexus-hero p{max-width:760px;color:#a6bdd4!important;line-height:1.7}
.nexus-ticker{border-radius:9px!important;background:rgba(15,37,57,.85)!important;border-color:rgba(81,154,210,.18)!important}
[data-testid="stSidebar"] [data-testid="stSelectbox"]{margin:4px 0 10px}
@media(max-width:768px){.block-container{padding:1rem .8rem 2rem!important}.nexus-hero{padding:21px 19px!important}.nexus-hero:after{opacity:.35}[data-testid="stMetric"]{padding:13px!important}[data-testid="stMetricValue"]{font-size:1.18rem!important}}
@media(prefers-reduced-motion:reduce){div.stButton>button,div.stFormSubmitButton>button{transition:none!important;transform:none!important}}


/* Compact workspace tiles; keep navigation as native Streamlit buttons. */
.nexus-workspace-label{font-size:10px;letter-spacing:.17em;color:#819bb6;margin:0 0 7px;font-weight:750}
.nexus-workspace-label span{letter-spacing:0;font-weight:500;color:#86c9ed;margin-left:6px}
[class*="st-key-workspace_top_"] button{min-height:57px!important;height:57px!important;padding:7px 5px!important;border-radius:11px!important;background:linear-gradient(145deg,rgba(21,37,58,.97),rgba(12,23,38,.98))!important;border:1px solid rgba(121,158,198,.2)!important;box-shadow:none!important;font-size:clamp(10px,1.2vw,13px)!important;font-weight:650!important;line-height:1.3!important;white-space:normal!important}
[class*="st-key-workspace_top_"] button[kind="primary"]{background:linear-gradient(145deg,#153d60,#102b45)!important;border-color:rgba(97,194,246,.7)!important;box-shadow:inset 0 0 0 1px rgba(78,170,222,.12)!important}
[class*="st-key-workspace_top_"] button:hover{border-color:#68c4f1!important}
@media(max-width:768px){[class*="st-key-workspace_top_"] button{min-height:52px!important;height:52px!important;padding:5px 2px!important;font-size:10px!important;border-radius:9px!important}.nexus-workspace-label{margin-bottom:5px}}
</style>
""",unsafe_allow_html=True)

# Prototype authentication storage: set AUTH_DB_PATH to a durable mounted volume.
# For public deployment use managed authentication + verified email and a persistent DB.
AUTH_DB_PATH = os.environ.get("AUTH_DB_PATH", "/tmp/nexus_members.db")
def auth_connection():
    Path(AUTH_DB_PATH).parent.mkdir(parents=True,exist_ok=True)
    conn=sqlite3.connect(AUTH_DB_PATH,timeout=10)
    conn.execute("PRAGMA busy_timeout=10000")
    conn.execute("""CREATE TABLE IF NOT EXISTS members (
        email TEXT PRIMARY KEY, salt TEXT NOT NULL, password_hash TEXT NOT NULL,
        created_at TEXT NOT NULL, is_active INTEGER NOT NULL DEFAULT 1
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS member_feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL,
        period TEXT NOT NULL,
        rating TEXT NOT NULL,
        comment TEXT NOT NULL,
        created_at TEXT NOT NULL
    )""")
    conn.commit()
    return conn

def feedback_mail_settings():
    def setting(key):
        try:
            return str(st.secrets.get(key, os.environ.get(key, ""))).strip()
        except Exception:
            return os.environ.get(key, "").strip()
    sender=setting("GMAIL_SMTP_EMAIL")
    app_password=setting("GMAIL_APP_PASSWORD")
    recipient=setting("FEEDBACK_RECEIVER_EMAIL") or sender
    return sender,app_password,recipient

def send_feedback_email(member_email,period,rating,comment,created_at):
    sender,app_password,recipient=feedback_mail_settings()
    if not (sender and app_password and recipient):
        return False,"not_configured"
    msg=EmailMessage()
    msg["Subject"]="[NEXUS] 新的会员反馈"
    msg["From"]=sender
    msg["To"]=recipient
    msg.set_content(
        "NEXUS 内测会员反馈\\n\\n"
        f"会员邮箱：{member_email}\\n"
        f"预测周期：{period}\\n"
        f"评价：{rating}\\n"
        f"提交时间（UTC）：{created_at}\\n\\n"
        f"反馈内容：\\n{comment}\\n"
    )
    try:
        context=ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com",465,timeout=12,context=context) as smtp:
            smtp.login(sender,app_password)
            smtp.send_message(msg)
        return True,"sent"
    except Exception:
        return False,"failed"

def normalize_email(value):
    return value.strip().lower()

def valid_email(value):
    if len(value) > 254 or "@" not in value:
        return False
    local, domain = value.rsplit("@", 1)
    return bool(local and len(local) <= 64 and re.fullmatch(r"[A-Za-z0-9.!#$%&'*+/=?^`{|}~-]+", local)
                and re.fullmatch(r"[A-Za-z0-9-]+(?:[.][A-Za-z0-9-]+)+", domain)
                and all(not part.startswith("-") and not part.endswith("-") for part in domain.split(".")))

def password_hash(password,salt):
    return hashlib.pbkdf2_hmac("sha256",password.encode("utf-8"),bytes.fromhex(salt),310000).hex()

def register_member(email,password):
    salt=secrets.token_hex(16)
    with auth_connection() as conn:
        conn.execute("INSERT INTO members(email,salt,password_hash,created_at) VALUES(?,?,?,?)",
                     (email,salt,password_hash(password,salt),datetime.now(timezone.utc).isoformat()))

def verify_member(email,password):
    with auth_connection() as conn:
        row=conn.execute("SELECT salt,password_hash,is_active FROM members WHERE email=?",(email,)).fetchone()
    if row is None:
        # Do equivalent expensive work to reduce obvious account enumeration timing.
        password_hash(password,"00"*16)
        return False
    return bool(row[2]) and hmac.compare_digest(password_hash(password,row[0]),row[1])

def active_member(email):
    with auth_connection() as conn:
        row=conn.execute("SELECT is_active FROM members WHERE email=?",(email,)).fetchone()
    return bool(row and row[0])

def login_gate():
    if st.session_state.get("member_email"):
        if active_member(st.session_state["member_email"]):
            return
        st.session_state.pop("member_email",None)
    st.markdown('<div class="nexus-kicker">NEXUS / RESEARCH TERMINAL</div>',unsafe_allow_html=True)
    st.markdown('<div class="nexus-hero"><h1>洞察市场，始于数据。</h1><p>BTC · ETH 多周期行情研究 / 预测区间 / 风险评估 · 注册免费开放</p></div>',unsafe_allow_html=True)
    left,mid,right=st.columns([1,1.4,1])
    with mid:
        tab_login,tab_register=st.tabs(["🔐 会员登录","✉️ 免费注册"])
        with tab_login:
            with st.form("nexus_login",clear_on_submit=False):
                email=st.text_input("邮箱地址",key="login_email",placeholder="you@example.com")
                password=st.text_input("登录密码",type="password",key="login_password")
                submit=st.form_submit_button("登录研究终端",type="primary",use_container_width=True)
                if submit:
                    now=time.monotonic()
                    attempts=st.session_state.get("login_attempts",[])
                    attempts=[t for t in attempts if now-t<900]
                    if len(attempts)>=8:
                        st.error("尝试次数过多，请15分钟后再试。")
                    elif verify_member(normalize_email(email),password):
                        st.session_state["member_email"]=normalize_email(email)
                        st.session_state["login_attempts"]=[]
                        st.rerun()
                    else:
                        st.session_state["login_attempts"]=attempts+[now]
                        st.error("邮箱或密码错误，或账号已停用。")
        with tab_register:
            with st.form("nexus_register",clear_on_submit=False):
                new_email=st.text_input("注册邮箱",placeholder="you@example.com")
                new_password=st.text_input("设置密码（至少12位）",type="password")
                confirm=st.text_input("确认密码",type="password")
                accepted=st.checkbox("我理解本站仅提供研究参考，不提供交易或收益保证")
                create=st.form_submit_button("免费创建账号",type="primary",use_container_width=True)
                if create:
                    normalized=normalize_email(new_email)
                    if not valid_email(normalized):
                        st.error("请输入有效的邮箱地址。")
                    elif len(new_password)<12 or len(new_password)>128:
                        st.error("密码长度需要在12至128位之间。")
                    elif new_password!=confirm:
                        st.error("两次密码不一致。")
                    elif not accepted:
                        st.error("请先确认使用须知。")
                    else:
                        try:
                            register_member(normalized,new_password)
                            st.success("注册成功！请切换到会员登录。")
                        except sqlite3.IntegrityError:
                            st.error("该邮箱已注册，请直接登录。")
                        except Exception:
                            st.error("注册暂不可用，请稍后再试。")
        st.caption("当前为免费注册测试版：尚未发送邮箱验证邮件，也没有找回密码功能。正式对外开放前需要持久化数据库、邮箱验证和完善的安全防护。")
    st.stop()

login_gate()
with st.sidebar:
    st.markdown('<div class="nexus-brand">◈ NEXUS TERMINAL</div>', unsafe_allow_html=True)
    st.caption("DIGITAL MARKET INTELLIGENCE")
    st.divider()
    st.markdown("##### 👤 会员账户")
    st.caption("当前登录")
    st.write(st.session_state["member_email"])
    st.success("● FREE 会员 · 已登录")
    st.divider()
    st.markdown("##### 🧭 研究导航")
    def on_research_navigation_change():
        st.session_state["nexus_close_sidebar_requested"] = True

    research_view=st.selectbox(
        "选择研究页面",
        ["📊 行情总览","🔬 高级研究","📰 市场新闻","🏦 宏观日历"],
        key="research_navigation",
        on_change=on_research_navigation_change,
        help="切换工作区后，手机端尝试自动收起侧边栏",
    )
    if st.session_state.pop("nexus_close_sidebar_requested", False):
        # Streamlit has no public Python API to close the sidebar after a widget change.
        # This optional browser-side enhancement is guarded to avoid breaking navigation.
        import streamlit.components.v1 as components
        components.html("""
        <script>
        (function () {
          function closeSidebar() {
            try {
              const doc = window.parent.document;
              const sidebar = doc.querySelector('[data-testid="stSidebar"]');
              if (!sidebar) return;
              const expanded = sidebar.getAttribute('aria-expanded');
              const close = sidebar.querySelector('[data-testid="stSidebarCollapseButton"] button, button[aria-label*="Close"], button[aria-label*="close"], button[aria-label*="收起"], button[aria-label*="关闭"]');
              if (close && expanded !== 'false') close.click();
            } catch (e) { /* Browser isolation may prevent parent access. */ }
          }
          setTimeout(closeSidebar, 180);
          setTimeout(closeSidebar, 500);
        })();
        </script>
        """, height=0)

    st.caption("高级研究包含历史回测、实验模型与前瞻验证。")

    with st.expander("📚 使用指南", expanded=False):
        st.write("**行情与参考位**：查看市场价格、预测区间和K线。")
        st.write("**币圈新闻**：浏览市场信息。")
        st.write("**美联储与宏观**：查看事件风险。")
        st.write("**高级研究**：从左侧工作区单独进入。")
    with st.expander("⚙️ 会员中心", expanded=False):
        st.write("会员等级：免费会员")
        st.write("登录邮箱：", st.session_state["member_email"])
        st.caption("当前为测试版账号系统，邮箱验证、密码找回及付费会员尚未开放。")
    st.divider()
    st.markdown("##### 🖥️ 系统运行状态")
    st.success("● 页面服务：运行中")
    try:
        with auth_connection() as status_db:
            status_db.execute("SELECT 1").fetchone()
        st.success("● 会员数据库：连接正常")
    except Exception:
        st.warning("● 会员数据库：连接异常")
    st.caption("行情接口状态请以主页面实际加载结果为准；此处不代表交易所接口已检测。")
    st.caption("NEXUS RESEARCH · BETA")
    st.caption("仅供研究与风险参考，不提供投资建议，不自动交易。")
    if st.button("↪ 退出登录", key="nexus_logout", use_container_width=True):
        st.session_state.pop("member_email", None)
        st.rerun()

st.markdown('<div class="nexus-ticker"><span>📢 NEXUS 平台内测期间免费开放　｜　预测区间仅供研究参考，不保证准确率或交易收益　｜　欢迎在页面底部反馈预测体验与改进建议　｜　感谢参与内测</span></div>',unsafe_allow_html=True)
# Visible workspace navigation: works even if the mobile sidebar overlay stays open.
# Both sidebar and main navigation share the same session-state key.
def switch_workspace(target):
    st.session_state["research_navigation"] = target
    st.session_state["nexus_close_sidebar_requested"] = True

workspace_names = ["📊 行情总览", "🔬 高级研究", "📰 市场新闻", "🏦 宏观日历"]
# Compact four-tile navigation; selection remains synchronized with the sidebar.
st.markdown('<div class="nexus-workspace-label">WORKSPACE <span>· ' + research_view + '</span></div>', unsafe_allow_html=True)
workspace_cols = st.columns(4, gap="small")
for workspace_col, workspace_name in zip(workspace_cols, workspace_names):
    with workspace_col:
        st.button(
            workspace_name,
            key="workspace_top_" + workspace_name,
            use_container_width=True,
            type="primary" if research_view == workspace_name else "secondary",
            on_click=switch_workspace,
            args=(workspace_name,),
        )

st.markdown('<div class="nexus-kicker">NEXUS / MARKET INTELLIGENCE</div>',unsafe_allow_html=True)
st.markdown('<div class="nexus-hero"><h1>NEXUS / Market Intelligence</h1><p>BTC · ETH 数字资产研究终端　/　实时行情　/　K线结构　/　波动区间　/　风险模拟</p></div>',unsafe_allow_html=True)


BASE = "https://www.okx.com"
S = requests.Session()
S.headers.update({"User-Agent": "Mozilla/5.0 OKXResearchDashboard/2.0"})

def okx(path, params=None):
    r = S.get(BASE + path, params=params, timeout=12)
    r.raise_for_status()
    j = r.json()
    if j.get("code") != "0":
        raise RuntimeError(j.get("msg") or "OKX 接口返回错误")
    return j.get("data", [])

@st.cache_data(ttl=90, show_spinner=False)
def candles(inst, bar):
    rows, cursor = [], None
    for _ in range(12 if bar == "1H" else (8 if bar == "1W" else 3)):
        p = {"instId": inst, "bar": bar, "limit": "100"}
        if cursor: p["after"] = str(cursor)
        batch = okx("/api/v5/market/history-candles", p)
        if not batch: break
        rows.extend(batch)
        oldest = min(int(x[0]) for x in batch)
        if cursor and oldest >= cursor: break
        cursor = oldest
    if not rows: raise RuntimeError("没有获取到 K 线")
    df = pd.DataFrame(rows, columns=["ts","open","high","low","close","vol","volCcy","volQuote","confirm"])
    df = df[df.confirm == "1"].copy()
    for c in ["open","high","low","close","vol"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["ts"] = pd.to_datetime(pd.to_numeric(df.ts), unit="ms", utc=True).dt.tz_convert("Asia/Shanghai")
    return df.dropna(subset=["close"]).drop_duplicates("ts").sort_values("ts").tail(1200 if bar == "1H" else (800 if bar == "1W" else 240)).reset_index(drop=True)

@st.cache_data(ttl=86400, show_spinner=False)
def historical_hourly(inst):
    rows, cursor = [], None
    for _ in range(90):
        params = {"instId":inst,"bar":"1H","limit":"100"}
        if cursor is not None: params["after"] = str(cursor)
        batch = okx("/api/v5/market/history-candles", params)
        if not batch: break
        oldest = min(int(x[0]) for x in batch)
        if cursor is not None and oldest >= cursor: break
        rows.extend(batch)
        cursor = oldest
        if len(rows) >= 8800: break
    if not rows: raise RuntimeError("历史小时线接口未返回数据")
    frame = pd.DataFrame(rows, columns=["ts","open","high","low","close","vol","volCcy","volQuote","confirm"])
    frame = frame[frame.confirm == "1"].copy()
    frame["ts"] = pd.to_datetime(pd.to_numeric(frame.ts),unit="ms",utc=True).dt.tz_convert("Asia/Shanghai")
    frame["close"] = pd.to_numeric(frame.close,errors="coerce")
    return frame.dropna(subset=["ts","close"]).drop_duplicates("ts").sort_values("ts").tail(8760).reset_index(drop=True)

@st.cache_data(ttl=15, show_spinner=False)
def market(inst):
    def safe(path, params):
        try:
            result = okx(path, params)
            return result[0] if result else {}
        except (requests.RequestException, RuntimeError, ValueError):
            return {}
    ticker = safe("/api/v5/market/ticker", {"instId":inst})
    mark = safe("/api/v5/public/mark-price", {"instType":"SWAP","instId":inst})
    funding = safe("/api/v5/public/funding-rate", {"instId":inst})
    oi = safe("/api/v5/public/open-interest", {"instType":"SWAP","instId":inst})
    spec = safe("/api/v5/public/instruments", {"instType":"SWAP","instId":inst})
    return {"ticker":ticker, "mark":mark, "funding":funding, "oi":oi, "spec":spec}

def indicators(df):
    d = df.copy()
    c = d.close
    d["ema20"] = c.ewm(span=20,adjust=False).mean()
    d["ema50"] = c.ewm(span=50,adjust=False).mean()
    delta = c.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/14,adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/14,adjust=False).mean()
    rs = gain / loss.replace(0,np.nan)
    d["rsi"] = (100-100/(1+rs)).fillna(50)
    d["macd"] = c.ewm(span=12,adjust=False).mean()-c.ewm(span=26,adjust=False).mean()
    d["signal"] = d.macd.ewm(span=9,adjust=False).mean()
    tr = pd.concat([d.high-d.low,(d.high-c.shift()).abs(),(d.low-c.shift()).abs()],axis=1).max(axis=1)
    d["atr"] = tr.ewm(alpha=1/14,adjust=False).mean()
    d["vol_ma"] = d.vol.rolling(20).mean()
    return d

def direction(row):
    if row.close > row.ema20 > row.ema50 and row.macd > row.signal:
        return "偏多", "收盘价高于 EMA20/EMA50，且 MACD 高于信号线"
    if row.close < row.ema20 < row.ema50 and row.macd < row.signal:
        return "偏空", "收盘价低于 EMA20/EMA50，且 MACD 低于信号线"
    return "观望", "均线和 MACD 未同时确认方向"

@st.cache_data(ttl=900, show_spinner=False)
def feed(url):
    r = S.get(url, timeout=12)
    r.raise_for_status()
    return feedparser.parse(r.content).entries[:8]

def fmt(value, digits=2):
    try: return f"{float(value):,.{digits}f}"
    except (ValueError,TypeError): return "暂无"

@st.cache_data(ttl=300, show_spinner=False)
def multi_timeframe(inst):
    result = {}
    for tf in ("4H", "1D", "1W"):
        try:
            data = indicators(candles(inst, tf))
            result[tf] = direction(data.iloc[-1])[0] if len(data) >= 60 else "样本不足"
        except Exception:
            result[tf] = "数据不可用"
    return result

pair = st.selectbox("交易对", ["BTC-USDT-SWAP","ETH-USDT-SWAP"])
bar = st.radio("K 线周期", ["15m","1H","4H","1D","1W"], index=2, horizontal=True)
a,b,c = st.columns(3)
with a: capital = st.number_input("模拟本金（USDT）", min_value=100.0, value=1000.0, step=100.0)
with b: risk_pct = st.slider("单笔模拟风险占本金（%）", 0.25, 50.0, 1.0, 0.25)
with c: leverage = st.slider("假设杠杆（倍）", 1, 100, 3)
if risk_pct > 2.0 or leverage > 20:
    st.error("⚠️ 高风险模拟：单笔亏损预算超过本金2%或杠杆超过20倍，可能导致快速亏损甚至强平。这里仅展示假设情景，不代表交易所一定允许该杠杆。")
fee_pct = st.number_input("假设单边手续费（%）", min_value=0.0, max_value=1.0, value=0.05, step=0.01)
slip_pct = st.number_input("假设单边滑点（%）", min_value=0.0, max_value=1.0, value=0.02, step=0.01)
if st.button("🔄 手动刷新数据"):
    candles.clear()
    multi_timeframe.clear()
    market.clear()
    feed.clear()
    st.rerun()

if research_view == "📊 行情总览":
    try:
        d = indicators(candles(pair,bar))
        if len(d)<60: st.warning("K 线样本较少，指标参考性有限")
        row = d.iloc[-1]
        m = market(pair)
        t, mark, fund, oi, spec = (m[k] for k in ["ticker","mark","funding","oi","spec"])
        last = float(t["last"]) if t.get("last") else None
        ts_ms = int(t.get("ts") or 0)
        age = (datetime.now(timezone.utc).timestamp()*1000-ts_ms)/1000 if ts_ms else None
        direction_text, reason = direction(row)
        x1,x2,x3,x4 = st.columns(4)
        x1.metric("最新成交价 USDT",fmt(last))
        if last is None: st.error("最新成交价暂不可用，不得将历史收盘价当成实时价格。")
        x2.metric("标记价格 USDT",fmt(mark.get("markPx")))
        x3.metric("资金费率",fmt(float(fund["fundingRate"])*100,4)+"%" if fund.get("fundingRate") else "暂无")
        x4.metric("技术方向",direction_text)
        if age is not None:
            st.caption("最新成交数据时间（北京时间）：" + pd.to_datetime(ts_ms,unit="ms",utc=True).tz_convert("Asia/Shanghai").strftime("%Y-%m-%d %H:%M:%S") + f" · 距现在约 {max(0,int(age))} 秒")
            if age>120: st.error("最新成交数据超过120秒，暂停方向性模拟参考。")
        st.caption("最近已收盘 K 线：" + row.ts.strftime("%Y-%m-%d %H:%M") + "（北京时间）。技术指标以已收盘 K 线计算，最新成交价单独显示。")
        st.info(f"技术判断：{direction_text}。依据：{reason}。不构成交易建议。")
        st.subheader("🧠 多周期与24小时综合参考")
        trends = multi_timeframe(pair)
        st.write("｜".join(f"{tf}：{trends[tf]}" for tf in ("4H","1D","1W")))
        valid = list(trends.values())
        bull, bear = valid.count("偏多"), valid.count("偏空")
        if last is None or age is None or age > 120 or any(v in ("样本不足","数据不可用") for v in valid):
            overall = "行情不完整，优先观望"
        elif bull >= 2 and bear == 0:
            overall = "多周期偏多，等待回踩确认"
        elif bear >= 2 and bull == 0:
            overall = "多周期偏空，等待反弹确认"
        else:
            overall = "多周期分歧，优先观望"
        st.markdown(f"**综合技术参考：{overall}**")
        if last is not None and t.get("open24h"):
            open24 = float(t["open24h"])
            if open24 > 0:
                st.write(f"24小时涨跌：{(last/open24-1)*100:+.2f}%｜最高：{fmt(t.get('high24h'))}｜最低：{fmt(t.get('low24h'))} USDT")
        st.caption("多周期方向基于已收盘K线。币圈新闻和美联储公告仅作为事件背景，尚未纳入方向评分；未调用AI大模型，不冒充AI预测。")
        q1,q2,q3,q4=st.columns(4)
        q1.metric("RSI 14",fmt(row.rsi,1))
        q2.metric("ATR 14",fmt(row.atr))
        q3.metric("量比",fmt(row.vol/row.vol_ma if row.vol_ma>0 else None))
        q4.metric("未平仓量（张）",fmt(oi.get("oi"),0))
        st.subheader("📉 K线图与均线")
        show_levels=st.checkbox("显示支撑位 / 压力位",value=True,key="chart_levels")
        show_scenario=st.checkbox("显示未来走势情景与波动带（非预测保证）",value=True,key="chart_scenario")
        fig=go.Figure()
        fig.add_trace(go.Candlestick(x=d.ts,open=d.open,high=d.high,low=d.low,close=d.close,name="K线",
                                    increasing_line_color="#2dd4a4",decreasing_line_color="#f06c81"))
        fig.add_trace(go.Scatter(x=d.ts,y=d.ema20,name="EMA20",line=dict(color="#54b6f8",width=1.6)))
        fig.add_trace(go.Scatter(x=d.ts,y=d.ema50,name="EMA50",line=dict(color="#f5c46a",width=1.6)))
        chart_support=float(d.low.tail(20).min())
        chart_resistance=float(d.high.tail(20).max())
        if show_levels:
            fig.add_hline(y=chart_support,line_dash="dash",line_color="#36d5a0",
                          annotation_text=f"支撑 {chart_support:,.2f}",annotation_position="bottom right")
            fig.add_hline(y=chart_resistance,line_dash="dash",line_color="#fb7185",
                          annotation_text=f"压力 {chart_resistance:,.2f}",annotation_position="top right")
        if show_scenario and last is not None and age is not None and age<=120 and len(d)>=30:
            try:
                interval_map={"15m":15,"1H":60,"4H":240,"1D":1440,"1W":10080}
                minutes=interval_map.get(bar,60)
                # Chart scenario only: extrapolate current EMA slope with a capped drift.
                # ATR controls uncertainty width; this does not modify the frozen models.
                chart_atr=float(row.atr)
                chart_close=float(row.close)
                chart_slope=(float(d.ema20.iloc[-1])-float(d.ema20.iloc[-6]))/5
                chart_slope=float(np.clip(chart_slope,-chart_atr*0.35,chart_atr*0.35))
                if np.isfinite(chart_atr) and chart_atr>0 and np.isfinite(chart_slope):
                    start_time=pd.Timestamp(d.ts.iloc[-1])
                    future_dates=[start_time+pd.Timedelta(minutes=minutes*k) for k in range(0,7)]
                    centers=[last+chart_slope*k for k in range(7)]
                    widths=[chart_atr*np.sqrt(k)*1.2 for k in range(7)]
                    upper=[v+w for v,w in zip(centers,widths)]
                    lower=[max(0,v-w) for v,w in zip(centers,widths)]
                    fig.add_trace(go.Scatter(x=future_dates,y=upper,mode="lines",
                                             line=dict(width=0),showlegend=False,hoverinfo="skip"))
                    fig.add_trace(go.Scatter(x=future_dates,y=lower,mode="lines",fill="tonexty",
                                             fillcolor="rgba(64,160,241,.13)",line=dict(width=0),
                                             name="情景波动带（非置信区间）"))
                    fig.add_trace(go.Scatter(x=future_dates,y=centers,mode="lines+markers",
                                             line=dict(color="#72c6ff",dash="dot",width=2.5),
                                             marker=dict(size=4),name="EMA斜率情景（非方向预测）"))
            except (ValueError,TypeError,OverflowError):
                st.caption("未来情景暂不可用，历史K线仍可正常查看。")
        fig.update_layout(height=510,xaxis_rangeslider_visible=False,
                          margin=dict(l=8,r=12,t=20,b=12),paper_bgcolor="#0b1424",
                          plot_bgcolor="#0b1424",font=dict(color="#d2e4f5"),
                          xaxis=dict(showgrid=True,gridcolor="rgba(135,169,206,.09)"),
                          yaxis=dict(showgrid=True,gridcolor="rgba(135,169,206,.11)"),
                          legend=dict(orientation="h",y=1.12,x=0))
        st.plotly_chart(fig,use_container_width=True)
        st.caption("支撑/压力取最近20根已收盘K线的高低点；右侧虚线按EMA20近期斜率作情景外推，阴影宽度按ATR扩展，不是冻结预测模型输出，也不具有统计覆盖率保证。")
        st.subheader("🎯 分时段参考区间（1小时 / 4小时 / 1天）")
        st.caption("结合一年日线历史波动、24小时波动、资金费率和多周期趋势；新闻/宏观仅标注事件风险，未接入AI新闻语义模型。")
        if last is None or age is None or age > 120:
            st.error("实时成交价缺失或过期，暂停计算分时段参考区间。")
        else:
            try:
                annual = indicators(candles(pair,"1D"))
                daily_returns = np.log(annual.close / annual.close.shift(1)).dropna()
                if len(daily_returns)<180: raise ValueError("日线样本不足180天")
                annual_sigma = float(daily_returns.tail(240).std())
                if not np.isfinite(annual_sigma) or annual_sigma<=0: raise ValueError("年度历史波动数据无效")
                change24 = abs(last/float(t.get("open24h") or last)-1)
                funding_rate = abs(float(fund.get("fundingRate") or 0))
                for label, tf, hours in (("未来1小时","1H",1),("未来4小时","4H",4),("未来1天","1D",24)):
                    try:
                        hd=indicators(candles(pair,tf))
                        if len(hd)<30: raise ValueError("K线样本不足")
                        atr=float(hd.iloc[-1].atr)
                        annual_band=last*annual_sigma*np.sqrt(hours/24)
                        intraday_band=last*change24*np.sqrt(hours/24)
                        width=max(atr,annual_band,0.5*intraday_band)
                        if funding_rate>0.001: width*=1.10
                        support=float(hd.low.tail(20).min())
                        resistance=float(hd.high.tail(20).max())
                        st.markdown(f"**{label}**｜历史波动参考 **{max(0,last-width):,.2f} ～ {last+width:,.2f} USDT**")
                        st.caption(f"参考波幅 ±{width/last*100:.2f}%｜{tf}近期支撑 {support:,.2f}｜阻力 {resistance:,.2f} USDT")
                    except Exception as exc:
                        st.warning(f"{label} 暂不可用：{exc}")
                st.caption(f"日线历史样本 {len(daily_returns)} 天；长期波动率取最近最多240个日收益；24小时变化参与波幅估计。该范围没有统计覆盖率保证。")
            except Exception as exc:
                st.warning(f"长期历史波动分析不可用：{exc}")
        st.info("事件风险：币圈新闻、美联储公告、CPI及非农可能使波动超出区间。目前未验证新闻发布时间及情绪，暂不将标题机械转换成涨跌或波动倍数。")
        st.divider()
        st.subheader("🧮 模拟入场与仓位风险")
        st.caption("仅按已收盘 K 线生成方向和 ATR 参考位；入场以最近收盘价为观察参考，不等于当前可成交价格。")
        if direction_text == "观望" or last is None or age is None or age>120:
            if last is None:
                st.warning("建议观望：实时成交价不可用。")
            elif age is None or age > 120:
                st.warning("建议观望：行情数据过期，请刷新。")
            else:
                st.warning("建议观望：技术指标未共振，暂不生成模拟仓位。")
        else:
            sign = 1 if direction_text=="偏多" else -1
            entry = float(row.close)
            atr = float(row.atr)
            stop = entry-sign*1.5*atr
            take1 = entry+sign*1.5*atr
            take2 = entry+sign*3*atr
            ctval = float(spec.get("ctVal") or 0)
            ct_type = spec.get("ctType","")
            lot = float(spec.get("lotSz") or 1)
            min_sz = float(spec.get("minSz") or lot)
            budget = capital*risk_pct/100
            per_unit_loss = abs(entry-stop) + entry*2*(fee_pct+slip_pct)/100
            base_qty = budget/per_unit_loss if per_unit_loss>0 else 0
            if ct_type=="linear" and ctval>0 and lot>0:
                raw_contracts = base_qty/ctval
                contracts = np.floor((raw_contracts+1e-9)/lot)*lot
                if contracts<min_sz: contracts=0
                notional = contracts*ctval*entry
                margin = notional/leverage
                st.write(f"模拟方向：**{direction_text}** · 观察入场 **{entry:,.2f}** · 止损 **{stop:,.2f}** · 止盈一 **{take1:,.2f}** · 止盈二 **{take2:,.2f}** USDT")
                st.write(f"每张合约面值 **{ctval:g} {pair.split('-')[0]}**；按 OKX 最小张数步长取整，模拟仓位 **{contracts:g} 张**；名义价值约 **{notional:,.2f} USDT**；{leverage} 倍杠杆初始保证金估算 **{margin:,.2f} USDT**。")
                approx_loss = contracts*ctval*per_unit_loss
                st.write(f"单笔风险预算 **{budget:.2f} USDT**；计入假设双边手续费及滑点的止损估算损失约 **{approx_loss:.2f} USDT**（不含资金费率、极端滑点和强平）。")
                if margin>capital: st.error("所需保证金超过模拟本金，请降低仓位或调整风险参数。")
                if contracts==0: st.warning("按当前风险预算不足以开出最小合约张数，建议不交易。")
            else:
                st.warning("无法确认合约面值/线性合约属性，已停止仓位换算，避免给出错误张数。")
        warnings=[]
        candle_move=(float(row.close)/float(d.iloc[-2].close)-1)*100
        if abs(candle_move)>=2: warnings.append("单根已收盘 K 线涨跌超过 2%")
        if row.vol_ma>0 and row.vol/row.vol_ma>=2: warnings.append("成交量超过 20 根均量的两倍")
        if row.rsi>=70: warnings.append("RSI 超买")
        if row.rsi<=30: warnings.append("RSI 超卖")
        st.warning("波动提醒：" + ("；".join(warnings) if warnings else "未触发预设阈值，不代表没有风险"))
        st.caption("风险提示：合约杠杆可能导致强平；资金费率动态变化；手续费、滑点和保证金估算均非交易所结算值。")
    except Exception as e:
        st.error(f"行情接口暂不可用：{e}")
        st.info("可稍后刷新；某些网络或云服务器可能暂时无法访问 OKX 公共接口。")

elif research_view == "📰 市场新闻":
    st.markdown("### 📰 市场新闻")
    st.caption("CoinDesk RSS；新闻可能延迟，不自动作为交易信号。")
    try:
        entries=feed("https://www.coindesk.com/arc/outboundfeeds/rss/")
        for item in entries: st.markdown(f"**[{item.get('title','新闻')}]({item.get('link','#')})**  \n{item.get('published','')}")
        if not entries: st.info("暂时没有可显示的新闻")
    except Exception as e: st.warning(f"新闻暂不可用：{e}")

elif research_view == "🏦 宏观日历":
    st.markdown("### 🏦 宏观日历")
    st.caption("美联储官方货币政策公告；CPI、非农结果以美国劳工统计局为准。")
    try:
        entries=feed("https://www.federalreserve.gov/feeds/press_monetary.xml")
        for item in entries: st.markdown(f"**[{item.get('title','公告')}]({item.get('link','#')})**  \n{item.get('published','')}")
        if not entries: st.info("暂无公告")
    except Exception as e: st.warning(f"美联储公告暂不可用：{e}")
    st.markdown("[FOMC 官方日程](https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm) · [CPI 官方日程与数据](https://www.bls.gov/cpi/) · [非农就业报告](https://www.bls.gov/news.release/empsit.toc.htm)")
    st.info("目前仍使用官方公告和日程链接，尚未自动抓取 CPI、非农的预期值与实际值；避免把未经核实的数据当成实时消息。")

elif research_view == "🔬 高级研究":
    st.markdown("### 🔬 高级研究中心")
    st.caption("历史回测 · 模型对照 · 前瞻验证｜研究工具，不代表未来收益。")
    st.markdown("#### 历史样本与回测")
    try:
        st.subheader("🗞️ 新闻与宏观事件观察")
        st.caption("事件信息独立于技术信号；尚未将新闻情绪或CPI/非农预期差转换成方向分数。")
        for label, url in (("美联储", "https://www.federalreserve.gov/feeds/press_monetary.xml"), ("币圈", "https://www.coindesk.com/arc/outboundfeeds/rss/")):
            try:
                entries = feed(url)
                if not entries:
                    st.warning(f"{label}事件源暂无可用条目。")
                for item in entries[:3]:
                    title = item.get("title", "事件公告")
                    link = item.get("link", "")
                    published = item.get("published", "发布时间未知")
                    st.write(f"{label}｜{published}｜{title}")
                    if link: st.markdown(f"[查看原文]({link})")
            except Exception:
                st.warning(f"{label}事件源读取失败，不能据此判断没有风险。")
        st.caption("官方数据核对：CPI https://www.bls.gov/cpi/ ｜ 非农 https://www.bls.gov/news.release/empsit.toc.htm ｜ FOMC https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm")
        st.info("事件对历史K线的量化归因与回测尚未完成；新闻公告目前不会改变价格区间或开仓参考。")
        st.subheader("🗃️ 历史宏观事件样本库（建设中）")
        st.caption("按事件类型、官方发布时间、数据来源及K线覆盖范围分开核验。尚未建立完整一年的CPI、非农、FOMC历史事件库。")
        coverage = []
        for label, tf in (("小时行情","1H"),("日线行情","1D")):
            try:
                hist = candles(pair,tf)
                coverage.append({"数据":label,"已收盘K线":len(hist),"起始时间":str(hist.ts.iloc[0]),"结束时间":str(hist.ts.iloc[-1])})
            except Exception:
                coverage.append({"数据":label,"已收盘K线":0,"起始时间":"不可用","结束时间":"不可用"})
        st.dataframe(pd.DataFrame(coverage),use_container_width=True,hide_index=True)
        if st.button("🔎 拉取一年小时K线并检查完整性", key="historical_check"):
            try:
                with st.spinner("正在分页获取历史小时线，可能需要一些时间……"):
                    history = historical_hourly(pair)
                gaps = history.ts.diff().dropna().dt.total_seconds().div(3600)
                missing = int((gaps[gaps > 1.01].round().astype(int)-1).clip(lower=0).sum())
                duplicates = int(history.ts.duplicated().sum())
                st.write(f"交易对：{pair}｜已收盘小时K线：{len(history)} 条｜时间范围：{history.ts.iloc[0]} 至 {history.ts.iloc[-1]}")
                st.write(f"缺失小时数（按时间戳间隔估算）：{missing}｜重复时间戳：{duplicates}｜目标：8760条")
                if len(history) < 8760 or missing:
                    st.warning("历史覆盖未达到完整一年或存在缺口，暂不能据此进行全年宏观事件小时级回测。")
                else:
                    st.success("已取得约一年连续小时K线，可进入事件时间匹配阶段；尚未验证宏观事件数据。")
            except Exception as exc:
                st.warning(f"历史数据扩充未完成：{exc}。原有行情分析不受影响。")
        st.info("待接入：CPI公布时间、非农公布时间、FOMC决议时间及各自历史实际值。没有经过官方核对的事件，不计入宏观事件回测。")
        st.caption("历史事件数据需与BTC/ETH价格历史重叠，才能计算事件后1小时、4小时和24小时波动；暂不据此调整参考区间。")
        st.subheader("🗓️ 官方宏观事件与历史小时K线匹配（首批）")
        st.caption("以下为待逐条复核的2026年美国宏观事件日程；公布时间按纽约时区处理。回报采用公布前最后一根已收盘小时线与目标时间之后首根已收盘小时线，实际测量窗口最多偏离约一小时。")
        if st.button("📊 匹配2026年CPI、非农与FOMC事件",key="match_official_macro"):
            try:
                history = historical_hourly(pair)
                close_times = pd.to_datetime(history.ts,utc=True) + pd.Timedelta(hours=1)
                prices = history.close.astype(float).to_numpy()
                dates = {
                    "CPI":["2026-01-13","2026-02-13","2026-03-11","2026-04-10","2026-05-12","2026-06-10","2026-07-14","2026-08-12","2026-09-11","2026-10-14"],
                    "非农":["2026-01-09","2026-02-11","2026-03-06","2026-04-03","2026-05-08","2026-06-05","2026-07-02","2026-08-07","2026-09-04","2026-10-02"],
                    "FOMC":["2026-01-28","2026-03-18","2026-04-29","2026-06-17","2026-07-29","2026-09-16"]}
                results=[]
                for kind,days in dates.items():
                    for day in days:
                        clock="14:00" if kind=="FOMC" else "08:30"
                        published=pd.Timestamp(day+" "+clock,tz="America/New_York").tz_convert("UTC")
                        before=int(close_times.searchsorted(published,side="right"))-1
                        if before<0: continue
                        record={"事件":kind,"官方日期":day,"发布时间(北京)":str(published.tz_convert("Asia/Shanghai")),"基准价":round(float(prices[before]),4)}
                        for hours in (1,4,24):
                            after=int(close_times.searchsorted(published+pd.Timedelta(hours=hours),side="left"))
                            record[f"{hours}小时%"]=round((float(prices[after])/float(prices[before])-1)*100,3) if after<len(prices) else None
                        if any(record[f"{hours}小时%"] is not None for hours in (1,4,24)): results.append(record)
                if results:
                    result_df = pd.DataFrame(results)
                    st.dataframe(result_df,use_container_width=True,hide_index=True)
                    st.subheader("📊 宏观事件分类波动统计（探索性）")
                    summary=[]
                    for category, group in result_df.groupby("事件"):
                        for hours in (1,4,24):
                            vals=pd.to_numeric(group[f"{hours}小时%"],errors="coerce").dropna()
                            summary.append({"事件类型":category,"观察窗口":f"{hours}小时","有效样本":len(vals),"平均涨跌%":round(float(vals.mean()),3) if len(vals) else None,"绝对波动中位数%":round(float(vals.abs().median()),3) if len(vals) else None,"绝对波动75分位%":round(float(vals.abs().quantile(0.75)),3) if len(vals) else None})
                    st.dataframe(pd.DataFrame(summary),use_container_width=True,hide_index=True)
                    st.warning("各类事件样本偏少；日期与实际公布时刻仍需逐条复核。当前统计不用于调整交易信号、价格区间或仓位。")
                    st.caption(f"匹配到 {len(results)} 条候选宏观事件；仅计算事件窗口价格变化，不代表事件造成变化，也不代表方向预测。")
                else: st.info("当前历史K线范围与候选事件无可计算的交集。")
            except Exception as exc: st.warning(f"官方事件历史匹配失败：{exc}")
        st.caption("核对入口：美国劳工统计局 CPI、就业报告发布日程及美联储 FOMC 日历。当前日期列表尚未逐条完成来源核验，尤其非农可能出现改期；不包含预期差和政策结果。")
        st.subheader("🧪 样本外历史区间回测（独立于宏观事件）")
        st.caption("使用一年小时线的前70%训练、后30%测试；每个预测点只使用此前已收盘数据，计算历史75分位绝对涨跌幅形成对称区间。此测试不是当前ATR综合区间的准确率。")
        if st.button("▶️ 运行样本外区间回测",key="run_oos_backtest"):
            try:
                history = historical_hourly(pair)
                prices = history.close.astype(float).reset_index(drop=True)
                cutoff = int(len(prices)*0.7)
                records=[]
                for horizon in (1,4,24):
                    hits=[]
                    widths=[]
                    for idx in range(max(cutoff,720+horizon),len(prices)-horizon):
                        past = (prices.shift(-horizon)/prices-1).abs().iloc[idx-720-horizon:idx-horizon].dropna()
                        if len(past)<600: continue
                        width = float(past.quantile(0.75))
                        realized = abs(float(prices.iloc[idx+horizon]/prices.iloc[idx]-1))
                        hits.append(realized<=width)
                        widths.append(width*100)
                    if hits:
                        records.append({"周期":f"{horizon}小时","测试预测点":len(hits),"区间命中率%":round(np.mean(hits)*100,2),"平均半宽%":round(np.mean(widths),2),"训练结束":str(history.ts.iloc[cutoff])})
                if records:
                    st.dataframe(pd.DataFrame(records),use_container_width=True,hide_index=True)
                    st.caption("测试点的未来窗口互相重叠，命中率不是独立事件概率；75%是训练数据的历史分位数，并非保证达到的准确率。")
                else: st.warning("可用历史不足，无法完成样本外回测。")
            except Exception as exc: st.warning(f"样本外回测暂不可用：{exc}")
        st.subheader("⚖️ 历史分位区间 vs ATR代理区间：同点对照")
        st.caption("在相同的测试预测点比较历史75分位区间和ATR代理区间。ATR代理只使用历史小时K线与过去24小时变化；不是线上综合区间的完整复刻（未包含资金费率、日线波动等）。")
        if st.button("▶️ 运行两模型同点对照",key="compare_interval_models"):
            try:
                h = historical_hourly(pair)
                p = h.close.astype(float).reset_index(drop=True)
                highs = pd.to_numeric(h.high,errors="coerce").reset_index(drop=True)
                lows = pd.to_numeric(h.low,errors="coerce").reset_index(drop=True)
                tr = pd.concat([(highs-lows),(highs-p.shift()).abs(),(lows-p.shift()).abs()],axis=1).max(axis=1)
                atr = tr.ewm(alpha=1/14,adjust=False).mean()
                cutoff = int(len(p)*0.7)
                rows=[]
                for horizon in (1,4,24):
                    hits_hist=[];hits_atr=[];width_hist=[];width_atr=[]
                    forward = (p.shift(-horizon)/p-1).abs()
                    for idx in range(max(cutoff,744+horizon),len(p)-horizon):
                        past = forward.iloc[idx-720-horizon:idx-horizon].dropna()
                        if len(past)<600 or p.iloc[idx]<=0: continue
                        historical_width = float(past.quantile(0.75))
                        atr_width = max(float(atr.iloc[idx])/float(p.iloc[idx]),0.5*abs(float(p.iloc[idx]/p.iloc[idx-24]-1))*np.sqrt(horizon/24))
                        actual=float(forward.iloc[idx])
                        if not np.isfinite(atr_width) or not np.isfinite(actual):continue
                        hits_hist.append(actual<=historical_width);hits_atr.append(actual<=atr_width)
                        width_hist.append(historical_width*100);width_atr.append(atr_width*100)
                    if hits_hist:
                        for model,hits,widths in (("历史75分位",hits_hist,width_hist),("ATR代理",hits_atr,width_atr)):
                            rows.append({"周期":f"{horizon}小时","模型":model,"同组测试点":len(hits),"命中率%":round(float(np.mean(hits)*100),2),"平均半宽%":round(float(np.mean(widths)),3)})
                if rows: st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
                else: st.info("数据不足，无法进行同点对照。")
                st.caption("未来窗口互相重叠，结果不能作为独立胜率；两模型均未计入手续费、交易方向及新闻影响。")
            except Exception as exc: st.warning(f"同点对照暂不可用：{exc}")
        st.subheader("📊 1小时 / 4小时：上涨、下跌、震荡分类回测")
        st.caption("行情分类仅用预测点之前24小时的已收盘价格：涨幅超过1%为上涨，跌幅超过1%为下跌，其余为震荡；阈值是研究假设，并非最佳参数。")
        if st.button("▶️ 运行分类样本外回测",key="run_regime_oos"):
            try:
                rh=historical_hourly(pair)
                rp=rh.close.astype(float).reset_index(drop=True)
                split=int(len(rp)*0.7)
                results=[]
                for hh in (1,4):
                    realized=(rp.shift(-hh)/rp-1).abs()
                    widths=realized.shift(hh).rolling(720,min_periods=600).quantile(0.75)
                    prior24=rp/rp.shift(24)-1
                    regimes=np.where(prior24>0.01,"上涨",np.where(prior24< -0.01,"下跌","震荡"))
                    test=pd.DataFrame({"width":widths,"actual":realized,"regime":regimes}).iloc[split:len(rp)-hh].dropna()
                    for rg in ("上涨","下跌","震荡"):
                        sub=test[test.regime==rg]
                        if len(sub)==0:continue
                        results.append({"周期":f"{hh}小时","行情":rg,"预测点":len(sub),"区间命中率%":round(float((sub.actual<=sub.width).mean()*100),2),"平均半宽%":round(float(sub.width.mean()*100),3)})
                if results:st.dataframe(pd.DataFrame(results),use_container_width=True,hide_index=True)
                else:st.warning("可用样本不足。")
                st.caption("每个预测点只使用当时已知历史数据计算区间；未来1小时/4小时结果用于事后核验。预测窗口存在重叠，分类命中率不是独立交易胜率。")
            except Exception as exc:st.warning(f"分类回测暂不可用：{exc}")
        st.caption("官方时间核对入口：BLS发布日程 https://www.bls.gov/schedule/news_release/ ｜ FOMC https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm 。候选事件发布时间尚未逐条验证，不参与本项回测。")
        st.subheader("🧪 实验版B：条件分位区间样本外对照")
        st.caption("修正旧版B上下沿各取75分位导致区间过窄的问题：新B使用收益分布12.5%和87.5%分位；上涨趋势优先采用历史同类趋势样本，不足时回退整体样本。")
        if st.button("▶️ 运行动态区间样本外回测", key="run_asymmetric_oos"):
            try:
                hist = historical_hourly(pair)
                close = hist.close.astype(float).reset_index(drop=True)
                split = int(len(close)*0.7)
                out = []
                trend = close / close.shift(24) - 1 > 0.01
                for horizon in (1,4):
                    future = close.shift(-horizon)/close-1
                    known = future.shift(horizon)
                    prior_regime = trend.shift(horizon).fillna(False).astype(bool)
                    conditional = known.where(prior_regime)
                    lower_all = known.rolling(720,min_periods=600).quantile(.125)
                    upper_all = known.rolling(720,min_periods=600).quantile(.875)
                    lower_cond = conditional.rolling(720,min_periods=120).quantile(.125)
                    upper_cond = conditional.rolling(720,min_periods=120).quantile(.875)
                    lower = lower_cond.where(trend,lower_all).fillna(lower_all)
                    upper = upper_cond.where(trend,upper_all).fillna(upper_all)
                    symmetric = known.abs().rolling(720,min_periods=600).quantile(.75)
                    frame = pd.DataFrame({"actual":future,"lo":lower,"hi":upper,"sym":symmetric,"trend":trend}).iloc[split:len(close)-horizon].dropna()
                    for name,sub in (("全部",frame),("上涨趋势",frame[frame.trend])):
                        if sub.empty: continue
                        baseline = sub.actual.abs() <= sub.sym
                        dynamic = (sub.actual >= sub.lo) & (sub.actual <= sub.hi)
                        out.extend([
                            {"周期":f"{horizon}小时","行情":name,"模型":"原实验版：对称75分位","预测点":len(sub),"覆盖率%":round(baseline.mean()*100,2),"平均总宽%":round((2*sub.sym).mean()*100,3)},
                            {"周期":f"{horizon}小时","行情":name,"模型":"实验版B：条件12.5/87.5分位","预测点":len(sub),"覆盖率%":round(dynamic.mean()*100,2),"平均总宽%":round((sub.hi-sub.lo).mean()*100,3)}
                        ])
                if out: st.dataframe(pd.DataFrame(out),use_container_width=True,hide_index=True)
                else: st.warning("可用测试样本不足")
                st.caption("仅报告区间覆盖率，不是方向准确率或交易胜率；重叠预测窗口相关，须独立检验后才能决定是否采用。")
            except Exception as exc:
                st.warning(f"动态区间回测暂不可用：{exc}")
        st.subheader("⚖️ 同宽度覆盖率对照：上涨趋势")
        st.caption("对每个预测点，将实验版B的非对称上下沿等比例缩放至原实验版的总宽度；这样两者宽度完全一致，仅比较中心偏移是否改善覆盖。训练分位仅使用预测时已知数据。")
        if st.button("▶️ 运行同宽度覆盖率测试",key="run_equal_width_oos"):
            try:
                hist = historical_hourly(pair)
                close = hist.close.astype(float).reset_index(drop=True)
                split = int(len(close)*.7)
                trend = (close/close.shift(24)-1)>0.01
                equal_rows=[]
                for hh in (1,4):
                    future=close.shift(-hh)/close-1
                    known=future.shift(hh)
                    regime_past=trend.shift(hh).fillna(False).astype(bool)
                    selected=known.where(regime_past)
                    lo_all=known.rolling(720,min_periods=600).quantile(.125)
                    hi_all=known.rolling(720,min_periods=600).quantile(.875)
                    lo_cond=selected.rolling(720,min_periods=120).quantile(.125)
                    hi_cond=selected.rolling(720,min_periods=120).quantile(.875)
                    lo=lo_cond.where(trend,lo_all).fillna(lo_all)
                    hi=hi_cond.where(trend,hi_all).fillna(hi_all)
                    width=known.abs().rolling(720,min_periods=600).quantile(.75)
                    frame=pd.DataFrame({"actual":future,"lo":lo,"hi":hi,"half":width,"trend":trend}).iloc[split:len(close)-hh].dropna()
                    frame=frame[frame.trend & ((frame.hi-frame.lo)>0) & (frame.half>0)]
                    if frame.empty:continue
                    # Match each prediction's full width to the symmetric baseline, preserving B's center.
                    center=(frame.hi+frame.lo)/2
                    low_equal=center-frame.half
                    high_equal=center+frame.half
                    base_hit=frame.actual.abs()<=frame.half
                    new_hit=(frame.actual>=low_equal)&(frame.actual<=high_equal)
                    equal_rows.extend([
                        {"周期":f"{hh}小时","模型":"原实验版：对称区间","上涨样本":len(frame),"覆盖率%":round(base_hit.mean()*100,2),"平均总宽%":round((2*frame.half).mean()*100,3)},
                        {"周期":f"{hh}小时","模型":"实验版B：同宽度平移区间","上涨样本":len(frame),"覆盖率%":round(new_hit.mean()*100,2),"平均总宽%":round((2*frame.half).mean()*100,3)}
                    ])
                if equal_rows:
                    st.dataframe(pd.DataFrame(equal_rows),use_container_width=True,hide_index=True)
                    st.caption("同宽度意味着只检验非对称模型的区间中心是否更合理；不代表未来盈利能力。预测窗口重叠，结果仍需独立时段验证。")
                else:st.warning("上涨趋势有效测试样本不足。")
            except Exception as exc:
                st.warning(f"同宽度测试暂不可用：{exc}")
        st.subheader("🧭 前瞻验证：冻结模型，等待新行情")
        st.caption("此前历史数据已经被反复查看和调参，不能再称为全新独立测试。此处冻结当前两套算法，只评价2026-10-22 00:00（北京时间）之后新出现的完整小时K线。不会修改交易参考。")
        st.caption("进度目标：先积累100个上涨趋势预测点作初步观察，300个作阶段性复核；这是观察门槛，不是统计显著性或独立样本保证。")
        try:
            progress_hist = candles(pair, "1H")
            progress_close = progress_hist.close.astype(float).reset_index(drop=True)
            progress_time = progress_hist.ts.reset_index(drop=True)
            progress_cutoff = pd.Timestamp("2026-10-22 00:00:00", tz="Asia/Shanghai")
            progress_trend = (progress_close / progress_close.shift(24) - 1) > 0.01
            for progress_h in (1, 4):
                # Count only forecast origins with completed outcomes and known 24h trend.
                valid_indices = range(24, max(24, len(progress_close) - progress_h))
                count = sum(bool(progress_time.iloc[i] >= progress_cutoff and progress_trend.iloc[i]) for i in valid_indices)
                st.write(f"**{progress_h}小时上涨趋势：{count} / 100 个初步观察点**")
                st.progress(min(count / 100, 1.0))
                st.caption(f"距100点还差 {max(0,100-count)} 个；距300点还差 {max(0,300-count)} 个。1小时和4小时的预测窗口会重叠，不能把这些点当作独立交易。")
            st.caption("上方为轻量进度估算，基于最近已收盘小时K线；点击下方按钮可用更长历史数据核对覆盖率。缓存可能造成短暂延迟。")
        except Exception as progress_exc:
            st.warning(f"进度暂不可用：{progress_exc}")
        if st.button("▶️ 检查前瞻验证进度",key="prospective_holdout"):
            try:
                fresh=historical_hourly(pair)
                prices=fresh.close.astype(float).reset_index(drop=True)
                times=fresh.ts.reset_index(drop=True)
                cutoff=pd.Timestamp("2026-10-22 00:00:00",tz="Asia/Shanghai")
                trend=(prices/prices.shift(24)-1)>0.01
                records=[]
                for hh in (1,4):
                    realized=prices.shift(-hh)/prices-1
                    known=realized.shift(hh)
                    cond=known.where(trend.shift(hh).fillna(False).astype(bool))
                    half=known.abs().rolling(720,min_periods=600).quantile(.75)
                    low_all=known.rolling(720,min_periods=600).quantile(.125)
                    high_all=known.rolling(720,min_periods=600).quantile(.875)
                    low_cond=cond.rolling(720,min_periods=120).quantile(.125)
                    high_cond=cond.rolling(720,min_periods=120).quantile(.875)
                    low=low_cond.where(trend,low_all).fillna(low_all)
                    high=high_cond.where(trend,high_all).fillna(high_all)
                    frame=pd.DataFrame({"time":times,"realized":realized,"half":half,"low":low,"high":high,"trend":trend})
                    frame=frame[(frame.time>=cutoff)&frame.trend].dropna()
                    if frame.empty:
                        records.append({"周期":f"{hh}小时","新上涨样本":0,"原版覆盖率%":"待积累","B同宽覆盖率%":"待积累","同宽总宽%":"待积累"})
                        continue
                    center=(frame.low+frame.high)/2
                    hit_original=(frame.realized.abs()<=frame.half).mean()*100
                    hit_b=((frame.realized>=center-frame.half)&(frame.realized<=center+frame.half)).mean()*100
                    records.append({"周期":f"{hh}小时","新上涨样本":len(frame),"原版覆盖率%":round(hit_original,2),"B同宽覆盖率%":round(hit_b,2),"同宽总宽%":round((2*frame.half).mean()*100,3)})
                st.dataframe(pd.DataFrame(records),use_container_width=True,hide_index=True)
                st.caption("仅统计截止时间之后且未来结果已完成的预测点；新样本不足时不作胜负结论。重叠窗口非独立交易，当前算法与阈值必须保持冻结，才能保留前瞻验证意义。")
            except Exception as exc:
                st.warning(f"前瞻验证暂不可用：{exc}")
        st.subheader("📉 事件发布后的历史K线反应")
        st.caption("按新闻源标注的发布时间匹配OKX已收盘1小时K线；仅描述价格变化，不能证明事件导致涨跌。")
        try:
            event_candles = candles(pair, "1H")
            event_times = pd.to_datetime(event_candles.ts, utc=True)
            event_closes = event_candles.close.astype(float).to_numpy()
            event_rows = []
            for source_name, source_url in (("美联储公告", "https://www.federalreserve.gov/feeds/press_monetary.xml"), ("币圈新闻", "https://www.coindesk.com/arc/outboundfeeds/rss/")):
                try:
                    items = feed(source_url)
                except Exception:
                    continue
                for item in items[:8]:
                    stamp = pd.to_datetime(item.get("published", ""), utc=True, errors="coerce")
                    if pd.isna(stamp): continue
                    start_idx = int(event_times.searchsorted(stamp, side="right"))
                    if start_idx < 1 or start_idx + 24 >= len(event_closes): continue
                    if abs((event_times.iloc[start_idx] - stamp).total_seconds()) > 7200: continue
                    baseline = event_closes[start_idx-1]
                    if baseline <= 0: continue
                    changes = [(event_closes[start_idx+h-1] / baseline - 1) * 100 for h in (1,4,24)]
                    event_rows.append({"事件源":source_name, "发布时间(北京时间)":stamp.tz_convert("Asia/Shanghai").strftime("%m-%d %H:%M"), "标题":str(item.get("title",""))[:42], "1小时%":round(changes[0],2), "4小时%":round(changes[1],2), "24小时%":round(changes[2],2)})
            if event_rows:
                st.dataframe(pd.DataFrame(event_rows).head(12), use_container_width=True, hide_index=True)
                st.caption("起点为事件发布时间之前最近一根已收盘1小时K线的收盘价；新闻发布不一定等于经济数据实际公布时刻。")
            else:
                st.info("当前新闻源与可用K线时间没有足够重合，暂不展示事件回报，避免伪造历史结果。")
        except Exception as exc:
            st.warning(f"事件历史反应暂不可用：{exc}")
        st.subheader("📏 历史普通波动基准")
        try:
            prices = event_candles.close.astype(float)
            for name, periods in (("1小时",1),("4小时",4),("24小时",24)):
                moves = (prices / prices.shift(periods) - 1).abs().dropna() * 100
                if len(moves) >= 200:
                    st.write(f"{name}：普通历史窗口 {len(moves)} 个，绝对波动中位数 {moves.median():.2f}%，75分位 {moves.quantile(0.75):.2f}%")
                else:
                    st.info(f"{name}普通历史窗口不足200个，暂不展示基准。")
        except Exception as exc:
            st.info(f"历史波动基准暂不可用：{exc}")
        st.caption("普通历史窗口可能包含新闻事件，且窗口互相重叠；本项只供与上方事件样本观察对比，不是独立回测或预测概率。")
        if event_rows:
            st.subheader("🧪 事件样本波动统计（探索性）")
            event_stats = pd.DataFrame(event_rows)
            for horizon in ("1小时%", "4小时%", "24小时%"):
                samples = pd.to_numeric(event_stats[horizon], errors="coerce").dropna().abs()
                if len(samples) >= 5:
                    st.write(f"{horizon}｜样本 {len(samples)} 条｜绝对涨跌中位数 {samples.median():.2f}%｜75分位 {samples.quantile(0.75):.2f}%")
                else:
                    st.write(f"{horizon}｜有效样本仅 {len(samples)} 条，不足以校准波动区间。")
            st.caption("新闻样本并非随机抽样，可能有重复报道和选择偏差；仅做探索性统计，暂不据此放大交易区间或输出方向概率。")
        st.caption("CPI、非农的历史实际公布时间及市场预期差尚未结构化接入，因此不参与本次事件统计，也不自动改变交易方向。")
    except Exception as research_exc:
        st.warning(f"高级研究暂不可用：{research_exc}")
    st.divider()
    st.markdown("#### 实验预测模型")
    try:
        research_ticker=market(pair)["ticker"]
        last=float(research_ticker["last"]) if research_ticker.get("last") else None
        research_ts=int(research_ticker.get("ts") or 0)
        age=(datetime.now(timezone.utc).timestamp()*1000-research_ts)/1000 if research_ts else None
        st.subheader("🧪 实验版综合预测（1小时 / 4小时）")
        st.caption("与上方原版预测并列展示，不覆盖原有区间或交易参数。实验版目前仅使用历史75分位绝对涨跌幅，不包含新闻、宏观或方向预测；尚不是多模型融合。")
        if last is None or age is None or age > 120:
            st.warning("实时价格缺失或超过120秒，实验版暂停显示。")
        else:
            try:
                exp_hourly = candles(pair,"1H")
                exp_close = exp_hourly.close.astype(float).reset_index(drop=True)
                exp_rows = []
                for exp_hours in (1,4):
                    exp_move = (exp_close.shift(-exp_hours)/exp_close-1).abs()
                    exp_sample = exp_move.iloc[:-exp_hours].tail(720).dropna()
                    if len(exp_sample)<600: raise ValueError(f"{exp_hours}小时历史有效样本不足600")
                    exp_half = float(exp_sample.quantile(0.75))
                    exp_rows.append({"周期":f"{exp_hours}小时","模型":"实验版：历史75分位","下沿 USDT":round(max(0,last*(1-exp_half)),2),"上沿 USDT":round(last*(1+exp_half),2),"半宽%":round(exp_half*100,3),"历史样本":len(exp_sample)})
                st.dataframe(pd.DataFrame(exp_rows),use_container_width=True,hide_index=True)
                st.caption("采用最近720个已完成的历史收益窗口估算宽度，中心为当前实时价格；与此前一年样本外回测的历史测试期不同，历史命中率不可直接视为当前区间的保证。")
            except Exception as exc:
                st.warning(f"实验版区间暂不可用：{exc}")
        st.subheader("🧪 实验版B：条件分位区间（1小时 / 4小时）")
        st.caption("研究用：用已完成历史收益的12.5%和87.5%分位估算上下沿；上涨趋势优先采用同类历史样本，样本不足回退总体。原实验版不变。")
        if last is None or age is None or age > 120:
            st.warning("实时价格不可用或过期，实验版B暂停显示。")
        else:
            try:
                hist = candles(pair,"1H")
                closes = hist.close.astype(float).reset_index(drop=True)
                trend24 = float(closes.iloc[-1]/closes.iloc[-25]-1) if len(closes)>=25 else float("nan")
                trend_label = "上涨趋势" if trend24>0.01 else ("下跌趋势" if trend24< -0.01 else "震荡")
                st.write(f"已收盘小时线过去24小时变化：{trend24*100:+.2f}%｜分类：{trend_label}")
                rows_b=[]
                for hh in (1,4):
                    returns = closes.shift(-hh)/closes-1
                    known = returns.shift(hh)
                    regime = (closes/closes.shift(24)-1>0.01).shift(hh).fillna(False).astype(bool)
                    recent = known.tail(720).dropna()
                    if len(recent)<600: raise ValueError(f"{hh}小时有效历史窗口不足600")
                    selected = known.where(regime).tail(720).dropna() if trend_label=="上涨趋势" else recent
                    if len(selected)<120: selected=recent
                    lo=float(selected.quantile(.125))
                    hi=float(selected.quantile(.875))
                    rows_b.append({"周期":f"{hh}小时","模型":"实验版B：条件分位","下沿 USDT":round(max(0,last*(1+lo)),2),"上沿 USDT":round(last*(1+hi),2),"下行幅度%":round(lo*100,3),"上行幅度%":round(hi*100,3),"有效样本":len(selected)})
                st.dataframe(pd.DataFrame(rows_b),use_container_width=True,hide_index=True)
                st.caption("未验证优于原版；请在高级研究运行同点样本外对照。上下沿并非保证范围，不代表买卖建议。")
            except Exception as exc:
                st.warning(f"实验版B暂不可用：{exc}")
    except Exception as experiment_exc:
        st.warning(f"实验模型暂不可用：{experiment_exc}")

st.divider()
st.caption("稳定增强版 v3 · 免费公开数据 · 无 API 密钥 · 不自动交易 · 无后台推送 · 仅供研究与模拟")

st.divider()
st.subheader("💬 内测用户反馈")
st.caption("欢迎反馈预测区间的实际表现及产品体验。主观评价不等于经过统计验证的命中率。")
with st.form("nexus_member_feedback",clear_on_submit=True):
    feedback_period=st.selectbox("评价的预测周期",["1小时","4小时","24小时","整体体验"])
    feedback_rating=st.radio("你觉得预测区间的表现如何？",["比较准确","一般","偏差较大","暂时无法判断"],horizontal=True)
    feedback_comment=st.text_area("意见与建议",max_chars=1000,placeholder="例如：哪一天、哪个币种、什么周期的预测偏差较大？或者你希望改进什么功能？")
    if st.form_submit_button("提交反馈",type="primary"):
        if len(feedback_comment.strip())<5:
            st.warning("请至少填写5个字的反馈内容。")
        else:
            try:
                feedback_time=datetime.now(timezone.utc).isoformat()
                with auth_connection() as feedback_db:
                    feedback_db.execute("INSERT INTO member_feedback(email,period,rating,comment,created_at) VALUES(?,?,?,?,?)",(
                        st.session_state["member_email"],feedback_period,feedback_rating,feedback_comment.strip(),
                        feedback_time))
                mail_ok,mail_status=send_feedback_email(
                    st.session_state["member_email"],feedback_period,feedback_rating,feedback_comment.strip(),feedback_time)
                if mail_ok:
                    st.success("反馈已记录，并已发送邮件通知。感谢参与内测！")
                elif mail_status=="not_configured":
                    st.success("反馈已记录。邮件通知尚未配置，暂时不会发送。")
                else:
                    st.warning("反馈已记录，但邮件发送失败；请管理员检查邮件配置。")
            except Exception:
                st.error("反馈保存失败，请稍后再试。")
st.caption("反馈暂存于测试数据库，服务器重建时可能丢失；正式开放前需迁移到持久化云数据库。")
