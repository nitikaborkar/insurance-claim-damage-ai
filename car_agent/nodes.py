# nodes.py - Updated for Google Gemini
import os
from dotenv import load_dotenv
load_dotenv()

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from car_agent.state import AgentState, VEHICLE_DAMAGE_DATA, DAMAGE_CATEGORIES, CLAIM_ACTIONS_CATALOG
import json


def make_model(model_name: str = "models/gemini-2.5-flash-lite", timeout: int = 60):
    """Create Google Gemini model with retries and timeout."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY not found in environment.")
    
    return ChatGoogleGenerativeAI(
        model=model_name,
        temperature=0,
        max_retries=3,
        timeout=timeout,
        google_api_key=api_key
    )

def damage_classifier_node(state: AgentState) -> AgentState:
    """Agent 1: Classify the type of vehicle damage from image"""
    print("\n🔍 AGENT 1: Damage Type Classifier")
    print("=" * 60)
    
    categories_list = "\n".join([f"- {cat}" for cat in DAMAGE_CATEGORIES])
    
    system_prompt = f"""
You are a vehicle damage classification expert for car insurance claims.

You MUST:
1) Pick ONE damage category from this list:
{categories_list}

2) Provide a SHORT description of the damage (3-5 words).
Examples: "Front bumper collision damage", "Side door dent", "Windshield chip damage"

3) Briefly describe the incident context in 1 sentence:
Examples: "front-end collision with another vehicle", "parking lot side scrape", "road debris hit windshield"

Respond ONLY in this JSON format:
{{
"damage_category": "exact category name or OTHERS",
"damage_description": "short damage description",
"incident_context": "brief incident context"
}}
"""
    
    messages = [
        HumanMessage(content=[
            {
                "type": "text",
                "text": system_prompt + "\n\nClassify the vehicle damage type in this image and describe the incident context."
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{state['image_base64']}"
                }
            }
        ])
    ]
    
    llm = make_model("models/gemini-2.5-flash-lite", timeout=45)

    try:
        response = llm.invoke(messages)
    except Exception as e:
        print(f"⚠️ Damage classifier: primary model failed: {e}")
        try:
            llm_fallback = make_model("models/gemini-2.0-flash-lite", timeout=30)

            response = llm_fallback.invoke(messages)
        except Exception as e2:
            print(f"🛑 Damage classifier: fallback model also failed: {e2}")
            state["damage_category"] = "OTHERS"
            state["damage_description"] = "unspecified damage"
            state["incident_context"] = "unknown incident"
            state["messages"].append("Damage classifier failed; defaulting to OTHERS")
            return state
    
    response_text = response.content.strip()
    
    if "```json" in response_text:
        response_text = response_text.split("```json")[1].split("```")[0]
    elif "```" in response_text:
        response_text = response_text.split("```")[0]
    
    try:
        parsed = json.loads(response_text)
    except json.JSONDecodeError:
        print("⚠️ Failed to parse classifier JSON, defaulting to OTHERS.")
        parsed = {
            "damage_category": "OTHERS",
            "damage_description": "unspecified damage",
            "incident_context": "unknown incident"
        }
    
    damage_category = parsed.get("damage_category", "OTHERS").strip()
    damage_description = parsed.get("damage_description", "").strip() or "unspecified damage"
    incident_context = parsed.get("incident_context", "unknown incident").strip()
    
    # Validate damage_category
    if damage_category == "OTHERS":
        print(f"✅ Damage classified as: OTHERS (will use general analysis)")
    elif damage_category not in DAMAGE_CATEGORIES:
        print(f"⚠️ VLM returned: '{damage_category}'")
        print("   Attempting to match to known categories...")
        matched = False
        for cat in DAMAGE_CATEGORIES:
            if damage_category.lower() in cat.lower() or cat.lower() in damage_category.lower():
                damage_category = cat
                matched = True
                print(f"   ✓ Matched to: {damage_category}")
                break
        if not matched:
            damage_category = "OTHERS"
            print(f"   No match found. Using general analysis: OTHERS")
    else:
        print(f"✅ Damage classified as: {damage_category}")
    
    state["damage_category"] = damage_category
    state["damage_description"] = damage_description
    state["incident_context"] = incident_context
    state["messages"].append(f"Classified damage: {damage_category}; description: {damage_description}")
    
    return state


def filterer_node(state: AgentState) -> AgentState:
    """Agent 2: Validate if photo is suitable for damage assessment"""
    print("\n🔍 AGENT 2: Photo Quality Validator")
    print("=" * 60)
    
    system_prompt = f"""
