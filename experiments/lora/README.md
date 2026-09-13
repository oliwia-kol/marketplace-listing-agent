# LoRA experiment: grounded Polish listing copy

## Research question

Does a small LoRA adapter reduce omissions of declared defects and unsupported claims
when mapping approved facts to Polish listing copy, compared with the same base model
and a deterministic template?

The experiment is deliberately narrow. It does not train browser control, tools,
pricing, approval logic or authentication. Those operations remain deterministic.

## Design

- Base model: `Qwen/Qwen3-0.6B`, Apache-2.0.
- Method: supervised LoRA on the final eight transformer layers.
- Dataset: 300 rule-generated pairs: 240 train, 30 validation, 30 frozen test.
- Split: complete exact product variants, not individual condition scenarios, are assigned
  to a split. Related models can still appear in different splits; this is a stated limit.
- Privacy: no user photos, notes, credentials or copied marketplace descriptions.
- Seed: `20260913`.
- Baselines: deterministic template and the unchanged base model.

LoRA represents each learned weight update as a low-rank product instead of updating
the full matrix. If a weight matrix is `W`, training learns `ΔW = B·A`, where the rank
of `A` and `B` is much smaller than either dimension of `W`. This reduces the number
of trainable parameters and optimizer state. It does not create new factual evidence
and does not make a model safe by itself; the output still passes deterministic and
model-based validation in the application.

## Reproduction

```bash
python experiments/lora/generate_dataset.py
python -m mlx_lm lora --config experiments/lora/config.yaml
python experiments/lora/evaluate.py --output experiments/lora/results/base.json
python experiments/lora/evaluate.py \
  --adapter experiments/lora/adapters/qwen3-0.6b-copy \
  --output experiments/lora/results/lora.json
```

The adapter is eligible for product integration only if it improves defect preservation
and fact coverage on the frozen test without reducing the unsupported-phrase guard.
Synthetic results are evidence of the training pipeline, not evidence of marketplace
performance on real products.
