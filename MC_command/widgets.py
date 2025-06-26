# MC_command/widgets.py (新文件)

import json
from django import forms
from django.utils.safestring import mark_safe

class ColorPickerWidget(forms.Widget):
    template_name = 'MC_command/widgets/color_picker_widget.html'

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        if value in [None, '']:
            context['widget']['colors_list'] = []
            context['widget']['is_random'] = False
        elif value == 'random':
            context['widget']['colors_list'] = []
            context['widget']['is_random'] = True
        else:
            try:
                # 将整数颜色值转换为十六进制字符串
                int_colors = json.loads(value)
                context['widget']['colors_list'] = [f'#{c:06x}' for c in int_colors]
                context['widget']['is_random'] = False
            except (json.JSONDecodeError, TypeError):
                context['widget']['colors_list'] = []
                context['widget']['is_random'] = False
        return context

    class Media:
        css = {
            'all': ('MC_command/css/admin_color_widget.css',)
        }
        js = ('MC_command/js/admin_color_widget.js',)