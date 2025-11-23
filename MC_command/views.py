# amithyst/testwebdemo/TestWebDemo-aa984f0e28b37ace0788b6c8c16a1b3d096ffd1a/MC_command/views.py

from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR
import random
from django import forms
# --- 在文件顶部，确保导入以下所有内容 ---
import json
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.forms import inlineformset_factory, modelform_factory # <--- 确保导入 modelform_factory

# --- 实体更新新增：导入通用内联表单工厂 ---
from django.contrib.contenttypes.forms import generic_inlineformset_factory

from django.db import transaction

from django.http import JsonResponse
from django.db.models import Q
# 修改:引入 Material, ItemType
# 修改:引入 Material, ItemType, Spell
from .models import (Enchantment, AttributeType, PotionEffectType,
                     MinecraftVersion, Material, ItemType, Spell,
                     SpellInfusion, AppliedSpell, GeneratedCommand,
                     # --- 新增：导入实体相关的模型 ---
                         GeneratedEntity, EntityType, EntityComponentType, AppliedEntityComponent,
    EntityEquipmentSlot, TradeRecipe, AreaEffectCloudProperties, # <-- 确认已导入
    AppliedAttribute, AppliedPotionEffect, GeneratedCommand, # <-- 确认已导入
    UserWallet, GameTransaction
    )

from .models import GeneratedCommand
from .forms import (
    GeneratedCommandForm, VersionedModelChoiceField, 
    AppliedFireworkExplosionAdminForm, SpellInfusionForm,
    # --- 以下是为实体视图新添加的，请确保它们都在这里 ---
    GeneratedEntityForm, EntityEquipmentSlotForm, TradeRecipeForm,
    AppliedEntityComponentForm, AppliedAttributeForm, AppliedPotionEffectForm,
    AreaEffectCloudPropertiesForm # <-- 新增导入
)
from .components import COMPONENT_REGISTRY, generate_entity_nbt # <--- 导入实体NBT生成函数

# --- 核心视图 ---
def home(request):
    return render(request, 'MC_command/home.html')

@login_required
def item_index(request):
    command_list = GeneratedCommand.objects.filter(user=request.user).order_by("-updated_at")
    context = {
        'command_list':command_list,
    }
    return render(request, 'MC_command/item/index.html', context)

@login_required
def entity_index(request):
    return render(request, 'MC_command/entity/index.html')

@login_required
def book_index(request):
    return render(request, 'MC_command/book/index.html')

@login_required
def detail(request, command_id):
    command_obj = get_object_or_404(GeneratedCommand, pk=command_id, user=request.user)
    command_context = _generate_command_context(command_obj)
    context = {
        'command':command_obj,
        'give_command_string':command_context['give_command'],
        'data_structure_json':command_context['data_json'],
    }
    return render(request, 'MC_command/item/detail.html', context)

@login_required
def create(request):
    # 将法术组件与其他组件分开处理
    spell_prefix = 'applied_spells'
    spell_config = COMPONENT_REGISTRY.get(spell_prefix, {})
    other_components = {k: v for k, v in COMPONENT_REGISTRY.items() if k != spell_prefix}

    # 1. 为常规组件创建 FormSet 类
    FormSetClasses = {
        prefix: inlineformset_factory(
            GeneratedCommand, config['model'], form=config['form'], extra=1, can_delete=True, min_num=0
        ) for prefix, config in other_components.items()
    }

    # 2. 为法术注入组件创建独立的 Form 和 FormSet
    SpellInfusionFormSet = inlineformset_factory(
        SpellInfusion, AppliedSpell, form=spell_config.get('form'), extra=1, can_delete=True, min_num=0
    )

    if request.method == 'POST':
        form = GeneratedCommandForm(request.POST)
        formsets = {prefix: FormSetClasses[prefix](request.POST, prefix=prefix) for prefix in other_components}
        spell_infusion_form = SpellInfusionForm(request.POST, prefix='spell_infusion')
        spell_formset = SpellInfusionFormSet(request.POST, prefix=spell_prefix)

        all_valid = (form.is_valid() and
                     all(fs.is_valid() for fs in formsets.values()) and
                     spell_infusion_form.is_valid() and
                     spell_formset.is_valid())

        if all_valid:
            try:
                _validate_version_compatibility(
                    form,
                    formsets.get('enchantments'),
                    formsets.get('attributes'),
                    spell_formset,
                    form.cleaned_data['target_version']
                )

                with transaction.atomic():
                    command_instance = form.save(commit=False)
                    command_instance.user = request.user
                    command_instance.save()

                    # 保存常规组件
                    for prefix, formset in formsets.items():
                        formset.instance = command_instance
                        formset.save()

                    # --- 新的、更健壮的法术保存逻辑 ---
                    # 检查用户是否填写了任何与法术相关的数据
                    has_spell_data = spell_infusion_form.has_changed() or spell_formset.has_changed()

                    if has_spell_data:
                        # 计算实际的法术数量
                        num_spells = len([f for f in spell_formset.cleaned_data if f and not f.get('DELETE')])
                        
                        infusion_instance = spell_infusion_form.save(commit=False)
                        
                        # 智能调整 max_spells
                        if num_spells > infusion_instance.max_spells:
                            infusion_instance.max_spells = num_spells
                        
                        # 只有在确实有法术时才保存容器
                        if num_spells > 0:
                            infusion_instance.command = command_instance
                            infusion_instance.save()
                            spell_formset.instance = infusion_instance
                            spell_formset.save()

                    return redirect(reverse('MC_command:detail', args=[command_instance.id]))
            except forms.ValidationError:
                pass 

    else: # GET 请求
        form = GeneratedCommandForm()
        formsets = {prefix: FormSetClasses[prefix](prefix=prefix) for prefix in other_components}
        spell_infusion_form = SpellInfusionForm(prefix='spell_infusion')
        spell_formset = SpellInfusionFormSet(prefix=spell_prefix)

    # ... (视图的 context 部分保持不变) ...
    version_data = {v.pk: v.ordering_id for v in MinecraftVersion.objects.all()}
    item_type_data = {it.pk: {'type': it.function_type} for it in ItemType.objects.all()}
    component_data = {
        prefix: {'formset': formsets[prefix], 'verbose_name': config['verbose_name'], 'supported_types': json.dumps(config['supported_function_types'])}
        for prefix, config in other_components.items()
    }
    component_data[spell_prefix] = {
        'formset': spell_formset,
        'verbose_name': spell_config.get('verbose_name'),
        'supported_types': json.dumps(spell_config.get('supported_function_types', ['all'])),
        'extra_form': spell_infusion_form
    }
    context = {
        'form': form,
        'component_data': component_data,
        'form_title': '创建新命令',
        'version_data_json': json.dumps(version_data),
        'item_type_data_json': json.dumps(item_type_data),
    }
    return render(request, 'MC_command/item/command_form.html', context)


