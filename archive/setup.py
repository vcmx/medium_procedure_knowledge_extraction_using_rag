from setuptools import find_packages, setup

setup(
    name="pdf-processor",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "marker-pdf==1.7.3",
        "transformers",
        "torch",
        "Pillow",
        "einops",
        "timm",
        "chromadb",
        "sentence-transformers",
        "typing-extensions",
    ],
    python_requires=">=3.8",
)
