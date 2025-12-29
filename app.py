import streamlit as st
import pandas as pd
import io

# 設定頁面配置
st.set_page_config(page_title="學生轉社系統", layout="wide")

def process_allocation(students_df, clubs_df, h1_forbidden=[], h2_forbidden=[]):
    """
    執行轉社分發邏輯
    students_df: 包含 [學號, 姓名, 班級, 填寫時間, 原社團, 志願1..10]
    clubs_df: 包含 [社團名稱, 目前缺額] (Index: 社團名稱)
    h1_forbidden: 高一禁止轉入的社團列表
    h2_forbidden: 高二禁止轉入的社團列表
    """
    
    # 1. 初始化資料
    # 建立社團缺額字典 (使用 dict 提升效能，並追蹤狀態)
    club_vacancies = clubs_df['目前缺額'].to_dict()
    
    # 學生列表，依照填寫時間排序 (假設輸入時已經 sorted，或在此 sort)
    # 確保 '填寫時間' 格式正確，若無法 parsed 則可能需要 error handling，這裡假設已正確
    if '填寫時間' in students_df.columns:
        try:
            students_df['填寫時間'] = pd.to_datetime(students_df['填寫時間'])
            students_df = students_df.sort_values(by='填寫時間')
        except:
            st.warning("填寫時間格式無法解析，將使用原始順序進行分發。")
            
    # 建立學生狀態物件列表
    students = []
    for idx, row in students_df.iterrows():
        # --- 判斷年級 ---
        grade = None
        try:
            cls_str = str(row['班級']).strip()
            # 假設班級格式可能為 "101", "205" 或 "101班" 等，嘗試提取數字
            # 這裡簡化處理，假設前三碼為數字或整體可轉為數字
            cls_num = int(''.join(filter(str.isdigit, cls_str))[:3])
            
            if 101 <= cls_num <= 115:
                grade = 1
            elif 201 <= cls_num <= 215:
                grade = 2
        except:
            pass # 無法判斷年級則視為無限制

        forbidden_clubs = set()
        if grade == 1:
            forbidden_clubs = set(h1_forbidden)
        elif grade == 2:
            forbidden_clubs = set(h2_forbidden)

        prefs = []
        for i in range(1, 11):
            col_name = f'志願{i}'
            if col_name in row and pd.notna(row[col_name]):
                p = str(row[col_name]).strip()
                if p: # 排除空字串
                    # --- 檢查限制 ---
                    if p in forbidden_clubs:
                        # 該社團對此年級禁止轉入，直接忽略（從等待清單刪除）
                        continue
                    prefs.append(p)
        
        students.append({
            'id': row['學號'],
            'name': row['姓名'],
            'class': row['班級'],
            'original_club': str(row['原社團']).strip() if pd.notna(row['原社團']) else "",
            'prefs': prefs,
            'current_club': str(row['原社團']).strip() if pd.notna(row['原社團']) else "", # 初始狀態在原社團
            'status': '原社團', # 狀態標記: 原社團, 轉社成功, 志願落空(維持原社團)
            'rank': 999, # 當前錄取的志願序 (999 代表原社團/未錄取)
            'grade': grade
        })

    # 2. 核心分發迴圈 (Ripple Effect / Chain Reaction)
    # 持續掃描所有學生，直到沒有任何變動發生
    iteration = 0
    max_iterations = 1000 # 防止無窮迴圈
    
    while iteration < max_iterations:
        changed = False
        iteration += 1
        
        for s in students:
            # 嘗試提升志願
            # 檢查比 '當前錄取順位' 更前面的志願
            # 如果 s.rank 是 999，檢查 0..len(prefs)
            # 如果 s.rank 是 2 (已錄取志願3，也就是 index 2)，檢查 0..1
            
            current_rank_index = s['rank'] if s['rank'] != 999 else len(s['prefs'])
            
            # 從第一志願開始尋找
            for i in range(current_rank_index):
                wanted_club = s['prefs'][i]
                
                # 檢查該社團是否存在於系統中
                if wanted_club not in club_vacancies:
                    continue # 社團名稱對不上，跳過
                
                # 檢查是否有缺額
                if club_vacancies[wanted_club] > 0:
                    # == 發生移動 ==
                    old_club = s['current_club']
                    new_club = wanted_club
                    
                    # 1. 扣除新社團名額
                    club_vacancies[new_club] -= 1
                    
                    # 2. 釋出舊社團名額 (如果舊社團在我們的管理清單中)
                    if old_club in club_vacancies:
                        club_vacancies[old_club] += 1
                        
                    # 3. 更新學生狀態
                    s['current_club'] = new_club
                    s['rank'] = i # 更新為第 i+1 志願 (0-based index)
                    s['status'] = f'轉入志願{i+1}'
                    
                    changed = True
                    # 該學生本次移動完成，跳出志願檢查迴圈，但在大迴圈中會因為 changed=True 再次被檢查是否能更好
                    break 
        
        if not changed:
            break

    # 3. 交換演算法 (Post-Optimization: Pairwise Exchange)
    # 檢查是否有兩人互換後都能提升(或持平)志願序的情況
    # 簡單實作：雙人互換
    if True: # 可做為選項開關
        exchanged = True
        while exchanged:
            exchanged = False
            for i in range(len(students)):
                for j in range(i + 1, len(students)):
                    s1 = students[i]
                    s2 = students[j]
                    
                    # S1 想要 S2 的社團 (且比 S1 現在的更好)
                    s1_wants_s2 = False
                    s1_benefit = -1
                    if s2['current_club'] in s1['prefs']:
                        idx = s1['prefs'].index(s2['current_club'])
                        if idx < ((s1['rank'] if s1['rank'] != 999 else 999)):
                            s1_wants_s2 = True
                            s1_benefit = idx
                    
                    # S2 想要 S1 的社團 (且比 S2 現在的更好)
                    s2_wants_s1 = False
                    s2_benefit = -1
                    if s1['current_club'] in s2['prefs']:
                        idx = s2['prefs'].index(s1['current_club'])
                        if idx < ((s2['rank'] if s2['rank'] != 999 else 999)):
                            s2_wants_s1 = True
                            s2_benefit = idx
                            
                    # 執行交換
                    if s1_wants_s2 and s2_wants_s1:
                        c1 = s1['current_club']
                        c2 = s2['current_club']
                        
                        s1['current_club'] = c2
                        s1['rank'] = s1_benefit
                        s1['status'] = f'交換至志願{s1_benefit+1}'
                        
                        s2['current_club'] = c1
                        s2['rank'] = s2_benefit
                        s2['status'] = f'交換至志願{s2_benefit+1}'
                        
                        exchanged = True
                        # print(f"Swapped {s1['name']} and {s2['name']}")

    # 4. 整理結果
    results = []
    for s in students:
        res = {
            '學號': s['id'],
            '姓名': s['name'],
            '班級': s['class'],
            '原社團': s['original_club'],
            '分發結果': s['current_club'],
            '錄取志願序': s['rank'] + 1 if s['rank'] != 999 else '未轉社',
            '狀態': '成功' if s['current_club'] != s['original_club'] else '未變更'
        }
        results.append(res)
        
    return pd.DataFrame(results), pd.DataFrame(list(club_vacancies.items()), columns=['社團名稱', '剩餘缺額'])

