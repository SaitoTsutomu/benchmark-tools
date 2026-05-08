import os
from dataclasses import dataclass

from agents import Agent, Runner
from agents.extensions.models.litellm_model import LitellmModel

from core.models import Group, Item, LlmModel, Result


@dataclass(slots=True)
class BenchmarkRunSummary:
    """ベンチマーク実行結果"""

    created_results: int
    failed_requests: int


class BenchmarkExecutionError(Exception):
    """ベンチマーク実行時の業務エラー"""


def _normalize_text(value: str) -> str:
    return " ".join(value.strip().split())


def _resolve_api_key(llm_model: LlmModel) -> str:
    key_name = llm_model.api_key_name.strip()
    if not key_name:
        return "_"

    api_key = os.getenv(key_name, "")
    if not api_key:
        msg = f"環境変数 '{key_name}' が未設定のため、モデル '{llm_model.model}' を実行できません"
        raise BenchmarkExecutionError(msg)
    return api_key


def _run_single_benchmark(item: Item, llm_model: LlmModel) -> bool:
    api_key = _resolve_api_key(llm_model)
    model = LitellmModel(llm_model.model, base_url=llm_model.base_url, api_key=api_key)
    agent = Agent(name="Assistant", model=model)
    result = Runner.run_sync(agent, item.problem)
    return _normalize_text(result.final_output) == _normalize_text(item.answer)


def run_group_benchmark(groups: list[Group]) -> BenchmarkRunSummary:
    """テストグループでベンチマークを実行"""
    llm_models = list(LlmModel.objects.all())
    if not llm_models:
        msg = "LLMモデルが1件も登録されていません"
        raise BenchmarkExecutionError(msg)

    created_results = 0
    failed_requests = 0

    for group in groups:
        items = [group_item.item for group_item in group.group_items.select_related("item")]
        if not items:
            continue

        for item in items:
            for llm_model in llm_models:
                try:
                    judge = _run_single_benchmark(item=item, llm_model=llm_model)
                except BenchmarkExecutionError:
                    raise
                except Exception:
                    failed_requests += 1
                    continue
                Result.objects.create(group=group, item=item, llm_model=llm_model, judge=judge)
                created_results += 1

    return BenchmarkRunSummary(created_results=created_results, failed_requests=failed_requests)
