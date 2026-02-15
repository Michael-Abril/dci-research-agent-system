"""
Automated document acquisition for the DCI Research Agent System.

Downloads research papers from multiple sources with ZERO manual intervention:
  1. arXiv API — search by DCI author names and CBDC/crypto keywords
  2. Semantic Scholar API — find open-access PDFs by DCI researchers
  3. GitHub (mit-dci/*) — pull READMEs and documentation
  4. IACR ePrint — cryptography papers (RSS + search)
  5. Known paper URLs — direct download of key DCI publications

Usage:
    python scripts/download_documents.py              # download everything
    python scripts/download_documents.py --source arxiv   # only arXiv
    python scripts/download_documents.py --source github  # only GitHub docs
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DOCS_DIR = settings.paths.documents_dir

# Rate limiting
def _sleep(seconds: float = 1.0):
    time.sleep(seconds)

def _safe_filename(text: str, max_len: int = 80) -> str:
    """Sanitize a string for use as a filename."""
    cleaned = re.sub(r'[^\w\s\-.]', '', text)
    cleaned = re.sub(r'\s+', '_', cleaned.strip())
    return cleaned[:max_len]

def _download_pdf(url: str, filepath: Path) -> bool:
    """Download a PDF from a URL. Returns True on success."""
    if filepath.exists():
        logger.info("  Already exists: %s", filepath.name)
        return True
    try:
        resp = requests.get(url, timeout=60, headers={
            "User-Agent": "DCIResearchAgent/1.0 (MIT DCI research tool)"
        })
        if resp.status_code == 200 and len(resp.content) > 1000:
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_bytes(resp.content)
            logger.info("  Downloaded: %s (%.1f KB)", filepath.name, len(resp.content) / 1024)
            return True
        else:
            logger.warning("  Failed to download %s (HTTP %d, %d bytes)", url, resp.status_code, len(resp.content))
            return False
    except Exception as e:
        logger.warning("  Download error for %s: %s", url, e)
        return False


# ═══════════════════════════════════════════════════════════════════════
# SOURCE 1: arXiv API
# ═══════════════════════════════════════════════════════════════════════

# DCI researchers to search for
DCI_AUTHORS = [
    "Neha Narula",
    "Madars Virza",
    "Tadge Dryja",
    "Thaddeus Dryja",
    "James Lovejoy",
    "Brandon Arvanaghi",
    "Rabi Prasad Padhy",
]

# Keywords for DCI research areas
ARXIV_QUERIES = [
    'ti:"central bank digital currency" AND (au:narula OR au:virza OR au:dryja)',
    'ti:CBDC AND au:MIT',
    'ti:utreexo',
    'ti:"weak sentinel"',
    'ti:OpenCBDC',
    'abs:"digital currency initiative"',
    'ti:"payment token" AND abs:interoperability',
    'ti:stablecoin AND abs:"treasury market"',
]

# Domain classification based on keywords in title/abstract
def _classify_domain(title: str, abstract: str) -> str:
    text = (title + " " + abstract).lower()
    if any(kw in text for kw in ["cbdc", "hamilton", "opencbdc", "parsec", "central bank digital"]):
        return "cbdc"
    if any(kw in text for kw in ["privacy", "zero-knowledge", "zkp", "sentinel", "zerocash", "anonymous"]):
        return "privacy"
    if any(kw in text for kw in ["stablecoin", "genius act", "treasury", "redemption", "par value"]):
        return "stablecoins"
    if any(kw in text for kw in ["bitcoin", "utreexo", "fee estimation", "coinjoin", "utxo", "lightning"]):
        return "bitcoin"
    if any(kw in text for kw in ["payment token", "kinexys", "programmab", "interoperab"]):
        return "payment_tokens"
    return "general"


def download_from_arxiv() -> List[Dict[str, Any]]:
    """Search arXiv for DCI-related papers and download PDFs."""
    logger.info("=== Downloading from arXiv ===")

    try:
        import arxiv
    except ImportError:
        logger.error("arxiv package not installed. Run: pip install arxiv")
        return []

    client = arxiv.Client(page_size=50, delay_seconds=3.0, num_retries=3)
    downloaded = []
    seen_ids = set()

    # Search by DCI author names
    for author in DCI_AUTHORS:
        query = f'au:"{author}"'
        logger.info("Searching arXiv: %s", query)
        search = arxiv.Search(query=query, max_results=30, sort_by=arxiv.SortCriterion.SubmittedDate)

        try:
            for result in client.results(search):
                if result.entry_id in seen_ids:
                    continue
                seen_ids.add(result.entry_id)

                domain = _classify_domain(result.title, result.summary)
                filename = _safe_filename(result.title) + ".pdf"
                filepath = DOCS_DIR / domain / filename

                if _download_pdf(result.pdf_url, filepath):
                    downloaded.append({
                        "title": result.title,
                        "authors": [a.name for a in result.authors],
                        "year": result.published.year if result.published else None,
                        "domain": domain,
                        "source": "arxiv",
                        "arxiv_id": result.entry_id,
                        "pdf_path": str(filepath),
                    })
                _sleep(1)
        except Exception as e:
            logger.warning("arXiv search failed for '%s': %s", query, e)

    # Search by topic keywords
    for query in ARXIV_QUERIES:
        logger.info("Searching arXiv: %s", query)
        search = arxiv.Search(query=query, max_results=20, sort_by=arxiv.SortCriterion.Relevance)

        try:
            for result in client.results(search):
                if result.entry_id in seen_ids:
                    continue
                seen_ids.add(result.entry_id)

                domain = _classify_domain(result.title, result.summary)
                filename = _safe_filename(result.title) + ".pdf"
                filepath = DOCS_DIR / domain / filename

                if _download_pdf(result.pdf_url, filepath):
                    downloaded.append({
                        "title": result.title,
                        "authors": [a.name for a in result.authors],
                        "year": result.published.year if result.published else None,
                        "domain": domain,
                        "source": "arxiv",
                        "arxiv_id": result.entry_id,
                        "pdf_path": str(filepath),
                    })
                _sleep(1)
        except Exception as e:
            logger.warning("arXiv search failed for '%s': %s", query, e)

    logger.info("arXiv: downloaded %d papers", len(downloaded))
    return downloaded


# ═══════════════════════════════════════════════════════════════════════
# SOURCE 2: Semantic Scholar API
# ═══════════════════════════════════════════════════════════════════════

S2_BASE = "https://api.semanticscholar.org/graph/v1"

def _s2_search_author(author_name: str) -> Optional[str]:
    """Find an author's Semantic Scholar ID."""
    try:
        resp = requests.get(
            f"{S2_BASE}/author/search",
            params={"query": author_name, "fields": "name,paperCount", "limit": 3},
            timeout=30,
        )
        if resp.status_code == 200:
            data = resp.json().get("data", [])
            if data:
                return data[0]["authorId"]
    except Exception as e:
        logger.warning("S2 author search failed: %s", e)
    return None


