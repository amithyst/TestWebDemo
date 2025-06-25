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
from .models import Enchantment, AttributeType

from .models import GeneratedCommand, AppliedEnchantment, AppliedAttribute, AppliedPotionEffect, MinecraftVersion, BaseItem # Add AppliedPotionEffect, BaseItem
from .forms import GeneratedCommandForm, AppliedEnchantmentForm, AppliedAttributeForm, AppliedPotionEffectForm, VersionedModelChoiceField # Add AppliedPotionEffectForm
from .components import COMPONENT_REGISTRY

# --- 核心视图 ---

@login_required
def index(request):
    command_list = GeneratedCommand.objects.filter(user=request.user).order_by("-updated_at")
    context = {
        'command_list': command_list,
    }
    return render(request, 'MC_command/index.html', context)

@login_required
def detail(request, command_id):
    command_obj = get_object_or_404(GeneratedCommand, pk=command_id, user=request.user)
    command_context = _generate_command_context(command_obj)
    context = {
        'command': command_obj,
        'give_command_string': command_context['give_command'],
        'data_structure_json': command_context['data_json'],
    }
    return render(request, 'MC_command/detail.html', context)

# --- 增删改查 (CRUD) 视图 ---
# --- 完全替换旧的 CREATE 和 EDIT 视图 ---
# --- Replace the create and edit views with these refactored versions ---

@login_required
def create(request):
    """REFACTORED: Handles creation of a command and its dynamically-registered components."""
    # Dynamically create a mapping of prefixes to FormSet classes
    FormSetClasses = {
        prefix: inlineformset_factory(
            GeneratedCommand, config['model'], form=config['form'],
            extra=1, can_delete=True, min_num=0
        )
        for prefix, config in COMPONENT_REGISTRY.items()
    }

    if request.method == 'POST':
        form = GeneratedCommandForm(request.POST)
        # Instantiate all formsets from the request data
        formsets = {
            prefix: FormSetClasses[prefix](request.POST, prefix=prefix)
            for prefix in COMPONENT_REGISTRY.keys()
        }

        # Validate the main form and all formsets
        if form.is_valid() and all(fs.is_valid() for fs in formsets.values()):
            try:
                with transaction.atomic():
                    command_instance = form.save(commit=False)
                    command_instance.user = request.user
                    command_instance.save()

                    # Save data for each formset
                    for prefix, formset in formsets.items():
                        formset.instance = command_instance
                        formset.save()

                    return redirect(reverse('MC_command:detail', args=[command_instance.id]))
            except forms.ValidationError:
                pass # Validation errors will be handled by the form rendering below
    else: # GET
        form = GeneratedCommandForm()
        # Instantiate empty formsets
        formsets = {
            prefix: FormSetClasses[prefix](prefix=prefix)
            for prefix in COMPONENT_REGISTRY.keys()
        }

    # Prepare data for the template
    version_data = {v.pk: v.ordering_id for v in MinecraftVersion.objects.all()}
    base_item_data = {i.pk: {'type': i.item_type} for i in BaseItem.objects.all()}
    
    # NEW: Pass component info to the template for dynamic rendering
    component_data = {
        prefix: {
            'formset': formsets[prefix],
            'verbose_name': config['verbose_name'],
            'supported_types': json.dumps(config['supported_item_types'])
        }
        for prefix, config in COMPONENT_REGISTRY.items()
    }

    context = {
        'form': form,
        'component_data': component_data, # Replaces individual formsets
        'form_title': '创建新命令',
        'version_data_json': json.dumps(version_data),
        'base_item_data_json': json.dumps(base_item_data),
    }
    return render(request, 'MC_command/command_form.html', context)

