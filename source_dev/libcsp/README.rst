LibCSP Development Build Guide
==============================

Overview
--------
This repository provides a development setup for building LibCSP (v1.6 custom).
All scripts are designed for a local Linux build environment.

Directory Layout
----------------

::
    .
    ├── dev_buildall.py     # Python-based Waf build helper
    ├── ../allbuild.sh        # unified wrapper script (recommended)
    ├── 00_Dev16/DevBuild/  # build output directory
    └── src/                # main source files

Dependencies
------------
* Linux with Python 3
* Packages:
  - libsocketcan, libsocketcan-dev
  - pkg-config
  - python3-dev

* Make sure `python` points to Python 3:
  ::

    sudo ln -sf /usr/bin/python3 /usr/bin/python

Build Steps
-----------
1. **Setup (run once after clone):**
   ::
        chmod +x sbuild.sh
       ./sbuild.sh

2. **Build:**
   Recommended way:
   ::

       ./sbuild.sh

   This script automatically:
   - Runs setup if not done.
   - Configures Waf output to ``00_Dev16/DevBuild``.
   - Exports required library path:
     ::

         export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:pwd/libcsp-1.6/build
   - Runs ``python3 dev_buildall.py``.

Output
------
All build results (libraries, examples, Python bindings) are placed in:

::
    00_Dev16/DevBuild/

Clean build (optional):
::

    ./waf distclean

Notes
-----
* `sbuild.sh` is the only script you need for daily builds.
