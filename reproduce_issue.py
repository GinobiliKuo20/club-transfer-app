import pandas as pd
import io

# Copy of the process_allocation function (simplified to run without streamlit imports if possible, but st is not used inside heavily)
# We need to mock st.warning or remove it.
def process_allocation_mock(students_df, clubs_df, h1_forbidden=[], h2_forbidden=[], h1_ban_all=False, h2_ban_all=False):
    # Mocking club_vacancies logic from app.py
    # START CODE FROM APP.PY (Selected parts)
    
    # 1. 初始化資料
    # FIX APPLIED HERE
    if '社團名稱' in clubs_df.columns:
        club_vacancies = clubs_df.groupby('社團名稱')['目前缺額'].sum().to_dict()
    else:
        club_vacancies = clubs_df['目前缺額'].to_dict()

    # FIX: Add missing clubs
    all_original_clubs = students_df['原社團'].dropna().astype(str).unique()
    for club in all_original_clubs:
        club = club.strip()
        if club and club not in club_vacancies:
            club_vacancies[club] = 0
    
    # Debug print
    print(f"DEBUG: club_vacancies keys: {list(club_vacancies.keys())}")
    
    if '填寫時間' in students_df.columns:
        students_df['填寫時間'] = pd.to_datetime(students_df['填寫時間'])
        students_df = students_df.sort_values(by='填寫時間')
            
    students = []
    for idx, row in students_df.iterrows():
        grade = None
        # (Grade parsing logic omitted for brevity as it's not central to this bug, assuming grade is parsed or irrelevant if we don't ban)
        cls_str = str(row['班級'])
        # Simplified grade logic
        if "10" in cls_str: grade = 1
        elif "20" in cls_str: grade = 2
        
        forbidden_clubs = set()
        ban_all = False
        if grade == 1:
            if h1_ban_all: ban_all = True
            else: forbidden_clubs = set(h1_forbidden)
        elif grade == 2:
            if h2_ban_all: ban_all = True
            else: forbidden_clubs = set(h2_forbidden)

        prefs = []
        for i in range(1, 11):
            col_name = f'志願{i}'
            if col_name in row and pd.notna(row[col_name]):
                p = str(row[col_name]).strip()
                if p:
                    if ban_all: continue
                    if p in forbidden_clubs: continue
                    prefs.append(p)
        
        students.append({
            'id': row['學號'],
            'name': row['姓名'],
            'class': row['班級'],
            'original_club': str(row['原社團']).strip() if pd.notna(row['原社團']) else "",
            'prefs': prefs,
            'current_club': str(row['原社團']).strip() if pd.notna(row['原社團']) else "",
            'status': '原社團',
            'rank': 999,
            'grade': grade
        })

    iteration = 0
    max_iterations = 100
    
    while iteration < max_iterations:
        changed = False
        iteration += 1
        
        for s in students:
            current_rank_index = s['rank'] if s['rank'] != 999 else len(s['prefs'])
            
            for i in range(current_rank_index):
                wanted_club = s['prefs'][i]
                
                # BUG POTENTIAL: checking string against int keys?
                if wanted_club not in club_vacancies:
                    # print(f"DEBUG: {wanted_club} not in vacancies")
                    continue 
                
                if club_vacancies[wanted_club] > 0:
                    old_club = s['current_club']
                    new_club = wanted_club
                    
                    club_vacancies[new_club] -= 1
                    
                    # BUG POTENTIAL: If old_club (e.g. Comic Research) is not in vacancy dict, spot is lost.
                    if old_club in club_vacancies:
                        club_vacancies[old_club] += 1
                    else:
                        print(f"DEBUG: Leaving {old_club} but it's not in vacancy dict, so spot lost!")
                        
                    s['current_club'] = new_club
                    s['rank'] = i
                    s['status'] = f'轉入志願{i+1}'
                    
                    changed = True
                    break 
        
        if not changed:
            break

    # Results
    results = []
    for s in students:
        results.append(s)
    return results, club_vacancies

# --- TEST CASE ---
# Club A: Basketball (1 vacancy)
# Club B: Comic Research (0 vacancies, NOT IN LIST)
# Club C: Chess (5 vacancies)

# Student 1: In Club B (Comic), Wants Club A (Basketball) - Timestamp 1
# Student 2: In Club A (Basketball), Wants Club C (Chess) - Timestamp 2

# Expected Flow:
# 1. Student 1 wants A. A has 0 spots (filled by S2 effectively, wait, S2 is IN A. 
#    Actually, `clubs_df` specifies *vacancies*. So if Club A has 1 vacancy, it means 1 OPEN spot.
#    Let's adjust scenario to match "someone transferred OUT".
#    Scenario:
#      Club A (Comic): 0 Vacancies. (It's full).
#      Club B (Basketball): 1 Vacancy.
#      Student X (New): Wants A.
#      Student Y (In A): Wants B.
#    Processing:
#      Student Y moves to B. A should gain +1 vacancy.
#      Student X moves to A.

def test_reproduction():
    # Setup DataFrames
    # Note: defining columns but NOT setting index, simulating read_excel behavior
    clubs_data = {
        '社團名稱': ['Basketball', 'Chess'], # Comic is missing because it has 0 vacancies
        '目前缺額': [1, 5]
    }
    clubs_df = pd.DataFrame(clubs_data)
    
    students_data = [
        {
            '學號': '101', '姓名': 'StdX', '班級': '101', '填寫時間': '2023-01-01 10:00',
            '原社團': 'None', '志願1': 'Comic', '志願2': '', '志願3': ''
        },
        {
            '學號': '102', '姓名': 'StdY', '班級': '101', '填寫時間': '2023-01-01 10:01',
            '原社團': 'Comic', '志願1': 'Basketball', '志願2': '', '志願3': ''
        }
    ]
    students_df = pd.DataFrame(students_data)
    
    print("--- Running Reproduction ---")
    results, vacancies = process_allocation_mock(students_df, clubs_df)
    
    print("\n--- Results ---")
    for r in results:
        print(f"ID: {r['id']}, Orig: {r['original_club']}, Current: {r['current_club']}")

if __name__ == "__main__":
    test_reproduction()
