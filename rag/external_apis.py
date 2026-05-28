"""
External Clinical API Integrations for GeneTrustAI-Thal.
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
                    articles.append(f"- {title} ({source}, {pubdate}) [PMID: {uid}]")
                    
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
                return clean_summary[:500] + "..."
            return "No MedlinePlus summary found."
        except Exception as e:
            return f"MedlinePlus API Error: {str(e)}"

    def fetch_hpo_terms(self, disease_id: str = "OMIM:613985") -> str:
        """Fetch Human Phenotype Ontology terms for a disease."""
        # Beta-thalassemia is OMIM:613985 (Major)
        try:
            url = f"https://hpo.jax.org/api/hpo/disease/{disease_id}"
            res = self.session.get(url, timeout=5).json()
            cat_list = res.get("catTermsMap", [])
            terms = []
            for cat in cat_list:
                for term in cat.get("terms", []):
                    terms.append(term.get("ontologyId", {}).get("name", ""))
            
            # Return top 15 phenotypes to avoid context bloat
            if terms:
                return ", ".join(terms[:15])
            return "No HPO terms found."
        except Exception as e:
            return f"HPO API Error: {str(e)}"

    def fetch_pharmgkb(self, gene: str = "HBB") -> str:
        """Fetch Pharmacogenomics info (drug interactions) for the gene."""
        # Simple lookup strategy or placeholder if PharmGKB public API is restricted
        # PharmGKB public APIs are often subject to change.
        return "PharmGKB: Hydroxyurea is commonly used to induce fetal hemoglobin (HbF) in severe beta-thalassemia and sickle cell disease, mitigating severity."

    def gather_all_context(self, variant_hgvs: str = "") -> dict:
        """Run all external API fetches concurrently."""
        results = {}
        pubmed_query = f"HBB AND (thalassemia OR {variant_hgvs})" if variant_hgvs else "HBB beta thalassemia"
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_pubmed = executor.submit(self.fetch_pubmed_literature, pubmed_query)
            future_medline = executor.submit(self.fetch_medlineplus, "beta thalassemia")
            future_hpo = executor.submit(self.fetch_hpo_terms, "OMIM:613985")
            future_pharm = executor.submit(self.fetch_pharmgkb, "HBB")
            
            results["pubmed"] = future_pubmed.result()
            results["medlineplus"] = future_medline.result()
            results["hpo"] = future_hpo.result()
            results["pharmgkb"] = future_pharm.result()
            
        return results

api_service = ExternalClinicalAPIs()
