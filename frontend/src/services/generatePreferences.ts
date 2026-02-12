import apiClient from './api';

export interface PreferenceSuggestions {
    job_titles: {
        current_level: string[];
        advancement: string[];
        career_pivot: string[];
    };
    country: string;
    cities: string[];
    work_arrangement: string;
}

export const generatePreferences = async (): Promise<PreferenceSuggestions> => {
    const response = await apiClient.post<{ success: boolean; suggestions: PreferenceSuggestions }>('/api/generate-preferences');
    if (!response.data.success) {
        throw new Error('Failed to generate preferences');
    }
    return response.data.suggestions;
};
