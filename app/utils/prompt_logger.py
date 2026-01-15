"""
Prompt Logger - централизованное логирование всех промптов для анализа
"""
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

# Create dedicated logger for prompts
prompt_logger = logging.getLogger("prompt_analytics")
prompt_logger.setLevel(logging.INFO)

# Create logs directory if it doesn't exist
logs_dir = Path("logs")
logs_dir.mkdir(exist_ok=True)

# File handler for prompt logs (JSON format for easy analysis)
prompt_log_file = logs_dir / "prompts.jsonl"
file_handler = logging.FileHandler(prompt_log_file, encoding='utf-8')
file_handler.setLevel(logging.INFO)

# Console handler for debugging
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

# Formatters
file_formatter = logging.Formatter('%(message)s')  # JSON only
console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

file_handler.setFormatter(file_formatter)
console_handler.setFormatter(console_formatter)

prompt_logger.addHandler(file_handler)
prompt_logger.addHandler(console_handler)


class PromptLogger:
    """Utility class for logging prompts with structured data"""

    @staticmethod
    def log_style_generation(
        operation_type: str,
        product_description: str,
        aspect_ratio: str,
        random: bool,
        num_styles: int,
        system_prompt: str,
        user_prompt: str,
        response: Optional[Dict] = None,
        success: bool = True,
        error: Optional[str] = None,
        user_id: Optional[int] = None,
        duration_ms: Optional[float] = None
    ):
        """
        Log style generation request and response

        Args:
            operation_type: Type of operation (e.g., "random_styles", "analyzed_styles")
            product_description: Product description used
            aspect_ratio: Aspect ratio requested
            random: Whether random generation was requested
            num_styles: Number of styles requested
            system_prompt: System prompt sent to API
            user_prompt: User prompt sent to API
            response: Response from API (optional)
            success: Whether generation was successful
            error: Error message if failed
            user_id: Telegram user ID (optional)
            duration_ms: Request duration in milliseconds (optional)
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "operation": "style_generation",
            "operation_type": operation_type,
            "user_id": user_id,
            "input": {
                "product_description": product_description,
                "aspect_ratio": aspect_ratio,
                "random": random,
                "num_styles": num_styles
            },
            "prompts": {
                "system": system_prompt[:500] if len(system_prompt) > 500 else system_prompt,  # Truncate if too long
                "user": user_prompt
            },
            "response": {
                "success": success,
                "styles": response.get("styles", []) if response else [],
                "product_name": response.get("product_name") if response else None,
                "error": error
            },
            "duration_ms": duration_ms
        }

        # Log as JSON line
        prompt_logger.info(json.dumps(log_entry, ensure_ascii=False))

    @staticmethod
    def log_image_generation(
        product_description: str,
        style_name: str,
        style_prompt: str,
        aspect_ratio: str,
        system_prompt: str,
        full_user_prompt: str,
        success: bool = True,
        error: Optional[str] = None,
        user_id: Optional[int] = None,
        duration_ms: Optional[float] = None,
        image_size_kb: Optional[float] = None
    ):
        """
        Log image generation request and response

        Args:
            product_description: Product description
            style_name: Name of the style being generated
            style_prompt: Style prompt being used
            aspect_ratio: Aspect ratio requested
            system_prompt: System prompt sent to API
            full_user_prompt: Full user prompt sent to API
            success: Whether generation was successful
            error: Error message if failed
            user_id: Telegram user ID (optional)
            duration_ms: Request duration in milliseconds (optional)
            image_size_kb: Generated image size in KB (optional)
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "operation": "image_generation",
            "user_id": user_id,
            "input": {
                "product_description": product_description,
                "style_name": style_name,
                "style_prompt": style_prompt,
                "aspect_ratio": aspect_ratio
            },
            "prompts": {
                "system": system_prompt[:500] if len(system_prompt) > 500 else system_prompt,
                "user": full_user_prompt
            },
            "response": {
                "success": success,
                "error": error,
                "image_size_kb": image_size_kb
            },
            "duration_ms": duration_ms
        }

        # Log as JSON line
        prompt_logger.info(json.dumps(log_entry, ensure_ascii=False))

    @staticmethod
    def log_style_variation(
        base_style_name: str,
        base_style_prompt: str,
        product_description: str,
        aspect_ratio: str,
        num_variations: int,
        system_prompt: str,
        user_prompt: str,
        response: Optional[Dict] = None,
        success: bool = True,
        error: Optional[str] = None,
        user_id: Optional[int] = None,
        duration_ms: Optional[float] = None
    ):
        """
        Log style variation generation request and response

        Args:
            base_style_name: Name of base style
            base_style_prompt: Base style prompt
            product_description: Product description
            aspect_ratio: Aspect ratio requested
            num_variations: Number of variations requested
            system_prompt: System prompt sent to API
            user_prompt: User prompt sent to API
            response: Response from API (optional)
            success: Whether generation was successful
            error: Error message if failed
            user_id: Telegram user ID (optional)
            duration_ms: Request duration in milliseconds (optional)
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "operation": "style_variation",
            "user_id": user_id,
            "input": {
                "base_style_name": base_style_name,
                "base_style_prompt": base_style_prompt,
                "product_description": product_description,
                "aspect_ratio": aspect_ratio,
                "num_variations": num_variations
            },
            "prompts": {
                "system": system_prompt[:500] if len(system_prompt) > 500 else system_prompt,
                "user": user_prompt
            },
            "response": {
                "success": success,
                "styles": response.get("styles", []) if response else [],
                "error": error
            },
            "duration_ms": duration_ms
        }

        # Log as JSON line
        prompt_logger.info(json.dumps(log_entry, ensure_ascii=False))

    @staticmethod
    def get_analytics_summary(log_file: Optional[Path] = None) -> Dict[str, Any]:
        """
        Parse logs and return analytics summary

        Args:
            log_file: Path to log file (defaults to standard prompt log)

        Returns:
            Dictionary with analytics data
        """
        if log_file is None:
            log_file = logs_dir / "prompts.jsonl"

        if not log_file.exists():
            return {"error": "Log file not found"}

        analytics = {
            "total_requests": 0,
            "style_generation": {
                "total": 0,
                "success": 0,
                "failed": 0,
                "avg_duration_ms": 0
            },
            "image_generation": {
                "total": 0,
                "success": 0,
                "failed": 0,
                "avg_duration_ms": 0,
                "total_size_mb": 0
            },
            "unique_users": set(),
            "errors": []
        }

        durations_style = []
        durations_image = []

        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    analytics["total_requests"] += 1

                    if entry.get("user_id"):
                        analytics["unique_users"].add(entry["user_id"])

                    operation = entry.get("operation")
                    response = entry.get("response", {})

                    if operation == "style_generation":
                        analytics["style_generation"]["total"] += 1
                        if response.get("success"):
                            analytics["style_generation"]["success"] += 1
                        else:
                            analytics["style_generation"]["failed"] += 1
                            if response.get("error"):
                                analytics["errors"].append({
                                    "operation": operation,
                                    "error": response["error"],
                                    "timestamp": entry["timestamp"]
                                })

                        if entry.get("duration_ms"):
                            durations_style.append(entry["duration_ms"])

                    elif operation == "image_generation":
                        analytics["image_generation"]["total"] += 1
                        if response.get("success"):
                            analytics["image_generation"]["success"] += 1
                        else:
                            analytics["image_generation"]["failed"] += 1
                            if response.get("error"):
                                analytics["errors"].append({
                                    "operation": operation,
                                    "error": response["error"],
                                    "timestamp": entry["timestamp"]
                                })

                        if entry.get("duration_ms"):
                            durations_image.append(entry["duration_ms"])

                        if response.get("image_size_kb"):
                            analytics["image_generation"]["total_size_mb"] += response["image_size_kb"] / 1024

                except json.JSONDecodeError:
                    continue

        # Calculate averages
        if durations_style:
            analytics["style_generation"]["avg_duration_ms"] = sum(durations_style) / len(durations_style)

        if durations_image:
            analytics["image_generation"]["avg_duration_ms"] = sum(durations_image) / len(durations_image)

        analytics["unique_users"] = len(analytics["unique_users"])

        return analytics
