import pandas as pd
import numpy as np
import re

report_lines = []

def log_print(title, content):
    print(title)
    print(content)
    report_lines.append(title)
    report_lines.append(str(content))
    report_lines.append("\n")

df = pd.read_csv('structed_data.csv', encoding='utf-8')


# ===== 1.岗位类型 =====

# 关键词词库
ROLE_DICT = {
    "DA": [
        "数据アナリスト", "データ分析", "データ集計", "マーケティングデータ",
        "ビジネスアナリスト", "Business Analyst", "データ解析", "インサイト分析",
        "顧客データ", "アナリティクス", "データ運用" 
    ],
    "DS": [
        "データサイエンティスト", "数理", "AI", "機械学習", 
        "Machine Learning", "LLM", "ゲノム解析", "画像解析", 
        "動作解析", "深層学習", "統計" 
    ],
    "DE": [
        "データエンジニア", "基盤", "構築", "DWH", "ETL", "Databricks",
        "データプラットフォーム", "Data Platform", "データ基盤", 
        "パイプライン", "アナリティクスエンジニア" 
    ],
    "MLE": [
        "機械学習エンジニア", "MLエンジニア", "AIエンジニア", 
        "ML Engineer", "Software Engineer(ML)" 
    ],
    "BI": [
        "BI", "ダッシュボード", "可視化", "Tableau", "Looker", 
        "PowerBI", "レポート作成" 
    ],
    "CONSULTANT": [
        "コンサル", "利活用", "データ活用", "戦略", "DX推進", 
        "マーケティング戦略", "企画", "調査", "リサーチ", "Research",
        "マーケター", "マーケティング担当", "市場開発", "Promotion",
        "プロダクトマネージャー", "事業開発", "PMM", "BizOps", "RevOps" 
    ]
}

# 优先级
PRIORITY = ["DS", "MLE", "DE", "DA", "BI", "CONSULTANT"]

# 分类函数 (优化了大小写匹配)
def classify_role(title):
    if not isinstance(title, str):
        return "OTHER"
    
    # 统一转大写，处理如 "bi" 和 "BI" 的匹配问题
    title_upper = title.upper()
    matched_roles = []

    for role, keywords in ROLE_DICT.items():
        for kw in keywords:
            if kw.upper() in title_upper:
                matched_roles.append(role)
                break

    if not matched_roles:
        return "OTHER"

    # 按优先级返回最高的一个
    for p in PRIORITY:
        if p in matched_roles:
            return p
        
df["Position_Type"] = df["Position"].apply(classify_role)

# ===== 従業員数 分箱 =====
df["従業員数"] = (
    df["従業員数"]
    .astype(str)
    .str.replace(",", "", regex=False)
)

# 转成数值（防止空值或异常）
df["従業員数"] = pd.to_numeric(df["従業員数"], errors="coerce")

# 分箱区间
bins = [0, 100, 500, 1000, 10000, float("inf")]
labels = ["0-100", "100-500", "500-1000", "1000-10000", "10000+"]

# 创建分类列
df["employee_bin"] = pd.cut(
    df["従業員数"],
    bins=bins,
    labels=labels,
    right=False
)

# Power BI 排序辅助列
df["employee_bin_order"] = pd.cut(
    df["従業員数"],
    bins=bins,
    labels=range(len(labels)),
    right=False
)

# 转成整数（可选）
df["employee_bin_order"] = df["employee_bin_order"].astype("Int64")




# ===== 2.在宅情况 =====

# 关键词配置（保持你的逻辑，增强覆盖面）
REMOTE_KW = ["リモート", "在宅", "テレワーク", "フルリモート"]
ALLOW_KW = ["可", "可能", "OK", "利用", "対応", "推奨", "導入", "活用", "併用"]
NEGATIVE_REMOTE = ["不可", "実施しておりません", "対象外", "できません"]
ONSITE_KW = ["出社", "常駐", "対面"]

# 预处理函数
def normalize_text(text):
    if not isinstance(text, str): return ""
    # 显式处理代码1生成的“无匹配”
    if text == "无匹配": return "NONE"
    # 去掉空格和换行，但保留 || 作为逻辑分隔（或者直接去掉也可）
    text = re.sub(r"\s+", "", text)
    return text

