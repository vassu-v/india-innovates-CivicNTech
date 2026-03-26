function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text || '';
  return div.innerHTML;
}

function markdownToHtml(text) {
  if (!text) return "";
  let html = text
    .replace(/\*\*(.*?)\*\*/g, '<b>$1</b>')
    .replace(/\*(.*?)\*/g, '<i>$1</i>')
    .replace(/\n\n/g, '<br><br>')
    .replace(/\n/g, '<br>');
  return html;
}

async function fetchData(url, options = {}) {
  try {
    const response = await fetch(url, options);
    if (!response.ok) throw new Error('Network response was not ok');
    return await response.json();
  } catch (error) {
    console.error('Fetch error:', error);
    return null;
  }
}

async function loadHome() {
  const stats = await fetchData('/api/stats');
  const digest = await fetchData('/api/digest');
  const clusters = await fetchData('/api/issues/clusters');
  const profile = await fetchData('/api/profile');
  const todo = await fetchData('/api/todo'); // Fetch todo items

  // Dynamic Date for Home
  const now = new Date();
  const hour = now.getHours();
  let greeting = "Good evening";
  if (hour < 12) greeting = "Good morning";
  else if (hour < 17) greeting = "Good afternoon";
  const homeGreeting = document.getElementById('home-greeting-text');
  if (homeGreeting) homeGreeting.innerText = greeting;

  const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
  const months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
  const homeDateDay = document.getElementById('home-date-day');
  const homeDateFull = document.getElementById('home-date-full');
  if (homeDateDay) homeDateDay.innerText = now.getDate();
  if (homeDateFull) homeDateFull.innerText = `${days[now.getDay()]} · ${months[now.getMonth()]} ${now.getFullYear()}`;

  if (profile) {
    document.getElementById('top-user-name').innerText = profile.name;
    document.getElementById('top-user-sub').innerText = `${profile.designation} · ${profile.ward_name}`;

    // Initials for avatar
    const nameParts = (profile.name || '').trim().split(/\s+/);
    const initials = nameParts.length > 1 ? (nameParts[0][0] + nameParts[nameParts.length - 1][0]) : (nameParts[0] ? nameParts[0][0] : '..');
    const initialsEl = document.getElementById('user-initials');
    if (initialsEl) initialsEl.innerText = initials.toUpperCase();

    // Show first name or the only name
    const displayName = nameParts.length > 1 ? nameParts.slice(0, -1).join(' ') : nameParts[0];
    document.getElementById('hero-user-name').innerText = displayName;
    document.getElementById('hero-user-meta').innerText = `${profile.designation} · ${profile.ward_name} · Term since ${profile.term_start}`;
  }

  if (digest) {
    // Update hero quick stats
    const hqs = document.querySelectorAll('.hqs-num');
    if (hqs.length >= 4) {
      hqs[0].innerText = digest.open_right_now.critical;
      hqs[1].innerText = digest.open_right_now.urgent;
      hqs[2].innerText = digest.open_right_now.total;
      hqs[3].innerText = digest.resolved.resolution_rate + '%';
    }

    // Update commitment page stats if they exist
    const statRed = document.querySelector('.stat-num.red');
    const statAmber = document.querySelector('.stat-num.amber');
    const statBlue = document.querySelector('.stat-num.blue');
    if (statRed) statRed.innerText = digest.open_right_now.critical;
    if (statAmber) statAmber.innerText = digest.open_right_now.urgent;
    if (statBlue) statBlue.innerText = digest.open_right_now.total;

    // Update Today at a Glance
    const rows = document.querySelectorAll('#page-home .home-digest-row');
    if (rows.length >= 5) {
      rows[0].querySelector('.hdr-val').innerText = digest.new_items.issues;
      rows[0].classList.add('clickable');
      rows[0].onclick = () => drillDown('New Complaints', 'new_items');

      rows[1].querySelector('.hdr-val').innerText = digest.became_overdue_this_week.length + ' tasks';
      rows[1].classList.add('clickable');
      rows[1].onclick = () => drillDown('Overdue Tasks', 'became_overdue');

      rows[2].querySelector('.hdr-val').innerText = digest.resolved.total;
      rows[2].classList.add('clickable');
      rows[2].onclick = () => drillDown('Resolved this week', 'resolved');

      rows[3].querySelector('.hdr-val').innerText = digest.new_items.commitments;
      rows[3].classList.add('clickable');
      rows[3].onclick = () => drillDown('New Commitments', 'new_commitments');

      rows[4].querySelector('.hdr-val').innerText = digest.most_overdue.title ? digest.most_overdue.days_overdue + ' days' : '0 days';
    }
  }

  if (stats) {
    // Update Patterns card (formerly under onclick commitments, now generic)
    const patternsContainer = document.getElementById('home-suggestions-content');
    if (patternsContainer && stats.all_time.most_reliable_contact) {
      let html = "";
      if (stats.all_time.most_reliable_contact) {
        html += `<div class="home-pattern"><div class="pdot" style="background:var(--green)"></div><div>${stats.all_time.most_reliable_contact}: Most reliable contact</div></div>`;
      }
      if (stats.all_time.avg_days_to_resolve > 0) {
        html += `<div class="home-pattern"><div class="pdot" style="background:var(--blue)"></div><div>Avg resolution: ${Math.round(stats.all_time.avg_days_to_resolve)} days</div></div>`;
      }
      if (stats.all_time.extension_rate > 10) {
        html += `<div class="home-pattern"><div class="pdot" style="background:var(--amber)"></div><div>High extension rate: ${Math.round(stats.all_time.extension_rate)}%</div></div>`;
      }
      if (html) patternsContainer.innerHTML = html;
    }
  }
  // loadClusters(); // Original call, now moved inside loadHome
  if (todo) {
    const todoContainer = document.querySelector('#page-home .home-grid .home-card[onclick*="todo"]');
    if (todoContainer) {
      const label = todoContainer.querySelector('.home-card-label').outerHTML;
      let html = label;
      const allItems = [...(todo.meeting_items || []), ...(todo.issue_items || [])].sort((a, b) => b.weight - a.weight);
      if (allItems.length === 0) {
        html += `<div style="color:#888;font-size:11px;padding:10px 0">No urgent items found</div>`;
      } else {
        allItems.slice(0, 4).forEach(item => {
          const overdueText = item.days_overdue > 0 ? `${item.days_overdue}d overdue` : (item.urgency || '');
          html += `<div class="home-urgent-item"><span class="hui-text">${escapeHtml(item.title)}</span><span class="hui-tag ${item.urgency === 'critical' ? '' : 'amber'}">${escapeHtml(item.ward) || 'Gen'} · ${escapeHtml(overdueText)}</span></div>`;
        });
      }
      todoContainer.innerHTML = html;
    }
  }

  if (clusters) {
    const container = document.querySelector('#page-home .home-card[onclick*="issues"]');
    if (container) {
      const label = container.querySelector('.home-card-label').outerHTML;
      let html = label;
      if (clusters.length === 0) {
        html += `<div style="color:#888;font-size:11px;padding:10px 0">No complaint clusters found</div>`;
      } else {
        clusters.slice(0, 4).forEach(c => {
          html += `
                  <div class="home-urgent-item">
                  <span class="hui-text">${escapeHtml(c.summary)}</span>
                  <span class="hui-tag ${c.urgency === 'critical' ? '' : 'amber'}">${escapeHtml(c.ward)} · ${escapeHtml(c.urgency)}</span>
                  </div>`;
        });
      }
      container.innerHTML = html;
    }
  }
  loadRecentMeetings();
}

