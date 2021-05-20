# 10 MAY 2021
# Change directory to tests so that pytest can run in the hysplitplot directory.
import os
if os.path.exists('tests/data'):
  os.chdir('tests')
