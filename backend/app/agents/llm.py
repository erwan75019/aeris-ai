"""Optional local Ollama narrative adapter; structured analysis remains tool-owned."""

import httpx


class LLMError(RuntimeError):
    pass


class OllamaNarrator:
    def __init__(
        self,
        *,
        model: str,
        base_url: str,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._client = http_client or httpx.Client(timeout=30.0)

    def narrate(self, evidence_json: str) -> str:
        prompt = (
            "Summarize this AERIS research evidence. Preserve the separation between facts, "
            "predictions and hypotheses. Never infer an incident, danger or causality.\n\n"
            f"{evidence_json}"
        )
        try:
            response = self._client.post(
                f"{self._base_url}/api/chat",
                json={
                    "model": self._model,
                    "stream": False,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            response.raise_for_status()
            content = response.json()["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                raise LLMError("Ollama returned an empty narrative")
            return content.strip()
        except LLMError:
            raise
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            raise LLMError("Ollama narrative generation failed") from exc