async function loadClusters() {
  const clusters = await fetchData('/api/issues/clusters');
  if (clusters) {
    const container = document.querySelector('#page-home .home-card[onclick*="issues"]');
    if (container) {
      const label = container.querySelector('.home-card-label').outerHTML;
      let html = label;
      clusters.slice(0, 4).forEach(c => {
        html += `
                <div class="home-urgent-item">
                    <span class="hui-text">${escapeHtml(c.summary)}</span>
                    <span class="hui-tag ${c.urgency === 'critical' ? '' : 'amber'}">${escapeHtml(c.ward)} · ${escapeHtml(c.urgency)}</span>
                </div>`;
      });
      container.innerHTML = html;
    }
  }
}

async function uploadMeeting() {
  const fileInput = document.getElementById('meeting-file-input');
  const dateInput = document.getElementById('meeting-date');
  const typeInput = document.getElementById('meeting-type');
  const participantsInput = document.getElementById('meeting-participants');
  const notesInput = document.getElementById('meeting-notes');
  const btn = document.getElementById('meeting-upload-btn');
  const status = document.getElementById('meeting-upload-status');

  if (!fileInput.files[0]) return alert('Please select a transcript file (.txt)');
  if (!dateInput.value) return alert('Please select meeting date');

  const formData = new FormData();
  formData.append('file', fileInput.files[0]);
  formData.append('meeting_date', dateInput.value);
  formData.append('meeting_type', typeInput.value);
  if (participantsInput.value) formData.append('participants', participantsInput.value);
  if (notesInput.value) formData.append('notes', notesInput.value);

  btn.innerText = 'Processing...';
  btn.disabled = true;

  try {
    const res = await fetch('/api/upload/meeting', {
      method: 'POST',
      body: formData
    });
    const result = await res.json();
    if (res.ok) {
      status.innerText = `Success! ${result.extracted_count} items extracted from ${result.filename}.`;
      status.style.display = 'block';
      setTimeout(() => status.style.display = 'none', 5000);
      loadRecentMeetings();
      loadTodo();
      loadHome();
    } else {
      alert('Error: ' + result.detail);
    }
  } catch (e) {
    alert('Failed to upload: ' + e);
  } finally {
    btn.innerText = 'Upload and Process';
    btn.disabled = false;
  }
}

