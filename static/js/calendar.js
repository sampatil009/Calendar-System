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

    let currentEventId = null;
    let categories = [];
    let currentFilters = {
        category_id: null,
        source: null
    };

    // Initialize calendar
    const calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: initialView,
        headerToolbar: false,
        events: function(fetchInfo, successCallback, failureCallback) {
            // Build query string with filters
            let url = '/api/events';
            const params = new URLSearchParams();
            if (currentFilters.category_id) {
                params.append('category_id', currentFilters.category_id);
            }
            if (currentFilters.source) {
                params.append('source', currentFilters.source);
            }
            if (fetchInfo.start) {
                params.append('start_date', fetchInfo.start.toISOString());
            }
            if (fetchInfo.end) {
                params.append('end_date', fetchInfo.end.toISOString());
            }
            if (params.toString()) {
                url += '?' + params.toString();
            }

            fetch(url)
                .then(response => response.json())
                .then(data => {
                    const formattedData = data.map(event => ({
                        ...event,
                        id: String(event.id) 
                    }));
                    successCallback(formattedData);
                })
                .catch(error => {
                    console.error('Error fetching events:', error);
                    failureCallback(error);
                });
        },
        selectable: true,
        editable: true, 
        eventResizableFromStart: true,
        eventDrop: function(info) {
            updateEventTime(info.event);
        },
        eventResize: function(info) {
            updateEventTime(info.event);
        },
        eventClick: function(info) {
            showEventDetails(parseInt(info.event.id));
        },
        dateClick: function(info) {
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

    loadCategories();

    document.getElementById('create-category-btn').onclick = function() {
        const name = document.getElementById('new-category-name').value.trim();
        const color = document.getElementById('new-category-color').value;

        if (!name) {
            alert('Please enter a category name');
            return;
        }

        fetch('/api/category', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, color })
        })
        .then(response => response.json())
        .then(data => {
            loadCategories();
            document.getElementById('new-category-name').value = '';
            document.getElementById('new-category-color').value = '#3788d8';
        })
        .catch(error => {
            console.error('Error creating category:', error);
            alert('Failed to create category');
        });
    };

    function loadCategories() {
        fetch('/api/categories')
            .then(response => response.json())
            .then(data => {
                categories = data;
                renderCategories();
                updateCategoryFilter();
                updateEventFormCategories();
            })
            .catch(error => console.error('Error loading categories:', error));
    }

    function renderCategories() {
        const container = document.getElementById('categories-list');
        container.innerHTML = '';

        categories.forEach(cat => {
            const badge = document.createElement('div');
            badge.className = 'category-badge';
            badge.innerHTML = `
                <span class="color-dot" style="background-color: ${cat.color}"></span>
                <span>${cat.name}</span>
            `;
            container.appendChild(badge);
        });
    }

    function updateCategoryFilter() {
        const select = document.getElementById('filter-category');
        const allOption = select.querySelector('option[value=""]');
        select.innerHTML = '';
        if (allOption) select.appendChild(allOption);

        categories.forEach(cat => {
            const option = document.createElement('option');
            option.value = cat.id;
            option.textContent = cat.name;
            select.appendChild(option);
        });
    }

    function updateEventFormCategories() {
        const container = document.getElementById('event-categories-checkboxes');
        container.innerHTML = '';

        if (categories.length === 0) {
            container.innerHTML = '<p style="color: #999; font-size: 14px;">No categories created yet</p>';
            return;
        }

        categories.forEach(cat => {
            const label = document.createElement('label');
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.value = cat.id;
            checkbox.id = `cat-${cat.id}`;

            label.appendChild(checkbox);
            label.appendChild(document.createTextNode(' '));
            const colorDot = document.createElement('span');
            colorDot.className = 'color-dot';
            colorDot.style.backgroundColor = cat.color;
            colorDot.style.display = 'inline-block';
            colorDot.style.marginRight = '6px';
            label.insertBefore(colorDot, checkbox);
            label.appendChild(document.createTextNode(cat.name));

            container.appendChild(label);
        });
    }

    document.getElementById('filter-category').onchange = function() {
        currentFilters.category_id = this.value || null;
        calendar.refetchEvents();
    };

    document.getElementById('filter-source').onchange = function() {
        currentFilters.source = this.value || null;
        calendar.refetchEvents();
    };

    document.getElementById('clear-filters-btn').onclick = function() {
        document.getElementById('filter-category').value = '';
        document.getElementById('filter-source').value = '';
        currentFilters.category_id = null;
        currentFilters.source = null;
        calendar.refetchEvents();
    };

    const eventFormModal = document.getElementById('event-form-modal');
    const eventForm = document.getElementById('event-form');

    function openEventForm(dateStr = null, eventId = null) {
        currentEventId = eventId;
        const titleEl = document.getElementById('event-form-title');
        const formTitle = eventId ? 'Edit Event' : 'Create Event';
        titleEl.textContent = formTitle;

        if (eventId) {
            fetch(`/api/event/${eventId}`)
                .then(response => response.json())
                .then(data => {
                    document.getElementById('event-id').value = data.id;
                    document.getElementById('event-title').value = data.title;
                    document.getElementById('event-description').value = data.description || '';
                    document.getElementById('event-location').value = data.location || '';
                    document.getElementById('event-color').value = data.color || '#3788d8';
                    document.getElementById('event-all-day').checked = data.allDay;

                    const startDate = new Date(data.start);
                    const endDate = new Date(data.end);
                    document.getElementById('event-start').value = formatDateForInput(startDate);
                    document.getElementById('event-end').value = formatDateForInput(endDate);

                    if (data.categories) {
                        data.categories.forEach(cat => {
                            const checkbox = document.getElementById(`cat-${cat.id}`);
                            if (checkbox) checkbox.checked = true;
                        });
                    }
                })
                .catch(error => {
                    console.error('Error loading event:', error);
                    alert('Failed to load event');
                });
        } else {
            eventForm.reset();
            document.getElementById('event-id').value = '';
            if (dateStr) {
                document.getElementById('event-start').value = dateStr + 'T09:00';
                document.getElementById('event-end').value = dateStr + 'T10:00';
            }
        }

        eventFormModal.style.display = 'block';
    }

    eventForm.addEventListener('submit', function (e) {
        e.preventDefault();

        const eventId = document.getElementById('event-id').value;
        const isEdit = !!eventId;

        const selectedCategories = Array.from(
            document.querySelectorAll('#event-categories-checkboxes input[type="checkbox"]:checked')
        ).map(cb => parseInt(cb.value));

        const data = {
            title: document.getElementById('event-title').value,
            start: document.getElementById('event-start').value,
            end: document.getElementById('event-end').value,
            location: document.getElementById('event-location').value,
            description: document.getElementById('event-description').value,
            color: document.getElementById('event-color').value,
            allDay: document.getElementById('event-all-day').checked,
            category_ids: selectedCategories
        };

        const url = isEdit ? `/api/event/${eventId}` : '/api/event';
        const method = isEdit ? 'PUT' : 'POST';

        fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(() => {
            eventFormModal.style.display = 'none';
            calendar.refetchEvents();
            eventForm.reset();
            currentEventId = null;
        })
        .catch(error => {
            console.error('Error saving event:', error);
            alert('Failed to save event');
        });
    });

    document.querySelectorAll('.close, #cancel-form-btn').forEach(btn => {
        btn.onclick = () => {
            eventFormModal.style.display = 'none';
            eventForm.reset();
            currentEventId = null;
        };
    });

    const eventDetailsModal = document.getElementById('event-details-modal');

    function showEventDetails(eventId) {
        fetch(`/api/event/${eventId}`)
            .then(response => response.json())
            .then(data => {
                currentEventId = eventId;

                document.getElementById('details-title').textContent = data.title;
                document.getElementById('details-time').textContent = formatEventTime(data);
                document.getElementById('details-location').textContent = data.location || 'N/A';
                document.getElementById('details-description').textContent = data.description || 'N/A';
                document.getElementById('details-source').textContent = data.source || 'manual';

                const categoriesEl = document.getElementById('details-categories');
                if (data.categories && data.categories.length > 0) {
                    categoriesEl.innerHTML = data.categories.map(cat => 
                        `<span class="category-badge">
                            <span class="color-dot" style="background-color: ${cat.color}"></span>
                            ${cat.name}
                        </span>`
                    ).join(' ');
                } else {
                    categoriesEl.textContent = 'None';
                }

                const imagesEl = document.getElementById('details-images');
                if (data.images && data.images.length > 0) {
                    imagesEl.innerHTML = data.images.map(img => 
                        `<div class="image-item">
                            <img src="${img.path}" alt="Event image">
                        </div>`
                    ).join('');
                } else {
                    imagesEl.innerHTML = '<p style="color: #999;">No images</p>';
                }

                const attachmentsEl = document.getElementById('details-attachments');
                if (data.attachments && data.attachments.length > 0) {
                    attachmentsEl.innerHTML = data.attachments.map(att => 
                        `<div class="attachment-item">
                            <a href="${att.path}" download>${att.filename}</a>
                        </div>`
                    ).join('');
                } else {
                    attachmentsEl.innerHTML = '<p style="color: #999;">No attachments</p>';
                }

                eventDetailsModal.style.display = 'block';
            })
            .catch(error => {
                console.error('Error loading event details:', error);
                alert('Failed to load event details');
            });
    }

    function formatEventTime(data) {
        const start = new Date(data.start);
        const end = new Date(data.end);
        
        if (data.allDay) {
            return start.toLocaleDateString();
        }
        
        return `${start.toLocaleString()} - ${end.toLocaleString()}`;
    }

    document.getElementById('edit-event-btn').onclick = function() {
        eventDetailsModal.style.display = 'none';
        openEventForm(null, currentEventId);
    };

    document.getElementById('export-event-btn').onclick = function() {
        if (!currentEventId) return;
        window.location.href = `/api/event/${currentEventId}/export`;
    };

    document.getElementById('delete-event-btn').onclick = function() {
        const confirmModal = document.getElementById('delete-confirm-modal');
        confirmModal.style.display = 'block';
    };

    document.getElementById('confirm-delete-btn').onclick = function() {
        if (!currentEventId) return;

        fetch(`/api/event/${currentEventId}`, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(() => {
            document.getElementById('delete-confirm-modal').style.display = 'none';
            eventDetailsModal.style.display = 'none';
            calendar.refetchEvents();
            currentEventId = null;
        })
        .catch(error => {
            console.error('Error deleting event:', error);
            alert('Failed to delete event');
        });
    };

    document.getElementById('cancel-delete-btn').onclick = function() {
        document.getElementById('delete-confirm-modal').style.display = 'none';
    };

    document.querySelectorAll('#close-details, #close-details-btn').forEach(btn => {
        btn.onclick = () => {
            eventDetailsModal.style.display = 'none';
            currentEventId = null;
        };
    });

    document.getElementById('upload-image-btn').onclick = function() {
        document.getElementById('image-upload-input').click();
    };

    document.getElementById('image-upload-input').onchange = function() {
        if (!currentEventId) return;
        if (!this.files || this.files.length === 0) return;

        const formData = new FormData();
        Array.from(this.files).forEach(file => {
            formData.append('file', file);
        });

        const file = this.files[0];
        const uploadFormData = new FormData();
        uploadFormData.append('file', file);

        fetch(`/api/event/${currentEventId}/image`, {
            method: 'POST',
            body: uploadFormData
        })
        .then(response => response.json())
        .then(() => {
            showEventDetails(currentEventId);
            this.value = '';
        })
        .catch(error => {
            console.error('Error uploading image:', error);
            alert('Failed to upload image');
        });
    };

    document.getElementById('upload-attachment-btn').onclick = function() {
        document.getElementById('attachment-upload-input').click();
    };

    document.getElementById('attachment-upload-input').onchange = function() {
        if (!currentEventId) return;
        if (!this.files || this.files.length === 0) return;

        const formData = new FormData();
        formData.append('file', this.files[0]);

        fetch(`/api/event/${currentEventId}/attachment`, {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(() => {
            showEventDetails(currentEventId);
            this.value = '';
        })
        .catch(error => {
            console.error('Error uploading attachment:', error);
            alert('Failed to upload attachment');
        });
    };

    function updateEventTime(event) {
        const eventId = parseInt(event.id);
        const start = event.start;
        const end = event.end || event.start;

        fetch(`/api/event/${eventId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                start: start.toISOString(),
                end: end.toISOString(),
                allDay: event.allDay
            })
        })
        .then(response => response.json())
        .catch(error => {
            console.error('Error updating event time:', error);
            calendar.refetchEvents();
            alert('Failed to update event time');
        });
    }

    document.getElementById('upload-ics-btn').onclick = function() {
        const fileInput = document.getElementById('ics-file-input');
        if (!fileInput.files || fileInput.files.length === 0) {
            alert('Please select an ICS file');
            return;
        }

        const formData = new FormData();
        formData.append('file', fileInput.files[0]);

        const statusEl = document.getElementById('upload-status');
        statusEl.textContent = 'Uploading...';

        fetch('/api/upload/ics', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            statusEl.textContent = data.message || 'Upload successful';
            fileInput.value = '';
            calendar.refetchEvents();
            loadCategories(); 
            setTimeout(() => {
                statusEl.textContent = '';
            }, 3000);
        })
        .catch(error => {
            console.error('Error uploading ICS:', error);
            statusEl.textContent = 'Upload failed';
            setTimeout(() => {
                statusEl.textContent = '';
            }, 3000);
        });
    };

    window.onclick = function(event) {
        if (event.target.classList.contains('modal')) {
            event.target.style.display = 'none';
        }
    };
});
