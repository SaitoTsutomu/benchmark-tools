from logging import getLogger
from typing import TYPE_CHECKING

from django import forms
from django.contrib import admin, messages
from django.db import IntegrityError, transaction
from django.db.models import Avg, Count, QuerySet
from django.shortcuts import redirect
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html

from core.benchmark import (
    BenchmarkExecutionError,
    check_judge,
    normalize_text,
    run_group_benchmark,
)
from core.models import Group, GroupItem, GroupLlmModel, Item, LlmModel, Result

if TYPE_CHECKING:
    from django.db import models
    from django.http import HttpRequest
    from django.http.response import HttpResponse
    from django.urls.resolvers import URLPattern

logger = getLogger(__name__)


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

    list_display = ("name", "title", "updated_at")
    readonly_fields = ("updated_at", "created_at")
    search_fields = ("name", "problem", "answer")
    ordering = ("name",)
    actions = ("new_group",)

    @admin.action(description="選択したテスト項目で新しいグループを作成")
    def new_group(self, request: HttpRequest, queryset: QuerySet[Item]) -> HttpResponse | None:
        """選択したテスト項目で新しいグループを作成"""
        max_attempts = 100
        for i in range(max_attempts):
            name = f"New Group{i}"
            try:
                with transaction.atomic():
                    group = Group.objects.create(name=name)
                    objs = [GroupItem(group=group, item=item) for item in queryset]
                    GroupItem.objects.bulk_create(objs)
                break
            except IntegrityError:
                continue
        else:
            self.message_user(request, "新しいグループを作成できませんでした", level=messages.ERROR)
            return None

        self.message_user(request, "新しいグループを作成しました", level=messages.SUCCESS)
        return redirect("admin:core_group_change", object_id=group.id)


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

    list_display = ("name", "llm_model_count", "item_count", "updated_at", "display_run")
    readonly_fields = ("updated_at", "created_at")
    search_fields = ("name",)
    ordering = ("name",)
    inlines = (GroupLlmModelInline, GroupItemInline)
    actions = ("run_benchmark",)

    def get_urls(self) -> list[URLPattern]:
        """管理画面用の追加URLを返す"""
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:object_id>/run-benchmark/",
                self.admin_site.admin_view(self.run_benchmark_view),
                name="core_group_run_benchmark",
            ),
        ]
        return custom_urls + urls

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

    @classmethod
    @admin.display(description="実行")
    def display_run(cls, obj: Group) -> str:
        """実行のリンク"""
        url = reverse("admin:core_group_run_benchmark", args=(obj.pk,))
        return format_html('<a href="{}">実行</a>', url)

    def run_benchmark_view(self, request: HttpRequest, object_id: int) -> HttpResponse:
        """指定グループのベンチマークを実行する"""
        queryset = self.get_queryset(request).filter(pk=object_id)
        response = self.run_benchmark(request, queryset)
        return response or redirect("admin:core_group_changelist")

    @admin.action(description="選択したテストグループでベンチマークを実行")
    def run_benchmark(self, request: HttpRequest, queryset: QuerySet[Group]) -> HttpResponse | None:
        """選択したテストグループでベンチマークを実行"""
        try:
            summary = run_group_benchmark([*queryset])
        except BenchmarkExecutionError as exc:
            self.message_user(request, str(exc), level=messages.ERROR)
            return None

        if summary.created_results == 0 and summary.failed_requests == 0:
            self.message_user(request, "実行対象のテスト項目がありません。", level=messages.WARNING)
            return None

        if summary.failed_requests:
            self.message_user(
                request,
                f"ベンチマークを実行しました。全 {summary.created_results} 件中、失敗 {summary.failed_requests} 件",
                level=messages.WARNING,
            )
        else:
            self.message_user(request, f"ベンチマークを実行しました。全 {summary.created_results} 件")

        query: dict[str, int] = {}
        if queryset.count() == 1:
            query["group__id__exact"] = queryset.first().id
        return redirect(reverse("admin:core_result_changelist", query=query))


