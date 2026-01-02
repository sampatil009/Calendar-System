document.addEventListener('DOMContentLoaded', function () {

    console.log('calendar.js loaded');

    const calendarEl = document.getElementById('calendar');
    if (!calendarEl) {
        alert('Calendar div missing');
        return;
    }

    let initialView = 'dayGridMonth';
    if (calendarView === 'week') initialView = 'timeGridWeek';
    if (calendarView === 'day') initialView = 'timeGridDay';

    const calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: initialView,
        headerToolbar: false,
        events: '/api/events',
        selectable: true,

        dateClick(info) {
            openEventForm(info.dateStr);
        }
    });

    calendar.render();
    updateTitle();

    document.getElementById('prev-btn').onclick = () => {
        calendar.prev();
        updateTitle();
    };

    document.getElementById('next-btn').onclick = () => {
        calendar.next();
        updateTitle();
    };

    document.getElementById('today-btn').onclick = () => {
        calendar.today();
        updateTitle();
    };

    document.getElementById('new-event-btn').onclick = () => {
        openEventForm();
    };

    function updateTitle() {
        const title = document.getElementById('calendar-title');
        if (title) title.innerText = calendar.view.title;
    }

    const modal = document.getElementById('event-form-modal');

    function openEventForm(dateStr = null) {
        if (!modal) {
            alert('Event modal missing in HTML');
            return;
        }

        modal.style.display = 'block';

        if (dateStr) {
            document.getElementById('event-start').value = dateStr + 'T09:00';
            document.getElementById('event-end').value = dateStr + 'T10:00';
        }
    }

    document.querySelectorAll('.close, #cancel-form-btn').forEach(btn => {
        btn.onclick = () => modal.style.display = 'none';
    });

    document.getElementById('event-form').addEventListener('submit', function (e) {
        e.preventDefault();

        const data = {
            title: document.getElementById('event-title').value,
            start: document.getElementById('event-start').value,
            end: document.getElementById('event-end').value,
            location: document.getElementById('event-location').value,
            description: document.getElementById('event-description').value,
            color: document.getElementById('event-color').value,
            allDay: document.getElementById('event-all-day').checked
        };

        fetch('/api/event', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        })
        .then(() => {
            modal.style.display = 'none';
            calendar.refetchEvents();
            document.getElementById('event-form').reset();
        })
        .catch(() => alert('Failed to save event'));
    });
});
