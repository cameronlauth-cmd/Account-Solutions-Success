# Account Solutions Success - Full Architecture Plan

## Vision
Transform from case sentiment analysis → **Product & Service Performance Analytics Platform**

## Data Architecture

```
OPPORTUNITY (Salesforce Export)
    │
    │ Order Number (1:N)
    ▼
DEPLOYMENT CASE (Record Type: Deployment)
    │
    │ Order Number
    ▼
SUPPORT CASE (Record Type: Support)
```

**Primary Key:** Order Number (links all three sources)

## Sample Data Column Mappings

### Support Cases (`Account AI Email Body*.xlsx`)
| Col | Field | Notes |
|-----|-------|-------|
| A | Case Number | Primary ID |
| C | Account Name | Customer |
| D | Case Owner | Support rep |
| E | Case Age Days | Duration |
| F | Severity | S1-S4 |
| G | Text Body | Message content |
| H | From Address | Sender |
| I | Product Series | F/M/H/R |
| J | Case Reason | Category |
| K | Product Model | Specific model |
| L | Support Level | Gold/Silver/Bronze |
| M | Message Date | Timestamp |
| N | Status | Open/Closed |
| O | Serial Number | Asset ID |
| **P** | **Order Number** | **Link key** |

### Opportunities (`Ai Opportunities Correlation*.xlsx`)
| Col | Field | Notes |
|-----|-------|-------|
| A | Owner Role | Sales role |
| C | Opportunity Owner | Sales rep |
| D | Account Name | Customer |
| E | Opportunity Name | Deal name |
| F | Fiscal Period | Quarter |
| G | Amount | Deal value |
| H | Close Date | Won date |
| I | Created Date | Start date |
| J | Next Step | Action |
| K | Lead Source | Origin |
| L | Type | Deal type |
| M | Products Quoted | All products |
| N | Primary Product | Main product |
| O-P | System Model | Hardware model |
| **Q** | **Order Number** | **Link key** |
| **R** | **Business Need** | Customer requirement |
| **S** | **Primary Use Case** | Workload type |
| **T** | **Pain Points** | Customer challenges |

### Deployments (`PS Deploy*.xlsx`)
Same structure as Support Cases (columns A-P, including Order Number)

