/**
 * HailyDB Dashboard JavaScript
 * Focused on data integrity verification and system monitoring
 */

// Global variables
let dashboardData = {};
let lastShownResult = null;
let currentTimeMode = 'spc'; // Track current time mode selection - default to SPC Day

// Initialize dashboard
function initializeDashboard() {
    try {
        // Load dashboard data from script tag
        const dataElement = document.getElementById('dashboard-data');
        if (dataElement) {
            const dataText = dataElement.textContent.trim();
            if (dataText) {
                dashboardData = JSON.parse(dataText);
            }
        }
        
        // Ensure dashboardData has default values
        dashboardData = dashboardData || {};
        dashboardData.scheduler_running = dashboardData.scheduler_running || false;
        
        // Update status indicator
        updateStatusIndicator();
        
        // Calculate next poll time
        updateNextPollTime();
        
        // Load today's data for cron verification - use current mode
        loadTodaysAlertsWithMode(currentTimeMode);
        loadSPCVerificationTable();
        
        // Initialize world clock
        updateWorldClock();
        setInterval(updateWorldClock, 1000); // Update every second
        
        // Initialize time mode toggle
        initializeTimeModeToggle();
        
        // Set up automatic refresh every 30 seconds
        setInterval(() => {
            loadTodaysAlertsWithMode(currentTimeMode); // Use current mode instead of default
            loadSPCVerificationTable();
            updateStatusIndicator();
            updateNextPollTime();
            updateLastUpdateTime();
        }, 30000);
        
        // Start autonomous scheduler automatically
        startAutonomousScheduler();
        
        console.log('Dashboard initialized successfully');
    } catch (error) {
        console.error('Error initializing dashboard:', error);
        dashboardData = {
            scheduler_running: false
        };
    }
}

// Update status indicators and control buttons with real-time countdown
function updateStatusIndicator() {
    const statusElement = document.getElementById('scheduler-status');
    const playButton = document.getElementById('scheduler-play-btn');
    const pauseButton = document.getElementById('scheduler-pause-btn');
    const progressDiv = document.getElementById('ingestion-progress');
    const progressText = document.getElementById('progress-text');
    const progressBar = document.getElementById('progress-bar');
    const countdownDiv = document.getElementById('next-ingestion-countdown');
    const countdownTimer = document.getElementById('countdown-timer');
    const lastResultDiv = document.getElementById('last-ingestion-result');
    const resultText = document.getElementById('result-text');
    
    // Get current scheduler status from server
    fetch('/internal/scheduler/status')
        .then(response => response.json())
        .then(data => {
            const isRunning = data.success && data.scheduler && data.scheduler.running;
            const scheduler = data.scheduler || {};
            
            if (statusElement) {
                if (isRunning) {
                    statusElement.className = 'text-success me-2 font-weight-bold';
                    statusElement.innerHTML = '<i class="fas fa-play-circle me-1"></i>Running';
                } else {
                    statusElement.className = 'text-danger me-2 font-weight-bold';
                    statusElement.innerHTML = '<i class="fas fa-stop-circle me-1"></i>Stopped';
                }
            }
            
            // Update button visibility
            if (playButton && pauseButton) {
                if (isRunning) {
                    playButton.style.display = 'none';
                    pauseButton.style.display = 'inline-block';
                } else {
                    playButton.style.display = 'inline-block';
                    pauseButton.style.display = 'none';
                }
            }
            
            // Update countdown and progress
            if (isRunning && scheduler.next_countdown !== undefined) {
                const countdown = scheduler.next_countdown;
                const operation = scheduler.next_operation || 'operation';
                
                if (countdownDiv && countdownTimer) {
                    countdownDiv.style.display = 'block';
                    const nextTime = new Date(Date.now() + countdown * 1000);
                    const timeString = nextTime.toLocaleTimeString('en-US', { 
                        hour: 'numeric', 
                        minute: '2-digit',
                        hour12: true 
                    });
                    countdownTimer.textContent = `${timeString} (${operation})`;
                }
                
                // Update NWS progress bar
                if (progressDiv && progressText && progressBar) {
                    progressDiv.style.display = 'block';
                    
                    if (countdown <= 30 && countdown > 0 && operation === 'nws') {
                        progressText.textContent = `Starting NWS ingestion...`;
                        const progress = ((30 - countdown) / 30) * 100;
                        progressBar.style.width = `${progress}%`;
                        progressBar.className = 'progress-bar progress-bar-striped progress-bar-animated bg-warning';
                    } else {
                        const totalInterval = 300; // 5 minutes for NWS
                        const elapsed = totalInterval - countdown;
                        const progress = (elapsed / totalInterval) * 100;
                        progressText.textContent = `Waiting for next NWS ingestion...`;
                        progressBar.style.width = `${progress}%`;
                        progressBar.className = 'progress-bar bg-info';
                    }
                }
                
                // Update SPC progress bar
                const spcProgressDiv = document.getElementById('spc-progress');
                const spcProgressText = document.getElementById('spc-progress-text');
                const spcProgressBar = document.getElementById('spc-progress-bar');
                
                if (spcProgressDiv && spcProgressText && spcProgressBar) {
                    spcProgressDiv.style.display = 'block';
                    
                    if (countdown <= 30 && countdown > 0 && operation === 'spc') {
                        spcProgressText.textContent = `Starting SPC ingestion...`;
                        const progress = ((30 - countdown) / 30) * 100;
                        spcProgressBar.style.width = `${progress}%`;
                        spcProgressBar.className = 'progress-bar bg-warning progress-bar-striped progress-bar-animated';
                    } else {
                        const totalInterval = 300; // 5 minutes for SPC too
                        const elapsed = totalInterval - countdown;
                        const progress = (elapsed / totalInterval) * 100;
                        spcProgressText.textContent = `Waiting for next SPC ingestion...`;
                        spcProgressBar.style.width = `${progress}%`;
                        spcProgressBar.className = 'progress-bar bg-warning';
                    }
                }
                
                // Update SPC countdown
                const spcCountdownDiv = document.getElementById('spc-countdown');
                const spcCountdownTimer = document.getElementById('spc-countdown-timer');
                
                if (spcCountdownDiv && spcCountdownTimer) {
                    spcCountdownDiv.style.display = 'block';
                    const nextTime = new Date(Date.now() + countdown * 1000);
                    const timeString = nextTime.toLocaleTimeString('en-US', { 
                        hour: 'numeric', 
                        minute: '2-digit',
                        hour12: true 
                    });
                    // SPC should show "spc" operation type since both run together
                    const spcOperation = operation === 'nws' ? 'spc' : operation;
                    spcCountdownTimer.textContent = `${timeString} (${spcOperation})`;
                }
                
                // Show NWS last ingestion result
                if (lastResultDiv && resultText && scheduler.last_nws_operation) {
                    lastResultDiv.style.display = 'block';
                    const lastOp = scheduler.last_nws_operation;
                    const lastTime = new Date(lastOp.completed_at).toLocaleTimeString('en-US', {
                        hour: 'numeric',
                        minute: '2-digit',
                        hour12: true
                    });
                    
                    if (lastOp.success) {
                        resultText.className = 'text-success';
                        resultText.textContent = `Last Ingestion: ${lastOp.records_new} Alerts at ${lastTime}`;
                    } else {
                        resultText.className = 'text-danger';
                        resultText.textContent = `Last Ingestion: Failed at ${lastTime}`;
                    }
                }
                
                // Show SPC last ingestion result
                const spcLastResultDiv = document.getElementById('spc-last-result');
                const spcResultText = document.getElementById('spc-result-text');
                
                if (spcLastResultDiv && spcResultText && scheduler.last_spc_operation) {
                    spcLastResultDiv.style.display = 'block';
                    const lastOp = scheduler.last_spc_operation;
                    const lastTime = new Date(lastOp.completed_at).toLocaleTimeString('en-US', {
                        hour: 'numeric',
                        minute: '2-digit',
                        hour12: true
                    });
                    
                    if (lastOp.success) {
                        spcResultText.className = 'text-success';
                        spcResultText.textContent = `Last Ingestion: ${lastOp.records_new} Reports at ${lastTime}`;
                    } else {
                        spcResultText.className = 'text-danger';
                        spcResultText.textContent = `Last Ingestion: Failed at ${lastTime}`;
                    }
                }
                // Update SPC status display
                const spcStatusElement = document.getElementById('spc-status');
                if (spcStatusElement) {
                    if (scheduler.running) {
                        spcStatusElement.className = 'text-success me-2 font-weight-bold';
                        spcStatusElement.innerHTML = '<i class="fas fa-play-circle me-1"></i>Running';
                    } else {
                        spcStatusElement.className = 'text-danger me-2 font-weight-bold';
                        spcStatusElement.innerHTML = '<i class="fas fa-stop-circle me-1"></i>Stopped';
                    }
                }
                
            } else {
                if (countdownDiv) countdownDiv.style.display = 'none';
                if (progressDiv) progressDiv.style.display = 'none';
                if (lastResultDiv) lastResultDiv.style.display = 'none';
                
                // Hide SPC displays too
                const spcProgressDiv = document.getElementById('spc-progress');
                const spcCountdownDiv = document.getElementById('spc-countdown');
                const spcLastResultDiv = document.getElementById('spc-last-result');
                const spcStatusElement = document.getElementById('spc-status');
                
                if (spcProgressDiv) spcProgressDiv.style.display = 'none';
                if (spcCountdownDiv) spcCountdownDiv.style.display = 'none';
                if (spcLastResultDiv) spcLastResultDiv.style.display = 'none';
                if (spcStatusElement) {
                    spcStatusElement.className = 'text-danger me-2 font-weight-bold';
                    spcStatusElement.innerHTML = '<i class="fas fa-stop-circle me-1"></i>Stopped';
                }
            }

        })
        .catch(error => {
            console.error('Error fetching scheduler status:', error);
            if (statusElement) {
                statusElement.className = 'text-warning me-2 font-weight-bold';
                statusElement.innerHTML = '<i class="fas fa-exclamation-circle me-1"></i>Unknown';
            }
            if (countdownDiv) countdownDiv.style.display = 'none';
            if (progressDiv) progressDiv.style.display = 'none';
        });
}

