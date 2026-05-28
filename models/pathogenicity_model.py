import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
import pickle
import os

def train_pathogenicity_model():
    print("Loading trusted variants for training...")
    df = pd.read_csv('../data/merged/trusted_variants.csv')
    
    # Map classes
    def map_class(p):
        p = str(p).lower()
        if 'benign' in p: return 'Benign'
        if 'pathogenic' in p: return 'Pathogenic'
        if 'uncertain' in p: return 'VUS'
        return 'Unknown'
        
    df['target'] = df['pathogenicity'].apply(map_class)
    
    # Filter known targets for training
    train_df = df[df['target'] != 'Unknown'].copy()
    print(f"Training on {len(train_df)} rows with known pathogenicity.")
    
    # Features
    # 'allele_freq', 'homozygote_count', 'variant_type', 'mutation_class'
    
    # We need to encode categorical variables
    cat_cols = ['variant_type', 'mutation_class']
    num_cols = ['allele_freq', 'homozygote_count']
    
    # Simple label encoding for tree model
    encoders = {}
    for col in cat_cols:
        le = LabelEncoder()
        train_df[col] = train_df[col].fillna('Missing').astype(str)
        train_df[col] = le.fit_transform(train_df[col])
        encoders[col] = le
        
    # Target encoding
    target_le = LabelEncoder()
    y = target_le.fit_transform(train_df['target'])
    encoders['target'] = target_le
    
    X = train_df[num_cols + cat_cols].fillna(0)
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    model = xgb.XGBClassifier(n_estimators=100, max_depth=5, learning_rate=0.1, random_state=42)
    model.fit(X_train, y_train)
    
    train_acc = model.score(X_train, y_train)
    test_acc = model.score(X_test, y_test)
    print(f"Train Accuracy: {train_acc:.4f}, Test Accuracy: {test_acc:.4f}")
    
    # Save model and encoders
    os.makedirs('saved_models', exist_ok=True)
    with open('saved_models/pathogenicity_model.pkl', 'wb') as f:
        pickle.dump({'model': model, 'encoders': encoders, 'features': num_cols + cat_cols}, f)
        
    print("Pathogenicity model saved.")

if __name__ == "__main__":
    train_pathogenicity_model()
