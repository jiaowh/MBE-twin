
import sys
from pathlib import Path
args = sys.argv[1:]
out = Path(args[args.index("--out") + 1])
out.mkdir(parents=True, exist_ok=True)
if args[0] == "fail":
    sys.exit(3)
(out / "summary.json").write_text("{}")
