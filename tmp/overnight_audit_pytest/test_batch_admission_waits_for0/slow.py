
import sys, time
from pathlib import Path
args = sys.argv[1:]
out = Path(args[args.index("--out") + 1]); out.mkdir(parents=True, exist_ok=True)
(out / "start").write_text(repr(time.time())); time.sleep(3); (out / "summary.json").write_text("{}")
