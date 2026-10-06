import asyncio
import json
import random
from collections.abc import Callable
from typing import cast

import outlines
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    OpenAI,
    RateLimitError,
)
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionUserMessageParam,
)
from openai.types.chat.completion_create_params import ResponseFormatJSONObject

from config import LLM_API_BASE_URL, LLM_API_KEY, LLM_API_MODEL_ID

client = OpenAI(
    api_key=LLM_API_KEY,
    base_url=LLM_API_BASE_URL,
)

model = outlines.from_openai(client, LLM_API_MODEL_ID)

TRANSIENT_STATUSES = {408, 409, 425, 429, 500, 502, 503, 504}

TRANSIENT_ATTEMPTS = 3
TRANSIENT_BASE_DELAY = 2.0
TRANSIENT_MAX_DELAY = 30.0


def is_transient(exc: Exception) -> bool:
    """True for rate limits and transport faults worth retrying.

    Schema and validation errors are deliberately excluded so they
    raise immediately instead of burning the retry budget.
    """

    if isinstance(
        exc,
        (RateLimitError, APITimeoutError, APIConnectionError),
    ):
        return True

    if isinstance(exc, APIStatusError):
        return exc.status_code in TRANSIENT_STATUSES or exc.status_code >= 500

    return False


def retry_after_seconds(exc: Exception) -> float | None:
    """Parse the Retry-After header, or None when absent/unparsable."""

    response = getattr(exc, "response", None)

    if response is None:
        return None

    try:
        raw = response.headers.get("retry-after")

        if raw is None:
            return None

        return float(raw)
    except (AttributeError, TypeError, ValueError):
        return None


async def call_with_retry(
    label: str,
    fn: Callable[[], object],
    *,
    max_attempts: int = TRANSIENT_ATTEMPTS,
    base_delay: float = TRANSIENT_BASE_DELAY,
    max_delay: float = TRANSIENT_MAX_DELAY,
):
    """Run `fn` off-thread, retrying only transient API failures.

    This is the transport budget. It is deliberately separate from the
    schema budget in `run_model` so a rate limit never consumes a
    regeneration attempt.
    """

    for attempt in range(1, max_attempts + 1):
        try:
            return await asyncio.to_thread(fn)

        except Exception as exc:
            if not is_transient(exc) or attempt == max_attempts:
                raise

            hinted = retry_after_seconds(exc)

            delay = min(
                hinted if hinted is not None else base_delay * 2 ** (attempt - 1),
                max_delay,
            )

            # Jitter keeps the stage-1 fan-out from retrying in
            # lockstep and re-triggering the same limit.
            delay += random.uniform(0, delay * 0.25)

            print(
                f"[RATE-LIMIT] {label} attempt "
                f"{attempt}/{max_attempts} sleep {delay:.1f}s"
            )

            await asyncio.sleep(delay)


async def repair_output(
    bad_output,
    output_schema,
    reasoning: str = "high",
):
    if isinstance(bad_output, str):
        bad_output_text = bad_output
    else:
        bad_output_text = json.dumps(
            bad_output,
            ensure_ascii=False,
            indent=2,
        )

    repair_prompt = f"""
You are a JSON repair assistant.

The previous model generated output that could not be
validated against the required Pydantic schema.

Repair the output so that it conforms exactly to this schema.

IMPORTANT:
- Preserve the original information whenever possible.
- Do not invent new information.
- Do not change valid values unnecessarily.
- Fix structural, formatting, or schema violations.
- Return ONLY valid JSON.
- Do not use markdown fences.
- Do not add explanations.

REQUIRED SCHEMA:

{json.dumps(output_schema.model_json_schema(), indent=2)}

INVALID OUTPUT:

{bad_output_text}

Return the repaired JSON only.
"""

    messages: list[ChatCompletionUserMessageParam] = [
        {
            "role": "user",
            "content": repair_prompt,
        }
    ]

    response_format = ResponseFormatJSONObject(type="json_object")

    def request() -> ChatCompletion:
        return cast(
            ChatCompletion,
            client.chat.completions.create(
                model=LLM_API_MODEL_ID,
                messages=messages,
                response_format=response_format,
                extra_body={"reasoning": {"effort": reasoning}},
            ),
        )

    response = await call_with_retry(
        f"repair:{output_schema.__name__}",
        request,
    )

    content = response.choices[0].message.content

    if content is None:
        raise ValueError("[ERROR] Repair model returned no content")

    return output_schema.model_validate_json(content)


def coerce_plain_text(raw_output, output_schema):
    """Wrap a single-field text schema around a plain text model response."""

    if not isinstance(raw_output, str):
        return None

    text = raw_output.strip()

    if text.startswith("```"):
        text = "\n".join(
            line for line in text.splitlines() if not line.strip().startswith("```")
        ).strip()

        try:
            return output_schema.model_validate_json(text)
        except Exception:
            pass

    if not text:
        return None

    fields = output_schema.model_fields

    if len(fields) != 1:
        return None

    field_name, field = next(iter(fields.items()))

    if field.annotation is not str:
        return None

    return output_schema(**{field_name: text})


async def run_model(
    name: str,
    prompt: str,
    output_schema,
    max_retries: int = 3,
    reasoning: str = "high",
    *,
    repair_attempts: int = 1,
):
    """Generate once, healing schema misses before spending a retry.

    `max_retries` is the schema budget. Transport faults are handled
    inside `call_with_retry` and never consume it. `repair_attempts`
    bounds the speculative repair calls, so the worst case is
    `repair_attempts + max_retries` requests per item.
    """

    repairs_used = 0

    for attempt in range(1, max_retries + 1):
        try:
            print(f"[START] {name} (attempt {attempt}/{max_retries})")

            result = await call_with_retry(
                f"generate:{name}",
                lambda: model(
                    prompt,
                    output_schema,
                    extra_body={"reasoning": {"effort": reasoning}},
                ),
            )

            if result is None:
                raise ValueError("Model returned None")

            try:
                # Normal validation
                result = output_schema.model_validate_json(result)

            except Exception as validation_error:
                coerced = coerce_plain_text(result, output_schema)

                if coerced is not None:
                    print(f"[COERCE] {name}: wrapped plain text output")
                    return coerced

                print(f"[VALIDATION-ERROR] {name}: {validation_error}")

                if repairs_used < repair_attempts:
                    repairs_used += 1

                    print("[REPAIR] Trying to repair the invalid Output")

                    # Try healing before consuming another
                    # normal generation retry.
                    try:
                        repaired = await repair_output(
                            bad_output=result,
                            output_schema=output_schema,
                            reasoning=reasoning,
                        )

                    except Exception as repair_error:
                        # Chain so the schema violation stays
                        # visible alongside the repair failure.
                        raise validation_error from repair_error

                    if repaired is not None:
                        return repaired

                # Repair budget spent or repair came back
                # unusable, so regenerate instead.
                raise validation_error
            print(f"[DONE] {name}")

            return result

        except Exception as e:
            print(
                f"[ERROR] {name} attempt {attempt}/{max_retries}: "
                f"{type(e).__name__}: {e}"
            )

            if attempt == max_retries:
                print(f"[FAILED] {name} after {max_retries} attempts")
                return None

            await asyncio.sleep(2 * attempt)
