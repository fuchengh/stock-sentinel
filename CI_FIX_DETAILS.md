This file explains the changes made to fix the CI failure.

1.  **requirements.txt**: 
    - Replaced `pandas_ta` with `pandas-ta`. This is the correct package name on PyPI.
    
2.  **.github/workflows/weekly_scan.yml**: 
    - Updated `python-version` from `3.9` to `3.12`. 
    - The latest versions of `pandas-ta` (0.4.x) require Python 3.12 or newer. Updating the environment ensures compatibility.

To apply these changes and restart the CI pipeline, please run:
`git push`
