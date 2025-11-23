import json
import random # <--- 新增导入
from .models import (AppliedEnchantment, AppliedAttribute,
                     AppliedPotionEffect, AppliedFireworkExplosion,
                     AppliedBooleanComponent,
                     SpellInfusion, AppliedSpell  # <--- 1. 导入新模型
                     ,    # ... 你已有的模型 ...
                    GeneratedEntity, AppliedEntityComponent, EntityEquipmentSlot, TradeRecipe, GeneratedCommand,AreaEffectCloudProperties # <-- 新增导入
                     )
import copy # 导入copy模块用于深拷贝(实体更新加入)

from .forms import (AppliedEnchantmentForm, AppliedAttributeForm,
                    AppliedPotionEffectForm, AppliedFireworkExplosionForm,
                    AppliedBooleanComponentForm,
                    AppliedSpellForm  # <--- 2. 导入新表单
                    )
# ==============================================================================
# Helper Functions
# ==============================================================================

def _uuid_to_int_array(uuid_obj):
    """Converts a UUID object to the integer array format required by Minecraft NBT."""
    int_val = uuid_obj.int
    part1 = (int_val >> 96) & 0xFFFFFFFF
    part2 = (int_val >> 64) & 0xFFFFFFFF
    part3 = (int_val >> 32) & 0xFFFFFFFF
    part4 = int_val & 0xFFFFFFFF
    def to_signed(n):
        return n if n < 2**31 else n - 2**32
    return f"[I;{to_signed(part1)},{to_signed(part2)},{to_signed(part3)},{to_signed(part4)}]"

# ==============================================================================
# Component-Specific Generation Logic
# ==============================================================================

# --- Enchantments ---
def generate_nbt_enchantments(related_manager):
    enchantments = [{'id': ench.enchantment.enchant_id, 'lvl': ench.level} for ench in related_manager.all()]
    return {'Enchantments': enchantments}

def generate_component_enchantments(related_manager):
    enchantment_dict = {f"{ench.enchantment.enchant_id}": ench.level for ench in related_manager.all()}
    return {'minecraft:enchantments': f'{{levels:{json.dumps(enchantment_dict)}}}'}

# --- Attributes ---
def generate_nbt_attributes(related_manager):
    modifier_list = []
    for attr in related_manager.all():
        modifier_list.append({
            "AttributeName": attr.attribute.attribute_id, "Name": attr.modifier_name,
            "Amount": attr.amount, "Operation": attr.operation, "Slot": attr.slot,
            "UUID": _uuid_to_int_array(attr.uuid)
        })
    return {'AttributeModifiers': modifier_list}

def generate_component_attributes(related_manager):
    op_map = {0: "add_value", 1: "add_multiplied_base", 2: "add_multiplied_total"}
    modifier_list = []
    for attr in related_manager.all():
        modifier_list.append({
            "type": attr.attribute.attribute_id,
            "amount": attr.amount,
            "operation": op_map.get(attr.operation, "add_value"),
            "slot": attr.slot
        })
    # For 1.20.5+, 'show_in_tooltip' is a root property of the component, not per-modifier.
    # We will assume 'True' as a sensible default.
    return {'minecraft:attribute_modifiers': f'{{modifiers:{json.dumps(modifier_list, ensure_ascii=False)},show_in_tooltip:true}}'}


# --- Potion Effects ---
def generate_nbt_potion_effects(related_manager):
    effects_list = []
    for effect in related_manager.all():
        effects_list.append({
            'Id': effect.effect.effect_id, 'Amplifier': effect.amplifier, 'Duration': effect.duration,
            'Ambient': 1 if effect.is_ambient else 0, 'ShowParticles': 1 if effect.show_particles else 0,
            'ShowIcon': 1 if effect.show_icon else 0
        })
    return {'CustomPotionEffects': effects_list}

def generate_component_potion_effects(related_manager):
    effects_list = []
    for effect in related_manager.all():
        effects_list.append({
            "id": effect.effect.effect_id, "amplifier": effect.amplifier, "duration": effect.duration,
            "ambient": effect.is_ambient, "show_particles": effect.show_particles, "show_icon": effect.show_icon
        })
    potion_contents = {'custom_effects': effects_list}
    return {'minecraft:potion_contents': json.dumps(potion_contents, ensure_ascii=False, separators=(',', ':'))}


