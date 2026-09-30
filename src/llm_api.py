import asyncio
import json
from typing import cast

import outlines
from config import LLM_API_BASE_URL, LLM_API_KEY, LLM_API_MODEL_ID
from openai import OpenAI as LLM
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionUserMessageParam,
)
from openai.types.chat.completion_create_params import ResponseFormatJSONObject

client = LLM(
    api_key=LLM_API_KEY,
    base_url=LLM_API_BASE_URL,
)

model = outlines.from_openai(client, LLM_API_MODEL_ID)


async def repair_output(
    bad_output,
    output_schema,
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

    response = cast(
        ChatCompletion,
        await asyncio.to_thread(
            client.chat.completions.create,
            model=LLM_API_MODEL_ID,
            messages=messages,
            response_format=response_format,
            extra_body={"reasoning": {"effort": "high"}},
        ),
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
            line
            for line in text.splitlines()
            if not line.strip().startswith("```")
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
):
    for attempt in range(1, max_retries + 1):
        try:
            print(f"[START] {name} (attempt {attempt}/{max_retries})")

            result = await asyncio.to_thread(
                model,
                prompt,
                output_schema,
                extra_body={"reasoning": {"effort": reasoning}},
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
                print("[REPAIR] Trying to repair the invalid Output")
                # Try healing before consuming another
                # normal generation retry.
                repaired = await repair_output(
                    bad_output=result,
                    output_schema=output_schema,
                )

                if repaired is not None:
                    return repaired

                # Repair failed, so continue to the
                # normal retry loop.
                raise validation_error
            print(f"[DONE] {name}")

            return result

        except Exception as e:
            print(f"[ERROR] {name} attempt {attempt}/{max_retries}: {e}")

            if attempt == max_retries:
                print(f"[FAILED] {name} after {max_retries} attempts")
                return None

            await asyncio.sleep(2 * attempt)
