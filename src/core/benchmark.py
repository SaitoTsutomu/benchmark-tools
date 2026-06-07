import os
import subprocess  # noqa: S404
from dataclasses import dataclass
from time import perf_counter

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
    return result.final_output, exec_time


def run_code(code: str) -> tuple[int, str, str]:
    """コード実行"""
    result = subprocess.run(
        [  # noqa: S607
            "docker",
            "run",
            "-i",
            "--rm",
            "--user",
            "1000:1000",
            "--read-only",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,size=64m",  # noqa: S108
            "--network",
            "none",
            "--memory=256m",
            "--cpus=1",
            "--pids-limit=64",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges",
            "--security-opt=apparmor=docker-default",
            "sandbox",
            "python",
            "-",
        ],
        input=code,
        text=True,
        capture_output=True,
        check=False,
    )
    return result.returncode, result.stdout, result.stderr


def check_judge(answer_code: str, answer: str, result: str) -> bool:
    """判定"""
    if not answer_code:
        return answer in _normalize_text(result)

    returncode, actual, stderr = run_code(result)
    if returncode or stderr:
        msg = f"実行エラー {returncode} {stderr}"
        raise RuntimeError(msg)
    _, expected, _ = run_code(answer_code)
    return actual == expected


def run_group_benchmark(groups: list[Group]) -> BenchmarkRunSummary:
    """テストグループでベンチマークを実行"""
    created_results = 0
    failed_requests = 0

    for group in groups:
        llm_models = LlmModel.objects.filter(group_llm_models__group=group)
        items = Item.objects.filter(group_items__group=group)
        if not items or not llm_models:
            continue

        for item in items:
            answer = _normalize_text(item.answer)
            for llm_model in llm_models:
                result = ""
                exec_time = float("nan")
                judge = None
                try:
                    result, exec_time = _run_single_benchmark(item=item, llm_model=llm_model)
                    judge = check_judge(item.answer_code, answer, result)
                except BenchmarkExecutionError:
                    failed_requests += 1
                Result.objects.create(
                    group=group,
                    item=item,
                    llm_model=llm_model,
                    result=result,
                    exec_time=exec_time,
                    judge=judge,
                )
                created_results += 1

    return BenchmarkRunSummary(created_results=created_results, failed_requests=failed_requests)
