import requests
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
import feedparser

st.set_page_config(page_title="BTC ETH 合约研究台", page_icon="📈", layout="wide")
st.title("BTC / ETH 合约研究台")
st.caption("OKX 免费公开行情 · 技术指标 · 币圈新闻 · 美联储公告 · 仅供模拟研究")

@st.cache_data(ttl=120)
def candles(symbol, bar):
    all_rows = []
    cursor = None
    for _ in range(3):
        params = {"instId":symbol, "bar":bar, "limit":"100"}
        if cursor is not None:
            params["after"] = str(cursor)
        response = requests.get("https://www.okx.com/api/v5/market/history-candles", params=params, timeout=12)
        response.raise_for_status()
        data = response.json()
        if data.get("code") != "0":
            raise RuntimeError(data.get("msg", "OKX API error"))
        rows = data.get("data", [])
        if not rows:
            break
        all_rows.extend(rows)
        oldest = min(int(row[0]) for row in rows)
        if cursor is not None and oldest >= cursor:
            break
        cursor = oldest
    if not all_rows:
        raise RuntimeError("未获取到K线")
    d = pd.DataFrame(all_rows, columns=["ts","open","high","low","close","volume","vol_ccy","vol_quote","confirm"])
    d = d[d["confirm"] == "1"].copy()
    for col in ["open","high","low","close","volume"]:
        d[col] = pd.to_numeric(d[col], errors="coerce")
    d["ts"] = pd.to_datetime(pd.to_numeric(d["ts"]), unit="ms", utc=True).dt.tz_convert("Asia/Shanghai")
    return d.drop_duplicates("ts").sort_values("ts").tail(240).reset_index(drop=True)

def indicators(d):
    d = d.copy()
    c = d["close"]
    d["ema20"] = c.ewm(span=20, adjust=False).mean()
    d["ema50"] = c.ewm(span=50, adjust=False).mean()
    delta = c.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
    d["rsi"] = 100 - 100/(1+gain/loss.replace(0,np.nan))
    d["macd"] = c.ewm(span=12, adjust=False).mean()-c.ewm(span=26, adjust=False).mean()
    d["signal"] = d["macd"].ewm(span=9, adjust=False).mean()
    tr = pd.concat([d["high"]-d["low"],(d["high"]-c.shift()).abs(),(d["low"]-c.shift()).abs()],axis=1).max(axis=1)
    d["atr"] = tr.ewm(alpha=1/14, adjust=False).mean()
    d["volume_ma"] = d["volume"].rolling(20).mean()
    return d

@st.cache_data(ttl=900)
def news(url):
    response = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=12)
    response.raise_for_status()
    return feedparser.parse(response.content).entries[:8]

pair = st.selectbox("交易对", ["BTC-USDT-SWAP","ETH-USDT-SWAP"])
bar = st.radio("K线周期", ["1H","4H"], horizontal=True)
capital = st.number_input("模拟本金（USDT）", min_value=100.0, value=1000.0, step=100.0)
risk = st.slider("单笔最大模拟亏损（本金百分比）",0.25,2.0,1.0,0.25)
if st.button("刷新数据"):
    candles.clear()
    news.clear()