# --- 用这个新版本替换旧的 EDIT 视图 ---
@login_required
def edit(request, command_id):
    command_obj = get_object_or_404(GeneratedCommand, pk=command_id, user=request.user)
    
    try:
        spell_infusion_instance = command_obj.spell_infusion
    except SpellInfusion.DoesNotExist:
        spell_infusion_instance = None

    spell_prefix = 'applied_spells'
    spell_config = COMPONENT_REGISTRY.get(spell_prefix, {})
    other_components = {k: v for k, v in COMPONENT_REGISTRY.items() if k != spell_prefix}

    FormSetClasses = {
        prefix: inlineformset_factory(
            GeneratedCommand, config['model'], form=config['form'], extra=1, can_delete=True, min_num=0
        ) for prefix, config in other_components.items()
    }

    SpellInfusionFormSet = inlineformset_factory(
        SpellInfusion, AppliedSpell, form=spell_config.get('form'), extra=1, can_delete=True, min_num=0
    )

    if request.method == 'POST':
        form = GeneratedCommandForm(request.POST, instance=command_obj)
        formsets = {prefix: FormSetClasses[prefix](request.POST, instance=command_obj, prefix=prefix) for prefix in other_components}
        spell_infusion_form = SpellInfusionForm(request.POST, instance=spell_infusion_instance, prefix='spell_infusion')
        spell_formset = SpellInfusionFormSet(request.POST, instance=spell_infusion_instance, prefix=spell_prefix)
        
        all_valid = (form.is_valid() and
                     all(fs.is_valid() for fs in formsets.values()) and
                     spell_infusion_form.is_valid() and
                     spell_formset.is_valid())
        
        if all_valid:
            try:
                _validate_version_compatibility(
                    form,
                    formsets.get('enchantments'),
                    formsets.get('attributes'),
                    spell_formset,
                    form.cleaned_data['target_version']
                )

                with transaction.atomic():
                    command_instance = form.save()
                    
                    for formset in formsets.values():
                        formset.save()
                    
                    # --- 新的、更健Robust的法术保存逻辑 ---
                    num_spells = len([f for f in spell_formset.cleaned_data if f and not f.get('DELETE')])

                    if num_spells > 0:
                        infusion_instance = spell_infusion_form.save(commit=False)
                        
                        # 智能调整 max_spells
                        if num_spells > infusion_instance.max_spells:
                            infusion_instance.max_spells = num_spells
                        
                        # 确保与 command 关联
                        infusion_instance.command = command_instance
                        infusion_instance.save()
                        
                        spell_formset.instance = infusion_instance
                        spell_formset.save()
                    elif spell_infusion_instance:
                        # 如果法术数量变为0，且之前存在容器，则删除
                        spell_infusion_instance.delete()

                    return redirect(reverse('MC_command:detail', args=[command_obj.id]))
            except forms.ValidationError:
                pass

    else: # GET 请求
        form = GeneratedCommandForm(instance=command_obj)
        formsets = {prefix: FormSetClasses[prefix](instance=command_obj, prefix=prefix) for prefix in other_components}
        spell_infusion_form = SpellInfusionForm(instance=spell_infusion_instance, prefix='spell_infusion')
        spell_formset = SpellInfusionFormSet(instance=spell_infusion_instance, prefix=spell_prefix)

    # ... (视图的 context 部分保持不变) ...
    version_data = {v.pk: v.ordering_id for v in MinecraftVersion.objects.all()}
    item_type_data = {it.pk: {'type': it.function_type} for it in ItemType.objects.all()}
    component_data = {
        prefix: {'formset': formsets[prefix], 'verbose_name': config['verbose_name'], 'supported_types': json.dumps(config['supported_function_types'])}
        for prefix, config in other_components.items()
    }
    component_data[spell_prefix] = {
        'formset': spell_formset,
        'verbose_name': spell_config.get('verbose_name'),
        'supported_types': json.dumps(spell_config.get('supported_function_types', ['all'])),
        'extra_form': spell_infusion_form
    }
    context = {
        'form': form,
        'component_data': component_data,
        'command': command_obj,
        'form_title': '编辑命令',
        'version_data_json': json.dumps(version_data),
        'item_type_data_json': json.dumps(item_type_data),
    }
    return render(request, 'MC_command/item/command_form.html', context)

def _validate_version_compatibility(form, enchant_formset, attribute_formset, spell_formset, target_version):
    """
    一个辅助函数，用于检查所选版本是否与所有组件兼容。
    如果不兼容，则会向主表单添加一个错误并引发 ValidationError。
    """
    all_components = []

    if enchant_formset:
        for enchant_form in enchant_formset.cleaned_data:
            if enchant_form and not enchant_form.get('DELETE'):
                all_components.append(enchant_form.get('enchantment'))

    if attribute_formset:
        for attr_form in attribute_formset.cleaned_data:
            if attr_form and not attr_form.get('DELETE'):
                all_components.append(attr_form.get('attribute'))
    
    # --- 新增：检查法术表单集 ---
    if spell_formset:
        for spell_form in spell_formset.cleaned_data:
            if spell_form and not spell_form.get('DELETE'):
                all_components.append(spell_form.get('spell'))
    # --- 新增结束 ---

    min_v_id = 0
    max_v_id = float('inf')

    # 计算所有组件版本号的交集
    for component in filter(None, all_components):
        if component.min_version:
            min_v_id = max(min_v_id, component.min_version.ordering_id)

        if component.max_version:
            max_v_id = min(max_v_id, component.max_version.ordering_id)

    if min_v_id > max_v_id:
        min_v_obj = MinecraftVersion.objects.filter(ordering_id=min_v_id).first()
        max_v_obj = MinecraftVersion.objects.filter(ordering_id=max_v_id).first()
        min_v_str = min_v_obj.version_number if min_v_obj else f"ID({min_v_id})"
        max_v_str = max_v_obj.version_number if max_v_obj else "更早版本"

        error_msg = f"组件冲突：所选组件之间没有兼容的Minecraft版本 (计算出的最低版本需求为 {min_v_str}，最高为 {max_v_str})。请调整您的选择。"
        raise forms.ValidationError(error_msg, code='version_conflict')

    if not (min_v_id <= target_version.ordering_id <= max_v_id):
        min_v_obj = MinecraftVersion.objects.filter(ordering_id=min_v_id).first()
        max_v_obj = MinecraftVersion.objects.filter(ordering_id=max_v_id).first()
        min_v_str = min_v_obj.version_number if min_v_obj else f"ID({min_v_id})"
        max_v_str = "最新"
        if max_v_id != float('inf') and max_v_obj:
            max_v_str = max_v_obj.version_number

        error_msg = f"版本不兼容。根据所选组件，可用版本应在 {min_v_str} 和 {max_v_str} 之间。"
        form.add_error('target_version', error_msg)
        raise forms.ValidationError(error_msg, code='version_incompatible')


