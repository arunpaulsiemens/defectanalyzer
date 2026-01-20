"""
Dashboard A: Overview & Quick Win Metrics
==========================================
Consolidates:
- Quick Win Metrics (Aging Analysis, Escape Rate)
- Category Pareto with Stacked Bars
- Area vs Category Heatmap
- Classification Dimensions (SDLC, Test Phase, Defect Origin)

Features:
- Tabbed interface for easy navigation
- All interactive features preserved
- Industry benchmarks with hover calculations
- Export and search functionality

Generates: Dashboard_A_Overview.html
"""

import json
from datetime import datetime
from collections import Counter, defaultdict
import numpy as np
import sys
sys.path.append('.')
from enhanced_root_cause_extraction import extract_root_cause_enhanced, get_confidence_symbol

# Load data
print("=" * 70)
print("GENERATING DASHBOARD A: OVERVIEW & QUICK WIN METRICS")
print("=" * 70)

with open('defect_analysis_output.json', 'r', encoding='utf-8') as f:
    bugs = json.load(f)

filtered_bugs = [bug for bug in bugs if bug.get('Bug Severity') in [2, 3]]
print(f"Loaded {len(filtered_bugs)} defects (Severity 2 & 3)")

# =============================================================================
# QUICK WIN METRICS DATA
# =============================================================================
today = datetime.now()
aging_data = []
environment_distribution = defaultdict(int)

for bug in filtered_bugs:
    created_str = bug.get('Created Date', '')
    if created_str:
        try:
            created_date = datetime.fromisoformat(created_str.replace('Z', '+00:00'))
            age_days = (today - created_date.replace(tzinfo=None)).days
        except:
            age_days = 0
    else:
        age_days = 0
    
    bug['Age_Days'] = age_days
    
    if age_days <= 30:
        aging_bucket = '0-30 days'
    elif age_days <= 90:
        aging_bucket = '31-90 days'
    elif age_days <= 180:
        aging_bucket = '91-180 days'
    elif age_days <= 365:
        aging_bucket = '181-365 days'
    else:
        aging_bucket = '> 1 year'
    
    bug['Aging_Bucket'] = aging_bucket
    aging_data.append({'bucket': aging_bucket, 'severity': bug.get('Bug Severity', 3)})
    
    env = bug.get('Environment', 'Unknown')
    environment_distribution[env] += 1

aging_buckets = ['0-30 days', '31-90 days', '91-180 days', '181-365 days', '> 1 year']
aging_counts = {b: {'sev2': 0, 'sev3': 0} for b in aging_buckets}
for item in aging_data:
    bucket = item['bucket']
    if item['severity'] == 2:
        aging_counts[bucket]['sev2'] += 1
    else:
        aging_counts[bucket]['sev3'] += 1

total_age = sum(bug['Age_Days'] for bug in filtered_bugs)
avg_age = total_age / len(filtered_bugs) if filtered_bugs else 0
old_bugs_count = sum(aging_counts[b]['sev2'] + aging_counts[b]['sev3'] for b in ['181-365 days', '> 1 year'])
critical_old_bugs = sum(1 for b in filtered_bugs if b.get('Bug Severity')==2 and b.get('Age_Days', 0) > 180)

# Environment breakdown for escape rate calculation
field_count = environment_distribution.get('Field', 0)  # ASSIST-tagged bugs
prod_only_count = environment_distribution.get('Production', 0)  # Production keyword bugs
test_only_count = environment_distribution.get('Test', 0)
dev_count = environment_distribution.get('Development', 0)
staging_count = environment_distribution.get('Staging/UAT', 0)
cicd_count = environment_distribution.get('CI/CD Pipeline', 0)

# Escaped = Production + Field (ASSIST)
production_count = prod_only_count + field_count
# Caught = Test + Development + Staging + CI/CD
test_count = test_only_count + dev_count + staging_count + cicd_count
total_env = production_count + test_count
escape_rate = (production_count / total_env * 100) if total_env > 0 else 0

print(f"  • Average Age: {avg_age:.0f} days")
print(f"  • Escape Rate: {escape_rate:.1f}%")

# =============================================================================
# PARETO DATA
# =============================================================================
category_bugs = {}
for bug in filtered_bugs:
    category = bug.get('Category', 'Unknown')
    if category not in category_bugs:
        category_bugs[category] = []
    category_bugs[category].append(bug)

category_sev2 = Counter()
category_sev3 = Counter()

for bug in filtered_bugs:
    category = bug.get('Category', 'Unknown')
    severity = bug.get('Bug Severity')
    if severity == 2:
        category_sev2[category] += 1
    elif severity == 3:
        category_sev3[category] += 1

all_categories = set(category_sev2.keys()) | set(category_sev3.keys())
category_totals = {cat: category_sev2[cat] + category_sev3[cat] for cat in all_categories}
sorted_categories = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)

categories = [cat for cat, _ in sorted_categories]
sev2_counts = [category_sev2[cat] for cat in categories]
sev3_counts = [category_sev3[cat] for cat in categories]
totals = [sev2_counts[i] + sev3_counts[i] for i in range(len(categories))]

cumulative_counts = np.cumsum(totals)
cumulative_percentage = (cumulative_counts / sum(totals)) * 100
pareto_80_index = next((i for i, cum_pct in enumerate(cumulative_percentage) if cum_pct >= 80), len(categories)-1)

# =============================================================================
# HEATMAP DATA
# =============================================================================
category_area = {}
for bug in filtered_bugs:
    area_path = bug.get('Area Path', 'Unknown')
    area_parts = area_path.split('\\')
    high_level_area = area_parts[-1] if len(area_parts) > 0 else 'Unknown'
    category = bug.get('Category', 'Unknown')
    
    if category not in category_area:
        category_area[category] = {}
    if high_level_area not in category_area[category]:
        category_area[category][high_level_area] = 0
    category_area[category][high_level_area] += 1

area_totals = Counter()
for bug in filtered_bugs:
    area_path = bug.get('Area Path', 'Unknown')
    area_parts = area_path.split('\\')
    high_level_area = area_parts[-1] if len(area_parts) > 0 else 'Unknown'
    area_totals[high_level_area] += 1

top_areas = [area for area, _ in area_totals.most_common(12)]

heatmap_matrix = []
for category in categories:
    row = [category_area.get(category, {}).get(area, 0) for area in top_areas]
    heatmap_matrix.append(row)

# Heatmap: Version vs Category
version_category = defaultdict(lambda: defaultdict(int))
for bug in filtered_bugs:
    version = str(bug.get('Found in Version', 'Unknown') or 'Unknown')
    category = bug.get('Category', 'Unknown')
    version_category[version][category] += 1

# Get top versions by count
version_totals_for_heatmap = Counter()
for bug in filtered_bugs:
    version = str(bug.get('Found in Version', 'Unknown') or 'Unknown')
    version_totals_for_heatmap[version] += 1
top_versions_heatmap = [v for v, _ in version_totals_for_heatmap.most_common(12)]

heatmap_version_matrix = []
for version in top_versions_heatmap:
    row = [version_category.get(version, {}).get(cat, 0) for cat in categories]
    heatmap_version_matrix.append(row)

# =============================================================================
# DIMENSION DATA
# =============================================================================
sdlc_phases = defaultdict(int)
test_phases = defaultdict(int)
defect_origins = defaultdict(int)

for bug in filtered_bugs:
    sdlc = bug.get('SDLC_Phase', 'Implementation')
    test = bug.get('Test_Phase', 'System Test')
    origin = bug.get('Defect_Origin', 'Code')
    
    sdlc_phases[sdlc] += 1
    test_phases[test] += 1
    defect_origins[origin] += 1

# Cross-tabulation: SDLC Phase vs Test Phase for combined heatmap
sdlc_test_matrix = defaultdict(lambda: defaultdict(int))
for bug in filtered_bugs:
    sdlc = bug.get('SDLC_Phase', 'Implementation')
    test = bug.get('Test_Phase', 'System Test')
    sdlc_test_matrix[sdlc][test] += 1

# Get sorted lists
sdlc_list = sorted(sdlc_phases.keys(), key=lambda x: -sdlc_phases[x])
test_list = sorted(test_phases.keys(), key=lambda x: -test_phases[x])

# Build matrix for heatmap
dimension_heatmap_matrix = []
for sdlc in sdlc_list:
    row = [sdlc_test_matrix[sdlc][test] for test in test_list]
    dimension_heatmap_matrix.append(row)

# Find the highest concentration cell for actionable insight
max_sdlc_test = max(
    [(sdlc, test, sdlc_test_matrix[sdlc][test]) for sdlc in sdlc_list for test in test_list],
    key=lambda x: x[2]
)

# Calculate process improvement metrics
total_bugs = len(filtered_bugs)
design_defects = sdlc_phases.get('Design', 0) + sdlc_phases.get('Requirements', 0)
implementation_defects = sdlc_phases.get('Implementation', 0)
late_found = test_phases.get('System Test', 0) + test_phases.get('Integration Test', 0)
early_found = test_phases.get('Unit Test', 0)
code_origin = defect_origins.get('Code', 0)
design_origin = defect_origins.get('Design', 0) + defect_origins.get('Requirements', 0)

# =============================================================================
# FILTER DATA - Area Paths and Versions
# =============================================================================
area_path_list = []
version_list = []
for bug in filtered_bugs:
    # Get simplified area path (last component)
    area_path = bug.get('Area Path', 'Unknown')
    area_parts = area_path.split('\\')
    simplified_area = area_parts[-1] if area_parts else 'Unknown'
    if simplified_area not in area_path_list:
        area_path_list.append(simplified_area)
    
    # Get version
    version = str(bug.get('Found in Version', 'Unknown') or 'Unknown')
    if version not in version_list:
        version_list.append(version)

# Sort by frequency for area paths
area_path_counts = Counter()
for bug in filtered_bugs:
    area_path = bug.get('Area Path', 'Unknown')
    simplified_area = area_path.split('\\')[-1] if area_path else 'Unknown'
    area_path_counts[simplified_area] += 1
area_path_list = [a for a, _ in area_path_counts.most_common(20)]

# Sort versions
version_list = sorted(set(version_list))[:15]

# Convert to JSON-serializable format
pareto_bug_data = {}
for cat in categories:
    pareto_bug_data[cat] = []
    for bug in category_bugs.get(cat, []):
        cause, conf = extract_root_cause_enhanced(bug)
        pareto_bug_data[cat].append({
            'id': bug.get('Bug ID'),
            'title': bug.get('Bug Title', '')[:80],
            'severity': bug.get('Bug Severity'),
            'state': bug.get('State'),
            'root_cause': cause,
            'confidence': conf,
            'area_path': bug.get('Area Path', ''),
            'created_date': bug.get('Created Date', '')[:10]
        })

# Bug data by Area Path
area_bug_data = {}
for bug in filtered_bugs:
    area_path = bug.get('Area Path', '')
    simplified_area = area_path.split('\\')[-1] if area_path else 'Unknown'
    if simplified_area not in area_bug_data:
        area_bug_data[simplified_area] = []
    cause, conf = extract_root_cause_enhanced(bug)
    area_bug_data[simplified_area].append({
        'id': bug.get('Bug ID'),
        'title': bug.get('Bug Title', '')[:80],
        'severity': bug.get('Bug Severity'),
        'state': bug.get('State'),
        'root_cause': cause,
        'confidence': conf,
        'created_date': bug.get('Created Date', '')[:10]
    })

# Bug data by Version
version_bug_data = {}
for bug in filtered_bugs:
    version = str(bug.get('Found in Version', 'Unknown') or 'Unknown')
    if version not in version_bug_data:
        version_bug_data[version] = []
    cause, conf = extract_root_cause_enhanced(bug)
    version_bug_data[version].append({
        'id': bug.get('Bug ID'),
        'title': bug.get('Bug Title', '')[:80],
        'severity': bug.get('Bug Severity'),
        'state': bug.get('State'),
        'root_cause': cause,
        'confidence': conf,
        'created_date': bug.get('Created Date', '')[:10]
    })

# Bug data for Heatmap: Category + Area cell click
heatmap_bug_data = {}
for bug in filtered_bugs:
    area_path = bug.get('Area Path', '')
    simplified_area = area_path.split('\\')[-1] if area_path else 'Unknown'
    category = bug.get('Category', 'Unknown')
    cell_key = f"{category}|{simplified_area}"
    if cell_key not in heatmap_bug_data:
        heatmap_bug_data[cell_key] = []
    cause, conf = extract_root_cause_enhanced(bug)
    heatmap_bug_data[cell_key].append({
        'id': bug.get('Bug ID'),
        'title': bug.get('Bug Title', '')[:80],
        'severity': bug.get('Bug Severity'),
        'state': bug.get('State'),
        'root_cause': cause,
        'confidence': conf,
        'created_date': bug.get('Created Date', '')[:10]
    })

# Bug data for Heatmap: Category + Version cell click
heatmap_version_bug_data = {}
for bug in filtered_bugs:
    version = str(bug.get('Found in Version', 'Unknown') or 'Unknown')
    category = bug.get('Category', 'Unknown')
    cell_key = f"{category}|{version}"
    if cell_key not in heatmap_version_bug_data:
        heatmap_version_bug_data[cell_key] = []
    cause, conf = extract_root_cause_enhanced(bug)
    heatmap_version_bug_data[cell_key].append({
        'id': bug.get('Bug ID'),
        'title': bug.get('Bug Title', '')[:80],
        'severity': bug.get('Bug Severity'),
        'state': bug.get('State'),
        'root_cause': cause,
        'confidence': conf,
        'created_date': bug.get('Created Date', '')[:10]
    })

# Bug data for Dimensions: SDLC + Test Phase cell click
dimension_bug_data = {}
for bug in filtered_bugs:
    sdlc = bug.get('SDLC_Phase', 'Implementation')
    test = bug.get('Test_Phase', 'System Test')
    cell_key = f"{sdlc}|{test}"
    if cell_key not in dimension_bug_data:
        dimension_bug_data[cell_key] = []
    cause, conf = extract_root_cause_enhanced(bug)
    dimension_bug_data[cell_key].append({
        'id': bug.get('Bug ID'),
        'title': bug.get('Bug Title', '')[:80],
        'severity': bug.get('Bug Severity'),
        'state': bug.get('State'),
        'root_cause': cause,
        'confidence': conf,
        'sdlc_phase': sdlc,
        'test_phase': test,
        'created_date': bug.get('Created Date', '')[:10]
    })

