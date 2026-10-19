import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from apify_client import ApifyClient
from apify_client.errors import ApifyApiError

load_dotenv()

class ApifyWrapper:
    """
    Robust client wrapper for Apify Actors with rate limit detection,
    credential management, and error handling.
    """
    def __init__(self, token: Optional[str] = None):
        self.token = token or os.getenv("APIFY_TOKEN")
        if not self.token:
            raise ValueError("APIFY_TOKEN not found in environment or parameters.")
        self.client = ApifyClient(self.token)

    def check_account_status(self) -> Dict[str, Any]:
        """Check plan tier, credit limits, and usage status."""
        try:
            user = self.client.user().get()
            plan = user.get("plan", {})
            return {
                "authenticated": True,
                "username": user.get("username"),
                "plan_tier": plan.get("tier"),
                "monthly_credits_usd": plan.get("monthlyUsageCreditsUsd"),
                "max_monthly_usage_usd": plan.get("maxMonthlyUsageUsd")
            }
        except Exception as e:
            return {
                "authenticated": False,
                "error": str(e)
            }

    def run_actor_safe(self, actor_id: str, run_input: Dict[str, Any], timeout_secs: int = 120) -> Dict[str, Any]:
        """
        Safely executes an Apify actor, capturing limits or errors without crashing.
        """
        try:
            run = self.client.actor(actor_id).call(run_input=run_input, timeout_secs=timeout_secs)
            items = list(self.client.dataset(run["defaultDatasetId"]).iterate_items())
            return {
                "success": True,
                "status": run.get("status"),
                "items": items,
                "total_items": len(items),
                "usage_usd": run.get("usageTotalUsd", 0)
            }
        except ApifyApiError as e:
            err_msg = str(e)
            is_limit = "Monthly usage hard limit exceeded" in err_msg or "hard limit" in err_msg.lower()
            return {
                "success": False,
                "error": err_msg,
                "limit_exceeded": is_limit,
                "items": []
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "limit_exceeded": False,
                "items": []
            }
