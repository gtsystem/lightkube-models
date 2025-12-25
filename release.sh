if [[ ! -z "$1" ]]; then
  VERSIONS=$1   # provide version without `v`
  if [[ ! "$VERSIONS" =~ ^[0-9]+[.][0-9]+[.][0-9]$ ]]; then
    echo "Version $VERSIONS must match expression \d+.\d+.\d"
    exit 1
  fi
else
  VERSIONS=$(awk '/([0-9]+.[0-9]+.[0-9]+)/ {print $2}' .github/workflows/python-package.yml)
  rm dist/*.whl dist/*.tar.gz
fi

export PYTHONPATH=src

for v in $VERSIONS; do
  MAIN_VERSION=$(echo $v | cut -d. -f1,2 )
  echo "Building v$v"
  uv run --group compile python -m lightkube-generate resources models openapi/kubernetes_v$v.json --docs docs
  uv run python test_models.py
  uv run python test_resources.py
  rm -rf build
  uvx hatch build
  uv run --group compile python -m mkdocs build -d site/$MAIN_VERSION
  #twine upload dist/lightkube_models-${v}.*-py3-none-any.whl -r $1
  ls dist/lightkube_models-${v}.*-py3-none-any.whl
  ls dist/lightkube_models-${v}.*.tar.gz
done