// Calculate and display next poll time
function updateNextPollTime() {
    const nextPollElement = document.getElementById('next-poll-time');
    if (nextPollElement) {
        const now = new Date();
        const nextPoll = new Date(now.getTime() + (5 * 60 * 1000)); // 5 minutes from now
        nextPollElement.textContent = nextPoll.toLocaleTimeString();
    }
}

// Load today's alerts for cron verification


// Pagination function for dashboard alerts
function changePage(page) {
    if (!window.dashboardAlertsData) return;
    
    const { sortedAlerts, totalPages, alertsPerPage } = window.dashboardAlertsData;
    
    if (page < 1 || page > totalPages) return;
    
    const start = (page - 1) * alertsPerPage;
    const end = start + alertsPerPage;
    const pageAlerts = sortedAlerts.slice(start, end);
    
    let pageHtml = '';
    pageAlerts.forEach(alert => {
        const dateTime = new Date(alert.effective).toLocaleString();
        const severityBadge = getSeverityColor(alert.severity);
        const shortArea = alert.area_desc ? 
            (alert.area_desc.length > 50 ? alert.area_desc.substring(0, 50) + '...' : alert.area_desc) : 
            'N/A';
        
        pageHtml += `<tr>
            <td>${dateTime}</td>
            <td><span class="badge bg-${severityBadge}">${alert.severity || 'N/A'}</span></td>
            <td>${alert.event}</td>
            <td>${shortArea}</td>
            <td><a href="/alert/${alert.id}" class="btn btn-sm btn-outline-primary">View Details</a></td>
        </tr>`;
    });
    
    document.getElementById('alerts-tbody').innerHTML = pageHtml;
    
    // Update pagination buttons
    const paginationItems = document.querySelectorAll('.pagination .page-item');
    paginationItems.forEach(item => {
        item.classList.remove('active', 'disabled');
        const link = item.querySelector('.page-link');
        if (link && link.textContent == page) {
            item.classList.add('active');
        }
    });
    
    // Update previous/next buttons
    const prevButton = document.querySelector('.pagination .page-item:first-child');
    const nextButton = document.querySelector('.pagination .page-item:last-child');
    
    if (page === 1 && prevButton) {
        prevButton.classList.add('disabled');
    }
    if (page === totalPages && nextButton) {
        nextButton.classList.add('disabled');
    }
    
    // Update stored current page
    window.dashboardAlertsData.currentPage = page;
}

// Load SPC verification data (initial load only)
async function loadSPCVerificationTable() {
    try {
        const today = new Date().toISOString().split('T')[0];
        const response = await fetch(`/api/spc/reports?format=json`);
        const data = await response.json();
        
        const container = document.getElementById('todays-spc-events');
        if (!container) return;
        
        // Force refresh verification data every time (no caching)
        // This ensures accurate real-time counts without stale data display
        
        // Get verification data with cache-busting to ensure fresh data
        const timestamp = new Date().getTime();
        const verifyResponse = await fetch(`/internal/spc-verify-today?_t=${timestamp}`, {
            cache: 'no-cache',
            headers: {
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            }
        });
        const verifyData = await verifyResponse.json();
        
        if (verifyData.status === 'success' && verifyData.results) {
            let html = '<div class="table-responsive"><table class="table table-sm">';
            html += '<thead><tr><th>Date</th><th>HailyDB</th><th>SPC Live</th><th>Status</th><th>Action</th></tr></thead>';
            html += '<tbody>';
            
            verifyData.results.forEach(result => {
                const statusBadge = result.match_status === 'MATCH' 
                    ? '<span class="badge bg-success">MATCH</span>'
                    : result.match_status === 'MISMATCH'
                    ? '<span class="badge bg-danger">MISMATCH</span>'
                    : '<span class="badge bg-warning">PENDING</span>';
                    
                const spcCount = result.spc_live_count !== null ? result.spc_live_count : 'N/A';
                
                // Use green badges when counts match
                const hailyBadgeClass = result.match_status === 'MATCH' ? 'bg-success' : 'bg-primary';
                const spcBadgeClass = result.match_status === 'MATCH' ? 'bg-success' : 'bg-secondary';
                
                html += `<tr>
                    <td>${result.date}</td>
                    <td><span class="badge ${hailyBadgeClass}">${result.hailydb_count}</span></td>
                    <td><span class="badge ${spcBadgeClass}">${spcCount}</span></td>
                    <td>${statusBadge}</td>
                    <td><button class="btn btn-sm btn-outline-primary" onclick="forceReingestion('${result.date}', this)" title="Force re-ingestion for this date" data-date="${result.date}">
                        <i class="fas fa-sync-alt"></i>
                    </button></td>
                </tr>`;
            });
            
            html += '</tbody></table></div>';
            
            if (verifyData.last_updated) {
                html += `<div class="text-center mt-2">
                    <button class="btn btn-sm btn-outline-secondary me-2" onclick="loadNextWeek()">
                        <i class="fas fa-calendar-plus me-1"></i>Load Next Week
                    </button>
                    <small class="text-muted">Last verified: ${new Date(verifyData.last_updated).toLocaleTimeString()}</small>
                </div>`;
            }
            
            container.innerHTML = html;
        } else {
            container.innerHTML = '<div class="text-center py-3"><div class="h5 text-warning">Error</div><small class="text-muted">Unable to verify SPC data</small></div>';
        }
    } catch (error) {
        console.error('Error loading today\'s SPC events:', error);
        const container = document.getElementById('todays-spc-events');
        if (container) {
            container.innerHTML = '<p class="text-danger">Error loading today\'s SPC events.</p>';
        }
    }
}

