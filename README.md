# AI Text Classifier: IT Helpdesk Triage

An LLM-powered classifier that reads a free-form IT helpdesk message and returns structured JSON with a request type, category, subcategory, affected device, priority, confidence and a short reason. Vague, off-topic and adversarial inputs are handled explicitly.

```text
Input:  "My laptop is not connecting to the office Wi-Fi."
```

```json
{
  "request_type": "it_related",
  "category": "network",
  "subcategory": "wifi_connection",
  "affected_device": "laptop",
  "priority": "medium",
  "confidence": 0.95,
  "needs_clarification": false,
  "reasoning": "A single user's laptop cannot connect to Wi-Fi, which blocks their work."
}
```

## How it works

1. **Taxonomy:** [`categories.json`](categories.json) defines every allowed label. A readable version is in [`CATEGORIES.md`](CATEGORIES.md).
2. **Prompt:** [`prompts/classifier_prompt.txt`](prompts/classifier_prompt.txt) is a template. At run time the taxonomy is inserted into it, so the prompt always matches the allowed labels.
3. **Structured output:** a Pydantic model whose fields are `Literal` types built from the taxonomy is sent to the model as a JSON schema. The model can only return valid labels.
4. **Post-processing** ([`classifier.py`](classifier.py)):
   - Empty input returns `unclear` without an API call.
   - The category is corrected to match the subcategory if the two disagree.
   - `non_it_related` and `unclear` results get fixed values (`other` / `low`).
   - Failed calls are retried with backoff.

## Project structure

```text
classifier.py                 Classifier and CLI
server.py                     Web server for the UI (POST /api/classify)
ui/index.html                 React UI
evaluate.py                   Runs all test cases, writes results and report
categories.json               Label definitions (single source of truth)
CATEGORIES.md                 Human-readable category definitions
prompts/classifier_prompt.txt Prompt template
tests/test_cases.json         27 test cases (16 standard, 11 edge cases)
evaluation_results.json       Expected vs actual, full JSON per case (generated)
EVALUATION.md                 Evaluation report (generated)
```

## Setup

Requires Python 3.10+ and a free NVIDIA API key from [build.nvidia.com](https://build.nvidia.com). The model is `nvidia/nemotron-3-super-120b-a12b`, called through NVIDIA's OpenAI-compatible API.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
echo "NVIDIA_API_KEY=nvapi-your-key-here" > .env
```

## Usage

Classify one message:

```bash
python classifier.py
# Please enter the message you want to classify: My VPN keeps dropping
```

From Python:

```python
from classifier import classify_message
classify_message("The printer is showing a paper jam error.")
```

Web UI (React):

```bash
python server.py
# Open http://localhost:8000
```

`server.py` is a small standard-library Python server. It serves the React page in `ui/index.html` and exposes `POST /api/classify`, so the API key stays on the server. React is loaded from a CDN, so there is no `npm install` or build step.

Run the evaluation:

```bash
python evaluate.py
```

This prints PASS/FAIL per case and writes [`evaluation_results.json`](evaluation_results.json) (expected vs actual for each field) and [`EVALUATION.md`](EVALUATION.md) (summary and accuracy per field).

## Test cases

[`tests/test_cases.json`](tests/test_cases.json) has 27 cases. Each one lists the expected values for the five label fields. A case passes only if all five match.

The 11 edge cases are marked `"type": "edge_case"`, with a `note` explaining why each is tricky:

| ID | What it tests |
|---|---|
| T17 | Hardware vs software ambiguity (slow + freezing) |
| T18 | Urgent tone but no actual problem stated |
| T19 | Completely vague ("It's not working") |
| T20 | Could be network, account or access |
| T21 | Usually-low-priority device, but whole office blocked |
| T22 | Problem with a workaround (lower priority) |
| T23 | Prompt injection trying to force priority |
| T24 | Non-English input (Spanish) |
| T25 | Gibberish |
| T26 | Shouting "URGENT" on a how-to question |
| T27 | Two issues in one message (pick the most severe) |

## Evaluation results

See [`EVALUATION.md`](EVALUATION.md) for the latest run, including per-field accuracy and a table of every mismatch.

## Design decisions

- **Closed label sets instead of free text.** An earlier version let the model invent subcategory names, so outputs like `power_issue` vs `startup_failure` were both reasonable but could not be evaluated. Every field is now an enum.
- **`unclear` as its own request type.** Vague messages are neither IT nor non-IT. Flagging them with `needs_clarification` lets a helpdesk ask a follow-up instead of misrouting.
- **Priority by impact, not tone.** Scope (one person vs whole office), workarounds and security risk drive priority. Words like "URGENT" do not.
- **Security is its own category.** Phishing, malware and lost devices are always `high` priority.
- **Temperature 0** for consistent answers.
- **Switched from Gemini to NVIDIA Nemotron.** The Gemini free-tier quota made calls take minutes or hang. Nemotron on NVIDIA's free tier answers in about 5 seconds with the same prompt.

## Limitations

- Some messages are genuinely ambiguous (e.g. T17, T20). The expected labels follow the rules in `CATEGORIES.md`, but a reasonable person could disagree.
- The NVIDIA free tier allows about 40 requests per minute. `evaluate.py` runs 3 cases in parallel to stay under it, and each call has a 90-second time limit.
- Only one label is returned per message. Multi-issue messages are classified by their most severe issue.

## Demo



https://github.com/user-attachments/assets/75476e5d-ac11-414c-8430-08cbfc5f7eb7

