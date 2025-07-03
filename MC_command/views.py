# amithyst/testwebdemo/TestWebDemo-aa984f0e28b37ace0788b6c8c16a1b3d096ffd1a/MC_command/views.py
from django import forms
# --- 在文件顶部，确保导入以下所有内容 ---
import json
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.forms import inlineformset_factory
from django.db import transaction

from django.http import JsonResponse
from django.db.models import Q
# 修改:引入 Material, ItemType
from .models import Enchantment, AttributeType, PotionEffectType, MinecraftVersion, Material, ItemType
from .models import GeneratedCommand
from .forms import GeneratedCommandForm,VersionedModelChoiceField, AppliedFireworkExplosionAdminForm
from .components import COMPONENT_REGISTRY

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

# --- 增删改查 (CRUD) 视图 ---
# --- 完全替换旧的 CREATE 和 EDIT 视图 ---
# --- Replace the create and edit views with these refactored versions ---
@login_required
def create(request):
    FormSetClasses = {}
    for prefix, config in COMPONENT_REGISTRY.items():
        form_class = config['form']
        # # 如果是烟火组件，就强制使用 AdminForm
        # if prefix == 'firework_explosions':
        #     form_class = AppliedFireworkExplosionAdminForm
        
        FormSetClasses[prefix] = inlineformset_factory(
            GeneratedCommand, 
            config['model'], 
            form=form_class, 
            extra=1, 
            can_delete=True, 
            min_num=0
        )

    if request.method == 'POST':
        form = GeneratedCommandForm(request.POST)
        formsets = {prefix:FormSetClasses[prefix](request.POST, prefix=prefix) for prefix in COMPONENT_REGISTRY.keys()}

        # /-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/
        # /-/-/-/-/-/- START OF MODIFICATION /-/-/-/-/-/
        # /-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/
        all_forms_valid = form.is_valid() and all(fs.is_valid() for fs in formsets.values())

        if all_forms_valid:
            try:
                # Run custom validation only after standard validation passes
                _validate_version_compatibility(
                    form,
                    formsets.get('enchantments'),
                    formsets.get('attributes'),
                    form.cleaned_data['target_version']
                )

                with transaction.atomic():
                    command_instance = form.save(commit=False)
                    command_instance.user = request.user
                    command_instance.save()
                    for prefix, formset in formsets.items():
                        formset.instance = command_instance
                        formset.save()
                    return redirect(reverse('MC_command:detail', args=[command_instance.id]))
            except forms.ValidationError:
                # Custom validation failed, errors are already in the form.
                # The view will now fall through and re-render the form with errors.
                pass
        # If we are here, it means some form was invalid.
        # The view will proceed to render the form with errors below.
        # /-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/
        # /-/-/-/-/-/- END OF MODIFICATION /-/-/-/-/-/
        # /-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/

    else:
        form = GeneratedCommandForm()
        formsets = {prefix:FormSetClasses[prefix](prefix=prefix) for prefix in COMPONENT_REGISTRY.keys()}

    version_data = {v.pk:v.ordering_id for v in MinecraftVersion.objects.all()}
    item_type_data = {it.pk:{'type':it.function_type} for it in ItemType.objects.all()}

    component_data = {
        prefix:{'formset':formsets[prefix], 'verbose_name':config['verbose_name'], 'supported_types':json.dumps(config['supported_function_types'])}
        for prefix, config in COMPONENT_REGISTRY.items()
    }

    context = {
        'form':form,
        'component_data':component_data,
        'form_title':'创建新命令',
        'version_data_json':json.dumps(version_data),
        'item_type_data_json':json.dumps(item_type_data),
    }
    return render(request, 'MC_command/item/command_form.html', context)