## 4-Layer Analysis Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 4: EVALUATION (Sonnet)                                   │
│  Cross-correlate: expectations vs reality, churn risk           │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 3: SUPPORT     │  LAYER 2: DEPLOYMENT  │  LAYER 1: OPP  │
│  (Enhanced)           │  (NEW)                │  (NEW)          │
│  - Field performance  │  - Install success    │  - What sold    │
│  - TTR, escalations   │  - Service vs Self    │  - Use case     │
│  - Repeat issues      │  - Deploy score 0-100 │  - Expectations │
└───────────────────────┴───────────────────────┴─────────────────┘
```

## 3 Output Views

1. **Product-centric:** How is F-Series/M60 performing across all customers?
2. **Account-centric:** How is ACME Corp's entire deployment performing?
3. **Use-case-centric:** How do products perform in video editing vs backup?

## New Module Structure

```
src/
├── data/                           # NEW PACKAGE
│   ├── models.py                   # Dataclass definitions
│   ├── opportunity_loader.py       # Parse Opportunity Excel
│   ├── deployment_loader.py        # Parse Deployment Cases
│   ├── case_loader.py              # Renamed from data_loader.py
│   ├── data_linker.py              # Order Number correlation
│   └── data_store.py               # Unified data access
│
├── analysis/
│   ├── layers/                     # NEW PACKAGE
│   │   ├── opportunity_layer.py    # AI opportunity analysis
│   │   ├── deployment_layer.py     # AI deployment analysis
│   │   ├── support_layer.py        # Refactored from claude_analysis.py
│   │   └── evaluation_layer.py     # Cross-layer AI correlation
│   │
│   ├── metrics/                    # NEW PACKAGE
│   │   ├── product_metrics.py      # Product-centric calculations
│   │   ├── account_metrics.py      # Enhanced from scoring.py
│   │   ├── usecase_metrics.py      # Use-case aggregations
│   │   └── service_metrics.py      # Service team effectiveness
│
├── dashboard/
│   ├── pages/
│   │   ├── views/                  # NEW: View-specific pages
│   │   │   ├── product_view.py
│   │   │   ├── account_view.py
│   │   │   └── usecase_view.py
│   │   ├── 6_Opportunities.py      # NEW
│   │   ├── 7_Deployments.py        # NEW
│   │   └── 8_Service_Metrics.py    # NEW
```

## Key Metrics

| Metric | Description |
|--------|-------------|
| Deployment Success Rate | % deployments scoring >70 |
| Support Intensity | Cases per deployed unit |
| Repeat Issue Rate | % cases that are repeats |
| Time to Resolution | Avg days to close |
| Escalation Rate | Escalations per case |
| Service Value-Add | Service Team vs Self-Deploy delta |
| Field Failure Rate | Hardware failures per unit |
| Journey Health | 0-100 cross-layer score |

## Testing Strategy

**Gate-based validation:** Each phase has testing checkpoints that must pass before proceeding.

| Phase | Checkpoint | Key Validation |
|-------|------------|----------------|
| 1 | 1A: Loaders | Each file type loads, Order Number populated |
| 1 | 1B: Linking | Order Numbers correlate across sources, <50% orphans |
| 2 | 2A: Layer Access | Each layer can access its linked data |
| 2 | 2B: Cross-Layer | Evaluation layer sees all three sources |
| 3 | 3: Metrics | Aggregations consistent across views |
| 4 | 4: Pipeline | End-to-end produces all expected outputs |

**Sample Data:** Use files in `Account-Analysis-Reports/` for all tests.



## Git Commit Strategy

**Commit after each phase passes all checkpoints:**

| Phase | Commit Message | When to Commit |
|-------|----------------|----------------|
| 1 | \ | After Checkpoints 1A + 1B pass |
| 2 | \ | After Checkpoints 2A + 2B pass |
| 3 | \ | After Checkpoint 3 passes |
| 4 | \ | After Checkpoint 4 passes |
| 5 | \ | After dashboard pages work |
| 6 | \ | After reports work |

**Rules:**
- Never commit broken code - all checkpoints must pass first
- Each commit should be a working, testable increment
- Use conventional commit format: 
## Implementation Phases

### Phase 1: Data Foundation [COMPLETED]
- Create `src/data/` package
- `opportunity_loader.py` - parse Salesforce Opportunity export
- `deployment_loader.py` - parse Deployment cases (Record Type filter)
- Enhance `case_loader.py` - add Order Number, repeat detection
- `data_linker.py` - correlate via Order Number

**Testing Checkpoint 1A - Individual Loaders:**
```python
# tests/test_data_loaders.py
def test_opportunity_loader():
    opps = load_opportunities("sample_opps.xlsx")
    assert len(opps) > 0
    assert all(o.order_number for o in opps)  # Order Number populated
    assert all(o.primary_use_case for o in opps)  # Use case extracted

def test_deployment_loader():
    deps = load_deployments("sample_deploys.xlsx")
    assert len(deps) > 0
    assert all(d.order_number for d in deps)

def test_case_loader():
    cases = load_cases("sample_cases.xlsx")
    assert len(cases) > 0
    assert all(c.order_number for c in cases)
```

**Testing Checkpoint 1B - Data Linking:**
```python
# tests/test_data_linking.py
def test_order_number_correlation():
    opps, deps, cases = load_all_sources(...)
    linked = link_data_sources(opps, deps, cases)

    # Verify linkage
    assert linked.matched_orders > 0
    assert linked.orphan_cases < len(cases) * 0.5  # <50% orphans

    # Verify bidirectional lookup
    for order in linked.orders:
        if order.opportunity:
            assert order.order_number in [o.order_number for o in opps]
        if order.deployments:
            for d in order.deployments:
                assert d.order_number == order.order_number

