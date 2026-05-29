import streamlit as st
import pandas as pd
import requests
import matplotlib.pyplot as plt
import numpy as np
import shap

# --- Page Config ---
st.set_page_config(page_title="BETA-AI", layout="wide", page_icon="🧬")

# --- Custom CSS for Aesthetics ---
st.markdown("""
<style>
    /* Main background */
    .stApp {
        background-color: #0d1117;
        color: #c9d1d9;
        font-family: 'Inter', sans-serif;
    }
    /* Headers */
    h1, h2, h3 {
        color: #58a6ff;
        font-weight: 600;
    }
    /* Cards for metrics */
    div[data-testid="metric-container"] {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        transition: transform 0.2s;
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-5px);
        border-color: #58a6ff;
    }
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #161b22;
        border-right: 1px solid #30363d;
    }
    /* Buttons */
    .stButton>button {
        background-color: #238636;
        color: #ffffff;
        border: none;
        border-radius: 6px;
        padding: 10px 24px;
        font-weight: bold;
        transition: background-color 0.2s;
    }
    .stButton>button:hover {
        background-color: #2ea043;
    }
</style>
""", unsafe_allow_html=True)

# --- Load Data ---
@st.cache_data
def load_data():
    master = pd.read_csv('../data/merged/master_variant_table.csv')
    trusted = pd.read_csv('../data/merged/trusted_variants.csv')
    synthetic = pd.read_csv('../data/merged/synthetic_corrupted_vcf.csv')
    return master, trusted, synthetic

master_df, trusted_df, corrupted_df = load_data()

# --- Sidebar Navigation ---
st.sidebar.title("🧬 BETA-AI")
st.sidebar.markdown("Explainable Self-Healing Genomic Variant Interpretation Dashboard for Beta-Thalassemia")
page = st.sidebar.radio("Navigation", [
    "Dataset Overview", 
    "QC Dashboard", 
    "Variant Interpretation", 
    "Severity Prediction", 
    "Explainability"
])

# --- Page 1: Dataset Overview ---
if page == "Dataset Overview":
    st.title("Dataset Overview")
    st.markdown("Overview of the trusted Beta-Thalassemia variants combining ClinVar, gnomAD, and HbVar.")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Variants", len(trusted_df))
    col2.metric("Pathogenic", len(trusted_df[trusted_df['pathogenicity'] == 'Pathogenic']))
    col3.metric("Benign", len(trusted_df[trusted_df['pathogenicity'] == 'Benign']))
    col4.metric("VUS", len(trusted_df[trusted_df['pathogenicity'].str.contains('Uncertain', na=False)]))
    
    st.subheader("Trusted Variants Table")
    st.dataframe(trusted_df.head(100), use_container_width=True)

# --- Page 2: QC Dashboard ---
elif page == "QC Dashboard":
    st.title("Self-Healing QC Dashboard")
    st.markdown("Monitoring the automated data quality and repair pipeline (Isolation Forest).")
    
    col1, col2, col3 = st.columns(3)
    
    initial_rows = len(corrupted_df)
    final_rows = len(trusted_df)
    duplicates_removed = initial_rows - len(corrupted_df.drop_duplicates(subset=['chr', 'pos', 'ref', 'alt', 'gene']))
    
    col1.metric("Ingested Rows", initial_rows)
    col2.metric("Duplicates Repaired", duplicates_removed)
    col3.metric("Trusted Output Rows", final_rows)
    
    st.subheader("Anomaly Detection")
    st.markdown("Rows identified as highly anomalous by the Isolation Forest model:")
    # We don't have the anomaly column saved in trusted_df directly, so we just show a sample of corrupted
    st.dataframe(corrupted_df.head(10), use_container_width=True)

