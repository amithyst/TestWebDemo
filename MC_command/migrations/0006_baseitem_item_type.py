# Generated by Django 5.2 on 2025-06-25 01:37

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("MC_command", "0005_enchantment_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="baseitem",
            name="item_type",
            field=models.CharField(
                choices=[
                    ("all", "所有"),
                    ("spawn_egg", "生成蛋"),
                    ("potion", "药水"),
                    ("written_book", "成书"),
                ],
                default="all",
                help_text="物品类型, 例如 'all','spawn_egg','potion','written_book'等",
                max_length=50,
            ),
        ),
    ]
