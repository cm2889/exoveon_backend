import logging
import random
import time
from typing import List, Optional
from datetime import datetime, timedelta, UTC
from google_play_scraper import reviews, Sort, search, app

LANGUAGE = 'en'
COUNTRY = 'bd'
REVIEWS_BATCH_SIZE = 200
SLEEP_SECONDS_MIN = 1.0
SLEEP_SECONDS_MAX = 3.0


class ReviewEntry: 
    def __init__(self, index: int, source: dict):
        self.index = index
        self.score: Optional[int] = source.get('score')
        self.content: Optional[str] = source.get('content')

    def __str__(self) -> str:  
        score_str = 'null' if self.score is None else str(self.score)
        content_str = '' if self.content is None else str(self.content).strip()
        return (
            f"\n{self.index} : {{\n"
            f" \"score\": {score_str},\n"
            f" \"content\": \"{content_str}\", \n\n"
            f"}}\n"
        )


def find_app_id_by_name(query: str) -> Optional[str]:
    """
    If query looks like a package ID (contains dots), use it directly.
    Otherwise, search for the app.
    """
    # If it looks like a package ID (e.g., com.thecitybank.citytouch), use it directly
    if '.' in query and query.count('.') >= 2:
        print(f"Using package ID directly: {query}")
        try:
            # Verify the app exists
            app_metadata = app(query, lang=LANGUAGE, country='us')
            print(f"App verified: {app_metadata['title']} by {app_metadata['developer']}")
            return query
        except Exception as exc:
            print(f"Error verifying app: {exc}")
            return None
    
    # Otherwise search for it
    try:
        results = search(query=query, lang=LANGUAGE, country=COUNTRY, n_hits=5)
        if not results:
            print(f"No results found for query: {query}")
            return None
        print(f"Search found {len(results)} result(s)")
        for result in results:
            if result.get('appId'):
                print(f"Found app: {result['title']} - {result['appId']}")
                return result['appId']
        print("No valid appId found in search results")
        return None
    except Exception as exc:
        print(f"Error searching for app: {exc}")
        import traceback
        traceback.print_exc()
        return None


def fetch_all_reviews(app_id: str, max_total: int = 100, progress_step: int = 500) -> List[ReviewEntry]:
    if not app_id:
        raise ValueError("app_id is required")

    collected: List[dict] = []
    cutoff = datetime.now(UTC) - timedelta(days=365)
    next_progress_mark = max(progress_step, 1)
    continuation_token = None

    while len(collected) < max_total:
        remaining = max_total - len(collected)
        batch_size = min(REVIEWS_BATCH_SIZE, remaining)

        batch, continuation_token = reviews(
            app_id,
            lang=LANGUAGE,
            country=COUNTRY,
            sort=Sort.NEWEST,
            count=batch_size,
            filter_score_with=None,
            continuation_token=continuation_token,
        )

        if not batch:
            break

        try:
            oldest_dt = min(
                r.get('at') for r in batch if isinstance(r.get('at'), datetime)
            )
            if oldest_dt:
                if oldest_dt.tzinfo is None:
                    oldest_dt = oldest_dt.replace(tzinfo=UTC)
                if oldest_dt < cutoff:
                    break
        except Exception as exc:
            raise 
        
        collected.extend(batch)

        if len(collected) >= next_progress_mark:
            next_progress_mark += progress_step

        if continuation_token is None:
            break

        time.sleep(random.uniform(SLEEP_SECONDS_MIN, SLEEP_SECONDS_MAX))

    trimmed = collected[:max_total]
    wrapped = [ReviewEntry(index=i + 1, source=r) for i, r in enumerate(trimmed)]

    return wrapped



# if __name__ == "__main__":
#     app_name = "com.ebl.skybanking" 
#     max_total = 100 

#     app_id = find_app_id_by_name(app_name) 
#     print(f"Found app ID: {app_id}")
    
#     if not app_id:
#         print(f"Could not find app ID for '{app_name}'. Please check the app name or try searching on Google Play Store.")
#         exit(1)
    
#     reviews_list = fetch_all_reviews(app_id, max_total=max_total) 

#     for r in reviews_list:
#         print(r) 


# """ 

# 1 : {
#  "score": 5,
#  "content": "Great app", 
 
# }
# 2 : {
#  "score": 4,
#  "content": "Good app", 

# }

# """