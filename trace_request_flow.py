#!/usr/bin/env python3
"""
Comprehensive Request Flow Tracer

Traces a prompt through the entire ChainMind + engram-mcp integration,
logging all data transformations, inputs, and outputs at each stage.
"""

import os
import sys
import json
import asyncio
import logging
from typing import Dict, Any
from datetime import datetime

# Setup detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Add paths
CHAINMIND_PATH = "/mnt/dev/ai/ai-platform/chainmind"
ENGRAM_PATH = "/mnt/dev/ai/engram-mcp"

if CHAINMIND_PATH not in sys.path:
    sys.path.insert(0, CHAINMIND_PATH)
if ENGRAM_PATH not in sys.path:
    sys.path.insert(0, ENGRAM_PATH)

# Import after path setup
from engram.chainmind_helper import ChainMindHelper


class RequestTracer:
    """Traces request flow through the entire system."""

    def __init__(self):
        self.trace_log = []
        self.step_counter = 0

    def log_step(self, stage: str, step: str, data: Dict[str, Any], description: str = ""):
        """Log a step in the trace."""
        self.step_counter += 1
        entry = {
            "step": self.step_counter,
            "stage": stage,
            "step_name": step,
            "timestamp": datetime.now().isoformat(),
            "description": description,
            "data": self._sanitize_data(data)
        }
        self.trace_log.append(entry)

        # Print formatted output
        print(f"\n{'='*80}")
        print(f"STEP {self.step_counter}: {stage} - {step}")
        print(f"{'='*80}")
        if description:
            print(f"Description: {description}")
        print(f"\nData:")
        print(json.dumps(entry["data"], indent=2, default=str))
        print(f"{'='*80}\n")

    def _sanitize_data(self, data: Any) -> Any:
        """Sanitize data for JSON serialization."""
        if isinstance(data, dict):
            return {k: self._sanitize_data(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._sanitize_data(item) for item in data]
        elif isinstance(data, (str, int, float, bool, type(None))):
            return data
        elif hasattr(data, '__dict__'):
            return str(data)
        else:
            return str(data)

    def save_trace(self, filename: str = None):
        """Save trace log to file."""
        if filename is None:
            filename = f"trace_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        output_path = os.path.join(ENGRAM_PATH, filename)
        with open(output_path, 'w') as f:
            json.dump(self.trace_log, f, indent=2, default=str)

        print(f"\n✓ Trace saved to: {output_path}")
        return output_path


async def trace_request_flow(prompt: str, agent_role: str = "software_engineer", agent_id: str = "test_session_123"):
    """Trace a request through the entire system."""

    tracer = RequestTracer()

    # ========================================================================
    # STAGE 1: Initial Request
    # ========================================================================
    tracer.log_step(
        "INITIAL_REQUEST",
        "User Input",
        {
            "prompt": prompt,
            "agent_role": agent_role,
            "agent_id": agent_id,
            "parameters": {
                "auto_select_model": True,
                "prefer_claude": False,
                "temperature": 0.7,
                "max_tokens": 1024
            }
        },
        "Initial request from Claude Code with role and agent_id"
    )

    # ========================================================================
    # STAGE 2: ChainMindHelper Entry
    # ========================================================================
    helper = ChainMindHelper()

    tracer.log_step(
        "CHAINMIND_HELPER",
        "Initialization",
        {
            "helper_initialized": helper._initialized,
            "router_available": helper.is_available(),
            "config": {
                "auto_select_enabled": helper._auto_select_enabled,
                "default_strategy": helper._default_strategy,
                "fallback_providers": helper._fallback_providers
            }
        },
        "ChainMindHelper initialized, checking availability"
    )

    # Initialize router if needed
    if not helper._initialized:
        helper._init_chainmind()
        tracer.log_step(
            "CHAINMIND_HELPER",
            "Router Initialization",
            {
                "router_initialized": helper._router is not None,
                "init_attempts": helper._init_attempts,
                "last_init_error": helper._last_init_error
            },
            "ChainMind router initialization attempt"
        )

    # ========================================================================
    # STAGE 3: Smart Routing Path
    # ========================================================================
    # We'll trace through _generate_with_smart_routing

    # Build request dict (simulating what happens internally)
    request_dict = {
        "prompt": prompt,
        "provider": "openai",
        "agent_role": agent_role,
        "agent_id": agent_id,
        "context": {
            "agent_role": agent_role,
            "agent_id": agent_id
        },
        "budget_constraints": {
            "prefer_lower_cost": True,
            "enforce_budget": False,
            "max_cost": None
        },
        "prefer_local": False,
        "temperature": 0.7,
        "max_tokens": 1024
    }

    tracer.log_step(
        "CHAINMIND_HELPER",
        "Request Dict Construction",
        request_dict,
        "Request dictionary built for StrategicRouter"
    )

    # ========================================================================
    # STAGE 4: StrategicRouter - Request Analysis
    # ========================================================================
    if helper._router and hasattr(helper._router, 'strategic_router'):
        strategic_router = helper._router.strategic_router

        # Trace the analysis step
        tracer.log_step(
            "STRATEGIC_ROUTER",
            "Before Analysis",
            {
                "request_keys": list(request_dict.keys()),
                "prompt_length": len(prompt),
                "has_agent_role": "agent_role" in request_dict,
                "has_agent_id": "agent_id" in request_dict
            },
            "Request received by StrategicRouter, ready for analysis"
        )

        # Manually trace InputAnalyzer if accessible
        if hasattr(strategic_router, 'input_analyzer'):
            input_analyzer = strategic_router.input_analyzer

            # Trace InputAnalyzer.analyze()
            tracer.log_step(
                "INPUT_ANALYZER",
                "Input Analysis Start",
                {
                    "prompt": prompt,
                    "context": request_dict.get("context", {}),
                    "agent_id": agent_id,
                    "agent_role": agent_role
                },
                "InputAnalyzer.analyze() called with prompt and context"
            )

            # Analyze prompt structure
            structure_info = input_analyzer._analyze_prompt_structure(prompt)
            tracer.log_step(
                "INPUT_ANALYZER",
                "Prompt Structure Analysis",
                structure_info,
                "Structure analysis: code blocks, imports, file paths, etc."
            )

            # Detect domain
            domain = input_analyzer._detect_domain(prompt.lower(), agent_role=agent_role)
            tracer.log_step(
                "INPUT_ANALYZER",
                "Domain Detection",
                {
                    "detected_domain": domain,
                    "agent_role": agent_role,
                    "role_domain_mapping": agent_role in input_analyzer.role_domain_mapping,
                    "mapped_domain": input_analyzer.role_domain_mapping.get(agent_role) if agent_role in input_analyzer.role_domain_mapping else None
                },
                "Domain detection with role-based boosting"
            )

            # Detect task type with confidence
            task_type_result = input_analyzer._detect_task_type_with_confidence(
                prompt.lower(),
                structure_info,
                agent_id=agent_id,
                agent_role=agent_role
            )
            tracer.log_step(
                "INPUT_ANALYZER",
                "Task Type Detection",
                task_type_result,
                "Task type detection with confidence scoring and role boosting"
            )

            # Get context boost
            context_boost = input_analyzer._get_context_boost(agent_id=agent_id)
            agent_history = input_analyzer._get_agent_history(agent_id)
            tracer.log_step(
                "INPUT_ANALYZER",
                "Context-Aware Boosting",
                {
                    "context_boost": context_boost,
                    "agent_id": agent_id,
                    "history_size": len(agent_history) if agent_history else 0,
                    "history_entries": [
                        {
                            "task_type": entry.get("task_type"),
                            "domain": entry.get("domain"),
                            "age_seconds": round(datetime.now().timestamp() - entry.get("timestamp", 0), 2) if entry.get("timestamp") else None
                        }
                        for entry in list(agent_history)[-5:]  # Last 5 entries
                    ] if agent_history else []
                },
                "Context-aware boosting from agent-specific history"
            )

            # Full analysis
            analysis_result = input_analyzer.analyze(prompt, context=request_dict.get("context", {}))
            tracer.log_step(
                "INPUT_ANALYZER",
                "Complete Analysis Result",
                analysis_result,
                "Final analysis result with all classifications"
            )

            # Update request with analysis
            request_dict["analysis"] = analysis_result
            request_dict["task_type"] = analysis_result.get("task_type")
            request_dict["complexity"] = analysis_result.get("complexity")
            request_dict["domain"] = analysis_result.get("domain")
            request_dict["required_capabilities"] = analysis_result.get("capabilities", [])

    # ========================================================================
    # STAGE 5: StrategicRouter - Strategy Selection
    # ========================================================================
    if helper._router and hasattr(helper._router, 'strategic_router'):
        strategic_router = helper._router.strategic_router

        # Ensure router is initialized
        if not hasattr(strategic_router, 'routing_strategies'):
            # Router may not be fully initialized, try to access it safely
            try:
                if hasattr(strategic_router, '_load_routing_strategies'):
                    strategic_router.routing_strategies = strategic_router._load_routing_strategies()
            except Exception as e:
                tracer.log_step(
                    "STRATEGIC_ROUTER",
                    "Strategy Selection Failed",
                    {
                        "error": str(e),
                        "note": "Router may need full initialization"
                    },
                    "Could not select strategy (router initialization issue)"
                )
                strategic_router = None

        if strategic_router and hasattr(strategic_router, 'routing_strategies'):
            try:
                strategy = strategic_router._select_routing_strategy(request_dict)
                tracer.log_step(
                    "STRATEGIC_ROUTER",
                    "Strategy Selection",
                    {
                        "selected_strategy": strategy,
                        "task_type": request_dict.get("task_type"),
                        "complexity": request_dict.get("complexity")
                    },
                    "Routing strategy selected based on task type"
                )
            except Exception as e:
                tracer.log_step(
                    "STRATEGIC_ROUTER",
                    "Strategy Selection Error",
                    {
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "task_type": request_dict.get("task_type")
                    },
                    "Error during strategy selection"
                )

    # ========================================================================
    # STAGE 6: Model Selection (if we can access ModelRegistry)
    # ========================================================================
    if helper._router and hasattr(helper._router, 'strategic_router'):
        strategic_router = helper._router.strategic_router
        try:
            # Try to get hardware info safely
            hardware_info = None
            if hasattr(strategic_router, 'default_hardware_info'):
                hardware_info = strategic_router.default_hardware_info
            elif hasattr(strategic_router, '_detect_hardware_info'):
                hardware_info = strategic_router._detect_hardware_info()

            if hasattr(strategic_router, 'model_registry') and hardware_info:
                model_registry = strategic_router.model_registry
                task_description = f"[Role: {agent_role}] {prompt[:200]}"

                tracer.log_step(
                    "MODEL_REGISTRY",
                    "Model Selection Input",
                    {
                        "task_description": task_description,
                        "hardware_info": hardware_info,
                        "task_type": request_dict.get("task_type"),
                        "required_capabilities": request_dict.get("required_capabilities", []),
                        "agent_role": agent_role
                    },
                    "Model selection parameters including role in task description"
                )
        except Exception as e:
            tracer.log_step(
                "MODEL_REGISTRY",
                "Model Selection Info Unavailable",
                {
                    "error": str(e),
                    "note": "Model registry or hardware info not accessible"
                },
                "Could not access model selection information"
            )

    # ========================================================================
    # STAGE 7: Actual Request Execution (if API keys available)
    # ========================================================================
    # Check if we should attempt actual execution
    attempt_execution = os.environ.get("TRACE_EXECUTE", "false").lower() == "true"

    if attempt_execution:
        try:
            tracer.log_step(
                "EXECUTION",
                "Starting Request Execution",
                {
                    "will_call_api": True,
                    "note": "Making actual API calls"
                },
                "About to execute actual request through ChainMind"
            )

            result = await helper.generate(
                prompt=prompt,
                agent_role=agent_role,
                agent_id=agent_id,
                auto_select_model=True,
                prefer_claude=False,
                temperature=0.7,
                max_tokens=1024
            )

            tracer.log_step(
                "EXECUTION",
                "Request Complete",
                {
                    "response_length": len(result.get("response", "")),
                    "provider": result.get("provider"),
                    "model": result.get("model"),
                    "fallback_used": result.get("fallback_used", False),
                    "usage_limit_hit": result.get("usage_limit_hit", False),
                    "model_selection": result.get("model_selection"),
                    "latency_seconds": result.get("latency_seconds"),
                    "response_preview": result.get("response", "")[:200] + "..." if len(result.get("response", "")) > 200 else result.get("response", "")
                },
                "Request completed successfully"
            )

        except Exception as e:
            tracer.log_step(
                "EXECUTION",
                "Request Failed",
                {
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "traceback": str(e.__traceback__) if hasattr(e, '__traceback__') else None
                },
                "Request execution failed"
            )
    else:
        tracer.log_step(
            "EXECUTION",
            "Execution Skipped",
            {
                "will_call_api": False,
                "note": "Set TRACE_EXECUTE=true environment variable to enable actual API calls",
                "reason": "Skipping to avoid API costs and focus on tracing data transformations"
            },
            "Skipping actual API execution (set TRACE_EXECUTE=true to enable)"
        )

    # ========================================================================
    # STAGE 8: Final Summary
    # ========================================================================
    tracer.log_step(
        "SUMMARY",
        "Trace Complete",
        {
            "total_steps": len(tracer.trace_log),
            "stages_covered": list(set(entry["stage"] for entry in tracer.trace_log)),
            "prompt": prompt,
            "agent_role": agent_role,
            "agent_id": agent_id
        },
        "Complete trace of request flow"
    )

    # Save trace
    trace_file = tracer.save_trace()

    return tracer.trace_log, trace_file


async def main():
    """Main entry point."""
    print("="*80)
    print("REQUEST FLOW TRACER")
    print("="*80)
    print("\nThis script traces a prompt through the entire ChainMind + engram-mcp")
    print("integration, logging all data transformations at each stage.\n")

    # Test prompts
    test_prompts = [
        {
            "prompt": "how do i fix this python function?",
            "agent_role": "software_engineer",
            "agent_id": "software_engineer:session_123",
            "description": "Coding task with software_engineer role"
        },
        {
            "prompt": "how do i grow my youtube channel?",
            "agent_role": "youtube_content_creator",
            "agent_id": "youtube_content_creator:session_456",
            "description": "YouTube growth question with youtube_content_creator role"
        }
    ]

    # Use first prompt for detailed trace
    test_case = test_prompts[0]

    print(f"\nTest Case: {test_case['description']}")
    print(f"Prompt: {test_case['prompt']}")
    print(f"Agent Role: {test_case['agent_role']}")
    print(f"Agent ID: {test_case['agent_id']}")
    print("\n" + "="*80 + "\n")

    trace_log, trace_file = await trace_request_flow(
        prompt=test_case["prompt"],
        agent_role=test_case["agent_role"],
        agent_id=test_case["agent_id"]
    )

    print("\n" + "="*80)
    print("TRACE COMPLETE")
    print("="*80)
    print(f"\n✓ Traced {len(trace_log)} steps")
    print(f"✓ Trace saved to: {trace_file}")
    print(f"\nTo view the full trace:")
    print(f"  cat {trace_file} | jq '.'")
    print(f"\nTo view a specific step:")
    print(f"  cat {trace_file} | jq '.[0]'  # First step")
    print(f"  cat {trace_file} | jq '.[] | select(.stage == \"INPUT_ANALYZER\")'  # All InputAnalyzer steps")


if __name__ == "__main__":
    asyncio.run(main())