# --- 新增: 烟花组件生成逻辑 ---
def _generate_single_explosion_nbt(explosion_obj):
    """为单个 AppliedFireworkExplosion 实例生成 NBT 字典 (考虑随机性)"""
    # 处理随机形状
    shape_val = explosion_obj.shape
    if shape_val == 'random':
        possible_shapes = [s[0] for s in explosion_obj.SHAPE_CHOICES if s[0] != 'random']
        shape_id = random.choice(possible_shapes)
    else:
        shape_id = int(shape_val)

    # 处理随机颜色
    def get_colors(color_str):
        if color_str == 'random':
            # Generate 1 to 8 random colors, as per Minecraft's default random generation
            return random.sample(range(0, 16777216), k=random.randint(1, 8))
        try:
            return json.loads(color_str)
        except (json.JSONDecodeError, TypeError):
            return []

    colors_list = get_colors(explosion_obj.colors)
    fade_colors_list = get_colors(explosion_obj.fade_colors)

    explosion_nbt = {
        'Type': shape_id,
        'Trail': 1 if explosion_obj.has_trail else 0,
        'Flicker': 1 if explosion_obj.has_twinkle else 0,
        'Colors': colors_list,
        'FadeColors': fade_colors_list,
    }
    # 移除空的颜色列表以优化NBT
    if not colors_list: del explosion_nbt['Colors']
    if not fade_colors_list: del explosion_nbt['FadeColors']

    return explosion_nbt

def generate_nbt_fireworks(related_manager):
    explosions = []
    for explosion in related_manager.all():
        # Each explosion can be repeated
        for _ in range(explosion.repeat_count):
            explosions.append(_generate_single_explosion_nbt(explosion))

    if not explosions:
        return {}

    # For NBT, explosions are nested under 'Fireworks'
    return {'Fireworks': {'Explosions': explosions}}

def generate_component_fireworks(related_manager):
    """Generates the `minecraft:fireworks` component for a firework rocket."""
    SHAPE_ID_TO_STRING = {
        0: 'small_ball', 1: 'large_ball', 2: 'star',
        3: 'creeper', 4: 'burst'
    }
    explosions_list = []
    for explosion in related_manager.all():
        for _ in range(explosion.repeat_count):
            nbt = _generate_single_explosion_nbt(explosion)
            shape_string = SHAPE_ID_TO_STRING.get(nbt.get('Type'), 'small_ball')

            # --- START MODIFICATION ---
            # Correctly format the explosion component string
            explosion_parts = [f"shape:'{shape_string}'"]
            if nbt.get('Trail'): explosion_parts.append("has_trail:true")
            if nbt.get('Flicker'): explosion_parts.append("has_twinkle:true") # Note: 'Flicker' in NBT is 'twinkle' in component
            if nbt.get('Colors'):
                # Correctly format color array with 'I;' prefix
                explosion_parts.append(f"colors:[I;{','.join(map(str, nbt['Colors']))}]")
            if nbt.get('FadeColors'):
                # Correctly format fade color array with 'I;' prefix
                explosion_parts.append(f"fade_colors:[I;{','.join(map(str, nbt['FadeColors']))}]")
            # --- END MODIFICATION ---

            explosions_list.append(f"{{{','.join(explosion_parts)}}}")

    if not explosions_list:
        return {}

    # The final component is `minecraft:fireworks` which contains the list
    explosions_str = f"[{','.join(explosions_list)}]"
    return {'minecraft:fireworks': f"{{explosions:{explosions_str},flight_duration:1}}"}

def generate_nbt_boolean(related_manager):
    """
    为布尔型组件生成根级 NBT 标签字典 (用于 1.20.4 及更早版本)。
    此函数直接“粘贴”数据库中定义的字符串。
    它会遍历所有应用的组件，将 "true_str" 或 "false_str" 的内容直接作为NBT片段。
    """
    nbt_parts = []
    for applied_comp in related_manager.all():
        comp_type = applied_comp.component
        
        # 根据组件值是 True 还是 False，选择对应的字符串
        nbt_string = comp_type.true_str if applied_comp.value else comp_type.false_str
            
        # 只有在字符串非空时才添加。这允许在禁用时完全不生成标签。
        if nbt_string:
            nbt_parts.append(nbt_string)
            
    # 返回一个特殊的键，其值为需要直接拼接的字符串列表。
    # 命令生成器的主逻辑需要知道如何处理这个特殊的 '_raw_nbt' 键。
    if nbt_parts:
        return {'_raw_nbt': nbt_parts}
    return {}

