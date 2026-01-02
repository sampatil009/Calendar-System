from ics import Calendar
from datetime import timedelta
import pytz

from models import db, Event


class ICSParser:
    def detect_source(self, text: str) -> str:
        text = text.lower()
        if 'google' in text:
            return 'google'
        if 'microsoft' in text or 'outlook' in text:
            return 'outlook'
        if 'apple' in text or 'icloud' in text:
            return 'iphone'
        return 'ics'

    def parse_ics_file(self, file, user_id):
        try:
            raw = file.read()
            if isinstance(raw, bytes):
                raw = raw.decode('utf-8', errors='ignore')

            if not raw.strip():
                raise Exception("ICS file is empty")

            source = self.detect_source(raw)
            calendar = Calendar(raw)

            events_created = []

            for e in calendar.events:
                start = e.begin.datetime
                end = e.end.datetime if e.end else start + timedelta(hours=1)

                if start.tzinfo is None:
                    start = pytz.utc.localize(start)
                if end.tzinfo is None:
                    end = pytz.utc.localize(end)

                event = Event(
                    user_id=user_id,
                    title=e.name or "Untitled Event",
                    description=e.description or "",
                    location=e.location or "",
                    start_time=start.astimezone(pytz.utc),
                    end_time=end.astimezone(pytz.utc),
                    all_day=e.all_day,
                    source=source
                )

                db.session.add(event)
                events_created.append(event)

            db.session.commit()
            return events_created

        except Exception as e:
            db.session.rollback()
            raise Exception(str(e))
