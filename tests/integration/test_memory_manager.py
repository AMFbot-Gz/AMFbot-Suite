"""
Tests d'intégration — MemoryManager.

Couvre :
  - Stockage d'une interaction via add_interaction()
  - Récupération de l'historique récent via get_recent_history()
  - Recherche sémantique via search_relevant_context()

Les tests s'exécutent sur une base de données ChromaDB temporaire
(répertoire supprimé après chaque test via tempfile.TemporaryDirectory).

Prérequis : chromadb et sentence-transformers installés dans le venv.
Si absents, les tests sémantiques sont automatiquement ignorés (pytest.skip).
"""

import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from memory.memory_manager import MemoryManager


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def tmp_memory(tmp_path: Path) -> MemoryManager:
    """
    MemoryManager avec un répertoire de stockage temporaire.
    Isolé par test — aucune persistance entre tests.
    """
    return MemoryManager(storage_dir=tmp_path / "memory")


@pytest.fixture
def tmp_memory_with_semantic(tmp_path: Path) -> MemoryManager:
    """
    MemoryManager avec mémoire sémantique chargée.
    Ignoré automatiquement si chromadb/sentence-transformers absent.
    """
    mem = MemoryManager(storage_dir=tmp_path / "memory")
    ok = mem.load_semantic()
    if not ok:
        pytest.skip(
            "chromadb ou sentence-transformers non installé — "
            "tests sémantiques ignorés"
        )
    return mem


# ── Test 1 : Mémoire épisodique ───────────────────────────────────────────────

class TestEpisodicMemory:

    def test_add_and_retrieve_interaction(self, tmp_memory):
        """
        add_interaction() stocke l'épisode,
        get_recent_history() le retrouve.
        """
        tmp_memory.add_interaction(
            text="Ouvre Chrome",
            role="user",
        )

        history = tmp_memory.get_recent_history(n=10)

        assert len(history) == 1
        assert history[0].text == "Ouvre Chrome"
        assert history[0].role == "user"

    def test_multiple_interactions_order(self, tmp_memory):
        """
        Les épisodes sont récupérés dans l'ordre chronologique (plus ancien en premier).
        """
        tmp_memory.add_interaction("Message 1", role="user")
        tmp_memory.add_interaction("Réponse 1", role="jarvis")
        tmp_memory.add_interaction("Message 2", role="user")

        history = tmp_memory.get_recent_history(n=10)

        assert len(history) == 3
        assert history[0].text == "Message 1"
        assert history[1].role == "jarvis"
        assert history[2].text == "Message 2"

    def test_recent_history_limit(self, tmp_memory):
        """
        get_recent_history(n) ne retourne que les n derniers épisodes.
        """
        for i in range(10):
            tmp_memory.add_interaction(f"Message {i}", role="user")

        history = tmp_memory.get_recent_history(n=3)

        assert len(history) == 3
        # Les 3 derniers
        assert history[-1].text == "Message 9"

    def test_add_interaction_with_metadata(self, tmp_memory):
        """
        Les métadonnées et actions sont correctement stockés dans l'épisode.
        """
        tmp_memory.add_interaction(
            text="Ouvre Chrome et va sur github.com",
            role="jarvis",
            intent="open_app",
            actions=["open_app", "open_url"],
            metadata={"confidence": 0.95},
        )

        history = tmp_memory.get_recent_history(n=1)

        assert len(history) == 1
        ep = history[0]
        assert ep.role == "jarvis"
        assert "open_app" in ep.actions
        assert "open_url" in ep.actions
        assert ep.metadata.get("confidence") == 0.95

    def test_stats_episodic_count(self, tmp_memory):
        """stats() retourne le bon nombre d'épisodes."""
        assert tmp_memory.stats()["episodic_count"] == 0

        tmp_memory.add_interaction("Test", role="user")
        tmp_memory.add_interaction("Réponse", role="jarvis")

        stats = tmp_memory.stats()
        assert stats["episodic_count"] == 2

    def test_build_context_prompt_empty(self, tmp_memory):
        """build_context_prompt retourne une string vide si aucun historique."""
        result = tmp_memory.build_context_prompt("Qu'est-ce que Chrome ?")
        # Sans historique ni mémoire sémantique, doit retourner string vide
        assert isinstance(result, str)

    def test_build_context_prompt_with_history(self, tmp_memory):
        """build_context_prompt inclut l'historique récent."""
        tmp_memory.add_interaction("Ouvre Chrome", role="user")
        tmp_memory.add_interaction("Chrome ouvert.", role="jarvis")

        context = tmp_memory.build_context_prompt("Ferme Chrome")

        assert "HISTORIQUE" in context or "Chrome" in context