@login_required
@require_POST
def delete(request, command_id):
    command_obj = get_object_or_404(GeneratedCommand, pk=command_id, user=request.user)
    command_obj.delete()
    return redirect(reverse('MC_command:index'))


# --- 辅助函数 (Helper Functions) ---

# amithyst/testwebdemo/TestWebDemo-aa984f0e28b37ace0788b6c8c16a1b3d096ffd1a/MC_command/views.py
#旧版1.20.1-1.20.3
# mc_commands/views.py
# mc_commands/views.py
# mc_commands/views.py

def _to_snbt(data, parent_key=None):
    """
    【最终智能版】根据父键(parent_key)来决定如何处理JSON格式的字符串。
    """
    if isinstance(data, dict):
        raw_parts = data.pop('_raw_nbt', [])
        items = [f"{k}:{_to_snbt(v, parent_key=k)}" for k, v in data.items()]
        all_parts = items + raw_parts
        return f"{{{','.join(filter(None, all_parts))}}}"

    if isinstance(data, list):
        return f"[{','.join([_to_snbt(item, parent_key=parent_key) for item in data])}]"

    if isinstance(data, str):
        is_json_like = data.startswith('{') and data.endswith('}')

        if is_json_like:
            # --- 核心判断逻辑 ---
            # 规则1: 如果父键是 Name, Lore, 或 CustomName，则加单引号
            if parent_key in ['Name', 'Lore', 'CustomName']:
                return f"'{data}'"
            # 规则2: 否则 (例如 ForgeCaps)，直接返回原始字符串，不加引号
            else:
                return data

        # 对于非JSON格式的字符串，按原逻辑处理
        if data.startswith('[I;'):
            return data
        return json.dumps(data, ensure_ascii=False)

    if isinstance(data, bool): return '1b' if data else '0b'
    if isinstance(data, (int, float)): return str(data)

    return str(data)

def _generate_command_context(command: GeneratedCommand) -> dict:
    """
    Generates the command context, with special handling for both _raw_nbt and _raw_components.
    """
    target_version_id = command.target_version.ordering_id
    base_item_id = command.item_id
    target_selector = "@a"

    if target_version_id >= 12005:  # Minecraft 1.20.5+
        # ==================== MODIFICATION START ====================
        data_structure = _build_component_structure(command)
        
        # 1. 安全地提取并移除 _raw_components 列表
        raw_components_list = data_structure.pop('_raw_components', [])
        
        # 2. 将剩余的、结构化的组件数据格式化为 "key=value" 字符串列表
        structured_components_list = [f"{key}={value}" for key, value in data_structure.items()]
        
        # 3. 将结构化列表和原始列表合并
        all_components_list = structured_components_list + raw_components_list
        
        # 4. 将所有部分用逗号连接，并放入括号中
        if all_components_list:
            data_string = ",".join(all_components_list)
            give_command = f"/give {target_selector} {base_item_id}[{data_string}] {command.count}"
        else:
            # 如果没有任何组件，则不生成[]
            give_command = f"/give {target_selector} {base_item_id} {command.count}"

        # 为了在JSON预览中清晰地展示，可以将处理过的数据放回
        if raw_components_list:
            data_structure['_raw_components_was_processed'] = raw_components_list
        data_for_json_display = data_structure
        
        # ===================== MODIFICATION END =====================
    else:  # Older versions
        # --- 这部分处理 _raw_nbt 的逻辑保持不变 ---
        data_structure = _build_nbt_tag_structure(command)
        raw_nbt_list = data_structure.pop('_raw_nbt', [])
        structured_nbt_string = _to_snbt(data_structure) if data_structure else ""
        all_nbt_parts = []
        if structured_nbt_string:
            all_nbt_parts.append(structured_nbt_string[1:-1])
        all_nbt_parts.extend(raw_nbt_list)
        if all_nbt_parts:
            final_nbt_content = ",".join(filter(None, all_nbt_parts))
            data_string = f"{{{final_nbt_content}}}"
        else:
            data_string = ""
        give_command = f"/give {target_selector} {base_item_id}{data_string} {command.count}"
        if raw_nbt_list:
            data_structure['_raw_nbt_was_processed_into_command'] = raw_nbt_list
        data_for_json_display = data_structure

    return {
        'give_command': give_command,
        'data_json': json.dumps(data_for_json_display, indent=4, ensure_ascii=False),
    }
# mc_commands/views.py

def _build_nbt_tag_structure(command: GeneratedCommand) -> dict:
    """
    【与components.py对齐】
    如果 custom_name 是普通文本，则自动包装成 {"text":"..."} JSON 字符串。
    """
    nbt_data = {}
    display = {}

    if command.custom_name:
        custom_name_str = command.custom_name.strip()
        if custom_name_str.startswith('{') and custom_name_str.endswith('}'):
            display['Name'] = custom_name_str
        else:
            display['Name'] = json.dumps({"text": custom_name_str}, ensure_ascii=False)

    if command.lore:
        lore_list = []
        for line in command.lore.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith('{') and line.endswith('}'):
                lore_list.append(line)
            else:
                lore_list.append(json.dumps({"text": line}, ensure_ascii=False))

        if lore_list:
            display['Lore'] = lore_list

    if display:
        nbt_data['display'] = display

    for prefix, config in COMPONENT_REGISTRY.items():
        related_manager = getattr(command, prefix)
        if related_manager.exists():
            nbt_part = config['generate_nbt'](related_manager)
            nbt_data.update(nbt_part)

    return nbt_data
#新版1.20.3-1.20.6
# def _generate_command_context(command:GeneratedCommand) -> dict:
#     # This function remains mostly the same, but calls the refactored builders.
#     target_version_id = command.target_version.ordering_id
#     base_item_id = command.item_id
#     if target_version_id >= 12005:# Minecraft 1.20.5+
#         data_structure = _build_component_structure(command)
#         data_string = ",".join([f"{key}={value}" for key, value in data_structure.items()])
#         give_command = f"/give @p {base_item_id}[{data_string}] {command.count}"
#     else:# Older versions
#         data_structure = _build_nbt_tag_structure(command)
#         data_string = json.dumps(data_structure, separators=(',', ':')) if data_structure else ''
#         give_command = f"/give @p {base_item_id}{data_string} {command.count}"
#     return {
#         'give_command':give_command,
#         'data_json':json.dumps(data_structure, indent=4, ensure_ascii=False),
#     }

