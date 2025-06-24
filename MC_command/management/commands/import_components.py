import json
from django.core.management.base import BaseCommand, CommandError
from django.apps import apps
from MC_command.models import MinecraftVersion

class Command(BaseCommand):
    help = '从 JSON 文件导入组件数据 (如附魔、属性) 到指定的模型中。'

    def add_arguments(self, parser):
        parser.add_argument('model_name', type=str, help='要导入数据的模型名称 (例如, Enchantment, AttributeType)。')
        parser.add_argument('json_file', type=str, help='要导入的 JSON 文件的路径。')

    def handle(self, *args, **options):
        model_name = options['model_name']
        json_file_path = options['json_file']
        
        try:
            Model = apps.get_model('MC_command', model_name)
        except LookupError:
            raise CommandError(f'错误: 模型 "{model_name}" 在 "MC_command" 应用中未找到。')

        self.stdout.write(f"正在从 {json_file_path} 导入数据到 {model_name} 模型...")

        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
        except FileNotFoundError:
            raise CommandError(f'错误: 文件未找到于 {json_file_path}')
        except json.JSONDecodeError:
            raise CommandError(f'错误: 解析 JSON 文件失败 {json_file_path}')

        # --- 核心修改：让脚本更灵活 ---
        components = []
        if isinstance(raw_data, dict):
            # 处理 {"components": [...]} 格式
            if 'components' not in raw_data:
                raise CommandError('错误: 如果JSON是字典格式，它必须包含一个 "components" 键。')
            components = raw_data['components']
        elif isinstance(raw_data, list):
            # 直接处理 [...] 格式
            components = raw_data
        else:
            raise CommandError('错误: 不支持的JSON格式。顶层必须是一个列表或字典。')
        
        created_count = 0
        updated_count = 0

        for comp_data in components:
            component_id = comp_data.get('id')
            if not component_id:
                self.stdout.write(self.style.WARNING(f'  跳过一条记录，因为它缺少 "id" 字段: {comp_data}'))
                continue

            # 准备要创建或更新的数据
            defaults = {
                'name': comp_data.get('name', ''),
            }
            # 动态添加模型特有的字段
            if hasattr(Model, 'max_level'):
                defaults['max_level'] = comp_data.get('max_level', 1)
            
            # 处理版本外键
            min_version_id = comp_data.get('min_version_id')
            max_version_id = comp_data.get('max_version_id')

            try:
                if min_version_id is not None:
                    defaults['min_version'] = MinecraftVersion.objects.get(ordering_id=min_version_id)
                if max_version_id is not None:
                    defaults['max_version'] = MinecraftVersion.objects.get(ordering_id=max_version_id)
            except MinecraftVersion.DoesNotExist as e:
                self.stdout.write(self.style.ERROR(f'  跳过 "{component_id}": 未找到对应的 MinecraftVersion (ordering_id: {e})'))
                continue

            # 使用 get_or_create 更新或创建
            unique_field = 'enchant_id' if model_name == 'Enchantment' else 'attribute_id'
            
            obj, created = Model.objects.update_or_create(
                **{unique_field: component_id},
                defaults=defaults
            )

            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(self.style.SUCCESS(f'导入完成！创建了 {created_count} 条新记录，更新了 {updated_count} 条现有记录。'))