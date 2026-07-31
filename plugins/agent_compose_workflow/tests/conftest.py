import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
STRATEGY_ROOT = ROOT.parent / "agent_compose_strategy"
if str(STRATEGY_ROOT) not in sys.path:
    sys.path.append(str(STRATEGY_ROOT))
