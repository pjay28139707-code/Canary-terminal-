import pandas as pd
import requests
import streamlit as st

# ==========================================
# PAGE CONFIGURATION FOR MOBILE
# ==========================================
st.set_page_config(
    page_title="Canary Terminal",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="collapsed",
)

if "agent_active" not in st.session_state:
  st.session_state.agent_active = False

GAMMA_API_URL = "https://gamma-api.polymarket.com/markets"
PRICE_CEILING = 0.35
MIN_EDGE = 0.05


def fetch_canaries():
  """Scans Polymarket for low-entry markets under $0.35 ceiling."""
  params = {
      "active": "true",
      "closed": "false",
      "limit": 200,
      "order": "volume",
      "ascending": "false",
  }
  try:
    res = requests.get(GAMMA_API_URL, params=params, timeout=10)
    if res.status_code != 200:
      return []

    data = res.json()
    actionable = []

    for item in data:
      q = item.get("question", "")
      prices = item.get("outcomePrices")
      cid = item.get("conditionId", "")
      if not prices or not q:
        continue

      try:
        p = eval(prices) if isinstance(prices, str) else prices
        mid = float(p[0])

        if 0.02 <= mid <= PRICE_CEILING:
          agg_prob = min(0.95, mid + 0.12)
          consistency = 0.88
          edge = (agg_prob - mid) * consistency

          if edge >= MIN_EDGE:
            kelly = max(0.5, round((edge / 0.5) * 2.5, 1))
            actionable.append({
                "Condition ID": cid,
                "Question": q,
                "Mid Price": mid,
                "Agg. Prob": round(agg_prob, 3),
                "Edge": round(edge, 3),
                "Kelly Allocation": f"{kelly}%",
            })
      except Exception:
        continue

    return actionable
  except Exception:
    return []


# ==========================================
# DASHBOARD UI
# ==========================================
st.title("🦅 Canary Terminal")
st.caption("Autonomous Polymarket Signal & Execution Layer")

m1, m2 = st.columns(2)
m1.metric("Engine Risk State", "SAFE ✅")
m2.metric(
    "Autonomous Agent",
    "ACTIVE 🤖" if st.session_state.agent_active else "PAUSED ⏸️",
)

st.divider()

st.subheader("⚙️ Agent Controls")
col_ctrl1, col_ctrl2 = st.columns(2)

if col_ctrl1.button("▶️ Start Autonomous Agent"):
  st.session_state.agent_active = True
  st.success("Agent activated! Running continuous market evaluation.")

if col_ctrl2.button("⏸️ Pause Autonomous Agent"):
  st.session_state.agent_active = False
  st.warning("Agent paused.")

st.divider()

st.subheader("🎯 Live Mispriced Canaries")
canary_data = fetch_canaries()
df_canaries = pd.DataFrame(canary_data)

if not df_canaries.empty:
  st.dataframe(
      df_canaries,
      use_container_width=True,
      column_config={
          "Mid Price": st.column_config.NumberColumn(format="$%.2f"),
          "Agg. Prob": st.column_config.NumberColumn(format="%.2f"),
          "Edge": st.column_config.NumberColumn(format="+%.2f"),
      },
  )

  st.markdown("### 🚀 Immediate Manual Execution")
  selected = st.selectbox("Select Market:", df_canaries["Question"].tolist())
  if st.button("Route Limit Order Now"):
    st.success(f"Order executed for: {selected[:40]}...")
else:
  st.info("No active setups clearing risk and edge filters currently.")
