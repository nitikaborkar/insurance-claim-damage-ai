from langchain_core.messages import HumanMessage, SystemMessage
from ergo_agent.state import AgentState, ERGONOMIC_DATA, ACTIVITY_CATEGORIES
import json
from langchain_anthropic import ChatAnthropic
llm = ChatAnthropic(model="claude-sonnet-4-20250514", temperature=0)

def general_ergonomic_analysis(state: AgentState) -> AgentState:
    """
    Perform general ergonomic analysis using VLM's knowledge
    Used when activity doesn't match predefined categories
    """
    print("🔍 Using general ergonomic analysis (OTHERS category)")
    
    system_prompt = """You are an expert ergonomic assessor with deep knowledge of biomechanics, posture, and workplace ergonomics.

Analyze this image for ANY ergonomic risks or postural issues you can identify. Consider:

1. **Head and Neck Position**: Forward head posture, neck flexion/extension, rotation
2. **Shoulders and Upper Back**: Rounded shoulders, elevation, asymmetry
3. **Lower Back and Spine**: Lumbar support, slouching, twisting
4. **Arms and Wrists**: Arm support, wrist angles, reaching
5. **Hips and Legs**: Hip alignment, leg positioning, foot support
6. **Screen/Device Position**: Distance, height, angle
7. **Overall Posture**: Balance, symmetry, sustained positions
8. **Environmental Factors**: Workstation setup, furniture support

For EACH risk you identify, provide:
- Specific body region affected
- Clear description of what you observe
- Why this is problematic (health impact)
- Quick fix recommendation
- Long-term best practice

Respond in this exact JSON format:
{
  "risk_analysis": [
    {
      "check_number": 1,
      "cue": "descriptive name of the postural issue",
      "body_region": "specific body part",
      "present": true,
      "confidence": "HIGH/MEDIUM/LOW",
      "observation": "what you see in the image",
      "risk": "why this is harmful",
      "quick_fix": "immediate action to take",
      "long_term_practice": "sustainable solution"
    }
  ]
}

Only include risks you can actually see in the image. Be thorough but accurate."""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=[
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": state["image_base64"]
                }
            },
            {
                "type": "text",
                "text": "Analyze this image for any ergonomic risks. Use your expert knowledge to identify postural issues and provide recommendations."
            }
        ])
    ]
    
    response = llm.invoke(messages)
    
    # Parse the response
    try:
        response_text = response.content.strip()
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]
        
        analysis_result = json.loads(response_text)
        risk_analysis = analysis_result.get("risk_analysis", [])
    except json.JSONDecodeError as e:
        print(f"⚠️  Failed to parse JSON: {e}")
        print(f"Response: {response.content[:200]}...")
        risk_analysis = []
    
    state["risk_analysis"] = risk_analysis
    
    # Filter flagged risks (present = True)
    flagged_risks = [r for r in risk_analysis if r.get("present", False)]
    state["flagged_risks"] = flagged_risks
    
    print(f"✅ General analysis complete: {len(flagged_risks)} risks identified")
    for risk in flagged_risks:
        print(f"   ⚠️  {risk.get('cue')} [{risk.get('body_region')}] - Confidence: {risk.get('confidence')}")
    
    state["messages"].append(f"General analysis found {len(flagged_risks)} risks")
    
    return state

