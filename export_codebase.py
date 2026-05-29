import os
from pathlib import Path

def export_codebase(output_file="project_codebase.txt"):
    base_dir = Path(__file__).resolve().parent
    
    # Extensions to include
    valid_extensions = {".py", ".js", ".jsx", ".css", ".html", ".md", ".json", ".csv"}
    
    # Directories to completely ignore (to save tokens)
    ignore_dirs = {"node_modules", ".git", "__pycache__", "chroma_db", ".pytest_cache", "dist", "build"}
    
    # Specific files to ignore (like large datasets or models)
    ignore_files = {"package-lock.json", "master_hbb_dataset.csv", "synthetic_corrupted_vcf.csv"}
    
    with open(output_file, "w", encoding="utf-8") as outfile:
        outfile.write("=== GENETRUST AI: FULL CODEBASE EXPORT ===\n\n")
        
        for root, dirs, files in os.walk(base_dir):
            # Remove ignored directories from traversal
            dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith('.')]
            
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                
                # Skip if not a valid extension or if it's a massive file
                if ext not in valid_extensions or file in ignore_files:
                    continue
                    
                file_path = Path(root) / file
                rel_path = file_path.relative_to(base_dir)
                
                outfile.write(f"\n\n{'='*80}\n")
                outfile.write(f"FILE: {rel_path}\n")
                outfile.write(f"{'='*80}\n\n")
                
                try:
                    with open(file_path, "r", encoding="utf-8") as infile:
                        content = infile.read()
                        
                        # Truncate very long files (e.g. large JSON dumps) to save tokens, except for code
                        if ext == ".json" and len(content) > 10000:
                            outfile.write(content[:5000] + "\n\n... [TRUNCATED FOR LENGTH] ...\n")
                        else:
                            outfile.write(content)
                except Exception as e:
                    outfile.write(f"[Error reading file: {e}]\n")
                    
    print(f"✅ Successfully exported codebase to {output_file}")
    
if __name__ == "__main__":
    export_codebase()
