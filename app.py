import streamlit as st
import random
import pandas as pd
import os
from datetime import datetime, timedelta

# --- DATABASE SETUP ---
DB_FILE = "members_db.csv"

def load_members():
    if os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE)
        cols = {
            'appearances': 0, 
            'handicap': 18.0, 
            'main_winnings': 0.0, # Separate Main Pot
            'twos_winnings': 0.0, # Separate 2s Pot
            'twos_count': 0
        }
        for col, default in cols.items():
            if col not in df.columns: df[col] = default
        return df.to_dict('records')
    return []

def save_all_members(member_list):
    pd.DataFrame(member_list).to_csv(DB_FILE, index=False)

# --- UI SETUP ---
st.set_page_config(page_title="Golf Roll-Up Pro", layout="wide")
st.title("⛳ Club Roll-Up: Season 2026")

all_members = load_members()

# --- 1. SEPARATE MONEY LISTS ---
if all_members:
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader("🏆 Main Money List")
        main_list = sorted(all_members, key=lambda x: x['main_winnings'], reverse=True)[:3]
        for i, m in enumerate(main_list):
            st.write(f"{['🥇','🥈','🥉'][i]} **{m['name']}**: £{m['main_winnings']:.2f}")

    with col_right:
        st.subheader("🎯 2s Money List")
        twos_list = sorted(all_members, key=lambda x: x['twos_winnings'], reverse=True)[:3]
        for i, m in enumerate(twos_list):
            st.write(f"{['🥇','🥈','🥉'][i]} **{m['name']}**: £{m['twos_winnings']:.2f} ({m['twos_count']} total)")
    st.write("---")

# --- SIDEBAR ADMIN ---
with st.sidebar:
    st.header("Prize Pot & Admin")
    custom_pot = st.number_input("Main Prize Pot (£)", min_value=0.0, value=0.0, step=1.0)
    use_twos = st.checkbox("Include '2s' Competition", value=True)
    
    if all_members:
        csv = pd.DataFrame(all_members).to_csv(index=False).encode('utf-8')
        st.download_button("📥 Backup Database", csv, "golf_database_2026.csv", "text/csv")
    
    if st.button("Clear Today's Groups"):
        st.session_state.groups = []
        st.rerun()

# --- 2. CHECK-IN ---
member_names = sorted([m['name'] for m in all_members])
selected = st.multiselect("Check-in Players:", member_names)

if selected:
    if st.button("Shuffle & Start Round"):
        members_list = load_members()
        current_players = []
        for name in selected:
            for m in members_list:
                if m['name'] == name:
                    m['appearances'] += 1
                    current_players.append(m.copy())
        save_all_members(members_list)
        
        random.shuffle(current_players)
        n = len(current_players)
        num_fours = 1 if n % 3 == 1 else 2 if n % 3 == 2 else 0
        num_threes = (n - (num_fours * 4)) // 3
        gps = []
        idx = 0
        for _ in range(num_fours): gps.append(current_players[idx:idx+4]); idx += 4
        for _ in range(num_threes): gps.append(current_players[idx:idx+3]); idx += 3
        st.session_state.groups = gps
        st.rerun()

# --- 3. SCORING & FINALIZING ---
if st.session_state.groups:
    st.write("---")
    all_current_names = [p['name'] for g in st.session_state.groups for p in g]
    
    # Calculate 2s Pot
    twos_pot = sum(1 for n in all_current_names if st.session_state.get(f"paid_twos_{n}")) if use_twos else 0
    
    st.header("Enter Scores & 2s")
    for i in range(0, len(st.session_state.groups), 4):
        cols = st.columns(4)
        for j, group in enumerate(st.session_state.groups[i:i+4]):
            with cols[j]:
                st.info(f"Group {i+j+1}")
                for p in group:
                    p_name = p['name']
                    st.write(f"**{p_name}**")
                    c1, c2 = st.columns(2)
                    c1.checkbox("Entered 2s?", key=f"paid_twos_{p_name}")
                    c2.checkbox("Got a 2!", key=f"got_two_{p_name}")
                    
                    s1, s2 = st.columns(2)
                    s1.number_input("F9", 0, 30, key=f"f9_{p_name}")
                    s2.number_input("B9", 0, 30, key=f"b9_{p_name}")
                    st.write("---")

    st.write("---")
    st.header("🏆 Results & Final Payouts")
    
    twos_winners = [n for n in all_current_names if st.session_state.get(f"got_two_{n}") and st.session_state.get(f"paid_twos_{n}")]
    two_pay_each = twos_pot / len(twos_winners) if twos_winners else 0

    results = [{"name": n, "f9": st.session_state.get(f"f9_{n}", 0), "b9": st.session_state.get(f"b9_{n}", 0), 
                "total": st.session_state.get(f"f9_{n}", 0) + st.session_state.get(f"b9_{n}", 0)} for n in all_current_names]
    df = pd.DataFrame(results)

    if custom_pot > 0 and not df.empty:
        share = custom_pot / 3
        def get_win(data, col, skip=[]):
            filt = data[~data['name'].isin(skip)]
            if filt.empty: return [], 0
            m_score = filt[col].max()
            if m_score == 0: return [], 0
            ws = filt[filt[col] == m_score]['name'].tolist()
            return ws, share / len(ws)

        ov_w, ov_p = get_win(df, 'total')
        f9_w, f9_p = get_win(df, 'f9', skip=ov_w)
        b9_w, b9_p = get_win(df, 'b9', skip=ov_w)

        # Show Payouts summary
        st.write(f"**2s Pot (£{twos_pot}):** {', '.join(twos_winners) if twos_winners else 'No winners'}")
        st.write(f"**Main Pot (£{custom_pot}):** Overall: {', '.join(ov_w)} | F9: {', '.join(f9_w)} | B9: {', '.join(b9_w)}")

        if st.button("Finalize: Update Season Stats & Cuts"):
            members_list = load_members()
            for m in members_list:
                name = m['name']
                
                # 1. Update 2s List
                if name in twos_winners:
                    m['twos_count'] += 1
                    m['twos_winnings'] += two_pay_each
                
                # 2. Update Main Pot & Cuts
                main_pay = 0
                if name in ov_w: main_pay = ov_p
                elif name in f9_w: main_pay = f9_p
                elif name in b9_w: main_pay = b9_p
                
                if main_pay > 0:
                    m['main_winnings'] += main_pay
                    cut = 0.10 if main_pay >= 15.0 else 0.05
                    m['handicap'] = round(m['handicap'] * (1 - cut), 1)
            
            save_all_members(members_list)
            st.success("Main and 2s Money Lists updated!")
            st.rerun()

# --- 4. FULL LEADERBOARD ---
with st.expander("Full Season Stats"):
    df_full = pd.DataFrame(all_members).sort_values("main_winnings", ascending=False)
    st.table(df_full)
