"""Model loader with quantization support for local HuggingFace models."""

import os
from typing import Any, Dict, Optional

from src.monitoring.logger import get_logger

logger = get_logger(__name__)

# Quantization modes
QUANT_NONE = "none"
QUANT_8BIT = "8bit"
QUANT_4BIT = "4bit"


class ModelLoader:
    """Load and cache HuggingFace models with optional quantization.

    Supports 4-bit and 8-bit quantization via ``bitsandbytes`` when a GPU
    is available, falling back gracefully to CPU fp32.

    Attributes:
        cache_dir: Directory used to cache downloaded model weights.
        device: Target device string (``"cuda"``, ``"cpu"``, etc.).
        _loaded_models: Registry of already-loaded models.
    """

    def __init__(self, cache_dir: str = "./model_cache", device: Optional[str] = None) -> None:
        """Initialise the model loader.

        Args:
            cache_dir: Path to the local model weight cache directory.
            device: Device to load models onto.  Auto-detected if ``None``.
        """
        self.cache_dir = cache_dir
        self.device = device or self._detect_device()
        self._loaded_models: Dict[str, Any] = {}
        os.makedirs(cache_dir, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(
        self,
        model_name: str,
        quantization: str = QUANT_NONE,
        warm_up: bool = True,
    ) -> Any:
        """Load *model_name* and return the pipeline / model object.

        Loaded models are cached in-memory so subsequent calls are instant.

        Args:
            model_name: HuggingFace model identifier (e.g. ``"gpt2"``).
            quantization: One of ``"none"``, ``"8bit"``, or ``"4bit"``.
            warm_up: If True, run a dummy forward pass to JIT-compile layers.

        Returns:
            HuggingFace ``pipeline`` object.

        Raises:
            RuntimeError: If required packages (transformers, bitsandbytes)
                are not installed.
        """
        cache_key = f"{model_name}:{quantization}"
        if cache_key in self._loaded_models:
            logger.info("Model cache hit", model=model_name)
            return self._loaded_models[cache_key]

        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline  # type: ignore[import]
        except ImportError as exc:
            raise RuntimeError("transformers package is not installed.") from exc

        logger.info("Loading model", model=model_name, quantization=quantization)

        quant_kwargs: Dict[str, Any] = {}
        if quantization == QUANT_8BIT:
            quant_kwargs = {"load_in_8bit": True}
        elif quantization == QUANT_4BIT:
            try:
                from transformers import BitsAndBytesConfig  # type: ignore[import]

                quant_kwargs = {
                    "quantization_config": BitsAndBytesConfig(
                        load_in_4bit=True,
                        bnb_4bit_use_double_quant=True,
                        bnb_4bit_quant_type="nf4",
                    )
                }
            except ImportError as exc:
                raise RuntimeError(
                    "bitsandbytes package required for 4-bit quantization."
                ) from exc

        tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir=self.cache_dir)
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            cache_dir=self.cache_dir,
            device_map="auto" if self.device == "cuda" else None,
            **quant_kwargs,
        )

        pipe = pipeline("text-generation", model=model, tokenizer=tokenizer)

        if warm_up:
            self._warm_up(pipe)

        self._loaded_models[cache_key] = pipe
        logger.info("Model loaded successfully", model=model_name)
        return pipe

    def unload(self, model_name: str, quantization: str = QUANT_NONE) -> None:
        """Remove a model from the in-memory cache.

        Args:
            model_name: HuggingFace model identifier.
            quantization: Quantization mode used when the model was loaded.
        """
        key = f"{model_name}:{quantization}"
        if key in self._loaded_models:
            del self._loaded_models[key]
            logger.info("Model unloaded", model=model_name)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_device() -> str:
        """Return ``"cuda"`` if a GPU is available, else ``"cpu"``."""
        try:
            import torch  # type: ignore[import]

            return "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            return "cpu"

    @staticmethod
    def _warm_up(pipe: Any) -> None:
        """Run a minimal forward pass to warm up the model.

        Args:
            pipe: HuggingFace pipeline object.
        """
        try:
            pipe("warm up", max_new_tokens=1)
        except Exception:  # noqa: BLE001
            pass  # warm-up failure is non-fatal