# def _build_nbt_tag_structure(command:GeneratedCommand) -> dict:
#     """REFACTORED:Builds the NBT tag structure by iterating through the component registry."""
#     nbt_data = {}
#     display = {}

#     if command.custom_name:
#         display['Name'] = json.dumps(command.custom_name, ensure_ascii=False)
#     if command.lore:
#         lore_lines = [json.dumps(line, ensure_ascii=False) for line in command.lore.splitlines() if line.strip()]
#         if lore_lines:
#             display['Lore'] = f'[{",".join(lore_lines)}]'
#     if display:
#         nbt_data['display'] = display

#     for prefix, config in COMPONENT_REGISTRY.items():
#         related_manager = getattr(command, prefix)
#         if related_manager.exists():
#             nbt_part = config['generate_nbt'](related_manager)
#             nbt_data.update(nbt_part)

#     return nbt_data

def _build_component_structure(command:GeneratedCommand) -> dict:
    """REFACTORED:Builds the component structure by iterating through the component registry."""
    components = {}

    if command.custom_name:
        components['minecraft:custom_name'] = json.dumps(command.custom_name, ensure_ascii=False)
    if command.lore:
        lore_lines = [json.dumps(line, ensure_ascii=False) for line in command.lore.splitlines() if line.strip()]
        if lore_lines:
            components['minecraft:lore'] = f'[{",".join(lore_lines)}]'

    for prefix, config in COMPONENT_REGISTRY.items():
        related_manager = getattr(command, prefix)
        if related_manager.exists():
            component_part = config['generate_component'](related_manager)
            components.update(component_part)

    return components


def get_compatible_components(request):
    version_pk = request.GET.get('version_id')
    component_type = request.GET.get('type')

    if not version_pk or not component_type:
        return JsonResponse({'error':'Missing parameters'}, status=400)

    try:
        target_version = get_object_or_404(MinecraftVersion, pk=int(version_pk))
        target_ordering_id = target_version.ordering_id
    except (ValueError, TypeError):
        return JsonResponse({'error':'Invalid version_id'}, status=400)

    version_filter = (
        Q(min_version__ordering_id__lte=target_ordering_id) | Q(min_version__isnull=True)
    ) & (
        Q(max_version__ordering_id__gte=target_ordering_id) | Q(max_version__isnull=True)
    )

    data = []
    queryset = None

    if component_type == 'enchantment':
        queryset = Enchantment.objects.filter(version_filter).order_by('enchant_type', 'name')
    elif component_type == 'attribute':
        queryset = AttributeType.objects.filter(version_filter).order_by('name')
    elif component_type == 'potion_effect':
        queryset = PotionEffectType.objects.filter(version_filter).order_by('name')
    # --- 新增：处理法术组件的请求 ---
    elif component_type == 'spell':
        queryset = Spell.objects.filter(version_filter).order_by('name')
    # --- 新增结束 ---
    else:
        # 对于不支持动态加载的组件（如烟花），返回空列表
        return JsonResponse([], safe=False)

    if queryset:
        field = VersionedModelChoiceField(queryset=queryset)
        data = [{'id': obj.pk, 'text': field.label_from_instance(obj)} for obj in queryset]

    return JsonResponse(data, safe=False)


# ==============================================================================
# ==============================================================================
#  新增：实体 (ENTITY) 相关的视图和辅助函数
# ==============================================================================
# ==============================================================================

# --- 1. 新的SNBT格式化函数，专为实体NBT设计 ---
# mc_commands/views.py

def _entity_nbt_to_string(data):
    """
    【最终修正版】的序列化器。
    它能正确合并 _raw_nbt，并能将所有字符串（包括JSON格式的字符串）正确地用双引号包裹。
    """
    if isinstance(data, dict):
        raw_parts = data.pop('_raw_nbt', [])
        
        items = [f"{k}:{_entity_nbt_to_string(v)}" for k, v in data.items() if v is not None]
        
        all_parts = items + raw_parts
        return f"{{{','.join(filter(None, all_parts))}}}"
    
    if isinstance(data, list):
        return f"[{','.join([_entity_nbt_to_string(item) for item in data])}]"

    if isinstance(data, str):
        # --- 核心修改点：对所有字符串（包括内容是JSON的字符串）都使用 json.dumps ---
        # 这会正确地为其添加双引号并处理内部的转义字符。
        return json.dumps(data, ensure_ascii=False)

    if isinstance(data, bool): return '1b' if data else '0b'
    if isinstance(data, int): return f"{data}b"
    if isinstance(data, float): return f"{data}f"

    return str(data)
# --- 2. 更新实体索引视图 ---

@login_required
def entity_index(request):
    """
    更新后的视图，用于显示用户创建的实体列表。
    """
    entity_list = GeneratedEntity.objects.filter(user=request.user).order_by("-updated_at")
    context = {
        'entity_list': entity_list,
    }
    return render(request, 'MC_command/entity/index.html', context)


# --- 3. 实体详情、创建、编辑、删除视图 ---

@login_required
def entity_detail(request, entity_id):
    """显示单个实体配置的详情和生成的 /summon 命令。"""
    entity_obj = get_object_or_404(GeneratedEntity, pk=entity_id, user=request.user)

    nbt_data = generate_entity_nbt(entity_obj)

    # --- 核心修改点：调用正确的序列化函数 ---
    nbt_string = _to_snbt(nbt_data) 

    summon_command = f"/summon {entity_obj.entity_type.entity_id} ~ ~1 ~ {nbt_string}"

    context = {
        'entity': entity_obj,
        'summon_command_string': summon_command,
        'data_structure_json': json.dumps(nbt_data, indent=4, ensure_ascii=False),
    }
    return render(request, 'MC_command/entity/detail.html', context)


