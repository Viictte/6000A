class StorySparkApp {
    constructor() {
        this.apiBaseUrl = '/api';
        this.lastQuery = null;
        this.timelineButtons = [];
        this.userId = this.restoreUserId();
        this.notificationsEnabled = false;
        this.missions = [];
        this.missionProgress = {};
        this.selfieFile = null;
        this.selfieCharacterDescription = null;
        this.initializeEventListeners();
        this.initializeNotificationPreferences();
        this.fetchMissions();
    }

    initializeEventListeners() {
        const form = document.getElementById('comicForm');
        form.addEventListener('submit', (e) => this.handleSubmit(e));

        const missionsList = document.getElementById('missionsList');
        if (missionsList) {
            missionsList.addEventListener('click', (event) => this.handleMissionListClick(event));
        }

        const missionNotifyBtn = document.getElementById('missionNotifyBtn');
        if (missionNotifyBtn) {
            missionNotifyBtn.addEventListener('click', () => this.requestBrowserNotifications(true));
        }

        const selfieUploadBtn = document.getElementById('selfieUploadBtn');
        const selfieUpload = document.getElementById('selfieUpload');
        const removeSelfieBtn = document.getElementById('removeSelfieBtn');

        if (selfieUploadBtn && selfieUpload) {
            selfieUploadBtn.addEventListener('click', () => selfieUpload.click());
            selfieUpload.addEventListener('change', (e) => this.handleSelfieUpload(e));
        }

        if (removeSelfieBtn) {
            removeSelfieBtn.addEventListener('click', () => this.removeSelfie());
        }

        const viewNotificationsBtn = document.getElementById('viewNotificationsBtn');
        const closeNotificationModal = document.getElementById('closeNotificationModal');
        
        if (viewNotificationsBtn) {
            viewNotificationsBtn.addEventListener('click', () => this.showNotificationModal());
        }
        
        if (closeNotificationModal) {
            closeNotificationModal.addEventListener('click', () => this.hideNotificationModal());
        }

        const notificationTabs = document.querySelectorAll('.tab-btn');
        notificationTabs.forEach(tab => {
            tab.addEventListener('click', (e) => this.switchNotificationTab(e.target.dataset.tab));
        });
    }
    
    async handleSubmit(event) {
        event.preventDefault();
        
        const topic = document.getElementById('topic').value.trim();
        const ageGroup = document.getElementById('ageGroup').value;
        const imageStyle = document.getElementById('imageStyle').value;

        if (!topic) {
            alert('Please enter a topic!');
            return;
        }

        this.lastQuery = {
            topic,
            ageGroup,
            imageStyle
        };
        
        this.showLoading();
        
        try {
            const response = await fetch(`${this.apiBaseUrl}/generate-comic`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    topic: topic,
                    age_group: ageGroup,
                    image_style: imageStyle
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.displayResult(data);
            } else {
                this.showError(data.error || 'Failed to generate comic');
            }
            
        } catch (error) {
            console.error('Error:', error);
            this.showError('Network error, please try again later');
        }
        
        this.hideLoading();
    }
    
    showLoading() {
        document.getElementById('loading').classList.remove('hidden');
        document.getElementById('result').classList.add('hidden');
        document.getElementById('generateBtn').disabled = true;
    }
    
    hideLoading() {
        document.getElementById('loading').classList.add('hidden');
        document.getElementById('generateBtn').disabled = false;
    }
    
    displayResult(data) {
        const resultDiv = document.getElementById('result');
        const comicDisplay = document.getElementById('comicDisplay');
        const stepsDisplay = document.getElementById('stepsDisplay');

        console.log('Display result:', data);
        console.log('Comic ID:', data.comic_id);

        // Set English title
        const steps = data.steps || [];
        const topicTitle = steps[0] ? this.extractTopicFromTitle(steps[0].title) : (this.lastQuery?.topic || 'Tutorial');
        const heroSection = this.buildHeroSection(topicTitle, data.comic_url, steps);
        const timeline = this.buildTimeline(steps);
        comicDisplay.innerHTML = `${heroSection}${timeline}`;

        // Clear steps display area
        this.renderStepCarousel(stepsDisplay, steps, data.comic_id);
        this.bindTimelineInteractions();
        this.bindHeroActions(data.comic_url);

        // Show result area
        resultDiv.classList.remove('hidden');

        // Scroll to result
        resultDiv.scrollIntoView({ behavior: 'smooth' });
    }

    buildHeroSection(topicTitle, comicUrl, steps) {
        const summary = steps[0]?.description || 'Ready to explore a new skill!';
        const topicInput = this.lastQuery?.topic || topicTitle;
        const audience = this.lastQuery ? `Designed for ages ${this.lastQuery.ageGroup}` : 'Kid-friendly adventure';
        const styleLabel = this.humanizeStyle(this.lastQuery?.imageStyle);

        const media = comicUrl
            ? `<img src="${comicUrl}" alt="Complete comic" class="full-comic-image" loading="lazy" />`
            : `<div class="hero-placeholder">Comic panels are on the way!</div>`;

        const highlights = steps.length
            ? `<ul class="hero-highlights">${steps.slice(0, 3).map((step, idx) => `<li>Step ${idx + 1}: ${this.formatStepTitle(step.title)}</li>`).join('')}</ul>`
            : '';

        return `
            <section class="comic-hero">
                <div class="hero-media">${media}</div>
                <div class="hero-details">
                    <p class="hero-kicker">StorySpark Comic</p>
                    <h3 class="hero-title">${topicInput}</h3>
                    <p class="hero-meta">${audience} · ${styleLabel}</p>
                    <p class="hero-summary">${summary}</p>
                    ${highlights}
                    <div class="hero-actions">
                        <button type="button" id="downloadComicBtn" class="btn primary">Download Comic</button>
                        <button type="button" id="toggleStoryboardBtn" class="btn ghost">Show Storyboard Grid</button>
                    </div>
                </div>
            </section>
        `;
    }

    buildTimeline(steps) {
        if (!steps.length) {
            return '';
        }

        const nodes = steps.map((step, index) => `
            <button class="timeline-node" data-step="${index}" type="button">
                <span class="node-index">${index + 1}</span>
                <span class="node-title">${this.shortStepLabel(step.title)}</span>
            </button>
        `).join('');

        return `
            <div class="story-timeline" role="tablist">
                ${nodes}
            </div>
        `;
    }
    
    extractTopicFromTitle(firstTitle) {
        // Extract main topic from first step title
        const cleaned = firstTitle.replace(/^Step\s*\d+:\s*/i, '').replace(/🚀|📖|✨|🎉|[0-9]/g, '').trim();
        const words = cleaned.split(' ');
        return words.slice(0, 3).join(' ');
    }
    
    createStepCard(step, index, comicId) {
        const card = document.createElement('article');
        card.className = 'step-card';

        // Build single panel image URL
        const panelImageUrl = `/static/generated_comics/comic_${comicId}_panel_${index}.png`;
        console.log(`Step ${index + 1} image URL:`, panelImageUrl);

        const actionCue = step.action_scene ? `<p class="step-action">${step.action_scene}</p>` : '';

        card.innerHTML = `
            <div class="step-pill">
                <span class="step-mood">${this.pickMoodIcon(index)}</span>
                <span class="step-number-label">Step ${index + 1}</span>
            </div>
            <h4 class="step-title">${this.formatStepTitle(step.title)}</h4>
            ${actionCue}
            <div class="step-image-container">
                <img
                    class="step-image"
                    src="${panelImageUrl}"
                    alt="Step ${index + 1}"
                    loading="lazy"
                    onload="console.log('Image loaded successfully: Step ${index + 1}')"
                    onerror="this.parentElement.innerHTML='<div class=\\'image-placeholder\\'>Image loading...</div>'; console.error('Image failed to load:', this.src)"
                />
            </div>
            <div class="step-description">
                ${step.description}
            </div>
        `;

        return card;
    }

    formatStepTitle(title) {
        // Remove "Step N:" prefix, keep only main title and emoji
        if (!title) {
            return 'Creative step';
        }
        const cleaned = title.replace(/^Step\s*\d+:\s*/i, '').replace(/^Step\s*\d+\s*[-:]\s*/i, '');
        return cleaned;
    }

    shortStepLabel(title) {
        const cleaned = this.formatStepTitle(title);
        return cleaned.length > 24 ? `${cleaned.slice(0, 24)}…` : cleaned;
    }

    capitalizeFirst(str) {
        if (!str) return '';
        return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
    }

    humanizeStyle(styleTag) {
        if (!styleTag) return 'Playful style';
        const cleaned = styleTag.replace(/[<>]/g, '').trim();
        if (!cleaned) return 'Playful style';

        return cleaned.split(/\s+/).map((word) => {
            if (word.toLowerCase() === '3d') {
                return '3D';
            }
            return word.charAt(0).toUpperCase() + word.slice(1);
        }).join(' ');
    }

    pickMoodIcon(index) {
        const moods = ['🚀', '🎨', '🛠️', '🧠', '🎯', '🌟', '🤹‍♀️', '🎵'];
        return moods[index % moods.length];
    }

    renderStepCarousel(container, steps, comicId) {
        container.innerHTML = '';
        container.classList.add('carousel-view');
        container.classList.remove('grid-view');

        const track = document.createElement('div');
        track.className = 'step-cards-track';

        steps.forEach((step, index) => {
            const stepCard = this.createStepCard(step, index, comicId);
            stepCard.dataset.stepCard = index;
            track.appendChild(stepCard);
        });

        if (!steps.length) {
            track.innerHTML = '<p class="empty-storyboard">No storyboard steps available yet.</p>';
        }

        container.appendChild(track);
        this.updateStoryboardToggleLabel();
    }

    bindTimelineInteractions() {
        this.timelineButtons = Array.from(document.querySelectorAll('.timeline-node'));
        this.timelineButtons.forEach((btn) => {
            btn.addEventListener('click', () => {
                const stepIndex = Number(btn.dataset.step);
                this.scrollToStepCard(stepIndex);
                this.setActiveTimelineNode(stepIndex);
            });
        });

        if (this.timelineButtons.length) {
            this.setActiveTimelineNode(0);
        }
    }

    bindHeroActions(comicUrl) {
        const downloadBtn = document.getElementById('downloadComicBtn');
        if (downloadBtn) {
            downloadBtn.addEventListener('click', () => this.downloadComic(comicUrl));
        }

        const toggleBtn = document.getElementById('toggleStoryboardBtn');
        if (toggleBtn) {
            toggleBtn.addEventListener('click', () => this.toggleStoryboardView());
        }

        this.updateStoryboardToggleLabel();
    }

    toggleStoryboardView() {
        const container = document.getElementById('stepsDisplay');
        if (!container) return;

        container.classList.toggle('grid-view');
        container.classList.toggle('carousel-view');
        this.updateStoryboardToggleLabel();
    }

    updateStoryboardToggleLabel() {
        const toggleBtn = document.getElementById('toggleStoryboardBtn');
        const container = document.getElementById('stepsDisplay');
        if (!toggleBtn || !container) return;

        const isGrid = container.classList.contains('grid-view');
        toggleBtn.textContent = isGrid ? 'Show Cinematic Scroll' : 'Show Storyboard Grid';
    }

    downloadComic(url) {
        if (!url) return;
        const link = document.createElement('a');
        link.href = url;
        link.download = 'storyspark_comic.png';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    scrollToStepCard(stepIndex) {
        const target = document.querySelector(`.step-card[data-step-card="${stepIndex}"]`);
        if (target) {
            target.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' });
        }
    }

    setActiveTimelineNode(stepIndex) {
        if (!this.timelineButtons?.length) return;
        this.timelineButtons.forEach((btn) => {
            const isActive = Number(btn.dataset.step) === stepIndex;
            btn.classList.toggle('active', isActive);
        });
    }

    restoreUserId() {
        try {
            const stored = window.localStorage.getItem('storysparkUserId');
            if (stored) {
                return stored;
            }
            const newId = `guest-${Math.random().toString(36).slice(2, 10)}`;
            window.localStorage.setItem('storysparkUserId', newId);
            return newId;
        } catch (error) {
            console.warn('Unable to access localStorage, using ephemeral id', error);
            return `guest-${Date.now()}`;
        }
    }

    initializeNotificationPreferences() {
        if (!('Notification' in window)) {
            this.notificationsEnabled = false;
            this.updateNotificationButton();
            return;
        }

        this.notificationsEnabled = Notification.permission === 'granted';
        if (Notification.permission === 'default') {
            // Lazy prompt later when user interacts.
            this.notificationsEnabled = false;
        }
        this.updateNotificationButton();
    }

    async requestBrowserNotifications(forcePrompt = false) {
        if (!('Notification' in window)) {
            this.notificationsEnabled = false;
            this.updateNotificationButton();
            return;
        }

        if (Notification.permission === 'default' || forcePrompt) {
            try {
                const permission = await Notification.requestPermission();
                this.notificationsEnabled = permission === 'granted';
            } catch (error) {
                console.warn('Notification permission failed', error);
                this.notificationsEnabled = false;
            }
        } else {
            this.notificationsEnabled = Notification.permission === 'granted';
        }

        this.updateNotificationButton();
    }

    updateNotificationButton() {
        const btn = document.getElementById('missionNotifyBtn');
        if (!btn) return;

        if (!('Notification' in window)) {
            btn.textContent = 'Notifications unavailable';
            btn.disabled = true;
            return;
        }

        btn.classList.remove('primary', 'ghost');
        if (this.notificationsEnabled) {
            btn.textContent = 'Mission alerts enabled';
            btn.classList.add('ghost');
        } else {
            btn.textContent = 'Enable Mission Alerts';
            btn.classList.add('primary');
        }
    }

    triggerBrowserNotification({ title, body }) {
        if (!this.notificationsEnabled || !('Notification' in window)) {
            return;
        }

        try {
            new Notification(title, { body });
        } catch (error) {
            console.warn('Browser notification failed', error);
        }
    }

    handleMissionListClick(event) {
        const actionButton = event.target.closest('[data-action]');
        if (!actionButton) {
            return;
        }
        const missionId = actionButton.dataset.missionId;
        if (!missionId) return;

        const action = actionButton.dataset.action;
        if (action === 'enroll') {
            this.enrollMission(missionId);
        } else if (action === 'complete-step') {
            this.completeNextTopic(missionId);
        } else if (action === 'claim-dare') {
            const dareId = actionButton.dataset.dareId;
            if (dareId) {
                this.claimDare(missionId, dareId);
            }
        }
    }

    async fetchMissions() {
        const container = document.getElementById('missionsList');
        if (!container) return;

        try {
            const response = await fetch(`${this.apiBaseUrl}/missions?user_id=${this.userId}`);
            if (!response.ok) {
                throw new Error('Failed to load missions');
            }
            const payload = await response.json();
            this.missions = payload.missions || [];
            this.missions.forEach((mission) => {
                if (mission.progress) {
                    this.missionProgress[mission.id] = mission.progress;
                }
            });
            this.renderMissions();
        } catch (error) {
            console.error('Mission fetch failed', error);
            container.innerHTML = '<p class="mission-empty">Unable to load missions right now.</p>';
        }
    }

    renderMissions() {
        const container = document.getElementById('missionsList');
        if (!container) return;

        if (!this.missions.length) {
            container.innerHTML = '<p class="mission-empty">No missions published yet.</p>';
            return;
        }

        const fragment = document.createDocumentFragment();
        this.missions.forEach((mission) => {
            const card = document.createElement('article');
            card.className = 'mission-card';
            card.dataset.missionId = mission.id;
            card.innerHTML = this.buildMissionCard(mission);
            fragment.appendChild(card);
        });

        container.innerHTML = '';
        container.appendChild(fragment);
    }

    buildMissionCard(mission) {
        const progress = this.getMissionProgressSnapshot(mission);
        const topics = mission.topics || [];
        const topicsList = topics.map((topic) => {
            const isDone = progress.completedTopicIds.includes(topic.id);
            return `<li class="mission-topic ${isDone ? 'completed' : ''}">
                <span>${topic.title}</span>
                <span>${isDone ? '✔️' : ''}</span>
            </li>`;
        }).join('');

        const percent = progress.totalTopics ? Math.round((progress.completedCount / progress.totalTopics) * 100) : 0;
        const nextTopic = progress.nextTopic;
        const isComplete = progress.totalTopics > 0 && progress.completedCount >= progress.totalTopics;

        const primaryLabel = progress.enrolled ? 'Continue Mission' : 'Start Mission';
        const completeDisabled = !progress.enrolled || !nextTopic || isComplete ? 'disabled' : '';

        const unlockedDares = progress.unlockedDares || [];
        const claimedDares = progress.claimedDares || [];
        const nextDare = progress.nextDare;
        
        const daresSection = unlockedDares.length > 0 ? `
            <div class="mission-dares">
                <h4 class="dare-header">🎉 Parent Dares Unlocked!</h4>
                <p class="dare-explanation">Complete topics to unlock fun challenges for parents!</p>
                <ul class="dare-list">
                    ${unlockedDares.map(dare => {
                        const isClaimed = claimedDares.includes(dare.id);
                        return `<li class="dare-item ${isClaimed ? 'claimed' : ''}">
                            <div class="dare-content">
                                <strong>${dare.title}</strong>
                                <p>${dare.description}</p>
                                <small>Unlocked after ${dare.unlock_after} topics</small>
                            </div>
                            ${isClaimed ? '<span class="dare-badge">✅ Claimed!</span>' : 
                              `<button type="button" class="btn-dare" data-action="claim-dare" data-mission-id="${mission.id}" data-dare-id="${dare.id}">Claim Dare</button>`}
                        </li>`;
                    }).join('')}
                </ul>
            </div>
        ` : '';

        return `
            <header>
                <div class="mission-meta">${mission.badge || '🎯'} Ages ${mission.recommended_age}</div>
                <h3>${mission.title}</h3>
                <p>${mission.description}</p>
            </header>
            <div class="mission-progress">
                <div class="progress-track">
                    <div class="progress-fill" style="width: ${percent}%"></div>
                </div>
                <small>${progress.completedCount}/${progress.totalTopics || topics.length} topics complete</small>
            </div>
            <p class="mission-next-topic">${isComplete ? 'Mission complete!' : nextTopic ? `Next: ${nextTopic.title}` : 'Enroll to unlock topics'}</p>
            <ul class="mission-topics">${topicsList}</ul>
            ${daresSection}
            <div class="mission-actions">
                <button type="button" class="btn primary" data-action="enroll" data-mission-id="${mission.id}">${primaryLabel}</button>
                <button type="button" class="btn ghost" data-action="complete-step" data-mission-id="${mission.id}" ${completeDisabled}>Mark Next Topic Done</button>
            </div>
        `;
    }

    getMissionProgressSnapshot(mission) {
        const fallback = mission.progress || {};
        const local = this.missionProgress[mission.id] || fallback;
        const completedTopicIds = local?.completed_topics || [];
        const totalTopics = mission.topics?.length || local?.total_topics || 0;
        let nextTopic = null;
        if (local?.enrolled) {
            nextTopic = local?.next_topic || null;
            if (!nextTopic && mission.topics) {
                nextTopic = mission.topics.find((topic) => !completedTopicIds.includes(topic.id)) || null;
            }
        }
        const completedCount = local?.completed_count ?? completedTopicIds.length;
        const enrolled = Boolean(local?.enrolled);
        const unlockedDares = local?.unlocked_dares || [];
        const claimedDares = local?.claimed_dares || [];
        const nextDare = local?.next_dare || null;

        return {
            enrolled,
            completedCount,
            totalTopics,
            nextTopic,
            completedTopicIds,
            isComplete: Boolean(local?.is_complete),
            unlockedDares,
            claimedDares,
            nextDare
        };
    }

    async enrollMission(missionId) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/missions/enroll`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    user_id: this.userId,
                    mission_id: missionId
                })
            });
            if (!response.ok) {
                throw new Error('Failed to enroll in mission');
            }
            const data = await response.json();
            this.missionProgress[missionId] = data.progress;
            this.renderMissions();
            this.triggerBrowserNotification({
                title: 'Mission ready',
                body: `You joined ${data.mission?.title || 'a mission'}!`
            });
        } catch (error) {
            console.error('Mission enrollment failed', error);
            alert('Unable to enroll in this mission right now.');
        }
    }

    async completeNextTopic(missionId) {
        const snapshot = this.missionProgress[missionId];
        const nextTopic = snapshot?.next_topic;
        if (!nextTopic) {
            return;
        }
        await this.completeTopic(missionId, nextTopic.id, nextTopic.title);
    }

    async completeTopic(missionId, topicId, topicTitle) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/missions/complete-step`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    user_id: this.userId,
                    mission_id: missionId,
                    topic_id: topicId
                })
            });
            if (!response.ok) {
                throw new Error('Unable to complete mission topic');
            }
            const data = await response.json();
            this.missionProgress[missionId] = data.progress;
            this.renderMissions();

            const mission = this.missions.find((item) => item.id === missionId);
            if (data.progress?.is_complete) {
                this.triggerBrowserNotification({
                    title: 'Mission complete 🎉',
                    body: `${mission?.title || 'Mission'} finished!`
                });
            } else {
                this.triggerBrowserNotification({
                    title: 'Topic checked off',
                    body: `${topicTitle || 'Topic'} completed.`
                });
            }
        } catch (error) {
            console.error('Failed to complete mission topic', error);
            alert('Unable to update mission progress.');
        }
    }

    async claimDare(missionId, dareId) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/missions/claim-dare`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    user_id: this.userId,
                    mission_id: missionId,
                    dare_id: dareId
                })
            });
            if (!response.ok) {
                throw new Error('Unable to claim dare');
            }
            const data = await response.json();
            this.missionProgress[missionId] = data.progress;
            this.renderMissions();

            const dare = data.claimed_dare;
            this.triggerBrowserNotification({
                title: 'Dare Claimed! 🎉',
                body: `Parent must complete: ${dare?.title || 'the dare'}`
            });
        } catch (error) {
            console.error('Failed to claim dare', error);
            alert('Unable to claim dare. Make sure you have unlocked it!');
        }
    }

    handleSelfieUpload(event) {
        const file = event.target.files[0];
        if (!file) return;

        if (!file.type.startsWith('image/')) {
            alert('Please upload a valid image file');
            return;
        }

        this.selfieFile = file;
        const reader = new FileReader();
        reader.onload = (e) => {
            const preview = document.getElementById('selfiePreview');
            const previewImg = document.getElementById('selfiePreviewImg');
            previewImg.src = e.target.result;
            preview.classList.remove('hidden');
        };
        reader.readAsDataURL(file);

        this.uploadSelfieToServer(file);
    }

    removeSelfie() {
        this.selfieFile = null;
        this.selfieCharacterDescription = null;
        const preview = document.getElementById('selfiePreview');
        const previewImg = document.getElementById('selfiePreviewImg');
        const selfieUpload = document.getElementById('selfieUpload');
        
        preview.classList.add('hidden');
        previewImg.src = '';
        selfieUpload.value = '';
    }

    async uploadSelfieToServer(file) {
        try {
            const formData = new FormData();
            formData.append('selfie', file);
            formData.append('user_id', this.userId);

            const response = await fetch(`${this.apiBaseUrl}/upload-selfie`, {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                const data = await response.json();
                this.selfieCharacterDescription = data.character_description;
                console.log('Selfie uploaded successfully:', data);
            } else {
                console.error('Failed to upload selfie');
            }
        } catch (error) {
            console.error('Error uploading selfie:', error);
        }
    }

    showNotificationModal() {
        const modal = document.getElementById('notificationModal');
        modal.classList.remove('hidden');
        this.loadNotifications();
    }

    hideNotificationModal() {
        const modal = document.getElementById('notificationModal');
        modal.classList.add('hidden');
    }

    switchNotificationTab(tab) {
        const tabs = document.querySelectorAll('.tab-btn');
        tabs.forEach(t => t.classList.remove('active'));
        event.target.classList.add('active');
        this.loadNotifications(tab);
    }

    async loadNotifications(type = 'email') {
        const notificationList = document.getElementById('notificationList');
        
        try {
            const response = await fetch(`${this.apiBaseUrl}/notifications?user_id=${this.userId}&type=${type}`);
            if (response.ok) {
                const data = await response.json();
                const notifications = data.notifications || [];
                
                if (notifications.length === 0) {
                    notificationList.innerHTML = '<p class="notification-empty">No notifications yet. Complete missions to receive updates!</p>';
                    return;
                }
                
                notificationList.innerHTML = notifications.map(notif => `
                    <div class="notification-item ${type}">
                        <div class="notification-icon">${type === 'email' ? '📧' : '🔔'}</div>
                        <div class="notification-content">
                            <h4>${notif.title || notif.subject}</h4>
                            <p>${notif.body}</p>
                            <small>${new Date(notif.timestamp).toLocaleString()}</small>
                        </div>
                    </div>
                `).join('');
            }
        } catch (error) {
            console.error('Failed to load notifications:', error);
            notificationList.innerHTML = '<p class="notification-empty">Failed to load notifications.</p>';
        }
    }

    showError(message) {
        alert(`Error: ${message}`);
    }
}

// Initialize application
document.addEventListener('DOMContentLoaded', () => {
    new StorySparkApp();
});
