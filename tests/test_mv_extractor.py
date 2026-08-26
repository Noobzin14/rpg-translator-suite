"""Tests for RPG Maker MV database and map extraction."""

import json
from pathlib import Path

import pytest

from app.core.project_model import Project, ProjectLoadStatus
from plugins.rpgmaker_mv.plugin import RPGMakerMVPlugin


@pytest.fixture
def mv_plugin():
    """Create an RPG Maker MV plugin instance."""
    return RPGMakerMVPlugin()


@pytest.fixture
def complete_mv_database(tmp_path):
    """Create a complete RPG Maker MV database fixture with all data files."""
    www_data = tmp_path / "www" / "data"
    www_data.mkdir(parents=True)
    
    # System.json
    system_json = {
        "gameTitle": "Final Fantasy Test",
        "locale": "en_US",
        "partyMembers": [1, 2, 3],
        "terms": {
            "basic": {"party": "Party"},
            "params": {"hp": "HP", "mp": "MP"},
            "commands": {"fight": "Fight", "escape": "Escape"}
        }
    }
    (www_data / "System.json").write_text(json.dumps(system_json), encoding="utf-8")
    
    # Actors.json
    actors_json = [
        {"id": 1, "name": "Hero", "nickname": "The Brave", "profile": "A courageous hero who saved the world."},
        {"id": 2, "name": "Mage", "nickname": "The Wise", "profile": "A powerful magician."}
    ]
    (www_data / "Actors.json").write_text(json.dumps(actors_json), encoding="utf-8")
    
    # Classes.json
    classes_json = [
        {"id": 1, "name": "Warrior"},
        {"id": 2, "name": "Black Mage"}
    ]
    (www_data / "Classes.json").write_text(json.dumps(classes_json), encoding="utf-8")
    
    # Skills.json
    skills_json = [
        {"id": 1, "name": "Fire", "description": "Deals fire damage to one enemy.", "message1": " casts Fire!", "message2": "The enemy burns!"},
        {"id": 2, "name": "Cure", "description": "Restores HP to one ally.", "message1": " casts Cure!", "message2": ""}
    ]
    (www_data / "Skills.json").write_text(json.dumps(skills_json), encoding="utf-8")
    
    # Items.json
    items_json = [
        {"id": 1, "name": "Potion", "description": "Restores 50 HP."},
        {"id": 2, "name": "Ether", "description": "Restores 50 MP."}
    ]
    (www_data / "Items.json").write_text(json.dumps(items_json), encoding="utf-8")
    
    # Weapons.json
    weapons_json = [
        {"id": 1, "name": "Iron Sword", "description": "A basic sword made of iron."},
        {"id": 2, "name": "Magic Staff", "description": "A staff that boosts magic power."}
    ]
    (www_data / "Weapons.json").write_text(json.dumps(weapons_json), encoding="utf-8")
    
    # Armors.json
    armors_json = [
        {"id": 1, "name": "Leather Armor", "description": "Light armor made of leather."},
        {"id": 2, "name": "Magic Robe", "description": "A robe that enhances magic."}
    ]
    (www_data / "Armors.json").write_text(json.dumps(armors_json), encoding="utf-8")
    
    # Enemies.json
    enemies_json = [
        {"id": 1, "name": "Slime"},
        {"id": 2, "name": "Goblin"},
        {"id": 3, "name": "Dragon"}
    ]
    (www_data / "Enemies.json").write_text(json.dumps(enemies_json), encoding="utf-8")
    
    # States.json
    states_json = [
        {"id": 1, "name": "Poison", "message1": " is poisoned!", "message2": "", "message3": "", "message4": ""},
        {"id": 2, "name": "Sleep", "message1": " fell asleep!", "message2": "", "message3": "", "message4": ""}
    ]
    (www_data / "States.json").write_text(json.dumps(states_json), encoding="utf-8")
    
    # Animations.json
    animations_json = [
        {"id": 1, "name": "Fire Explosion"},
        {"id": 2, "name": "Ice Shard"}
    ]
    (www_data / "Animations.json").write_text(json.dumps(animations_json), encoding="utf-8")
    
    # Tilesets.json
    tilesets_json = [
        {"id": 1, "name": "Forest"},
        {"id": 2, "name": "Castle"}
    ]
    (www_data / "Tilesets.json").write_text(json.dumps(tilesets_json), encoding="utf-8")
    
    # CommonEvents.json
    common_events_json = [
        {"id": 1, "name": "Start Game", "list": []},
        {"id": 2, "name": "Victory Fanfare", "list": [
            {"code": 101, "parameters": ["Congratulations!"]},
            {"code": 401, "parameters": ["You defeated the enemy!"]}
        ]}
    ]
    (www_data / "CommonEvents.json").write_text(json.dumps(common_events_json), encoding="utf-8")
    
    # package.json e rpg_core.js
    (tmp_path / "package.json").write_text(json.dumps({"name": "test-mv-game", "dependencies": {"rpg_core": "1.0"}}))
    www_js = tmp_path / "www" / "js"
    www_js.mkdir()
    (www_js / "rpg_core.js").write_text("// RPG Maker MV v1.6.1")
    
    return tmp_path