def generate_component_boolean(related_manager):
    """
    修改后，为布尔型组件生成一个包含预格式化 'key=value' 字符串的列表。
    这些字符串将用于在新版命令中“直接粘贴”。
    """
    raw_components_list = []
    for applied_comp in related_manager.all():
        comp_type = applied_comp.component
        
        # 'comp_type.name' 应该是组件的ID, 如 'minecraft:unbreakable'
        # 'comp_type.true_str' 应该是组件的值, 如 'true' 或 '{}'
        component_key = comp_type.name
        component_value = comp_type.true_str if applied_comp.value else comp_type.false_str
            
        # 仅当key和value都存在时才生成
        if component_key and component_value:
            # 预先格式化为 "key=value" 的完整字符串
            full_component_string = f"{component_key}={component_value}"
            raw_components_list.append(full_component_string)
            
    # 如果列表不为空，则用特殊的 _raw_components 键返回
    if raw_components_list:
        return {'_raw_components': raw_components_list}
    return {}


def generate_nbt_spells(related_manager):
    """
    为法术注入组件生成 NBT 数据。
    (已修正)
    """
    # related_manager 是 command.applied_spells, 
    # 所以它的 .instance 属性直接就是 SpellInfusion 对象。
    spell_infusion_obj = related_manager.instance

    # 从 related_manager (即 command.applied_spells) 获取所有法术
    all_spells = related_manager.all().order_by('index')

    data_list = []
    # 为了NBT格式正确，我们需要将Python的布尔值转为0b/1b，并将id/level等字段的顺序固定
    for spell in all_spells:
        # 注意：在生成NBT时，字段的顺序有时很重要，这里我们手动构建
        # 并且根据你的NBT格式要求，level是整数，id是字符串，index是整数，locked是byte
        spell_nbt = {
            "level": spell.level,
            "id": spell.spell.spell_id,
            "index": spell.index,
            "locked": 1 if spell.locked else 0
        }
        data_list.append(spell_nbt)

    # 构建最终的 NBT 字典
    return {
        "ISB_Spells": {
            "spellWheel": 1 if spell_infusion_obj.spell_wheel else 0,
            "mustEquip": 1 if spell_infusion_obj.must_equip else 0,
            "data": data_list,
            "maxSpells": spell_infusion_obj.max_spells
        }
    }

def generate_component_spells(related_manager):
    """
    法术注入的组件生成逻辑 (占位符)。
    由于目标版本是 1.20.1，主要使用 NBT，此函数暂时为空。
    """
    return {}

