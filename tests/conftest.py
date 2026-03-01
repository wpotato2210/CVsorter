from __future__ import annotations

import sys
import types

if "cv2" not in sys.modules:
    cv2_stub = types.SimpleNamespace(
        imread=lambda *_args, **_kwargs: None,
        VideoCapture=lambda *_args, **_kwargs: types.SimpleNamespace(
            isOpened=lambda: False,
            get=lambda *_a, **_k: 0.0,
            read=lambda: (False, None),
            release=lambda: None,
        ),
        CAP_PROP_FPS=0,
    )
    sys.modules["cv2"] = cv2_stub
