class SegmentViewer {
    constructor() {
        this.segment = null;
        this.allocations = [];
        this.colors = this.getColorsFromCSS();
        this.init();
    }

    init() {
        this.loadSegmentData();
        this.updateVisualization();
        this.updateAllocationsTable();
        this.initInfoBox();
    }

    loadSegmentData() {
        const dataElement = document.getElementById('segment-data');
        if (dataElement) {
            this.segment = JSON.parse(dataElement.textContent);
            this.allocations = this.segment.allocations || [];
        } else {
            console.error('segment-data element not found');
        }
    }

    getColorsFromCSS() {
        const style = getComputedStyle(document.documentElement);
        return [
            style.getPropertyValue('--segment-color-0').trim() || '#0072B2',
            style.getPropertyValue('--segment-color-1').trim() || '#E69F00',
            style.getPropertyValue('--segment-color-2').trim() || '#009E73',
            style.getPropertyValue('--segment-color-3').trim() || '#CC79A7',
            style.getPropertyValue('--segment-color-4').trim() || '#F0E442',
            style.getPropertyValue('--segment-color-5').trim() || '#D55E00',
            style.getPropertyValue('--segment-color-6').trim() || '#56B4E9',
            style.getPropertyValue('--segment-color-7').trim() || '#999999'
        ];
    }

    initInfoBox() {
        const infoBox = document.getElementById('allocation-info-box');
        
        infoBox.addEventListener('mouseenter', () => {
            this.clearHideTimeout();
        });
        
        infoBox.addEventListener('mouseleave', () => {
            this.scheduleHideAllocationInfo();
        });
    }

    parseNetwork(cidr) {
        const [ip, prefixLength] = cidr.split('/');
        const ipParts = ip.split('.').map(Number);
        const ipInt = (ipParts[0] << 24) | (ipParts[1] << 16) | (ipParts[2] << 8) | ipParts[3];
        const maskBits = parseInt(prefixLength);
        const size = Math.pow(2, 32 - maskBits);
        const mask = (0xFFFFFFFF << (32 - maskBits)) >>> 0;
        const start = (ipInt & mask) >>> 0;
        
        return { start, size, mask };
    }

    compareNetworks(networkA, networkB) {
        const parsedA = this.parseNetwork(networkA);
        const parsedB = this.parseNetwork(networkB);
        
        if (parsedA.start !== parsedB.start) {
            return parsedA.start - parsedB.start;
        }
        
        const prefixA = parseInt(networkA.split('/')[1]);
        const prefixB = parseInt(networkB.split('/')[1]);
        return prefixA - prefixB;
    }

    updateVisualization() {
        const networkBar = document.getElementById('network-bar');
        networkBar.innerHTML = '';
        
        if (!this.segment || !this.segment.network || this.allocations.length === 0) {
            // Add a placeholder message when there are no allocations
            if (!this.segment || !this.segment.network) {
                networkBar.innerHTML = '<div style="padding: 20px; text-align: center; color: var(--color-text-muted);">No base network defined for this block</div>';
            } else if (this.allocations.length === 0) {
                networkBar.innerHTML = '<div style="padding: 20px; text-align: center; color: var(--color-text-muted);">No subnets allocated yet. Add subnets to see the network visualization.</div>';
            }
            return;
        }

        const baseNetwork = this.parseNetwork(this.segment.network);
        const totalAddresses = baseNetwork.size;
        
        // Sort allocations by start address
        const sortedAllocations = [...this.allocations].sort((a, b) => {
            const aStart = this.parseNetwork(a.network).start;
            const bStart = this.parseNetwork(b.network).start;
            return aStart - bStart;
        });

        // Assign colors (avoiding adjacent duplicates)
        let lastColorIndex = -1;
        sortedAllocations.forEach((allocation, index) => {
            let colorIndex = (lastColorIndex + 1) % this.colors.length;
            if (colorIndex === lastColorIndex && this.colors.length > 1) {
                colorIndex = (colorIndex + 1) % this.colors.length;
            }
            allocation.colorIndex = colorIndex;
            lastColorIndex = colorIndex;
        });

        // Create boundary lines first (so they appear behind allocation segments)
        this.createBoundaryLines(networkBar, baseNetwork, totalAddresses);

        // Create visualization segments
        sortedAllocations.forEach((allocation) => {
            const allocNetwork = this.parseNetwork(allocation.network);
            const startPercent = ((allocNetwork.start - baseNetwork.start) / totalAddresses) * 100;
            const widthPercent = (allocNetwork.size / totalAddresses) * 100;

            const segment = document.createElement('div');
            segment.className = 'allocation-segment';
            segment.style.left = `${startPercent}%`;
            segment.style.width = `${widthPercent}%`;
            segment.style.backgroundColor = this.colors[allocation.colorIndex];
            
            // Add hover events
            segment.addEventListener('mouseenter', (e) => {
                this.clearHideTimeout();
                this.showAllocationInfo(e, allocation);
            });
            
            segment.addEventListener('mouseleave', (e) => {
                this.scheduleHideAllocationInfo();
            });
            
            segment.addEventListener('mousemove', (e) => {
                if (this.currentlyShowing) {
                    this.updateInfoBoxPosition(e);
                }
            });

            networkBar.appendChild(segment);
        });
    }