@login_required
def entity_create(request):
    """【修改后】处理实体创建的视图，增加了AEC表单集和传递给模板的数据。"""
    AttributeFormSet = generic_inlineformset_factory(AppliedAttribute, form=AppliedAttributeForm, extra=1, can_delete=True)
    PotionEffectFormSet = generic_inlineformset_factory(AppliedPotionEffect, form=AppliedPotionEffectForm, extra=1, can_delete=True)
    ComponentFormSet = inlineformset_factory(GeneratedEntity, AppliedEntityComponent, form=AppliedEntityComponentForm, extra=1, can_delete=True)
    EquipmentFormSet = inlineformset_factory(GeneratedEntity, EntityEquipmentSlot, form=EntityEquipmentSlotForm, extra=1, can_delete=True)
    TradeFormSet = inlineformset_factory(GeneratedEntity, TradeRecipe, form=TradeRecipeForm, extra=1, can_delete=True)
    # --- 新增：为AEC属性创建表单集 (max_num=1 保证一对一关系) ---
    AECFormSet = inlineformset_factory(GeneratedEntity, AreaEffectCloudProperties, form=AreaEffectCloudPropertiesForm, extra=1, can_delete=True, max_num=1)

    if request.method == 'POST':
        form = GeneratedEntityForm(request.POST)
        formsets = {
            'attributes': AttributeFormSet(request.POST, prefix='attributes'),
            'potion_effects': PotionEffectFormSet(request.POST, prefix='potions'),
            'components': ComponentFormSet(request.POST, prefix='components'),
            'equipment': EquipmentFormSet(request.POST, prefix='equipment'),
            'trades': TradeFormSet(request.POST, prefix='trades'),
            'aec_properties': AECFormSet(request.POST, prefix='aec'), # <-- 新增
        }

        if form.is_valid() and all(fs.is_valid() for fs in formsets.values()):
            with transaction.atomic():
                entity_instance = form.save(commit=False)
                entity_instance.user = request.user
                entity_instance.save()
                # Django 的 M2M 字段需要先保存主实例
                form.save_m2m()

                for fs in formsets.values():
                    fs.instance = entity_instance
                    fs.save()

            return redirect(reverse('MC_command:entity_detail', args=[entity_instance.id]))
        # else: (验证失败的打印逻辑可以保留用于调试)
        #     ...

    else: # GET 请求
        form = GeneratedEntityForm()
        formsets = {
            'attributes': AttributeFormSet(prefix='attributes'),
            'potion_effects': PotionEffectFormSet(prefix='potions'),
            'components': ComponentFormSet(prefix='components'),
            'equipment': EquipmentFormSet(prefix='equipment'),
            'trades': TradeFormSet(prefix='trades'),
            'aec_properties': AECFormSet(prefix='aec'), # <-- 新增
        }

    # --- 新增：准备实体类型数据给JS使用 ---
    entity_type_data = {et.pk: et.entity_id for et in EntityType.objects.all()}

    context = {
        'form': form,
        'formsets': formsets,
        'form_title': '创建新实体配置',
        'entity_type_data_json': json.dumps(entity_type_data), # <-- 新增
    }
    return render(request, 'MC_command/entity/entity_form.html', context)


@login_required
def entity_edit(request, entity_id):
    """【修改后】处理实体编辑的视图，增加了AEC表单集和传递给模板的数据。"""
    entity_obj = get_object_or_404(GeneratedEntity, pk=entity_id, user=request.user)

    AttributeFormSet = generic_inlineformset_factory(AppliedAttribute, form=AppliedAttributeForm, extra=1, can_delete=True)
    PotionEffectFormSet = generic_inlineformset_factory(AppliedPotionEffect, form=AppliedPotionEffectForm, extra=1, can_delete=True)
    ComponentFormSet = inlineformset_factory(GeneratedEntity, AppliedEntityComponent, form=AppliedEntityComponentForm, extra=1, can_delete=True)
    EquipmentFormSet = inlineformset_factory(GeneratedEntity, EntityEquipmentSlot, form=EntityEquipmentSlotForm, extra=1, can_delete=True)
    TradeFormSet = inlineformset_factory(GeneratedEntity, TradeRecipe, form=TradeRecipeForm, extra=1, can_delete=True)
    # --- 新增：为AEC属性创建表单集 ---
    AECFormSet = inlineformset_factory(GeneratedEntity, AreaEffectCloudProperties, form=AreaEffectCloudPropertiesForm, extra=1, can_delete=True, max_num=1)

    if request.method == 'POST':
        form = GeneratedEntityForm(request.POST, instance=entity_obj)
        formsets = {
            'attributes': AttributeFormSet(request.POST, instance=entity_obj, prefix='attributes'),
            'potion_effects': PotionEffectFormSet(request.POST, instance=entity_obj, prefix='potions'),
            'components': ComponentFormSet(request.POST, instance=entity_obj, prefix='components'),
            'equipment': EquipmentFormSet(request.POST, instance=entity_obj, prefix='equipment'),
            'trades': TradeFormSet(request.POST, instance=entity_obj, prefix='trades'),
            'aec_properties': AECFormSet(request.POST, instance=entity_obj, prefix='aec'), # <-- 新增
        }

        if form.is_valid() and all(fs.is_valid() for fs in formsets.values()):
            with transaction.atomic():
                entity_instance = form.save() # m2m 会在这里被自动处理
                for fs in formsets.values():
                    fs.save()

            return redirect(reverse('MC_command:entity_detail', args=[entity_instance.id]))

    else: # GET 请求
        form = GeneratedEntityForm(instance=entity_obj)
        formsets = {
            'attributes': AttributeFormSet(instance=entity_obj, prefix='attributes'),
            'potion_effects': PotionEffectFormSet(instance=entity_obj, prefix='potions'),
            'components': ComponentFormSet(instance=entity_obj, prefix='components'),
            'equipment': EquipmentFormSet(instance=entity_obj, prefix='equipment'),
            'trades': TradeFormSet(instance=entity_obj, prefix='trades'),
            'aec_properties': AECFormSet(instance=entity_obj, prefix='aec'), # <-- 新增
        }

    # --- 新增：准备实体类型数据给JS使用 ---
    entity_type_data = {et.pk: et.entity_id for et in EntityType.objects.all()}

    context = {
        'form': form,
        'formsets': formsets,
        'entity': entity_obj,
        'form_title': '编辑实体配置',
        'entity_type_data_json': json.dumps(entity_type_data), # <-- 新增
    }
    return render(request, 'MC_command/entity/entity_form.html', context)

@login_required
@require_POST
def entity_delete(request, entity_id):
    """处理实体删除的视图。"""
    entity_obj = get_object_or_404(GeneratedEntity, pk=entity_id, user=request.user)
    entity_obj.delete()
    return redirect(reverse('MC_command:entity_index'))
# --- 精度控制常量 ---
CENTS = Decimal('0.01')