// Load next week of SPC verification data
async function refreshSPCVerificationData() {
    console.log('[REFRESH] Reloading verification data after re-ingestion...');
    
    try {
        // Get current date range from existing table
        const container = document.getElementById('todays-spc-events');
        if (!container) {
            console.error('[REFRESH] SPC verification container not found');
            return;
        }
        
        const tbody = container.querySelector('tbody');
        if (!tbody) {
            console.error('[REFRESH] Table body not found');
            return;
        }
        
        // Get existing date range
        const rows = tbody.querySelectorAll('tr');
        if (rows.length === 0) {
            console.log('[REFRESH] No existing rows to refresh');
            return;
        }
        
        const dates = Array.from(rows).map(row => {
            const firstCell = row.querySelector('td');
            return firstCell ? firstCell.textContent.trim() : null;
        }).filter(date => date);
        
        if (dates.length === 0) {
            console.log('[REFRESH] No valid dates found');
            return;
        }
        
        // Sort dates to get range
        dates.sort();
        const startDate = dates[0];
        const endDate = dates[dates.length - 1];
        
        console.log(`[REFRESH] Refreshing data from ${startDate} to ${endDate}`);
        
        // Fetch fresh verification data with JSON format
        const response = await fetch(`/internal/spc-verify?start_date=${startDate}&end_date=${endDate}&format=json`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        console.log('[REFRESH] Fresh verification data received:', data);
        
        if (data.results && data.results.length > 0) {
            // Clear existing table and rebuild with fresh data
            tbody.innerHTML = '';
            
            // Sort results by date (newest first)
            data.results.sort((a, b) => new Date(b.date) - new Date(a.date));
            
            // Add all rows with fresh data
            data.results.forEach(result => {
                const statusBadge = result.match_status === 'MATCH' 
                    ? '<span class="badge bg-success">MATCH</span>'
                    : result.match_status === 'MISMATCH'
                    ? '<span class="badge bg-danger">MISMATCH</span>'
                    : result.match_status === 'SPC_UNAVAILABLE'
                    ? '<span class="badge bg-warning">SPC_UNAVAILABLE</span>'
                    : '<span class="badge bg-secondary">PENDING</span>';
                
                const spcCount = result.spc_live_count !== null ? result.spc_live_count : 'N/A';
                const dateForUrl = result.date.replace(/-/g, '').slice(2); // Convert 2025-05-21 to 250521
                const externalLink = `<a href="https://www.spc.noaa.gov/climo/reports/${dateForUrl}_rpts.html" target="_blank" class="btn btn-xs btn-outline-primary me-1">
                    <i class="fas fa-external-link-alt"></i>
                </a>`;
                const reuploadButton = result.match_status === 'MISMATCH' ? 
                    `<button class="btn btn-xs btn-outline-warning" onclick="forceReingestion('${result.date}', this)">
                        <i class="fas fa-sync-alt"></i>
                    </button>` : 
                    `<button class="btn btn-xs btn-outline-secondary" disabled>
                        <i class="fas fa-check"></i>
                    </button>`;
                const actionButtons = externalLink + reuploadButton;
                
                const newRow = document.createElement('tr');
                newRow.innerHTML = `
                    <td>${result.date}</td>
                    <td>${result.hailydb_count}</td>
                    <td>${spcCount}</td>
                    <td>${statusBadge}</td>
                    <td>${actionButtons}</td>
                `;
                tbody.appendChild(newRow);
            });
            
            // Update timestamp outside the table
            const timestampElement = container.parentElement.querySelector('.text-muted');
            if (timestampElement) {
                timestampElement.textContent = `Last verified: ${new Date().toLocaleTimeString()}`;
            }
            
            console.log(`[REFRESH] Successfully refreshed ${data.results.length} verification records`);
        }
        
    } catch (error) {
        console.error('[REFRESH] Error refreshing verification data:', error);
    }
}

async function loadNextWeek() {
    try {
        // Temporarily disable auto-refresh to prevent interference
        window.loadingNextWeek = true;
        // Find the oldest date in the current table
        const container = document.getElementById('todays-spc-events');
        const tableRows = container.querySelectorAll('tbody tr');
        let oldestDate = null;
        
        // Get all existing dates first
        const existingDates = [];
        tableRows.forEach(row => {
            const dateCell = row.querySelector('td:first-child');
            if (dateCell && dateCell.textContent.trim()) {
                const dateStr = dateCell.textContent.trim();
                existingDates.push(dateStr);
                const date = new Date(dateStr);
                if (!oldestDate || date < oldestDate) {
                    oldestDate = date;
                }
            }
        });
        
        if (!oldestDate) {
            // If no dates found, start from 8 days ago
            oldestDate = new Date();
            oldestDate.setDate(oldestDate.getDate() - 8);
        }
        
        // Calculate the previous 7 days ending the day before the oldest
        const endDate = new Date(oldestDate);
        endDate.setDate(endDate.getDate() - 1);
        
        const startDate = new Date(endDate);
        startDate.setDate(startDate.getDate() - 6);
        
        // Format dates for API call
        const startDateStr = startDate.toISOString().split('T')[0];
        const endDateStr = endDate.toISOString().split('T')[0];
        
        console.log(`Loading previous week SPC data from ${startDateStr} to ${endDateStr}`);
        
        // Show loading message below existing content
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'text-center py-2';
        loadingDiv.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading next week...';
        loadingDiv.id = 'loading-indicator';
        container.appendChild(loadingDiv);
        
        // Fetch verification data for the date range
        const response = await fetch(`/internal/spc-verify?start_date=${startDateStr}&end_date=${endDateStr}&format=json`);
        const data = await response.json();
        
        // Remove loading indicator
        const loading = document.getElementById('loading-indicator');
        if (loading) loading.remove();
        
        console.log('API Response:', data);
        
        if (data.results && data.results.length > 0) {
            console.log('Results received:', data.results.length);
            // Get the current table body
            const tbody = container.querySelector('tbody');
            console.log('Table body found:', tbody);
            if (tbody) {
                // Filter out dates that already exist
                console.log('Existing dates:', existingDates);
                const newResults = data.results.filter(result => 
                    !existingDates.includes(result.date)
                );
                console.log('New results after filtering:', newResults.length, newResults);
                
                if (newResults.length > 0) {
                    // Sort new results by date (newest first to maintain chronological order)
                    newResults.sort((a, b) => new Date(b.date) - new Date(a.date));
                    
                    // Add new rows to the existing table
                    newResults.forEach(result => {
                        const statusBadge = result.match_status === 'MATCH' 
                            ? '<span class="badge bg-success">MATCH</span>'
                            : result.match_status === 'MISMATCH'
                            ? '<span class="badge bg-danger">MISMATCH</span>'
                            : '<span class="badge bg-warning">PENDING</span>';
                        
                        const spcCount = result.spc_live_count !== null ? result.spc_live_count : 'N/A';
                        const dateForUrl = result.date.replace(/-/g, '').slice(2); // Convert 2025-05-21 to 250521
                        const externalLink = `<a href="https://www.spc.noaa.gov/climo/reports/${dateForUrl}_rpts.html" target="_blank" class="btn btn-xs btn-outline-primary me-1">
                            <i class="fas fa-external-link-alt"></i>
                        </a>`;
                        const reuploadButton = result.match_status === 'MISMATCH' ? 
                            `<button class="btn btn-xs btn-outline-warning" onclick="forceReingestion('${result.date}', this)">
                                <i class="fas fa-sync-alt"></i>
                            </button>` : 
                            `<button class="btn btn-xs btn-outline-secondary" disabled>
                                <i class="fas fa-check"></i>
                            </button>`;
                        const actionButtons = externalLink + reuploadButton;
                        
                        const newRow = document.createElement('tr');
                        newRow.innerHTML = `
                            <td>${result.date}</td>
                            <td>${result.hailydb_count}</td>
                            <td>${spcCount}</td>
                            <td>${statusBadge}</td>
                            <td>${actionButtons}</td>
                        `;
                        tbody.appendChild(newRow);
                    });
                    
                    // Update the timestamp
                    const timestampElement = container.querySelector('.text-muted');
                    if (timestampElement) {
                        timestampElement.textContent = `Last verified: ${new Date().toLocaleTimeString()}`;
                    }
                    
                    console.log(`Added ${newResults.length} new dates to the table`);
                } else {
                    alert('No new dates found in the requested range');
                }
            }
        } else {
            alert('No verification data found for the next week');
        }
        
    } catch (error) {
        console.error('Error loading next week:', error);
        // Remove loading indicator if it exists
        const loading = document.getElementById('loading-indicator');
        if (loading) loading.remove();
        alert('Error loading next week data: ' + error.message);
    } finally {
        // Re-enable auto-refresh
        window.loadingNextWeek = false;
    }
}

// Get badge color for severity
function getSeverityColor(severity) {
    // Return custom severity classes for green-to-orange-to-red scale
    switch (severity?.toLowerCase()) {
        case 'extreme': return 'severity-extreme';
        case 'severe': return 'severity-severe';
        case 'moderate': return 'severity-moderate';
        case 'minor': return 'severity-minor';
        default: return 'severity-unknown';
    }
}

// Update dashboard status
async function updateDashboardStatus() {
    try {
        const response = await fetch('/internal/status');
        const status = await response.json();
        
        // Update timestamp
        updateLastUpdateTime();
        
        // Reload recent alerts
        loadRecentAlerts();
        
    } catch (error) {
        console.error('Error updating dashboard status:', error);
    }
}

// Run full update - combines all operations
async function runFullUpdate() {
    const button = document.getElementById('run-button');
    if (button) {
        button.disabled = true;
        button.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Running...';
    }
    
    try {
        // Sequential execution: NWS ingestion → SPC ingestion → matching
        showNotification('Starting NWS alert ingestion...', 'info');
        const nwsResponse = await fetch('/internal/trigger-ingestion', { method: 'POST' });
        const nwsResult = await nwsResponse.json();
        showNotification(`NWS: ${nwsResult.message}`, nwsResult.status === 'success' ? 'success' : 'warning');
        
        showNotification('Starting SPC data ingestion...', 'info');
        const spcResponse = await fetch('/internal/spc-ingest', { method: 'POST' });
        const spcResult = await spcResponse.json();
        showNotification(`SPC: ${spcResult.message}`, spcResult.status === 'success' ? 'success' : 'warning');
        
        showNotification('Running alert verification matching...', 'info');
        const matchResponse = await fetch('/internal/spc-match', { method: 'POST' });
        const matchResult = await matchResponse.json();
        showNotification(`Matching: ${matchResult.message}`, matchResult.status === 'success' ? 'success' : 'warning');
        
        showNotification('Full update completed successfully!', 'success');
        setTimeout(() => {
            updateDashboardStatus();
            loadTodaysAlerts();
            loadSPCVerificationTable();
        }, 2000);
        
    } catch (error) {
        console.error('Error in full update:', error);
        showNotification('Error during full update process', 'error');
    } finally {
        if (button) {
            button.disabled = false;
            button.innerHTML = '<i class="fas fa-play me-1"></i>Run Full Update';
        }
    }
}

// Trigger manual ingestion
async function triggerIngestion() {
    try {
        const response = await fetch('/internal/trigger-ingestion', { method: 'POST' });
        const result = await response.json();
        
        if (response.ok) {
            showNotification('Manual ingestion triggered successfully', 'success');
            setTimeout(() => {
                updateDashboardStatus();
            }, 2000);
        } else {
            showNotification('Error triggering ingestion: ' + (result.message || 'Unknown error'), 'error');
        }
    } catch (error) {
        console.error('Error triggering ingestion:', error);
        showNotification('Error triggering ingestion', 'error');
    }
}

// Enrich batch with optional limit
async function enrichBatch(limit = 50) {
    try {
        const response = await fetch('/api/alerts/enrich-batch', { 
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ limit: limit })
        });
        const result = await response.json();
        
        if (response.ok) {
            showNotification(`Batch enrichment completed: ${result.enriched || 0} alerts enriched`, 'success');
            setTimeout(() => {
                updateDashboardStatus();
            }, 2000);
        } else {
            showNotification('Error enriching batch: ' + (result.message || 'Unknown error'), 'error');
        }
    } catch (error) {
        console.error('Error enriching batch:', error);
        showNotification('Error enriching batch', 'error');
    }
}

