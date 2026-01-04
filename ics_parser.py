from ics import Calendar
from datetime import timedelta, datetime
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
            max_recurrence_instances = 100  # Limit to prevent too many events
            max_recurrence_date = datetime.now(pytz.utc) + timedelta(days=730)  # 2 years ahead

            for e in calendar.events:
                # Check if event has recurrence rule
                try:
                    has_recurrence = hasattr(e, 'rrule') and e.rrule is not None
                    if has_recurrence and hasattr(e, 'occurrences'):
                        # Expand recurring events
                        occurrences = list(e.occurrences)
                        
                        # Limit occurrences
                        limited_occurrences = []
                        for occ in occurrences:
                            if len(limited_occurrences) >= max_recurrence_instances:
                                break
                            if occ > max_recurrence_date:
                                break
                            limited_occurrences.append(occ)
                        
                        # Create event for each occurrence
                        for occ_start in limited_occurrences:
                            # Calculate duration
                            duration = e.duration if hasattr(e, 'duration') and e.duration else timedelta(hours=1)
                            occ_end = occ_start + duration
                            
                            # Handle timezone
                            if occ_start.tzinfo is None:
                                occ_start = pytz.utc.localize(occ_start)
                            if occ_end.tzinfo is None:
                                occ_end = pytz.utc.localize(occ_end)
                            
                            event = Event(
                                user_id=user_id,
                                title=e.name or "Untitled Event",
                                description=e.description or "",
                                location=e.location or "",
                                start_time=occ_start.astimezone(pytz.utc),
                                end_time=occ_end.astimezone(pytz.utc),
                                all_day=e.all_day if hasattr(e, 'all_day') else False,
                                source=source
                            )
                            
                            db.session.add(event)
                            events_created.append(event)
                    else:
                        # Non-recurring event or recurrence not supported
                        raise AttributeError("No recurrence")
                except (AttributeError, TypeError):
                    # Non-recurring event or error processing recurrence
                    # Non-recurring event
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
