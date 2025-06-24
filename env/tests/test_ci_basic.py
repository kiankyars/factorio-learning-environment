import pytest
from env.src.instance import FactorioInstance

@pytest.fixture
def ci_instance():
    """Lightweight instance for CI testing"""
    return FactorioInstance(
        address='localhost',
        bounding_box=50,  # Smaller for faster tests
        tcp_port=27015,
        cache_scripts=False,
        fast=True,
        inventory={'coal': 10, 'iron-plate': 10}
    )

def test_basic_placement(ci_instance):
    """Test basic entity placement"""
    namespace = ci_instance.namespace
    namespace.reset()
    entity = namespace.place_entity('stone-furnace', position=(0, 0))
    assert entity is not None
    assert entity.position.x == 0
    assert entity.position.y == 0

def test_basic_movement(ci_instance):
    """Test basic movement"""
    namespace = ci_instance.namespace
    namespace.reset()
    namespace.move_to((5, 5))
    # Optionally verify position if API allows 