@login_required
def edit(request, command_id):
    command_obj = get_object_or_404(GeneratedCommand, pk=command_id, user=request.user)
    FormSetClasses = {}
    for prefix, config in COMPONENT_REGISTRY.items():
        form_class = config['form']
        # 如果是烟火组件，就强制使用 AdminForm
        # if prefix == 'firework_explosions':
        #     form_class = AppliedFireworkExplosionAdminForm
        
        FormSetClasses[prefix] = inlineformset_factory(
            GeneratedCommand, 
            config['model'], 
            form=form_class, 
            extra=1, 
            can_delete=True, 
            min_num=0
        )

    if request.method == 'POST':
        form = GeneratedCommandForm(request.POST, instance=command_obj)
        formsets = {prefix:FormSetClasses[prefix](request.POST, instance=command_obj, prefix=prefix) for prefix in COMPONENT_REGISTRY.keys()}

        # /-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/
        # /-/-/-/-/-/- START OF MODIFICATION /-/-/-/-/-/
        # /-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/
        all_forms_valid = form.is_valid() and all(fs.is_valid() for fs in formsets.values())

        if all_forms_valid:
            try:
                # Run custom validation only after standard validation passes
                _validate_version_compatibility(
                    form,
                    formsets.get('enchantments'),
                    formsets.get('attributes'),
                    form.cleaned_data['target_version']
                )

                with transaction.atomic():
                    form.save()
                    for formset in formsets.values():
                        formset.save()
                    return redirect(reverse('MC_command:detail', args=[command_obj.id]))
            except forms.ValidationError:
                # Custom validation failed, errors are already in the form.
                # The view will now fall through and re-render the form with errors.
                pass
        # If we are here, it means some form was invalid.
        # The view will proceed to render the form with errors below.
        # /-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/
        # /-/-/-/-/-/- END OF MODIFICATION /-/-/-/-/-/
        # /-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/

    else:
        form = GeneratedCommandForm(instance=command_obj)
        formsets = {prefix:FormSetClasses[prefix](instance=command_obj, prefix=prefix) for prefix in COMPONENT_REGISTRY.keys()}

    version_data = {v.pk:v.ordering_id for v in MinecraftVersion.objects.all()}
    item_type_data = {it.pk:{'type':it.function_type} for it in ItemType.objects.all()}

    component_data = {
        prefix:{'formset':formsets[prefix], 'verbose_name':config['verbose_name'], 'supported_types':json.dumps(config['supported_function_types'])}
        for prefix, config in COMPONENT_REGISTRY.items()
    }

    context = {
        'form':form,
        'component_data':component_data,
        'command':command_obj,
        'form_title':'编辑命令',
        'version_data_json':json.dumps(version_data),
        'item_type_data_json':json.dumps(item_type_data),
    }
    return render(request, 'MC_command/item/command_form.html', context)


# ... (文件其他部分不变) ...

def _validate_version_compatibility(form, enchant_formset, attribute_formset, target_version):
    """
    一个辅助函数，用于检查所选版本是否与所有组件兼容。
    如果不兼容，则会向主表单添加一个错误并引发 ValidationError。
    """
    # I have removed the obsolete reference to 'base_item'. The validation now
    # correctly checks only the versioned components from the formsets.
    all_components = []

    if enchant_formset:
        for enchant_form in enchant_formset.cleaned_data:
            if enchant_form and not enchant_form.get('DELETE'):
                all_components.append(enchant_form.get('enchantment'))

    if attribute_formset:
        for attr_form in attribute_formset.cleaned_data:
            if attr_form and not attr_form.get('DELETE'):
                all_components.append(attr_form.get('attribute'))

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
                    display_items.append(f"Name:{json_str}")
                if 'Lore' in v and isinstance(v['Lore'], list):
                    lore_list = [json.dumps({'text':line}, ensure_ascii=False, separators=(',', ':')) for line in v['Lore']]
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



# --- 新增：用于 AJAX 的 API 视图 ---
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
    if component_type == 'enchantment':
        queryset = Enchantment.objects.filter(version_filter).order_by('enchant_type', 'name')
        field = VersionedModelChoiceField(queryset=queryset)
        data = [
            {'id':obj.pk, 'text':field.label_from_instance(obj)}
            for obj in queryset
        ]
    elif component_type == 'attribute':
        queryset = AttributeType.objects.filter(version_filter).order_by('name')
        field = VersionedModelChoiceField(queryset=queryset)
        data = [
            {'id':obj.pk, 'text':field.label_from_instance(obj), 'attribute_id':obj.attribute_id}
            for obj in queryset
        ]
    elif component_type == 'potion_effect':
        queryset = PotionEffectType.objects.filter(version_filter).order_by('name')
        field = VersionedModelChoiceField(queryset=queryset)
        data = [
            {'id':obj.pk, 'text':field.label_from_instance(obj)}
            for obj in queryset
        ]
    elif component_type == 'firework_explosions':
        data = []
    else:
        return JsonResponse({'error':'Invalid component type'}, status=400)

    return JsonResponse(data, safe=False)