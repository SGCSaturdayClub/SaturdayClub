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

# --- 3. THE DRAW (With 8:30 Start & Priority) ---
if selected:
    if st.button("Shuffle & Generate Tee Times"):
        members_list = load_members()
        
        # Separate Priority and Normal
        priority_list = [m for m in members_list if m['name'] in priority_players]
        normal_list = [m for m in members_list if m['name'] in selected and m['name'] not in priority_players]
        
        random.shuffle(priority_list)
        random.shuffle(normal_list)
        
        full_roster = priority_list + normal_list
        
        # Grouping Logic
        n = len(full_roster)
        num_fours = 1 if n % 3 == 1 else 2 if n % 3 == 2 else 0
        num_threes = (n - (num_fours * 4)) // 3
        
        temp_groups = []
        idx = 0
        for _ in range(num_fours): 
            temp_groups.append(full_roster[idx:idx+4])
            idx += 4
        for _ in range(num_threes): 
            temp_groups.append(full_roster[idx:idx+3])
            idx += 3
        
        # Store in session state so it survives the rerun
        st.session_state.groups = temp_groups
        st.rerun()

# --- 4. DISPLAY & SCORING ---
if st.session_state.groups:
    st.write("---")
    st.header("⛳ Today's Groups & Tee Times")
    
    start_time = datetime.strptime("08:30", "%H:%M")
    
    # We show the tee times first for everyone to see
    for i, group in enumerate(st.session_state.groups):
        tee_time = (start_time + timedelta(minutes=i * 8)).strftime("%H:%M")
        names = ", ".join([p['name'] for p in group])
        st.info(f"**{tee_time} - Group {i+1}:** {names}")

    # Now the Scoring Form
    st.write("---")
    st.header("🏆 Enter Results")
    with st.form("scoring_form"):
        all_scores = []
        for i, group in enumerate(st.session_state.groups):
            st.subheader(f"Group {i+1}")
            cols = st.columns([3, 1, 1, 1])
            
            for player in group:
                p_name = player['name']
                c = st.columns([3, 1, 1, 1])
                c[0].write(f"**{p_name}**")
                f9 = c[1].number_input("F9", 0, 50, 0, key=f"f9_{p_name}")
                b9 = c[2].number_input("B9", 0, 50, 0, key=f"b9_{p_name}")
                two = c[3].checkbox("2", key=f"two_{p_name}")
                
                all_scores.append({
                    "name": p_name, "f9": f9, "b9": b9, 
                    "total": f9+b9, "two": two, "handicap": player['handicap']
                })
        
        if st.form_submit_button("Calculate Winners & Update Handicaps"):
            process_results(all_scores)
