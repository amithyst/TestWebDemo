# Generated by Django 5.2 on 2025-06-25 12:23

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("MC_command", "0013_itemtype_material_alter_baseitem_options_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="itemtype",
            name="item_type_id",
            field=models.CharField(
                default="unknown",
                help_text="物品类型的ID, 例如 'sword' 或 'pickaxe'",
                max_length=100,
                unique=True,
            ),
        ),
        migrations.AddField(
            model_name="material",
            name="material_id",
            field=models.CharField(
                default="unknown",
                help_text="材质的ID, 例如 'diamond' 或 'iron'",
                max_length=100,
                unique=True,
            ),
        ),
        migrations.AlterField(
            model_name="itemtype",
            name="name",
            field=models.CharField(
                help_text="物品的人类可读, 例如 '剑'", max_length=50, unique=True
            ),
        ),
        migrations.AlterField(
            model_name="material",
            name="name",
            field=models.CharField(
                help_text="材质的人类可读名称, 例如 '钻石'", max_length=50, unique=True
            ),
        ),
    ]