async function uploadContext() {
  const fileInput = document.getElementById('ctx-file-input');
  const labelInput = document.getElementById('ctx-label');
  const typeSelect = document.querySelector('#page-profile .upload-type.selected .upload-type-name');
  const btn = document.getElementById('ctx-upload-btn');

  if (!fileInput.files[0]) return alert('Please select a text file (.txt)');
  if (!labelInput.value) return alert('Please enter a label');

  const formData = new FormData();
  formData.append('file', fileInput.files[0]);
  formData.append('label', labelInput.value);
  formData.append('category', typeSelect.innerText);

  btn.innerText = 'Injecting...';
  btn.disabled = true;

  try {
    const res = await fetch('/api/upload/context', {
      method: 'POST',
      body: formData
    });
    const result = await res.json();
    if (res.ok) {
      document.getElementById('inject-confirm').style.display = 'block';
      setTimeout(() => document.getElementById('inject-confirm').style.display = 'none', 3000);
      loadContextFiles();
    } else {
      alert('Error: ' + result.detail);
    }
  } catch (e) {
    alert('Failed to inject: ' + e);
  } finally {
    btn.innerText = 'Inject into DB1';
    btn.disabled = false;
  }
}

async function loadContextFiles() {
  const files = await fetchData('/api/context/files');
  if (files) {
    const list = document.querySelector('#page-profile .uploaded-list');
    if (list) {
      list.innerHTML = files.map(f => `
        <div class="uploaded-item">
          <div>
            <div class="uploaded-name">${escapeHtml(f.label)} (${escapeHtml(f.filename)})</div>
            <div class="uploaded-meta">${escapeHtml(f.category)} · ${new Date(f.created_at).toLocaleDateString()}</div>
          </div>
          <span class="status-chip done">Active</span>
        </div>
      `).join('');
    }
  }
}

// Update initial load
document.addEventListener('DOMContentLoaded', () => {
  loadProfile();
  loadHome();
  loadContextFiles();
  if (document.getElementById('page-issues')) loadRecentComplaints();
});

async function loadTodo(filter = null) {
  let url = '/api/todo';
  const todo = await fetchData(url);
  if (todo) {
    let allItems = [...todo.meeting_items, ...todo.issue_items];

    // Apply frontend filter if provided
    if (filter && filter.urgency) {
      allItems = allItems.filter(i => i.urgency === filter.urgency);
    }

    const container = document.getElementById('page-todo');
    const title = container.querySelector('.page-title').outerHTML;
    const summaryText = `${allItems.length} ${filter ? filter.urgency : ''} pending`;
    const sub = `
    <div class="page-sub">
      <span id="todo-stats-summary">${summaryText}</span> · Ranked by weight
      <button class="gen-btn" style="float:right;margin:0;padding:4px 10px;font-size:10px" onclick="liveEscalate()">Live Escalate</button>
    </div>`;

    let html = title + sub;

    if (allItems.length === 0) {
      html += `<div style="color:#666;font-size:11px;padding:20px">No pending items found</div>`;
    }

    const renderItems = (items, label, className) => {
      if (items.length === 0) return '';
      let section = `<div class="section-label">${label}</div>`;
      items.forEach(item => {
        section += `
            <div class="todo-item ${className}">
              <div onclick="completeItem(${item.id})">
                <div class="todo-text">${escapeHtml(item.title)}</div>
                <div class="todo-meta">
                  ${escapeHtml(item.type)} · ${escapeHtml(item.ward) || 'General'}
                  ${item.deadline ? ` · <span style="opacity:0.8">Due: ${item.deadline}</span>` : item.meeting_date ? ` · <span style="opacity:0.8">Meeting: ${item.meeting_date}</span>` : ''}
                </div>
              </div>
              <div class="todo-right">
                <span class="tag ${className === 'c' ? 'red' : className === 'u' ? 'amber' : 'blue'}">${escapeHtml(item.urgency)}</span>
                ${item.days_overdue > 0 ? `<div class="overdue">▲ ${escapeHtml(item.days_overdue)} days overdue</div>` : ''}
                <button class="gen-btn" style="padding:2px 5px;font-size:8px;margin-top:5px" onclick="extendItem(${item.id})">Extend</button>
              </div>
            </div>`;
      });
      return section;
    };

    const critical = allItems.filter(i => i.urgency === 'critical');
    const urgent = allItems.filter(i => i.urgency === 'urgent');
    const normal = allItems.filter(i => i.urgency === 'normal');

    html += renderItems(critical, 'Critical', 'c');
    html += renderItems(urgent, 'Urgent', 'u');
    html += renderItems(normal, 'Normal', 'n');

    container.innerHTML = html;
  }
}

