"""
Social Strategy Module
----------------------
Plans and validates social-media activities without directly
publishing, messaging, following, liking, commenting, or creating
accounts.

Any consequential social-media action must be executed later through
an approval-controlled integration.
"""

from datetime import datetime
from typing import Any, Dict, List


class SocialStrategy:
    """
    Creates safe social-media plans and content proposals.

    This module is deliberately non-executing. It does not contain
    credentials, login automation, scraping of private accounts, or
    direct social-media publishing.
    """

    PLATFORMS = {
        "instagram",
        "facebook",
        "x",
        "twitter",
        "linkedin",
        "youtube",
        "tiktok",
        "reddit",
        "threads",
    }

    CONTENT_TYPES = {
        "post",
        "caption",
        "thread",
        "video",
        "short",
        "article",
        "comment",
        "announcement",
    }

    def __init__(self, memory=None):
        self.memory = memory

    def create_content_plan(
        self,
        platform: str,
        topic: str,
        content_type: str = "post",
        objective: str = "audience_growth",
        audience: str = "general",
    ) -> Dict[str, Any]:
        platform = self._normalise_platform(platform)
        content_type = (
            content_type or "post"
        ).strip().lower()

        topic = (topic or "").strip()
        objective = (objective or "audience_growth").strip()
        audience = (audience or "general").strip()

        if platform not in self.PLATFORMS:
            return {
                "status": "error",
                "message": f"Unsupported platform: {platform}",
                "supported_platforms": sorted(
                    self.PLATFORMS
                ),
            }

        if content_type not in self.CONTENT_TYPES:
            return {
                "status": "error",
                "message": (
                    f"Unsupported content type: {content_type}"
                ),
                "supported_content_types": sorted(
                    self.CONTENT_TYPES
                ),
            }

        if not topic:
            return {
                "status": "error",
                "message": "Topic is required.",
            }

        plan = {
            "id": self._make_id(
                platform,
                topic,
            ),
            "platform": platform,
            "topic": topic,
            "content_type": content_type,
            "objective": objective,
            "audience": audience,
            "created_at": datetime.utcnow().isoformat(),
            "status": "proposed",
            "steps": [
                {
                    "step": 1,
                    "action": "Research topic",
                    "type": "research",
                },
                {
                    "step": 2,
                    "action": "Identify audience needs",
                    "type": "analysis",
                },
                {
                    "step": 3,
                    "action": "Draft content",
                    "type": "creation",
                },
                {
                    "step": 4,
                    "action": "Review factual accuracy",
                    "type": "quality_control",
                },
                {
                    "step": 5,
                    "action": "Prepare platform-specific version",
                    "type": "adaptation",
                },
                {
                    "step": 6,
                    "action": (
                        "Submit publishing action for Creator approval"
                    ),
                    "type": "approval",
                },
            ],
            "success_metrics": [
                "Relevant audience reached",
                "Genuine engagement",
                "Qualified traffic",
                "Conversions where applicable",
                "No policy violations",
            ],
            "safety": {
                "direct_publishing": False,
                "direct_messaging": False,
                "automated_following": False,
                "automated_liking": False,
                "automated_commenting": False,
                "account_creation": False,
                "creator_approval_required_for_external_action": True,
            },
        }

        if self.memory is not None:
            self.memory.log(
                "SocialStrategy",
                (
                    f"Created social content plan for "
                    f"{platform}: {topic}"
                ),
            )

        return {
            "status": "success",
            "plan": plan,
        }

    def create_draft(
        self,
        platform: str,
        topic: str,
        key_points: List[str] = None,
        call_to_action: str = "",
    ) -> Dict[str, Any]:
        platform = self._normalise_platform(platform)
        topic = (topic or "").strip()

        if platform not in self.PLATFORMS:
            return {
                "status": "error",
                "message": f"Unsupported platform: {platform}",
            }

        if not topic:
            return {
                "status": "error",
                "message": "Topic is required.",
            }

        if key_points is None:
            key_points = []

        if not isinstance(key_points, list):
            return {
                "status": "error",
                "message": "key_points must be a list.",
            }

        clean_points = [
            str(point).strip()
            for point in key_points
            if str(point).strip()
        ]

        lines = [
            f"Topic: {topic}",
            "",
            "Key points:",
        ]

        if clean_points:
            lines.extend(
                f"- {point}"
                for point in clean_points
            )
        else:
            lines.append(
                "- Add verified supporting information."
            )

        if call_to_action.strip():
            lines.extend(
                [
                    "",
                    f"Call to action: {call_to_action.strip()}",
                ]
            )

        draft = "\n".join(lines)

        return {
            "status": "success",
            "platform": platform,
            "topic": topic,
            "draft": draft,
            "requires_review": True,
            "requires_creator_approval_before_publishing": True,
        }

    def evaluate_content(
        self,
        content: str,
        platform: str = "",
    ) -> Dict[str, Any]:
        content = (content or "").strip()
        platform = self._normalise_platform(platform)

        if not content:
            return {
                "status": "error",
                "message": "Content is required.",
            }

        checks = {
            "has_content": bool(content),
            "reasonable_length": len(content) <= 10000,
            "contains_no_obvious_credentials": not self._contains_secret(
                content
            ),
            "requires_human_policy_review": True,
            "requires_creator_approval_for_publishing": True,
        }

        warnings = []

        if len(content) > 3000:
            warnings.append(
                "Content may need platform-specific shortening."
            )

        if any(
            phrase in content.lower()
            for phrase in [
                "guaranteed profit",
                "guaranteed income",
                "get rich quick",
                "risk free",
                "risk-free",
            ]
        ):
            warnings.append(
                "Potentially misleading financial language detected."
            )

        if platform in {
            "instagram",
            "facebook",
            "tiktok",
            "youtube",
        }:
            warnings.append(
                "Verify platform-specific advertising and "
                "commercial-content rules before publishing."
            )

        return {
            "status": "success",
            "platform": platform,
            "checks": checks,
            "warnings": warnings,
            "approved_for_publishing": False,
        }

    def create_campaign_plan(
        self,
        platform: str,
        topic: str,
        posts: int = 5,
        objective: str = "audience_growth",
    ) -> Dict[str, Any]:
        platform = self._normalise_platform(platform)
        topic = (topic or "").strip()
        objective = (objective or "audience_growth").strip()

        if platform not in self.PLATFORMS:
            return {
                "status": "error",
                "message": f"Unsupported platform: {platform}",
            }

        if not topic:
            return {
                "status": "error",
                "message": "Topic is required.",
            }

        try:
            posts = max(
                1,
                min(int(posts), 30),
            )
        except (TypeError, ValueError):
            posts = 5

        content_plan = []

        for index in range(1, posts + 1):
            content_plan.append(
                {
                    "sequence": index,
                    "topic": topic,
                    "platform": platform,
                    "objective": objective,
                    "status": "draft",
                    "requires_review": True,
                    "requires_creator_approval": True,
                }
            )

        campaign = {
            "id": self._make_id(
                platform,
                topic,
                prefix="campaign",
            ),
            "platform": platform,
            "topic": topic,
            "objective": objective,
            "posts": content_plan,
            "created_at": datetime.utcnow().isoformat(),
            "status": "proposed",
            "publishing_enabled": False,
        }

        if self.memory is not None:
            self.memory.log(
                "SocialStrategy",
                (
                    f"Created social campaign plan: "
                    f"{platform} / {topic}"
                ),
            )

        return {
            "status": "success",
            "campaign": campaign,
        }

    def get_supported_platforms(self) -> Dict[str, Any]:
        return {
            "status": "success",
            "platforms": sorted(
                self.PLATFORMS
            ),
        }

    @staticmethod
    def _normalise_platform(platform: str) -> str:
        value = (platform or "").strip().lower()

        aliases = {
            "twitter": "x",
        }

        return aliases.get(
            value,
            value,
        )

    @staticmethod
    def _contains_secret(content: str) -> bool:
        lowered = content.lower()

        secret_markers = [
            "password=",
            "api_key=",
            "apikey=",
            "secret=",
            "access_token=",
            "refresh_token=",
            "bearer ",
        ]

        return any(
            marker in lowered
            for marker in secret_markers
        )

    @staticmethod
    def _make_id(
        platform: str,
        topic: str,
        prefix: str = "social",
    ) -> str:
        timestamp = datetime.utcnow().strftime(
            "%Y%m%d%H%M%S"
        )

        slug = "".join(
            character
            if character.isalnum()
            else "-"
            for character in topic.lower()
        )

        slug = "-".join(
            part
            for part in slug.split("-")
            if part
        )

        return (
            f"{prefix}-"
            f"{platform}-"
            f"{timestamp}-"
            f"{slug[:25]}"
        )