# === UI 部分 ===
st.title("🔀 學生轉社系統 (Student Club Transfer)")
st.markdown("---")

# Sidebar
st.sidebar.header("1. 上傳資料")

# 學生資料上傳
uploaded_students = st.sidebar.file_uploader("上傳學生志願 (Excel)", type=['xlsx'])
students_df = None
if uploaded_students:
    try:
        students_df = pd.read_excel(uploaded_students)
        
        # 清除欄位名稱前後空白 (避免使用者不小心多打空白)
        students_df.columns = students_df.columns.str.strip()
        
        # 基本欄位檢查
        req_cols = ['學號', '班級', '填寫時間', '原社團'] # 姓名不再是必填
        missing_cols = [c for c in req_cols if c not in students_df.columns]
        
        if missing_cols:
            st.sidebar.error(f"Excel 缺少必要欄位: {missing_cols}")
            st.sidebar.warning(f"目前讀取到的欄位: {list(students_df.columns)}")
            st.sidebar.info("請檢查 Excel 標題列是否包含上述欄位，且沒有多餘的空白或錯字。")
            students_df = None
        else:
            # 檢查學號是否重複
            if students_df['學號'].duplicated().any():
                dup_ids = students_df[students_df['學號'].duplicated()]['學號'].unique()
                st.sidebar.error(f"發現重複學號，無法處理: {list(dup_ids)}")
                st.sidebar.warning("請修正 Excel 中的重複學號後重新上傳。")
                students_df = None
            else:
                # 若無姓名欄位，自動填補 (為了顯示方便)
                if '姓名' not in students_df.columns:
                    students_df['姓名'] = ""
                
                # 再次確保學號轉為字串比較安全
                students_df['學號'] = students_df['學號'].astype(str).str.strip()

                st.sidebar.success(f"已讀取 {len(students_df)} 名學生資料")
    except Exception as e:
        st.sidebar.error(f"讀取錯誤: {e}")

# 準備所有社團列表供選單使用
all_clubs_found = set()
if students_df is not None:
    if '原社團' in students_df.columns:
        all_clubs_found.update(students_df['原社團'].dropna().unique())
    for i in range(1, 11):
        if f'志願{i}' in students_df.columns:
            all_clubs_found.update(students_df[f'志願{i}'].dropna().astype(str).unique())
    all_clubs_found = {c for c in all_clubs_found if c and str(c).strip()}

