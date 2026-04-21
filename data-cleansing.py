# %%
import pandas as pd
import re
df = pd.read_csv('full_data.csv', encoding='utf-8')


# 清洗全文

def clean_content(text):
    if not isinstance(text, str):
        return text
    
    # 删除 "NEW " 字段
    text = text.replace('NEW ', '')
    
    # 任务2：删除 "求人票No ... あとからチェックしたい方は 気になる" 之后的所有内容
    # 我们定位到 "気になる" 这个关键词并截断
    # 如果关键词非常固定，可以使用 split
    keyword = "あとからチェックしたい方は 気になる"
    if keyword in text:
        text = text.split(keyword)[0]
    
    # 额外清理：由于截断后末尾可能残留 "求人票No K..." 等信息，
    # 我们可以用正则表达式进一步精准定位到 "求人票No" 之前
    text = re.sub(r'求人票No\s+K\d{8}-\d{3}-\d{2}-\d{2}.*$', '', text, flags=re.DOTALL)
    
    return text.strip()

df['内容全文'] = df['内容全文'].apply(clean_content)




#清洗公司和position
def extract_advanced(text):
    if not isinstance(text, str):
        return None, None

    # 1. 扩充公司特征：加入“相互会社”并明确包含全角空格
    # \S* 表示匹配非空白字符（含全角字符）
    company_pattern = r"(\S*(?:株式会社|合同会社|有限会社|相互会社|（株）|\(株\))\S*)"
    
    # 2. 护城河标签：同样适配全角/半角空格
    stop_tags = r"(?:業界未経験|フレックス|年間休日|土曜出勤なし|正社員|想定年収|勤務地)"
    
    # 3. 核心正则表达式改动：
    # ^\s* : 容错开头可能存在的换行或不可见字符
    # (.*?) : 职位名
    # [ \s　]+ : 匹配半角、全角或Tab空格
    regex = rf"^\s*(.*?)[ \s　]+{company_pattern}(?:[ \s　]+{stop_tags}|$)"
    
    match = re.search(regex, text)
    
    if match:
        job_title = match.group(1).strip()
        company_name = match.group(2).strip()
        
        # 针对 NEC 等带括号的特殊处理：检查公司名后紧跟的括号
        extra_parentheses = re.search(r"^[（\(][^）\)]+[）\)]", text[match.end(2):])
        if extra_parentheses:
            company_name += extra_parentheses.group()
            
        return job_title, company_name
    
    # 保底方案：使用正则 split 兼容全角/半角
    parts = re.split(r'[\s　]+', text.strip())
    if len(parts) >= 2:
        for i, p in enumerate(parts):
            if any(x in p for x in ['株式会社', '合同会社', '有限会社', '相互会社', '（株）']):
                return " ".join(parts[:i]), parts[i]
                
    return text[:20], "未识别"
# 应用
df[['Position', '会社名']] = df['内容全文'].apply(lambda x: pd.Series(extract_advanced(x)))



# 提取其他信息
def extract_fields(text):
    # 这里的 text 已经是之前处理过的（删除了 NEW 和 尾部冗余）
    clean_text = text

    
    if not isinstance(clean_text, str) or clean_text.strip() == "":
        return pd.Series([''] * 9)

    # === 3. 提取在宅/Remote 关键词 (优化版) ===
    # 加入了 ハイブリッド、出社 等关键词，并捕捉前后 25 个字符以获取更完整的语境（如：原则出社、不可等）
    # 使用 re.IGNORECASE 以防万一有英文大写
    pattern = r'(.{0,5}(?:在宅|リモート|テレワーク|ハイブリッド|出社).{0,25})'
    remote_keywords = re.findall(pattern, clean_text)
    
    if remote_keywords:
        # 去重并合并
        remote_info = " || ".join(dict.fromkeys([k.strip() for k in remote_keywords]))
    else:
        remote_info = "无匹配"

    # === 4. 提取特定段落 ===
    def extract_between(source, start_str, end_str):
        start_idx = source.find(start_str)
        if start_idx == -1:
            return ""
        start_idx += len(start_str)
        end_idx = source.find(end_str, start_idx)
        if end_idx == -1:
            # 如果没找到结束标志，截取后面 500 字
            return source[start_idx:].strip()[:500] 
        return source[start_idx:end_idx].strip()

    job_content = extract_between(clean_text, "仕事の内容", "配属先情報")
    dept_info = extract_between(clean_text, "配属先情報", "必要な能力・経験")
    requirements = extract_between(clean_text, "必要な能力・経験", "勤務地") 
    salary = extract_between(clean_text, "給与", "就業時間")
    work_hours = extract_between(clean_text, "就業時間", "通勤手当")
    selection = extract_between(clean_text, "選考内容", "企業情報")
    
    # 提取员工人数
    emp_count_match = re.search(r'従業員数[\s　]*([0-9,]+)', clean_text)
    emp_count = emp_count_match.group(1) if emp_count_match else ""

    return pd.Series([
        emp_count, 
        remote_info, 
        salary,
        requirements, 
        job_content,  
        dept_info, 
        work_hours, 
        selection, 
        clean_text
    ])

# 应用函数到 DataFrame
columns = [
    '従業員数',
    '在宅可否', 
    '給与',
    '必要経験', 
    '仕事内容',  
    '配属部门', 
    '就業時間', 
    '選考内容', 
    '清洗后全文'
]

df[columns] = df['内容全文'].apply(extract_fields)

# 只有在确定不再需要原始列时才 drop
if '内容全文' in df.columns:
    df = df.drop(columns = ['内容全文'])

df.to_csv('structed_data.csv', index=False, encoding='utf-8-sig')