# All bugs data for filtering (simplified)
all_bugs_for_filter = []
for cat in categories:
    for bug in category_bugs.get(cat, []):
        area_path = bug.get('Area Path', '')
        simplified_area = area_path.split('\\')[-1] if area_path else 'Unknown'
        version = str(bug.get('Found in Version', 'Unknown') or 'Unknown')
        all_bugs_for_filter.append({
            'category': cat,
            'area': simplified_area,
            'version': version,
            'severity': bug.get('Bug Severity')
        })

# Prepare data for different Pareto groupings
# By Area Path
area_sev2 = defaultdict(int)
area_sev3 = defaultdict(int)
for bug in filtered_bugs:
    area_path = bug.get('Area Path', '')
    simplified_area = area_path.split('\\')[-1] if area_path else 'Unknown'
    if bug.get('Bug Severity') == 2:
        area_sev2[simplified_area] += 1
    else:
        area_sev3[simplified_area] += 1

# Sort areas by total count
area_totals_sorted = sorted([(a, area_sev2[a] + area_sev3[a]) for a in set(area_sev2.keys()) | set(area_sev3.keys())], key=lambda x: -x[1])
pareto_areas = [a for a, _ in area_totals_sorted[:15]]
pareto_area_sev2 = [area_sev2[a] for a in pareto_areas]
pareto_area_sev3 = [area_sev3[a] for a in pareto_areas]

# By Version
version_sev2 = defaultdict(int)
version_sev3 = defaultdict(int)
for bug in filtered_bugs:
    version = str(bug.get('Found in Version', 'Unknown') or 'Unknown')
    if bug.get('Bug Severity') == 2:
        version_sev2[version] += 1
    else:
        version_sev3[version] += 1

# Sort versions by total count
version_totals_sorted = sorted([(v, version_sev2[v] + version_sev3[v]) for v in set(version_sev2.keys()) | set(version_sev3.keys())], key=lambda x: -x[1])
pareto_versions = [v for v, _ in version_totals_sorted[:15]]
pareto_version_sev2 = [version_sev2[v] for v in pareto_versions]
pareto_version_sev3 = [version_sev3[v] for v in pareto_versions]

# =============================================================================
# PREDICTIVE ANALYTICS DATA
# =============================================================================
print("\n📈 Calculating Predictive Analytics...")

# 1. Defect Velocity - Defects per month (from 2022 onwards for reliable data)
monthly_defects = defaultdict(int)
for bug in filtered_bugs:
    created_str = bug.get('Created Date', '')
    if created_str:
        try:
            created_date = datetime.fromisoformat(created_str.replace('Z', '+00:00'))
            # Only include data from 2022 onwards (reliable data period)
            if created_date.year >= 2022:
                month_key = created_date.strftime('%Y-%m')
                monthly_defects[month_key] += 1
        except:
            pass

# Sort months and use all available data from 2022+
sorted_months = sorted(monthly_defects.keys())
monthly_counts = [monthly_defects[m] for m in sorted_months]
avg_monthly_inflow = sum(monthly_counts) / len(monthly_counts) if monthly_counts else 0

# 2. Resolution Analysis - Calculate based on closed bugs
closed_states = ['Closed', 'Resolved', 'Done', 'Verified']
closed_bugs = [b for b in filtered_bugs if b.get('State') in closed_states]
open_bugs = [b for b in filtered_bugs if b.get('State') not in closed_states]

# Estimate resolution rate (bugs closed per month based on data period)
data_months = len(sorted_months) if sorted_months else 12
resolution_rate = len(closed_bugs) / data_months if closed_bugs else avg_monthly_inflow * 0.8  # Assume 80% resolution rate

# 3. Backlog Burndown Projection
current_backlog = len(open_bugs)
sev2_aging_90 = sum(1 for b in open_bugs if b.get('Bug Severity')==2 and b.get('Age_Days', 0) > 90)
open_sev2_count = sum(1 for b in open_bugs if b.get('Bug Severity')==2)
net_monthly_change = resolution_rate - avg_monthly_inflow
if net_monthly_change > 0:
    months_to_clear = current_backlog / net_monthly_change
    burndown_status = "decreasing"
elif net_monthly_change < 0:
    months_to_clear = -1  # Backlog growing
    burndown_status = "increasing"
else:
    months_to_clear = float('inf')
    burndown_status = "stable"

# 4. Average Age by Category (for Vital Few - 80% categories)
category_avg_age = {}
vital_few_count = pareto_80_index + 1  # Number of categories that make up 80%
for cat in categories[:vital_few_count]:
    cat_bugs = category_bugs.get(cat, [])
    cat_ages = [b.get('Age_Days', 0) for b in cat_bugs]
    category_avg_age[cat] = sum(cat_ages) / len(cat_ages) if cat_ages else 0

# 5. Category-specific Escape Rates (for Vital Few)
category_escape_rates = {}
for cat in categories[:vital_few_count]:
    cat_bugs = category_bugs.get(cat, [])
    cat_prod = sum(1 for b in cat_bugs if b.get('Environment') in ['Production', 'Field'])
    cat_total = len(cat_bugs)
    category_escape_rates[cat] = (cat_prod / cat_total * 100) if cat_total > 0 else 0

# 6. Risk Score Calculation (0-100)
def calculate_risk_score(bug):
    score = 0
    # Age factor (max 30 points)
    age = bug.get('Age_Days', 0)
    score += min(30, age / 12)  # 1 point per 12 days, max 30
    
    # Severity factor (max 30 points)
    if bug.get('Bug Severity') == 2:
        score += 30
    else:
        score += 15
    
    # Environment factor (max 20 points)
    if bug.get('Environment') in ['Production', 'Field']:
        score += 20
    elif bug.get('Environment') == 'Test':
        score += 10
    
    # Category factor (max 20 points) - high-volume categories are riskier
    cat = bug.get('Category', 'Unknown')
    if cat in categories[:3]:  # Top 3 categories
        score += 20
    elif cat in categories[3:6]:
        score += 10
    
    return min(100, score)

# Calculate risk scores
for bug in filtered_bugs:
    bug['Risk_Score'] = calculate_risk_score(bug)

high_risk_bugs = [b for b in filtered_bugs if b.get('Risk_Score', 0) >= 70]
avg_risk_score = sum(b.get('Risk_Score', 0) for b in filtered_bugs) / len(filtered_bugs)

# 7. Category Health Index (0-100, higher is better)
category_health = {}
for cat in categories:
    cat_bugs = category_bugs.get(cat, [])
    if not cat_bugs:
        category_health[cat] = 100
        continue
    
    # Factors: volume, escape rate, avg age, sev2 ratio
    volume_penalty = min(30, len(cat_bugs) / 2)  # More bugs = lower health
    escape_penalty = category_escape_rates.get(cat, 0) * 0.3  # Escape rate penalty
    age_penalty = min(20, category_avg_age.get(cat, 0) / 30)  # Age penalty
    sev2_ratio = sum(1 for b in cat_bugs if b.get('Bug Severity') == 2) / len(cat_bugs)
    sev2_penalty = sev2_ratio * 20
    
    health = max(0, 100 - volume_penalty - escape_penalty - age_penalty - sev2_penalty)
    category_health[cat] = health

# 8. Forecast: Expected defects in next quarter
quarterly_forecast = avg_monthly_inflow * 3
expected_escapes = quarterly_forecast * (escape_rate / 100)

# 10. CONFIDENCE INTERVALS & VARIANCE ANALYSIS
import statistics

# Calculate variance in monthly inflow
if len(monthly_counts) >= 3:
    inflow_std = statistics.stdev(monthly_counts)
    inflow_variance = statistics.variance(monthly_counts)
    inflow_cv = (inflow_std / avg_monthly_inflow * 100) if avg_monthly_inflow > 0 else 0  # Coefficient of Variation
else:
    inflow_std = avg_monthly_inflow * 0.3  # Assume 30% if insufficient data
    inflow_variance = inflow_std ** 2
    inflow_cv = 30

# Confidence intervals (±1.5 std for ~87% coverage, simplified)
confidence_margin = 1.5 * inflow_std

# Calculate 6-month forecast date
from dateutil.relativedelta import relativedelta
forecast_date = today + relativedelta(months=6)
forecast_date_str = forecast_date.strftime('%b %Y')  # e.g., "Jul 2026"

# Backlog forecast with confidence intervals
backlog_6mo_point = current_backlog + (abs(net_monthly_change) * 6) if burndown_status == 'increasing' else max(0, current_backlog - (net_monthly_change * 6))
backlog_6mo_low = max(0, backlog_6mo_point - (confidence_margin * 6 * 0.5))  # Lower bound
backlog_6mo_high = backlog_6mo_point + (confidence_margin * 6 * 0.5)  # Upper bound

# Quarterly forecast with confidence intervals
quarterly_low = max(0, quarterly_forecast - (confidence_margin * 3))
quarterly_high = quarterly_forecast + (confidence_margin * 3)

# Escape forecast with confidence intervals
escapes_low = quarterly_low * (escape_rate / 100)
escapes_high = quarterly_high * (escape_rate / 100)

# Model reliability score (0-100) based on data quality
# data_months already calculated above from sorted_months
reliability_score = min(100, (
    30 * min(1, data_months / 24) +  # Data coverage - 24 months for full score (30 pts)
    30 * max(0, 1 - inflow_cv / 100) +  # Low variance = more reliable (30 pts)
    20 * (1 if len(filtered_bugs) >= 100 else len(filtered_bugs) / 100) +  # Sample size (20 pts)
    20 * (1 if resolution_rate > 0 else 0)  # Resolution data available (20 pts)
))

reliability_label = 'HIGH' if reliability_score >= 70 else 'MEDIUM' if reliability_score >= 50 else 'LOW'

print(f"  • Inflow Std Dev: {inflow_std:.2f} (CV: {inflow_cv:.0f}%)")
print(f"  • 6-Mo Backlog Range: {backlog_6mo_low:.0f} - {backlog_6mo_high:.0f}")
print(f"  • Quarterly Range: {quarterly_low:.0f} - {quarterly_high:.0f}")
print(f"  • Model Reliability: {reliability_score:.0f}/100 ({reliability_label})")

# 9. Top Root Causes with Impact (enhanced with open/sev2 counts)
root_cause_data = defaultdict(lambda: {'count': 0, 'open': 0, 'sev2': 0})
for bug in filtered_bugs:
    cause, _ = extract_root_cause_enhanced(bug)
    root_cause_data[cause]['count'] += 1
    if bug.get('State') not in closed_states:
        root_cause_data[cause]['open'] += 1
    if bug.get('Bug Severity') == 2:
        root_cause_data[cause]['sev2'] += 1

# Sort by count and get top 5
top_root_causes = sorted(root_cause_data.items(), key=lambda x: x[1]['count'], reverse=True)[:5]
top_3_rc_count = sum(data['count'] for _, data in top_root_causes[:3])
top_3_rc_reduction = (top_3_rc_count / len(filtered_bugs)) * 100 if filtered_bugs else 0

# Priority score for ranking (open bugs + 2*sev2 bugs)
for rc, data in top_root_causes:
    data['priority'] = data['open'] + (2 * data['sev2'])

print(f"  • Avg Monthly Inflow: {avg_monthly_inflow:.1f} defects/month")
print(f"  • Current Backlog: {current_backlog} open defects")
print(f"  • Resolution Rate: {resolution_rate:.1f} defects/month")
print(f"  • Burndown Status: {burndown_status}")
print(f"  • Avg Risk Score: {avg_risk_score:.1f}/100")
print(f"  • High Risk Bugs: {len(high_risk_bugs)}")
print(f"  • Quarterly Forecast: {quarterly_forecast:.0f} new defects")

