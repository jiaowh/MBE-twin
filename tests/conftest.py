"""Single-threaded BLAS for the whole test session.

Set before numpy is first imported: on the shared laptop multithreaded BLAS made the small dense
heater solves about 1000x slower (scripts/heater_zones.py).
"""

import os

for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
