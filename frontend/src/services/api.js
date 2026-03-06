import axios from 'axios';

const api = axios.create({
    baseURL: '/api',
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
    async triggerScan(type = "all", directory = "") {
        const res = await api.post(`/scan?type=${encodeURIComponent(type)}&directory=${encodeURIComponent(directory)}`);
        return res.data;
    },
    async getTasks() {
        const res = await api.get('/tasks');
        return res.data;
    },
    async cancelTask(taskId) {
        const res = await api.post(`/tasks/${encodeURIComponent(taskId)}/cancel`);
        return res.data;
    },
    async clearFinishedTasks() {
        const res = await api.post('/tasks/clear');
        return res.data;
    },
    async listDirectory(path = "") {
        const res = await api.get(`/fs/list?path=${encodeURIComponent(path)}`);
        return res.data;
    },
    async getLibraryFolders() {
        const res = await api.get('/library/folders');
        return res.data;
    },
    async deleteVideo(videoId) {
        const res = await api.delete(`/library/videos/${videoId}`);
        return res.data;
    },
    async deleteFolder(folderPath) {
        const res = await api.delete(`/library/folders?folder=${encodeURIComponent(folderPath)}`);
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