@pytest.fixture
def mv_map_with_events(tmp_path):
    """Create Map001.json with events, pages, Show Text and Show Choices."""
    www_data = tmp_path / "www" / "data"
    www_data.mkdir(parents=True)
    
    # Map001.json com múltiplos eventos e páginas
    map_json = {
        "displayName": "Starting Town",
        "events": [
            {
                "id": 1,
                "name": "Old Man",
                "pages": [
                    {
                        "list": [
                            {"code": 101, "parameters": ["Welcome, traveler!", 0, 0, 0]},
                            {"code": 401, "parameters": ["This is our village."]},
                            {"code": 401, "parameters": ["Please rest here."]}
                        ]
                    }
                ]
            },
            {
                "id": 2,
                "name": "Shopkeeper",
                "pages": [
                    {
                        "list": [
                            {"code": 101, "parameters": ["Want to buy something?", 0, 0, 0]},
                            {"code": 102, "parameters": [["Yes, please", "No, thanks", "Maybe later"], 1, 0, 2, 0]},
                            {"code": 404, "parameters": []},
                            {"code": 101, "parameters": ["Come back anytime!"]}
                        ]
                    }
                ]
            },
            {
                "id": 3,
                "name": "Guard",
                "pages": [
                    {
                        "list": [
                            {"code": 101, "parameters": ["Halt!", 0, 0, 0]},
                            {"code": 102, "parameters": [["Who are you?", "I'm a hero", "Just passing by"], 1, 0, 3, 0]},
                            {"code": 404, "parameters": []}
                        ]
                    },
                    {
                        "list": [
                            {"code": 101, "parameters": ["You may pass.", 0, 0, 0]}
                        ]
                    }
                ]
            }
        ]
    }
    (www_data / "Map001.json").write_text(json.dumps(map_json), encoding="utf-8")
    
    # Map002.json - outro mapa
    map2_json = {
        "displayName": "Dark Forest",
        "events": [
            {
                "id": 1,
                "name": "Mysterious Tree",
                "pages": [
                    {
                        "list": [
                            {"code": 101, "parameters": ["The tree whispers...", 0, 0, 0]}
                        ]
                    }
                ]
            }
        ]
    }
    (www_data / "Map002.json").write_text(json.dumps(map2_json), encoding="utf-8")
    
    # Arquivos mínimos necessários
    (tmp_path / "package.json").write_text(json.dumps({"name": "test-map-game"}))
    www_js = tmp_path / "www" / "js"
    www_js.mkdir()
    (www_js / "rpg_core.js").write_text("// v1.6.1")
    (www_data / "System.json").write_text(json.dumps({"gameTitle": "Test"}))
    
    return tmp_path