async function completeItem(id) {
  if (confirm('Mark this item as completed?')) {
    const res = await fetchData(`/api/item/${id}/complete`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ resolution_notes: "Completed via dashboard" })
    });
    if (res) {
      alert('Item completed!');
      loadTodo();
      loadHome();
      loadHistory(); // Also refresh history/commitments page
    }
  }
}

async function liveEscalate() {
  const btn = event.target;
  const originalText = btn.innerText;
  btn.innerText = "Escalating...";
  btn.disabled = true;
  try {
    const res = await fetchData('/api/escalate', { method: 'POST' });
    if (res) {
      loadTodo();
      loadHome();
    }
  } catch (e) {
    console.error('Escalation error:', e);
  }
  btn.innerText = originalText;
  btn.disabled = false;
}

async function extendItem(id) {
  const date = prompt("Enter new deadline (YYYY-MM-DD):");
  if (date) {
    const res = await fetchData(`/api/item/${id}/extend`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ new_deadline: date })
    });
    if (res) {
      alert('Deadline extended');
      loadTodo();
      loadHistory(); // Also refresh history/commitments page
    }
  }
}

async function loadHistory() {
  // 1. Fetch active commitments for the tracker
  const activeCommitments = await fetchData('/api/todo?type=commitment');
  const activeList = document.getElementById('active-commitments-list');
  if (activeCommitments && activeList) {
    let items = [...activeCommitments.meeting_items, ...activeCommitments.issue_items];
    if (items.length === 0) {
      activeList.innerHTML = '<div style="color:#666;font-size:11px;padding:20px">No active commitments found</div>';
    } else {
      activeList.innerHTML = items.map(item => `
            <div class="todo-item n" style="margin-bottom:10px">
              <div>
                <div class="todo-text">${escapeHtml(item.title)}</div>
                <div class="todo-meta">${escapeHtml(item.to_whom) || ''} · ${escapeHtml(item.ward) || 'General'} · Deadline: ${escapeHtml(item.deadline) || 'None'}</div>
              </div>
              <div class="todo-right">
                 <button class="gen-btn" style="padding:4px 8px;font-size:9px" onclick="completeItem(${item.id})">Mark Done</button>
              </div>
            </div>
          `).join('');
    }
  }

  // 2. Fetch history for the recently resolved section
  const history = await fetchData('/api/history');
  if (history) {
    const container = document.getElementById('page-commitments');
    let histDiv = document.getElementById('history-section');
    if (!histDiv) {
      histDiv = document.createElement('div');
      histDiv.id = 'history-section';
      container.appendChild(histDiv);
    }

    let html = '<div class="section-label">Recently Resolved</div><div class="issue-list">';
    history.items.slice(0, 10).forEach(item => {
      html += `
            <div class="issue-item closed">
                <div>
                    <div class="issue-text">${escapeHtml(item.title)}</div>
                    <div class="issue-meta">${escapeHtml(item.to_whom) || ''} · ${escapeHtml(item.ward) || 'General'} · Resolved ${item.completed_at ? escapeHtml(item.completed_at.split('T')[0]) : ''}</div>
                </div>
                <span class="tag green">Resolved</span>
            </div>`;
    });
    html += '</div>';
    histDiv.innerHTML = html;
  }
}

let globalDigestData = null;

async function loadDigestView() {
  const digest = await fetchData('/api/digest');
  globalDigestData = digest; // Store for drillDown
  if (digest) {
    // Dynamic Range
    const now = new Date();
    const lastWeek = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
    const options = { day: 'numeric', month: 'long' };
    const digestWeekRange = document.getElementById('digest-period');
    if (digestWeekRange) digestWeekRange.innerText = `Week of ${lastWeek.toLocaleDateString('en-IN', options)} – ${now.toLocaleDateString('en-IN', options)} ${now.getFullYear()}`;

    document.getElementById('dw-new-issues').innerText = digest.new_items.issues;
    document.getElementById('dw-resolved').innerText = digest.resolved.total;
    document.getElementById('dw-overdue').innerText = digest.became_overdue_this_week.length;
    document.getElementById('dw-new-commitments').innerText = digest.new_items.commitments;
    document.getElementById('dw-open-critical').innerText = digest.open_right_now.critical;
    document.getElementById('dw-open-urgent').innerText = digest.open_right_now.urgent;
  }
}

function drillDown(title, key) {
  if (!globalDigestData) return;
  let items = [];
  if (key === 'new_items') items = globalDigestData.new_items.items.filter(i => i.type === 'issue');
  if (key === 'new_commitments') items = globalDigestData.new_items.items.filter(i => i.type !== 'issue');
  if (key === 'resolved') items = globalDigestData.resolved.items;
  if (key === 'became_overdue') items = globalDigestData.became_overdue_this_week;

  showOverlay(title, items);
}

