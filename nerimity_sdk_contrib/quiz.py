"""QuizPlugin — channel-based trivia quiz game.

How it works:
  1. ``/quiz start [rounds]`` — starts a quiz in the current channel.
  2. The bot posts a question; players type the answer.
  3. First correct answer wins the round and earns a point.
  4. After all rounds the leaderboard is shown.

Questions are loaded from a JSON file or the built-in sample set.

Usage::

    await bot.plugins.load(QuizPlugin(
        questions_file="quiz.json",   # optional; uses built-ins if omitted
        rounds=5,
        answer_timeout=20.0,
    ))

``quiz.json`` format::

    [
      {"question": "What is 2 + 2?", "answer": "4"},
      {"question": "Capital of France?", "answer": "paris"}
    ]

Answers are compared case-insensitively and with leading/trailing whitespace stripped.
"""
from __future__ import annotations

import asyncio
import json
import os
import random
from typing import Any

from nerimity_sdk.plugins.manager import PluginBase, listener

_BUILTIN_QUESTIONS: list[dict[str, str]] = [
    {"question": "What is the capital of Japan?", "answer": "tokyo"},
    {"question": "How many sides does a hexagon have?", "answer": "6"},
    {"question": "What planet is known as the Red Planet?", "answer": "mars"},
    {"question": "What is 12 × 12?", "answer": "144"},
    {"question": "Who wrote Romeo and Juliet?", "answer": "shakespeare"},
    {"question": "What is the chemical symbol for water?", "answer": "h2o"},
    {"question": "How many continents are there?", "answer": "7"},
    {"question": "What is the fastest land animal?", "answer": "cheetah"},
    {"question": "What year did World War II end?", "answer": "1945"},
    {"question": "What is the square root of 144?", "answer": "12"},
]


class QuizPlugin(PluginBase):
    """Trivia quiz game for a channel."""
    name = "quiz"

    def __init__(
        self,
        questions_file: str | None = None,
        rounds: int = 5,
        answer_timeout: float = 20.0,
    ) -> None:
        super().__init__()
        self.default_rounds = rounds
        self.answer_timeout = answer_timeout
        self._questions: list[dict[str, str]] = []
        self._questions_file = questions_file
        # channel_id → active quiz state
        self._active: dict[str, dict[str, Any]] = {}

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def on_load(self) -> None:
        self._questions = self._load_questions()
        plugin = self

        @self.bot.command("quiz", description="Start a trivia quiz")
        async def quiz_cmd(ctx) -> None:
            if not ctx.server_id:
                return await ctx.reply("❌ Quiz only works in a server channel.")
            if ctx.channel_id in plugin._active:
                return await ctx.reply("⚠️ A quiz is already running in this channel!")

            rounds = int(ctx.args[0]) if ctx.args else plugin.default_rounds
            rounds = max(1, min(rounds, 20))
            await plugin._run_quiz(ctx.channel_id, rounds)

        @self.bot.command("quizstop", description="Stop the running quiz")
        async def quizstop_cmd(ctx) -> None:
            state = plugin._active.get(ctx.channel_id)
            if not state:
                return await ctx.reply("No quiz is running here.")
            state["stopped"] = True
            await ctx.reply("🛑 Quiz stopped.")

    # ── Quiz runner ───────────────────────────────────────────────────────────

    async def _run_quiz(self, channel_id: str, rounds: int) -> None:
        questions = random.sample(self._questions, min(rounds, len(self._questions)))
        scores: dict[str, int] = {}
        state: dict[str, Any] = {"stopped": False, "answer": None, "winner": None}
        self._active[channel_id] = state

        await self.bot.rest.create_message(
            channel_id,
            f"🎉 **Quiz starting!** {len(questions)} rounds — {self.answer_timeout:.0f}s per question."
        )
        await asyncio.sleep(2)

        try:
            for i, q in enumerate(questions, 1):
                if state["stopped"]:
                    break
                state["answer"] = q["answer"].strip().lower()
                state["winner"] = None

                await self.bot.rest.create_message(
                    channel_id,
                    f"**Question {i}/{len(questions)}:** {q['question']}"
                )

                try:
                    await asyncio.wait_for(
                        self._wait_for_answer(state),
                        timeout=self.answer_timeout,
                    )
                except asyncio.TimeoutError:
                    await self.bot.rest.create_message(
                        channel_id,
                        f"⏰ Time's up! The answer was **{q['answer']}**."
                    )
                else:
                    winner = state["winner"]
                    if winner:
                        scores[winner] = scores.get(winner, 0) + 1
                        user = self.bot.cache.users.get(winner)
                        name = user.username if user else winner
                        await self.bot.rest.create_message(
                            channel_id,
                            f"✅ **{name}** got it! The answer was **{q['answer']}**. "
                            f"(+1 point, total: {scores[winner]})"
                        )

                await asyncio.sleep(2)
        finally:
            del self._active[channel_id]

        if not scores:
            await self.bot.rest.create_message(channel_id, "😢 Nobody scored any points!")
            return

        sorted_scores = sorted(scores.items(), key=lambda x: -x[1])
        lines = ["🏆 **Quiz Over! Final Scores:**"]
        medals = ["🥇", "🥈", "🥉"]
        for idx, (uid, pts) in enumerate(sorted_scores):
            user = self.bot.cache.users.get(uid)
            name = user.username if user else uid
            medal = medals[idx] if idx < 3 else f"#{idx+1}"
            lines.append(f"{medal} **{name}** — {pts} point{'s' if pts != 1 else ''}")
        await self.bot.rest.create_message(channel_id, "\n".join(lines))

    async def _wait_for_answer(self, state: dict[str, Any]) -> None:
        """Spin until state['winner'] is set by the message listener."""
        while state["winner"] is None and not state["stopped"]:
            await asyncio.sleep(0.1)

    # ── Message listener ──────────────────────────────────────────────────────

    @listener("message:created")
    async def on_message(self, event) -> None:
        from nerimity_sdk.events.payloads import MessageCreatedEvent
        if not isinstance(event, MessageCreatedEvent):
            return
        msg = event.message
        state = self._active.get(msg.channel_id)
        if not state or state["winner"] is not None:
            return
        if self.bot._me and msg.created_by.id == self.bot._me.id:
            return
        if (msg.content or "").strip().lower() == state["answer"]:
            state["winner"] = msg.created_by.id

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _load_questions(self) -> list[dict[str, str]]:
        if self._questions_file and os.path.isfile(self._questions_file):
            with open(self._questions_file, encoding="utf-8") as fh:
                return json.load(fh)
        return list(_BUILTIN_QUESTIONS)
