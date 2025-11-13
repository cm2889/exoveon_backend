
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import datetime, timedelta, UTC
import re
import sys

# ====== CONFIGURE YOUR CREDENTIALS HERE ======
# ⚠️ ACTION: REPLACE THIS WITH YOUR ACTUAL API KEY FROM GOOGLE CLOUD CONSOLE
# This is NOT your client secret (GOCSPX-...). It should look like AIzaSy...
API_KEY = " AIzaSyBnLftThDcZ2nBxcQeUxOhaVyhiFo52G9w"  
PUBLIC_CAL_ID = "calendar-json.googleapis.com" # A public calendar ID that works for testing
# =============================================

CLIENT_ID_RE = re.compile(r"[0-9\-]+-[a-z0-9]+\.apps\.googleusercontent\.com$", re.I)

def rfc3339_utc(dt: datetime) -> str:
    """Formats a datetime object to an RFC3339 string for the API."""
    return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")

def build_service():
    """Builds the Calendar service object using the API key."""
    return build("calendar", "v3", developerKey=API_KEY)

def test_colors(service):
    """Tests the colors.get endpoint."""
    print("• colors.get …")
    colors = service.colors().get().execute()
    print(f"  calendars: {len(colors.get('calendar', {}))}, events: {len(colors.get('event', {}))}")

def test_calendars_get(service, calendar_id):
    """Tests the calendars.get endpoint."""
    print(f"• calendars.get ({calendar_id}) …")
    meta = service.calendars().get(calendarId=calendar_id).execute()
    print(f"  summary = {meta.get('summary')!r}, timeZone = {meta.get('timeZone')!r}")

def test_events_list(service, calendar_id):
    """Tests the events.list endpoint for upcoming events."""
    print(f"• events.list ({calendar_id}) …")
    now = datetime.now(UTC)
    res = service.events().list(
        calendarId=calendar_id,
        timeMin=rfc3339_utc(now),
        maxResults=5,
        singleEvents=True,
        orderBy="startTime",
    ).execute()
    items = res.get("items", [])
    if not items:
        print("  (no upcoming events)")
    else:
        print(f"  Found {len(items)} upcoming events:")
        for e in items:
            start = e["start"].get("dateTime", e["start"].get("date"))
            print(f"  - {start} — {e.get('summary', '(no title)')}")

def test_freebusy(service, calendar_id):
    """Tests the freebusy.query endpoint."""
    print(f"• freebusy.query ({calendar_id}) …")
    start = datetime.now(UTC)
    end = start + timedelta(days=7)
    body = {
        "timeMin": rfc3339_utc(start),
        "timeMax": rfc3339_utc(end),
        "items": [{"id": calendar_id}],
    }
    res = service.freebusy().query(body=body).execute()
    busy = res.get("calendars", {}).get(calendar_id, {}).get("busy", [])
    print(f"  busy blocks in next 7 days: {len(busy)}")

def main(calendar_id: str = PUBLIC_CAL_ID):
    """Main function to run all tests."""
    if API_KEY == "YOUR_GENERATED_API_KEY_HERE":
        print("❌ ERROR: You must replace 'YOUR_GENERATED_API_KEY_HERE' with your actual Google API Key.")
        sys.exit(1)

    if CLIENT_ID_RE.search(calendar_id):
        print("❌ You passed an OAuth CLIENT ID, not a calendar ID. Using default public calendar.")
        calendar_id = PUBLIC_CAL_ID

    try:
        service = build_service()
        print("Testing Google Calendar API (API key mode)…\n")
        
        test_colors(service)
        test_calendars_get(service, calendar_id)
        test_events_list(service, calendar_id)
        test_freebusy(service, calendar_id)
        
        print("\n✅ API key test completed successfully")
        return True

    except HttpError as he:
        print(f"\n[Google API HttpError] {he}")
        print(
            "\nIf the message includes **accessNotConfigured / PERMISSION_DENIED**:\n"
            "  • Ensure **Google Calendar API** is enabled in the SAME project as this API key\n"
            "  • If your key is restricted, add **Google Calendar API** to the allowed list\n"
        )
        return False
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        return False

if __name__ == "__main__":
    ok = main() 
    print("\nAll good!" if ok else "\nSomething failed.")
CLIENT_ID_RE = re.compile(r"[0-9\-]+-[a-z0-9]+\.apps\.googleusercontent\.com$", re.I)

def rfc3339_utc(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")

def build_service():
    return build("calendar", "v3", developerKey=API_KEY)

def test_colors(service):
    print("• colors.get …")
    colors = service.colors().get().execute()
    print(f"  calendars: {len(colors.get('calendar', {}))}, events: {len(colors.get('event', {}))}")

def test_calendars_get(service, calendar_id):
    print(f"• calendars.get ({calendar_id}) …")
    meta = service.calendars().get(calendarId=calendar_id).execute()
    print(f"  summary = {meta.get('summary')!r}, timeZone = {meta.get('timeZone')!r}")

def test_events_list(service, calendar_id):
    print(f"• events.list ({calendar_id}) …")
    now = datetime.now(UTC)
    res = service.events().list(
        calendarId=calendar_id,
        timeMin=rfc3339_utc(now),
        maxResults=10,
        singleEvents=True,
        orderBy="startTime",
    ).execute()
    items = res.get("items", [])
    if not items:
        print("  (no upcoming events)")
    else:
        for e in items:
            start = e["start"].get("dateTime", e["start"].get("date"))
            print(f"  {start} — {e.get('summary', '(no title)')}")

def test_freebusy(service, calendar_id):
    print(f"• freebusy.query ({calendar_id}) …")
    start = datetime.now(UTC)
    end = start + timedelta(days=7)
    body = {
        "timeMin": rfc3339_utc(start),
        "timeMax": rfc3339_utc(end),
        "items": [{"id": calendar_id}],
    }
    res = service.freebusy().query(body=body).execute()
    busy = res.get("calendars", {}).get(calendar_id, {}).get("busy", [])
    print(f"  busy blocks in next 7 days: {len(busy)}")

def main(calendar_id: str = PUBLIC_CAL_ID):
    if CLIENT_ID_RE.search(calendar_id):
        print("❌ You passed an OAuth CLIENT ID, not a calendar ID.")
        print("   Use a public calendar ID like: en.usa#holiday@group.v.calendar.google.com")
        sys.exit(1)

    try:
        service = build_service()
        print("Testing Google Calendar API (API key mode)…\n")
        test_colors(service)
        test_calendars_get(service, calendar_id)
        test_events_list(service, calendar_id)
        test_freebusy(service, calendar_id)
        print("\n✅ API key test completed successfully")
        return True

    except HttpError as he:
        print(f"\n[Google API HttpError] {he}")
        print(
            "\nIf the message includes accessNotConfigured / PERMISSION_DENIED:\n"
            "  • Enable **Google Calendar API** in the SAME project as this API key\n"
            "  • If your key is API-restricted, add **Google Calendar API** to the allowed list\n"
            "  • Check any IP / HTTP referrer restrictions\n"
        )
        return False
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        return False

if __name__ == "__main__":
    ok = main(PUBLIC_CAL_ID)   # or replace with another public calendar ID
    print("\nAll good!" if ok else "\nSomething failed.")
