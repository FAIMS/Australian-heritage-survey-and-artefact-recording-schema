# This script will execute the generate.sh script and then ./update_selenium.py

set -euo pipefail

for dir in $(find . -mindepth 2  -name "module.xml" | cut -d'/' -f2); do
  echo $dir
  cd $dir
  generate.sh
  ./upload_selenium.py
  cd ..
done