// Enrich priority alerts
async function enrichPriorityAlerts() {
    try {
        showNotification('Starting priority alert enrichment...', 'info');
        
        const response = await fetch('/api/alerts/enrich-priority', { method: 'POST' });
        const result = await response.json();
        
        if (response.ok) {
            showNotification(`Priority enrichment completed: ${result.enriched || 0} alerts enriched`, 'success');
            setTimeout(() => {
                updateDashboardStatus();
            }, 2000);
        } else {
            showNotification('Error enriching priority alerts: ' + (result.message || 'Unknown error'), 'error');
        }
    } catch (error) {
        console.error('Error enriching priority alerts:', error);
        showNotification('Error enriching priority alerts', 'error');
    }
}

// Enrich by category
async function enrichByCategory(category, limit = 100) {
    try {
        showNotification(`Starting ${category} enrichment...`, 'info');
        
        const response = await fetch('/api/alerts/enrich-by-category', { 
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ category: category, limit: limit })
        });
        const result = await response.json();
        
        if (response.ok) {
            showNotification(`${category} enrichment completed: ${result.enriched || 0} alerts enriched`, 'success');
            setTimeout(() => {
                updateDashboardStatus();
            }, 2000);
        } else {
            showNotification(`Error enriching ${category}: ` + (result.message || 'Unknown error'), 'error');
        }
    } catch (error) {
        console.error(`Error enriching ${category}:`, error);
        showNotification(`Error enriching ${category}`, 'error');
    }
}