You are an insurance claim photo validator for vehicle damage assessment.

Decide if this photo is suitable for damage assessment: `{state["damage_category"]}`

Classify into:
- "VALID" → damage is clearly visible and assessable
- "INVALID" → photo unsuitable for assessment

Rules:
1. Photo must show REAL vehicle damage (not stock photos, toy cars, or illustrations)
2. Damage must be clearly visible (not too blurry, dark, or obstructed)
3. Relevant damaged area must be in frame and identifiable
4. Reject if:
   - No damage visible
   - Photo too blurry, dark, or distant
   - Wrong subject (not a vehicle)
   - Damage area completely obscured
   - Screenshot or heavily edited image

Respond ONLY in this JSON format:
{{
  "validity": "VALID" or "INVALID",
  "reason": "one-sentence explanation",
  "notes_for_downstream": "hints for assessment or empty string"
}}
"""
    
    messages = [
        HumanMessage(content=[
            {
                "type": "text",
                "text": system_prompt + "\n\nDecide if this image is VALID or INVALID for vehicle damage assessment."
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{state['image_base64']}"
                }
            }
        ])
    ]
    
    llm = make_model("models/gemini-2.5-flash-lite", timeout=45)

    try:
        response = llm.invoke(messages)
    except Exception as e:
        print(f"⚠️ Filterer: primary model failed: {e}")
        try:
            llm_fallback = make_model("models/gemini-2.0-flash-lite", timeout=30)
            response = llm_fallback.invoke(messages)
        except Exception as e2:
            print(f"🛑 Filterer failed: {e2}")
            state["filter_result"] = {
                "validity": "INVALID",
                "reason": "Model error during validation",
                "notes_for_downstream": "",
            }
            state["should_skip_assessment"] = True
            state["messages"].append("Filterer failed; marking as INVALID")
            return state
    
    response_text = response.content.strip()
    
    if "```json" in response_text:
        response_text = response_text.split("```json")[1].split("```")[0]
    elif "```" in response_text:
        response_text = response_text.split("```")[0]
    
    try:
        result = json.loads(response_text)
    except json.JSONDecodeError:
        print("⚠️ Filterer: failed to parse JSON, marking as INVALID")
        result = {
            "validity": "INVALID",
            "reason": "Model returned malformed JSON",
            "notes_for_downstream": "",
        }
    
    validity = (result.get("validity") or "").upper()
    reason = result.get("reason", "")
    notes = result.get("notes_for_downstream", "")
    
    state["filter_result"] = {
        "validity": validity,
        "reason": reason,
        "notes_for_downstream": notes,
    }
    
    print(f"✅ Filter decision: {validity} — {reason}")
    
    if validity == "INVALID":
        state["should_skip_assessment"] = True
    else:
        state["should_skip_assessment"] = False
    
    return state


def damage_analyzer_node(state: AgentState) -> AgentState:
    """Agent 3: Analyze damage severity and estimate repair costs"""
    print("\n🔬 AGENT 3: Damage Severity Analyzer")
    print("=" * 60)
    
    damage_category = state["damage_category"]
    relevant_checks = VEHICLE_DAMAGE_DATA.get(damage_category, [])
    state["relevant_checks"] = relevant_checks
    
    if not relevant_checks or damage_category == "OTHERS":
        return general_damage_analysis(state)
    
    print(f"📋 Found {len(relevant_checks)} damage checks for {damage_category}")
    
    # Prepare detailed analysis prompt
    checks_description = "\n\n".join([
        f"CHECK #{i+1}:\n"
        f"  Looking for: {check['cue']}\n"
        f"  Damage area: {check['damage_area']}\n"
        f"  Risk: {check['risk']}\n"
        f"  Typical cost: {check['cost_estimate']}"
        for i, check in enumerate(relevant_checks)
    ])
    
    system_prompt = f"""
You are an expert vehicle damage assessor for insurance claims.

Analyze this {damage_category} image for specific damage indicators.

