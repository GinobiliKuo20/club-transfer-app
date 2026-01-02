import streamlit as st
import pandas as pd
import io

# 設定頁面配置
st.set_page_config(page_title="學生轉社系統", layout="wide")

# --- 1. 資料模型類別 (Class Definitions) ---
class Student:
    def __init__(self, data, h1_forbidden, h2_forbidden, h1_ban_all, h2_ban_all):
        self.id = str(data['學號']).strip()
        self.name = data.get('姓名', '')
        self.original_club = str(data.get('原社團', '')).strip()
        self.class_str = str(data.get('班級', '')).strip() # Store original class string
        
        # 處理班級與年級判斷
        self.grade = None
        try:
            cls_num = int(''.join(filter(str.isdigit, self.class_str))[:3])
            if 101 <= cls_num <= 115:
                self.grade = 1
            elif 201 <= cls_num <= 215:
                self.grade = 2
        except:
            pass
            
        # 處理志願 (套用限制)
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

        self.current_assigned = self.original_club # 初始狀態在原社團
        self.status = "原社團留任" 
        self.rank = 999 # 999代表未錄取任何志願，0代表第一志願

# -- Skipping Club definition as it is fine --

# ... inside process_allocation ...
# (We need to make sure process_allocation uses handling logic, but we can't redefine it fully here easily without context)
# Instead, since I already replaced process_allocation in previous step, I will target the areas that need fix.

# Update UI section to handle 4 return values
# Finding the line where process_allocation is called.

# First, let's fix the Student class definition at the top


class Club:
    def __init__(self, name, initial_vacancy):
        self.name = str(name).strip()
        self.initial_vacancy = int(initial_vacancy)
        self.current_students = [] # 存放目前在此社團的學生ID
        self.capacity = 0 # 將在初始化時計算: 初始缺額 + 初始成員數