class TestMVDatabaseExtraction:
    """Test extraction from RPG Maker MV database files."""
    
    def test_extract_system_game_title(self, mv_plugin, complete_mv_database):
        """Test extracting game title from System.json."""
        project = Project(path=complete_mv_database, engine="rpgmaker_mv", status=ProjectLoadStatus.LOADED)
        result = mv_plugin.extract_data(project)
        
        game_title_entries = [e for e in result.entries if e.entry_id == "system:game_title"]
        assert len(game_title_entries) == 1
        assert game_title_entries[0].text == "Final Fantasy Test"
        assert game_title_entries[0].source_path == Path("www/data/System.json")
    
    def test_extract_actors(self, mv_plugin, complete_mv_database):
        """Test extracting actor names, nicknames, and profiles."""
        project = Project(path=complete_mv_database, engine="rpgmaker_mv", status=ProjectLoadStatus.LOADED)
        result = mv_plugin.extract_data(project)
        
        actor_entries = [e for e in result.entries if e.metadata.get("source_kind") == "actor"]
        assert len(actor_entries) == 6  # 2 actors * 3 fields each
        
        # Verify specific entries
        texts = {e.text for e in actor_entries}
        assert "Hero" in texts
        assert "The Brave" in texts
        assert "A courageous hero who saved the world." in texts
        assert "Mage" in texts
        assert "The Wise" in texts
    
    def test_extract_classes(self, mv_plugin, complete_mv_database):
        """Test extracting class names."""
        project = Project(path=complete_mv_database, engine="rpgmaker_mv", status=ProjectLoadStatus.LOADED)
        result = mv_plugin.extract_data(project)
        
        class_entries = [e for e in result.entries if e.metadata.get("source_kind") == "classe"]
        assert len(class_entries) == 2
        
        texts = {e.text for e in class_entries}
        assert "Warrior" in texts
        assert "Black Mage" in texts
    
    def test_extract_skills(self, mv_plugin, complete_mv_database):
        """Test extracting skill names, descriptions, and messages."""
        project = Project(path=complete_mv_database, engine="rpgmaker_mv", status=ProjectLoadStatus.LOADED)
        result = mv_plugin.extract_data(project)
        
        skill_entries = [e for e in result.entries if e.metadata.get("source_kind") == "skill"]
        assert len(skill_entries) >= 4  # name, description, message1, message2 (some may be empty)
        
        texts = {e.text for e in skill_entries}
        assert "Fire" in texts
        assert "Deals fire damage to one enemy." in texts
        assert "casts Fire!" in texts or " casts Fire!" in texts
    
    def test_extract_items(self, mv_plugin, complete_mv_database):
        """Test extracting item names and descriptions."""
        project = Project(path=complete_mv_database, engine="rpgmaker_mv", status=ProjectLoadStatus.LOADED)
        result = mv_plugin.extract_data(project)
        
        item_entries = [e for e in result.entries if e.metadata.get("source_kind") == "item"]
        assert len(item_entries) == 4  # 2 items * 2 fields each
        
        texts = {e.text for e in item_entries}
        assert "Potion" in texts
        assert "Restores 50 HP." in texts
        assert "Ether" in texts
    
    def test_extract_weapons(self, mv_plugin, complete_mv_database):
        """Test extracting weapon names and descriptions."""
        project = Project(path=complete_mv_database, engine="rpgmaker_mv", status=ProjectLoadStatus.LOADED)
        result = mv_plugin.extract_data(project)
        
        weapon_entries = [e for e in result.entries if e.metadata.get("source_kind") == "weapon"]
        assert len(weapon_entries) == 4  # 2 weapons * 2 fields each
        
        texts = {e.text for e in weapon_entries}
        assert "Iron Sword" in texts
        assert "A basic sword made of iron." in texts
    
    def test_extract_armors(self, mv_plugin, complete_mv_database):
        """Test extracting armor names and descriptions."""
        project = Project(path=complete_mv_database, engine="rpgmaker_mv", status=ProjectLoadStatus.LOADED)
        result = mv_plugin.extract_data(project)
        
        armor_entries = [e for e in result.entries if e.metadata.get("source_kind") == "armor"]
        assert len(armor_entries) == 4  # 2 armors * 2 fields each
        
        texts = {e.text for e in armor_entries}
        assert "Leather Armor" in texts
        assert "Light armor made of leather." in texts
    
    def test_extract_enemies(self, mv_plugin, complete_mv_database):
        """Test extracting enemy names."""
        project = Project(path=complete_mv_database, engine="rpgmaker_mv", status=ProjectLoadStatus.LOADED)
        result = mv_plugin.extract_data(project)
        
        enemy_entries = [e for e in result.entries if e.metadata.get("source_kind") == "enemie"]
        assert len(enemy_entries) == 3
        
        texts = {e.text for e in enemy_entries}
        assert "Slime" in texts
        assert "Goblin" in texts
        assert "Dragon" in texts
    
    def test_extract_states(self, mv_plugin, complete_mv_database):
        """Test extracting state names and messages."""
        project = Project(path=complete_mv_database, engine="rpgmaker_mv", status=ProjectLoadStatus.LOADED)
        result = mv_plugin.extract_data(project)
        
        state_entries = [e for e in result.entries if e.metadata.get("source_kind") == "state"]
        assert len(state_entries) >= 2  # At least names
        
        texts = {e.text for e in state_entries}
        assert "Poison" in texts
        assert "is poisoned!" in texts or " is poisoned!" in texts
    
    def test_extract_animations(self, mv_plugin, complete_mv_database):
        """Test extracting animation names."""
        project = Project(path=complete_mv_database, engine="rpgmaker_mv", status=ProjectLoadStatus.LOADED)
        result = mv_plugin.extract_data(project)
        
        animation_entries = [e for e in result.entries if e.metadata.get("source_kind") == "animation"]
        assert len(animation_entries) == 2
        
        texts = {e.text for e in animation_entries}
        assert "Fire Explosion" in texts
        assert "Ice Shard" in texts
    
    def test_extract_tilesets(self, mv_plugin, complete_mv_database):
        """Test extracting tileset names."""
        project = Project(path=complete_mv_database, engine="rpgmaker_mv", status=ProjectLoadStatus.LOADED)
        result = mv_plugin.extract_data(project)
        
        tileset_entries = [e for e in result.entries if e.metadata.get("source_kind") == "tileset"]
        assert len(tileset_entries) == 2
        
        texts = {e.text for e in tileset_entries}
        assert "Forest" in texts
        assert "Castle" in texts
    
    def test_extract_common_events(self, mv_plugin, complete_mv_database):
        """Test extracting common event names and commands."""
        project = Project(path=complete_mv_database, engine="rpgmaker_mv", status=ProjectLoadStatus.LOADED)
        result = mv_plugin.extract_data(project)
        
        common_event_entries = [e for e in result.entries if e.metadata.get("source_kind") == "commonEvent"]
        assert len(common_event_entries) >= 3  # 2 names + at least 1 text from Victory Fanfare
        
        texts = {e.text for e in common_event_entries}
        assert "Start Game" in texts
        assert "Victory Fanfare" in texts
        # Text may be joined with newlines
        assert any("Congratulations" in t for t in texts)


