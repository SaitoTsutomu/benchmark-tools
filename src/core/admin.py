from typing import TYPE_CHECKING

from django import forms
from django.contrib import admin, messages
from django.db.models import Avg, Count, Q, QuerySet

from core.benchmark import BenchmarkExecutionError, run_group_benchmark
from core.models import Group, GroupItem, GroupLlmModel, Item, LlmModel, Result

if TYPE_CHECKING:
    from collections.abc import Iterable

    from django.db import models
    from django.http import HttpRequest
    from django.http.response import HttpResponse


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

    list_display = ("name", "llm_model_count", "item_count", "updated_at")
    readonly_fields = ("updated_at", "created_at")
    search_fields = ("name",)
    ordering = ("name",)
    inlines = (GroupLlmModelInline, GroupItemInline)
    actions = ("run_benchmark",)

    def get_queryset(self, request: HttpRequest) -> QuerySet[Group]:
        """一覧表示用のクエリセットを取得する"""
        queryset = super().get_queryset(request)
        return queryset.annotate(
            llm_model_count=Count("group_llm_models", distinct=True),
            item_count=Count("group_items", distinct=True),
        )

    @classmethod
    @admin.display(description="LLM数", ordering="llm_model_count")
    def llm_model_count(cls, obj: Group) -> int:
        """グループ内のLLM数を返す"""
        return int(obj.llm_model_count)

    @classmethod
    @admin.display(description="項目数", ordering="item_count")
    def item_count(cls, obj: Group) -> int:
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
    change_list_template = "admin/core/result/change_list.html"

    @staticmethod
    def _build_summary_rows(
        summary_queryset: Iterable[dict[str, object]],
        label_key: str,
    ) -> list[dict[str, object]]:
        """集計クエリ結果を表示用の行データへ変換する。"""
        rows: list[dict[str, object]] = []
        for row in summary_queryset:
            total = int(row["total"])
            success = int(row["success"])
            accuracy = (success / total * 100.0) if total else 0.0
            rows.append(
                {
                    "label": str(row[label_key]),
                    "total": total,
                    "success": success,
                    "accuracy": accuracy,
                    "avg_exec_time": float(row["avg_exec_time"]),
                },
            )
        return rows

    def _summary_by_llm(self, queryset: QuerySet[Result]) -> list[dict[str, object]]:
        """指定クエリの結果をLLM単位で集計する。"""
        summary_queryset = (
            queryset.values("llm_model__model")
            .annotate(
                total=Count("id"),
                success=Count("id", filter=Q(judge=True)),
                avg_exec_time=Avg("exec_time"),
            )
            .order_by("-success", "avg_exec_time", "llm_model__model")
        )
        return self._build_summary_rows(summary_queryset=summary_queryset, label_key="llm_model__model")

    def changelist_view(self, request: HttpRequest, extra_context: dict[str, object] | None = None) -> HttpResponse:
        """一覧画面に集計サマリーを追加する。"""
        response = super().changelist_view(request, extra_context=extra_context)
        context = getattr(response, "context_data", None)
        if context is None:
            return response

        changelist = context.get("cl")
        if changelist is None:
            return response

        filtered_results = changelist.queryset
        context["summary_all_by_llm"] = self._summary_by_llm(filtered_results)
        return response

    def formfield_for_dbfield(self, db_field: models.Field, request: HttpRequest, **kwargs: object) -> None:
        """resultフィールドの入力欄を複数行向けに調整する"""
        if db_field.name == "result":
            kwargs["widget"] = forms.Textarea(attrs={"rows": 8, "cols": 72})
        super().formfield_for_dbfield(db_field, request, **kwargs)
