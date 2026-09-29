# Comparison app and model setup on a 36 GB Mac

The app runs locally and compares the same selected incidents across whichever models you enable. It supports single incidents, batches, paired challenges, per-field answers and probabilities, latency, error counts, persistent run history, cancellation and JSON export. Missing model results stay empty.

Use an **Apple Silicon Mac**, Python 3.10 or newer available as `python3`, and optionally `uv`. The app itself has no third-party Python dependencies. Run these commands from a checkout of this repository. No models download until you explicitly start the corresponding model server. Setup scripts install software packages only.

## 1. Start the app

```bash
git clone https://github.com/mumit/triage-incident.git
cd triage-incident
python3 -m triage_bench.app
```

Open **http://127.0.0.1:8765**. It binds to loopback only. Select **Rules baseline** and run five validation incidents to confirm the app works without credentials or model downloads.

The model setup scripts use the interpreter selected by `python3`, including when `uv` is installed. The repository is private, so clone with your normal authenticated GitHub setup.

## 2. Add Jev

Open **Model settings → Jev**, paste your API key, and save. The key stays in server memory and is cleared on server restart. The browser does not store it in local storage; the server does not include it in saved runs or exports. A blank key field preserves the current key unless you select Clear or change the endpoint.

For persistent local configuration, copy `.env.example` to `.env` and edit it yourself. `.env` is ignored by Git; it contains plaintext secrets if you put keys there. Existing shell environment variables take precedence. Never put a real key in `.env.example`.

The default endpoint is `https://api.typesafe.ai/v1/systemone`. `jev-latest` is convenient for an initial test; use a pinned supported identifier for repeatable runs. Confirm that the declared context capacity matches your deployment. Checking Jev and pressing Run sends the selected synthetic incidents to that endpoint and can incur API charges.

## 3. Set up local Kev

Kev serves the same typed `/v1/systemone` request shape as Jev. The default here is the upstream author's recommended **Kev-4B** checkpoint. It is already trained on public and generated decision tasks; “zero-shot” means **no Northstar training or prompt tuning**, not an untrained base model. On the 36 GB Apple Silicon Mac, use:

```bash
scripts/setup_kev_mac.sh
scripts/start_kev_mac.sh
```

The setup script installs a pinned upstream Kev source revision into `.venv-kev-mac` using `uv`; it does not download model weights. Kev requires Python >=3.12,<3.14. The script selects an available compatible Python 3 interpreter because the active `python3` may be newer; set `KEV_PYTHON` to a compatible interpreter path to choose another. The first start downloads the pinned Kev-4B adapter and its Qwen base. It binds only to `127.0.0.1:8009`. Leave its terminal running.

- Endpoint: `http://127.0.0.1:8009/v1/systemone`
- App model identifier: `kev-latest`
- Checkpoint: `jaredpalmer/kev-4b@139fdd94f1b6a6ad80cc15e08fcb99cac885a101`
- Deployment details: `http://127.0.0.1:8009/v1/models` (reports the checkpoint, backend, precision and temperature)

The default checkpoint needs roughly 9 GB for its bf16 weights, plus runtime memory. The app runs providers sequentially, but local servers may hold weights concurrently; stop a server you are not using if the Mac is short on memory. `KEV_RUN` can select a different checkpoint, but label that result with its exact Hub revision and update the app's deployment details. The released checkpoint was measured on the **same 20 incident IDs and question protocol** as the initial Jev/Laya/CLM pilot, then across the [full evaluation sets](full-zero-shot-evaluation.md). A Northstar-trained Kev checkpoint would be a separate experiment. The local API accepts no key by default; if you set `KEV_API_KEY` on the Kev server, set the same key in the app's Kev settings.

## 4. Set up local Laya

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

## 5. Set up local CLM on Apple Silicon

The upstream CLM package normally installs vLLM, whose standard deployment is Linux/GPU. The Mac setup replaces that embedding server with a small **MLX** endpoint while retaining the upstream CLM schema, projection heads and scoring engine. It does not substitute a generic embedding model or a chat-completion model.

```bash
scripts/setup_clm_mac.sh
scripts/start_clm_mac.sh
```

The setup script creates `.venv-clm-mac`, installs `mlx-lm==0.31.3`, inference dependencies, and `contrastive-lm==0.1.0` without its Linux-specific dependency chain. Missing vLLM and training-only pyarrow in `pip check` are expected for this intentionally inference-only environment. These packages are not needed by the selected Mac serving path.

At first start, the script downloads a community MLX conversion of the **Qwen3-8B encoder** and the original `Contrastive-LM/CLM-v0.1-8B` decision head. The default encoder is `czl/CLM-v0.1-8B-MLX` in bf16, approximately 16.5 GB of weights. A 36 GB Apple Silicon Mac is a reasonable target, but total memory also includes macOS, activations and other applications. Fit and speed have not been measured on your machine. Start with small samples and close memory-heavy applications.

