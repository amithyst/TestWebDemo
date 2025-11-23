# mc_commands/models.py
import uuid # <--- 在文件顶部添加此行
import json
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError # 引入验证错误

# 实体更新新加
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType


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

# --- 修改后的模型 ---
class AppliedAttribute(models.Model):
    """
    存储应用到物品或实体上的属性修改器。
    【修改】: 增加了通用关系，使其可以关联到任何模型。
    """
    # --- 1. 旧的直接外键，设为可选 ---
    command = models.ForeignKey(
        GeneratedCommand,
        on_delete=models.CASCADE,
        related_name="attributes",
        null=True,  # 允许为空
        blank=True, # 允许为空
        help_text="[旧] 直接关联到物品配置"
    )

    # --- 2. 新增的通用关系字段 ---
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True, blank=True,
        help_text="关联对象的类型 (物品或实体)"
    )
    object_id = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="关联对象的ID"
    )
    content_object = GenericForeignKey('content_type', 'object_id')

    # --- 其它字段保持不变 ---
    attribute = models.ForeignKey(AttributeType, on_delete=models.CASCADE)
    amount = models.FloatField()
    operation = models.IntegerField(choices=[(0, "add_value"), (1, "add_multiplied_base"), (2, "add_multiplied_total")], default=0)
    slot = models.CharField(max_length=20, choices=[("any", "Any"), ("mainhand", "Main Hand"), ("offhand", "Off Hand"), ("head", "Head"), ("chest", "Chest"), ("legs", "Legs"), ("feet", "Feet")], default="any")
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, help_text="修饰符的唯一ID，自动生成。")
    modifier_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="[重要] 仅用于 1.20.4 及更早版本。1.20.5+ 版本已废弃此字段。"
    )

    def clean(self):
        # 确保 command 和 content_object 只有一个被设置
        if self.command and self.content_object:
            raise ValidationError("一个属性修改器不能同时关联到旧的 'command' 和新的 'content_object'。")
        # if not self.command and not self.content_object:
        #     raise ValidationError("一个属性修改器必须关联到 'command' 或 'content_object'。")

    def __str__(self):
        # 改进 __str__ 以处理两种关联方式
        target = self.command or self.content_object
        return f"{self.attribute.name} on {target}"


class AppliedPotionEffect(models.Model):
    """
    将一个药水效果应用到一个物品或实体上。
    【修改】: 增加了通用关系。
    """
    # --- 1. 旧的直接外键，设为可选 ---
    command = models.ForeignKey(
        GeneratedCommand,
        on_delete=models.CASCADE,
        related_name="potion_effects",
        verbose_name="所属命令",
        null=True, blank=True,
        help_text="[旧] 直接关联到物品配置"
    )

    # --- 2. 新增的通用关系字段 ---
    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE,
        null=True, blank=True
    )
    object_id = models.PositiveIntegerField(
        null=True, blank=True
    )
    content_object = GenericForeignKey('content_type', 'object_id')

    # --- 其它字段保持不变 ---
    effect = models.ForeignKey(PotionEffectType, on_delete=models.CASCADE, verbose_name="药水效果")
    amplifier = models.PositiveIntegerField(default=0, help_text="效果等级, 从0开始 (0=I, 1=II)")
    duration = models.PositiveIntegerField(default=600, help_text="持续时间 (单位: ticks, 20 ticks = 1s)")
    is_ambient = models.BooleanField(default=False, help_text="设为True时粒子效果会有信标?")
    show_particles = models.BooleanField(default=True, help_text="是否显示粒子效果")
    show_icon = models.BooleanField(default=True, help_text="是否在HUD中显示效果图标")

    class Meta:
        verbose_name = "应用的效果"
        verbose_name_plural = "应用的效果 (药水/属性)"

    def __str__(self):
        target = self.command or self.content_object
        return f"{target} - {self.effect.name} (等级 {self.amplifier})"


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
    

#--------------------------------------------------------------------------------实体模型--------------------------------------------------------------------------------#

# ==============================================================================
# 6. 实体生成器模型 (新增)
# ==============================================================================

class EntityTag(models.Model):
    """【无需修改】存储实体的标签分类，例如 'undead', 'merchant', 'mob'"""
    name = models.CharField(max_length=50, unique=True, help_text="例如 'undead', 'merchant', 'mob'")
    description = models.CharField(max_length=200, blank=True)
    def __str__(self): return self.name
    class Meta:
        verbose_name = "实体标签"
        verbose_name_plural = "[🏷️]实体标签"


