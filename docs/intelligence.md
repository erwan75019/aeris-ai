# AERIS Intelligence

AERIS Intelligence is a tool-driven orchestration layer, not a set of static
personas. Every report runs four specialists:

- `flight_analyst` queries the normalized historical track;
- `anomaly_investigator` executes the active anomaly model and records evidence;
- `prediction_analyst` executes the trained/fallback trajectory predictor;
- `weather_analyst` obtains explicit synthetic offline context, or records that
  weather was disabled.

The report generator preserves each specialist's structured finding and every
tool call. Facts, predictions, hypotheses and limitations remain separate in the
API. An unavailable tool produces `limited`/`error` evidence rather than an
invented answer.

## Optional Ollama narrative

Set the following to let a local model narrate the already-structured evidence:

```bash
AERIS_LLM_PROVIDER=ollama
AERIS_LLM_MODEL=qwen3:4b
AERIS_LLM_BASE_URL=http://127.0.0.1:11434
```

The LLM does not replace tools or calculate model results. A prompt explicitly
forbids causal/safety claims. If Ollama fails, the response remains usable in
`deterministic_fallback` mode, logs the error and keeps all specialist evidence.

No remote LLM is configured by default, and no API key is required for the
offline application.
