from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class Message:
    role: str
    content: str


class BackendProtocol:
    def generate(self, messages: list[Message], max_tokens: int = 1024, temperature: float = 0.0) -> str:
        raise NotImplementedError


class OpenAIBackend(BackendProtocol):
    def __init__(self, model: str):
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("Install the optional 'openai' extra to use the OpenAI backend.") from exc

        self.model = model
        self.client = OpenAI()

    def generate(self, messages: list[Message], max_tokens: int = 1024, temperature: float = 0.0) -> str:
        payload = [{"role": message.role, "content": message.content} for message in messages]
        response = self.client.chat.completions.create(
            model=self.model,
            messages=payload,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""


class TransformersBackend(BackendProtocol):
    def __init__(self, model: str):
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as exc:
            raise RuntimeError("Install the optional 'gpu' extra to use the transformers backend.") from exc

        self.model_name = model
        self.tokenizer = AutoTokenizer.from_pretrained(model)
        self.model = AutoModelForCausalLM.from_pretrained(model, device_map="auto")

    def generate(self, messages: list[Message], max_tokens: int = 1024, temperature: float = 0.0) -> str:
        chat_messages = [{"role": message.role, "content": message.content} for message in messages]
        if hasattr(self.tokenizer, "apply_chat_template"):
            prompt = self.tokenizer.apply_chat_template(
                chat_messages,
                add_generation_prompt=True,
                tokenize=False,
            )
        else:
            prompt = "\n\n".join(f"{message.role.upper()}:\n{message.content}" for message in messages)
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)

        generate_kwargs: dict[str, Any] = {
            "input_ids": inputs["input_ids"],
            "max_new_tokens": max_tokens,
            "pad_token_id": self.tokenizer.eos_token_id,
        }
        if "attention_mask" in inputs:
            generate_kwargs["attention_mask"] = inputs["attention_mask"]
        if temperature > 0:
            generate_kwargs.update(
                {
                    "do_sample": True,
                    "temperature": temperature,
                    "top_p": 0.95,
                }
            )
        else:
            generate_kwargs["do_sample"] = False

        output = self.model.generate(**generate_kwargs)
        new_tokens = output[0][inputs["input_ids"].shape[-1] :]
        return self.tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
