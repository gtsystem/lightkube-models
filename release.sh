VERSIONS=$(awk '/([0-9]+.[0-9]+.[0-9]+)/ {print $2}' .github/workflows/python-package.yml)

rm dist/*.whl
for v in $VERSIONS; do
  echo "Building v$v"
  python -m lightkube-generate resources models openapi/kubernetes_v$v.json
  python setup.py bdist_wheel
  #twine upload dist/lightkube_models-${v}.*-py3-none-any.whl -r $1
  ls dist/lightkube_models-${v}.*-py3-none-any.whl
done

