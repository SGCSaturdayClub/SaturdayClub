import streamlit as st
import random
import pandas as pd
import os

# --- DATABASE SETUP ---
DB_FILE = "members_db.csv"

def load_members():
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE).to_dict('records')
    return []

def save_member(name, handicap):
    members = load_members()
    if not any(m['name'].lower() == name.lower() for m in members):
        members.append({"name": name, "handicap": float(handicap)})
        pd.DataFrame(members).to_csv(DB_FILE, index=False)

# --- APP STATE MANAGEMENT ---
if 'groups' not in st.session_state:
    st.session_state.groups = []

def perform_swap(p1_name, p2_name):
    # Find positions
    idx1, g1 = next((i, g) for i, g in enumerate(st.session_state.groups) if any(p['name'] == p1_name for p in g))
    idx2, g2 = next((i, g) for i, g in enumerate(st.session_state.groups) if any(p['name'] == p2_name for p in g))
    
    # Get player objects
    p1_obj = next(p for p in st.session_state.groups[idx1] if p['name'] == p1_name)
    p2_obj = next(p for p in st.session_state.groups[idx2] if p['name'] == p2_name)
    
    # Swap them
    st.session_state.groups[idx1] = [p if p['name'] != p1_name else p2_obj for p in st.session_state.groups[idx1]]
    st.session_state.groups[idx2] = [p if p['name'] != p2_name else p1_obj for p in st.session_state.groups[idx2]]

# --- GROUPING LOGIC ---
def generate_initial_groups(players):
    priority_players = [p for p in players if p['priority']]
    normal_players = [p for p in players if not p['priority']]
    random.shuffle(normal_players)
    
    full_list = priority_players + normal_players
    n = len(full_list)
    
    num_fours = 0
    if n % 3 == 1: num_fours = 1
    elif n % 3 == 2: num_fours = 2
    
    num_threes = (n - (num_fours * 4)) // 3
    
    groups = []
    idx = 0
    for _ in range(num_fours):
        groups.append(full_list[idx:idx+4])
        idx += 4
    for _ in range(num_threes):
        groups.append(full_list[idx:idx+3])
        idx += 3
    return groups

# --- UI ---
st.set_page_config(page_title="Golf Roll-Up", layout="wide")
st.title("⛳ Club Roll-Up Manager")

# Sidebar for Database
with st.sidebar:
    st.header("Player Database")
    with st.expander("Add New Player"):
        new_name = st.text_input("Name")
        new_hc = st.number_input("Handicap", 0.0, 54.0, 18.0)
        if st.button("Add to Club"):
            if new_name:
                save_member(new_name, new_hc)
                st.rerun()
    
    st.write("---")
    if st.button("Clear Today's Groups"):
        st.session_state.groups = []
        st.rerun()

# 1. Sign In
all_members = load_members()
member_names = sorted([m['name'] for m in all_members])
selected = st.multiselect("Check-in Players:", member_names)

# 2. Priorities
if selected:
    priority_names = st.multiselect("Early Leavers (Group 1 priority):", selected)
    
    if st.button("Generate Randomized Groups"):
        current_players = []
        for name in selected:
            p_data = next(m for m in all_members if m['name'] == name)
            p_data['priority'] = name in priority_names
            current_players.append(p_data)
        st.session_state.groups = generate_initial_groups(current_players)

# 3. Results & Manual Override
if st.session_state.groups:
    st.write("---")
    st.header("Final Groupings")
    
    all_current_names = [p['name'] for g in st.session_state.groups for p in g]
    
    # Display Groups in columns
    cols = st.columns(len(st.session_state.groups))
    for i, group in enumerate(st.session_state.groups):
        with cols[i]:
            avg_hc = sum(p['handicap'] for p in group) / len(group)
            st.subheader(f"Group {i+1}")
            st.caption(f"Avg HC: {avg_hc:.1f}")
            for p in group:
                st.write(f"• **{p['name']}**")
            
            # Individual swap logic
            to_swap_out = st.selectbox("Swap out:", ["-"] + [p['name'] for p in group], key=f"out_{i}")
            if to_swap_out != "-":
                others = [n for n in all_current_names if n not in [p['name'] for p in group]]
                to_swap_in = st.selectbox(f"Swap {to_swap_out} with:", ["-"] + others, key=f"in_{i}")
                if to_swap_in != "-":
                    if st.button(f"Confirm Swap", key=f"btn_{i}"):
                        perform_swap(to_swap_out, to_swap_in)
                        st.rerun()