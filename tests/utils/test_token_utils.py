"""Tests for token counting and pagination utilities.

Test Coverage:
- Token estimation accuracy
- JSON token estimation
- Pagination with various limits and offsets
- Token-aware truncation
- Edge cases (empty lists, invalid parameters)
- Large dataset handling
"""

import json

from mcp_ticketer.utils.token_utils import (
    CHARS_PER_TOKEN,
    estimate_json_tokens,
    estimate_tokens,
    paginate_response,
)


class TestEstimateTokens:
    """Test token estimation for plain text."""

    def test_empty_string(self):
        """Empty string should return 0 tokens."""
        assert estimate_tokens("") == 0

    def test_short_string(self):
        """Short string should estimate correctly."""
        # "Hello world" = 11 chars / 4 = 2.75 → 2 tokens (integer division)
        assert estimate_tokens("Hello world") == 11 // CHARS_PER_TOKEN

    def test_exact_multiple(self):
        """String with exact multiple of CHARS_PER_TOKEN."""
        # 12 chars = exactly 3 tokens
        text = "a" * 12
        assert estimate_tokens(text) == 3

    def test_minimum_one_token(self):
        """Even 1 character should count as 1 token."""
        assert estimate_tokens("a") == max(1, 1 // CHARS_PER_TOKEN)
        assert estimate_tokens("ab") == max(1, 2 // CHARS_PER_TOKEN)

    def test_large_text(self):
        """Large text should estimate correctly."""
        # 10,000 chars = 2,500 tokens
        text = "a" * 10_000
        assert estimate_tokens(text) == 10_000 // CHARS_PER_TOKEN

    def test_unicode_text(self):
        """Unicode characters should be counted correctly."""
        # Unicode chars may be multiple bytes, but we count characters
        text = "Hello 世界 🌍"  # Mix of ASCII, Chinese, emoji
        assert estimate_tokens(text) > 0

    def test_json_structure(self):
        """JSON-formatted string should include structure overhead."""
        json_str = json.dumps({"id": "123", "title": "Test"})
        tokens = estimate_tokens(json_str)
        # JSON has extra characters for quotes, braces, colons
        assert tokens > 0


class TestEstimateJsonTokens:
    """Test token estimation for JSON data structures."""

    def test_empty_dict(self):
        """Empty dict should have minimal tokens."""
        assert estimate_json_tokens({}) > 0  # "{}" = 2 chars

    def test_simple_dict(self):
        """Simple dict should estimate correctly."""
        data = {"id": "123"}
        # JSON: {"id":"123"} = ~12 chars = ~3 tokens
        tokens = estimate_json_tokens(data)
        assert tokens > 0

    def test_nested_dict(self):
        """Nested dict should account for structure."""
        data = {
            "id": "123",
            "user": {"name": "Test", "email": "test@example.com"},
            "tags": ["bug", "urgent"],
        }
        tokens = estimate_json_tokens(data)
        # Should be more than simple dict
        assert tokens > 10

    def test_list_of_dicts(self):
        """List of dicts should sum correctly."""
        data = [
            {"id": "1", "title": "First"},
            {"id": "2", "title": "Second"},
        ]
        tokens = estimate_json_tokens(data)
        assert tokens > 5

    def test_non_serializable_with_default(self):
        """Non-serializable objects should use str() fallback."""

        class CustomObject:
            def __str__(self):
                return "custom_object"

        data = {"obj": CustomObject()}
        # Should not raise, uses default=str
        tokens = estimate_json_tokens(data)
        assert tokens > 0

    def test_large_json_array(self):
        """Large array should estimate correctly."""
        data = [{"id": f"{i}", "value": f"item_{i}"} for i in range(100)]
        tokens = estimate_json_tokens(data)
        # 100 items * ~15 chars each = ~1500 chars = ~375 tokens
        assert tokens > 300


class TestPaginateResponse:
    """Test pagination with token awareness."""

    def test_empty_list(self):
        """Empty list should return empty result."""
        result = paginate_response([])
        assert result["items"] == []
        assert result["count"] == 0
        assert result["total"] == 0
        assert result["has_more"] is False

    def test_basic_pagination(self):
        """Basic pagination without token limits."""
        items = [{"id": f"{i}", "value": i} for i in range(50)]

        # First page
        page1 = paginate_response(items, limit=10, offset=0)
        assert page1["count"] == 10
        assert page1["total"] == 50
        assert page1["offset"] == 0
        assert page1["limit"] == 10
        assert page1["has_more"] is True
        assert len(page1["items"]) == 10

        # Second page
        page2 = paginate_response(items, limit=10, offset=10)
        assert page2["count"] == 10
        assert page2["offset"] == 10
        assert page2["has_more"] is True

        # Last page
        last_page = paginate_response(items, limit=10, offset=40)
        assert last_page["count"] == 10
        assert last_page["has_more"] is False

    def test_offset_beyond_total(self):
        """Offset beyond total should return empty result."""
        items = [{"id": f"{i}"} for i in range(10)]
        result = paginate_response(items, limit=10, offset=20)

        assert result["count"] == 0
        assert result["total"] == 10
        assert result["has_more"] is False

    def test_limit_larger_than_items(self):
        """Limit larger than total items should return all items."""
        items = [{"id": f"{i}"} for i in range(5)]
        result = paginate_response(items, limit=10, offset=0)

        assert result["count"] == 5
        assert result["total"] == 5
        assert result["has_more"] is False

    def test_token_truncation(self):
        """Response should truncate when token limit is reached."""
        # Create items with large descriptions to trigger token limit
        items = [
            {"id": f"{i}", "description": "x" * 1000} for i in range(100)
        ]  # Each ~250 tokens

        # Request 100 items but set low token limit
        result = paginate_response(items, limit=100, offset=0, max_tokens=5000)

        # Should return fewer items due to token limit
        assert result["count"] < 100
        assert result["truncated_by_tokens"] is True
        assert result["estimated_tokens"] <= 5000

    def test_compact_mode(self):
        """Compact mode should reduce token usage."""

        def compact_fn(item):
            return {"id": item["id"]}  # Only keep ID

        items = [
            {
                "id": f"{i}",
                "title": "Long title " * 10,
                "description": "Long desc " * 20,
            }
            for i in range(20)
        ]

        # Without compact mode
        full = paginate_response(items, limit=20, compact=False)
        full_tokens = full["estimated_tokens"]

        # With compact mode
        compact = paginate_response(
            items, limit=20, compact=True, compact_fn=compact_fn
        )
        compact_tokens = compact["estimated_tokens"]

        # Compact should use significantly fewer tokens
        assert compact_tokens < full_tokens
        # Each compact item should only have 'id' field
        assert list(compact["items"][0].keys()) == ["id"]

    def test_serialize_fn(self):
        """Custom serialize function should be used."""

        class MockTicket:
            def __init__(self, id, title):
                self.id = id
                self.title = title

        def serialize(ticket):
            return {"id": ticket.id, "title": ticket.title}

        tickets = [MockTicket(f"{i}", f"Ticket {i}") for i in range(10)]

        result = paginate_response(tickets, serialize_fn=serialize)

        assert result["count"] == 10
        assert result["items"][0]["id"] == "0"
        assert result["items"][0]["title"] == "Ticket 0"

    def test_model_dump_fallback(self):
        """Should use model_dump() if no serialize_fn provided."""

        class MockModel:
            def __init__(self, id):
                self.id = id

            def model_dump(self):
                return {"id": self.id}

        models = [MockModel(i) for i in range(5)]
        result = paginate_response(models)

        assert result["count"] == 5
        assert result["items"][0] == {"id": 0}

    def test_invalid_limit(self):
        """Invalid limit should use default."""
        items = [{"id": f"{i}"} for i in range(50)]

        # Negative limit
        result = paginate_response(items, limit=-10)
        assert result["limit"] == 20  # Should use default

        # Zero limit
        result = paginate_response(items, limit=0)
        assert result["limit"] == 20  # Should use default

    def test_invalid_offset(self):
        """Invalid offset should use 0."""
        items = [{"id": f"{i}"} for i in range(10)]
        result = paginate_response(items, limit=5, offset=-5)

        assert result["offset"] == 0

    def test_serialization_error_handling(self):
        """Should skip items that fail serialization."""

        class FailingObject:
            def model_dump(self):
                raise ValueError("Serialization failed")

        items = [
            {"id": "1"},  # Good
            FailingObject(),  # Bad
            {"id": "3"},  # Good
        ]

        result = paginate_response(items)

        # Should skip the failing object
        assert result["count"] == 2  # Only 2 successful items

    def test_no_overlap_between_pages(self):
        """Sequential pages should not overlap."""
        items = [{"id": f"{i}", "value": i} for i in range(30)]

        page1 = paginate_response(items, limit=10, offset=0)
        page2 = paginate_response(items, limit=10, offset=10)
        page3 = paginate_response(items, limit=10, offset=20)

        # Extract IDs from each page
        ids1 = {item["id"] for item in page1["items"]}
        ids2 = {item["id"] for item in page2["items"]}
        ids3 = {item["id"] for item in page3["items"]}

        # No overlaps
        assert len(ids1 & ids2) == 0
        assert len(ids2 & ids3) == 0
        assert len(ids1 & ids3) == 0

        # All IDs accounted for
        all_ids = ids1 | ids2 | ids3
        assert len(all_ids) == 30

    def test_estimated_tokens_accuracy(self):
        """Estimated tokens should be reasonably accurate."""
        items = [{"id": f"{i}", "title": f"Ticket {i}"} for i in range(10)]

        result = paginate_response(items, limit=10)

        # Manually calculate expected tokens
        json_str = json.dumps(result["items"])
        expected_tokens = len(json_str) // CHARS_PER_TOKEN

        # Should be within reasonable bounds (accounting for BASE_RESPONSE_OVERHEAD)
        # The estimate includes overhead while manual calc doesn't
        assert result["estimated_tokens"] >= expected_tokens
        # Overhead should not be more than double the content
        assert result["estimated_tokens"] < expected_tokens * 2.5


class TestTokenAwarenessBehavior:
    """Test token-aware behavior under various conditions."""

    def test_warning_threshold(self):
        """Should warn when approaching 80% of token limit."""
        # Create items that will use ~16k tokens (80% of 20k)
        items = [{"id": f"{i}", "data": "x" * 800} for i in range(80)]

        result = paginate_response(items, limit=80, max_tokens=20_000)

        # Should return most items but be near limit
        assert result["estimated_tokens"] > 16_000
        assert result["estimated_tokens"] <= 20_000

    def test_large_dataset_handling(self):
        """Should handle large datasets efficiently."""
        # Create 1000 items
        items = [{"id": f"{i}", "value": i} for i in range(1000)]

        # Request first page
        result = paginate_response(items, limit=20, offset=0)

        assert result["count"] == 20
        assert result["total"] == 1000
        assert result["has_more"] is True
        # Should process quickly without loading all items

    def test_token_limit_enforcement(self):
        """Should strictly enforce token limit."""
        # Create items with varying sizes
        items = [{"id": f"{i}", "data": "x" * (i * 100)} for i in range(1, 100)]

        result = paginate_response(items, limit=100, max_tokens=5000)

        # Must not exceed limit
        assert result["estimated_tokens"] <= 5000
        # Should have truncated
        assert result["truncated_by_tokens"] is True
        assert result["count"] < 100