# 社團缺額設定
st.sidebar.header("2. 社團缺額設定")
quota_mode = st.sidebar.radio("缺額來源", ["手動輸入/修改", "上傳 Excel"])

clubs_df = pd.DataFrame(columns=['社團名稱', '目前缺額'])

if quota_mode == "上傳 Excel":
    uploaded_clubs = st.sidebar.file_uploader("上傳社團缺額 (Excel)", type=['xlsx'])
    if uploaded_clubs:
        try:
            d = pd.read_excel(uploaded_clubs)
            if '社團名稱' in d.columns and '目前缺額' in d.columns:
                clubs_df = d[['社團名稱', '目前缺額']]
                st.sidebar.success(f"已讀取 {len(clubs_df)} 個社團設定")
            else:
                st.sidebar.error("Excel 需包含 [社團名稱, 目前缺額]")
        except Exception as e:
            st.sidebar.error(f"讀取錯誤: {e}")
else:
    st.sidebar.info("請在右側主畫面表格輸入社團缺額")
    
    if students_df is not None:
        # 如果 session state 還沒存，就初始化
        if 'editor_clubs' not in st.session_state:
            init_data = [{'社團名稱': c, '目前缺額': 0} for c in sorted(list(all_clubs_found))]
            st.session_state['editor_clubs'] = pd.DataFrame(init_data)
    else:
        if 'editor_clubs' not in st.session_state:
             st.session_state['editor_clubs'] = pd.DataFrame([{'社團名稱': '範例社團', '目前缺額': 5}])

# 限制設定
st.sidebar.header("3. 限制設定")
st.sidebar.caption("設定特定年級無法轉入的社團 (將自動略過該志願)")
available_clubs_list = sorted(list(all_clubs_found)) if all_clubs_found else []

h1_forbidden = st.sidebar.multiselect(
    "❌ 高一 (101-115) 不能轉入的社團",
    options=available_clubs_list
)

h2_forbidden = st.sidebar.multiselect(
    "❌ 高二 (201-215) 不能轉入的社團",
    options=available_clubs_list
)

# Main Area
if students_df is not None:
    with st.expander("📄 檢視已上傳學生資料 (前 5 筆)", expanded=True):
        st.dataframe(students_df.head())
        st.caption(f"共 {len(students_df)} 筆資料。")

c1, c2 = st.columns([2, 1])

with c1:
    st.subheader("社團缺額管理")
    if quota_mode == "手動輸入/修改":
        if 'editor_clubs' in st.session_state:
            edited_clubs = st.data_editor(st.session_state['editor_clubs'], num_rows="dynamic", key="data_editor")
            clubs_df = edited_clubs
    else:
        st.dataframe(clubs_df)

with c2:
    st.subheader("操作")
    start_btn = st.button("🚀 開始分發", type="primary", disabled=(students_df is None or clubs_df.empty))

# Logic Execution
if start_btn and students_df is not None and not clubs_df.empty:
    with st.spinner("正在進行演算法分發..."):
        # 確保 clubs_df 格式正確 (如果是 data_editor 回傳的，可能型別要轉)
        clubs_df['目前缺額'] = pd.to_numeric(clubs_df['目前缺額'], errors='coerce').fillna(0).astype(int)
        
        result_df, vacancies_df = process_allocation(students_df, clubs_df, h1_forbidden=h1_forbidden, h2_forbidden=h2_forbidden)
        
        st.session_state['result_df'] = result_df
        st.session_state['final_vacancies'] = vacancies_df
        st.success("分發完成！")

# Results Display
if 'result_df' in st.session_state:
    st.markdown("---")
    st.header("分發結果")
    
    res = st.session_state['result_df']
    vac = st.session_state['final_vacancies']
    
    tab1, tab2, tab3 = st.tabs(["📋 成功名單", "⚠️ 未變更/失敗名單", "📊 社團餘額"])
    
    with tab1:
        success_list = res[res['狀態'] == '成功']
        st.info(f"共有 {len(success_list)} 人成功轉社")
        st.dataframe(success_list)
        
    with tab2:
        fail_list = res[res['狀態'] != '成功']
        st.warning(f"共有 {len(fail_list)} 人維持原社團 (或未填寫有效志願)")
        st.dataframe(fail_list)
        
    with tab3:
        st.dataframe(vac)

    # Download
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        res.to_excel(writer, sheet_name='分發結果', index=False)
        vac.to_excel(writer, sheet_name='剩餘缺額', index=False)
        success_list.to_excel(writer, sheet_name='成功名單', index=False)
    
    st.download_button(
        label="📥 下載完整結果 Excel",
        data=output.getvalue(),
        file_name="轉社結果.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

