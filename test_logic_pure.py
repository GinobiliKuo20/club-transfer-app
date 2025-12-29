def simulate_allocation(students_data, clubs_data):
    club_vacancies = clubs_data.copy()
    
    students = []
    for s_in in students_data:
        students.append({
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

students_input = [
    {'name': 'U2', 'original_club': 'C', 'prefs': ['A']},
    {'name': 'U3', 'original_club': 'D', 'prefs': ['C']},
    {'name': 'U1', 'original_club': 'A', 'prefs': ['B']},
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
