import os
import glob

dirs_to_search = ['frontend/src', 'api', 'rag', 'dashboard', 'etl', '.']
files_to_process = []

for d in dirs_to_search:
    if d == '.':
        files_to_process.extend(glob.glob('*.md'))
        files_to_process.extend(glob.glob('*.py'))
    else:
        for root, _, files in os.walk(d):
            for f in files:
                if f.endswith('.js') or f.endswith('.jsx') or f.endswith('.py') or f.endswith('.md') or f.endswith('.html'):
                    files_to_process.append(os.path.join(root, f))

files_to_process = list(set(files_to_process))

replacements = [
    ("GeneTrustAI-Thal", "BETA-AI"),
    ("GeneTrustAI Assistant", "BETA-AI Assistant"),
    ("GeneTrustAI", "BETA-AI"),
    ("GeneTrust AI", "BETA-AI"),
    ("GeneTrust", "BETA-AI")
]

for filepath in files_to_process:
    if os.path.isfile(filepath) and not 'rename_tool.py' in filepath:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        new_content = content
        for old, new in replacements:
            new_content = new_content.replace(old, new)
            
        if new_content != content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Updated {filepath}")

