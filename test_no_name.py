
import pandas as pd
from app import process_allocation

def test_no_name():
    print("Testing No Name Column Logic...")

    # Mock Data without '姓名'
    data = {
        '學號': ['S001', 'S002'],
        '班級': ['101', '201'],
        '原社團': ['None', 'None'],
        '填寫時間': pd.to_datetime(['2023-01-01 10:00', '2023-01-01 10:01']),
        '志願1': ['ClubA', 'ClubB'],
        '志願2': ['ClubB', 'ClubA']
    }
    students_df = pd.DataFrame(data)
    
    # Simulate the preprocessing step done in app.py
    if '姓名' not in students_df.columns:
        students_df['姓名'] = ""

    # Mock Clubs
    clubs_data = {
        '社團名稱': ['ClubA', 'ClubB'],
        '目前缺額': [10, 10]
    }
    clubs_df = pd.DataFrame(clubs_data)

    try:
        result_df, vac_df = process_allocation(students_df, clubs_df)
        print("✅ process_allocation ran successfully without Name column (after preprocessing)")
        print(result_df.head())
    except Exception as e:
        print(f"❌ Failed: {e}")

if __name__ == "__main__":
    test_no_name()
