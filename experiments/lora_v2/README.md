# LoRA v2: category-general Polish listing copy

This experiment asks whether a 0.6B model can learn to turn sparse, approved facts
into short Polish listing prose while generalizing to product families absent from
training.

The dataset is project-authored and synthetic. It contains 400 train, 100 validation
and 100 frozen-test examples. Product families are the split unit: dryers and drills
appear only in the frozen test. No marketplace text, user photos or private notes are
included.

```bash
python experiments/lora_v2/generate_dataset.py
mlx_lm.lora --config experiments/lora_v2/config_rank8.yaml
mlx_lm.lora --config experiments/lora_v2/config_rank16.yaml
python experiments/lora_v2/evaluate.py --output experiments/lora_v2/results/base.json
python experiments/lora_v2/evaluate.py \
  --adapter experiments/lora_v2/adapters/rank8 \
  --output experiments/lora_v2/results/rank8.json
python experiments/lora_v2/evaluate.py \
  --adapter experiments/lora_v2/adapters/rank16 \
  --output experiments/lora_v2/results/rank16.json
```

Adapters are local ignored artifacts. See `RESULTS.md` for the decision and limits.
