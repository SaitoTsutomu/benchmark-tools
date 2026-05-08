from django import forms
from django.contrib import admin, messages
from django.db import models
from django.db.models import Count, QuerySet
from django.http import HttpRequest

from core.benchmark import BenchmarkExecutionError, run_group_benchmark
from core.models import Group, GroupItem, GroupLlmModel, Item, LlmModel, Result


@admin.register(LlmModel)
class LlmModelAdmin(admin.ModelAdmin):
    """LLMモデル"""

    list_display = ("model", "base_url", "api_key_name", "can_parallel", "updated_at")
    readonly_fields = ("updated_at", "created_at")
    list_filter = ("can_parallel",)
    search_fields = ("model", "base_url", "api_key_name")
    ordering = ("model",)


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    """テスト項目"""

    list_display = ("name", "updated_at")
    readonly_fields = ("updated_at", "created_at")
    search_fields = ("name", "problem", "answer")
    ordering = ("name",)


class GroupItemInline(admin.TabularInline):
    """テストグループとテスト項目"""

    model = GroupItem
    extra = 0
    autocomplete_fields = ("item",)
    readonly_fields = ("updated_at", "created_at")


class GroupLlmModelInline(admin.TabularInline):
    """テストグループとLLMモデル"""

    model = GroupLlmModel
    extra = 0
    autocomplete_fields = ("llm_model",)
    readonly_fields = ("updated_at", "created_at")


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    """テストグループ"""

    list_display = ("name", "item_count", "updated_at")
    readonly_fields = ("updated_at", "created_at")
    search_fields = ("name",)
    ordering = ("name",)
    inlines = (GroupLlmModelInline, GroupItemInline)
    actions = ("run_benchmark",)

    def get_queryset(self, request: HttpRequest) -> QuerySet[Group]:
        """一覧表示用のクエリセットを取得する"""
        queryset = super().get_queryset(request)
        return queryset.annotate(item_count=Count("group_items"))

    @admin.display(description="項目数", ordering="item_count")
    def item_count(self, obj: Group) -> int:
        """グループ内のテスト項目数を返す"""
        return int(obj.item_count)

    @admin.action(description="選択したテストグループでベンチマークを実行")
    def run_benchmark(self, request: HttpRequest, queryset: QuerySet[Group]) -> None:
        """選択したテストグループでベンチマークを実行"""
        try:
            summary = run_group_benchmark(list(queryset))
        except BenchmarkExecutionError as exc:
            self.message_user(request, str(exc), level=messages.ERROR)
            return

        if summary.created_results == 0 and summary.failed_requests == 0:
            self.message_user(request, "実行対象のテスト項目がありません。", level=messages.WARNING)
            return

        if summary.failed_requests:
            self.message_user(
                request,
                f"ベンチマークを実行しました。成功: {summary.created_results}件 / 失敗: {summary.failed_requests}件",
                level=messages.WARNING,
            )
            return

        self.message_user(request, f"ベンチマークを実行しました。成功: {summary.created_results}件")


@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    """テスト結果"""

    list_display = ("group", "item", "llm_model", "judge", "updated_at")
    readonly_fields = ("updated_at", "created_at")
    list_filter = ("group", "llm_model", "judge")
    search_fields = ("group__name", "item__name", "llm_model__model")
    autocomplete_fields = ("group", "item", "llm_model")

    def formfield_for_dbfield(self, db_field: models.Field, request: HttpRequest, **kwargs: object) -> forms.Field:
        """resultフィールドの入力欄を複数行向けに調整する"""
        if db_field.name == "result":
            kwargs["widget"] = forms.Textarea(attrs={"rows": 8, "cols": 72})
        return super().formfield_for_dbfield(db_field, request, **kwargs)