class EntityType(models.Model):
    """【无需修改】存储实体类型定义"""
    entity_id = models.CharField(max_length=100, unique=True, help_text="例如 'minecraft:zombie'")
    name = models.CharField(max_length=100)
    tags = models.ManyToManyField(EntityTag, blank=True)
    def __str__(self): return self.name
    class Meta:
        verbose_name = "实体种类"
        verbose_name_plural = "[🐑]实体种类"


class EntityComponentType(models.Model):
    """
    【修改】定义一个实体可用的 NBT 组件 (数据值)。
    这是实现需求 #2 和 #6 的核心。
    """
    VALUE_TYPE_CHOICES = [
        ('boolean', '布尔值 (是/否)'),
        ('integer', '整数'),
        ('float', '浮点数'),
        ('string', '字符串'),
        ('position_vector', '坐标向量 [x, y, z]'),
        ('json', '自定义JSON文本'),
    ]
    name = models.CharField(max_length=100, help_text="显示名称, e.g., '禁用AI'")
    nbt_key = models.CharField(max_length=100, help_text="NBT键, e.g., 'NoAI'")
    value_type = models.CharField(max_length=20, choices=VALUE_TYPE_CHOICES)
    tags = models.ManyToManyField(EntityTag, blank=True, help_text="将此组件限制在拥有特定标签的实体上")
    description = models.TextField(blank=True, help_text="为用户解释这个组件的作用")
    def __str__(self): return self.name
    class Meta:
        verbose_name = "实体组件定义"
        verbose_name_plural = "[⚙️]实体组件定义"


class GeneratedEntity(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="entities")
    title = models.CharField(max_length=100, help_text="为这个实体配置起一个名字")
    entity_type = models.ForeignKey(EntityType, on_delete=models.PROTECT)
    
    equipment = models.ManyToManyField(
        GeneratedCommand,
        through='EntityEquipmentSlot',
        blank=True,
        related_name="equipped_by_entities"
    )
    attributes = GenericRelation(AppliedAttribute, related_query_name='entity')
    potion_effects = GenericRelation(AppliedPotionEffect, related_query_name='entity')

    # --- 新增：骑乘功能 (需求 #1) ---
    passengers = models.ManyToManyField(
        'self',
        blank=True,
        symmetrical=False, # A骑B，不等于B骑A，所以设为False
        related_name='ridden_by',
        verbose_name="乘客实体"
    )

    # --- 新增：用于物品实体和投射物的功能 (需求 #3, #4) ---
    source_item = models.ForeignKey(
        GeneratedCommand,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='used_by_entities',
        help_text="关联的物品配置 (用于'物品实体'的Item标签, 或'投射物'的TridentItem等标签)",
        verbose_name="来源物品"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self): return self.title
    class Meta:
        verbose_name = "实体配置"
        verbose_name_plural = "<Σ>完整实体配置"

class AppliedEntityComponent(models.Model):
    """【无需修改】将一个组件应用到一个具体实体配置上。"""
    entity = models.ForeignKey(GeneratedEntity, on_delete=models.CASCADE, related_name="components")
    component_type = models.ForeignKey(EntityComponentType, on_delete=models.CASCADE)
    # 用一个文本字段存储各种类型的值，在生成命令时再解析
    value = models.CharField(max_length=5000)
    class Meta:
        verbose_name = "应用的实体组件"
        verbose_name_plural = "应用的实体组件"
        unique_together = ('entity', 'component_type')

# --- 【新增模型】: 用于处理装备槽位 ---
class EntityEquipmentSlot(models.Model):
    """
    通过模型 (Through Model)，连接 GeneratedEntity 和 GeneratedCommand，并指定槽位。
    """
    SLOT_CHOICES = [
        ('mainhand', '主手'), ('offhand', '副手'),
        ('head', '头部'), ('chest', '胸部'),
        ('legs', '腿部'), ('feet', '脚部'),
    ]
    entity = models.ForeignKey(GeneratedEntity, on_delete=models.CASCADE)
    item = models.ForeignKey(GeneratedCommand, on_delete=models.CASCADE)
    slot = models.CharField(max_length=10, choices=SLOT_CHOICES)
    # 新增掉落几率
    drop_chance = models.FloatField(default=1.0, help_text="物品的掉落几率 (0.0 到 1.0)")

    class Meta:
        unique_together = ('entity', 'slot') # 每个槽位只能有一件装备
        verbose_name = "实体装备槽"
        verbose_name_plural = "实体装备槽"