class TestMVMapExtraction:
    """Test extraction from RPG Maker MV map files."""
    
    def test_extract_map_display_name(self, mv_plugin, mv_map_with_events):
        """Test extracting map display names."""
        project = Project(path=mv_map_with_events, engine="rpgmaker_mv", status=ProjectLoadStatus.LOADED)
        result = mv_plugin.extract_data(project)
        
        map_name_entries = [e for e in result.entries if "displayName" in e.entry_id]
        assert len(map_name_entries) == 2  # Map001 and Map002
        
        texts = {e.text for e in map_name_entries}
        assert "Starting Town" in texts
        assert "Dark Forest" in texts
    
    def test_extract_event_names(self, mv_plugin, mv_map_with_events):
        """Test extracting event names."""
        project = Project(path=mv_map_with_events, engine="rpgmaker_mv", status=ProjectLoadStatus.LOADED)
        result = mv_plugin.extract_data(project)
        
        event_name_entries = [e for e in result.entries if ":event:" in e.entry_id and ":name" in e.entry_id]
        assert len(event_name_entries) == 4  # 3 events in Map001 + 1 in Map002
        
        texts = {e.text for e in event_name_entries}
        assert "Old Man" in texts
        assert "Shopkeeper" in texts
        assert "Guard" in texts
        assert "Mysterious Tree" in texts
    
    def test_extract_show_text_command_101(self, mv_plugin, mv_map_with_events):
        """Test extracting Show Text (command 101) content."""
        project = Project(path=mv_map_with_events, engine="rpgmaker_mv", status=ProjectLoadStatus.LOADED)
        result = mv_plugin.extract_data(project)
        
        text_entries = [e for e in result.entries if e.metadata.get("command_code") == 101]
        assert len(text_entries) >= 5  # Multiple show text commands across events
        
        texts = {e.text for e in text_entries}
        assert "Welcome, traveler!\nThis is our village.\nPlease rest here." in texts
        assert "Want to buy something?" in texts
        assert "Halt!" in texts
        assert "The tree whispers..." in texts
    
    def test_extract_show_choices_command_102(self, mv_plugin, mv_map_with_events):
        """Test extracting Show Choices (command 102) options."""
        project = Project(path=mv_map_with_events, engine="rpgmaker_mv", status=ProjectLoadStatus.LOADED)
        result = mv_plugin.extract_data(project)
        
        choice_entries = [e for e in result.entries if e.metadata.get("command_code") == 102]
        assert len(choice_entries) == 6  # 3 choices + 3 choices from two command 102 instances
        
        texts = {e.text for e in choice_entries}
        assert "Yes, please" in texts
        assert "No, thanks" in texts
        assert "Maybe later" in texts
        assert "Who are you?" in texts
        assert "I'm a hero" in texts
        assert "Just passing by" in texts
    
    def test_extract_preserves_order(self, mv_plugin, mv_map_with_events):
        """Test that choices preserve their order."""
        project = Project(path=mv_map_with_events, engine="rpgmaker_mv", status=ProjectLoadStatus.LOADED)
        result = mv_plugin.extract_data(project)
        
        # Get choices from first Show Choices command
        shop_choices = [
            e for e in result.entries 
            if e.metadata.get("command_code") == 102 
            and "event:2" in e.entry_id
        ]
        
        # Sort by entry_id to get order
        shop_choices.sort(key=lambda e: e.entry_id)
        
        assert len(shop_choices) == 3
        assert shop_choices[0].text == "Yes, please"
        assert shop_choices[1].text == "No, thanks"
        assert shop_choices[2].text == "Maybe later"
    
    def test_extract_multiple_pages(self, mv_plugin, mv_map_with_events):
        """Test extraction from events with multiple pages."""
        project = Project(path=mv_map_with_events, engine="rpgmaker_mv", status=ProjectLoadStatus.LOADED)
        result = mv_plugin.extract_data(project)
        
        # Guard has 2 pages
        guard_texts = [e for e in result.entries if "event:3" in e.entry_id and e.metadata.get("command_code") == 101]
        assert len(guard_texts) >= 2  # "Halt!" from page 1, "You may pass." from page 2
        
        texts = {e.text for e in guard_texts}
        assert "Halt!" in texts
        assert "You may pass." in texts
    
    def test_extract_metadata_preserved(self, mv_plugin, mv_map_with_events):
        """Test that metadata is correctly preserved."""
        project = Project(path=mv_map_with_events, engine="rpgmaker_mv", status=ProjectLoadStatus.LOADED)
        result = mv_plugin.extract_data(project)
        
        # Find a text entry from Map001, event 1
        old_man_text = next(
            (e for e in result.entries if "Map001" in e.entry_id and "event:1" in e.entry_id and e.metadata.get("command_code") == 101),
            None
        )
        
        assert old_man_text is not None
        assert old_man_text.metadata["map"] == "Map001"
        assert old_man_text.metadata["event_id"] == 1
        assert old_man_text.metadata["page"] == 1
        assert old_man_text.source_path == Path("www/data/Map001.json")


