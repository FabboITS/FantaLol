window.LecDataSource={
    async loadInsights(request){
        return request('/lec/summer-2026/insights');
    }
};
