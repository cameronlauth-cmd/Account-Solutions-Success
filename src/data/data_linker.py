"""
Data Linker for Account Solutions Success.

Links Opportunities, Deployments, and Support Cases via Order Number
to create a unified view of the customer journey.
"""

from typing import List, Dict, Tuple, Any, Optional
from collections import defaultdict

from .models import (
    Opportunity,
    Deployment,
    SupportCase,
    LinkedOrder,
    LinkSummary,
)


class LinkedDataStore:
    """
    Container for linked data with convenient access methods.
    """

    def __init__(
        self,
        orders: List[LinkedOrder],
        orphan_opportunities: List[Opportunity],
        orphan_deployments: List[Deployment],
        orphan_cases: List[SupportCase],
        summary: LinkSummary,
    ):
        self.orders = orders
        self.orphan_opportunities = orphan_opportunities
        self.orphan_deployments = orphan_deployments
        self.orphan_cases = orphan_cases
        self.summary = summary

        # Build lookup indexes
        self._order_by_number: Dict[str, LinkedOrder] = {
            o.order_number: o for o in orders
        }
        self._orders_by_account: Dict[str, List[LinkedOrder]] = defaultdict(list)
        for order in orders:
            self._orders_by_account[order.account_name].append(order)

    def get_order(self, order_number: str) -> Optional[LinkedOrder]:
        """Get a linked order by order number."""
        return self._order_by_number.get(order_number)

    def get_orders_by_account(self, account_name: str) -> List[LinkedOrder]:
        """Get all orders for an account."""
        return self._orders_by_account.get(account_name, [])

    def get_fully_linked_orders(self) -> List[LinkedOrder]:
        """Get all orders that have data from all three sources."""
        return [o for o in self.orders if o.is_fully_linked]

    def get_orders_with_support(self) -> List[LinkedOrder]:
        """Get all orders that have support cases."""
        return [o for o in self.orders if o.has_support_cases]

    @property
    def all_accounts(self) -> List[str]:
        """Get list of all unique account names."""
        return list(self._orders_by_account.keys())

    @property
    def matched_orders(self) -> int:
        """Number of orders with at least one data source."""
        return len(self.orders)


def _normalize_order_number(order_num: str) -> str:
    """
    Normalize order number for matching.

    Handles variations like leading zeros, spaces, etc.
    """
    if not order_num:
        return ""

    # Strip whitespace
    normalized = str(order_num).strip()

    # Remove common prefixes
    for prefix in ["ORD-", "ORD", "ORDER-", "ORDER", "#"]:
        if normalized.upper().startswith(prefix):
            normalized = normalized[len(prefix):]

    # Remove leading zeros if it's numeric
    try:
        if normalized.isdigit():
            normalized = str(int(normalized))
    except:
        pass

    return normalized.upper()


def link_data_sources(
    opportunities: List[Opportunity],
    deployments: List[Deployment],
    support_cases: List[SupportCase],
    console_output: Any = None,
) -> LinkedDataStore:
    """
    Link all data sources via Order Number.

    Creates LinkedOrder objects for each unique order number found
    across all sources, linking related Opportunities, Deployments,
    and Support Cases.

    Args:
        opportunities: List of loaded Opportunity objects
        deployments: List of loaded Deployment objects
        support_cases: List of loaded SupportCase objects
        console_output: Optional output handler with stream_message() method

    Returns:
        LinkedDataStore with linked orders and summary statistics
    """
    if console_output:
        console_output.stream_message("\nLinking data sources via Order Number...")

    # Build order number -> records maps
    opp_by_order: Dict[str, Opportunity] = {}
    deploy_by_order: Dict[str, List[Deployment]] = defaultdict(list)
    cases_by_order: Dict[str, List[SupportCase]] = defaultdict(list)

    # Track orphans (records without valid order numbers)
    orphan_opps: List[Opportunity] = []
    orphan_deploys: List[Deployment] = []
    orphan_cases: List[SupportCase] = []

    # Index opportunities
    for opp in opportunities:
        norm_order = _normalize_order_number(opp.order_number)
        if norm_order:
            opp_by_order[norm_order] = opp
        else:
            orphan_opps.append(opp)

    # Index deployments
    for deploy in deployments:
        norm_order = _normalize_order_number(deploy.order_number)
        if norm_order:
            deploy_by_order[norm_order].append(deploy)
        else:
            orphan_deploys.append(deploy)

    # Index support cases
    for case in support_cases:
        norm_order = _normalize_order_number(case.order_number)
        if norm_order:
            cases_by_order[norm_order].append(case)
        else:
            orphan_cases.append(case)

    # Collect all unique order numbers
    all_order_numbers = set()
    all_order_numbers.update(opp_by_order.keys())
    all_order_numbers.update(deploy_by_order.keys())
    all_order_numbers.update(cases_by_order.keys())

    if console_output:
        console_output.stream_message(f"  Found {len(all_order_numbers)} unique order numbers")

    # Create linked orders
    linked_orders: List[LinkedOrder] = []

    for order_num in all_order_numbers:
        opp = opp_by_order.get(order_num)
        deploys = deploy_by_order.get(order_num, [])
        cases = cases_by_order.get(order_num, [])

        # Determine account name (prefer opportunity, then deployment, then case)
        account_name = "Unknown"
        if opp:
            account_name = opp.account_name
        elif deploys:
            account_name = deploys[0].account_name
        elif cases:
            account_name = cases[0].account_name

        linked = LinkedOrder(
            order_number=order_num,
            account_name=account_name,
            opportunity=opp,
            deployments=deploys,
            support_cases=cases,
        )

        linked_orders.append(linked)

    # Calculate summary statistics
    summary = LinkSummary(
        total_orders=len(linked_orders),
        orders_with_opportunity=sum(1 for o in linked_orders if o.has_opportunity),
        orders_with_deployment=sum(1 for o in linked_orders if o.has_deployments),
        orders_with_support=sum(1 for o in linked_orders if o.has_support_cases),
        fully_linked_orders=sum(1 for o in linked_orders if o.is_fully_linked),
        orphan_opportunities=len(orphan_opps),
        orphan_deployments=len(orphan_deploys),
        orphan_cases=len(orphan_cases),
        total_opportunities=len(opportunities),
        total_deployments=len(deployments),
        total_cases=len(support_cases),
    )

    if console_output:
        console_output.stream_message(summary.summary())

    return LinkedDataStore(
        orders=linked_orders,
        orphan_opportunities=orphan_opps,
        orphan_deployments=orphan_deploys,
        orphan_cases=orphan_cases,
        summary=summary,
    )


def load_and_link_all_sources(
    opportunities_path: str,
    deployments_path: str,
    support_path: str,
    console_output: Any = None,
) -> LinkedDataStore:
    """
    Convenience function to load all sources and link them.

    Args:
        opportunities_path: Path to opportunities Excel file
        deployments_path: Path to deployments Excel file
        support_path: Path to support cases Excel file
        console_output: Optional output handler

    Returns:
        LinkedDataStore with all data loaded and linked
    """
    from .opportunity_loader import load_opportunities
    from .deployment_loader import load_deployments
    from .case_loader import load_support_cases

    if console_output:
        console_output.stream_message("Loading all data sources...")

    # Load each source
    opps = load_opportunities(opportunities_path, console_output)
    deploys = load_deployments(deployments_path, console_output)
    cases = load_support_cases(support_path, console_output=console_output)

    # Link them
    return link_data_sources(opps, deploys, cases, console_output)