# ==============================================================================
# THE COMPONENT REGISTRY
# ==============================================================================
# This is the single source of truth for all item components.
# To add a new component (e.g., fireworks), you just add a new entry here.
COMPONENT_REGISTRY = {
    # The key is used as the formset prefix and the related_name on the GeneratedCommand model.
    'enchantments': {
        'verbose_name': '附魔',
        'model': AppliedEnchantment,
        'form': AppliedEnchantmentForm,
        'template_path': 'MC_command/formsets/_enchantment_formset.html',
        # 'all' means it applies to every item type.
        'supported_function_types': ['all'],
        'generate_nbt': generate_nbt_enchantments,
        'generate_component': generate_component_enchantments,
    },
    'attributes': {
        'verbose_name': '属性修饰符',
        'model': AppliedAttribute,
        'form': AppliedAttributeForm,
        'template_path': 'MC_command/formsets/_attribute_formset.html',
        'supported_function_types': ['all'], # Attributes can be applied to any item.
        'generate_nbt': generate_nbt_attributes,
        'generate_component': generate_component_attributes,
    },
    'potion_effects': {
        'verbose_name': '药水效果',
        'model': AppliedPotionEffect,
        'form': AppliedPotionEffectForm,
        'template_path': 'MC_command/formsets/_potion_effect_formset.html',
        'supported_function_types': ['potion'],
        'generate_nbt': generate_nbt_potion_effects,
        'generate_component': generate_component_potion_effects,
    },
    # --- 在此添加新组件 ---
    'firework_explosions': {
        'verbose_name': '烟火之星',
        'model': AppliedFireworkExplosion,
        'form': AppliedFireworkExplosionForm,
        'template_path': 'MC_command/formsets/_firework_explosion_formset.html',
        'supported_function_types': ['firework'], # 关键：仅对烟花火箭显示
        'generate_nbt': generate_nbt_fireworks,
        'generate_component': generate_component_fireworks,
    },
    # --- 在此添加新的布尔组件注册信息 ---
    'boolean_components': {
        'verbose_name': '布尔型组件',
        'model': AppliedBooleanComponent,
        'form': AppliedBooleanComponentForm, # 确保你已经创建了这个表单
        'template_path': 'MC_command/formsets/_boolean_component_formset.html', # 模板路径示例
        'supported_function_types': ['all'], # 对所有物品类型都可用
        'generate_nbt': generate_nbt_boolean, 
        'generate_component': generate_component_boolean, # 关联到我们上面创建的新函数
    },
    'applied_spells': {
        'verbose_name': '法术注入',
        'model': AppliedSpell,
        'form': AppliedSpellForm,
        'template_path': 'MC_command/formsets/_spell_formset.html', # 你需要创建这个模板文件
        'supported_function_types': ['all'], # 假设所有物品都可注入法术
        'generate_nbt': generate_nbt_spells,
        'generate_component': generate_component_spells,
    }
    # Add future components here, e.g., 'fireworks', 'book_content'
}

#--------------------------------------------------------------------------------实体部分-----------------------------------------------------------------------------

# mc_commands/components.py
# mc_commands/components.py
# mc_commands/components.py

def _generate_item_nbt_tag(item_command: GeneratedCommand):
    """
    【与/give命令逻辑对齐】
    如果 custom_name 是普通文本，则自动包装成 {"text":"..."} JSON 字符串。
    """
    if not item_command:
        return {}

    nbt_data = {}
    
    display_tag = {}
    if item_command.custom_name:
        custom_name_str = item_command.custom_name.strip()
        # 检查是否已经是JSON格式，如果不是，则进行包装
        if custom_name_str.startswith('{') and custom_name_str.endswith('}'):
            display_tag['Name'] = custom_name_str
        else:
            # 自动包装成JSON text component
            display_tag['Name'] = json.dumps({"text": custom_name_str}, ensure_ascii=False)

    if item_command.lore:
        lore_list = []
        for line in item_command.lore.split('\\n'):
            line = line.strip()
            if not line:
                continue
            # 同样，对Lore的每一行也进行包装
            if line.startswith('{') and line.endswith('}'):
                lore_list.append(line)
            else:
                lore_list.append(json.dumps({"text": line}, ensure_ascii=False))
        
        if lore_list:
            display_tag['Lore'] = lore_list
    
    if display_tag:
        nbt_data['display'] = display_tag

    # 组件NBT部分保持不变
    for key, config in COMPONENT_REGISTRY.items():
        related_manager = getattr(item_command, key, None)
        if related_manager and related_manager.exists():
            nbt_generator = config.get('generate_nbt')
            if nbt_generator:
                component_nbt = nbt_generator(related_manager)
                if '_raw_nbt' in component_nbt:
                    nbt_data.setdefault('_raw_nbt', []).extend(component_nbt['_raw_nbt'])
                else:
                    nbt_data.update(component_nbt)

    return nbt_data


# ... 在 _generate_item_nbt_tag 函数之后 ...

