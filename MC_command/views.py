from django.http import HttpResponse
from .models import GeneratedCommand

from django.template import loader # 导入模板加载器

from django.shortcuts import get_object_or_404, render


from django.http import Http404


def index(request):
    """
    显示当前登录用户的所有命令配置列表。
    """
    # 仅查询属于当前登录用户的命令
    # 如果用户未登录, command_list 将是一个空集
    if request.user.is_authenticated:
        command_list = GeneratedCommand.objects.filter(user=request.user).order_by("-updated_at")
    else:
        command_list = GeneratedCommand.objects.none() # 返回一个空的 QuerySet
    
    context = {
        'command_list': command_list,
    }
    return render(request, 'MC_command/index.html', context)




def generate(request, command_id):
    response = f"你正在查看命令配置 {command_id} 的生成结果。"
    return HttpResponse(response)

def delete(request, command_id):
    return HttpResponse(f"你正在删除命令配置 {command_id}。")

# MC_command/views.py

import json
import uuid
from django.shortcuts import get_object_or_404, render
from .models import GeneratedCommand

# --- 核心视图 ---

def detail(request, command_id):
    """
    显示单个命令配置的详细信息，并生成最终的命令。
    """
    command_obj = get_object_or_404(GeneratedCommand, pk=command_id)
    
    # 调用帮助函数来生成命令数据
    command_context = _generate_command_context(command_obj)
    
    context = {
        'command': command_obj,
        'give_command_string': command_context['give_command'],
        'data_structure_json': command_context['data_json'],
    }
    
    return render(request, 'MC_command/detail.html', context)

# --- 帮助函数 (Helper Functions) ---

def _generate_command_context(command: GeneratedCommand) -> dict:
    """
    版本判断的“路由器”，根据目标版本选择使用哪种生成策略。
    返回一个包含最终命令字符串和数据结构JSON的字典。
    """
    target_version_id = command.target_version.ordering_id
    base_item_id = command.base_item.item_id

    # 假设 1.20.5 的 ordering_id 是 12005
    if target_version_id >= 12005:
        # --- 新版 Component 格式 ---
        data_structure = _build_component_structure(command)
        # 新版组件格式紧凑，可以直接嵌入
        data_string = ",".join([f"{key}={value}" for key, value in data_structure.items()])
        give_command = f"/give @p {base_item_id}[{data_string}] {command.count}"
    else:
        # --- 旧版 NBT Tag 格式 ---
        data_structure = _build_nbt_tag_structure(command)
        # 旧版NBT需要转为紧凑的JSON字符串
        data_string = json.dumps(data_structure, separators=(',', ':'))
        give_command = f"/give @p {base_item_id}{data_string} {command.count}"

    return {
        'give_command': give_command,
        'data_json': json.dumps(data_structure, indent=4, ensure_ascii=False), # 用于美化显示的JSON
    }

def _build_nbt_tag_structure(command: GeneratedCommand) -> dict:
    """为 1.20.4 及更早版本构建 NBT Tag 字典"""
    nbt_data = {}
    
    # 显示属性
    display = {}
    if command.custom_name:
        display['Name'] = f'"{command.custom_name}"' # JSON 文本格式
    if command.lore:
        lore_lines = [f'"{line}"' for line in command.lore.splitlines()]
        display['Lore'] = f'[{",".join(lore_lines)}]'
    if display:
        nbt_data['display'] = display
        
    # 附魔
    enchantments = []
    for ench in command.enchantments.all():
        enchantments.append({'id': ench.enchantment.enchant_id, 'lvl': ench.level})
    if enchantments:
        nbt_data['Enchantments'] = enchantments
        
    # 属性修饰符 (需要 UUID 和 Name)
    attributes = []
    for attr in command.attributes.all():
        name = attr.modifier_name if attr.modifier_name else attr.attribute.attribute_id
        # 旧版UUID是必需的，且格式复杂，这里用字符串简化表示
        # 一个真正的实现需要生成符合格式的 [I; int, int, int, int]
        random_uuid_str = f"[I; {uuid.uuid4().int & 0xFFFFFFFF}, {uuid.uuid4().int & 0xFFFFFFFF}, {uuid.uuid4().int & 0xFFFFFFFF}, {uuid.uuid4().int & 0xFFFFFFFF}]"
        attributes.append({
            'AttributeName': attr.attribute.attribute_id,
            'Name': name,
            'Amount': float(attr.amount),
            'Operation': attr.operation,
            'Slot': attr.slot,
            'UUID': random_uuid_str # 这是一个简化表示
        })
    if attributes:
        nbt_data['AttributeModifiers'] = attributes
        
    # 其他...
    if command.book_content:
        nbt_data['title'] = command.book_content.title
        nbt_data['author'] = command.book_content.author
        nbt_data['pages'] = [f'"{page}"' for page in command.book_content.pages.splitlines()]

    return nbt_data

