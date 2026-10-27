"""
prism_core/survey/inject_rag_memory.py

Helper module to load and inject simulated storefront memory into the PRISM RAG pipeline:
- Ingests specs, defect clusters, and customer verbatims from Amazon, Flipkart, JioMart, Brand, and Steam.
- Prepares documents for embedding in pgvector / ChromaDB or direct in-memory LLM prompt context injection.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


MEMORY_FILE_PATH = Path(__file__).resolve().parents[3] / "data" / "rag_simulation_memory.json"


def load_simulation_rag_memory(path: Optional[Path] = None) -> Dict[str, Any]:
    """Load the simulation RAG memory bank from JSON."""
    target_path = path or MEMORY_FILE_PATH
    if not target_path.exists():
        # Fallback check in simulation directory
        alt_path = Path("d:/Prism/PRISM FRONTEND/simulation/rag_simulation_memory.json")
        if alt_path.exists():
            target_path = alt_path
        else:
            raise FileNotFoundError(f"RAG memory file not found at {target_path}")

    with open(target_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_context_for_product(product_id: str, memory_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Extract technical specs, defect clusters, and verified customer verbatims
    for a specific product (or 'steam_games') across all simulated channels.
    """
    data = memory_data or load_simulation_rag_memory()
    chunks = data.get("rag_memory_chunks", [])

    specs = [c for c in chunks if c.get("product_id") == product_id and c.get("type") == "technical_spec"]
    clusters = [c for c in chunks if c.get("product_id") == product_id and c.get("type") == "defect_cluster"]
    verbatims = [c for c in chunks if c.get("product_id") == product_id and c.get("type") == "customer_verbatim"]
    diagnostic_trees = [c for c in chunks if c.get("product_id") == product_id and c.get("type") == "diagnostic_survey_template"]

    return {
        "product_id": product_id,
        "specs": specs[0]["content"] if specs else "",
        "defect_clusters": [c["content"] for c in clusters],
        "evidence_quotes": [v["content"] for v in verbatims],
        "diagnostic_templates": [d["content"] for d in diagnostic_trees],
    }


def format_rag_prompt_context(product_id: str) -> str:
    """
    Formats high-signal RAG ground truth text to inject directly into
    system prompts (e.g. Gemini, OpenAI, Claude, or local LLM).
    """
    ctx = get_context_for_product(product_id)
    if not ctx["specs"]:
        return "No specific simulation memory found for this product ID."

    lines = [
        f"### GROUND TRUTH SPECIFICATIONS & ARCHITECTURE ({product_id}):",
        ctx["specs"],
        "",
        "### KNOWN DEFECT CLUSTERS & ROOT CAUSES (SIMULATION DATA):",
    ]
    for cluster in ctx["defect_clusters"]:
        lines.append(f"- {cluster}")

    lines.append("")
    lines.append("### REPRESENTATIVE CROSS-PLATFORM CUSTOMER VERBATIMS:")
    for quote in ctx["evidence_quotes"]:
        lines.append(f"- {quote}")

    return "\n".join(lines)


if __name__ == "__main__":
    memory = load_simulation_rag_memory()
    print(f"Loaded {len(memory.get('rag_memory_chunks', []))} RAG memory chunks across {len(memory.get('platforms', []))} platforms.")
    print("\nSample Prompt Injection Block for prod_001 (Horizon ANC):")
    print("-" * 60)
    print(format_rag_prompt_context("prod_001"))
