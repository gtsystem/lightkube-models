#!/bin/bash
rm -rf lightkube/models lightkube/resources
mkdir lightkube/models lightkube/resources
python -m tools.compile_models  openapi/swagger.json lightkube/ test_models.py
python -m tools.compile_resources  openapi/swagger.json lightkube/ test_resources.py
