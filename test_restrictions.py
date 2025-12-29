import pandas as pd
from app import process_allocation

def test_restrictions():
    print("Testing Grade Restrictions Logic...")

    # Mock Data
    data = {
        '學號': ['S001', 'S002', 'S003', 'S004'],
        '姓名': ['Alice', 'Bob', 'Charlie', 'Dave'],
        '班級': ['101', '201', '301', '115'], # G1, G2, None, G1
        '原社團': ['None', 'None', 'None', 'None'],
        '填寫時間': pd.to_datetime(['2023-01-01 10:00', '2023-01-01 10:01', '2023-01-01 10:02', '2023-01-01 10:03']),
        '志願1': ['ClubA', 'ClubB', 'ClubA', 'ClubB'],
        '志願2': ['ClubB', 'ClubA', 'ClubB', 'ClubA']
    }
    students_df = pd.DataFrame(data)

    # Mock Clubs: ample space
    clubs_data = {
        '社團名稱': ['ClubA', 'ClubB'],
        '目前缺額': [10, 10]
    }
    clubs_df = pd.DataFrame(clubs_data)

    # Scenarios:
    # 1. H1 cannot join ClubA.
    # 2. H2 cannot join ClubB.
    
    h1_forbidden = ['ClubA']
    h2_forbidden = ['ClubB']

    result_df, vac_df = process_allocation(students_df, clubs_df, h1_forbidden, h2_forbidden)

    print("\n--- Result DataFrame ---")
    print(result_df[['學號', '班級', '分發結果', '錄取志願序', '狀態']])

    # Verify S001 (Class 101, Grade 1)
    # Wanted ClubA (Forbidden) -> ClubB (Allowed)
    s001 = result_df[result_df['學號'] == 'S001'].iloc[0]
    assert s001['分發結果'] == 'ClubB', f"S001 should get ClubB, got {s001['分發結果']}"
    assert s001['錄取志願序'] == 2, f"S001 should get Rank 2, got {s001['錄取志願序']}"

    # Verify S002 (Class 201, Grade 2)
    # Wanted ClubB (Forbidden) -> ClubA (Allowed)
    s002 = result_df[result_df['學號'] == 'S002'].iloc[0]
    assert s002['分發結果'] == 'ClubA', f"S002 should get ClubA, got {s002['分發結果']}"

    # Verify S003 (Class 301, Grade None)
    # Wanted ClubA (Restricted for H1, but S003 is not H1) -> ClubA
    s003 = result_df[result_df['學號'] == 'S003'].iloc[0]
    assert s003['分發結果'] == 'ClubA', f"S003 should get ClubA (No restriction), got {s003['分發結果']}"

    # Verify S004 (Class 115, Grade 1)
    # Wanted ClubB (Allowed) -> ClubB
    s004 = result_df[result_df['學號'] == 'S004'].iloc[0]
    assert s004['分發結果'] == 'ClubB', f"S004 should get ClubB, got {s004['分發結果']}"

    print("\n✅ All restriction tests passed!")

if __name__ == "__main__":
    test_restrictions()
