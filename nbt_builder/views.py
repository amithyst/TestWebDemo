from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, ValidationError

from .models import Component, StructureDefinition
from .serializers import ComponentSerializer, StructureDefinitionSerializer

class ComponentListView(APIView):
    """
    API视图：获取在特定Minecraft版本下所有可用的组件列表。
    需要一个查询参数 `version`，例如: /api/components/?version=1.20.4
    """
    def get(self, request, *args, **kwargs):
        version = request.query_params.get('version', None)
        if not version:
            raise ValidationError({'error': 'A "version" query parameter is required.'})

        # 找到所有在目标版本下有有效结构定义的组件
        # 使用 distinct() 确保每个组件只返回一次
        components = Component.objects.filter(
            structures__min_version__lte=version,
            structures__max_version__gte=version
        ).distinct()
        
        serializer = ComponentSerializer(components, many=True)
        return Response(serializer.data)


class ComponentDetailView(APIView):
    """
    API视图：获取某个特定组件在特定版本下的详细结构定义和数据选项。
    需要一个查询参数 `version`，例如: /api/components/enchantments/?version=1.20.4
    """
    def get(self, request, component_key, *args, **kwargs):
        version = request.query_params.get('version', None)
        if not version:
            raise ValidationError({'error': 'A "version" query parameter is required.'})

        try:
            # 找到完全匹配组件key和版本范围的那个唯一的结构定义
            structure = StructureDefinition.objects.get(
                component__component_key=component_key,
                min_version__lte=version,
                max_version__gte=version
            )
        except StructureDefinition.DoesNotExist:
            raise NotFound(f"No structure definition found for component '{component_key}' and version '{version}'.")
        except StructureDefinition.MultipleObjectsReturned:
            # 这是一个重要的错误处理，如果您的数据有重叠的版本范围，这里会报警
            raise ValidationError(f"Error: Multiple structure definitions found for '{component_key}' and version '{version}'. Please check your data for overlapping version ranges.")

        # 在调用序列化器时，通过 context 传入 'version'
        # 这样，嵌套的 AttributeDefinitionSerializer 就能获取到它
        serializer_context = {'version': version}
        serializer = StructureDefinitionSerializer(structure, context=serializer_context)
        return Response(serializer.data)