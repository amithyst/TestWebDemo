# Generated by Django 5.2 on 2025-06-25 06:16

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("MC_command", "0010_alter_enchantment_enchant_type"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="appliedpotioneffect",
            options={"verbose_name": "应用的药水效果", "verbose_name_plural": "应用的药水效果"},
        ),
        migrations.AlterModelOptions(
            name="attributetype",
            options={
                "ordering": ["name"],
                "verbose_name": "属性效果",
                "verbose_name_plural": "属性效果",
            },
        ),
        migrations.AlterModelOptions(
            name="baseitem",
            options={
                "ordering": ["name"],
                "verbose_name": "基础物品",
                "verbose_name_plural": "基础物品",
            },
        ),
        migrations.AlterModelOptions(
            name="enchantment",
            options={
                "ordering": ["name"],
                "verbose_name": "附魔效果",
                "verbose_name_plural": "附魔效果",
            },
        ),
        migrations.AlterModelOptions(
            name="generatedcommand",
            options={"verbose_name": "物品配置", "verbose_name_plural": "<完整物品配置>"},
        ),
        migrations.AlterModelOptions(
            name="minecraftversion",
            options={
                "ordering": ["ordering_id"],
                "verbose_name": "版本",
                "verbose_name_plural": "[版本]",
            },
        ),
        migrations.AlterModelOptions(
            name="potioneffecttype",
            options={
                "ordering": ["name"],
                "verbose_name": "药水效果",
                "verbose_name_plural": "药水效果",
            },
        ),
        migrations.AddField(
            model_name="appliedpotioneffect",
            name="show_icon",
            field=models.BooleanField(default=True, help_text="是否在HUD中显示效果图标"),
        ),
        migrations.AlterField(
            model_name="appliedpotioneffect",
            name="command",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="potion_effects",
                to="MC_command.generatedcommand",
                verbose_name="所属命令",
            ),
        ),
        migrations.AlterField(
            model_name="appliedpotioneffect",
            name="effect",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to="MC_command.potioneffecttype",
                verbose_name="药水效果",
            ),
        ),
        migrations.AlterField(
            model_name="appliedpotioneffect",
            name="is_ambient",
            field=models.BooleanField(default=False, help_text="设为True时粒子效果会更不明显"),
        ),
        migrations.AlterField(
            model_name="appliedpotioneffect",
            name="show_particles",
            field=models.BooleanField(default=True, help_text="是否显示粒子效果"),
        ),
        migrations.AlterField(
            model_name="potioneffecttype",
            name="effect_id",
            field=models.CharField(max_length=100, unique=True, verbose_name="效果ID"),
        ),
        migrations.AlterField(
            model_name="potioneffecttype",
            name="max_version",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="MC_command.minecraftversion",
                verbose_name="最高兼容版本",
            ),
        ),
        migrations.AlterField(
            model_name="potioneffecttype",
            name="min_version",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="MC_command.minecraftversion",
                verbose_name="最低兼容版本",
            ),
        ),
        migrations.AlterField(
            model_name="potioneffecttype",
            name="name",
            field=models.CharField(max_length=100, verbose_name="效果名称"),
        ),
    ]