def download_from_semantic_scholar() -> List[Dict[str, Any]]:
    """Search Semantic Scholar for DCI researchers' papers with open-access PDFs."""
    logger.info("=== Downloading from Semantic Scholar ===")
    downloaded = []
    seen_titles = set()

    for author_name in DCI_AUTHORS:
        logger.info("Searching Semantic Scholar: %s", author_name)
        author_id = _s2_search_author(author_name)
        if not author_id:
            continue
        _sleep(1.5)

        try:
            resp = requests.get(
                f"{S2_BASE}/author/{author_id}/papers",
                params={
                    "fields": "title,year,abstract,openAccessPdf,externalIds",
                    "limit": 50,
                },
                timeout=30,
            )
            if resp.status_code != 200:
                continue

            for paper in resp.json().get("data", []):
                title = paper.get("title", "")
                if title in seen_titles or not title:
                    continue
                seen_titles.add(title)

                pdf_info = paper.get("openAccessPdf")
                if not pdf_info or not pdf_info.get("url"):
                    continue

                abstract = paper.get("abstract", "") or ""
                domain = _classify_domain(title, abstract)
                filename = _safe_filename(title) + ".pdf"
                filepath = DOCS_DIR / domain / filename

                if _download_pdf(pdf_info["url"], filepath):
                    downloaded.append({
                        "title": title,
                        "authors": [author_name],
                        "year": paper.get("year"),
                        "domain": domain,
                        "source": "semantic_scholar",
                        "pdf_path": str(filepath),
                    })
                _sleep(0.5)

        except Exception as e:
            logger.warning("S2 papers fetch failed for %s: %s", author_name, e)
        _sleep(1.5)

    # Also search by keywords
    keyword_queries = [
        "MIT digital currency initiative CBDC",
        "OpenCBDC transaction processor",
        "stablecoin plumbing treasury risk",
        "weak sentinel privacy auditability CBDC",
        "utreexo bitcoin accumulator",
    ]

    for query in keyword_queries:
        logger.info("Searching Semantic Scholar: %s", query)
        try:
            resp = requests.get(
                f"{S2_BASE}/paper/search",
                params={
                    "query": query,
                    "fields": "title,year,abstract,openAccessPdf",
                    "limit": 20,
                },
                timeout=30,
            )
            if resp.status_code != 200:
                continue

            for paper in resp.json().get("data", []):
                title = paper.get("title", "")
                if title in seen_titles or not title:
                    continue
                seen_titles.add(title)

                pdf_info = paper.get("openAccessPdf")
                if not pdf_info or not pdf_info.get("url"):
                    continue

                abstract = paper.get("abstract", "") or ""
                domain = _classify_domain(title, abstract)
                filename = _safe_filename(title) + ".pdf"
                filepath = DOCS_DIR / domain / filename

                if _download_pdf(pdf_info["url"], filepath):
                    downloaded.append({
                        "title": title,
                        "year": paper.get("year"),
                        "domain": domain,
                        "source": "semantic_scholar",
                        "pdf_path": str(filepath),
                    })
                _sleep(0.5)

        except Exception as e:
            logger.warning("S2 keyword search failed: %s", e)
        _sleep(1.5)

    logger.info("Semantic Scholar: downloaded %d papers", len(downloaded))
    return downloaded


