"""Terminal interaction adapters with optional questionary support."""
from __future__ import annotations

from typing import List


class PromptAdapter:
    def select(self, message: str, choices: List[str], default_index: int = 0) -> str:
        print(message)
        for index, item in enumerate(choices, start=1):
            marker = " (default)" if index - 1 == default_index else ""
            print(f"  {index}) {item}{marker}")
        raw = input("Choose: ").strip()
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(choices):
                return choices[idx]
        return choices[default_index]

    def text(self, message: str, default: str = "") -> str:
        prompt = f"{message}"
        if default:
            prompt += f" [{default}]"
        prompt += ": "
        value = input(prompt).strip()
        return value or default

    def confirm(self, message: str, default: bool = True) -> bool:
        suffix = "(Y/n)" if default else "(y/N)"
        raw = input(f"{message} {suffix}: ").strip().lower()
        if not raw:
            return default
        return raw in {"y", "yes"}

    def multi_select(self, message: str, choices: List[str], default_selected: Optional[List[str]] = None) -> List[str]:
        """Present numbered choices and accept comma-separated indices.

        Returns the list of selected choice strings. If the user presses
        Enter, returns the provided defaults or the first choice.
        """
        print(message)
        for index, item in enumerate(choices, start=1):
            marker = " (default)" if default_selected and item in default_selected else ""
            print(f"  {index}) {item}{marker}")
        raw = input("Choose (comma-separated numbers, e.g. 1,3): ").strip()
        if not raw:
            if default_selected:
                return [c for c in choices if c in default_selected]
            return [choices[0]] if choices else []

        parts = [p.strip() for p in raw.split(",") if p.strip()]
        selected = []
        for part in parts:
            if part.isdigit():
                idx = int(part) - 1
                if 0 <= idx < len(choices):
                    selected.append(choices[idx])
        return selected


class QuestionaryAdapter(PromptAdapter):
    def __init__(self):
        import questionary  # type: ignore

        self.questionary = questionary

    def select(self, message: str, choices: List[str], default_index: int = 0) -> str:
        # Use questionary's interactive select (arrow-key navigation).
        # Do not print numbered choices or accept numeric input here so the
        # interactive UI remains primary when questionary is available.
        return self.questionary.select(
            message,
            choices=choices,
            default=choices[default_index],
        ).ask() or choices[default_index]

    def multi_select(self, message: str, choices: List[str], default_selected: Optional[List[str]] = None) -> List[str]:
        # Use questionary's checkbox for multi-selection (arrow/space to toggle).
        defaults = list(default_selected or [])
        if defaults:
            result = self.questionary.checkbox(message, choices=choices, default=defaults).ask()
        else:
            # Avoid passing an empty default list which some questionary versions
            # treat as an invalid default value.
            result = self.questionary.checkbox(message, choices=choices).ask()
        return list(result or [])

    def text(self, message: str, default: str = "") -> str:
        return self.questionary.text(message, default=default).ask() or default

    def confirm(self, message: str, default: bool = True) -> bool:
        return bool(self.questionary.confirm(message, default=default).ask())


def build_prompt_adapter(prefer_questionary: bool = True) -> PromptAdapter:
    if prefer_questionary:
        try:
            return QuestionaryAdapter()
        except Exception:
            return PromptAdapter()
    return PromptAdapter()