function showOverlay(title, items) {
  let overlay = document.getElementById('drilldown-overlay');
  if (!overlay) {
    overlay = document.createElement('div');
    overlay.id = 'drilldown-overlay';
    overlay.style = "position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.8);z-index:2000;display:flex;align-items:center;justify-content:center;padding:20px";
    overlay.innerHTML = `
          <div style="background:#111;width:100%;max-width:500px;max-height:80%;overflow:auto;border-radius:12px;padding:20px;border:1px solid #333">
            <div style="display:flex;justify-content:space-between;margin-bottom:15px">
              <div class="section-label" id="overlay-title" style="margin:0;color:var(--mid)"></div>
              <button onclick="document.getElementById('drilldown-overlay').style.display='none'" style="background:none;border:none;color:#888;cursor:pointer;font-size:16px">✕</button>
            </div>
            <div id="overlay-content" class="issue-list"></div>
          </div>
        `;
    document.body.appendChild(overlay);
  }

  document.getElementById('overlay-title').innerText = title;
  const content = document.getElementById('overlay-content');
  if (items.length === 0) {
    content.innerHTML = '<div style="color:#666;font-size:11px">No items found</div>';
  } else {
    content.innerHTML = items.map(item => `
          <div class="issue-item">
            <div>
              <div class="issue-text" style="color:#fff">${escapeHtml(item.title)}</div>
              <div class="issue-meta" style="color:#888">${escapeHtml(item.type)} · ${escapeHtml(item.ward) || 'General'} · ${escapeHtml(item.deadline) || 'No deadline'}</div>
            </div>
          </div>
        `).join('');
  }
  overlay.style.display = 'flex';
}

function goTodo(urgency) {
  goPage('todo', { urgency });
}

async function loadProfile() {
  const p = await fetchData('/api/profile');
  if (p) {
    if (document.getElementById('prof-name')) document.getElementById('prof-name').value = p.name;
    if (document.getElementById('prof-party')) document.getElementById('prof-party').value = p.party;
    if (document.getElementById('prof-designation')) document.getElementById('prof-designation').value = p.designation;
    if (document.getElementById('prof-term')) document.getElementById('prof-term').value = p.term_start;
    if (document.getElementById('prof-email')) document.getElementById('prof-email').value = p.email;
    if (document.getElementById('prof-contact')) document.getElementById('prof-contact').value = p.contact;
    if (document.getElementById('prof-ward-name')) document.getElementById('prof-ward-name').value = p.ward_name;
    if (document.getElementById('prof-state')) document.getElementById('prof-state').value = p.state;
    if (document.getElementById('prof-district')) document.getElementById('prof-district').value = p.district;
    if (document.getElementById('prof-wards-covered')) document.getElementById('prof-wards-covered').value = p.wards_covered;
    if (document.getElementById('prof-population')) document.getElementById('prof-population').value = p.population;
    if (document.getElementById('prof-voters')) document.getElementById('prof-voters').value = p.registered_voters;
    if (document.getElementById('prof-address')) document.getElementById('prof-address').value = p.office_address;
    if (document.getElementById('prof-jd-day')) document.getElementById('prof-jd-day').value = p.janata_darbar_day;
    if (document.getElementById('prof-jd-time')) document.getElementById('prof-jd-time').value = p.janata_darbar_time;
    if (document.getElementById('prof-pa-name')) document.getElementById('prof-pa-name').value = p.pa_name;
    if (document.getElementById('prof-pa-contact')) document.getElementById('prof-pa-contact').value = p.pa_contact;
    if (document.getElementById('prof-manager-name')) document.getElementById('prof-manager-name').value = p.manager_name;
    if (document.getElementById('prof-manager-contact')) document.getElementById('prof-manager-contact').value = p.manager_contact;
  }
}

async function saveProfile() {
  const data = {
    name: document.getElementById('prof-name').value,
    party: document.getElementById('prof-party').value,
    designation: document.getElementById('prof-designation').value,
    term_start: document.getElementById('prof-term').value,
    email: document.getElementById('prof-email').value,
    contact: document.getElementById('prof-contact').value,
    ward_name: document.getElementById('prof-ward-name').value,
    state: document.getElementById('prof-state').value,
    district: document.getElementById('prof-district').value,
    wards_covered: document.getElementById('prof-wards-covered').value,
    population: document.getElementById('prof-population').value,
    registered_voters: document.getElementById('prof-voters').value,
    office_address: document.getElementById('prof-address').value,
    janata_darbar_day: document.getElementById('prof-jd-day').value,
    janata_darbar_time: document.getElementById('prof-jd-time').value,
    pa_name: document.getElementById('prof-pa-name').value,
    pa_contact: document.getElementById('prof-pa-contact').value,
    manager_name: document.getElementById('prof-manager-name').value,
    manager_contact: document.getElementById('prof-manager-contact').value
  };

  const res = await fetchData('/api/profile', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });

  if (res) {
    document.getElementById('prof-confirm').style.display = 'block';
    setTimeout(() => { document.getElementById('prof-confirm').style.display = 'none'; }, 3000);
    loadHome();
  }
}

