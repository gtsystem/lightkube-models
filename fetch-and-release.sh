#!/bin/bash

# Fetch list of available Kubernetes versions and let user choose
echo "Fetching available Kubernetes versions..."
PYTHON="uv run --group compile python"
VERSIONS=$($PYTHON -m lightkube-generate.fetch list 20 2>/dev/null | grep -E "^  [0-9]+\.[0-9]+\.[0-9]+$" | sed 's/^  //')

if [ -z "$VERSIONS" ]; then
    echo "Failed to fetch versions. Please check your internet connection."
    exit 1
fi

# Display versions and prompt user to select
echo ""
echo "Available Kubernetes versions:"
select VERSION in $VERSIONS; do
    if [ -n "$VERSION" ]; then
        echo ""
        echo "Selected version: $VERSION"
        break
    else
        echo "Invalid selection. Please try again."
    fi
done

# Validate version format
if [[ ! "$VERSION" =~ ^[0-9]+[.][0-9]+[.][0-9]+$ ]]; then
    echo "Version $VERSION must match expression \d+.\d+.\d"
    exit 1
fi

# 1. Fetch the OpenAPI spec
echo ""
echo "Step 1/3: Fetching OpenAPI spec for version $VERSION..."
$PYTHON -m lightkube-generate.fetch fetch "$VERSION"
if [ $? -ne 0 ]; then
    echo "Failed to fetch spec"
    exit 1
fi

# 2. Update workflow file
echo ""
echo "Step 2/3: Updating GitHub workflow..."
$PYTHON -m lightkube-generate.fetch update-workflow "$VERSION"
if [ $? -ne 0 ]; then
    echo "Failed to update workflow"
    exit 1
fi

# 3. Update documentation
echo ""
echo "Step 3/3: Updating documentation..."
$PYTHON -m lightkube-generate.fetch update-docs "$VERSION"
if [ $? -ne 0 ]; then
    echo "Failed to update docs"
    exit 1
fi


# 4. Execute release script
bash release.sh "$VERSION"
if [ $? -ne 0 ]; then
    echo "Release script failed"
    exit 1
fi

echo ""
echo "✓ All steps completed successfully for version $VERSION"
