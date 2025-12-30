"""
Context loader for TrueNAS Sentiment Analysis.
Loads SLA (always) and product-specific documentation based on case metadata.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from functools import lru_cache

try:
    from PyPDF2 import PdfReader
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False


# Get the context directory path
CONTEXT_DIR = Path(__file__).parent.parent.parent / "context"
PRODUCT_MAPPING_FILE = CONTEXT_DIR / "product-mapping.json"


class ContextLoader:
    """
    Loads and composes context from PDFs and configuration files.

    Usage:
        loader = ContextLoader()
        context = loader.get_context_for_case(asset_serial="A1-123456")
    """

    def __init__(self, context_dir: Optional[Path] = None):
        self.context_dir = context_dir or CONTEXT_DIR
        self.mapping = self._load_product_mapping()
        self._pdf_cache: Dict[str, str] = {}

    def _load_product_mapping(self) -> Dict:
        """Load the product mapping configuration."""
        mapping_file = self.context_dir / "product-mapping.json"
        if mapping_file.exists():
            with open(mapping_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def get_product_line_from_serial(self, serial: str) -> Optional[str]:
        """
        Determine product line from asset serial number.

        Args:
            serial: Asset serial number (e.g., "A1-123456")

        Returns:
            Product line name (e.g., "M-Series") or None if not matched
        """
        if not serial:
            return None

        # Clean up serial - handle multiple serials separated by space or +
        serials = re.split(r'[\s+]+', serial.strip())
        first_serial = serials[0] if serials else serial

        # Get serial prefixes from mapping
        prefixes = self.mapping.get("serial_prefixes", {})

        # Try to match prefix (e.g., "A1" from "A1-123456")
        for prefix, product_line in prefixes.items():
            if first_serial.upper().startswith(prefix.upper()):
                return product_line

        return None

    def get_product_line_from_series(self, series_letter: str) -> Optional[str]:
        """
        Determine product line from series letter (from Product Series column).

        Args:
            series_letter: Single letter like "F", "M", "H", "R"

        Returns:
            Product line name (e.g., "F-Series") or None if not matched
        """
        if not series_letter:
            return None

        letter = str(series_letter).strip().upper()
        series_mapping = self.mapping.get("series_letter_mapping", {})

        return series_mapping.get(letter)

    def get_product_line_from_model(self, model: str) -> Optional[str]:
        """
        Determine product line from product model (e.g., "F100-HA" -> "F-Series").

        Args:
            model: Product model string like "F100-HA", "M50", "H20-HA"

        Returns:
            Product line name (e.g., "F-Series") or None if not matched
        """
        if not model:
            return None

        model_str = str(model).strip().upper()
        if not model_str:
            return None

        # Extract first letter which indicates series
        first_letter = model_str[0]
        return self.get_product_line_from_series(first_letter)

    def extract_pdf_text(self, pdf_path: Path, max_chars: int = 50000) -> str:
        """
        Extract text content from a PDF file.

        Args:
            pdf_path: Path to the PDF file
            max_chars: Maximum characters to extract (to avoid token limits)

        Returns:
            Extracted text content
        """
        if not PDF_AVAILABLE:
            return f"[PDF extraction unavailable - install PyPDF2: {pdf_path.name}]"

        if not pdf_path.exists():
            return f"[PDF not found: {pdf_path.name}]"

        # Check cache
        cache_key = str(pdf_path)
        if cache_key in self._pdf_cache:
            return self._pdf_cache[cache_key]

        try:
            reader = PdfReader(pdf_path)
            text_parts = []
            total_chars = 0

            for page in reader.pages:
                page_text = page.extract_text() or ""
                if total_chars + len(page_text) > max_chars:
                    # Truncate to fit limit
                    remaining = max_chars - total_chars
                    text_parts.append(page_text[:remaining])
                    text_parts.append(f"\n[...truncated at {max_chars} chars...]")
                    break
                text_parts.append(page_text)
                total_chars += len(page_text)

            text = "\n".join(text_parts)
            self._pdf_cache[cache_key] = text
            return text

        except Exception as e:
            return f"[Error reading PDF {pdf_path.name}: {str(e)}]"

    def load_global_context(self) -> str:
        """
        Load context that should be included for all analyses.
        This includes the SLA and any other always-load documents.

        Returns:
            Combined text from all global context files
        """
        global_config = self.mapping.get("global_context", {})
        always_load = global_config.get("always_load", [])

        context_parts = []

        for filename in always_load:
            pdf_path = self.context_dir / filename
            if pdf_path.exists():
                context_parts.append(f"=== {filename.upper()} ===")
                context_parts.append(self.extract_pdf_text(pdf_path))
                context_parts.append("")

        return "\n".join(context_parts)

    def load_product_context(self, product_line: str) -> str:
        """
        Load context specific to a product line.

        Args:
            product_line: Product line name (e.g., "M-Series")

        Returns:
            Combined text from product-specific PDFs plus product metadata
        """
        product_info = self.mapping.get("product_lines", {}).get(product_line, {})

        if not product_info:
            return ""

        context_parts = []

        # Add product metadata as structured context
        context_parts.append(f"=== {product_line} PRODUCT INFORMATION ===")
        context_parts.append(f"Description: {product_info.get('description', 'N/A')}")
        context_parts.append(f"Target Use: {product_info.get('target_use', 'N/A')}")
        context_parts.append(f"Controller Type: {product_info.get('controller_type', 'N/A')}")
        context_parts.append(f"Storage Type: {product_info.get('storage_type', 'N/A')}")
        context_parts.append(f"Models: {', '.join(product_info.get('models', []))}")
        context_parts.append(f"Support Priority: {product_info.get('support_priority', 'N/A')}")

        # Key features
        features = product_info.get('key_features', [])
        if features:
            context_parts.append(f"\nKey Features:")
            for feature in features:
                context_parts.append(f"  - {feature}")

        # Common issues
        issues = product_info.get('common_issues', [])
        if issues:
            context_parts.append(f"\nCommon Issues to Watch For:")
            for issue in issues:
                context_parts.append(f"  - {issue}")

        context_parts.append("")

        # Load product-specific PDFs
        pdf_files = product_info.get('pdf_files', [])
        for filename in pdf_files:
            pdf_path = self.context_dir / filename
            if pdf_path.exists():
                context_parts.append(f"=== {filename.upper()} ===")
                context_parts.append(self.extract_pdf_text(pdf_path, max_chars=30000))
                context_parts.append("")

        return "\n".join(context_parts)

    def load_severity_context(self, product_line: str) -> str:
        """
        Load severity-specific guidance for a product line.

        Args:
            product_line: Product line name

        Returns:
            Severity handling guidance
        """
        severity_info = self.mapping.get("severity_by_product", {}).get(product_line, {})

        if not severity_info:
            return ""

        lines = [f"=== {product_line} SEVERITY HANDLING ==="]
        for severity_type, guidance in severity_info.items():
            lines.append(f"  {severity_type}: {guidance}")

        return "\n".join(lines)

    def load_support_considerations(self, product_line: str) -> str:
        """
        Load support considerations based on product characteristics.

        Args:
            product_line: Product line name

        Returns:
            Relevant support considerations
        """
        product_info = self.mapping.get("product_lines", {}).get(product_line, {})
        considerations = self.mapping.get("support_considerations", {})

        if not product_info or not considerations:
            return ""

        lines = ["=== SUPPORT CONSIDERATIONS ==="]

        # Controller type considerations
        controller_type = product_info.get("controller_type", "")
        if "Dual" in controller_type:
            for item in considerations.get("dual_controller", []):
                lines.append(f"  - {item}")
        elif "Single" in controller_type:
            for item in considerations.get("single_controller", []):
                lines.append(f"  - {item}")

        # Storage type considerations
        storage_type = product_info.get("storage_type", "")
        if "flash" in storage_type.lower() or "nvme" in storage_type.lower():
            for item in considerations.get("flash_storage", []):
                lines.append(f"  - {item}")
        if "hybrid" in storage_type.lower():
            for item in considerations.get("hybrid_storage", []):
                lines.append(f"  - {item}")

        return "\n".join(lines)

    def get_context_for_case(
        self,
        asset_serial: Optional[str] = None,
        product_line: Optional[str] = None,
        include_global: bool = True,
        max_total_chars: int = 80000
    ) -> Tuple[str, Optional[str]]:
        """
        Build complete context for a case.

        Args:
            asset_serial: Asset serial number to determine product
            product_line: Explicit product line (overrides serial detection)
            include_global: Whether to include SLA and global context
            max_total_chars: Maximum total context size

        Returns:
            Tuple of (combined_context_string, detected_product_line)
        """
        context_parts = []
        detected_product = product_line

        # Determine product line from serial if not provided
        if not detected_product and asset_serial:
            detected_product = self.get_product_line_from_serial(asset_serial)

        # Load global context (SLA, etc.) - always first
        if include_global:
            global_ctx = self.load_global_context()
            if global_ctx:
                context_parts.append(global_ctx)

        # Load product-specific context
        if detected_product:
            product_ctx = self.load_product_context(detected_product)
            if product_ctx:
                context_parts.append(product_ctx)

            severity_ctx = self.load_severity_context(detected_product)
            if severity_ctx:
                context_parts.append(severity_ctx)

            support_ctx = self.load_support_considerations(detected_product)
            if support_ctx:
                context_parts.append(support_ctx)

        # Combine and truncate if needed
        combined = "\n\n".join(context_parts)
        if len(combined) > max_total_chars:
            combined = combined[:max_total_chars] + "\n[...context truncated...]"

        return combined, detected_product


# Convenience functions for simpler usage
_default_loader: Optional[ContextLoader] = None


def get_loader() -> ContextLoader:
    """Get or create the default context loader."""
    global _default_loader
    if _default_loader is None:
        _default_loader = ContextLoader()
    return _default_loader


def load_context_for_case(
    asset_serial: Optional[str] = None,
    product_line: Optional[str] = None
) -> Tuple[str, Optional[str]]:
    """
    Load context for a specific case.

    Args:
        asset_serial: Asset serial number
        product_line: Explicit product line

    Returns:
        Tuple of (context_string, detected_product_line)
    """
    return get_loader().get_context_for_case(
        asset_serial=asset_serial,
        product_line=product_line
    )


def load_global_context() -> str:
    """Load global context (SLA, etc.)."""
    return get_loader().load_global_context()


def get_product_line_from_serial(serial: str) -> Optional[str]:
    """Get product line from serial number."""
    return get_loader().get_product_line_from_serial(serial)


def get_product_line_from_series(series_letter: str) -> Optional[str]:
    """Get product line from series letter (e.g., 'F' -> 'F-Series')."""
    return get_loader().get_product_line_from_series(series_letter)


def get_product_line_from_model(model: str) -> Optional[str]:
    """Get product line from product model (e.g., 'F100-HA' -> 'F-Series')."""
    return get_loader().get_product_line_from_model(model)