function go(tab, page, filter = null) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
  const targetPage = document.getElementById('page-' + page);
  if (targetPage) targetPage.classList.add('active');
  if (tab) tab.classList.add('active');

  if (page === 'home') loadHome();
  if (page === 'todo') loadTodo(filter);
  if (page === 'commitments') loadHistory();
  if (page === 'digest') loadDigestView();
  if (page === 'profile') loadProfile();
  if (page === 'upload') loadRecentMeetings();
}

function goPage(page, filter = null) {
  const tab = document.querySelector(`.nav-tab[onclick*="'${page}'"]`);
  go(tab, page, filter);
}

async function logIssue() {
  const form = document.getElementById('page-issues');
  const name = form.querySelector('input[placeholder="Full name"]').value;
  const contact = form.querySelector('input[placeholder="Mobile number"]').value;
  const ward = form.querySelector('input[placeholder*="Ward"]').value;
  const via = form.querySelector('select').value;
  const description = form.querySelector('textarea').value;

  if (!description) return alert('Please enter a description');

  const res = await fetchData('/api/complaint', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      citizen_name: name,
      citizen_contact: contact,
      ward: ward,
      channel: via,
      complaint_text: description,
      date_received: new Date().toISOString().split('T')[0]
    })
  });

  if (res) {
    document.getElementById('submit-confirm').style.display = 'block';
    setTimeout(() => document.getElementById('submit-confirm').style.display = 'none', 3000);
    form.querySelectorAll('input').forEach(i => i.value = '');
    form.querySelector('textarea').value = '';
    loadTodo();
    loadRecentComplaints();
  }
}

async function loadRecentComplaints() {
  const complaints = await fetchData('/api/complaints/recent');
  if (complaints) {
    const list = document.getElementById('recent-complaints-list');
    if (list) {
      if (complaints.length === 0) {
        list.innerHTML = '<div style="color:#666;font-size:11px;padding:20px">No recent entries</div>';
      } else {
        list.innerHTML = complaints.map(c => `
              <div class="issue-item">
                <div>
                  <div class="issue-text">${escapeHtml(c.raw_description)}</div>
                  <div class="issue-meta">${escapeHtml(c.citizen_name) || 'Anonymous'} · ${escapeHtml(c.ward) || 'General'} · Received ${escapeHtml(c.date_received) || 'N/A'}</div>
                </div>
                <span class="tag ${c.status === 'pending' ? 'blue' : 'green'}">${escapeHtml(c.status)}</span>
              </div>
            `).join('');
      }
    }
  }
}

let currentSuggestionsTrace = [];

async function generateSuggestions(autoThink = false) {
  const qInput = document.getElementById('sug-query');
  if (autoThink && qInput) qInput.value = ""; // Clear for autonomous mode
  const query = qInput ? qInput.value.trim() : null;

  const btn = document.getElementById('sug-gen-btn');
  const autoBtn = document.getElementById('sug-auto-btn');
  const resultsDiv = document.getElementById('sug-results');
  const traceContainer = document.getElementById('sug-trace-container');
  const traceContent = document.getElementById('trace-content');
  const traceSummary = document.getElementById('trace-summary');
  const followupArea = document.getElementById('sug-followup-area');

  const mainBtnText = btn.innerText;
  btn.innerText = 'Analysing...';
  btn.disabled = true;
  if (autoBtn) autoBtn.disabled = true;

  resultsDiv.innerHTML = '';
  resultsDiv.style.display = 'none';
  traceContainer.style.display = 'none';
  followupArea.style.display = 'none';
  
  currentSuggestionsTrace = [];

  try {
    const data = await fetchData('/api/suggestions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: query || null })
    });
    
    if (data && data.suggestions) {
      currentSuggestionsTrace = data.thinking_trace || [];
      renderSuggestions(data.suggestions, false);
      renderThinkingTrace(data);
      followupArea.style.display = 'block';
    } else {
      resultsDiv.innerHTML = '<div style="color:#666;font-size:11px;padding:20px">No suggestions generated.</div>';
      resultsDiv.style.display = 'block';
    }
  } catch (e) {
    console.error(e);
  } finally {
    btn.innerText = mainBtnText;
    btn.disabled = false;
    if (autoBtn) autoBtn.disabled = false;
  }
}

function toggleTrace() {
  const content = document.getElementById('trace-content');
  const arrow = document.querySelector('.trace-arrow');
  if (content.style.display === 'none') {
    content.style.display = 'block';
    arrow.innerText = '▲';
  } else {
    content.style.display = 'none';
    arrow.innerText = '▼';
  }
}

function showSug() {
  goPage('suggestions');
  const results = document.getElementById('sug-results');
  const btn = document.getElementById('sug-gen-btn');
  // Only auto-trigger if no results present and not already loading
  if (results.children.length === 0 && !btn.disabled) {
    generateSuggestions();
  }
}

