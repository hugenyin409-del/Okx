import requests
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
import feedparser
from datetime import datetime, timezone

st.set_page_config(page_title="OKX BTC ETH 合约研究台 Pro", page_icon="📈", layout="wide")
st.title("📈 OKX BTC / ETH 合约研究台 · 稳定增强版 v3")
st.caption("免费公开数据 · 最新成交与标记价格 · 多周期技术分析 · 合约风险模拟 · 新闻与宏观 · 不自动下单")

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
    for _ in range(8 if bar == "1W" else 3):
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
    return df.dropna(subset=["close"]).drop_duplicates("ts").sort_values("ts").tail(800 if bar == "1W" else 240).reset_index(drop=True)

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

tab1,tab2,tab3 = st.tabs(["📊 行情与参考位","📰 币圈新闻","🏦 美联储与宏观"])
with tab1:
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
        fig=go.Figure()
        fig.add_trace(go.Candlestick(x=d.ts,open=d.open,high=d.high,low=d.low,close=d.close,name="K线"))
        fig.add_trace(go.Scatter(x=d.ts,y=d.ema20,name="EMA20"))
        fig.add_trace(go.Scatter(x=d.ts,y=d.ema50,name="EMA50"))
        fig.update_layout(height=440,xaxis_rangeslider_visible=False,margin=dict(l=5,r=5,t=20,b=5))
        st.plotly_chart(fig,use_container_width=True)
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
            st.warning("指标尚未共振，暂不生成方向性模拟仓位。")
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

with tab2:
    st.caption("CoinDesk RSS；新闻可能延迟，不自动作为交易信号。")
    try:
        entries=feed("https://www.coindesk.com/arc/outboundfeeds/rss/")
        for item in entries: st.markdown(f"**[{item.get('title','新闻')}]({item.get('link','#')})**  \n{item.get('published','')}")
        if not entries: st.info("暂时没有可显示的新闻")
    except Exception as e: st.warning(f"新闻暂不可用：{e}")

with tab3:
    st.caption("美联储官方货币政策公告；CPI、非农结果以美国劳工统计局为准。")
    try:
        entries=feed("https://www.federalreserve.gov/feeds/press_monetary.xml")
        for item in entries: st.markdown(f"**[{item.get('title','公告')}]({item.get('link','#')})**  \n{item.get('published','')}")
        if not entries: st.info("暂无公告")
    except Exception as e: st.warning(f"美联储公告暂不可用：{e}")
    st.markdown("[FOMC 官方日程](https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm) · [CPI 官方日程与数据](https://www.bls.gov/cpi/) · [非农就业报告](https://www.bls.gov/news.release/empsit.toc.htm)")
    st.info("目前仍使用官方公告和日程链接，尚未自动抓取 CPI、非农的预期值与实际值；避免把未经核实的数据当成实时消息。")

st.divider()
st.caption("稳定增强版 v3 · 免费公开数据 · 无 API 密钥 · 不自动交易 · 无后台推送 · 仅供研究与模拟")