@login_required
def edit(request, command_id):
    """REFACTORED: Handles editing of a command and its dynamically-registered components."""
    command_obj = get_object_or_404(GeneratedCommand, pk=command_id, user=request.user)
    FormSetClasses = {
        prefix: inlineformset_factory(
            GeneratedCommand, config['model'], form=config['form'],
            extra=1, can_delete=True, min_num=0
        )
        for prefix, config in COMPONENT_REGISTRY.items()
    }

    if request.method == 'POST':
        form = GeneratedCommandForm(request.POST, instance=command_obj)
        formsets = {
            prefix: FormSetClasses[prefix](request.POST, instance=command_obj, prefix=prefix)
            for prefix in COMPONENT_REGISTRY.keys()
        }

        if form.is_valid() and all(fs.is_valid() for fs in formsets.values()):
            try:
                with transaction.atomic():
                    form.save()
                    for formset in formsets.values():
                        formset.save()
                    return redirect(reverse('MC_command:detail', args=[command_obj.id]))
            except forms.ValidationError:
                pass
    else: # GET
        form = GeneratedCommandForm(instance=command_obj)
        formsets = {
            prefix: FormSetClasses[prefix](instance=command_obj, prefix=prefix)
            for prefix in COMPONENT_REGISTRY.keys()
        }
        
    version_data = {v.pk: v.ordering_id for v in MinecraftVersion.objects.all()}
    base_item_data = {i.pk: {'type': i.item_type} for i in BaseItem.objects.all()}
    component_data = {
        prefix: {
            'formset': formsets[prefix],
            'verbose_name': config['verbose_name'],
            'supported_types': json.dumps(config['supported_item_types'])
        }
        for prefix, config in COMPONENT_REGISTRY.items()
    }
    
    context = {
        'form': form,
        'component_data': component_data,
        'command': command_obj,
        'form_title': '编辑命令',
        'version_data_json': json.dumps(version_data),
        'base_item_data_json': json.dumps(base_item_data),
    }
    return render(request, 'MC_command/command_form.html', context)

# C:\Github\djangotutorial\MC_command\views.py

# ... (文件其他部分不变) ...

def _validate_version_compatibility(form, enchant_formset, attribute_formset, target_version):
    """
    一个辅助函数，用于检查所选版本是否与所有组件兼容。
    如果不兼容，则会向主表单添加一个错误并引发 ValidationError。
    """
    all_components = [form.cleaned_data.get('base_item')]
    for enchant_form in enchant_formset.cleaned_data:
        if enchant_form and not enchant_form.get('DELETE'):
            all_components.append(enchant_form.get('enchantment'))
    for attr_form in attribute_formset.cleaned_data:
        if attr_form and not attr_form.get('DELETE'):
            all_components.append(attr_form.get('attribute'))

    min_v_id = 0
    max_v_id = float('inf')

    # 计算所有组件版本号的交集
    for component in filter(None, all_components):
        # 修复: 在访问 .ordering_id 前检查对象是否存在
        if component.min_version:
            min_v_id = max(min_v_id, component.min_version.ordering_id)
        
        # 修复: 同样检查 max_version
        if component.max_version:
            max_v_id = min(max_v_id, component.max_version.ordering_id)

    # 新增: 检查是否存在有效的版本范围交集
    if min_v_id > max_v_id:
        min_v_str = MinecraftVersion.objects.get(ordering_id=min_v_id).version_number
        max_v_str = "更早版本"
        if max_v_id != float('inf'):
            max_v_str = MinecraftVersion.objects.get(ordering_id=max_v_id).version_number
        
        error_msg = f"组件冲突：所选组件之间没有兼容的Minecraft版本 (计算出的最低版本需求为 {min_v_str}，最高为 {max_v_str})。请调整您的选择。"
        # 引发一个非字段错误，它将显示在表单顶部
        raise forms.ValidationError(error_msg)

    # 现有逻辑: 检查用户选择的版本是否在有效范围内
    if not (min_v_id <= target_version.ordering_id <= max_v_id):
        min_v_str = MinecraftVersion.objects.get(ordering_id=min_v_id).version_number
        max_v_str = "最新"
        if max_v_id != float('inf'):
            max_v_str = MinecraftVersion.objects.get(ordering_id=max_v_id).version_number
        
        error_msg = f"版本不兼容。根据所选组件，可用版本应在 {min_v_str} 和 {max_v_str} 之间。"
        form.add_error('target_version', error_msg)
        raise forms.ValidationError(error_msg)
    

@login_required
@require_POST
def delete(request, command_id):
    command_obj = get_object_or_404(GeneratedCommand, pk=command_id, user=request.user)
    command_obj.delete()
    return redirect(reverse('MC_command:index'))