def process_allocation(students_df, clubs_df, h1_forbidden=[], h2_forbidden=[], h1_ban_all=False, h2_ban_all=False):
    """
    執行轉社分發邏輯 (Object-Oriented Version)
    包含: 動態遞補 (Ripple Effect) + 最佳化交換 (Swapping) + 完整過程紀錄
    """
    
    # --- A. 初始化環境 ---
    students = []
    clubs = {}
    logs = []
    swap_logs = []
    
    # 1. 建立社團物件 (從缺額設定)
    # 確保社團名稱唯一
    if '社團名稱' in clubs_df.columns:
        # 加總重複的社團缺額 (防呆)
        grouped_clubs = clubs_df.groupby('社團名稱')['目前缺額'].sum()
        for c_name, vac in grouped_clubs.items():
            clubs[str(c_name).strip()] = Club(c_name, vac)
    else:
        # Fallback
        for c_name, vac in clubs_df['目前缺額'].items():
            clubs[str(c_name).strip()] = Club(c_name, vac)

    # 2. 自動發現隱藏社團 (Critical Fix: 確保所有原社團都被追蹤)
    # 掃描學生的原社團，若不在 clubs 中，則新增一個 initial_vacancy=0 的社團
    all_original = students_df['原社團'].dropna().astype(str).unique()
    for c_name in all_original:
        c_name = str(c_name).strip()
        if c_name and c_name not in clubs:
            clubs[c_name] = Club(c_name, 0)
            # print(f"Auto-discovered club: {c_name}")

    # 3. 建立學生物件並放入原社團
    # 確保依照時間排序
    if '填寫時間' in students_df.columns:
        students_df['填寫時間'] = pd.to_datetime(students_df['填寫時間'], errors='coerce')
        students_df = students_df.sort_values(by="填寫時間")
        
    for _, row in students_df.iterrows():
        s = Student(row, h1_forbidden, h2_forbidden, h1_ban_all, h2_ban_all)
        students.append(s)
        
        # 將學生放入原社團名單 (如果原社團有效)
        if s.original_club in clubs:
            clubs[s.original_club].current_students.append(s.id)
            
    # 4. 計算社團總容量 (Capacity)
    # 容量 = 該社團初始缺額 + 該社團的初始原有學生數
    for c in clubs.values():
        c.capacity = c.initial_vacancy + len(c.current_students)
    
    # --- B. 動態連鎖分發 (Chain Reaction) ---
    changed = True
    iteration = 0
    max_iterations = len(students) * 10 + 2000 # 增加上限，因為每次只移動一人就重來
    
    status_container = st.empty()
    bar = st.progress(0)
    
    while changed and iteration < max_iterations:
        changed = False
        iteration += 1
        
        # UI 更新頻率控制 (每 5 輪更新一次，避免拖慢效能)
        if iteration % 5 == 0:
            status_container.text(f"正在進行第 {iteration} 輪動態分發 (優先權掃描)...")
            bar.progress(min(iteration % 100, 100))
        
        for s in students:
            # 檢查每個志願
            for i, p_club_name in enumerate(s.prefs):
                
                # 如果這個志願比目前的結果更差或一樣，跳過
                if i >= s.rank:
                    continue
                
                # 檢查社團是否存在
                if p_club_name not in clubs:
                    continue
                
                target_club = clubs[p_club_name]
                
                # 檢查是否有空位 (目前人數 < 總容量)
                # 總容量 = 初始願意收的人 + 原本就在裡面的人
                # 只要有人離開 (remove)，len(current) 就會減少，名額就釋出
                if len(target_club.current_students) < target_club.capacity:
                    # == 移動發生 ==
                    old_club_name = s.current_assigned
                    
                    # 1. 從舊社團移除
                    if old_club_name in clubs:
                        clubs[old_club_name].current_students.remove(s.id)
                    
                    # 2. 加入新社團
                    target_club.current_students.append(s.id)
                    
                    # 3. 更新狀態
                    s.current_assigned = p_club_name
                    s.rank = i
                    s.status = "成功"
                    
                    logs.append(f"#{iteration}: {s.name} ({s.id}) 從 [{old_club_name}] 轉入 [{p_club_name}] (志願{i+1})")
                    changed = True
                    break # 跳出志願迴圈
            
            if changed:
                break # !!! 關鍵修正：跳出學生迴圈，重新從第 1 位學生開始掃描 (Strict Priority)

    status_container.text("進行交換最佳化...")
    
    # --- C. 最佳化交換 (Post-Optimization) ---
    swapped = True
    while swapped:
        swapped = False
        for s1 in students:
            if s1.rank == 0: continue # 已滿足第一志願
            
            for s2 in students:
                if s1.id == s2.id: continue
                if s2.rank == 0: continue
                
                c1 = s1.current_assigned
                c2 = s2.current_assigned
                
                if c1 == c2: continue
                
                # 檢查 s1 是否想去 c2 且更好
                if c2 in s1.prefs:
                    r1 = s1.prefs.index(c2)
                    if r1 < s1.rank:
                        # 檢查 s2 是否想去 c1 且更好
                        if c1 in s2.prefs:
                            r2 = s2.prefs.index(c1)
                            if r2 < s2.rank:
                                # == 執行交換 ==
                                s1.current_assigned = c2
                                s1.rank = r1
                                
                                s2.current_assigned = c1
                                s2.rank = r2
                                
                                # 更新社團名單 (這裡其實不影響容量，只是交換人頭)
                                if c1 in clubs:
                                    clubs[c1].current_students.remove(s1.id)
                                    clubs[c1].current_students.append(s2.id)
                                if c2 in clubs:
                                    clubs[c2].current_students.remove(s2.id)
                                    clubs[c2].current_students.append(s1.id)
                                    
                                swap_logs.append(f"{s1.name} <-> {s2.name} : {c1} <-> {c2}")
                                swapped = True

    status_container.empty()
    bar.empty()
    
    # --- D. 整理結果 ---
    results = []
    for s in students:
        results.append({
            '學號': s.id,
            '姓名': s.name,
            '班級': s.class_str,
            '原社團': s.original_club,
            '分發結果': s.current_assigned,
            '錄取志願序': s.rank + 1 if s.rank != 999 else '未轉社',
            '狀態': '成功' if s.current_assigned != s.original_club else '未變更'
        })
        
    # 計算剩餘缺額
    vac_data = []
    for c in clubs.values():
        remaining = c.capacity - len(c.current_students)
        vac_data.append({'社團名稱': c.name, '剩餘缺額': max(0, remaining)})
        
    return pd.DataFrame(results), pd.DataFrame(vac_data), logs, swap_logs


# === UI 部分 ===
st.title("🔀 學生轉社系統 (Student Club Transfer)")
st.markdown("---")

