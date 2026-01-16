#!/usr/bin/env python3
"""
Unit tests for v3.5 recipe migration and schema validation.
Converted to pytest style with proper data path handling.
"""

import logging
from pathlib import Path

import pytest
import yaml

from village_game import GameEngine


# Configure logging for tests
logging.basicConfig(level=logging.INFO)


@pytest.fixture
def data_path():
    """Return the path to test data files.

    Tests are independent of working directory by looking for data files
    relative to the module location or in the current directory.
    """
    # Try module directory first
    module_dir = Path(__file__).parent
    if (module_dir / 'recipes.yaml').exists():
        return module_dir

    # Fall back to current working directory
    cwd = Path.cwd()
    if (cwd / 'recipes.yaml').exists():
        return cwd

    # If running from a subdirectory, try parent
    if (cwd.parent / 'recipes.yaml').exists():
        return cwd.parent

    pytest.fail("Could not locate data files (recipes.yaml). "
                "Ensure tests run from repo root or data files are in module directory.")


@pytest.fixture
def v35_data(data_path):
    """Load v3.5 recipes (current recipes.yaml)."""
    with open(data_path / 'recipes.yaml', encoding='utf-8') as f:
        return yaml.safe_load(f)


@pytest.fixture
def legacy_data(data_path):
    """Load legacy recipes (recipes_legacy.yaml)."""
    with open(data_path / 'recipes_legacy.yaml', encoding='utf-8') as f:
        return yaml.safe_load(f)


@pytest.fixture
def raw_goods(data_path):
    """Load raw goods data."""
    with open(data_path / 'raw_goods.yaml', encoding='utf-8') as f:
        data = yaml.safe_load(f)
        return data.get('goods', {})


@pytest.fixture
def produced_goods(data_path):
    """Load produced goods data."""
    with open(data_path / 'produced_goods.yaml', encoding='utf-8') as f:
        data = yaml.safe_load(f)
        return data.get('goods', {})


@pytest.fixture
def all_goods(raw_goods, produced_goods):
    """Combined dictionary of all goods."""
    return {**raw_goods, **produced_goods}


@pytest.fixture
def facilities(data_path):
    """Load facilities data."""
    with open(data_path / 'facilities.yaml', encoding='utf-8') as f:
        data = yaml.safe_load(f)
        return data.get('facilities', {})