# ========================
# 页面渲染视图
# ========================
from .game_engine import score_blackjack, deal_blackjack_card, generate_rigged_hands_zjh
from .models import CasinoGameSession
# ==========================
# 💰 游戏底注配置
# ==========================
GAME_MIN_BETS = {
    'rps': Decimal('20.00'),       # 石头剪刀布：最低 20
    'zjh': Decimal('100.00'),      # 扎金花(Pro)：最低 100 (因为倍率高)
    'blackjack': Decimal('50.00'), # 21点：最低 50
}

@login_required
def casino_lobby(request):
    """娱乐大厅：只显示游戏入口"""
    wallet, _ = UserWallet.objects.get_or_create(user=request.user)
    return render(request, 'MC_command/casino/lobby.html', {'wallet': wallet})

@login_required
def game_view_rps(request):
    """石头剪刀布页面"""
    wallet, _ = UserWallet.objects.get_or_create(user=request.user)
    return render(request, 'MC_command/casino/game_rps.html', {'wallet': wallet})

@login_required
def game_view_zjh(request):
    """扎金花页面"""
    wallet, _ = UserWallet.objects.get_or_create(user=request.user)
    return render(request, 'MC_command/casino/game_zjh.html', {'wallet': wallet})

# --- 页面路由 ---
@login_required
def game_view_blackjack(request):
    wallet, _ = UserWallet.objects.get_or_create(user=request.user)
    return render(request, 'MC_command/casino/game_blackjack.html', {'wallet': wallet})

# --- 扎金花路由 ---
@login_required
def game_view_zjh_pro(request):
    wallet, _ = UserWallet.objects.get_or_create(user=request.user)
    return render(request, 'MC_command/casino/game_zjh_pro.html', {'wallet': wallet})

# ========================
# 游戏算法与黑幕逻辑
# ========================


def _calculate_payout(wallet, bet_amount, odds):
    """
    统一的派彩计算器 (含向下取整和向上抽水)
    """
    # 1. 理论总奖金 (本金 * 赔率)
    raw_gross_win = bet_amount * Decimal(str(odds))
    # 【规则1：用户赢钱向下取整】
    gross_win = raw_gross_win.quantize(CENTS, rounding=ROUND_FLOOR)

    # 2. 计算抽水 (只对纯利润抽水)
    profit = gross_win - bet_amount
    fee = Decimal('0.00')
    
    if profit > 0:
        fee_rate = Decimal(str(wallet.fee_rate))
        raw_fee = profit * fee_rate
        # 【规则2：赌场抽成向上取整】
        fee = raw_fee.quantize(CENTS, rounding=ROUND_CEILING)
    
    final_payout = gross_win - fee
    return final_payout, fee

def _play_rps(user_choice, black_curtain_rate):
    """
    石头剪刀布逻辑
    black_curtain_rate < 1.0 : 玩家容易输 (系统读心)
    black_curtain_rate > 1.0 : 玩家容易赢 (系统放水)
    """
    choices = ['rock', 'paper', 'scissors']
    # 定义克制关系
    beats = {'rock': 'scissors', 'paper': 'rock', 'scissors': 'paper'}
    loses_to = {'rock': 'paper', 'paper': 'scissors', 'scissors': 'rock'}
    
    # 基础概率
    rand = random.random()
    
    # --- 黑幕介入 ---
    # 如果玩家是"重点监控(黑幕值低)"，系统有概率直接出克制牌
    if black_curtain_rate < 0.9:
        # 霉运模式：例如 0.6 的黑幕值，意味着有 40% 的概率系统作弊
        cheat_prob = 1.0 - black_curtain_rate 
        if rand < cheat_prob:
            # 系统作弊：选择克制用户的牌
            sys_choice = loses_to[user_choice]
            return sys_choice, 'lose', '庄家看穿了你的意图！'
            
    # 如果玩家是"欧皇(黑幕值高)"
    if black_curtain_rate > 1.1:
        cheat_prob = black_curtain_rate - 1.0
        if rand < cheat_prob:
            # 系统放水：选择被用户克制的牌
            sys_choice = beats[user_choice]
            return sys_choice, 'win', '运气爆棚！'

    # 正常随机
    sys_choice = random.choice(choices)
    
    if user_choice == sys_choice:
        return sys_choice, 'draw', '平局，退还本金'
    elif beats[user_choice] == sys_choice:
        return sys_choice, 'win', '恭喜获胜！'
    else:
        return sys_choice, 'lose', '遗憾落败'

def _play_zjh(black_curtain_rate):
    """
    扎金花逻辑 (简化版：只比大小，不比花色)
    黑幕重点：制造'冤家牌' (Bad Beat)
    """
    # 牌力值：豹子(1000+) > 同花顺(800+) > 同花(600+) > 顺子(400+) > 对子(200+) > 单张
    # 这里简化生成逻辑，直接生成"分数"
    
    def generate_hand_score():
        r = random.random()
        if r < 0.01: return random.randint(1000, 1100), "豹子" # 1%
        if r < 0.05: return random.randint(600, 700), "同花"   # 4%
        if r < 0.15: return random.randint(400, 500), "顺子"   # 10%
        if r < 0.40: return random.randint(200, 300), "对子"   # 25%
        return random.randint(1, 100), "散牌"                 # 60%

    user_score, user_desc = generate_hand_score()
    sys_score, sys_desc = generate_hand_score()
    
    # --- 黑幕介入 ---
    # 所谓冤家牌：如果你拿了同花，庄家必拿豹子；你拿对子，庄家拿大对子。
    if black_curtain_rate < 0.8:
        # 霉运模式：如果玩家拿到了好牌(>200)，系统强制生成一副比玩家大一点点的牌
        if user_score > 200 and random.random() < 0.7:
            sys_score = user_score + random.randint(1, 50)
            # 修正描述
            if sys_score > 1000: sys_desc = "更大的豹子"
            elif sys_score > 600: sys_desc = "更大的同花"
            elif sys_score > 400: sys_desc = "更大的顺子"
            else: sys_desc = "更大的对子"

    # 判定
    outcome = 'lose'
    if user_score > sys_score: outcome = 'win'
    elif user_score == sys_score: outcome = 'draw'
    
    details = {
        'user_hand': user_desc, 
        'sys_hand': sys_desc, 
        'score_diff': user_score - sys_score
    }
    return details, outcome


# ========================
# 统一 API 入口
# ========================