# ═══════════════════════════════════════════════════════════════════════
# SOURCE 3: GitHub (mit-dci/* repos)
# ═══════════════════════════════════════════════════════════════════════

MIT_DCI_REPOS = [
    "mit-dci/opencbdc-tx",
    "mit-dci/utreexo",
    "mit-dci/lit",
    "mit-dci/dlc",
    "mit-dci/CryptoCurrency",
]

def download_from_github() -> List[Dict[str, Any]]:
    """Pull READMEs and documentation from mit-dci GitHub repos."""
    logger.info("=== Downloading from GitHub (mit-dci/*) ===")
    downloaded = []
    github_dir = DOCS_DIR / "general" / "github"
    github_dir.mkdir(parents=True, exist_ok=True)

    # First: discover all repos in the org
    try:
        resp = requests.get(
            "https://api.github.com/orgs/mit-dci/repos",
            params={"per_page": 100, "type": "public"},
            timeout=30,
        )
        if resp.status_code == 200:
            repos = [r["full_name"] for r in resp.json()]
            logger.info("Found %d repos in mit-dci org", len(repos))
            MIT_DCI_REPOS.clear()
            MIT_DCI_REPOS.extend(repos)
    except Exception as e:
        logger.warning("Could not list org repos: %s. Using default list.", e)

    for repo in MIT_DCI_REPOS:
        repo_name = repo.split("/")[1]
        repo_dir = github_dir / repo_name
        repo_dir.mkdir(parents=True, exist_ok=True)

        # Get README
        raw_url = f"https://raw.githubusercontent.com/{repo}/master/README.md"
        alt_url = f"https://raw.githubusercontent.com/{repo}/main/README.md"

        for url in [raw_url, alt_url]:
            try:
                resp = requests.get(url, timeout=30)
                if resp.status_code == 200 and len(resp.text) > 50:
                    readme_path = repo_dir / "README.md"
                    readme_path.write_text(resp.text)
                    downloaded.append({
                        "title": f"{repo_name} README",
                        "domain": "general",
                        "source": "github",
                        "path": str(readme_path),
                    })
                    logger.info("  %s: README saved", repo_name)
                    break
            except Exception:
                pass
        _sleep(0.3)

        # Look for docs/ directory
        try:
            resp = requests.get(
                f"https://api.github.com/repos/{repo}/contents/docs",
                timeout=30,
            )
            if resp.status_code == 200:
                for item in resp.json():
                    if item.get("type") == "file" and item["name"].endswith((".md", ".rst", ".txt")):
                        raw = f"https://raw.githubusercontent.com/{repo}/master/docs/{item['name']}"
                        try:
                            file_resp = requests.get(raw, timeout=30)
                            if file_resp.status_code == 200:
                                doc_path = repo_dir / item["name"]
                                doc_path.write_text(file_resp.text)
                                downloaded.append({
                                    "title": f"{repo_name}/{item['name']}",
                                    "domain": "general",
                                    "source": "github",
                                    "path": str(doc_path),
                                })
                                logger.info("  %s: %s saved", repo_name, item["name"])
                        except Exception:
                            pass
                        _sleep(0.3)
        except Exception:
            pass

    logger.info("GitHub: downloaded %d files", len(downloaded))
    return downloaded


# ═══════════════════════════════════════════════════════════════════════
# SOURCE 4: IACR ePrint (Cryptography papers)
# ═══════════════════════════════════════════════════════════════════════

# Known IACR paper IDs by DCI researchers
KNOWN_IACR_PAPERS = [
    # Zerocash
    {"id": "2014/349", "domain": "privacy", "title": "Zerocash_Decentralized_Anonymous_Payments"},
]

