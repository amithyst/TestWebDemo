# Generated by Django 5.2 on 2025-06-25 03:07

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("MC_command", "0008_alter_baseitem_item_type"),
    ]

    operations = [
        migrations.AlterField(
            model_name="baseitem",
            name="item_type",
            field=models.CharField(
                choices=[
                    ("all", "普通物品"),
                    ("spawn_egg", "生成蛋"),
                    ("potion", "药水(箭/食物)"),
                    ("written_book", "成书"),
                    ("firework", "烟花火箭"),
                ],
                default="all",
                help_text="物品类型, 例如 'all','spawn_egg','potion','written_book'等",
                max_length=50,
            ),
        ),
    ]