function toggleDigest(btn, type) {
  document.querySelectorAll('.d-toggle-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  document.getElementById('digest-daily').style.display = type === 'daily' ? 'block' : 'none';
  document.getElementById('digest-weekly').style.display = type === 'weekly' ? 'block' : 'none';
}

function selectType(el) {
  document.querySelectorAll('.upload-type').forEach(t => t.classList.remove('selected'));
  el.classList.add('selected');
}

function fakeSave() {
  document.getElementById('save-confirm').style.display = 'block';
  setTimeout(() => document.getElementById('save-confirm').style.display = 'none', 3000);
}

function fakeInject() {
  document.getElementById('inject-confirm').style.display = 'block';
  setTimeout(() => document.getElementById('inject-confirm').style.display = 'none', 3000);
}

function selectCtx(el) {
  el.closest('.upload-type-row').querySelectorAll('.upload-type').forEach(t => t.classList.remove('selected'));
  el.classList.add('selected');
}

async function loadRecentMeetings() {
  const meetings = await fetchData('/api/meetings/recent');
  if (meetings) {
    const list = document.querySelector('#page-upload .uploaded-list');
    if (list) {
      if (meetings.length === 0) {
        list.innerHTML = '<div style="color:#666;font-size:11px;padding:20px">No recent meetings found</div>';
      } else {
        list.innerHTML = meetings.map(m => `
              <div class="uploaded-item">
                <div>
                  <div class="uploaded-name">${m.source_id} — ${m.meeting_date || 'N/A'}</div>
                  <div class="uploaded-meta">${m.commitments} commitments extracted</div>
                </div>
                <span class="status-chip done">Processed</span>
              </div>
            `).join('');
      }
    }
  }
}

let currentWorkingMemory = [];
let chatHistory = [];
let currentStrategicContext = null;

async function sendChat() {
  const input = document.querySelector('.chat-input');
  const log = document.querySelector('.chat-log');
  const query = input.value.trim();
  if (!query) return;

  // Add user message
  const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  const userMsg = document.createElement('div');
  userMsg.className = 'msg';
  userMsg.innerHTML = `
    <div class="msg-from">You · ${time}</div>
    <div class="bubble you">${escapeHtml(query)}</div>
  `;
  log.appendChild(userMsg);
  input.value = '';
  log.scrollTop = log.scrollHeight;

  // Show thinking
  const aiMsg = document.createElement('div');
  aiMsg.className = 'msg';
  aiMsg.innerHTML = `
    <div class="msg-from">Co-Pilot · ${time}</div>
    <div class="bubble ai thinking">Thinking across all databases...</div>
  `;
  log.appendChild(aiMsg);
  log.scrollTop = log.scrollHeight;

  const res = await fetchData('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query: query,
      working_memory: currentWorkingMemory,
      history: chatHistory,
      strategic_context: currentStrategicContext
    })
  });

  // Track user message
  chatHistory.push({ role: 'user', content: query });

  if (res) {
    // Update working memory for next turn
    if (res.working_memory) {
      currentWorkingMemory = res.working_memory;
    }

    const bubble = aiMsg.querySelector('.bubble');
    bubble.classList.remove('thinking');

    if (res.routed === "instant") {
      bubble.classList.add('instant');
      bubble.style.borderLeft = "4px solid #4ade80"; // Subtle indicator for instant
    } else if (res.routed === "follow-up") {
      bubble.style.borderLeft = "4px solid #60a5fa"; // Blue for follow-up intelligence
    }

    bubble.innerHTML = markdownToHtml(res.response);
    
    // Track AI message
    chatHistory.push({ role: 'ai', content: res.response });
    
    if (res.sources && res.sources.length > 0) {
      const sourcesDiv = document.createElement('div');
      sourcesDiv.className = 'sources';
      sourcesDiv.innerHTML = 'Sources: ' + res.sources.map(s => `
        <span class="src-chip" title="${escapeHtml(s.domain)}">${escapeHtml(s.title)}</span>
      `).join('');
      aiMsg.appendChild(sourcesDiv);
    }
  } else {
    aiMsg.querySelector('.bubble').innerText = "Sorry, I'm having trouble connecting to my brain right now.";
  }
  log.scrollTop = log.scrollHeight;
}

async function sendSuggestionsFollowup() {
  const input = document.getElementById('sug-chat-input');
  const query = input.value.trim();
  if (!query) return;

  const resultsDiv = document.getElementById('sug-results');
  const traceSummary = document.getElementById('trace-summary');
  
  traceSummary.innerText = 'Refining analysis...';
  // UI indicator
  const btn = document.querySelector('#sug-followup-area .gen-btn');
  btn.innerText = 'Refining...';
  btn.disabled = true;

  try {
    const data = await fetchData('/api/suggestions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        query: query,
        history: currentSuggestionsTrace
      })
    });

    if (data && data.suggestions) {
      // Append new suggestions
      renderSuggestions(data.suggestions, true);
      // Update global trace
      currentSuggestionsTrace = data.thinking_trace || [];
      renderThinkingTrace(data);
    }
  } catch (e) {
    console.error(e);
  } finally {
    btn.innerText = 'Analyze & Append';
    btn.disabled = false;
    input.value = '';
    input.focus();
  }
}

