import api from './api';

export async function getOnboardingStatus(): Promise<{
    onboarding_completed: boolean;
    onboarding_step: number;
    onboarding_skipped: boolean;
}> {
    const { data } = await api.get('/api/onboarding/status');
    return data;
}

export async function updateOnboardingStep(step: number): Promise<{ success: boolean }> {
    const { data } = await api.post('/api/onboarding/update', { step });
    return data;
}

export async function completeOnboarding(): Promise<{ success: boolean }> {
    const { data } = await api.post('/api/onboarding/complete');
    return data;
}

export async function skipOnboarding(): Promise<{ success: boolean }> {
    const { data } = await api.post('/api/onboarding/skip');
    return data;
}
