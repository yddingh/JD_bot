import time
import csv
import os
import re
import random
import tkinter as tk
from tkinter import simpledialog, messagebox
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# --- 全局配置 ---
FULL_DATA_FILE = "full_data.csv"
TODAY_STR = datetime.now().strftime("%Y-%m-%d")
DAILY_FILE = f"{TODAY_STR}.csv"
FIELDNAMES = ["序号", "求人票No", "更新日", "内容全文"]

def get_user_input():
    """弹出对话框获取用户输入"""
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口
    
    target_url = simpledialog.askstring("输入", "1. 请粘贴搜索结果页URL:", 
                                        initialvalue="https://pdt.r-agent.com/...")
    if not target_url: return None, None
    
    date_limit = simpledialog.askstring("输入", "2. 只抓取该日期及之后的更新 (YYYY-MM-DD):", 
                                        initialvalue="2026-01-01")
    if not date_limit: return None, None
    
    root.destroy()
    return target_url, date_limit

def init_driver():
    chrome_options = Options()
    # 规避反爬检测
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_argument("--start-maximized")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    return driver

def get_existing_ids():
    """从总库读取已存在的ID，用于去重"""
    ids = set()
    if not os.path.exists(FULL_DATA_FILE):
        return ids
    try:
        with open(FULL_DATA_FILE, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                jid = row.get('求人票No')
                if jid: ids.add(jid.strip())
    except Exception as e:
        print(f"读取旧数据异常: {e}")
    return ids

def parse_date(date_str):
    """解析日文字符串日期"""
    match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', date_str)
    return datetime(int(match.group(1)), int(match.group(2)), int(match.group(3))) if match else None

def perform_final_save(new_records):
    """
    高效合并保存逻辑：
    1. 保存今日独立文件。
    2. 使用流式写入更新总表，确保新内容在顶部且不拖慢速度。
    """
    if not new_records:
        print("本次未抓取到新数据，无需更新文件。")
        return

    # --- 1. 保存/追加到今日独立文件 ---
    daily_exists = os.path.exists(DAILY_FILE)
    with open(DAILY_FILE, 'a', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if not daily_exists:
            writer.writeheader()
        writer.writerows(new_records)
    print(f"-> 已生成/更新今日数据文件: {DAILY_FILE}")

    # --- 2. 流式更新总库 (New Data at Top) ---
    print("正在合并至总库 (full_data.csv)...")
    temp_full = "full_data_temp.csv"
    
    try:
        with open(temp_full, 'w', newline='', encoding='utf-8-sig') as f_out:
            writer = csv.DictWriter(f_out, fieldnames=FIELDNAMES)
            writer.writeheader()
            
            # 首先写入本次新抓取的所有数据
            writer.writerows(new_records)
            
            # 然后将旧库的数据逐行追加到后面
            if os.path.exists(FULL_DATA_FILE):
                with open(FULL_DATA_FILE, 'r', encoding='utf-8-sig') as f_in:
                    reader = csv.DictReader(f_in)
                    for row in reader:
                        writer.writerow(row)
        
        # 替换文件
        if os.path.exists(FULL_DATA_FILE):
            os.remove(FULL_DATA_FILE)
        os.rename(temp_full, FULL_DATA_FILE)
        print("-> 总库合并完成，新抓取内容已置顶。")
    except Exception as e:
        print(f"合并总库时出错: {e}")

def crawl_jd():
    # 1. 获取用户输入
    target_url, date_limit_str = get_user_input()
    if not target_url or not date_limit_str:
        print("操作取消。")
        return

    try:
        limit_dt = datetime.strptime(date_limit_str, "%Y-%m-%d")
    except ValueError:
        print("日期格式错误，请使用 YYYY-MM-DD")
        return

    # 2. 读取旧ID去重
    dealt_ids = get_existing_ids()
    print(f"本地总库已识别: {len(dealt_ids)} 条记录。")

    driver = init_driver()
    this_session_records = [] 
    
    try:
        driver.get(target_url)
        input("【操作提示】请手动完成登录并进入列表页，确认看到卡片后，回车开始抓取...")

        while True:
            wait = WebDriverWait(driver, 10)
            # 重新获取当前页面所有的按钮
            buttons = driver.find_elements(By.CLASS_NAME, "mod-jobList-toDetailButton")
            found_new_to_click = False 

            for btn in buttons:
                # 提取ID
                href = btn.get_attribute("href")
                id_match = re.search(r'jobofferManagementNo=([^&]+)', href)
                jd_id = id_match.group(1) if id_match else None
                
                # 去重判定
                if not jd_id or jd_id in dealt_ids:
                    continue 

                found_new_to_click = True
                main_window = driver.current_window_handle
                
                try:
                    # 滚动并点击
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                    time.sleep(0.5)
                    btn.click()
                    
                    # 切换窗口
                    wait.until(lambda d: len(d.window_handles) > 1)
                    driver.switch_to.window(driver.window_handles[-1])
                    
                    # 抓取全文
                    body_element = wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                    full_text = body_element.text
                    
                    # 日期判定
                    date_match = re.search(r'最終更新日\s*(\d{4}年\d{1,2}月\d{1,2}日)', full_text)
                    update_date_str = date_match.group(1) if date_match else "未知日期"
                    update_dt = parse_date(update_date_str)

                    if update_dt and update_dt < limit_dt:
                        print(f"跳过: {jd_id} (更新于 {update_date_str})")
                    else:
                        record = {
                            "序号": "NEW", 
                            "求人票No": jd_id,
                            "更新日": update_date_str,
                            "内容全文": full_text.replace('\n', ' ')
                        }
                        this_session_records.append(record)
                        print(f"成功: {jd_id} ({update_date_str})")

                    dealt_ids.add(jd_id) # 标记为已处理

                except Exception as e:
                    print(f"抓取 ID {jd_id} 异常: {e}")
                finally:
                    if len(driver.window_handles) > 1:
                        driver.close()
                    driver.switch_to.window(main_window)
                    time.sleep(random.uniform(0.8, 1.5))

            # 翻页逻辑
            try:
                load_more_btn = driver.find_element(By.CSS_SELECTOR, ".mod-loadMore-text")
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", load_more_btn)
                time.sleep(1)
                load_more_btn.click()
                print("--- 已点击加载更多，等待内容刷新 ---")
                time.sleep(3) 
            except:
                if not found_new_to_click:
                    print("已无更多新数据可抓取。")
                    break
                continue

    except Exception as e:
        print(f"运行中发生错误: {e}")
    finally:
        # 无论程序是正常结束还是报错，都尝试保存已抓取的数据
        perform_final_save(this_session_records)
        driver.quit()
        print(f"任务结束。本次总计新增: {len(this_session_records)} 条。")

if __name__ == "__main__":
    crawl_jd()