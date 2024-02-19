#!/usr/bin/env python
# This script will add or update the license header to all .py files in the repository

import os

header = """
#  This file is part of dflow-galaxy.
#  Copyright (C) 2024  Laboratory of AI for Electrochemistry (AI4EC), IKKEM
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published
#  by the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.
""".strip()


# list .py files with git ls-files

files = os.popen('git ls-files').read().split('\n')
files = [f for f in files if f.endswith('.py')]

# add license header to each file
# the license header section can be identified by the first and last line of header

for file in files:
    with open(file, 'r') as f:
        content = f.read()
    if content.startswith(header):
        continue
    with open(file, 'w') as f:
            f.write(header + '\n\n' + content)
    print(f'Updated {file}')
print('Done')