class TestMVEdgeCases:
    """Test edge cases in MV extraction."""
    
    def test_unicode_extraction(self, mv_plugin, tmp_path):
        """Test extraction with Unicode text."""
        www_data = tmp_path / "www" / "data"
        www_data.mkdir(parents=True)
        
        # Japanese text
        actors_json = [{"id": 1, "name": "勇者", "nickname": "光の戦士", "profile": "世界を救う英雄"}]
        (www_data / "Actors.json").write_text(json.dumps(actors_json), encoding="utf-8")
        (www_data / "System.json").write_text(json.dumps({"gameTitle": "テストゲーム"}))
        (tmp_path / "package.json").write_text(json.dumps({"name": "unicode-test"}))
        www_js = tmp_path / "www" / "js"
        www_js.mkdir()
        (www_js / "rpg_core.js").write_text("// v1.6.1")
        
        project = Project(path=tmp_path, engine="rpgmaker_mv", status=ProjectLoadStatus.LOADED)
        result = mv_plugin.extract_data(project)
        
        texts = {e.text for e in result.entries}
        assert "勇者" in texts
        assert "光の戦士" in texts
        assert "テストゲーム" in texts
    
    def test_empty_strings_skipped(self, mv_plugin, tmp_path):
        """Test that empty strings are not extracted."""
        www_data = tmp_path / "www" / "data"
        www_data.mkdir(parents=True)
        
        actors_json = [{"id": 1, "name": "", "nickname": "   ", "profile": "Valid profile"}]
        (www_data / "Actors.json").write_text(json.dumps(actors_json), encoding="utf-8")
        (www_data / "System.json").write_text(json.dumps({"gameTitle": "Test"}))
        (tmp_path / "package.json").write_text(json.dumps({"name": "empty-test"}))
        www_js = tmp_path / "www" / "js"
        www_js.mkdir()
        (www_js / "rpg_core.js").write_text("// v1.6.1")
        
        project = Project(path=tmp_path, engine="rpgmaker_mv", status=ProjectLoadStatus.LOADED)
        result = mv_plugin.extract_data(project)
        
        actor_entries = [e for e in result.entries if e.metadata.get("source_kind") == "actor"]
        # Only profile should be extracted (name and nickname are empty/whitespace)
        assert len(actor_entries) == 1
        assert actor_entries[0].text == "Valid profile"
    
    def test_missing_files_handled(self, mv_plugin, tmp_path):
        """Test handling of missing database files."""
        www_data = tmp_path / "www" / "data"
        www_data.mkdir(parents=True)
        
        # Only System.json exists
        (www_data / "System.json").write_text(json.dumps({"gameTitle": "Minimal"}))
        (tmp_path / "package.json").write_text(json.dumps({"name": "minimal"}))
        www_js = tmp_path / "www" / "js"
        www_js.mkdir()
        (www_js / "rpg_core.js").write_text("// v1.6.1")
        
        project = Project(path=tmp_path, engine="rpgmaker_mv", status=ProjectLoadStatus.LOADED)
        result = mv_plugin.extract_data(project)
        
        # Should not crash, should extract what's available
        assert result.status.value in ("extracted", "partial")
        assert len(result.errors) == 0  # Missing optional files shouldn't cause errors
    
    def test_invalid_json_handled(self, mv_plugin, tmp_path):
        """Test handling of invalid JSON files."""
        www_data = tmp_path / "www" / "data"
        www_data.mkdir(parents=True)
        
        (www_data / "System.json").write_text("{ invalid json }", encoding="utf-8")
        (www_data / "Actors.json").write_text("not json at all", encoding="utf-8")
        (tmp_path / "package.json").write_text(json.dumps({"name": "invalid-test"}))
        www_js = tmp_path / "www" / "js"
        www_js.mkdir()
        (www_js / "rpg_core.js").write_text("// v1.6.1")
        
        project = Project(path=tmp_path, engine="rpgmaker_mv", status=ProjectLoadStatus.LOADED)
        result = mv_plugin.extract_data(project)
        
        # Should have errors but not crash
        assert any(e.code == "invalid_json" for e in result.errors)
    
    def test_map_without_events(self, mv_plugin, tmp_path):
        """Test extraction from map without events."""
        www_data = tmp_path / "www" / "data"
        www_data.mkdir(parents=True)
        
        map_json = {"displayName": "Empty Map", "events": []}
        (www_data / "Map001.json").write_text(json.dumps(map_json), encoding="utf-8")
        (www_data / "System.json").write_text(json.dumps({"gameTitle": "Test"}))
        (tmp_path / "package.json").write_text(json.dumps({"name": "empty-map-test"}))
        www_js = tmp_path / "www" / "js"
        www_js.mkdir()
        (www_js / "rpg_core.js").write_text("// v1.6.1")
        
        project = Project(path=tmp_path, engine="rpgmaker_mv", status=ProjectLoadStatus.LOADED)
        result = mv_plugin.extract_data(project)
        
        # Should extract map name but no events
        map_entries = [e for e in result.entries if "displayName" in e.entry_id]
        assert len(map_entries) == 1
        assert map_entries[0].text == "Empty Map"
    
    def test_event_without_pages(self, mv_plugin, tmp_path):
        """Test extraction from event without pages."""
        www_data = tmp_path / "www" / "data"
        www_data.mkdir(parents=True)
        
        map_json = {"displayName": "Test Map", "events": [{"id": 1, "name": "Empty Event", "pages": []}]}
        (www_data / "Map001.json").write_text(json.dumps(map_json), encoding="utf-8")
        (www_data / "System.json").write_text(json.dumps({"gameTitle": "Test"}))
        (tmp_path / "package.json").write_text(json.dumps({"name": "no-pages-test"}))
        www_js = tmp_path / "www" / "js"
        www_js.mkdir()
        (www_js / "rpg_core.js").write_text("// v1.6.1")
        
        project = Project(path=tmp_path, engine="rpgmaker_mv", status=ProjectLoadStatus.LOADED)
        result = mv_plugin.extract_data(project)
        
        # Should extract event name but no commands
        event_name_entries = [e for e in result.entries if ":event:1:name" in e.entry_id]
        assert len(event_name_entries) == 1
        assert event_name_entries[0].text == "Empty Event"
    
    def test_unknown_command_codes_ignored(self, mv_plugin, tmp_path):
        """Test that unknown command codes don't break extraction."""
        www_data = tmp_path / "www" / "data"
        www_data.mkdir(parents=True)
        
        map_json = {
            "displayName": "Test",
            "events": [{
                "id": 1,
                "name": "Test Event",
                "pages": [{
                    "list": [
                        {"code": 999, "parameters": ["unknown"]},
                        {"code": 101, "parameters": ["Known text", 0, 0, 0]},
                        {"code": 888, "parameters": ["another unknown"]}
                    ]
                }]
            }]
        }
        (www_data / "Map001.json").write_text(json.dumps(map_json), encoding="utf-8")
        (www_data / "System.json").write_text(json.dumps({"gameTitle": "Test"}))
        (tmp_path / "package.json").write_text(json.dumps({"name": "unknown-cmd-test"}))
        www_js = tmp_path / "www" / "js"
        www_js.mkdir()
        (www_js / "rpg_core.js").write_text("// v1.6.1")
        
        project = Project(path=tmp_path, engine="rpgmaker_mv", status=ProjectLoadStatus.LOADED)
        result = mv_plugin.extract_data(project)
        
        # Should extract known text, ignore unknown commands
        text_entries = [e for e in result.entries if e.metadata.get("command_code") == 101]
        assert len(text_entries) == 1
        assert text_entries[0].text == "Known text"


