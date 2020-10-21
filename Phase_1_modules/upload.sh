#!/usr/bin/env bash

for d in */
do
  echo "Directory: $d"
  (
    cd "$d"

    /home/christian/Documents/Work/Intersect/FAIMS-Tools/generators/christian/validate.sh
    /home/christian/Documents/Work/Intersect/FAIMS-Tools/generators/christian/generate.sh
    tests/test.sh

    # ./upload.py --replace
  )
done