# --- 新增辅助函数：为粒子效果云(AEC)生成独有NBT ---
def _generate_aec_properties_nbt(entity: GeneratedEntity):
    """为粒子效果云实体生成其独有的NBT数据。"""
    # 检查实体是否有关联的AEC属性，如果没有则返回空字典
    if not hasattr(entity, 'aec_properties'):
        return {}

    props = entity.aec_properties

    # 将模型字段映射到NBT键名
    aec_nbt = {
        "Duration": props.duration,
        "WaitTime": props.wait_time,
        "ReapplicationDelay": props.reapplication_delay,
        "DurationOnUse": props.duration_on_use,
        "Radius": props.radius,
        "RadiusOnUse": props.radius_on_use,
        "RadiusPerTick": props.radius_per_tick,
        "Particle": props.particle_type,
    }

    # 处理药水效果 (对于AEC，药水效果在根NBT中，而不是ActiveEffects)
    # 注意：这里的逻辑与物品的药水效果生成非常相似
    effects_list = []
    for effect in entity.potion_effects.all():
        effects_list.append({
            'Id': effect.effect.effect_id, 'Amplifier': effect.amplifier, 'Duration': effect.duration,
            'Ambient': 1 if effect.is_ambient else 0, 'ShowParticles': 1 if effect.show_particles else 0,
            'ShowIcon': 1 if effect.show_icon else 0
        })

    if effects_list:
        aec_nbt['CustomPotionEffects'] = effects_list

    return aec_nbt


# --- 新增辅助函数：为物品实体或投射物生成来源物品NBT ---
def _generate_entity_source_item_nbt(entity: GeneratedEntity):
    """为需要关联物品的实体（如物品实体、三叉戟）生成对应的NBT标签。"""
    if not entity.source_item:
        return {}

    item_command = entity.source_item

    # 定义实体类型到NBT键名的映射
    nbt_key_map = {
        'minecraft:item': 'Item',
        'minecraft:trident': 'TridentItem',
        'minecraft:firework_rocket': 'FireworksItem',
        # 未来可以扩展更多投射物...
    }

    nbt_key = nbt_key_map.get(entity.entity_type.entity_id)

    # 如果当前实体类型不需要来源物品NBT，则返回空
    if not nbt_key:
        return {}

    item_data = {
        'id': item_command.item_id,
        'Count': item_command.count,
    }
    tag_data = _generate_item_nbt_tag(item_command)
    if tag_data:
        item_data['tag'] = tag_data

    return {nbt_key: item_data}

# --- 3. 各部分实体 NBT 生成函数 ---

def _generate_entity_components_nbt(entity: GeneratedEntity):
    """生成实体基础NBT组件 (如 NoAI, CustomName, VillagerData 等)"""
    nbt = {}
    for applied_comp in entity.components.all():
        key = applied_comp.component_type.nbt_key
        value_type = applied_comp.component_type.value_type
        raw_value = applied_comp.value

        # 根据值的类型进行转换
        try:
            if value_type == 'boolean':
                # Minecraft NBT 中布尔值通常是 0b 或 1b
                nbt[key] = 1 if raw_value.lower() in ['true', '1'] else 0
            elif value_type == 'integer':
                nbt[key] = int(raw_value)
            elif value_type == 'float':
                nbt[key] = float(raw_value)
            elif value_type in ['string', 'json']:
                 # 对于JSON字符串，我们直接使用
                 # 对于普通字符串，也直接使用
                nbt[key] = raw_value
            # position_vector 等更复杂的类型可以在这里扩展
        except (ValueError, TypeError):
            # 如果值转换失败，跳过这个组件
            continue
    return nbt

def _generate_entity_equipment_nbt(entity: GeneratedEntity):
    """生成 ArmorItems 和 HandItems 列表"""
    # 初始化空的槽位
    armor_items = [{}, {}, {}, {}] # feet, legs, chest, head
    hand_items = [{}, {}]          # mainhand, offhand
    slot_map = {
        'feet': (armor_items, 0), 'legs': (armor_items, 1),
        'chest': (armor_items, 2), 'head': (armor_items, 3),
        'mainhand': (hand_items, 0), 'offhand': (hand_items, 1),
    }

    for slot in entity.entityequipmentslot_set.all():
        if slot.slot in slot_map:
            item_nbt = {
                'id': slot.item.item_id,
                'Count': slot.item.count,
            }
            tag_data = _generate_item_nbt_tag(slot.item)
            if tag_data:
                item_nbt['tag'] = tag_data
            
            target_list, index = slot_map[slot.slot]
            target_list[index] = item_nbt
            
    return {'ArmorItems': armor_items, 'HandItems': hand_items}

