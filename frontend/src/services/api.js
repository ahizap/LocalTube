import axios from 'axios';

const api = axios.create({
    baseURL: 'http://localhost:8080/api', // FastAPI default port modified
});

export default {
    async getSettings() {
        const res = await api.get('/settings');
        return res.data;
    },
    async saveSetting(key, value) {
        const res = await api.post(`/settings?key=${encodeURIComponent(key)}&value=${encodeURIComponent(JSON.stringify(value))}`);
        return res.data;
    },
    async triggerScan() {
        const res = await api.post('/scan');
        return res.data;
    },
    async getScanProgress() {
        const res = await api.get('/scan/progress');
        return res.data;
    },
    async cancelScan() {
        const res = await api.post('/scan/cancel');
        return res.data;
    },
    async getVideos() {
        const res = await api.get('/videos');
        return res.data;
    },
    async getVideoDetails(id) {
        const res = await api.get(`/videos/${id}`);
        return res.data;
    }
};