def _build_component_structure(command: GeneratedCommand) -> dict:
    """为 1.20.5 及更新版本构建 Components 字典"""
    components = {}
    
    # 显示属性
    if command.custom_name:
        components['minecraft:custom_name'] = f'"{command.custom_name}"'
    if command.lore:
        lore_lines = [f'"{line}"' for line in command.lore.splitlines()]
        components['minecraft:lore'] = f'[{",".join(lore_lines)}]'
        
    # 附魔 (新格式是 key:level 的字典)
    enchantments = {f'"{ench.enchantment.enchant_id}"': ench.level for ench in command.enchantments.all()}
    if enchantments:
        # 注意新格式的结构
        components['minecraft:enchantments'] = f'{{levels:{json.dumps(enchantments)}}}'

    # 属性修饰符 (新格式更简洁，无 UUID 和 Name)
    attributes = []
    operation_map = {0: "add_value", 1: "add_multiplied_base", 2: "add_multiplied_total"}
    for attr in command.attributes.all():
        attributes.append(
            f'{{type:"{attr.attribute.attribute_id}", '
            f'slot:"{attr.slot}", '
            f'amount:{attr.amount}, '
            f'operation:"{operation_map[attr.operation]}"}}'
        )
    if attributes:
        components['minecraft:attribute_modifiers'] = f'{{modifiers:[{",".join(attributes)}]}}'
    
    # 其他...
    # ... 新版的药水、书本等组件有不同的结构，可以在此添加 ...

    return components

import uuid # 用于旧版命令

def generate_final_command_string(command_obj):
    """根据命令配置对象，生成最终的命令字符串"""
    
    target_version_id = command_obj.target_version.ordering_id

    # 假设 1.20.5 的 ordering_id 是 12005
    if target_version_id >= 12005:
        # --- 使用新的 Component 格式 ---
        return generate_component_style_command(command_obj)
    else:
        # --- 使用旧的 NBT Tag 格式 ---
        return generate_nbt_tag_style_command(command_obj)


def generate_component_style_command(command_obj):
    # ...
    # 在这里构建属性修饰符部分
    attribute_components = []
    operation_map = {0: "add_value", 1: "add_multiplied_base", 2: "add_multiplied_total"}

    for attr in command_obj.attributes.all():
        component = (
            f'{{type:"{attr.attribute.attribute_id}", '
            f'amount:{attr.amount}, '
            f'operation:"{operation_map[attr.operation]}", '
            f'slot:"{attr.slot}"}}'
        )
        attribute_components.append(component)
    
    # ... 最终将所有组件组合成 /give @p item[comp1={...},comp2={...}] 格式
    # ... 注意：此处忽略 attr.modifier_name
    pass


def generate_nbt_tag_style_command(command_obj):
    # ...
    # 在这里构建属性修饰符部分
    attribute_nbt = []
    for attr in command_obj.attributes.all():
        # 旧版需要一个名字，如果用户没填，我们可以用 attribute id 代替
        name = attr.modifier_name if attr.modifier_name else attr.attribute.attribute_id
        # 旧版需要 UUID
        random_uuid = str(uuid.uuid4())

        nbt_part = (
            f'{{AttributeName:"{attr.attribute.attribute_id}", '
            f'Name:"{name}", '
            f'Amount:{attr.amount}, '
            f'Operation:{attr.operation}, '
            f'Slot:"{attr.slot}", '
            f'UUID:"{random_uuid}"}}'  # 注意：实际的UUID格式更复杂，这里是简化示例
        )
        attribute_nbt.append(nbt_part)

    # ... 最终将所有 NBT 组合成 /give @p item{tag1:[...],tag2:{...}} 格式
    pass