def download_from_iacr() -> List[Dict[str, Any]]:
    """Download cryptography papers from IACR ePrint."""
    logger.info("=== Downloading from IACR ePrint ===")
    downloaded = []

    # Download known papers
    for paper in KNOWN_IACR_PAPERS:
        url = f"https://eprint.iacr.org/{paper['id']}.pdf"
        filename = _safe_filename(paper["title"]) + ".pdf"
        filepath = DOCS_DIR / paper["domain"] / filename

        if _download_pdf(url, filepath):
            downloaded.append({
                "title": paper["title"],
                "domain": paper["domain"],
                "source": "iacr",
                "pdf_path": str(filepath),
            })
        _sleep(1)

    # Search IACR for DCI-related topics
    search_terms = ["digital currency auditability", "CBDC privacy", "central bank digital currency"]
    for term in search_terms:
        try:
            resp = requests.get(
                "https://eprint.iacr.org/search",
                params={"q": term},
                headers={"User-Agent": "DCIResearchAgent/1.0"},
                timeout=30,
            )
            if resp.status_code == 200:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(resp.text, "html.parser")
                for link in soup.find_all("a", href=True):
                    match = re.match(r"^/(\d{4})/(\d+)$", link["href"])
                    if match:
                        year, num = match.groups()
                        title = link.get_text(strip=True)[:80] or f"iacr_{year}_{num}"
                        pdf_url = f"https://eprint.iacr.org/{year}/{num}.pdf"
                        filename = _safe_filename(title) + ".pdf"
                        filepath = DOCS_DIR / "privacy" / filename

                        if _download_pdf(pdf_url, filepath):
                            downloaded.append({
                                "title": title,
                                "domain": "privacy",
                                "source": "iacr",
                                "pdf_path": str(filepath),
                            })
                        _sleep(1)
                        if len(downloaded) > 15:
                            break
        except Exception as e:
            logger.warning("IACR search failed for '%s': %s", term, e)

    logger.info("IACR: downloaded %d papers", len(downloaded))
    return downloaded


# ═══════════════════════════════════════════════════════════════════════
# SOURCE 5: Known direct URLs
# ═══════════════════════════════════════════════════════════════════════

KNOWN_PAPERS = [
    {
        "url": "https://www.usenix.org/system/files/nsdi23-lovejoy.pdf",
        "domain": "cbdc",
        "filename": "Hamilton_NSDI_2023.pdf",
    },
]

def download_known_papers() -> List[Dict[str, Any]]:
    """Download papers with known direct URLs."""
    logger.info("=== Downloading known papers ===")
    downloaded = []

    for paper in KNOWN_PAPERS:
        filepath = DOCS_DIR / paper["domain"] / paper["filename"]
        if _download_pdf(paper["url"], filepath):
            downloaded.append({
                "title": paper["filename"].replace(".pdf", "").replace("_", " "),
                "domain": paper["domain"],
                "source": "direct",
                "pdf_path": str(filepath),
            })

    logger.info("Known papers: downloaded %d", len(downloaded))
    return downloaded


# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Download DCI research documents automatically")
    parser.add_argument("--source", choices=["arxiv", "s2", "github", "iacr", "known", "all"],
                        default="all", help="Which source to download from")
    args = parser.parse_args()

    # Ensure directories exist
    for domain in ["cbdc", "privacy", "stablecoins", "payment_tokens", "bitcoin", "general"]:
        (DOCS_DIR / domain).mkdir(parents=True, exist_ok=True)

    all_downloaded = []
    source = args.source

    if source in ("all", "known"):
        all_downloaded.extend(download_known_papers())
    if source in ("all", "arxiv"):
        all_downloaded.extend(download_from_arxiv())
    if source in ("all", "s2"):
        all_downloaded.extend(download_from_semantic_scholar())
    if source in ("all", "github"):
        all_downloaded.extend(download_from_github())
    if source in ("all", "iacr"):
        all_downloaded.extend(download_from_iacr())

    # Save manifest
    manifest_path = DOCS_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(all_downloaded, indent=2))

    # Summary
    logger.info("=" * 60)
    logger.info("DOWNLOAD COMPLETE")
    logger.info("Total documents: %d", len(all_downloaded))
    by_domain = {}
    for doc in all_downloaded:
        d = doc.get("domain", "unknown")
        by_domain[d] = by_domain.get(d, 0) + 1
    for domain, count in sorted(by_domain.items()):
        logger.info("  %s: %d", domain, count)
    logger.info("Manifest saved to: %s", manifest_path)


if __name__ == "__main__":
    main()