def activity_classifier_node(state: AgentState) -> AgentState:
    """
    Agent 1: Classify the activity in the image
    Uses VLM to identify which activity category the image belongs to
    """
    print("\n🔍 AGENT 1: Activity Classifier")
    print("=" * 60)
        
    # Prepare the prompt
    categories_list = "\n".join([f"- {cat}" for cat in ACTIVITY_CATEGORIES])
    
    system_prompt = f"""You are an ergonomic activity classifier. Your job is to analyze an image and classify it into ONE of these specific activity categories:

{categories_list}

Analyze the image carefully and determine which activity category best matches what you see. Consider:
- What is the person doing? (working, watching TV, gaming, cooking, etc.)
- What is their posture/position? (on sofa, in bed, on floor, standing, sitting at desk, driving)
- What devices or objects are visible? (laptop, phone, TV, gaming console, kitchen items, car interior)

Respond with ONLY the exact category name from the list above.
If the image doesn't clearly match any category, respond with exactly: OTHERS"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=[
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": state["image_base64"]
                }
            },
            {
                "type": "text",
                "text": "What activity category does this image belong to? Respond with ONLY the category name."
            }
        ])
    ]
    
    response = llm.invoke(messages)
    activity_category = response.content.strip()
    
    # Validate the category - allow "OTHERS" as valid
    if activity_category == "OTHERS":
        print(f"✅ Activity classified as: OTHERS (will use general analysis)")
    elif activity_category not in ACTIVITY_CATEGORIES:
        print(f"⚠️  VLM returned: '{activity_category}'")
        print("   Attempting to match to known categories...")
        # Try fuzzy matching first
        matched = False
        for cat in ACTIVITY_CATEGORIES:
            if activity_category.lower() in cat.lower() or cat.lower() in activity_category.lower():
                activity_category = cat
                matched = True
                print(f"   ✓ Matched to: {activity_category}")
                break
        
        # If no match found, use OTHERS instead of forcing wrong category
        if not matched:
            activity_category = "OTHERS"
            print(f"   No match found. Using general analysis: OTHERS")
    else:
        print(f"✅ Activity classified as: {activity_category}")
    
    state["activity_category"] = activity_category
    state["messages"].append(f"Classified activity: {activity_category}")
    
    return state

def filterer_node(state: AgentState) -> AgentState:
    """
    Agent: Filter relevant ergonomic checks based on activity category
    """
    print("\n🔍 AGENT: Filterer")
    print("=" * 60)

    # Get relevant checks for this activity

    system_prompt = f"""
    You are an ergonomic activity filterer. Your job is to decide whether an input image
    is suitable for meaningful ergonomic assessment for the activity category:
    `{state["activity_category"]}`.

    You MUST classify the image into one of two labels:
    - "VALID"      → ergonomic assessment CAN be performed
    - "INVALID"    → ergonomic assessment SHOULD BE SKIPPED

    General rules:
    1. Only assess REAL humans in REAL photos or videos.
    - Reject cartoons, illustrations, avatars, CGI renders, stick figures, or mannequin images.
    2. The activity must be a meaningful, sustained task where posture is held or repeated
    long enough to create ergonomic risk (e.g., desk work, lifting, cooking, cleaning).
    - Reject short, transient or incidental actions such as:
        - quickly glancing at a watch.
        - casual posing for a photo or stretching for a second
    3. The person’s posture and work setup must be visible enough to judge ergonomics.
    - Reject images where:
        - most of the body is out of frame or heavily occluded
        - the key working limb or tool is completely hidden
        - the scene is too dark, blurry, or distant to see posture clearly.
    4. If the image shows a mobility aid (wheelchair, walking stick, crutches, walker),
    it is STILL VALID as long as:
    - the person is clearly performing a real task (e.g., typing, cooking, reaching, pushing, texting, scrolling, lifting)
    - the posture and relationship to the workstation/equipment can be seen.
    - the person is engaging in a common activity (eg: carrying items, backpack, luggage) that could be analyzed ergonomically.
    - the person is exercising (eg: lifting weights, doing yoga, running, walking) where posture and setup can be judged.
    5. If the scene is ambiguous and you cannot reliably infer what task is being performed,
    treat it as INVALID.

    Think step by step about:
    - Is this a real human?
    - Is this a sustained, ergonomically relevant activity?
    - Can posture and setup be seen clearly enough to judge risk?

    Respond ONLY in this strict JSON format:

    {{
    "validity": "VALID" or "INVALID",
    "reason": "one-sentence explanation",
    "notes_for_downstream": "any hints for later ergonomic analysis, or empty string"
    }}
    """


    messages = [
    SystemMessage(content=system_prompt),
    HumanMessage(content=[
        {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": state["image_base64"],
            },
        },
        {
            "type": "text",
            "text": "Decide if this image is VALID or INVALID for ergonomic assessment using the rules.",
        },
    ]),
    ]

    response = llm.invoke(messages)

    # Claude returns an AIMessage; extract text
    response_text = response.content.strip()

    # Strip code fences if any
    if "```json" in response_text:
        response_text = response_text.split("```json")[1].split("```")[0]
    elif "```" in response_text:
        response_text = response_text.split("```")[1].split("```")[0]

    try:
        result = json.loads(response_text)
    except json.JSONDecodeError:
        print("⚠️ Filterer: failed to parse JSON, marking image as INVALID")
        result = {
            "validity": "INVALID",
            "reason": "Model returned malformed JSON",
            "notes_for_downstream": "",
        }


    validity = (result.get("validity") or "").upper()
    reason = result.get("reason", "")
    notes = result.get("notes_for_downstream", "")

    # Save into state for later nodes
    state["filter_result"] = {
        "validity": validity,
        "reason": reason,
        "notes_for_downstream": notes,
    }

    print(f"✅ Filter decision: {validity} — {reason}")

    # If INVALID, you can either stop early or mark a flag
    if validity == "INVALID":
        state["should_skip_ergonomics"] = True
        # Option A: short-circuit later nodes by returning early
        # (your graph logic will need to check this flag)
        return state

    state["should_skip_ergonomics"] = False
    return state

def risk_analyzer_node(state: AgentState) -> AgentState:
    """
    Agent 2: Analyze risks based on the activity category
    Extracts relevant checks and uses VLM to analyze if risks are present
    """
    print("\n🔬 AGENT 2: Risk Analyzer")
    print("=" * 60)
        
    # Get relevant checks for this activity
    activity_category = state["activity_category"]
    relevant_checks = ERGONOMIC_DATA.get(activity_category, [])
    state["relevant_checks"] = relevant_checks
    
    # If no predefined checks or OTHERS category, use general analysis
    if not relevant_checks or activity_category == "OTHERS":
        return general_ergonomic_analysis(state)
    
    print(f"📋 Found {len(relevant_checks)} checks for this activity")
    
    # Prepare detailed analysis prompt
    checks_description = "\n\n".join([
        f"CHECK #{i+1}:\n"
        f"  Looking for: {check['cue']}\n"
        f"  Body region: {check['body_region']}\n"
        f"  Risk if present: {check['risk']}"
        for i, check in enumerate(relevant_checks)
    ])
    
    system_prompt = f"""
