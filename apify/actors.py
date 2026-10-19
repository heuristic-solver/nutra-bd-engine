from typing import List, Dict, Any, Optional
try:
    from apify.client import ApifyWrapper
except (ImportError, ModuleNotFoundError):
    try:
        from .client import ApifyWrapper
    except (ImportError, ModuleNotFoundError):
        from client import ApifyWrapper

class ApifyActorsManager:
    """
    High-level interface for running verified Apify actors on target companies.
    """
    def __init__(self, wrapper: Optional[ApifyWrapper] = None):
        self.wrapper = wrapper or ApifyWrapper()

    def get_linkedin_job_changes(self, company_slug: str, days_ago: int = 365, max_results: int = 50) -> Dict[str, Any]:
        """
        Actor: data-slayer/linkedin-job-change-tracker
        Tracks employee departures, new hires, and internal promotions from LinkedIn.
        """
        run_input = {
            "company_urls": [company_slug],
            "event_type": "any",
            "days_ago": days_ago,
            "max_results": max_results
        }
        res = self.wrapper.run_actor_safe("data-slayer/linkedin-job-change-tracker", run_input, timeout_secs=90)
        if res["success"]:
            events = [i for i in res["items"] if i.get("event_type") in ("joined", "left", "title_change")]
            return {
                "success": True,
                "events": events,
                "total": len(events)
            }
        return res

    def get_growjo_growth(self, company_name: str) -> Dict[str, Any]:
        """
        Actor: scrapesage/growjo-scraper
        Extracts YoY employee growth %, revenue estimates, total funding, and CEO name.
        """
        run_input = {
            "company_name": company_name,
            "max_results": 1
        }
        res = self.wrapper.run_actor_safe("scrapesage/growjo-scraper", run_input, timeout_secs=60)
        if res["success"] and res["items"]:
            item = res["items"][0]
            return {
                "success": True,
                "employee_growth_pct": item.get("employee_growth_pct"),
                "employees": item.get("employees"),
                "estimated_revenue": item.get("estimated_revenue"),
                "total_funding": item.get("total_funding"),
                "ceo_name": item.get("ceo_name")
            }
        return res

    def get_leadership_changes(self, domain_or_name: str) -> Dict[str, Any]:
        """
        Actor: inovaflow/leadership-change-tracker
        Scrapes news and leadership pages for executive hires and buying windows.
        """
        run_input = {
            "target": domain_or_name,
            "onlyNewSinceLastRun": False
        }
        res = self.wrapper.run_actor_safe("inovaflow/leadership-change-tracker", run_input, timeout_secs=90)
        return res

    def get_crunchbase_funding(self, company_name: str) -> Dict[str, Any]:
        """
        Actor: memo23/crunchbase-scraper
        Scrapes Crunchbase for verified funding rounds and lead investors.
        """
        run_input = {
            "query": company_name,
            "max_items": 1
        }
        res = self.wrapper.run_actor_safe("memo23/crunchbase-scraper", run_input, timeout_secs=60)
        return res

    def search_linkedin_posts_for_moves(self, company_name: str, event_type: str = "any", max_posts: int = 30) -> Dict[str, Any]:
        """
        Actor: harvestapi/linkedin-post-search (No Cookies Required)
        Searches all of LinkedIn for posts where people announce they joined or left the company,
        or company welcome / promotion announcements.
        """
        c_clean = company_name.replace('"', '').strip()
        queries = []
        if event_type in ("departure", "any"):
            queries.append(f'("my last day" OR "new chapter" OR "leaving" OR "moving on") AND "{c_clean}"')
        if event_type in ("join", "any"):
            queries.append(f'("excited to announce" OR "thrilled to share" OR "starting as" OR "joined") AND "{c_clean}"')
        if event_type in ("company_welcome", "any"):
            queries.append(f'("please join us in welcoming" OR "welcome to the team" OR "congratulations on your promotion") AND "{c_clean}"')

        run_input = {
            "searchQueries": queries,
            "postedLimit": "month",
            "sortBy": "date",
            "maxPosts": max_posts
        }
        res = self.wrapper.run_actor_safe("harvestapi/linkedin-post-search", run_input, timeout_secs=90)
        return res

    def get_company_linkedin_posts(self, company_linkedin_url: str, max_posts: int = 15) -> Dict[str, Any]:
        """
        Actor: harvestapi/linkedin-company-posts (No Cookies Required)
        Scrapes recent updates published by the company's official LinkedIn page
        to detect welcome announcements, promotions, or facility expansions.
        """
        run_input = {
            "targetUrls": [company_linkedin_url],
            "maxPosts": max_posts
        }
        res = self.wrapper.run_actor_safe("harvestapi/linkedin-company-posts", run_input, timeout_secs=60)
        return res

    def fetch_company_social_signals(self, company_name: str, company_linkedin_url: Optional[str] = None, max_posts: int = 10) -> Dict[str, Any]:
        """
        High-level unified orchestrator:
        1. Queries company page posts for welcome/promotion/facility updates.
        2. Queries LinkedIn global post search for individual departure & join posts.
        3. Parses raw items into structured BD signals.
        """
        all_raw_items = []
        errors = []

        # 1. Company Page Updates
        if company_linkedin_url and "linkedin.com/company" in company_linkedin_url:
            co_res = self.get_company_linkedin_posts(company_linkedin_url, max_posts=max_posts)
            if co_res.get("success"):
                all_raw_items.extend(co_res.get("items", []))
            elif co_res.get("error"):
                errors.append(f"CompanyPosts: {co_res.get('error')}")

        # 2. Global Post Search for Departures / Joins
        search_res = self.search_linkedin_posts_for_moves(company_name, event_type="any", max_posts=max_posts)
        if search_res.get("success"):
            all_raw_items.extend(search_res.get("items", []))
        elif search_res.get("error"):
            errors.append(f"PostSearch: {search_res.get('error')}")

        # 3. Parse and normalize
        parsed = parse_linkedin_posts_to_signals(all_raw_items, company_name)
        return {
            "success": len(parsed) > 0 or len(errors) == 0,
            "signals": parsed,
            "errors": errors,
            "total_signals": len(parsed)
        }


