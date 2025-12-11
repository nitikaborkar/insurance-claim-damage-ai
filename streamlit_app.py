# streamlit_app.py - PROFESSIONAL EDITION (VERTICAL LAYOUT)
import streamlit as st
import os
from dotenv import load_dotenv
from PIL import Image
import glob

from car_agent.service import analyze_image_path

load_dotenv()

# PROFESSIONAL DARK MODE CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    /* Main Background */
    .stApp {
        background: linear-gradient(135deg, #0f0f1e 0%, #1a1a2e 50%, #16213e 100%);
        font-family: 'Inter', sans-serif;
    }
    
    /* Header Styling */
    h1 {
        font-family: 'Inter', sans-serif !important;
        font-weight: 700 !important;
        font-size: 3rem !important;
        text-align: center;
        color: #ffffff !important;
        letter-spacing: 0.02em;
        margin: 2rem 0 1rem 0 !important;
    }
    
    .subtitle {
        text-align: center;
        color: #4db8ff;
        font-size: 1.1rem;
        font-weight: 500;
        letter-spacing: 0.05em;
        margin-bottom: 3rem;
    }
    
    /* Sidebar Professional */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0a0a14 0%, #1a1a2e 100%);
        border-right: 1px solid rgba(77, 184, 255, 0.2);
    }
    
    [data-testid="stSidebar"] h3 {
        color: #4db8ff;
        font-weight: 600;
        font-size: 1.1rem;
        letter-spacing: 0.03em;
    }
    
    /* Professional Button */
    .stButton button {
        background: linear-gradient(135deg, #0066cc 0%, #4db8ff 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.85rem 2rem;
        font-family: 'Inter', sans-serif;
        font-weight: 600;
        font-size: 1rem;
        letter-spacing: 0.02em;
        transition: all 0.3s ease;
        box-shadow: 0 4px 12px rgba(77, 184, 255, 0.3);
        width: 100%;
    }
    
    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(77, 184, 255, 0.4);
        background: linear-gradient(135deg, #0052a3 0%, #3da3e0 100%);
    }
    
    /* Metric Cards */
    [data-testid="stMetricValue"] {
        font-family: 'Inter', sans-serif !important;
        font-size: 2rem !important;
        font-weight: 700 !important;
        color: #4db8ff !important;
    }
    
    [data-testid="stMetricLabel"] {
        color: #a0a0b0 !important;
        font-family: 'Inter', sans-serif;
        font-size: 0.85rem !important;
        font-weight: 500 !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    div[data-testid="metric-container"] {
        background: rgba(26, 26, 46, 0.6);
        border: 1px solid rgba(77, 184, 255, 0.3);
        border-radius: 12px;
        padding: 1.5rem;
        backdrop-filter: blur(10px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: transparent;
        border-bottom: 2px solid rgba(77, 184, 255, 0.2);
    }
    
    .stTabs [data-baseweb="tab"] {
        font-family: 'Inter', sans-serif;
        font-weight: 500;
        color: #a0a0b0;
        border-radius: 8px 8px 0 0;
        padding: 0.75rem 1.5rem;
        transition: all 0.3s ease;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background: rgba(77, 184, 255, 0.1);
        color: #4db8ff;
    }
    
    .stTabs [aria-selected="true"] {
        background: rgba(77, 184, 255, 0.15);
        color: #4db8ff !important;
        border-bottom: 3px solid #4db8ff;
    }
    
    /* Images */
    img {
        border: 2px solid rgba(77, 184, 255, 0.3);
        border-radius: 12px;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
    }
    
    /* File Uploader */
    [data-testid="stFileUploader"] {
        background: rgba(26, 26, 46, 0.4);
        border: 2px dashed rgba(77, 184, 255, 0.4);
        border-radius: 12px;
        padding: 2rem;
    }
    
    /* Radio Buttons */
    .stRadio > div {
        background: rgba(26, 26, 46, 0.4);
        border: 1px solid rgba(77, 184, 255, 0.2);
        border-radius: 8px;
        padding: 0.8rem;
    }
    
    .stRadio label {
        font-weight: 500;
        color: #ffffff !important;
    }
    
    /* Selectbox */
    .stSelectbox > div > div {
        background: rgba(26, 26, 46, 0.8);
        border: 1px solid rgba(77, 184, 255, 0.3);
        border-radius: 8px;
        color: #ffffff;
        font-weight: 500;
    }
    
    /* Expanders */
    .streamlit-expanderHeader {
        background: rgba(26, 26, 46, 0.6);
        border: 1px solid rgba(77, 184, 255, 0.3);
        border-radius: 8px;
        font-weight: 600;
        color: #4db8ff;
        padding: 1rem;
    }
    
    /* Alerts */
    .stSuccess {
        background: rgba(34, 197, 94, 0.15);
        border-left: 4px solid #22c55e;
        border-radius: 8px;
    }
    
    .stWarning {
        background: rgba(251, 191, 36, 0.15);
        border-left: 4px solid #fbbf24;
        border-radius: 8px;
    }
    
    .stError {
        background: rgba(239, 68, 68, 0.15);
        border-left: 4px solid #ef4444;
        border-radius: 8px;
    }
    
    .stInfo {
        background: rgba(77, 184, 255, 0.15);
        border-left: 4px solid #4db8ff;
        border-radius: 8px;
    }
    
    /* Divider */
    hr {
        border: none;
        height: 1px;
        background: rgba(77, 184, 255, 0.3);
        margin: 2rem 0;
    }
    
    /* Code Blocks */
    code {
        background: rgba(26, 26, 46, 0.8);
        border: 1px solid rgba(77, 184, 255, 0.3);
        border-radius: 4px;
        color: #4db8ff;
        padding: 0.2rem 0.5rem;
    }
    
    /* Headings */
    h3 {
        font-family: 'Inter', sans-serif !important;
        color: #ffffff !important;
        font-weight: 600 !important;
        font-size: 1.3rem !important;
        margin-bottom: 1.5rem !important;
    }
    
    /* Paragraph Text */
    p {
        color: #d0d0d8;
        font-weight: 400;
        line-height: 1.6;
    }
    
    /* Professional Card */
    .pro-card {
        background: rgba(26, 26, 46, 0.5);
        border: 1px solid rgba(77, 184, 255, 0.3);
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        backdrop-filter: blur(10px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    }
    
    /* Spinner */
    .stSpinner > div {
        border-top-color: #4db8ff !important;
    }
    
    /* Section Container */
    .section-container {
        background: rgba(26, 26, 46, 0.3);
        border: 1px solid rgba(77, 184, 255, 0.2);
        border-radius: 12px;
        padding: 2rem;
        margin-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)

st.set_page_config(
    page_title="AI Vehicle Damage Assessment",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Header
st.markdown("<h1>🚗 AI Vehicle Damage Assessment</h1>", unsafe_allow_html=True)
st.markdown("<p class='subtitle'>Automated Insurance Claim Analysis System</p>", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("### 📊 System Information")
    st.markdown("""
    <div class='pro-card'>
        <b style='color: #4db8ff; font-size: 1rem;'>AI Analysis Pipeline</b><br><br>
        <span style='color: #d0d0d8;'>• Damage Classification</span><br>
        <span style='color: #d0d0d8;'>• Photo Validation</span><br>
        <span style='color: #d0d0d8;'>• Severity Analysis</span><br>
        <span style='color: #d0d0d8;'>• Claim Decision Engine</span><br>
        <span style='color: #d0d0d8;'>• Action Recommendations</span><br>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    st.markdown("""
    <div class='pro-card'>
        <b style='color: #4db8ff; font-size: 1rem;'>Technology Stack</b><br><br>
        <code>LangGraph</code> <code>Gemini AI</code> <code>Multi-Agent System</code>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("""
    <div style='text-align: center; color: #4db8ff; font-size: 0.85rem; font-weight: 500;'>
        ● System Active ●
    </div>
    """, unsafe_allow_html=True)

# ===== IMAGE UPLOAD SECTION (TOP) =====
st.markdown("### 📤 Image Upload")

# Get test images
test_images_folder = "testing_images"
test_images = []
if os.path.exists(test_images_folder):
    test_images = glob.glob(os.path.join(test_images_folder, "*"))
    test_images = [f for f in test_images if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

# Image source
image_source = st.radio(
    "Select image source:",
    ["Upload New Image", "Use Test Image"],
    horizontal=True
)

image_path = None
image = None

if image_source == "Use Test Image":
    if test_images:
        test_image_names = [os.path.basename(f) for f in test_images]
        selected_image_name = st.selectbox(
            "Select test image:",
            test_image_names,
            help="Choose from pre-loaded test images"
        )
        
        image_path = os.path.join(test_images_folder, selected_image_name)
        image = Image.open(image_path)
        st.image(image, caption=f"Selected: {selected_image_name}", use_column_width=True)
    else:
        st.warning(f"No test images found in `{test_images_folder}` folder")

else:  # Upload New Image
    uploaded_file = st.file_uploader(
        "Upload vehicle damage photo",
        type=['jpg', 'jpeg', 'png'],
        help="Supported formats: JPG, JPEG, PNG"
    )
    
    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Image", use_column_width=True)
        
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp:
            image.save(tmp.name)
            image_path = tmp.name

# Analyze button (centered and prominent)
if image:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔍 Analyze Damage", type="primary"):
        with st.spinner("Analyzing damage... Please wait"):
            try:
                result = analyze_image_path(image_path)
                
                if image_source == "Upload New Image" and os.path.exists(image_path):
                    os.unlink(image_path)
                
                st.divider()
                
                # ===== ANALYSIS RESULTS SECTION (BOTTOM) =====
                st.markdown("### 📋 Analysis Results")
                
                st.success("✅ Analysis Complete")
                
                # Metrics
                st.markdown("<br>", unsafe_allow_html=True)
                m1, m2, m3 = st.columns(3)
                with m1:
                    st.metric("Claim Status", result['claim_decision'])
                with m2:
                    st.metric("Severity Level", result['overall_severity'])
                with m3:
                    st.metric("Estimated Cost", result['estimated_cost'])
                
                st.markdown("<br>", unsafe_allow_html=True)
                st.divider()
                
                # Tabs
                tab1, tab2, tab3 = st.tabs(["Summary", "Damage Details", "Recommendations"])
                
                with tab1:
                    st.markdown(f"""
                    <div class='pro-card'>
                        <p><b style='color: #4db8ff;'>Category:</b> <span style='color: #fff;'>{result['damage_category']}</span></p>
                        <p><b style='color: #4db8ff;'>Description:</b> <span style='color: #fff;'>{result['damage_description']}</span></p>
                        <p><b style='color: #4db8ff;'>Incident Type:</b> <span style='color: #fff;'>{result.get('incident_context', 'Not specified')}</span></p>
                        <p><b style='color: #4db8ff;'>Photo Valid:</b> <span style='color: #22c55e;'>{'✓ Yes' if result['photo_valid'] else '✗ No'}</span></p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if result.get('skip_reason'):
                        st.warning(f"⚠️ {result['skip_reason']}")
                    
                    if result.get('affected_areas'):
                        st.markdown("<br>", unsafe_allow_html=True)
                        areas_str = ", ".join(result['affected_areas'])
                        st.markdown(f"""
                        <div class='pro-card'>
                            <b style='color: #4db8ff;'>Affected Areas</b><br><br>
                            <span style='color: #ffffff; font-size: 1.05rem;'>{areas_str}</span>
                        </div>
                        """, unsafe_allow_html=True)
                
                with tab2:
                    if result.get('flagged_damages'):
                        st.markdown(f"**Detected Damages: {len(result['flagged_damages'])}**")
                        st.markdown("<br>", unsafe_allow_html=True)
                        
                        for i, damage in enumerate(result['flagged_damages'][:5], 1):
                            severity_emoji = {
                                "SEVERE": "🔴",
                                "MODERATE": "🟡",
                                "MINOR": "🟢"
                            }
                            emoji = severity_emoji.get(damage.get('severity'), "⚪")
                            
                            with st.expander(
                                f"{emoji} {damage.get('damage_area')} - {damage.get('severity')} Severity", 
                                expanded=(i==1)
                            ):
                                st.markdown(f"""
                                <div class='pro-card'>
                                    <p><b>Observation:</b> {damage.get('observation', 'N/A')}</p>
                                    <p><b>Estimated Cost:</b> {damage.get('estimated_cost', 'N/A')}</p>
                                    <p><b>Confidence Level:</b> {damage.get('confidence', 'N/A')}</p>
                                </div>
                                """, unsafe_allow_html=True)
                                
                                if damage.get('repair_action'):
                                    st.info(f"**Repair Required:** {damage.get('repair_action')}")
                                
                                if damage.get('risk'):
                                    st.warning(f"**Risk Assessment:** {damage.get('risk')}")
                    else:
                        st.info("No damage detected in the uploaded image")
                
                with tab3:
                    if result.get('recommended_actions'):
                        st.markdown("**Recommended Actions:**")
                        for action in result['recommended_actions']:
                            st.success(f"• {action}")
                    
                    if result.get('next_actions'):
                        st.markdown("<br>", unsafe_allow_html=True)
                        st.markdown("**Next Steps:**")
                        for action in result['next_actions']:
                            st.info(f"**{action.get('action_name', 'N/A')}:** {action.get('reasoning', '')}")
                    
                    if result.get('fraud_indicators'):
                        st.markdown("<br>", unsafe_allow_html=True)
                        st.error("**⚠️ Fraud Indicators Detected**")
                        for indicator in result['fraud_indicators']:
                            st.markdown(f"""
                            <div class='pro-card' style='border-color: #ef4444;'>
                                ⚠ {indicator}
                            </div>
                            """, unsafe_allow_html=True)
                
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                import traceback
                with st.expander("View error details"):
                    st.code(traceback.format_exc())
else:
    st.info("👆 Please upload or select an image above to begin analysis")

st.divider()
st.markdown("""
<div style='text-align: center; color: #a0a0b0;'>
    <span style='color: #ffffff; font-size: 0.95rem; font-weight: 500;'>Automated Car Damage Inspection & Insurance Processing</span><br>
    <span style='font-size: 0.85rem; color: #4db8ff;'>Multi-Agent AI System for Insurance Automation</span><br>
    <span style='font-size: 0.75rem; color: #808090;'>© 2025 Nitika Borkar</span>
</div>
""", unsafe_allow_html=True)