You are an expert ergonomic risk assessor. Analyze the image for postural risks related to:
`{activity_category}`.

IMPORTANT: You are NOT judging this exact frozen pose as if the person holds it forever.
Instead, you must:
- Infer the TYPICAL way this activity is performed over time in real life.
- Assume a realistic duration and repetition pattern for this activity
  (e.g., desk work: many hours with short breaks; cooking: repeated reaching, chopping, stirring;
  lifting boxes: repeated lifts over a shift).
- Distinguish between:
  - brief, transient actions (e.g., quickly smelling food, glancing at a watch)
  - sustained or frequently repeated postures (e.g., prolonged bending, twisting, overhead reaching).

If the current frame shows a short, incidental motion that would only last a few seconds
during normal work, you MUST:
- Treat it as LOW ergonomic significance UNLESS this posture would be repeated frequently.
- Base your main risk judgment on the general posture pattern expected for this activity
  (e.g., for cooking, the person will mostly stand upright, alternate between cutting and stirring,
  and only occasionally bend to smell or check food).

You need to evaluate the following ergonomic checks:

{checks_description}

For EACH check, you must:
1. Mentally simulate how a typical person performs this activity over a realistic period.
2. Use the image to estimate their likely GENERAL posture during the task
   (not just this single micro-moment).
3. Decide if that risk would be present for a meaningful duration or at a meaningful frequency.

