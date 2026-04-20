import streamlit as st
from supabase import create_client, Client
import datetime
import time

# ==========================================
# 1. 页面设置与【现代金融风】主题美化
# ==========================================
st.set_page_config(page_title="球星卡小荷包", page_icon="💳", layout="wide")

st.markdown("""
    <style>
    /* 强制全局暗黑背景与现代原生字体栈 */
    .stApp {
        background-color: #0E1117 !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif !important;
    }
    h1 {
        text-align: center; 
        color: #FF8C00 !important; 
        font-weight: 700 !important;
        text-shadow: 0px 2px 8px rgba(255,140,0,0.15); 
        margin-bottom: 5px;
    }
    .subtitle {
        text-align: center; 
        color: #888888; 
        font-size: 14px; 
        margin-bottom: 30px; 
        letter-spacing: 0.5px;
    }
    /* 数据看板卡片美化 */
    [data-testid="stMetric"] {
        background: linear-gradient(145deg, #1A1C23, #121419) !important;
        border: 1px solid #2A2D35 !important;
        border-top: 3px solid #FF8C00 !important;
        border-radius: 12px; 
        padding: 20px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2); 
        text-align: center;
        transition: transform 0.3s ease;
    }
    [data-testid="stMetric"]:hover { 
        transform: translateY(-4px); 
        border-color: #FF8C00 !important; 
    }
    [data-testid="stMetricValue"] { 
        justify-content: center; 
        color: #F8F9FA !important; 
        font-size: 34px !important; 
        font-weight: 600 !important;
    }
    [data-testid="stMetricLabel"] { 
        justify-content: center; 
        color: #A0AEC0 !important; 
        font-size: 14px !important; 
    }
    /* 按钮美化 */
    .stButton > button {
        background: linear-gradient(90deg, #FF8C00, #FF6347) !important;
        color: white !important; 
        border: none !important; 
        border-radius: 8px !important;
        padding: 10px 24px !important; 
        font-weight: 600 !important; 
        width: 100%;
    }
    .card-title {
        text-align: center; 
        color: #E0E0E0; 
        margin-top: 10px; 
        margin-bottom: 5px; 
        font-weight: 600;
    }
    [data-testid="stForm"] { 
        border-color: #2A2D35 !important; 
        border-radius: 12px !important; 
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. 连接数据库
# ==========================================
@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase: Client = init_connection()

# ==========================================
# 3. 核心财务逻辑计算
# ==========================================
def get_financials():
    # 获取所有卡片和资金流水记录
    cards = supabase.table("cards").select("*").execute().data or []
    deposits = supabase.table("wallet_logs").select("*").execute().data or []
    
    # 1. 累计净投入 (充值 - 提现)
    net_capital = sum(d['amount'] for d in deposits)
    
    # 2. 计算所有买卡支出和卖卡收入
    buy_all = sum(c['buy_price'] + (c['costs'] or 0) for c in cards)
    sell_all = sum(c['sell_price'] or 0 for c in cards if c['status'] == '已售出')
    
    # 3. 现金余额 = 净投入 - 买卡支出 + 卖卡收入
    cash_balance = net_capital - buy_all + sell_all
    
    # 4. 在手卡片价值 (仅统计状态为"持有中"的卡片成本)
    inventory_value = sum(c['buy_price'] + (c['costs'] or 0) for c in cards if c['status'] == '持有中')
    
    # 5. 钱包总资产 = 现金 + 在手卡片
    total_balance = cash_balance + inventory_value
    
    return net_capital, cash_balance, inventory_value, total_balance, cards

# --- 渲染顶部看板 ---
st.markdown("<h1>💳 球星卡资产管理系统</h1>", unsafe_allow_html=True)
st.markdown("<div class='subtitle'>资产全维度管理 · 数据实时同步</div>", unsafe_allow_html=True)

net_cap, cash_bal, inv_val, total_bal, all_cards = get_financials()

col1, col2, col3, col4 = st.columns(4)
col1.metric("累计净投入", f"¥ {net_cap:,.2f}")
col2.metric("当前现金余额", f"¥ {cash_bal:,.2f}")
col3.metric("在手卡片价值", f"¥ {inv_val:,.2f}")
col4.metric("钱包总资产", f"¥ {total_bal:,.2f}", delta=f"{total_bal - net_cap:,.2f} 盈亏")

st.divider()

# ==========================================
# 4. 导航与页面内容
# ==========================================
tabs = st.tabs(["🖼️ 资产画廊与管理", "📝 录入新卡", "💰 资金池管理"])

# ----------------------------------------
# 页面 1: 资产画廊 (1:1图片 + 全字段修改)
# ----------------------------------------
with tabs[0]:
    if not all_cards:
        st.info("📦 你的库存还是空的，先去录入卡片吧！")
    else:
        cols = st.columns(3)
        for i, card in enumerate(all_cards):
            with cols[i % 3]:
                
                # 【完美 1:1 照片展示】
                st.markdown(f"""
                    <div style="width: 100%; aspect-ratio: 1 / 1; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.3); margin-bottom: 10px; border: 1px solid #333;">
                        <img src="{card['image_url']}" style="width: 100%; height: 100%; object-fit: cover; display: block;">
                    </div>
                """, unsafe_allow_html=True)
                
                st.markdown(f"<h4 class='card-title'>{card['card_name']}</h4>", unsafe_allow_html=True)
                
                date_str = card.get('date', '未记录日期')
                st.markdown(f"<p style='text-align: center; color:#888; font-size: 13px; margin-bottom: 5px;'>交易日: {date_str}</p>", unsafe_allow_html=True)
                
                # 状态与盈亏展示
                buy_total = card['buy_price'] + (card['costs'] or 0)
                if card['status'] == "持有中":
                    st.warning(f"持有中 · 总成本: ¥{buy_total:,.2f}")
                else:
                    profit = (card['sell_price'] or 0) - buy_total
                    st.success(f"已售出 · 盈亏: ¥{profit:,.2f}")
                
                # 【全能编辑表单】
                with st.expander("✏️ 编辑详情 / 卖出"):
                    with st.form(f"edit_form_{card['id']}"):
                        
                        # 新增：允许修改卡片名称
                        new_name = st.text_input("修改卡片名称", value=card['card_name'])
                        
                        col_e1, col_e2 = st.columns(2)
                        with col_e1:
                            new_status = st.selectbox("状态", ["持有中", "已售出"], index=0 if card['status']=="持有中" else 1)
                            new_buy = st.number_input("修改买入价", value=float(card['buy_price']), step=10.0)
                        
                        with col_e2:
                            new_cost = st.number_input("修改杂费(邮费等)", value=float(card['costs'] or 0.0), step=5.0)
                            new_sell = st.number_input("卖出价格", value=float(card['sell_price'] or 0.0), step=10.0)
                        
                        # 日期处理
                        default_date = datetime.date.fromisoformat(card['date']) if card.get('date') else datetime.date.today()
                        new_date = st.date_input("交易日期", value=default_date)
                        
                        # 提交修改
                        if st.form_submit_button("保存所有修改"):
                            update_data = {
                                "card_name": new_name,
                                "status": new_status, 
                                "buy_price": new_buy,
                                "costs": new_cost,
                                "sell_price": new_sell, 
                                "date": str(new_date)
                            }
                            supabase.table("cards").update(update_data).eq("id", card['id']).execute()
                            st.rerun()
                            
                st.markdown("<hr style='border: 1px dashed #333; margin-top: 20px; margin-bottom: 20px;'>", unsafe_allow_html=True)

# ----------------------------------------
# 页面 2: 录入买入 
# ----------------------------------------
with tabs[1]:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        with st.form("buy_card_form", clear_on_submit=True):
            name = st.text_input("球星卡名称")
            
            col_a, col_b = st.columns(2)
            with col_a:
                b_price = st.number_input("购入金额 (元)", min_value=0.0, step=10.0)
            with col_b:
                c_price = st.number_input("杂费(邮费/手续费)", min_value=0.0, step=5.0)
                
            b_date = st.date_input("购入日期", value=datetime.date.today())
            img = st.file_uploader("📸 上传卡片照片", type=['jpg','png','jpeg','webp'])
            
            if st.form_submit_button("确认入库 (-¥)", use_container_width=True):
                if not name or not img:
                    st.error("卡片名称和照片是必填项哦！")
                else:
                    with st.spinner("正在上传图片并记录数据..."):
                        try:
                            # 1. 处理图片上传
                            file_ext = img.name.split('.')[-1]
                            file_name = f"{int(time.time())}.{file_ext}" 
                            supabase.storage.from_("card-images").upload(file_name, img.getvalue())
                            img_url = supabase.storage.from_("card-images").get_public_url(file_name)
                            
                            # 2. 写入数据库
                            new_card_data = {
                                "card_name": name, 
                                "buy_price": b_price, 
                                "costs": c_price,
                                "date": str(b_date), 
                                "status": "持有中", 
                                "image_url": img_url
                            }
                            supabase.table("cards").insert(new_card_data).execute()
                            
                            st.success("入库成功！现金余额已自动扣除。")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"上传失败: {e}")

# ----------------------------------------
# 页面 3: 资金池管理 
# ----------------------------------------
with tabs[2]:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.info("💡 记录汇入小荷包的本金，或将赚到的现金提现。")
        
        action_type = st.radio("操作类型", ["📥 汇入资金 (充值)", "📤 汇出资金 (提现)"], horizontal=True)
        
        with st.form("fund_management_form"):
            amt = st.number_input("操作金额 (¥)", min_value=0.0, step=100.0)
            d_date = st.date_input("操作日期", value=datetime.date.today())
            
            submit_label = "确认汇入" if "汇入" in action_type else "确认提现"
            
            if st.form_submit_button(submit_label, use_container_width=True):
                if amt > 0:
                    if "汇出" in action_type and amt > cash_bal:
                        st.warning("⚠️ 提取金额超过当前现金余额，可能会导致现金为负数！")
                    
                    # 核心逻辑：充值为正数，提现存为负数
                    final_amt = amt if "汇入" in action_type else -amt
                    
                    try:
                        new_log = {
                            "amount": final_amt, 
                            "date": str(d_date)
                        }
                        supabase.table("wallet_logs").insert(new_log).execute()
                        
                        st.success(f"成功{submit_label} ¥{amt}！")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"记录失败: {e}")
                else:
                    st.error("请输入大于 0 的金额！")