# 分类函数（保持判断逻辑，优化匹配深度）
def classify_remote(text):
    text = normalize_text(text)
    
    if text == "NONE" or text == "":
        return "UNKNOWN", -1

    # ---- ① 否定优先（针对远程词的否定） ----
    # 捕捉类似 “在宅不可”、“リモートワークは実施しておりません”
    for r_kw in REMOTE_KW:
        if r_kw in text:
            for n_kw in NEGATIVE_REMOTE:
                if n_kw in text and text.find(r_kw) < text.find(n_kw) < text.find(r_kw) + 10:
                    return "ONSITE", 0

    # ---- ② 强判定：组合命中（你的核心逻辑） ----
    for r_kw in REMOTE_KW:
        if r_kw in text:
            for a_kw in ALLOW_KW:
                if a_kw in text:
                    return "REMOTE", 1

    # ---- ③ 弱判定：补充命中（针对“一部従業員利用可”或“フルリモート”等固定搭配） ----
    # 很多文本里“可”在括号里，上面的逻辑有时会漏掉，这里做一层兜底
    if any(kw in text for kw in ["フルリモート", "リモートワーク制度", "在宅勤務制度"]):
        return "REMOTE", 1

    # ---- ④ 明确 onsite ----
    # 如果前面没匹配到远程许可，且出现了出社关键词
    for kw in ONSITE_KW:
        if kw in text:
            return "ONSITE", 0

    # ---- ⑤ 最后的兜底：含有远程词但无明确许可/否定 ----
    # 只要出现了在宅相关的词，在招聘语境下大概率是支持的，减少 UNKNOWN
    if any(kw in text for kw in REMOTE_KW):
        return "REMOTE", 1

    return "UNKNOWN", -1

# 应用
res = df["在宅可否"].apply(lambda x: pd.Series(classify_remote(x)))
df["remote_flag"] = res[0]
df["remote_score"] = res[1]



# =====3. 年收=====
def extract_salary(salary_text):

    if pd.isna(salary_text) or salary_text == "":
        return np.nan, np.nan, np.nan

    text = str(salary_text).replace(" ", "").replace(",", "")

    # 500万円～900万円
    pattern = r'(\d{3,4})(?:万円|万)?(?:～|-|~)(\d{3,4})(?:万円|万)?'

    match = re.search(pattern, text)

    if match:
        try:
            s_min = int(match.group(1))
            s_max = int(match.group(2))
            s_avg = (s_min + s_max) / 2

            return s_min, s_max, s_avg

        except:
            return np.nan, np.nan, np.nan

    # 单值兜底
    single_pattern = r'(\d{3,4})万円'

    single_match = re.search(single_pattern, text)

    if single_match:
        try:
            s_min = int(single_match.group(1))

            return s_min, np.nan, np.nan

        except:
            pass

    return np.nan, np.nan, np.nan


salary_data = df["給与"].apply(extract_salary)

df[["salary_min", "salary_max", "salary_avg"]] = pd.DataFrame(
    salary_data.tolist(),
    index=df.index
)


for col in ["salary_min", "salary_max", "salary_avg"]:

    df[col] = pd.to_numeric(df[col], errors="coerce")



bins = list(range(0, 2000, 100))

labels = [f"{i}-{i+100}" for i in bins[:-1]]

df["salary_bin"] = pd.cut(
    df["salary_avg"],
    bins=bins,
    labels=labels,
    right=False
)


df["salary_bin_order"] = pd.cut(df["salary_avg"],bins=bins,labels=range(len(labels)),right=False)

df["salary_bin"] = df["salary_bin"].astype(str)

salary_dist_df = (df["salary_bin"].value_counts(dropna=False).sort_index().to_frame(name="count"))

salary_dist_df["ratio"] = (salary_dist_df["count"] / salary_dist_df["count"].sum())






