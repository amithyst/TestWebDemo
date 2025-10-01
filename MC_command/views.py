# amithyst/testwebdemo/TestWebDemo-aa984f0e28b37ace0788b6c8c16a1b3d096ffd1a/MC_command/views.py
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
                     GeneratedEntity, EntityEquipmentSlot, TradeRecipe,
                     AppliedEntityComponent, AppliedAttribute, AppliedPotionEffect)

from .models import GeneratedCommand
from .forms import (
    GeneratedCommandForm, VersionedModelChoiceField, 
    AppliedFireworkExplosionAdminForm, SpellInfusionForm,
    # --- 以下是为实体视图新添加的，请确保它们都在这里 ---
    GeneratedEntityForm, EntityEquipmentSlotForm, TradeRecipeForm,
    AppliedEntityComponentForm, AppliedAttributeForm, AppliedPotionEffectForm
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

# 用下面的函数替换掉您文件中的 _to_snbt 函数
def _to_snbt(data, parent_key=None):
    """
    将 Python 对象转换为 Minecraft 命令所用的 SNBT 字符串。
    此最终版本使用基于“键”的策略来精确控制字符串是否需要加引号。
    """
    # 规则1：这些键所对应的字符串值，总是需要加引号
    QUOTED_STRING_KEYS = {'AttributeName', 'Name'}

    # 规则2：这些键所对应的字符串值，总是不加引号
    UNQUOTED_STRING_KEYS = {'id', 
                            # 'Slot'
                            }

    WHETHER_TO_QUOTE = True  # 默认情况下，字符串值会被加引号

    # --- 函数主体 ---

    # 处理字典类型
    if isinstance(data, dict):
        items = []
        for k, v in data.items():
            # 特殊处理：display 标签的结构是固定的，单独处理，不进入通用递归
            if k == 'display':
                display_items = []
                if 'Name' in v and isinstance(v['Name'], str):
                    json_str = json.dumps({'text':v['Name']}, ensure_ascii=False, separators=(',', ':'))
                    display_items.append(f"Name:'{json_str}'")
                # if 'Lore' in v and isinstance(v['Lore'], list):
                #     lore_list = [json.dumps({'text':line}, ensure_ascii=False, separators=(',', ':')) for line in v['Lore']]
                #     display_items.append(f"Lore:[{','.join(lore_list)}]")
                if 'Lore' in v and isinstance(v['Lore'], list):
                    lore_list = [f"'{json.dumps({'text':line}, ensure_ascii=False, separators=(',', ':'))}'" for line in v['Lore']]
                    display_items.append(f"Lore:[{','.join(lore_list)}]")
                items.append(f"display:{{{','.join(display_items)}}}")
                continue

            # 对于其他所有键，递归调用本函数，并将当前键(k)作为 parent_key 传下去
            items.append(f"{k}:{_to_snbt(v, parent_key=k)}")
        return f"{{{','.join(items)}}}"

    # 处理列表类型
    if isinstance(data, list):
        # 列表中的元素继承列表的键(parent_key)
        return f"[{','.join([_to_snbt(item, parent_key=parent_key) for item in data])}]"

    # 处理字符串类型
    if isinstance(data, str):
        # UUID 格式特殊，直接返回，不加引号
        if data.startswith('[I;'):
            return data
        
        # 应用规则1：如果字符串的键在 QUOTED_STRING_KEYS 列表中，就加引号
        if parent_key in QUOTED_STRING_KEYS:
            return json.dumps(data, ensure_ascii=False)
        
        # 应用规则2：如果字符串的键在 UNQUOTED_STRING_KEYS 列表中，就不加引号
        if parent_key in UNQUOTED_STRING_KEYS:
            return data

        # 对于未定义的其他情况，为安全起见默认加上引号
        if WHETHER_TO_QUOTE:
            return json.dumps(data, ensure_ascii=False)
        else:
            return data

    # 处理布尔和数字类型
    if isinstance(data, bool):return '1b' if data else '0b'
    if isinstance(data, (int, float)):return str(data)

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

def _build_nbt_tag_structure(command:GeneratedCommand) -> dict:
    """
    REVISED:Builds a pure Python dictionary for the NBT tag structure.
    The final string formatting is now handled by the _to_snbt serializer.
    """
    nbt_data = {}
    display = {}

    if command.custom_name:
        # Store raw string. The serializer will handle JSON formatting.
        display['Name'] = command.custom_name
    if command.lore:
        # Store raw list of strings. The serializer will handle JSON formatting.
        lore_lines = [line for line in command.lore.splitlines() if line.strip()]
        if lore_lines:
            display['Lore'] = lore_lines
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

def _entity_nbt_to_string(data):
    """
    将Python字典递归转换为实体命令所用的SNBT字符串。
    这个版本比物品的 _to_snbt 更通用，能处理字节(b)/浮点(f)等类型。
    """
    if isinstance(data, dict):
        # 移除内部使用的、值为None的键
        items = [f"{k}:{_entity_nbt_to_string(v)}" for k, v in data.items() if v is not None]
        return f"{{{','.join(items)}}}"
    
    if isinstance(data, list):
        return f"[{','.join([_entity_nbt_to_string(item) for item in data])}]"

    if isinstance(data, str):
        # 如果字符串本身就是个JSON或者已经被正确引用，直接返回
        if (data.startswith(('{', '[')) and data.endswith(('}', ']'))) or \
           (data.startswith("'") and data.endswith("'")) or \
           (data.startswith('"') and data.endswith('"')):
            return data
        # 否则，使用JSON库来安全地添加引号并转义
        return json.dumps(data, ensure_ascii=False)

    if isinstance(data, bool): return '1b' if data else '0b'
    
    # 依据Python类型来猜测NBT类型
    if isinstance(data, int): return f"{data}b" # 默认为byte类型，如有需要可扩展为Short/Int/Long
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
    
    # 1. 调用components.py中的函数生成NBT字典
    nbt_data = generate_entity_nbt(entity_obj)
    
    # 2. 将NBT字典格式化为字符串
    nbt_string = _entity_nbt_to_string(nbt_data)
    
    # 3. 组装最终命令
    summon_command = f"/summon {entity_obj.entity_type.entity_id} ~ ~1 ~ {nbt_string}"
    
    context = {
        'entity': entity_obj,
        'summon_command_string': summon_command,
        'data_structure_json': json.dumps(nbt_data, indent=4, ensure_ascii=False),
    }
    return render(request, 'MC_command/entity/detail.html', context)

@login_required
def entity_create(request):
    """处理实体创建的视图。"""
    # 为每个关联模型定义内联表单集
    # a. 通用关系表单集 (属性和药水效果)
    AttributeFormSet = generic_inlineformset_factory(AppliedAttribute, form=AppliedAttributeForm, extra=1, can_delete=True)
    PotionEffectFormSet = generic_inlineformset_factory(AppliedPotionEffect, form=AppliedPotionEffectForm, extra=1, can_delete=True)
    
    # b. 标准外键关系表单集
    ComponentFormSet = inlineformset_factory(GeneratedEntity, AppliedEntityComponent, form=AppliedEntityComponentForm, extra=1, can_delete=True)
    EquipmentFormSet = inlineformset_factory(GeneratedEntity, EntityEquipmentSlot, form=EntityEquipmentSlotForm, extra=1, can_delete=True)
    TradeFormSet = inlineformset_factory(GeneratedEntity, TradeRecipe, form=TradeRecipeForm, extra=1, can_delete=True)

    if request.method == 'POST':
        form = GeneratedEntityForm(request.POST)
        formsets = {
            'attributes': AttributeFormSet(request.POST, prefix='attributes'),
            'potion_effects': PotionEffectFormSet(request.POST, prefix='potions'),
            'components': ComponentFormSet(request.POST, prefix='components'),
            'equipment': EquipmentFormSet(request.POST, prefix='equipment'),
            'trades': TradeFormSet(request.POST, prefix='trades'),
        }

        if form.is_valid() and all(fs.is_valid() for fs in formsets.values()):
            with transaction.atomic():
                entity_instance = form.save(commit=False)
                entity_instance.user = request.user
                entity_instance.save()

                for fs in formsets.values():
                    fs.instance = entity_instance
                    fs.save()
            
            return redirect(reverse('MC_command:entity_detail', args=[entity_instance.id]))
        
        # --- 在这里添加 else 块来打印错误 ---
        else:
            print("="*20, "FORM VALIDATION FAILED", "="*20)
            if not form.is_valid():
                print("Main Form Errors:", form.errors)
            for name, fs in formsets.items():
                if not fs.is_valid():
                    print(f"Formset '{name}' Errors:", fs.errors)
                    print(f"Formset '{name}' Non-form Errors:", fs.non_form_errors())
            print("="*58)

    else: # GET 请求
        form = GeneratedEntityForm()
        formsets = {
            'attributes': AttributeFormSet(prefix='attributes'),
            'potion_effects': PotionEffectFormSet(prefix='potions'),
            'components': ComponentFormSet(prefix='components'),
            'equipment': EquipmentFormSet(prefix='equipment'),
            'trades': TradeFormSet(prefix='trades'),
        }

    context = {
        'form': form,
        'formsets': formsets,
        'form_title': '创建新实体配置',
    }
    return render(request, 'MC_command/entity/entity_form.html', context)


@login_required
def entity_edit(request, entity_id):
    """处理实体编辑的视图。"""
    entity_obj = get_object_or_404(GeneratedEntity, pk=entity_id, user=request.user)
    
    # (表单集的定义与 create 视图中完全相同)
    AttributeFormSet = generic_inlineformset_factory(AppliedAttribute, form=AppliedAttributeForm, extra=1, can_delete=True)
    PotionEffectFormSet = generic_inlineformset_factory(AppliedPotionEffect, form=AppliedPotionEffectForm, extra=1, can_delete=True)
    ComponentFormSet = inlineformset_factory(GeneratedEntity, AppliedEntityComponent, form=AppliedEntityComponentForm, extra=1, can_delete=True)
    EquipmentFormSet = inlineformset_factory(GeneratedEntity, EntityEquipmentSlot, form=EntityEquipmentSlotForm, extra=1, can_delete=True)
    TradeFormSet = inlineformset_factory(GeneratedEntity, TradeRecipe, form=TradeRecipeForm, extra=1, can_delete=True)

    if request.method == 'POST':
        form = GeneratedEntityForm(request.POST, instance=entity_obj)
        formsets = {
            'attributes': AttributeFormSet(request.POST, instance=entity_obj, prefix='attributes'),
            'potion_effects': PotionEffectFormSet(request.POST, instance=entity_obj, prefix='potions'),
            'components': ComponentFormSet(request.POST, instance=entity_obj, prefix='components'),
            'equipment': EquipmentFormSet(request.POST, instance=entity_obj, prefix='equipment'),
            'trades': TradeFormSet(request.POST, instance=entity_obj, prefix='trades'),
        }

        if form.is_valid() and all(fs.is_valid() for fs in formsets.values()):
            with transaction.atomic():
                entity_instance = form.save()
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
        }
        
    context = {
        'form': form,
        'formsets': formsets,
        'entity': entity_obj,
        'form_title': '编辑实体配置',
    }
    return render(request, 'MC_command/entity/entity_form.html', context)


@login_required
@require_POST
def entity_delete(request, entity_id):
    """处理实体删除的视图。"""
    entity_obj = get_object_or_404(GeneratedEntity, pk=entity_id, user=request.user)
    entity_obj.delete()
    return redirect(reverse('MC_command:entity_index'))