"""
Metrics Package for Account Solutions Success.

Provides multi-dimensional metrics aggregation across:
- Products (F-Series, M-Series, H-Series, R-Series)
- Accounts (customer-level health and performance)
- Use Cases (workload-specific performance)
- Service Teams (deployment effectiveness)
"""

from .product_metrics import (
    ProductMetrics,
    calculate_product_metrics,
    calculate_all_product_metrics,
)

from .account_metrics import (
    AccountMetrics,
    calculate_account_metrics,
    calculate_all_account_metrics,
)

from .usecase_metrics import (
    UseCaseMetrics,
    calculate_usecase_metrics,
    calculate_all_usecase_metrics,
)

from .service_metrics import (
    ServiceMetrics,
    calculate_service_metrics,
    compare_service_vs_self_deploy,
)

__all__ = [
    # Product
    "ProductMetrics",
    "calculate_product_metrics",
    "calculate_all_product_metrics",
    # Account
    "AccountMetrics",
    "calculate_account_metrics",
    "calculate_all_account_metrics",
    # Use Case
    "UseCaseMetrics",
    "calculate_usecase_metrics",
    "calculate_all_usecase_metrics",
    # Service
    "ServiceMetrics",
    "calculate_service_metrics",
    "compare_service_vs_self_deploy",
]
