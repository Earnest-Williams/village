#!/usr/bin/env python3
"""
Medieval Village Simulation - Basic Gameplay Loop
A turn-based resource management game with production chains.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from collections import defaultdict

import yaml

# Setup logger for library code
logger = logging.getLogger(__name__)


@dataclass
class Inventory:
    """Manages storage of goods with stack limits."""
    items: Dict[str, float] = field(default_factory=lambda: defaultdict(float))

    def add(self, item: str, amount: float) -> float:
        """Add items, return amount actually added."""
        self.items[item] += amount
        return amount

    def remove(self, item: str, amount: float) -> bool:
        """Remove items if available, return success."""
        if self.items[item] >= amount:
            self.items[item] -= amount
            if self.items[item] == 0:
                del self.items[item]
            return True
        return False

    def has(self, item: str, amount: float) -> bool:
        """Check if inventory has enough of an item."""
        return self.items.get(item, 0) >= amount

    def get(self, item: str) -> float:
        """Get current amount of an item."""
        return self.items.get(item, 0)


@dataclass
class Facility:
    """A production facility that runs recipes."""
    facility_id: str
    capacity: int
    workers_assigned: int = 0
    enabled_recipes: List[str] = field(default_factory=list)

    def can_work(self) -> bool:
        return self.workers_assigned > 0


@dataclass
class Village:
    """Main game state."""
    day: int = 1
    population: int = 5
    idle_workers: int = 5

    inventory: Inventory = field(default_factory=Inventory)
    facilities: Dict[str, Facility] = field(default_factory=dict)

    # Game data
    raw_goods: Dict = field(default_factory=dict)
    produced_goods: Dict = field(default_factory=dict)
    compound_goods: Dict = field(default_factory=dict)
    recipes: Dict = field(default_factory=dict)


class GameEngine:
    """Core game loop and mechanics."""

    def __init__(self, data_path: Optional[str] = None):
        self.village = Village()
        # Default to ./data if it exists next to this module, otherwise fall back to the module directory
        if data_path is None:
            base_dir = Path(__file__).parent
            data_dir = base_dir / "data"
            data_path = data_dir if data_dir.is_dir() else base_dir
        self.load_game_data(str(data_path))

    def load_game_data(self, path: str):
        """Load YAML game data files with robust error handling."""
        base = Path(path)

        # Helper to safely load YAML files
        def safe_load_yaml(filename: str, default_key: str = None):
            """Load YAML file with error handling."""
            file_path = base / filename
            try:
                with open(file_path, encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                    logger.debug(f"Loaded {filename}")
                    return data
            except FileNotFoundError:
                logger.error(f"Missing data file: {file_path}")
                return {}
            except yaml.YAMLError as e:
                logger.error(f"Invalid YAML in {filename}: {e}")
                return {}
            except Exception as e:
                logger.error(f"Error loading {filename}: {e}")
                return {}

        # Load raw goods
        raw_data = safe_load_yaml("raw_goods.yaml")
        self.village.raw_goods = raw_data.get("goods", {})

        # Load produced goods
        prod_data = safe_load_yaml("produced_goods.yaml")
        self.village.produced_goods = prod_data.get("goods", {})

        # Load compound goods from separate files
        facilities_data = safe_load_yaml("facilities.yaml")
        fixtures_data = safe_load_yaml("fixtures.yaml")
        equipment_data = safe_load_yaml("equipment.yaml")

        # Merge into compound_goods structure for backward compatibility
        self.village.compound_goods = {
            "facilities": facilities_data.get("facilities", {}),
            "fixtures": fixtures_data.get("fixtures", {}),
            "equipment": equipment_data.get("equipment", {}),
        }

        # Load recipes with conversion from list to dict format
        recipes_data = safe_load_yaml("recipes.yaml")
        recipes_list = recipes_data.get("recipes", [])
        recipes_dict = {}
        for recipe in recipes_list:
            rid = recipe.get("id")
            if not rid:
                logger.warning(f"Recipe missing 'id' field, skipping: {recipe}")
                continue
            recipes_dict[rid] = {
                "facility": recipe.get("facility"),
                "inputs": recipe.get("inputs", {}),
                "outputs": recipe.get("outputs", {}),
                "byproducts": recipe.get("byproducts", {}),
                "cycle_time_minutes": recipe.get("cycle_time_minutes", 60),
                "workers_required": recipe.get("workers_required", 1),
                "skill_used": recipe.get("skill_used", ""),
                "min_skill": recipe.get("min_skill", 0),
                "waste_chance": recipe.get("waste_chance", 0.0)
            }
        self.village.recipes = recipes_dict

        # Log summary
        logger.info(
            f"Loaded game data: {len(self.village.raw_goods)} raw goods, "
            f"{len(self.village.produced_goods)} produced goods, "
            f"{len(self.village.compound_goods['facilities'])} facilities, "
            f"{len(self.village.recipes)} recipes"
        )

    def get_all_goods(self) -> Dict:
        """Combined goods dictionary."""
        return {**self.village.raw_goods, **self.village.produced_goods}

    def gather_resources(self, resource: str, workers: int = 1) -> float:
        """Gather raw resources. Returns amount gathered."""
        goods = self.get_all_goods()

        if resource not in goods:
            return 0

        item = goods[resource]
        gather_rate = item.get("gather_rate", 0)

        if gather_rate == 0:
            return 0

        # Base gathering: 1 worker gathers at rate% efficiency per day
        # This is simplified - real game would have more complex formulas
        base_amount = workers * (gather_rate / 100.0) * 10  # 10 units at 100% rate

        self.village.inventory.add(resource, base_amount)
        return base_amount

    def build_facility(self, facility_id: str) -> bool:
        """Build a facility if resources are available."""
        facilities = self.village.compound_goods.get("facilities", {})

        if facility_id not in facilities:
            return False

        if facility_id in self.village.facilities:
            return False  # Already built

        facility_data = facilities[facility_id]
        inputs = facility_data.get("inputs", {})

        # Check resources
        for item, amount in inputs.items():
            if not self.village.inventory.has(item, amount):
                return False

        # Consume resources
        for item, amount in inputs.items():
            self.village.inventory.remove(item, amount)

        # Create facility
        capacity = facility_data.get("capacity", 1)
        enabled = facility_data.get("enables_recipes", [])

        self.village.facilities[facility_id] = Facility(
            facility_id=facility_id,
            capacity=capacity,
            enabled_recipes=enabled
        )

        return True

    def assign_worker(self, facility_id: str, workers: int = 1) -> bool:
        """Assign workers to a facility."""
        if facility_id not in self.village.facilities:
            return False

        if self.village.idle_workers < workers:
            return False

        facility = self.village.facilities[facility_id]
        if facility.workers_assigned + workers > facility.capacity:
            return False

        facility.workers_assigned += workers
        self.village.idle_workers -= workers
        return True

    def unassign_worker(self, facility_id: str, workers: int = 1) -> bool:
        """Remove workers from a facility."""
        if facility_id not in self.village.facilities:
            return False

        facility = self.village.facilities[facility_id]
        if facility.workers_assigned < workers:
            return False

        facility.workers_assigned -= workers
        self.village.idle_workers += workers
        return True

    def run_recipe(self, recipe_id: str, facility_id: str, times: int = 1) -> int:
        """Run a recipe at a facility. Returns number of successful runs."""
        if recipe_id not in self.village.recipes:
            return 0

        if facility_id not in self.village.facilities:
            return 0

        recipe = self.village.recipes[recipe_id]
        facility = self.village.facilities[facility_id]

        # Check recipe is enabled at this facility
        if recipe.get("facility") != facility_id:
            return 0

        if not facility.can_work():
            return 0

        successful = 0
        for _ in range(times):
            # Check inputs
            inputs = recipe.get("inputs", {})
            can_craft = all(
                self.village.inventory.has(item, amount)
                for item, amount in inputs.items()
            )

            if not can_craft:
                break

            # Consume inputs
            for item, amount in inputs.items():
                self.village.inventory.remove(item, amount)

            # Add outputs
            outputs = recipe.get("outputs", {})
            for item, amount in outputs.items():
                self.village.inventory.add(item, amount)

            # Add byproducts
            byproducts = recipe.get("byproducts", {})
            for item, amount in byproducts.items():
                self.village.inventory.add(item, amount)

            successful += 1

        return successful

    def advance_day(self):
        """Process end-of-day production and advance time."""
        # Auto-run recipes at facilities with assigned workers
        for facility_id, facility in self.village.facilities.items():
            if facility.workers_assigned > 0:
                # Find recipes for this facility
                for recipe_id, recipe in self.village.recipes.items():
                    if recipe.get("facility") == facility_id:
                        recipe_cycle = recipe.get("cycle_time_minutes", 60) or 60
                        # how many times a single worker can complete this recipe in an 8h day
                        work_hours_per_day = 8
                        runs_per_worker = max(1, int((work_hours_per_day * 60) // recipe_cycle))
                        runs = facility.workers_assigned * runs_per_worker
                        if runs > 0:
                            self.run_recipe(recipe_id, facility_id, runs)

        self.village.day += 1

    def get_status(self) -> str:
        """Get current village status as a formatted string."""
        lines = []
        lines.append(f"\n{'='*60}")
        lines.append(f"Day {self.village.day} | Population: {self.village.population} | Idle Workers: {self.village.idle_workers}")
        lines.append(f"{'='*60}")

        # Inventory
        if self.village.inventory.items:
            lines.append("\n📦 INVENTORY:")
            for item, amount in sorted(self.village.inventory.items.items()):
                lines.append(f"  {item}: {amount:.1f}")
        else:
            lines.append("\n📦 INVENTORY: Empty")

        # Facilities
        if self.village.facilities:
            lines.append("\n🏭 FACILITIES:")
            for fid, facility in self.village.facilities.items():
                status = f"{facility.workers_assigned}/{facility.capacity} workers"
                lines.append(f"  {fid}: {status}")
        else:
            lines.append("\n🏭 FACILITIES: None")

        return "\n".join(lines)

    def print_status(self):
        """Display current village status (CLI wrapper)."""
        status = self.get_status()
        print(status)
        logger.debug("Village status displayed")


def main():
    """Main game loop."""
    print("=" * 60)
    print("MEDIEVAL VILLAGE SIMULATION")
    print("=" * 60)

    game = GameEngine()

    print("\nStarting with 5 idle workers and no resources.")
    print("Let's gather some basic materials to get started!")

    # Tutorial: Gather initial resources
    print("\n--- GATHERING PHASE (Day 1-3) ---")
    print("Assigning 2 workers to gather logs...")
    game.gather_resources("logs", workers=2)

    print("Assigning 2 workers to gather stone...")
    game.gather_resources("stone", workers=2)

    print("Assigning 1 worker to gather clay...")
    game.gather_resources("clay", workers=1)

    game.print_status()

    # Build first facility
    print("\n--- BUILDING PHASE (Day 4) ---")
    print("Attempting to build woodworker_hut...")

    if game.build_facility("woodworker_hut"):
        print("✓ Built woodworker_hut!")
    else:
        print("✗ Cannot build - missing resources")
        print("Required: lumber: 12, stone: 5")
        print("We need to process logs into lumber first!")

    # Try to build sawmill instead
    print("\nTrying sawmill instead (needs: lumber: 30, stone_blocks: 10, nails: 6, iron_ingots: 2)...")
    print("We don't have these either. Let's gather more raw materials.")

    # More gathering
    print("\n--- MORE GATHERING (Day 4-7) ---")
    for day in range(3):
        game.gather_resources("logs", workers=3)
        game.gather_resources("stone", workers=2)
        game.advance_day()

    game.print_status()

    # Interactive loop
    print("\n" + "=" * 60)
    print("INTERACTIVE MODE")
    print("=" * 60)
    print("Commands:")
    print("  gather <resource> <workers> - Gather resources")
    print("  build <facility>            - Build a facility")
    print("  assign <facility> <workers> - Assign workers to facility")
    print("  unassign <facility> <workers> - Remove workers from facility")
    print("  recipe <recipe_id> <facility> <times> - Run a recipe manually")
    print("  next                        - Advance to next day")
    print("  status                      - Show village status")
    print("  list [goods|facilities|recipes] - List available items")
    print("  help                        - Show this help")
    print("  quit                        - Exit game")

    while True:
        try:
            cmd = input(f"\n[Day {game.village.day}]> ").strip().lower().split()

            if not cmd:
                continue

            action = cmd[0]

            if action == "quit":
                print("Thanks for playing!")
                break

            elif action == "status":
                game.print_status()

            elif action == "help":
                print("\nAvailable commands: gather, build, assign, unassign, recipe, next, status, list, help, quit")

            elif action == "list":
                category = cmd[1] if len(cmd) > 1 else "goods"

                if category == "goods":
                    print("\nRAW GOODS:")
                    for gid in sorted(game.village.raw_goods.keys()):
                        rate = game.village.raw_goods[gid].get("gather_rate", 0)
                        print(f"  {gid} (gather rate: {rate}%)")
                    print("\nPRODUCED GOODS:")
                    for gid in sorted(game.village.produced_goods.keys()):
                        print(f"  {gid}")

                elif category == "facilities":
                    facilities = game.village.compound_goods.get("facilities", {})
                    print("\nAVAILABLE FACILITIES:")
                    for fid, fdata in facilities.items():
                        built = "✓" if fid in game.village.facilities else " "
                        inputs = fdata.get("inputs", {})
                        inp_str = ", ".join(f"{k}:{v}" for k, v in inputs.items())
                        print(f"  [{built}] {fid}")
                        print(f"      Requires: {inp_str}")

                elif category == "recipes":
                    print("\nAVAILABLE RECIPES:")
                    for rid, rdata in game.village.recipes.items():
                        facility = rdata.get("facility", "?")
                        inputs = rdata.get("inputs", {})
                        outputs = rdata.get("outputs", {})
                        inp_str = ", ".join(f"{k}:{v}" for k, v in inputs.items())
                        out_str = ", ".join(f"{k}:{v}" for k, v in outputs.items())
                        print(f"  {rid} @ {facility}")
                        print(f"      In: {inp_str} → Out: {out_str}")

            elif action == "gather" and len(cmd) >= 2:
                resource = cmd[1]
                workers = int(cmd[2]) if len(cmd) > 2 else 1

                if workers > game.village.idle_workers:
                    print(f"Not enough idle workers! Have {game.village.idle_workers}, need {workers}")
                else:
                    amount = game.gather_resources(resource, workers)
                    if amount > 0:
                        print(f"Gathered {amount:.1f} {resource}")
                    else:
                        print(f"Cannot gather {resource} (gather_rate is 0 or invalid resource)")

            elif action == "build" and len(cmd) >= 2:
                facility = cmd[1]
                if game.build_facility(facility):
                    print(f"✓ Built {facility}!")
                else:
                    print(f"✗ Cannot build {facility}")
                    facilities = game.village.compound_goods.get("facilities", {})
                    if facility in facilities:
                        req = facilities[facility].get("inputs", {})
                        print(f"Required: {req}")

            elif action == "assign" and len(cmd) >= 2:
                facility = cmd[1]
                workers = int(cmd[2]) if len(cmd) > 2 else 1

                if game.assign_worker(facility, workers):
                    print(f"✓ Assigned {workers} worker(s) to {facility}")
                else:
                    print(f"✗ Cannot assign workers to {facility}")

            elif action == "unassign" and len(cmd) >= 2:
                facility = cmd[1]
                workers = int(cmd[2]) if len(cmd) > 2 else 1

                if game.unassign_worker(facility, workers):
                    print(f"✓ Removed {workers} worker(s) from {facility}")
                else:
                    print(f"✗ Cannot remove workers from {facility}")

            elif action == "recipe" and len(cmd) >= 3:
                recipe_id = cmd[1]
                facility_id = cmd[2]
                times = int(cmd[3]) if len(cmd) > 3 else 1

                runs = game.run_recipe(recipe_id, facility_id, times)
                if runs > 0:
                    print(f"✓ Ran {recipe_id} {runs} time(s)")
                else:
                    print(f"✗ Could not run {recipe_id}")

            elif action == "next":
                game.advance_day()
                print(f"Advanced to day {game.village.day}")
                print("Facilities with workers have auto-produced items.")
                game.print_status()

            else:
                print("Unknown command. Type 'help' for commands.")

        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()