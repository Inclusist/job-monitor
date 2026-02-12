import apiClient from './api';

export interface SearchQueries {
    titles: string[];
    locations: string[];
    work_arrangement: string | null;
    query_count: number;
}

export const getSearchQueries = async (): Promise<SearchQueries> => {
    const response = await apiClient.get<SearchQueries>('/api/search-queries');
    return response.data;
};
