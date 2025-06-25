# 常用命令

```bash
git remote add origin https://github.com/amithyst/TestWebDemo.git
git add .
git commit -m "更新"
git push -u origin master

```

切换到根目录创建文件夹**djangotutorial后创建**项目

```
django-admin startproject mysite djangotutorial
```

改变模型需要这三步：

* 编辑 `models.py` 文件，改变模型。
* 运行 [`python manage.py makemigrations`](https://docs.djangoproject.com/zh-hans/5.2/ref/django-admin/#django-admin-makemigrations) 为模型的改变生成迁移文件。
* 运行 [`python manage.py migrate`](https://docs.djangoproject.com/zh-hans/5.2/ref/django-admin/#django-admin-migrate) 来应用数据库迁移。
* ```python
  python manage.py makemigrations
  python manage.py migrate
  ```

## 导入数据

```python
python manage.py import_components enchantments.json
python manage.py import_components attributes.json
python manage.py import_components effects.json
```

# 如何添加新的组件

本项目的核心设计思想是组件化。每个命令的附加部分（如附魔、属性、药水效果）都被视为一个独立的“组件”。这种设计使得添加新的功能变得模块化和清晰。

本教程将指导您完成添加一个全新组件（例如：烟火之星、成书内容）所需的所有步骤。

### 步骤概览

添加一个新组件通常需要修改以下文件：

1. `MC_command/models.py`: 定义新组件的数据结构。
2. `MC_command/forms.py`: 为新组件创建数据输入表单。
3. `MC_command/components.py`: 编写组件的核心逻辑并将其注册到系统中。
4. `MC_command/templates/MC_command/detail.html`: 在命令详情页展示新组件的数据。
5. `MC_command/templates/MC_command/command_form.html`: （通常无需修改）模板会自动根据注册信息渲染表单。
6. (可选) `MC_command/json_data/`: 如果组件需要预设数据，可以在此添加。
7. (可选) `MC_command/management/commands/import_components.py`: 编写导入预设数据的逻辑。

---

### 详细步骤 (以“烟火之星”为例)

我们的目标是添加一个“烟火之星”组件，允许用户为一个物品（如烟花火箭）添加爆炸效果。

#### 1. 创建数据模型 (`MC_command/models.py`)

首先，我们需要一个模型来存储每个烟火之星效果的属性。在 `models.py` 中添加以下类：

**Python**

```
# amithyst/testwebdemo/TestWebDemo-4fa6cf57045ff52b83a4e5463edddcd4c84bea51/MC_command/models.py

# ... (在文件末尾或其他模型定义之后)

class AppliedFireworksStar(models.Model):
    """
    代表应用到命令物品上的单个烟火之星效果。
    """
    SHAPE_CHOICES = [
        (0, 'Small Ball'),
        (1, 'Large Ball'),
        (2, 'Star-shaped'),
        (3, 'Creeper-shaped'),
        (4, 'Burst'),
    ]

    command = models.ForeignKey(GeneratedCommand, related_name='fireworks_stars', on_delete=models.CASCADE)
    shape = models.IntegerField(choices=SHAPE_CHOICES, default=0, verbose_name="爆炸形状")
    colors = models.CharField(max_length=100, help_text="英文逗号分隔的颜色16进制代码, 例如 FFFFFF,000000", verbose_name="颜色")
    fade_colors = models.CharField(max_length=100, blank=True, help_text="同上", verbose_name="渐变颜色")
    has_twinkle = models.BooleanField(default=False, verbose_name="闪烁")
    has_trail = models.BooleanField(default=False, verbose_name="轨迹")

    def __str__(self):
        return f"Fireworks Star for {self.command.command_name}"

```

#### 2. 创建表单 (`MC_command/forms.py`)

接下来，为新模型创建对应的 `ModelForm` 和 `inlineformset_factory`。

**Python**

```
# amithyst/testwebdemo/TestWebDemo-4fa6cf57045ff52b83a4e5463edddcd4c84bea51/MC_command/forms.py

# ... (在文件顶部导入新模型)
from .models import (
    GeneratedCommand, MinecraftVersion, BaseItem, Enchantment, AppliedEnchantment,
    Attribute, AppliedAttribute, PotionEffect, AppliedPotionEffect, AppliedFireworksStar # <--- 添加导入
)

# ... (在文件末尾)

class AppliedFireworksStarForm(forms.ModelForm):
    class Meta:
        model = AppliedFireworksStar
        fields = ['shape', 'colors', 'fade_colors', 'has_twinkle', 'has_trail']
        widgets = {
            'colors': forms.TextInput(attrs={'placeholder': '例如：FFFFFF,FF0000'}),
            'fade_colors': forms.TextInput(attrs={'placeholder': '例如：00FF00'}),
        }

# 创建对应的 Formset
AppliedFireworksStarFormset = forms.inlineformset_factory(
    GeneratedCommand,
    AppliedFireworksStar,
    form=AppliedFireworksStarForm,
    extra=1,
    can_delete=True
)
```

#### 3. 编写命令生成逻辑 (`MC_command/components.py`)

这是组件的核心。我们需要一个函数，它能接收保存到数据库的烟火之星数据，并将其转换为Minecraft命令中的NBT字符串。

**Python**

```
# amithyst/testwebdemo/TestWebDemo-4fa6cf57045ff52b83a4e5463edddcd4c84bea51/MC_command/components.py

# ... (在文件顶部导入新模型和Formset)
from .models import AppliedFireworksStar
from .forms import AppliedFireworksStarFormset

# ...

def generate_fireworks_command(queryset):
    """
    为烟火之星生成NBT字符串。
    示例: Fireworks:{Explosions:[{Type:1b,Flicker:1b,Trail:1b,Colors:[I;16711680],FadeColors:[I;16776960]}]}
    """
    if not queryset.exists():
        return ""

    explosions = []
    for star in queryset:
        explosion_nbt = f"Type:{star.shape}b"
        if star.has_twinkle:
            explosion_nbt += ",Flicker:1b"
        if star.has_trail:
            explosion_nbt += ",Trail:1b"

        # 处理颜色
        try:
            colors_int = [int(c, 16) for c in star.colors.replace(' ', '').split(',') if c]
            explosion_nbt += f",Colors:[I;{','.join(map(str, colors_int))}]"
        except (ValueError, TypeError):
            pass # 忽略无效的颜色格式

        # 处理渐变颜色
        try:
            fade_colors_int = [int(c, 16) for c in star.fade_colors.replace(' ', '').split(',') if c]
            explosion_nbt += f",FadeColors:[I;{','.join(map(str, fade_colors_int))}]"
        except (ValueError, TypeError):
            pass

        explosions.append(f"{{{explosion_nbt}}}")

    return f"Fireworks:{{Explosions:[{','.join(explosions)}]}}"

```

#### 4. 注册组件 (`MC_command/components.py`)

将我们刚才创建的所有部分组合起来，注册到 `COMPONENT_REGISTRY` 中。这是让系统识别并使用新组件的关键一步。

**Python**

```
# amithyst/testwebdemo/TestWebDemo-4fa6cf57045ff52b83a4e5463edddcd4c84bea51/MC_command/components.py

# ...

COMPONENT_REGISTRY = {
    'enchantments': {
        # ... (已有的附魔组件)
    },
    'attributes': {
        # ... (已有的属性组件)
    },
    'potion_effects': {
        # ... (已有的药水效果组件)
    },
    # --- 在此添加新组件 ---
    'fireworks': {
        'model': AppliedFireworksStar,
        'formset': AppliedFireworksStarFormset,
        'verbose_name': '烟火之星',
        'supported_item_types': ['firework_rocket'], # 此组件只对烟花火箭类型的物品显示
        'command_generator': generate_fireworks_command,
    },
}
```

#### 5. 更新详情页模板 (`MC_command/templates/MC_command/detail.html`)

为了能在命令详情页看到已添加的烟火之星效果，需要修改 `detail.html`。

**HTML**

```
{% if command.fireworks_stars.all %}
<div class="card mt-3">
    <div class="card-header">
        <h4>烟火之星</h4>
    </div>
    <div class="card-body">
        <table class="table">
            <thead>
                <tr>
                    <th>形状</th>
                    <th>颜色</th>
                    <th>渐变色</th>
                    <th>闪烁</th>
                    <th>轨迹</th>
                </tr>
            </thead>
            <tbody>
                {% for star in command.fireworks_stars.all %}
                <tr>
                    <td>{{ star.get_shape_display }}</td>
                    <td>{{ star.colors }}</td>
                    <td>{{ star.fade_colors|default:"无" }}</td>
                    <td>{{ star.has_twinkle|yesno:"是,否" }}</td>
                    <td>{{ star.has_trail|yesno:"是,否" }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
{% endif %}
```

#### 6. 迁移数据库

由于我们创建了一个新的数据模型 `AppliedFireworksStar`，需要让Django更新数据库结构。

在您的项目终端中运行以下命令：

**Bash**

```
python manage.py makemigrations MC_command
python manage.py migrate
```

**恭喜！** 完成以上步骤后，重启您的Django服务器，现在您就可以在创建/编辑命令时，为“烟花火箭”类型的物品添加“烟火之星”组件了。