# --- 辅助函数 (Helper Functions) ---

def _generate_command_context(command: GeneratedCommand) -> dict:
    # This function remains mostly the same, but calls the refactored builders.
    target_version_id = command.target_version.ordering_id
    base_item_id = command.base_item.item_id
    if target_version_id >= 12005: # Minecraft 1.20.5+
        data_structure = _build_component_structure(command)
        data_string = ",".join([f"{key}={value}" for key, value in data_structure.items()])
        give_command = f"/give @p {base_item_id}[{data_string}] {command.count}"
    else: # Older versions
        data_structure = _build_nbt_tag_structure(command)
        data_string = json.dumps(data_structure, separators=(',', ':')) if data_structure else ''
        give_command = f"/give @p {base_item_id}{data_string} {command.count}"
    return {
        'give_command': give_command,
        'data_json': json.dumps(data_structure, indent=4, ensure_ascii=False),
    }

def _build_nbt_tag_structure(command: GeneratedCommand) -> dict:
    """REFACTORED: Builds the NBT tag structure by iterating through the component registry."""
    nbt_data = {}
    display = {}

    if command.custom_name:
        display['Name'] = json.dumps(command.custom_name, ensure_ascii=False)
    if command.lore:
        lore_lines = [json.dumps(line, ensure_ascii=False) for line in command.lore.splitlines() if line.strip()]
        if lore_lines:
            display['Lore'] = f'[{",".join(lore_lines)}]'
    if display:
        nbt_data['display'] = display

    # Dynamic part using the registry
    for prefix, config in COMPONENT_REGISTRY.items():
        related_manager = getattr(command, prefix)
        if related_manager.exists():
            nbt_part = config['generate_nbt'](related_manager)
            nbt_data.update(nbt_part)

    return nbt_data

def _build_component_structure(command: GeneratedCommand) -> dict:
    """REFACTORED: Builds the component structure by iterating through the component registry."""
    components = {}

    if command.custom_name:
        components['minecraft:custom_name'] = json.dumps(command.custom_name, ensure_ascii=False)
    if command.lore:
        lore_lines = [json.dumps(line, ensure_ascii=False) for line in command.lore.splitlines() if line.strip()]
        if lore_lines:
            components['minecraft:lore'] = f'[{",".join(lore_lines)}]'

    # Dynamic part using the registry
    for prefix, config in COMPONENT_REGISTRY.items():
        related_manager = getattr(command, prefix)
        if related_manager.exists():
            component_part = config['generate_component'](related_manager)
            components.update(component_part)

    return components

# --- 新增：用于 AJAX 的 API 视图 ---
def get_compatible_components(request):
    version_pk = request.GET.get('version_id') # Changed variable name for clarity
    component_type = request.GET.get('type')

    if not version_pk or not component_type:
        return JsonResponse({'error': 'Missing parameters'}, status=400)

    try:
        # --- FIX: First, get the version object using its Primary Key (pk) ---
        target_version = get_object_or_404(MinecraftVersion, pk=int(version_pk))
        # --- FIX: Then, use its ordering_id for the query ---
        target_ordering_id = target_version.ordering_id
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Invalid version_id'}, status=400)

    # 构建动态的版本过滤查询
    version_filter = (
        Q(min_version__ordering_id__lte=target_ordering_id) | Q(min_version__isnull=True)
    ) & (
        Q(max_version__ordering_id__gte=target_ordering_id) | Q(max_version__isnull=True)
    )

    if component_type == 'enchantment':
        queryset = Enchantment.objects.filter(version_filter)
        field = VersionedModelChoiceField(queryset=queryset)
        data = [
            {'id': obj.pk, 'text': field.label_from_instance(obj)}
            for obj in queryset
        ]
    elif component_type == 'attribute':
        queryset = AttributeType.objects.filter(version_filter)
        field = VersionedModelChoiceField(queryset=queryset)
        # UPDATE: Include attribute_id in the response for attributes
        data = [
            {'id': obj.pk, 'text': field.label_from_instance(obj), 'attribute_id': obj.attribute_id}
            for obj in queryset
        ]
    else:
        return JsonResponse({'error': 'Invalid component type'}, status=400)
    
    return JsonResponse(data, safe=False)
    