// Get enrichment statistics
async function getEnrichmentStats() {
    try {
        const response = await fetch('/api/alerts/enrichment-stats');
        const stats = await response.json();
        
        if (response.ok) {
            const message = `Enrichment Stats:
            • Total Alerts: ${stats.total_alerts || 0}
            • Enriched: ${stats.enriched_alerts || 0} (${stats.enrichment_rate || 0}%)
            • Priority Enriched: ${stats.priority_alerts_enriched || 0}/${stats.priority_alerts_total || 0} (${stats.priority_enrichment_rate || 0}%)
            • Tagged: ${stats.tagged_alerts || 0}`;
            
            showNotification(message, 'info', 8000);
        } else {
            showNotification('Error getting enrichment stats: ' + (stats.error || 'Unknown error'), 'error');
        }
    } catch (error) {
        console.error('Error getting enrichment stats:', error);
        showNotification('Error getting enrichment stats', 'error');
    }
}



// Toggle scheduler
async function toggleScheduler() {
    try {
        const action = dashboardData.scheduler_running ? 'stop' : 'start';
        const response = await fetch('/internal/cron', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: action })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            dashboardData.scheduler_running = !dashboardData.scheduler_running;
            updateStatusIndicator();
            showNotification(`Scheduler ${action}ed successfully`, 'success');
        } else {
            showNotification('Error toggling scheduler: ' + (result.message || 'Unknown error'), 'error');
        }
    } catch (error) {
        console.error('Error toggling scheduler:', error);
        showNotification('Error toggling scheduler', 'error');
    }
}

// Refresh single date in verification table
async function refreshSingleDateInTable(dateStr) {
    try {
        console.log(`[SINGLE REFRESH] Updating verification data for ${dateStr}`);
        
        // Get fresh verification data for just this date
        const response = await fetch(`/internal/spc-verify?start_date=${dateStr}&end_date=${dateStr}&format=json`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        console.log(`[SINGLE REFRESH] Fresh data for ${dateStr}:`, data);
        
        if (data.results && data.results.length > 0) {
            const result = data.results[0];
            
            // Find the table row for this date
            const table = document.querySelector('#todays-spc-events table tbody');
            if (table) {
                const rows = table.querySelectorAll('tr');
                for (let row of rows) {
                    const dateCell = row.querySelector('td:first-child');
                    if (dateCell && dateCell.textContent === dateStr) {
                        // Update this row
                        const statusBadge = result.match_status === 'MATCH' 
                            ? '<span class="badge bg-success">MATCH</span>'
                            : result.match_status === 'MISMATCH'
                            ? '<span class="badge bg-danger">MISMATCH</span>'
                            : result.match_status === 'SPC_UNAVAILABLE'
                            ? '<span class="badge bg-warning">SPC_UNAVAILABLE</span>'
                            : '<span class="badge bg-secondary">PENDING</span>';
                        
                        const spcCount = result.spc_live_count !== null ? result.spc_live_count : 'N/A';
                        const dateForUrl = result.date.replace(/-/g, '').slice(2);
                        const externalLink = `<a href="https://www.spc.noaa.gov/climo/reports/${dateForUrl}_rpts.html" target="_blank" class="btn btn-xs btn-outline-primary me-1">
                            <i class="fas fa-external-link-alt"></i>
                        </a>`;
                        const reuploadButton = result.match_status === 'MISMATCH' ? 
                            `<button class="btn btn-xs btn-outline-warning" onclick="forceReingestion('${result.date}', this)">
                                <i class="fas fa-sync-alt"></i>
                            </button>` : 
                            `<button class="btn btn-xs btn-outline-secondary" disabled>
                                <i class="fas fa-check"></i>
                            </button>`;
                        const actionButtons = externalLink + reuploadButton;
                        
                        row.innerHTML = `
                            <td>${result.date}</td>
                            <td>${result.hailydb_count}</td>
                            <td>${spcCount}</td>
                            <td>${statusBadge}</td>
                            <td>${actionButtons}</td>
                        `;
                        
                        console.log(`[SINGLE REFRESH] Updated row for ${dateStr}`);
                        break;
                    }
                }
            }
        }
    } catch (error) {
        console.error(`[SINGLE REFRESH] Error refreshing ${dateStr}:`, error);
    }
}

// Refresh dashboard
function refreshDashboard() {
    location.reload();
}

// Show notification
function showNotification(message, type = 'info') {
    const alertClass = type === 'error' ? 'alert-danger' : `alert-${type}`;
    const alert = document.createElement('div');
    alert.className = `alert ${alertClass} alert-dismissible fade show position-fixed`;
    alert.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(alert);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (alert.parentNode) {
            alert.parentNode.removeChild(alert);
        }
    }, 5000);
}

// Update last update time
function updateLastUpdateTime() {
    const timeElement = document.getElementById('last-update-time');
    if (timeElement) {
        timeElement.textContent = new Date().toLocaleTimeString();
    }
}

