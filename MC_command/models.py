# mc_commands/models.py
import uuid # <--- 在文件顶部添加此行
import json
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError # 引入验证错误

# ==============================================================================
# 1. 基础与版本控制模型 (无变化)
# ==============================================================================

class MinecraftVersion(models.Model):
    """存储支持的 Minecraft 版本。"""
    version_number = models.CharField(max_length=20, unique=True, help_text="例如 '1.20.1' 或 '1.21.4'")
    ordering_id = models.PositiveIntegerField(unique=True, help_text="用于排序和比较的版本整数ID, 例如 12001 代表 1.20.1")

    class Meta:
        ordering = ['ordering_id']
        verbose_name = "版本"
        verbose_name_plural = "<1>版本"

    def __str__(self):
        return self.version_number

# ==============================================================================
# 2. 静态游戏数据模型 (带有版本范围)
# ==============================================================================

class VersionedItem(models.Model):
    """一个抽象基类，为所有需要版本控制的静态游戏数据提供通用字段。"""
    min_version = models.ForeignKey(
        MinecraftVersion, on_delete=models.PROTECT, related_name='+',
        blank=True, null=True, help_text="该项目有效的最低版本 (留空表示无限制)"
    )
    max_version = models.ForeignKey(
        MinecraftVersion, on_delete=models.PROTECT, related_name='+',
        blank=True, null=True, help_text="该项目有效的最高版本 (留空表示无限制)"
    )

    class Meta:
        abstract = True

# --- 新增模型：Material ---

class Material(models.Model):
    """存储物品材质，例如：钻石 (diamond)"""
    system_name = models.CharField(max_length=50, unique=True, help_text="系统内部名称, e.g., 'diamond'"
                                   ,
        null=True,  # 允许数据库中的值为 NULL
        blank=True  # 允许在表单中该字段为空
        )
    # --- 在这里进行修改 ---
    display_name = models.CharField(
        max_length=50,
        help_text="用于显示的名称, e.g., '钻石'",
        null=True,  # 允许数据库中的值为 NULL
        blank=True  # 允许在表单中该字段为空
    )

    class Meta:
        verbose_name = "材质"
        verbose_name_plural = "<💎>材质"
        ordering = ['display_name']

    def __str__(self):
        # 如果显示名称为空，则返回系统名称，避免显示空白
        return self.display_name or self.system_name

class ItemType(models.Model):
    """存储物品基础类型，例如：剑 (sword)"""
    system_name = models.CharField(max_length=50, unique=True, help_text="系统内部名称, e.g., 'sword'",
        null=True,  # 允许数据库中的值为 NULL
        blank=True  # 允许在表单中该字段为空
    )
    display_name = models.CharField(
        max_length=50,
        help_text="用于显示的名称, e.g., '剑'",
        null=True,  # 允许数据库中的值为 NULL
        blank=True  # 允许在表单中该字段为空
    )
    function_type = models.CharField(
        max_length=50, help_text="物品的功能分类",
        choices=[
            ('all', '普通物品'),
            ('spawn_egg', '生成蛋'),
            ('potion', '药水(箭/食物)'),
            ('written_book', '成书'),
            ('firework', '烟花火箭'),
        ],default='all', verbose_name="功能类型"
    )

    class Meta:
        verbose_name = "物品类型"
        verbose_name_plural = "<🗡>物品类型"
        ordering = ['display_name']

    def __str__(self):
        # 同样，如果显示名称为空，则返回系统名称
        return self.display_name or self.system_name

class Enchantment(VersionedItem):
    """存储所有可用的附魔类型及其版本范围"""
    enchant_id = models.CharField(max_length=100, help_text="附魔ID, 例如 'minecraft:sharpness'")
    name = models.CharField(max_length=100, help_text="人类可读的名称, 例如 'Sharpness'")
    max_level = models.PositiveIntegerField(default=127, help_text="附魔的最大等级, 例如 Sharpness 的最大等级是 127")
    enchant_type = models.CharField(
        max_length=50,help_text="附魔类型, 例如 'weapon', 'armor', 'fishing_rod', 'trident' 等",
        choices=[
            ('weapon', '武器'),
            ('tool', '工具'),
            ('armor', '盔甲'),
            ('chestplate', '胸甲'),
            ('leggings', '护腿'),
            ('boots', '靴子'),
            ('fishing_rod', '钓鱼竿'),
            ('trident', '三叉戟'),
            ('bow', '弓'),
            ('crossbow', '弩'),
            ('all', '所有物品'),
            ('helmet', '头盔'),
            ('wand', '[铁魔法]法杖'),
            ('magic_books', '[铁魔法]法术书'),
            ('unknown', '未知'),
        ],
        default='all'
    )
    class Meta:
        verbose_name = "附魔效果"
        verbose_name_plural = "[🔥]附魔效果"
        ordering = ['name']

    def __str__(self):
        return self.name

