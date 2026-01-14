"""
Demo Tests - YouTube-Ready Demonstrations

Each test here demonstrates a key feature of Engram.
Run these with verbose output for screen recording:

    pytest tests/test_demos.py -v

Each test tells a story that could be a video segment.
"""


class TestTheProblem:
    """
    VIDEO: "The Problem Every Claude User Has"

    These tests demonstrate the pain points Engram solves.
    Good for the "before" part of before/after videos.
    """

    def test_claude_forgets_between_sessions(self):
        """DEMO: Claude has no memory between sessions.

        This is the fundamental problem.
        Session 1: You explain everything
        Session 2: Claude knows nothing

        Video script:
        "Watch - I tell Claude my preferences in session 1,
        then in session 2... it's like we never talked."
        """
        # Session 1: User shares context
        session1_context = {
            "preference": "I prefer TypeScript over JavaScript",
            "project": "Working on engram-mcp",
            "past_solution": "Fixed GPU issue with cu128",
        }

        # Session 2: New Claude instance
        session2_memory = {}  # Empty! Claude starts fresh.

        # The problem: everything is lost
        assert session2_memory == {}, "Without Engram, Claude forgets everything"

        # User must re-explain ALL of this
        assert "preference" not in session2_memory
        assert "project" not in session2_memory
        assert "past_solution" not in session2_memory

    def test_count_repeated_explanations(self):
        """DEMO: How much time is wasted re-explaining?

        Video script:
        "Let's count how many times per week you re-explain
        the same things to Claude..."
        """
        # Common things users re-explain
        repeated_topics = [
            "What GPU/hardware do I have?",
            "What's the project structure?",
            "Which virtual environment to use?",
            "What was that fix we used last time?",
            "What are my coding preferences?",
        ]

        sessions_per_week = 20  # Typical heavy user
        explanations_per_topic = sessions_per_week  # Once per session

        total_wasted_explanations = len(repeated_topics) * explanations_per_topic

        # That's 100 repeated explanations per week!
        assert total_wasted_explanations == 100

        # With Engram: 0 (it remembers)


class TestTheSolution:
    """
    VIDEO: "Give Claude a Memory - Finally!"

    These tests demonstrate Engram working.
    Good for the "after" part of before/after videos.
    """

    def test_memories_persist(self, memory_store):
        """DEMO: Memories survive across sessions.

        Video script:
        "Now watch - I store a preference, and even after
        restarting, Engram remembers."
        """
        # Store a preference
        memory_id = memory_store.remember(
            content="User prefers TypeScript over JavaScript for new projects",
            memory_type="preference",
            importance=0.8
        )

        # Verify it's stored
        assert memory_id is not None
        assert memory_id.startswith("mem_")

        # Search for it (simulating new session)
        results = memory_store.recall("TypeScript preferences")

        # It's there!
        assert len(results) > 0
        assert "TypeScript" in results[0]["content"]

        # This is the magic moment - it remembers!

    def test_semantic_search_not_keywords(self, memory_store):
        """DEMO: Find by meaning, not exact words.

        Video script:
        "Watch this - I search with completely different words,
        and it STILL finds what I'm looking for."
        """
        # Store a memory with specific wording
        memory_store.remember(
            content="README-driven development: write comprehensive docs first, then build to match",
            memory_type="philosophy",
            importance=0.9
        )

        # Search with COMPLETELY DIFFERENT words
        results = memory_store.recall("documentation before coding approach")

        # It finds it anyway! (semantic similarity)
        assert len(results) > 0
        assert "README" in results[0]["content"]

        # This is NOT keyword matching - it understands MEANING

    def test_importance_affects_results(self, memory_store):
        """DEMO: Important memories rank higher.

        Video script:
        "You can mark memories as important, and they'll
        surface first when relevant."
        """
        # Store a less important memory
        memory_store.remember(
            content="Minor style preference: use single quotes",
            memory_type="preference",
            importance=0.3
        )

        # Store a more important memory
        memory_store.remember(
            content="Critical: always validate user input to prevent injection",
            memory_type="fact",
            importance=0.95
        )

        # Search for both
        results = memory_store.recall("coding practices")

        # Important one should rank higher
        assert len(results) >= 2
        # The critical security one should come first
        assert results[0]["importance"] > results[1]["importance"]


