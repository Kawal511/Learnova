"""
LLMRouter — ordered failover across multiple LLM providers.

The router *is* an ``LLMProvider``, so any module that already accepts one
takes a router with no code change. On a rate-limit or transient error it
moves to the next provider in the chain instead of raising.

Providers are constructed lazily and defensively: a missing API key means
that provider is simply absent from the chain, never an import-time crash.

Task-based preferences let each call site express intent ("this is a bulk
JSON classification, favour the fast model") without hardcoding a vendor.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Sequence

from learnova.logging_config import logger
from learnova.providers.base import LLMProvider

# Task identifiers used across the codebase.
TASK_LAYOUT = "layout"          # short JSON, high call volume, latency-sensitive
TASK_IMPROVE = "improve"        # pedagogical rewriting, quality-sensitive
TASK_QUIZ = "quiz"              # distractor quality matters
TASK_ENHANCE = "enhance"        # examples/analogies/mnemonics
TASK_DIAGRAM = "diagram"        # mermaid generation

# Preferred provider order per task. First available wins; the rest are fallback.
TASK_PREFERENCE: Dict[str, Sequence[str]] = {
    TASK_LAYOUT: ("groq", "nvidia"),
    TASK_IMPROVE: ("nvidia", "groq"),
    TASK_QUIZ: ("nvidia", "groq"),
    TASK_ENHANCE: ("nvidia", "groq"),
    TASK_DIAGRAM: ("groq", "nvidia"),
}

# Per-provider default model for each task.
TASK_MODEL: Dict[str, Dict[str, str]] = {
    "groq": {
        TASK_LAYOUT: "llama-3.1-8b-instant",
        TASK_IMPROVE: "llama-3.1-8b-instant",
        TASK_QUIZ: "llama-3.1-8b-instant",
        TASK_ENHANCE: "llama-3.1-8b-instant",
        TASK_DIAGRAM: "llama-3.1-8b-instant",
    },
    "nvidia": {
        TASK_LAYOUT: "meta/llama-3.1-8b-instruct",
        TASK_IMPROVE: "meta/llama-3.3-70b-instruct",
        TASK_QUIZ: "meta/llama-3.3-70b-instruct",
        TASK_ENHANCE: "meta/llama-3.3-70b-instruct",
        TASK_DIAGRAM: "meta/llama-3.1-8b-instruct",
    },
}


def _model_fits(provider_name: str, model: str) -> bool:
    """True when a model id belongs to the given provider's namespace."""
    namespaced = "/" in model
    if provider_name == "nvidia":
        return namespaced
    if provider_name == "groq":
        return not namespaced
    return True


def _is_retryable(exc: Exception) -> bool:
    """True when the error is worth retrying on a different provider."""
    text = f"{type(exc).__name__} {exc}".lower()
    needles = (
        "ratelimit", "rate limit", "429", "quota", "too many requests",
        "timeout", "timed out", "connection", "unavailable", "503", "502", "500",
        "overloaded", "capacity",
    )
    return any(n in text for n in needles)


class LLMRouter(LLMProvider):
    """Tries each provider in order, falling through on retryable failures."""

    def __init__(self, providers: Optional[List[tuple[str, LLMProvider]]] = None):
        """
        Args:
            providers: ordered ``(name, provider)`` pairs. When None, the chain
                is auto-built from whichever API keys are present.
        """
        self._providers: List[tuple[str, LLMProvider]] = (
            list(providers) if providers is not None else _build_default_chain()
        )
        if self._providers:
            logger.info(
                "LLMRouter ready with %d provider(s): %s",
                len(self._providers),
                ", ".join(name for name, _ in self._providers),
            )
        else:
            logger.warning("LLMRouter has no usable providers — no API keys found.")

    @property
    def available(self) -> bool:
        return bool(self._providers)

    @property
    def provider_names(self) -> List[str]:
        return [name for name, _ in self._providers]

    # ── ordering ─────────────────────────────────────────────────────────────
    def _ordered_for(self, task: Optional[str]) -> List[tuple[str, LLMProvider]]:
        if not task or task not in TASK_PREFERENCE:
            return self._providers
        preference = TASK_PREFERENCE[task]
        rank = {name: i for i, name in enumerate(preference)}
        return sorted(
            self._providers,
            key=lambda pair: rank.get(pair[0], len(preference)),
        )

    def _attempt(self, call: Callable[[LLMProvider, dict], str], task: Optional[str],
                 kwargs: dict) -> str:
        chain = self._ordered_for(task)
        if not chain:
            raise RuntimeError(
                "No LLM provider is configured. Set GROQ_API_KEY and/or NVIDIA_API_KEY."
            )

        errors: List[str] = []
        for name, provider in chain:
            call_kwargs = dict(kwargs)
            requested = call_kwargs.get("model")

            # A caller-pinned model belongs to one vendor. NVIDIA ids are
            # namespaced ("meta/llama-..."), Groq ids are not — so a pinned
            # Groq name would 404 on NVIDIA during failover. Swap in the right
            # id for whichever provider we are actually about to call.
            if requested and not _model_fits(name, requested):
                replacement = TASK_MODEL.get(name, {}).get(task or "")
                if replacement:
                    call_kwargs["model"] = replacement
                else:
                    call_kwargs.pop("model", None)
            elif not requested and task:
                model = TASK_MODEL.get(name, {}).get(task)
                if model:
                    call_kwargs["model"] = model
            try:
                return call(provider, call_kwargs)
            except Exception as exc:
                errors.append(f"{name}: {exc}")
                if _is_retryable(exc) and len(chain) > 1:
                    logger.warning(
                        "LLMRouter: %s failed (%s) — falling through to next provider.",
                        name, exc,
                    )
                    continue
                logger.error("LLMRouter: %s failed non-retryably: %s", name, exc)
                raise

        raise RuntimeError("All LLM providers failed: " + " | ".join(errors))

    # ── LLMProvider interface ────────────────────────────────────────────────
    def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs: Any) -> str:
        task = kwargs.pop("task", None)
        return self._attempt(
            lambda p, kw: p.generate(prompt, system_prompt=system_prompt, **kw),
            task, kwargs,
        )

    def chat(self, messages: List[Dict[str, str]], **kwargs: Any) -> str:
        task = kwargs.pop("task", None)
        return self._attempt(lambda p, kw: p.chat(messages, **kw), task, kwargs)

    def rewrite(self, text: str, instructions: str, **kwargs: Any) -> str:
        task = kwargs.pop("task", None)
        return self._attempt(
            lambda p, kw: p.rewrite(text, instructions, **kw), task, kwargs
        )


def _build_default_chain() -> List[tuple[str, LLMProvider]]:
    """Build the provider chain from whatever credentials are available."""
    chain: List[tuple[str, LLMProvider]] = []

    try:
        from learnova.providers.groq_provider import GroqProvider

        chain.append(("groq", GroqProvider()))
    except Exception as exc:
        logger.info("LLMRouter: Groq unavailable (%s)", exc)

    try:
        from learnova.providers.nvidia_provider import NvidiaProvider

        chain.append(("nvidia", NvidiaProvider()))
    except Exception as exc:
        logger.info("LLMRouter: NVIDIA NIM unavailable (%s)", exc)

    return chain


_default_router: Optional[LLMRouter] = None


def get_router() -> LLMRouter:
    """Process-wide shared router (providers hold reusable HTTP sessions)."""
    global _default_router
    if _default_router is None:
        _default_router = LLMRouter()
    return _default_router
