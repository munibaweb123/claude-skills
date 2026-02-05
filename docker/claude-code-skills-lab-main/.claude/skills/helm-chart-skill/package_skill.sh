#!/bin/bash
# Package the Helm Chart Skill

set -euo pipefail

SKILL_NAME="helm-chart"
SKILL_DIR="helm-chart-skill"
OUTPUT_FILE="${SKILL_NAME}.skill"

echo "Packaging Helm Chart Skill..."

# Validate required files exist
if [[ ! -f "SKILL.md" ]]; then
    echo "Error: SKILL.md not found"
    exit 1
fi

# Create temporary directory for packaging
TEMP_DIR=$(mktemp -d)
trap 'rm -rf "$TEMP_DIR"' EXIT

# Copy skill contents to temp directory
cp -r ./* "$TEMP_DIR/"

# Create the skill package
cd "$TEMP_DIR"
tar -czf "../$OUTPUT_FILE" ./*

echo "Helm Chart Skill packaged successfully as $OUTPUT_FILE"
echo "Size: $(du -h "$OUTPUT_FILE" | cut -f1)"

# Verify the package
echo "Verifying package contents:"
tar -tzf "../$OUTPUT_FILE" | head -20