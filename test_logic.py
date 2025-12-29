import pandas as pd

def simulate_allocation(students_data, clubs_data):
    # Re-implement the key logic from app.py for testing
    club_vacancies = clubs_data.copy()
    
    students = []
    for s_in in students_data:
        students.append({
            'id': s_in['id'],
            'name': s_in['name'],
            'original_club': s_in['original_club'],
            'prefs': s_in['prefs'],
            'current_club': s_in['original_club'],
            'rank': 999
        })
        
    iteration = 0
    max_iterations = 20
    logs = []
    
    while iteration < max_iterations:
        changed = False
        iteration += 1
        logs.append(f"Iteration {iteration}")
        
        for s in students:
            # Check prefs better than current
            current_rank_index = s['rank'] if s['rank'] != 999 else len(s['prefs'])
            
            for i in range(current_rank_index):
                wanted = s['prefs'][i]
                if wanted in club_vacancies and club_vacancies[wanted] > 0:
                    old = s['current_club']
                    new = wanted
                    
                    club_vacancies[new] -= 1
                    if old in club_vacancies:
                        club_vacancies[old] += 1
                        
                    s['current_club'] = new
                    s['rank'] = i
                    changed = True
                    logs.append(f"Moved {s['name']} from {old} to {new}")
                    break
        if not changed:
            break
            
    return students, club_vacancies, logs

# Scenario: Chain Reaction
# U1 (in A) -> Wants B
# U2 (in C) -> Wants A
# U3 (in D) -> Wants C
# B has 1 spot. A, C have 0.
students_input = [
    {'id': 2, 'name': 'U2', 'original_club': 'C', 'prefs': ['A']}, # Time 2 (Earlier)
    {'id': 3, 'name': 'U3', 'original_club': 'D', 'prefs': ['C']}, # Time 3
    {'id': 1, 'name': 'U1', 'original_club': 'A', 'prefs': ['B']}, # Time 1 (Sorted later? No, usually sorted by time. Let's say U1 is Late)
]
# Wait, let's sort by time properly. 
# Case: U2 (Time 1) -> Wants A. U3 (Time 2) -> Wants C. U1 (Time 3) -> Wants B.
# B has 1. A=0, C=0.
# Pass 1:
# U2 wants A. Full.
# U3 wants C. Full.
# U1 wants B. Open -> Moves! A opens.
# Pass 2:
# U2 wants A. Open! Moves -> C opens.
# U3 wants C. Open! Moves.
# Pass 3: Stable.

students_input = [
    {'id': 2, 'name': 'U2', 'original_club': 'C', 'prefs': ['A']},
    {'id': 3, 'name': 'U3', 'original_club': 'D', 'prefs': ['C']},
    {'id': 1, 'name': 'U1', 'original_club': 'A', 'prefs': ['B']},
]
# Clubs
clubs_input = {'A': 0, 'B': 1, 'C': 0, 'D': 0}

final_students, final_clubs, logs = simulate_allocation(students_input, clubs_input)

print("Logs:")
for l in logs:
    print(l)

print("\nFinal State:")
for s in final_students:
    print(f"{s['name']}: {s['current_club']}")
