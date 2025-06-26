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
# 修改: 引入 Material, ItemType
from .models import Enchantment, AttributeType, PotionEffectType, MinecraftVersion, Material, ItemType
from .models import GeneratedCommand
from .forms import GeneratedCommandForm,VersionedModelChoiceField
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
    FormSetClasses = {
        prefix: inlineformset_factory(GeneratedCommand, config['model'], form=config['form'], extra=1, can_delete=True, min_num=0)
        for prefix, config in COMPONENT_REGISTRY.items()
    }

    if request.method == 'POST':
        form = GeneratedCommandForm(request.POST)
        formsets = {prefix: FormSetClasses[prefix](request.POST, prefix=prefix) for prefix in COMPONENT_REGISTRY.keys()}

        # /-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/
        # /-/-/-/-/-/- START OF MODIFICATION /-/-/-/-/-/
        # /-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/
        forms_are_valid = form.is_valid() and all(fs.is_valid() for fs in formsets.values())

        if forms_are_valid:
            try:
                # 在保存前运行自定义验证
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
                # 验证失败，错误已添加到表单中，将重新渲染页面以显示错误
                pass
        # /-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/
        # /-/-/-/-/-/- END OF MODIFICATION /-/-/-/-/-/
        # /-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/

    else:
        form = GeneratedCommandForm()
        formsets = {prefix: FormSetClasses[prefix](prefix=prefix) for prefix in COMPONENT_REGISTRY.keys()}

    version_data = {v.pk: v.ordering_id for v in MinecraftVersion.objects.all()}
    item_type_data = {it.pk: {'type': it.function_type} for it in ItemType.objects.all()}

    component_data = {
        prefix: {'formset': formsets[prefix], 'verbose_name': config['verbose_name'], 'supported_types': json.dumps(config['supported_function_types'])}
        for prefix, config in COMPONENT_REGISTRY.items()
    }

    context = {
        'form': form,
        'component_data': component_data,
        'form_title': '创建新命令',
        'version_data_json': json.dumps(version_data),
        'item_type_data_json': json.dumps(item_type_data),
    }
    return render(request, 'MC_command/command_form.html', context)

@login_required
def edit(request, command_id):
    command_obj = get_object_or_404(GeneratedCommand, pk=command_id, user=request.user)
    FormSetClasses = {
        prefix: inlineformset_factory(GeneratedCommand, config['model'], form=config['form'], extra=1, can_delete=True, min_num=0)
        for prefix, config in COMPONENT_REGISTRY.items()
    }

    if request.method == 'POST':
        form = GeneratedCommandForm(request.POST, instance=command_obj)
        formsets = {prefix: FormSetClasses[prefix](request.POST, instance=command_obj, prefix=prefix) for prefix in COMPONENT_REGISTRY.keys()}

        # /-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/
        # /-/-/-/-/-/- START OF MODIFICATION /-/-/-/-/-/
        # /-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/
        forms_are_valid = form.is_valid() and all(fs.is_valid() for fs in formsets.values())

        if forms_are_valid:
            try:
                # 在保存前运行自定义验证
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
                # 验证失败，错误已添加到表单中，将重新渲染页面以显示错误
                pass
        # /-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/
        # /-/-/-/-/-/- END OF MODIFICATION /-/-/-/-/-/
        # /-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/

    else:
        form = GeneratedCommandForm(instance=command_obj)
        formsets = {prefix: FormSetClasses[prefix](instance=command_obj, prefix=prefix) for prefix in COMPONENT_REGISTRY.keys()}
        
    version_data = {v.pk: v.ordering_id for v in MinecraftVersion.objects.all()}
    item_type_data = {it.pk: {'type': it.function_type} for it in ItemType.objects.all()}
    
    component_data = {
        prefix: {'formset': formsets[prefix], 'verbose_name': config['verbose_name'], 'supported_types': json.dumps(config['supported_function_types'])}
        for prefix, config in COMPONENT_REGISTRY.items()
    }
    
    context = {
        'form': form,
        'component_data': component_data,
        'command': command_obj,
        'form_title': '编辑命令',
        'version_data_json': json.dumps(version_data),
        'item_type_data_json': json.dumps(item_type_data),
    }
    return render(request, 'MC_command/command_form.html', context)

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

def _generate_command_context(command: GeneratedCommand) -> dict:
    # This function remains mostly the same, but calls the refactored builders.
    target_version_id = command.target_version.ordering_id
    base_item_id = command.item_id
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

    fireworks_nbt = {}
    for prefix, config in COMPONENT_REGISTRY.items():
        related_manager = getattr(command, prefix)
        if related_manager.exists():
            if prefix == 'firework_explosions':
                fireworks_nbt.update(config['generate_nbt'](related_manager))
            else:
                nbt_part = config['generate_nbt'](related_manager)
                nbt_data.update(nbt_part)
    if fireworks_nbt:
        nbt_data['Fireworks'] = fireworks_nbt.get('Fireworks', {})

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

    fireworks_component = {}
    for prefix, config in COMPONENT_REGISTRY.items():
        related_manager = getattr(command, prefix)
        if related_manager.exists():
            if prefix == 'firework_explosions':
                 fireworks_component.update(config['generate_component'](related_manager))
            else:
                component_part = config['generate_component'](related_manager)
                components.update(component_part)

    if fireworks_component:
        explosions_list = fireworks_component.get('minecraft:firework_explosion', '[]')
        components['minecraft:fireworks'] = f"{{explosions:{explosions_list},flight_duration:1}}"

    return components

# --- 新增：用于 AJAX 的 API 视图 ---
def get_compatible_components(request):
    version_pk = request.GET.get('version_id')
    component_type = request.GET.get('type')

    if not version_pk or not component_type:
        return JsonResponse({'error': 'Missing parameters'}, status=400)

    try:
        target_version = get_object_or_404(MinecraftVersion, pk=int(version_pk))
        target_ordering_id = target_version.ordering_id
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Invalid version_id'}, status=400)

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
            {'id': obj.pk, 'text': field.label_from_instance(obj)}
            for obj in queryset
        ]
    elif component_type == 'attribute':
        queryset = AttributeType.objects.filter(version_filter).order_by('name')
        field = VersionedModelChoiceField(queryset=queryset)
        data = [
            {'id': obj.pk, 'text': field.label_from_instance(obj), 'attribute_id': obj.attribute_id}
            for obj in queryset
        ]
    elif component_type == 'potion_effect':
        queryset = PotionEffectType.objects.filter(version_filter).order_by('name')
        field = VersionedModelChoiceField(queryset=queryset)
        data = [
            {'id': obj.pk, 'text': field.label_from_instance(obj)}
            for obj in queryset
        ]
    elif component_type == 'firework_explosions':
        data = []
    else:
        return JsonResponse({'error': 'Invalid component type'}, status=400)
    
    return JsonResponse(data, safe=False)