def _generate_entity_trades_nbt(entity: GeneratedEntity):
    """生成村民的 Offers.Recipes 列表"""
    if not entity.trades.exists():
        return {}

    recipes = []
    for trade in entity.trades.all():
        recipe = {
            'maxUses': trade.max_uses,
            'xp': trade.xp,
            'priceMultiplier': trade.price_multiplier,
            # 添加其他交易属性...
        }
        
        # 处理收购和出售的物品
        for item_field in ['buy_item1', 'buy_item2', 'sell_item']:
            item_command = getattr(trade, item_field, None)
            if item_command:
                # 映射到NBT中的键名 (buy_item1 -> buy, buy_item2 -> buyB)
                nbt_key_map = {'buy_item1': 'buy', 'buy_item2': 'buyB', 'sell_item': 'sell'}
                nbt_key = nbt_key_map[item_field]
                
                item_nbt = {
                    'id': item_command.item_id,
                    'Count': item_command.count,
                }
                tag_data = _generate_item_nbt_tag(item_command)
                if tag_data:
                    item_nbt['tag'] = tag_data
                recipe[nbt_key] = item_nbt
        
        recipes.append(recipe)

    return {'Offers': {'Recipes': recipes}}

def _generate_entity_attributes_nbt(entity: GeneratedEntity):
    """生成实体的基础属性 (Attributes) 列表"""
    if not entity.attributes.exists():
        return {}
        
    attributes_list = []
    for attr in entity.attributes.all():
        # 对于实体的基础属性，我们通常只设置 Base 值
        attributes_list.append({
            'Name': attr.attribute.attribute_id,
            'Base': attr.amount
        })
    return {'Attributes': attributes_list}

def _generate_entity_potion_effects_nbt(entity: GeneratedEntity):
    """生成实体的永久药水效果 (ActiveEffects) 列表"""
    if not entity.potion_effects.exists():
        return {}

    effects_list = []
    for effect in entity.potion_effects.all():
        effects_list.append({
            'Id': effect.effect.effect_id,
            'Amplifier': effect.amplifier,
            'Duration': effect.duration, # 对于永久效果，通常设为-1或一个极大值
            'Ambient': 1 if effect.is_ambient else 0,
            'ShowParticles': 1 if effect.show_particles else 0,
            'ShowIcon': 1 if effect.show_icon else 0
        })
    return {'ActiveEffects': effects_list}


# --- 4. 主入口函数 ---

# --- 用下面的【完整代码块】替换掉从 `_generate_entity_components_nbt` 到 `generate_entity_nbt` 的所有旧函数 ---

