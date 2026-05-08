import os
from time import perf_counter
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


def _run_single_benchmark(item: Item, llm_model: LlmModel) -> tuple[str, float]:
    """単一ベンチマークを実行し、応答と実行時間を返す"""
    api_key = _resolve_api_key(llm_model)
    model = LitellmModel(llm_model.model, base_url=llm_model.base_url, api_key=api_key)
    agent = Agent(
        name="Assistant",
        model=model,
        instructions="コードブロックは不要。出力は常に解答のみ出力すること",
    )
    start = perf_counter()
    result = Runner.run_sync(agent, item.problem)
    exec_time = perf_counter() - start
    return _normalize_text(result.final_output), exec_time


def run_group_benchmark(groups: list[Group]) -> BenchmarkRunSummary:
    """テストグループでベンチマークを実行"""
    created_results = 0
    failed_requests = 0

    for group in groups:
        items = [group_item.item for group_item in group.group_items.select_related("item")]
        llm_models = [entry.llm_model for entry in group.group_llm_models.select_related("llm_model")]
        if not items or not llm_models:
            continue

        for item in items:
            for llm_model in llm_models:
                try:
                    result, exec_time = _run_single_benchmark(item=item, llm_model=llm_model)
                except BenchmarkExecutionError:
                    raise
                except Exception:
                    failed_requests += 1
                    continue
                Result.objects.create(
                    group=group,
                    item=item,
                    llm_model=llm_model,
                    result=result,
                    exec_time=exec_time,
                    judge=item.answer in result,
                )
                created_results += 1

    return BenchmarkRunSummary(created_results=created_results, failed_requests=failed_requests)
