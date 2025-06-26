import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# 导入 Edge 相关的模块
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options

# --- 配置区 ---

# 【修改点 1】: 您的 Django 登录页面的 URL
LOGIN_URL = "http://127.0.0.1:8000/admin/login/"

# 【修改点 2】: 您的登录用户名和密码
ADMIN_USERNAME = "dkj"
ADMIN_PASSWORD = ""

# 【修改点 3】: 要测试的页面 URL
COMMAND_EDIT_URL = "http://127.0.0.1:8000/MC_command/9/edit/"

# 【修改点 4】: Edge 驱动和浏览器的路径
EDGEDRIVER_PATH = r"djangotutorial\MC_command\test\edgedriver_win64\msedgedriver.exe"
EDGE_BROWSER_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

# --- 其他配置（无需修改） ---
TEST_COLOR_HEX = "#FF00FF"  # 一个鲜艳的颜色，便于识别 (洋红色)
TEST_COLOR_INT = 16711935  # #FF00FF 对应的整数值

def print_configuration():
    """打印当前的配置信息"""
    print("\n--- 测试配置 ---")
    print(f"  登录页面 URL: {LOGIN_URL}")
    print(f"  管理员用户名: {ADMIN_USERNAME}")
    print(f"  管理员密码: {'*' * len(ADMIN_PASSWORD)}") # 密码用星号代替，保护隐私
    print(f"  目标编辑页面 URL: {COMMAND_EDIT_URL}")
    print(f"  Edge 驱动路径: {EDGEDRIVER_PATH}")
    print(f"  Edge 浏览器路径: {EDGE_BROWSER_PATH}")
    print("--- 配置结束 ---\n")

def login(driver, wait):
    """自动登录函数"""
    try:
        print("\n[操作] 正在导航到登录页面...")
        driver.get(LOGIN_URL)
        user_input = wait.until(EC.presence_of_element_located((By.ID, "id_username")))
        pass_input = driver.find_element(By.ID, "id_password")
        login_button = driver.find_element(By.CSS_SELECTOR, 'input[type="submit"]')
        print(f"  [操作] 正在输入用户名: {ADMIN_USERNAME}")
        user_input.send_keys(ADMIN_USERNAME)
        pass_input.send_keys(ADMIN_PASSWORD)
        print("  [操作] 正在点击登录按钮...")
        login_button.click()
        wait.until(EC.url_contains('/admin/'))
        print("  [成功] 登录成功！")
        return True
    except Exception as e:
        print(f"  [失败] 登录时发生错误: {e}")
        return False

def test_firework_component_full_flow():
    """
    一个完整的端到端测试函数，包括登录、添加颜色、保存和最终验证。
    """
    print_configuration()
    
    service = Service(executable_path=EDGEDRIVER_PATH)
    options = Options()
    options.binary_location = EDGE_BROWSER_PATH
    
    driver = webdriver.Edge(service=service, options=options)
    wait = WebDriverWait(driver, 10)

    print("--- 测试开始 (使用 Edge 浏览器)：验证烟火组件颜色添加与保存功能 ---")

    if not login(driver, wait):
        driver.quit()
        return

    try:
        print(f"\n[操作] 正在导航到目标编辑页面: {COMMAND_EDIT_URL}")
        driver.get(COMMAND_EDIT_URL)

        # --- 阶段 1: 测试添加颜色的交互 ---
        print("\n[阶段 1] 正在测试“添加颜色”按钮的交互...")
        
        try:
            firework_row = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".firework-form-row"))
            )
            print("  [成功] 找到了烟火组件行。")
        except TimeoutException:
            print("  [失败] 无法在页面上找到 .firework-form-row。请确认页面已正确加载。")
            return

        # 查找交互所需的各个元素
        color_input = firework_row.find_element(By.CSS_SELECTOR, 'input[type="color"][data-type="colors"]')
        add_color_btn = firework_row.find_element(By.CSS_SELECTOR, '.add-color-btn[data-type="colors"]')
        hidden_colors_input = firework_row.find_element(By.CSS_SELECTOR, 'input[name$="-colors"]')
        color_palette = firework_row.find_element(By.CSS_SELECTOR, '.color-palette[data-type="colors"]')
        print("  [成功] 所有交互元素均已找到。")

        # 模拟添加颜色
        driver.execute_script(f"arguments[0].value = '{TEST_COLOR_HEX}';", color_input)
        add_color_btn.click()
        print(f"  [操作] 已输入颜色 {TEST_COLOR_HEX} 并点击了“添加颜色”。")
        time.sleep(0.5) # 等待DOM更新

        # 验证前端交互是否成功
        color_palette.find_element(By.CSS_SELECTOR, f'.color-chip[data-hex="{TEST_COLOR_HEX.lower()}"]')
        print("  [成功] 新的颜色块已出现在调色板中。")
        
        hidden_value = hidden_colors_input.get_attribute('value')
        colors_list = json.loads(hidden_value)
        if TEST_COLOR_INT in colors_list:
            print(f"  [成功] 隐藏字段的值已正确更新为: {hidden_value}")
        else:
             print(f"  [失败] 隐藏字段的值不正确: {hidden_value}")
             return


        # --- 阶段 2: 测试保存和数据持久化 ---
        print("\n[阶段 2] 正在测试表单保存与数据验证...")

        # 点击保存按钮
        save_button = driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
        save_button.click()
        print("  [操作] 已点击保存按钮。")

        # 等待页面保存后跳转或刷新，这里我们直接重新加载页面以确保拿到的是数据库里的最新数据
        print("  [操作] 等待 2 秒后重新加载页面以验证数据...")
        time.sleep(2)
        driver.get(COMMAND_EDIT_URL)
        print("  [操作] 页面已重新加载。")

        # 重新定位组件并验证数据是否被持久化
        print("  [验证] 正在验证数据是否已成功保存...")
        
        firework_row_after_save = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".firework-form-row"))
        )
        hidden_input_after_save = firework_row_after_save.find_element(By.CSS_SELECTOR, 'input[name$="-colors"]')
        palette_after_save = firework_row_after_save.find_element(By.CSS_SELECTOR, '.color-palette[data-type="colors"]')
        
        final_value = hidden_input_after_save.get_attribute('value')
        final_colors = json.loads(final_value)
        if TEST_COLOR_INT in final_colors:
            print(f"  [成功] 验证通过！重新加载后，隐藏字段的值依然包含测试颜色。值为: {final_value}")
        else:
            print(f"  [失败] 验证失败！重新加载后，隐藏字段的值 ( {final_value} ) 不再包含测试颜色。")
            return

        # 验证调色板是否也正确渲染
        palette_after_save.find_element(By.CSS_SELECTOR, f'.color-chip[data-hex="{TEST_COLOR_HEX.lower()}"]')
        print("  [成功] 验证通过！重新加载后，调色板中也正确显示了已保存的颜色。")
        
        print("\n🎉🎉🎉 恭喜！所有测试均已通过！ 🎉🎉🎉")

    except Exception as e:
        print(f"\n[测试中断] 测试过程中发生意外错误: {e.__class__.__name__}")
        print(f"  错误详情: {e}")
        
    finally:
        print("\n--- 测试结束 ---")
        driver.quit()

if __name__ == "__main__":
    test_firework_component_full_flow()