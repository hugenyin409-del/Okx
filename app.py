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
        st.caption("官方时间核对入口：BLS发布日程 https://www.bls.gov/schedule/news_release/ ｜ FOMC https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm 。候选事件发布时间尚未逐条验证，不参与本项回测。")
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
