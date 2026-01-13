#!/usr/bin/env python3
"""
Demo gameplay session showing the production chain in action.
This script demonstrates a typical early-game progression.
"""

from village_game import GameEngine


def demo_session():
    """Run a scripted demo showing key gameplay mechanics."""
    
    print("=" * 70)
    print("MEDIEVAL VILLAGE SIMULATION - DEMO SESSION")
    print("=" * 70)
    print("\nGoal: Build a bakery and produce bread")
    print("Strategy: logs → lumber → build sawmill → build bakery → produce bread")
    print()
    
    game = GameEngine()
    game.print_status()
    
    # Phase 1: Initial gathering
    print("\n" + "=" * 70)
    print("PHASE 1: Gather raw materials (Days 1-3)")
    print("=" * 70)
    
    print("\nDay 1: All 5 workers gather logs")
    game.gather_resources("logs", workers=5)
    game.advance_day()
    
    print("\nDay 2: Continue gathering logs")
    game.gather_resources("logs", workers=5)
    game.advance_day()
    
    print("\nDay 3: Gather stone and clay")
    game.gather_resources("stone", workers=3)
    game.gather_resources("clay", workers=2)
    game.advance_day()
    
    game.print_status()
    
    # Phase 2: Try to build something
    print("\n" + "=" * 70)
    print("PHASE 2: Build first facility")
    print("=" * 70)
    
    print("\nChecking what we can build...")
    print("\n1. Woodcutter hut requires: lumber: 12, stone: 5")
    print("   Problem: We have logs but not lumber!")
    
    print("\n2. Sawmill requires: lumber: 30, stone_blocks: 10, nails: 6, iron_ingots: 2")
    print("   Problem: We need processed materials we can't make yet!")
    
    print("\n3. Solution: We're in a bootstrapping problem.")
    print("   In a real game, you'd start with some basic processed goods,")
    print("   or have a simple way to convert logs → lumber manually.")
    
    print("\n💡 Let's cheat a bit and add some starter lumber...")
    game.village.inventory.add("lumber", 50)
    game.village.inventory.add("stone_blocks", 15)
    game.village.inventory.add("iron_ingots", 5)
    game.village.inventory.add("nails", 10)
    
    game.print_status()
    
    # Phase 3: Build production chain
    print("\n" + "=" * 70)
    print("PHASE 3: Build production facilities")
    print("=" * 70)
    
    print("\nBuilding sawmill...")
    if game.build_facility("sawmill"):
        print("✓ Sawmill built!")
    
    print("\nBuilding woodworker_hut...")
    if game.build_facility("woodworker_hut"):
        print("✓ Woodworker hut built!")
    
    game.print_status()
    
    # Phase 4: Assign workers and produce
    print("\n" + "=" * 70)
    print("PHASE 4: Assign workers and start production")
    print("=" * 70)
    
    print("\nAssigning 1 worker to sawmill...")
    game.assign_worker("sawmill", 1)
    
    print("Assigning 1 worker to woodworker_hut...")
    game.assign_worker("woodworker_hut", 1)
    
    game.print_status()
    
    print("\n--- Advancing 3 days with automated production ---")
    for i in range(3):
        # Gather more logs with remaining workers
        game.gather_resources("logs", workers=3)
        game.advance_day()
        print(f"Day {game.village.day}: Auto-production running...")
    
    game.print_status()
    
    # Phase 5: Build food production
    print("\n" + "=" * 70)
    print("PHASE 5: Establish food production")
    print("=" * 70)
    
    # Need grain for flour/bread, but we can't gather it
    print("\nProblem: We need grain to make flour, but grain has gather_rate: 0")
    print("Solution: Add some grain to get started (farm simulation would go here)")
    
    game.village.inventory.add("grain", 50)
    game.village.inventory.add("water", 100)
    
    print("\nBuilding grain_mill...")
    
    # Need a mill wheel first
    print("First need to craft mill_wheel...")
    game.village.inventory.add("mill_wheel", 1)  # Shortcut for demo
    
    if game.build_facility("grain_mill"):
        print("✓ Grain mill built!")
    
    print("\nBuilding bakery...")
    if game.build_facility("bakery"):
        print("✓ Bakery built!")
    
    print("\nAssigning workers to new facilities...")
    game.assign_worker("grain_mill", 1)
    game.assign_worker("bakery", 1)
    
    game.print_status()
    
    # Phase 6: Food production
    print("\n" + "=" * 70)
    print("PHASE 6: Produce food")
    print("=" * 70)
    
    print("\nAdvancing 5 days with full production chain active...")
    for i in range(5):
        game.advance_day()
        
        if i == 2:
            print(f"\nDay {game.village.day} status check:")
            print(f"  Flour: {game.village.inventory.get('flour'):.1f}")
            print(f"  Bread: {game.village.inventory.get('bread'):.1f}")
            print(f"  Bran (byproduct): {game.village.inventory.get('bran'):.1f}")
    
    game.print_status()
    
    # Summary
    print("\n" + "=" * 70)
    print("DEMO COMPLETE!")
    print("=" * 70)
    print("\nWe successfully:")
    print("  ✓ Gathered raw materials (logs, stone, clay)")
    print("  ✓ Built production facilities (sawmill, woodcutter, mill, bakery)")
    print("  ✓ Assigned workers to automate production")
    print("  ✓ Created a production chain: grain → flour → bread")
    print("  ✓ Generated byproducts automatically (bran from milling)")
    
    print("\nKey gameplay mechanics demonstrated:")
    print("  1. Resource gathering (gather_resources)")
    print("  2. Facility construction (build_facility)")
    print("  3. Worker assignment (assign_worker)")
    print("  4. Automated daily production (advance_day)")
    print("  5. Recipe chains (grain → flour → bread)")
    
    print("\nNext steps for a full game:")
    print("  - Add farming system for grain/vegetables")
    print("  - Implement equipment crafting (tools, wagons, etc.)")
    print("  - Add population growth and food consumption")
    print("  - Create trading system")
    print("  - Add random events (seasons, raids, etc.)")
    print("  - Implement building durability and maintenance")
    
    return game


if __name__ == "__main__":
    demo_session()
    
    print("\n" + "=" * 70)
    print("Launch the interactive mode? (y/n)")
    choice = input("> ").strip().lower()
    
    if choice == 'y':
        print("\nStarting interactive mode...")
        print("Type 'help' for commands\n")
        from village_game import main
        main()