class TradeRecipe(models.Model):
    """
    【修改后】定义一个村民或流浪商人的单条交易。
    新增了可选的数量覆盖字段。
    """
    trader = models.ForeignKey(GeneratedEntity, on_delete=models.CASCADE, related_name="trades", limit_choices_to={'entity_type__tags__name__in': ['merchant']})
    
    # 交易输入
    buy_item1 = models.ForeignKey(GeneratedCommand, on_delete=models.PROTECT, related_name='+')
    buy_item2 = models.ForeignKey(GeneratedCommand, on_delete=models.PROTECT, related_name='+', null=True, blank=True)

    # 交易输出
    sell_item = models.ForeignKey(GeneratedCommand, on_delete=models.PROTECT, related_name='+')

    # --- 新增：数量覆盖字段 ---
    buy_item1_count = models.PositiveIntegerField(
        null=True, blank=True, help_text="留空则使用所选物品配置的默认数量"
    )
    buy_item2_count = models.PositiveIntegerField(
        null=True, blank=True, help_text="留空则使用所选物品配置的默认数量"
    )
    sell_item_count = models.PositiveIntegerField(
        null=True, blank=True, help_text="留空则使用所选物品配置的默认数量"
    )

    # 交易属性
    max_uses = models.PositiveIntegerField(default=10, help_text="最大交易次数")
    xp = models.PositiveIntegerField(default=1, help_text="给予玩家的经验值")
    price_multiplier = models.FloatField(default=0.0)
    
    class Meta:
        ordering = ['id']
        verbose_name = "村民交易"
        verbose_name_plural = "村民交易"

