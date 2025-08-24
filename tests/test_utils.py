import torch

from src.modules.utils import get_available_device, get_device_info, to_device


def test_get_available_device():
    """Test device selection logic"""
    # Test without preferred device
    device = get_available_device()
    assert device in ["cuda", "mps", "cpu"]

    # Test with preferred device that's available
    if torch.cuda.is_available():
        assert get_available_device("cuda") == "cuda"
    if torch.backends.mps.is_available():
        assert get_available_device("mps") == "mps"
    assert get_available_device("cpu") == "cpu"

    # Test with preferred device that's not available
    if not torch.cuda.is_available():
        device = get_available_device("cuda")
        assert device in ["mps", "cpu"]
    if not torch.backends.mps.is_available():
        device = get_available_device("mps")
        assert device in ["cuda", "cpu"]


def test_get_device_info():
    """Test device information gathering"""
    info = get_device_info()

    # Check structure
    assert "available_devices" in info
    assert "current_device" in info
    assert "device_count" in info
    assert "device_names" in info

    # Check values
    assert isinstance(info["available_devices"], list)
    assert info["current_device"] in ["cuda", "mps", "cpu"]
    assert isinstance(info["device_count"], dict)
    assert isinstance(info["device_names"], dict)

    # Check device counts
    assert info["device_count"]["cuda"] == (
        torch.cuda.device_count() if torch.cuda.is_available() else 0
    )
    assert info["device_count"]["mps"] == (
        1 if torch.backends.mps.is_available() else 0
    )
    assert info["device_count"]["cpu"] == 1

    # Check available devices list
    if torch.cuda.is_available():
        assert "cuda" in info["available_devices"]
    if torch.backends.mps.is_available():
        assert "mps" in info["available_devices"]
    assert "cpu" in info["available_devices"]


def test_to_device():
    """Test tensor device movement"""
    # Create a test tensor
    tensor = torch.randn(2, 3)

    # Test moving to specific device
    if torch.cuda.is_available():
        moved_tensor = to_device(tensor, "cuda")
        assert moved_tensor.device.type == "cuda"

    if torch.backends.mps.is_available():
        moved_tensor = to_device(tensor, "mps")
        assert moved_tensor.device.type == "mps"

    moved_tensor = to_device(tensor, "cpu")
    assert moved_tensor.device.type == "cpu"

    # Test moving to best available device
    moved_tensor = to_device(tensor)
    assert moved_tensor.device.type in ["cuda", "mps", "cpu"]
