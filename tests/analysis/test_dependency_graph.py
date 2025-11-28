"""Tests for dependency graph analysis."""

from mcp_ticketer.analysis.dependency_graph import DependencyGraph, DependencyNode
from mcp_ticketer.core.models import Task, TicketState


def test_dependency_node_creation():
    """Test DependencyNode model creation."""
    node = DependencyNode(
        ticket_id="TEST-123",
        blocks=["TEST-124", "TEST-125"],
        blocked_by=["TEST-100"],
        depth=2,
    )

    assert node.ticket_id == "TEST-123"
    assert len(node.blocks) == 2
    assert len(node.blocked_by) == 1
    assert node.depth == 2


def test_dependency_graph_initialization():
    """Test DependencyGraph initialization."""
    graph = DependencyGraph()

    assert len(graph.nodes) == 0
    assert len(graph.edges) == 0
    assert len(graph.reverse_edges) == 0


def test_extract_dependencies_blocks_pattern():
    """Test extraction of 'blocks' pattern from ticket description."""
    graph = DependencyGraph()

    ticket = Task(
        id="1M-100",
        title="Test ticket",
        description="This blocks 1M-101 and blocks 1M-102",
        state=TicketState.OPEN,
    )

    graph.add_ticket(ticket)
    graph.finalize()

    assert "1M-100" in graph.nodes
    assert len(graph.edges["1M-100"]) == 2
    assert "1M-101" in graph.edges["1M-100"]
    assert "1M-102" in graph.edges["1M-100"]


def test_extract_dependencies_blocked_by_pattern():
    """Test extraction of 'blocked by' pattern."""
    graph = DependencyGraph()

    ticket = Task(
        id="1M-200",
        title="Test ticket",
        description="This is blocked by 1M-199",
        state=TicketState.OPEN,
    )

    graph.add_ticket(ticket)
    graph.finalize()

    assert "1M-200" in graph.nodes
    assert "1M-200" in graph.reverse_edges
    assert "1M-199" in graph.reverse_edges["1M-200"]


def test_extract_dependencies_depends_on_pattern():
    """Test extraction of 'depends on' pattern."""
    graph = DependencyGraph()

    ticket = Task(
        id="1M-300",
        title="Test ticket",
        description="Depends on 1M-299 for data",
        state=TicketState.OPEN,
    )

    graph.add_ticket(ticket)
    graph.finalize()

    assert "1M-300" in graph.nodes
    assert "1M-300" in graph.reverse_edges
    assert "1M-299" in graph.reverse_edges["1M-300"]


def test_extract_dependencies_related_pattern():
    """Test extraction of 'related to' pattern."""
    graph = DependencyGraph()

    ticket = Task(
        id="1M-400",
        title="Test ticket",
        description="Related to 1M-401 and 1M-402",
        state=TicketState.OPEN,
    )

    graph.add_ticket(ticket)
    # Related doesn't create edges, just identifies relationships
    assert "1M-400" in graph.nodes


def test_extract_dependencies_inline_reference():
    """Test extraction of inline ticket references like '1M-500:'."""
    graph = DependencyGraph()

    ticket = Task(
        id="1M-500",
        title="Test ticket",
        description="See 1M-501: Feature implementation for details",
        state=TicketState.OPEN,
    )

    graph.add_ticket(ticket)
    assert "1M-500" in graph.nodes


def test_extract_dependencies_number_format():
    """Test extraction with just numbers (infers prefix from current ticket)."""
    graph = DependencyGraph()

    ticket = Task(
        id="1M-600",
        title="Test ticket",
        description="Blocks #601 and depends on #599",
        state=TicketState.OPEN,
    )

    graph.add_ticket(ticket)
    graph.finalize()

    assert "1M-600" in graph.nodes
    # Should infer "1M-" prefix
    assert "1M-601" in graph.edges["1M-600"]
    assert "1M-599" in graph.reverse_edges["1M-600"]


def test_avoid_self_references():
    """Test that self-references are not added to the graph."""
    graph = DependencyGraph()

    ticket = Task(
        id="1M-700",
        title="Test ticket",
        description="Blocks 1M-700",  # Self-reference
        state=TicketState.OPEN,
    )

    graph.add_ticket(ticket)
    graph.finalize()

    assert "1M-700" in graph.nodes
    assert len(graph.edges.get("1M-700", set())) == 0


def test_calculate_depths_simple_chain():
    """Test depth calculation for a simple dependency chain."""
    graph = DependencyGraph()

    # Create chain: A blocks B blocks C
    ticket_a = Task(
        id="1M-800",
        title="A blocks B",
        description="Blocks 1M-801",
        state=TicketState.OPEN,
    )
    ticket_b = Task(
        id="1M-801",
        title="B blocks C",
        description="Blocks 1M-802",
        state=TicketState.OPEN,
    )
    ticket_c = Task(
        id="1M-802", title="C", description="Final task", state=TicketState.OPEN
    )

    graph.add_ticket(ticket_a)
    graph.add_ticket(ticket_b)
    graph.add_ticket(ticket_c)
    graph.finalize()

    # Depths: C=0, B=1, A=2
    assert graph.nodes["1M-802"].depth == 0
    assert graph.nodes["1M-801"].depth == 1
    assert graph.nodes["1M-800"].depth == 2