    createBoundaryLines(networkBar, baseNetwork, totalAddresses) {
        // Determine boundary size based on container prefix length
        const containerPrefix = parseInt(this.segment.network.split('/')[1]);
        let boundaryPrefix;
        
        if (containerPrefix >= 16) {
            // Container is /16 or greater (smaller network) → mark at /24 boundaries
            boundaryPrefix = 24;
        } else if (containerPrefix >= 8) {
            // Container is /8-/16 → mark at /16 boundaries
            boundaryPrefix = 16;
        } else {
            // Container is smaller than /8 → mark at /8 boundaries
            boundaryPrefix = 8;
        }
        
        // Calculate boundary interval
        const boundarySize = Math.pow(2, 32 - boundaryPrefix);
        
        // Find first boundary within the container
        const containerStart = baseNetwork.start;
        const containerEnd = baseNetwork.start + baseNetwork.size;
        
        // Round up to first boundary
        const firstBoundary = Math.ceil(containerStart / boundarySize) * boundarySize;
        
        // Create boundary lines
        for (let boundary = firstBoundary; boundary < containerEnd; boundary += boundarySize) {
            // Skip if boundary is at the very start (0% position)
            if (boundary === containerStart) continue;
            
            const boundaryPercent = ((boundary - containerStart) / totalAddresses) * 100;
            
            // Only show boundaries that are within the visible area (0% to 100%)
            if (boundaryPercent > 0 && boundaryPercent < 100) {
                const line = document.createElement('div');
                line.className = 'boundary-line';
                line.style.left = `${boundaryPercent}%`;
                line.title = `/${boundaryPrefix} boundary: ${this.intToIP(boundary)}`;
                networkBar.appendChild(line);
            }
        }
    }

    updateAllocationsTable() {
        // Update the size column for each allocation
        this.allocations.forEach(allocation => {
            const sizeCell = document.querySelector(`[data-network="${allocation.network}"]`);
            if (sizeCell) {
                const network = this.parseNetwork(allocation.network);
                sizeCell.textContent = `${network.size} addresses`;
            }
        });
    }

    showAllocationInfo(event, allocation) {
        this.clearHideTimeout();
        
        const infoBox = document.getElementById('allocation-info-box');
        if (!infoBox) return;
        
        const network = this.parseNetwork(allocation.network);
        this.currentlyShowing = true;
        
        // Update content
        const colorIndicator = infoBox.querySelector('.info-box-color-indicator');
        const networkElement = infoBox.querySelector('.info-box-network');
        const descriptionValue = infoBox.querySelector('.description-value');
        const vlanValue = infoBox.querySelector('.vlan-value');
        const sizeValue = infoBox.querySelector('.size-value');
        const rangeValue = infoBox.querySelector('.range-value');
        
        if (colorIndicator) colorIndicator.style.backgroundColor = this.colors[allocation.colorIndex];
        if (networkElement) networkElement.textContent = allocation.network;
        
        if (descriptionValue) {
            descriptionValue.textContent = allocation.description || 'No description';
            descriptionValue.className = allocation.description ? 'info-box-value description-value' : 'info-box-value description-value info-box-empty';
        }
        
        if (vlanValue) {
            vlanValue.textContent = allocation.vlan_tag || 'No VLAN';
            vlanValue.className = allocation.vlan_tag ? 'info-box-value vlan-value' : 'info-box-value vlan-value info-box-empty';
        }
        
        if (sizeValue) sizeValue.textContent = `${network.size} addresses`;
        
        if (rangeValue) {
            const startIP = this.intToIP(network.start);
            const endIP = this.intToIP(network.start + network.size - 1);
            rangeValue.textContent = `${startIP} - ${endIP}`;
        }
        
        // Position the info box
        this.updateInfoBoxPosition(event);
        
        // Show with animation
        requestAnimationFrame(() => {
            infoBox.classList.add('show');
        });
    }

    updateInfoBoxPosition(event) {
        const infoBox = document.getElementById('allocation-info-box');
        if (!infoBox.classList.contains('show')) return;
        
        const rect = event.target.getBoundingClientRect();
        const containerRect = document.querySelector('.visualization-container').getBoundingClientRect();
        const infoBoxWidth = 280;
        
        let leftPos = rect.left - containerRect.left + (rect.width / 2) - (infoBoxWidth / 2);
        const maxLeft = containerRect.width - infoBoxWidth - 10;
        leftPos = Math.max(10, Math.min(leftPos, maxLeft));
        
        infoBox.style.left = `${leftPos}px`;
        infoBox.style.top = `${rect.bottom - containerRect.top + 10}px`;
    }

    hideAllocationInfo() {
        const infoBox = document.getElementById('allocation-info-box');
        infoBox.classList.remove('show');
        this.currentlyShowing = false;
        this.clearHideTimeout();
    }

    scheduleHideAllocationInfo() {
        this.hideTimeout = setTimeout(() => {
            this.hideAllocationInfo();
        }, 100);
    }

    clearHideTimeout() {
        if (this.hideTimeout) {
            clearTimeout(this.hideTimeout);
            this.hideTimeout = null;
        }
    }

    intToIP(int) {
        return [
            (int >>> 24) & 255,
            (int >>> 16) & 255,
            (int >>> 8) & 255,
            int & 255
        ].join('.');
    }
}

// Initialize the segment viewer
document.addEventListener('DOMContentLoaded', function() {
    new SegmentViewer();
});