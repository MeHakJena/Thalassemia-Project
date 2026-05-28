import shap
import pickle
import matplotlib.pyplot as plt
import numpy as np

def generate_shap_explanation(model_path, instance_df):
    """
    Generates SHAP values for the given instance using the trained XGBoost model.
    """
    with open(model_path, 'rb') as f:
        data = pickle.load(f)
        
    model = data['model']
    features = data['features']
    encoders = data['encoders']
    
    # Preprocess instance
    X = instance_df[features].copy()
    for col in features:
        if col in encoders and col != 'target':
            le = encoders[col]
            # Handle unknown categories safely
            known_classes = set(le.classes_)
            X[col] = X[col].apply(lambda x: x if x in known_classes else 'Missing')
            # Create a dictionary for mapping to avoid ValueError on unseeen
            mapper = dict(zip(le.classes_, le.transform(le.classes_)))
            # Assume 0 is 'Missing' or default if not found
            default_val = mapper.get('Missing', 0)
            X[col] = X[col].map(lambda x: mapper.get(x, default_val))
            
    # Calculate SHAP values
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X)
    
    # Ensure shape consistency for multiclass
    if isinstance(shap_values, list):
        # Multiclass: return the explanation for the predicted class
        pred_class_idx = model.predict(X)[0]
        sv = shap_values[pred_class_idx][0]
        base_value = explainer.expected_value[pred_class_idx]
    else:
        # Binary or single output
        sv = shap_values[0]
        base_value = explainer.expected_value
        if isinstance(base_value, np.ndarray):
            base_value = base_value[0]
            
    # Ensure base_value is a scalar
    if isinstance(base_value, (list, np.ndarray)):
        base_value = base_value[0]
        
    # Return as dict for frontend to render or just return the raw values
    explanation = {
        'features': features,
        'values': sv.tolist() if isinstance(sv, np.ndarray) else sv,
        'base_value': float(base_value)
    }
    return explanation

if __name__ == "__main__":
    print("Explainability module ready.")