@login_required
@require_POST
def casino_api(request, game_type):
    user = request.user
    wallet = get_object_or_404(UserWallet, user=user)
    
    try:
        bet_amount = Decimal(request.POST.get('bet', '0'))
    except:
        return JsonResponse({'status': 'error', 'msg': '金额错误'})

    # --- 新增：底注校验 ---
    min_bet = GAME_MIN_BETS.get(game_type, Decimal('10.00')) # 默认10
    if bet_amount < min_bet:
        return JsonResponse({'status': 'error', 'msg': f'该游戏最低起注 {min_bet} 金币'})
    # --------------------

    if bet_amount <= 0: return JsonResponse({'status': 'error', 'msg': '下注需>0'})
    if wallet.balance < bet_amount: return JsonResponse({'status': 'error', 'msg': '余额不足'})

    # 1. 扣除本金
    # 这里稍微改一下逻辑：如果是扎金花等复杂游戏，可能先扣钱，最后再算输赢
    GameTransaction.objects.create(
        wallet=wallet, amount=bet_amount, trans_type='game_bet', description=f"参与 {game_type}"
    )

    result_data = {}
    payout = Decimal('0.00')
    fee = Decimal('0.00')
    is_win = False
    
    # --- 游戏分发 ---
    
    if game_type == 'rps':
        user_choice = request.POST.get('choice')
        sys_choice, outcome, msg = _play_rps(user_choice, wallet.black_curtain_rate)
        
        result_data = {'sys_choice': sys_choice, 'outcome': outcome}
        
        if outcome == 'win':
            is_win = True
            payout, fee = _calculate_payout(wallet, bet_amount, 2.0) # 1赔2
        elif outcome == 'draw':
            payout = bet_amount # 退还本金
            msg += " (退还本金)"

    elif game_type == 'zjh':
        # 极速扎金花赔率高，假设 1赔3 (赢了拿回3倍)
        details, outcome = _play_zjh(wallet.black_curtain_rate)
        msg = f"你: {details['user_hand']} VS 庄: {details['sys_hand']}"
        
        result_data = details
        
        if outcome == 'win':
            is_win = True
            msg = "你赢了！" + msg
            payout, fee = _calculate_payout(wallet, bet_amount, 3.0)
        elif outcome == 'draw':
             payout = bet_amount
             msg = "平局 " + msg
        else:
            msg = "你输了..." + msg

    # 2. 派彩
    if payout > 0:
        trans_type = 'game_win' if is_win else 'admin_grant' # 平局算退款
        desc = f"赢取 {game_type} (抽水 {fee})" if is_win else f"{game_type} 平局退款"
        
        GameTransaction.objects.create(
            wallet=wallet, amount=payout, trans_type=trans_type, description=desc
        )

    return JsonResponse({
        'status': 'success',
        'balance': wallet.balance,
        'is_win': is_win,
        'payout': payout,
        'msg': msg,
        'data': result_data
    })

# ==========================================
# 统一状态机 API
# ==========================================

