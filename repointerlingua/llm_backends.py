from __future__ import annotations

from dataclasses import dataclass


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
        prompt = "\n\n".join(f"{message.role.upper()}:\n{message.content}" for message in messages)
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        output = self.model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            do_sample=temperature > 0,
            temperature=max(temperature, 1e-5),
        )
        decoded = self.tokenizer.decode(output[0], skip_special_tokens=True)
        return decoded[len(prompt) :].strip() if decoded.startswith(prompt) else decoded.strip()
