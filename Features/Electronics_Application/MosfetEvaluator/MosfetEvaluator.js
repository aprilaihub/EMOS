// MOSFET evaluator Feature
class MosfetEvaluatorFeature extends BaseFeature {
    constructor(featureId) {
        super(featureId, 'MOSFET evaluator', 'Evaluate MOSFET performance from uploaded CIF files and simulation parameters');
    }

    createInputsHTML() {
        return `
            <p>Configure all non-runtime solver inputs for MOSFET evaluator.</p>
            <div class="input-controls" style="max-height: 560px; overflow: auto; padding-right: 6px;">
                <p><strong>Geometry Inputs (defaults mirror Python solver)</strong></p>
                ${this.createNumberInput(`channelLengthNm_${this.featureId}`, 'Channel Length (nm, default 14)', '1', '1000', '0.1', '14')}
                ${this.createNumberInput(`sourceDrainLengthNm_${this.featureId}`, 'Source/Drain Length (nm, default 4)', '0.1', '1000', '0.1', '4')}
                ${this.createNumberInput(`oxideThicknessNm_${this.featureId}`, 'Oxide Thickness (nm, default 1)', '0.1', '100', '0.1', '1')}
                ${this.createNumberInput(`channelThicknessNm_${this.featureId}`, 'Channel Thickness (nm, default 4)', '0.1', '1000', '0.1', '4')}

                <p><strong>Mesh Inputs (defaults mirror Python solver)</strong></p>
                ${this.createNumberInput(`dxM_${this.featureId}`, 'Mesh dx (m, default 5e-10)', '1e-12', '1e-6', '1e-12', '5e-10')}
                ${this.createNumberInput(`dyM_${this.featureId}`, 'Mesh dy (m, default 5e-10)', '1e-12', '1e-6', '1e-12', '5e-10')}

                <p><strong>Thermal and Contact Inputs (defaults mirror Python solver)</strong></p>
                ${this.createNumberInput(`temperatureK_${this.featureId}`, 'Temperature (K, default 300)', '77', '1000', '1', '300')}
                ${this.createNumberInput(`gateWorkFunctionEv_${this.featureId}`, 'Gate Work Function (eV, default 3.65)', '2', '8', '0.01', '3.65')}
                ${this.createNumberInput(`sdWorkFunctionEv_${this.featureId}`, 'Source/Drain Work Function (eV, default 0.0)', '-10', '10', '0.01', '0.0')}

                <p><strong>Doping Inputs (defaults mirror Python solver)</strong></p>
                ${this.createNumberInput(`channelDopingCm3_${this.featureId}`, 'Channel Doping (cm^-3, default -1e15)', '-1e22', '1e22', '1e14', '-1e15')}
                ${this.createNumberInput(`sourceDrainDopingCm3_${this.featureId}`, 'Source/Drain Doping (cm^-3, default 1e20)', '1e15', '1e22', '1e14', '1e20')}

                <p><strong>Bias Sweep Inputs (defaults mirror Python solver)</strong></p>
                ${this.createNumberInput(`gateVoltageSweepStartV_${this.featureId}`, 'Gate Sweep Start (V, default 0.0)', '-10', '10', '0.01', '0.0')}
                ${this.createNumberInput(`gateVoltageSweepStopV_${this.featureId}`, 'Gate Sweep Stop (V, default 0.7)', '-10', '10', '0.01', '0.7')}
                ${this.createNumberInput(`numberOfGatePoints_${this.featureId}`, 'Gate Sweep Points Nvg (default 14)', '2', '500', '1', '14')}
                ${this.createNumberInput(`drainVoltageSweepStartV_${this.featureId}`, 'Drain Sweep Start (V, default 0.0)', '-10', '10', '0.01', '0.0')}
                ${this.createNumberInput(`drainVoltageSweepStopV_${this.featureId}`, 'Drain Sweep Stop (V, default 0.7)', '-10', '10', '0.01', '0.7')}
                ${this.createNumberInput(`numberOfDrainPoints_${this.featureId}`, 'Drain Sweep Points Nvd (default 13)', '2', '500', '1', '13')}
                ${this.createNumberInput(`drainVoltageVd_${this.featureId}`, 'Drain Voltage VD (legacy alias)', '0', '5', '0.01', '0.7')}

                <p><strong>Channel Material Inputs (defaults mirror Python solver)</strong></p>
                ${this.createNumberInput(`channelNc_${this.featureId}`, 'channel Nc (default 2.8e25)', '0', '1e30', '1e20', '2.8e25')}
                ${this.createNumberInput(`channelNv_${this.featureId}`, 'channel Nv (default 1.04e25)', '0', '1e30', '1e20', '1.04e25')}
                ${this.createNumberInput(`channelEpsRel_${this.featureId}`, 'channel relative permittivity ep (default 11.9)', '0.1', '1000', '0.1', '11.9')}
                ${this.createNumberInput(`channelUn_${this.featureId}`, 'channel electron mobility un (default 0.1500)', '0', '10', '0.0001', '0.1500')}
                ${this.createNumberInput(`channelUp_${this.featureId}`, 'channel hole mobility up (default 0.0475)', '0', '10', '0.0001', '0.0475')}
                ${this.createNumberInput(`channelXiEv_${this.featureId}`, 'channel electron affinity xi (eV, default 4.05)', '0', '10', '0.01', '4.05')}
                ${this.createNumberInput(`channelEgEv_${this.featureId}`, 'channel band gap Eg (eV, default 1.12)', '0', '20', '0.01', '1.12')}
                ${this.createNumberInput(`channelVsatN_${this.featureId}`, 'channel electron saturation velocity vsat_n (default 2e5)', '1e3', '1e8', '1e3', '2e5')}
                ${this.createNumberInput(`channelVsatP_${this.featureId}`, 'channel hole saturation velocity vsat_p (default 2e5)', '1e3', '1e8', '1e3', '2e5')}
                ${this.createNumberInput(`channelPowN_${this.featureId}`, 'channel pow_n (default 2.0)', '0.1', '10', '0.1', '2.0')}
                ${this.createNumberInput(`channelPowP_${this.featureId}`, 'channel pow_p (default 1.0)', '0.1', '10', '0.1', '1.0')}

                <p><strong>Insulator Material Inputs (defaults mirror Python solver)</strong></p>
                ${this.createNumberInput(`insulatorNc_${this.featureId}`, 'insulator Nc (default 1.0)', '0', '1e30', '1', '1.0')}
                ${this.createNumberInput(`insulatorNv_${this.featureId}`, 'insulator Nv (default 1.0)', '0', '1e30', '1', '1.0')}
                ${this.createNumberInput(`insulatorEpsRel_${this.featureId}`, 'insulator relative permittivity ep (default 3.9)', '0.1', '1000', '0.1', '3.9')}
                ${this.createNumberInput(`insulatorUn_${this.featureId}`, 'insulator electron mobility un (default 1e-3)', '0', '10', '0.0001', '1e-3')}
                ${this.createNumberInput(`insulatorUp_${this.featureId}`, 'insulator hole mobility up (default 1e-3)', '0', '10', '0.0001', '1e-3')}
                ${this.createNumberInput(`insulatorXiEv_${this.featureId}`, 'insulator electron affinity xi (eV, default 0.9)', '0', '20', '0.01', '0.9')}
                ${this.createNumberInput(`insulatorEgEv_${this.featureId}`, 'insulator band gap Eg (eV, default 9.0)', '0', '30', '0.01', '9.0')}
                ${this.createNumberInput(`insulatorVsatN_${this.featureId}`, 'insulator electron saturation velocity vsat_n (default 2e5)', '1e3', '1e8', '1e3', '2e5')}
                ${this.createNumberInput(`insulatorVsatP_${this.featureId}`, 'insulator hole saturation velocity vsat_p (default 2e5)', '1e3', '1e8', '1e3', '2e5')}
                ${this.createNumberInput(`insulatorPowN_${this.featureId}`, 'insulator pow_n (default 2.0)', '0.1', '10', '0.1', '2.0')}
                ${this.createNumberInput(`insulatorPowP_${this.featureId}`, 'insulator pow_p (default 1.0)', '0.1', '10', '0.1', '1.0')}

            </div>
        `;
    }

