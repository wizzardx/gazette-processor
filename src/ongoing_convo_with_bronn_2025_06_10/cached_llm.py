#!/usr/bin/env python3
"""
CachedLLM Wrapper for Claude API - Clean Version
================================================

A simple, cached wrapper around Claude API that:
1. Provides sensible defaults
2. Offers a single summarize(text) -> summary method
3. Caches results based on MD5 hash to avoid duplicate API calls
4. Uses comprehensive few-shot examples for clean output

Installation:
    pip install anthropic environs

Usage:
    from cached_llm import CachedLLM

    llm = CachedLLM()  # Uses .env for config
    summary = llm.summarize("Your long text here...")
    print(summary)
"""

import hashlib
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import anthropic
from anthropic.types import MessageParam, TextBlock
from environs import Env

logger = logging.getLogger(__name__)


class ClaudeConfig:
    """Simplified config class with sensible defaults"""

    def __init__(self, env_file: str = ".env"):
        self.env = Env()
        if os.path.exists(env_file):
            self.env.read_env(env_file, override=True)

        # Required settings
        self.api_key = self.env.str("ANTHROPIC_API_KEY", "")

        # Sensible defaults optimized for cost/performance
        self.model = self.env.str("ANTHROPIC_MODEL", "claude-3-haiku-20240307")
        self.max_tokens = self.env.int(
            "MAX_TOKENS", 250
        )  # Increased to reduce truncation
        self.temperature = self.env.float("TEMPERATURE", 0.1)

        if not self.api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY is required. Set it in .env file or environment."
            )


class SimpleClaudeSummarizer:
    """Simplified Claude client focused on summarization"""

    def __init__(self, config: ClaudeConfig):
        self.config = config
        self.client = anthropic.Anthropic(api_key=config.api_key)

    def summarize(self, text: str) -> str:
        """Summarize text and return just the summary string"""

        # Try with default tokens first, then retry with more if truncated
        for attempt, max_tokens in enumerate(
            [self.config.max_tokens, int(self.config.max_tokens * 1.4)]
        ):
            messages: List[MessageParam] = [
                {
                    "role": "user",
                    "content": f"""I need you to summarize the following text. Start immediately with the summary content. Never use introductory phrases. IMPORTANT: Always end with complete sentences and proper punctuation. If you're running out of space, prioritize finishing your current sentence rather than starting a new one.

Here are some examples:

Text: Solar and wind power have become increasingly cost-competitive with fossil fuels over the past decade. Many countries are investing heavily in renewable infrastructure development. However, energy storage challenges remain a significant barrier to widespread adoption of these technologies.

Summary: Solar and wind power have become cost-competitive with fossil fuels, prompting heavy investment in renewable infrastructure by many countries. Energy storage challenges remain a significant barrier to widespread adoption.

Text: The European Union has announced new regulations for artificial intelligence systems that will take effect in 2025. These regulations will classify AI systems into different risk categories based on their potential impact on safety and fundamental rights. High-risk AI applications, such as those used in healthcare, transportation, and law enforcement, will face stricter oversight and compliance requirements. Companies will need to conduct risk assessments, implement quality management systems, and ensure human oversight. The regulations aim to balance innovation with consumer protection while establishing the EU as a global leader in AI governance.

Summary: The European Union has announced new AI regulations taking effect in 2025 that classify systems into risk categories based on safety and rights impact. High-risk applications in healthcare, transportation, and law enforcement will face stricter oversight, requiring companies to conduct risk assessments, implement quality management, and ensure human oversight. The regulations aim to balance innovation with consumer protection while establishing EU leadership in AI governance.

Now please summarize this text:

Text: {text}

Summary:""",
                }
            ]

            try:
                response = self.client.messages.create(
                    model=self.config.model,
                    max_tokens=max_tokens,
                    temperature=self.config.temperature,
                    messages=messages,
                )

                # Handle union type properly - only TextBlock has text attribute
                first_block = response.content[0]
                if isinstance(first_block, TextBlock):
                    summary = first_block.text.strip()
                else:
                    raise RuntimeError(
                        f"Unexpected response block type: {type(first_block)}"
                    )

                # Check if truncated based on stop reason
                is_truncated = response.stop_reason == "max_tokens"
                ends_properly = summary and summary[-1] in ".!?"

                # If first attempt was truncated and doesn't end properly, try again
                if is_truncated and not ends_properly and attempt == 0:
                    logger.info(
                        f"Summary truncated, retrying with {int(self.config.max_tokens * 1.4)} tokens..."
                    )
                    continue

                # Provide feedback on final result
                if is_truncated:
                    logger.warning(
                        f"Summary may be truncated (reached {max_tokens} token limit)"
                    )

                assert isinstance(summary, str)
                return summary

            except Exception as e:
                if attempt == 1:  # Final attempt failed
                    raise RuntimeError(f"Claude API error: {e}")
                continue

        # Should not reach here
        raise RuntimeError("Unexpected error in summarization")