def test_link_summary_report():
    """Generate human-readable correlation report"""
    linked = link_data_sources(...)
    report = linked.summary()
    print(report)
    # Output:
    # Total Orders: 45
    # Orders with Opportunity: 42 (93%)
    # Orders with Deployment: 38 (84%)
    # Orders with Support Cases: 35 (78%)
    # Fully Linked (all 3): 30 (67%)
    # Orphan Cases (no order): 12
```

### Phase 2: New Analysis Layers
- `src/analysis/layers/` package
- `opportunity_layer.py` - Haiku analysis + scoring
- `deployment_layer.py` - Haiku analysis + 0-100 scoring + Sonnet timelines
- `support_layer.py` - refactor existing + add new fields
- `evaluation_layer.py` - Sonnet cross-correlation

**Testing Checkpoint 2A - Layer Analysis Access:**
```python
# tests/test_layer_analysis.py
def test_opportunity_layer_with_linked_data():
    linked = load_and_link_all_sources(...)

    # Can opportunity layer access its data?
    for order in linked.orders:
        if order.opportunity:
            result = analyze_opportunity(order.opportunity)
            assert result.use_case_extracted
            assert result.business_need_extracted
            assert 0 <= result.opportunity_score <= 100

def test_deployment_layer_inherits_opp_context():
    linked = load_and_link_all_sources(...)

    # Does deployment analysis have access to opportunity context?
    for order in linked.orders:
        if order.opportunity and order.deployments:
            dep_result = analyze_deployment(
                order.deployments[0],
                opportunity_context=order.opportunity
            )
            # Verify we can compare deployment to expectations
            assert dep_result.expectation_match is not None

def test_support_layer_inherits_deploy_context():
    linked = load_and_link_all_sources(...)

    # Does case analysis know about deployment history?
    for order in linked.orders:
        if order.deployments and order.support_cases:
            case_result = analyze_case(
                order.support_cases[0],
                deployment_context=order.deployments
            )
            assert case_result.deployment_related is not None
```

**Testing Checkpoint 2B - Cross-Layer Correlation:**
```python
def test_evaluation_layer_sees_all_layers():
    linked = load_and_link_all_sources(...)

    # Pick a fully-linked order
    full_order = next(o for o in linked.orders
                      if o.opportunity and o.deployments and o.support_cases)

    eval_result = evaluate_customer_journey(full_order)

    # Verify cross-layer insights
    assert eval_result.expectation_vs_reality is not None
    assert eval_result.deployment_impact_on_support is not None
    assert 0 <= eval_result.journey_health_score <= 100
    assert eval_result.churn_risk in ['Low', 'Medium', 'High', 'Critical']
```

### Phase 3: Metrics Engine
- `src/analysis/metrics/` package
- Product, Account, Use-case, Service metrics
- Cross-layer aggregations

**Testing Checkpoint 3 - Metrics Aggregation:**
```python
# tests/test_metrics.py
def test_product_metrics_aggregation():
    linked = load_and_link_all_sources(...)

    product_metrics = calculate_product_metrics(linked, "F-Series")

    # Verify aggregation across layers
    assert product_metrics.units_sold >= 0  # From opportunities
    assert product_metrics.units_deployed >= 0  # From deployments
    assert product_metrics.support_cases >= 0  # From cases
    assert 0 <= product_metrics.deployment_success_rate <= 1
    assert product_metrics.support_intensity >= 0  # cases/unit

def test_account_metrics_cross_layer():
    linked = load_and_link_all_sources(...)

    # Pick an account with full data
    account = "Sample Account Name"
    acct_metrics = calculate_account_metrics(linked, account)

    # Verify all layers contribute
    assert acct_metrics.total_spend > 0  # From opportunities
    assert acct_metrics.deployment_status  # From deployments
    assert acct_metrics.health_score >= 0  # From cases