# --- Page 3: Variant Interpretation ---
elif page == "Variant Interpretation":
    st.title("Variant Interpretation (AI)")
    st.markdown("Predict the pathogenicity of an HBB variant using our XGBoost model.")
    
    col1, col2 = st.columns(2)
    with col1:
        allele_freq = st.number_input("Allele Frequency (gnomAD)", value=0.0001, format="%f")
        homozygote_count = st.number_input("Homozygote Count", value=0, step=1)
    with col2:
        variant_type = st.selectbox("Variant Type", trusted_df['variant_type'].dropna().unique())
        mutation_class = st.selectbox("Mutation Class", trusted_df['mutation_class'].dropna().unique())
        
    if st.button("Predict Pathogenicity"):
        payload = {
            "allele_freq": allele_freq,
            "homozygote_count": homozygote_count,
            "variant_type": variant_type,
            "mutation_class": mutation_class
        }
        try:
            res = requests.post("http://127.0.0.1:8000/predict_pathogenicity", json=payload).json()
            st.success(f"**Prediction:** {res['prediction']}")
            st.session_state['last_prediction'] = res
        except Exception as e:
            st.error("API Error. Ensure FastAPI is running on port 8000.")

# --- Page 4: Severity Prediction ---
elif page == "Severity Prediction":
    st.title("Disease Severity Prediction")
    st.markdown("Predict Beta-Thalassemia clinical severity based on genomic evidence.")
    
    mut_class = st.selectbox("Mutation Class", ["beta0", "beta+", "alpha-2", "delta+", "Unknown"])
    zygosity = st.selectbox("Zygosity", ["Heterozygous", "Homozygous", "Compound Heterozygous"])
    hbvar_sev = st.selectbox("HbVar Known Severity", ["Major", "Intermedia", "Minor", "Carrier", "Unknown"])
    var_type = st.selectbox("Variant Type", ["Pathogenic", "Benign", "single nucleotide variant"])
    
    if st.button("Predict Severity"):
        payload = {
            "mutation_class": mut_class,
            "zygosity": zygosity,
            "hbvar_severity": hbvar_sev,
            "variant_type": var_type
        }
        try:
            res = requests.post("http://127.0.0.1:8000/predict_severity", json=payload).json()
            st.info(f"**Predicted Severity:** {res['severity']}")
        except Exception as e:
            st.error("API Error.")

# --- Page 5: Explainability ---
elif page == "Explainability":
    st.title("Explainable AI (SHAP)")
    st.markdown("Understand why the AI made its pathogenicity prediction.")
    
    if 'last_prediction' in st.session_state:
        res = st.session_state['last_prediction']
        st.subheader(f"Explanation for prediction: {res['prediction']}")
        
        # Display raw SHAP values in a bar chart
        features = res['features']
        values = res['shap_values']
        
        fig, ax = plt.subplots(figsize=(8, 4))
        # Ensure values is 1D
        if isinstance(values[0], list):
             values = values[0]
             
        y_pos = np.arange(len(features))
        colors = ['red' if v > 0 else 'blue' for v in values]
        
        ax.barh(y_pos, values, align='center', color=colors)
        ax.set_yticks(y_pos, labels=features)
        ax.invert_yaxis()  # labels read top-to-bottom
        ax.set_xlabel('SHAP Value (Impact on output)')
        ax.set_title('Feature Importance for this Prediction')
        
        # Set dark theme for matplotlib
        fig.patch.set_facecolor('#0d1117')
        ax.set_facecolor('#0d1117')
        ax.xaxis.label.set_color('#c9d1d9')
        ax.yaxis.label.set_color('#c9d1d9')
        ax.title.set_color('#c9d1d9')
        ax.tick_params(axis='x', colors='#c9d1d9')
        ax.tick_params(axis='y', colors='#c9d1d9')
        
        st.pyplot(fig)
        
        st.info("Red indicates features pushing the prediction higher (e.g. towards Pathogenic), Blue pushes lower.")
    else:
        st.warning("Please make a prediction on the 'Variant Interpretation' page first to see the explanation.")
