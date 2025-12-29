import pandas as pd

# Mocking the classes from app.py
class Student:
    def __init__(self, data, h1_forbidden=[], h2_forbidden=[], h1_ban_all=False, h2_ban_all=False):
        self.id = str(data['學號']).strip()
        self.name = data.get('姓名', '')
        self.original_club = str(data.get('原社團', '')).strip()
        self.class_str = str(data.get('班級', '')).strip()
        
        self.grade = None
        try:
            # Simple digit extraction
            cls_num = int(''.join(filter(str.isdigit, self.class_str))[:3])
            if 101 <= cls_num <= 115:
                self.grade = 1
            elif 201 <= cls_num <= 215:
                self.grade = 2
        except:
            pass
            
        self.prefs = []
        forbidden = set()
        ban = False
        
        if self.grade == 1:
            if h1_ban_all: ban = True
            else: forbidden = set(h1_forbidden)
        elif self.grade == 2:
            if h2_ban_all: ban = True
            else: forbidden = set(h2_forbidden)
            
        if not ban:
            for i in range(1, 11):
                col = f'志願{i}'
                if col in data:
                    p = str(data[col]).strip()
                    if p and p not in forbidden:
                        self.prefs.append(p)

        self.current_assigned = self.original_club 
        self.status = "原社團留任" 
        self.rank = 999 

class Club:
    def __init__(self, name, initial_vacancy):
        self.name = str(name).strip()
        self.initial_vacancy = int(initial_vacancy)
        self.current_students = []
        self.capacity = 0 

def process_allocation(students_df, clubs_df):
    # Setup
    clubs = {}
    logs = []
    
    # 1. Clubs from config
    for idx, row in clubs_df.iterrows():
        c_name = str(row['社團名稱']).strip()
        vac = row['目前缺額']
        clubs[c_name] = Club(c_name, vac)
        
    # 2. Auto-discover
    all_original = students_df['原社團'].dropna().astype(str).unique()
    for c_name in all_original:
        c_name = str(c_name).strip()
        if c_name and c_name not in clubs:
            clubs[c_name] = Club(c_name, 0) # Implicit club
            
    # 3. Create Students
    if '填寫時間' in students_df.columns:
         students_df = students_df.sort_values(by="填寫時間")
         
    students = []
    for _, row in students_df.iterrows():
        s = Student(row, [], [], False, False)
        students.append(s)
        if s.original_club in clubs:
            clubs[s.original_club].current_students.append(s.id)
            
    # 4. Capacity
    for c in clubs.values():
        c.capacity = c.initial_vacancy + len(c.current_students)
        print(f"Club {c.name}: InitVac={c.initial_vacancy}, InitUsers={len(c.current_students)}, Cap={c.capacity}")
        
    # Logic
    changed = True
    round_count = 0
    while changed and round_count < 10:
        changed = False
        round_count += 1
        print(f"\n--- Round {round_count} ---")
        
        for s in students:
            for i, p_club_name in enumerate(s.prefs):
                if i >= s.rank: continue
                if p_club_name not in clubs: continue
                
                target = clubs[p_club_name]
                
                # Check occupancy
                occupancy = len(target.current_students)
                print(f" checking {s.name} -> {target.name} (Occ: {occupancy}/{target.capacity})")
                
                if occupancy < target.capacity:
                    # Move
                    old = s.current_assigned
                    if old in clubs:
                        clubs[old].current_students.remove(s.id)
                    target.current_students.append(s.id)
                    s.current_assigned = p_club_name
                    s.rank = i
                    s.status = "Success"
                    logs.append(f"{s.name} moved to {p_club_name}")
                    print(f"  MOVED! {s.name} from {old} to {p_club_name}")
                    changed = True
                    break
                    
    return students

# Test Data
def run_test():
    # Comic Club (0 Vacancy originally, implicit). Basketball (1 Vacancy).
    # S1: In 'None', Wants 'Comic'.
    # S2: In 'Comic', Wants 'Basket'.
    
    # Expected: 
    # S2 moves to Basket (Basket has 1 spot). Comic frees up 1 spot (0->1).
    # S1 moves to Comic in next pass (or same pass if S1 comes AFTER S2).
    # IF S1 comes BEFORE S2:
    # Round 1: S1 checks Comic. Full. Fails. S2 checks Basket. Moves. Comic open.
    # Round 2: S1 checks Comic. Open. Moves.
    
    clubs_data = {
        '社團名稱': ['Basketball'],
        '目前缺額': [1]
    }
    clubs_df = pd.DataFrame(clubs_data)
    
    # S1 is EARLIER (10:00) than S2 (10:01)
    students_data = [
        {'學號': '101', '姓名': 'S1', '班級': '101', '填寫時間': '2023-01-01 10:00', '原社團': 'None', '志願1': 'Comic'},
        {'學號': '102', '姓名': 'S2', '班級': '101', '填寫時間': '2023-01-01 10:01', '原社團': 'Comic', '志願1': 'Basketball'}
    ]
    students_df = pd.DataFrame(students_data)
    
    print("Running Logic Test...")
    final_students = process_allocation(students_df, clubs_df)
    
    for s in final_students:
        print(f"Student {s.name}: {s.current_assigned}")

if __name__ == "__main__":
    run_test()
