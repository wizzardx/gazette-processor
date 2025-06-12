from typing import List, Optional, Tuple, Union

import numpy as np
from PIL.Image import Image

class Reader:
    def __init__(
        self,
        lang_list: List[str],
        gpu: bool = True,
        model_storage_directory: Optional[str] = None,
        user_network_directory: Optional[str] = None,
        recog_network: str = "standard",
        detector: bool = True,
        recognizer: bool = True,
        verbose: bool = True,
        quantize: bool = True,
        cudnn_benchmark: bool = False,
    ) -> None: ...
    def readtext(
        self,
        image: Union[str, np.ndarray, Image],
        decoder: str = "greedy",
        beamWidth: int = 5,
        batch_size: int = 1,
        workers: int = 0,
        allowlist: Optional[str] = None,
        blocklist: Optional[str] = None,
        detail: int = 1,
        rotation_info: Optional[List[int]] = None,
        paragraph: bool = False,
        min_size: int = 20,
        text_threshold: float = 0.7,
        low_text: float = 0.4,
        link_threshold: float = 0.4,
        canvas_size: int = 2560,
        mag_ratio: float = 1.0,
        slope_ths: float = 0.1,
        ycenter_ths: float = 0.5,
        height_ths: float = 0.7,
        width_ths: float = 0.5,
        y_ths: float = 0.5,
        x_ths: float = 1.0,
        add_margin: float = 0.1,
        threshold: float = 0.2,
        bbox_min_score: float = 0.2,
        bbox_min_size: int = 3,
        max_candidates: int = 0,
    ) -> List[Tuple[List[List[int]], str, float]]: ...