class TestRecipeMigration:
    """Test v3.5 recipe migration and compatibility."""

    def test_v35_schema_version(self, v35_data):
        """Test that v3.5 file has correct schema version."""
        assert v35_data.get('schema_version') == '3.5'

    def test_v35_recipe_count(self, v35_data, legacy_data):
        """Test that all legacy recipes were converted."""
        legacy_count = len(legacy_data.get('recipes', {}))
        v35_count = len(v35_data.get('recipes', []))
        assert v35_count == legacy_count, \
            f"Expected {legacy_count} recipes, got {v35_count}"

    def test_v35_recipe_structure(self, v35_data):
        """Test that v3.5 recipes have required fields."""
        required_fields = [
            'id', 'facility', 'inputs', 'outputs',
            'cycle_time_minutes', 'workers_required',
            'skill_used', 'min_skill', 'waste_chance'
        ]

        recipes = v35_data.get('recipes', [])
        assert len(recipes) > 0, "No recipes found"

        for recipe in recipes:
            for field in required_fields:
                assert field in recipe, \
                    f"Recipe {recipe.get('id')} missing field: {field}"

    def test_all_items_exist(self, v35_data, all_goods):
        """Test that all recipe items reference valid goods."""
        recipes = v35_data.get('recipes', [])

        for recipe in recipes:
            recipe_id = recipe.get('id')

            # Check inputs
            for item in recipe.get('inputs', {}).keys():
                assert item in all_goods, \
                    f"Recipe {recipe_id} references unknown input: {item}"

            # Check outputs
            for item in recipe.get('outputs', {}).keys():
                assert item in all_goods, \
                    f"Recipe {recipe_id} references unknown output: {item}"

            # Check byproducts
            for item in recipe.get('byproducts', {}).keys():
                assert item in all_goods, \
                    f"Recipe {recipe_id} references unknown byproduct: {item}"

    def test_all_facilities_exist(self, v35_data, facilities):
        """Test that all recipe facilities are defined."""
        recipes = v35_data.get('recipes', [])

        for recipe in recipes:
            recipe_id = recipe.get('id')
            facility = recipe.get('facility')
            assert facility in facilities, \
                f"Recipe {recipe_id} references undefined facility: {facility}"

    def test_numeric_values(self, v35_data):
        """Test that numeric fields have valid values."""
        recipes = v35_data.get('recipes', [])

        for recipe in recipes:
            recipe_id = recipe.get('id')

            # Cycle time should be positive
            cycle_time = recipe.get('cycle_time_minutes', 0)
            assert cycle_time > 0, \
                f"Recipe {recipe_id} has invalid cycle_time_minutes: {cycle_time}"

            # Workers should be positive
            workers = recipe.get('workers_required', 0)
            assert workers > 0, \
                f"Recipe {recipe_id} has invalid workers_required: {workers}"

            # Waste chance should be between 0 and 1
            waste = recipe.get('waste_chance', 0)
            assert waste >= 0, \
                f"Recipe {recipe_id} has negative waste_chance: {waste}"
            assert waste <= 1, \
                f"Recipe {recipe_id} has waste_chance > 1: {waste}"

    def test_game_engine_loads_v35(self, data_path):
        """Test that GameEngine can load v3.5 recipes."""
        # Pass explicit data path to GameEngine
        game = GameEngine(data_path=str(data_path))
        assert len(game.village.recipes) > 0, "No recipes loaded"

        # Check that a sample recipe has expected structure
        if 'flour_from_grain' in game.village.recipes:
            recipe = game.village.recipes['flour_from_grain']
            assert 'facility' in recipe
            assert 'inputs' in recipe
            assert 'outputs' in recipe
            # Fixed: GameEngine uses 'workers_required', not 'labor'
            assert 'workers_required' in recipe

    def test_mass_conservation_examples(self, v35_data):
        """Test that some recipes conserve mass approximately."""
        recipes = v35_data.get('recipes', [])

        for recipe in recipes:
            recipe_id = recipe.get('id')

            # Calculate total input mass (kg)
            total_input = sum(recipe.get('inputs', {}).values())

            # Calculate total output mass (kg)
            total_output = sum(recipe.get('outputs', {}).values())
            total_output += sum(recipe.get('byproducts', {}).values())

            # Skip recipes with water or recipes that transform materials significantly
            if 'water' in recipe.get('inputs', {}):
                continue

            # For most physical processes, output shouldn't exceed input
            # (allow some tolerance for data entry variations)
            if total_input > 0:
                ratio = total_output / total_input
                assert ratio < 2.0, \
                    f"Recipe {recipe_id} has suspicious output/input ratio: {ratio:.2f}"


class TestSchemaValidation:
    """Test schema validation helpers."""

    def test_legacy_recipe_format(self, data_path):
        """Test that legacy recipes have dict structure."""
        with open(data_path / 'recipes_legacy.yaml', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            recipes = data.get('recipes', {})
            assert isinstance(recipes, dict), \
                "Legacy recipes should be a dict"

    def test_v35_recipe_format(self, data_path):
        """Test that v3.5 recipes have list structure."""
        with open(data_path / 'recipes.yaml', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            recipes = data.get('recipes', [])
            assert isinstance(recipes, list), \
                "v3.5 recipes should be a list"


def test_game_engine_missing_files(tmp_path):
    """Test that GameEngine handles missing files gracefully."""
    # Create an empty directory with no data files
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    # GameEngine should not crash when files are missing
    # Instead, it should log errors and continue with empty data
    game = GameEngine(data_path=str(empty_dir))

    # Verify it loaded empty data structures
    assert len(game.village.recipes) == 0, "Should have no recipes when files missing"
    assert len(game.village.raw_goods) == 0, "Should have no raw goods when files missing"
    assert len(game.village.produced_goods) == 0, "Should have no produced goods when files missing"


if __name__ == '__main__':
    # Run with pytest
    import sys
    sys.exit(pytest.main([__file__, '-v']))