@login_required
@require_POST
def casino_action_api(request):
    """
    处理所有分步博弈的逻辑
    Action: start, hit, stand, bet, fold, look, compare
    """
    action = request.POST.get('action')
    game_type = request.POST.get('game_type')
    user = request.user
    wallet = get_object_or_404(UserWallet, user=user)
    
    # 1. 开始新游戏 (Start)
    if action == 'start':
        # 清理旧会话
        CasinoGameSession.objects.filter(user=user, is_active=True).update(is_active=False)
        
        # 扣除底注
        try:
            ante = Decimal(request.POST.get('ante', '10'))
        except:
            return JsonResponse({'status': 'error', 'msg': '金额格式错误'})

        # --- 新增：底注校验 ---
        min_bet = GAME_MIN_BETS.get(game_type, Decimal('10.00'))
        if ante < min_bet:
            return JsonResponse({'status': 'error', 'msg': f'{game_type} 场次最低起注 {min_bet} 金币！穷鬼勿进！'})
        # --------------------
        if wallet.balance < ante: return JsonResponse({'status':'error', 'msg':'余额不足'})
        
        # 创建新会话
        session = CasinoGameSession.objects.create(user=user, game_type=game_type, state_data={})
        state = {}
        
        # --- 初始化 21点 ---
        if game_type == 'blackjack':
            GameTransaction.objects.create(wallet=wallet, amount=ante, trans_type='game_bet', description="21点底注")
            
            # 发初始牌
            p_card1 = deal_blackjack_card(0, 1.0) # 第一张随意
            p_card2 = deal_blackjack_card(p_card1['val'], wallet.black_curtain_rate) # 第二张受控
            d_card1 = deal_blackjack_card(0, 1.0) # 庄家明牌
            
            state = {
                'step': 'playing',
                'pot': float(ante),
                'p_hand': [p_card1, p_card2],
                'd_hand': [d_card1], # 庄家暗牌暂不生成，结算时再生成，方便控制
                'd_hidden_val': 0 # 占位
            }

        # --- 初始化 扎金花 ---
        elif game_type == 'zjh':
            GameTransaction.objects.create(wallet=wallet, amount=ante, trans_type='game_bet', description="扎金花底注")
            
            # 此时就已经决定了输赢结果（预埋黑幕），但玩家不知道
            p_cards, d_cards, p_score, d_score = generate_rigged_hands_zjh(wallet.black_curtain_rate)
            
            state = {
                'step': 'blind', # 闷牌阶段
                'pot': float(ante),
                'ante': float(ante),
                'current_bet': float(ante),
                'p_cards': p_cards,   # 真实牌数据
                'd_cards': d_cards,
                'p_score': p_score,
                'd_score': d_score,
                'has_looked': False
            }

        session.state_data = state
        session.save()
        
        return JsonResponse({'status': 'success', 'state': state, 'balance': wallet.balance})

    # 2. 获取当前会话
    session = CasinoGameSession.objects.filter(user=user, is_active=True, game_type=game_type).last()
    if not session: return JsonResponse({'status':'error', 'msg':'游戏已结束或不存在'})
    state = session.state_data
    
    # ==================== 21点 逻辑 ====================
    if game_type == 'blackjack':
        p_score = score_blackjack(state['p_hand'])
        
        if action == 'hit':
            # 要牌：根据黑幕发牌
            new_card = deal_blackjack_card(p_score, wallet.black_curtain_rate)
            state['p_hand'].append(new_card)
            new_score = score_blackjack(state['p_hand'])
            
            if new_score > 21:
                # 爆牌，直接输
                state['step'] = 'finished'
                session.is_active = False
                msg = "爆牌了！你输了。"
            else:
                msg = "要了一张牌..."
                
        elif action == 'stand':
            # 停牌：庄家开始行动
            # 庄家规则：小于17必须补牌
            d_hand = state['d_hand']
            d_score = score_blackjack(d_hand)
            
            # 黑幕：如果玩家点数大，且玩家是“非酋”，庄家极大概率拿到刚好比玩家大的牌
            while d_score < 17:
                # 这里简化：直接发牌
                card = deal_blackjack_card(d_score, 1.0) # 庄家正常发牌
                d_hand.append(card)
                d_score = score_blackjack(d_hand)
            
            state['d_hand'] = d_hand # 更新庄家牌
            state['step'] = 'finished'
            session.is_active = False
            # 定义计算抽水的辅助逻辑 (利用闭包或直接写)
            def apply_fee(gross_win, principal):
                profit = gross_win - principal
                fee = Decimal('0.00')
                if profit > 0:
                    # 向上取整计算抽水
                    raw_fee = profit * Decimal(str(wallet.fee_rate))
                    fee = raw_fee.quantize(CENTS, rounding=ROUND_CEILING)
                return gross_win - fee, fee
            # 结算逻辑
            if d_score > 21:
                # 赢：拿回双倍底注
                principal = Decimal(str(state['pot'])) # 本金
                gross_win = principal * 2
                
                real_payout, fee = apply_fee(gross_win, principal) # <--- 计算抽水
                
                wallet.balance += real_payout
                
                # 记录带抽水的流水
                GameTransaction.objects.create(
                    wallet=wallet, amount=real_payout, trans_type='game_win', 
                    description=f"21点赢取 (庄爆, 抽水{fee})"
                )
                msg = f"庄家爆牌！你赢了 {real_payout} (含本金, 抽水{fee})"

            elif d_score >= p_score: 
                # 输或平 (21点通常庄赢平局，或者你可以由自己定规则)
                # 这里假设是庄赢平局，不退钱
                msg = f"庄家 {d_score} 点，你 {p_score} 点。你输了。"
                # 如果你想做平局退款：
                # if d_score == p_score:
                #    wallet.balance += Decimal(str(state['pot']))
                #    msg = "平局退还本金"
            else:
                # 赢：点数大
                principal = Decimal(str(state['pot']))
                gross_win = principal * 2
                
                real_payout, fee = apply_fee(gross_win, principal) # <--- 计算抽水
                
                wallet.balance += real_payout
                
                GameTransaction.objects.create(
                    wallet=wallet, amount=real_payout, trans_type='game_win', 
                    description=f"21点赢取 (点数胜, 抽水{fee})"
                )
                msg = f"庄家 {d_score} 点，你 {p_score} 点。你赢了 {real_payout} (含本金, 抽水{fee})！"
            
            wallet.save()
            
    # ==================== 沉浸式扎金花 逻辑 ====================
    elif game_type == 'zjh':
        bet_amt = Decimal(request.POST.get('amount', '0'))
        
        if action == 'look':
            state['has_looked'] = True
            state['step'] = 'seen'
            msg = "你查看了手牌。"
            
        elif action == 'bet':
            # 加注
            if wallet.balance < bet_amt: return JsonResponse({'status':'error', 'msg':'余额不足'})
            GameTransaction.objects.create(wallet=wallet, amount=bet_amt, trans_type='game_bet', description="扎金花加注")
            state['pot'] += float(bet_amt) * 2 # 假定庄家跟注
            state['current_bet'] = float(bet_amt)
            msg = "你加注了，庄家跟注。"
            
        elif action == 'fold':
            # 弃牌
            state['step'] = 'folded'
            session.is_active = False
            msg = "你弃牌了，庄家赢走底池。"
            
        elif action == 'compare':
            # --- 修改开始：支持梭哈 (All-in) 开牌 ---
            
            # 1. 计算理论需要的开牌费用 (通常是当前单注的2倍)
            required_cost = Decimal(str(state['current_bet'])) * 2
            
            # 2. 确定实际扣款金额
            if wallet.balance < 0:
                return JsonResponse({'status':'error', 'msg':'余额不足，无法开牌'})
            
            # 如果余额不足以支付标准费用，就触发梭哈逻辑：扣光所有余额
            if wallet.balance < required_cost:
                actual_cost = wallet.balance
                note = " (梭哈开牌!)"
            else:
                actual_cost = required_cost
                note = " (开牌)"

            # 3. 写入流水
            GameTransaction.objects.create(
                wallet=wallet, 
                amount=actual_cost, 
                trans_type='game_bet', 
                description=f"扎金花{note}"
            )
            
            # 4. 更新底池和状态
            state['pot'] += float(actual_cost)
            state['step'] = 'finished'
            session.is_active = False
            
            # 5. 结算比大小
            p_score = state['p_score']
            d_score = state['d_score']
            
            # 构造赢牌/输牌的消息
            # 注意：这里 state['d_cards'] 已经在生成时确定了
            # 我们需要在 msg 中告诉前端具体是什么牌型
            
            if p_score > d_score:
                # 1. 计算总奖金 (整个底池)
                gross_win = Decimal(str(state['pot']))
                
                # 2. 计算玩家投入的本金 (底池的一半，因为是1v1且庄家跟注)
                # 注意：如果是"梭哈"情况，底池可能不完全是2倍关系，但PVE里pot包含庄家跟注
                # PVE逻辑简化：底池的一半是你的本金，一半是赚的
                principal = gross_win / 2 
                
                # 3. 计算利润
                profit = gross_win - principal
                
                # 4. 计算抽水 (向上取整)
                fee = Decimal('0.00')
                if profit > 0:
                    raw_fee = profit * Decimal(str(wallet.fee_rate))
                    fee = raw_fee.quantize(CENTS, rounding=ROUND_CEILING)
                
                # 5. 实际派彩
                final_payout = gross_win - fee
                wallet.balance += final_payout
                
                GameTransaction.objects.create(
                    wallet=wallet, 
                    amount=final_payout, 
                    trans_type='game_win', 
                    description=f"扎金花赢取{note} (抽水{fee})"
                )
                msg = f"你赢了！{note} 到手:{final_payout} (抽水{fee})"
                is_win = True
            

            elif p_score == d_score:
                 # 平局退回底池的一半或者全部？这里简单处理退回全部（当做赢）或者退本金
                 # 扎金花通常没有平局（比花色），这里简单处理为退钱
                 refund = Decimal(str(state['pot']))
                 wallet.balance += refund
                 msg = "平局，退还底池。"
                 is_win = True # 算作不输
            else:
                msg = f"庄家赢了。{note}"
                is_win = False
            
            wallet.save()
            state['is_win'] = is_win
            # --- 修改结束 ---

    # 保存状态
    session.state_data = state
    session.save()
    
    return JsonResponse({'status': 'success', 'state': state, 'balance': wallet.balance, 'msg': msg if 'msg' in locals() else ''})