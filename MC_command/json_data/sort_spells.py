import json
import os

# --- 配置 ---
# 将你的JSON文件名放在这里
JSON_FILE_PATH = 'spells.json' 
# -----------

def get_sort_keys(spell_object):
    """
    从法术对象的'name'字段中提取排序所需的键（学派, 等级, 来源模组）。

    Args:
        spell_object (dict): 代表单个法术的字典。

    Returns:
        tuple: 一个包含 (学派, 等级, 来源模组) 的元组，用于排序。
               如果解析失败，则返回一个默认值以将该项排在末尾。
    """
    try:
        name_str = spell_object.get('name', '')
        # 通过 ']' 分割字符串来提取关键部分
        # 例如: '[冰霜🧊][4传奇...][旅行学]...' -> ['[冰霜🧊', '[4传奇...', '[旅行学', '...']
        parts = name_str.split(']')
        
        # 第一个部分是学派 (例如: '[冰霜🧊')
        school = parts[0] + ']'
        
        # 第二个部分的第二个字符是等级数字 (例如: '[4传奇...' -> '4')
        level = int(parts[1][1])
        
        # --- 新增逻辑：提取来源模组作为第三排序关键词 ---
        # 默认来源模组为空字符串，这样没有模组标签的原版法术会排在最前面
        mod_name = ''
        # 检查是否存在第三个部分，并且这个部分是一个标签 (以'['开头)
        if len(parts) > 2 and parts[2].startswith('['):
            # 提取模组名称 (例如: 从 '[旅行学' 提取 '旅行学')
            mod_name = parts[2][1:]

        # 返回一个元组，sorted()函数会按元组的元素依次排序：
        # 1. 学派 (school)
        # 2. 等级 (level)
        # 3. 来源模组 (mod_name)，按字典序
        return (school, level, mod_name)
        
    except (IndexError, ValueError) as e:
        # 如果某个法术的'name'格式不正确，打印错误并将其排在最后
        print(f"警告: 解析法术时出错 '{name_str}': {e}. 将其置于列表末尾。")
        # 返回一个在排序中会排在最后的值，元组长度需保持一致
        return ('~', 999, '~')

def sort_json_file(file_path):
    """
    读取、排序并重写指定的法术JSON文件。
    """
    # 检查文件是否存在
    if not os.path.exists(file_path):
        print(f"错误: 文件 '{file_path}' 不存在。请检查文件名和路径。")
        return

    print(f"正在读取文件: '{file_path}'...")
    try:
        # 使用 'utf-8' 编码打开文件以支持中文字符
        with open(file_path, 'r', encoding='utf-8') as f:
            spells_data = json.load(f)
    except json.JSONDecodeError:
        print(f"错误: '{file_path}' 不是一个有效的JSON文件。")
        return
    except Exception as e:
        print(f"读取文件时发生未知错误: {e}")
        return

    # 确保我们正在处理一个列表
    if not isinstance(spells_data, list):
        print("错误: JSON文件的顶层结构不是一个列表。无法排序。")
        return
        
    print("正在根据 学派、等级 和 来源模组 进行排序...")
    # 使用自定义的函数作为排序的key
    sorted_spells = sorted(spells_data, key=get_sort_keys)
    print("排序完成。")

    print(f"正在将排序后的数据写回文件: '{file_path}'...")
    try:
        # 使用 'w' 模式写回文件，这将覆盖原有内容
        with open(file_path, 'w', encoding='utf-8') as f:
            # json.dump() 用于将Python对象写入JSON文件
            # indent=2: 使JSON文件格式化，带2个空格的缩进，更易读
            # ensure_ascii=False: 确保中文字符被正确写入，而不是被转义成 \uXXXX 的形式
            json.dump(sorted_spells, f, indent=2, ensure_ascii=False)
        print("文件已成功更新！")
    except Exception as e:
        print(f"写入文件时发生错误: {e}")


# --- 程序入口 ---
if __name__ == "__main__":
    # 假设你的JSON文件与此脚本在同一个目录下
    # 如果不在，请提供完整路径，例如 'C:/Users/YourUser/Desktop/spells.json'
    sort_json_file(JSON_FILE_PATH)