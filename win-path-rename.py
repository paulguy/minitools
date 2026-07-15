#!/usr/bin/env python3

import sys
import pathlib

for oldpath in pathlib.Path('.').glob(f"{sys.argv[1]}\\*"):
    print(oldpath)
    newpath = pathlib.Path(str(oldpath).replace('\\', '/'))
    if oldpath.is_dir():
        newpath.mkdir(parents=True, exist_ok=True)
    else:
        parent = newpath.parent
        # still try making the parent directory anyway
        parent.mkdir(parents=True, exist_ok=True)
        oldpath.copy(newpath)