The start script refuses an occupied encoder port and waits for its own encoder instance and requested model identity before launching the CLM head. Stop an older encoder on port 8092 before changing precision or restarting.

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

**Validation status:** the Mac serving code has run end to end with actual weights and produced distinct answers on live validation incidents. Two reference canaries closely matched the conversion maintainer's published bf16 MLX values; numerical agreement with the original vLLM deployment has not been established. See the [zero-shot study](zero-shot-study.md) for measured outcomes and limitations. The app and test suite never download or start models automatically.

For a Linux NVIDIA alternative, use `scripts/setup_clm.sh` and `scripts/start_clm.sh`. That server uses model identifier `clm-latest`; change the app setting accordingly. Connect through an SSH tunnel rather than exposing either model server publicly.

## 6. Add a Fuel iX LLM

Open **Model settings → LLM · Fuel iX**. Enter your Fuel iX bearer token, the model identifier exposed by your proxy (for example `gpt-6-luna`), and its **OpenAI-compatible base URL**. A base URL ending in `/v1` is typical; the app appends `/chat/completions`. You may also paste the complete `/chat/completions` URL. The gateway must accept OpenAI-style chat-completion requests and Bearer authorization. Its exact URL, model identifier, availability, and billing come from your Fuel iX account; the app cannot infer them.

The default reasoning effort is `none` for a low-cost Luna baseline. If the gateway rejects the `reasoning_effort` parameter, choose **Gateway default** in settings, which omits it. Set Declared context capacity to the deployment's actual limit; the default 32,768 is a conservative request preflight setting, not a claim about the model's maximum context. The bearer token stays in server memory and is cleared on restart. A blank token field retains the current token unless you select Clear or change the base URL. You can alternatively set `FUELIX_BEARER_TOKEN`, `LLM_BASE_URL`, and `LLM_MODEL` in a local `.env` file.

The LLM receives the same public incident packet, fictional policy, and allowed decision keys as the typed providers through a separate, zero-shot chat prompt. It gets no examples, answer labels, or tools. It returns four categorical choices; the app does **not** invent probabilities or apply the rules baseline to its answers. The run metadata records the chat protocol, prompt hash, model, reasoning effort, and provider-reported token usage. The prompt protocol differs from the `/v1/systemone` typed API, so compare outcomes as different interfaces to the same decision task.

To run Luna without rerunning other models, check **LLM · Fuel iX** in Models to run and uncheck **Rules baseline** and any other checked models. Earlier scores remain in Run history. A five-incident validation run checks connectivity and output shape; it is not an accuracy estimate.

## 7. Run the comparison

1. Start the app and whichever model servers you want to compare.
2. Configure Jev or the Fuel iX LLM if selected, and check every model identifier and Deployment details.
3. Choose **Validation**, five incidents, and the models to run.
4. Click **Run comparison**. First requests may be slower because caches are cold.
5. Inspect errors, then compare individual answers with the benchmark references.
6. Run larger validation batches before a fixed held-out test. Paired challenge batches retain complete pairs.
7. Export JSON. Complete raw run records and metrics are also in `runs/app/<run-id>/`.

The app is serial across models to avoid concurrent contention on the Mac. Report that configuration, model precision, hardware and first/warm-call effects alongside latency. Hosted Jev timing includes the network; local model timing does not have the same network path. A five-incident sample is a connection check, not a model ranking.

“All 4 correct” requires all four decisions for the same incident to match accepted answers. Inspect the four field accuracies and failed/missing counts before interpreting a zero joint score. A failed request counts as incorrect for every field. Runs made with different question-format hashes use different prompt protocols and should not be pooled.

Cancellation stops before the next request; an in-flight request may take up to the app's 300-second timeout to finish. Client cancellation does not necessarily stop computation already accepted by a model server. Keep server terminals open during a comparison. Run history persists, while interactive settings and keys do not.

## Troubleshooting

- **Connection refused:** the corresponding server is not ready, has stopped, or the port is wrong. Check its terminal/log.
- **HTTP 401:** check the provider API key. Local scripts do not require keys unless you independently configure one.
- **Fuel iX HTTP 429:** the gateway has rate limited a request. The updated LLM adapter waits and retries up to four times; its per-case latency includes the wait. For a partially completed older run, use `scripts/resume_llm_app_run.py` while the app still holds the token, then score the composite output. Keep the source manifest with the result.
- **Fuel iX HTTP 403 / Cloudflare code 1010:** restart the app server after updating this checkout. The LLM adapter sends an application user agent because Fuel iX's edge rejects Python's default `urllib` user agent. If 403 persists with the updated server, check gateway access policy and confirm the token field contains only the token, without a `Bearer ` prefix.
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
- [Kev source and local serving guide](https://github.com/jaredpalmer/kev)
- [Kev-4B model card](https://huggingface.co/jaredpalmer/kev-4b)
