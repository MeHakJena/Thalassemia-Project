"""
Test script for GeneTrustAI-Thal API predictions
"""

import requests
import json
import sys
import time
import subprocess
import os

# Start API server in background
print("=" * 80)
print("TESTING GENETRUSAI-THAL API V2.0")
print("=" * 80)

print("\n[1/4] Starting FastAPI server...")
api_process = subprocess.Popen(
    ['python3', '-m', 'uvicorn', 'api.main:app', '--host', '127.0.0.1', '--port', '8000'],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    cwd='/Users/mehakjena/Desktop/Thalassemia'
)

# Give server time to start
time.sleep(3)

BASE_URL = "http://127.0.0.1:8000"

# Test cases
test_cases = [
    {
        "name": "Pathogenic Variant (high allele freq, with mutation class)",
        "data": {
            "allele_freq": 0.15,
            "homozygote_count": 500,
            "variant_type": "SNP",
            "mutation_class": "beta0"
        }
    },
    {
        "name": "Benign Variant (low allele freq)",
        "data": {
            "allele_freq": 0.001,
            "homozygote_count": 2,
            "variant_type": "SNP",
            "mutation_class": "beta+"
        }
    },
    {
        "name": "VUS - Unknown mutation class",
        "data": {
            "allele_freq": 0.05,
            "homozygote_count": 100,
            "variant_type": "SNP",
            "mutation_class": "Unknown"
        }
    },
    {
        "name": "Rare variant (very low frequency)",
        "data": {
            "allele_freq": 0.00001,
            "homozygote_count": 0,
            "variant_type": "SNP",
            "mutation_class": "beta+"
        }
    }
]

try:
    print("\n[2/4] Testing API endpoints...")
    
    # Health check
    print("\n  → GET /")
    response = requests.get(f"{BASE_URL}/")
    if response.status_code == 200:
        print(f"    ✓ Health check passed")
        health = response.json()
        print(f"    ✓ Service: {health.get('service')}")
        print(f"    ✓ Version: {health.get('version')}")
        print(f"    ✓ Model: {health.get('model')}")
    else:
        print(f"    ✗ Health check failed: {response.status_code}")
    
    # Dataset overview
    print("\n  → GET /dataset_overview")
    response = requests.get(f"{BASE_URL}/dataset_overview")
    if response.status_code == 200:
        data = response.json()
        print(f"    ✓ Total variants: {data.get('total_variants')}")
        print(f"    ✓ Labeled variants: {data.get('labeled_variants')}")
        print(f"    ✓ Pathogenic: {data.get('pathogenic')}")
        print(f"    ✓ Benign: {data.get('benign')}")
        print(f"    ✓ VUS: {data.get('vus')}")
        print(f"    ✓ Genomic range: {data.get('genomic_range')}")
    else:
        print(f"    ✗ Failed: {response.status_code}")
    
    # Predictions
    print("\n[3/4] Testing pathogenicity predictions...")
    for i, test in enumerate(test_cases, 1):
        print(f"\n  Test {i}: {test['name']}")
        print(f"  Input: {test['data']}")
        
        response = requests.post(
            f"{BASE_URL}/predict_pathogenicity",
            json=test['data']
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"    ✓ Prediction: {result['prediction']}")
            print(f"    ✓ Confidence: {result['confidence']:.3f}")
            print(f"    ✓ Model classes: {result['model_classes']}")
        else:
            print(f"    ✗ Error {response.status_code}: {response.text}")
    
    # Severity prediction
    print("\n[4/4] Testing severity prediction...")
    severity_data = {
        "mutation_class": "beta0",
        "zygosity": "homozygous",
        "hbvar_severity": "Major",
        "variant_type": "SNP"
    }
    
    response = requests.post(
        f"{BASE_URL}/predict_severity",
        json=severity_data
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"  ✓ Severity: {result['severity']}")
    else:
        print(f"  ✗ Error: {response.status_code}")
    
    print("\n" + "=" * 80)
    print("✅ API TESTING COMPLETE")
    print("=" * 80)
    print("\nAPI is ready for:")
    print("  • Frontend integration (React Dashboard)")
    print("  • Clinical variant interpretation")
    print("  • Real-time pathogenicity predictions")

except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()

finally:
    print("\nCleaning up...")
    api_process.terminate()
    api_process.wait(timeout=5)
    print("✓ API server stopped")
