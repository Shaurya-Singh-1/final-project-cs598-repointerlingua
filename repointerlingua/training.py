from __future__ import annotations

import json
from pathlib import Path

from repointerlingua.utils import ensure_dir, write_jsonl


def export_sft_data(runs_dir: Path, output_dir: Path) -> dict[str, int]:
    output_dir = ensure_dir(output_dir)
    state_rows = []
    patch_rows = []

    for episode_path in sorted(runs_dir.rglob("episode.json")):
        episode = json.loads(episode_path.read_text(encoding="utf-8"))
        if not episode.get("solved"):
            continue

        observations = episode.get("observations", [])
        state_history = episode.get("state_history", [])
        patches = episode.get("patches", [])

        for index, state_snapshot in enumerate(state_history):
            prompt = {
                "step": state_snapshot["step"],
                "observation": observations[min(index, len(observations) - 1)] if observations else {},
            }
            state_rows.append(
                {
                    "task_id": episode["task_id"],
                    "kind": "state_update",
                    "prompt": json.dumps(prompt, indent=2),
                    "completion": json.dumps(state_snapshot["state"], indent=2),
                }
            )

        if state_history and patches:
            patch_rows.append(
                {
                    "task_id": episode["task_id"],
                    "kind": "patch_generation",
                    "prompt": json.dumps(state_history[-1]["state"], indent=2),
                    "completion": json.dumps({"patches": patches}, indent=2),
                }
            )

    write_jsonl(output_dir / "state_updates.jsonl", state_rows)
    write_jsonl(output_dir / "patch_generation.jsonl", patch_rows)
    return {"state_updates": len(state_rows), "patch_generation": len(patch_rows)}


def train_lora(train_file: Path, model_name: str, output_dir: Path, epochs: int = 1) -> None:
    try:
        from datasets import Dataset
        from peft import LoraConfig, get_peft_model
        from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments
    except ImportError as exc:
        raise RuntimeError("Install the optional 'gpu' extra to use LoRA training.") from exc

    rows = [json.loads(line) for line in train_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    dataset = Dataset.from_list(rows)
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(model_name, device_map="auto")
    lora_config = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora_config)

    def preprocess(example):
        prompt = f"PROMPT:\n{example['prompt']}\n\nCOMPLETION:\n{example['completion']}"
        tokenized = tokenizer(prompt, truncation=True, max_length=2048)
        tokenized["labels"] = tokenized["input_ids"].copy()
        return tokenized

    tokenized_dataset = dataset.map(preprocess, remove_columns=dataset.column_names)
    args = TrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=epochs,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=8,
        learning_rate=2e-4,
        logging_steps=5,
        save_strategy="epoch",
        report_to=[],
    )
    trainer = Trainer(model=model, args=args, train_dataset=tokenized_dataset)
    trainer.train()
    trainer.save_model(str(output_dir))