def test_calculate_depths_diamond_pattern():
    """Test depth calculation for diamond dependency pattern."""
    graph = DependencyGraph()

    # Diamond: A blocks B and C, both block D
    ticket_a = Task(
        id="1M-900",
        title="A",
        description="Blocks 1M-901 and 1M-902",
        state=TicketState.OPEN,
    )
    ticket_b = Task(
        id="1M-901", title="B", description="Blocks 1M-903", state=TicketState.OPEN
    )
    ticket_c = Task(
        id="1M-902", title="C", description="Blocks 1M-903", state=TicketState.OPEN
    )
    ticket_d = Task(id="1M-903", title="D", description="Final", state=TicketState.OPEN)

    graph.add_ticket(ticket_a)
    graph.add_ticket(ticket_b)
    graph.add_ticket(ticket_c)
    graph.add_ticket(ticket_d)
    graph.finalize()

    # Depths: D=0, B=1, C=1, A=2
    assert graph.nodes["1M-903"].depth == 0
    assert graph.nodes["1M-901"].depth == 1
    assert graph.nodes["1M-902"].depth == 1
    assert graph.nodes["1M-900"].depth == 2


def test_get_critical_path_simple_chain():
    """Test critical path for simple chain."""
    graph = DependencyGraph()

    ticket_a = Task(
        id="1M-1000", title="A", description="Blocks 1M-1001", state=TicketState.OPEN
    )
    ticket_b = Task(
        id="1M-1001", title="B", description="Blocks 1M-1002", state=TicketState.OPEN
    )
    ticket_c = Task(id="1M-1002", title="C", description="", state=TicketState.OPEN)

    graph.add_ticket(ticket_a)
    graph.add_ticket(ticket_b)
    graph.add_ticket(ticket_c)
    graph.finalize()

    critical_path = graph.get_critical_path()

    assert len(critical_path) == 3
    assert critical_path[0] == "1M-1000"
    assert critical_path[-1] == "1M-1002"


def test_get_critical_path_multiple_branches():
    """Test critical path with multiple branches (picks longest)."""
    graph = DependencyGraph()

    # Long branch: A -> B -> C -> D
    # Short branch: A -> E
    ticket_a = Task(
        id="1M-1100",
        title="A",
        description="Blocks 1M-1101 and 1M-1105",
        state=TicketState.OPEN,
    )
    ticket_b = Task(
        id="1M-1101", title="B", description="Blocks 1M-1102", state=TicketState.OPEN
    )
    ticket_c = Task(
        id="1M-1102", title="C", description="Blocks 1M-1103", state=TicketState.OPEN
    )
    ticket_d = Task(id="1M-1103", title="D", description="", state=TicketState.OPEN)
    ticket_e = Task(id="1M-1105", title="E", description="", state=TicketState.OPEN)

    graph.add_ticket(ticket_a)
    graph.add_ticket(ticket_b)
    graph.add_ticket(ticket_c)
    graph.add_ticket(ticket_d)
    graph.add_ticket(ticket_e)
    graph.finalize()

    critical_path = graph.get_critical_path()

    # Should pick the longer path
    assert len(critical_path) >= 3
    assert "1M-1100" in critical_path


def test_get_blocked_tickets():
    """Test identification of blocked tickets."""
    graph = DependencyGraph()

    ticket_a = Task(
        id="1M-1200", title="A", description="Blocks 1M-1201", state=TicketState.OPEN
    )
    ticket_b = Task(
        id="1M-1201",
        title="B",
        description="Blocked by 1M-1200",
        state=TicketState.BLOCKED,
    )

    graph.add_ticket(ticket_a)
    graph.add_ticket(ticket_b)
    graph.finalize()

    blocked = graph.get_blocked_tickets()

    assert "1M-1201" in blocked
    assert "1M-1200" in blocked["1M-1201"]


def test_get_high_impact_tickets():
    """Test identification of high-impact tickets (blocking many others)."""
    graph = DependencyGraph()

    # Ticket A blocks 3 others
    ticket_a = Task(
        id="1M-1300",
        title="A",
        description="Blocks 1M-1301 and blocks 1M-1302 and blocks 1M-1303",
        state=TicketState.OPEN,
    )
    ticket_b = Task(id="1M-1301", title="B", description="", state=TicketState.OPEN)
    ticket_c = Task(id="1M-1302", title="C", description="", state=TicketState.OPEN)
    ticket_d = Task(id="1M-1303", title="D", description="", state=TicketState.OPEN)

    graph.add_ticket(ticket_a)
    graph.add_ticket(ticket_b)
    graph.add_ticket(ticket_c)
    graph.add_ticket(ticket_d)
    graph.finalize()

    high_impact = graph.get_high_impact_tickets()

    assert len(high_impact) > 0
    assert high_impact[0][0] == "1M-1300"
    assert high_impact[0][1] == 3  # Blocks 3 tickets


def test_empty_graph():
    """Test operations on empty graph."""
    graph = DependencyGraph()
    graph.finalize()

    assert len(graph.get_critical_path()) == 0
    assert len(graph.get_blocked_tickets()) == 0
    assert len(graph.get_high_impact_tickets()) == 0


def test_case_insensitive_matching():
    """Test that dependency patterns are matched case-insensitively."""
    graph = DependencyGraph()

    ticket = Task(
        id="1M-1400",
        title="Test",
        description="BLOCKS 1M-1401 and Depends On 1M-1399",
        state=TicketState.OPEN,
    )

    graph.add_ticket(ticket)
    graph.finalize()

    assert "1M-1401" in graph.edges["1M-1400"]
    assert "1M-1399" in graph.reverse_edges["1M-1400"]
