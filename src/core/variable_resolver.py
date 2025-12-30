"""Variable Resolver for PyAPI Studio"""

import re
from typing import Optional
from dataclasses import dataclass


@dataclass
class Variable:
    """변수 데이터"""
    key: str
    value: str
    is_secret: bool = False
    environment_id: Optional[int] = None


class VariableResolver:
    """변수 치환 엔진"""

    VARIABLE_PATTERN = re.compile(r'\{\{([^}]+)\}\}')

    def __init__(self):
        self._global_variables: dict[str, Variable] = {}
        self._environment_variables: dict[str, Variable] = {}
        self._runtime_variables: dict[str, str] = {}

    def set_global_variables(self, variables: dict[str, Variable]) -> None:
        """글로벌 변수 설정"""
        self._global_variables = variables

    def set_environment_variables(self, variables: dict[str, Variable]) -> None:
        """환경 변수 설정"""
        self._environment_variables = variables

    def set_runtime_variable(self, key: str, value: str) -> None:
        """스크립트에서 설정하는 런타임 변수"""
        self._runtime_variables[key] = value

    def resolve(self, text: str) -> str:
        """텍스트 내의 모든 변수를 치환"""
        if not text:
            return text

        def replacer(match: re.Match) -> str:
            var_name = match.group(1).strip()
            return self._get_value(var_name)

        return self.VARIABLE_PATTERN.sub(replacer, text)

    def resolve_dict(self, data: dict) -> dict:
        """딕셔너리 내 모든 값의 변수 치환"""
        result = {}
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = self.resolve(value)
            else:
                result[key] = value
        return result

    def _get_value(self, var_name: str) -> str:
        """변수 값 조회 (우선순위: runtime > environment > global)"""
        # 1. Runtime 변수
        if var_name in self._runtime_variables:
            return self._runtime_variables[var_name]

        # 2. Environment 변수
        if var_name in self._environment_variables:
            return self._environment_variables[var_name].value

        # 3. Global 변수
        if var_name in self._global_variables:
            return self._global_variables[var_name].value

        # 미발견 시 원본 유지
        return f"{{{{{var_name}}}}}"

    def get_unresolved_variables(self, text: str) -> list[str]:
        """치환되지 않은 변수 목록 반환"""
        resolved = self.resolve(text)
        matches = self.VARIABLE_PATTERN.findall(resolved)
        return list(set(matches))

    def validate(self, text: str) -> tuple[bool, list[str]]:
        """모든 변수가 정의되어 있는지 검증"""
        unresolved = self.get_unresolved_variables(text)
        return len(unresolved) == 0, unresolved

    def clear_runtime(self) -> None:
        """런타임 변수 초기화"""
        self._runtime_variables.clear()

    def get_all_variables(self) -> dict[str, str]:
        """모든 변수 반환 (우선순위 적용)"""
        result = {}
        
        # Global 먼저
        for key, var in self._global_variables.items():
            result[key] = var.value
        
        # Environment가 덮어씀
        for key, var in self._environment_variables.items():
            result[key] = var.value
        
        # Runtime이 최종 덮어씀
        result.update(self._runtime_variables)
        
        return result