# =============================================================================
# GENERATE HTML
# =============================================================================
html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DefectAnalyzer - Dashboard A: Overview</title>
    <script src="https://cdn.plot.ly/plotly-2.18.2.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, sans-serif;
            background: #1a1a2e;
            color: #ffffff;
            min-height: 100vh;
        }}
        
        .header {{
            background: linear-gradient(135deg, #16213e 0%, #1a1a2e 100%);
            padding: 15px 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 2px solid #00d4ff;
        }}
        
        .header h1 {{
            color: #00d4ff;
            font-size: 1.4em;
        }}
        
        .header-info {{
            display: flex;
            gap: 25px;
            font-size: 0.85em;
        }}
        
        .header-info span {{
            color: #888;
        }}
        
        .header-info strong {{
            color: #00d4ff;
        }}
        
        .tabs {{
            display: flex;
            background: rgba(0,0,0,0.3);
            border-bottom: 1px solid #333;
        }}
        
        .tab {{
            padding: 15px 30px;
            cursor: pointer;
            color: #888;
            border-bottom: 3px solid transparent;
            transition: all 0.3s ease;
            font-weight: 500;
        }}
        
        .tab:hover {{
            color: #fff;
            background: rgba(0, 212, 255, 0.1);
        }}
        
        .tab.active {{
            color: #00d4ff;
            border-bottom-color: #00d4ff;
            background: rgba(0, 212, 255, 0.15);
        }}
        
        .tab-content {{
            display: none;
            padding: 20px;
        }}
        
        .tab-content.active {{
            display: block;
        }}
        
        /* Overview tab needs flex layout when active */
        #tab-overview.active {{
            display: flex;
            flex-direction: column;
            height: calc(100vh - 120px);
        }}
        
        /* Quick Win Styles */
        .metrics-row {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
            margin-bottom: 25px;
        }}
        
        .metric-card {{
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            padding: 25px;
            text-align: center;
            border: 1px solid rgba(255,255,255,0.1);
            position: relative;
            cursor: help;
        }}
        
        .metric-card:hover {{
            transform: translateY(-3px);
            transition: transform 0.3s ease;
        }}
        
        .metric-value {{
            font-size: 2.5em;
            font-weight: bold;
            background: linear-gradient(90deg, #00d4ff, #7c3aed);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        
        .metric-label {{
            color: #888;
            margin-top: 10px;
        }}
        
        .metric-trend {{
            margin-top: 10px;
            font-size: 0.85em;
            padding: 5px 12px;
            border-radius: 15px;
            display: inline-block;
        }}
        
        .trend-good {{ background: rgba(0,255,127,0.2); color: #00ff7f; }}
        .trend-warning {{ background: rgba(255,200,0,0.2); color: #ffc800; }}
        .trend-bad {{ background: rgba(255,107,107,0.2); color: #ff6b6b; }}
        
        .charts-row {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 25px;
        }}
        
        .chart-card {{
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            padding: 20px;
            border: 1px solid rgba(255,255,255,0.1);
        }}
        
        .chart-title {{
            color: #00d4ff;
            font-size: 1.1em;
            margin-bottom: 15px;
        }}
        
        .insight-box {{
            background: rgba(0,212,255,0.1);
            border-left: 4px solid #00d4ff;
            padding: 15px 20px;
            border-radius: 0 10px 10px 0;
            margin-top: 15px;
        }}
        
        .insight-box strong {{
            color: #00d4ff;
        }}
        
        .benchmark-box {{
            background: rgba(0,255,127,0.1);
            border-left: 4px solid #00ff7f;
            padding: 15px 20px;
            border-radius: 0 10px 10px 0;
            margin-top: 15px;
        }}
        
        .benchmark-box strong {{
            color: #00ff7f;
        }}
        
        .benchmark-table {{
            width: 100%;
            margin-top: 10px;
            font-size: 0.85em;
        }}
        
        .benchmark-table td {{
            padding: 5px 10px;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }}
        
        .benchmark-good {{ color: #00ff7f; }}
        .benchmark-warning {{ color: #ffc800; }}
        .benchmark-bad {{ color: #ff6b6b; }}
        
        .your-score {{
            background: rgba(0,212,255,0.2);
            border-radius: 5px;
        }}
        
        /* Pareto & Heatmap Styles */
        .pareto-container {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
        }}
        
        .heatmap-container {{
            background: white;
            border-radius: 10px;
            padding: 20px;
        }}
        
        /* Dimensions Bar */
        .dimensions-bar {{
            display: flex;
            gap: 15px;
            padding: 15px 20px;
            background: rgba(255,255,255,0.05);
            border-radius: 10px;
            margin-top: 20px;
        }}
        
        .dimension-chart {{
            flex: 1;
            text-align: center;
            background: rgba(0,0,0,0.2);
            padding: 15px;
            border-radius: 10px;
        }}
        
        .dimension-title {{
            font-weight: bold;
            font-size: 0.85em;
            color: #00d4ff;
            margin-bottom: 10px;
        }}
        
        /* Tooltip */
        .tooltip {{
            visibility: hidden;
            opacity: 0;
            position: absolute;
            bottom: 100%;
            left: 50%;
            transform: translateX(-50%);
            background: #16213e;
            border: 1px solid #00d4ff;
            border-radius: 10px;
            padding: 15px;
            min-width: 280px;
            z-index: 1000;
            transition: opacity 0.3s ease;
        }}
        
        .metric-card:hover .tooltip {{
            visibility: visible;
            opacity: 1;
        }}
        
        .tooltip h4 {{
            color: #00d4ff;
            margin-bottom: 8px;
            font-size: 0.9em;
        }}
        
        .tooltip .formula {{
            background: rgba(0,0,0,0.3);
            padding: 8px;
            border-radius: 5px;
            font-family: monospace;
            font-size: 0.85em;
            color: #00ff7f;
            margin: 8px 0;
        }}
        
        .tooltip .result {{
            color: #00d4ff;
            font-weight: bold;
            margin-top: 8px;
        }}
        
        /* Modal */
        .modal {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.8);
            z-index: 10000;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        
        .modal-content {{
            background: white;
            padding: 30px;
            border-radius: 10px;
            max-width: 90%;
            max-height: 85vh;
            overflow-y: auto;
            color: #333;
        }}
        
        .modal-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }}
        
        .modal-close {{
            background: #e74c3c;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-weight: bold;
        }}
        
        .bug-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
        }}
        
        .bug-table th {{
            background: #34495e;
            color: white;
            padding: 10px;
            text-align: left;
        }}
        
        .bug-table td {{
            padding: 8px 10px;
            border-bottom: 1px solid #ddd;
        }}
        
        .bug-table tr:nth-child(even) {{
            background: #f8f9fa;
        }}
        
        .sev-badge {{
            padding: 3px 8px;
            border-radius: 10px;
            font-size: 10px;
            font-weight: bold;
        }}
        
        .sev-2 {{ background: #cc0000; color: white; }}
        .sev-3 {{ background: #ffcccc; color: #333; }}
        
        .footer {{
            text-align: center;
            padding: 20px;
            color: #666;
            font-size: 0.85em;
            border-top: 1px solid #333;
        }}
        
        /* ========================================
           RESPONSIVE DESIGN - Media Queries
           ======================================== */
        
        /* Large screens (1400px+) - Full layout */
        @media (min-width: 1400px) {{
            .header h1 {{ font-size: 1.5em; }}
        }}
        
        /* Medium screens (1024px - 1399px) - Laptop */
        @media (max-width: 1399px) {{
            .header {{ padding: 12px 20px; }}
            .header h1 {{ font-size: 1.2em; }}
            .header-info {{ gap: 15px; font-size: 0.8em; }}
            .tab {{ padding: 12px 20px; font-size: 0.9em; }}
            .tab-content {{ padding: 15px; }}
            #tab-overview.active {{ height: calc(100vh - 110px); }}
        }}
        
        /* Small screens (768px - 1023px) - Tablet */
        @media (max-width: 1023px) {{
            .header {{ 
                flex-direction: column; 
                gap: 10px; 
                padding: 10px 15px;
                text-align: center;
            }}
            .header h1 {{ font-size: 1.1em; }}
            .header-info {{ 
                flex-wrap: wrap; 
                justify-content: center;
                gap: 10px;
                font-size: 0.75em;
            }}
            .tabs {{ 
                flex-wrap: wrap;
                justify-content: center;
            }}
            .tab {{ 
                padding: 10px 15px; 
                font-size: 0.8em;
                flex: 1;
                text-align: center;
                min-width: 120px;
            }}
            .tab-content {{ padding: 10px; }}
            #tab-overview.active {{ height: auto; min-height: calc(100vh - 150px); }}
            
            /* Stack cards vertically on tablet */
            .metrics-row {{ grid-template-columns: repeat(2, 1fr); }}
            .charts-row {{ grid-template-columns: 1fr; }}
        }}
        
        /* Extra small screens (<768px) - Mobile */
        @media (max-width: 767px) {{
            .header h1 {{ font-size: 1em; }}
            .header-info {{ 
                flex-direction: column; 
                gap: 5px;
                font-size: 0.7em;
            }}
            .tabs {{ 
                overflow-x: auto;
                flex-wrap: nowrap;
                -webkit-overflow-scrolling: touch;
            }}
            .tab {{ 
                padding: 8px 12px; 
                font-size: 0.75em;
                white-space: nowrap;
            }}
            .tab-content {{ padding: 8px; }}
            
            /* Stack all cards vertically on mobile */
            .metrics-row {{ grid-template-columns: 1fr; }}
            .charts-row {{ grid-template-columns: 1fr; }}
            .dimensions-bar {{ flex-direction: column; }}
            
            /* Modal adjustments */
            .modal-content {{ 
                max-width: 95%; 
                padding: 15px;
                max-height: 90vh;
            }}
            .bug-table {{ font-size: 10px; }}
        }}
        
        /* ========================================
           Overview Tab Responsive Grid Classes
           ======================================== */
        .kpi-row {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 8px;
            margin-bottom: 8px;
        }}
        
        .forecast-row {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 8px;
            margin-bottom: 8px;
        }}
        
        .summary-row {{
            display: grid;
            grid-template-columns: 3fr 2fr;
            gap: 8px;
            margin-bottom: 6px;
        }}
        
        /* Tablet responsive for Overview grids */
        @media (max-width: 1200px) {{
            .forecast-row {{
                grid-template-columns: repeat(2, 1fr);
            }}
        }}
        
        @media (max-width: 1100px) {{
            .kpi-row {{
                grid-template-columns: repeat(2, 1fr);
            }}
        }}
        
        @media (max-width: 900px) {{
            .summary-row {{
                grid-template-columns: 1fr;
            }}
        }}
        
        @media (max-width: 600px) {{
            .kpi-row {{
                grid-template-columns: 1fr;
            }}
            .forecast-row {{
                grid-template-columns: 1fr;
            }}
        }}
        
        /* Print styles */
        @media print {{
            body {{ background: white !important; color: black !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
            .header {{ background: #f5f5f5 !important; border-bottom: 2px solid #333; padding: 10px !important; }}
            .header button {{ display: none !important; }}
            .tabs {{ display: none !important; }}
            .tab-content {{ display: block !important; page-break-inside: avoid; }}
            .tab-content:not(#tab-overview) {{ display: none !important; }}
            .modal {{ display: none !important; }}
            .metric-card, .chart-card {{ border: 1px solid #ccc !important; background: #fff !important; }}
            .metric-value {{ color: #333 !important; }}
            .kpi-row, .forecast-row, .summary-row {{ gap: 8px !important; }}
            * {{ box-shadow: none !important; }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>📊 Dashboard A: Defect Overview</h1>
            <p style="color: #888; font-size: 0.85em;">Key metrics, trends, and benchmarks for defect management <span style="color: #666; font-size: 0.8em;">| v1.0 (2026-01-19)</span></p>
        </div>
        <div style="display: flex; align-items: center; gap: 12px;">
            <span style="color: #888; font-size: 0.7em;">Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</span>
            <button onclick="window.print()" style="background: linear-gradient(135deg, #3498db, #2980b9); border: none; padding: 6px 14px; border-radius: 6px; color: white; font-size: 0.75em; cursor: pointer; display: flex; align-items: center; gap: 5px;" title="Print or save as PDF">🖨️ Export</button>
        </div>
    </div>
    
    <div class="tabs">
        <div class="tab active" onclick="showTab('overview', this)">📊 Overview & Analytics</div>
        <div class="tab" onclick="showTab('pareto', this)">📊 Category Pareto</div>
        <div class="tab" onclick="showTab('heatmap', this)">🗺️ Area Heatmap</div>
        <div class="tab" onclick="showTab('dimensions', this)">📋 Classification Dimensions</div>
    </div>
    
    <!-- TAB 1: Single-Page Overview (Full Height) -->
    <div id="tab-overview" class="tab-content active">
        <!-- ROW 1: Compact KPI Cards (4 columns: Total → Inflow → Sev2 Aging → Backlog) -->
        <div class="kpi-row">
            <!-- Card 1: Total Defects -->
            <div class="metric-card" style="padding: 10px 12px; cursor: help;" title="📐 TOTAL DEFECTS&#10;━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━&#10;&#10;All Severity 2 & 3 bugs&#10;&#10;Sev2 (High): {sum(1 for b in filtered_bugs if b.get('Bug Severity')==2)}&#10;Sev3 (Medium): {sum(1 for b in filtered_bugs if b.get('Bug Severity')==3)}">
                <div class="metric-value" style="font-size: 1.8em;">{len(filtered_bugs)}</div>
                <div class="metric-label" style="font-size: 0.75em;">Total Defects</div>
                <div class="metric-trend trend-warning" style="font-size: 0.7em;">Sev2: {sum(1 for b in filtered_bugs if b.get('Bug Severity')==2)} | Sev3: {sum(1 for b in filtered_bugs if b.get('Bug Severity')==3)}</div>
            </div>
            <!-- Card 2: Inflow Rate -->
            <div class="metric-card" style="padding: 10px 12px; background: linear-gradient(135deg, rgba(0,212,255,0.12), rgba(0,212,255,0.03)); cursor: help;" title="📐 INFLOW RATE&#10;━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━&#10;&#10;Average new bugs per month&#10;Based on {data_months} months of data&#10;&#10;Calculation: Total ÷ Months&#10;= {sum(monthly_counts)} ÷ {data_months} = {avg_monthly_inflow:.1f}/mo">
                <div class="metric-value" style="font-size: 1.8em; color: #00d4ff;">{avg_monthly_inflow:.1f}</div>
                <div class="metric-label" style="font-size: 0.75em;">Inflow Rate</div>
                <div class="metric-trend" style="font-size: 0.7em;">defects/month (avg)</div>
            </div>
            <!-- Card 3: Sev2 Aging (>90 days) -->
            <div class="metric-card" style="padding: 10px 12px; background: linear-gradient(135deg, rgba(255,107,107,0.12), rgba(255,107,107,0.03)); cursor: help;" title="📐 SEV2 AGING RISK&#10;━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━&#10;&#10;High-priority bugs older than 90 days.&#10;These represent accumulated risk.&#10;&#10;Sev2 >90 days: {sev2_aging_90}&#10;Total open Sev2: {open_sev2_count}">
                <div class="metric-value" style="font-size: 1.8em; color: #ff6b6b;">{sev2_aging_90}</div>
                <div class="metric-label" style="font-size: 0.75em;">Sev2 Aging (>90d)</div>
                <div class="metric-trend trend-bad" style="font-size: 0.7em;">of {open_sev2_count} open Sev2</div>
            </div>
            <!-- Card 4: Open Backlog -->
            <div class="metric-card" style="padding: 10px 12px; background: linear-gradient(135deg, rgba(243,156,18,0.15), rgba(243,156,18,0.03)); cursor: help;" title="📐 OPEN BACKLOG&#10;━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━&#10;&#10;Bugs not yet resolved&#10;(State NOT IN Closed, Resolved, Done)&#10;&#10;Open: {current_backlog}&#10;Closed: {len(filtered_bugs) - current_backlog}">
                <div class="metric-value" style="font-size: 1.8em; color: #f39c12;">{current_backlog}</div>
                <div class="metric-label" style="font-size: 0.75em;">Open Backlog</div>
                <div class="metric-trend trend-neutral" style="font-size: 0.7em;">{len(filtered_bugs) - current_backlog} closed | {(current_backlog/len(filtered_bugs)*100):.0f}% open</div>
            </div>
        </div>
        
        <!-- ROW 2: 4 Forecast Cards -->
        <div class="forecast-row">
            
            <!-- Card 1: AGING RISK -->
            <div class="chart-card" style="padding: 10px; display: flex; flex-direction: column; cursor: help;" title="📐 AGING RISK ANALYSIS&#10;━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━&#10;&#10;Bugs older than 180 days need attention.&#10;They represent accumulated technical debt.&#10;&#10;Your Data:&#10;• Old bugs (>180d): {old_bugs_count}&#10;• Critical old (Sev2 >180d): {critical_old_bugs}&#10;• Very old (>1 year): {aging_counts['> 1 year']['sev2'] + aging_counts['> 1 year']['sev3']}&#10;&#10;Risk: Older bugs are harder to fix&#10;and may indicate systemic issues.">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                    <span style="color: {'#ff6b6b' if old_bugs_count > len(filtered_bugs)*0.5 else '#f39c12' if old_bugs_count > len(filtered_bugs)*0.3 else '#2ecc71'}; font-size: 0.9em; font-weight: bold;">⏰ Aging Risk</span>
                    <span style="background: {'rgba(255,107,107,0.25)' if critical_old_bugs > 20 else 'rgba(243,156,18,0.25)' if critical_old_bugs > 10 else 'rgba(46,204,113,0.25)'}; padding: 2px 6px; border-radius: 6px; font-size: 0.65em; font-weight: bold; color: {'#ff6b6b' if critical_old_bugs > 20 else '#f39c12' if critical_old_bugs > 10 else '#2ecc71'};">Tech Debt</span>
                </div>
                <div style="text-align: center; padding: 8px 0; flex: 1; display: flex; flex-direction: column; justify-content: center;">
                    <div style="font-size: 0.75em; color: #888; margin-bottom: 2px;">Bugs Older Than 180 Days</div>
                    <div style="font-size: 2em; font-weight: bold; color: {'#ff6b6b' if old_bugs_count > len(filtered_bugs)*0.5 else '#f39c12' if old_bugs_count > len(filtered_bugs)*0.3 else '#2ecc71'};">{old_bugs_count}</div>
                    <div style="font-size: 0.7em; color: #888; margin-top: 3px;"><strong style="color: #ff6b6b;">{critical_old_bugs}</strong> are Sev2 | <strong style="color: #f39c12;">{aging_counts['> 1 year']['sev2'] + aging_counts['> 1 year']['sev3']}</strong> over 1 year</div>
                </div>
                <div style="background: rgba(0,0,0,0.4); border-radius: 4px; padding: 6px; border: 1px solid rgba(255,107,107,0.3);">
                    <div style="color: #888; font-size: 0.7em; margin-bottom: 3px;">📊 Age Distribution:</div>
                    <div style="display: flex; gap: 4px; font-size: 0.65em;">
                        <span style="background: rgba(46,204,113,0.3); padding: 2px 6px; border-radius: 3px; color: #2ecc71;">0-90d: {aging_counts['0-30 days']['sev2'] + aging_counts['0-30 days']['sev3'] + aging_counts['31-90 days']['sev2'] + aging_counts['31-90 days']['sev3']}</span>
                        <span style="background: rgba(243,156,18,0.3); padding: 2px 6px; border-radius: 3px; color: #f39c12;">91-365d: {aging_counts['91-180 days']['sev2'] + aging_counts['91-180 days']['sev3'] + aging_counts['181-365 days']['sev2'] + aging_counts['181-365 days']['sev3']}</span>
                        <span style="background: rgba(255,107,107,0.3); padding: 2px 6px; border-radius: 3px; color: #ff6b6b;">>1yr: {aging_counts['> 1 year']['sev2'] + aging_counts['> 1 year']['sev3']}</span>
                    </div>
                </div>
                <div style="font-size: 0.7em; margin-top: 5px; padding: 5px; background: {'rgba(255,107,107,0.15)' if critical_old_bugs > 20 else 'rgba(243,156,18,0.15)' if critical_old_bugs > 10 else 'rgba(46,204,113,0.15)'}; border-radius: 3px; color: {'#ff6b6b' if critical_old_bugs > 20 else '#f39c12' if critical_old_bugs > 10 else '#2ecc71'}; text-align: center;">
                    ⚡ {'🔴 ' + str(critical_old_bugs) + ' critical old Sev2 need review' if critical_old_bugs > 20 else '⚠️ ' + str(critical_old_bugs) + ' aging Sev2 bugs' if critical_old_bugs > 10 else '✅ Aging under control'}
                </div>
            </div>
            
            <!-- Card 2: BACKLOG FORECAST -->
            <div class="chart-card" style="padding: 10px; display: flex; flex-direction: column;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                    <span style="color: {'#ff6b6b' if burndown_status == 'increasing' else '#2ecc71'}; font-size: 0.9em; font-weight: bold;">{'📈' if burndown_status == 'increasing' else '📉'} 6-Month Forecast</span>
                    <span style="background: rgba(0,212,255,0.2); padding: 2px 6px; border-radius: 6px; font-size: 0.65em; color: #00d4ff;">Backlog</span>
                </div>
                <div style="text-align: center; padding: 8px 0; flex: 1; display: flex; flex-direction: column; justify-content: center;">
                    <div style="font-size: 0.75em; color: #888; margin-bottom: 2px;">Today → {forecast_date_str}</div>
                    <div style="font-size: 2em; font-weight: bold; color: {'#ff6b6b' if burndown_status == 'increasing' else '#2ecc71'};">{current_backlog} → {backlog_6mo_point:.0f}</div>
                    <div style="font-size: 0.7em; color: #888; margin-top: 3px;">Range: {backlog_6mo_low:.0f} - {backlog_6mo_high:.0f} <span title="HOW RANGE IS CALCULATED:&#10;&#10;Point estimate: {backlog_6mo_point:.0f}&#10;&#10;Your monthly inflow varies by ~{inflow_std:.0f} bugs/month&#10;Over 6 months: ±{int(confidence_margin * 6 * 0.5)} variation&#10;&#10;Best case: {backlog_6mo_point:.0f} - {int(confidence_margin * 6 * 0.5)} = {backlog_6mo_low:.0f}&#10;Worst case: {backlog_6mo_point:.0f} + {int(confidence_margin * 6 * 0.5)} = {backlog_6mo_high:.0f}" style="cursor: help; border-bottom: 1px dotted #888;">(± variation ⓘ)</span></div>
                </div>
                <div style="background: rgba(0,0,0,0.4); border-radius: 4px; padding: 6px; font-family: 'Courier New', monospace; border: 1px solid rgba(0,212,255,0.3);">
                    <div style="color: #00d4ff; font-size: 0.7em; margin-bottom: 3px;">📐 Projection:</div>
                    <div style="color: #ccc; font-size: 0.75em; line-height: 1.4;">
                        {'Closing ' + f'{resolution_rate:.1f}/mo < Incoming {avg_monthly_inflow:.1f}/mo → <strong style="color: #ff6b6b;">+{abs(net_monthly_change):.1f} growth/mo</strong>' if net_monthly_change < 0 else 'Closing ' + f'{resolution_rate:.1f}/mo > Incoming {avg_monthly_inflow:.1f}/mo → <strong style="color: #2ecc71;">{net_monthly_change:.1f} shrink/mo</strong>'}<br/>
                        6mo: {current_backlog} + ({abs(net_monthly_change):.1f} × 6) = <strong>{backlog_6mo_point:.0f}</strong>
                    </div>
                </div>
                <div style="font-size: 0.7em; margin-top: 5px; padding: 5px; background: {'rgba(255,107,107,0.15)' if burndown_status == 'increasing' else 'rgba(46,204,113,0.15)'}; border-radius: 3px; color: {'#ff6b6b' if burndown_status == 'increasing' else '#2ecc71'}; text-align: center;">
                    ⚡ {'⚠️ Need to resolve ' + f'{abs(net_monthly_change):.0f}+ more bugs/month to stabilize' if burndown_status == 'increasing' else '✅ Backlog shrinking'}
                </div>
            </div>
            
            <!-- Card 3: QUARTERLY FORECAST -->
            <div class="chart-card" style="padding: 10px; display: flex; flex-direction: column;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                    <span style="color: #00d4ff; font-size: 0.9em; font-weight: bold;">📅 Quarterly Forecast</span>
                    <span style="background: rgba(255,107,107,0.2); padding: 2px 6px; border-radius: 6px; font-size: 0.65em; color: #ff6b6b;">New Defects</span>
                </div>
                <div style="text-align: center; padding: 8px 0; flex: 1; display: flex; flex-direction: column; justify-content: center;">
                    <div style="font-size: 0.75em; color: #888; margin-bottom: 2px;">Next 3 Months</div>
                    <div style="font-size: 2em; font-weight: bold; color: #00d4ff;">{quarterly_forecast:.0f}</div>
                    <div style="font-size: 0.7em; color: #888; margin-top: 3px;">Of which <strong style="color: #ff6b6b;">~{expected_escapes:.0f}</strong> will escape to customers</div>
                </div>
                <div style="background: rgba(0,0,0,0.4); border-radius: 4px; padding: 6px; font-family: 'Courier New', monospace; border: 1px solid rgba(0,212,255,0.3);">
                    <div style="color: #00d4ff; font-size: 0.7em; margin-bottom: 3px;">📐 How we got this:</div>
                    <div style="color: #ccc; font-size: 0.7em; line-height: 1.5;">
                        <strong>Step 1:</strong> Avg = {avg_monthly_inflow:.1f} bugs/mo<br/>
                        <strong>Step 2:</strong> Qtr = {avg_monthly_inflow:.1f} × 3 = <strong>{quarterly_forecast:.0f}</strong> bugs<br/>
                        <strong>Step 3:</strong> Escape = {escape_rate:.0f}% (historical)<br/>
                        <strong>Result:</strong> {quarterly_forecast:.0f} × {escape_rate:.0f}% = <strong style="color: #ff6b6b;">{expected_escapes:.0f}</strong> escapes
                    </div>
                </div>
                <div style="font-size: 0.7em; margin-top: 5px; padding: 5px; background: {'rgba(255,107,107,0.15)' if expected_escapes >= 5 else 'rgba(243,156,18,0.15)' if expected_escapes >= 2 else 'rgba(46,204,113,0.15)'}; border-radius: 3px; color: {'#ff6b6b' if expected_escapes >= 5 else '#f39c12' if expected_escapes >= 2 else '#2ecc71'}; text-align: center;">
                    ⚡ {'⚠️ ' + f'{expected_escapes:.0f} customer bugs expected' if expected_escapes >= 2 else '✅ Low escape forecast'}
                </div>
            </div>
            
            <!-- Card 4: QUICK WIN -->
            <div class="chart-card" style="padding: 10px; display: flex; flex-direction: column;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                    <span style="color: #2ecc71; font-size: 0.9em; font-weight: bold;">🎯 Quick Win Potential</span>
                    <span style="background: rgba(46,204,113,0.2); padding: 2px 6px; border-radius: 6px; font-size: 0.65em; color: #2ecc71;">Top 3 Causes</span>
                </div>
                <div style="text-align: center; padding: 8px 0; flex: 1; display: flex; flex-direction: column; justify-content: center;">
                    <div style="font-size: 0.75em; color: #888; margin-bottom: 2px;">Fix top 3 causes → Eliminate</div>
                    <div style="font-size: 2em; font-weight: bold; color: #2ecc71;">{top_3_rc_count} bugs <span style="font-size: 0.5em; color: #888;">({top_3_rc_reduction:.0f}%)</span></div>
                </div>
                <div style="background: rgba(0,0,0,0.4); border-radius: 4px; padding: 6px; border: 1px solid rgba(46,204,113,0.3);">
                    <table style="width: 100%; font-size: 0.7em; border-collapse: collapse;">
                        <thead>
                            <tr style="color: #2ecc71; border-bottom: 1px solid rgba(46,204,113,0.3);">
                                <th style="text-align: left; padding: 2px;">What to Fix</th>
                                <th style="text-align: center; padding: 2px;">Total</th>
                                <th style="text-align: center; padding: 2px;">Open</th>
                                <th style="text-align: center; padding: 2px;">Sev2</th>
                            </tr>
                        </thead>
                        <tbody style="color: #ccc;">
                            {''.join(f'<tr><td style="padding: 2px; font-size: 0.95em;">{rc[:16]}</td><td style="text-align: center; color: #2ecc71; font-weight: bold;">{data["count"]}</td><td style="text-align: center; color: #ff6b6b;">{data["open"]}</td><td style="text-align: center; color: #f39c12;">{data["sev2"]}</td></tr>' for rc, data in top_root_causes[:3])}
                        </tbody>
                    </table>
                </div>
                <div style="font-size: 0.7em; margin-top: 5px; padding: 5px; background: rgba(46,204,113,0.15); border-radius: 3px; color: #2ecc71; text-align: center;">
                    🏆 Priority: <strong>{top_root_causes[0][0][:16]}</strong> ({top_root_causes[0][1]['open']} open)
                </div>
            </div>
        </div>
        
        <!-- ROW 3: Category Summary Table + Industry Benchmarks (Side by Side) -->
        <div class="summary-row">
            <!-- Category Summary Table - Vital Few (80%) -->
            <div style="background: rgba(46,204,113,0.08); border: 1px solid rgba(46,204,113,0.3); border-radius: 6px; padding: 6px 8px;">
                <div style="display: flex; justify-content: flex-end; align-items: center; margin-bottom: 4px;">
                    <span style="color: #888; font-size: 0.6em;">🟢 &lt;15% | 🟡 15-30% | 🔴 &gt;30%</span>
                </div>
                <table style="width: 100%; border-collapse: collapse; font-size: 0.75em;">
                    <thead>
                        <tr style="background: rgba(0,0,0,0.3); color: #00d4ff;">
                            <th style="padding: 4px 6px; text-align: left; cursor: help;" title="VITAL FEW DEFECT CATEGORIES&#10;━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━&#10;Top defect categories that account&#10;for 80% of all defects.&#10;&#10;Sorted by bug count (highest first)">Vital Few Defect Categories (80%)</th>
                            <th style="padding: 4px 6px; text-align: center; cursor: help;" title="BUG COUNT&#10;━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━&#10;Total number of Sev2 + Sev3 bugs&#10;in this category.&#10;&#10;Formula: Count(bugs where Category = X)">Bugs</th>
                            <th style="padding: 4px 6px; text-align: center; cursor: help;" title="PERCENTAGE OF TOTAL&#10;━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━&#10;What % of all bugs belong to&#10;this category.&#10;&#10;Formula: (Category Bugs ÷ Total Bugs) × 100">%</th>
                            <th style="padding: 4px 6px; text-align: center; cursor: help;" title="ESCAPE RATE (Esc%)&#10;━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━&#10;% of bugs in this category that&#10;escaped to Production or Field.&#10;&#10;Formula:&#10;(Production + Field bugs) ÷ Category Total × 100&#10;&#10;Color coding:&#10;🟢 Green: <15% (Good)&#10;🟡 Yellow: 15-30% (Moderate)&#10;🔴 Red: >30% (High risk)">Esc%</th>
                            <th style="padding: 4px 6px; text-align: center; cursor: help;" title="AVERAGE AGE (days)&#10;━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━&#10;Average age of open bugs in&#10;this category.&#10;&#10;Formula:&#10;Sum(Today - Created_Date) ÷ Bug_Count&#10;&#10;Color coding:&#10;🟢 Green: <180 days&#10;🟡 Yellow: 180-365 days&#10;🔴 Red: >365 days (1 year+)">Age</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(f"""
                        <tr style="background: rgba(0,0,0,0.15);">
                            <td style="padding: 3px 6px; color: #fff; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100px;" title="{cat}">{cat[:15]}{'.' if len(cat) > 15 else ''}</td>
                            <td style="padding: 3px 6px; text-align: center; color: #2ecc71; font-weight: bold;">{category_totals.get(cat, 0)}</td>
                            <td style="padding: 3px 6px; text-align: center; color: #fff;">{category_totals.get(cat, 0)/sum(totals)*100:.0f}%</td>
                            <td style="padding: 3px 6px; text-align: center; color: {'#ff6b6b' if category_escape_rates.get(cat, 0) > 30 else '#f39c12' if category_escape_rates.get(cat, 0) > 15 else '#2ecc71'}; font-weight: bold;">{category_escape_rates.get(cat, 0):.0f}%</td>
                            <td style="padding: 3px 6px; text-align: center; color: {'#ff6b6b' if category_avg_age.get(cat, 0) > 365 else '#f39c12' if category_avg_age.get(cat, 0) > 180 else '#2ecc71'};">{category_avg_age.get(cat, 0):.0f}d</td>
                        </tr>
                        """ for cat in categories[:vital_few_count])}
                    </tbody>
                </table>
            </div>
            
            <!-- Your Data vs Industry Benchmarks -->
            <div style="background: rgba(52,152,219,0.08); border: 1px solid rgba(52,152,219,0.3); border-radius: 6px; padding: 8px 10px; display: flex; flex-direction: column;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                    <span style="color: #3498db; font-size: 0.8em; font-weight: bold;">📊 Your Data vs Industry Benchmarks</span>
                    <span style="color: #888; font-size: 0.55em; cursor: help;" title="📚 CREDIBLE REFERENCE SOURCES&#10;━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━&#10;&#10;ESCAPE RATE:&#10;  📖 Capers Jones - Applied Software&#10;     Measurement (3rd Edition, 2008)&#10;  📖 IEEE Std 982.1 - Dictionary of&#10;     Measures for Software Quality&#10;&#10;RESOLUTION RATE:&#10;  📖 DORA State of DevOps Report&#10;     (Lead Time for Changes metric)&#10;  📖 ITIL v4 - Incident Management&#10;     Service Level Objectives&#10;&#10;DEFECT AGE:&#10;  📖 CISQ - Cost of Poor Quality in&#10;     Software (OMG, 2020)&#10;  📖 Microsoft SDL - Bug Bar&#10;     Response Time Guidelines&#10;&#10;Note: Benchmarks vary by industry,&#10;team size, and product complexity.&#10;Use as directional guidance.">📚 References</span>
                </div>
                <!-- Table Header -->
                <div style="display: grid; grid-template-columns: 1.2fr 1fr 1fr 0.8fr; gap: 4px; margin-bottom: 4px; padding: 4px 6px; background: rgba(0,0,0,0.3); border-radius: 4px;">
                    <div style="font-size: 0.6em; color: #888; font-weight: bold;">METRIC</div>
                    <div style="font-size: 0.6em; color: #f39c12; font-weight: bold; text-align: center;">YOUR DATA</div>
                    <div style="font-size: 0.6em; color: #3498db; font-weight: bold; text-align: center;">BENCHMARK</div>
                    <div style="font-size: 0.6em; color: #888; font-weight: bold; text-align: center;">STATUS</div>
                </div>
                <!-- Escape Rate Row -->
                <div style="display: grid; grid-template-columns: 1.2fr 1fr 1fr 0.8fr; gap: 4px; padding: 6px; background: rgba(0,0,0,0.15); border-radius: 4px; margin-bottom: 3px; align-items: center; cursor: help;" title="📊 ESCAPE RATE&#10;━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━&#10;&#10;What it measures:&#10;  % of bugs found in production&#10;  (escaped pre-release testing)&#10;&#10;Your Calculation:&#10;  Production bugs: {production_count}&#10;  Total bugs: {total_env}&#10;  Escape Rate = {production_count} ÷ {total_env} × 100 = {escape_rate:.1f}%&#10;&#10;Industry Scale:&#10;  • Best: &lt;5%  • Good: 5-15%&#10;  • Avg: 15-25%  • High: &gt;30%&#10;&#10;Source: Capers Jones, IEEE Std 982.1">
                    <div style="font-size: 0.7em; color: #ccc;">Escape Rate</div>
                    <div style="font-size: 0.9em; font-weight: bold; color: {'#2ecc71' if escape_rate < 15 else '#f39c12' if escape_rate < 30 else '#ff6b6b'}; text-align: center;">{escape_rate:.0f}%</div>
                    <div style="font-size: 0.75em; color: #3498db; text-align: center;">&lt;15%</div>
                    <div style="font-size: 0.65em; text-align: center; color: {'#2ecc71' if escape_rate < 15 else '#ff6b6b' if escape_rate > 30 else '#f39c12'};">{'✓ Good' if escape_rate < 15 else '✗ High' if escape_rate > 30 else '○ Avg'}</div>
                </div>
                <!-- Resolution Rate Row -->
                <div style="display: grid; grid-template-columns: 1.2fr 1fr 1fr 0.8fr; gap: 4px; padding: 6px; background: rgba(0,0,0,0.15); border-radius: 4px; margin-bottom: 3px; align-items: center; cursor: help;" title="📊 RESOLUTION RATE&#10;━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━&#10;&#10;What it measures:&#10;  Bugs closed per month (team velocity)&#10;&#10;Your Calculation:&#10;  Closed bugs: {len([b for b in filtered_bugs if b.get('State') in ['Closed', 'Resolved', 'Done', 'Verified']])}&#10;  Time period: {data_months} months&#10;  Rate = Closed ÷ Months = {resolution_rate:.1f}/mo&#10;&#10;Industry Scale:&#10;  • High: 5+/mo  • Good: 3-5/mo&#10;  • Avg: 1-3/mo  • Slow: &lt;1/mo&#10;&#10;Source: DORA, ITIL v4">
                    <div style="font-size: 0.7em; color: #ccc;">Resolution Rate</div>
                    <div style="font-size: 0.9em; font-weight: bold; color: {'#2ecc71' if resolution_rate >= 3 else '#f39c12' if resolution_rate >= 1 else '#ff6b6b'}; text-align: center;">{resolution_rate:.1f}/mo</div>
                    <div style="font-size: 0.75em; color: #3498db; text-align: center;">&gt;3/mo</div>
                    <div style="font-size: 0.65em; text-align: center; color: {'#2ecc71' if resolution_rate >= 3 else '#ff6b6b' if resolution_rate < 1 else '#f39c12'};">{'✓ Good' if resolution_rate >= 3 else '✗ Low' if resolution_rate < 1 else '○ Avg'}</div>
                </div>
                <!-- Avg Age Row -->
                <div style="display: grid; grid-template-columns: 1.2fr 1fr 1fr 0.8fr; gap: 4px; padding: 6px; background: rgba(0,0,0,0.15); border-radius: 4px; align-items: center; cursor: help;" title="📊 AVERAGE DEFECT AGE&#10;━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━&#10;&#10;What it measures:&#10;  How long bugs remain open (days)&#10;&#10;Your Calculation:&#10;  Total age: {total_age:,} days&#10;  Bug count: {len(filtered_bugs)}&#10;  Avg Age = {total_age:,} ÷ {len(filtered_bugs)} = {avg_age:.0f} days&#10;&#10;Industry Scale:&#10;  • Excellent: &lt;90d  • Good: 90-180d&#10;  • Avg: 180-365d  • Old: &gt;1 year&#10;&#10;Source: CISQ, Microsoft SDL">
                    <div style="font-size: 0.7em; color: #ccc;">Avg Defect Age</div>
                    <div style="font-size: 0.9em; font-weight: bold; color: {'#2ecc71' if avg_age < 180 else '#f39c12' if avg_age < 365 else '#ff6b6b'}; text-align: center;">{avg_age:.0f} days</div>
                    <div style="font-size: 0.75em; color: #3498db; text-align: center;">&lt;180 days</div>
                    <div style="font-size: 0.65em; text-align: center; color: {'#2ecc71' if avg_age < 180 else '#ff6b6b' if avg_age > 365 else '#f39c12'};">{'✓ Good' if avg_age < 180 else '✗ Old' if avg_age > 365 else '○ Avg'}</div>
                </div>
            </div>
        </div>
        
        <!-- ROW 4: Simplified Footer -->
        <div style="background: rgba(100,100,100,0.08); border: 1px solid rgba(100,100,100,0.2); border-radius: 6px; padding: 6px 12px;">
            <span style="color: #888; font-size: 0.7em; cursor: help;" title="Forecasts use linear projection based on historical data.&#10;&#10;Data Quality Score: {reliability_score:.0f}/100&#10;• Good (≥70): Reliable forecasts&#10;• Fair (50-69): Use as estimates&#10;• Limited (<50): Directional only&#10;&#10;Volatility: {inflow_cv:.0f}%&#10;• Low (<30%): Stable, predictable&#10;• Moderate (30-60%): Some variation&#10;• High (>60%): High uncertainty">📊 Forecast based on {data_months} months | Data Quality: {'Good' if reliability_score >= 70 else 'Fair' if reliability_score >= 50 else 'Limited'} ({reliability_score:.0f}/100) | Volatility: {'Low' if inflow_cv < 30 else 'Moderate' if inflow_cv < 60 else 'High'} ({inflow_cv:.0f}%)</span>
        </div>
    </div>
    
    <!-- TAB 2: Pareto Analysis -->
    <div id="tab-pareto" class="tab-content">
        <div style="padding: 15px; height: calc(100vh - 130px); display: flex; flex-direction: column;">
            <!-- Modern Filter Toggle Bar -->
            <div style="display: flex; justify-content: center; margin-bottom: 12px;">
                <div style="display: inline-flex; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); border-radius: 50px; padding: 4px; box-shadow: 0 4px 15px rgba(0,0,0,0.3);">
                    <button id="btnCategory" onclick="setParetoView('category')" class="pareto-btn active" style="padding: 10px 22px; border: none; border-radius: 50px; background: linear-gradient(135deg, #00d4ff, #0099cc); color: #000; font-weight: bold; cursor: pointer; transition: all 0.3s ease; margin: 0 2px; font-size: 0.9em;">
                        📂 Defect Categories
                    </button>
                    <button id="btnArea" onclick="setParetoView('area')" class="pareto-btn" style="padding: 10px 22px; border: none; border-radius: 50px; background: transparent; color: #888; font-weight: bold; cursor: pointer; transition: all 0.3s ease; margin: 0 2px; font-size: 0.9em;">
                        📍 By Area Path
                    </button>
                    <button id="btnVersion" onclick="setParetoView('version')" class="pareto-btn" style="padding: 10px 22px; border: none; border-radius: 50px; background: transparent; color: #888; font-weight: bold; cursor: pointer; transition: all 0.3s ease; margin: 0 2px; font-size: 0.9em;">
                        🏷️ By Version
                    </button>
                </div>
            </div>
            
            <!-- Chart Container - Larger -->
            <div style="flex: 1; min-height: 0; background: linear-gradient(180deg, #ffffff 0%, #f8f9fa 100%); border-radius: 12px; box-shadow: 0 6px 24px rgba(0,0,0,0.12); padding: 10px; margin-bottom: 10px;">
                <div id="paretoChart" style="height: 100%;"></div>
            </div>
            
            <!-- Dynamic Insight Cards - Compact -->
            <div id="paretoInsights" style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px;">
                <!-- Card 1: 80/20 Focus Area -->
                <div id="insight80-20" style="background: linear-gradient(135deg, #fff8e1 0%, #ffecb3 100%); border-radius: 10px; padding: 14px; box-shadow: 0 3px 10px rgba(255,193,7,0.15); border-left: 4px solid #ffc107; position: relative;">
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                        <span style="font-size: 1.2em;">🎯</span>
                        <span style="font-weight: bold; color: #f57c00; font-size: 0.95em;">80/20 FOCUS AREA</span>
                        <span title="Pareto Principle: ~20% of causes contribute to ~80% of defects. Items are sorted by total count, and cumulative % is calculated until reaching 80%." style="cursor: help; color: #f57c00; font-size: 0.8em; margin-left: auto;">ⓘ</span>
                    </div>
                    <div style="color: #5d4037; font-size: 0.95em; line-height: 1.5;">
                        <span id="insight80-20-text">Top <strong style="color: #e65100; font-size: 1.3em;">{pareto_80_index + 1}</strong> drive <strong style="color: #e65100;">80%</strong> of all defects</span>
                    </div>
                    <div id="insight80-20-detail" style="font-size: 0.85em; color: #6d4c41; margin-top: 8px; border-top: 2px solid #ffcc80; padding-top: 8px; background: rgba(255,255,255,0.5); border-radius: 5px; padding: 8px;">
                        <strong style="color: #e65100;">✅ RECOMMENDATION:</strong><br>
                        Assign dedicated owners to the top {pareto_80_index + 1}. Focus resources here for maximum impact.
                    </div>
                </div>
                
                <!-- Card 2: Quick Win -->
                <div id="insightPriority" style="background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%); border-radius: 10px; padding: 14px; box-shadow: 0 3px 10px rgba(76,175,80,0.15); border-left: 4px solid #4caf50; position: relative;">
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                        <span style="font-size: 1.2em;">🚀</span>
                        <span style="font-weight: bold; color: #2e7d32; font-size: 0.95em;">QUICK WIN TARGET</span>
                        <span title="The #1 ranked item by total defect count. Fixing this single category will have the highest impact on reducing your backlog." style="cursor: help; color: #2e7d32; font-size: 0.8em; margin-left: auto;">ⓘ</span>
                    </div>
                    <div id="insightPriority-text" style="color: #1b5e20; font-size: 0.95em; line-height: 1.5;">
                        <strong style="font-size: 1.1em;">{categories[0]}</strong><br>
                        <span style="background: #4caf50; color: white; padding: 3px 10px; border-radius: 12px; font-size: 1em; font-weight: bold;">{totals[0]} bugs</span> <span style="color: #388e3c;">({totals[0]/sum(totals)*100:.0f}% of total)</span>
                    </div>
                    <div id="insightPriority-detail" style="font-size: 0.85em; color: #2e7d32; margin-top: 8px; border-top: 2px solid #81c784; padding-top: 8px; background: rgba(255,255,255,0.5); border-radius: 5px; padding: 8px;">
                        <strong style="color: #1b5e20;">✅ RECOMMENDATION:</strong><br>
                        Create a sprint dedicated to "{categories[0][:25]}" bugs. Single biggest impact!
                    </div>
                </div>
                
                <!-- Card 3: Time to Clear -->
                <div id="insightEffort" style="background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%); border-radius: 10px; padding: 14px; box-shadow: 0 3px 10px rgba(33,150,243,0.15); border-left: 4px solid #2196f3; position: relative;">
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                        <span style="font-size: 1.2em;">⏱️</span>
                        <span style="font-weight: bold; color: #1565c0; font-size: 0.95em;">TIME TO CLEAR TOP 3</span>
                        <span title="Estimated time to resolve the top 3 highest-count items. Formula: (Sum of bugs in top 3) ÷ (Monthly resolution rate). Resolution rate = {resolution_rate:.1f} bugs/month." style="cursor: help; color: #1565c0; font-size: 0.8em; margin-left: auto;">ⓘ</span>
                    </div>
                    <div id="insightEffort-text" style="color: #0d47a1; font-size: 0.95em; line-height: 1.5;">
                        <span style="font-size: 1.5em; font-weight: bold; color: #1976d2;">{sum(totals[:3])/max(resolution_rate, 0.1):.0f} months</span><br>
                        <span style="color: #1565c0;">to clear <strong>{sum(totals[:3])}</strong> bugs ({sum(totals[:3])/sum(totals)*100:.0f}% of backlog)</span>
                    </div>
                    <div id="insightEffort-detail" style="font-size: 0.85em; color: #1565c0; margin-top: 8px; border-top: 2px solid #64b5f6; padding-top: 8px; background: rgba(255,255,255,0.5); border-radius: 5px; padding: 8px;">
                        <strong style="color: #0d47a1;">✅ RECOMMENDATION:</strong><br>
                        At {resolution_rate:.1f} bugs/mo, increase capacity to 2×{resolution_rate:.1f}={resolution_rate*2:.0f}/mo to halve this time.
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <!-- TAB 3: Heatmap -->
    <div id="tab-heatmap" class="tab-content">
        <div class="heatmap-container" style="padding: 15px; height: calc(100vh - 130px); display: flex; flex-direction: column;">
            <!-- Toggle Buttons - Same style as Pareto -->
            <div style="display: flex; justify-content: center; margin-bottom: 12px;">
                <div style="display: inline-flex; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); border-radius: 50px; padding: 4px; box-shadow: 0 4px 15px rgba(0,0,0,0.3);">
                    <button id="btnHeatmapCategory" onclick="setHeatmapView('category')" class="heatmap-btn active" style="padding: 10px 22px; border: none; border-radius: 50px; background: linear-gradient(135deg, #00d4ff, #0099cc); color: #000; font-weight: bold; cursor: pointer; transition: all 0.3s ease; margin: 0 2px; font-size: 0.9em;">
                        📂 Category vs Area Path
                    </button>
                    <button id="btnHeatmapVersion" onclick="setHeatmapView('version')" class="heatmap-btn" style="padding: 10px 22px; border: none; border-radius: 50px; background: transparent; color: #888; font-weight: bold; cursor: pointer; transition: all 0.3s ease; margin: 0 2px; font-size: 0.9em;">
                        🏷️ Category vs Version
                    </button>
                </div>
            </div>
            
            <!-- Chart Container -->
            <div style="flex: 1; min-height: 0; background: linear-gradient(180deg, #ffffff 0%, #f8f9fa 100%); border-radius: 12px; box-shadow: 0 6px 24px rgba(0,0,0,0.12); padding: 10px; margin-bottom: 10px;">
                <div id="heatmapChart" style="height: 100%;"></div>
            </div>
            
            <!-- Dynamic Insight Cards -->
            <div id="heatmapInsights" style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px;">
                <div id="heatmapHotspot" style="background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%); border-radius: 10px; padding: 12px; box-shadow: 0 3px 10px rgba(33,150,243,0.15); border-left: 4px solid #2196f3;">
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
                        <span style="font-size: 1.1em;">🔥</span>
                        <span style="font-weight: bold; color: #1565c0; font-size: 0.85em;">Hotspot Analysis</span>
                    </div>
                    <div id="heatmapHotspot-text" style="color: #0d47a1; font-size: 0.8em; line-height: 1.4;">
                        Top hotspot: <strong>{categories[0]}</strong> in <strong>{top_areas[0] if top_areas else 'Unknown'}</strong> area
                    </div>
                </div>
                
                <div id="heatmapRisk" style="background: linear-gradient(135deg, #fff8e1 0%, #ffecb3 100%); border-radius: 10px; padding: 12px; box-shadow: 0 3px 10px rgba(255,193,7,0.15); border-left: 4px solid #ffc107;">
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
                        <span style="font-size: 1.1em;">⚠️</span>
                        <span style="font-weight: bold; color: #f57c00; font-size: 0.85em;">Risk Zone</span>
                    </div>
                    <div id="heatmapRisk-text" style="color: #5d4037; font-size: 0.8em; line-height: 1.4;">
                        {len([c for c in categories if category_totals.get(c,0) > 10])} categories have >10 bugs. Darker cells = higher concentration.
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <!-- TAB 4: Dimensions -->
    <div id="tab-dimensions" class="tab-content">
        <div style="padding: 15px; height: calc(100vh - 130px); display: flex; flex-direction: column;">
            <!-- Combined Heatmap: SDLC Phase vs Test Phase -->
            <div style="flex: 1; min-height: 0; background: linear-gradient(180deg, #ffffff 0%, #f8f9fa 100%); border-radius: 12px; box-shadow: 0 6px 24px rgba(0,0,0,0.12); padding: 15px; margin-bottom: 10px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <div style="font-weight: bold; color: #333; font-size: 1em;">📊 SDLC Phase vs Test Phase Detection Matrix</div>
                    <div style="font-size: 0.75em; color: #666;">Standards: IEEE 12207 (SDLC) × ISTQB/IEEE 829 (Test)</div>
                </div>
                <div id="dimensionHeatmap" style="height: calc(100% - 30px);"></div>
            </div>
            
            <!-- Actionable Insight Cards -->
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px;">
                <!-- Process Gap Insight -->
                <div style="background: linear-gradient(135deg, #ffebee 0%, #ffcdd2 100%); border-radius: 10px; padding: 12px; box-shadow: 0 3px 10px rgba(244,67,54,0.15); border-left: 4px solid #f44336;">
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
                        <span style="font-size: 1.1em;">🔴</span>
                        <span style="font-weight: bold; color: #c62828; font-size: 0.85em;">Critical Hotspot</span>
                        <span title="Calculation: Find the cell with maximum bug count in the SDLC Phase × Test Phase matrix. This identifies where defects are most concentrated - bugs introduced in a specific SDLC phase and detected at a specific testing phase." style="cursor: help; color: #c62828; font-size: 0.75em; margin-left: auto;">ⓘ</span>
                    </div>
                    <div style="color: #b71c1c; font-size: 0.8em; line-height: 1.4;">
                        <strong>{max_sdlc_test[2]}</strong> bugs introduced in <strong>{max_sdlc_test[0]}</strong> found at <strong>{max_sdlc_test[1]}</strong>
                    </div>
                    <div style="font-size: 0.7em; color: #d32f2f; margin-top: 4px; border-top: 1px dashed #ef9a9a; padding-top: 4px;">
                        <strong>Action:</strong> Add code reviews in {max_sdlc_test[0]} phase
                    </div>
                </div>
                
                <!-- Shift-Left Opportunity -->
                <div style="background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%); border-radius: 10px; padding: 12px; box-shadow: 0 3px 10px rgba(76,175,80,0.15); border-left: 4px solid #4caf50;">
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
                        <span style="font-size: 1.1em;">⬅️</span>
                        <span style="font-weight: bold; color: #2e7d32; font-size: 0.85em;">Shift-Left Potential</span>
                        <span title="Calculation: Sum of all bugs where Test Phase = 'System Test' or 'Integration Test'. These are bugs found late in the testing cycle that could potentially be caught earlier with unit/component testing. Formula: late_found = ΣSystem Test + ΣIntegration Test" style="cursor: help; color: #2e7d32; font-size: 0.75em; margin-left: auto;">ⓘ</span>
                    </div>
                    <div style="color: #1b5e20; font-size: 0.8em; line-height: 1.4;">
                        <strong>{late_found}</strong> bugs ({late_found*100//max(total_bugs,1)}%) found late in System/Integration Test
                    </div>
                    <div style="font-size: 0.7em; color: #388e3c; margin-top: 4px; border-top: 1px dashed #a5d6a7; padding-top: 4px;">
                        <strong>Action:</strong> Invest in unit tests to catch {late_found*30//100}+ earlier
                    </div>
                </div>
                
                <!-- Root Cause Focus -->
                <div style="background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%); border-radius: 10px; padding: 12px; box-shadow: 0 3px 10px rgba(33,150,243,0.15); border-left: 4px solid #2196f3;">
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
                        <span style="font-size: 1.1em;">🎯</span>
                        <span style="font-weight: bold; color: #1565c0; font-size: 0.85em;">Prevention Focus</span>
                        <span title="Calculation: Based on Defect Origin classification (Capers Jones methodology). Code = bugs from coding errors/implementation mistakes. Design = bugs from design flaws/architecture issues. Helps prioritize code quality tools vs design review improvements." style="cursor: help; color: #1565c0; font-size: 0.75em; margin-left: auto;">ⓘ</span>
                    </div>
                    <div style="color: #0d47a1; font-size: 0.8em; line-height: 1.4;">
                        <strong>{code_origin}</strong> bugs ({code_origin*100//max(total_bugs,1)}%) from Code, <strong>{design_origin}</strong> ({design_origin*100//max(total_bugs,1)}%) from Design
                    </div>
                    <div style="font-size: 0.7em; color: #1976d2; margin-top: 4px; border-top: 1px dashed #90caf9; padding-top: 4px;">
                        <strong>Action:</strong> {'Improve design reviews' if design_origin > code_origin*0.3 else 'Focus on code quality tools'}
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <div class="footer">
        <p>Dashboard A: Overview & Quick Win Metrics | Generated: {datetime.now().strftime('%B %d, %Y at %H:%M')}</p>
        <p>DefectAnalyzer v4.0 | Siemens PCS7 Telecontrol</p>
    </div>
    
    <!-- Bug Detail Modal Container -->
    <div id="modalContainer"></div>
    
    <script>
        // Tab switching with immediate chart initialization
        function showTab(tabId, clickedTab) {{
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            
            clickedTab.classList.add('active');
            document.getElementById('tab-' + tabId).classList.add('active');
            
            // Double requestAnimationFrame ensures DOM is fully painted before chart render
            requestAnimationFrame(() => {{
                requestAnimationFrame(() => {{
                    if (tabId === 'pareto') {{
                        initParetoChart();
                        // Force resize to ensure chart fits container
                        const chartEl = document.getElementById('paretoChart');
                        if (chartEl && chartEl.data) {{
                            Plotly.Plots.resize(chartEl);
                        }}
                    }} else if (tabId === 'heatmap') {{
                        initHeatmapChart();
                        const chartEl = document.getElementById('heatmapChart');
                        if (chartEl && chartEl.data) {{
                            Plotly.Plots.resize(chartEl);
                        }}
                    }} else if (tabId === 'dimensions') {{
                        initDimensionCharts();
                    }}
                }});
            }});
        }}
        
        // Bug data for modals (by category, area, version)
        const paretoBugData = {json.dumps(pareto_bug_data)};
        const areaBugData = {json.dumps(area_bug_data)};
        const versionBugData = {json.dumps(version_bug_data)};
        
        // Bug data for heatmap and dimension click-to-filter
        const heatmapBugData = {json.dumps(heatmap_bug_data)};
        const heatmapVersionBugData = {json.dumps(heatmap_version_bug_data)};
        const dimensionBugData = {json.dumps(dimension_bug_data)};
        
        const categories = {json.dumps(categories)};
        const sev2Counts = {sev2_counts};
        const sev3Counts = {sev3_counts};
        
        // Data for different groupings
        const paretoAreas = {json.dumps(pareto_areas)};
        const paretoAreaSev2 = {pareto_area_sev2};
        const paretoAreaSev3 = {pareto_area_sev3};
        const paretoVersions = {json.dumps(pareto_versions)};
        const paretoVersionSev2 = {pareto_version_sev2};
        const paretoVersionSev3 = {pareto_version_sev3};
        
        // Track current Pareto view mode
        let currentParetoView = 'category';
        
        // Set active Pareto view with button toggle
        function setParetoView(view) {{
            currentParetoView = view;  // Track current view
            // Update button styles
            document.querySelectorAll('.pareto-btn').forEach(btn => {{
                btn.style.background = 'transparent';
                btn.style.color = '#888';
            }});
            const activeBtn = document.getElementById('btn' + view.charAt(0).toUpperCase() + view.slice(1));
            if (activeBtn) {{
                activeBtn.style.background = 'linear-gradient(135deg, #00d4ff, #0099cc)';
                activeBtn.style.color = '#000';
            }}
            updateParetoChart(view);
        }}
        
        // Update Pareto chart based on view selection
        function updateParetoChart(groupBy) {{
            let xLabels, sev2Data, sev3Data, xTitle, itemLabel;
            
            if (groupBy === 'category') {{
                xLabels = categories;
                sev2Data = sev2Counts;
                sev3Data = sev3Counts;
                xTitle = 'Defect Category';
                itemLabel = 'categories';
            }} else if (groupBy === 'area') {{
                xLabels = paretoAreas;
                sev2Data = paretoAreaSev2;
                sev3Data = paretoAreaSev3;
                xTitle = 'Area Path';
                itemLabel = 'areas';
            }} else {{
                xLabels = paretoVersions;
                sev2Data = paretoVersionSev2;
                sev3Data = paretoVersionSev3;
                xTitle = 'Found in Version';
                itemLabel = 'versions';
            }}
            
            // Calculate cumulative percentage
            const totals = sev2Data.map((v, i) => v + sev3Data[i]);
            const totalSum = totals.reduce((a, b) => a + b, 0);
            let cumSum = 0;
            const cumPct = totals.map(v => {{ cumSum += v; return totalSum > 0 ? (cumSum / totalSum) * 100 : 0; }});
            
            // Find 80% threshold index
            let pareto80Index = cumPct.findIndex(v => v >= 80);
            if (pareto80Index < 0) pareto80Index = cumPct.length - 1;
            
            // Update dynamic insight cards
            updateParetoInsights(xLabels, totals, pareto80Index, itemLabel);
            
            // Sev3 trace FIRST (at bottom), Sev2 trace SECOND (stacks on TOP)
            Plotly.react('paretoChart', [
                {{ 
                    x: xLabels, 
                    y: sev3Data, 
                    name: '🟠 Severity 3 (Medium)', 
                    type: 'bar', 
                    marker: {{ 
                        color: sev3Data.map((v, i) => i === 0 ? '#ff8a65' : '#ffab91'),
                        line: {{ color: '#ff7043', width: 1 }}
                    }},
                    hovertemplate: '<b>%{{x}}</b><br><span style="color:#ff7043">●</span> Severity 3: <b>%{{y}}</b><extra></extra>'
                }},
                {{ 
                    x: xLabels, 
                    y: sev2Data, 
                    name: '🔴 Severity 2 (High)', 
                    type: 'bar', 
                    text: totals.map(t => t > 0 ? t : ''),
                    textposition: 'outside',
                    textfont: {{ size: 10, color: '#333', family: 'Segoe UI' }},
                    marker: {{ 
                        color: sev2Data.map((v, i) => i === 0 ? '#b71c1c' : '#e53935'),
                        line: {{ color: '#b71c1c', width: 1 }}
                    }},
                    hovertemplate: '<b>%{{x}}</b><br><span style="color:#e53935">●</span> Severity 2: <b>%{{y}}</b><br>Total: %{{customdata}}<extra></extra>',
                    customdata: totals
                }},
                {{ 
                    x: xLabels, 
                    y: cumPct, 
                    name: '📈 Cumulative %', 
                    type: 'scatter', 
                    mode: 'lines+markers+text', 
                    text: cumPct.map((v, i) => i % 2 === 0 || i === cumPct.length - 1 ? v.toFixed(0) + '%' : ''),
                    textposition: 'top center',
                    textfont: {{ size: 9, color: '#1565c0' }},
                    yaxis: 'y2', 
                    line: {{ color: '#1976d2', width: 4, shape: 'spline' }}, 
                    marker: {{ size: 10, color: '#1976d2', line: {{ color: '#fff', width: 2 }} }},
                    hovertemplate: '<b>%{{x}}</b><br>📊 Cumulative: <b>%{{y:.1f}}%</b><extra></extra>'
                }}
            ], {{
                barmode: 'stack',
                paper_bgcolor: 'transparent',
                plot_bgcolor: 'transparent',
                font: {{ family: 'Segoe UI, sans-serif', size: 12 }},
                margin: {{ l: 55, r: 55, t: 40, b: 90 }},
                xaxis: {{ 
                    tickangle: -40, 
                    title: {{ text: xTitle, font: {{ size: 13, color: '#555' }}, standoff: 15 }},
                    gridcolor: 'rgba(0,0,0,0.05)',
                    tickfont: {{ size: 10 }}
                }},
                yaxis: {{ 
                    title: {{ text: 'Defect Count', font: {{ size: 13, color: '#555' }}, standoff: 10 }},
                    gridcolor: 'rgba(0,0,0,0.08)',
                    tickfont: {{ size: 10 }}
                }},
                yaxis2: {{ 
                    title: {{ text: 'Cumulative %', font: {{ size: 13, color: '#1976d2' }}, standoff: 10 }},
                    overlaying: 'y', 
                    side: 'right', 
                    range: [0, 105],
                    tickfont: {{ size: 10, color: '#1976d2' }},
                    showgrid: false
                }},
                legend: {{ 
                    orientation: 'h', 
                    y: 1.08, 
                    x: 0.5, 
                    xanchor: 'center',
                    bgcolor: 'rgba(255,255,255,0.9)',
                    bordercolor: 'rgba(0,0,0,0.1)',
                    borderwidth: 1,
                    font: {{ size: 10 }}
                }},
                shapes: [{{ 
                    type: 'line', 
                    x0: -0.5, 
                    x1: xLabels.length - 0.5, 
                    y0: 80, 
                    y1: 80, 
                    yref: 'y2', 
                    line: {{ color: '#e74c3c', dash: 'dot', width: 2 }}
                }}],
                hoverlabel: {{
                    bgcolor: 'white',
                    bordercolor: '#ddd',
                    font: {{ size: 11, color: '#333' }}
                }}
            }}, {{responsive: true}});
        }}
        
        // Attach Pareto chart events (called after chart is rendered)
        function attachParetoEvents() {{
            const paretoChartEl = document.getElementById('paretoChart');
            if (!paretoChartEl) return;
            
            // Remove any existing listeners first
            paretoChartEl.removeAllListeners && paretoChartEl.removeAllListeners('plotly_click');
            paretoChartEl.removeAllListeners && paretoChartEl.removeAllListeners('plotly_hover');
            paretoChartEl.removeAllListeners && paretoChartEl.removeAllListeners('plotly_unhover');
            
            // Add click event to show bug modal
            paretoChartEl.on('plotly_click', function(data) {{
                const point = data.points[0];
                const xValue = point.x;
                const curveNumber = point.curveNumber;
                const clickedSeverity = curveNumber === 0 ? 3 : (curveNumber === 1 ? 2 : null);
                
                let bugData;
                let groupLabel;
                if (currentParetoView === 'category') {{
                    bugData = paretoBugData[xValue] || [];
                    groupLabel = xValue;
                }} else if (currentParetoView === 'area') {{
                    bugData = areaBugData[xValue] || [];
                    groupLabel = 'Area: ' + xValue;
                }} else {{
                    bugData = versionBugData[xValue] || [];
                    groupLabel = 'Version: ' + xValue;
                }}
                
                if (clickedSeverity !== null) {{
                    bugData = bugData.filter(b => b.severity === clickedSeverity);
                    const sevLabel = clickedSeverity === 2 ? 'Severity 2 (High)' : 'Severity 3 (Medium)';
                    showBugModal(groupLabel + ' - ' + sevLabel, bugData);
                }} else {{
                    showBugModal(groupLabel, bugData);
                }}
            }});
            
            // Add hover event to show bug list preview
            paretoChartEl.on('plotly_hover', function(data) {{
                const point = data.points[0];
                const xValue = point.x;
                const curveNumber = point.curveNumber;
                
                if (curveNumber > 1) return;
                
                const severity = curveNumber === 0 ? 3 : 2;
                let bugData;
                if (currentParetoView === 'category') {{
                    bugData = paretoBugData[xValue] || [];
                }} else if (currentParetoView === 'area') {{
                    bugData = areaBugData[xValue] || [];
                }} else {{
                    bugData = versionBugData[xValue] || [];
                }}
                
                bugData = bugData.filter(b => b.severity === severity);
                
                if (bugData.length > 0) {{
                    const bugIds = bugData.slice(0, 8).map(b => b.id).join(', ');
                    const moreText = bugData.length > 8 ? ' + ' + (bugData.length - 8) + ' more...' : '';
                    const sevLabel = severity === 2 ? 'Sev 2' : 'Sev 3';
                    
                    showHoverTooltip(
                        xValue + ' (' + sevLabel + '): ' + bugData.length + ' bugs',
                        'Bug IDs: ' + bugIds + moreText
                    );
                }}
            }});
            
            paretoChartEl.on('plotly_unhover', function() {{
                hideHoverTooltip();
            }});
        }}
        
        // Update insight cards dynamically based on current filter
        function updateParetoInsights(labels, totals, pareto80Index, itemLabel) {{
            const totalSum = totals.reduce((a, b) => a + b, 0);
            const resRate = {resolution_rate:.1f};
            
            // 80/20 Focus Area Insight - with actionable recommendation
            document.getElementById('insight80-20-text').innerHTML = 
                '<strong style="color: #e65100;">' + (pareto80Index + 1) + '</strong> ' + itemLabel + ' drive <strong style="color: #e65100;">80%</strong> of defects';
            document.getElementById('insight80-20-detail').innerHTML = 
                '<strong>Action:</strong> Assign dedicated owner to top ' + (pareto80Index + 1) + ' ' + itemLabel;
            
            // Quick Win Insight - with sprint recommendation
            const topItem = labels[0];
            const topCount = totals[0];
            const topPct = totalSum > 0 ? Math.round((topCount / totalSum) * 100) : 0;
            const truncatedTop = topItem.length > 20 ? topItem.substring(0, 20) + '...' : topItem;
            document.getElementById('insightPriority-text').innerHTML = 
                'Fix <strong>' + topItem + '</strong> • <span style="background: #4caf50; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.9em;">' + topCount + ' bugs</span> <span style="color: #666;">(' + topPct + '%)</span>';
            document.getElementById('insightPriority-detail').innerHTML = 
                '<strong>Action:</strong> Schedule sprint focus on "' + truncatedTop + '"';
            
            // Effort Insight (Top 3) - with resource recommendation
            const top3Sum = totals.slice(0, 3).reduce((a, b) => a + b, 0);
            const months = resRate > 0 ? Math.round(top3Sum / resRate) : 'N/A';
            const top3Pct = totalSum > 0 ? Math.round((top3Sum / totalSum) * 100) : 0;
            
            // Get individual top 3 items with counts
            const item1 = labels[0] ? (labels[0].length > 12 ? labels[0].substring(0, 12) + '...' : labels[0]) : 'N/A';
            const item2 = labels[1] ? (labels[1].length > 12 ? labels[1].substring(0, 12) + '...' : labels[1]) : 'N/A';
            const item3 = labels[2] ? (labels[2].length > 12 ? labels[2].substring(0, 12) + '...' : labels[2]) : 'N/A';
            const count1 = totals[0] || 0;
            const count2 = totals[1] || 0;
            const count3 = totals[2] || 0;
            
            // Calculate recommended team size
            const targetMonths = 3;
            const devNeeded = resRate > 0 ? Math.ceil(top3Sum / (resRate * targetMonths)) : 1;
            
            document.getElementById('insightEffort-text').innerHTML = 
                '<span style="font-size: 1.4em; font-weight: bold; color: #1976d2;">' + months + ' mo</span>' +
                '<span style="color: #1565c0; margin-left: 8px;">to clear ' + top3Sum + ' bugs (' + top3Pct + '%)</span>';
            document.getElementById('insightEffort-detail').innerHTML = 
                '<div style="display: flex; justify-content: space-between; font-size: 0.95em;">' +
                '<span>📌 ' + item1 + ': ' + count1 + '</span>' +
                '<span>📌 ' + item2 + ': ' + count2 + '</span>' +
                '<span>📌 ' + item3 + ': ' + count3 + '</span>' +
                '</div>' +
                '<div style="margin-top: 3px; color: #1976d2;"><strong>Action:</strong> Need ' + devNeeded + ' dev(s) to clear in 3 months</div>';
        }}
        
        // Hover tooltip for showing bug list preview
        let hoverTooltipEl = null;
        let lastMouseX = 0, lastMouseY = 0;
        
        // Track mouse position globally for tooltip placement
        document.addEventListener('mousemove', function(e) {{
            lastMouseX = e.clientX;
            lastMouseY = e.clientY;
        }});
        
        function showHoverTooltip(title, content) {{
            if (!hoverTooltipEl) {{
                hoverTooltipEl = document.createElement('div');
                hoverTooltipEl.id = 'hoverTooltip';
                hoverTooltipEl.style.cssText = `
                    position: fixed;
                    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                    color: #fff;
                    padding: 12px 16px;
                    border-radius: 8px;
                    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
                    border: 1px solid #00d4ff;
                    z-index: 10000;
                    max-width: 400px;
                    font-size: 12px;
                    pointer-events: none;
                `;
                document.body.appendChild(hoverTooltipEl);
            }}
            
            hoverTooltipEl.innerHTML = `
                <div style="font-weight: bold; color: #00d4ff; margin-bottom: 6px; font-size: 13px;">${{title}}</div>
                <div style="color: #ccc; line-height: 1.4;">${{content}}</div>
                <div style="color: #888; font-size: 10px; margin-top: 8px; border-top: 1px solid #333; padding-top: 6px;">💡 Click bar to see full bug list</div>
            `;
            
            // Position tooltip near last known cursor position
            hoverTooltipEl.style.left = (lastMouseX + 15) + 'px';
            hoverTooltipEl.style.top = (lastMouseY + 15) + 'px';
            hoverTooltipEl.style.display = 'block';
        }}
        
        function hideHoverTooltip() {{
            if (hoverTooltipEl) {{
                hoverTooltipEl.style.display = 'none';
            }}
        }}
        
        // Create bug modal with export button
        let currentModalBugs = [];
        let currentModalTitle = '';
        
        function showBugModal(title, bugs) {{
            currentModalBugs = bugs;
            currentModalTitle = title;
            
            let rows = bugs.map((bug, i) => `
                <tr style="background: ${{i % 2 === 0 ? '#f8f9fa' : 'white'}}">
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>${{bug.id}}</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd; max-width: 350px;">${{bug.title}}</td>
                    <td style="padding: 8px; text-align: center; border: 1px solid #ddd;">
                        <span class="sev-badge sev-${{bug.severity}}">Sev ${{bug.severity}}</span>
                    </td>
                    <td style="padding: 8px; border: 1px solid #ddd;">${{bug.state}}</td>
                    <td style="padding: 8px; border: 1px solid #ddd; font-size: 11px;">${{bug.root_cause}}</td>
                    <td style="padding: 8px; border: 1px solid #ddd; font-size: 11px;">${{bug.created_date}}</td>
                </tr>
            `).join('');
            
            document.getElementById('modalContainer').innerHTML = `
                <div class="modal" onclick="this.remove()">
                    <div class="modal-content" onclick="event.stopPropagation()">
                        <div class="modal-header">
                            <h2 style="color: #2c3e50;">🔍 ${{title}} (${{bugs.length}} defects)</h2>
                            <div style="display: flex; gap: 10px;">
                                <button onclick="exportBugsToCSV()" style="background: linear-gradient(135deg, #4caf50, #388e3c); color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-weight: bold; display: flex; align-items: center; gap: 6px; box-shadow: 0 2px 8px rgba(76,175,80,0.3);">
                                    📥 Export CSV
                                </button>
                                <button class="modal-close" onclick="document.querySelector('.modal').remove()">✖ Close</button>
                            </div>
                        </div>
                        <table class="bug-table">
                            <thead>
                                <tr>
                                    <th>Bug ID</th>
                                    <th>Title</th>
                                    <th>Severity</th>
                                    <th>State</th>
                                    <th>Root Cause</th>
                                    <th>Created</th>
                                </tr>
                            </thead>
                            <tbody>${{rows}}</tbody>
                        </table>
                    </div>
                </div>
            `;
        }}
        
        // Export bugs to CSV
        function exportBugsToCSV() {{
            if (!currentModalBugs || currentModalBugs.length === 0) {{
                alert('No bugs to export');
                return;
            }}
            
            // CSV header
            const headers = ['Bug ID', 'Title', 'Severity', 'State', 'Root Cause', 'Created Date'];
            
            // CSV rows
            const csvRows = [headers.join(',')];
            currentModalBugs.forEach(bug => {{
                const row = [
                    bug.id,
                    '"' + (bug.title || '').replace(/"/g, '""') + '"',
                    bug.severity,
                    bug.state,
                    '"' + (bug.root_cause || '').replace(/"/g, '""') + '"',
                    bug.created_date
                ];
                csvRows.push(row.join(','));
            }});
            
            // Create and download
            const csvContent = csvRows.join('\\n');
            const blob = new Blob([csvContent], {{ type: 'text/csv;charset=utf-8;' }});
            const link = document.createElement('a');
            const filename = currentModalTitle.replace(/[^a-z0-9]/gi, '_') + '_bugs.csv';
            link.href = URL.createObjectURL(blob);
            link.download = filename;
            link.click();
            URL.revokeObjectURL(link.href);
        }}
        
        // Escape Rate Chart (Tab 1 - always visible initially)
        Plotly.newPlot('escapeChart', [{{
            values: [{production_count}, {test_count}],
            labels: ['Escaped', 'Caught'],
            type: 'pie',
            hole: 0.55,
            marker: {{ colors: ['#ff6b6b', '#00ff7f'] }},
            textinfo: 'percent',
            textposition: 'inside',
            textfont: {{ size: 11, color: '#fff' }},
            hovertemplate: '<b>%{{label}}</b><br>Count: %{{value}}<br>%{{percent}}<extra></extra>'
        }}], {{
            paper_bgcolor: 'rgba(0,0,0,0)',
            font: {{ color: '#e0e0e0', size: 10 }},
            margin: {{ l: 5, r: 5, t: 25, b: 5 }},
            showlegend: true,
            legend: {{ 
                orientation: 'h', 
                x: 0.5, 
                xanchor: 'center', 
                y: 1.15,
                font: {{ size: 9, color: '#ccc' }}
            }},
            annotations: [{{ text: '{escape_rate:.0f}%', showarrow: false, font: {{ size: 14, color: '#ff6b6b', family: 'Arial Black' }}, y: 0.5 }}]
        }}, {{responsive: true}});
        
        // Track which charts have been initialized
        const chartsInitialized = {{ pareto: false, heatmap: false, dimensions: false }};
        
        // Lazy initialization: Pareto Chart
        function initParetoChart() {{
            if (chartsInitialized.pareto) return;
            updateParetoChart('category');  // Initialize with category view
            
            // Attach events after a short delay to ensure chart is fully rendered
            setTimeout(function() {{
                attachParetoEvents();
            }}, 100);
            
            chartsInitialized.pareto = true;
        }}
        
        // Heatmap data for different views
        const heatmapCategoryMatrix = {heatmap_matrix};
        const heatmapAreas = {top_areas};
        const heatmapCategories = {categories};
        const heatmapVersionMatrix = {heatmap_version_matrix};
        const heatmapVersions = {top_versions_heatmap};
        
        // Track current heatmap view
        let currentHeatmapView = 'category';
        
        // Set heatmap view with button toggle
        function setHeatmapView(view) {{
            currentHeatmapView = view;
            document.querySelectorAll('.heatmap-btn').forEach(btn => {{
                btn.style.background = 'transparent';
                btn.style.color = '#888';
            }});
            const activeBtn = document.getElementById('btnHeatmap' + view.charAt(0).toUpperCase() + view.slice(1));
            if (activeBtn) {{
                activeBtn.style.background = 'linear-gradient(135deg, #00d4ff, #0099cc)';
                activeBtn.style.color = '#000';
            }}
            updateHeatmapChart(view);
        }}
        
        // Update heatmap based on view
        function updateHeatmapChart(viewType) {{
            let zData, xLabels, yLabels, xTitle, yTitle, hoverTemplate;
            
            if (viewType === 'category') {{
                // Category vs Area Path: Categories on X-axis, Areas on Y-axis
                // Transpose the original matrix (which has categories as rows, areas as columns)
                zData = heatmapAreas.map((area, aIdx) => 
                    heatmapCategories.map((cat, cIdx) => heatmapCategoryMatrix[cIdx][aIdx])
                );
                xLabels = heatmapCategories;
                yLabels = heatmapAreas;
                xTitle = 'Category';
                yTitle = 'Area Path';
                hoverTemplate = '<b>Area: %{{y}}</b><br>Category: %{{x}}<br>Count: <b>%{{z}}</b><extra></extra>';
            }} else {{
                // Category vs Version: Categories on X-axis, Versions on Y-axis
                zData = heatmapVersionMatrix;
                xLabels = heatmapCategories;
                yLabels = heatmapVersions;
                xTitle = 'Category';
                yTitle = 'Version';
                hoverTemplate = '<b>Version: %{{y}}</b><br>Category: %{{x}}<br>Count: <b>%{{z}}</b><extra></extra>';
            }}
            
            // Find max value for annotation
            let maxVal = 0, maxX = '', maxY = '';
            zData.forEach((row, yIdx) => {{
                row.forEach((val, xIdx) => {{
                    if (val > maxVal) {{
                        maxVal = val;
                        maxX = xLabels[xIdx];
                        maxY = yLabels[yIdx];
                    }}
                }});
            }});
            
            // Update insight cards
            document.getElementById('heatmapHotspot-text').innerHTML = 
                'Top hotspot: <strong>' + maxY + '</strong> × <strong>' + maxX + '</strong> with <span style="background: #c53030; color: white; padding: 2px 6px; border-radius: 8px;">' + maxVal + ' bugs</span>';
            
            Plotly.react('heatmapChart', [{{
                z: zData,
                x: xLabels,
                y: yLabels,
                type: 'heatmap',
                colorscale: [[0, '#fff5f5'], [0.25, '#feb2b2'], [0.5, '#fc8181'], [0.75, '#f56565'], [1, '#c53030']],
                hovertemplate: hoverTemplate,
                text: zData.map(row => row.map(v => v > 0 ? v : '')),
                texttemplate: '%{{text}}',
                textfont: {{ size: 9, color: '#333' }}
            }}], {{
                paper_bgcolor: 'transparent',
                plot_bgcolor: 'transparent',
                font: {{ family: 'Segoe UI, sans-serif', size: 11 }},
                margin: {{ l: 150, r: 30, t: 30, b: 100 }},
                xaxis: {{ 
                    tickangle: -40, 
                    title: {{ text: xTitle, font: {{ size: 12, color: '#555' }}, standoff: 10 }},
                    tickfont: {{ size: 9 }}
                }},
                yaxis: {{ 
                    autorange: 'reversed',
                    title: {{ text: yTitle, font: {{ size: 12, color: '#555' }}, standoff: 5 }},
                    tickfont: {{ size: 9 }}
                }}
            }}, {{responsive: true}});
        }}
        
        // Lazy initialization: Heatmap Chart
        function initHeatmapChart() {{
            if (chartsInitialized.heatmap) return;
            updateHeatmapChart('category');
            
            // Add click handler for heatmap cells
            document.getElementById('heatmapChart').on('plotly_click', function(data) {{
                const point = data.points[0];
                const xValue = point.x;  // Category
                const yValue = point.y;  // Area or Version
                const count = point.z;
                
                if (count === 0) return;  // Skip empty cells
                
                let bugData, title;
                if (currentHeatmapView === 'category') {{
                    // Category vs Area Path
                    const cellKey = xValue + '|' + yValue;
                    bugData = heatmapBugData[cellKey] || [];
                    title = xValue + ' × ' + yValue;
                }} else {{
                    // Category vs Version  
                    const cellKey = xValue + '|' + yValue;
                    bugData = heatmapVersionBugData[cellKey] || [];
                    title = xValue + ' (v' + yValue + ')';
                }}
                
                if (bugData.length > 0) {{
                    showBugModal(title, bugData);
                }}
            }});
            
            chartsInitialized.heatmap = true;
        }}
        
        // Lazy initialization: Dimension Heatmap (SDLC vs Test Phase)
        function initDimensionCharts() {{
            if (chartsInitialized.dimensions) return;
            
            const sdlcLabels = {list(sdlc_list)};
            const testLabels = {list(test_list)};
            const dimMatrix = {dimension_heatmap_matrix};
            
            Plotly.newPlot('dimensionHeatmap', [{{
                z: dimMatrix,
                x: testLabels,
                y: sdlcLabels,
                type: 'heatmap',
                colorscale: [[0, '#e8f5e9'], [0.25, '#a5d6a7'], [0.5, '#66bb6a'], [0.75, '#43a047'], [1, '#1b5e20']],
                hovertemplate: '<b>SDLC: %{{y}}</b><br>Test Phase: %{{x}}<br>Defects: <b>%{{z}}</b><extra></extra>',
                text: dimMatrix.map(row => row.map(v => v > 0 ? v : '')),
                texttemplate: '%{{text}}',
                textfont: {{ size: 11, color: '#333' }}
            }}], {{
                paper_bgcolor: 'transparent',
                plot_bgcolor: 'transparent',
                font: {{ family: 'Segoe UI, sans-serif', size: 11 }},
                margin: {{ l: 120, r: 30, t: 10, b: 80 }},
                xaxis: {{ 
                    tickangle: -30, 
                    title: {{ text: 'Test Phase (When Found)', font: {{ size: 12, color: '#555' }}, standoff: 10 }},
                    tickfont: {{ size: 10 }},
                    side: 'bottom'
                }},
                yaxis: {{ 
                    autorange: 'reversed',
                    title: {{ text: 'SDLC Phase (When Introduced)', font: {{ size: 12, color: '#555' }}, standoff: 5 }},
                    tickfont: {{ size: 10 }}
                }}
            }}, {{responsive: true}});
            
            // Add click handler for dimension heatmap cells
            document.getElementById('dimensionHeatmap').on('plotly_click', function(data) {{
                const point = data.points[0];
                const testPhase = point.x;   // Test Phase (X-axis)
                const sdlcPhase = point.y;   // SDLC Phase (Y-axis)
                const count = point.z;
                
                if (count === 0) return;  // Skip empty cells
                
                const cellKey = sdlcPhase + '|' + testPhase;
                const bugData = dimensionBugData[cellKey] || [];
                
                if (bugData.length > 0) {{
                    const title = 'SDLC: ' + sdlcPhase + ' → Test: ' + testPhase;
                    showBugModal(title, bugData);
                }}
            }});
            
            chartsInitialized.dimensions = true;
        }}
    </script>
</body>
</html>
"""

# Write HTML
with open('Dashboard_A_Overview.html', 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"\n✅ Dashboard A Created Successfully!")
print(f"📄 File: Dashboard_A_Overview.html")
print(f"\n🎯 Tabs Included:")
print(f"   1. ⏱️  Quick Win Metrics (Aging + Escape Rate)")
print(f"   2. 📊 Category Pareto (Stacked bars + 80/20 line)")
print(f"   3. 🗺️  Area Heatmap (Category vs Area correlation)")
print(f"   4. 📋 Classification Dimensions (SDLC, Test, Origin)")
