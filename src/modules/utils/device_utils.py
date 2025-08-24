from typing import Literal, Optional

import torch

DeviceType = Literal["cuda", "mps", "cpu"]


def get_available_device(preferred_device: Optional[DeviceType] = None) -> DeviceType:
    """
    Determine the best available device for PyTorch operations.
    """
    if preferred_device:
        if preferred_device == "cuda" and torch.cuda.is_available():
            return "cuda"
        elif preferred_device == "mps" and torch.backends.mps.is_available():
            return "mps"
        elif preferred_device == "cpu":
            return "cpu"

    if torch.cuda.is_available():
        return "cuda"
    elif torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def get_device_info() -> dict:
    """
    Get information about the available devices and their capabilities.
    """
    info = {
        "available_devices": [],
        "current_device": get_available_device(),
        "device_count": {
            "cuda": torch.cuda.device_count() if torch.cuda.is_available() else 0,
            "mps": 1 if torch.backends.mps.is_available() else 0,
            "cpu": 1,
        },
        "device_names": {
            "cuda": [
                torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())
            ]
            if torch.cuda.is_available()
            else [],
            "mps": ["Apple Silicon GPU"] if torch.backends.mps.is_available() else [],
            "cpu": ["CPU"],
        },
    }

    if torch.cuda.is_available():
        info["available_devices"].append("cuda")
    if torch.backends.mps.is_available():
        info["available_devices"].append("mps")
    info["available_devices"].append("cpu")

    return info


def to_device(
    tensor: torch.Tensor, device: Optional[DeviceType] = None
) -> torch.Tensor:
    """
    Move a tensor to the specified device.
    """
    target_device = get_available_device(device)
    return tensor.to(target_device)
