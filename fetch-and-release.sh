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

# Extract major.minor for branch name (e.g., 1.35 from 1.35.0)
MAJOR_MINOR=$(echo "$VERSION" | cut -d. -f1,2 | tr '.' '_')
EXPECTED_BRANCH="v${MAJOR_MINOR}"

# Check current branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
if [ $? -ne 0 ]; then
    echo "Error: Not in a git repository"
    exit 1
fi


if [ "$CURRENT_BRANCH" != "$EXPECTED_BRANCH" ]; then
    echo "Warning: You are not on the expected branch for version $VERSION"
    read -p "Do you want to create and switch to branch '$EXPECTED_BRANCH'? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Creating new branch $EXPECTED_BRANCH..."
        git checkout -b "$EXPECTED_BRANCH"
        if [ $? -ne 0 ]; then
            echo "Failed to create/switch to branch"
            exit 1
        fi
    fi
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
echo "Updating documentation..."
$PYTHON -m lightkube-generate.fetch update-docs "$VERSION"
if [ $? -ne 0 ]; then
    echo "Failed to update docs"
    exit 1
fi

# 4. Update README file
echo ""
echo "Updating README..."
$PYTHON -m lightkube-generate.fetch update-readme "$VERSION"
if [ $? -ne 0 ]; then
    echo "Failed to update readme"
    exit 1
fi

# 5. Execute release script
bash release.sh "$VERSION"
if [ $? -ne 0 ]; then
    echo "Release script failed"
    exit 1
fi

echo ""
echo "✓ All steps completed successfully for version $VERSION"