def test_usecase_metrics_correlation():
    linked = load_and_link_all_sources(...)

    usecase_metrics = calculate_usecase_metrics(linked, "Video Editing")

    # Verify use case aggregates across products
    assert len(usecase_metrics.products_deployed) > 0
    assert usecase_metrics.best_performing_product  # Recommended product

def test_metrics_consistency():
    """Verify metrics sum correctly across views"""
    linked = load_and_link_all_sources(...)

    all_product_metrics = [calculate_product_metrics(linked, p)
                           for p in ['F-Series', 'M-Series', 'H-Series', 'R-Series']]
    all_account_metrics = calculate_all_account_metrics(linked)

    # Total cases should match
    total_cases_by_product = sum(p.support_cases for p in all_product_metrics)
    total_cases_by_account = sum(a.support_cases for a in all_account_metrics)
    assert total_cases_by_product == total_cases_by_account
```

### Phase 4: Pipeline & CLI
- Enhance `main.py` with `run_full_analysis()`
- Add `analyze-full` CLI command
- Enhanced JSON output structure

**Testing Checkpoint 4 - End-to-End Pipeline:**
```python
# tests/test_pipeline.py
def test_full_pipeline_integration():
    """Run entire pipeline with sample data"""
    result = run_full_analysis(
        opportunities="Account-Analysis-Reports/Ai Opportunities*.xlsx",
        deployments="Account-Analysis-Reports/PS Deploy*.xlsx",
        support="Account-Analysis-Reports/Account AI Email Body*.xlsx",
        skip_sonnet=True  # Fast test mode
    )

    # Verify all outputs generated
    assert result.opportunities_analyzed > 0
    assert result.deployments_analyzed > 0
    assert result.cases_analyzed > 0
    assert result.linked_orders > 0

    # Verify JSON outputs
    assert Path(result.output_dir / "json/opportunities.json").exists()
    assert Path(result.output_dir / "json/deployments.json").exists()
    assert Path(result.output_dir / "json/support_cases.json").exists()
    assert Path(result.output_dir / "json/cross_layer_insights.json").exists()
    assert Path(result.output_dir / "json/product_metrics.json").exists()

def test_cli_analyze_full():
    """Test CLI command works"""
    result = subprocess.run([
        "python", "-m", "src.cli", "analyze-full",
        "--opportunities", "sample_opps.xlsx",
        "--deployments", "sample_deploys.xlsx",
        "--support", "sample_cases.xlsx",
        "--quick"
    ], capture_output=True)
    assert result.returncode == 0
```

### Phase 5: Dashboard Views
- Product-centric view
- Account-centric view
- Use-case-centric view
- New pages: Opportunities, Deployments, Service Metrics

### Phase 6: Reports & Polish
- PDF report generators per view
- Documentation

## Critical Files to Modify

| File | Changes |
|------|---------|
| `src/main.py` | Multi-source pipeline, 4-layer flow |
| `src/analysis/data_loader.py` | Refactor → `src/data/case_loader.py` |
| `src/analysis/scoring.py` | Add opportunity/deployment scores |
| `src/analysis/claude_analysis.py` | New layer-specific prompts |
| `src/dashboard/pages/1_Overview.py` | View selector, multi-view nav |
| `src/cli.py` | New commands: `analyze-full`, view reports |

## CLI Commands (Final)

```bash
# Full analysis (all sources)
python -m src.cli analyze-full \
    --opportunities input/opps.xlsx \
    --deployments input/deploys.xlsx \
    --support input/cases.xlsx

# Backward compatible (support only)
python -m src.cli analyze input/cases.xlsx

# View-specific reports
python -m src.cli report --view product --filter "F-Series"
python -m src.cli report --view account --filter "ACME Corp"
python -m src.cli report --view usecase --filter "Video Editing"
```
