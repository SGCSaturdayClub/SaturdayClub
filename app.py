import streamlit as st
import random
import pandas as pd
import os
from datetime import datetime, timedelta

# --- 1. DATABASE SETUP ---
DB_FILE = "members_db.csv"

# --- 2. INITIALIZE SESSION STATE (CRITICAL FIX) ---
# This must be here so the app doesn't crash on the first load
if 'groups' not in st.session_state:
    st.session_state.groups = []

# --- 3. DATABASE FUNCTIONS ---
def load_members():
    if os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE)
        # (The rest of your code here must also be indented...)
        cols = {
            'appearances': 0, 
            'handicap': 18.0, 
            'main_winnings': 0.0,
            'twos_winnings': 0.0,
            'twos_count': 0
        }
        for col, default in cols.items():
            if col not in df.columns: df[col] = default
        return df.to_dict('records')
    return []

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
st.set_page_config(page_title="Seckford Golf Club Saturday Club", layout="wide")
st.title("⛳ Saturday Club: 2026")

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
# --- ADD NEW PLAYER SECTION ---
    st.write("---")
    with st.expander("➕ Add New Player to Club"):
        new_name = st.text_input("Player Name (First & Last)")
        new_hc = st.number_input("Starting Handicap", 0.0, 54.0, 18.0, step=0.1)
        if st.button("Add to Database"):
            if new_name:
                # Check if name already exists
                if not any(m['name'].lower() == new_name.lower() for m in all_members):
                    new_player = {
                        "name": new_name,
                        "handicap": new_hc,
                        "appearances": 0,
                        "main_winnings": 0.0,
                        "twos_winnings": 0.0,
                        "twos_count": 0
                    }
                    all_members.append(new_player)
                    save_all_members(all_members)
                    st.success(f"Added {new_name}!")
                    st.rerun()
                else:
                    st.error("Player already exists!")
            else:
                st.warning("Please enter a name.")    
    if st.button("Clear Today's Groups"):
        st.session_state.groups = []
        st.rerun()

# --- 2. CHECK-IN WITH PRIORITY ---
st.header("Step 1: Check-in Players")
member_names = sorted([m['name'] for m in all_members])
selected = st.multiselect("Select players standing on the tee:", member_names)

# Create a list to track who needs an early exit
priority_players = []
if selected:
    with st.expander("⭐ Set Priorities (Early Leavers)"):
        st.write("Tick players who need to be in the first few groups:")
        for name in selected:
            if st.checkbox(f"Priority: {name}", key=f"pri_{name}"):
                priority_players.append(name)

# --- 3. THE DRAW (With 8:30 Start) ---
if selected:
    if st.button("Shuffle & Generate Tee Times"):
        members_list = load_members()
        
        # Separate Priority and Normal players
        priority_list = [m for m in members_list if m['name'] in priority_players]
        normal_list = [m for m in members_list if m['name'] in selected and m['name'] not in priority_players]
        
        # Randomize both lists separately to maintain fairness within the tiers
        random.shuffle(priority_list)
        random.shuffle(normal_list)
        
        # Combine: Priority players at the front of the queue
        full_roster = priority_list + normal_list
        
        # Update appearance counts
        for m in members_list:
            if m['name'] in selected:
                m['appearances'] += 1
        save_all_members(members_list)
        
        # Grouping Logic (3s and 4s)
        n = len(full_roster)
        num_fours = 1 if n % 3 == 1 else 2 if n % 3 == 2 else 0
        num_threes = (n - (num_fours * 4)) // 3
        
        gps = []
        idx = 0
        for _ in range(num_fours): 
            gps.append(full_roster[idx:idx+4])
            idx += 4
        for _ in range(num_threes): 
            gps.append(full_roster[idx:idx+3])
            idx += 3
        
        st.session_state.groups = gps
        st.rerun()

# --- 4. DISPLAY GROUPS & TEE TIMES ---
def process_results(all_scores):
    members_list = load_members()
    pot_value = 15.0  # Or your dynamic pot variable
    
    # 1. Determine OVERALL Winners (Highest Priority)
    best_overall = max(p['total'] for p in all_scores)
    winners_overall = [p['name'] for p in all_scores if p['total'] == best_overall]
    
    # Create a list of players who have already won to exclude them from F9/B9
    already_won = set(winners_overall)
    
    # 2. Determine FRONT 9 Winners (Exclude Overall Winners)
    # Filter scores to only include those not in the 'already_won' set
    f9_eligible = [p for p in all_scores if p['name'] not in already_won]
    if f9_eligible:
        best_f9 = max(p['f9'] for p in f9_eligible)
        winners_f9 = [p['name'] for p in f9_eligible if p['f9'] == best_f9]
        already_won.update(winners_f9)
    else:
        winners_f9 = []

    # 3. Determine BACK 9 Winners (Exclude Overall and F9 Winners)
    b9_eligible = [p for p in all_scores if p['name'] not in already_won]
    if b9_eligible:
        best_b9 = max(p['b9'] for p in b9_eligible)
        winners_b9 = [p['name'] for p in b9_eligible if p['b9'] == best_b9]
    else:
        winners_b9 = []

    # --- Payouts & Database Updates ---
    overall_share = pot_value / len(winners_overall) if winners_overall else 0
    f9_share = pot_value / len(winners_f9) if winners_f9 else 0
    b9_share = pot_value / len(winners_b9) if winners_b9 else 0

    # Apply winnings and tax logic
    for m in members_list:
        p_score = next((s for s in all_scores if s['name'] == m['name']), None)
        if not p_score: continue
        
        amt_won = 0
        if m['name'] in winners_overall: amt_won += overall_share
        elif m['name'] in winners_f9: amt_won += f9_share
        elif m['name'] in winners_b9: amt_won += b9_share
        
        # 10% cut for a full win (£15), 5% for a split win
        if amt_won >= 15.0:
            m['handicap'] = round(m['handicap'] * 0.90, 1)
        elif amt_won > 0:
            m['handicap'] = round(m['handicap'] * 0.95, 1)
            
        m['main_winnings'] += amt_won
        if p_score['two']: m['twos_count'] += 1

    save_all_members(members_list)
    
    # --- DISPLAY SUMMARY ---
    st.write("---")
    st.success("### 💰 Seckford Payouts (One Prize Rule Applied)")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.subheader("Overall")
        for w in winners_overall: st.write(f"🏆 {w} (£{overall_share:.2f})")
    with col2:
        st.subheader("Front 9")
        for w in winners_f9: st.write(f"🚩 {w} (£{f9_share:.2f})")
    with col3:
        st.subheader("Back 9")
        for w in winners_b9: st.write(f"🏁 {w} (£{b9_share:.2f})")