function renderSuggestions(suggestions, append) {
  const resultsDiv = document.getElementById('sug-results');
  const html = suggestions.map((s, idx) => `
    <div class="suggestion ${s.priority || 'normal'}" style="animation: fadeIn 0.5s ease-out">
      <div class="sug-title">${append ? 'REFINED' : '0' + (idx+1)} — ${escapeHtml(s.title)}</div>
      <div class="sug-body">${markdownToHtml(s.body)}</div>
    </div>
  `).join('');
  
  if (append) {
    resultsDiv.innerHTML += `<div class="section-label" style="margin: 20px 0">Refined Insights</div>` + html;
  } else {
    resultsDiv.innerHTML = html;
  }
  
  // Bridge Button: Take to Chat
  if (!document.getElementById('sug-chat-bridge')) {
    const bridge = document.createElement('div');
    bridge.id = 'sug-chat-bridge';
    bridge.style.padding = "20px 0";
    bridge.innerHTML = `
      <button class="gen-btn btn-alt" style="width: auto; padding: 10px 25px; margin: 0 auto; display: block;" onclick="transferSuggestionsToChat()">
        Take this Conversation to Chat →
      </button>
    `;
    resultsDiv.appendChild(bridge);
  }

  resultsDiv.style.display = 'block';
}

function renderThinkingTrace(data) {
  const traceContainer = document.getElementById('sug-trace-container');
  const traceContent = document.getElementById('trace-content');
  const traceSummary = document.getElementById('trace-summary');

  if (data.thinking_trace) {
    traceSummary.innerText = data.context_summary || 'Analysis complete';
    traceContent.innerHTML = data.thinking_trace.map(t => `
      <div class="trace-entry">
        <div class="trace-meta">Round ${t.round} · ${t.type} · ${new Date(t.timestamp).toLocaleTimeString()}</div>
        <div class="trace-text">${escapeHtml(t.content)}</div>
        ${t.tool ? `<div class="trace-tool">Tool: ${t.tool}(${t.args})</div>` : ''}
      </div>
    `).join('');
    traceContainer.style.display = 'block';
  }
}

async function transferSuggestionsToChat() {
  // Capture ALL refinements (thinking trace) and results
  const refinements = currentSuggestionsTrace.map(t => `Round ${t.round} (${t.type}): ${t.content}`).join("\n\n");
  
  // Also capture the actual suggestions visible in UI
  const suggestionsDiv = document.getElementById('sug-results');
  const suggestionsText = suggestionsDiv ? suggestionsDiv.innerText : "";

  currentStrategicContext = `=== PRIOR STRATEGIC ANALYSIS ===\n${suggestionsText}\n\n=== REFINEMENTS & THINKING TRACE ===\n${refinements}`;
  
  const log = document.querySelector('.chat-log');
  const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  const bridgeMsg = document.createElement('div');
  bridgeMsg.className = 'msg';
  bridgeMsg.innerHTML = `
    <div class="msg-from">Co-Pilot · System Bridge · ${time}</div>
    <div class="bubble ai" style="border-left: 4px solid var(--accent); font-size: 0.9em; opacity: 0.9;">
      <strong>Strategic Context & Refinements Transferred:</strong> I have imported the full iterative analysis and suggested interventions. How should we proceed with these insights?
    </div>
  `;
  log.appendChild(bridgeMsg);
  
  const input = document.querySelector('.chat-input');
  input.value = "Let's discuss the strategic insights and refinements you just generated.";
  
  goPage('chat');
  input.focus();
}

// Wire up chat event listeners
document.addEventListener('DOMContentLoaded', () => {
  const sendBtn = document.querySelector('.chat-send');
  const input = document.querySelector('.chat-input');
  if (sendBtn) sendBtn.onclick = sendChat;
  if (input) {
    input.onkeypress = (e) => { if (e.key === 'Enter') sendChat(); };
  }
  
  // Suggestions Enter Listeners
  const sugQuery = document.getElementById('sug-query');
  if (sugQuery) {
    sugQuery.onkeypress = (e) => { if (e.key === 'Enter') generateSuggestions(); };
  }
  const sugChat = document.getElementById('sug-chat-input');
  if (sugChat) {
    sugChat.onkeypress = (e) => { if (e.key === 'Enter') sendSuggestionsFollowup(); };
  }

  // Auto-Think button
  const autoBtn = document.getElementById('sug-auto-btn');
  if (autoBtn) autoBtn.onclick = () => generateSuggestions(true);
});
