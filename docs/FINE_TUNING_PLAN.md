# Fine-Tuning Roadmap — MIT CSAIL Collaboration

## Phase 1: Baseline (Current)
- Pre-trained open-source SLMs with domain system prompts
- Differentiation through retrieved knowledge graph context
- **No fine-tuning required** — production-ready as-is

## Phase 2: Domain Fine-Tuning

### Approach: QLoRA (Quantized Low-Rank Adaptation)
- Adapter-based fine-tuning — modifies <1% of model parameters
- 4-bit quantization during training to fit on single GPU
- Estimated: 2-4 hours per domain on a single A100

### Instruction Dataset Generation
For each domain, generate ~1,000 instruction-response pairs from DCI papers:
1. Extract Q&A pairs from paper sections
2. Generate synthetic questions from paper abstracts
3. Create multi-hop reasoning examples from cross-paper connections
4. Include citation formatting examples

### Models to Fine-Tune
| Agent | Base Model | Training Data |
|-------|-----------|---------------|
| CBDC Agent | Qwen3-4B | Hamilton, OpenCBDC, PArSEC papers |
| Privacy Agent | Qwen3-4B | Weak Sentinel, Digital Pound Privacy, Zerocash |
| Stablecoin Agent | Qwen3-4B | Hidden Plumbing of Stablecoins |
| Bitcoin Agent | Qwen3-4B | Utreexo, Fee Estimation, CoinJoin papers |
| Token Agent | Qwen3-4B | Payment Token Design, Programmability |

### Expected Improvement
- 15-30% accuracy gain on domain-specific questions
- Better citation formatting (fewer hallucinated references)
- More precise use of domain terminology

## Phase 3: Reasoning Fine-Tuning
- Distill reasoning chains from DeepSeek-R1 into domain models
- Train structured reasoning with chain-of-thought
- Integrate with Lean 4 for formal proof verification (Math/Crypto agent)

## Phase 4: Continuous Learning (RLHF)
- Deploy feedback collection in Streamlit UI
- Use researcher corrections as training signal
- Periodic re-training with accumulated feedback
- Self-play: agents generate and evaluate their own training data
