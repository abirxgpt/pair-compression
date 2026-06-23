"""Tests for importance map generation."""

import numpy as np
import pytest
from pawc.importance_map import ImportanceMapGenerator, generate_importance_map


def test_importance_map_shape():
    """Test that importance map has correct shape."""
    # Create test image
    image = np.random.randint(0, 256, size=(256, 256, 3), dtype=np.uint8)
    
    # Generate importance map
    imp_map = generate_importance_map(image)
    
    # Check shape
    assert imp_map.shape == (256, 256)


def test_importance_map_range():
    """Test that importance map values are in [0, 1]."""
    image = np.random.randint(0, 256, size=(128, 128, 3), dtype=np.uint8)
    imp_map = generate_importance_map(image)
    
    assert imp_map.min() >= 0.0
    assert imp_map.max() <= 1.0


def test_importance_map_grayscale():
    """Test importance map generation for grayscale images."""
    image = np.random.randint(0, 256, size=(100, 100), dtype=np.uint8)
    imp_map = generate_importance_map(image)
    
    assert imp_map.shape == (100, 100)


def test_custom_weights():
    """Test importance map with custom weights."""
    image = np.random.randint(0, 256, size=(64, 64, 3), dtype=np.uint8)
    
    generator = ImportanceMapGenerator(
        edge_weight=0.5,
        texture_weight=0.3,
        saliency_weight=0.2
    )
    
    imp_map = generator.generate(image)
    
    assert imp_map.shape == (64, 64)
    assert 0.0 <= imp_map.min() <= 1.0
    assert 0.0 <= imp_map.max() <= 1.0