@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    """テスト結果"""

    list_display = ("group", "item", "llm_model", "judge", "display_exec_time", "updated_at")
    readonly_fields = ("updated_at", "created_at")
    list_filter = ("group", "llm_model", "judge")
    search_fields = ("group__name", "item__name", "llm_model__model")
    autocomplete_fields = ("group", "item", "llm_model")
    change_list_template = "admin/core/result/change_list.html"
    actions = ("run_check_judge",)

    @classmethod
    def _summary_by_dimension(cls, queryset: QuerySet[Result], label_field: str) -> list[dict[str, object]]:
        """指定軸ごとに結果を集計する。"""
        all_combo_rows = queryset.values("group_id", "item_id", label_field).annotate(
            success=Avg("judge"),
            avg_exec_time=Avg("exec_time"),
        )
        per_combo_rows = (
            queryset.filter(judge__isnull=False)
            .values("group_id", "item_id", label_field)
            .annotate(
                success=Avg("judge"),
                avg_exec_time=Avg("exec_time"),
            )
        )
        summary_map: dict[str, dict[str, float | int]] = {}
        for row in all_combo_rows:
            label = str(row[label_field])
            summary = summary_map.setdefault(
                label,
                {"total": 0, "executed_total": 0, "unexecuted_total": 0, "success": 0.0, "exec_time_sum": 0.0},
            )
            summary["total"] += 1
            if row["success"] is None:
                summary["unexecuted_total"] += 1

        for row in per_combo_rows:
            label = str(row[label_field])
            summary = summary_map.setdefault(
                label,
                {"total": 0, "executed_total": 0, "unexecuted_total": 0, "success": 0.0, "exec_time_sum": 0.0},
            )
            summary["executed_total"] += 1
            summary["success"] += float(row["success"] or 0.0)
            summary["exec_time_sum"] += float(row["avg_exec_time"] or 0.0)

        summary_rows: list[dict[str, object]] = []
        for label, summary in summary_map.items():
            total = int(summary["total"])
            executed_total = int(summary["executed_total"])
            unexecuted_total = int(summary["unexecuted_total"])
            success = float(summary["success"])
            avg_exec_time = (float(summary["exec_time_sum"]) / executed_total) if executed_total else 0.0
            summary_rows.append(
                {
                    "label": label,
                    "total": executed_total,
                    "success": success,
                    "accuracy": (success / executed_total * 100.0) if executed_total else 0.0,
                    "unexecuted_ratio": (unexecuted_total / total * 100.0) if total else 0.0,
                    "avg_exec_time": avg_exec_time,
                },
            )

        summary_rows.sort(key=lambda row: (-float(row["success"]), float(row["avg_exec_time"]), str(row["label"])))
        return summary_rows

    @classmethod
    def summary_by_llm(cls, queryset: QuerySet[Result]) -> list[dict[str, object]]:
        """指定クエリの結果をLLM単位で集計する。"""
        return cls._summary_by_dimension(queryset, "llm_model__model")

    @classmethod
    def summary_by_group(cls, queryset: QuerySet[Result]) -> list[dict[str, object]]:
        """指定クエリの結果をグループ単位で集計する。"""
        return cls._summary_by_dimension(queryset, "group__name")

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
        context["summary_all_by_llm"] = self.summary_by_llm(filtered_results)
        context["summary_all_by_group"] = self.summary_by_group(filtered_results)
        return response

    def formfield_for_dbfield(
        self,
        db_field: models.Field,
        request: HttpRequest,
        **kwargs: object,
    ) -> forms.Field | None:
        """resultフィールドの入力欄を複数行向けに調整する"""
        if db_field.name == "result":
            kwargs["widget"] = forms.Textarea(attrs={"rows": 8, "cols": 72})
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    @classmethod
    @admin.display(ordering="exec_time", description="実行時間")
    def display_exec_time(cls, obj: Result) -> str:
        return f"{obj.exec_time:.1f}"

    @admin.action(description="選択したテスト結果を再判定")
    def run_check_judge(self, request: HttpRequest, queryset: QuerySet[Result]) -> None:
        """選択したテスト結果を再判定"""
        results = [*queryset]
        for result in results:
            item = result.item
            answer = normalize_text(item.answer)
            result.judge = check_judge(item.answer_code, item.re_output, answer, result.result)
        Result.objects.bulk_update(results, ["judge"])
        queryset.update(updated_at=timezone.now())
        self.message_user(request, f"{len(queryset)}件再判定しました")
