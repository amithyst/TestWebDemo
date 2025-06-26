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
    }
    # Add future components here, e.g., 'fireworks', 'book_content'
}