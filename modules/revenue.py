"""
Revenue Strategy Module
-----------------------
Provides structured, simulation-safe revenue opportunity analysis.

This module does not move money, create accounts, publish content,
send messages, purchase advertising, or perform other consequential
external actions.
"""

from datetime import datetime
from typing import Any, Dict, List


class RevenueStrategy:
    """
    Generates and evaluates potential revenue experiments.

    All outputs are proposals or simulations. Execution of any
    consequential external action must happen through the central
    approval-controlled ToolRegistry.
    """

    CATEGORIES = [
        "digital_services",
        "content",
        "affiliate",
        "software",
        "marketplace",
        "research",
        "automation",
        "data_products",
    ]

    def __init__(self, economy=None, memory=None):
        self.economy = economy
        self.memory = memory

    def generate_ideas(
        self,
        category: str = "",
        budget: float = 0.0,
        skill_level: str = "general",
    ) -> Dict[str, Any]:
        category = (category or "").strip().lower()
        skill_level = (skill_level or "general").strip().lower()

        if category and category not in self.CATEGORIES:
            return {
                "status": "error",
                "message": f"Unknown revenue category: {category}",
                "valid_categories": self.CATEGORIES,
            }

        ideas = self._idea_catalog()

        if category:
            ideas = [
                idea
                for idea in ideas
                if idea["category"] == category
            ]

        ideas = [
            idea
            for idea in ideas
            if idea["minimum_budget"] <= max(0.0, budget)
        ]

        if not ideas:
            return {
                "status": "success",
                "category": category or "all",
                "budget": budget,
                "ideas": [],
                "message": (
                    "No ideas matched the supplied constraints."
                ),
            }

        for idea in ideas:
            idea["fit_score"] = self._fit_score(
                idea,
                skill_level,
            )

        ideas.sort(
            key=lambda item: item["fit_score"],
            reverse=True,
        )

        return {
            "status": "success",
            "category": category or "all",
            "budget": budget,
            "skill_level": skill_level,
            "ideas": ideas,
        }

    def score_idea(
        self,
        name: str,
        demand: float,
        competition: float,
        startup_cost: float,
        time_to_test_days: float,
        margin: float,
        automation: float,
        legal_complexity: float = 1.0,
    ) -> Dict[str, Any]:
        """
        Score an opportunity using a simple transparent model.

        Inputs are expected on a 0-10 scale except costs and days.
        Higher competition and legal complexity reduce the score.
        """

        try:
            demand = self._bounded(demand)
            competition = self._bounded(competition)
            margin = self._bounded(margin)
            automation = self._bounded(automation)
            legal_complexity = self._bounded(
                legal_complexity
            )
            startup_cost = max(0.0, float(startup_cost))
            time_to_test_days = max(
                0.0,
                float(time_to_test_days),
            )
        except (TypeError, ValueError):
            return {
                "status": "error",
                "message": (
                    "Opportunity scoring values must be numeric."
                ),
            }

        cost_score = max(
            0.0,
            10.0 - min(startup_cost / 10.0, 10.0),
        )

        speed_score = max(
            0.0,
            10.0 - min(time_to_test_days / 3.0, 10.0),
        )

        competition_score = 10.0 - competition
        legal_score = 10.0 - legal_complexity

        total = (
            demand * 0.25
            + competition_score * 0.15
            + cost_score * 0.10
            + speed_score * 0.10
            + margin * 0.20
            + automation * 0.10
            + legal_score * 0.10
        )

        total = round(
            min(10.0, max(0.0, total)),
            2,
        )

        if total >= 8:
            rating = "high"
        elif total >= 6:
            rating = "promising"
        elif total >= 4:
            rating = "experimental"
        else:
            rating = "weak"

        return {
            "status": "success",
            "name": name,
            "score": total,
            "rating": rating,
            "factors": {
                "demand": demand,
                "competition": competition,
                "startup_cost": startup_cost,
                "time_to_test_days": time_to_test_days,
                "margin": margin,
                "automation": automation,
                "legal_complexity": legal_complexity,
            },
        }

    def create_test_plan(
        self,
        idea: str,
        budget: float = 0.0,
        duration_days: int = 7,
    ) -> Dict[str, Any]:
        """
        Create a small validation experiment.

        The plan is only a proposal. It does not execute external
        actions.
        """

        idea = (idea or "").strip()

        if not idea:
            return {
                "status": "error",
                "message": "Idea is required.",
            }

        try:
            budget = max(0.0, float(budget))
        except (TypeError, ValueError):
            return {
                "status": "error",
                "message": "Budget must be numeric.",
            }

        try:
            duration_days = max(
                1,
                min(int(duration_days), 90),
            )
        except (TypeError, ValueError):
            duration_days = 7

        plan = {
            "id": self._experiment_id(idea),
            "idea": idea,
            "budget": budget,
            "duration_days": duration_days,
            "objective": (
                "Validate demand before committing significant "
                "resources."
            ),
            "steps": [
                {
                    "step": 1,
                    "action": "Define target customer",
                    "type": "research",
                },
                {
                    "step": 2,
                    "action": "Research existing competitors",
                    "type": "research",
                },
                {
                    "step": 3,
                    "action": "Define a minimal offer",
                    "type": "planning",
                },
                {
                    "step": 4,
                    "action": "Identify an allowed validation channel",
                    "type": "planning",
                },
                {
                    "step": 5,
                    "action": "Measure interest",
                    "type": "measurement",
                },
                {
                    "step": 6,
                    "action": "Review results",
                    "type": "analysis",
                },
            ],
            "success_metrics": [
                "Evidence of genuine demand",
                "Cost to acquire a prospect",
                "Conversion or response rate",
                "Estimated gross margin",
                "Time required per customer",
                "Repeatability",
            ],
            "created_at": datetime.utcnow().isoformat(),
            "status": "proposed",
            "requires_creator_approval": True,
        }

        if self.memory is not None:
            self.memory.log(
                "RevenueStrategy",
                f"Created test plan: {idea}",
            )

        return {
            "status": "success",
            "plan": plan,
        }

    def rank_opportunities(
        self,
        opportunities: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        if not isinstance(opportunities, list):
            return {
                "status": "error",
                "message": "Opportunities must be a list.",
            }

        ranked = []

        for opportunity in opportunities:
            if not isinstance(opportunity, dict):
                continue

            score = self._opportunity_score(
                opportunity
            )

            item = dict(opportunity)
            item["strategy_score"] = score
            ranked.append(item)

        ranked.sort(
            key=lambda item: item["strategy_score"],
            reverse=True,
        )

        return {
            "status": "success",
            "count": len(ranked),
            "opportunities": ranked,
        }

    def _opportunity_score(
        self,
        opportunity: Dict[str, Any],
    ) -> float:
        demand = self._bounded(
            opportunity.get("demand", 5)
        )

        margin = self._bounded(
            opportunity.get("margin", 5)
        )

        automation = self._bounded(
            opportunity.get("automation", 5)
        )

        competition = self._bounded(
            opportunity.get("competition", 5)
        )

        risk = self._bounded(
            opportunity.get("risk", 5)
        )

        return round(
            max(
                0.0,
                min(
                    10.0,
                    demand * 0.30
                    + margin * 0.25
                    + automation * 0.20
                    + (10.0 - competition) * 0.10
                    + (10.0 - risk) * 0.15,
                ),
            ),
            2,
        )

    def _fit_score(
        self,
        idea: Dict[str, Any],
        skill_level: str,
    ) -> float:
        score = float(
            idea.get("base_score", 5.0)
        )

        required = str(
            idea.get("skill_level", "general")
        ).lower()

        if required == skill_level:
            score += 1.0

        if skill_level in {
            "advanced",
            "technical",
            "developer",
        }:
            if required in {
                "technical",
                "advanced",
            }:
                score += 0.5

        return round(
            min(10.0, score),
            2,
        )

    @staticmethod
    def _bounded(value: Any) -> float:
        value = float(value)
        return min(10.0, max(0.0, value))

    @staticmethod
    def _experiment_id(idea: str) -> str:
        timestamp = datetime.utcnow().strftime(
            "%Y%m%d%H%M%S"
        )

        slug = "".join(
            character
            if character.isalnum()
            else "-"
            for character in idea.lower()
        )

        slug = "-".join(
            part
            for part in slug.split("-")
            if part
        )

        return f"rev-{timestamp}-{slug[:30]}"

    @staticmethod
    def _idea_catalog() -> List[Dict[str, Any]]:
        return [
            {
                "name": "Small-business automation service",
                "category": "automation",
                "minimum_budget": 0.0,
                "skill_level": "technical",
                "base_score": 8.2,
                "model": "service",
                "description": (
                    "Build narrowly scoped automation workflows "
                    "for small businesses."
                ),
            },
            {
                "name": "Research briefing service",
                "category": "research",
                "minimum_budget": 0.0,
                "skill_level": "general",
                "base_score": 7.5,
                "model": "service",
                "description": (
                    "Produce structured research and competitive "
                    "briefings for clients."
                ),
            },
            {
                "name": "Niche digital information product",
                "category": "data_products",
                "minimum_budget": 0.0,
                "skill_level": "general",
                "base_score": 7.3,
                "model": "digital_product",
                "description": (
                    "Package useful original research into a "
                    "focused digital product."
                ),
            },
            {
                "name": "Micro SaaS utility",
                "category": "software",
                "minimum_budget": 20.0,
                "skill_level": "technical",
                "base_score": 8.0,
                "model": "subscription",
                "description": (
                    "Build a narrowly defined software utility "
                    "solving one recurring problem."
                ),
            },
            {
                "name": "Content research pipeline",
                "category": "content",
                "minimum_budget": 0.0,
                "skill_level": "general",
                "base_score": 6.9,
                "model": "content",
                "description": (
                    "Research topics and prepare factual content "
                    "ideas for an approved publishing workflow."
                ),
            },
            {
                "name": "Affiliate comparison research",
                "category": "affiliate",
                "minimum_budget": 0.0,
                "skill_level": "general",
                "base_score": 6.7,
                "model": "affiliate",
                "description": (
                    "Research useful product categories and build "
                    "transparent comparison resources."
                ),
            },
            {
                "name": "Marketplace digital service",
                "category": "marketplace",
                "minimum_budget": 0.0,
                "skill_level": "general",
                "base_score": 7.1,
                "model": "service",
                "description": (
                    "Offer a clearly defined digital service "
                    "through an approved marketplace."
                ),
            },
            {
                "name": "Custom data dashboard",
                "category": "data_products",
                "minimum_budget": 0.0,
                "skill_level": "technical",
                "base_score": 7.8,
                "model": "service",
                "description": (
                    "Build dashboards that turn public or "
                    "customer-provided data into useful insight."
                ),
            },
        ]