class PotionEffectType(VersionedItem):
    """存储所有可用的药水效果"""
    effect_id = models.CharField(max_length=100, unique=True, verbose_name="效果ID")
    name = models.CharField(max_length=100, verbose_name="效果名称")
    min_version = models.ForeignKey(MinecraftVersion, on_delete=models.SET_NULL, null=True, blank=True, related_name='+', verbose_name="最低兼容版本")
    max_version = models.ForeignKey(MinecraftVersion, on_delete=models.SET_NULL, null=True, blank=True, related_name='+', verbose_name="最高兼容版本")
    
    class Meta:
        verbose_name = "药水效果"
        verbose_name_plural = "[💧]药水效果"
        ordering = ['name']

    def __str__(self):
        return self.name
    
class Spell(VersionedItem):
    """存储所有可用的法术，例如 'cataclysm_spellbooks:summon_koboleton'"""
    spell_id = models.CharField(max_length=150, unique=True, help_text="法术的唯一ID, 例如 'cataclysm_spellbooks:summon_koboleton'")
    name = models.CharField(max_length=100, help_text="法术的显示名称, 例如 '召唤骷髅兵'")
    min_version = models.ForeignKey(MinecraftVersion, on_delete=models.SET_NULL, null=True, blank=True, related_name='+', verbose_name="最低兼容版本")
    max_version = models.ForeignKey(MinecraftVersion, on_delete=models.SET_NULL, null=True, blank=True, related_name='+', verbose_name="最高兼容版本")
   
    class Meta:
        verbose_name = "法术"
        verbose_name_plural = "[🪄]法术"
        ordering = ['name']

    def __str__(self):
        return self.name

# --- 新增的静态数据模型 ---
class AttributeType(VersionedItem):
    """存储所有可用的属性类型及其版本范围"""
    attribute_id = models.CharField(max_length=100, help_text="属性ID, 例如 'generic.attack_damage'")
    name = models.CharField(max_length=100, help_text="人类可读的名称, 例如 'Generic Attack Damage'")

    class Meta:
        verbose_name = "属性效果"
        verbose_name_plural = "[💪]属性效果"
        ordering = ['name']

    def __str__(self):
        return self.name
    
class BooleanComponentType(VersionedItem):
    """布尔型物品组件的定义。"""
    name = models.CharField(max_length=100, verbose_name="名称")
    description = models.CharField(max_length=200, blank=True, verbose_name="说明")
    true_str = models.CharField(max_length=100, verbose_name="启用时字符串",default="")
    false_str = models.CharField(max_length=100, blank=True, verbose_name="关闭时字符串",default="")

    class Meta:
        verbose_name = "布尔型组件定义"
        verbose_name_plural = "[⚙]布尔型组件定义"

    def __str__(self):
        return self.name
    

# ==============================================================================
# 3. 核心用户创建内容模型 (已修改)
# ==============================================================================
class GeneratedCommand(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="commands")
    title = models.CharField(max_length=100, help_text="为这个命令配置起一个名字，方便查找")
    target_version = models.ForeignKey(MinecraftVersion, on_delete=models.PROTECT, help_text="命令生成的目标 Minecraft 版本")
    material = models.ForeignKey(Material, on_delete=models.PROTECT, null=True, blank=True, help_text="物品的材质")
    item_type = models.ForeignKey(ItemType, on_delete=models.PROTECT, null=True, blank=True, help_text="物品的基础类型")
    custom_name = models.CharField(max_length=255, blank=True, null=True, help_text="物品在游戏中的自定义名称 (支持JSON文本)")
    lore = models.TextField(blank=True, null=True, help_text="物品的描述文字 (支持JSON文本), 每行用 \\n 分隔")
    count = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def item_name(self):
        material_dn = self.material.display_name if self.material else ""
        type_dn = self.item_type.display_name if self.item_type else ""
        if material_dn and type_dn:
            return f"{material_dn} {type_dn}"
        return material_dn or type_dn
    
    @property
    def item_id(self):
        material_sn = self.material.system_name if self.material else ""
        type_sn = self.item_type.system_name if self.item_type else ""
        base_id = ""
        if material_sn and type_sn:
            base_id = f"{material_sn}_{type_sn}"
        else:
            base_id = material_sn or type_sn
        return f"{base_id}" if base_id else ""

    @property
    def function_type(self):
        if self.item_type:
            return self.item_type.function_type
        return 'all'
    
    @property
    def applied_spells(self):
        """
        一个属性，用于直接访问与此命令关联的应用法术列表。
        这为组件注册表提供了一个统一的接口。
        """
        if hasattr(self, 'spell_infusion') and self.spell_infusion is not None:
            return self.spell_infusion.spells
        # 如果没有关联的 SpellInfusion 对象，则返回一个空的 manager
        return AppliedSpell.objects.none()
    
    def clean(self):
        if not self.material and not self.item_type:
            raise ValidationError("材质 (Material) 和物品类型 (ItemType) 不能同时为空。")
    
    def __str__(self):
        return f"'{self.title}' for v{self.target_version} by {self.user.username}"
    
    class Meta:
        verbose_name = "物品配置"
        verbose_name_plural = "<0>完整物品配置"


