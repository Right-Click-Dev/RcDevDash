"""
Proposal Parser - Extract project phases from PDF proposals using Claude AI
"""

import json
import os


def extract_text_from_pdf(filepath):
    """Extract text content from a PDF file"""
    try:
        import pdfplumber
        text = ""
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text.strip()
    except ImportError:
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(filepath)
            text = ""
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            return text.strip()
        except ImportError:
            raise ImportError("Install pdfplumber or PyPDF2: pip install pdfplumber")


def parse_proposal(filepath):
    """
    Parse a proposal PDF and extract phases using Claude AI.

    Returns dict with:
        - phases: list of {name, description, amount, hours}
        - proposal_amount: total proposal amount (if found)
        - billing_client: client name (if found)
    """
    text = extract_text_from_pdf(filepath)
    if not text:
        return None

    # Truncate very long documents
    if len(text) > 50000:
        text = text[:50000] + "\n...[truncated]"

    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is not set. Add it to your .env file.")

    try:
        import anthropic
    except ImportError:
        raise ImportError("Install the anthropic package: pip install anthropic")

    client = anthropic.Anthropic(api_key=api_key)

    prompt = f"""Analyze this project proposal and extract the following information as JSON:

1. **phases**: A list of project phases/milestones. For each phase extract:
   - "name": Short phase name (e.g., "Discovery & Planning", "Design", "Development", "Testing & QA", "Launch")
   - "description": Brief description of what this phase includes
   - "amount": Dollar amount for this phase (0 if not specified)
   - "hours": Estimated hours for this phase (0 if not specified)

2. **proposal_amount**: The total proposal/contract amount as a number (0 if not found)

3. **billing_client**: The client/company name the proposal is for (null if not found)

Return ONLY valid JSON with no markdown formatting. Example:
{{"phases": [{{"name": "Phase 1 - Discovery", "description": "Requirements gathering and planning", "amount": 5000, "hours": 40}}], "proposal_amount": 25000, "billing_client": "Acme Corp"}}

Here is the proposal text:
---
{text}
---

Return ONLY the JSON object, nothing else."""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )

    response_text = message.content[0].text.strip()

    # Try to parse JSON from the response
    try:
        # Handle case where response might be wrapped in markdown code blocks
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            json_lines = []
            in_block = False
            for line in lines:
                if line.startswith("```"):
                    in_block = not in_block
                    continue
                if in_block:
                    json_lines.append(line)
            response_text = "\n".join(json_lines)

        result = json.loads(response_text)
        return result
    except json.JSONDecodeError:
        return None