    createOutputsHTML() {
        return `
            <div class="output-display" id="outputDisplay_${this.featureId}">
                <div class="output-item">
                    <strong>Key Metrics:</strong>
                    <div id="metricsTable_${this.featureId}" style="margin-top: 0.5rem; display: none;">
                        <table style="width: 100%; border-collapse: collapse;">
                            <tbody id="metricsBody_${this.featureId}"></tbody>
                        </table>
                    </div>
                    <div id="metricsLoading_${this.featureId}">Calculating...</div>
                </div>
                
                <div class="output-item">
                    <strong>Id/W - Vd Characteristic Curve:</strong>
                    <div id="chartContainer_${this.featureId}" style="width: 100%; height: 350px; margin-top: 0.5rem;"></div>
                </div>
                
                <div class="output-item">
                    <strong>Download Full Results (JSON):</strong>
                    <div id="downloadLink_${this.featureId}" style="margin-top: 0.5rem;">Preparing download...</div>
                </div>
            </div>
        `;
    }

    async cancelProcessing() {
        if (!this.isProcessing) return;

        this._cancelled = true;

        const cancelBtn = document.getElementById(`cancelBtn_${this.featureId}`);
        if (cancelBtn) {
            cancelBtn.disabled = true;
            cancelBtn.textContent = 'Cancelling...';
        }

        this.addLog('Requesting cancellation...', 'warning');

        const backendUrl = window.EMOS_BACKEND_BASE_URL || window.BACKEND_BASE_URL || 'http://localhost:5001';
        try {
            const resp = await fetch(`${backendUrl}/api/process/${this.featureId}/cancel`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
            });

            if (resp.ok) {
                const data = await resp.json();
                this.addLog(`Backend: ${data.message || 'cancel acknowledged'}`, 'info');
            } else {
                this.addLog(`Backend cancel returned HTTP ${resp.status}`, 'warning');
            }
        } catch (err) {
            this.addLog(`Cancel request failed: ${err.message}`, 'error');
        }
    }

    async processFeature() {
        // Placeholder processing logic for MOSFET evaluator
        return {
            downloadResultsJson: 'Download Results (JSON) - placeholder',
        };
    }

    updateOutputs(results = null) {
        const finalResults = results || this.results;
        
        if (finalResults.error) {
            document.getElementById(`metricsLoading_${this.featureId}`).textContent = `Error: ${finalResults.error}`;
            return;
        }
        
        // Display key metrics
        if (finalResults.key_metrics) {
            this.displayKeyMetrics(finalResults.key_metrics);
        }
        
        // Plot characteristic curve
        if (finalResults.J_uA_per_um && finalResults.Vgs_V && finalResults.Vds_V) {
            this.plotCharacteristicCurve(finalResults.J_uA_per_um, finalResults.Vgs_V, finalResults.Vds_V);
        }
        
        // Display download link
        if (finalResults.json_filename && finalResults.json_path) {
            this.displayDownloadLink(finalResults.json_filename, finalResults.json_path);
        }
    }
    
    displayKeyMetrics(metrics) {
        const metricsTable = document.getElementById(`metricsTable_${this.featureId}`);
        const metricsBody = document.getElementById(`metricsBody_${this.featureId}`);
        const metricsLoading = document.getElementById(`metricsLoading_${this.featureId}`);
        
        if (!metricsBody) return;
        
        // Clear and populate table
        metricsBody.innerHTML = '';
        
        const metricsList = [
            { label: 'Id (on)', value: metrics.Id_on_uA_per_um, unit: 'μA/μm' },
            { label: 'Id (off)', value: metrics.Id_off_uA_per_um, unit: 'μA/μm' },
            { label: 'Vth (approx)', value: metrics.Vth_approx_V, unit: 'V' },
            { label: 'Ion/Ioff ratio', value: metrics.Ion_Ioff_ratio, unit: '' },
        ];
        
        metricsList.forEach((metric, idx) => {
            const row = document.createElement('tr');
            row.style.borderBottom = '1px solid #ddd';
            if (idx % 2 === 0) {
                row.style.backgroundColor = '#f9f9f9';
            }
            
            let valueStr;
            if (metric.value < 1e-3 || metric.value > 1e6) {
                valueStr = metric.value.toExponential(2);
            } else {
                valueStr = metric.value.toFixed(4);
            }
            
            row.innerHTML = `
                <td style="padding: 0.5rem; text-align: left;"><strong>${metric.label}</strong></td>
                <td style="padding: 0.5rem; text-align: right;">${valueStr} ${metric.unit}</td>
            `;
            metricsBody.appendChild(row);
        });
        
        metricsTable.style.display = 'block';
        metricsLoading.style.display = 'none';
    }
    
    plotCharacteristicCurve(J_data, Vgs_data, Vds_data) {
        const chartContainer = document.getElementById(`chartContainer_${this.featureId}`);
        if (!chartContainer) return;
        
        // Select 9 representative gate-bias curves
        const targetVgs = this.linspace(Math.min(...Vgs_data), Math.max(...Vgs_data), 9);
        const selIdx = targetVgs.map(v => this.argmin(Vgs_data.map(vgs => Math.abs(vgs - v))));
        
        // Remove duplicates while preserving order
        const uniqueIdx = [...new Set(selIdx)];
        
        // Prepare data for Plotly
        const traces = uniqueIdx.map(i => ({
            x: Vds_data,
            y: J_data[i],
            name: `Vgs=${Vgs_data[i].toFixed(3)} V`,
            mode: 'lines',
            line: { width: 2.5 }
        }));
        
        const layout = {
            title: 'Id/W - Vd Characteristic (L=14 nm)',
            xaxis: { 
                title: 'Vd (V)',
                showgrid: true,
                gridwidth: 1,
                gridcolor: 'rgba(200, 200, 200, 0.3)',
                zeroline: false
            },
            yaxis: { 
                title: 'Id/W (μA/μm)',
                showgrid: true,
                gridwidth: 1,
                gridcolor: 'rgba(200, 200, 200, 0.3)',
                zeroline: false
            },
            hovermode: 'closest',
            margin: { l: 80, r: 40, t: 60, b: 80 },
            showlegend: true,
            legend: {
                x: 0.98,
                y: 0.98,
                xanchor: 'right',
                yanchor: 'top',
                bgcolor: 'rgba(255, 255, 255, 0.8)',
                bordercolor: 'rgba(0, 0, 0, 0.2)',
                borderwidth: 1
            },
            plot_bgcolor: 'rgba(250, 250, 250, 0.5)'
        };
        
        // Check if Plotly is available
        if (typeof Plotly !== 'undefined') {
            Plotly.newPlot(chartContainer, traces, layout, { responsive: true });
        } else {
            // Fallback: simple canvas plot if Plotly not available
            this.fallbackPlotCurve(chartContainer, J_data, Vgs_data, Vds_data, uniqueIdx);
        }
    }
    
    fallbackPlotCurve(container, J_data, Vgs_data, Vds_data, selIdx) {
        const canvas = document.createElement('canvas');
        canvas.width = container.offsetWidth || 800;
        canvas.height = 350;
        container.innerHTML = '';
        container.appendChild(canvas);
        
        const ctx = canvas.getContext('2d');
        const padding = { left: 70, right: 30, top: 40, bottom: 60 };
        const plotWidth = canvas.width - padding.left - padding.right;
        const plotHeight = canvas.height - padding.top - padding.bottom;
        
        // Calculate data range
        const minVds = Math.min(...Vds_data);
        const maxVds = Math.max(...Vds_data);
        const maxJ = Math.max(...J_data.flat());
        const minJ = Math.min(...J_data.flat());
        
        // Generate nice tick marks
        const xTicks = this.generateTicks(minVds, maxVds, 5);
        const yTicks = this.generateTicks(minJ, maxJ, 5);
        
        // Draw background
        ctx.fillStyle = 'rgba(250, 250, 250, 0.5)';
        ctx.fillRect(padding.left, padding.top, plotWidth, plotHeight);
        
        // Draw grid (faint)
        ctx.strokeStyle = 'rgba(200, 200, 200, 0.3)';
        ctx.lineWidth = 1;
        
        // Vertical grid lines
        xTicks.forEach(tick => {
            const x = padding.left + ((tick - minVds) / (maxVds - minVds)) * plotWidth;
            ctx.beginPath();
            ctx.moveTo(x, padding.top);
            ctx.lineTo(x, padding.top + plotHeight);
            ctx.stroke();
        });
        
        // Horizontal grid lines
        yTicks.forEach(tick => {
            const y = padding.top + plotHeight - ((tick - minJ) / (maxJ - minJ)) * plotHeight;
            ctx.beginPath();
            ctx.moveTo(padding.left, y);
            ctx.lineTo(padding.left + plotWidth, y);
            ctx.stroke();
        });
        
        // Draw axes
        ctx.strokeStyle = '#000';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(padding.left, padding.top + plotHeight);
        ctx.lineTo(padding.left + plotWidth, padding.top + plotHeight);
        ctx.stroke();
        
        ctx.beginPath();
        ctx.moveTo(padding.left, padding.top);
        ctx.lineTo(padding.left, padding.top + plotHeight);
        ctx.stroke();
        
        // Draw X-axis ticks and labels
        ctx.fillStyle = '#000';
        ctx.font = '11px Arial';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';
        xTicks.forEach(tick => {
            const x = padding.left + ((tick - minVds) / (maxVds - minVds)) * plotWidth;
            ctx.beginPath();
            ctx.moveTo(x, padding.top + plotHeight);
            ctx.lineTo(x, padding.top + plotHeight + 5);
            ctx.stroke();
            ctx.fillText(tick.toFixed(2), x, padding.top + plotHeight + 8);
        });
        
        // Draw Y-axis ticks and labels
        ctx.textAlign = 'right';
        ctx.textBaseline = 'middle';
        yTicks.forEach(tick => {
            const y = padding.top + plotHeight - ((tick - minJ) / (maxJ - minJ)) * plotHeight;
            ctx.beginPath();
            ctx.moveTo(padding.left - 5, y);
            ctx.lineTo(padding.left, y);
            ctx.stroke();
            ctx.fillText(tick.toExponential(1), padding.left - 8, y);
        });
        
        // Draw axis labels
        ctx.font = 'bold 12px Arial';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';
        ctx.fillText('Vd (V)', canvas.width / 2, canvas.height - 10);
        
        ctx.save();
        ctx.translate(15, canvas.height / 2);
        ctx.rotate(-Math.PI / 2);
        ctx.textAlign = 'center';
        ctx.textBaseline = 'bottom';
        ctx.fillText('Id/W (μA/μm)', 0, 0);
        ctx.restore();
        
        // Draw curves
        const colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22'];
        selIdx.forEach((idx, colorIdx) => {
            ctx.strokeStyle = colors[colorIdx % colors.length];
            ctx.lineWidth = 2;
            ctx.beginPath();
            
            J_data[idx].forEach((j, vdsIdx) => {
                const x = padding.left + ((Vds_data[vdsIdx] - minVds) / (maxVds - minVds)) * plotWidth;
                const y = padding.top + plotHeight - ((j - minJ) / (maxJ - minJ)) * plotHeight;
                
                if (vdsIdx === 0) {
                    ctx.moveTo(x, y);
                } else {
                    ctx.lineTo(x, y);
                }
            });
            ctx.stroke();
        });
        
        // Draw legend
        const legendX = padding.left + plotWidth - 150;
        const legendY = padding.top + 10;
        const legendItemHeight = 20;
        
        ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
        ctx.strokeStyle = 'rgba(0, 0, 0, 0.2)';
        ctx.lineWidth = 1;
        ctx.fillRect(legendX, legendY, 140, selIdx.length * legendItemHeight + 8);
        ctx.strokeRect(legendX, legendY, 140, selIdx.length * legendItemHeight + 8);
        
        selIdx.forEach((idx, colorIdx) => {
            const y = legendY + 4 + colorIdx * legendItemHeight + 8;
            
            // Color line
            ctx.strokeStyle = colors[colorIdx % colors.length];
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.moveTo(legendX + 8, y);
            ctx.lineTo(legendX + 25, y);
            ctx.stroke();
            
            // Label
            ctx.fillStyle = '#000';
            ctx.font = '10px Arial';
            ctx.textAlign = 'left';
            ctx.textBaseline = 'middle';
            ctx.fillText(`Vgs=${Vgs_data[idx].toFixed(3)} V`, legendX + 32, y);
        });
    }
    
    generateTicks(min, max, targetCount) {
        const range = max - min;
        const step = Math.pow(10, Math.floor(Math.log10(range / targetCount)));
        const tickStart = Math.ceil(min / step) * step;
        const ticks = [];
        
        for (let tick = tickStart; tick <= max; tick += step) {
            ticks.push(parseFloat(tick.toFixed(10)));
        }
        
        return ticks.length > 0 ? ticks : [min, max];
    }
    
    displayDownloadLink(filename, filepath) {
        const downloadDiv = document.getElementById(`downloadLink_${this.featureId}`);
        if (!downloadDiv) return;
        
        downloadDiv.innerHTML = `
            <a id="downloadLink_json_${this.featureId}" style="cursor: pointer; color: #0078d4; text-decoration: underline;">${filename}</a>
        `;
        
        const link = document.getElementById(`downloadLink_json_${this.featureId}`);
        link.addEventListener('click', () => this.downloadResultsJSON(filepath, filename));
    }
    
    async downloadResultsJSON(filepath, filename) {
        try {
            const response = await fetch(filepath, { method: 'GET' });
            if (!response.ok) throw new Error('Download failed');
            
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } catch (error) {
            // Fallback: try to fetch from backend API
            const backendUrl = window.EMOS_BACKEND_BASE_URL || window.BACKEND_BASE_URL || 'http://localhost:5001';
            try {
                const response = await fetch(`${backendUrl}/api/download/${filename}`);
                if (response.ok) {
                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = filename;
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    document.body.removeChild(a);
                }
            } catch (e) {
                alert(`Could not download file: ${e.message}`);
            }
        }
    }
    
    // Helper functions
    linspace(start, end, num) {
        const result = [];
        const step = (end - start) / (num - 1);
        for (let i = 0; i < num; i++) {
            result.push(start + step * i);
        }
        return result;
    }
    
    argmin(arr) {
        return arr.reduce((idx, val, i) => val < arr[idx] ? i : idx, 0);
    }
}

window.MosfetEvaluatorFeature = MosfetEvaluatorFeature;