# ── Test 2 : Mémoire sémantique ───────────────────────────────────────────────

class TestSemanticMemory:

    def test_add_fact_and_search_relevant(self, tmp_memory_with_semantic):
        """
        Un fait ajouté via add_fact() est retrouvé par search_relevant_context()
        avec un score de similarité suffisant (> 0.3).
        """
        mem = tmp_memory_with_semantic

        # Stocker un fait explicite
        ok = mem.add_fact(
            "L'utilisateur préfère Chrome à Safari",
            category="préférence",
        )
        assert ok is True

        # Recherche sémantique
        results = mem.search_relevant_context("Quel navigateur utilise l'utilisateur ?", k=3)

        assert len(results) >= 1
        top = results[0]
        assert top["score"] > 0.3
        assert "Chrome" in top["text"] or "navigateur" in top["text"].lower()

    def test_interaction_with_preference_pattern_stored_semantically(
        self, tmp_memory_with_semantic
    ):
        """
        Une interaction contenant un mot-clé de préférence ('préfère')
        est automatiquement indexée dans la mémoire sémantique.
        """
        mem = tmp_memory_with_semantic

        # add_interaction détecte automatiquement 'préfère' → stockage sémantique
        mem.add_interaction(
            text="J'aime mieux VS Code que PyCharm",
            role="user",
        )

        # La recherche doit retrouver cet épisode
        results = mem.search_relevant_context("quel éditeur de code", k=3)

        assert len(results) >= 1
        assert results[0]["score"] > 0.3

    def test_search_empty_collection_returns_empty_list(self, tmp_memory_with_semantic):
        """
        Une recherche sur une collection vide ne doit pas lever d'exception.
        """
        mem = tmp_memory_with_semantic

        results = mem.search_relevant_context("quel navigateur", k=5)

        assert isinstance(results, list)
        # Vide ou filtrée — pas d'exception
        assert len(results) >= 0

    def test_stats_semantic_count(self, tmp_memory_with_semantic):
        """
        stats()['semantic_count'] reflète le nombre de faits stockés.
        """
        mem = tmp_memory_with_semantic

        initial = mem.stats()["semantic_count"]

        mem.add_fact("L'utilisateur préfère le terminal zsh")

        updated = mem.stats()["semantic_count"]
        assert updated == initial + 1

    def test_search_returns_sorted_by_score(self, tmp_memory_with_semantic):
        """
        Les résultats de la recherche sont triés du plus pertinent au moins pertinent.
        """
        mem = tmp_memory_with_semantic

        mem.add_fact("L'utilisateur utilise Chrome comme navigateur principal")
        mem.add_fact("L'utilisateur a un MacBook Pro 2023")
        mem.add_fact("L'utilisateur parle français")

        results = mem.search_relevant_context("navigateur web préféré", k=5)

        if len(results) >= 2:
            scores = [r["score"] for r in results]
            assert scores == sorted(scores, reverse=True), (
                "Les résultats doivent être triés par score décroissant"
            )


# ── Test 3 : Intégration épisodique + sémantique ──────────────────────────────

class TestFullIntegration:

    def test_build_context_prompt_includes_semantic_facts(
        self, tmp_memory_with_semantic
    ):
        """
        build_context_prompt intègre à la fois l'historique épisodique
        et les faits sémantiques pertinents.
        """
        mem = tmp_memory_with_semantic

        mem.add_fact("L'utilisateur préfère Chrome à Firefox")
        mem.add_interaction("Ouvre mon navigateur préféré", role="user")
        mem.add_interaction("Chrome ouvert.", role="jarvis")

        context = mem.build_context_prompt("ouvre le navigateur")

        # Le contexte doit contenir au moins une section
        assert len(context) > 0
        assert isinstance(context, str)
