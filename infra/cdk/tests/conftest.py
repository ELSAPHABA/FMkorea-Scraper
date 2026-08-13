from __future__ import annotations

import sys
from pathlib import Path


CDK_ROOT = Path(__file__).resolve().parents[1]
if str(CDK_ROOT) not in sys.path:
    sys.path.insert(0, str(CDK_ROOT))