class TestSmartContext:
    """
    VIDEO: "AI That Knows What Project You're In"

    These tests demonstrate project awareness.
    """

    def test_project_detection(self, memory_store):
        """DEMO: Engram detects your project automatically.

        Video script:
        "Engram knows what project you're working on
        just from your current directory."
        """
        # Test the project detection
        test_cases = [
            ("/mnt/dev/ai/engram-mcp/src/main.py", "engram-mcp"),
            ("/mnt/dev/ai/hallo2/lib/utils.py", "hallo2"),
            ("/home/eric/projects/myapp/index.ts", "myapp"),
            ("/home/eric/random/file.txt", None),  # No project
        ]

        for path, expected in test_cases:
            detected = memory_store._detect_project(path)
            assert detected == expected, f"Path {path} should detect as {expected}"

    def test_layer_filtering_works(self, populated_store):
        """DEMO: Right memories for the right context.

        Video script:
        "Watch - when I'm in the Engram project, I get Engram memories.
        But universal principles show up everywhere."
        """
        # Simulate being in Engram project
        engram_context = populated_store.context(
            query="development approach",
            cwd="/mnt/dev/ai/engram-mcp/src"
        )

        # Should get Layer 1 (universal) AND Layer 3 (engram-specific)
        contents = [m["content"] for m in engram_context]

        # Universal principles should appear
        has_universal = any("README-driven" in c or "MVP" in c for c in contents)

        # Engram-specific should also appear (we're in that project!)
        has_project = any("Engram" in c for c in contents)

        assert has_universal, "Should get universal principles"
        assert has_project, "Should get project-specific memories when in project"

    def test_wrong_project_filtered_out(self, populated_store):
        """DEMO: Engram doesn't spam you with irrelevant memories.

        Video script:
        "Importantly, when I'm in a DIFFERENT project,
        I don't get Engram-specific memories cluttering things up."
        """
        # Simulate being in a DIFFERENT project (hallo2)
        hallo2_context = populated_store.context(
            query="how to approach this project",
            cwd="/mnt/dev/ai/hallo2/src"
        )

        contents = [m["content"] for m in hallo2_context]

        # Should get universal principles (Layer 1)
        has_universal = any("README-driven" in c or "MVP" in c for c in contents)

        # Should NOT get Engram-specific decisions (Layer 3)
        has_engram_specific = any("Engram MVP scope" in c or "Engram architecture" in c for c in contents)

        assert has_universal, "Universal principles should still appear"
        assert not has_engram_specific, "Engram-specific memories should be filtered out!"


class TestDecisionArchaeology:
    """
    VIDEO: "Never Forget WHY You Made That Decision"

    These tests demonstrate decision tracking.
    """

    def test_decisions_include_reasoning(self, populated_store):
        """DEMO: Get the WHY, not just the WHAT.

        Video script:
        "6 months later, you'll forget WHY you chose SQLite.
        But Engram remembers the reasoning."
        """
        # Search for architecture decisions
        results = populated_store.recall(
            query="database choice",
            memory_types=["decision"]
        )

        assert len(results) > 0

        decision = results[0]["content"]

        # Should have the choice AND the reasoning
        assert "SQLite" in decision
        # The reasoning: avoiding heavy dependencies
        assert "heavy" in decision.lower() or "neo4j" in decision.lower() or "redis" in decision.lower()

    def test_find_past_solutions(self, memory_store):
        """DEMO: Find solutions to problems you've solved before.

        Video script:
        "Remember that weird bug you fixed 3 months ago?
        Engram does."
        """
        # Store a solution
        memory_store.remember(
            content="Fixed CUDA out of memory by setting PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512",
            memory_type="solution",
            importance=0.8
        )

        # Later... you hit the same problem
        results = memory_store.recall("GPU memory error PyTorch")

        assert len(results) > 0
        assert "CUDA" in results[0]["content"]
        assert "max_split_size" in results[0]["content"]

        # You don't have to solve it again!


class TestRealWorldScenarios:
    """
    VIDEO: "A Day in the Life with Engram"

    These tests show realistic usage patterns.
    """

    def test_morning_context_check(self, populated_store):
        """DEMO: Start your day by asking what you should know.

        Video script:
        "Every morning, I just ask Engram what's relevant
        for today's work."
        """
        # Morning routine: get context for current project
        context = populated_store.context(
            query="what should I remember for today's work",
            cwd="/mnt/dev/ai/engram-mcp",
            limit=5
        )

        # Should get useful memories
        assert len(context) > 0

        # Mix of philosophy, patterns, and project-specific
        types = set(m["memory_type"] for m in context)
        assert len(types) >= 2, "Should get diverse memory types"

    def test_quick_preference_lookup(self, memory_store):
        """DEMO: Instant preference lookup.

        Video script:
        "What was my preference for X again?
        Just ask Engram."
        """
        # Store some preferences
        memory_store.remember("Prefer tabs over spaces", memory_type="preference")
        memory_store.remember("Prefer dark mode in all editors", memory_type="preference")
        memory_store.remember("Prefer TypeScript strict mode enabled", memory_type="preference")

        # Quick lookup
        results = memory_store.recall(
            query="editor settings preferences",
            memory_types=["preference"]
        )

        assert len(results) >= 1
        # Should find the relevant preference
        assert any("dark mode" in r["content"].lower() for r in results)

    def test_stats_for_peace_of_mind(self, populated_store):
        """DEMO: See your memory health at a glance.

        Video script:
        "Want to know how much Engram knows?
        Just check the stats."
        """
        stats = populated_store.get_stats()

        # Should have counts
        assert stats["total_memories"] > 0
        assert "by_type" in stats
        assert "by_project" in stats

        # Our founding memories should be there
        assert stats["total_memories"] >= 11  # 4 + 4 + 3 = 11 founding memories