# ===== 4.经验年数 =====
def extract_experience_years_v2(text):
    if pd.isna(text) or text == "" or text == "无匹配":
        return 0
    
    text = str(text)
    
    # 优先提取具体年数
    # 匹配：3年以上、5年以上の実務経験、经验2年 等
    year_match = re.search(r'(\d{1,2})\s*年以上?|経験(\d{1,2})\s*年', text)
    if year_match:
        # 取出匹配到的第一个非空数字组
        val = year_match.group(1) if year_match.group(1) else year_match.group(2)
        return int(val)
    
    # 匹配：社会人年次2年目～5年目 (取最小值)
    genji_match = re.search(r'社会人年次(\d{1,2})年目', text)
    if genji_match:
        return int(genji_match.group(1))

    # 逻辑调整：必须有项目经验但未写年数的设为 1
    # 定义表示“有经验”的关键词
    has_exp_keywords = [
        "経験", "実務", "開発経験", "運用経験", "構築経験", 
        "携わった", "職務での", "スキルをお持ちの方"
    ]
    
    if any(kw in text for kw in has_exp_keywords):
        return 1

    # 彻底没提到的设为 0
    return 0

# 应用清洗
df["experience_years"] = df["必要経験"].apply(extract_experience_years_v2)




# ===== 5.level ===== 

def classify_level(row):
    # 获取 Position 和之前清洗出的经验年数
    position = str(row['Position']).upper()
    exp = row['experience_years']
    
    # MANAGER (管理/领导层)
    # 关键词包含：经理、组长、PM、负责人、管理监督者等
    manager_keywords = [
        "マネージャー", "MANAGER", "リーダー", "LEADER", "PM", "PMO", "PL", "CMO",
        "室長", "課長", "部長", "責任者", "幹部", "管理监督者", "管理職", "パートナー"
    ]
    if any(kw in position for kw in manager_keywords):
        return "manager"

    # SENIOR (资深/专家/上流工程)
    # 关键词包含：资深、专家、首席、架构师、设计、战略、以及 3 年以上经验
    senior_keywords = [
        "リード", "LEAD", "シニア", "SENIOR", "エキスパート", "EXPERT", 
        "設計", "上流", "アーキテクト", "ARCHITECT", "戦略", "エバンジェリスト",
        "プロ採用"
    ]
    if any(kw in position for kw in senior_keywords) or exp >= 3:
        return "senior"

    # JUNIOR (初级/潜力/未开发)
    # 关键词包含：未经验、潜力、研修、第二新卒、或是经验为 0 且不含管理词
    junior_keywords = [
        "未経験", "ポテンシャル", "研修", "第二新卒", "アシスタント", 
        "新卒", "オープンポジション", "OPEN POSITION", "メンバークラス"
    ]
    if any(kw in position for kw in junior_keywords) or exp == 0:
        return "junior"

    #  MID (中坚/中级)
    # 默认分类：有一定实务经验（1-3年），且职位没有明确标注为管理或资深
    return "mid"

# 应用函数
df['level'] = df.apply(classify_level, axis=1)





# ===== 6.要求技能 ===== 

# 建立关键词字典
keywords = [
    "Python", "SQL", "R", "C++", "Java", "MATLAB", "PyTorch", "TensorFlow", "scikit-learn",
    "機械学習", "AI", "データ分析", "データサイエンス", "統計解析", "深層学習", "ディープラーニング",
    "LLM", "生成AI", "自然言語処理", "画像処理", "信号処理",
    "AWS", "Azure", "GCP", "クラウド", "DWH", "ETL", "BIツール", "Tableau", "Power BI",
    "英語", "TOEIC", "ビジネスコミュニケーション", "マーケティング", "要件定義", "設計"
]

# 执行 One-Hot 编码
for word in keywords:
    # 针对英文单词（如 R, AI, SQL），使用 \b 边界符防止误触（如 CRM 里的 R）
    # [a-zA-Z] 结尾或开头的词被视为英文词
    if re.match(r'^[a-zA-Z]+', word) or len(word) <= 2:
        # re.escape(word) 会把 C++ 变成 C\+\+，确保正则能识别加号
        # \b 确保单词前后是空格、标点或换行，而不是其他字母
        pattern = rf'\b{re.escape(word)}\b'
        is_matched = df['必要経験'].str.contains(pattern, case=False, na=False, regex=True)
    else:
        # 针对中文/日文长词，直接匹配即可（regex=False 关闭正则引擎，速度更快且更准）
        is_matched = df['必要経験'].str.contains(word, case=False, na=False, regex=False)
    
    df[f'exp_{word}'] = is_matched.astype(int)


#统计exp技能
# 筛选出所有以 'exp_' 开头的特征列
exp_cols = [f'exp_{word}' for word in keywords]

