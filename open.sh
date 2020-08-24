#!/usr/bin/env bash

# This script will execute the generate.sh script and then ./update_selenium.py

set -euo pipefail

readonly script_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

while IFS= read -r -d '' module
do
  dir=$(dirname "$module")
  echo "$dir"
  (
    cd "$dir"
    generate.sh
    ./upload_selenium.py --replace
  )
done < <(find "$script_dir" -name module.xml -print0)