with st.expander("📖 系統使用說明 (User Guide)", expanded=False):
    st.markdown("""
    ### 1. 準備資料
    請準備一個 Excel 檔案，包含以下欄位（標題需準確）：
    - **必要欄位**：`學號`、`班級`、`原社團`、`填寫時間`
    - **志願欄位**：`志願1`、`志願2` ... `志願10` (可依需求增減)
    - **選填欄位**：`姓名` (若無則顯示空白)

    ### 2. 操作流程
    1. **上傳資料**：在左側欄位上傳您的學生志願 Excel 檔。
    2. **社團缺額設定**：
       - 系統會自動掃描檔案中出現的所有社團。
       - 您可以在中間的「社團缺額管理」表格中手動輸入該社團本次開放的缺額 (Vacancy)。
       - 也可以透過左側上傳「社團缺額 Excel」來整批匯入。
    3. **設定限制 (選填)**：
       - 若要限制特定年級 (高一/高二) 不能轉入某些熱門社團，請在左側勾選或設定。
       - 支援「禁止特定社團」或「完全禁止該年級轉社」。
    4. **開始分發**：
       - 點擊「🚀 開始分發」按鈕。
       - 系統將執行演算法，包含「動態遞補」與「交換最佳化」。
    
    ### 3. 下載結果
    - 分發完成後，下方會顯示成功與失敗名單。
    - 點擊「📥 下載完整結果 Excel」即可取得包含詳細名單、遞補日誌與交換紀錄的報表。
    """)

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

# 整合所有來源的社團名單 (學生資料 + 社團缺額設定)
if '社團名稱' in clubs_df.columns: 
    # 注意: 若是手動輸入模式且尚未存入 clubs_df (例如剛啟動)，可能要看 session_state
    if not clubs_df.empty:
        all_clubs_found.update(clubs_df['社團名稱'].dropna().astype(str).unique())

if 'editor_clubs' in st.session_state and not st.session_state['editor_clubs'].empty:
    all_clubs_found.update(st.session_state['editor_clubs']['社團名稱'].dropna().astype(str).unique())

available_clubs_list = sorted(list(all_clubs_found)) if all_clubs_found else []

st.sidebar.subheader("高一 (101-115)")
h1_ban_all = st.sidebar.checkbox("🚫 禁止高一所有轉社 (完全凍結)", value=False, key="h1_ban_all")
h1_forbidden = []
if not h1_ban_all:
    h1_forbidden = st.sidebar.multiselect(
        "❌ 高一禁止轉入的社團",
        options=available_clubs_list
    )

st.sidebar.subheader("高二 (201-215)")
h2_ban_all = st.sidebar.checkbox("🚫 禁止高二所有轉社 (完全凍結)", value=False, key="h2_ban_all")
h2_forbidden = []
if not h2_ban_all:
    h2_forbidden = st.sidebar.multiselect(
        "❌ 高二禁止轉入的社團",
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
        
        result_df, vacancies_df, logs, swap_logs = process_allocation(
            students_df, 
            clubs_df, 
            h1_forbidden=h1_forbidden, 
            h2_forbidden=h2_forbidden,
            h1_ban_all=h1_ban_all,
            h2_ban_all=h2_ban_all
        )
        
        st.session_state['result_df'] = result_df
        st.session_state['final_vacancies'] = vacancies_df
        st.session_state['logs'] = logs
        st.session_state['swap_logs'] = swap_logs
        
        st.success("分發完成！")

# Results Display
if 'result_df' in st.session_state:
    st.markdown("---")
    st.header("分發結果")
    
    res = st.session_state['result_df']
    vac = st.session_state['final_vacancies']
    logs = st.session_state.get('logs', [])
    swap_logs = st.session_state.get('swap_logs', [])
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 成功名單", "⚠️ 未變更/失敗名單", "📊 社團餘額", "📜 遞補日誌", "🔄 交換紀錄"])
    
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
        
    with tab4:
        st.caption("顯示名額釋出後的動態遞補過程")
        st.text_area("遞補過程", "\n".join(logs), height=300)
        
    with tab5:
        if swap_logs:
            st.success(f"系統自動執行了 {len(swap_logs)} 組交換")
            st.text_area("交換紀錄", "\n".join(swap_logs), height=300)
        else:
            st.info("本次無可進行的最佳化交換")

    # Download
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        res.to_excel(writer, sheet_name='分發結果', index=False)
        vac.to_excel(writer, sheet_name='剩餘缺額', index=False)
        success_list.to_excel(writer, sheet_name='成功名單', index=False)
        if logs:
             pd.DataFrame({'Log': logs}).to_excel(writer, sheet_name='遞補日誌', index=False)
        if swap_logs:
             pd.DataFrame({'Swap': swap_logs}).to_excel(writer, sheet_name='交換紀錄', index=False)
    
    st.download_button(
        label="📥 下載完整結果 Excel",
        data=output.getvalue(),
        file_name="轉社結果.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

