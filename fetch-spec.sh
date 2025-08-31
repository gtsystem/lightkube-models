#!/bin/bash

VERSION=$1   # provide version without `v`

if [[ ! "$VERSION" =~ ^[0-9]+[.][0-9]+[.][0-9]$ ]]; then
    echo "Version $VERSION must match expression \d+.\d+.\d"
    exit 1
fi

curl -L https://raw.githubusercontent.com/kubernetes/kubernetes/refs/tags/v${VERSION}/api/openapi-spec/swagger.json -o openapi/tmp.json
sed s/unversioned/v${VERSION}/ openapi/tmp.json > openapi/kubernetes_v${VERSION}.json
rm openapi/tmp.json
