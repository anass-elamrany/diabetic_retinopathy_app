// Initialize charts when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    try {
        // Debugging - log chart data
        console.log("Chart Data:", chartData);
        
        // Initialize Stage Distribution Chart
        if (chartData.stage.data.length > 0 && !chartData.stage.error) {
            initStageChart();
        } else {
            console.error("Stage chart data not available:", chartData.stage.error);
        }
        
        // Initialize Monthly Trend Chart
        if (chartData.monthly.data.length > 0 && !chartData.monthly.error) {
            initMonthlyChart();
        } else {
            console.error("Monthly chart data not available:", chartData.monthly.error);
        }
        
    } catch (error) {
        console.error("Error initializing charts:", error);
    }
});

function initStageChart() {
    try {
        const ctx = document.getElementById('stageChart').getContext('2d');
        new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: chartData.stage.labels,
                datasets: [{
                    data: chartData.stage.data,
                    backgroundColor: [
                        '#4e73df',   // No DR
                        '#1cc88a',   // Mild
                        '#36b9cc',   // Moderate
                        '#f6c23e',   // Severe
                        '#e74a3b'    // Proliferative DR
                    ],
                    hoverBackgroundColor: [
                        '#2e59d9',
                        '#17a673',
                        '#2c9faf',
                        '#dda20a',
                        '#be2617'
                    ],
                    hoverBorderColor: "rgba(234, 236, 244, 1)",
                }]
            },
            options: {
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: {
                            usePointStyle: true,
                            padding: 20
                        }
                    }
                },
                cutout: '70%',
            }
        });
    } catch (error) {
        console.error("Error initializing stage chart:", error);
        document.getElementById('stageChart').closest('.card-body').innerHTML = `
            <div class="alert alert-danger">
                <i class="bi bi-exclamation-triangle-fill me-2"></i>
                Error loading stage chart. Please try again.
            </div>
        `;
    }
}

function initMonthlyChart() {
    try {
        const ctx = document.getElementById('monthlyChart').getContext('2d');
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: chartData.monthly.labels,
                datasets: [{
                    label: "Analyses",
                    lineTension: 0.3,
                    backgroundColor: "rgba(78, 115, 223, 0.05)",
                    borderColor: "rgba(78, 115, 223, 1)",
                    pointRadius: 4,
                    pointBackgroundColor: "rgba(78, 115, 223, 1)",
                    pointBorderColor: "rgba(78, 115, 223, 1)",
                    pointHoverRadius: 5,
                    pointHoverBackgroundColor: "rgba(78, 115, 223, 1)",
                    pointHoverBorderColor: "rgba(78, 115, 223, 1)",
                    pointHitRadius: 10,
                    pointBorderWidth: 2,
                    data: chartData.monthly.data,
                }]
            },
            options: {
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    } catch (error) {
        console.error("Error initializing monthly chart:", error);
        document.getElementById('monthlyChart').closest('.card-body').innerHTML = `
            <div class="alert alert-danger">
                <i class="bi bi-exclamation-triangle-fill me-2"></i>
                Error loading monthly chart. Please try again.
            </div>
        `;
    }
}