tab1,tab2,tab3 = st.tabs(["行情与参考位","币圈新闻","美联储与宏观"])
with tab1:
    try:
        d = indicators(candles(pair,bar))
        if len(d)<60:
            st.warning("K线样本不足，指标可靠性有限")
        row = d.iloc[-1]
        price,atr = float(row["close"]),float(row["atr"])
        bullish = price>row["ema20"]>row["ema50"] and row["macd"]>row["signal"]
        bearish = price<row["ema20"]<row["ema50"] and row["macd"]<row["signal"]
        direction = "偏多" if bullish else "偏空" if bearish else "观望"
        change = (price/float(d.iloc[-2]["close"])-1)*100
        volume_ratio = float(row["volume"]/row["volume_ma"]) if row["volume_ma"]>0 else 0
        a,b,c,e=st.columns(4)
        a.metric("最近收盘价 USDT",f"{price:,.2f}",f"{change:+.2f}%")
        b.metric("RSI",f"{row['rsi']:.1f}")
        c.metric("量比",f"{volume_ratio:.2f}")
        e.metric("技术方向",direction)
        fig=go.Figure()
        fig.add_trace(go.Candlestick(x=d["ts"],open=d["open"],high=d["high"],low=d["low"],close=d["close"],name="K线"))
        fig.add_trace(go.Scatter(x=d["ts"],y=d["ema20"],name="EMA20"))
        fig.add_trace(go.Scatter(x=d["ts"],y=d["ema50"],name="EMA50"))
        fig.update_layout(height=440,xaxis_rangeslider_visible=False,margin=dict(l=5,r=5,t=20,b=5))
        st.plotly_chart(fig,use_container_width=True)
        st.subheader("模拟入场与止盈止损")
        if bullish or bearish:
            sign = 1 if bullish else -1
            stop = price-sign*1.5*atr
            take1 = price+sign*1.5*atr
            take2 = price+sign*3*atr
            risk_budget = capital*risk/100
            quantity = risk_budget/abs(price-stop) if abs(price-stop)>0 else 0
            st.write(f"方向：**{'模拟做多' if bullish else '模拟做空'}**；观察入场价 **{price:,.2f}**；止损 **{stop:,.2f}**；止盈一 **{take1:,.2f}**；止盈二 **{take2:,.2f}** USDT。")
            st.write(f"按风险预算 **{risk_budget:.2f} USDT**，示例持仓约 **{quantity:.5f} {pair.split('-')[0]}**（未计手续费、滑点、资金费率与爆仓风险）。")
        else:
            st.info("指标冲突：暂不提供方向性入场、止盈和止损参考。")
        alerts=[]
        if abs(change)>=2: alerts.append("单根K线涨跌幅超过2%")
        if volume_ratio>=2: alerts.append("成交量超过20根均量的2倍")
        if row["rsi"]>=70: alerts.append("RSI超买")
        if row["rsi"]<=30: alerts.append("RSI超卖")
        st.warning("波动提醒：" + ("；".join(alerts) if alerts else "当前未触发预设阈值，不代表没有风险"))
        st.caption(f"最近已收盘K线：{row['ts']:%Y-%m-%d %H:%M} 北京时间。不是实时成交报价；参考位由ATR计算，不是盈利预测。")
    except Exception as exc:
        st.error(f"OKX 行情获取失败：{exc}")
        st.info("部分地区或云服务器可能无法访问OKX公共接口。")
with tab2:
    st.caption("CoinDesk RSS，新闻更新可能延迟；不自动把新闻当作交易信号。")
    try:
        entries=news("https://www.coindesk.com/arc/outboundfeeds/rss/")
        for item in entries:
            st.markdown(f"**[{item.get('title','新闻')} ]({item.get('link','#')})**  \n{item.get('published','')}")
        if not entries: st.info("当前无新闻")
    except Exception as exc: st.warning(f"新闻源暂不可用：{exc}")
with tab3:
    st.caption("美联储官方货币政策公告；CPI、非农数据由美国劳工统计局发布。")
    try:
        entries=news("https://www.federalreserve.gov/feeds/press_monetary.xml")
        for item in entries:
            st.markdown(f"**[{item.get('title','公告')}]({item.get('link','#')})**  \n{item.get('published','')}")
        if not entries: st.info("当前无公告")
    except Exception as exc: st.warning(f"美联储公告暂不可用：{exc}")
    st.markdown("[美联储FOMC日程](https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm) · [美国CPI](https://www.bls.gov/cpi/) · [非农就业报告](https://www.bls.gov/news.release/empsit.toc.htm)")
st.divider()
st.caption("仅供学习和模拟；无自动交易、无API密钥、无后台推送。合约交易可能快速亏损甚至爆仓。")
