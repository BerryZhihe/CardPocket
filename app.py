import streamlit as st
from supabase import create_client, Client
import datetime
import time

# ==========================================
# 1. 页面设置与黑橙主题美化 (保持不变)
# ==========================================
st.set_page_config(page_title="球星卡小荷包", page_icon="💳", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0E1117; }
    h1, h2, h3 { text-align: center; color: #FF8C00 !important; }
    .stMetric {
        background-color: #1E1E1E;
        padding: 20px;
        border-radius: 15px;
        border: 1px solid #FF8C00;
        text-align: center;
    }
    [data-testid="stMetricValue"] { justify-content: center; color: #FFFFFF !important; }
    .centered-text { text-align: center; }
    </style>
    """, unsafe_allow_html=True)


# ==========================================
# 2. 连接数据库 (保持不变)
# ==========================================
@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])


supabase: Client = init_connection()


# ==========================================
# 3. 核心财务逻辑计算 (升级：区分在手与已售)
# ==========================================
def get_financials():
    cards = supabase.table("cards").select("*").execute().data or []
    deposits = supabase.table("wallet_logs").select("*").execute().data or []

    # 累计充值
    total_deposited = sum(d['amount'] for d in deposits)

    # 现金余额 = 总充值 - 所有买卡花出去的钱 + 卖卡收回来的钱
    buy_all = sum(c['buy_price'] + (c['costs'] or 0) for c in cards)
    sell_all = sum(c['sell_price'] or 0 for c in cards if c['status'] == '已售出')
    cash_balance = total_deposited - buy_all + sell_all

    # 在手卡片价值 (仅算没卖的卡)
    inventory_value = sum(c['buy_price'] + (c['costs'] or 0) for c in cards if c['status'] == '持有中')

    # 钱包总余额 = 现金余额 + 在手卡片价值
    total_balance = cash_balance + inventory_value

    return total_deposited, cash_balance, inventory_value, total_balance, cards


# 渲染顶部数据看板
st.markdown("<h1>💳 球星卡资产管理系统</h1>", unsafe_allow_html=True)
st.markdown("<p class='centered-text' style='color:#888;'>日期化记录 · 资产/现金分离模式</p>", unsafe_allow_html=True)

total_dep, cash_bal, inv_val, total_bal, all_cards = get_financials()

col1, col2, col3, col4 = st.columns(4)
col1.metric("累计汇入本金", f"¥ {total_dep:,.2f}")
col2.metric("当前现金余额", f"¥ {cash_bal:,.2f}")
col3.metric("在手卡片价值", f"¥ {inv_val:,.2f}")
col4.metric("钱包总资产", f"¥ {total_bal:,.2f}", delta=f"{total_bal - total_dep:,.2f} 总盈亏")

st.divider()

# ==========================================
# 4. 居中导航与页面内容
# ==========================================
tabs = st.tabs(["🖼️ 资产画廊与管理", "📝 录入新卡", "💰 荷包充值"])

# ----------------------------------------
# 页面 1: 资产画廊 (加入日期展示与修改)
# ----------------------------------------
with tabs[0]:
    if not all_cards:
        st.info("📦 你的库存还是空的，先去录入卡片吧！")
    else:
        cols = st.columns(3)
        for i, card in enumerate(all_cards):
            with cols[i % 3]:
                st.image(card['image_url'], use_container_width=True)
                st.markdown(f"<h4 class='centered-text' style='margin-bottom:0;'>{card['card_name']}</h4>",
                            unsafe_allow_html=True)

                # 新增：显示日期
                date_str = card.get('date', '未记录日期')
                st.markdown(f"<p class='centered-text' style='color:#888; font-size: 14px;'>交易日: {date_str}</p>",
                            unsafe_allow_html=True)

                buy_total = card['buy_price'] + (card['costs'] or 0)

                if card['status'] == "持有中":
                    st.warning(f"持有中 · 成本: ¥{buy_total}")
                else:
                    profit = (card['sell_price'] or 0) - buy_total
                    st.success(f"已售出 · 盈亏: ¥{profit}")

                with st.expander("✏️ 修改状态 / 卖出"):
                    with st.form(f"edit_{card['id']}"):
                        new_status = st.selectbox("状态", ["持有中", "已售出"],
                                                  index=0 if card['status'] == "持有中" else 1)
                        new_sell = st.number_input("卖出价格", value=float(card['sell_price'] or 0.0), step=10.0)
                        # 新增：修改日期
                        default_date = datetime.date.fromisoformat(card['date']) if card.get(
                            'date') else datetime.date.today()
                        new_date = st.date_input("交易日期", value=default_date)

                        if st.form_submit_button("保存修改"):
                            supabase.table("cards").update({
                                "status": new_status, "sell_price": new_sell, "date": str(new_date)
                            }).eq("id", card['id']).execute()
                            st.rerun()
                st.markdown("<hr style='border: 1px dashed #333;'>", unsafe_allow_html=True)

# ----------------------------------------
# 页面 2: 录入买入 (完整带图片上传版)
# ----------------------------------------
with tabs[1]:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        with st.form("buy_card", clear_on_submit=True):
            name = st.text_input("球星卡名称")
            col_a, col_b = st.columns(2)
            with col_a:
                b_price = st.number_input("购入金额 (元)", min_value=0.0, step=10.0)
            with col_b:
                c_price = st.number_input("杂费(邮费/手续费)", min_value=0.0, step=5.0)

            # 新增：买入日期
            b_date = st.date_input("购入日期", value=datetime.date.today())
            img = st.file_uploader("📸 上传卡片照片", type=['jpg', 'png', 'jpeg'])

            if st.form_submit_button("确认入库", use_container_width=True):
                if not name or not img:
                    st.error("卡片名称和照片是必填项哦！")
                else:
                    with st.spinner("正在上传图片并记录数据..."):
                        try:
                            # 完整图片上传逻辑恢复
                            file_ext = img.name.split('.')[-1]
                            file_name = f"{int(time.time())}.{file_ext}"
                            supabase.storage.from_("card-images").upload(file_name, img.getvalue())
                            img_url = supabase.storage.from_("card-images").get_public_url(file_name)

                            # 写入带日期的数据
                            supabase.table("cards").insert({
                                "card_name": name,
                                "buy_price": b_price,
                                "costs": c_price,
                                "date": str(b_date),
                                "status": "持有中",
                                "image_url": img_url
                            }).execute()
                            st.success("入库成功！现金余额已扣除。")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"上传失败: {e}")

# ----------------------------------------
# 页面 3: 资金充值 (加入日期)
# ----------------------------------------
with tabs[2]:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.info("💡 记录汇入小荷包的本金，用于后续买卡。")
        with st.form("deposit"):
            amt = st.number_input("充值金额 (¥)", min_value=0.0, step=100.0)
            # 新增：充值日期
            d_date = st.date_input("充值日期", value=datetime.date.today())

            if st.form_submit_button("确认汇入", use_container_width=True):
                if amt > 0:
                    try:
                        supabase.table("wallet_logs").insert({
                            "amount": amt,
                            "date": str(d_date)
                        }).execute()
                        st.success(f"成功汇入 ¥{amt}！")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"充值记录失败: {e}")