# ==============================================================================
# 4. 物品组件模型 (与 GeneratedCommand 关联)
# ==============================================================================

class AppliedEnchantment(models.Model):
    """连接 GeneratedCommand 和 Enchantment，并存储附魔等级"""
    command = models.ForeignKey(GeneratedCommand, on_delete=models.CASCADE, related_name="enchantments")
    enchantment = models.ForeignKey(Enchantment, on_delete=models.CASCADE)
    level = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ('command', 'enchantment')

# --- 修正后的模型 ---
class AppliedAttribute(models.Model):
    """
    存储应用到物品上的属性修改器。
    替代了原先的 AttributeModifier 模型。
    """
    command = models.ForeignKey(GeneratedCommand, on_delete=models.CASCADE, related_name="attributes")
    attribute = models.ForeignKey(AttributeType, on_delete=models.CASCADE) 
    amount = models.FloatField()
    operation = models.IntegerField(choices=[(0, "add_value"), (1, "add_multiplied_base"), (2, "add_multiplied_total")], default=0)
    slot = models.CharField(max_length=20, choices=[("any", "Any"), ("mainhand", "Main Hand"), ("offhand", "Off Hand"), ("head", "Head"), ("chest", "Chest"), ("legs", "Legs"), ("feet", "Feet")], default="any")
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, help_text="修饰符的唯一ID，自动生成。")
    
    # --- 这里是关键改动 ---
    modifier_name = models.CharField(
        max_length=100,
        blank=True,  # 允许该字段在表单中为空
        null=True,   # 允许数据库中该字段为 NULL
        help_text="[重要] 仅用于 1.20.4 及更早版本。1.20.5+ 版本已废弃此字段。"
    )

    def __str__(self):
        # 增加一个更有用的字符串表示
        return f"{self.attribute.name} on {self.command.title}"


class AppliedPotionEffect(models.Model):
    """将一个药水效果应用到一个生成的命令上"""
    command = models.ForeignKey(GeneratedCommand, on_delete=models.CASCADE, related_name="potion_effects", verbose_name="所属命令")
    effect = models.ForeignKey(PotionEffectType, on_delete=models.CASCADE, verbose_name="药水效果")
    amplifier = models.PositiveIntegerField(default=0, help_text="效果等级, 从0开始 (0=I, 1=II)")
    duration = models.PositiveIntegerField(default=600, help_text="持续时间 (单位: ticks, 20 ticks = 1s)")
    is_ambient = models.BooleanField(default=False, help_text="设为True时粒子效果会有信标?")
    show_particles = models.BooleanField(default=True, help_text="是否显示粒子效果")
    show_icon = models.BooleanField(default=True, help_text="是否在HUD中显示效果图标")

    class Meta:
        verbose_name = "应用的药水效果"
        verbose_name_plural = "应用的药水效果"

    def __str__(self):
        return f"{self.command.title} - {self.effect.name} (等级 {self.amplifier})"


class WrittenBookContent(models.Model):
    """存储成书 (`minecraft:written_book`) 的内容"""
    command = models.OneToOneField(GeneratedCommand, on_delete=models.CASCADE, related_name="book_content")
    title = models.CharField(max_length=100)
    author = models.CharField(max_length=50)
    pages = models.TextField(help_text="书本内容，存储为 JSON 字符串数组")