# --- 新增模型：用于存储所有可用的粒子效果类型 ---
class ParticleType(models.Model):
    """存储所有可用的粒子效果ID"""
    particle_id = models.CharField(max_length=100, unique=True, help_text="粒子的ID, 例如 'minecraft:flame'")
    name = models.CharField(max_length=100, help_text="用于显示的名称, 例如 '火焰'")
    min_version = models.ForeignKey(MinecraftVersion, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    max_version = models.ForeignKey(MinecraftVersion, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')

    class Meta:
        verbose_name = "粒子效果类型"
        verbose_name_plural = "[✨]粒子效果类型"
        ordering = ['name']

    def __str__(self):
        return self.name
    
# --- 新增模型：用于存储粒子效果云的独有属性 ---
class AreaEffectCloudProperties(models.Model):
    """
    存储 `area_effect_cloud` 实体的独有NBT属性。
    与 GeneratedEntity 是一对一关系。
    """
    entity = models.OneToOneField(
        GeneratedEntity,
        on_delete=models.CASCADE,
        related_name="aec_properties",
        verbose_name="所属实体配置",
        # 这是一个很好的实践，限制这个配置只能关联到 area_effect_cloud 类型的实体
        limit_choices_to={'entity_type__entity_id': 'minecraft:area_effect_cloud'}
    )
    
    duration = models.IntegerField(default=600, help_text="效果云的总持续时间 (ticks)")
    wait_time = models.IntegerField(default=20, help_text="效果云生成后，开始施加效果前的等待时间 (ticks)")
    reapplication_delay = models.IntegerField(default=40, help_text="对同一个实体重复施加效果的间隔时间 (ticks)")
    duration_on_use = models.IntegerField(default=0, help_text="每次有实体受影响时，总持续时间减少的量 (ticks)")
    radius = models.FloatField(default=3.0, help_text="效果云的初始半径（米）")
    radius_on_use = models.FloatField(default=-0.5, help_text="每次有实体受影响时，半径变化的量（可以为负数）")
    radius_per_tick = models.FloatField(default=-0.005, help_text="每 tick 半径变化的量（可以为负数，实现缩小）")
    
    # 粒子效果相关的字段
    # --- 这里是修改点 ---
    particle = models.ForeignKey(
        ParticleType,
        on_delete=models.PROTECT, # 保护，防止意外删除正在被使用的粒子效果
        null=True, blank=True, # 允许为空
        help_text="选择效果云要显示的粒子效果"
    )
    # 对于复杂的粒子参数 (如 minecraft:dust)，我们可以用一个JSON字段
    # particle_params = models.JSONField(blank=True, null=True, help_text="复杂粒子的参数，例如颜色、大小等")

    class Meta:
        verbose_name = "粒子效果云属性"
        verbose_name_plural = "粒子效果云属性"

    def __str__(self):
        return f"为 '{self.entity.title}' 配置的效果云"



# ==============================================================================
# 7. 赌博小游戏与经济系统 (新增)
# ==============================================================================
from django.db.models.signals import post_save
from django.dispatch import receiver
from decimal import Decimal

class UserWallet(models.Model):
    """
    用户资产钱包。
    包含金币余额、VIP统计数据以及'黑幕'控制参数。
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="wallet")
    balance = models.DecimalField(max_digits=20, decimal_places=2, default=0.00, verbose_name="当前金币余额")
    
    # VIP 统计字段
    total_recharged = models.DecimalField(max_digits=20, decimal_places=2, default=0.00, verbose_name="历史累计充值(RMB)")
    total_earnings = models.DecimalField(max_digits=20, decimal_places=2, default=0.00, verbose_name="历史游戏盈利总额")
    
    # 黑幕字段
    black_curtain_rate = models.FloatField(
        default=1.0, 
        help_text="运气修正值。1.0=正常，0.5=霉运(胜率减半)，2.0=欧皇(胜率翻倍)。用于后台控制该玩家输赢。"
    )
    is_flagged = models.BooleanField(default=False, verbose_name="重点监控", help_text="标记为问题赌狗，后台特殊显示")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def vip_level(self):
        """
        计算VIP等级。
        逻辑：每充值100元升1级，或者每赢10000金币升1级。取两者最高。
        """
        # 简单的硬编码逻辑，你可以根据需求修改
        level_by_charge = int(self.total_recharged // 100)
        level_by_earnings = int(self.total_earnings // 10000)
        raw_level = max(level_by_charge, level_by_earnings)
        return min(raw_level, 10) # 假设最高VIP 10级

    @property
    def fee_rate(self):
        """
        计算赌场抽水比例 (House Edge)。
        VIP越高，抽水越低。
        基础抽水 5%，每级VIP减少 0.3%，最低 1%。
        """
        base_fee = 0.05 # 5%
        discount = self.vip_level * 0.003
        final_fee = max(base_fee - discount, 0.01) # 至少抽 1%
        return final_fee

    def __str__(self):
        return f"{self.user.username} 的钱包 (VIP{self.vip_level})"

    class Meta:
        verbose_name = "用户钱包(黑幕配置)"
        verbose_name_plural = "💰用户钱包(黑幕配置)"


class GameTransaction(models.Model):
    """
    交易流水表。
    管理员在这里'添加记录'来充值，而不是直接改钱包。
    """
    TRANS_TYPES = [
        ('recharge', '后台充值(增加VIP)'),
        ('admin_grant', '系统赠送(不加VIP)'),
        ('game_bet', '游戏下注'),
        ('game_win', '游戏派彩'),
        ('withdraw', '提现/扣除'),
    ]

    wallet = models.ForeignKey(UserWallet, on_delete=models.CASCADE, related_name="transactions")
    amount = models.DecimalField(max_digits=20, decimal_places=2, verbose_name="变动金额")
    trans_type = models.CharField(max_length=20, choices=TRANS_TYPES, default='game_bet', verbose_name="交易类型")
    description = models.CharField(max_length=255, blank=True, verbose_name="备注/游戏名")
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # 在保存前，先检查是否是新建记录（也就是没有ID的时候）
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # 只有新建流水时才触发余额变动，防止管理员修改备注导致二次加钱
        if is_new:
            self._update_wallet()

    def _update_wallet(self):
        """核心逻辑：根据流水类型更新钱包余额和VIP进度"""
        w = self.wallet
        amt = Decimal(self.amount)

        if self.trans_type == 'recharge':
            w.balance += amt
            w.total_recharged += amt # 只有充值才加VIP进度
        elif self.trans_type == 'admin_grant':
            w.balance += amt
        elif self.trans_type == 'game_bet':
            w.balance -= abs(amt) # 下注扣钱
        elif self.trans_type == 'game_win':
            w.balance += amt
            # 只有净胜值才算earnings，这里简单处理，只要是派彩都累积，或者你可以在view里计算净利
            w.total_earnings += amt 
        elif self.trans_type == 'withdraw':
            w.balance -= abs(amt)
        
        w.save()

    def __str__(self):
        return f"{self.get_trans_type_display()} - {self.amount}"

    class Meta:
        verbose_name = "资金流水"
        verbose_name_plural = "🧾资金流水"

# --- 信号：创建用户时自动创建钱包 ---
@receiver(post_save, sender=User)
def create_user_wallet(sender, instance, created, **kwargs):
    if created:
        UserWallet.objects.create(user=instance)

class CasinoGameSession(models.Model):
    """
    存储正在进行中的牌局状态。
    当一局游戏结束（结算）后，这个记录可以标记为完成或删除。
    """
    GAME_TYPES = [
        ('blackjack', '21点'),
        ('zjh', '扎金花'),
        ('holdem', '德州扑克'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    game_type = models.CharField(max_length=20, choices=GAME_TYPES)
    
    # 核心：存储JSON状态
    # 包含：player_hand, dealer_hand, community_cards, pot_size, current_stage, deck_cursor...
    state_data = models.JSONField(default=dict) 
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} playing {self.game_type}"