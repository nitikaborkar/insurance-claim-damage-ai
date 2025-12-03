# Ergonomic Risk Assessment Agent

## 1. Project Structure

Example layout:

```text
Ergo_Agent/
├── app.py                          # Flask API entrypoint
├── .env                            # API keys (not committed)
├── activities.json                 # Ergonomic checks per activity
├── ergo_agent/
│   ├── __init__.py
│   ├── state.py                    # AgentState, helpers, data loading
│   ├── nodes.py                    # classifier, filterer, analyzer, recommender
│   ├── graph.py                    # create_ergonomic_agent_graph()
│   └── service.py                  # analyze_image_path() for API / scripts
└── Common activities images/       # Local test images (optional)
```

***

## 2. Installation

```bash
git clone <this-repo>
cd Ergo_Agent
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```
***

## 3. Environment Variables (`.env`)

Create a `.env` file in the **project root** (`Ergo_Agent/`):

```env
ANTHROPIC_API_KEY=sk-xxxxx
LANGCHAIN_API_KEY=lsv2_xxxxx       # if using LangSmith
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=ergonomic-risk-assessment
```

In `config.py` or at the top of `app.py` / `service.py`, load it:

```python
from dotenv import load_dotenv
load_dotenv()
```

Then read keys via `os.getenv("ANTHROPIC_API_KEY")` etc., instead of hard‑coding.

***

## 4. Running the Flask API (`app.py`)

`app.py` exposes a `/analyze` endpoint that accepts a single image and returns ergonomic assessment JSON.

Run the server from the project root:

```bash
cd Ergo_Agent
python app.py
```

You should see:

```text
* Running on http://127.0.0.1:8000
```


***

## 5. Calling the API

### Single image via `curl`

```bash
curl -X POST http://127.0.0.1:8000/analyze \
  -F "image=@/absolute/path/to/image.jpg" \
  -H "Accept: application/json"
```

You should get a JSON response like:

```json
{
  "image_path": "/tmp/tmpxyz.jpg",
  "activity_category": "DESK_WORK",
  "skipped": false,
  "skip_reason": null,
  "risk_analysis": [
    {
      "cue": "Neck flexion > 20°",
      "present": true,
      "observation": "Head tilted forward towards the laptop screen..."
    }
  ],
  "recommendations": [
    {
      "summary": "Found 2 ergonomic concerns...",
      "quick_fixes": [...],
      "long_term_practices": [...],
      "detailed_risks": [...]
    }
  ]
}
```
Note : For invalid images skipped will be true and skip_reason will show why it was invalid

### Batch testing in a notebook (without HTTP)

```python
from ergo_agent.service import analyze_image_path
import os

img_dir = "Common activities images"
results = []

for img in os.listdir(img_dir):
    path = os.path.join(img_dir, img)
    if not os.path.isfile(path):
        continue
    print("Analyzing:", path)
    res = analyze_image_path(path)
    results.append(res)
```

To persist to JSON compatible with the report generator:

```python
import json

with open("ergonomic_assessment_results_with_filtering.json", "w") as f:
    json.dump(results, f, indent=2)
```


***

## 6. Generating the Word Report

Use the script you wrote (e.g., `ergonomic_report_generator.py`):

```bash
cd Ergo_Agent
python ergonomic_report_generator.py
```

By default it:

- Reads `ergonomic_assessment_results_with_filtering.json`
- Validates image paths
- Creates `ergonomic_assessment_results_with_filtering.docx`

You can also call the function from a notebook:

```python
from ergonomic_report_generator import create_ergonomic_report

create_ergonomic_report(
    json_path="ergonomic_assessment_results_with_filtering.json",
    output_path="ergonomic_assessment_results_with_filtering.docx",
    skip_missing_images=True
)
```

Make sure you run from the directory where the image paths in the JSON are valid (or store absolute paths when saving results).

***

## 7. Key Internals (for reference)

- **Graph**: built in `ergo_agent/graph.py` via `create_ergonomic_agent_graph()`
    - `classifier` → `filterer` → (`analyzer` → `recommender`) or `END`
- **Nodes** (in `nodes.py`):
    - `activity_classifier_node` – uses Claude vision to pick an activity category.
    - `filterer_node` – rejects transient / non-ergonomic / non-human images.
    - `risk_analyzer_node` – performs check-wise analysis with dynamic posture assumptions.
    - `recommender_node` – aggregates flagged risks into quick fixes \& long-term practices.
- **Service** (in `service.py`):
    - `analyze_image_path(path: str) -> dict` – single entrypoint used both by `app.py` and notebooks.

This README should give you (or anyone else) a clean path to:

1) Configure keys,
2) Run `app.py` and hit `/analyze`, and
3) Generate a full ergonomic report `.docx` from accumulated assessments.