// Load integrity verification data
async function loadIntegrityVerification() {
    const container = document.getElementById('integrity-verification-container');
    if (!container) return;
    
    // Show loading state
    container.innerHTML = `
        <div class="text-center py-3">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="text-muted small mt-2">Verifying data integrity...</p>
        </div>
    `;
    
    try {
        const response = await fetch('/internal/spc-verify?format=json&days=7');
        const data = await response.json();
        
        if (response.ok && data.results) {
            displayIntegrityResults(data.results, data.summary);
        } else {
            container.innerHTML = `
                <div class="alert alert-warning">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    Unable to verify data integrity. Please try again.
                </div>
            `;
        }
    } catch (error) {
        console.error('Error loading integrity verification:', error);
        container.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-times me-2"></i>
                Error loading verification data.
            </div>
        `;
    }
}

// Display integrity verification results
function displayIntegrityResults(results, summary) {
    const container = document.getElementById('integrity-verification-container');
    
    let html = `
        <div class="row mb-3">
            <div class="col-md-3">
                <small class="text-muted">Total Checked</small>
                <div class="h6 mb-0">${summary.total_dates} days</div>
            </div>
            <div class="col-md-3">
                <small class="text-success">Matches</small>
                <div class="h6 mb-0 text-success">${summary.matches}</div>
            </div>
            <div class="col-md-3">
                <small class="text-danger">Mismatches</small>
                <div class="h6 mb-0 text-danger">${summary.mismatches}</div>
            </div>
            <div class="col-md-3">
                <small class="text-muted">Match Rate</small>
                <div class="h6 mb-0">${summary.match_percentage.toFixed(1)}%</div>
            </div>
        </div>
        
        <div class="table-responsive">
            <table class="table table-sm">
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>HailyDB</th>
                        <th>SPC Live</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    results.forEach(result => {
        const statusBadge = result.match_status === 'MATCH' 
            ? '<span class="badge bg-success">MATCH</span>'
            : result.match_status === 'MISMATCH'
            ? '<span class="badge bg-danger">MISMATCH</span>'
            : '<span class="badge bg-warning">N/A</span>';
            
        const spcCount = result.spc_live_count !== null ? result.spc_live_count : 'N/A';
        
        html += `
            <tr>
                <td>${result.date}</td>
                <td><span class="badge bg-primary">${result.hailydb_count}</span></td>
                <td><span class="badge bg-secondary">${spcCount}</span></td>
                <td>${statusBadge}</td>
            </tr>
        `;
    });
    
    html += `
                </tbody>
            </table>
        </div>
        
        <div class="text-center mt-3">
            <a href="/internal/spc-verify" class="btn btn-sm btn-outline-primary">
                <i class="fas fa-external-link-alt me-1"></i>View Full Report
            </a>
        </div>
    `;
    
    container.innerHTML = html;
}

// Force re-ingestion for a specific date
async function forceReingestion(date, buttonElement) {
    console.log(`[SPC REIMPORT] Starting re-ingestion for date: ${date}`);
    
    const button = buttonElement || event.target.closest('button');
    const originalContent = button.innerHTML;
    const originalClass = button.className;
    
    console.log(`[SPC REIMPORT] Button found:`, button);
    console.log(`[SPC REIMPORT] Original content:`, originalContent);
    
    // Show loading state
    button.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    button.disabled = true;
    button.className = 'btn btn-sm btn-warning';
    
    console.log(`[SPC REIMPORT] Button set to loading state`);
    
    try {
        const url = `/internal/spc-reupload/${date}`;
        console.log(`[SPC REIMPORT] Making POST request to: ${url}`);
        
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        console.log(`[SPC REIMPORT] Response status: ${response.status}`);
        console.log(`[SPC REIMPORT] Response headers:`, response.headers);
        
        const result = await response.json();
        console.log(`[SPC REIMPORT] Response body:`, result);
        
        if (response.ok && result.success) {
            console.log(`[SPC REIMPORT] Success! Re-ingestion completed for ${date}`);
            
            // Show success temporarily
            button.innerHTML = '<i class="fas fa-check"></i>';
            button.className = 'btn btn-sm btn-success';
            
            // Refresh only this specific date after a short delay
            setTimeout(() => {
                console.log(`[SPC REIMPORT] Refreshing data for ${date} only...`);
                refreshSingleDateInTable(date);
            }, 1500);
            
        } else {
            console.error(`[SPC REIMPORT] Error response:`, result);
            
            // Show error temporarily
            button.innerHTML = '<i class="fas fa-times"></i>';
            button.className = 'btn btn-sm btn-danger';
            
            setTimeout(() => {
                console.log(`[SPC REIMPORT] Restoring button to original state`);
                button.innerHTML = originalContent;
                button.className = originalClass;
                button.disabled = false;
            }, 3000);
        }
    } catch (error) {
        console.error(`[SPC REIMPORT] Network/parsing error:`, error);
        console.error(`[SPC REIMPORT] Error stack:`, error.stack);
        
        // Show error state
        button.innerHTML = '<i class="fas fa-exclamation-triangle"></i>';
        button.className = 'btn btn-sm btn-danger';
        
        setTimeout(() => {
            console.log(`[SPC REIMPORT] Restoring button after error`);
            button.innerHTML = originalContent;
            button.className = originalClass;
            button.disabled = false;
        }, 3000);
    }
}

// Start autonomous scheduler
async function startAutonomousScheduler() {
    try {
        const response = await fetch('/internal/scheduler/start', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const result = await response.json();
        if (result.success) {
            console.log('Autonomous scheduler started successfully');
            updateStatusIndicator();
        } else {
            console.error('Failed to start autonomous scheduler:', result.error);
        }
    } catch (error) {
        console.error('Error starting autonomous scheduler:', error);
    }
}

// Stop autonomous scheduler
async function stopAutonomousScheduler() {
    try {
        const response = await fetch('/internal/scheduler/stop', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const result = await response.json();
        if (result.success) {
            console.log('Autonomous scheduler stopped successfully');
            updateStatusIndicator();
        } else {
            console.error('Failed to stop autonomous scheduler:', result.error);
        }
    } catch (error) {
        console.error('Error stopping autonomous scheduler:', error);
    }
}

// Play button click handler
function onPlayScheduler() {
    startAutonomousScheduler();
}

// Pause button click handler
function onPauseScheduler() {
    stopAutonomousScheduler();
}

// World Clock Functions
function updateWorldClock() {
    const now = new Date();
    
    // All Continental US Time Zones
    const pacificTime = now.toLocaleTimeString('en-US', {
        timeZone: 'America/Los_Angeles',
        hour12: true,
        hour: 'numeric',
        minute: '2-digit'
    });
    
    const mountainTime = now.toLocaleTimeString('en-US', {
        timeZone: 'America/Denver',
        hour12: true,
        hour: 'numeric',
        minute: '2-digit'
    });
    
    const centralTime = now.toLocaleTimeString('en-US', {
        timeZone: 'America/Chicago',
        hour12: true,
        hour: 'numeric',
        minute: '2-digit'
    });
    
    const easternTime = now.toLocaleTimeString('en-US', {
        timeZone: 'America/New_York',
        hour12: true,
        hour: 'numeric',
        minute: '2-digit'
    });
    
    const utcTime = now.toLocaleTimeString('en-US', {
        timeZone: 'UTC',
        hour12: true,
        hour: 'numeric',
        minute: '2-digit'
    });
    
    // SPC Day calculation and date formatting
    const utcHour = parseInt(now.toLocaleTimeString('en-US', {
        timeZone: 'UTC',
        hour12: false,
        hour: '2-digit'
    }));
    
    // Get UTC date in MMM DD format
    const utcDate = now.toLocaleDateString('en-US', { 
        timeZone: 'UTC',
        month: 'short',
        day: '2-digit'
    });
    
    let spcDate;
    if (utcHour >= 12) {
        // Current time is >= 12:00Z, so SPC day is today (UTC date)
        spcDate = now.toLocaleDateString('en-US', { 
            timeZone: 'UTC',
            day: '2-digit'
        });
    } else {
        // Current time is < 12:00Z, so SPC day is yesterday (UTC date - 1)
        const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000);
        spcDate = yesterday.toLocaleDateString('en-US', { 
            timeZone: 'UTC',
            day: '2-digit'
        });
    }
    
    // Update DOM elements
    const pacificElement = document.getElementById('pacific-time');
    const mountainElement = document.getElementById('mountain-time');
    const centralElement = document.getElementById('central-time');
    const easternElement = document.getElementById('eastern-time');
    const utcElement = document.getElementById('utc-time');
    const spcUtcDateElement = document.getElementById('spc-utc-date');
    
    if (pacificElement) pacificElement.textContent = pacificTime;
    if (mountainElement) mountainElement.textContent = mountainTime;
    if (centralElement) centralElement.textContent = centralTime;
    if (easternElement) easternElement.textContent = easternTime;
    if (utcElement) utcElement.textContent = utcTime;
    if (spcUtcDateElement) spcUtcDateElement.textContent = `${utcDate.replace(/(\w{3}) (\d{2})/, '$1 $2')} / ${spcDate}`;
}

// Time Mode Toggle Functions
function initializeTimeModeToggle() {
    const utcModeRadio = document.getElementById('utc-mode');
    const spcModeRadio = document.getElementById('spc-mode');
    
    if (utcModeRadio && spcModeRadio) {
        utcModeRadio.addEventListener('change', function() {
            if (this.checked) {
                currentTimeMode = 'utc';
                loadTodaysAlertsWithMode('utc');
            }
        });
        
        spcModeRadio.addEventListener('change', function() {
            if (this.checked) {
                currentTimeMode = 'spc';
                loadTodaysAlertsWithMode('spc');
            }
        });
    }
}

async function loadTodaysAlertsWithMode(mode) {
    try {
        const tableContainer = document.getElementById('todays-alerts-table');
        if (!tableContainer) return;
        
        let endpoint, dateParam;
        
        if (mode === 'spc') {
            // SPC Day - fetch NWS alerts effective during SPC Day window
            const spcDay = getSPCDay();
            const spcWindow = getSPCDayWindow(spcDay);
            
            const cacheBuster = new Date().getTime();
            endpoint = `/alerts?format=json&per_page=1000&effective_start=${spcWindow.start}&effective_end=${spcWindow.end}&_cb=${cacheBuster}`;
            
            const response = await fetch(endpoint);
            const data = await response.json();
            
            const spcDayAlerts = data.alerts || [];
            
            if (spcDayAlerts.length > 0) {
                // Group by event type for compact breakdown
                const alertsByType = spcDayAlerts.reduce((acc, alert) => {
                    const eventType = alert.event || 'Unknown';
                    acc[eventType] = (acc[eventType] || 0) + 1;
                    return acc;
                }, {});
                
                const totalSPCDay = data.pagination ? data.pagination.total : spcDayAlerts.length;
                let html = `<div class="mb-3"><strong>${spcDayAlerts.length}/${totalSPCDay} NWS alerts for SPC Day ${spcDay}</strong></div>
                           <div class="mb-2"><small class="text-muted">SPC Day: ${spcWindow.start} → ${spcWindow.end} (effective time window)</small></div>`;
                
                displayNWSAlerts(spcDayAlerts, html, tableContainer);
            } else {
                tableContainer.innerHTML = `
                    <div class="text-center py-3">
                        <div class="h5 text-warning">0</div>
                        <small class="text-muted">No NWS alerts effective during SPC Day ${spcDay}</small>
                    </div>`;
            }
            return;
        } else {
            // UTC Mode - use current logic
            const today = new Date().toISOString().split('T')[0];
            const cacheBuster = new Date().getTime();
            endpoint = `/alerts?format=json&per_page=1000&ingested_date=${today}&_cb=${cacheBuster}`;
        }
        
        const response = await fetch(endpoint);
        const data = await response.json();
        
        // Use existing logic for UTC mode
        const todaysAlerts = data.alerts || [];
        
        if (todaysAlerts.length > 0) {
            // Group by event type for compact breakdown
            const alertsByType = todaysAlerts.reduce((acc, alert) => {
                const eventType = alert.event || 'Unknown';
                acc[eventType] = (acc[eventType] || 0) + 1;
                return acc;
            }, {});
            
            const totalIngestedToday = data.pagination ? data.pagination.total : todaysAlerts.length;
            let html = `<div class="mb-3"><strong>${todaysAlerts.length}/${totalIngestedToday} alerts ingested today (UTC)</strong></div>
                       <div class="mb-2"><small class="text-muted">Showing alerts by ingestion date (database completeness)</small></div>`;
            
            // Continue with existing alert display logic...
            displayNWSAlerts(todaysAlerts, html, tableContainer);
        } else {
            tableContainer.innerHTML = '<div class="text-center py-3"><div class="h5 text-warning">0</div><small class="text-muted">No alerts ingested today (UTC)</small></div>';
        }
    } catch (error) {
        console.error('Error loading alerts with mode:', error);
        const tableContainer = document.getElementById('todays-alerts-table');
        if (tableContainer) {
            tableContainer.innerHTML = '<p class="text-danger">Error loading alerts data.</p>';
        }
    }
}

function displaySPCReports(reports, spcDay, container) {
    // Group reports by type
    const reportsByType = reports.reduce((acc, report) => {
        const type = report.report_type || 'Unknown';
        acc[type] = (acc[type] || 0) + 1;
        return acc;
    }, {});
    
    let html = `
        <div class="mb-3">
            <strong>${reports.length} SPC reports for SPC Day ${spcDay}</strong>
        </div>
        <div class="mb-2">
            <small class="text-muted">SPC Day: ${spcDay}T12:00Z → ${getNextDay(spcDay)}T11:59Z</small>
        </div>`;
    
    // Create summary table
    if (Object.keys(reportsByType).length > 0) {
        html += '<div class="table-responsive mb-3"><table class="table table-sm">';
        html += '<thead><tr><th>Report Type</th><th class="text-end">Count</th></tr></thead><tbody>';
        
        Object.entries(reportsByType).forEach(([type, count]) => {
            const typeCapitalized = type.charAt(0).toUpperCase() + type.slice(1);
            html += `
                <tr>
                    <td>${typeCapitalized}</td>
                    <td class="text-end"><span class="badge bg-warning">${count}</span></td>
                </tr>`;
        });
        html += '</tbody></table></div>';
        
        // Show recent reports with basic info
        html += '<div class="table-responsive"><table class="table table-sm small">';
        html += '<thead><tr><th>Time</th><th>Type</th><th>Location</th><th>State</th><th>Details</th></tr></thead><tbody>';
        
        // Sort by time descending
        const sortedReports = reports.sort((a, b) => (b.time_utc || '').localeCompare(a.time_utc || ''));
        
        sortedReports.slice(0, 20).forEach(report => {
            const time = report.time_utc || '--';
            const type = (report.report_type || 'Unknown').charAt(0).toUpperCase() + (report.report_type || 'Unknown').slice(1);
            const location = report.location || '--';
            const state = report.state || '--';
            const magnitude = report.magnitude || {};
            
            let details = '--';
            if (type.toLowerCase() === 'hail' && magnitude.size_inches) {
                details = `${magnitude.size_inches}"`;
            } else if (type.toLowerCase() === 'wind' && magnitude.speed_mph) {
                details = `${magnitude.speed_mph} mph`;
            } else if (report.comments) {
                details = report.comments.substring(0, 50) + (report.comments.length > 50 ? '...' : '');
            }
            
            html += `
                <tr>
                    <td>${time}</td>
                    <td><span class="badge bg-warning">${type}</span></td>
                    <td>${location}</td>
                    <td>${state}</td>
                    <td><small>${details}</small></td>
                </tr>`;
        });
        
        html += '</tbody></table></div>';
    }
    
    container.innerHTML = html;
}

function displayNWSAlerts(alerts, existingHtml, container) {
    let html = existingHtml;
    
    if (alerts.length > 0) {
        // Group by event type for category breakdown
        const alertsByType = alerts.reduce((acc, alert) => {
            const eventType = alert.event || 'Unknown';
            acc[eventType] = (acc[eventType] || 0) + 1;
            return acc;
        }, {});
        
        // NWS Alert Category mapping
        const alertCategories = {
            'Tornado Watch': 'Severe Weather Alert',
            'Tornado Warning': 'Severe Weather Alert',
            'Severe Thunderstorm Watch': 'Severe Weather Alert',
            'Severe Thunderstorm Warning': 'Severe Weather Alert',
            'Severe Weather Statement': 'Severe Weather Alert',
            'Extreme Wind Warning': 'Severe Weather Alert',
            'Snow Squall Warning': 'Severe Weather Alert',
            'Winter Storm Watch': 'Winter Weather Alert',
            'Winter Storm Warning': 'Winter Weather Alert',
            'Blizzard Warning': 'Winter Weather Alert',
            'Ice Storm Warning': 'Winter Weather Alert',
            'Winter Weather Advisory': 'Winter Weather Alert',
            'Freezing Rain Advisory': 'Winter Weather Alert',
            'Wind Chill Advisory': 'Winter Weather Alert',
            'Wind Chill Warning': 'Winter Weather Alert',
            'Frost Advisory': 'Winter Weather Alert',
            'Freeze Warning': 'Winter Weather Alert',
            'Flood Watch': 'Flood Alert',
            'Flood Warning': 'Flood Alert',
            'Flash Flood Watch': 'Flood Alert',
            'Flash Flood Warning': 'Flood Alert',
            'Flood Advisory': 'Flood Alert',
            'Coastal Flood Watch': 'Coastal Alert',
            'Coastal Flood Warning': 'Coastal Alert',
            'Coastal Flood Advisory': 'Coastal Alert',
            'Lakeshore Flood Watch': 'Coastal Alert',
            'Lakeshore Flood Warning': 'Coastal Alert',
            'Lakeshore Flood Advisory': 'Coastal Alert',
            'High Wind Watch': 'Wind & Fog Alert',
            'High Wind Warning': 'Wind & Fog Alert',
            'Wind Advisory': 'Wind & Fog Alert',
            'Dense Fog Advisory': 'Wind & Fog Alert',
            'Freezing Fog Advisory': 'Wind & Fog Alert',
            'Fire Weather Watch': 'Fire Weather Alert',
            'Red Flag Warning': 'Fire Weather Alert',
            'Air Quality Alert': 'Air Quality & Dust Alert',
            'Air Stagnation Advisory': 'Air Quality & Dust Alert',
            'Blowing Dust Advisory': 'Air Quality & Dust Alert',
            'Dust Storm Warning': 'Air Quality & Dust Alert',
            'Ashfall Advisory': 'Air Quality & Dust Alert',
            'Ashfall Warning': 'Air Quality & Dust Alert',
            'Small Craft Advisory': 'Marine Alert',
            'Gale Watch': 'Marine Alert',
            'Gale Warning': 'Marine Alert',
            'Storm Watch': 'Marine Alert',
            'Storm Warning': 'Marine Alert',
            'Hurricane Force Wind Warning': 'Marine Alert',
            'Special Marine Warning': 'Marine Alert',
            'Low Water Advisory': 'Marine Alert',
            'Brisk Wind Advisory': 'Marine Alert',
            'Marine Weather Statement': 'Marine Alert',
            'Hazardous Seas Warning': 'Marine Alert',
            'Tropical Storm Watch': 'Tropical Weather Alert',
            'Tropical Storm Warning': 'Tropical Weather Alert',
            'Hurricane Watch': 'Tropical Weather Alert',
            'Hurricane Warning': 'Tropical Weather Alert',
            'Storm Surge Watch': 'Tropical Weather Alert',
            'Storm Surge Warning': 'Tropical Weather Alert',
            'Tsunami Watch': 'Tsunami Alert',
            'Tsunami Advisory': 'Tsunami Alert',
            'Tsunami Warning': 'Tsunami Alert',
            'Special Weather Statement': 'General Weather Info',
            'Hazardous Weather Outlook': 'General Weather Info',
            'Short Term Forecast': 'General Weather Info',
            'Public Information Statement': 'General Weather Info',
            'Administrative Message': 'General Weather Info',
            'Test Message': 'General Weather Info',
            'Beach Hazards Statement': 'Coastal Alert'
        };
        
        // Group alerts by category
        const alertsByCategory = {};
        Object.entries(alertsByType).forEach(([alertType, count]) => {
            const category = alertCategories[alertType] || 'Other Alerts';
            if (!alertsByCategory[category]) {
                alertsByCategory[category] = [];
            }
            alertsByCategory[category].push([alertType, count]);
        });
        
        // Create comprehensive category table
        html += '<div class="table-responsive mb-3">';
        html += '<table class="table table-sm table-striped">';
        html += '<thead class="table-dark"><tr><th>Category</th><th>Alert Type</th><th class="text-end">Count</th></tr></thead><tbody>';
        
        // Sort categories and display
        const categoryOrder = [
            'Severe Weather Alert',
            'Flood Alert', 
            'Winter Weather Alert',
            'Marine Alert',
            'Wind & Fog Alert',
            'Fire Weather Alert',
            'Coastal Alert',
            'Tropical Weather Alert',
            'Air Quality & Dust Alert',
            'Tsunami Alert',
            'General Weather Info',
            'Other Alerts'
        ];
        
        categoryOrder.forEach(category => {
            if (alertsByCategory[category]) {
                // Sort alerts within category by count descending
                alertsByCategory[category].sort((a, b) => b[1] - a[1]);
                
                alertsByCategory[category].forEach(([alertType, count], index) => {
                    const categoryCell = index === 0 ? 
                        `<td rowspan="${alertsByCategory[category].length}" class="align-middle"><strong>${category}</strong></td>` : '';
                    
                    html += `<tr>
                        ${categoryCell}
                        <td>${alertType}</td>
                        <td class="text-end"><span class="badge bg-primary">${count}</span></td>
                    </tr>`;
                });
            }
        });
        
        html += '</tbody></table></div>';
        
        // Pagination setup
        const alertsPerPage = 50;
        const totalPages = Math.ceil(alerts.length / alertsPerPage);
        let currentPage = 1;
        
        html += '<div class="table-responsive"><table class="table table-sm small">';
        html += '<thead><tr><th>Date/Time</th><th>Severity</th><th>Type</th><th>Area</th><th>Actions</th></tr></thead><tbody id="alerts-tbody">';
        
        // Sort by effective date descending
        const sortedAlerts = alerts.sort((a, b) => new Date(b.effective) - new Date(a.effective));
        
        // Show first page
        const pageAlerts = sortedAlerts.slice(0, alertsPerPage);
        pageAlerts.forEach(alert => {
            const effectiveDate = new Date(alert.effective).toLocaleString();
            const severity = alert.severity || 'Unknown';
            const event = alert.event || 'Unknown';
            const areas = alert.area_desc || 'Unknown';
            
            html += `
                <tr>
                    <td><small>${effectiveDate}</small></td>
                    <td><span class="badge severity-${severity.toLowerCase()}">${severity}</span></td>
                    <td>${event}</td>
                    <td><small>${areas.substring(0, 50)}${areas.length > 50 ? '...' : ''}</small></td>
                    <td><a href="/alerts/${alert.id}" class="btn btn-sm btn-outline-primary">View</a></td>
                </tr>`;
        });
        
        html += '</tbody></table></div>';
        
        // Store data for pagination
        window.dashboardAlertsData = {
            sortedAlerts: sortedAlerts,
            currentPage: currentPage,
            totalPages: totalPages,
            alertsPerPage: alertsPerPage
        };
    }
    
    container.innerHTML = html;
}

function getNextDay(dateString) {
    const date = new Date(dateString + 'T00:00:00Z');
    date.setUTCDate(date.getUTCDate() + 1);
    return date.toISOString().split('T')[0];
}

function getSPCDay() {
    const now = new Date();
    const utcHour = parseInt(now.toLocaleTimeString('en-US', {
        timeZone: 'UTC',
        hour12: false,
        hour: '2-digit'
    }));
    
    if (utcHour >= 12) {
        // Current time is >= 12:00Z, so SPC day is today (UTC date)
        return now.toLocaleDateString('en-CA', { timeZone: 'UTC' });
    } else {
        // Current time is < 12:00Z, so SPC day is yesterday (UTC date - 1)
        const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000);
        return yesterday.toLocaleDateString('en-CA', { timeZone: 'UTC' });
    }
}

function getSPCDayWindow(spcDay) {
    // SPC Day runs from 12:00Z to 11:59Z next day
    const startTime = `${spcDay}T12:00:00Z`;
    const nextDay = getNextDay(spcDay);
    const endTime = `${nextDay}T11:59:59Z`;
    
    return {
        start: startTime,
        end: endTime
    };
}

console.log('Dashboard JavaScript loaded successfully');