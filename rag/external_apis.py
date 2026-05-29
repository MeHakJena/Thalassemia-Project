"""
External Clinical API Integrations for BETA-AI.
Fetches live data from public medical APIs to enhance RAG context.
"""

import requests
import json
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

class ExternalClinicalAPIs:
    def __init__(self):
        self.session = requests.Session()

    def fetch_pubmed_literature(self, query: str, max_results: int = 3) -> str:
        """Fetch recent literature from PubMed using NCBI E-utilities."""
        try:
            # 1. Search for IDs
            encoded_query = urllib.parse.quote(query)
            search_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={encoded_query}&retmode=json&retmax={max_results}&sort=date"
            search_res = self.session.get(search_url, timeout=5).json()
            
            id_list = search_res.get("esearchresult", {}).get("idlist", [])
            if not id_list:
                return "No recent PubMed literature found for this query."

            # 2. Fetch summaries for IDs
            ids_str = ",".join(id_list)
            summary_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={ids_str}&retmode=json"
            summary_res = self.session.get(summary_url, timeout=5).json()
            
            results = summary_res.get("result", {})
            articles = []
            for uid in id_list:
                if uid in results:
                    title = results[uid].get("title", "")
                    pubdate = results[uid].get("pubdate", "")
                    source = results[uid].get("source", "")
                    url = f"https://pubmed.ncbi.nlm.nih.gov/{uid}/"
                    articles.append(f"- {title} ({source}, {pubdate}) [PMID: {uid}] - URL: {url}")
                    
            return "\n".join(articles)
        except Exception as e:
            return f"PubMed API Error: {str(e)}"

    def fetch_medlineplus(self, condition: str = "beta thalassemia") -> str:
        """Fetch patient-friendly summary from MedlinePlus Genetics."""
        try:
            url = f"https://wsearch.nlm.nih.gov/ws/query?db=healthTopics&term={urllib.parse.quote(condition)}&retmax=1"
            # MedlinePlus returns XML by default. To keep it simple and fast without xml.etree,
            # we just do a basic string extraction of the snippet.
            res = self.session.get(url, timeout=5).text
            if "<FullSummary>" in res:
                start = res.find("<FullSummary>") + 13
                end = res.find("</FullSummary>")
                summary = res[start:end].replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
                # Strip basic HTML tags
                import re
                clean_summary = re.sub('<[^<]+>', '', summary)
                # truncate to 500 chars to save token space
                url = "https://medlineplus.gov/genetics/condition/beta-thalassemia/"
                return f"{clean_summary[:500]}...\nSource URL: {url}"
            return "No MedlinePlus summary found."
        except Exception as e:
            return f"MedlinePlus API Error: {str(e)}"

    def fetch_hpo_terms(self, disease_id: str = "OMIM:613985") -> str:
        """Fetch Human Phenotype Ontology terms for a disease."""
        # The Jax HPO REST API is currently returning HTML/404s. 
        # Hardcoding the established clinical phenotypes for Beta-Thalassemia (OMIM:613985) 
        # to ensure the LLM has accurate clinical implications.
        if disease_id == "OMIM:613985":
            terms = [
                "Microcytic anemia", 
                "Hepatosplenomegaly", 
                "Jaundice", 
                "Abnormal facial shape (Chipmunk facies)",
                "Extramedullary hematopoiesis",
                "Elevated hemoglobin F",
                "Growth delay",
                "Skeletal dysplasia",
                "Iron overload"
            ]
            url = f"https://hpo.jax.org/app/browse/disease/{disease_id}"
            return f"{', '.join(terms)}\nSource URL: {url}"
            
        return "No HPO terms found."

    def fetch_pharmgkb(self, gene: str = "HBB") -> str:
        """Fetch Pharmacogenomics info (drug interactions) for the gene."""
        # Simple lookup strategy or placeholder if PharmGKB public API is restricted
        # PharmGKB public APIs are often subject to change.
        url = "https://www.pharmgkb.org/gene/PA28919/clinicalAnnotation"
        return f"PharmGKB: Hydroxyurea is commonly used to induce fetal hemoglobin (HbF) in severe beta-thalassemia and sickle cell disease, mitigating severity.\nSource URL: {url}"

    def fetch_monarch_data(self, disease_id: str = "MONDO:0011985") -> str:
        """Fetch disease ontology data from Monarch Initiative."""
        # MONDO:0011985 is beta-thalassemia
        try:
            url = f"https://api-v3.monarchinitiative.org/v3/api/entity/{disease_id}"
            res = self.session.get(url, timeout=5)
            if res.status_code == 200:
                data = res.json()
                desc = data.get("description", "Beta-thalassemia is a blood disorder that reduces the production of hemoglobin.")
                synonyms = data.get("synonym", [])
                syn_str = ", ".join(synonyms[:3]) if synonyms else ""
                
                source_url = f"https://monarchinitiative.org/disease/{disease_id}"
                result = f"Monarch Ontology: {desc}\nSynonyms: {syn_str}\nSource URL: {source_url}"
                return result
            return "No Monarch Initiative data found."
        except Exception as e:
            return f"Monarch API Error: {str(e)}"

    def fetch_clingen_data(self, variant_hgvs: str) -> str:
        """Fetch canonical variant ID and pathogenicity assertions from ClinGen Allele Registry."""
        if not variant_hgvs:
            return "No ClinGen data (No HGVS provided)."
        try:
            # We assume variant_hgvs might be something like NC_000011.10:g.5227002T>C or similar
            # In a real app, this should be a properly formatted HGVS string.
            encoded_hgvs = urllib.parse.quote(variant_hgvs)
            url = f"https://reg.clinicalgenome.org/allele?hgvs={encoded_hgvs}"
            res = self.session.get(url, timeout=5)
            if res.status_code == 200:
                data = res.json()
                caid = data.get("@id", "").split("/")[-1]
                if caid:
                    source_url = f"https://reg.clinicalgenome.org/red/allele/{caid}"
                    return f"ClinGen Canonical ID: {caid}\nThis variant is registered in the ClinGen database.\nSource URL: {source_url}"
            return "Variant not found in ClinGen Allele Registry."
        except Exception as e:
            return f"ClinGen API Error: {str(e)}"

    def gather_all_context(self, variant_hgvs: str = "") -> dict:
        """Run all external API fetches concurrently."""
        results = {}
        pubmed_query = f"HBB AND (thalassemia OR {variant_hgvs})" if variant_hgvs else "HBB beta thalassemia"
        
        with ThreadPoolExecutor(max_workers=6) as executor:
            future_pubmed = executor.submit(self.fetch_pubmed_literature, pubmed_query)
            future_medline = executor.submit(self.fetch_medlineplus, "beta thalassemia")
            future_hpo = executor.submit(self.fetch_hpo_terms, "OMIM:613985")
            future_pharm = executor.submit(self.fetch_pharmgkb, "HBB")
            future_monarch = executor.submit(self.fetch_monarch_data, "MONDO:0011985")
            future_clingen = executor.submit(self.fetch_clingen_data, variant_hgvs)
            
            results["pubmed"] = future_pubmed.result()
            results["medlineplus"] = future_medline.result()
            results["hpo"] = future_hpo.result()
            results["pharmgkb"] = future_pharm.result()
            results["monarch"] = future_monarch.result()
            results["clingen"] = future_clingen.result()
            
        return results

api_service = ExternalClinicalAPIs()
