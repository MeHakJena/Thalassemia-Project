import pickle
import os

def predict_severity(mutation_class, zygosity, hbvar_severity, variant_type):
    """
    Rule-based severity prediction for Beta-thalassemia.
    Returns: Carrier, Minor, Intermedia, Major, or Unknown.
    """
    mclass = str(mutation_class).lower()
    zyg = str(zygosity).lower()
    hb_sev = str(hbvar_severity).lower()
    
    # If HbVar already specifies Major/Intermedia and zygosity is homozygous
    if zyg == 'homozygous' or zyg == 'compound heterozygous':
        if 'major' in hb_sev or 'beta0' in mclass:
            return 'Major'
        if 'intermedia' in hb_sev or 'beta+' in mclass:
            return 'Intermedia'
        return 'Major' # Default severe if homozygous
        
    if zyg == 'heterozygous':
        if 'beta0' in mclass or 'beta+' in mclass:
            return 'Minor'
        if 'carrier' in hb_sev or 'benign' in str(variant_type).lower():
            return 'Carrier'
        return 'Minor'
        
    return 'Unknown'

def save_severity_rules():
    os.makedirs('saved_models', exist_ok=True)
    # Just save a dummy config or the logic is in the code
    with open('saved_models/severity_model.pkl', 'wb') as f:
        pickle.dump({'predict': predict_severity}, f)
    print("Severity rule-based model saved.")

if __name__ == "__main__":
    save_severity_rules()
