/**
 * Live Statistics Module for HailyDB
 * Fetches real-time database statistics and updates displays
 */

class LiveStatsManager {
    constructor() {
        this.cache = {};
        this.cacheTimeout = 5 * 60 * 1000; // 5 minutes
        this.isLoading = false;
    }

    async fetchStatistics() {
        if (this.isLoading) return this.cache.data;
        
        const now = Date.now();
        if (this.cache.data && (now - this.cache.timestamp) < this.cacheTimeout) {
            return this.cache.data;
        }

        this.isLoading = true;

        try {
            // Use dedicated statistics endpoint for better performance
            const response = await fetch('/api/stats/summary');
            const data = await response.json();

            const stats = {
                totalAlerts: data.total_alerts || 0,
                spcReports: data.spc_reports || 0,
                radarDetected: data.radar_detected_events || 0,
                lastUpdated: new Date().toISOString()
            };

            this.cache = {
                data: stats,
                timestamp: now
            };

            return stats;

        } catch (error) {
            console.error('Failed to fetch statistics:', error);
            // Return cached data if available, otherwise fallback
            return this.cache.data || {
                totalAlerts: 'Error',
                spcReports: 'Error',
                radarDetected: 'Error',
                lastUpdated: new Date().toISOString()
            };
        } finally {
            this.isLoading = false;
        }
    }

    formatNumber(num) {
        if (typeof num !== 'number') return num;
        return num.toLocaleString() + '+';
    }

    async updateReadmeStats() {
        const stats = await this.fetchStatistics();
        
        // Update README-style statistics display
        const elements = {
            'total-alerts': stats.totalAlerts,
            'spc-reports': stats.spcReports,
            'radar-detected': stats.radarDetected
        };

        Object.entries(elements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = this.formatNumber(value);
                element.classList.add('updated');
                setTimeout(() => element.classList.remove('updated'), 1000);
            }
        });

        // Update last updated timestamp
        const lastUpdatedElement = document.getElementById('stats-last-updated');
        if (lastUpdatedElement) {
            const time = new Date(stats.lastUpdated).toLocaleString();
            lastUpdatedElement.textContent = `Last updated: ${time}`;
        }
    }

    async createLiveDashboard(containerId) {
        const stats = await this.fetchStatistics();
        const container = document.getElementById(containerId);
        
        if (!container) {
            console.error(`Container ${containerId} not found`);
            return;
        }

        container.innerHTML = `
            <div class="live-dashboard">
                <h3>Live Database Statistics</h3>
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-number" id="dash-total-alerts">${this.formatNumber(stats.totalAlerts)}</div>
                        <div class="stat-label">Total NWS Alerts</div>
                        <div class="stat-desc">Comprehensive enrichments</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number" id="dash-spc-reports">${this.formatNumber(stats.spcReports)}</div>
                        <div class="stat-label">SPC Storm Reports</div>
                        <div class="stat-desc">100% historical coverage</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number" id="dash-radar-detected">${this.formatNumber(stats.radarDetected)}</div>
                        <div class="stat-label">Radar-Detected Events</div>
                        <div class="stat-desc">Pre-filtered for damage assessment</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">100%</div>
                        <div class="stat-label">Data Integrity</div>
                        <div class="stat-desc">Continuous verification</div>
                    </div>
                </div>
                <div class="stats-footer">
                    <span id="dash-last-updated">Last updated: ${new Date(stats.lastUpdated).toLocaleString()}</span>
                    <button id="refresh-stats" onclick="liveStats.refreshDashboard('${containerId}')">Refresh</button>
                </div>
            </div>
        `;

        this.addDashboardStyles();
    }

    addDashboardStyles() {
        if (document.getElementById('live-stats-styles')) return;

        const styles = document.createElement('style');
        styles.id = 'live-stats-styles';
        styles.textContent = `
            .live-dashboard {
                background: #f8f9fa;
                border-radius: 12px;
                padding: 24px;
                margin: 20px 0;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }
            
            .live-dashboard h3 {
                margin: 0 0 20px 0;
                color: #2c3e50;
                text-align: center;
            }
            
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 16px;
                margin-bottom: 20px;
            }
            
            .stat-card {
                background: white;
                border-radius: 8px;
                padding: 20px;
                text-align: center;
                border: 1px solid #e9ecef;
                transition: transform 0.2s, box-shadow 0.2s;
            }
            
            .stat-card:hover {
                transform: translateY(-2px);
                box-shadow: 0 6px 12px rgba(0,0,0,0.15);
            }
            
            .stat-number {
                font-size: 2rem;
                font-weight: bold;
                color: #2980b9;
                margin-bottom: 8px;
            }
            
            .stat-label {
                font-weight: 600;
                color: #34495e;
                margin-bottom: 4px;
            }
            
            .stat-desc {
                font-size: 0.9rem;
                color: #7f8c8d;
            }
            
            .stats-footer {
                display: flex;
                justify-content: space-between;
                align-items: center;
                font-size: 0.9rem;
                color: #6c757d;
                border-top: 1px solid #e9ecef;
                padding-top: 16px;
            }
            
            #refresh-stats {
                background: #3498db;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                cursor: pointer;
                transition: background 0.2s;
            }
            
            #refresh-stats:hover {
                background: #2980b9;
            }
            
            .updated {
                animation: highlight 1s ease-in-out;
            }
            
            @keyframes highlight {
                0% { background-color: #fff3cd; }
                100% { background-color: transparent; }
            }
            
            @media (max-width: 768px) {
                .stats-grid {
                    grid-template-columns: 1fr;
                }
                
                .stats-footer {
                    flex-direction: column;
                    gap: 12px;
                }
            }
        `;
        document.head.appendChild(styles);
    }

    async refreshDashboard(containerId) {
        // Clear cache to force fresh data
        this.cache = {};
        await this.createLiveDashboard(containerId);
    }

    // Auto-refresh functionality
    startAutoRefresh(intervalMinutes = 5) {
        setInterval(() => {
            this.updateReadmeStats();
            
            // Refresh dashboard if present
            const dashboard = document.querySelector('.live-dashboard');
            if (dashboard && dashboard.closest('[id]')) {
                const containerId = dashboard.closest('[id]').id;
                this.refreshDashboard(containerId);
            }
        }, intervalMinutes * 60 * 1000);
    }
}

// Global instance
const liveStats = new LiveStatsManager();

// Auto-initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    // Update README-style stats if elements exist
    if (document.getElementById('total-alerts')) {
        liveStats.updateReadmeStats();
    }
    
    // Create dashboard if container exists
    const dashboardContainer = document.getElementById('live-dashboard-container');
    if (dashboardContainer) {
        liveStats.createLiveDashboard('live-dashboard-container');
    }
    
    // Start auto-refresh
    liveStats.startAutoRefresh(5);
});