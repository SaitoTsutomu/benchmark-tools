from django.contrib import admin

from core.models import Group, GroupItem, Item, LlmModel, Result


@admin.register(LlmModel)
class LlmModelAdmin(admin.ModelAdmin):
    """LLMモデル"""

    list_display = ("model", "base_url", "api_key_name", "can_parallel", "updated_at")
    list_filter = ("can_parallel",)
    search_fields = ("model", "base_url", "api_key_name")
    ordering = ("model",)


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    """テスト項目"""

    list_display = ("name", "updated_at")
    search_fields = ("name", "problem", "answer")
    ordering = ("name",)


class GroupItemInline(admin.TabularInline):
    """テストグループとテスト項目"""

    model = GroupItem
    extra = 0
    autocomplete_fields = ("item",)


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    """テストグループ"""

    list_display = ("name", "updated_at")
    search_fields = ("name",)
    ordering = ("name",)
    inlines = (GroupItemInline,)


@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    """テスト結果"""

    list_display = ("group", "item", "llm_model", "judge", "updated_at")
    list_filter = ("group", "llm_model", "judge")
    search_fields = ("group__name", "item__name", "llm_model__model")
    autocomplete_fields = ("group", "item", "llm_model")
