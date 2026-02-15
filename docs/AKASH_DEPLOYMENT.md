# Akash Network Deployment Guide

## Overview
Deploy the DCI Research Agent System's SLM inference on Akash Network for
cost-effective decentralized GPU compute (~$0.75/hr for A100 vs ~$3+/hr on AWS).

## Prerequisites
- Akash account with AKT tokens (or $100 free credits via AkashML)
- Docker images for your deployment

## Option 1: AkashML Managed Inference (Simplest)
AkashML provides OpenAI-compatible endpoints with pre-hosted models.

1. Sign up at akashml.com
2. Select models: Qwen3-4B, Qwen3-8B, DeepSeek-R1-Distill-7B
3. Get API endpoint and key
4. Set in .env:
   ```
   OLLAMA_BASE_URL=https://your-akashml-endpoint
   INFERENCE_PRIORITY=ollama
   ```

## Option 2: Custom SDL Deployment

### Hardware Requirements
All agent models quantized to Q4 fit on a single A100 40GB:
- Gemma 1B (Q4): ~0.6 GB
- 5x Qwen3-4B (Q4): ~12.5 GB
- DeepSeek-R1-Distill-7B (Q4): ~4.5 GB
- Qwen3-8B (Q4): ~5 GB
- Phi-4-mini-reasoning (Q4): ~2.2 GB
- **Total: ~25 GB VRAM**

### GPU Pricing (Feb 2026)
| GPU | Price/hr | Fits All Models? |
|-----|----------|-----------------|
| A100 SXM4 40GB | ~$0.75 | Yes |
| A100 SXM4 80GB | ~$0.80 | Yes (with room) |
| H100 SXM5 | ~$1.18 | Yes |
| RTX 4090 24GB | ~$0.40 | Tight fit |

### Estimated Monthly Cost
- A100 40GB: ~$540/month (24/7)
- With auto-scaling (8hr/day): ~$180/month

## Option 3: Hybrid
- Lightweight models (Router, Critique) on CPU via Groq free tier
- Heavy models (Domain agents, Math agent) on Akash GPU
- Reduces GPU requirements and cost