# 计算各项指标
# .sum() 统计 1 的个数（出现次数）
# .mean() 统计 1 的占比（出现频率，即百分比）
skill_summary_df  = pd.DataFrame({
    'frequency': df[exp_cols].sum(),
    'percentage (%)': (df[exp_cols].mean() * 100).round(2)
})
skill_summary_df  = skill_summary_df .sort_values(by='frequency', ascending=False)






# ===== 7.工作内容 ===== 

# 定义【工作内容】特征字典 (Key 为列名, Value 为匹配词列表)
job_content_dict = {
    # データ基盤
    "job_データ基盤構築": ["データ基盤", "データベース構築", "マスターデータ", "DWH", "ETL"],
    
    # データ分析
    "job_データ加工": ["データクレンジング", "データ整備", "データ加工", "データマネジメント"],
    "job_統計解析": ["統計解析", "傾向集計", "定量分析", "定性分析", "インサイト"],
    "job_アルゴリズム": ["アルゴリズム", "予測モデル", "予兆保全", "機械学習", "AI解析"],
    "job_可視化": ["ビジュアライズ", "レポーティング", "ダッシュボード", "可視化", "BI"],

    # マーケティング
    "job_市場分析": ["市場分析", "競合分析", "市場調査", "調査研究", "マーケティング"],
    "job_CRM": ["CRM", "LTV", "リードナーチャリング"],
    "job_营销": ["ブランディング", "プロモーション", "広告", "商品企画"],
    
    # 業務向上
    "job_戦略立案": ["戦略立案", "グランドデザイン", "事業成長", "中長期計画"],
    "job_課題解決": ["課題解決", "変革", "コンサルティング", "提案", "ソリューション"],
    "job_KPI": ["KPI設計", "モニタリング", "PDCA", "効果検証", "数値管理"],
    
    # DX化とシステム開発
    "job_DX推进": ["DX", "デジタルトランスフォーメーション", "デジタル化", "IT戦略"],
    "job_IoT": ["IoT", "センサー", "遠隔監視", "産業機器", "稼働データ"],
    "job_システム開発": ["要件定義", "システム開発", "インフラ"],
    
}

# 执行独热编码函数
def apply_one_hot(text, keywords):
    if pd.isna(text):
        return 0
    # 只要匹配到列表中的任何一个词，就返回 1
    for word in keywords:
        # 使用 regex=False 提高速度
        if word in str(text):
            return 1
    return 0

# 循环生成新列
for col_name, keywords in job_content_dict.items():
    # 对【仕事内容】列应用匹配逻辑
    df[col_name] = df['仕事内容'].apply(lambda x: apply_one_hot(x, keywords))


#统计job要求
# 筛选出所有以 'job_' 开头的特征列
job_cols = [col for col in df.columns if col.startswith('job_')]

# 计算各项指标
# .sum() 统计 1 的个数（出现次数）
# .mean() 统计 1 的占比（出现频率，即百分比）
job_summary_df = pd.DataFrame({
    'frequency': df[job_cols].sum(),
    'percentage (%)': (df[job_cols].mean() * 100).round(2)
})
job_summary_df = job_summary_df.sort_values(by='frequency', ascending=False)


#=========print=========
log_print("\n=== Employee Size Distribution ===",df["employee_bin"].value_counts().sort_index())

log_print("\n=== Position Type ===", df["Position_Type"].value_counts().sort_index())

log_print("\n=== Remote Work ===", df["remote_flag"].value_counts())

log_print("\n=== Salary Distribution ===", salary_dist_df)

log_print("\n=== Experience ===", df["experience_years"].value_counts().sort_index())

log_print("\n=== Level ===", df["level"].value_counts().sort_index())

log_print("\n=== Skill ===", skill_summary_df)

log_print("\n=== Job Duties ===", job_summary_df)




#=========drop=========
drop_cols = ['序号', '更新日', 'Position', '会社名', '従業員数', '在宅可否', 
             '給与',  '配属部门', '就業時間', '選考内容', '清洗后全文','必要経験', '仕事内容']
df = df.drop(columns=[c for c in drop_cols if c in df.columns])
df.to_csv('one_hot.csv', index=False, encoding='utf-8-sig')

with open("analysis_report.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(report_lines))