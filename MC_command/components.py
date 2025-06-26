import json
import random # <--- 新增导入
from .models import AppliedEnchantment, AppliedAttribute, AppliedPotionEffect, AppliedFireworkExplosion # <--- 导入新模型
from .forms import AppliedEnchantmentForm, AppliedAttributeForm, AppliedPotionEffectForm, AppliedFireworkExplosionForm # <--- 导入新表单

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
            "attribute": attr.attribute.attribute_id, "amount": attr.amount,
            "operation": op_map.get(attr.operation, "add_value"), "slot": attr.slot
        })
    return {'minecraft:attribute_modifiers': f'{{modifiers:{json.dumps(modifier_list, ensure_ascii=False)}}}'}

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
    shape_map = {str(k): v for k, v in explosion_obj.SHAPE_CHOICES}

    # 处理随机形状
    shape_val = explosion_obj.shape
    if shape_val == 'random':
        # 从 choices 中排除 'random' 本身
        possible_shapes = [s[0] for s in explosion_obj.SHAPE_CHOICES if s[0] != 'random']
        shape_id = random.choice(possible_shapes)
    else:
        shape_id = int(shape_val)

    # 处理随机颜色
    def get_colors(color_str):
        if color_str == 'random':
            return [random.randint(0, 16777215)]
        try:
            # 假设 color_str 是一个 JSON 数组字符串，例如 '[16711680, 255]'
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
        for _ in range(explosion.repeat_count):
            explosions.append(_generate_single_explosion_nbt(explosion))

    if not explosions:
        return {}

    return {'Fireworks': {'Explosions': explosions}}

def generate_component_fireworks(related_manager):
    explosions = []
    for explosion in related_manager.all():
        for _ in range(explosion.repeat_count):
            # JSON Component 使用字符串键
            nbt = _generate_single_explosion_nbt(explosion)
            component_nbt = {
                'shape': f"'{nbt['Type']}'", # 注意：形状在component里是枚举字符串
                'has_trail': 'true' if nbt.get('Trail') else 'false',
                'has_twinkle': 'true' if nbt.get('Flicker') else 'false',
                'colors': f"[{','.join(map(str, nbt.get('Colors', [])))}]",
                'fade_colors': f"[{','.join(map(str, nbt.get('FadeColors', [])))}]"
            }
            # 这里我们直接构建字符串，因为格式比较特殊
            explosion_str = f"{{shape:{component_nbt['shape']},has_trail:{component_nbt['has_trail']},has_twinkle:{component_nbt['has_twinkle']},colors:{component_nbt['colors']},fade_colors:{component_nbt['fade_colors']}}}"
            explosions.append(explosion_str)

    if not explosions:
        return {}

    # Minecraft 1.20.5+ 的 firework_explosions 是一个列表
    return {'minecraft:firework_explosion': f"[{','.join(explosions)}]"}

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
        'supported_function_types': ['potion'], # VULNERABILITY: This can now be easily changed to ['all'] or ['potion', 'food']
        'generate_nbt': generate_nbt_potion_effects,
        'generate_component': generate_component_potion_effects,
    },
    # --- 在此添加新组件 ---
    'firework_explosions': {
        'verbose_name': '烟火之星',
        'model': AppliedFireworkExplosion,
        'form': AppliedFireworkExplosionForm,
        'template_path': 'MC_command/formsets/_firework_explosion_formset.html', # 我们将创建这个模板
        'supported_function_types': ['firework'], # 关键：仅对烟花火箭显示
        'generate_nbt': generate_nbt_fireworks,
        'generate_component': generate_component_fireworks,
    }
    # Add future components here, e.g., 'fireworks', 'book_content'
}