#!/usr/bin/env python3
"""
Unit tests for v3.5 recipe migration and schema validation.
"""

import unittest
from pathlib import Path

import yaml

from village_game import GameEngine


class TestRecipeMigration(unittest.TestCase):
    """Test v3.5 recipe migration and compatibility."""

    def setUp(self):
        """Load test data."""
        self.base_path = Path('.')

        # Load v3.5 recipes (now the main recipes.yaml)
        with open(self.base_path / 'recipes.yaml', encoding='utf-8') as f:
            self.v35_data = yaml.safe_load(f)

        # Load legacy recipes (archived)
        with open(self.base_path / 'recipes_legacy.yaml', encoding='utf-8') as f:
            self.legacy_data = yaml.safe_load(f)

        # Load goods for validation
        with open(self.base_path / 'raw_goods.yaml', encoding='utf-8') as f:
            raw_data = yaml.safe_load(f)
            self.raw_goods = raw_data.get('goods', {})

        with open(self.base_path / 'produced_goods.yaml', encoding='utf-8') as f:
            prod_data = yaml.safe_load(f)
            self.produced_goods = prod_data.get('goods', {})

        self.all_goods = {**self.raw_goods, **self.produced_goods}

        # Load facilities
        with open(self.base_path / 'facilities.yaml', encoding='utf-8') as f:
            fac_data = yaml.safe_load(f)
            self.facilities = fac_data.get('facilities', {})

    def test_v35_schema_version(self):
        """Test that v3.5 file has correct schema version."""
        self.assertEqual(self.v35_data.get('schema_version'), '3.5')

    def test_v35_recipe_count(self):
        """Test that all legacy recipes were converted."""
        legacy_count = len(self.legacy_data.get('recipes', {}))
        v35_count = len(self.v35_data.get('recipes', []))
        self.assertEqual(v35_count, legacy_count,
                        f"Expected {legacy_count} recipes, got {v35_count}")

    def test_v35_recipe_structure(self):
        """Test that v3.5 recipes have required fields."""
        required_fields = ['id', 'facility', 'inputs', 'outputs',
                          'cycle_time_minutes', 'workers_required',
                          'skill_used', 'min_skill', 'waste_chance']

        recipes = self.v35_data.get('recipes', [])
        self.assertGreater(len(recipes), 0, "No recipes found")

        for recipe in recipes:
            for field in required_fields:
                self.assertIn(field, recipe,
                             f"Recipe {recipe.get('id')} missing field: {field}")

    def test_all_items_exist(self):
        """Test that all recipe items reference valid goods."""
        recipes = self.v35_data.get('recipes', [])

        for recipe in recipes:
            recipe_id = recipe.get('id')

            # Check inputs
            for item in recipe.get('inputs', {}).keys():
                self.assertIn(item, self.all_goods,
                             f"Recipe {recipe_id} references unknown input: {item}")

            # Check outputs
            for item in recipe.get('outputs', {}).keys():
                self.assertIn(item, self.all_goods,
                             f"Recipe {recipe_id} references unknown output: {item}")

            # Check byproducts
            for item in recipe.get('byproducts', {}).keys():
                self.assertIn(item, self.all_goods,
                             f"Recipe {recipe_id} references unknown byproduct: {item}")

    def test_all_facilities_exist(self):
        """Test that all recipe facilities are defined."""
        recipes = self.v35_data.get('recipes', [])

        for recipe in recipes:
            recipe_id = recipe.get('id')
            facility = recipe.get('facility')
            self.assertIn(facility, self.facilities,
                         f"Recipe {recipe_id} references undefined facility: {facility}")

    def test_numeric_values(self):
        """Test that numeric fields have valid values."""
        recipes = self.v35_data.get('recipes', [])

        for recipe in recipes:
            recipe_id = recipe.get('id')

            # Cycle time should be positive
            cycle_time = recipe.get('cycle_time_minutes', 0)
            self.assertGreater(cycle_time, 0,
                             f"Recipe {recipe_id} has invalid cycle_time_minutes: {cycle_time}")

            # Workers should be positive
            workers = recipe.get('workers_required', 0)
            self.assertGreater(workers, 0,
                             f"Recipe {recipe_id} has invalid workers_required: {workers}")

            # Waste chance should be between 0 and 1
            waste = recipe.get('waste_chance', 0)
            self.assertGreaterEqual(waste, 0,
                                   f"Recipe {recipe_id} has negative waste_chance: {waste}")
            self.assertLessEqual(waste, 1,
                                f"Recipe {recipe_id} has waste_chance > 1: {waste}")

    def test_game_engine_loads_v35(self):
        """Test that GameEngine can load v3.5 recipes."""
        # This would load from recipes.yaml by default, but we can test the conversion logic
        game = GameEngine()
        self.assertGreater(len(game.village.recipes), 0, "No recipes loaded")

        # Check that a sample recipe has expected structure
        if 'flour_from_grain' in game.village.recipes:
            recipe = game.village.recipes['flour_from_grain']
            self.assertIn('facility', recipe)
            self.assertIn('inputs', recipe)
            self.assertIn('outputs', recipe)
            self.assertIn('labor', recipe)

    def test_mass_conservation_examples(self):
        """Test that some recipes conserve mass approximately."""
        recipes = self.v35_data.get('recipes', [])

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
                self.assertLess(ratio, 2.0,
                               f"Recipe {recipe_id} has suspicious output/input ratio: {ratio:.2f}")


class TestSchemaValidation(unittest.TestCase):
    """Test schema validation helpers."""

    def test_legacy_recipe_format(self):
        """Test that legacy recipes have dict structure."""
        with open('recipes_legacy.yaml', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            recipes = data.get('recipes', {})
            self.assertIsInstance(recipes, dict,
                                "Legacy recipes should be a dict")

    def test_v35_recipe_format(self):
        """Test that v3.5 recipes have list structure."""
        with open('recipes.yaml', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            recipes = data.get('recipes', [])
            self.assertIsInstance(recipes, list,
                                "v3.5 recipes should be a list")


def run_tests():
    """Run all tests and print results."""
    print("="*70)
    print("RUNNING MIGRATION TESTS")
    print("="*70)

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestRecipeMigration))
    suite.addTests(loader.loadTestsFromTestCase(TestSchemaValidation))

    # Run with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")

    if result.wasSuccessful():
        print("\n✓ ALL TESTS PASSED!")
        return 0
    else:
        print("\n✗ SOME TESTS FAILED")
        return 1


if __name__ == '__main__':
    exit(run_tests())