def parse_linkedin_posts_to_signals(items: List[Dict[str, Any]], company_name: str) -> List[Dict[str, str]]:
    """
    Parses heterogeneous LinkedIn post scraper payloads into canonical signal descriptors.
    """
    signals = []
    c_lower = company_name.lower().strip()

    for item in items:
        # Resolve post text
        text = item.get("text") or item.get("postText") or item.get("content") or item.get("body") or ""
        if not text or len(text.strip()) < 15:
            continue
        t_lower = text.lower()

        # Resolve author metadata
        author = item.get("author") or item.get("authorName") or item.get("author_name") or {}
        if isinstance(author, dict):
            author_name = author.get("name") or author.get("title") or "LinkedIn Member"
            headline = author.get("headline") or author.get("occupation") or author.get("subTitle") or ""
            author_url = author.get("url") or author.get("link") or ""
        else:
            author_name = str(author) if author else "LinkedIn Member"
            headline = item.get("authorHeadline") or item.get("headline") or ""
            author_url = item.get("authorUrl") or ""

        post_url = item.get("postUrl") or item.get("url") or ""
        post_date = str(item.get("postedDate") or item.get("postedAt") or item.get("date") or "")[:10]

        # Categorize signal
        if any(k in t_lower for k in ["last day", "new chapter", "leaving", "moving on", "thank you for the journey", "bittersweet"]):
            sig_type = "EXECUTIVE_DEPARTURE"
            snippet = text.replace("\n", " ").strip()[:140]
            label = f"[0-DAY DEPARTURE POST] {author_name} ({headline}): \"{snippet}...\""
        elif any(k in t_lower for k in ["pleased to announce", "please join us in welcoming", "welcome to the team", "congratulations to", "promoted to", "proud to welcome"]):
            sig_type = "COMPANY_WELCOME_OR_PROMOTION"
            snippet = text.replace("\n", " ").strip()[:140]
            label = f"[COMPANY ANNOUNCEMENT] {company_name}: \"{snippet}...\""
        elif any(k in t_lower for k in ["excited to announce", "thrilled to share", "starting as", "joined", "happy to share that i'm starting"]):
            sig_type = "NEW_HIRE_POST"
            snippet = text.replace("\n", " ").strip()[:140]
            label = f"[0-DAY JOIN POST] {author_name} ({headline}): \"{snippet}...\""
        else:
            sig_type = "COMPANY_UPDATE"
            snippet = text.replace("\n", " ").strip()[:140]
            label = f"[LINKEDIN UPDATE] {author_name}: \"{snippet}...\""

        signals.append({
            "type": sig_type,
            "label": label,
            "author": author_name,
            "headline": headline,
            "snippet": text[:250],
            "date": post_date,
            "post_url": post_url,
            "author_url": author_url
        })

    return signals

