"""Deterministic scripted provider for staged-authoring tests and fixtures.

This is the injected fake model demanded by the go-forward plan: it answers
every schedule job from the request context alone, with policy-clean template
prose, so executor runs are reproducible byte-for-byte without a GPU.  It is
not a creative model and must never be wired into a production render; the
first real Lab story runs through an actual local or cloud provider.
"""

from __future__ import annotations

from typing import Any

from .authoring_executor import ModelJobRequest


_ARC_MOVES = (
    "a discovery is made and its cost is glimpsed",
    "the cost is argued and loyalties strain",
    "a choice is made that cannot be unmade",
    "the wider world answers the choice",
    "what remains is named and accepted",
)
_EXIT_MOVES = (
    "the discovery named aloud for the first time",
    "the cost of speaking laid on the table",
    "a decision made that cannot be recalled",
    "the outside world pressing on the choice",
    "the consequence accepted in plain words",
)
_BEAT_MOVES = (
    "the situation sharpens",
    "a hidden detail surfaces",
    "the stakes are said aloud",
    "an objection lands",
    "a small choice closes a door",
    "the pressure rises",
    "an exit is glimpsed",
)
_DIALOGUE_TEXTS = (
    "I checked the figures twice tonight, and the answer refuses to change.",
    "Then tell me plainly, because the plain version is the one people "
    "deserve.",
    "The map on this desk is a promise of smoke, and the wind will keep it.",
    "If we sit on this until morning, the morning will arrive without us.",
    "I want one more reading before anything leaves this room.",
    "One more reading will only tell us what we already know.",
    "Every number here is a street where somebody has to breathe.",
    "Then we carry it together, and we carry it tonight.",
)


class ScriptedStoryProvider:
    """Answer every authoring job deterministically from its context."""

    def run_job(self, request: ModelJobRequest) -> dict[str, Any]:
        handlers = {
            "story_seed": self._story_seed,
            "story_arc": self._story_arc,
            "act_spine": self._act_spine,
            "act_beats": self._act_beats,
            "act_dialogue": self._act_dialogue,
            "act_cleanup": self._act_cleanup,
            "announcer_open": self._announcer_open,
            "announcer_news_coda": self._announcer_news_coda,
        }
        return handlers[request.kind](request.context)

    def _story_seed(self, context: dict[str, Any]) -> dict[str, Any]:
        return {
            "episode_title": "The Cartographer of Smoke",
            "story_seed": (
                "Two colleagues discover that tonight's data maps "
                "tomorrow's danger, and must decide who hears it first."
            ),
        }

    def _story_arc(self, context: dict[str, Any]) -> dict[str, Any]:
        act_count = context["act_count"]
        return {
            "summary": (
                "A discovery is shared, its cost is argued, and a choice "
                "is made before the night ends."
            ),
            "act_premises": [
                f"Act {act_number}: "
                f"{_ARC_MOVES[(act_number - 1) % len(_ARC_MOVES)]}"
                for act_number in range(1, act_count + 1)
            ],
        }

    def _act_spine(self, context: dict[str, Any]) -> dict[str, Any]:
        act_number = context["act_number"]
        premise = context["story_arc"]["act_premises"][act_number - 1]
        entry_state = context.get(
            "prior_act_exit_state",
            "The drama opens with the discovery still private.",
        )
        return {
            "spine": f"{premise}.",
            "entry_state": entry_state,
            "exit_state": (
                f"Act {act_number} ends with "
                f"{_EXIT_MOVES[(act_number - 1) % len(_EXIT_MOVES)]}."
            ),
        }

    def _act_beats(self, context: dict[str, Any]) -> dict[str, Any]:
        act_number = context["act_number"]
        beat_count = context["guidance"]["beats_per_act"][0]
        return {
            "beat_intents": [
                f"Act {act_number}, beat {index}: "
                f"{_BEAT_MOVES[(index - 1) % len(_BEAT_MOVES)]}."
                for index in range(1, beat_count + 1)
            ]
        }

    def _act_dialogue(self, context: dict[str, Any]) -> dict[str, Any]:
        act_number = context["act_number"]
        # A scripted two-hander: the first two locked characters carry the
        # drama, so any additional locked character exercises the cast sweep.
        character_ids = [
            row["char_id"]
            for row in context["locked_cast"]
            if row["cast_role"] == "character"
        ][:2]
        beats = context["beats"]
        assigned_fact_ids = list(context["assigned_fact_ids"])
        rows: list[dict[str, Any]] = []
        line_counter = 0
        for beat_index, beat in enumerate(beats):
            for _ in range(2):
                text = _DIALOGUE_TEXTS[
                    (act_number + line_counter) % len(_DIALOGUE_TEXTS)
                ]
                rows.append(
                    {
                        "role": "character_dialogue",
                        "beat_id": beat["beat_id"],
                        "char_id": character_ids[
                            line_counter % len(character_ids)
                        ],
                        "text": text,
                        "fact_ids": (
                            assigned_fact_ids if line_counter == 0 else []
                        ),
                    }
                )
                line_counter += 1
            if (
                act_number == 2
                and beat_index == 0
                and len(beats) > 1
            ):
                rows.append(
                    {
                        "role": "music_inter",
                        "description": (
                            "A short transition as the argument turns."
                        ),
                        "generation_prompt": (
                            "Brief thoughtful vintage radio transition."
                        ),
                    }
                )
        return {"rows": rows}

    def _act_cleanup(self, context: dict[str, Any]) -> dict[str, Any]:
        """Return the draft unchanged: scripted rows are already speakable.

        A real cleanup model rewrites unspeakable rows here.  The scripted
        provider writes clean dialogue to begin with, so the honest scripted
        answer is a pass-through, which also proves the pass never mangles an
        already-valid act.
        """

        return {
            "rows": [
                {
                    "role": "character_dialogue",
                    "beat_id": row["beat_id"],
                    "char_id": row["char_id"],
                    "text": row["text"],
                    "fact_ids": list(row.get("fact_ids", ())),
                }
                if "beat_id" in row
                else {
                    "role": "music_inter",
                    "description": row["description"],
                    "generation_prompt": row["generation_prompt"],
                }
                for row in context["draft_rows"]
            ]
        }

    def _announcer_open(self, context: dict[str, Any]) -> dict[str, Any]:
        names = [
            row["name"]
            for row in context["final_cast"]
            if row["cast_role"] == "character"
        ]
        return {
            "text": (
                f"It's {context['scene_time']} at {context['setting']}. "
                f"Tonight's story, {context['episode_title']}, finds "
                f"{' and '.join(names)} with one discovery between them."
            )
        }

    def _announcer_news_coda(self, context: dict[str, Any]) -> dict[str, Any]:
        return {
            # Lane-neutral on purpose: this fake writer serves every bank, and
            # "the news is real" is a news phrase that leaked into Shakespeare
            # and archive codas. A real model writes a bridge specific to its
            # own tale; this one must at least not lie about the lane.
            "text": (
                "The record behind tonight's drama: "
                f"{context['closing_fact_claim']}"
            ),
            "fact_id": context["closing_fact_id"],
        }


__all__ = ["ScriptedStoryProvider"]
