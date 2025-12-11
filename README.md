# AI Vehicle Damage Assessment System

An intelligent multi-agent system for automated vehicle damage detection and insurance claim processing using computer vision and large language models.

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://car-damage-ai.streamlit.app)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Live Demo

**Try it now:** [https://car-damage-ai.streamlit.app](https://car-damage-ai.streamlit.app)

Upload a photo of vehicle damage and get instant AI-powered assessment with cost estimation and claim recommendations.

## IT LOOKS LIKE : 

### Home Interface
![Home Screen](screenshots/home-screen.png)

### Upload & Analysis
![Upload Interface](screenshots/upload-interface.png)

### Results Dashboard
![Analysis Results](screenshots/analysis-results.png)

### Detailed Damage Report
![Damage Details](screenshots/damage-details.png)
## Features

- **5-Agent AI Pipeline**
  - Damage Classification Agent
  - Photo Validation Agent  
  - Severity Analysis Agent
  - Claim Decision Engine
  - Action Recommendation System

- ** Modern Dark UI** - Professional, responsive interface
- ** Detailed Analysis** - Component-level damage assessment
- ** Cost Estimation** - Automated repair cost calculation
- ** Fraud Detection** - Pattern recognition for suspicious claims
- ** Real-time Processing** - 30-40 second analysis time

## Architecture

User Upload → Image Validation → Damage Classification
↓
Multi-Agent Analysis Pipeline
↓
┌───────────────────┼───────────────────┐
↓ ↓ ↓
Severity Analysis Cost Estimation Fraud Detection
└───────────────────┼───────────────────┘
↓
Claim Decision + Actions


### **Tech Stack**

- **Frontend:** Streamlit (Python)
- **AI Framework:** LangGraph (Multi-agent orchestration)
- **LLM:** Google Gemini 1.5 (Flash & Pro models)
- **Vision:** Gemini Vision API
- **Deployment:** Streamlit Cloud
- **Version Control:** Git/GitHub

## Quick Start

### **Prerequisites**

- Python 3.12+
- Google Gemini API key ([Get one here](https://aistudio.google.com/))

### **Installation**

## Clone the repository

```bash
git clone https://github.com/nitikaborkar/insurance-claim-damage-ai.git
cd insurance-claim-damage-ai
```

## Create virtual environment
```bash
python -m venv venv
source venv/bin/activate # On Windows: venv\Scripts\activate
```

## Install dependencies
```bash
pip install -r requirements.txt
```

## Create .env file
```bash
echo "GOOGLE_API_KEY=your_api_key_here" > .env
```

### **Run Locally**
```bash 
streamlit run streamlit_app.py
```

## Project Structure

insurance-claim-damage-ai/
├── streamlit_app.py # Main Streamlit application
├── car_agent/
│ ├── service.py # Business logic layer
│ ├── graph.py # LangGraph workflow definition
│ ├── nodes.py # Agent node implementations
│ ├── state.py # State management
│ └── config.py # Configuration
├── data/
│ ├── vehicle_damage_types.json # Damage taxonomy
│ └── claim_actions.json # Action catalog
├── testing_images/ # Sample test images
├── requirements.txt # Python dependencies
└── README.md


## How It Works

1. **Image Upload:** User uploads vehicle damage photo
2. **Agent 1 - Classifier:** Categorizes damage type (front-end collision, side impact, etc.)
3. **Agent 2 - Validator:** Verifies photo quality and authenticity
4. **Agent 3 - Analyzer:** Performs detailed damage assessment with confidence scores
5. **Agent 4 - Decision Maker:** Determines claim status (Approve/Investigate/Reject)
6. **Agent 5 - Recommender:** Suggests next actions and repair protocols

## Supported Damage Categories

- Front-End Collision
- Rear-End Collision  
- Side Impact
- Windshield Damage
- Roof Damage
- Undercarriage Damage
- Hail/Weather Damage
- Vandalism
- Fire Damage
- Others (General analysis)

## Use Cases

- **Insurance Companies:** Automated first-pass claim assessment
- **Auto Repair Shops:** Instant damage evaluation
- **Fleet Management:** Bulk vehicle inspection
- **Car Dealerships:** Pre-sale condition reports
- **Individual Owners:** DIY damage assessment before filing claims

## Security & Privacy

- No data storage - All processing is ephemeral
- API keys stored securely in environment variables
- No personal information collected
- HTTPS encrypted communication

## Performance

- **Analysis Time:** 30-40 seconds per image
- **Accuracy:** ~85-90% damage classification
- **Cost:** ~$0.001-0.002 per analysis (Gemini API)
- **Uptime:** 99.9% (Streamlit Cloud)