def generate_entity_nbt(entity: GeneratedEntity, processed_ids=None):
    """
    【重构后】的主函数：接收一个 GeneratedEntity 对象，生成并返回其完整的 NBT 字典。
    支持递归生成乘客NBT，并能根据实体类型处理特殊逻辑。
    """
    if not isinstance(entity, GeneratedEntity):
        raise TypeError("Input must be a GeneratedEntity instance.")

    # --- 递归保护：防止无限循环（例如 A骑B, B骑A）---
    if processed_ids is None:
        processed_ids = set()
    if entity.id in processed_ids:
        return {"id": entity.entity_type.entity_id, "error": "Recursive passenger loop detected"}
    processed_ids.add(entity.id)

    # --- 1. 生成基础NBT组件 ---
    final_nbt = {}
    for applied_comp in entity.components.all():
        key = applied_comp.component_type.nbt_key
        value_type = applied_comp.component_type.value_type
        raw_value = applied_comp.value
        try:
            # --- 【新增】对 CustomName 的特殊处理逻辑 ---
            if key == 'CustomName':
                # 检查输入的值是否已经是JSON格式，如果不是，则自动包装
                if raw_value.startswith('{') and raw_value.endswith('}'):
                    final_nbt[key] = raw_value
                else:
                    # 将普通文本包装成 {"text":"..."} 的JSON字符串
                    final_nbt[key] = json.dumps({"text": raw_value}, ensure_ascii=False)
                continue # 处理完毕，跳过后面的通用逻辑
            # --- 特殊处理结束 ---

            # 通用逻辑保持不变
            if value_type == 'boolean': final_nbt[key] = 1 if raw_value.lower() in ['true', '1'] else 0
            elif value_type == 'integer': final_nbt[key] = int(raw_value)
            elif value_type == 'float': final_nbt[key] = float(raw_value)
            else: final_nbt[key] = raw_value
        except (ValueError, TypeError): continue

    # --- 2. 生成装备和交易 (逻辑不变) ---
    # 装备
    armor_items = [{}, {}, {}, {}]
    hand_items = [{}, {}]
    slot_map = {'feet': (armor_items, 0), 'legs': (armor_items, 1), 'chest': (armor_items, 2), 'head': (armor_items, 3), 'mainhand': (hand_items, 0), 'offhand': (hand_items, 1)}
    for slot in entity.entityequipmentslot_set.all():
        if slot.slot in slot_map:
            item_nbt = {'id': slot.item.item_id, 'Count': slot.item.count}
            tag_data = _generate_item_nbt_tag(slot.item)
            if tag_data: item_nbt['tag'] = tag_data
            target_list, index = slot_map[slot.slot]
            target_list[index] = item_nbt
    final_nbt.update({'ArmorItems': armor_items, 'HandItems': hand_items})
    # 交易
    if entity.trades.exists():
        recipes = []
        for trade in entity.trades.all():
            recipe = {'maxUses': trade.max_uses, 'xp': trade.xp, 'priceMultiplier': trade.price_multiplier}
            
            # --- 核心修改逻辑 ---
            # 定义要处理的物品和对应的数量覆盖字段
            items_to_process = [
                ('buy_item1', 'buy_item1_count', 'buy'),
                ('buy_item2', 'buy_item2_count', 'buyB'),
                ('sell_item', 'sell_item_count', 'sell')
            ]
            
            for item_field, count_field, nbt_key in items_to_process:
                item_command = getattr(trade, item_field, None)
                if item_command:
                    # 优先使用覆盖数量，否则使用物品配置的默认数量
                    override_count = getattr(trade, count_field, None)
                    count = override_count or item_command.count
                    
                    item_nbt = {'id': item_command.item_id, 'Count': count}
                    tag_data = _generate_item_nbt_tag(item_command)
                    if tag_data:
                        item_nbt['tag'] = tag_data
                    
                    recipe[nbt_key] = item_nbt
            # --- 修改结束 ---

            recipes.append(recipe)
        final_nbt.update({'Offers': {'Recipes': recipes}})

    # --- 3. 根据实体类型，处理【特殊逻辑】 ---
    entity_type_id = entity.entity_type.entity_id

    # a. 如果是粒子效果云 (AEC)
    if entity_type_id == 'minecraft:area_effect_cloud':
        final_nbt.update(_generate_aec_properties_nbt(entity))
    # b. 否则，对于普通实体，生成属性和激活药水效果
    else:
        # 基础属性
        if entity.attributes.exists():
            attributes_list = [{'Name': attr.attribute.attribute_id, 'Base': attr.amount} for attr in entity.attributes.all()]
            final_nbt['Attributes'] = attributes_list
        # 激活的药水效果
        if entity.potion_effects.exists():
            effects_list = [{'Id': e.effect.effect_id, 'Amplifier': e.amplifier, 'Duration': e.duration, 'Ambient': 1 if e.is_ambient else 0, 'ShowParticles': 1 if e.show_particles else 0, 'ShowIcon': 1 if e.show_icon else 0} for e in entity.potion_effects.all()]
            final_nbt['ActiveEffects'] = effects_list

    # c. 处理需要来源物品的实体 (物品实体、投射物等)
    final_nbt.update(_generate_entity_source_item_nbt(entity))

    # --- 4. 递归生成乘客NBT ---
    if entity.passengers.exists():
        passengers_list = []
        for passenger_entity in entity.passengers.all():
            # 创建一个新的processed_ids副本，以处理同一层级的多个不同乘客
            passenger_nbt = generate_entity_nbt(passenger_entity, processed_ids=copy.copy(processed_ids))
            passengers_list.append(passenger_nbt)
        final_nbt['Passengers'] = passengers_list

    return final_nbt