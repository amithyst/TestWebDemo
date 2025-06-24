import json
from django.core.management.base import BaseCommand, CommandError
from django.apps import apps
from MC_command.models import MinecraftVersion

class Command(BaseCommand):
    help = '从 JSON 文件导入游戏组件数据到数据库'

    def add_arguments(self, parser):
        parser.add_argument('model_name', type=str, help='要导入的模型名称 (例如: Enchantment, BaseItem)')
        parser.add_argument('json_file', type=str, help='包含组件数据的 JSON 文件路径')

    def handle(self, *args, **options):
        model_name = options['model_name'].capitalize()
        json_file_path = options['json_file']

        try:
            # 动态获取模型类
            Model = apps.get_model('MC_command', model_name)
        except LookupError:
            raise CommandError(f'错误: 模型 "{model_name}" 在应用 "MC_command" 中未找到。')

        self.stdout.write(f'正在从 {json_file_path} 导入数据到 {model_name} 模型...')

        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            raise CommandError(f'错误: 文件 "{json_file_path}" 未找到。')
        except json.JSONDecodeError:
            raise CommandError('错误: JSON 文件格式无效。')

        # 获取数据中指定的 Minecraft 版本
        version_str = data.get('version')
        if not version_str:
            raise CommandError('错误: JSON 文件中缺少 "version" 字段。')

        version_obj, created = MinecraftVersion.objects.get_or_create(
            version_number=version_str,
            defaults={'ordering_id': int(version_str.replace('.', ''))} # 简易生成 ordering_id
        )
        if created:
            self.stdout.write(self.style.WARNING(f'警告: Minecraft 版本 "{version_str}" 不存在，已自动创建。'))
        
        # 定义模型字段的映射
        # key 是 JSON 中的键, value 是模型中的字段名
        field_mapping = {
            'Enchantment': {'id': 'enchant_id', 'name': 'name', 'max_level': 'max_level'},
            'BaseItem': {'id': 'item_id', 'name': 'name'},
            'AttributeType': {'id': 'attribute_id', 'name': 'name'},
            'PotionEffectType': {'id': 'effect_id', 'name': 'name'},
        }

        if model_name not in field_mapping:
            raise CommandError(f'错误: 未为模型 "{model_name}" 定义字段映射。')
        
        mapping = field_mapping[model_name]
        id_field = mapping['id']
        name_field = mapping['name']

        # 遍历数据并导入
        count_created = 0
        count_updated = 0
        for item in data.get('data', []):
            defaults = {
                name_field: item['name'],
                # 假设此文件中的所有数据都从这个版本开始有效
                # 您可以扩展JSON格式来支持 min_version 和 max_version
                'min_version': version_obj, 
            }
            
            # 使用 update_or_create 来避免重复创建
            obj, created = Model.objects.update_or_create(
                **{id_field: item['id']},
                defaults=defaults
            )
            if created:
                count_created += 1
            else:
                count_updated += 1

        self.stdout.write(self.style.SUCCESS(
            f'导入完成！创建了 {count_created} 条新记录，更新了 {count_updated} 条记录。'
        ))