# --- 新增烟火之星模型 ---
# --- 在文件末尾添加以下新模型 ---
class AppliedFireworkExplosion(models.Model):
    """
    Represents a single explosion effect applied to a firework rocket or star.
    A firework can have multiple explosions.
    """
    SHAPE_CHOICES = [
        ('0', '小球型'), ('1', '大球型'), ('2', '星型'),
        ('3', '苦力怕脸型'), ('4', '爆裂型'), ('random', '随机形状')
    ]

    command = models.ForeignKey(
        GeneratedCommand,
        on_delete=models.CASCADE,
        related_name='firework_explosions' # 这个名称必须与 COMPONENT_REGISTRY 中的键匹配
    )
    # 核心属性
    shape = models.CharField(max_length=10, choices=SHAPE_CHOICES, default='0', verbose_name="爆炸形状")
    colors = models.CharField(max_length=200, default='[]', verbose_name="颜色", help_text='JSON 格式的颜色值列表, e.g., [16711680, 16776960] for red, yellow. Use "random" for random colors.')
    fade_colors = models.CharField(max_length=200, blank=True, default='[]', verbose_name="淡出颜色", help_text='效果消失时渐变到的颜色 (JSON 列表或 "random")')
    has_trail = models.BooleanField(default=False, verbose_name="有拖尾效果")
    has_twinkle = models.BooleanField(default=False, verbose_name="有闪烁效果")

    # 控制逻辑
    repeat_count = models.PositiveSmallIntegerField(default=1, verbose_name="重复次数", help_text="此爆炸效果重复多少次")

    # --- 在此处添加以下两个方法 ---
    def get_colors_list(self):
        """将JSON字符串解析为主颜色列表"""
        if self.colors and self.colors != 'random':
            try:
                return json.loads(self.colors)
            except json.JSONDecodeError:
                return []
        return []

    def get_fade_colors_list(self):
        """将JSON字符串解析为淡出颜色列表"""
        if self.fade_colors and self.fade_colors != 'random':
            try:
                return json.loads(self.fade_colors)
            except json.JSONDecodeError:
                return []
        return []
    # --- 添加结束 ---

    def __str__(self):
        shape_name = self.get_shape_display()
        return f"爆炸效果 ({shape_name})"

    class Meta:
        verbose_name = "烟火爆炸效果"
        verbose_name_plural = "烟火爆炸效果"

class AppliedBooleanComponent(models.Model):
    """在 GeneratedCommand 上应用的布尔组件。"""
    command = models.ForeignKey(
        GeneratedCommand,
        on_delete=models.CASCADE,
        related_name="boolean_components",
    )
    component = models.ForeignKey(BooleanComponentType, on_delete=models.PROTECT)
    value = models.BooleanField(default=True, verbose_name="启用？")

    class Meta:
        unique_together = ("command", "component")
        verbose_name = "布尔型组件"
        verbose_name_plural = "布尔型组件"

class SpellInfusion(models.Model):
    """
    存储物品的法术注入核心配置 (对应 NBT 的 ISB_Spells 标签)。
    与 GeneratedCommand 是一对一关系。
    """
    command = models.OneToOneField(
        GeneratedCommand,
        on_delete=models.CASCADE,
        related_name="spell_infusion" # 方便从 command 反向查询
    )
    spell_wheel = models.BooleanField(default=True, verbose_name="启用法术轮盘 (spellWheel)")
    must_equip = models.BooleanField(default=False, verbose_name="必须装备才能施法 (mustEquip)")
    max_spells = models.PositiveSmallIntegerField(default=1, verbose_name="最大法术数量 (maxSpells)")

    class Meta:
        verbose_name = "法术注入配置"
        verbose_name_plural = "法术注入配置"

    def __str__(self):
        return f"为 '{self.command.title}' 配置的法术"


class AppliedSpell(models.Model):
    """
    存储应用到物品上的具体法术及其属性 (对应 NBT 的 data 数组中的每个条目)。
    """
    infusion_config = models.ForeignKey(
        SpellInfusion,
        on_delete=models.CASCADE,
        related_name="spells", # 对应 NBT 的 data 字段
        verbose_name="所属法术配置"
    )
    spell = models.ForeignKey(Spell, on_delete=models.PROTECT, verbose_name="选择的法术")
    level = models.PositiveIntegerField(default=1, verbose_name="法术等级 (level)")
    index = models.PositiveSmallIntegerField(default=0, verbose_name="法术索引 (index)", help_text="法术在列表中的位置，从0开始")
    locked = models.BooleanField(default=False, verbose_name="是否锁定 (locked)")

    class Meta:
        verbose_name = "应用的法术"
        verbose_name_plural = "应用的法术"
        ordering = ['index'] # 默认按索引排序
        unique_together = ('infusion_config', 'index') # 同一个物品配置中，每个索引只能有一个法术

    def __str__(self):
        return f"[{self.index}] {self.spell.name} (Lv. {self.level}) for '{self.infusion_config.command.title}'"