class TestMVDeterminism:
    """Test deterministic extraction behavior."""
    
    def test_extraction_is_deterministic(self, mv_plugin, complete_mv_database):
        """Test that running extraction twice produces identical results."""
        project = Project(path=complete_mv_database, engine="rpgmaker_mv", status=ProjectLoadStatus.LOADED)
        
        # Run extraction twice
        result1 = mv_plugin.extract_data(project)
        result2 = mv_plugin.extract_data(project)
        
        # Same number of entries
        assert len(result1.entries) == len(result2.entries)
        
        # Same entry IDs in same order
        ids1 = [e.entry_id for e in result1.entries]
        ids2 = [e.entry_id for e in result2.entries]
        assert ids1 == ids2
        
        # Same texts
        texts1 = [e.text for e in result1.entries]
        texts2 = [e.text for e in result2.entries]
        assert texts1 == texts2
        
        # Same metadata
        meta1 = [e.metadata for e in result1.entries]
        meta2 = [e.metadata for e in result2.entries]
        assert meta1 == meta2
    
    def test_entry_ids_are_stable(self, mv_plugin, complete_mv_database):
        """Test that entry IDs follow a stable pattern."""
        project = Project(path=complete_mv_database, engine="rpgmaker_mv", status=ProjectLoadStatus.LOADED)
        result = mv_plugin.extract_data(project)
        
        # All entry IDs should be non-empty strings
        for entry in result.entries:
            assert isinstance(entry.entry_id, str)
            assert len(entry.entry_id) > 0
            
            # Entry IDs should contain relevant info
            assert ":" in entry.entry_id  # Should have colon-separated parts
    
    def test_no_random_ids(self, mv_plugin, mv_map_with_events):
        """Test that no random or UUID-based IDs are used."""
        project = Project(path=mv_map_with_events, engine="rpgmaker_mv", status=ProjectLoadStatus.LOADED)
        result = mv_plugin.extract_data(project)
        
        for entry in result.entries:
            # Entry IDs should be based on file/event/command structure, not random
            assert "-" not in entry.entry_id or "Map" in entry.entry_id  # Allow hyphens in map names
            # Should not look like UUIDs
            assert len([c for c in entry.entry_id if c.isdigit()]) < 32 or "event" in entry.entry_id.lower()
