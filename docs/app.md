# Comparison app and model setup on a 36 GB Mac

The app runs locally and compares the same selected incidents across whichever models you enable. It supports single incidents, batches, paired challenges, per-field answers and probabilities, latency, error counts, persistent run history, cancellation and JSON export. Missing model results stay empty.

Use an **Apple Silicon Mac**, Python 3.12 and optionally `uv`. The app itself has no third-party Python dependencies. Run these commands from a checkout of this repository. No models download until you explicitly start the corresponding model server. Setup scripts install software packages only.

## 1. Start the app

```bash
git clone https://github.com/mumit/triage-incident.git
cd triage-incident
python3 -m triage_bench.app
```

Open **http://127.0.0.1:8765**. It binds to loopback only. Select **Rules baseline** and run five validation incidents to confirm the app works without credentials or model downloads.

If using `uv`, `uv run --python 3.12 python -m triage_bench.app` is an alternative. The repository is private, so clone with your normal authenticated GitHub setup.

## 2. Add Jev

Open **Model settings → Jev**, paste your API key, and save. The key stays in server memory and is cleared on server restart. The browser does not store it in local storage; the server does not include it in saved runs or exports. A blank key field preserves the current key unless you select Clear or change the endpoint.

For persistent local configuration, copy `.env.example` to `.env` and edit it yourself. `.env` is ignored by Git; it contains plaintext secrets if you put keys there. Existing shell environment variables take precedence. Never put a real key in `.env.example`.

The default endpoint is `https://api.typesafe.ai/v1/systemone`. `jev-latest` is convenient for an initial test; use a pinned supported identifier for repeatable runs. Confirm that the declared context capacity matches your deployment. Checking Jev and pressing Run sends the selected synthetic incidents to that endpoint and can incur API charges.

## 3. Set up local Laya

In a separate terminal in the same checkout:

```bash
scripts/setup_laya.sh
scripts/start_laya.sh
```

Keep the server terminal running. The first start downloads the **multilingual** checkpoint, then prints its resolved revision, device, and endpoint. No paid API key is needed for these public weights. The wrapper selects Apple GPU/MPS when available and exposes:

- Endpoint: `http://127.0.0.1:8000/v1/systemone`
- App model identifier: `laya-multilingual`
- Context capacity: `8192`
- Health/deployment details: `http://127.0.0.1:8000/health`

The English base checkpoint is shorter-context, so the app setup deliberately uses the multilingual model. This is a specific variant, not an interchangeable benchmark of every Laya checkpoint. The wrapper refuses oversized requests instead of silently truncating them. To reproduce a revision, use `scripts/start_laya.sh --revision COMMIT_SHA`.

## 4. Set up local CLM on Apple Silicon

The upstream CLM package normally installs vLLM, whose standard deployment is Linux/GPU. The Mac setup replaces that embedding server with a small **MLX** endpoint while retaining the upstream CLM schema, projection heads and scoring engine. It does not substitute a generic embedding model or a chat-completion model.

```bash
scripts/setup_clm_mac.sh
scripts/start_clm_mac.sh
```

The setup script creates `.venv-clm-mac`, installs `mlx-lm==0.31.3`, inference dependencies, and `contrastive-lm==0.1.0` without its Linux-specific dependency chain. Missing vLLM and training-only pyarrow in `pip check` are expected for this intentionally inference-only environment. These packages are not needed by the selected Mac serving path.

At first start, the script downloads a community MLX conversion of the **Qwen3-8B encoder** and the original `Contrastive-LM/CLM-v0.1-8B` decision head. The default encoder is `czl/CLM-v0.1-8B-MLX` in bf16, approximately 16.5 GB of weights. A 36 GB Apple Silicon Mac is a reasonable target, but total memory also includes macOS, activations and other applications. Fit and speed have not been measured on your machine. Start with small samples and close memory-heavy applications.

Defaults in the app:

- Endpoint: `http://127.0.0.1:8700/v1/systemone`
- Model identifier: `clm-mlx-bf16`
- Declared context capacity: `8192`