Then answer for each check:
1. "present": true/false  → Is this risk likely to be present in the REALISTIC, ongoing activity?
2. "confidence": "HIGH" / "MEDIUM" / "LOW"
3. "observation": Brief explanation:
   - reference what you see in the image, AND
   - briefly state your assumption about how the activity continues over time
     (e.g., "momentarily bent to smell food, but will mostly cook in upright standing posture,
      so sustained trunk flexion risk is low").

Respond ONLY in this JSON format:

{{
  "risk_analysis": [
    {{
      "check_number": 1,
      "cue": "exact cue text",
      "present": true or false,
      "confidence": "HIGH" or "MEDIUM" or "LOW",
      "observation": "what you see + how you expect the posture over time"
    }},
    ...
  ]
}}
"""


    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=[
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": state["image_base64"]
                }
            },
            {
                "type": "text",
                "text": "Analyze this image for the ergonomic risks listed above. Return your analysis in the JSON format specified."
            }
        ])
    ]
    
    response = llm.invoke(messages)
    
    # Parse the response
    try:
        # Extract JSON from response (handle markdown code blocks)
        response_text = response.content.strip()
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]
        
        analysis_result = json.loads(response_text)
        risk_analysis = analysis_result.get("risk_analysis", [])
    except json.JSONDecodeError as e:
        print(f"⚠️  Failed to parse JSON: {e}")
        print(f"Response: {response.content[:200]}...")
        risk_analysis = []
    
    # Combine analysis with original check data
    for i, analysis in enumerate(risk_analysis):
        if i < len(relevant_checks):
            analysis.update({
                "body_region": relevant_checks[i]["body_region"],
                "risk": relevant_checks[i]["risk"],
                "long_term_practice": relevant_checks[i]["long_term_practice"],
                "quick_fix": relevant_checks[i]["quick_fix"]
            })
    
    state["risk_analysis"] = risk_analysis
    
    # Filter flagged risks (present = True)
    flagged_risks = [r for r in risk_analysis if r.get("present", False)]
    state["flagged_risks"] = flagged_risks
    
    print(f"✅ Analysis complete: {len(flagged_risks)} risks flagged out of {len(risk_analysis)} checks")
    for risk in flagged_risks:
        print(f"   ⚠️  {risk.get('cue')} - Confidence: {risk.get('confidence')}")
    
    state["messages"].append(f"Analyzed {len(risk_analysis)} checks, flagged {len(flagged_risks)} risks")
    
    return state


def recommender_node(state: AgentState) -> AgentState:
    """
    Agent 3: Generate recommendations based on flagged risks
    Provides both quick fixes and long-term best practices
    """
    print("\n💡 AGENT 3: Recommender")
    print("=" * 60)
    
    flagged_risks = state["flagged_risks"]
    
    if not flagged_risks:
        print("✅ No risks flagged - no recommendations needed")
        state["recommendations"] = [{
            "summary": "Great posture! No ergonomic risks detected.",
            "quick_fixes": [],
            "long_term_practices": []
        }]
        state["messages"].append("No risks detected")
        return state
    
    print(f"📝 Generating recommendations for {len(flagged_risks)} flagged risks")
    
    # Organize recommendations
    recommendations = {
        "summary": f"Found {len(flagged_risks)} ergonomic concerns that need attention:",
        "quick_fixes": [],
        "long_term_practices": [],
        "detailed_risks": []
    }
    
    for risk in flagged_risks:
        recommendations["detailed_risks"].append({
            "issue": risk.get("cue"),
            "body_region": risk.get("body_region"),
            "why_risky": risk.get("risk"),
            "observation": risk.get("observation"),
            "confidence": risk.get("confidence")
        })
        
        recommendations["quick_fixes"].append({
            "body_region": risk.get("body_region"),
            "action": risk.get("quick_fix")
        })
        
        recommendations["long_term_practices"].append({
            "body_region": risk.get("body_region"),
            "practice": risk.get("long_term_practice")
        })
    
    state["recommendations"] = [recommendations]
    state["messages"].append(f"Generated recommendations for {len(flagged_risks)} risks")
    
    print("✅ Recommendations generated successfully")
    
    return state