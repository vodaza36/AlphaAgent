#!/usr/bin/env python3
"""Test Alpha158 feature configuration."""

import qlib
from qlib.contrib.data.handler import Alpha158

qlib.init(provider_uri='~/.qlib/qlib_data/us_data', region='us')

print("Creating Alpha158 handler for US data...")
handler = Alpha158(
    instruments='SP500',
    start_time='2025-01-01',
    end_time='2025-01-10',
)

# Get feature config
feature_config = handler.get_feature_config()
print(f"\nAlpha158 uses {len(feature_config[0])} features")
print(f"\nFirst 10 feature expressions:")
for i, (expr, name) in enumerate(zip(feature_config[0][:10], feature_config[1][:10])):
    print(f"  {name}: {expr}")

# Check if VWAP is in the features
vwap_features = [name for name in feature_config[1] if 'VWAP' in name]
if vwap_features:
    print(f"\nVWAP-based features ({len(vwap_features)} total):")
    print(f"  {vwap_features[:5]}")
else:
    print("\nNo VWAP features found!")

# Print all unique fields used
import re
all_fields = set()
for expr in feature_config[0]:
    # Extract all $field references
    fields = re.findall(r'\$(\w+)', expr)
    all_fields.update(fields)

print(f"\nAll unique data fields required by Alpha158:")
for field in sorted(all_fields):
    print(f"  ${field}")