The embedding service runs on port 8092, returns 4096-dimensional last-token, L2-normalized vectors, and processes one unpadded text at a time. It does not apply a chat template or run text generation. The small CLM projection heads run on CPU. The original upstream head, not the MLX conversion's alternative head implementation, performs scoring.

If memory pressure is high, stop CLM with Ctrl-C and use:

```bash
CLM_PRECISION=8bit scripts/start_clm_mac.sh
```

Then set the app's CLM model identifier to **`clm-mlx-8bit`** and update Deployment details to record 8-bit. That encoder is approximately 9.3 GB. It is a separate quantized variant; do not label its results as bf16 or assume identical decisions. The conversion maintainer reports substantial degradation for its 4-bit variant, so this setup does not offer 4-bit.

First-start progress is in `runs/clm-mac/encoder.log`. The encoder revision and head SHA-256 are recorded in `runs/clm-mac/deployment.json`; copy these details into the app's Deployment field or retain the file with exported results. Runtime software versions can be captured with `.venv-clm-mac/bin/python -m pip freeze` if pip is available, or `uv pip freeze --python .venv-clm-mac/bin/python`.

**Validation status:** the Mac serving code was checked against upstream pooling and wire-format contracts, and its request handling is tested without weights. End-to-end CLM inference and numerical agreement with the original vLLM deployment have not been tested here. Treat it as a Mac implementation to validate, not an established equivalent benchmark. The app and test suite never download or start models automatically.

For a Linux NVIDIA alternative, use `scripts/setup_clm.sh` and `scripts/start_clm.sh`. That server uses model identifier `clm-latest`; change the app setting accordingly. Connect through an SSH tunnel rather than exposing either model server publicly.

## 5. Run the comparison

1. Start the app and whichever model servers you want to compare.
2. Configure Jev and check the model identifiers and Deployment details.
3. Choose **Validation**, five incidents, and the models to run.
4. Click **Run comparison**. First requests may be slower because caches are cold.
5. Inspect errors, then compare individual answers with the benchmark references.
6. Run larger validation batches before a fixed held-out test. Paired challenge batches retain complete pairs.
7. Export JSON. Complete raw run records and metrics are also in `runs/app/<run-id>/`.

The app is serial across models to avoid concurrent contention on the Mac. Report that configuration, model precision, hardware and first/warm-call effects alongside latency. Hosted Jev timing includes the network; local model timing does not have the same network path. A five-incident sample is a connection check, not a model ranking.

Cancellation stops before the next request; an in-flight request may take up to the app's 300-second timeout to finish. Client cancellation does not necessarily stop computation already accepted by a model server. Keep server terminals open during a comparison. Run history persists, while interactive settings and keys do not.

## Troubleshooting

- **Connection refused:** the corresponding server is not ready, has stopped, or the port is wrong. Check its terminal/log.
- **HTTP 401:** check the provider API key. Local scripts do not require keys unless you independently configure one.
- **HTTP 422 / context preflight failed:** check the exact checkpoint, context settings and server log. Do not bypass a real short context by raising only the app declaration.
- **MLX out of memory:** stop the bf16 server, close other GPU-heavy processes, or use the separately labeled 8-bit variant.
- **Slow first start:** weights must download and load. Later starts reuse the repository-local `.cache/` directory.
- **Other program uses a port:** stop it or change the app/server port and endpoint consistently.
- **Mac reports vLLM installation errors:** use `setup_clm_mac.sh`, not the Linux setup or an unrestricted `pip install contrastive-lm`.

## Sources

- [Laya upstream installation and long-context guidance](https://github.com/NandhaKishorM/laya)
- [CLM upstream implementation](https://github.com/Contrastive-LM/CLM)
- [CLM reference head](https://huggingface.co/Contrastive-LM/CLM-v0.1-8B)
- [Community MLX bf16 encoder and conversion caveats](https://huggingface.co/czl/CLM-v0.1-8B-MLX)
- [Community MLX 8-bit encoder](https://huggingface.co/czl/CLM-v0.1-8B-MLX-8bit)
- [Jev API quickstart](https://docs.typesafe.ai/introduction/quickstart)
