class TerrainViewer {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.init3DScene();
        this.initControls();
        this.currentMode = '3d';
        this.breakLinePoints = [];
        this.isBreakLineMode = false;
        this.pointData = null;  // Store point data for analysis
    }

    init3DScene() {
        // Scene setup with improved visuals
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0xf8f9fa);  // Match Bootstrap bg-light
        
        this.camera = new THREE.PerspectiveCamera(75, this.container.clientWidth / this.container.clientHeight, 0.1, 1000);
        this.renderer = new THREE.WebGLRenderer({ 
            antialias: true,
            alpha: true 
        });
        this.renderer.setSize(this.container.clientWidth, this.container.clientHeight);
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.container.appendChild(this.renderer.domElement);

        // Enhanced lighting for better depth perception
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
        const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
        directionalLight.position.set(10, 10, 10);
        const backLight = new THREE.DirectionalLight(0xffffff, 0.3);
        backLight.position.set(-10, 5, -10);
        this.scene.add(ambientLight, directionalLight, backLight);

        // Initial camera position
        this.camera.position.set(50, 50, 50);
        this.camera.lookAt(0, 0, 0);

        // Enhanced grid helper
        const gridHelper = new THREE.GridHelper(100, 20, 0x666666, 0xcccccc);
        gridHelper.material.opacity = 0.5;
        gridHelper.material.transparent = true;
        this.scene.add(gridHelper);

        // Start animation loop
        this.animate();
    }

    initControls() {
        // Enhanced orbit controls
        this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.05;
        this.controls.rotateSpeed = 0.8;
        this.controls.zoomSpeed = 1.2;
        this.controls.panSpeed = 0.8;

        // Responsive handling
        const resizeObserver = new ResizeObserver(() => {
            this.camera.aspect = this.container.clientWidth / this.container.clientHeight;
            this.camera.updateProjectionMatrix();
            this.renderer.setSize(this.container.clientWidth, this.container.clientHeight);
        });
        resizeObserver.observe(this.container);

        // Enhanced point selection
        this.renderer.domElement.addEventListener('click', (event) => {
            if (!this.isBreakLineMode) return;
            
            const rect = this.renderer.domElement.getBoundingClientRect();
            const x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
            const y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
            
            this.handlePointSelection(x, y);
        });

        // Add hover effect for points
        this.renderer.domElement.addEventListener('mousemove', (event) => {
            const rect = this.renderer.domElement.getBoundingClientRect();
            const x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
            const y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
            
            this.handlePointHover(x, y);
        });
    }

    animate() {
        requestAnimationFrame(() => this.animate());
        this.controls.update();
        this.renderer.render(this.scene, this.camera);
    }

    displayTerrain(terrainData) {
        // Clear existing terrain
        this.clearTerrain();

        // Store point data for analysis
        this.pointData = terrainData.points;

        // Create point cloud geometry
        const geometry = new THREE.BufferGeometry();
        const positions = [];
        const colors = [];

        let minZ = Infinity;
        let maxZ = -Infinity;

        // Process points
        terrainData.points.forEach(point => {
            const [id, x, y, z] = point;
            positions.push(x, z, -y); // Three.js uses Y as up axis
            minZ = Math.min(minZ, z);
            maxZ = Math.max(maxZ, z);
        });

        // Enhanced color scale using viridis-like palette
        const colorScale = (z) => {
            const t = (z - minZ) / (maxZ - minZ);
            const h = (1 - t) * 0.6; // Blue to red
            const s = 0.8;
            const l = 0.4 + t * 0.2; // Darker to brighter
            return new THREE.Color().setHSL(h, s, l);
        };

        terrainData.points.forEach(([id, x, y, z]) => {
            const color = colorScale(z);
            colors.push(color.r, color.g, color.b);
        });

        geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
        geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));

        // Enhanced point material
        const material = new THREE.PointsMaterial({
            size: 0.5,
            vertexColors: true,
            sizeAttenuation: true,
        });

        // Create and add point cloud to scene
        this.pointCloud = new THREE.Points(geometry, material);
        this.scene.add(this.pointCloud);

        // Add break lines with enhanced styling
        this.addBreakLines(terrainData.break_lines, terrainData.points);

        // Center camera on terrain
        this.centerCamera();
    }

    addBreakLines(breakLines, points) {
        const material = new THREE.LineBasicMaterial({ 
            color: 0xff3333,
            linewidth: 2,
            opacity: 0.8,
            transparent: true
        });

        breakLines.forEach(pointIds => {
            const geometry = new THREE.BufferGeometry();
            const positions = [];

            pointIds.forEach(id => {
                const point = points.find(p => p[0] === id);
                if (point) {
                    positions.push(point[1], point[3], -point[2]); // x, z, -y
                }
            });

            geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
            const line = new THREE.Line(geometry, material);
            this.scene.add(line);
        });
    }

    clearTerrain() {
        if (this.pointCloud) {
            this.scene.remove(this.pointCloud);
            this.pointCloud.geometry.dispose();
            this.pointCloud.material.dispose();
        }

        // Remove break lines and other objects
        this.scene.children = this.scene.children.filter(child => 
            child.type === 'GridHelper' || 
            child.type === 'DirectionalLight' || 
            child.type === 'AmbientLight'
        );

        // Clear stored data
        this.pointData = null;
    }

    centerCamera() {
        if (!this.pointCloud) return;

        const box = new THREE.Box3().setFromObject(this.pointCloud);
        const center = box.getCenter(new THREE.Vector3());
        const size = box.getSize(new THREE.Vector3());

        // Position camera to view entire terrain with margin
        const maxDim = Math.max(size.x, size.y, size.z);
        const fov = this.camera.fov * (Math.PI / 180);
        const cameraZ = Math.abs(maxDim / Math.sin(fov / 2)) * 1.5;

        this.camera.position.set(center.x + cameraZ, center.y + cameraZ, center.z + cameraZ);
        this.camera.lookAt(center);
        this.camera.updateProjectionMatrix();
        this.controls.target.copy(center);
    }

    toggleView() {
        this.currentMode = this.currentMode === '3d' ? '2d' : '3d';
        
        if (this.currentMode === '2d') {
            // Smooth transition to top view
            const duration = 1000;
            const startPos = this.camera.position.clone();
            const endPos = new THREE.Vector3(0, 100, 0);
            
            const start = performance.now();
            const animate = (currentTime) => {
                const elapsed = currentTime - start;
                const progress = Math.min(elapsed / duration, 1);
                
                // Ease out cubic
                const t = 1 - Math.pow(1 - progress, 3);
                
                this.camera.position.lerpVectors(startPos, endPos, t);
                this.camera.lookAt(0, 0, 0);
                
                if (progress < 1) {
                    requestAnimationFrame(animate);
                } else {
                    this.controls.maxPolarAngle = 0;
                    this.controls.minPolarAngle = 0;
                }
            };
            
            requestAnimationFrame(animate);
        } else {
            this.controls.maxPolarAngle = Math.PI;
            this.controls.minPolarAngle = 0;
            this.centerCamera();
        }
    }

    startBreakLine() {
        this.isBreakLineMode = true;
        this.breakLinePoints = [];
        
        // Visual feedback
        this.container.style.cursor = 'crosshair';
    }

    finishBreakLine() {
        this.isBreakLineMode = false;
        this.container.style.cursor = 'default';
        const pointIds = this.breakLinePoints.map(p => p.id);
        this.breakLinePoints = [];
        return pointIds;
    }

    handlePointSelection(x, y) {
        const raycaster = new THREE.Raycaster();
        raycaster.params.Points.threshold = 0.5;
        const mouse = new THREE.Vector2(x, y);
        
        raycaster.setFromCamera(mouse, this.camera);
        const intersects = raycaster.intersectObject(this.pointCloud);
        
        if (intersects.length > 0) {
            const index = intersects[0].index;
            const point = this.pointData[index];
            this.breakLinePoints.push({ id: point[0], x: point[1], y: point[2], z: point[3] });
            
            // Visual feedback
            const highlightMaterial = new THREE.PointsMaterial({
                color: 0xff0000,
                size: 1.0
            });
            
            const highlightGeometry = new THREE.BufferGeometry();
            const position = intersects[0].point;
            highlightGeometry.setAttribute('position', new THREE.Float32BufferAttribute([position.x, position.y, position.z], 3));
            
            const highlight = new THREE.Points(highlightGeometry, highlightMaterial);
            this.scene.add(highlight);
        }
    }

    handlePointHover(x, y) {
        if (!this.isBreakLineMode || !this.pointCloud) return;
        
        const raycaster = new THREE.Raycaster();
        raycaster.params.Points.threshold = 0.5;
        const mouse = new THREE.Vector2(x, y);
        
        raycaster.setFromCamera(mouse, this.camera);
        const intersects = raycaster.intersectObject(this.pointCloud);
        
        this.container.style.cursor = intersects.length > 0 ? 'pointer' : 'crosshair';
    }
}