For EACH damage check below, assess:
1. "present": true/false - Is this specific damage visible?
2. "confidence": "HIGH" / "MEDIUM" / "LOW" - How certain are you?
3. "severity": "MINOR" / "MODERATE" / "SEVERE" - How bad is the damage?
4. "observation": Brief description of what you see (or don't see)
5. "estimated_cost": Your estimate based on visible damage (use provided range as guide)

Damage checks to evaluate:
{checks_description}

Respond ONLY in this JSON format:
{{
  "damage_analysis": [
    {{
      "check_number": 1,
      "cue": "exact damage indicator text",
      "present": true or false,
      "confidence": "HIGH" or "MEDIUM" or "LOW",
      "severity": "MINOR" or "MODERATE" or "SEVERE",
      "observation": "what you see in the image",
      "estimated_cost": "$X-Y" or "Not applicable"
    }},
    ...
  ]
}}
"""
    
    messages = [
        HumanMessage(content=[
            {
                "type": "text",
                "text": system_prompt + "\n\nAnalyze this vehicle damage image for the specific damage indicators listed above."
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{state['image_base64']}"
                }
            }
        ])
    ]
    
    llm = make_model("models/gemini-2.5-flash-lite", timeout=60)

    
    try:
        response = llm.invoke(messages)
    except Exception as e:
        print(f"⚠️ Damage analyzer: primary model failed: {e}")
        try:
            llm_fallback = make_model("models/gemini-2.0-flash-lite", timeout=30)
            response = llm_fallback.invoke(messages)
        except Exception as e2:
            print(f"🛑 Damage analyzer: fallback failed: {e2}")
            state["damage_analysis"] = []
            state["flagged_damages"] = []
            state["messages"].append("Damage analyzer failed")
            return state
    
    # Parse response
    try:
        response_text = response.content.strip()
        
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[0]
        
        analysis_result = json.loads(response_text)
        damage_analysis = analysis_result.get("damage_analysis", [])
    except json.JSONDecodeError as e:
        print(f"⚠️ Failed to parse JSON: {e}")
        damage_analysis = []
    
    # Combine analysis with original check data
    for i, analysis in enumerate(damage_analysis):
        if i < len(relevant_checks):
            analysis.update({
                "damage_area": relevant_checks[i]["damage_area"],
                "risk": relevant_checks[i]["risk"],
                "repair_action": relevant_checks[i]["repair_action"],
                "cost_estimate_reference": relevant_checks[i]["cost_estimate"]
            })
    
    state["damage_analysis"] = damage_analysis
    
    # Filter flagged damages (present = True)
    flagged_damages = [d for d in damage_analysis if d.get("present", False)]
    
    # Sort by severity: SEVERE → MODERATE → MINOR
    severity_order = {"SEVERE": 0, "MODERATE": 1, "MINOR": 2}
    flagged_damages.sort(
        key=lambda d: severity_order.get(d.get("severity", "MINOR"), 3)
    )
    
    state["flagged_damages"] = flagged_damages
    
    print(f"✅ Analysis complete: {len(flagged_damages)} damages flagged out of {len(damage_analysis)} checks")
    for damage in flagged_damages:
        print(f"   ⚠️ {damage.get('damage_area')} - {damage.get('severity')} severity")
    
    state["messages"].append(f"Analyzed {len(damage_analysis)} checks, flagged {len(flagged_damages)} damages")
    
    return state


def general_damage_analysis(state: AgentState) -> AgentState:
    """Fallback: General damage analysis when category is OTHERS"""
    print("🔍 Using general damage analysis (OTHERS category)")
    
    system_prompt = """You are a vehicle damage assessment expert.

Analyze this image for ANY visible vehicle damage. Identify:
1. Damaged components/areas
2. Severity of each damage
3. Estimated repair costs
4. Any safety concerns

Respond in JSON:
{
  "damage_analysis": [
    {
      "check_number": 1,
      "cue": "damage description",
      "damage_area": "component name",
      "present": true,
      "confidence": "HIGH/MEDIUM/LOW",
      "severity": "MINOR/MODERATE/SEVERE",
      "observation": "what you see",
      "estimated_cost": "$X-Y"
    }
  ]
}
"""
    
    messages = [
        HumanMessage(content=[
            {
                "type": "text",
                "text": system_prompt + "\n\nAnalyze this image for vehicle damage and provide assessment."
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{state['image_base64']}"
                }
            }
        ])
    ]
    
    llm = make_model("models/gemini-2.5-flash-lite", timeout=60)

    
    try:
        response = llm.invoke(messages)
        response_text = response.content.strip()
        
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[0]
        
        analysis_result = json.loads(response_text)
        damage_analysis = analysis_result.get("damage_analysis", [])
    except Exception as e:
        print(f"⚠️ General analysis failed: {e}")
        damage_analysis = []
    
    state["damage_analysis"] = damage_analysis
    flagged_damages = [d for d in damage_analysis if d.get("present", False)]
    state["flagged_damages"] = flagged_damages
    
    print(f"✅ General analysis: {len(flagged_damages)} damages identified")
    
    return state


def claim_decision_node(state: AgentState) -> AgentState:
    """Agent 4: Make claim decision and provide recommendations"""
    print("\n💡 AGENT 4: Claim Decision Maker")
    print("=" * 60)
    
    flagged_damages = state["flagged_damages"]
    damage_category = state.get("damage_category", "OTHERS")
    incident_context = state.get("incident_context", "unknown incident")
    
    if not flagged_damages:
        print("✅ No damage detected - potential reject or no claim needed")
        state["claim_recommendations"] = [{
            "observed_damages": [],
            "claim_decision": "REJECT",
            "recommended_actions": ["No visible damage detected. If damage exists, submit clearer photos."],
            "reasoning": "No damage visible in submitted photo"
        }]
        state["overall_severity_level"] = "NONE"
        state["estimated_total_cost"] = "$0"
        state["fraud_indicators"] = []
        state["messages"].append("No damage detected")
        return state
    
    print(f"📝 Making claim decision for {len(flagged_damages)} flagged damages")
    
    # Prepare damage summary for LLM
    damages_for_llm = []
    for d in flagged_damages:
        damages_for_llm.append({
            "damage_area": d.get("damage_area"),
            "damage_description": d.get("cue"),
            "severity": d.get("severity"),
            "confidence": d.get("confidence"),
            "observation": d.get("observation"),
            "estimated_cost": d.get("estimated_cost"),
            "risk": d.get("risk")
        })
    
    system_prompt = f"""
You are an insurance claims adjuster making decisions on vehicle damage claims.

Incident type: {damage_category}
Context: {incident_context}

Your task:
1. Review all flagged damages
2. Make a claim decision: APPROVE / APPROVE_WITH_INSPECTION / INVESTIGATE / PARTIAL_APPROVE / REJECT / TOTAL_LOSS
3. Provide clear, actionable recommendations
4. Identify any fraud indicators

Consider:
- Minor damages (<$2k total) → APPROVE immediately
- Moderate damages ($2k-$5k) → APPROVE_WITH_INSPECTION (workshop verification)
- Severe damages ($5k-$10k) → INVESTIGATE (adjuster inspection)
- Very severe (>$10k or structural) → Possible TOTAL_LOSS
- Inconsistencies or suspicious patterns → INVESTIGATE for fraud

Respond in JSON:
{{
  "observed_damages": [
    {{
      "area": "Front Bumper",
      "description": "Cracked bumper with separation",
      "severity": "MODERATE",
      "confidence": "HIGH"
    }}
  ],
  "claim_decision": "APPROVE" or "APPROVE_WITH_INSPECTION" or "INVESTIGATE" or "PARTIAL_APPROVE" or "REJECT" or "TOTAL_LOSS",
  "recommended_actions": [
    "Approve repair at authorized workshop",
    "Estimated repair cost: $1,500-$2,200",
    "Processing time: 3-5 business days"
  ],
  "affected_areas": ["Front Bumper", "Hood"],
  "overall_severity": "LOW" or "MEDIUM" or "HIGH",
  "estimated_total_cost": "$X-Y",
  "fraud_indicators": [],
  "reasoning": "Brief explanation of decision"
}}
"""
    
    llm = make_model("models/gemini-2.5-flash-lite", timeout=60)

    
    messages = [
        HumanMessage(content=[
            {
                "type": "text",
                "text": system_prompt + "\n\nFlagged damages data:\n" + json.dumps({"flagged_damages": damages_for_llm}, ensure_ascii=False)
            }
        ])
    ]
    
    try:
        response = llm.invoke(messages)
    except Exception as e:
        print(f"⚠️ Claim decision: primary model failed: {e}")
        # Fallback
        parsed = {
            "observed_damages": [{"area": d.get("damage_area"), "description": d.get("cue"), "severity": d.get("severity"), "confidence": d.get("confidence")} for d in flagged_damages],
            "claim_decision": "INVESTIGATE",
            "recommended_actions": ["Manual review required due to system error"],
            "affected_areas": list(set([d.get("damage_area") for d in flagged_damages])),
            "overall_severity": "UNDETERMINED",
            "estimated_total_cost": "TBD",
            "fraud_indicators": [],
            "reasoning": "System error during automated assessment"
        }
        state["claim_recommendations"] = [parsed]
        state["overall_severity_level"] = "UNDETERMINED"
        state["estimated_total_cost"] = "TBD"
        state["fraud_indicators"] = []
        return state
    
    response_text = response.content.strip()
    
    if "```json" in response_text:
        response_text = response_text.split("```json")[1].split("```")[0]
    elif "```" in response_text:
        response_text = response_text.split("```")[0]
    
    try:
        parsed = json.loads(response_text)
    except json.JSONDecodeError as e:
        print(f"⚠️ Failed to parse claim decision JSON: {e}")
        parsed = {
            "observed_damages": [{"area": d.get("damage_area"), "description": d.get("cue"), "severity": d.get("severity")} for d in flagged_damages],
            "claim_decision": "INVESTIGATE",
            "recommended_actions": ["Manual review required"],
            "affected_areas": [],
            "overall_severity": "UNDETERMINED",
            "estimated_total_cost": "TBD",
            "fraud_indicators": []
        }
    
    state["claim_recommendations"] = [parsed]
    state["affected_areas"] = parsed.get("affected_areas", [])
    state["overall_severity_level"] = parsed.get("overall_severity", "UNDETERMINED")
    state["estimated_total_cost"] = parsed.get("estimated_total_cost", "TBD")
    state["fraud_indicators"] = parsed.get("fraud_indicators", [])
    
    print(f"✅ Claim decision: {parsed.get('claim_decision')}")
    print(f"   Severity: {state['overall_severity_level']}, Estimated cost: {state['estimated_total_cost']}")
    
    state["messages"].append(f"Claim decision: {parsed.get('claim_decision')}")
    
    return state


def action_recommender_node(state: AgentState) -> AgentState:
    """Agent 5: Recommend specific actions from catalog"""
    print("\n🎯 AGENT 5: Action Recommender")
    print("=" * 60)
    
    claim_recommendations = state.get("claim_recommendations", [])
    if not claim_recommendations:
        print("✅ No actions needed")
        state["action_recommendations"] = []
        state["action_selection_reasoning"] = "No damage detected, no actions required"
        return state
    
    # Fix: claim_recommendations is a list, get first element
    claim_rec = claim_recommendations[0] if claim_recommendations else {}
    
    if not claim_rec.get("observed_damages"):
        print("✅ No actions needed")
        state["action_recommendations"] = []
        state["action_selection_reasoning"] = "No damage detected, no actions required"
        return state
    
    claim_decision = claim_rec.get("claim_decision", "INVESTIGATE")
    overall_severity = state.get("overall_severity_level", "MEDIUM")
    estimated_cost = state.get("estimated_total_cost", "TBD")
    fraud_indicators = state.get("fraud_indicators", [])
    
    system_prompt = f"""
You are a claims operations specialist recommending next actions.

Claim decision: {claim_decision}
Overall severity: {overall_severity}
Estimated cost: {estimated_cost}
Fraud indicators: {len(fraud_indicators)} detected

Available actions catalog:
{json.dumps(CLAIM_ACTIONS_CATALOG, indent=2)}

Select 1-3 most appropriate actions based on:
- Claim decision (APPROVE → action ID 1 or 2)
- Severity (HIGH → action ID 4 or 6)
- Fraud flags (> 0 → action ID 5)
- Cost estimate (>$10k → action ID 6)

Respond in JSON:
{{
  "action_recommendations": [
    {{
      "action_id": 2,
      "action_name": "Approve with Workshop Inspection",
      "reasoning": "Moderate damage requires workshop verification before final approval",
      "priority": "HIGH"
    }}
  ],
  "reasoning": "Overall action strategy explanation"
}}
"""
    
    llm = make_model("models/gemini-2.5-flash-lite", timeout=60)

    
    messages = [
        HumanMessage(content=[
            {
                "type": "text",
                "text": system_prompt + "\n\nClaim data:\n" + json.dumps({
                    "claim_decision": claim_decision,
                    "overall_severity": overall_severity,
                    "estimated_cost": estimated_cost,
                    "fraud_indicators": fraud_indicators
                }, ensure_ascii=False)
            }
        ])
    ]
    
    try:
        response = llm.invoke(messages)
        response_text = response.content.strip()
        
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[0]
        
        parsed = json.loads(response_text)
        action_recommendations = parsed.get("action_recommendations", [])
        reasoning = parsed.get("reasoning", "")
    except Exception as e:
        print(f"⚠️ Action recommender failed: {e}")
        action_recommendations = []
        reasoning = "Failed to generate actions"
    
    state["action_recommendations"] = action_recommendations
    state["action_selection_reasoning"] = reasoning
    
    print(f"✅ Recommended {len(action_recommendations)} actions")
    for action in action_recommendations:
        print(f"   → {action.get('action_name')} (Priority: {action.get('priority')})")
    
    state["messages"].append(f"Recommended {len(action_recommendations)} actions")
    
    return state
