"""Package setup for secure-llm-deployment."""

from setuptools import find_packages, setup

setup(
    name="secure-llm-deployment",
    version="1.0.0",
    description="Secure and Cost-Efficient Deployment of Large Language Models",
    author="Gurutejareddy9",
    python_requires=">=3.10",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "fastapi>=0.104.0",
        "uvicorn[standard]>=0.24.0",
        "python-jose[cryptography]>=3.3.0",
        "bcrypt>=4.0.1",
        "slowapi>=0.1.9",
        "openai>=1.3.0",
        "redis>=5.0.0",
        "sentence-transformers>=2.2.2",
        "prometheus-client>=0.19.0",
        "pyyaml>=6.0.1",
        "python-dotenv>=1.0.0",
        "structlog>=23.2.0",
        "bleach>=6.1.0",
        "numpy>=1.24.0",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
