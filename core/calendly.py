import uuid 
import requests
from django.conf import settings


class CalendlyClient:

    def __init__(self):
        token = getattr(settings, "CALENDLY_TOKEN", None)
        if not token:
            raise RuntimeError("CALENDLY_TOKEN is not configured in settings")

        self.base_url = "https://api.calendly.com"
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _handle_response(self, response: requests.Response):
        """Raise informative error with Calendly payload if available."""
        try:
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            try:
                details = response.json()
            except Exception:
                details = {"detail": response.text}
            raise requests.HTTPError(
                f"{e}. Calendly response: {details}",
                response=response,
            )

    def _get(self, path: str, params: dict | None = None):
        url = f"{self.base_url}{path}"
        resp = requests.get(url, headers=self.headers, params=params, timeout=30)
        return self._handle_response(resp)

    def _post(self, path: str, json: dict):
        url = f"{self.base_url}{path}"
        resp = requests.post(url, headers=self.headers, json=json, timeout=30)
        return self._handle_response(resp)

    def get_user_info(self):
        return self._get("/users/me")

    def list_event_types(self, organization: str | None = None, user: str | None = None, active: bool | None = None, count: int = 50, page_token: str | None = None,):
       
        params: dict = {"count": max(1, min(count, 100))}

        if page_token:
            params["page_token"] = page_token

        if active is not None:
            params["active"] = str(bool(active)).lower()

        # Ensure we pass a required filter
        if not organization and not user:
            me = self.get_user_info()
            resource = me.get("resource", {}) if isinstance(me, dict) else {}
            organization = resource.get("current_organization")
            if not organization:
                user = resource.get("uri")

        if organization:
            params["organization"] = organization
        elif user:
            params["user"] = user
        else:
            raise ValueError(
                "Calendly list_event_types requires 'organization' or 'user' filter, and auto-discovery failed"
            )

        return self._get("/event_types", params=params)


    def create_scheduled_event(self, name: str, slug: str, internal_note: str, description_plain: str, kind: str, duration: int ):

        payload = {
            "name": name if name else "New Event Type",
            "slug": slug if slug else uuid.uuid4().hex,
            "internal_note": internal_note if internal_note else "",
            "description_plain": description_plain if description_plain else "",
            "kind": kind,
            "duration": duration if duration else 30,
            "owner": 'https://api.calendly.com/users/c2438102-5ad5-4595-bf5f-82d00234b648',
        }

        return self._post("/event_types", json=payload)