class CacheManager:
    """Manages MD5-based caching with optional persistence"""

    def __init__(self, cache_file: Optional[str] = None, max_cache_size: int = 1000):
        self.cache_file = cache_file
        self.max_cache_size = max_cache_size
        self.cache: Dict[str, Dict[str, Any]] = {}

        # Load existing cache if file exists
        if cache_file and os.path.exists(cache_file):
            self._load_cache()

    def _compute_hash(self, text: str) -> str:
        """Compute MD5 hash of input text"""
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    def _load_cache(self) -> None:
        """Load cache from file"""
        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:  # type: ignore[arg-type]
                data = json.load(f)
                self.cache = data.get("cache", {})
        except Exception as e:
            logger.warning(f"Could not load cache file: {e}")
            self.cache = {}

    def _save_cache(self) -> None:
        """Save cache to file"""
        if not self.cache_file:
            return

        try:
            # Ensure directory exists
            Path(self.cache_file).parent.mkdir(parents=True, exist_ok=True)

            # Save cache with metadata
            data = {
                "cache": self.cache,
                "last_updated": datetime.now().isoformat(),
                "version": "1.0",
            }

            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.warning(f"Could not save cache file: {e}")

    def get(self, text: str) -> Optional[str]:
        """Get cached summary for text"""
        text_hash = self._compute_hash(text)

        if text_hash in self.cache:
            entry = self.cache[text_hash]

            # Update access time for LRU-style management
            entry["last_accessed"] = time.time()
            entry["access_count"] = entry.get("access_count", 0) + 1

            summary = entry["summary"]
            assert isinstance(summary, str)
            return summary

        return None

    def set(self, text: str, summary: str) -> None:
        """Cache summary for text"""
        text_hash = self._compute_hash(text)

        # Manage cache size
        if len(self.cache) >= self.max_cache_size:
            self._evict_oldest()

        # Store entry with metadata
        self.cache[text_hash] = {
            "summary": summary,
            "created": time.time(),
            "last_accessed": time.time(),
            "access_count": 1,
            "text_preview": text[:100] + "..." if len(text) > 100 else text,
        }

        # Save to file if configured
        self._save_cache()

    def _evict_oldest(self) -> None:
        """Remove least recently used entries when cache is full"""
        if not self.cache:
            return

        # Sort by last accessed time and remove oldest 20%
        sorted_items = sorted(self.cache.items(), key=lambda x: x[1]["last_accessed"])

        num_to_remove = max(1, len(sorted_items) // 5)

        for i in range(num_to_remove):
            key = sorted_items[i][0]
            del self.cache[key]

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self.cache:
            return {"size": 0, "hit_rate": 0.0, "total_accesses": 0}

        total_accesses = sum(
            entry.get("access_count", 0) for entry in self.cache.values()
        )

        return {
            "size": len(self.cache),
            "max_size": self.max_cache_size,
            "total_accesses": total_accesses,
            "oldest_entry": min(entry["created"] for entry in self.cache.values()),
            "newest_entry": max(entry["created"] for entry in self.cache.values()),
        }

    def clear(self) -> None:
        """Clear all cached entries"""
        self.cache.clear()
        self._save_cache()


class CachedLLM:
    """
    Simple, cached LLM wrapper with sensible defaults

    Provides a single summarize() method that caches results to save costs
    and improve performance on repeated inputs.
    """

    def __init__(
        self,
        cache_file: str = ".llm_cache.json",
        max_cache_size: int = 1000,
        env_file: str = ".env",
    ):
        """
        Initialize CachedLLM

        Args:
            cache_file: Path to cache file (None for memory-only)
            max_cache_size: Maximum number of cached entries
            env_file: Path to environment file for configuration
        """

        # Initialize components
        self.config = ClaudeConfig(env_file)
        self.summarizer = SimpleClaudeSummarizer(self.config)
        self.cache = CacheManager(cache_file, max_cache_size)

        # Stats tracking
        self.stats = {
            "total_requests": 0,
            "cache_hits": 0,
            "api_calls": 0,
            "total_cost_saved": 0.0,
        }

        # print(f"🚀 CachedLLM initialized")
        # print(f"   Model: {self.config.model}")
        # print(f"   Cache: {cache_file if cache_file else 'Memory only'}")
        # print(f"   Max cache size: {max_cache_size}")

    def summarize(self, text: str) -> str:
        """
        Summarize text with caching

        Args:
            text: Text to summarize

        Returns:
            Summary string
        """

        if not text or not text.strip():
            return ""

        # Clean input text
        text = text.strip()

        # Update request count
        self.stats["total_requests"] += 1

        # Try cache first
        cached_summary = self.cache.get(text)
        if cached_summary:
            self.stats["cache_hits"] += 1
            # print(f"📋 Cache hit! (Total hits: {self.stats['cache_hits']}/{self.stats['total_requests']})")
            return cached_summary

        # Cache miss - call API
        # print(f"🌐 API call... (Cache misses: {self.stats['api_calls'] + 1})")

        try:
            summary = self.summarizer.summarize(text)

            # Cache the result
            self.cache.set(text, summary)

            # Update stats
            self.stats["api_calls"] += 1

            # Estimate cost saved (rough calculation for claude-3-haiku)
            estimated_tokens = len(text.split()) * 1.3  # Rough token estimate
            estimated_cost_saved = (
                estimated_tokens / 1000000
            ) * 0.25  # $0.25 per 1M tokens
            self.stats["total_cost_saved"] += estimated_cost_saved

            return summary

        except Exception as e:
            logger.error(f"Error during summarization: {e}")
            raise

    def get_stats(self) -> Dict[str, Any]:
        """Get usage and cache statistics"""
        cache_stats = self.cache.get_stats()

        hit_rate = (
            self.stats["cache_hits"] / self.stats["total_requests"] * 100
            if self.stats["total_requests"] > 0
            else 0
        )

        return {
            "requests": {
                "total": self.stats["total_requests"],
                "cache_hits": self.stats["cache_hits"],
                "api_calls": self.stats["api_calls"],
                "hit_rate_percent": round(hit_rate, 1),
            },
            "cache": cache_stats,
            "estimated_cost_saved": round(self.stats["total_cost_saved"], 4),
            "model": self.config.model,
        }

    def clear_cache(self) -> None:
        """Clear all cached summaries"""
        self.cache.clear()
        logger.info("Cache cleared")

    def __str__(self) -> str:
        stats = self.get_stats()
        return (
            f"CachedLLM(model={self.config.model}, "
            f"requests={stats['requests']['total']}, "
            f"hit_rate={stats['requests']['hit_rate_percent']}%)"
        )


def main() -> None:
    """Example usage of CachedLLM"""

    # Sample texts
    sample_texts = [
        """
        The rise of artificial intelligence represents one of the most significant
        technological developments of the 21st century. Machine learning algorithms
        have achieved remarkable breakthroughs in areas such as natural language
        processing, computer vision, and strategic game playing. Companies across
        industries are integrating AI solutions to automate processes, enhance
        decision-making, and create new products and services. However, this rapid
        advancement also brings challenges including ethical considerations, job
        displacement concerns, and the need for robust governance frameworks.
        """,
        """
        Climate change continues to pose significant challenges to global ecosystems
        and human societies. Rising temperatures, changing precipitation patterns, and
        extreme weather events are affecting agriculture, water resources, and coastal
        communities worldwide. International efforts to address climate change through
        emissions reduction and adaptation strategies are ongoing, but scientists
        emphasize the urgency of accelerated action to limit global temperature rise
        and mitigate the most severe potential impacts.
        """,
        # Duplicate of first text to demonstrate caching
        """
        The rise of artificial intelligence represents one of the most significant
        technological developments of the 21st century. Machine learning algorithms
        have achieved remarkable breakthroughs in areas such as natural language
        processing, computer vision, and strategic game playing. Companies across
        industries are integrating AI solutions to automate processes, enhance
        decision-making, and create new products and services. However, this rapid
        advancement also brings challenges including ethical considerations, job
        displacement concerns, and the need for robust governance frameworks.
        """,
    ]

    try:
        print("=" * 60)
        print("🧠 CachedLLM Demo")
        print("=" * 60)

        # Initialize CachedLLM
        llm = CachedLLM(cache_file=".demo_cache.json")

        # Process texts
        for i, text in enumerate(sample_texts, 1):
            print(f"\n📝 Processing text {i}:")
            print(f"Text preview: {text.strip()[:100]}...")

            summary = llm.summarize(text)
            print(f"Summary: {summary}")
            print("-" * 40)

        # Show statistics
        print("\n📊 Final Statistics:")
        stats = llm.get_stats()

        print(f"Total requests: {stats['requests']['total']}")
        print(f"Cache hits: {stats['requests']['cache_hits']}")
        print(f"API calls: {stats['requests']['api_calls']}")
        print(f"Hit rate: {stats['requests']['hit_rate_percent']}%")
        print(f"Cache size: {stats['cache']['size']}")
        print(f"Estimated cost saved: ${stats['estimated_cost_saved']}")

        print("\n✅ Demo completed!")
        print(f"Final state: {llm}")

    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        print("\nCreate a .env file with:")
        print("ANTHROPIC_API_KEY=your_api_key_here")

    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()
