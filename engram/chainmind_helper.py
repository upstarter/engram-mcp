"""
ChainMind Helper for engram-mcp
================================

Provides cost-optimized text generation with automatic fallback when Claude
hits usage/token limits. This helps avoid purchasing extra credits by automatically
using alternative providers when Claude's monthly limit is reached.
"""

import os
import sys
import logging
import uuid
import time
import hashlib
from typing import Optional, Dict, Any, List
from datetime import datetime
from collections import OrderedDict

# Add ChainMind to path
CHAINMIND_PATH = "/mnt/dev/ai/ai-platform/chainmind"
if CHAINMIND_PATH not in sys.path:
    sys.path.insert(0, CHAINMIND_PATH)

# Setup structured logging
logger = logging.getLogger("engram.chainmind_helper")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stderr)
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class ChainMindHelper:
    """
    Helper class for Claude to use ChainMind's cost optimization and usage limit handling.

    Key Features:
    - Tries Claude first (preferred provider)
    - Automatically falls back to alternative providers when Claude hits usage limits
    - Provides usage limit status to Claude
    - Graceful degradation if ChainMind unavailable
    """

    def __init__(self, cache_size: int = 100, config: Optional[Dict[str, Any]] = None):
        self._router = None
        self._initialized = False
        self._usage_limit_detected = False

        # Load configuration
        self._config = self._load_config(config)
        self._fallback_providers = self._config.get("fallback_providers", ["openai", "ollama"])
        self._max_tokens_per_request = self._config.get("max_tokens_per_request")
        self._max_cost_per_request = self._config.get("max_cost_per_request")
        self._request_timeout_seconds = self._config.get("request_timeout_seconds", 60.0)

        # Model selection configuration
        model_selection_config = self._config.get("model_selection", {})
        self._auto_select_enabled = model_selection_config.get("auto_select_enabled", True)  # Default to enabled
        # PRIMARY: Claude - Default to prefer_claude since user uses Claude Code mostly
        self._default_strategy = model_selection_config.get("default_strategy", "prefer_claude")

        self._error_classifier = None
        self._init_attempts = 0
        self._last_init_error = None

        # Response cache (LRU)
        self._cache_size = cache_size
        self._response_cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()

        # Provider health tracking
        self._provider_health: Dict[str, Dict[str, Any]] = {}

        # Metrics
        self._metrics = {
            "total_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "fallback_requests": 0,
            "provider_usage": {},
            "error_counts": {},
            "total_latency": 0.0,
            "circuit_breaker_skips": 0,
            "batch_requests": 0,
            "connection_pool_reuses": 0
        }

    def _init_chainmind(self, retry_count: int = 0, max_retries: int = 3):
        """Initialize ChainMind router (lazy) with retry logic."""
        if self._initialized:
            return

        try:
            # Import and register core services first
            from backend.core.di import get_container
            from backend.core.di.service_registrations import register_core_services

            container = get_container()

            # Ensure core services are registered
            register_core_services(container)

            # Use the correct interface names from router_extensions.py
            # (These match what service_registrations.py registers)
            from backend.core.interfaces.router_extensions import (
                TwoTierRouterInterface,
                StrategicRouterInterface,
                TacticalRouterInterface,
            )

            # Try to resolve the router directly
            try:
                resolved_router = container.resolve(TwoTierRouterInterface)
                if resolved_router is not None:
                    self._router = resolved_router
                    self._initialized = True
                    logger.info("ChainMind router initialized from DI container")

                    # Initialize error classifier
                    try:
                        from backend.core.errors.standardized_provider_errors import get_provider_error_classifier
                        self._error_classifier = get_provider_error_classifier()
                    except Exception as classifier_error:
                        logger.warning(f"Failed to initialize error classifier: {classifier_error}")

                    return
                else:
                    logger.debug("DI resolution returned None, trying fallback")
            except Exception as di_error:
                logger.debug(f"DI resolution failed, trying fallback: {di_error}")

            # Fallback: Resolve routers from DI container and create TwoTierRouter
            print("Creating router via DI resolution (fallback mode)...", file=sys.stderr)
            from backend.core.routing.two_tier_router import TwoTierRouter

            # Resolve strategic and tactical routers from DI
            strategic_router = container.resolve(StrategicRouterInterface)
            tactical_router = container.resolve(TacticalRouterInterface)

            if strategic_router and tactical_router:
                self._router = TwoTierRouter(
                    strategic_router=strategic_router,
                    tactical_router=tactical_router
                )
                self._initialized = True
                logger.info("ChainMind router initialized (fallback mode)")

                # Initialize error classifier
                try:
                    from backend.core.errors.standardized_provider_errors import get_provider_error_classifier
                    self._error_classifier = get_provider_error_classifier()
                except Exception as classifier_error:
                    logger.warning(f"Failed to initialize error classifier: {classifier_error}")

                return
            else:
                raise RuntimeError(f"Failed to resolve routers: strategic={strategic_router is not None}, tactical={tactical_router is not None}")

        except Exception as e:
            self._init_attempts += 1
            self._last_init_error = str(e)

            # Retry with exponential backoff for transient errors
            if retry_count < max_retries:
                import time
                delay = (2 ** retry_count) * 0.5  # 0.5s, 1s, 2s
                logger.info(f"Retrying ChainMind initialization (attempt {retry_count + 1}/{max_retries}) after {delay}s")
                time.sleep(delay)
                return self._init_chainmind(retry_count + 1, max_retries)

            logger.warning(f"ChainMind initialization failed (attempt {self._init_attempts}): {e}", exc_info=True)
            self._router = None
            self._initialized = True  # Mark as attempted

    async def generate(
        self,
        prompt: str,
        prefer_claude: Optional[bool] = True,
        auto_select_model: bool = False,
        fallback_providers: Optional[List[str]] = None,
        agent_role: Optional[str] = None,
        agent_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate text using ChainMind's routing with usage limit handling and smart model selection.

        Args:
            prompt: The prompt to generate from
            prefer_claude: If True, try Claude first. If False, use ChainMind routing.
                         If None, auto-select based on task (requires auto_select_model=True)
            auto_select_model: If True, use ChainMind's strategic router for optimal model selection
            fallback_providers: List of providers to try if Claude hits limits
            **kwargs: Additional parameters (temperature, max_tokens, etc.)

        Returns:
            Dict with:
            - response: Generated text
            - provider: Provider used
            - model: Model used (if available)
            - fallback_used: Whether fallback was needed
            - usage_limit_hit: Whether Claude usage limit was hit
            - model_selection: Information about model selection (if auto_select_model=True)
        """
        # IMPORTANT: Claude Code already uses Claude API by default
        # ChainMind is ONLY called when Claude Code's Claude API hits token limits
        # Therefore: Skip Claude, use smart routing to select best fallback (OpenAI)

        # Auto-select model if requested or enabled by config
        if auto_select_model or (prefer_claude is None and self._auto_select_enabled):
            return await self._generate_with_smart_routing(prompt, fallback_providers, agent_role=agent_role, agent_id=agent_id, **kwargs)

        # If prefer_claude is False (default), skip Claude (Claude Code already tried it)
        if not prefer_claude:
            # Skip Claude, go straight to fallback providers
            return await self._generate_with_fallback_skip_claude(prompt, fallback_providers, agent_role=agent_role, agent_id=agent_id, **kwargs)

        # Generate correlation ID for request tracking
        correlation_id = str(uuid.uuid4())[:8]
        start_time = time.time()
        self._metrics["total_requests"] += 1

        logger.info(f"[{correlation_id}] Starting generation request", extra={
            "correlation_id": correlation_id,
            "prefer_claude": prefer_claude,
            "prompt_length": len(prompt)
        })

        # Validate request limits
        try:
            self._validate_request_limits(prompt, kwargs)
        except ValueError as e:
            logger.warning(f"[{correlation_id}] Request validation failed: {e}")
            self._metrics["failed_requests"] += 1
            raise

        # Check cache for duplicate requests
        cache_key = self._generate_cache_key(prompt, prefer_claude if prefer_claude is not None else False, kwargs)
        if cache_key in self._response_cache:
            cached_result = self._response_cache[cache_key]
            # Move to end (most recently used)
            self._response_cache.move_to_end(cache_key)
            self._metrics["cache_hits"] += 1

            logger.info(f"[{correlation_id}] Cache hit", extra={
                "correlation_id": correlation_id,
                "cache_key": cache_key[:16]
            })

            # Return cached result with new correlation ID
            result = cached_result.copy()
            result["correlation_id"] = correlation_id
            result["from_cache"] = True
            return result

        self._metrics["cache_misses"] += 1

        self._init_chainmind()

        if not self._router:
            error_msg = "ChainMind router not available"
            logger.error(f"[{correlation_id}] {error_msg}")
            self._metrics["failed_requests"] += 1
            raise RuntimeError(error_msg)

        fallback_providers = fallback_providers or self._fallback_providers

        # Try Claude first if preferred
        if prefer_claude:
            try:
                result = await self._try_provider_with_timeout(
                    prompt=prompt,
                    provider="anthropic",
                    correlation_id=correlation_id,
                    timeout=self._request_timeout_seconds,
                    **kwargs
                )

                # Validate and extract response
                response_text = self._extract_response(result)
                if not response_text or not response_text.strip():
                    logger.warning(f"[{correlation_id}] Empty response received from Claude")
                    raise ValueError("Empty response received from provider")

                latency = time.time() - start_time
                self._metrics["successful_requests"] += 1
                self._metrics["total_latency"] += latency
                self._metrics["provider_usage"]["anthropic"] = self._metrics["provider_usage"].get("anthropic", 0) + 1

                logger.info(f"[{correlation_id}] Successfully generated response", extra={
                    "correlation_id": correlation_id,
                    "provider": "anthropic",
                    "response_length": len(response_text),
                    "latency_seconds": round(latency, 3)
                })

                # Success with Claude
                response = {
                    "response": response_text,
                    "provider": "anthropic",
                    "fallback_used": False,
                    "usage_limit_hit": False,
                    "metadata": self._extract_metadata(result),
                    "correlation_id": correlation_id,
                    "latency_seconds": latency,
                    "from_cache": False
                }

                # Cache the result
                self._cache_result(cache_key, response)

                return response

            except Exception as e:
                # Classify error using ProviderErrorClassifier
                error_category = self._classify_error(e, "anthropic")
                is_usage_limit = self._is_usage_limit_error(e, error_category)

                logger.warning(f"[{correlation_id}] Claude request failed", extra={
                    "correlation_id": correlation_id,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "error_category": error_category,
                    "is_usage_limit": is_usage_limit
                }, exc_info=True)

                if is_usage_limit:
                    self._usage_limit_detected = True
                    logger.info(f"[{correlation_id}] Claude usage limit detected, falling back to alternatives")

                    # Try fallback providers in parallel for faster response
                    fallback_errors = []
                    healthy_providers = [
                        p for p in fallback_providers
                        if self._check_provider_health(p)
                    ]

                    # Skip unhealthy providers
                    for provider in fallback_providers:
                        if provider not in healthy_providers:
                            logger.debug(f"[{correlation_id}] Skipping unhealthy provider: {provider}")
                            fallback_errors.append({
                                "provider": provider,
                                "error_type": "CircuitBreakerOpenError",
                                "error_message": "Provider circuit breaker is open",
                                "error_category": "service_unavailable"
                            })

                    # Filter providers by capabilities
                    capable_providers = [
                        p for p in healthy_providers
                        if self._match_provider_capabilities(p, kwargs)
                    ]

                    if not capable_providers:
                        # All providers unhealthy or incapable - skip to error aggregation
                        logger.warning(f"[{correlation_id}] No capable fallback providers available")
                    else:
                        # Try all healthy providers in parallel
                        async def try_fallback_provider(provider: str):
                            """Try a single fallback provider."""
                            try:
                                return await self._try_provider_with_timeout(
                                    prompt=prompt,
                                    provider=provider,
                                    correlation_id=correlation_id,
                                    timeout=self._request_timeout_seconds,
                                    **kwargs
                                ), provider, None
                            except Exception as fallback_error:
                                fallback_category = self._classify_error(fallback_error, provider)
                                return None, provider, {
                                    "error_type": type(fallback_error).__name__,
                                    "error_message": str(fallback_error),
                                    "error_category": fallback_category
                                }

                        # Execute all fallback attempts in parallel
                        fallback_tasks = [
                            try_fallback_provider(provider)
                            for provider in capable_providers
                        ]

                        fallback_results = await asyncio.gather(*fallback_tasks, return_exceptions=True)

                        # Process results - return first successful
                        for result in fallback_results:
                            if isinstance(result, Exception):
                                continue

                            result_data, provider, error_info = result

                            if error_info:
                                # Failed attempt
                                fallback_errors.append({
                                    "provider": provider,
                                    **error_info
                                })
                                logger.warning(f"[{correlation_id}] Fallback provider {provider} failed", extra={
                                    "correlation_id": correlation_id,
                                    "provider": provider,
                                    "error_type": error_info["error_type"],
                                    "error_category": error_info["error_category"]
                                })
                            elif result_data:
                                # Success!
                                response_text = self._extract_response(result_data)
                                if not response_text or not response_text.strip():
                                    logger.warning(f"[{correlation_id}] Empty response from {provider}")
                                    fallback_errors.append({
                                        "provider": provider,
                                        "error_type": "ValueError",
                                        "error_message": "Empty response from provider",
                                        "error_category": "validation"
                                    })
                                    continue

                                latency = time.time() - start_time
                                self._metrics["successful_requests"] += 1
                                self._metrics["fallback_requests"] += 1
                                self._metrics["total_latency"] += latency
                                self._metrics["provider_usage"][provider] = self._metrics["provider_usage"].get(provider, 0) + 1

                                logger.info(f"[{correlation_id}] Fallback successful (parallel)", extra={
                                    "correlation_id": correlation_id,
                                    "provider": provider,
                                    "response_length": len(response_text),
                                    "latency_seconds": round(latency, 3)
                                })

                                # Success with fallback
                                response = {
                                    "response": response_text,
                                    "provider": provider,
                                    "fallback_used": True,
                                    "usage_limit_hit": True,
                                    "fallback_reason": "Claude usage limit exceeded",
                                    "metadata": self._extract_metadata(result_data),
                                    "correlation_id": correlation_id,
                                    "latency_seconds": latency,
                                    "original_error": {
                                        "type": type(e).__name__,
                                        "message": str(e),
                                        "category": error_category
                                    },
                                    "from_cache": False
                                }

                                # Cache the result
                                self._cache_result(cache_key, response)

                                return response

                    # All fallbacks failed - aggregate errors
                    latency = time.time() - start_time
                    self._metrics["failed_requests"] += 1
                    error_type = type(e).__name__
                    self._metrics["error_counts"][error_type] = self._metrics["error_counts"].get(error_type, 0) + 1

                    error_details = {
                        "original_error": {
                            "provider": "anthropic",
                            "type": error_type,
                            "message": str(e),
                            "category": error_category
                        },
                        "fallback_errors": fallback_errors,
                        "correlation_id": correlation_id,
                        "latency_seconds": latency
                    }

                    aggregated_error = RuntimeError(
                        f"Claude usage limit exceeded and all fallback providers failed. "
                        f"Original error: {error_type}: {str(e)}. "
                        f"Fallback attempts: {len(fallback_errors)}"
                    )
                    aggregated_error.error_details = error_details
                    raise aggregated_error
                else:
                    # Other error, preserve context and re-raise
                    error_with_context = type(e)(f"{str(e)} (correlation_id: {correlation_id})")
                    error_with_context.correlation_id = correlation_id
                    error_with_context.error_category = error_category
                    raise error_with_context from e

        else:
            # Don't prefer Claude, use ChainMind's routing
            result = await self._router.route(
                prompt=prompt,
                prefer_lower_cost=True,
                **kwargs
            )

            response_text = self._extract_response(result)
            if not response_text or not response_text.strip():
                logger.warning(f"[{correlation_id}] Empty response from ChainMind routing")
                raise ValueError("Empty response received from provider")

            latency = time.time() - start_time
            provider = self._extract_provider(result)
            self._metrics["successful_requests"] += 1
            self._metrics["total_latency"] += latency
            self._metrics["provider_usage"][provider] = self._metrics["provider_usage"].get(provider, 0) + 1

            logger.info(f"[{correlation_id}] Generated via ChainMind routing", extra={
                "correlation_id": correlation_id,
                "provider": provider,
                "response_length": len(response_text),
                "latency_seconds": round(latency, 3)
            })

            response = {
                "response": response_text,
                "provider": provider,
                "fallback_used": False,
                "usage_limit_hit": False,
                "metadata": self._extract_metadata(result),
                "correlation_id": correlation_id,
                "latency_seconds": latency,
                "from_cache": False
            }

            # Cache the result
            self._cache_result(cache_key, response)

            return response

    async def _generate_with_smart_routing(
        self,
        prompt: str,
        fallback_providers: Optional[List[str]] = None,
        agent_role: Optional[str] = None,
        agent_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate using ChainMind's strategic router for optimal model selection.

        This method uses ChainMind's StrategicRouter to analyze the task and select
        the optimal model based on task type, capabilities, cost, and performance.

        Args:
            prompt: The prompt to generate from
            fallback_providers: List of providers for fallback (used if smart routing fails)
            **kwargs: Additional parameters

        Returns:
            Dict with response and model selection information
        """
        correlation_id = str(uuid.uuid4())[:8]
        start_time = time.time()
        self._metrics["total_requests"] += 1

        logger.info(f"[{correlation_id}] Starting smart routing request", extra={
            "correlation_id": correlation_id,
            "prompt_length": len(prompt),
            "smart_routing": True
        })

        # Validate request limits
        try:
            self._validate_request_limits(prompt, kwargs)
        except ValueError as e:
            logger.warning(f"[{correlation_id}] Request validation failed: {e}")
            self._metrics["failed_requests"] += 1
            raise

        # Check cache (use smart routing cache key)
        cache_key = self._generate_cache_key(prompt, False, kwargs)  # False = smart routing
        if cache_key in self._response_cache:
            cached_result = self._response_cache[cache_key]
            self._response_cache.move_to_end(cache_key)
            self._metrics["cache_hits"] += 1

            logger.info(f"[{correlation_id}] Cache hit (smart routing)", extra={
                "correlation_id": correlation_id,
                "cache_key": cache_key[:16]
            })

            result = cached_result.copy()
            result["correlation_id"] = correlation_id
            result["from_cache"] = True
            return result

        self._metrics["cache_misses"] += 1

        self._init_chainmind()

        if not self._router:
            error_msg = "ChainMind router not available"
            logger.error(f"[{correlation_id}] {error_msg}")
            self._metrics["failed_requests"] += 1
            raise RuntimeError(error_msg)

        # Build request for strategic router
        # IMPORTANT: Claude Code already uses Claude API by default
        # ChainMind is ONLY called when Claude Code's Claude API hits token limits
        # Therefore: Skip Claude, prefer OpenAI as primary fallback
        # Let ChainMind's StrategicRouter do all the analysis via its InputAnalyzer
        request = {
            "prompt": prompt,
            "provider": "openai",  # PRIMARY FALLBACK: OpenAI (Claude Code already tried Claude)
            "budget_constraints": {
                "prefer_lower_cost": kwargs.get("prefer_lower_cost", True),  # Cost optimization for fallback
                "enforce_budget": kwargs.get("enforce_budget", False),
                "max_cost": kwargs.get("max_cost", self._max_cost_per_request),
            },
            "prefer_local": kwargs.get("prefer_local", False),
            # Pass agent_role for optimal domain/model selection
            "agent_role": agent_role,
            # Pass agent_id for context isolation (per-agent history tracking)
            "agent_id": agent_id,
            "context": {
                "agent_role": agent_role,
                "agent_id": agent_id
            } if agent_role or agent_id else {},
            # Don't specify task_type/complexity - let ChainMind's InputAnalyzer determine it
            **{k: v for k, v in kwargs.items() if k not in ["prefer_lower_cost", "enforce_budget", "max_cost", "prefer_local", "provider", "agent_role", "agent_id"]}
        }

        try:
            # Use route_request() for full strategic routing
            if hasattr(self._router, "route_request"):
                # Use strategic routing for optimal model selection
                result = await self._router.route_request(request)
            else:
                # Fallback to simple route() if route_request not available
                logger.warning(f"[{correlation_id}] route_request not available, using simple route")
                result = await self._router.route(
                    prompt=prompt,
                    prefer_lower_cost=True,
                    **kwargs
                )

            # Extract response
            response_text = self._extract_response(result)
            if not response_text or not response_text.strip():
                logger.warning(f"[{correlation_id}] Empty response from smart routing")
                raise ValueError("Empty response received from provider")

            latency = time.time() - start_time
            provider = self._extract_provider(result)
            model = result.get("model") or result.get("model_info", {}).get("model_id", "unknown")

            self._metrics["successful_requests"] += 1
            self._metrics["total_latency"] += latency
            self._metrics["provider_usage"][provider] = self._metrics["provider_usage"].get(provider, 0) + 1

            # Extract task analysis from ChainMind's result (it does the analysis)
            task_type = result.get("task_type") or result.get("analysis", {}).get("task_type", "general")
            complexity = result.get("complexity") or result.get("analysis", {}).get("complexity", "medium")

            logger.info(f"[{correlation_id}] Smart routing successful", extra={
                "correlation_id": correlation_id,
                "provider": provider,
                "model": model,
                "task_type": task_type,
                "response_length": len(response_text),
                "latency_seconds": round(latency, 3)
            })

            # Build response with model selection info
            response = {
                "response": response_text,
                "provider": provider,
                "model": model,
                "fallback_used": False,
                "usage_limit_hit": False,
                "metadata": self._extract_metadata(result),
                "correlation_id": correlation_id,
                "latency_seconds": latency,
                "from_cache": False,
                "model_selection": {
                    "method": "smart_routing",
                    "task_type": task_type,  # From ChainMind's analysis
                    "complexity": complexity,  # From ChainMind's analysis
                    "selected_provider": provider,
                    "selected_model": model,
                    "routing_strategy": result.get("strategy", "capability_match"),
                    "model_info": result.get("model_info", {})
                }
            }

            # Cache the result
            self._cache_result(cache_key, response)

            return response

        except Exception as e:
            # If smart routing fails, fall back to standard routing with fallback providers
            logger.warning(f"[{correlation_id}] Smart routing failed, falling back to standard routing", extra={
                "correlation_id": correlation_id,
                "error": str(e),
                "error_type": type(e).__name__
            }, exc_info=True)

            # Fallback to standard routing
            fallback_providers = fallback_providers or self._fallback_providers
            return await self._generate_with_fallback(
                prompt=prompt,
                prefer_claude=False,  # Don't prefer Claude in fallback
                fallback_providers=fallback_providers,
                correlation_id=correlation_id,
                start_time=start_time,
                cache_key=cache_key,
                **kwargs
            )

    async def _generate_with_fallback_skip_claude(
        self,
        prompt: str,
        fallback_providers: List[str],
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate with fallback logic, skipping Claude (used when Claude Code already tried Claude).

        IMPORTANT: Claude Code already uses Claude API by default.
        This method is called when Claude Code's Claude API hits token limits.
        Therefore: Skip Claude, go straight to OpenAI as primary fallback.
        """
        correlation_id = str(uuid.uuid4())[:8]
        start_time = time.time()
        self._metrics["total_requests"] += 1

        logger.info(f"[{correlation_id}] Starting fallback (Claude Code already tried Claude)", extra={
            "correlation_id": correlation_id,
            "prompt_length": len(prompt),
            "skip_claude": True
        })

        # Generate cache key
        cache_key = self._generate_cache_key(prompt, False, kwargs)  # False = not preferring Claude

        # Check cache
        if cache_key in self._response_cache:
            cached_result = self._response_cache[cache_key]
            self._response_cache.move_to_end(cache_key)
            self._metrics["cache_hits"] += 1
            result = cached_result.copy()
            result["correlation_id"] = correlation_id
            result["from_cache"] = True
            return result

        self._metrics["cache_misses"] += 1

        # Try providers in order (skip Claude)
        for provider in fallback_providers:
            if not self._check_provider_health(provider):
                continue

            try:
                result = await self._try_provider_with_timeout(
                    prompt=prompt,
                    provider=provider,
                    correlation_id=correlation_id,
                    timeout=self._request_timeout_seconds,
                    **kwargs
                )

                response_text = self._extract_response(result)
                if response_text and response_text.strip():
                    latency = time.time() - start_time
                    self._metrics["successful_requests"] += 1
                    self._metrics["total_latency"] += latency
                    self._metrics["provider_usage"][provider] = self._metrics["provider_usage"].get(provider, 0) + 1

                    response = {
                        "response": response_text,
                        "provider": provider,
                        "fallback_used": True,
                        "usage_limit_hit": False,
                        "metadata": self._extract_metadata(result),
                        "correlation_id": correlation_id,
                        "latency_seconds": latency,
                        "from_cache": False
                    }

                    self._cache_result(cache_key, response)
                    return response

            except Exception as e:
                logger.debug(f"[{correlation_id}] Provider {provider} failed: {e}")
                continue

        # All providers failed
        self._metrics["failed_requests"] += 1
        raise RuntimeError(f"All providers failed. Last error: {e}")

    def _match_provider_capabilities(
        self,
        provider: str,
        requirements: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Check if provider matches request requirements.

        Args:
            provider: Provider name
            requirements: Optional requirements dict (model, max_tokens, etc.)

        Returns:
            True if provider can handle the request
        """
        if not requirements:
            return True

        # Basic capability matching
        # Ollama may not support all models
        if provider.lower() in ["ollama", "local"]:
            # Check if specific model is required that Ollama might not have
            required_model = requirements.get("model")
            if required_model and "claude" in required_model.lower():
                return False  # Ollama doesn't have Claude models

        # Check token limits if specified
        max_tokens = requirements.get("max_tokens")
        if max_tokens:
            # Some providers have lower token limits
            if provider.lower() == "ollama" and max_tokens > 8192:
                return False  # Many Ollama models have 8k context

        return True

    async def _try_provider(
        self,
        prompt: str,
        provider: str,
        correlation_id: Optional[str] = None,
        **kwargs
    ) -> Any:
        """Try generating with a specific provider."""
        # Map provider names to ChainMind provider names
        provider_map = {
            "anthropic": "anthropic",
            "claude": "anthropic",
            "openai": "openai",
            "gpt": "openai",
            "ollama": "ollama",
            "local": "ollama"
        }

        mapped_provider = provider_map.get(provider.lower(), provider.lower())

        # Check provider capabilities
        if not self._match_provider_capabilities(mapped_provider, kwargs):
            raise ValueError(
                f"Provider {mapped_provider} does not support the requested capabilities"
            )

        if correlation_id:
            logger.debug(f"[{correlation_id}] Attempting provider: {mapped_provider}")

        return await self._router.route(
            prompt=prompt,
            provider=mapped_provider,
            **kwargs
        )

    def _classify_error(self, error: Exception, provider: Optional[str] = None) -> str:
        """Classify error using ChainMind's ProviderErrorClassifier."""
        if self._error_classifier:
            try:
                # Extract error context if available
                error_context = {}
                if hasattr(error, "details") and isinstance(error.details, dict):
                    error_context = error.details
                if hasattr(error, "code"):
                    error_context["error_code"] = str(error.code)

                return self._error_classifier.classify_error(error, provider, error_context)
            except Exception as classifier_error:
                logger.debug(f"Error classifier failed: {classifier_error}")

        # Fallback to basic classification
        error_str = str(error).lower()
        if "quota" in error_str or "usage limit" in error_str:
            return "quota_exceeded"
        elif "rate limit" in error_str:
            return "rate_limit"
        elif "auth" in error_str or "invalid api key" in error_str:
            return "authentication"
        else:
            return "unknown"

    def _is_usage_limit_error(self, error: Exception, error_category: Optional[str] = None) -> bool:
        """Check if error is a usage/token limit error."""
        # Use error category if provided
        if error_category:
            from backend.core.errors.standardized_provider_errors import ProviderErrorCategory
            return error_category == ProviderErrorCategory.QUOTA_EXCEEDED

        # Check exception type hierarchy first
        try:
            from backend.core.errors.additional_errors import QuotaExceededError
            if isinstance(error, QuotaExceededError):
                return True
        except ImportError:
            pass

        # Check for wrapped exceptions
        current_error = error
        for _ in range(5):  # Max depth for exception chain
            error_type = type(current_error).__name__
            if "QuotaExceededError" in error_type or "QuotaExceeded" in error_type:
                return True

            # Check error code
            if hasattr(current_error, "code"):
                error_code = str(getattr(current_error, "code", ""))
                if "1801" in error_code or "QUOTA_EXCEEDED" in error_code:
                    return True

            # Check if there's a cause
            if hasattr(current_error, "__cause__") and current_error.__cause__:
                current_error = current_error.__cause__
            elif hasattr(current_error, "cause") and current_error.cause:
                current_error = current_error.cause
            else:
                break

        # Use error classifier if available
        if self._error_classifier:
            try:
                category = self._classify_error(error)
                from backend.core.errors.standardized_provider_errors import ProviderErrorCategory
                return category == ProviderErrorCategory.QUOTA_EXCEEDED
            except Exception:
                pass

        # Fallback to string matching
        error_str = str(error).lower()
        usage_limit_indicators = [
            "quota exceeded",
            "usage limit",
            "token limit",
            "monthly limit",
            "billing limit",
            "insufficient credits",
            "payment required",
            "purchase extra",
            "extra usage credits",
            "cm-1801",
            "error code: 1801",
        ]

        for indicator in usage_limit_indicators:
            if indicator in error_str:
                return True

        return False

    def _extract_response(self, result: Any) -> str:
        """Extract response text from ChainMind result with validation."""
        response_text = None

        if isinstance(result, dict):
            # Try multiple possible keys
            response_text = (
                result.get("response") or
                result.get("text") or
                result.get("content") or
                result.get("output")
            )

            # Handle nested response structures
            if not response_text and "choices" in result and len(result["choices"]) > 0:
                choice = result["choices"][0]
                if isinstance(choice, dict):
                    if "message" in choice and isinstance(choice["message"], dict):
                        response_text = choice["message"].get("content") or choice["message"].get("text")
                    elif "text" in choice:
                        response_text = choice["text"]
                    elif "content" in choice:
                        response_text = choice["content"]

            # Handle message dict structure
            if not response_text and "message" in result:
                if isinstance(result["message"], dict):
                    response_text = result["message"].get("content") or result["message"].get("text")
                elif isinstance(result["message"], str):
                    response_text = result["message"]

        elif hasattr(result, "response"):
            response_text = result.response
        elif hasattr(result, "text"):
            response_text = result.text
        elif hasattr(result, "content"):
            response_text = result.content

        # Convert to string and validate
        if response_text is None:
            response_text = str(result)

        # Ensure it's a string
        if not isinstance(response_text, str):
            response_text = str(response_text)

        # Validate non-empty
        if not response_text.strip():
            logger.warning("Extracted empty response from result")
            return ""

        return response_text

    def _extract_provider(self, result: Any) -> str:
        """Extract provider name from ChainMind result."""
        if isinstance(result, dict):
            return result.get("provider", "unknown")
        elif hasattr(result, "provider"):
            return result.provider
        else:
            return "unknown"

    def _extract_metadata(self, result: Any) -> Dict[str, Any]:
        """Extract and normalize metadata from ChainMind result."""
        metadata = {}

        if isinstance(result, dict):
            # Extract metadata dict if present
            metadata = result.get("metadata", {}).copy() if isinstance(result.get("metadata"), dict) else {}

            # Extract token usage information
            tokens_info = {}
            if "tokens_used" in result:
                tokens_data = result["tokens_used"]
                if isinstance(tokens_data, dict):
                    tokens_info = tokens_data.copy()
                elif isinstance(tokens_data, (int, float)):
                    tokens_info = {"total": int(tokens_data)}

            # Also check usage field (OpenAI format)
            if "usage" in result and isinstance(result["usage"], dict):
                usage = result["usage"]
                tokens_info.update({
                    "input": usage.get("prompt_tokens", tokens_info.get("input", 0)),
                    "output": usage.get("completion_tokens", tokens_info.get("output", 0)),
                    "total": usage.get("total_tokens", tokens_info.get("total", 0))
                })

            if tokens_info:
                metadata["tokens"] = tokens_info

            # Extract cost information
            if "cost" in result:
                metadata["cost"] = result["cost"]

            # Extract execution time
            if "execution_time" in result:
                metadata["execution_time"] = result["execution_time"]
            elif "latency" in result:
                metadata["execution_time"] = result["latency"]

            # Extract model information
            if "model" in result:
                metadata["model"] = result["model"]

            # Extract request ID
            if "request_id" in result:
                metadata["request_id"] = result["request_id"]

            # Extract from_cache flag
            if "from_cache" in result:
                metadata["from_cache"] = result["from_cache"]

        elif hasattr(result, "metadata"):
            metadata = result.metadata if isinstance(result.metadata, dict) else {}

        return metadata

    def is_available(self) -> bool:
        """Check if ChainMind is available."""
        if not self._initialized:
            self._init_chainmind()

        available = self._router is not None
        if not available and self._last_init_error:
            logger.debug(f"ChainMind unavailable: {self._last_init_error}")

        return available

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on ChainMind router.

        Returns:
            Dict with health status and details
        """
        health_status = {
            "router_initialized": self._router is not None,
            "initialization_attempts": self._init_attempts,
            "last_init_error": self._last_init_error,
            "healthy": False
        }

        if not self._router:
            return health_status

        # Try a simple routing operation to verify router is functional
        try:
            # Use a minimal test prompt
            test_result = await self._router.route(
                prompt="test",
                provider="anthropic",
                max_tokens=1
            )

            # If we got a result (even if empty), router is functional
            health_status["healthy"] = True
            health_status["test_successful"] = True

        except Exception as e:
            health_status["healthy"] = False
            health_status["test_error"] = str(e)
            health_status["test_error_type"] = type(e).__name__

        return health_status

    def get_usage_status(self) -> Dict[str, Any]:
        """Get current usage limit status."""
        return {
            "usage_limit_detected": self._usage_limit_detected,
            "fallback_providers": self._fallback_providers,
            "initialization_attempts": self._init_attempts,
            "last_init_error": self._last_init_error if self._init_attempts > 0 else None,
            "router_available": self._router is not None
        }

    def get_metrics(self) -> Dict[str, Any]:
        """Get performance and usage metrics."""
        total_requests = self._metrics["total_requests"]
        avg_latency = (
            self._metrics["total_latency"] / total_requests
            if total_requests > 0 else 0.0
        )
        cache_hit_rate = (
            self._metrics["cache_hits"] / total_requests * 100
            if total_requests > 0 else 0.0
        )

        # Get connection pool metrics if available
        pool_metrics = self._get_pool_metrics()

        return {
            "total_requests": total_requests,
            "successful_requests": self._metrics["successful_requests"],
            "failed_requests": self._metrics["failed_requests"],
            "fallback_requests": self._metrics["fallback_requests"],
            "cache_hits": self._metrics["cache_hits"],
            "cache_misses": self._metrics["cache_misses"],
            "cache_hit_rate_percent": round(cache_hit_rate, 2),
            "average_latency_seconds": round(avg_latency, 3),
            "provider_usage": self._metrics["provider_usage"].copy(),
            "error_counts": self._metrics["error_counts"].copy(),
            "cache_size": len(self._response_cache),
            "cache_max_size": self._cache_size,
            "batch_requests": self._metrics["batch_requests"],
            "connection_pool": pool_metrics
        }

    def _get_pool_metrics(self) -> Dict[str, Any]:
        """Get connection pool metrics from ChainMind if available."""
        pool_metrics = {
            "available": False,
            "reuses": self._metrics["connection_pool_reuses"]
        }

        if self._router and hasattr(self._router, "tactical_router"):
            try:
                tactical = self._router.tactical_router
                if hasattr(tactical, "client_pool"):
                    pool = tactical.client_pool
                    if hasattr(pool, "clients"):
                        # Count active clients
                        total_clients = 0
                        active_clients = 0
                        for provider_clients in pool.clients.values():
                            for model_clients in provider_clients.values():
                                total_clients += len(model_clients)
                                active_clients += sum(1 for c in model_clients if c.in_use)

                        pool_metrics.update({
                            "available": True,
                            "total_clients": total_clients,
                            "active_clients": active_clients,
                            "max_clients_per_provider": getattr(pool, "max_clients_per_provider", None)
                        })
            except Exception as e:
                logger.debug(f"Could not get pool metrics: {e}")

        return pool_metrics

    def _generate_cache_key(self, prompt: str, prefer_claude: bool, kwargs: Dict[str, Any]) -> str:
        """Generate cache key for request deduplication."""
        # Include prompt, provider preference, and key parameters
        key_parts = [
            prompt,
            str(prefer_claude),
            str(kwargs.get("temperature", "")),
            str(kwargs.get("max_tokens", "")),
            str(kwargs.get("model", ""))
        ]
        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()

    def _cache_result(self, cache_key: str, result: Dict[str, Any]) -> None:
        """Cache a result with LRU eviction."""
        # Remove correlation_id and from_cache from cached version
        cached_result = result.copy()
        cached_result.pop("correlation_id", None)
        cached_result.pop("from_cache", None)

        # Add to cache
        self._response_cache[cache_key] = cached_result
        self._response_cache.move_to_end(cache_key)

        # Evict oldest if cache is full
        if len(self._response_cache) > self._cache_size:
            self._response_cache.popitem(last=False)


    def _load_config(self, provided_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Load configuration from various sources."""
        config = {}

        # Try to use ChainMind's ConfigManager (preferred method)
        try:
            from backend.config.config_loader import get_config_manager
            config_manager = get_config_manager()
            chainmind_config = config_manager.get_config()

            # Extract relevant sections from ChainMind config
            if "cost_optimization" in chainmind_config:
                config["cost_optimization"] = chainmind_config["cost_optimization"]
            if "model_selection" in chainmind_config:
                config["model_selection"] = chainmind_config["model_selection"]
            if "routing" in chainmind_config:
                config["routing"] = chainmind_config["routing"]
        except Exception as e:
            logger.debug(f"Could not load ChainMind ConfigManager: {e}")

        # Load from environment variables (for engram-specific overrides)
        import os
        if os.environ.get("CHAINMIND_FALLBACK_PROVIDERS"):
            config["fallback_providers"] = os.environ["CHAINMIND_FALLBACK_PROVIDERS"].split(",")
        if os.environ.get("CHAINMIND_MAX_TOKENS"):
            config["max_tokens_per_request"] = int(os.environ["CHAINMIND_MAX_TOKENS"])
        if os.environ.get("CHAINMIND_MAX_COST"):
            config["max_cost_per_request"] = float(os.environ["CHAINMIND_MAX_COST"])
        if os.environ.get("CHAINMIND_TIMEOUT"):
            config["request_timeout_seconds"] = float(os.environ["CHAINMIND_TIMEOUT"])

        # Load from engram-mcp config file (for engram-specific settings)
        # This takes precedence over ChainMind config for engram-specific settings
        try:
            config_path = os.path.expanduser("~/.engram/config/chainmind.yaml")
            if os.path.exists(config_path):
                import yaml
                with open(config_path) as f:
                    file_config = yaml.safe_load(f) or {}
                    # Merge engram config (takes precedence for engram-specific settings)
                    config.update(file_config)
        except Exception as e:
            logger.debug(f"Could not load engram config file: {e}")

        # Override with provided config (highest precedence)
        if provided_config:
            config.update(provided_config)

        return config

    def _check_provider_health(self, provider: str) -> bool:
        """Check if provider is healthy (circuit breaker not open)."""
        # Check circuit breaker if router is available
        if self._router and hasattr(self._router, "tactical_router"):
            try:
                tactical = self._router.tactical_router
                if hasattr(tactical, "_check_circuit_breaker"):
                    return tactical._check_circuit_breaker(provider)
            except Exception as e:
                logger.debug(f"Error checking circuit breaker for {provider}: {e}")

        # Check local health tracking
        if provider in self._provider_health:
            health = self._provider_health[provider]
            if health.get("circuit_open", False):
                return False
            # Check if recent failures exceed threshold
            recent_failures = health.get("recent_failures", 0)
            if recent_failures >= 3:  # Threshold
                return False

        return True

    def _update_provider_health(self, provider: str, success: bool) -> None:
        """Update provider health tracking."""
        if provider not in self._provider_health:
            self._provider_health[provider] = {
                "successes": 0,
                "failures": 0,
                "recent_failures": 0,
                "circuit_open": False,
                "last_success": None,
                "last_failure": None
            }

        health = self._provider_health[provider]
        if success:
            health["successes"] += 1
            health["recent_failures"] = 0
            health["last_success"] = time.time()
            health["circuit_open"] = False
        else:
            health["failures"] += 1
            health["recent_failures"] += 1
            health["last_failure"] = time.time()
            if health["recent_failures"] >= 3:
                health["circuit_open"] = True
                logger.warning(f"Provider {provider} marked as unhealthy (circuit open)")

    def _validate_request_limits(self, prompt: str, kwargs: Dict[str, Any]) -> None:
        """Validate request against resource limits."""
        # Check token limit
        if self._max_tokens_per_request:
            estimated_tokens = len(prompt) // 4  # Rough estimate
            requested_tokens = kwargs.get("max_tokens", 0)
            total_estimate = estimated_tokens + requested_tokens

            if total_estimate > self._max_tokens_per_request:
                raise ValueError(
                    f"Request exceeds token limit: estimated {total_estimate} tokens "
                    f"(limit: {self._max_tokens_per_request})"
                )

        # Note: Cost validation would require provider-specific cost calculation
        # This is a placeholder for future implementation

    async def _try_provider_with_timeout(
        self,
        prompt: str,
        provider: str,
        correlation_id: Optional[str] = None,
        timeout: Optional[float] = None,
        **kwargs
    ) -> Any:
        """Try provider with timeout and health check."""
        timeout = timeout or self._request_timeout_seconds

        # Check provider health before attempting
        if not self._check_provider_health(provider):
            self._metrics["circuit_breaker_skips"] += 1
            logger.warning(f"[{correlation_id}] Skipping {provider} - circuit breaker open")
            raise RuntimeError(f"Provider {provider} is unavailable (circuit breaker open)")

        # Use asyncio timeout
        import asyncio
        try:
            result = await asyncio.wait_for(
                self._try_provider(prompt, provider, correlation_id, **kwargs),
                timeout=timeout
            )
            self._update_provider_health(provider, True)
            return result
        except asyncio.TimeoutError:
            self._update_provider_health(provider, False)
            raise RuntimeError(f"Request to {provider} timed out after {timeout}s")
        except Exception as e:
            self._update_provider_health(provider, False)
            raise

    async def generate_batch(
        self,
        prompts: List[str],
        prefer_claude: bool = True,
        fallback_providers: Optional[List[str]] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Generate responses for multiple prompts in batch.

        Args:
            prompts: List of prompts to generate from
            prefer_claude: If True, try Claude first for each prompt
            fallback_providers: List of providers to try if Claude hits limits
            **kwargs: Additional parameters (temperature, max_tokens, etc.)

        Returns:
            List of response dictionaries, one per prompt
        """
        if not prompts:
            return []

        self._metrics["batch_requests"] += 1

        # Check for duplicate prompts and group them
        prompt_groups: Dict[str, List[int]] = {}
        for i, prompt in enumerate(prompts):
            cache_key = self._generate_cache_key(prompt, prefer_claude, kwargs)
            if cache_key not in prompt_groups:
                prompt_groups[cache_key] = []
            prompt_groups[cache_key].append(i)

        # Process prompts concurrently (but respect rate limits)
        tasks = [
            self.generate(prompt, prefer_claude=prefer_claude, fallback_providers=fallback_providers, **kwargs)
            for prompt in prompts
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results and handle errors
        batch_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # Error occurred - create error response
                batch_results.append({
                    "response": "",
                    "provider": "unknown",
                    "fallback_used": False,
                    "usage_limit_hit": False,
                    "error": str(result),
                    "error_type": type(result).__name__,
                    "correlation_id": None,
                    "latency_seconds": 0.0,
                    "from_cache": False
                })
            else:
                batch_results.append(result)

        return batch_results

# Global instance (singleton)
_helper_instance = None

def get_helper() -> ChainMindHelper:
    """Get global ChainMind helper instance."""
    global _helper_instance
    if _helper_instance is None:
        _helper_instance = ChainMindHelper()
    return _helper_instance
